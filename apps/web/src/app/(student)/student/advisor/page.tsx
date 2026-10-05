"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Image from "next/image";
import ReactMarkdown from 'react-markdown';
import {ChatHistory} from '@/components/ui/ChatHistory';
import {ChatComposer} from '@/components/ui/ChatComposer';
import {LogoMark} from '@/components/ui/Logo';
import {FriendlyState} from '@/components/ui/DesignSystem';
import {LoadingSkeletonCard} from '@/components/ui/LoadingSkeleton';
import {label,conversationTitle} from '@/lib/labels';
import {Compass,Copy,Check,PanelRight,ArrowDown} from 'lucide-react';
import { useAuth } from "@/auth/auth-provider";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import { AuthenticatedApiError } from "@/lib/api/authenticated-client";
import { StudentApiService } from "@/lib/api/student-api";
import { useCourseIdentities } from "@/lib/api/use-course-identities";
import { CourseIdentity } from "@/components/academic/CourseIdentity";
import type { AdvisorResponse, ConversationThread, ConversationMessage } from "@/lib/api/student-types";

interface ChatMessage {
  id: string;
  sender: "student" | "advisor";
  text: string;
  advisorData?: AdvisorResponse;
  timestamp: string;
}

type HistoryStatus = "initializing" | "loading" | "ready" | "error" | "auth-error";
type SendError = "failed" | "timeout" | null;

const CHAT_RESPONSE_TIMEOUT_MS = 55_000;

