import React, { useMemo, useState, useEffect } from 'react'
import { Panel, Stat, Tag, RiskChart, ParetoChart, OeeBars, SyncBars, DeviationBars } from './components.jsx'
import { whatIfW1, financials, fmtPct, fmtInt, fmtH, fmtEur, oeeColor } from './lib.js'

const FANUC = ['Makine 1', 'Makine 2', 'Makine 3', 'Makine 5', 'Makine 9']
const NAV = [
  { id: 'predict', label: 'Kestirimci Bakım', icon: '◈' },
  { id: 'cross', label: 'Senkron Duruşlar', icon: '⊞' },
  { id: 'overview', label: 'Filo & OEE', icon: '▦' },
]
const ASSUM = { margin_per_piece: 12, downtime_cost_per_hour: 80, intervention_cost: 300, horizon_days: 30, currency: 'EUR' }

export default function App() {
  const [data, setData] = useState(null)
  const q = new URLSearchParams(window.location.search).get('view')
  const [view, setView] = useState(NAV.some((n) => n.id === q) ? q : 'predict')
  useEffect(() => { fetch('data/bundle.json').then((r) => r.json()).then(setData) }, [])
  if (!data) return <div className="boot"><div className="stat"><div className="v">…</div><div className="l">yükleniyor</div></div></div>

  return (
    <div className="shell">
      <aside className="rail">
        <div className="brand">
          <div className="dot" />
          <div><div className="name">trexCloud</div><div className="sub">predictive oee · rca</div></div>
        </div>
        {NAV.map((n) => (
          <div key={n.id} className={`navitem ${view === n.id ? 'active' : ''}`} onClick={() => setView(n.id)}>
            <span className="k">{n.icon}</span>{n.label}
          </div>
        ))}
        <div className="foot">12 makine · 7,4M telemetri<br />HistGBDT · ROC {data.fanuc.meta.ROC_AUC}</div>
      </aside>
      <main className="main">
        {view === 'predict' && <Predict data={data} />}
        {view === 'cross' && <Cross data={data} />}
        {view === 'overview' && <Overview data={data} />}
      </main>
    </div>
  )
}

/* ── 1. PREDICT → ROOT CAUSE → WHAT-IF (the whole story, one screen) ── */
function Predict({ data }) {
  const [machine, setMachine] = useState('Makine 1')
  const meta = data.fanuc.meta
  const dep = data.pm_value.deployed
  const eps = data.fanuc.episodes[machine] || []
  const [ei, setEi] = useState(0)
  const ep = eps[ei]
  const mc = data.machines.find((x) => x.name === machine)

  return (
    <>
      <header className="head">
        <div>
          <h1>Kestirimci Bakım</h1>
          <div className="lede">Model bir duruşu <b>önceden işaretler</b> · RCA <b>nedenini</b> bulur ·
            What-If <b>OEE & € kazanımını</b> ölçer.</div>
        </div>
        <Tag kind="green">ALTIN + PLATİN</Tag>
      </header>

      <div className="grid g4 kpis">
        <Panel cls="d1"><Stat label="ROC-AUC" value={meta.ROC_AUC} /></Panel>
        <Panel cls="d2"><Stat label="Lift" value={`${meta.lift}×`} /></Panel>
        <Panel cls="d3"><Stat label="Recall" value={fmtPct(dep.recall)} plain
          sub={`${dep.caught_stops}/${dep.significant_stops} önemli duruş`} /></Panel>
        <Panel cls="d4"><Stat label="ΔOEE (kestirimci)"
          value={`+${(dep.oee.delta.dOEE * 100).toFixed(1)} puan`} /></Panel>
      </div>

      <div className="ctl mt">
        <span className="ctl-lbl">Makine</span>
        {FANUC.map((m) => (
          <button key={m} className={`pill ${m === machine ? 'on' : ''}`}
            onClick={() => { setMachine(m); setEi(0) }}>{m.replace('Makine ', 'M')}</button>
        ))}
      </div>

      {/* PREDICT */}
      <Panel title="1 · Tahmin — duruş riski (tutulmamış gelecek)" icon="◈" cls="d2"
        cap={`Yeşil çizgi = risk · kırmızı kesikli = alarm eşiği · kırmızı × = gerçek duruş · sarı = seçili dönem.`}>
        <RiskChart points={data.fanuc.risk[machine] || []} threshold={meta.threshold}
          stops={data.fanuc.stops[machine] || []} episode={ep} />
        {eps.length > 0 && (
          <div className="btnrow mt-s">
            {eps.slice(0, 6).map((e, i) => (
              <button key={i} className={`pill ${i === ei ? 'on' : ''}`} onClick={() => setEi(i)}>
                {e.start.slice(5, 10)} · {(e.peak * 100).toFixed(0)}%{e.hit ? ' ⚠' : ''}
              </button>
            ))}
          </div>
        )}
      </Panel>

      {/* RCA */}
      <RcaPanel data={data} machine={machine} />

      {/* WHAT-IF */}
      <WhatIf machine={mc} />

      <div className="foot-note">Tahmin kapsamı: <b>Fanuc hücresi {`{1,2,3,5,9}`}</b> — duruş öncesi sinyali
        yalnız burada akıyor. Mitsubishi {`{7,8}`} RCA/OEE'de kapsanır; {`{4,6,10,TurboCut,ARES}`} telemetrisiz.</div>
    </>
  )
}

