import React, { useEffect, useMemo, useState } from 'react'
import { Panel, Stat, Tag, RiskChart, ParetoChart, OeeBars, TelemetrySpark, SyncBars, DeviationBars } from './components.jsx'
import { recompute, whatIfW1, financials, fmtPct, fmtInt, fmtH, oeeColor } from './lib.js'

const FANUC = ['Makine 1', 'Makine 2', 'Makine 3', 'Makine 5', 'Makine 9']
const NAV = [
  { id: 'overview', label: 'Genel Bakış', icon: '◳' },
  { id: 'predict', label: 'Tahmin → Aksiyon', icon: '◈' },
  { id: 'cross', label: 'Çapraz Makine', icon: '⊞' },
]

export default function App() {
  const [data, setData] = useState(null)
  const [view, setView] = useState('predict')
  useEffect(() => { fetch('data/bundle.json').then((r) => r.json()).then(setData) }, [])
  if (!data) return <Boot />

  return (
    <div className="shell">
      <aside className="rail">
        <div className="brand">
          <div className="dot" />
          <div>
            <div className="name">trexCloud</div>
            <div className="sub">predictive oee · rca</div>
          </div>
        </div>
        <div className="navlabel">Panolar</div>
        {NAV.map((n) => (
          <div key={n.id} className={`navitem ${view === n.id ? 'active' : ''}`}
            onClick={() => setView(n.id)}>
            <span className="k">{n.icon}</span>{n.label}
          </div>
        ))}
        <div className="foot">
          12 makine · {fmtInt(7.4e6)} telemetri satırı<br />
          model: HistGBDT · ROC {data.fanuc.meta.ROC_AUC}<br />
          Ağu 2025 – May 2026
        </div>
      </aside>
      <main className="main">
        {view === 'overview' && <Overview data={data} go={setView} />}
        {view === 'predict' && <Predict data={data} />}
        {view === 'cross' && <Cross data={data} />}
      </main>
    </div>
  )
}

const Boot = () => (
  <div style={{ display: 'grid', placeItems: 'center', height: '100vh' }}>
    <div className="stat"><div className="v">…</div><div className="l">veri yükleniyor</div></div>
  </div>
)

/* ───────────────────────── OVERVIEW ───────────────────────── */
function Overview({ data, go }) {
  const [sel, setSel] = useState('Makine 1')
  const tel = data.machines.filter((m) => m.has_telemetry)
  const plantOEE = tel.reduce((s, m) => s + m.oee, 0) / tel.length
  const totalDown = data.machines.reduce((s, m) => s + m.down_h, 0)
  const m = data.machines.find((x) => x.name === sel)
  return (
    <>
      <header className="head">
        <div>
          <h1>Genel Bakış</h1>
          <div className="lede">12 makinelik CNC + lazer tesisi. Renkler <b>rejimi</b> gösterir:
            yeşil = Fanuc üretim hücresi (tahmin edilebilir), kehribar = Mitsubishi (yalnız RCA/OEE),
            gri = telemetrisiz. Bir makineye tıklayıp bileşenlerini görün.</div>
        </div>
        <div className="badge">PLATIN HEDEFİ · çapraz-makine + ΔOEE + finansal</div>
      </header>

      <div className="grid g3" style={{ marginBottom: 14 }}>
        <Panel cls="d1"><Stat label="Tesis ort. OEE (telemetrili)" value={fmtPct(plantOEE)} /></Panel>
        <Panel cls="d2"><Stat label="Toplam plansız duruş" value={fmtH(totalDown)} plain /></Panel>
        <Panel cls="d3"><Stat label="Fanuc tahmin modeli · kazanç" value={`${data.fanuc.meta.lift}×`} /></Panel>
      </div>

      <div className="grid g-2-1">
        <Panel title="Makine Filosu — rejime göre" icon="▦" cls="d2"
          cap="OEE = Kullanılabilirlik × Performans × Kalite. <b>P</b> üretim sayımı olmayan günlerde 0; <b>Q</b> hurda kaydı olmadığından 1.">
          <div className="mgrid">
            {data.machines.map((mc) => {
              const c = mc.regime.startsWith('Fanuc') ? 'green' : mc.regime.startsWith('Mits') ? 'amber' : 'dim'
              return (
                <div key={mc.name} className={`mcard ${sel === mc.name ? 'sel' : ''}`}
                  onClick={() => setSel(mc.name)}>
                  <div className="mn">{mc.name}<Tag kind={c}>{mc.vendor}</Tag></div>
                  <div className="oee" style={{ color: oeeColor(mc.oee) }}>{fmtPct(mc.oee)}</div>
                  <div className="bar"><i style={{ width: `${mc.oee * 100}%` }} /></div>
                  <div className="meta">{mc.has_telemetry ? `duruş ${mc.down_h} sa` : 'telemetri YOK'}</div>
                </div>
              )
            })}
          </div>
        </Panel>

        <Panel title={`${sel} — KPI ayrışımı`} icon="◷" cls="d3"
          cap="Bu makinenin tüm dönem bileşenlerinden yeniden hesaplanan OEE.">
          <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <Stat label="OEE" value={fmtPct(m.oee)} />
            <Stat label="Kullanılabilirlik" value={fmtPct(m.A)} plain />
            <Stat label="Performans" value={fmtPct(m.P)} plain />
            <Stat label="Kalite" value={fmtPct(m.Q)} plain />
          </div>
          <div className="scope" style={{ marginTop: 14 }}>
            Rejim: <b>{m.regime}</b>
          </div>
        </Panel>
      </div>

      <div style={{ height: 14 }} />
      <Panel title="Duruş Pareto — arıza vs bağlantı" icon="▬" cls="d4"
        cap="<b>Kırmızı</b> = makine arızası (giderilebilir). <b>Gri</b> = System Offline / bağlantı kesintisi — bir IT/ağ sorunudur, makine OEE'sini geri kazandırmaz. TurboCut en büyük duruş kaynağı ama telemetrisi yok.">
        <ParetoChart rows={data.pareto} />
      </Panel>
    </>
  )
}

