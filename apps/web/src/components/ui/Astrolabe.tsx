export function Astrolabe({className=''}:{className?:string}) {return <svg viewBox="0 0 600 600" className={`astrolabe ${className}`} fill="none" aria-hidden="true">
  {[278,266,242,212,180,100].map(r=><circle key={r} cx="300" cy="300" r={r} stroke="currentColor" strokeWidth={r===278?1.3:.5}/>)}
  {Array.from({length:72},(_,i)=><path key={i} d={`M300 22v${i%6===0?20:8}`} stroke="currentColor" transform={`rotate(${i*5} 300 300)`}/>)}
  {['٠','١','٢','٣','٤','٥','٦','٧','٨','٩','١٠','١١'].map((n,i)=><text key={n} x={300+225*Math.sin(i*Math.PI/6)} y={306-225*Math.cos(i*Math.PI/6)} fill="currentColor" textAnchor="middle" fontSize="14">{n}</text>)}
  <path d="M300 86 350 246 514 300 352 352 300 514 246 354 86 300 248 248Z" stroke="currentColor" strokeWidth=".6"/><path d="M120 120 480 480M480 120 120 480" stroke="currentColor" strokeWidth=".4"/><circle cx="300" cy="300" r="8" stroke="currentColor"/>
</svg>;}
