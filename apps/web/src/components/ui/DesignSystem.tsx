'use client';

import { useEffect, useRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { Compass, RotateCcw } from 'lucide-react';
import { motion, useReducedMotion } from 'framer-motion';
import { label } from '@/lib/labels';

export function CountUp({ value }: { value: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const previous = useRef(value);
  const reduced = useReducedMotion();
  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const from = previous.current;
    previous.current = value;
    if (reduced) { node.textContent = String(value); return; }
    let frame = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / 600);
      node.textContent = new Intl.NumberFormat('en', { maximumFractionDigits: 2 }).format(from + (value - from) * (1 - Math.pow(1 - progress, 3)));
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value, reduced]);
  return <span ref={ref} className="tabular-nums">{value}</span>;
}

export function Button({ children, className = '', ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button {...props} className={`button-primary ${className}`}>{children}</button>;
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`engraved ${className}`}>{children}</div>;
}

export function PageHeader({ eyebrow, title, description, action, className = '' }: { eyebrow?: string; title: string; description?: string; action?: ReactNode; className?: string }) {
  return <header className={`page-header ${className}`}><div className="page-header-copy">{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h1>{title}</h1>{description && <p>{description}</p>}</div>{action && <div className="page-header-action">{action}</div>}</header>;
}

export function SectionHeader({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return <div className="section-header"><div><h2>{title}</h2>{description && <p>{description}</p>}</div>{action}</div>;
}

export function InsightCard({ icon, eyebrow, title, children, hrefLabel }: { icon?: ReactNode; eyebrow?: string; title: string; children?: ReactNode; hrefLabel?: string }) {
  return <article className="insight-card"><div className="insight-icon">{icon}</div><div>{eyebrow && <span>{eyebrow}</span>}<h3>{title}</h3>{children && <p>{children}</p>}{hrefLabel && <strong>{hrefLabel} <b aria-hidden="true">↖</b></strong>}</div></article>;
}

export function Dial({ value, max = 100, label: caption, size = 160 }: { value: number; max?: number; label?: string; size?: number }) {
  const percent = max > 0 ? Math.min(100, Math.max(0, value / max * 100)) : 0;
  return <div className="dial" style={{ width: size, maxWidth: '100%' }} role="img" aria-label={`${caption ?? 'التقدم'} ${Math.round(percent)}%`}><svg viewBox="0 0 180 180" fill="none" aria-hidden="true"><circle cx="90" cy="90" r="87" stroke="var(--line)"/><circle cx="90" cy="90" r="70" stroke="var(--line)" strokeWidth="2"/>{Array.from({ length: 48 }, (_, i) => <path key={i} d={`M90 8v${i % 4 === 0 ? 9 : 4}`} transform={`rotate(${i * 7.5} 90 90)`} stroke={i / 48 * 100 < percent ? 'var(--copper)' : 'var(--line)'}/>)}<motion.circle cx="90" cy="90" r="70" stroke="var(--copper)" strokeWidth="3" strokeLinecap="round" pathLength="100" strokeDasharray="100" initial={false} animate={{ strokeDashoffset: 100 - percent }} transition={{ duration: .6 }} transform="rotate(-90 90 90)"/><circle cx="90" cy="90" r="62" stroke="var(--line)" strokeDasharray="1 8"/></svg><div className="dial-value"><strong><CountUp value={Math.round(percent)}/><small>%</small></strong>{caption && <span>{caption}</span>}</div></div>;
}

export function StatusLantern({ status }: { status: string }) { return <span className={`lantern lantern-${status.toLowerCase()}`} role="img" aria-label={label(status, 'حالة المادة')} title={label(status, 'حالة المادة')}/>; }
export function DifficultyDots({ level, low = false, locale = 'ar' }: { level: string; low?: boolean; locale?: 'ar' | 'en' }) { const n = ['VERY_EASY', 'EASY', 'MODERATE', 'HARD', 'VERY_HARD'].indexOf(level) + 1; if (!n) return null; const title = locale === 'en' ? 'Initial estimate' : 'تقدير أولي'; return <span className="difficulty" role="img" aria-label={locale === 'en' ? (n < 3 ? 'Easy' : n === 3 ? 'Moderate' : 'Hard') : (n < 3 ? 'سهلة' : n === 3 ? 'متوسطة' : 'صعبة')} title={low ? title : ''}>{Array.from({ length: 5 }, (_, i) => <i className={i < n ? 'filled' : ''} key={i}/>)}{low && <small aria-label={title}>·</small>}</span>; }
export function FriendlyState({ error = false, onRetry, title }: { error?: boolean; onRetry?: () => void; title?: string }) { return <div className="friendly-state" role={error ? 'alert' : undefined}><Compass size={42} strokeWidth={1}/><h3>{title ?? (error ? 'تعذّر التحميل' : 'لا بيانات بعد')}</h3>{onRetry && <button className="button-secondary" onClick={onRetry}><RotateCcw size={16}/>إعادة المحاولة</button>}</div>; }
export function SegmentedControl({ options, value, onChange }: { options: { value: string; label: string }[]; value: string; onChange: (value: string) => void }) { return <div className="segmented">{options.map((option) => <button key={option.value} aria-pressed={value === option.value} onClick={() => onChange(option.value)} type="button">{option.label}</button>)}</div>; }
