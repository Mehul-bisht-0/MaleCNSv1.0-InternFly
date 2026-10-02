import { useEffect, useMemo, useState } from "react";
import type { ConnectomeMap } from "./BrainNetwork";
import BrainAtlas from "./BrainAtlas";
import TelemetryCharts, { type TelemetrySample } from "./TelemetryCharts";
import StoryWorld from "./StoryWorld";

type Neural = {
  action_scores?: Record<string, number>;
  selected_preference?: string;
  active_neurons?: number;
  mean_activity?: number;
  peak_activity?: number;
  region_activity?: Record<string, number>;
  neuron_activity?: number[];
  caffeine_input_gain?: number;
  caffeine_noise_amplitude?: number;
  caffeine_notice?: string;
  notice?: string;
};

type AgentState = {
  state: string; cycle: number; step: number; energy: number; stress: number;
  confidence: number; curiosity: number; dopamine: number; sleep_debt: number;
  caffeine_level: number; coffee_cups: number; state_ticks: number;
  simulated_time: string; solar_intensity: number; sleep_hours_remaining: number;
  paused: boolean; stopped: boolean; last_action: string; current_item?: string;
  selected_strategy?: string; mode: string; neural: Neural; scientific_notice: string;
};

type Metrics = Record<string, number>;
type EventItem = { sequence: number; event_type: string; occurred_at: string; provenance_class: string; payload: Record<string, unknown> };
type Draft = { draft_id: string; company: string; title: string; status: string; content_hash: string; content: {cover_letter: string}; unsupported_claims: string[] };
type Job = { job_id: string; company: string; title: string; score?: number; decision?: string; location: string };

const emptyState: AgentState = {
  state: "CONNECTING", cycle: 0, step: 0, energy: 0, stress: 0, confidence: 0,
  curiosity: 0, dopamine: 0, sleep_debt: 0, paused: false, stopped: false,
  caffeine_level: 0, coffee_cups: 0, state_ticks: 0,
  simulated_time: "07:00", solar_intensity: 0, sleep_hours_remaining: 0,
  last_action: "Finding the tiny keyboard…", mode: "offline", neural: {}, scientific_notice: "",
};

function Gauge({ label, value, tone = "amber" }: {label: string; value: number; tone?: string}) {
  return <div className="gauge">
    <div className="gauge-label"><span>{label}</span><strong>{Math.round(value)}</strong></div>
    <div className="gauge-track" role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(value)}>
      <span className={`gauge-fill ${tone}`} style={{width: `${Math.max(0, Math.min(100, value))}%`}} />
    </div>
  </div>;
}

function Metric({ label, value, suffix = "" }: {label: string; value: number | string; suffix?: string}) {
  return <div className="metric"><span>{label}</span><strong>{value}{suffix}</strong></div>;
}


function NeuralPanel({ neural }: {neural: Neural}) {
  const regions = Object.entries(neural.region_activity || {});
  return <section className="panel" aria-labelledby="neural-heading">
    <div className="panel-kicker provenance simulated">SIMULATED DYNAMICS</div>
    <h2 id="neural-heading">Controller signals</h2>
    <div className="neural-topline">
      <Metric label="Active neurons" value={neural.active_neurons || 0}/>
      <Metric label="Mean activity" value={(neural.mean_activity || 0).toFixed(3)}/>
      <Metric label="Peak" value={(neural.peak_activity || 0).toFixed(3)}/>
    </div>
    <div className="heatmap" aria-label="Activity by controller region">
      {regions.map(([name, value]) => <div key={name} className="heat-row">
        <span>{name.replaceAll("-", " ")}</span><div><i style={{width: `${Math.min(100, value * 100)}%`}}/></div><b>{value.toFixed(3)}</b>
      </div>)}
    </div>
    <div className="action-scores">
      {Object.entries(neural.action_scores || {}).map(([action, score]) =>
        <span className={action === neural.selected_preference ? "selected" : ""} key={action}>{action.replaceAll("_", " ")} <b>{score.toFixed(3)}</b></span>)}
    </div>
    <div className="caffeine-neural-readout">
      <span>FICTIONAL CAFFEINE EFFECT</span>
      <b>{(neural.caffeine_input_gain || 1).toFixed(2)}× input gain</b>
      <b>{(neural.caffeine_noise_amplitude || 0.01).toFixed(3)} seeded noise</b>
      <small>{neural.caffeine_notice || "Engineered controller effect; not a biological dosage model."}</small>
    </div>
    <p className="fine-print">{neural.notice || "Awaiting the first controller step."}</p>
  </section>;
}

