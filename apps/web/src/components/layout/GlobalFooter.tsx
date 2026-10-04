'use client';
import {usePathname} from 'next/navigation';
import {Logo} from '@/components/ui/Logo';
export function GlobalFooter(){const path=usePathname();if(path.startsWith('/student')||path==='/login')return null;return <footer className="global-footer"><Logo/><span>© {new Date().getFullYear()} مرشدي</span><small>التسجيل النهائي عبر الجامعة.</small></footer>;}
