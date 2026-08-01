import type { ReactNode } from 'react'
import { Activity, BrainCircuit, ChevronRight, CircleDot, Database, Eye, FlaskConical, Gauge, MessageSquareText, Network, Pause, Play, Power, ScanSearch, ShieldCheck, Sparkles, UserRoundCog } from 'lucide-react'

export const icons = {overview: Gauge, conversation: MessageSquareText, cognition: Network, memory: Database, self: UserRoundCog, metacognition: BrainCircuit, witness: Eye, vi: Sparkles, beliefs: ShieldCheck, experiments: FlaskConical, control: Power, evaluation: ScanSearch}

export function Panel({title, eyebrow, actions, children, className = ''}: {title: string; eyebrow?: string; actions?: ReactNode; children: ReactNode; className?: string}) {
  return <section className={`panel ${className}`}><header className="panel-header"><div>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h2>{title}</h2></div>{actions}</header>{children}</section>
}

export function Metric({label, value, tone = 'neutral', detail}: {label: string; value: ReactNode; tone?: string; detail?: string}) {
  return <article className={`metric metric-${tone}`}><p>{label}</p><strong>{value}</strong>{detail && <span>{detail}</span>}</article>
}

export function Badge({children, tone = 'neutral'}: {children: ReactNode; tone?: string}) {return <span className={`badge badge-${tone}`}>{children}</span>}

export function Empty({title, text}: {title: string; text: string}) {return <div className="empty"><CircleDot size={22}/><strong>{title}</strong><p>{text}</p></div>}

export function Flow({active}: {active?: string}) {
  const stages = ['Manas', 'Attention', 'Workspace', 'Recurrence', 'Metacognition', 'Buddhi', 'Ahamkara', 'Response']
  return <div className="flow" aria-label="AEON cognitive flow">{stages.map((stage, i) => <div key={stage} className={`flow-step ${active === stage.toLowerCase() ? 'active' : ''}`}><Activity size={15}/><span>{stage}</span>{i < stages.length - 1 && <ChevronRight className="flow-arrow" size={15}/>}</div>)}</div>
}

export function ControlButtons({status, act}: {status: string; act: (path: string) => void}) {
  return <div className="button-row"><button className="button secondary" onClick={() => act(status === 'paused' ? '/api/control/resume' : '/api/control/pause')}>{status === 'paused' ? <Play size={16}/> : <Pause size={16}/>} {status === 'paused' ? 'Resume' : 'Pause'}</button><button className="button danger" onClick={() => act('/api/control/shutdown')}><Power size={16}/> Shutdown</button></div>
}

