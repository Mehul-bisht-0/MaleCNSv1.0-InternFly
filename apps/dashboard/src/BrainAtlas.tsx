import { useId, useMemo, useState } from "react";
import type { ConnectomeMap, ControllerNode } from "./BrainNetwork";

const COLORS: Record<string, string> = {
  modulatory: "#ffd166", "mushroom-body": "#99e06f", "central-complex": "#8ce7ff",
  descending: "#ff769f", "optic-lobe": "#54d9ff", olfactory: "#ff9b73",
  "superior-protocerebrum": "#be9cff", "lateral-complex": "#e682d8", ventrolateral: "#729fff",
  gnathal: "#f7dc75", "ventral-nerve-cord": "#ff756f", ascending: "#68e6bd",
};

// Engineered display coordinates only. They organize annotated populations into a
// fly-CNS-shaped projection; they are not Male CNS skeleton coordinates.
const CENTERS: Record<string, [number, number]> = {
  "superior-protocerebrum": [270, 92], "mushroom-body": [270, 118],
  "central-complex": [270, 172], "lateral-complex": [270, 199],
  "optic-lobe": [270, 173], ventrolateral: [270, 222], modulatory: [270, 225],
  olfactory: [270, 244], gnathal: [270, 258], ascending: [284, 276],
  descending: [270, 286], "ventral-nerve-cord": [270, 333],
};

const regionOf = (node: ControllerNode) => node.super_segment || node.region || "unassigned";
const readable = (name: string) => name.replaceAll("-", " ").replace(/\b\w/g, c => c.toUpperCase());
const hash = (value: string) => Array.from(value).reduce((n, c) => (n * 31 + c.charCodeAt(0)) >>> 0, 2166136261);
type Point = { x: number; y: number };
type VisualUnit = Point & { id: number; parent: number; phase: number };
type VisualLink = { source: number; target: number; parent: number };
const curve = (from: Point, to: Point, bend: number) => {
  const mx = (from.x + to.x) / 2, my = (from.y + to.y) / 2;
  const dx = to.x - from.x, dy = to.y - from.y, length = Math.max(1, Math.hypot(dx, dy));
  return `M${from.x.toFixed(1)},${from.y.toFixed(1)} Q${(mx - dy / length * bend).toFixed(1)},${(my + dx / length * bend).toFixed(1)} ${to.x.toFixed(1)},${to.y.toFixed(1)}`;
};