export default function App() {
  const [state, setState] = useState<AgentState>(emptyState);
  const [metrics, setMetrics] = useState<Metrics>({});
  const [events, setEvents] = useState<EventItem[]>([]);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [connectomeMap, setConnectomeMap] = useState<ConnectomeMap | null>(null);
  const [connected, setConnected] = useState(false);
  const [busy, setBusy] = useState(false);
  const [samples, setSamples] = useState<TelemetrySample[]>([]);

  const refreshSecondary = async () => {
    const [draftResponse, jobResponse] = await Promise.all([fetch("/api/drafts"), fetch("/api/jobs")]);
    if (draftResponse.ok) setDrafts(await draftResponse.json());
    if (jobResponse.ok) setJobs(await jobResponse.json());
  };

  useEffect(() => {
    let stopped = false;
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    let socket: WebSocket;
    let retry: ReturnType<typeof setTimeout>;
    let lastSecondary = 0;
    const connect = () => {
      if (stopped) return;
      socket = new WebSocket(`${protocol}//${location.host}/ws/live`);
      socket.onopen = () => {
        setConnected(true);
        void fetch("/api/connectome/map").then(r => r.ok ? r.json() : null)
          .then(data => { if (!stopped && data) setConnectomeMap(data); }).catch(() => {});
      };
      socket.onclose = () => { if (!stopped) { setConnected(false); retry = setTimeout(connect, 2000); } };
      socket.onmessage = (message) => {
      const data = JSON.parse(message.data);
      const next = { ...emptyState, ...data.state } as AgentState;
      setState(next);
      const at = Date.now();
      setSamples(old => [...old, { at, clock: next.simulated_time, cycle: next.cycle, state: next.state,
        energy: next.energy, stress: next.stress, caffeine: next.caffeine_level,
        mean: next.neural?.mean_activity || 0, peak: next.neural?.peak_activity || 0 }].slice(-180));
      setMetrics(data.metrics);
      if (data.events?.length) setEvents((old: EventItem[]) => Array.from(new Map([...old, ...data.events].map(e => [e.sequence, e])).values()).sort((a, b) => a.sequence - b.sequence).slice(-80));
      if (at - lastSecondary > 5000) { lastSecondary = at; void refreshSecondary().catch(() => {}); }
      };
    };
    connect();
    return () => { stopped = true; clearTimeout(retry); socket?.close(); };
  }, []);

  const command = async (action: string) => {
    setBusy(true);
    try { await fetch("/api/commands", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({action})}); }
    finally { setBusy(false); }
  };

  const decide = async (draft: Draft, decision: "approved" | "rejected") => {
    setBusy(true);
    try {
      await fetch(`/api/drafts/${draft.draft_id}/decision`, {method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({decision, content_hash: draft.content_hash})});
      await refreshSecondary();
    } finally { setBusy(false); }
  };

  const timeline = useMemo(() => events.filter(e => e.event_type === "agent.state_transition").slice(-10), [events]);
  const latestDream = [...events].reverse().find(e => e.event_type === "sleep.dream_generated");
  const pending = drafts.filter(d => d.status === "pending");

  return <div className="app-shell">
    <header className="topbar">
      <div className="brand"><span className="brand-mark">IF</span><div><h1>InternFly</h1><p>CAREER OPERATIONS · MALE CNS CONTROL EXPERIMENT</p></div></div>
      <div className="status-cluster" aria-live="polite">
        <span className={`status-dot ${connected ? "online" : ""}`}/>
        <span>{state.stopped ? "STOPPED" : state.paused ? "PAUSED" : connected ? "RUNNING" : "RECONNECTING"}</span>
        <b>CYCLE {String(state.cycle).padStart(3, "0")}</b>
      </div>
      <div className="controls">
        <button disabled={busy} onClick={() => command(state.paused ? "resume" : "pause")}>{state.paused ? "Resume" : "Pause"}</button>
        <button disabled={busy} onClick={() => command("sleep-now")}>Sleep now</button>
        <button disabled={busy} className="danger" onClick={() => command("emergency-stop")}>Emergency stop</button>
      </div>
    </header>

    <div className="intro-bar"><div><span className="panel-kicker">A SMALL LIFE. A LONG EXPERIMENT.</span><h2>A day in the life of InternFly<span>Observe. Learn. Repeat.</span></h2></div><div className="experiment-clock"><strong>{state.simulated_time}</strong><span>SIMULATED LOCAL TIME</span></div></div>
    <div className="truth-banner"><b>{connectomeMap?.source_kind === "male-cns-derived" ? "MALE CNS v1.0" : "DEVELOPMENT FIXTURE"}</b><span>Simulated neural control · external software performs reasoning and tasks · fictional character</span></div>

    <main id="main" className="dashboard">
      <section className="story-stage" aria-label="Interactive InternFly story world and neural controller">
        <StoryWorld state={state}/>
        <BrainAtlas map={connectomeMap} activity={state.neural?.neuron_activity || []}/>
      </section>
      <TelemetryCharts samples={samples}/>
      <section className="panel activity-panel" aria-labelledby="activity-heading">
        <div className="panel-kicker">CURRENT ACTIVITY</div><h2 id="activity-heading">{state.state.replaceAll("_", " ")}</h2>
        <p className="hero-copy">{state.current_item || state.last_action}</p>
        <div className="mini-grid">
          <Metric label="Selected strategy" value={state.selected_strategy || "—"}/>
          <Metric label="Controller preference" value={state.neural?.selected_preference?.replaceAll("_", " ") || "—"}/>
          <Metric label="Operating mode" value={state.mode.toUpperCase()}/>
          <Metric label="Virtual time" value={state.simulated_time}/>
        </div>
        <div className="timeline" aria-label="Recent state transitions">
          {timeline.map(event => <div key={event.sequence}><i/><span>{String(event.payload.to || "").replaceAll("_", " ").toLowerCase()}</span><time>{new Date(event.occurred_at).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit", second: "2-digit"})}</time></div>)}
        </div>
      </section>
      <section className="panel health-panel" aria-labelledby="health-heading">
        <div className="panel-kicker">AGENT HEALTH · FICTIONAL</div><h2 id="health-heading">Internal weather</h2>
        <Gauge label="Energy" value={state.energy}/><Gauge label="Confidence" value={state.confidence} tone="green"/>
        <Gauge label="Stress" value={state.stress} tone="magenta"/><Gauge label="Curiosity" value={state.curiosity} tone="blue"/>
        <Gauge label="Dopamine / reward" value={state.dopamine} tone="green"/><Gauge label="Sleep debt" value={state.sleep_debt} tone="magenta"/>
        <Gauge label="Caffeine load" value={state.caffeine_level} tone="amber"/>
      </section>

      <section className="panel stats-panel" aria-labelledby="stats-heading">
        <div className="panel-kicker">LIFETIME TELEMETRY</div><h2 id="stats-heading">The long, strange résumé</h2>
        <div className="metric-grid">
          <Metric label="Cycles completed" value={metrics.cycles_completed || 0}/><Metric label="DSA solved" value={metrics.dsa_solved || 0}/>
          <Metric label="Success rate" value={metrics.dsa_success_rate || 0} suffix="%"/><Metric label="Listings" value={metrics.jobs_discovered || 0}/>
          <Metric label="Drafts awaiting" value={metrics.drafts_pending || 0}/><Metric label="Dreams" value={metrics.dreams_generated || 0}/>
          <Metric label="Fictional coffees" value={state.coffee_cups}/><Metric label="Sleep remaining" value={state.sleep_hours_remaining} suffix="h"/>
        </div>
        <div className="score-card"><span>CURRENT 10x DROSOPHILA SCORE</span><strong>{metrics.ten_x_drosophila_score || 0}</strong><small>Entertainment metric. Please do not use for compensation decisions.</small></div>
      </section>
      <NeuralPanel neural={state.neural || {}}/>

      <section className="panel funnel-panel" aria-labelledby="funnel-heading">
        <div className="panel-kicker">INTERNSHIP FUNNEL · FICTIONAL DATA</div><h2 id="funnel-heading">Applications without the spam</h2>
        <div className="funnel">
          {[['DISCOVERED', metrics.jobs_discovered], ['EVALUATED', metrics.jobs_evaluated], ['DRAFTED', metrics.drafts_created], ['APPROVED', metrics.drafts_approved]].map(([name, value]) =>
            <div key={String(name)}><span>{name}</span><i style={{width: `${Math.min(100, Number(value || 0) / Math.max(1, metrics.jobs_discovered || 0) * 100)}%`}}/><b>{value || 0}</b></div>)}
        </div>
        <div className="job-list">{jobs.slice(0, 3).map(job => <div key={job.job_id}><span><b>{job.company}</b>{job.title}</span><strong>{job.score ?? "—"}</strong></div>)}</div>
      </section>

      <section className="panel approval-panel" aria-labelledby="approval-heading">
        <div className="panel-kicker">HUMAN APPROVAL INBOX</div><h2 id="approval-heading">{pending.length} draft{pending.length === 1 ? "" : "s"} waiting</h2>
        {pending.length === 0 ? <p className="empty">No draft is begging for a grown-up right now.</p> : pending.map(draft =>
          <article className="draft" key={draft.draft_id}>
            <div><b>{draft.company}</b><span>{draft.title}</span></div>
            <p>{draft.content.cover_letter.slice(0, 150)}…</p>
            <small>Bound to content hash {draft.content_hash.slice(0, 10)}… · never auto-submitted</small>
            <div className="draft-actions"><button disabled={busy} onClick={() => decide(draft, "rejected")}>Reject</button><button disabled={busy} className="approve" onClick={() => decide(draft, "approved")}>Approve draft</button></div>
          </article>)}
      </section>

      <section className="panel journal-panel" aria-labelledby="journal-heading">
        <div className="panel-kicker provenance fictional">FICTIONAL ENTERTAINMENT</div><h2 id="journal-heading">Dream & journal feed</h2>
        {latestDream ? <blockquote>“{String(latestDream.payload.text)}”</blockquote> : <p className="empty">No dreams yet. The fly remains tragically well-rested.</p>}
        <div className="event-feed">{events.slice(-8).reverse().map(event => <div key={event.sequence}><time>{new Date(event.occurred_at).toLocaleTimeString()}</time><span>{event.event_type.replaceAll(".", " / ")}</span><em>{event.provenance_class.replaceAll("_", " ")}</em></div>)}</div>
      </section>
    </main>
    <footer><span>InternFly v0.1 · Offline-first demonstration</span><span>Biology inspires control topology; engineered software does the work.</span></footer>
  </div>;
}