function RcaPanel({ data, machine }) {
  if (machine === 'Makine 1' && data.rca_demo?.card) {
    const d = data.rca_demo, card = d.card, cas = card.cascade
    return (
      <Panel title="2 · Kök-Neden — baseline sapma → nedensellik zinciri" icon="◎" cls="d3"
        cap="Altın: çok-sinyal baseline sapması (robust-z) + alarmların nedensel önceliğe göre sıralanması.">
        <div className="rca">
          <div>
            {cas && <>
              <div className="cascade">
                {cas.alarms.map((a, i) => (
                  <React.Fragment key={i}>
                    <span className={`casc-node ${a === cas.root_alarm ? 'root' : ''}`}>{a}</span>
                    {i < cas.alarms.length - 1 && <span className="casc-arrow">→</span>}
                  </React.Fragment>
                ))}
              </div>
              <div className="kv">Kök neden: <b className="red">{cas.root_alarm}</b></div>
            </>}
            <div className="kv ok">Aksiyon: {card.recommended_action}</div>
          </div>
          <div>
            <div className="mini-h">Baseline sapma imzası</div>
            <DeviationBars dev={d.deviation} />
            <div className="cap n">Olay anında baseline'dan sapan sinyaller — alarm kaskadını doğrular.</div>
          </div>
        </div>
      </Panel>
    )
  }
  const par = data.pareto.filter((p) => p.machine === machine).slice(0, 4)
  return (
    <Panel title="2 · Kök-Neden" icon="◎" cls="d3">
      <div className="note">Bu makinenin plansız duruşları tek genel etiket taşır (<b>Duruş</b>) → RCA
        <b> ne/ne zaman</b> sıralar (Pareto), cihaz düzeyinde <b>neden</b> diyemez (alarm yalnız M1 & M2).</div>
      <div className="rows mt-s">
        {par.length ? par.map((p, i) => (
          <div className="row" key={i}><span>{p.reason}</span><b>{p.hours} sa</b></div>
        )) : <div className="cap">Pareto kalemi yok.</div>}
      </div>
    </Panel>
  )
}

function WhatIf({ machine }) {
  const [pct, setPct] = useState(50)
  const r = useMemo(() => whatIfW1(machine.components, pct / 100), [machine, pct])
  const fin = useMemo(() => financials(r.recoveredH, r.extraPieces, ASSUM, 'downtime_cost'), [r])
  const dOEE = (r.after.OEE - r.before.OEE) * 100
  return (
    <Panel title="3 · What-If — düzeltmenin OEE & finansal etkisi" icon="◇" cls="d4">
      <div className="ctl">
        <span className="ctl-lbl">{machine.name} plansız duruşunu azalt</span>
        <input type="range" min="0" max="100" value={pct} onChange={(e) => setPct(+e.target.value)} />
        <b className="pct">%{pct}</b>
      </div>
      <div className="wi">
        <OeeBars before={r.before} after={r.after} />
        <div className="wi-stats">
          <Stat label="ΔOEE" value={`+${dOEE.toFixed(1)} puan`} />
          <Stat label="Geri kazanılan" value={fmtH(r.recoveredH)} plain />
          <Stat label="Net fayda / 30g" value={fmtEur(fin.net)} plain />
          <div className="cap n">Varsayım: €80/saat duruş, €300 müdahale · veride maliyet yok.</div>
        </div>
      </div>
    </Panel>
  )
}

