'use client';
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {useState,type ReactNode} from 'react';
import {motion} from 'framer-motion';
import {LayoutDashboard,UserRound,ChartNoAxesCombined,BookOpen,CalendarDays,MessagesSquare,Compass,DoorOpen,Route,ClipboardList,LibraryBig,Columns3,ScrollText,Menu,X,Pin,ChevronDown,Bell} from 'lucide-react';
import {useAuth} from '@/auth/auth-provider';
import {SignOutButton} from '@/auth/sign-out-button';
import {Logo,LogoMark} from '@/components/ui/Logo';
const groups=[{title:'حسابي',items:[['','نظرة عامة',LayoutDashboard],['profile','الملف',UserRound],['progress','التقدم',ChartNoAxesCombined],['courses','المواد والدرجات',BookOpen]]},{title:'التخطيط',items:[['planner','خطة الفصل',CalendarDays],['advisor','مرشدي AI',MessagesSquare],['recommendations','التوصيات',Compass],['eligibility','أهلية التسجيل',DoorOpen],['degree-path','مسار التخرج',Route],['mock-registration','محاكاة التسجيل',ClipboardList]]},{title:'مراجع',items:[['roadmap','الخطة الدراسية',LibraryBig],['offerings','المواد المطروحة',Columns3],['policies','اللوائح',ScrollText]]}] as const;
export function AppShell({children}:{children:ReactNode}) {
 const pathname=usePathname();const auth=useAuth();const [pinned,setPinned]=useState(false);const [drawer,setDrawer]=useState(false);const [bell,setBell]=useState(false);
 const active=groups.flatMap(g=>[...g.items]).find(([path])=>pathname===`/student${path?'/'+path:''}`);
 const initial=(auth.user?.user_metadata?.full_name||auth.user?.email||'م').slice(0,1);
 return <div className={`app-shell ${pinned?'shell-pinned':''}`} dir="rtl">
  <header className="topbar"><Logo/><span className="breadcrumb">حسابي <span>/</span> {active?.[1]??'مرشدي'}</span><div className="topbar-actions"><div className="notification-wrap"><button className="icon-button" aria-label="الإشعارات" aria-expanded={bell} onClick={()=>setBell(!bell)}><Bell size={19}/></button>{bell&&<div className="account-popover"><p>لا إشعارات بعد</p></div>}</div><details className="account-menu"><summary><span className="account-initial">{initial}</span><span className="account-email" dir="ltr">{auth.user?.email}</span><ChevronDown size={14}/></summary><div className="account-popover"><Link href="/student/profile">الملف الشخصي</Link><Link href="/student/privacy">الخصوصية</Link><Link href="/student/decision-history">سجل القرارات</Link><SignOutButton/></div></details></div></header>
  {drawer&&<button className="drawer-scrim" aria-label="إغلاق القائمة" onClick={()=>setDrawer(false)}/>}
  <aside className={`sidebar ${drawer?'sidebar-open':''}`} aria-label="قائمة الطالب"><div className="sidebar-cap"><LogoMark/><button className="icon-button" aria-label={drawer?'إغلاق القائمة':'تثبيت القائمة'} aria-pressed={pinned} onClick={()=>drawer?setDrawer(false):setPinned(!pinned)}>{drawer?<X size={16}/>:<Pin size={16}/>}</button></div>
   <nav>{groups.map(group=><div className="nav-group" key={group.title}><h2>{group.title}</h2>{group.items.map(([path,title,Icon])=>{const href=`/student${path?'/'+path:''}`;return <Link key={href} href={href} title={title} onClick={()=>setDrawer(false)} aria-current={pathname===href?'page':undefined} className="sidebar-link">{pathname===href&&<motion.i className="nav-needle" layoutId="nav-needle" transition={{duration:.35}}/>}<Icon size={20} strokeWidth={1.5}/><span>{title}</span></Link>;})}</div>)}</nav><Link className="sidebar-journey" href="/student/degree-path"><Compass size={22}/><span>رحلة التخرج</span></Link>
  </aside>
  <div className="app-content"><div key={pathname} className="route-reveal">{children}</div><footer className="app-footer">مرشدي © {new Date().getFullYear()} <span>التسجيل النهائي عبر الجامعة.</span></footer></div>
  {pathname!=='/student/advisor'&&<Link className="ask-morshidi" href="/student/advisor" aria-label="اسأل مرشدي"><LogoMark/><span>اسأل مرشدي</span></Link>}
  <nav className="mobile-tabs" aria-label="التنقل السريع">{[['','الرئيسية',LayoutDashboard],['planner','خطتي',CalendarDays],['advisor','مرشدي',Compass],['progress','تقدمي',ChartNoAxesCombined]].map(([path,title,Icon])=>{const IconComponent=Icon as typeof Compass;return <Link key={String(path)} href={`/student${path?'/'+path:''}`} aria-current={pathname===`/student${path?'/'+path:''}`?'page':undefined}><IconComponent size={20}/><span>{String(title)}</span></Link>;})}<button aria-expanded={drawer} onClick={()=>setDrawer(!drawer)}><Menu size={20}/><span>القائمة</span></button></nav>
 </div>;
}
