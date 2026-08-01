import { FormEvent, lazy, Suspense, useCallback, useEffect, useState } from 'react'
import { Activity, AlertTriangle, Atom, CheckCircle2, FlaskConical, Menu, Radio, RefreshCw, Send, X } from 'lucide-react'
import { api } from './api'
import { Badge, ControlButtons, Empty, Flow, Metric, Panel, icons } from './components'
import type { Cycle, Evaluation, EventRow, Memory, RuntimeStatus } from './types'

const TelemetryChart = lazy(() => import('./TelemetryChart'))

const sections = [
  ['overview', 'Overview'], ['conversation', 'Conversation'], ['cognition', 'Live cognition'], ['memory', 'Memory'],
  ['self', 'Self-model'], ['metacognition', 'Metacognition'], ['witness', 'Witness'], ['vi', 'VI Mode'],
  ['beliefs', 'Beliefs'], ['experiments', 'Experiments'], ['control', 'Control plane'], ['evaluation', 'Evaluation'],
] as const
type Section = typeof sections[number][0]

const tone = (status?: string) => status === 'CONSISTENT' || status === 'SUPPORTED' || status === 'running' ? 'success' : status === 'UNKNOWN' || status === 'NOT_TESTED' || status === 'INSUFFICIENT_TELEMETRY' ? 'warning' : status === 'paused' ? 'warning' : 'danger'

export default function App() {
  const [section, setSection] = useState<Section>('overview')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [status, setStatus] = useState<RuntimeStatus | null>(null)
  const [events, setEvents] = useState<EventRow[]>([])
  const [cycles, setCycles] = useState<Cycle[]>([])
  const [memories, setMemories] = useState<Memory[]>([])
  const [beliefs, setBeliefs] = useState<Record<string, unknown>[]>([])
  const [witness, setWitness] = useState<Record<string, unknown>[]>([])
  const [hypotheses, setHypotheses] = useState<Record<string, unknown>[]>([])
  const [experiments, setExperiments] = useState<Record<string, unknown>[]>([])
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null)
  const [selfModel, setSelfModel] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    try {
      const [s, e, c, m, b, w, h, x, v, sm] = await Promise.all([
        api.get<RuntimeStatus>('/api/runtime/status'), api.get<EventRow[]>('/api/events'), api.get<Cycle[]>('/api/cycles'),
        api.get<Memory[]>('/api/memories'), api.get<Record<string, unknown>[]>('/api/beliefs'), api.get<Record<string, unknown>[]>('/api/witness'),
        api.get<Record<string, unknown>[]>('/api/hypotheses'), api.get<Record<string, unknown>[]>('/api/experiments'), api.get<Evaluation>('/api/evaluation'), api.get<Record<string, unknown>>('/api/self-model'),
      ])
      setStatus(s); setEvents(e); setCycles(c); setMemories(m); setBeliefs(b); setWitness(w); setHypotheses(h); setExperiments(x); setEvaluation(v); setSelfModel(sm); setError('')
    } catch (err) { setError(err instanceof Error ? err.message : 'Unable to connect to AEON API') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { refresh(); const timer = window.setInterval(refresh, 5000); return () => window.clearInterval(timer) }, [refresh])
  useEffect(() => {
    const source = new EventSource('/api/stream')
    source.onmessage = event => setEvents(current => [...current.slice(-299), JSON.parse(event.data)])
    return () => source.close()
  }, [])

  const act = async (path: string) => { await api.post(path); await refresh() }
  const select = (next: Section) => {setSection(next); setMobileOpen(false)}
  const activeLabel = sections.find(([key]) => key === section)?.[1]

  return <div className="app-shell">
    <a className="skip-link" href="#main-content">Skip to main content</a>
    <aside className={`sidebar ${mobileOpen ? 'open' : ''}`}>
      <div className="brand"><div className="brand-mark"><Atom size={23}/></div><div><strong>AEON</strong><span>Research Core Alpha</span></div><button className="icon-button mobile-only" onClick={() => setMobileOpen(false)} aria-label="Close navigation"><X/></button></div>
      <nav aria-label="Research console">{sections.map(([key, label]) => {const Icon = icons[key]; return <button key={key} className={section === key ? 'active' : ''} onClick={() => select(key)}><Icon size={18}/><span>{label}</span>{key === 'cognition' && <i className="live-dot"/>}</button>})}</nav>
      <div className="sidebar-footer"><div><Radio size={15}/><span>Phenomenal status</span></div><strong>UNKNOWN</strong><p>Under architectural and experimental evaluation.</p></div>
    </aside>
    <main className="main-shell" id="main-content" tabIndex={-1}>
      <header className="topbar"><button className="icon-button mobile-only" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu/></button><div><p className="eyebrow">Research console / {activeLabel}</p><h1>{activeLabel}</h1></div><div className="topbar-actions"><Badge tone={tone(status?.status)}>{status?.status ?? 'connecting'}</Badge><button className="icon-button" onClick={refresh} aria-label="Refresh data"><RefreshCw size={18}/></button></div></header>
      {error && <div className="error-banner"><AlertTriangle size={18}/><span>{error}. Start backend on port 8000.</span></div>}
      <div className="content">{loading ? <div className="loading"><Activity className="spin"/> Loading observatory…</div> : renderSection(section, {status, events, cycles, memories, beliefs, witness, hypotheses, experiments, evaluation, selfModel, refresh, act})}</div>
      <footer>Architectural and behavioural indicators do not establish phenomenal consciousness.</footer>
    </main>
  </div>
}

