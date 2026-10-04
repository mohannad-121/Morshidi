"use client";

import { useEffect, useRef, useState } from "react";
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
  const [historyReady, setHistoryReady] = useState(false);
  const [historyError, setHistoryError] = useState(false);
  const [olderAvailable, setOlderAvailable] = useState(false);
  const [loadedCount, setLoadedCount] = useState(0);
  const [inputPrompt, setInputPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [copied, setCopied] = useState<string|null>(null);
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
    timestamp: new Date(row.created_at).toLocaleTimeString("ar-JO-u-nu-latn", { hour: "2-digit", minute: "2-digit", hour12: false }),
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
        timestamp: new Date(reply.assistant_message.created_at).toLocaleTimeString("ar-JO-u-nu-latn", { hour: "2-digit", minute: "2-digit" }),
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


  const archived=Boolean(threadId&&threads.find(t=>t.id===threadId)?.status==='ARCHIVED');
  return <div className="chat-workspace">
    <div className="chat-mobile-heading"><h1>المحادثة</h1><button className="icon-button" aria-label="سجل المحادثات" aria-expanded={historyOpen} onClick={()=>setHistoryOpen(!historyOpen)}><PanelRight size={20}/></button></div>
    <aside className={`chat-sidebar ${historyOpen?'is-open':''}`}>
      <ChatHistory threads={threads.map(t=>({...t,title:conversationTitle(t.title,t.id===threadId?messages.find(m=>m.sender==='student')?.text:undefined)}))} activeId={threadId} disabled={loading||!historyReady}
        onNew={()=>{setThreadId(null);setMessages(INITIAL_MESSAGES);setLoadedCount(0);setOlderAvailable(false);setHistoryOpen(false);}}
        onSelect={id=>{void openThread(id);setHistoryOpen(false);}}
        onArchive={id=>{void new StudentApiService(client).archiveConversation(id).then(async()=>setThreads(await new StudentApiService(client).listConversations())).catch(()=>setHistoryError(true));}}/>
      {olderThreadsAvailable&&<button className="button-secondary" onClick={()=>{void new StudentApiService(client).listConversations(threads.length).then(older=>{setThreads(c=>[...c,...older]);setOlderThreadsAvailable(older.length===100);}).catch(()=>setHistoryError(true));}}>محادثات أقدم</button>}
    </aside>
    <section className="chat-main" aria-label="المحادثة">
      <div className="chat-reading panel-scroll" role="log" aria-live="polite" aria-relevant="additions">
        {!historyReady?<LoadingSkeletonCard/>:historyError?<FriendlyState error onRetry={()=>threadId?void openThread(threadId):window.location.reload()}/>:null}
        {historyReady&&!historyError&&!messages.length&&<div className="chat-welcome"><div className="chat-mascot"><Image src="/brand/morshidi-guide-cutout.png" alt="" width={160} height={240}/></div><h1>كيف نرسم خطوتك القادمة؟</h1><div className="chat-suggestions">{SUGGESTED_QUESTIONS.map((q,i)=><button key={q} onClick={()=>setInputPrompt(q)}><span className="suggestion-number">0{i+1}</span><span>{q}</span><span aria-hidden="true">↖</span></button>)}</div></div>}
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
      <div className="chat-composer-wrap">{messages.length>4&&<button className="latest-message" onClick={scrollToBottom}><ArrowDown size={13}/>آخر الرسائل</button>}{archived&&<p className="text-xs text-muted">محادثة مؤرشفة</p>}<ChatComposer value={inputPrompt} onChange={setInputPrompt} onSend={()=>void handleSendMessage()} loading={loading} disabled={!historyReady||historyError||archived}/></div>
    </section>
  </div>;
}

