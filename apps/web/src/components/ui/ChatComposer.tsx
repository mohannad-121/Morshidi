'use client';
import {useEffect,useRef} from 'react';
import {ArrowUp,Compass} from 'lucide-react';
export function ChatComposer({value,onChange,onSend,disabled,loading}:{value:string;onChange:(s:string)=>void;onSend:()=>void;disabled:boolean;loading:boolean}){
 const ref=useRef<HTMLTextAreaElement>(null);
 useEffect(()=>{const el=ref.current;if(el){el.style.height='auto';el.style.height=Math.min(el.scrollHeight,160)+'px';}},[value]);
 return <form className="chat-composer" onSubmit={e=>{e.preventDefault();onSend();}}><textarea ref={ref} rows={1} aria-label="الاستفسار الأكاديمي" placeholder="بماذا تفكّر؟" value={value} onChange={e=>onChange(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();if(!disabled&&!loading&&value.trim())onSend();}}}/><button type="submit" disabled={disabled||loading||!value.trim()} aria-label={loading?'جارٍ تجهيز الرد':'إرسال'}>{loading?<Compass className="needle-loading" size={20}/>:<ArrowUp size={20}/>}</button></form>;
}