export default function BrainAtlas({ map, activity }: { map: ConnectomeMap | null; activity: number[] }) {
  const prefix = useId().replaceAll(":", "");
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<number | null>(null);
  const [showEdges, setShowEdges] = useState(true);
  const [showActivity, setShowActivity] = useState(true);
  const [showPopulation, setShowPopulation] = useState(true);
  const groups = useMemo(() => {
    const result = new Map<string, number[]>();
    map?.neurons.forEach((node, index) => result.set(regionOf(node), [...(result.get(regionOf(node)) || []), index]));
    return Array.from(result, ([name, indices]) => ({ name, indices, color: COLORS[name] || "#cad8df" }));
  }, [map]);
  const positions = useMemo(() => map?.neurons.map((node, index) => {
    const region = regionOf(node), group = groups.find(g => g.name === region)!;
    const ordinal = group.indices.indexOf(index), side = node.hemisphere?.toLowerCase();
    const direction = side === "left" || side === "l" ? -1 : side === "right" || side === "r" ? 1 : (ordinal % 2 ? 1 : -1);
    const base = CENTERS[region] || [270, 205];
    const lateral = region === "optic-lobe" ? 172 : region === "olfactory" ? 103 : region === "lateral-complex" || region === "ventrolateral" ? 75 : 42;
    const seed = hash(String(node.body_id)), angle = (seed % 6283) / 1000;
    const density = 7 + Math.sqrt((ordinal + .65) / Math.max(1, group.indices.length)) * (region === "optic-lobe" ? 45 : 31);
    return { x: base[0] + direction * lateral + Math.cos(angle) * density, y: base[1] + Math.sin(angle) * density * .58 };
  }) || [], [map, groups]);
  const visualField = useMemo(() => {
    const sourceCount = map?.neurons.length || 0;
    if (!sourceCount) return { units: [] as VisualUnit[], links: [] as VisualLink[] };
    const unitsPerSource = Math.max(2, Math.min(64, Math.floor(1024 / sourceCount)));
    const units: VisualUnit[] = [];
    for (let parent = 0; parent < sourceCount; parent += 1) {
      const anchor = positions[parent];
      for (let ordinal = 0; ordinal < unitsPerSource; ordinal += 1) {
        const seed = hash(`${map!.neurons[parent].body_id}:unit:${ordinal}`);
        const angle = (seed % 6283) / 1000, radial = Math.sqrt(((seed >>> 9) % 1000) / 1000);
        const inCord = seed % 13 === 0;
        const fieldX = inCord ? 270 + Math.cos(angle) * radial * 18 : 270 + Math.cos(angle) * radial * 226;
        const fieldY = inCord ? 274 + ((seed >>> 19) % 1000) / 1000 * 94 : 166 + Math.sin(angle) * radial * 132;
        // A light attraction to the source anchor preserves population identity while
        // allowing the numerical units to occupy the whole observable CNS envelope.
        units.push({ id: units.length, parent, phase: ((seed >>> 4) % 1000) / 1000,
          x: fieldX * .76 + anchor.x * .24, y: fieldY * .76 + anchor.y * .24 });
      }
    }
    const links: VisualLink[] = [];
    for (let parent = 0; parent < sourceCount; parent += 1) {
      const start = parent * unitsPerSource;
      for (let ordinal = 0; ordinal < unitsPerSource; ordinal += 1) {
        links.push({ source: start + ordinal, target: start + (ordinal + 1) % unitsPerSource, parent });
        if (ordinal % 4 === 0 && unitsPerSource > 8) links.push({ source: start + ordinal, target: start + (ordinal + 7) % unitsPerSource, parent });
      }
    }
    map?.edges.forEach((edge, edgeIndex) => {
      for (let bridge = 0; bridge < 3; bridge += 1) links.push({
        source: edge.source * unitsPerSource + ((edgeIndex * 7 + bridge * 11) % unitsPerSource),
        target: edge.target * unitsPerSource + ((edgeIndex * 13 + bridge * 17) % unitsPerSource), parent: edge.source,
      });
    });
    return { units, links };
  }, [map, positions]);
  const node = selectedNode !== null ? map?.neurons[selectedNode] : undefined;
  const mean = activity.length ? activity.reduce((sum, n) => sum + Math.abs(n), 0) / activity.length : 0;
  const real = map?.source_kind === "male-cns-derived";
  const unitActivity = (unit: VisualUnit) => Math.min(1, Math.abs(activity[unit.parent] || 0) * (.5 + unit.phase * .65));
  const renderedUnits = useMemo(() => {
    const stride = Math.max(1, Math.ceil(visualField.units.length / 320));
    return visualField.units.filter((_, index) => index % stride === 0);
  }, [visualField]);
  const renderedLinks = useMemo(() => {
    const stride = Math.max(1, Math.ceil(visualField.links.length / 420));
    return visualField.links.filter((_, index) => index % stride === 0);
  }, [visualField]);
  const { firingUnits, distribution } = useMemo(() => {
    const buckets = Array.from({ length: 10 }, () => 0);
    let firing = 0;
    visualField.units.forEach(unit => {
      const value = Math.min(1, Math.abs(activity[unit.parent] || 0) * (.5 + unit.phase * .65));
      if (value >= .2) firing += 1;
      buckets[Math.min(9, Math.floor(value * 10))] += 1;
    });
    return { firingUnits: firing, distribution: buckets };
  }, [activity, visualField]);
  const distributionPeak = Math.max(1, ...distribution);
  const rasterUnits = visualField.units.filter((_, index) => index % Math.max(1, Math.floor(visualField.units.length / 48)) === 0).slice(0, 48);

  return <aside className="brain-sidebar" aria-labelledby="brain-heading">
    <div className="brain-header"><div><div className="panel-kicker">02 / NEURAL OBSERVATORY</div><h2 id="brain-heading">Fly CNS signal map</h2></div><span className="live-pill"><i/> LIVE SIM</span></div>
    <div className="brain-summary"><div><strong>{map?.neurons.length || 0}</strong><span>source nodes</span></div><div><strong>{visualField.units.length.toLocaleString()}</strong><span>simulated units</span></div><div><strong>{renderedLinks.length.toLocaleString()}</strong><span>rendered paths</span></div><div><strong>{firingUnits.toLocaleString()}</strong><span>units firing</span></div></div>
    <div className="brain-map-wrap">
      <div className="map-caption"><span>NUMERICAL POPULATION FIELD · {map?.neurons.length || 0} SOURCES / {map?.edges.length || 0} BIOLOGICAL EDGES</span><b>t+{String(activity.length).padStart(3, "0")}</b></div>
      <svg className={`brain-map ${showActivity ? "activity-on" : ""}`} viewBox="0 0 540 390" aria-label="Interactive fly CNS region projection. Select a neuron to inspect its identifier and simulated activity.">
        <defs>
          <radialGradient id={`${prefix}-field`} cx="50%" cy="42%" r="65%"><stop stopColor="#513b2b" stopOpacity=".82"/><stop offset=".55" stopColor="#221e21" stopOpacity=".84"/><stop offset="1" stopColor="#090d12"/></radialGradient>
          <radialGradient id={`${prefix}-tissue`} cx="48%" cy="42%"><stop stopColor="#d6a363" stopOpacity=".13"/><stop offset=".7" stopColor="#9f6e4e" stopOpacity=".055"/><stop offset="1" stopColor="#101821" stopOpacity=".02"/></radialGradient>
          <linearGradient id={`${prefix}-scan`} x1="0" y1="0" x2="0" y2="1"><stop stopColor="#fff" stopOpacity="0"/><stop offset=".5" stopColor="#ffd89a" stopOpacity=".13"/><stop offset="1" stopColor="#fff" stopOpacity="0"/></linearGradient>
          <filter id={`${prefix}-soft`} x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="9"/></filter>
          <filter id={`${prefix}-glow`} x="-160%" y="-160%" width="420%" height="420%"><feGaussianBlur stdDeviation="2.4" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
          <filter id={`${prefix}-hot`} x="-250%" y="-250%" width="600%" height="600%"><feGaussianBlur stdDeviation="5" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
          <clipPath id={`${prefix}-brain-clip`}><path d="M268 42 C214 16 143 30 111 82 C65 66 20 107 26 169 C31 220 66 251 112 247 C137 278 179 287 218 268 C229 281 241 290 252 295 L252 348 C251 370 262 380 270 380 C280 380 291 370 288 347 L287 295 C301 288 313 278 322 266 C361 286 404 275 428 245 C475 251 509 218 514 168 C520 108 477 66 431 82 C398 30 327 16 272 42 Z"/></clipPath>
        </defs>
        <rect width="540" height="390" fill={`url(#${prefix}-field)`}/><ellipse cx="270" cy="184" rx="238" ry="165" fill="#d8a469" opacity=".07" filter={`url(#${prefix}-soft)`}/>
        <g className="brain-anatomy" fill={`url(#${prefix}-tissue)`} stroke="#d8aa78" strokeOpacity=".35" strokeWidth="1.1">
          <path d="M268 42 C214 16 143 30 111 82 C65 66 20 107 26 169 C31 220 66 251 112 247 C137 278 179 287 218 268 C229 281 241 290 252 295 L252 348 C251 370 262 380 270 380 C280 380 291 370 288 347 L287 295 C301 288 313 278 322 266 C361 286 404 275 428 245 C475 251 509 218 514 168 C520 108 477 66 431 82 C398 30 327 16 272 42 Z"/>
          <path d="M111 82 C79 118 73 191 112 247 M431 82 C462 118 467 191 428 245 M164 44 C119 91 120 191 158 262 M377 44 C422 91 421 190 383 261" fill="none"/>
          <path d="M218 68 C236 51 250 65 249 94 L240 149 M322 68 C304 51 290 65 291 94 L300 149" fill="none" strokeOpacity=".55"/>
          <ellipse cx="270" cy="173" rx="46" ry="22"/><ellipse cx="174" cy="232" rx="30" ry="19"/><ellipse cx="366" cy="232" rx="30" ry="19"/>
        </g>
        <g className="atlas-guides" clipPath={`url(#${prefix}-brain-clip)`}>{[0,1,2,3,4,5].map(i => <path key={i} d={`M${42 + i * 22},${87 + i * 23} C${170 + i * 14},${30 + i * 20} ${360 - i * 12},${320 - i * 17} ${501 - i * 16},${121 + i * 19}`} fill="none" stroke="#ffe0aa" strokeOpacity=".04" strokeWidth=".7"/>)}</g>
        {showPopulation && <g className="micro-connectome" clipPath={`url(#${prefix}-brain-clip)`}>
          <g className="micro-links">{renderedLinks.map((link, index) => {
            const from = visualField.units[link.source], to = visualField.units[link.target];
            const signal = from ? unitActivity(from) : 0;
            const region = map ? regionOf(map.neurons[link.parent]) : "unassigned";
            const visible = !selectedRegion || region === selectedRegion;
            return from && to ? <line key={index} x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke={COLORS[region] || "#cbdde2"} strokeOpacity={visible ? .055 + signal * .18 : .008} strokeWidth={signal > .5 ? .48 : .3}/> : null;
          })}</g>
          <g className="micro-units">{renderedUnits.map(unit => {
            const signal = unitActivity(unit), region = map ? regionOf(map.neurons[unit.parent]) : "unassigned";
            const visible = !selectedRegion || region === selectedRegion;
            return <circle key={unit.id} className={`micro-unit ${signal >= .2 && showActivity ? "micro-active" : ""}`} cx={unit.x} cy={unit.y} r={signal > .65 ? 1.3 : .88} fill={COLORS[region] || "#d9e6e8"} opacity={visible ? .38 + signal * .6 : .025} style={{ animationDelay: `${-(unit.phase * 2.7).toFixed(2)}s` }}/>
          })}</g>
        </g>}
        {showEdges && map?.edges.map((edge, i) => {
          const from = positions[edge.source], to = positions[edge.target]; if (!from || !to) return null;
          const sourceRegion = regionOf(map.neurons[edge.source]), targetRegion = regionOf(map.neurons[edge.target]);
          const signal = Math.max(Math.abs(activity[edge.source] || 0), Math.abs(activity[edge.target] || 0));
          const emphasized = selectedNode !== null ? edge.source === selectedNode || edge.target === selectedNode : !selectedRegion || sourceRegion === selectedRegion || targetRegion === selectedRegion;
          const color = edge.weight < 0 ? "#ff789e" : COLORS[sourceRegion] || "#d9eced";
          const d = curve(from, to, ((hash(`${edge.source}:${edge.target}`) % 49) - 24) * .72);
          return <g key={`${edge.source}-${edge.target}-${i}`} className={signal > .2 && emphasized ? "signal-path" : undefined} opacity={emphasized ? 1 : .055}>
            <path d={d} fill="none" stroke={color} strokeWidth={emphasized ? .55 + Math.min(1.4, Math.abs(edge.weight) * .08) : .35} strokeOpacity={.17 + signal * .48}/><path d={d} fill="none" stroke="#fff6da" strokeWidth=".28" strokeOpacity={emphasized ? .1 + signal * .33 : 0}/>
            {showActivity && signal > .12 && emphasized && <circle r={signal > .55 ? 1.8 : 1.15} fill="#fff4bd" filter={`url(#${prefix}-glow)`}><animateMotion dur={`${(2.5 - Math.min(1.6, signal * 1.8)).toFixed(2)}s`} repeatCount="indefinite" path={d}/></circle>}
          </g>;
        })}
        {map?.neurons.map((n, i) => {
          const pos = positions[i], amplitude = Math.abs(activity[i] || 0), color = COLORS[regionOf(n)] || "#d6e4e8", dimmed = Boolean(selectedRegion && selectedRegion !== regionOf(n));
          const radius = map.neurons.length < 60 ? 3.15 : 1.65;
          return <g key={n.body_id} role="button" tabIndex={0} aria-label={`Neuron ${n.body_id}, ${readable(regionOf(n))}, activity ${amplitude.toFixed(3)}`} onClick={() => setSelectedNode(i)} onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSelectedNode(i); } }} opacity={dimmed ? .12 : 1} className={`neuron-target ${amplitude >= .2 ? "is-active" : ""}`}>
            <title>{n.body_id} · {n.type || readable(regionOf(n))} · |a| {amplitude.toFixed(3)}</title><circle cx={pos.x} cy={pos.y} r={8 + amplitude * 16} fill={color} opacity={showActivity ? .045 + amplitude * .17 : .05} filter={`url(#${prefix}-soft)`}/>
            {showActivity && amplitude >= .2 && <circle className="neuron-pulse" cx={pos.x} cy={pos.y} r={radius + 4 + amplitude * 5} fill="none" stroke={color} strokeWidth=".55" opacity=".6"/>}<circle cx={pos.x} cy={pos.y} r={radius + amplitude * 2.7} fill={color} stroke={selectedNode === i ? "#fffde5" : "#170f12"} strokeWidth={selectedNode === i ? 1.8 : .7} filter={amplitude > .3 && showActivity ? `url(#${prefix}-hot)` : undefined}/><circle cx={pos.x} cy={pos.y} r="8" fill="transparent"/>
          </g>;
        })}
        <g className="brain-orientation" fontFamily="ui-monospace, monospace"><text x="20" y="28">LEFT</text><text x="480" y="28">RIGHT</text><path d="M270 22 V370"/><text x="18" y="371">SCHEMATIC ENVELOPE · DATA NODES + EDGES</text></g><rect className="brain-scanline" x="0" y="0" width="540" height="54" fill={`url(#${prefix}-scan)`}/>
      </svg>
      <div className="brain-map-key" aria-label="Region color key">{groups.slice(0, 6).map(group => <span key={group.name}><i style={{ background: group.color }}/>{readable(group.name)}</span>)}</div>
      <div className="map-toolbar"><label><input type="checkbox" checked={showPopulation} onChange={e => setShowPopulation(e.target.checked)}/> Population</label><label><input type="checkbox" checked={showEdges} onChange={e => setShowEdges(e.target.checked)}/> Source edges</label><label><input type="checkbox" checked={showActivity} onChange={e => setShowActivity(e.target.checked)}/> Signals</label><button onClick={() => { setSelectedNode(null); setSelectedRegion(null); }}>Reset</button></div>
    </div>
    <div className="brain-detail-grid">
      <div className="region-list" aria-label="Filter neural regions">{groups.map(({ name, indices, color }) => {
        const value = indices.reduce((sum, i) => sum + Math.abs(activity[i] || 0), 0) / indices.length;
        return <button key={name} className={selectedRegion === name ? "selected" : ""} aria-pressed={selectedRegion === name} onClick={() => { setSelectedRegion(selectedRegion === name ? null : name); setSelectedNode(null); }}><i style={{ background: color }}/><span>{readable(name)}<small>{indices.length} neurons</small></span><span className="region-bar"><i style={{ width: `${Math.min(100, value * 100)}%`, background: color }}/></span><b>{value.toFixed(2)}</b></button>;
      })}</div>
      <div className="node-inspector" aria-live="polite"><span>{node ? `NEURON ${node.body_id}` : "MEAN |ACTIVITY|"}</span><strong>{node && selectedNode !== null ? Math.abs(activity[selectedNode] || 0).toFixed(3) : mean.toFixed(3)} <small>a.u.</small></strong><div className="inspector-wave" aria-hidden="true">{[.2,.45,.28,.7,.38,.9,.52,.32,.66,.3,.48,.22].map((v, i) => <i key={i} style={{ height: `${4 + v * (showActivity ? 30 + mean * 20 : 12)}px` }}/>)}</div><p>{node ? `${node.type || readable(regionOf(node))} · ${node.transmitter || "transmitter unavailable"} · ${node.hemisphere || "side unassigned"}` : "Select a neuron or population to inspect the latest simulated controller sample."}</p></div>
    </div>
    <div className="population-graphs">
      <section className="population-graph" aria-label={`Numerical population raster for ${visualField.units.length} simulated units`}>
        <header><span>POPULATION FIRING RASTER</span><b>{firingUnits.toLocaleString()} / {visualField.units.length.toLocaleString()}</b></header>
        <svg viewBox="0 0 300 92" role="img" aria-label="Simulated firing raster derived from current source-node activity">
          <g className="raster-grid">{[0,1,2,3,4].map(i => <line key={i} x1={i * 75} y1="0" x2={i * 75} y2="92"/>)}</g>
          {rasterUnits.map((unit, row) => {
            const signal = unitActivity(unit), color = map ? COLORS[regionOf(map.neurons[unit.parent])] || "#dce7ea" : "#dce7ea";
            const ticks = Math.max(1, Math.round(signal * 12));
            const d = Array.from({ length: ticks }, (_, tick) => {
              const x = ((hash(`${unit.id}:${tick}`) % 2860) / 10) + 7;
              const y = 3 + row * (86 / Math.max(1, rasterUnits.length - 1));
              return `M${x.toFixed(1)},${(y - 1.2).toFixed(1)}v2.4`;
            }).join(" ");
            return <path key={unit.id} d={d} stroke={color} strokeWidth={signal > .55 ? 1.5 : 1} opacity={.35 + signal * .65}/>;
          })}
        </svg>
        <footer><span>−2.0 s</span><span>NOW</span></footer>
      </section>
      <section className="population-graph distribution-graph" aria-label="Simulated unit activity distribution">
        <header><span>UNIT ACTIVITY DISTRIBUTION</span><b>μ {mean.toFixed(3)}</b></header>
        <div className="distribution-bars">{distribution.map((count, bucket) => <i key={bucket} title={`${(bucket / 10).toFixed(1)}–${((bucket + 1) / 10).toFixed(1)}: ${count} units`} style={{ height: `${Math.max(3, 4 + count / distributionPeak * 76)}px` }}><span>{count}</span></i>)}</div>
        <footer><span>QUIET 0.0</span><span>ACTIVE 1.0</span></footer>
      </section>
    </div>
    <div className="population-disclaimer"><b>ENGINEERED NUMERICAL EXPANSION</b><span>{visualField.units.length.toLocaleString()} visual simulation units inherit dynamics from {map?.neurons.length || 0} source nodes. They increase observable density; they are not additional reconstructed Male CNS neurons.</span></div>
    <details className="brain-provenance"><summary><i className={real ? "real" : "fixture"}/>{real ? "Male CNS v1.0 · imported connectivity subset" : `Development fixture · ${map?.neurons.length || 0} synthetic nodes`}</summary><p>{map?.notice || "Loading source metadata."} The envelope, placement, glow and moving signal particles are engineered visualization. They are not measured neuron coordinates or recorded biological firing.</p><code>{map?.dataset}</code></details>
  </aside>;
}
