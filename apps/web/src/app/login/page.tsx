import { Suspense } from 'react';
import Link from 'next/link';
import { ArrowLeft, BookOpenCheck, Route, Sparkles } from 'lucide-react';
import { LoginForm } from '@/auth/login-form';
import { Logo, LogoMark } from '@/components/ui/Logo';

export default function LoginPage() {
  return <main className="login-page" dir="rtl">
    <section className="login-story" aria-label="رحلتك الأكاديمية مع مرشدي">
      <Logo/>
      <div className="login-story-copy"><span className="eyebrow">مساحتك الأكاديمية، أوضح</span><h1>من وضعك اليوم<br/>إلى خطوتك القادمة.</h1><p>اقرأ تقدمك، اختبر قراراتك، وابنِ فصلك على بيانات جامعتك الموثوقة.</p></div>
      <div className="login-orbit" aria-hidden="true"><div className="orbit-ring orbit-one"/><div className="orbit-ring orbit-two"/><LogoMark/><span className="orbit-node node-one"><BookOpenCheck/></span><span className="orbit-node node-two"><Route/></span><span className="orbit-node node-three"><Sparkles/></span></div>
      <div className="login-proof"><span>بيانات الجامعة</span><i/><span>قواعد حتمية</span><i/><span>شرح مفهوم</span></div>
    </section>
    <section className="login-access"><div className="login-access-inner"><div className="login-mobile-logo"><Logo/></div><span className="eyebrow">بوابة الطالب</span><h2>أهلاً بعودتك</h2><p>ادخل بحساب جامعتك للوصول إلى مساحتك الأكاديمية.</p><Suspense fallback={<p className="login-loading" role="status">جاري تجهيز تسجيل الدخول…</p>}><LoginForm/></Suspense><Link href="/" className="login-back"><ArrowLeft size={15}/>العودة إلى الصفحة الرئيسية</Link></div></section>
  </main>;
}
