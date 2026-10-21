"""Master deterministic curriculum regeneration script.

Executes:
1. build.py (generates canonical_curriculum.json, plans/*.json, CSVs)
2. generate_morshidi_sql.py (generates morshidi_multi_plan_seed.sql, morshidi_plan_ids.json)
3. generate_fake_university.py (generates fake_university_multi_plan_migration.sql, fake_university_curriculum_registry.json)
4. Computes data/curricula/MANIFEST.json with SHA256 checksums.
"""

import os
import sys
import subprocess
import json
import hashlib

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(DIR))
DATA_DIR = os.path.join(REPO_ROOT, "data", "curricula")


def run_step(script_name: str) -> None:
    path = os.path.join(DIR, script_name)
    print(f"=== Running {script_name} ===")
    res = subprocess.run([sys.executable, path], capture_output=True, text=True, cwd=DIR, encoding='utf-8')
    if res.stdout:
        print(res.stdout.strip())
    if res.returncode != 0:
        if res.stderr:
            print(res.stderr.strip(), file=sys.stderr)
        raise RuntimeError(f"Step {script_name} failed with exit code {res.returncode}")


def update_manifest() -> None:
    print("=== Updating data/curricula/MANIFEST.json ===")
    manifest = {}
    for root, dirs, files in os.walk(DATA_DIR):
        for f in sorted(files):
            if f == "MANIFEST.json":
                continue
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, DATA_DIR).replace("\\", "/")
            with open(full_path, "rb") as bf:
                h = hashlib.sha256(bf.read()).hexdigest()
            manifest[rel_path] = {
                "bytes": os.path.getsize(full_path),
                "sha256": h
            }
    manifest_path = os.path.join(DATA_DIR, "MANIFEST.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Updated MANIFEST.json ({len(manifest)} files tracked)")


def main():
    run_step("build.py")
    run_step("generate_morshidi_sql.py")
    run_step("generate_fake_university.py")
    update_manifest()
    print("=== All curriculum generation steps completed successfully! ===")


if __name__ == "__main__":
    main()
