'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState, type ReactNode } from 'react';
import { motion } from 'framer-motion';
import { LayoutDashboard, UserRound, ChartNoAxesCombined, BookOpen, CalendarDays, MessagesSquare, Compass, DoorOpen, Route, ClipboardList, LibraryBig, Columns3, ScrollText, Menu, X, ChevronDown, Bell, Command } from 'lucide-react';
import { useAuth } from '@/auth/auth-provider';
import { SignOutButton } from '@/auth/sign-out-button';
import { Logo, LogoMark } from '@/components/ui/Logo';
import { getStudentDisplayName, getStudentInitial } from '@/lib/student-identity';

const groups = [
  { title: 'مساحتي', items: [['', 'نظرة عامة', LayoutDashboard], ['profile', 'الملف الأكاديمي', UserRound], ['progress', 'التقدم الدراسي', ChartNoAxesCombined], ['courses', 'المواد والدرجات', BookOpen]] },
  { title: 'قراراتي', items: [['planner', 'خطة الفصل', CalendarDays], ['advisor', 'مرشدي AI', MessagesSquare], ['recommendations', 'التوصيات', Compass], ['eligibility', 'أهلية التسجيل', DoorOpen], ['degree-path', 'مسار التخرج', Route], ['mock-registration', 'محاكاة التسجيل', ClipboardList]] },
  { title: 'مصادري', items: [['roadmap', 'الخطة الدراسية', LibraryBig], ['offerings', 'المواد المطروحة', Columns3], ['policies', 'اللوائح', ScrollText]] },
] as const;

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const auth = useAuth();
  const [drawer, setDrawer] = useState(false);
  const [bell, setBell] = useState(false);
  const active = groups.flatMap((group) => [...group.items]).find(([path]) => pathname === `/student${path ? '/' + path : ''}`);
  const displayName = getStudentDisplayName(auth.user);
  const initial = getStudentInitial(auth.user);
  const studentId = auth.user?.user_metadata?.university_student_id;

  return <div className="app-shell" dir="rtl">
    <header className="topbar">
      <button className="mobile-menu-button icon-button" aria-label="فتح القائمة" onClick={() => setDrawer(true)}><Menu size={20}/></button>
      <div className="topbar-context"><span>مساحة الطالب</span><strong>{active?.[1] ?? 'مرشدي'}</strong></div>
      <div className="topbar-actions">
        <Link className="quick-command" href="/student/advisor"><Command size={16}/><span>اسأل مرشدي</span><kbd>⌘ K</kbd></Link>
        <div className="notification-wrap"><button className="icon-button" aria-label="الإشعارات" aria-expanded={bell} onClick={() => setBell(!bell)}><Bell size={19}/></button>{bell && <div className="account-popover"><p>لا إشعارات بعد</p></div>}</div>
        <details className="account-menu"><summary><span className="account-initial">{initial}</span><span className="account-name">{displayName}</span><ChevronDown size={14}/></summary><div className="account-popover"><div className="account-identity"><strong>{displayName}</strong>{studentId ? <span dir="ltr">{String(studentId)}</span> : null}</div><Link href="/student/profile">الملف الشخصي</Link><Link href="/student/privacy">الخصوصية</Link><Link href="/student/decision-history">سجل القرارات</Link><SignOutButton/></div></details>
      </div>
    </header>
    {drawer && <button className="drawer-scrim" aria-label="إغلاق القائمة" onClick={() => setDrawer(false)}/>}
    <aside className={`sidebar ${drawer ? 'sidebar-open' : ''}`} aria-label="قائمة الطالب">
      <div className="sidebar-brand"><Logo/><button className="icon-button" aria-label="إغلاق القائمة" onClick={() => setDrawer(false)}><X size={17}/></button></div>
      <nav>{groups.map((group) => <div className="nav-group" key={group.title}><h2>{group.title}</h2>{group.items.map(([path, title, Icon]) => { const href = `/student${path ? '/' + path : ''}`; const selected = pathname === href; return <Link key={href} href={href} onClick={() => setDrawer(false)} aria-current={selected ? 'page' : undefined} className="sidebar-link">{selected && <motion.i className="nav-needle" layoutId="nav-needle" transition={{ duration: .28 }}/>}<span className="nav-icon"><Icon size={18} strokeWidth={1.7}/></span><span>{title}</span></Link>; })}</div>)}</nav>
      <div className="sidebar-student"><span className="account-initial">{initial}</span><div><strong>{displayName}</strong>{studentId ? <small dir="ltr">{String(studentId)}</small> : null}</div></div>
    </aside>
    <div className="app-content"><div key={pathname} className="route-reveal">{children}</div><footer className="app-footer">مرشدي © {new Date().getFullYear()} <span>القرار الأكاديمي النهائي عبر الجامعة.</span></footer></div>
    {pathname !== '/student/advisor' && <Link className="ask-morshidi" href="/student/advisor" aria-label="اسأل مرشدي"><LogoMark/><span>اسأل مرشدي</span></Link>}
    <nav className="mobile-tabs" aria-label="التنقل السريع">{[['', 'الرئيسية', LayoutDashboard], ['planner', 'خطتي', CalendarDays], ['advisor', 'مرشدي', Compass], ['progress', 'تقدمي', ChartNoAxesCombined]].map(([path, title, Icon]) => { const IconComponent = Icon as typeof Compass; return <Link key={String(path)} href={`/student${path ? '/' + path : ''}`} aria-current={pathname === `/student${path ? '/' + path : ''}` ? 'page' : undefined}><IconComponent size={20}/><span>{String(title)}</span></Link>; })}<button aria-expanded={drawer} onClick={() => setDrawer(!drawer)}><Menu size={20}/><span>القائمة</span></button></nav>
  </div>;
}
