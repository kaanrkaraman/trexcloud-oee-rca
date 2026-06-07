"""trexCloud hackathon EDA — grounded inspection of the curated CSVs.
Reads with cp1254 (Turkish) encoding. Big nightwatch tables are sampled, never full-scanned.
"""
import pandas as pd, json, glob, warnings
warnings.simplefilter("ignore")
pd.set_option("display.width", 160); pd.set_option("display.max_columns", 40)
D = "dataset/"
ENC = "cp1254"

def load(name, **kw):
    return pd.read_csv(D + name + ".csv", encoding=ENC, low_memory=False, **kw)

def hdr(t): print("\n" + "=" * 78 + "\n" + t + "\n" + "=" * 78)

# ---------------------------------------------------------------- units/devices
hdr("1. MACHINE MASTER (MES unit + device collector)")
unit = load("trex_mes_unit"); dev = load("trex_mes_device")
m = unit.merge(dev[["uid", "collector_type_name"]], left_on="device_uid", right_on="uid",
               suffixes=("", "_dev"), how="left")
print(m[["name", "uid", "collector_type_name", "is_enabled", "usage_scenario"]]
      .sort_values("name").to_string(index=False))

hdr("1b. NIGHTWATCH unit (note integer id used to join reading_def.unit_id)")
nu = load("trex_nightwatch_unit")
print(nu[["id", "unit_uid", "name", "is_enabled"]].sort_values("name").to_string(index=False))
mes_units = set(unit.uid); nw_units = set(nu.unit_uid)
print("\nMES units:", len(mes_units), "| NW units:", len(nw_units))
print("In MES but NOT in Nightwatch:", [unit.set_index('uid').loc[u,'name'] for u in mes_units - nw_units])

# ---------------------------------------------------------------- reading defs
hdr("2. MES reading_def — signal_type x signal_category")
rd = load("trex_mes_reading_def")
print(pd.crosstab(rd.signal_type.fillna("(blank)"), rd.signal_category.fillna("(blank)")))
print("\nDistinct enabled signals per unit (top):")
print(rd[rd.is_enabled==True].groupby("unit_uid").size().sort_values(ascending=False).head())

hdr("2b. Nightwatch reading_def — external_signal_type counts + meta fields")
nrd = load("trex_nightwatch_reading_def")
print(nrd.external_signal_type.fillna("(blank)").value_counts())
print("\nSample readingdef_name by signal type:")
for st in ["STOP","ALERT_ARRAY","COUNT","STOCK_CYCLE","PULSE_COUNT",None]:
    sub = nrd[nrd.external_signal_type.isna()] if st is None else nrd[nrd.external_signal_type==st]
    print(f"  [{st}] ", list(sub.readingdef_name.dropna().unique()[:6]))

# ---------------------------------------------------------------- THE JOIN
hdr("3. *** CROSS-DOMAIN JOIN TEST: MES reading_def.uid <-> NW readingdef_uid ***")
mes_sig = set(rd.uid.dropna()); nw_sig = set(nrd.readingdef_uid.dropna())
print(f"MES reading_def uids: {len(mes_sig)} | NW readingdef uids: {len(nw_sig)}")
both = mes_sig & nw_sig
print(f"UIDs present in BOTH catalogs: {len(both)}  ({100*len(both)/max(len(nw_sig),1):.1f}% of NW)")
print(f"MES-only: {len(mes_sig-nw_sig)} | NW-only: {len(nw_sig-mes_sig)}")
# show a few matched signals with names from both sides
mm = rd[rd.uid.isin(both)][["uid","name","display_text","signal_type","unit_uid"]].merge(
     nrd[["readingdef_uid","readingdef_name","external_signal_type","unit_id"]],
     left_on="uid", right_on="readingdef_uid", how="inner")
print("\nMatched-signal examples (MES name | NW name | types):")
print(mm[["name","readingdef_name","signal_type","external_signal_type"]].head(12).to_string(index=False))

# Also test per-unit join path: NW reading_def.unit_id -> NW unit.id -> unit_uid
nrd_u = nrd.merge(nu[["id","unit_uid","name"]], left_on="unit_id", right_on="id", how="left")
print("\nNW signals per machine (via unit_id->unit_uid):")
print(nrd_u.groupby("name").size().sort_values(ascending=False).to_string())

# ---------------------------------------------------------------- OEE summary
hdr("4. OEE SUMMARY — parse JSON, distributions")
oee = load("trex_mes_oee_summary")
oee["trans_date"] = pd.to_datetime(oee["trans_date"], utc=True, errors="coerce")
def jget(s, k):
    out=[]
    for v in s:
        try: out.append(json.loads(v).get(k))
        except: out.append(None)
    return out
