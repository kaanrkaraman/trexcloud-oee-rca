import React from 'react'
import {
  ResponsiveContainer, ComposedChart, BarChart, LineChart, Bar, Line, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, Cell,
} from 'recharts'
import { PAL, fmtPct, tms, hhmm } from './lib.js'

export const Panel = ({ title, icon, children, className = '', cap, cls = '' }) => (
  <div className={`panel ${cls}`}>
    {title && <div className="ptitle"><span className="i">{icon}</span>{title}</div>}
    <div className={className}>{children}</div>
    {cap && <div className="cap" dangerouslySetInnerHTML={{ __html: cap }} />}
  </div>
)

export const Stat = ({ label, value, delta, plain }) => (
  <div className="stat">
    <div className={`v ${plain ? 'plain' : ''}`}>{value}</div>
    <div className="l">{label}</div>
    {delta != null && <div className={`d ${delta >= 0 ? 'up' : 'down'}`}>
      {delta >= 0 ? '▲' : '▼'} {fmtPct(Math.abs(delta))}</div>}
  </div>
)

export const Tag = ({ children, kind = '' }) => <span className={`tag ${kind}`}>{children}</span>

const axis = { stroke: PAL.line, tick: { fill: PAL.text3 } }
const dateFmt = (v) => hhmm(v).slice(0, 5)

function RiskTip({ active, payload }) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return <div className="tt"><div className="tl">{hhmm(p.x)}</div>
    <div style={{ color: PAL.greenB }}>risk {(p.r * 100).toFixed(0)}%</div></div>
}

export function RiskChart({ points, threshold, stops, episode }) {
  const data = points.map((p) => ({ x: tms(p.t), r: p.r }))
  const stopData = (stops || []).map((s) => ({ x: tms(s), y: threshold }))
  return (
    <ResponsiveContainer width="100%" height={230}>
      <ComposedChart data={data} margin={{ top: 8, right: 10, bottom: 4, left: -18 }}>
        <CartesianGrid stroke={PAL.line} strokeDasharray="2 4" vertical={false} />
        <XAxis dataKey="x" type="number" domain={['dataMin', 'dataMax']} {...axis}
          tickFormatter={dateFmt} minTickGap={48} />
        <YAxis domain={[0, 1]} {...axis} tickFormatter={(v) => v.toFixed(1)} />
        <Tooltip content={<RiskTip />} />
        {episode && <ReferenceLine x={tms(episode.start)} stroke={PAL.amber} strokeDasharray="3 3" />}
        <ReferenceLine y={threshold} stroke={PAL.red} strokeDasharray="4 4"
          label={{ value: 'alarm eşiği', fill: PAL.red, fontSize: 10, position: 'insideTopRight' }} />
        <Line type="monotone" dataKey="r" stroke={PAL.green} strokeWidth={1.6} dot={false}
          isAnimationActive={false} />
        <Scatter data={stopData} dataKey="y" fill={PAL.red} shape="cross" isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  )
}

export function ParetoChart({ rows }) {
  const data = rows.map((r) => ({
    label: `${r.machine.replace('Makine', 'M')} · ${r.reason}`.slice(0, 24),
    hours: r.hours, kind: r.kind,
  }))
  return (
    <ResponsiveContainer width="100%" height={Math.max(220, data.length * 26)}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 8 }}>
        <CartesianGrid stroke={PAL.line} horizontal={false} />
        <XAxis type="number" {...axis} tickFormatter={(v) => v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v} />
        <YAxis type="category" dataKey="label" {...axis} width={150}
          tick={{ fill: PAL.text3, fontSize: 10 }} />
        <Tooltip cursor={{ fill: 'rgba(255,255,255,.03)' }}
          formatter={(v) => [Math.round(v) + ' saat', 'duruş']} />
        <Bar dataKey="hours" radius={[0, 2, 2, 0]} isAnimationActive={false}>
          {data.map((d, i) => <Cell key={i} fill={d.kind === 'connectivity' ? PAL.gray : PAL.red} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

export function OeeBars({ before, after }) {
  const data = ['OEE', 'A', 'P', 'Q'].map((k) => ({ k, Önce: before[k], Sonra: after[k] }))
  return (
    <ResponsiveContainer width="100%" height={210}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: -22 }} barGap={2}>
        <CartesianGrid stroke={PAL.line} vertical={false} />
        <XAxis dataKey="k" {...axis} />
        <YAxis domain={[0, 1]} {...axis} tickFormatter={(v) => v.toFixed(1)} />
        <Tooltip formatter={(v) => fmtPct(v)} cursor={{ fill: 'rgba(255,255,255,.03)' }} />
        <Bar dataKey="Önce" fill={PAL.gray} radius={[2, 2, 0, 0]} isAnimationActive={false} />
        <Bar dataKey="Sonra" fill={PAL.green} radius={[2, 2, 0, 0]} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  )
}

export function TelemetrySpark({ role, points }) {
  const data = points.map((p, i) => ({ i, v: p.v }))
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', alignItems: 'center', gap: 10 }}>
      <span className="tag dim">{role}</span>
      <ResponsiveContainer width="100%" height={42}>
        <LineChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <Line type="monotone" dataKey="v" stroke={PAL.blue} strokeWidth={1.3} dot={false}
            isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export function DeviationBars({ dev }) {
  if (!dev || !dev.length) return null
  const max = Math.max(...dev.map((d) => d.dev), 1)
  return (
    <div className="devbars">
      {dev.map((d, i) => (
        <div className="devrow" key={i}>
          <span className="tag dim">{d.role}</span>
          <div className="devtrack">
            <i style={{ width: `${Math.min(100, (d.dev / max) * 100)}%`,
              background: d.dir === 'down' ? PAL.red : PAL.blue }} />
          </div>
          <span className="devval" style={{ color: d.dir === 'down' ? PAL.red : PAL.blue }}>
            {d.dir === 'down' ? '▼' : '▲'} {d.dev.toFixed(1)}σ
          </span>
        </div>
      ))}
    </div>
  )
}

export function SyncBars({ sync }) {
  const data = [
    { k: 'Gözlemlenen', v: sync.observed_co_stop_hours, c: PAL.green },
    { k: 'Beklenen (saat-içi)', v: sync.daily?.exp, c: PAL.amber },
    { k: 'Beklenen (rastgele)', v: sync.free?.exp, c: PAL.gray },
  ]
  return (
    <ResponsiveContainer width="100%" height={170}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: -16 }}>
        <CartesianGrid stroke={PAL.line} vertical={false} />
        <XAxis dataKey="k" {...axis} tick={{ fill: PAL.text3, fontSize: 9.5 }} />
        <YAxis {...axis} />
        <Tooltip formatter={(v) => [Math.round(v) + ' saat']} cursor={{ fill: 'rgba(255,255,255,.03)' }} />
        <Bar dataKey="v" radius={[2, 2, 0, 0]} isAnimationActive={false}>
          {data.map((d, i) => <Cell key={i} fill={d.c} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
