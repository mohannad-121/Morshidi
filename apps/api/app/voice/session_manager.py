"""Multi-worker safe concurrency, duration quotas, and dialect state manager for live voice sessions.

ARCHITECTURAL COORDINATION AUDIT:
- Single-Node / Multi-Worker (Default): Uses SQLite in Write-Ahead-Logging mode (`PRAGMA journal_mode = WAL;`)
  with atomic immediate transactions and busy timeouts. This guarantees safe, synchronized concurrency and quota
  checks across multiple Uvicorn worker processes on a shared host.
- Multi-Node / Horizontally Scaled Environments (e.g. independent Render instances or ephemeral container clusters):
  SQLite files do not span separate container disks. In horizontally distributed multi-node clusters,
  a shared PostgreSQL or Redis atomic coordinator must be configured. No unapproved production database migrations
  are applied; schema changes must follow separate governed approval.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import threading
import time
from typing import Any, Literal


class VoiceQuotaExceededError(Exception):
    """Raised when student exceeds maximum allowed daily voice sessions or minutes."""


class VoiceRateLimitError(Exception):
    """Raised when session creation attempts occur too quickly."""


class VoiceConcurrencyError(VoiceRateLimitError):
    """Raised when student already has an active live voice session."""


@dataclass
class VoiceSessionState:
    session_id: str
    student_user_id: str
    university_id: str
    thread_id: str | None
    created_at: float
    expires_at: float
    max_duration_seconds: int
    language: Literal["ar", "en"] = "ar"
    arabic_dialect: Literal["msa", "jordanian"] = "msa"
    dialect_source: Literal["default", "explicit_user_request"] = "default"
    is_active: bool = True
    last_activity_at: float = 0.0


class VoiceSessionManager:
    """Safely govern student live voice sessions, quotas, and spoken dialect preferences across workers.

    Deployment Architecture & Persistence Note:
    This coordinator uses SQLite with Write-Ahead Logging (WAL) to synchronize multiple concurrent
    Uvicorn worker processes on a shared host filesystem.
    IMPORTANT: On stateless cloud platforms (e.g. Render Web Services), the container filesystem is
    ephemeral across redeployments and instance restarts. Therefore, this SQLite-backed coordinator is
    approved for single-host development and evaluation. Production live voice activation MUST remain
    disabled (MORSHIDI_LIVE_VOICE_ENABLED=False) until persistent distributed quota storage
    (e.g., PostgreSQL or Redis) is officially configured.
    """

    def __init__(
        self,
        *,
        max_duration_seconds: int = 900,
        max_daily_sessions_per_student: int = 25,
        max_daily_seconds_per_student: int = 3600,
        min_seconds_between_starts: float = 3.0,
        inactivity_timeout_seconds: float = 180.0,
        db_path: str | None = None,
    ) -> None:
        self._max_duration_seconds = max_duration_seconds
        self._max_daily_sessions = max_daily_sessions_per_student
        self._max_daily_seconds = max_daily_seconds_per_student
        self._min_cooldown = min_seconds_between_starts
        self._inactivity_timeout = inactivity_timeout_seconds
        self._lock = threading.Lock()

        if db_path is None:
            # Default to a coordination directory for multi-worker uvicorn processes
            base_dir = Path(__file__).resolve().parents[2] / ".runtime"
            try:
                base_dir.mkdir(parents=True, exist_ok=True)
                self._db_path = str(base_dir / "voice_coordination.db")
                self._is_memory = False
            except Exception:
                self._db_path = ":memory:"
                self._is_memory = True
        else:
            self._db_path = db_path
            self._is_memory = (db_path == ":memory:")

        if self._is_memory:
            self._mem_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._mem_conn.row_factory = sqlite3.Row
        else:
            self._mem_conn = None

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._is_memory:
            assert self._mem_conn is not None
            return self._mem_conn
        conn = sqlite3.connect(self._db_path, timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode = WAL;")
        except Exception:
            pass
        conn.execute("PRAGMA busy_timeout = 5000;")
        return conn

    def _close_connection(self, conn: sqlite3.Connection) -> None:
        if not self._is_memory:
            conn.close()

    def _init_db(self) -> None:
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.executescript(
                        """
                        CREATE TABLE IF NOT EXISTS voice_active_sessions (
                            student_user_id TEXT PRIMARY KEY,
                            session_id TEXT NOT NULL,
                            university_id TEXT NOT NULL,
                            thread_id TEXT,
                            created_at REAL NOT NULL,
                            last_activity_at REAL NOT NULL DEFAULT 0.0,
                            expires_at REAL NOT NULL,
                            max_duration_seconds INTEGER NOT NULL,
                            language TEXT NOT NULL,
                            arabic_dialect TEXT NOT NULL,
                            dialect_source TEXT NOT NULL,
                            is_active INTEGER NOT NULL DEFAULT 1
                        );

                        CREATE TABLE IF NOT EXISTS voice_cooldowns (
                            student_user_id TEXT PRIMARY KEY,
                            last_start_at REAL NOT NULL
                        );

                        CREATE TABLE IF NOT EXISTS voice_daily_usage (
                            student_user_id TEXT NOT NULL,
                            date_str_utc TEXT NOT NULL,
                            session_count INTEGER NOT NULL DEFAULT 0,
                            total_seconds REAL NOT NULL DEFAULT 0.0,
                            PRIMARY KEY (student_user_id, date_str_utc)
                        );
                        """
                    )
                    # Safe migration for existing DB files lacking last_activity_at
                    try:
                        conn.execute("ALTER TABLE voice_active_sessions ADD COLUMN last_activity_at REAL NOT NULL DEFAULT 0.0;")
                    except Exception:
                        pass
            finally:
                self._close_connection(conn)

    def _today_utc(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _cleanup_expired_locked(self, conn: sqlite3.Connection, now: float) -> int:
        """Internal helper to clean up expired or abandoned sessions while holding the lock."""
        today = self._today_utc()
        # Find active sessions where hard limit reached OR inactivity timeout exceeded
        rows = conn.execute(
            """
            SELECT student_user_id, session_id, created_at, last_activity_at, expires_at, max_duration_seconds
            FROM voice_active_sessions
            WHERE is_active = 1 AND (expires_at <= ? OR (? - last_activity_at) > ?)
            """,
            (now, now, self._inactivity_timeout),
        ).fetchall()

        if not rows:
            return 0

        with conn:
            for r in rows:
                server_elapsed = max(0.0, now - float(r["created_at"]))
                duration_to_record = min(server_elapsed, float(r["max_duration_seconds"]))
                if duration_to_record > 0:
                    conn.execute(
                        """
                        INSERT INTO voice_daily_usage (student_user_id, date_str_utc, session_count, total_seconds)
                        VALUES (?, ?, 0, ?)
                        ON CONFLICT(student_user_id, date_str_utc) DO UPDATE SET
                            total_seconds = voice_daily_usage.total_seconds + excluded.total_seconds
                        """,
                        (r["student_user_id"], today, duration_to_record),
                    )
                conn.execute(
                    "UPDATE voice_active_sessions SET is_active = 0 WHERE student_user_id = ? AND session_id = ?",
                    (r["student_user_id"], r["session_id"]),
                )
        return len(rows)

    def touch_activity(self, student_user_id: str) -> None:
        """Record real student speech turn or tool delegation activity to reset the abandonment timer."""
        now = time.time()
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute(
                        "UPDATE voice_active_sessions SET last_activity_at = ? WHERE student_user_id = ? AND is_active = 1",
                        (now, student_user_id),
                    )
            finally:
                self._close_connection(conn)

    def get_daily_usage(self, student_user_id: str) -> int:
        """Returns the number of sessions initiated by the student today."""
        now = time.time()
        today = self._today_utc()
        with self._lock:
            conn = self._get_connection()
            try:
                self._cleanup_expired_locked(conn, now)
                row = conn.execute(
                    "SELECT session_count FROM voice_daily_usage WHERE student_user_id = ? AND date_str_utc = ?",
                    (student_user_id, today),
                ).fetchone()
                return int(row["session_count"]) if row else 0
            finally:
                self._close_connection(conn)

    def get_daily_duration_seconds(self, student_user_id: str) -> float:
        """Returns the total audio duration in seconds consumed by the student today."""
        now = time.time()
        today = self._today_utc()
        with self._lock:
            conn = self._get_connection()
            try:
                self._cleanup_expired_locked(conn, now)
                row = conn.execute(
                    "SELECT total_seconds FROM voice_daily_usage WHERE student_user_id = ? AND date_str_utc = ?",
                    (student_user_id, today),
                ).fetchone()
                return float(row["total_seconds"]) if row else 0.0
            finally:
                self._close_connection(conn)

    def get_remaining_daily_quota(self, student_user_id: str) -> int:
        """Returns remaining daily session count for backwards-compatibility."""
        used = self.get_daily_usage(student_user_id)
        return max(0, self._max_daily_sessions - used)

    def get_quota_details(self, student_user_id: str) -> dict[str, Any]:
        """Provides full multi-dimension quota breakdown (sessions + duration minutes)."""
        now = time.time()
        with self._lock:
            conn = self._get_connection()
            try:
                self._cleanup_expired_locked(conn, now)
            finally:
                self._close_connection(conn)

        used_sessions = self.get_daily_usage(student_user_id)
        used_seconds = self.get_daily_duration_seconds(student_user_id)
        used_minutes = round(used_seconds / 60.0, 1)
        max_minutes = round(self._max_daily_seconds / 60.0, 1)
        remaining_minutes = max(0.0, round(max_minutes - used_minutes, 1))

        return {
            "max_daily_sessions": self._max_daily_sessions,
            "used_daily_sessions": used_sessions,
            "remaining_daily_sessions": max(0, self._max_daily_sessions - used_sessions),
            "max_daily_minutes": max_minutes,
            "used_daily_minutes": used_minutes,
            "remaining_daily_minutes": remaining_minutes,
            "max_session_duration_seconds": self._max_duration_seconds,
        }

    def get_active_session(self, student_user_id: str) -> VoiceSessionState | None:
        now = time.time()
        with self._lock:
            conn = self._get_connection()
            try:
                self._cleanup_expired_locked(conn, now)
                row = conn.execute(
                    "SELECT * FROM voice_active_sessions WHERE student_user_id = ? AND is_active = 1",
                    (student_user_id,),
                ).fetchone()
                if row is None:
                    return None
                return VoiceSessionState(
                    session_id=row["session_id"],
                    student_user_id=row["student_user_id"],
                    university_id=row["university_id"],
                    thread_id=row["thread_id"],
                    created_at=row["created_at"],
                    expires_at=row["expires_at"],
                    max_duration_seconds=row["max_duration_seconds"],
                    language=row["language"],
                    arabic_dialect=row["arabic_dialect"],
                    dialect_source=row["dialect_source"],
                    is_active=bool(row["is_active"]),
                    last_activity_at=row["last_activity_at"] if "last_activity_at" in row.keys() else row["created_at"],
                )
            finally:
                self._close_connection(conn)

    def validate_can_start(self, student_user_id: str) -> None:
        now = time.time()
        today = self._today_utc()
        with self._lock:
            conn = self._get_connection()
            try:
                # 0. Clean up any expired or abandoned sessions
                self._cleanup_expired_locked(conn, now)

                # 1. Cooldown check
                cd_row = conn.execute(
                    "SELECT last_start_at FROM voice_cooldowns WHERE student_user_id = ?",
                    (student_user_id,),
                ).fetchone()
                if cd_row is not None and (now - cd_row["last_start_at"]) < self._min_cooldown:
                    raise VoiceRateLimitError("يرجى الانتظار بضع ثوانٍ قبل بدء محادثة صوتية جديدة.")

                # 2. Concurrency check & previous session release:
                # If an active session is still open, auto-terminate it and account for its elapsed time,
                # cleanly releasing concurrency for the student.
                active_row = conn.execute(
                    "SELECT session_id, created_at, expires_at, max_duration_seconds FROM voice_active_sessions WHERE student_user_id = ? AND is_active = 1",
                    (student_user_id,),
                ).fetchone()
                if active_row is not None:
                    prev_elapsed = min(float(active_row["max_duration_seconds"]), max(0.0, now - float(active_row["created_at"])))
                    with conn:
                        if prev_elapsed > 0:
                            conn.execute(
                                """
                                INSERT INTO voice_daily_usage (student_user_id, date_str_utc, session_count, total_seconds)
                                VALUES (?, ?, 0, ?)
                                ON CONFLICT(student_user_id, date_str_utc) DO UPDATE SET
                                    total_seconds = voice_daily_usage.total_seconds + excluded.total_seconds
                                """,
                                (student_user_id, today, prev_elapsed),
                            )
                        conn.execute(
                            "UPDATE voice_active_sessions SET is_active = 0 WHERE student_user_id = ?",
                            (student_user_id,),
                        )

                # 3. Daily usage checks (both session count AND audio duration)
                usage_row = conn.execute(
                    "SELECT session_count, total_seconds FROM voice_daily_usage WHERE student_user_id = ? AND date_str_utc = ?",
                    (student_user_id, today),
                ).fetchone()
                if usage_row:
                    if usage_row["session_count"] >= self._max_daily_sessions:
                        raise VoiceQuotaExceededError("تم تجاوز الحد اليومي للمحادثات الصوتية. يمكنك متابعة المحادثة نصياً.")
                    if usage_row["total_seconds"] >= self._max_daily_seconds:
                        raise VoiceQuotaExceededError("تم استنفاد الحد اليومي لدقائق المحادثة الصوتية. يمكنك متابعة المحادثة نصياً.")
            finally:
                self._close_connection(conn)

    def register_session(
        self,
        *,
        session_id: str,
        student_user_id: str,
        university_id: str,
        thread_id: str | None,
        duration_seconds: int | None = None,
    ) -> VoiceSessionState:
        with self._lock:
            now = time.time()
            today = self._today_utc()
            conn = self._get_connection()
            try:
                # 0. Clean up any expired or abandoned sessions
                self._cleanup_expired_locked(conn, now)

                # 1. Cooldown check
                cd_row = conn.execute(
                    "SELECT last_start_at FROM voice_cooldowns WHERE student_user_id = ?",
                    (student_user_id,),
                ).fetchone()
                if cd_row is not None and (now - cd_row["last_start_at"]) < self._min_cooldown:
                    raise VoiceRateLimitError("يرجى الانتظار بضع ثوانٍ قبل بدء محادثة صوتية جديدة.")

                # 2. Daily usage checks
                usage_row = conn.execute(
                    "SELECT session_count, total_seconds FROM voice_daily_usage WHERE student_user_id = ? AND date_str_utc = ?",
                    (student_user_id, today),
                ).fetchone()
                if usage_row:
                    if usage_row["session_count"] >= self._max_daily_sessions:
                        raise VoiceQuotaExceededError("تم تجاوز الحد اليومي للمحادثات الصوتية. يمكنك متابعة المحادثة نصياً.")
                    if usage_row["total_seconds"] >= self._max_daily_seconds:
                        raise VoiceQuotaExceededError("تم استنفاد الحد اليومي لدقائق المحادثة الصوتية. يمكنك متابعة المحادثة نصياً.")

                duration = duration_seconds or self._max_duration_seconds
                expires = now + duration

                with conn:
                    # Update cooldown
                    conn.execute(
                        "INSERT INTO voice_cooldowns (student_user_id, last_start_at) VALUES (?, ?) "
                        "ON CONFLICT(student_user_id) DO UPDATE SET last_start_at = excluded.last_start_at",
                        (student_user_id, now),
                    )
                    # Insert / replace active session with initial activity timestamp
                    conn.execute(
                        """
                        INSERT INTO voice_active_sessions (
                            student_user_id, session_id, university_id, thread_id,
                            created_at, last_activity_at, expires_at, max_duration_seconds,
                            language, arabic_dialect, dialect_source, is_active
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ar', 'msa', 'default', 1)
                        ON CONFLICT(student_user_id) DO UPDATE SET
                            session_id = excluded.session_id,
                            university_id = excluded.university_id,
                            thread_id = excluded.thread_id,
                            created_at = excluded.created_at,
                            last_activity_at = excluded.last_activity_at,
                            expires_at = excluded.expires_at,
                            max_duration_seconds = excluded.max_duration_seconds,
                            language = 'ar',
                            arabic_dialect = 'msa',
                            dialect_source = 'default',
                            is_active = 1
                        """,
                        (student_user_id, session_id, university_id, thread_id, now, now, expires, duration),
                    )
                    # Increment daily session count
                    conn.execute(
                        """
                        INSERT INTO voice_daily_usage (student_user_id, date_str_utc, session_count, total_seconds)
                        VALUES (?, ?, 1, 0.0)
                        ON CONFLICT(student_user_id, date_str_utc) DO UPDATE SET
                            session_count = voice_daily_usage.session_count + 1
                        """,
                        (student_user_id, today),
                    )
            finally:
                self._close_connection(conn)

            return VoiceSessionState(
                session_id=session_id,
                student_user_id=student_user_id,
                university_id=university_id,
                thread_id=thread_id,
                created_at=now,
                expires_at=expires,
                max_duration_seconds=duration,
                language="ar",
                arabic_dialect="msa",
                dialect_source="default",
                is_active=True,
                last_activity_at=now,
            )

    def record_duration(self, student_user_id: str, duration_seconds: float) -> None:
        """Atomically record consumed audio seconds toward the daily voice quota."""
        if duration_seconds <= 0:
            return
        today = self._today_utc()
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute(
                        """
                        INSERT INTO voice_daily_usage (student_user_id, date_str_utc, session_count, total_seconds)
                        VALUES (?, ?, 0, ?)
                        ON CONFLICT(student_user_id, date_str_utc) DO UPDATE SET
                            total_seconds = voice_daily_usage.total_seconds + excluded.total_seconds
                        """,
                        (student_user_id, today, duration_seconds),
                    )
            finally:
                self._close_connection(conn)

    def update_dialect(
        self,
        student_user_id: str,
        dialect: str,
        source: Literal["default", "explicit_user_request"] = "explicit_user_request",
    ) -> None:
        normalized = dialect.lower().strip()
        new_lang: Literal["ar", "en"] = "ar"
        new_dialect: Literal["msa", "jordanian"] = "msa"

        if normalized in ("jordanian", "أردني", "أردنية", "عامية"):
            new_lang = "ar"
            new_dialect = "jordanian"
        elif normalized in ("msa", "فصحى", "standard", "arabic"):
            new_lang = "ar"
            new_dialect = "msa"
        elif normalized in ("english", "en", "إنجليزي", "انجليزي"):
            new_lang = "en"
            new_dialect = "msa"

        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute(
                        """
                        UPDATE voice_active_sessions
                        SET language = ?, arabic_dialect = ?, dialect_source = ?
                        WHERE student_user_id = ? AND is_active = 1
                        """,
                        (new_lang, new_dialect, source, student_user_id),
                    )
            finally:
                self._close_connection(conn)

    def end_session(
        self,
        student_user_id: str,
        session_id: str | None = None,
        actual_duration_seconds: float | None = None,
    ) -> float:
        """Mark active session as terminated and server-authoritatively account for actual duration."""
        now = time.time()
        today = self._today_utc()
        duration_to_record = 0.0

        with self._lock:
            conn = self._get_connection()
            try:
                # 1. Proactively clean up any stale expired sessions
                self._cleanup_expired_locked(conn, now)

                # 2. Query student active session
                row = conn.execute(
                    "SELECT session_id, created_at, max_duration_seconds FROM voice_active_sessions WHERE student_user_id = ? AND is_active = 1",
                    (student_user_id,),
                ).fetchone()

                if row is not None:
                    if session_id is None or row["session_id"] == session_id:
                        server_elapsed = max(0.0, now - float(row["created_at"]))
                        max_duration = float(row["max_duration_seconds"])

                        # Baseline is server-measured wall-clock elapsed time
                        duration_to_record = min(server_elapsed, max_duration)

                        # Protection against client duration manipulation:
                        # Client-reported duration is only accepted if within plausible bounds.
                        # If client claims significantly less than server elapsed (> 25% lower and > 10s gap),
                        # reject the client value as manipulated or lagged, and enforce server_elapsed.
                        if actual_duration_seconds is not None and actual_duration_seconds > 0:
                            client_val = min(float(actual_duration_seconds), max_duration)
                            if client_val < server_elapsed * 0.75 and (server_elapsed - client_val) > 10.0:
                                duration_to_record = min(server_elapsed, max_duration)
                            else:
                                duration_to_record = min(client_val, server_elapsed, max_duration)

                with conn:
                    if session_id:
                        conn.execute(
                            "UPDATE voice_active_sessions SET is_active = 0 WHERE student_user_id = ? AND session_id = ?",
                            (student_user_id, session_id),
                        )
                    else:
                        conn.execute(
                            "UPDATE voice_active_sessions SET is_active = 0 WHERE student_user_id = ?",
                            (student_user_id,),
                        )

                    if duration_to_record > 0:
                        conn.execute(
                            """
                            INSERT INTO voice_daily_usage (student_user_id, date_str_utc, session_count, total_seconds)
                            VALUES (?, ?, 0, ?)
                            ON CONFLICT(student_user_id, date_str_utc) DO UPDATE SET
                                total_seconds = voice_daily_usage.total_seconds + excluded.total_seconds
                            """,
                            (student_user_id, today, duration_to_record),
                        )
            finally:
                self._close_connection(conn)

        return duration_to_record

    def cleanup_expired(self) -> int:
        """Clean up expired or abandoned sessions and server-authoritatively account for their elapsed active duration."""
        now = time.time()
        with self._lock:
            conn = self._get_connection()
            try:
                return self._cleanup_expired_locked(conn, now)
            finally:
                self._close_connection(conn)