for col,keys in [("availability",["A","WorkTotal","PlannedStop","UnPlannedStop","StopTotal"]),
                 ("performance",["P","WorkingTime","PlannedTime"]),
                 ("quality",["Q","ProductSum","ScrapeSum"])]:
    for k in keys:
        oee[f"{col[:1]}_{k}"] = pd.to_numeric(pd.Series(jget(oee[col], k)), errors="coerce")
print("Rows:", len(oee), "| date range:", oee.trans_date.min(), "->", oee.trans_date.max())
print("level counts (0=plant,1=machine):"); print(oee.level.value_counts())
print("\nKPI describe (machine-level, level==1):")
L1 = oee[oee.level==1]
print(L1[["oee","a_A","p_P","q_Q","q_ProductSum","q_ScrapeSum"]].describe().round(3).to_string())
print("\nScrapeSum nonzero rows:", int((oee.q_ScrapeSum.fillna(0)!=0).sum()), "(expect 0 -> Q=1 everywhere)")
print("Rows where A>0 but P==0:", int(((L1.a_A>0)&(L1.p_P==0)).sum()))
print("Rows where oee==0:", int((L1.oee==0).sum()), "of", len(L1))

# ---------------------------------------------------------------- alerts
hdr("5. ALERTS (RCA entry point)")
al = load("trex_mes_alert")
al["started_on"] = pd.to_datetime(al["started_on"], utc=True, errors="coerce")
al = al.merge(unit[["uid","name"]], left_on="unit_uid", right_on="uid", how="left")
print("rows:", len(al), "| range:", al.started_on.min(), "->", al.started_on.max())
print("\nTop alarm texts:"); print(al.value.str.strip().value_counts().head(15).to_string())
print("\nAlarms per machine:"); print(al.groupby("name").size().sort_values(ascending=False).to_string())

# ---------------------------------------------------------------- stoppages
hdr("6. STOPPAGE_SLICE (Availability driver)")
ss = load("trex_mes_stoppage_slice")
ss["started_on"]=pd.to_datetime(ss["started_on"],utc=True,errors="coerce")
ss = ss.merge(unit[["uid","name"]], left_on="unit_uid", right_on="uid", how="left")
ss = ss.merge(rd[["uid","display_text","signal_category"]].rename(columns={"uid":"rduid"}),
              left_on="reading_def_uid", right_on="rduid", how="left")
print("rows:", len(ss), "| range:", ss.started_on.min(), "->", ss.started_on.max())
print("planned flag:"); print(ss.is_planned.value_counts())
print("\nTop unplanned stop reasons by total hours:")
up = ss[ss.is_planned==False].copy(); up["hrs"]=up.duration_milliseconds/3.6e6
g = up.groupby("display_text").agg(events=("id","size"), hours=("hrs","sum")).sort_values("hours",ascending=False)
print(g.head(12).round(1).to_string())

# ---------------------------------------------------------------- counters/workorders
hdr("7. COUNTER_SLICE + WORKORDER (Performance / throughput)")
cs = load("trex_mes_counter_slice")
print("counter rows:", len(cs), "| signal_type:", dict(cs.signal_type.value_counts().head()))
print("triggered_by:", dict(cs.triggered_by.value_counts(dropna=False).head()))
wo = load("trex_mes_workorder")
wo["started_on"]=pd.to_datetime(wo["started_on"],utc=True,errors="coerce")
print("\nworkorder rows:", len(wo), "| is_stock:", dict(wo.is_stock.value_counts(dropna=False)))
print("stock_cycle nonnull:", int(wo.stock_cycle.notna().sum()), "| sample order_no:", list(wo.order_no.dropna().unique()[:5]))

# ---------------------------------------------------------------- nightwatch sample
hdr("8. NIGHTWATCH telemetry SAMPLE (first 200k rows of part 001 only)")
nd = pd.read_csv(D+"trex_nightwatch_data_001.csv", encoding=ENC, nrows=200000, low_memory=False)
nd["time"]=pd.to_datetime(nd["time"],utc=True,errors="coerce")
print("sample range:", nd.time.min(), "->", nd.time.max())
ndj = nd.merge(nrd[["readingdef_uid","readingdef_name","external_signal_type"]], on="readingdef_uid", how="left")
print("top signals in sample:"); print(ndj.readingdef_name.value_counts().head(10).to_string())
nds = pd.read_csv(D+"trex_nightwatch_data_string_001.csv", encoding=ENC, nrows=100000, low_memory=False)
ndsj = nds.merge(nrd[["readingdef_uid","readingdef_name"]], on="readingdef_uid", how="left")
print("\nstring telemetry top signals:"); print(ndsj.readingdef_name.value_counts().head(10).to_string())
print("string value examples:", list(nds.value.dropna().astype(str).unique()[:8]))
print("\nDONE.")
