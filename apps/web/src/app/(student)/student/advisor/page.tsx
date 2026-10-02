"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { useAuth } from "@/auth/auth-provider";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import { StudentApiService } from "@/lib/api/student-api";
import { useCourseIdentities } from "@/lib/api/use-course-identities";
import { CourseIdentity } from "@/components/academic/CourseIdentity";
import type { AdvisorResponse, ConversationThread, ConversationMessage } from "@/lib/api/student-types";
import { Badge } from "@/components/ui/Badge";
import {
  AdvisorIcon,
  AlertTriangleIcon,
  CheckCircleIcon,
  InfoIcon,
  MorshidiLogo,
  SendIcon,
  SparklesIcon,
} from "@/components/ui/Icons";

interface ChatMessage {
  id: string;
  sender: "student" | "advisor";
  text: string;
  advisorData?: AdvisorResponse;
  timestamp: string;
}

const INITIAL_MESSAGES: ChatMessage[] = [
  {
    id: "welcome",
    sender: "advisor",
    text: "أهلاً بك في مرشدي! أنا مرشدك الأكاديمي الذكي المعتمد على القواعد الحتمية لجامعتك. يمكنني شرح أهليتك للمواد، توضيح شجرة المتطلبات السابقة، واقتراح خطة دراسية متوازنة. تفضل بطرح أي استفسار أكاديمي.",
    timestamp: "الآن",
  },
];

const SUGGESTED_QUESTIONS = [
  "هل يمكنني تسجيل مادة الذكاء الاصطناعي؟",
  "كم ساعة متبقية لتخرجي في الخطة؟",
  "ما هي أفضل باقة مواد مقترحة للفصل القادم؟",
  "ما هي المتطلبات السابقة لمادة الخوارزميات؟",
];