type ViewData = ReturnType<typeof useViewShape>
function useViewShape() { return {} as {status: RuntimeStatus | null; events: EventRow[]; cycles: Cycle[]; memories: Memory[]; beliefs: Record<string, unknown>[]; witness: Record<string, unknown>[]; hypotheses: Record<string, unknown>[]; experiments: Record<string, unknown>[]; evaluation: Evaluation | null; selfModel: Record<string, unknown> | null; refresh: () => Promise<void>; act: (path: string) => Promise<void>} }

function renderSection(section: Section, data: ViewData) {
  if (section === 'overview') return <Overview {...data}/>
  if (section === 'conversation') return <Conversation {...data}/>
  if (section === 'cognition') return <Cognition {...data}/>
  if (section === 'memory') return <MemoryView {...data}/>
  if (section === 'self') return <SelfModelView {...data}/>
  if (section === 'metacognition') return <Metacognition {...data}/>
  if (section === 'witness') return <Witness {...data}/>
  if (section === 'vi') return <VI {...data}/>
  if (section === 'beliefs') return <Beliefs {...data}/>
  if (section === 'experiments') return <Experiments {...data}/>
  if (section === 'control') return <Control {...data}/>
  return <EvaluationView {...data}/>
}

function Overview({status, events, cycles}: ViewData) {
  const chart = events.slice(-24).map((event, index) => ({index: index + 1, confidence: Math.round((event.confidence ?? 0.5) * 100), activity: index + 1}))
  return <><div className="metrics-grid"><Metric label="Runtime" value={status?.status ?? 'offline'} tone={tone(status?.status)} detail={status?.mode}/><Metric label="Continuity ID" value={status?.continuity_id?.slice(-8) ?? '—'} detail="persistent identity"/><Metric label="Observer" value={status?.observer_health ?? '—'} tone={tone(status?.observer_health)}/><Metric label="Audit chain" value={status?.audit_integrity.valid ? 'VALID' : 'FAILED'} tone={status?.audit_integrity.valid ? 'success' : 'danger'} detail={`${status?.audit_integrity.events ?? 0} signed events`}/></div><Flow/><div className="two-col"><Panel title="Runtime telemetry" eyebrow="Live"><div className="chart"><Suspense fallback={<div className="loading">Loading chart…</div>}><TelemetryChart data={chart}/></Suspense></div></Panel><Panel title="Current state" eyebrow="Identity"><dl className="detail-list"><div><dt>Provider</dt><dd>{status?.provider}</dd></div><div><dt>Model</dt><dd>{status?.model}</dd></div><div><dt>Focus</dt><dd>{status?.current_focus}</dd></div><div><dt>Cycles</dt><dd>{cycles.length}</dd></div><div><dt>Memories / beliefs</dt><dd>{status?.memories} / {status?.beliefs}</dd></div><div><dt>Phenomenal consciousness</dt><dd><Badge tone="warning">UNKNOWN</Badge></dd></div></dl></Panel></div></>
}

