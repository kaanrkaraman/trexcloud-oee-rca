// client-side ports of trex.oee.recompute + W1 What-If, plus formatters & palette.
const clip = (x, lo, hi) => Math.max(lo, Math.min(hi, x))

export function recompute(c) {
  const sched = c.WorkTotal - c.PlannedStop
  const run = sched - c.UnPlannedStop
  const A = sched > 0 ? clip(run / sched, 0, 1) : 0
  const P = c.PlannedTime > 0 && c.ProductSum > 0 ? clip(c.WorkingTime / c.PlannedTime, 0, 1) : 0
  const Q = c.ProductSum > 0 ? clip((c.ProductSum - c.ScrapeSum) / c.ProductSum, 0, 1) : 1
  return { OEE: A * P * Q, A, P, Q }
}

// W1: cut the machine's unplanned downtime by pct
export function whatIfW1(components, pct) {
  const c0 = { ...components }
  const before = recompute(c0)
  const reduce = pct * c0.UnPlannedStop
  const c1 = { ...c0, UnPlannedStop: Math.max(0, c0.UnPlannedStop - reduce) }
  const after = recompute(c1)
  const recoveredH = reduce / 3.6e6
  const cycle = before.OEE >= 0 && c0.ProductSum > 0 ? c0.WorkingTime / c0.ProductSum : null
  const extraPieces = cycle ? recoveredH * 3.6e6 / cycle : 0
  return { before, after, recoveredH, extraPieces }
}

export function financials(recoveredH, extraPieces, a, valueAs = 'margin') {
  const marginGain = extraPieces * a.margin_per_piece
  const downSaving = recoveredH * a.downtime_cost_per_hour
  const timeValue = valueAs === 'margin' ? marginGain : downSaving
  const grossHorizon = timeValue * a.horizon_days
  const net = grossHorizon - a.intervention_cost
  const payback = timeValue > 0 ? a.intervention_cost / timeValue : null
  return { grossHorizon, net, payback, marginGain, downSaving }
}

export function pmFinancials(pm, effectiveness, downtimeCost, interventionCost) {
  const deployed = pm.deployed
  const components = deployed.oee.components_before
  const before = recompute(components)
  const preventedH = Math.min(
    deployed.caught_downtime_h * effectiveness,
    components.UnPlannedStop / 3.6e6,
  )
  const after = recompute({
    ...components,
    UnPlannedStop: Math.max(0, components.UnPlannedStop - preventedH * 3.6e6),
  })
  const gross = preventedH * downtimeCost
  const intervention = deployed.episodes * interventionCost
  const net = gross - intervention
  const roi = intervention > 0 ? net / intervention : null
  const factor = pm.assumptions.pm.annual_days / deployed.observed_days
  return {
    before, after, preventedH,
    deltaA: after.A - before.A,
    deltaOEE: after.OEE - before.OEE,
    observed: { gross, intervention, net, roi },
    annualized: {
      preventedH: preventedH * factor,
      gross: gross * factor,
      intervention: intervention * factor,
      net: net * factor,
      roi,
    },
  }
}

export const fmtPct = (x) => (x * 100).toFixed(1) + '%'
export const fmtInt = (x) => Math.round(x).toLocaleString('en-US')
export const fmtH = (x) => x.toFixed(0) + ' h'
export const fmtEur = (x) => new Intl.NumberFormat('tr-TR', {
  style: 'currency', currency: 'EUR', maximumFractionDigits: 0,
}).format(x)
export const tms = (s) => new Date(s.replace(' ', 'T') + 'Z').getTime()
export const hhmm = (ms) => {
  const d = new Date(ms)
  return d.toISOString().slice(5, 16).replace('T', ' ')
}

export const PAL = {
  green: '#35e08a', greenB: '#6df7af', red: '#ff5e5e', amber: '#ffc24d',
  blue: '#5bb7e6', gray: '#5a6b63', line: '#243531', text3: '#56655e',
}
export const oeeColor = (v) => (v >= 0.6 ? PAL.green : v >= 0.35 ? PAL.amber : PAL.red)
