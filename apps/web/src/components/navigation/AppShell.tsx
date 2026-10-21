'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState, type ReactNode } from 'react';
import { ChevronDown, Menu, X } from 'lucide-react';
import { useAuth } from '@/auth/auth-provider';
import { SignOutButton } from '@/auth/sign-out-button';
import { Emoji } from '@/components/ui/Emoji';
import { getStudentDisplayName, getStudentInitial } from '@/lib/student-identity';

const groups = [
  { title: 'مساحتي', items: [['', 'نظرة عامة', '🏠'], ['profile', 'الملف الأكاديمي', '👤'], ['progress', 'التقدم الدراسي', '📈'], ['courses', 'المواد والدرجات', '📚']] },
  { title: 'قراراتي', items: [['registration', 'التسجيل الرسمي', '📝'], ['planner', 'خطة الفصل', '🗓️'], ['advisor', 'مرشدي AI', '🤖'], ['recommendations', 'التوصيات', '🧭'], ['eligibility', 'أهلية التسجيل', '✅'], ['degree-path', 'مسار التخرج', '🎯']] },
  { title: 'مصادري', items: [['roadmap', 'الخطة الدراسية', '🗺️'], ['offerings', 'المواد المطروحة', '📋'], ['chapters', 'شباتر المواد', '📖'], ['policies', 'اللوائح', '📜']] },
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
        <Link className="quick-command" href="/student/advisor"><span aria-hidden="true"><Emoji emoji="🤖" decorative /></span><span>اسأل مرشدي</span><kbd>⌘ K</kbd></Link>
        <div className="notification-wrap"><button className="icon-button" aria-label="الإشعارات" aria-expanded={bell} onClick={() => setBell(!bell)}><Emoji emoji="🔔" decorative /></button>{bell && <div className="account-popover"><p>لا إشعارات بعد</p></div>}</div>
        <details className="account-menu"><summary><span className="account-initial">{initial}</span><span className="account-name">{displayName}</span><ChevronDown size={14}/></summary><div className="account-popover"><div className="account-identity"><strong>{displayName}</strong>{studentId ? <span dir="ltr">{String(studentId)}</span> : null}</div><Link href="/student/profile">الملف الشخصي</Link><Link href="/student/privacy">الخصوصية</Link><Link href="/student/decision-history">سجل القرارات</Link><SignOutButton/></div></details>
      </div>
    </header>
    {drawer && <button className="drawer-scrim" aria-label="إغلاق القائمة" onClick={() => setDrawer(false)}/>}
    <aside className={`sidebar ${drawer ? 'sidebar-open' : ''}`} aria-label="قائمة الطالب">
      <div className="sidebar-brand"><Link href="/student" className="midnight-logo">مرشدي <span aria-hidden="true"><Emoji emoji="🎓" decorative /></span></Link><button className="icon-button" aria-label="إغلاق القائمة" onClick={() => setDrawer(false)}><X size={17}/></button></div>
      <nav>{groups.map((group) => <div className="nav-group" key={group.title}><h2>{group.title}</h2>{group.items.map(([path, title, emoji]) => { const href = `/student${path ? '/' + path : ''}`; const selected = pathname === href; return <Link key={href} href={href} onClick={() => setDrawer(false)} aria-current={selected ? 'page' : undefined} className="sidebar-link"><span className="nav-icon" aria-hidden="true"><Emoji emoji={emoji} decorative /></span><span>{title}</span></Link>; })}</div>)}</nav>
      <div className="sidebar-student glass"><span aria-hidden="true"><Emoji emoji="🧑‍🎓" decorative /></span><div><strong>{displayName}</strong>{studentId ? <small dir="ltr">{String(studentId)}</small> : null}</div></div>
    </aside>
    <div className="app-content"><div key={pathname} className="route-reveal">{children}</div><footer className="app-footer">مرشدي © {new Date().getFullYear()} <span>القرار الأكاديمي النهائي عبر الجامعة.</span></footer></div>
    {pathname !== '/student/advisor' && <Link className="ask-morshidi glass" href="/student/advisor" aria-label="اسأل مرشدي"><span aria-hidden="true"><Emoji emoji="🤖" decorative /></span><span>اسأل مرشدي</span></Link>}
    <nav className="mobile-tabs glass" aria-label="التنقل السريع">{[['', 'الرئيسية', '🏠'], ['progress', 'التقدم', '📈'], ['advisor', 'مرشدي', '🤖'], ['courses', 'المواد', '📚']].map(([path, title, emoji]) => <Link key={path} href={`/student${path ? '/' + path : ''}`} aria-current={pathname === `/student${path ? '/' + path : ''}` ? 'page' : undefined}><span className="mobile-tab-emoji" aria-hidden="true"><Emoji emoji={emoji} decorative /></span><span>{title}</span></Link>)}</nav>
  </div>;
}