/* ───────────────────────── PREDICT → ACTION ───────────────────────── */
function Predict({ data }) {
  const [machine, setMachine] = useState('Makine 1')
  const meta = data.fanuc.meta
  const eps = data.fanuc.episodes[machine] || []
  const [epIdx, setEpIdx] = useState(0)
  const ep = eps[epIdx]
  const mc = data.machines.find((x) => x.name === machine)

  return (
    <>
      <header className="head">
        <div>
          <h1>Tahmin → Kök-Neden → What-If</h1>
          <div className="lede">Altın + Platin senaryosu tek ekranda: model bir <b>yüksek-risk dönemi</b> işaretler →
            RCA <b>nedeni</b> açıklar → What-If <b>OEE / € geri kazanımını</b> ölçer.</div>
        </div>
        <div className="badge">tutulmamış gelecek üzerinde · ROC {meta.ROC_AUC}</div>
      </header>

      <div className="scope" style={{ marginBottom: 14 }}>
        <b>Kapsam (tasarım gereği):</b> tahmin katmanı <b>Fanuc üretim hücresi {`{1,2,3,5,9}`}</b> içindir —
        duruş öncesi sinyali taşıyan cycle-time / run-state sinyalleri yalnız burada akıyor. Mitsubishi {`{7,8}`}
        bu sinyallerden yoksun (tahmin ≈ rastlantı) → RCA/OEE'de kapsanıyor, atılmıyor. {`{4,6,10,TurboCut,ARES}`} telemetrisiz.
      </div>

      <div className="grid g3" style={{ marginBottom: 14 }}>
        <Panel cls="d1"><Stat label="ROC-AUC (Fanuc)" value={meta.ROC_AUC} /></Panel>
        <Panel cls="d2"><Stat label="Taban-üstü kazanç" value={`${meta.lift}×`} /></Panel>
        <Panel cls="d3"><Stat label="Dönem isabeti"
          value={`${Math.round(meta.episode_precision * 100)}%`} plain /></Panel>
      </div>

      <div className="ctl" style={{ marginBottom: 12 }}>
        <label className="fld">Fanuc makinesi
          <select value={machine} onChange={(e) => { setMachine(e.target.value); setEpIdx(0) }}>
            {FANUC.map((m) => <option key={m}>{m}</option>)}
          </select>
        </label>
      </div>

      {/* 1 — PREDICT */}
      <Panel title="1 · Tahmin — duruş-risk zaman çizgisi" icon="◈" cls="d2"
        cap={`Mavi çizgi = tahmin edilen risk. Kırmızı kesikli = alarm eşiği (${meta.threshold}). Kırmızı ×'ler = gerçekleşen ≥15 dk plansız duruşlar. Sarı çizgi = seçili dönem. Modelin bu pencereyi <b>hiç görmediğini</b> unutmayın.`}>
        <RiskChart points={data.fanuc.risk[machine] || []} threshold={meta.threshold}
          stops={data.fanuc.stops[machine] || []} episode={ep} />
        {eps.length > 0 && (
          <>
            <div className="cap" style={{ marginBottom: 8 }}>Yüksek-risk dönemleri (riske göre sıralı) — birini seçin:</div>
            <div className="btnrow">
              {eps.map((e, i) => (
                <div key={i} className={`chip ${i === epIdx ? 'on' : ''}`} onClick={() => setEpIdx(i)}>
                  {e.start.slice(5)} · pik {(e.peak * 100).toFixed(0)}% ·{' '}
                  {e.hit ? <span className="hit">gerçek duruş ⚠</span> : <span className="nohit">duruş yok</span>}
                </div>
              ))}
            </div>
          </>
        )}
      </Panel>

      <div style={{ height: 14 }} />

      {/* 2 — RCA */}
      <RcaPanel data={data} machine={machine} ep={ep} />

      <div style={{ height: 14 }} />

      {/* 3 — WHAT-IF */}
      <WhatIf machine={mc} assumptions={data.whatif_assumptions} />
    </>
  )
}

