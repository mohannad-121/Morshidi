'use client';
import {useEffect,useRef} from 'react';
import {ArrowUp,Compass,ShieldCheck} from 'lucide-react';
export function ChatComposer({value,onChange,onSend,disabled,loading}:{value:string;onChange:(s:string)=>void;onSend:()=>void;disabled:boolean;loading:boolean}){
 const ref=useRef<HTMLTextAreaElement>(null);
 useEffect(()=>{const el=ref.current;if(el){el.style.height='auto';el.style.height=Math.min(el.scrollHeight,160)+'px';}},[value]);
 return <div className="chat-composer-cluster"><form className="chat-composer" onSubmit={e=>{e.preventDefault();onSend();}}><textarea ref={ref} id="advisor-prompt" rows={1} aria-label="الاستفسار الأكاديمي" aria-describedby="advisor-composer-assurance" placeholder="اسأل عن خطتك، موادك، أو أهليتك…" value={value} onChange={e=>onChange(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();if(!disabled&&!loading&&value.trim())onSend();}}}/><button type="submit" disabled={disabled||loading||!value.trim()} aria-label={loading?'جارٍ تجهيز الرد':'إرسال'}>{loading?<Compass className="needle-loading" size={20} aria-hidden="true"/>:<ArrowUp size={20} aria-hidden="true"/>}</button></form><p className="composer-assurance" id="advisor-composer-assurance"><ShieldCheck size={13} aria-hidden="true"/><span>مرشدي يشرح النتائج؛ القواعد الأكاديمية الحتمية هي التي تقرر.</span></p></div>;
}