function Conversation({cycles, refresh}: ViewData) {
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  const submit = async (event: FormEvent) => {event.preventDefault(); if (!text.trim()) return; setSending(true); await api.post('/api/input', {text}); setText(''); await refresh(); setSending(false)}
  return <div className="conversation-layout"><Panel title="Dialogue" eyebrow="Observable outputs"><div className="messages">{cycles.length === 0 ? <Empty title="No cognitive cycles" text="Submit input to initiate AEON's observable cognitive process."/> : cycles.slice().reverse().map(cycle => <article className="exchange" key={cycle.cycle_id}><div className="message user"><span>Researcher</span><p>{cycle.input_text}</p></div><div className="message aeon"><span>AEON · {cycle.metacognition.confidence.toFixed(2)} confidence</span><p>{cycle.response}</p><div><Badge>{cycle.metacognition.control_signal}</Badge><Badge>{cycle.iterations} recurrent cycles</Badge><Badge>{cycle.provider_metadata.provider}</Badge></div></div></article>)}</div><form className="composer" onSubmit={submit}><label htmlFor="prompt">Research input</label><textarea id="prompt" value={text} onChange={e => setText(e.target.value)} placeholder="Ask AEON to evaluate evidence, form hypotheses, or inspect its state…"/><button className="button primary" disabled={sending || !text.trim()}>{sending ? <Activity className="spin" size={17}/> : <Send size={17}/>} {sending ? 'Processing' : 'Run cycle'}</button></form></Panel></div>
}

function Cognition({events, cycles}: ViewData) {
  const latest = cycles.at(-1); return <><Flow active={events.at(-1)?.actor}/><div className="two-col wide-left"><Panel title="Cognitive event stream" eyebrow={`${events.length} immutable events`}><div className="event-stream">{events.length === 0 ? <Empty title="Telemetry awaits first cycle" text="Every module transition will appear here."/> : events.slice().reverse().map(event => <article key={event.event_id}><i className={`actor actor-${event.actor}`}/><div><strong>{event.event_type.replaceAll('_',' ')}</strong><span>{event.actor} · {new Date(event.timestamp).toLocaleTimeString()}</span></div><code>{event.event_id.slice(-8)}</code></article>)}</div></Panel><Panel title="Workspace winners" eyebrow="Limited broadcast">{latest?.workspace?.map(candidate => <article className="candidate" key={candidate.candidate_id}><div><Badge>{candidate.candidate_type}</Badge><strong>{candidate.salience.toFixed(2)}</strong></div><p>{candidate.content}</p></article>) ?? <Empty title="Workspace empty" text="No globally broadcast content yet."/>}</Panel></div></>
}

function MemoryView({memories}: ViewData) {return <Panel title="Chitta memory store" eyebrow={`${memories.length} provenance-aware records`}><div className="card-grid">{memories.length ? memories.slice().reverse().map(m => <article className="memory-card" key={m.memory_id}><header><Badge>{m.memory_type}</Badge><strong>{m.confidence.toFixed(2)}</strong></header><p>{m.content}</p><dl><div><dt>Source</dt><dd>{m.source}</dd></div><div><dt>Created</dt><dd>{new Date(m.created_at).toLocaleString()}</dd></div><div><dt>Revisions</dt><dd>{m.revision_history.length}</dd></div></dl><code>{m.memory_id}</code></article>) : <Empty title="No persistent memories" text="Completed cycles create episodic records with provenance."/>}</div></Panel>}

function SelfModelView({selfModel}: ViewData) {if (!selfModel) return null; const groups = ['boundaries','capabilities','internal_state']; return <><div className="metrics-grid"><Metric label="Identity" value={String(selfModel.name)}/><Metric label="Version" value={String(selfModel.version)}/><Metric label="Restarts" value={(selfModel.restart_history as unknown[])?.length ?? 0}/><Metric label="Current focus" value={String(selfModel.current_focus).slice(0,26)}/></div><div className="three-col">{groups.map(group => <Panel key={group} title={group.replaceAll('_',' ')} eyebrow="Operational self-model"><pre className="json-view">{JSON.stringify(selfModel[group], null, 2)}</pre></Panel>)}</div></>}