function RcaPanel({ data, machine, ep }) {
  const isFlagship = machine === 'Makine 1' && data.rca_demo?.card
  if (isFlagship) {
    const d = data.rca_demo, card = d.card
    const cas = card.cascade
    return (
      <Panel title="2 · Kök-Neden — baseline sapma + çok-sinyal → nedensellik" icon="◎" cls="d3"
        cap="Altın kriteri: birden çok sinyalin baseline'dan sapması (robust-z) saptanır ve alarm kaskadı nedensel önceliğe göre sıralanarak kök nedene inilir.">
        <div className="grid g-2-1">
          <div>
            <div style={{ marginBottom: 6 }}><Tag kind="red">{card.pattern}</Tag>
              <span style={{ marginLeft: 8, color: 'var(--text-2)', fontSize: 13 }}>
                tetik: {card.trigger}</span></div>
            {cas && (
              <>
                <div className="cap" style={{ border: 0, padding: 0, margin: '10px 0 4px' }}>
                  Alarm kaskadı (nedensel önceliğe göre sıralı, indekse göre değil):</div>
                <div className="cascade">
                  {cas.alarms.map((a, i) => (
                    <React.Fragment key={i}>
                      <span className={`casc-node ${a === cas.root_alarm ? 'root' : ''}`}>{a}</span>
                      {i < cas.alarms.length - 1 && <span className="casc-arrow">→</span>}
                    </React.Fragment>
                  ))}
                </div>
                <div className="cap" style={{ marginTop: 8 }}>Kök neden:
                  <b style={{ color: 'var(--red)' }}> {cas.root_alarm}</b> ({cas.root_category})</div>
              </>
            )}
            {d.deviation?.length > 0 && (
              <>
                <div className="ptitle" style={{ fontSize: 11, marginTop: 14 }}>
                  Baseline sapma imzası (robust-z, olay penceresi)</div>
                <DeviationBars dev={d.deviation} />
                <div className="cap">Olay anında baseline'dan en çok sapan sinyaller. <b>run_state ▼7.7σ</b> =
                  makine duruyor; cycle_time de sapıyor. Bu çok-sinyal sapması alarm kaskadını
                  <b> doğruluyor</b> — sapma burada eşzamanlı kanıttır, öngörücü değil (dürüst not).</div>
              </>
            )}
            <ul className="evid">{card.evidence.map((e, i) => <li key={i}>{e}</li>)}</ul>
            <div className="note" style={{ color: 'var(--green-bright)', borderColor: 'var(--line-2)', background: 'var(--green-dim)' }}>
              Önerilen aksiyon: {card.recommended_action}</div>
          </div>
          <div>
            <div className="ptitle" style={{ fontSize: 11 }}>Telemetri (alarm penceresi)</div>
            {d.telemetry.map((t) => <TelemetrySpark key={t.role} role={t.role} points={t.points} />)}
            <div className="ptitle" style={{ fontSize: 11, marginTop: 14 }}>Sıralı hipotezler</div>
            {card.hypotheses.slice(0, 3).map((h, i) => (
              <div className="hyp" key={i}>
                <div className="c">{h.cause}</div><div className="lk">{(h.likelihood * 100).toFixed(0)}%</div>
                <div className="a">{h.recommended_action}</div>
              </div>
            ))}
          </div>
        </div>
      </Panel>
    )
  }
  // non-alarm Fanuc machines — honest Pareto-based RCA
  const par = data.pareto.filter((p) => p.machine === machine)
  return (
    <Panel title="2 · Kök-Neden — neden duruyor" icon="◎" cls="d3">
      <div className="note">ℹ️ Bu makinenin plansız duruşları tek bir genel etiket taşıyor (<b>Duruş</b>) —
        alarm ayrıntısı yok. Bu yüzden RCA <b>ne / ne zaman</b> sıralar (Pareto + tekrar), cihaz düzeyinde
        <b> neden</b> diyemez. Alarm düzeyinde kök-neden yalnız Makine 1 &amp; 2'de mevcut.</div>
      <div className="cap" style={{ marginTop: 12 }}>{machine} için en büyük plansız duruş kalemleri:</div>
      <table className="dt" style={{ marginTop: 8 }}>
        <thead><tr><th>Neden</th><th>Olay</th><th>Saat</th></tr></thead>
        <tbody>{par.length ? par.map((p, i) => (
          <tr key={i}><td>{p.reason}</td><td className="num">{fmtInt(p.events)}</td>
            <td className="num">{p.hours}</td></tr>
        )) : <tr><td colSpan="3" className="cap">Bu makine için Pareto kalemi yok.</td></tr>}</tbody>
      </table>
    </Panel>
  )
}

