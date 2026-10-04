import {Dial} from './DesignSystem';
export function CircularProgress({value,max,size=120,label,sublabel,className=''}:{value:number;max:number;size?:number;strokeWidth?:number;label?:string;sublabel?:string;className?:string}){return <div className={className}><Dial value={value} max={max} size={size} label={label}/>{sublabel&&<small>{sublabel}</small>}</div>;}