const INITIAL_MESSAGES: ChatMessage[] = [];

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
  const [historyStatus, setHistoryStatus] = useState<HistoryStatus>("initializing");
  const [olderAvailable, setOlderAvailable] = useState(false);
  const [loadedCount, setLoadedCount] = useState(0);
  const [inputPrompt, setInputPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [sendError, setSendError] = useState<SendError>(null);
  const [failedMessage, setFailedMessage] = useState("");
  const [historyOpen, setHistoryOpen] = useState(false);
  const [copied, setCopied] = useState<string|null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const historyRequestRef = useRef(0);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView?.({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const showHistory = (rows: ConversationMessage[]): ChatMessage[] => rows.map((row) => ({
    id: row.id, sender: row.role === "USER" ? "student" : "advisor",
    text: row.content,
    timestamp: new Date(row.created_at).toLocaleTimeString("ar-JO-u-nu-latn", { hour: "2-digit", minute: "2-digit", hour12: false }),
  }));

  const isAuthError = (error: unknown) =>
    error instanceof AuthenticatedApiError && error.code === "UNAUTHENTICATED";

  const loadHistory = useCallback(async () => {
    const requestId = ++historyRequestRef.current;
    setHistoryStatus("loading");
    const api = new StudentApiService(client);
    try {
      const items = await api.listConversations();
      if (requestId !== historyRequestRef.current) return;
      setThreads(items);
      setOlderThreadsAvailable(items.length === 100);
      const first = items.find((item) => item.status === "ACTIVE") ?? items[0];
      if (first) {
        const rows = await api.getConversationMessages(first.id);
        if (requestId !== historyRequestRef.current) return;
        setThreadId(first.id);
        setMessages(rows.length ? showHistory(rows) : INITIAL_MESSAGES);
        setLoadedCount(rows.length);
        setOlderAvailable(rows.length === 100);
      } else {
        setThreadId(null);
        setMessages(INITIAL_MESSAGES);
        setLoadedCount(0);
        setOlderAvailable(false);
      }
      setHistoryStatus("ready");
    } catch (error) {
      if (requestId !== historyRequestRef.current) return;
      setThreadId(null);
      setMessages(INITIAL_MESSAGES);
      setHistoryStatus(isAuthError(error) ? "auth-error" : "error");
    }
  }, [client]);

  useEffect(() => {
    if (!auth.isAuthenticated) return;
    const timer = window.setTimeout(() => void loadHistory(), 0);
    return () => {
      window.clearTimeout(timer);
      historyRequestRef.current += 1;
    };
  }, [auth.isAuthenticated, loadHistory]);

  const openThread = async (id: string) => {
    setHistoryStatus("loading");
    try {
      const rows = await new StudentApiService(client).getConversationMessages(id);
      setThreadId(id);
      setMessages(rows.length ? showHistory(rows) : INITIAL_MESSAGES);
      setLoadedCount(rows.length);
      setOlderAvailable(rows.length === 100);
      setHistoryStatus("ready");
    } catch (error) {
      setThreadId(null);
      setMessages(INITIAL_MESSAGES);
      setHistoryStatus(isAuthError(error) ? "auth-error" : "error");
    }
  };

  const loadOlder = async () => {
    if (!threadId) return;
    try {
      const rows = await new StudentApiService(client).getConversationMessages(threadId, loadedCount);
      setMessages((current) => [...showHistory(rows), ...current]);
      setLoadedCount((count) => count + rows.length);
      setOlderAvailable(rows.length === 100);
    } catch (error) {
      setHistoryStatus(isAuthError(error) ? "auth-error" : "error");
    }
  };

  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend ?? inputPrompt).trim();
    if (!query || loading || historyStatus === "initializing" ||
        historyStatus === "loading" || historyStatus === "auth-error" ||
        (threadId && threads.find((item) => item.id === threadId)?.status === "ARCHIVED")) return;

    setInputPrompt("");
    setLoading(true);
    setSendError(null);
    setFailedMessage("");
    let activeThreadId = threadId;
    const signal = AbortSignal.timeout(CHAT_RESPONSE_TIMEOUT_MS);

    try {
      const api = new StudentApiService(client);
      let studentMsg: ChatMessage;
      let advisorMsg: ChatMessage;
      if (historyStatus === "ready") {
        const id = activeThreadId ?? (await api.createConversation(query.slice(0, 100))).id;
        activeThreadId = id;
        if (!threadId) setThreadId(id);
        const reply = await api.continueConversation(id, query, signal);
        advisorMsg = {
          id: reply.assistant_message.id,
          sender: "advisor",
          text: reply.assistant_message.content,
          advisorData: reply.advisor,
          timestamp: new Date(reply.assistant_message.created_at).toLocaleTimeString("ar-JO-u-nu-latn", { hour: "2-digit", minute: "2-digit" }),
        };
        studentMsg = showHistory([reply.user_message])[0];
      } else {
        const reply = await api.askAdvisor({ message: query }, signal);
        const timestamp = new Date().toLocaleTimeString("ar-JO-u-nu-latn", { hour: "2-digit", minute: "2-digit" });
        studentMsg = { id: `local-user-${Date.now()}`, sender: "student", text: query, timestamp };
        advisorMsg = {
          id: `local-assistant-${Date.now()}`,
          sender: "advisor",
          text: reply.explanation ?? "تمت معالجة استفسارك وفق القواعد الحتمية.",
          advisorData: reply,
          timestamp,
        };
      }
      setMessages((prev) => [...(prev === INITIAL_MESSAGES ? [] : prev), studentMsg, advisorMsg]);
      setLoadedCount((count) => count + 2);
      if (historyStatus === "ready") {
        try {
          setThreads(await api.listConversations());
        } catch (error) {
          setHistoryStatus(isAuthError(error) ? "auth-error" : "error");
        }
      }
    } catch (error) {
      setFailedMessage(query);
      if (isAuthError(error)) setHistoryStatus("auth-error");
      else setSendError(signal.aborted ? "timeout" : "failed");
    } finally {
      setLoading(false);
    }
  };


  const archived=Boolean(threadId&&threads.find(t=>t.id===threadId)?.status==='ARCHIVED');
  return <div className="chat-workspace">
    <div className="chat-mobile-heading"><h1>المحادثة</h1><button className="icon-button" aria-label="سجل المحادثات" aria-expanded={historyOpen} onClick={()=>setHistoryOpen(!historyOpen)}><PanelRight size={20}/></button></div>
    <aside className={`chat-sidebar ${historyOpen?'is-open':''}`}>
      <ChatHistory threads={threads.map(t=>({...t,title:conversationTitle(t.title,t.id===threadId?messages.find(m=>m.sender==='student')?.text:undefined)}))} activeId={threadId} disabled={loading||historyStatus==='loading'||historyStatus==='auth-error'}
        onNew={()=>{setThreadId(null);setMessages(INITIAL_MESSAGES);setLoadedCount(0);setOlderAvailable(false);setHistoryOpen(false);}}
        onSelect={id=>{void openThread(id);setHistoryOpen(false);}}
        onArchive={id=>{void new StudentApiService(client).archiveConversation(id).then(async()=>setThreads(await new StudentApiService(client).listConversations())).catch((error)=>setHistoryStatus(isAuthError(error)?'auth-error':'error'));}}/>
      {olderThreadsAvailable&&<button className="button-secondary" onClick={()=>{void new StudentApiService(client).listConversations(threads.length).then(older=>{setThreads(c=>[...c,...older]);setOlderThreadsAvailable(older.length===100);}).catch((error)=>setHistoryStatus(isAuthError(error)?'auth-error':'error'));}}>محادثات أقدم</button>}
    </aside>
    <section className="chat-main" aria-label="المحادثة">
      <div className="chat-reading panel-scroll" role="log" aria-live="polite" aria-relevant="additions">
        {(historyStatus==='initializing'||historyStatus==='loading')&&!messages.length?<LoadingSkeletonCard/>:null}
        {historyStatus==='error'&&<div className="chat-history-warning" role="alert"><span>تعذّر تحميل المحادثات السابقة. يمكنك بدء محادثة جديدة.</span><button className="button-secondary" onClick={()=>void loadHistory()}>إعادة المحاولة</button></div>}
        {historyStatus==='auth-error'?<FriendlyState error title="انتهت صلاحية الجلسة. يرجى تسجيل الدخول مرة أخرى."/>:null}
        {sendError&&<div className="chat-send-error" role="alert"><span>{sendError==='timeout'?'استغرق الرد وقتًا أطول من المتوقع. حاول مرة أخرى.':'تعذّر إرسال الرسالة. حاول مرة أخرى.'}</span><button className="button-secondary" onClick={()=>void handleSendMessage(failedMessage)}>إعادة المحاولة</button></div>}
        {historyStatus!=='auth-error'&&!messages.length&&historyStatus!=='initializing'&&historyStatus!=='loading'&&<div className="chat-welcome"><div className="chat-mascot"><Image src="/brand/morshidi-guide-cutout.png" alt="" width={160} height={240}/></div><h1>كيف نرسم خطوتك القادمة؟</h1><div className="chat-suggestions">{SUGGESTED_QUESTIONS.map((q,i)=><button key={q} onClick={()=>setInputPrompt(q)}><span className="suggestion-number">0{i+1}</span><span>{q}</span><span aria-hidden="true">↖</span></button>)}</div></div>}
        {olderAvailable&&<button className="button-secondary" onClick={()=>void loadOlder()}>رسائل أقدم</button>}
        {messages.map(msg=><article key={msg.id} className={`chat-message ${msg.sender==='student'?'message-user':'message-advisor'}`}>
          {msg.sender==='advisor'&&<div className="message-brand"><LogoMark/><span>مرشدي</span></div>}
          <div className="message-prose"><ReactMarkdown>{msg.text}</ReactMarkdown></div>
          {msg.advisorData&&<div className="message-sources">{label(msg.advisorData.answer_authority)&&<span>{label(msg.advisorData.answer_authority)}</span>}
            {msg.advisorData.clarification?.candidate_course_codes?.map(code=><button className="button-secondary" key={code} onClick={()=>void handleSendMessage(`ما هي متطلبات المادة ${code}؟`)}><CourseIdentity courseCode={code} identities={identities}/></button>)}
          </div>}
          <div className="message-meta"><time>{msg.timestamp}</time><button aria-label="نسخ الرسالة" onClick={()=>{void navigator.clipboard.writeText(msg.text).then(()=>setCopied(msg.id)).catch(()=>setCopied(null));}}>{copied===msg.id?<Check size={14}/>:<Copy size={14}/>}</button></div>
        </article>)}
        {loading&&<div className="chat-pending" role="status"><Compass className="needle-loading" size={22}/><span>يجهّز مرشدي الرد…</span></div>}
        <div ref={messagesEndRef}/>
      </div>
      <div className="chat-composer-wrap">{messages.length>4&&<button className="latest-message" onClick={scrollToBottom}><ArrowDown size={13}/>آخر الرسائل</button>}{archived&&<p className="text-xs text-muted">محادثة مؤرشفة</p>}<ChatComposer value={inputPrompt} onChange={setInputPrompt} onSend={()=>void handleSendMessage()} loading={loading} disabled={historyStatus==='initializing'||historyStatus==='loading'||historyStatus==='auth-error'||archived}/></div>
    </section>
  </div>;
}