function WhatIf({ machine, assumptions }) {
  const [pct, setPct] = useState(50)
  const [a, setA] = useState(assumptions)
  const [valueAs, setValueAs] = useState('margin')
  const r = useMemo(() => whatIfW1(machine.components, pct / 100), [machine, pct])
  const fin = useMemo(() => financials(r.recoveredH, r.extraPieces, a, valueAs), [r, a, valueAs])
  const set = (k) => (e) => setA({ ...a, [k]: parseFloat(e.target.value) || 0 })

  return (
    <Panel title="3 · What-If — düzeltmenin OEE / € etkisi" icon="◇" cls="d4">
      <div className="ctl" style={{ marginBottom: 12 }}>
        <label className="fld" style={{ flex: 1, minWidth: 240 }}>
          {machine.name} plansız duruşunu %{pct} azalt
          <input type="range" min="0" max="100" value={pct} onChange={(e) => setPct(+e.target.value)} />
        </label>
      </div>
      <div className="grid g2">
        <div>
          <OeeBars before={r.before} after={r.after} />
          <div className="cap">Geri kazanılan çalışma süresi: <b>{r.recoveredH.toFixed(0)} saat</b> ·
            ek parça: <b>{fmtInt(r.extraPieces)}</b>. ΔOEE = <b style={{ color: 'var(--green)' }}>
              +{((r.after.OEE - r.before.OEE) * 100).toFixed(1)} puan</b>.</div>
        </div>
        <div>
          <div className="ptitle" style={{ fontSize: 11 }}>Finansal etki <span className="tag amber" style={{ marginLeft: 6 }}>VARSAYIM</span></div>
          <div className="cap" style={{ marginBottom: 10 }}>Veri setinde maliyet/fiyat yok — tüm € değerleri
            kullanıcı varsayımıdır, gerçek değil.</div>
          <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <label className="fld">Marj / parça
              <input type="number" value={a.margin_per_piece} onChange={set('margin_per_piece')} /></label>
            <label className="fld">Duruş maliyeti / saat
              <input type="number" value={a.downtime_cost_per_hour} onChange={set('downtime_cost_per_hour')} /></label>
            <label className="fld">Müdahale maliyeti
              <input type="number" value={a.intervention_cost} onChange={set('intervention_cost')} /></label>
            <label className="fld">Süreyi değerle
              <select value={valueAs} onChange={(e) => setValueAs(e.target.value)}>
                <option value="margin">marj</option><option value="downtime_cost">duruş maliyeti</option>
              </select></label>
          </div>
          <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 14 }}>
            <Stat label={`Net / ${a.horizon_days}g`} value={`${fmtInt(fin.net)} ${a.currency}`} />
            <Stat label="Geri ödeme (gün)" value={fin.payback ? fin.payback.toFixed(1) : '—'} plain />
          </div>
        </div>
      </div>
    </Panel>
  )
}

