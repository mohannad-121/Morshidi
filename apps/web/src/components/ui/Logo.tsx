import Image from 'next/image';
import Link from 'next/link';
export function LogoMark({className=''}:{className?:string}) {
  return <Image className={`brand-mark object-contain ${className}`} src="/brand/morshidi-logo-transparent.png" alt="" width={48} height={64} aria-hidden="true"/>;
}
export function Logo({compact=false}:{compact?:boolean}) {return <Link className="brand" href="/" aria-label="مرشدي — الرئيسية"><LogoMark/>{!compact&&<span>مرشدي<i/></span>}</Link>;}