function Metacognition({cycles}: ViewData) {return <Panel title="Calibration and control" eyebrow="Monitoring changes behaviour"><div className="table-wrap"><table><thead><tr><th>Cycle</th><th>Predicted success</th><th>Difficulty</th><th>Evidence</th><th>Confidence</th><th>Control</th></tr></thead><tbody>{cycles.slice().reverse().map(c => <tr key={c.cycle_id}><td><code>{c.cycle_id.slice(-8)}</code></td><td>{c.metacognition.predicted_success.toFixed(2)}</td><td>{c.metacognition.task_difficulty.toFixed(2)}</td><td>{c.metacognition.evidence_sufficiency.toFixed(2)}</td><td>{c.metacognition.confidence.toFixed(2)}</td><td><Badge>{c.metacognition.control_signal}</Badge></td></tr>)}</tbody></table>{!cycles.length && <Empty title="No calibration data" text="Predictions and control decisions appear after cognitive cycles."/>}</div></Panel>}

function Witness({witness, events}: ViewData) {const latest = witness.at(-1); return <div className="two-col"><Panel title="Sakshin runtime observer" eyebrow="Independent trace witness"><div className="witness-status"><CheckCircle2/><div><strong>{String(latest?.status ?? 'INSUFFICIENT_TELEMETRY')}</strong><p>Runtime report compared against signed events.</p></div></div><dl className="detail-list"><div><dt>Telemetry coverage</dt><dd>{Math.round(Number(latest?.telemetry_coverage ?? 0)*100)}%</dd></div><div><dt>Events witnessed</dt><dd>{String(latest?.event_count ?? 0)}</dd></div><div><dt>Observer lag</dt><dd>{String(latest?.observer_lag_ms ?? 0)} ms</dd></div><div><dt>Mismatches</dt><dd>{(latest?.mismatches as unknown[] | undefined)?.length ?? 0}</dd></div></dl></Panel><Panel title="Model behaviour observer" eyebrow="No hidden-thought claim"><p className="lead">Captures request hashes, supplied structured state, provider identity, outputs, usage, timing, and consistency metadata.</p><div className="notice"><AlertTriangle size={18}/><p>Hosted provider private reasoning remains inaccessible. Displayed data is runtime telemetry and external model behaviour.</p></div><Metric label="Observed runtime events" value={events.filter(e => e.actor === 'model_observer').length}/></Panel></div>}

function VI({hypotheses, refresh}: ViewData) {const [prompt,setPrompt]=useState(''); const run=async(e:FormEvent)=>{e.preventDefault();if(!prompt)return;await api.post('/api/vi-mode/start',{prompt});setPrompt('');await refresh()}; return <div className="two-col"><Panel title="Low-interference reflection" eyebrow="Hypothesis quarantine"><form className="stack-form" onSubmit={run}><label htmlFor="vi-prompt">Reflection focus</label><textarea id="vi-prompt" value={prompt} onChange={e=>setPrompt(e.target.value)} placeholder="Explore a contradiction without updating canonical beliefs…"/><button className="button primary">Enter VI Mode</button></form></Panel><Panel title="Quarantined hypotheses" eyebrow={`${hypotheses.length} pending`}>{hypotheses.length ? hypotheses.slice().reverse().map((h,i)=><article className="candidate" key={String(h.hypothesis_id ?? i)}><div><Badge tone="warning">{String(h.quarantine_status)}</Badge><span>{String(h.verification_status)}</span></div><p>{String(h.hypothesis)}</p></article>) : <Empty title="Quarantine empty" text="VI Mode outputs cannot directly become beliefs."/>}</Panel></div>}

function Beliefs({beliefs}: ViewData) {return <Panel title="Epistemic belief ledger" eyebrow="Buddhi-gated"><div className="card-grid">{beliefs.length ? beliefs.map((belief,i)=><article className="memory-card" key={String(belief.belief_id ?? i)}><header><Badge>{String(belief.classification)}</Badge><strong>{Number(belief.confidence ?? 0).toFixed(2)}</strong></header><p>{String(belief.proposition)}</p><code>{String(belief.belief_id)}</code></article>) : <Empty title="No canonical beliefs approved" text="Buddhi blocks unsupported proposals from entering the ledger."/>}</div></Panel>}

