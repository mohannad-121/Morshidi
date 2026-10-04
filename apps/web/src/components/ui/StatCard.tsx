'use client';
import {type ReactNode} from 'react';
import {CountUp} from './DesignSystem';
export function StatCard({title,value,badge,icon,className=''}:{title:string;value:string|number;subtitle?:string;badge?:ReactNode;icon?:ReactNode;variant?:'default'|'warm'|'gold';className?:string}) {return <div className={`engraved stat-plate p-6 ${className}`}><div className="flex items-center justify-between gap-3"><p className="text-xs text-muted">{title}</p><span className="text-copper">{icon}</span></div><div className="mt-5 flex items-baseline gap-2"><span className="text-3xl font-medium tabular-nums">{typeof value==='number'?<CountUp value={value}/>:value}</span>{badge}</div></div>;}