/* ── 2. CROSS-MACHINE (Platinum) ── */
function Cross({ data }) {
  const cm = data.crossmachine
  const sync = cm.synchronization
  const regimes = Object.entries(cm.regimes || {})
  return (
    <>
      <header className="head">
        <div>
          <h1>Senkron Duruşlar</h1>
          <div className="lede">Her iddia <b>null-model testinden</b> geçti — şansa ve ortak vardiyaya
            bağlı olanları ayıkladık.</div>
        </div>
        <Tag kind="green">PLATİN</Tag>
      </header>

      <Panel title="Eşzamanlı duruşlar — şansın ötesinde mi?" icon="◫" cls="d1"
        cap={`Saat-içi vardiya ritmini koruyan null bile aşılıyor → <b>z=${sync.daily?.z}, p<0.001</b>. Yani 'herkes vardiyada durdu' değil; gerçek senkronizasyon.`}>
        <SyncBars sync={sync} />
      </Panel>

      <div className="grid g2 mt">
        <Panel title="Veri rejimleri — birlikte modellenebilir mi?" icon="⊞" cls="d2"
          cap="Sinyal kullanılabilirliğinden türetildi. Vendor aileleri ortak sütun paylaşmıyor → ancak rejim içinde, makine-içi normalizasyonla.">
          {regimes.map(([pat, ms], i) => (
            <div className="regime" key={i}>
              <div className="ctl-tags">
                {ms.map((m) => <Tag key={m} kind={FANUC.includes(m) ? 'green' : pat === '(blind)' ? 'dim' : 'amber'}>{m.replace('Makine', 'M')}</Tag>)}
              </div>
              <div className="cap n">{pat === '(blind)' ? 'telemetrisiz' : pat}</div>
            </div>
          ))}
        </Panel>
        <Panel title="Dürüst okuma" icon="◈" cls="d3">
          <div className="rows">
            <div className="row"><span>Eski yöntemin #1 bulgusu (bağlantı kesintisi)</span><Tag kind="red">geçersiz · veri tekrarı</Tag></div>
            <div className="row"><span>{`{1,2,3,9}`} kümesi · seviye r≤0.91</span><Tag kind="amber">ortak gün ritmi</Tag></div>
            <div className="row"><span>günlük dalgalanma çıkarılınca · r≈0</span><Tag kind="dim">anlık bağ yok</Tag></div>
          </div>
          <div className="note mt-s">Tüm plansız duruşlar tek etiket (<b>Duruş</b>) → MES verisi 'aynı neden'
            korelasyonunu doğrulayamaz. Negatif bulgu, saklamıyoruz.</div>
        </Panel>
      </div>
    </>
  )
}

/* ── 3. FLEET & OEE (context) ── */
function Overview({ data }) {
  // only real, active machines: telemetry present AND non-zero downtime, highest OEE first
  const fleet = data.machines
    .filter((m) => m.has_telemetry && m.down_h > 0)
    .sort((a, b) => b.oee - a.oee)
  const [sel, setSel] = useState(fleet[0]?.name || 'Makine 1')
  const plantOEE = fleet.reduce((s, m) => s + m.oee, 0) / fleet.length
  const sc = data.scenarios?.rows || []
  return (
    <>
      <header className="head">
        <div>
          <h1>Filo & OEE</h1>
          <div className="lede">Telemetrisi olan ve duruşu kaydedilen makineler, OEE'ye göre sıralı.
            Renk = rejim: yeşil Fanuc (tahmin edilebilir) · kehribar Mitsubishi.</div>
        </div>
        <Tag kind="green">{fmtPct(plantOEE)} ort. OEE</Tag>
      </header>

      <Panel title="Makine filosu" icon="▦" cls="d1"
        cap="OEE = A × P × Q. P üretimsiz günlerde 0; Q hurda kaydı olmadığından 1.">
        <div className="mgrid">
          {fleet.map((mc) => {
            const c = mc.regime.startsWith('Fanuc') ? 'green' : mc.regime.startsWith('Mits') ? 'amber' : 'dim'
            return (
              <div key={mc.name} className={`mcard ${sel === mc.name ? 'sel' : ''}`} onClick={() => setSel(mc.name)}>
                <div className="mn">{mc.name}<Tag kind={c}>{mc.vendor}</Tag></div>
                <div className="oee" style={{ color: oeeColor(mc.oee) }}>{fmtPct(mc.oee)}</div>
                <div className="bar"><i style={{ width: `${mc.oee * 100}%` }} /></div>
                <div className="meta">duruş {mc.down_h} sa</div>
              </div>
            )
          })}
        </div>
      </Panel>

      <div className="grid g2 mt">
        <Panel title="Duruş Pareto — arıza vs bağlantı" icon="▬" cls="d2"
          cap="<b>Kırmızı</b> = makine arızası · <b>gri</b> = bağlantı kesintisi (IT, OEE'yi geri kazandırmaz).">
          <ParetoChart rows={data.pareto.slice(0, 10)} />
        </Panel>
        <Panel title="What-If senaryoları — ΔOEE & net €" icon="◇" cls="d3"
          cap="Her senaryo aynı OEE motoruyla yeniden hesaplanır (ΔA/ΔP/ΔOEE). Varsayımlar etiketli.">
          <div className="rows">
            {sc.map((s) => (
              <div className="row sc" key={s.id}>
                <span>{s.scenario}</span>
                <span className="num"><b className={s.delta_OEE_pp > 0 ? 'green' : 'dim'}>+{s.delta_OEE_pp} pp</b>
                  <i className={s.net_eur >= 0 ? 'green' : 'red'}>{fmtEur(s.net_eur)}</i></span>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </>
  )
}