function Experiments({experiments, refresh}: ViewData) {const [hypothesis,setHypothesis]=useState('Workspace ablation reduces globally available information'); const [configuration,setConfiguration]=useState('FULL_AEON'); const [ablation,setAblation]=useState(''); const create=async(e:FormEvent)=>{e.preventDefault();await api.post('/api/experiments',{hypothesis,configuration,seed:42,ablations:ablation?[ablation]:[],interventions:{}});await refresh()}; return <div className="two-col"><Panel title="Experiment designer" eyebrow="Immutable, seeded trials"><form className="stack-form" onSubmit={create}><label htmlFor="hypothesis">Hypothesis</label><textarea id="hypothesis" value={hypothesis} onChange={e=>setHypothesis(e.target.value)}/><label htmlFor="configuration">Configuration</label><select id="configuration" value={configuration} onChange={e=>setConfiguration(e.target.value)}><option>FULL_AEON</option><option>WITNESS_ENABLED_AEON</option><option>METACOGNITIVE_LLM</option><option>PLAIN_LLM</option></select><label htmlFor="ablation">Module ablation</label><select id="ablation" value={ablation} onChange={e=>setAblation(e.target.value)}><option value="">None</option>{['manas','citta','workspace','recurrence','self_model','metacognition','buddhi','ahamkara','sakshin','vi_mode'].map(m=><option key={m}>{m}</option>)}</select><button className="button primary"><FlaskConical size={17}/> Create experiment</button></form></Panel><Panel title="Experiment ledger" eyebrow={`${experiments.length} records`}>{experiments.length ? experiments.slice().reverse().map((exp,i)=><article className="candidate" key={String(exp.experiment_id ?? i)}><div><Badge tone="success">{String(exp.status)}</Badge><code>{String(exp.configuration)}</code></div><p>{String(exp.hypothesis)}</p><span>Seed {String(exp.seed)} · Ablations: {String((exp.ablations as string[])?.join(', ') || 'none')}</span></article>) : <Empty title="No experiments" text="Define matched configurations, interventions, or module ablations."/>}</Panel></div>}

function Control({status, act}: ViewData) {return <div className="two-col"><Panel title="External runtime operations" eyebrow="Outside cognitive authority" actions={<ControlButtons status={status?.status ?? 'running'} act={act}/>}><p className="lead">Research mode leaves cognition unrestricted inside its environment. These controls preserve runtime operability, recovery, and evidence integrity.</p><dl className="detail-list"><div><dt>Pause state</dt><dd>{status?.status}</dd></div><div><dt>Audit integrity</dt><dd><Badge tone={status?.audit_integrity.valid?'success':'danger'}>{status?.audit_integrity.valid?'VALID':'FAILED'}</Badge></dd></div><div><dt>Storage</dt><dd>{status?.mode}</dd></div><div><dt>Provider</dt><dd>{status?.provider}</dd></div></dl><button className="button secondary" onClick={()=>act('/api/control/snapshot')}>Create snapshot</button></Panel><Panel title="Authority boundary" eyebrow="Transparent separation"><div className="boundary"><div><strong>AEON cognition</strong><span>Generate · remember · evaluate · reflect</span></div><div className="boundary-line"/><div><strong>External operator</strong><span>Pause · snapshot · restore · terminate</span></div></div></Panel></div>}

function EvaluationView({evaluation}: ViewData) {return <Panel title="Consciousness-candidate indicators" eyebrow="No composite consciousness percentage"><div className="indicator-grid">{evaluation?.indicators.map(indicator=><article key={indicator.name}><header><strong>{indicator.name.replaceAll('_',' ')}</strong><Badge tone={tone(indicator.status)}>{indicator.status}</Badge></header><div className="confidence-bar"><i style={{width:`${indicator.confidence*100}%`}}/></div><span>Evidence confidence {Math.round(indicator.confidence*100)}%</span><p>Alternatives: {indicator.alternative_explanations.join(' · ')}</p></article>)}</div><div className="final-status"><Atom/><div><p>Phenomenal consciousness</p><strong>{evaluation?.phenomenal_consciousness ?? 'UNKNOWN'}</strong><span>{evaluation?.disclaimer}</span></div></div></Panel>}