export default function AdvisorPage() {
  const auth = useAuth();
  const client = useAuthenticatedApi();

  const [messages, setMessages] = useState<ChatMessage[]>(INITIAL_MESSAGES);
  const identities = useCourseIdentities(messages.some(message =>
    Boolean(message.advisorData?.clarification?.candidate_course_codes?.length)));
  const [threads, setThreads] = useState<ConversationThread[]>([]);
  const [olderThreadsAvailable, setOlderThreadsAvailable] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [historyReady, setHistoryReady] = useState(false);
  const [historyError, setHistoryError] = useState(false);
  const [olderAvailable, setOlderAvailable] = useState(false);
  const [loadedCount, setLoadedCount] = useState(0);
  const [inputPrompt, setInputPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView?.({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const showHistory = (rows: ConversationMessage[]): ChatMessage[] => rows.map((row) => ({
    id: row.id, sender: row.role === "USER" ? "student" : "advisor",
    text: row.content,
    timestamp: new Date(row.created_at).toLocaleTimeString("ar-SA", { hour: "2-digit", minute: "2-digit" }),
  }));

  useEffect(() => {
    if (!auth.isAuthenticated) return;
    let active = true;
    const api = new StudentApiService(client);
    void api.listConversations().then(async (items) => {
      if (!active) return;
      setThreads(items);
      setOlderThreadsAvailable(items.length === 100);
      const first = items.find((item) => item.status === "ACTIVE") ?? items[0];
      if (first) {
        const rows = await api.getConversationMessages(first.id);
        if (!active) return;
        setThreadId(first.id);
        setMessages(rows.length ? showHistory(rows) : INITIAL_MESSAGES);
        setLoadedCount(rows.length);
        setOlderAvailable(rows.length === 100);
      }
      setHistoryReady(true);
    }).catch(() => { if (active) { setHistoryError(true); setHistoryReady(true); } });
    return () => { active = false; };
  }, [auth.isAuthenticated, client]);

  const openThread = async (id: string) => {
    setHistoryError(false);
    setHistoryReady(false);
    try {
      const rows = await new StudentApiService(client).getConversationMessages(id);
      setThreadId(id);
      setMessages(rows.length ? showHistory(rows) : INITIAL_MESSAGES);
      setLoadedCount(rows.length);
      setOlderAvailable(rows.length === 100);
    } catch { setHistoryError(true); }
    finally { setHistoryReady(true); }
  };

  const loadOlder = async () => {
    if (!threadId) return;
    try {
      const rows = await new StudentApiService(client).getConversationMessages(threadId, loadedCount);
      setMessages((current) => [...showHistory(rows), ...current]);
      setLoadedCount((count) => count + rows.length);
      setOlderAvailable(rows.length === 100);
    } catch { setHistoryError(true); }
  };

  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend ?? inputPrompt).trim();
    if (!query || loading || !historyReady || historyError ||
        (threadId && threads.find((item) => item.id === threadId)?.status === "ARCHIVED")) return;

    setInputPrompt("");
    setLoading(true);
    let activeThreadId = threadId;

    try {
      const api = new StudentApiService(client);
      const id = activeThreadId ?? (await api.createConversation(query.slice(0, 100))).id;
      activeThreadId = id;
      if (!threadId) setThreadId(id);
      const reply = await api.continueConversation(id, query, AbortSignal.timeout(55_000));
      const advisorMsg: ChatMessage = {
        id: reply.assistant_message.id,
        sender: "advisor",
        text: reply.assistant_message.content,
        advisorData: reply.advisor,
        timestamp: new Date(reply.assistant_message.created_at).toLocaleTimeString("ar-SA", { hour: "2-digit", minute: "2-digit" }),
      };
      const studentMsg = showHistory([reply.user_message])[0];
      setMessages((prev) => [...(prev === INITIAL_MESSAGES ? [] : prev), studentMsg, advisorMsg]);
      setLoadedCount((count) => count + 2);
      setThreads(await api.listConversations());
    } catch {
      if (activeThreadId) await openThread(activeThreadId);
      setHistoryError(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-140px)] flex-col space-y-4">
      {/* Header */}
      <div className="flex shrink-0 flex-col gap-3 border-b border-[#EDE2C5] pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="relative h-12 w-12 shrink-0 rounded-2xl bg-[#FFF4C7] p-1 border border-[#E2AD27]/30 shadow-xs flex items-center justify-center">
            <Image
              src="/brand/morshidi-guide.png"
              alt="مرشدي"
              width={48}
              height={48}
              className="h-full w-full object-contain"
            />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-[#A66F00]/10 px-2.5 py-0.5 text-xs font-bold text-[#A66F00]">
                المساعد الأكاديمي الحتمي
              </span>
              <span className="text-xs text-[#726B5E]">شرح مدعوم بالأدلة القطعية</span>
            </div>
            <h1 className="mt-1 text-2xl font-bold tracking-tight text-[#28241C]">
              المرشد الأكاديمي الذكي
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="gold">
            AI EXPLAINS — DETERMINISTIC RULES DECIDE
          </Badge>
        </div>
      </div>

      {/* Suggested Questions */}
      <nav aria-label="المحادثات السابقة" className="flex shrink-0 flex-wrap items-center gap-2 text-xs">
        <button type="button" onClick={() => { setThreadId(null); setMessages(INITIAL_MESSAGES); setLoadedCount(0); setOlderAvailable(false); }}
          className="rounded-lg border px-3 py-1">محادثة جديدة / New chat</button>
        {threads.map((thread) => <button key={thread.id} type="button" onClick={() => void openThread(thread.id)}
          aria-current={threadId === thread.id ? "page" : undefined} className="rounded-lg border px-3 py-1">
          {thread.title} {thread.status === "ARCHIVED" ? "(مؤرشفة)" : ""}
        </button>)}
        {olderThreadsAvailable ? <button type="button" onClick={() => {
          void new StudentApiService(client).listConversations(threads.length).then((older) => {
            setThreads((current) => [...current, ...older]); setOlderThreadsAvailable(older.length === 100);
          }).catch(() => setHistoryError(true));
        }} className="rounded-lg border px-3 py-1">محادثات أقدم / Older chats</button> : null}
        {threadId && threads.find((item) => item.id === threadId)?.status === "ACTIVE" ?
          <button type="button" onClick={() => { void new StudentApiService(client).archiveConversation(threadId).then(async () => {
            setThreads(await new StudentApiService(client).listConversations());
          }).catch(() => setHistoryError(true)); }} className="rounded-lg border px-3 py-1">أرشفة / Archive</button> : null}
      </nav>
      {historyError ? <p role="alert" className="text-sm text-red-700">تعذّر حفظ أو تحميل المحادثة. يرجى إعادة المحاولة؛ لا تُرسل رسالة جديدة حتى يعود التخزين. Conversation storage unavailable.</p> : null}
      <div className="flex shrink-0 flex-wrap items-center gap-2 text-xs">
        <span className="font-bold text-[#726B5E]">أسئلة شائعة سريعة:</span>
        {SUGGESTED_QUESTIONS.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => void handleSendMessage(q)}
            disabled={loading || !historyReady || historyError ||
              Boolean(threadId && threads.find((item) => item.id === threadId)?.status === "ARCHIVED")}
            className="rounded-xl border border-[#EDE2C5] bg-[#FFF9E8] px-3 py-1 font-semibold text-[#805400] hover:bg-[#FFF4C7] hover:border-[#E2AD27] transition-colors disabled:opacity-50"
          >
            {q}
          </button>
        ))}
      </div>

      {/* Chat Messages Area */}
      <div role="log" aria-live="polite" aria-relevant="additions" className="flex-1 overflow-y-auto rounded-3xl border border-[#EDE2C5] bg-white p-6 shadow-xs space-y-6">
        {olderAvailable ? <button type="button" onClick={() => void loadOlder()} className="rounded-lg border px-3 py-1 text-xs">رسائل أقدم / Older messages</button> : null}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex items-start gap-3.5 ${
              msg.sender === "student" ? "flex-row-reverse" : "flex-row"
            }`}
          >
            {/* Avatar */}
            {msg.sender === "advisor" ? (
              <div className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-[#FFF4C7] p-1 border border-[#E2AD27]/30 shadow-xs">
                <Image
                  src="/brand/morshidi-guide.png"
                  alt="مرشدي"
                  width={36}
                  height={36}
                  className="h-full w-full object-contain"
                />
              </div>
            ) : (
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-[#E2AD27] font-bold text-[#28241C] shadow-xs">
                ط
              </div>
            )}

            {/* Bubble */}
            <div
              className={`max-w-[85%] sm:max-w-[75%] rounded-3xl p-5 text-xs ${
                msg.sender === "student"
                  ? "bg-[#E2AD27] text-[#28241C] rounded-tr-xs font-semibold shadow-xs"
                  : "bg-[#FFFCF4] border border-[#EDE2C5] text-[#28241C] rounded-tl-xs shadow-xs"
              }`}
            >
              <div className="flex items-center justify-between gap-4 mb-2 text-[10px]">
                <span className={`font-bold ${msg.sender === "student" ? "text-[#28241C]/80" : "text-[#A66F00]"}`}>
                  {msg.sender === "student" ? "أنت" : "مرشدي (المرشد الأكاديمي)"}
                </span>
                <span className={msg.sender === "student" ? "text-[#28241C]/60" : "text-[#726B5E]"}>
                  {msg.timestamp}
                </span>
              </div>

              {/* Message text */}
              <p className="leading-relaxed whitespace-pre-line text-sm font-medium">
                {msg.text}
              </p>

              {/* Advisor Evidence & Authority Badge */}
              {msg.advisorData ? (
                <div className="mt-4 space-y-2 border-t border-[#EDE2C5]/70 pt-3 text-[11px] text-[#726B5E]">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-md bg-white px-2 py-0.5 font-bold text-[#A66F00] border border-[#EDE2C5]">
                      المصدر: {msg.advisorData.answer_authority}
                    </span>
                    <span className="rounded-md bg-white px-2 py-0.5 text-[#726B5E] border border-[#EDE2C5]">
                      النية: {msg.advisorData.intent}
                    </span>
                    <span className="rounded-md bg-white px-2 py-0.5 font-mono text-[#726B5E] border border-[#EDE2C5]">
                      السياسة: {msg.advisorData.policy_version}
                    </span>
                  </div>

                  {/* Clarification candidate course codes if any */}
                  {msg.advisorData.clarification?.candidate_course_codes &&
                  msg.advisorData.clarification.candidate_course_codes.length > 0 ? (
                    <div className="pt-2">
                      <span className="block font-bold text-[#28241C] mb-1.5">
                        هل تقصد إحدى المواد التالية؟ اضغط للتحديد:
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {msg.advisorData.clarification.candidate_course_codes.map((code) => (
                          <button
                            key={code}
                            type="button"
                            onClick={() => void handleSendMessage(`ما هي متطلبات المادة ${code}؟`)}
                            className="rounded-xl bg-white px-3 py-1 font-mono font-bold text-[#A66F00] border border-[#EDE2C5] hover:bg-[#FFF4C7] transition-colors"
                            dir="ltr"
                          >
                            <CourseIdentity courseCode={code} identities={identities} />
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : null}

                  {/* Trace authoritative sources */}
                  {msg.advisorData.trace?.authoritative_sources &&
                  msg.advisorData.trace.authoritative_sources.length > 0 ? (
                    <div className="text-[10px] text-[#726B5E] pt-1">
                      <strong>المستندات المعتمدة: </strong>
                      {msg.advisorData.trace.authoritative_sources.join(", ")}
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          </div>
        ))}

        {/* Loading Indicator */}
        {loading ? (
          <div className="flex items-start gap-3.5">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-[#FFF4C7] text-[#A66F00]">
              <MorshidiLogo className="h-6 w-6 animate-pulse" />
            </div>
            <div className="rounded-3xl rounded-tl-xs border border-[#EDE2C5] bg-[#FFFCF4] p-4 text-xs shadow-xs">
              <div className="flex items-center gap-2 text-[#726B5E]">
                <SparklesIcon className="h-4 w-4 animate-spin text-[#A66F00]" />
                <span>مرشدي يجهّز الرد...</span>
              </div>
            </div>
          </div>
        ) : null}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Box */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void handleSendMessage();
        }}
        className="shrink-0"
      >
        <div className="flex gap-2">
          <input
            type="text"
            aria-label="الاستفسار الأكاديمي"
            value={inputPrompt}
            onChange={(e) => setInputPrompt(e.target.value)}
            placeholder="اكتب استفسارك الأكاديمي هنا (مثال: هل يمكنني تسجيل مادة معالجة اللغات الطبيعية؟)..."
            className="flex-1 rounded-2xl border border-[#EDE2C5] bg-white px-5 py-3 text-xs text-[#28241C] placeholder-[#726B5E]/60 focus:border-[#E2AD27] focus:outline-hidden focus:ring-2 focus:ring-[#E2AD27]/20 shadow-xs"
          />
          <button
            type="submit"
            disabled={loading || !historyReady || historyError || !inputPrompt.trim() ||
              Boolean(threadId && threads.find((item) => item.id === threadId)?.status === "ARCHIVED")}
            className="inline-flex items-center gap-2 rounded-2xl bg-[#E2AD27] px-6 py-3 text-xs font-bold text-[#28241C] hover:bg-[#A66F00] hover:text-white transition-all shadow-xs disabled:opacity-50"
          >
            <SendIcon className="h-4 w-4" />
            <span>إرسال</span>
          </button>
        </div>
      </form>
    </div>
  );
}
