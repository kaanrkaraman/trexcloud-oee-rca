"""Follow-up EDA: fix Postgres 't'/'f' boolean handling; finish stoppage/counter/wo/telemetry."""
import pandas as pd, warnings
warnings.simplefilter("ignore")
pd.set_option("display.width",160); pd.set_option("display.max_columns",40)
D="dataset/"; ENC="cp1254"
def load(n,**k): return pd.read_csv(D+n+".csv",encoding=ENC,low_memory=False,**k)
def tf(s): return s.map({'t':True,'f':False})
def hdr(t): print("\n"+"="*78+"\n"+t+"\n"+"="*78)

unit=load("trex_mes_unit"); rd=load("trex_mes_reading_def")

hdr("6. STOPPAGE_SLICE — corrected boolean filter ('f'=unplanned)")
ss=load("trex_mes_stoppage_slice")
ss["started_on"]=pd.to_datetime(ss["started_on"],utc=True,errors="coerce")
ss=ss.merge(unit[["uid","name"]],left_on="unit_uid",right_on="uid",how="left")
ss=ss.merge(rd[["uid","display_text","signal_category"]].rename(columns={"uid":"rduid"}),
            left_on="reading_def_uid",right_on="rduid",how="left")
ss["planned"]=tf(ss.is_planned); ss["excl"]=tf(ss.exclude_from_oee); ss["test"]=tf(ss.is_test_prod)
ss["hrs"]=ss.duration_milliseconds/3.6e6
print("rows:",len(ss),"| planned counts:",dict(ss.planned.value_counts(dropna=False)))
print("exclude_from_oee:",dict(ss.excl.value_counts(dropna=False)),"| is_test_prod:",dict(ss.test.value_counts(dropna=False)))
print("null ended_on (still-open):", int(ss.ended_on.isna().sum()))
up=ss[ss.planned==False]
print("\nTOP UNPLANNED STOP REASONS by total hours (all machines):")
g=up.groupby("display_text").agg(events=("id","size"),hours=("hrs","sum"),
     mins_median=("duration_milliseconds",lambda x:x.median()/6e4)).sort_values("hours",ascending=False)
print(g.head(12).round(1).to_string())
print("\nUnplanned downtime hours per machine:")
print(up.groupby("name").hrs.sum().sort_values(ascending=False).round(0).to_string())
print("\nPLANNED stop reasons:")
print(ss[ss.planned==True].groupby("display_text").hrs.sum().sort_values(ascending=False).head(8).round(1).to_string())

hdr("7. COUNTER_SLICE + WORKORDER")
cs=load("trex_mes_counter_slice")
cs=cs.merge(unit[["uid","name"]],left_on="unit_uid",right_on="uid",how="left")
print("counter rows:",len(cs))
print("signal_type:",dict(cs.signal_type.value_counts(dropna=False)))
print("triggered_by:",dict(cs.triggered_by.value_counts(dropna=False)))
print("pieces (value) summed per machine:")
print(cs.groupby("name").value.sum().sort_values(ascending=False).round(0).to_string())
wo=load("trex_mes_workorder")
wo["started_on"]=pd.to_datetime(wo["started_on"],utc=True,errors="coerce")
wo["is_stock_b"]=tf(wo.is_stock); wo["is_wo_b"]=tf(wo.is_work_order)
print("\nworkorder rows:",len(wo),"| is_stock:",dict(wo.is_stock_b.value_counts(dropna=False)),
      "| is_work_order:",dict(wo.is_wo_b.value_counts(dropna=False)))
print("stock_cycle non-null:",int(wo.stock_cycle.notna().sum()),
      "| stock_cycle describe(ms):",dict(wo.stock_cycle.describe().round(0)))
print("date range:",wo.started_on.min(),"->",wo.started_on.max())
print("top order_no:",list(wo.order_no.dropna().value_counts().head(6).index))

hdr("8. OEE summary — A validity (how messy is the 'A' field?)")
import json
oee=load("trex_mes_oee_summary")
def jget(s,k):
    o=[]
    for v in s:
        try:o.append(json.loads(v).get(k))
        except:o.append(None)
    return o
oee["A"]=pd.to_numeric(pd.Series(jget(oee.availability,"A")),errors="coerce")
L1=oee[oee.level==1]
print("level==1 rows:",len(L1))
print("A in [0,1]:",int(((L1.A>=0)&(L1.A<=1)).sum()),
      "| A<0:",int((L1.A<0).sum()),"| A>1:",int((L1.A>1).sum()),"| A null:",int(L1.A.isna().sum()))
print("=> the stored 'A' is noisy; recompute from WorkTotal/PlannedStop/UnPlannedStop when modeling.")

hdr("9. NIGHTWATCH telemetry sample (part 001, 300k numeric rows)")
nrd=load("trex_nightwatch_reading_def")
nd=pd.read_csv(D+"trex_nightwatch_data_001.csv",encoding=ENC,nrows=300000,low_memory=False)
nd["time"]=pd.to_datetime(nd["time"],utc=True,errors="coerce")
ndj=nd.merge(nrd[["readingdef_uid","readingdef_name","external_signal_type"]],on="readingdef_uid",how="left")
print("numeric sample time range:",nd.time.min(),"->",nd.time.max())
print("top numeric signals:");print(ndj.readingdef_name.value_counts().head(10).to_string())
print("distinct signals in sample:",ndj.readingdef_uid.nunique())
nds=pd.read_csv(D+"trex_nightwatch_data_string_001.csv",encoding=ENC,nrows=100000,low_memory=False)
ndsj=nds.merge(nrd[["readingdef_uid","readingdef_name"]],on="readingdef_uid",how="left")
print("\ntop string signals:");print(ndsj.readingdef_name.value_counts().head(8).to_string())
print("string value examples:",list(pd.Series(nds.value.dropna().astype(str).unique())[:8]))
print("\nDONE.")
