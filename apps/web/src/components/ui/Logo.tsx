import Link from 'next/link';
export function LogoMark({className=''}:{className?:string}) {
  return <svg className={className} viewBox="0 0 48 48" fill="none" aria-hidden="true"><circle cx="24" cy="24" r="20" stroke="currentColor" strokeWidth="1"/><circle cx="24" cy="24" r="15" stroke="currentColor" strokeWidth=".5"/>{Array.from({length:8},(_,i)=><path key={i} d="M24 4v4" stroke="currentColor" transform={`rotate(${i*45} 24 24)`}/>)}<path d="m32 12-5 16-5-5-7 11 3-16 5 5Z" fill="currentColor"/><circle cx="24" cy="24" r="2" fill="#0b1210"/></svg>;
}
export function Logo({compact=false}:{compact?:boolean}) {return <Link className="brand" href="/" aria-label="مرشدي — الرئيسية"><LogoMark/>{!compact&&<span>مرشدي<i/></span>}</Link>;}
