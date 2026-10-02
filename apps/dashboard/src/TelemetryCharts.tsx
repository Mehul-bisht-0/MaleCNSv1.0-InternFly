import { useState } from "react";

export type TelemetrySample = { at: number; clock: string; cycle: number; state: string; energy: number; stress: number; caffeine: number; mean: number; peak: number };
type Series = { key: "energy" | "stress" | "caffeine" | "mean" | "peak"; label: string; color: string; dashed?: boolean };
const physiology: Series[] = [{ key: "energy", label: "Energy", color: "#aee49a" }, { key: "stress", label: "Stress", color: "#f098b6", dashed: true }, { key: "caffeine", label: "Caffeine", color: "#f7c47a" }];
const neural: Series[] = [{ key: "mean", label: "Mean |activity|", color: "#7adce4" }, { key: "peak", label: "Peak |activity|", color: "#b8a6ef", dashed: true }];

function Trace({ samples: incoming, series, max, title, subtitle }: { samples: TelemetrySample[]; series: Series[]; max: number; title: string; subtitle: string }) {
  const [frozen, setFrozen] = useState<TelemetrySample[] | null>(null);
  const samples = frozen || incoming;
  const [selected, setSelected] = useState<number | null>(null);
  const [hidden, setHidden] = useState<string[]>([]);
  const start = samples[0]?.at || 0, end = samples.at(-1)?.at || 0;
  const duration = Math.max(1, (end - start) / 1000);
  const view = selected === null ? samples.at(-1) : samples[Math.min(selected, samples.length - 1)];
  const x = (at: number) => 42 + ((at - start) / 1000) / duration * 480;
  const y = (value: number) => 170 - Math.max(0, Math.min(max, value)) / max * 140;
  const path = (key: Series["key"]) => samples.map((s, i) => !i || s.at - samples[i - 1].at > 5000
    ? `M${x(s.at).toFixed(2)},${y(s[key]).toFixed(2)}`
    : `H${x(s.at).toFixed(2)} V${y(s[key]).toFixed(2)}`).join(" ");
  const sleep = samples.map((s, i) => ["SLEEP", "DREAM", "CONSOLIDATE_MEMORY"].includes(s.state) && i < samples.length - 1 && samples[i + 1].at - s.at < 5000 ? <rect key={s.at} x={x(s.at)} y="30" width={Math.max(1, x(samples[i + 1].at) - x(s.at))} height="140" fill="#9c99d5" opacity=".065"/> : null);
  return <section className="panel trace-panel">
    <div className="chart-heading"><div><div className="panel-kicker">LIVE TIME SERIES</div><h2>{title}</h2></div><span className="chart-count">{samples.length} samples</span></div>
    <p className="chart-subtitle">{subtitle}</p>
    <div className="chart-legend">{series.map(s => <button key={s.key} aria-pressed={!hidden.includes(s.key)} onClick={() => setHidden(old => old.includes(s.key) ? old.filter(k => k !== s.key) : [...old, s.key])} style={{ opacity: hidden.includes(s.key) ? .4 : 1 }}><i style={{ borderColor: s.color, borderTopStyle: s.dashed ? "dashed" : "solid" }}/>{s.label}<strong>{view ? view[s.key].toFixed(max === 1 ? 3 : 0) : "—"}</strong></button>)}</div>
    <svg viewBox="0 0 550 208" className="trace-chart" role="img" aria-label={`${title}. ${samples.length} live samples over ${Math.round(duration)} seconds. Latest ${series.map(s => `${s.label} ${view?.[s.key].toFixed(2) ?? "unavailable"}`).join(", ")}.`}>
      <text x="42" y="15" className="axis-label">{max === 1 ? "Normalized activity · a.u." : "Fictional state · 0–100"}</text>
      {sleep}
      {[0, .25, .5, .75, 1].map(t => <g key={t}><path d={`M42 ${y(t * max)} H522`} className="chart-grid"/><text x="30" y={y(t * max) + 4} textAnchor="end" className="axis-label">{max === 1 ? t.toFixed(2) : t * max}</text></g>)}
      {series.filter(s => !hidden.includes(s.key)).map(s => <path key={s.key} d={path(s.key)} fill="none" stroke={s.color} strokeWidth="2.4" strokeDasharray={s.dashed ? "6 4" : undefined} strokeLinecap="round" strokeLinejoin="round"/>)}
      {view && <g><path d={`M${x(view.at)} 30 V170`} stroke="#c1ccdc" opacity=".35" strokeDasharray="3 4"/>{series.filter(s => !hidden.includes(s.key)).map(s => <circle key={s.key} cx={x(view.at)} cy={y(view[s.key])} r="3.4" fill={s.color} stroke="#0f1825" strokeWidth="1.5"/>)}</g>}
      {[0, .5, 1].map(t => <text key={t} x={42 + t * 480} y="195" textAnchor={t === 0 ? "start" : t === 1 ? "end" : "middle"} className="axis-label">{Math.round(t * duration)}s</text>)}
    </svg>
    {samples.length < 2 && <p className="chart-wait">Recording the first samples…</p>}
    <div className="chart-scrubber"><label>{frozen ? "Inspecting" : "Inspect sample"}<input aria-label={`Inspect ${title} sample`} type="range" min="0" max={Math.max(0, samples.length - 1)} value={selected === null ? Math.max(0, samples.length - 1) : Math.min(selected, samples.length - 1)} onChange={e => { if (!frozen) setFrozen([...incoming]); setSelected(Number(e.target.value)); }}/></label><button onClick={() => { setSelected(null); setFrozen(null); }} aria-pressed={selected === null}>Live</button></div>
    <p className="chart-footnote">{view ? `${view.clock} simulated · cycle ${view.cycle} · ${view.state.replaceAll("_", " ").toLowerCase()}` : "Waiting for stream"} <span>Shading = sleep</span></p>
  </section>;
}

export default function TelemetryCharts({ samples }: { samples: TelemetrySample[] }) {
  return <div className="telemetry-charts"><Trace samples={samples} series={physiology} max={100} title="Energy, stress & caffeine" subtitle="Follow the coffee boost, accumulated stress, and recovery during sleep."/><Trace samples={samples} series={neural} max={1} title="Controller activity" subtitle="Latest controller readings; held between decision steps. No synthetic waveform."/><p className="session-caption">Current browser session · up to 180 readings · x-axis shows elapsed real seconds · disconnections leave gaps · refresh starts a new recording.</p></div>;
}
