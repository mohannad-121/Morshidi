'use client';
import {useState} from 'react';
import {Plus,Search,Archive,MessageSquare} from 'lucide-react';
import type {ConversationThread} from '@/lib/api/student-types';
import {conversationTitle} from '@/lib/labels';
export function ChatHistory({threads,activeId,onSelect,onNew,onArchive,disabled=false}:{threads:ConversationThread[];activeId:string|null;onSelect:(id:string)=>void;onNew:()=>void;onArchive:(id:string)=>void;disabled?:boolean}) {
 const [search,setSearch]=useState('');
 const grouped:Record<string,ConversationThread[]>={'اليوم':[],'أمس':[],'آخر 7 أيام':[],'أقدم':[]};
 const midnight=new Date();midnight.setHours(0,0,0,0);
 for(const thread of threads){if(!conversationTitle(thread.title).includes(search))continue;const age=Math.floor((midnight.getTime()-new Date(thread.updated_at).getTime())/86400000);grouped[age<0?'اليوم':age===0?'أمس':age<7?'آخر 7 أيام':'أقدم'].push(thread);}
 return <nav className="chat-history" aria-label="المحادثات السابقة"><button className="button-secondary w-full" disabled={disabled} onClick={onNew}><Plus size={17}/>محادثة جديدة</button><label className="history-search"><Search size={16}/><input aria-label="بحث المحادثات" placeholder="بحث" value={search} onChange={e=>setSearch(e.target.value)}/></label><div className="panel-scroll history-items">{Object.entries(grouped).map(([group,items])=>items.length>0&&<section key={group}><h2>{group}</h2>{items.map(thread=><div className="history-row" key={thread.id} data-active={activeId===thread.id}><button disabled={disabled} aria-current={activeId===thread.id?'page':undefined} onClick={()=>onSelect(thread.id)}><MessageSquare size={15}/><span>{conversationTitle(thread.title)}</span>{thread.status==='ARCHIVED'&&<Archive size={12}/>}</button>{thread.status==='ACTIVE'&&<button disabled={disabled} className="history-archive" onClick={()=>onArchive(thread.id)} aria-label="أرشفة المحادثة"><Archive size={14}/></button>}</div>)}</section>)}</div></nav>;
}