/* ───────────────────────── CROSS-MACHINE ───────────────────────── */
function Cross({ data }) {
  const cm = data.crossmachine
  const sync = cm.synchronization
  const cluster = cm.coupling?.running?.clusters?.[0] || []
  const regimeEntries = Object.entries(cm.regimes || {})
  const rm = (data.regime_models || []).filter(
    (r) => r.experiment === 'cross' && r.model === 'hist_gbdt')

  return (
    <>
      <header className="head">
        <div>
          <h1>Çapraz Makine & Rejimler</h1>
          <div className="lede">Platin kriteri: çapraz-makine örüntüleri. Buradaki her iddia <b>boş-model
            (null) testinden</b> geçti — şansa ya da ortak vardiyaya bağlı olanları dürüstçe ayırdık.</div>
        </div>
        <div className="badge">dürüst · null-model destekli</div>
      </header>

      <Panel title="Eski yöntemin tuzağı" icon="⚠" cls="d1"
        cap="Eski 'recurrence' yöntemi CONNECTIVITY'yi 1 numaralı sistemik bulgu sayıyordu — ama bu, tek bir System Offline kaydının aynı instance_id'deki makinelere kopyalanmasıdır. Yani örüntü 'tespit' değil, kayıt tekrarıdır. Yeni yöntem bunu ayıkladı.">
        <div className="ctl">
          <Tag kind="red">eski: CONNECTIVITY sıra #{cm.old_connectivity_rank} = totoloji</Tag>
          <Tag kind="green">yeni: null-model + rejim haritası + kümeleme</Tag>
        </div>
      </Panel>

      <div style={{ height: 14 }} />
      <div className="grid g2">
        <Panel title="Eşzamanlı duruşlar — şansın ötesinde mi?" icon="◫" cls="d2"
          cap={`≥2 makinenin aynı saatte ≥15dk plansız duruşa başlaması: <b>${sync.observed_co_stop_hours} saat</b>. Saat-içi ritmi koruyan null beklentisinin (${Math.round(sync.daily?.exp)}) çok üstünde → <b>z=${sync.daily?.z}, p&lt;0.001</b>. Yani 'herkes vardiya değişiminde durdu' değil; gerçek bir senkronizasyon var.`}>
          <SyncBars sync={sync} />
        </Panel>

        <Panel title="Veri rejimleri — hangi makineler birlikte modellenebilir" icon="⊞" cls="d3"
          cap="Sinyal <b>kullanılabilirliğinden</b> türetildi, katalogdan değil. Vendor aileleri neredeyse hiç ortak sütun paylaşmıyor; cycle_time bile makineler arası 8× ölçek farkı taşıyor → makine-içi normalizasyon şart.">
          {regimeEntries.map(([pat, ms], i) => (
            <div key={i} style={{ marginBottom: 10 }}>
              <div className="ctl" style={{ marginBottom: 4 }}>
                {ms.map((m) => <Tag key={m} kind={FANUC.includes(m) ? 'green' : pat === '(blind)' ? 'dim' : 'amber'}>{m.replace('Makine', 'M')}</Tag>)}
              </div>
              <div className="cap" style={{ border: 0, padding: 0 }}>{pat === '(blind)' ? 'telemetrisiz' : pat}</div>
            </div>
          ))}
        </Panel>
      </div>

      <div style={{ height: 14 }} />
      <div className="grid g2">
        <Panel title="Eşleşen küme — ama dürüst okuma" icon="◈" cls="d4"
          cap="Skor seviyelerinde {1,2,3,9} güçlü korele (r≤0.91), ama <b>türev alınınca (olay ölçeği) korelasyon ~0'a düşüyor</b>. Yani ortak bir <b>yavaş zarf</b> (çok-haftalık çalışma ritmi) paylaşıyorlar — eşzamanlı arıza yayılımı DEĞİL. Aksini iddia etmek yanlış olurdu.">
          <div className="ctl">
            {cluster.map((m) => <Tag key={m} kind="green">{m.replace('Makine', 'M')}</Tag>)}
            <Tag kind="dim">seviye r≤0.91</Tag><Tag kind="red">türev r≈0 → akut değil</Tag>
          </div>
          <div className="note" style={{ marginTop: 12 }}>Plansız duruşların tamamı tek etiket taşıyor
            (<b>Duruş</b>) → MES verisi 'aynı neden' korelasyonunu doğrulayamaz. Bu bir negatif bulgu,
            saklamıyoruz.</div>
        </Panel>

        <Panel title="Rejim modelleri — birleştirmek işe yarıyor mu?" icon="▤" cls="d5"
          cap="Aynı test satırları üzerinde HistGBDT. Birleştirme ham haliyle berabere; asıl kazanç <b>makine-içi z-norm</b>. Pooled 0.76 ROC kısmen taban-oranı şişmesiydi; dürüst makine-içi ROC ≈ 0.72 (Fanuc) / 0.63 (Mitsubishi).">
          <table className="dt">
            <thead><tr><th>Test</th><th>Eğitim</th><th>ROC</th><th>Kazanç</th></tr></thead>
            <tbody>
              {rm.map((r, i) => (
                <tr key={i}>
                  <td>{r.test_set}</td>
                  <td>{r.train_regime}</td>
                  <td className={`num ${r.train_regime === 'merged' ? 'win' : ''}`}>{r.ROC_AUC}</td>
                  <td className="num">{r.lift_PRAUC_over_base}×</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      </div>
    </>
  )
}
