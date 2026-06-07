# -*- coding: utf-8 -*-
"""Landscape 16:9 PDF render of the deck (viewable everywhere, identical design to the .pptx).
Same fixed master furniture on every slide. Run: uv run python scripts/build_slides_pdf.py
"""
import json
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

PM = json.loads(Path("analysis/artifacts/pm_value.json").read_text(encoding="utf-8"))
SCENARIOS = json.loads(Path("analysis/artifacts/scenarios.json").read_text(encoding="utf-8"))["rows"]
DEPLOYED = PM["deployed"]
ECON = PM["sensitivity"]["economic_optimum"]
DASH = Path("analysis/reports/dashboard")


def first_font(*paths):
    return next(str(p) for p in map(Path, paths) if p.exists())


pdfmetrics.registerFont(TTFont("AR", first_font(
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "C:/Windows/Fonts/arial.ttf")))
pdfmetrics.registerFont(TTFont("ARB", first_font(
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf")))

OUT = "trexCloud_Sunum.pdf"
INK = HexColor("#1A1F1D"); GREEN = HexColor("#127145"); GREEN_SOFT = HexColor("#ECF4EF")
MUTED = HexColor("#6B776F"); HAIR = HexColor("#D9DFDB")
BRONZE = HexColor("#A9773B"); SILVER = HexColor("#8A969E"); GOLD = HexColor("#C98B2A"); PLAT = HexColor("#2F8E86")

PT = 72.0
SW, SH = 13.333, 7.5
ML, CW = 0.85, 13.333 - 1.7
W, H = SW * PT, SH * PT
c = canvas.Canvas(OUT, pagesize=(W, H))


def X(i): return i * PT
def Y(top): return (SH - top) * PT          # y of a top edge


def st(size, color=INK, font="AR", lead=None):
    return ParagraphStyle("s", fontName=font, fontSize=size, leading=lead or size * 1.2,
                          textColor=color)


def para(text, top, x=ML, w=CW, size=15, color=INK, font="AR", align=0, lead=None):
    p = Paragraph(text, ParagraphStyle("p", fontName=font, fontSize=size,
                  leading=lead or size * 1.22, textColor=color, alignment=align))
    p.wrapOn(c, X(w), 6 * PT)
    p.drawOn(c, X(x), Y(top) - p.height)
    return top + p.height / PT


def rect(x, top, w, h, fill=None, line=None, lw=1.0):
    if fill is not None:
        c.setFillColor(fill)
    if line is not None:
        c.setStrokeColor(line); c.setLineWidth(lw)
    c.rect(X(x), Y(top + h), X(w), X(h), stroke=1 if line is not None else 0,
           fill=1 if fill is not None else 0)


def bullets(items, top, x=ML, w=CW, size=15, gap=0.14):
    y = top
    for it in items:
        nb = para(f'<font color="#127145"><b>—  </b></font>{it}', y, x, w, size, INK)
        y = nb + gap
    return y


def base(section, title, n):
    rect(0, 0, 0.14, SH, fill=GREEN)
    if section:
        para(f'<b>{section.upper()}</b>', 0.55, ML, CW, 11.5, GREEN, "ARB")
    para(f'<b>{title}</b>', 0.92, ML, CW, 28, INK, "ARB", lead=30)
    rect(ML, 1.92, CW, 0.012, fill=HAIR)
    para("trexCloud · Öngörücü OEE &amp; Kök-Neden Analizi", 7.08, ML, 8, 9, MUTED)
    para(f"{n:02d}", 7.08, SW - 1.4, 0.55, 9, MUTED, align=2)


def page():
    c.showPage()


def image_fit(path, x, top, w, h):
    image = ImageReader(str(path))
    iw, ih = image.getSize()
    scale = min(X(w) / iw, X(h) / ih)
    pw, ph = iw * scale, ih * scale
    c.drawImage(
        image,
        X(x) + (X(w) - pw) / 2,
        Y(top + h) + (X(h) - ph) / 2,
        width=pw,
        height=ph,
        preserveAspectRatio=True,
        mask="auto",
    )


def guide_panel(top, title, items, h=4.55, x=9.05, w=3.43):
    rect(x, top, w, h, fill=GREEN_SOFT, line=GREEN, lw=1.1)
    para(f"<b>{title}</b>", top + 0.34, x + 0.25, w - 0.5, 11, GREEN, "ARB")
    bullets(items, top + 0.82, x + 0.25, w - 0.55, 11.3, gap=0.1)


# 01 cover
rect(0, 0, 0.14, SH, fill=GREEN)
para('<b>TREXCLOUD HACKATHON</b>', 2.4, ML, CW, 13, GREEN, "ARB")
para('<b>Öngörücü OEE &amp; Kök-Neden Analizi</b>', 2.95, ML, CW, 40, INK, "ARB", lead=44)
para("Bir CNC + lazer tesisi için uçtan uca tahmin, kök-neden ve What-If sistemi", 4.5, ML, CW, 16, MUTED)
rect(ML, 5.25, 2.2, 0.025, fill=GREEN)
para("Veri dönemi: Ağustos 2025 – Mayıs 2026  ·  12 makine", 5.5, ML, CW, 12.5, MUTED)
para("trexCloud · Öngörücü OEE &amp; Kök-Neden Analizi", 7.08, ML, 8, 9, MUTED)
page()

# 02 yaklaşım
base("Yaklaşım", "Hedef: değerlendirmenin en üst iki seviyesi", 2)
para("Değerlendirme dört seviyeli. Bronz ve Gümüş bizde temel; odağımız Altın ve Platin.", 2.3, ML, CW, 15, INK)
cards = [("BRONZ", BRONZE, "Alarm ve duruşları zaman aralığında listele", False),
         ("GÜMÜŞ", SILVER, "Alarmları duruşlarla eşleştir, Pareto çıkar", False),
         ("ALTIN", GOLD, "Baseline sapma + çok-sinyal ile nedensellik zinciri", True),
         ("PLATİN", PLAT, "Çapraz-makine örüntü + ΔOEE + finansal öneri", True)]
cwd = (CW - 3 * 0.3) / 4
for i, (name, col, desc, hi) in enumerate(cards):
    x = ML + i * (cwd + 0.3)
    rect(x, 3.1, cwd, 2.75, fill=(GREEN_SOFT if hi else white), line=(GREEN if hi else HAIR), lw=(1.5 if hi else 1))
    rect(x, 3.1, cwd, 0.12, fill=col)
    para(f'<b>{name}</b>', 3.45, x + 0.18, cwd - 0.36, 14, INK, "ARB")
    para(desc, 3.98, x + 0.18, cwd - 0.36, 12.5, (INK if hi else MUTED), lead=16)
    if hi:
        para('<b>HEDEF</b>', 5.4, x + 0.18, cwd - 0.36, 9.5, GREEN, "ARB")
page()

# 03 veri
base("Veri", "Önce veriyi dürüstçe envanterledik", 3)
bullets([
    "12 makine, yaklaşık <b>7,4 milyon</b> telemetri kaydı; cp1254 kodlama, UTC, milisaniye.",
    "Dokümanın vaat ettiği kanıt sinyalleri (<b>servo sıcaklık, path-load</b>) pratikte boş: "
    "en yoğun makinede bile <b>0 / 28 satır</b>.",
    "Gerçekte akan sinyaller: <b>cycle_time, run_state, run_time, axis_position</b>. "
    "Nightwatch–MES eşleşmesi <b>162 / 162 (%100)</b>.",
], 2.35)
rect(ML, 5.25, CW, 1.05, fill=GREEN_SOFT, line=GREEN, lw=1.2)
para("Modeli dokümanın değil, gerçekten akan sinyallerin üzerine kurduk. "
     "Jüri veriyi iyi bilir; dürüst envanter güven kazandırır.", 5.5, ML + 0.25, CW - 0.5, 14, INK, lead=18)
page()

# 04 mimari
base("Mimari", "Uçtan uca hat", 4)
steps = ["Kanonik<br/>sinyal katmanı", "Baseline<br/>sapma (AD)", "Kök-neden<br/>(RCA)", "What-If / OEE", "Tahmin"]
bw = (CW - 4 * 0.45) / 5
for i, sstep in enumerate(steps):
    x = ML + i * (bw + 0.45); last = i == 4
    rect(x, 3.0, bw, 1.5, fill=(GREEN_SOFT if last else white), line=(GREEN if last else HAIR), lw=(1.5 if last else 1))
    para(f'<b>{sstep}</b>', 3.45, x, bw, 12.5, (GREEN if last else INK), "ARB", align=1, lead=15)
    if not last:
        para('<font color="#9aa6a0">›</font>', 3.45, x + bw + 0.02, 0.45, 22, MUTED, align=1)
para("Vendor-bağımsız rol haritası çapraz-makineyi mümkün kılar: Fanuc IsNotRunning ile "
     "Mitsubishi RUN_STATUS_START aynı role eşlenir.", 5.2, ML, CW, 14, MUTED, lead=18)
para("Rejim ayrımı:&nbsp;&nbsp;<b>Fanuc {1,2,3,5,9}</b>&nbsp;&nbsp;·&nbsp;&nbsp;<b>Mitsubishi {7,8}</b>"
     "&nbsp;&nbsp;·&nbsp;&nbsp;telemetrisiz {4,6,10, TurboCut, ARES}", 5.95, ML, CW, 13.5, INK)
page()

# 05 bronz+gümüş
base("Bronz · Gümüş", "Temel: olay akışı, eşleştirme, Pareto", 5)
bullets([
    "Alarm, duruş, bağlantı kesintisi ve sapma olayları tek bir akışta birleşik.",
    "Alarmlar duruşlara zaman damgasıyla eşleştirildi (ileri yönlü asof).",
    "Pareto, duruşu <b>arıza</b> ve <b>bağlantı</b> olarak ayırır — yatırım kararını bu ayrım belirler.",
], 2.35)
rect(ML, 5.25, CW, 1.05, fill=GREEN_SOFT, line=GREEN, lw=1.2)
para("En büyük duruş kaynağı bir makine arızası değil, bağlantı kesintisidir (System Offline). "
     "Bunu ayırmazsanız yanlış yere yatırım yaparsınız.", 5.5, ML + 0.25, CW - 0.5, 14, INK, lead=18)
page()

# 06 ALTIN
base("Altın", "Baseline sapma + çok-sinyal ile nedensellik", 6)
para("Örnek olay:&nbsp;&nbsp;Makine 1&nbsp;&nbsp;·&nbsp;&nbsp;12 Ocak 2026, 04:47", 2.3, ML, CW, 14, MUTED)
rect(ML, 2.95, 3.6, 0.9, fill=GREEN_SOFT, line=GREEN, lw=1.5)
para('<b>AIR PRESSURE FAILED</b>', 3.18, ML, 3.6, 13.5, GREEN, "ARB", align=1)
para('kök neden', 3.48, ML, 3.6, 11, GREEN, align=1)
para('<font color="#9aa6a0">›</font>', 3.18, ML + 3.7, 0.5, 24, MUTED, align=1)
rect(ML + 4.35, 2.95, 3.6, 0.9, fill=white, line=HAIR, lw=1.0)
para('<b>Z-AXIS ZERO RETURN</b>', 3.18, ML + 4.35, 3.6, 13.5, INK, "ARB", align=1)
para('sonuç', 3.48, ML + 4.35, 3.6, 11, MUTED, align=1)
bullets([
    "Baseline sapma imzası (robust-z):&nbsp;&nbsp;<b>run_state −7,7σ</b> (makine duruyor),&nbsp;cycle_time −0,8σ.",
    "Alarmlar dizine göre değil <b>nedensel önceliğe</b> göre sıralanır: kök neden hava basıncı, "
    "Z-ekseni hatası sonuçtur.",
], 4.2)
para("Dürüst not: bu olayda sapma eşzamanlı kanıttır, öngörücü bir öncül değildir.", 5.85, ML, CW, 12.5, MUTED)
page()

# 07 tahmin -> değer
base("Tahmin · Değer", "ROC / lift katmanından OEE ve €'ya", 7)
stats = [
    ("0,73", "ROC-AUC"),
    ("2,38×", "taban-üstü kazanç"),
    (f"%{DEPLOYED['recall'] * 100:.0f}", "duruş yakalama · held-out"),
    (f"+{DEPLOYED['oee']['delta']['dOEE'] * 100:.2f}".replace(".", ","), "puan OEE · e=%35"),
]
swd = (CW - 3 * 0.25) / 4
for i, (v, l) in enumerate(stats):
    x = ML + i * (swd + 0.25)
    rect(x, 2.55, swd, 1.35, fill=white, line=HAIR, lw=1.0)
    para(f'<b>{v}</b>', 2.8, x, swd, 29, GREEN, "ARB", align=1)
    para(l, 3.48, x + 0.08, swd - 0.16, 10.5, MUTED, align=1)
bullets([
    f"Gerçek held-out ölçüm: <b>{DEPLOYED['caught_stops']}/{DEPLOYED['significant_stops']}</b> duruş "
    f"yakalandı; <b>{DEPLOYED['episodes']}</b> alarm döneminin isabeti %{DEPLOYED['episode_precision']*100:.0f}.",
    f"e=%35 varsayımıyla yıllık projeksiyon: <b>{DEPLOYED['financial']['annualized']['prevented_h']:.0f} saat</b>; "
    f"fakat 300 €/kontrol varsayımında net <b>{DEPLOYED['financial']['annualized']['net_eur']:,.0f} €</b>.",
], 4.25, gap=0.1)
rect(ML, 5.65, CW, 0.72, fill=GREEN_SOFT, line=GREEN, lw=1.2)
para(f"Ekonomik duyarlılık (retrospektif): eşik <b>{ECON['threshold']:.2f}</b> → "
     f"{ECON['episodes']} kontrol → <b>{ECON['annualized_net_eur']:,.0f} €/yıl net</b>. "
     "Canlı eşiğin yerine geçmez.", 5.84, ML + 0.22, CW - 0.44, 12.5, INK)
page()

# 08 PLATİN cross
base("Platin", "Çapraz-makine örüntüleri — null-model ile", 8)
para("≥2 makinenin aynı saatte plansız duruşa girmesi — şansın ve vardiya ritminin ötesinde mi?", 2.3, ML, CW, 14, INK)
bars = [("Gözlemlenen", 708, GREEN), ("Beklenen (saat-içi ritim)", 564, MUTED), ("Beklenen (rastgele)", 333, HAIR)]
for i, (lab, v, col) in enumerate(bars):
    y = 3.1 + i * 0.62
    para(lab, y + 0.05, ML, 3.0, 12, INK)
    rect(ML + 3.1, y, (v / 760) * 6.2, 0.42, fill=col)
    para(f'<b>{v} saat</b>', y + 0.07, ML + 3.25 + (v / 760) * 6.2, 1.5, 12, INK, "ARB")
para("Sonuç:&nbsp;&nbsp;<b>z = 5,16, p &lt; 0,001</b> — senkronizasyon, ortak vardiya programıyla açıklanamıyor.",
     5.2, ML, CW, 14, INK)
bullets([
    "Eski yöntemin 1 numaralı ‘sistemik’ bulgusu (bağlantı) bir kayıt tekrarıydı; ayıkladık.",
    "Eşleşen küme {1,2,3,9} ortak bir çalışma ritmidir — eşzamanlı arıza yayılımı değil (dürüst okuma).",
], 5.65, gap=0.1)
page()

# 09 PLATİN scenario catalog
base("Platin", "İncelenebilir senaryo kataloğu", 9)
cols = [("Senaryo / kapsam", 4.15), ("ΔA", 1.05), ("ΔP", 1.05),
        ("ΔOEE", 1.15), ("Saat", 1.2), ("Net €", 1.55)]
x = ML
for label, width in cols:
    rect(x, 2.35, width, 0.45, fill=INK)
    para(f"<b>{label}</b>", 2.48, x + 0.1, width - 0.2, 10, white, "ARB")
    x += width
for i, row in enumerate(SCENARIOS):
    y = 2.85 + i * 0.68
    fill = GREEN_SOFT if i == 0 else white
    values = [
        (f"{row['id']} · {row['machine']} · {row['scenario']}", 4.15, 0),
        (f"{row['delta_A_pp']:.2f}".replace(".", ","), 1.05, 2),
        (f"{row['delta_P_pp']:.2f}".replace(".", ","), 1.05, 2),
        (f"{row['delta_OEE_pp']:.2f}".replace(".", ","), 1.15, 2),
        (f"{max(row['recovered_runtime_h'], row['recovered_schedule_h']):.0f}", 1.2, 2),
        (f"{row['net_eur']:,.0f}", 1.55, 2),
    ]
    x = ML
    for value, width, align in values:
        rect(x, y, width, 0.6, fill=fill, line=HAIR, lw=0.7)
        para(value, y + 0.16, x + 0.1, width - 0.2, 10.5,
             GREEN if i == 0 else INK, "ARB" if i == 0 else "AR", align=align)
        x += width
rect(ML, 5.78, CW, 0.62, fill=GREEN_SOFT, line=GREEN, lw=1.2)
para("S2 yalnız sınıflandırmayı değiştirir; S3 üretim sayımı olmadığı için inerttir; "
     "S4 IT aksiyonudur ve makine OEE'sine yazılmaz. Tüm € değerleri <b>VARSAYIM</b>.",
     5.94, ML + 0.22, CW - 0.44, 11.5, INK)
page()

# 10 sınırlar
base("Sınırlar", "Neyi tahmin edemeyeceğimizi de biliyoruz", 10)
bullets([
    "Kondisyon sinyalleri (sıcaklık, yük) boş → tahminin tavanını model değil, <b>veri</b> belirler.",
    "Mitsubishi 60 dk’da %53 duruş: tahmin doygun. 30 dk ufkunda zayıf ama mevcut; makineler atılmadı.",
    "Plansız duruşlar tek etiket taşır → ‘ne / ne zaman’ var, ‘neden’ yalnız Makine 1 ve 2’de.",
    "Kalite kaydı yok → Q simüle edilir; üretimsiz günlerde P doğal olarak sıfır.",
], 2.35, gap=0.18)
page()

# 11 sonuç
base("Sonuç", "Dürüst, çalışan, uçtan uca", 11)
bullets([
    "Dört seviye de kapsandı; en üst ikisi — Altın ve Platin — güçlü biçimde karşılandı.",
    "Tek akışta: duruş tahmini (Fanuc 2,38×) + kök-neden (kaskad) + sayısal ΔOEE / € önerisi.",
    "Sonraki adım: makine-bazlı olasılık kalibrasyonu, Mitsubishi için kısa-ufuk hedef.",
], 2.35)
rect(ML, 5.35, CW, 0.95, fill=INK)
para('<b>Tahmin eder, açıklar, sayısallaştırır — ve filodaki her makine için neden öyle '
     'davrandığımızı biliriz.</b>', 5.66, ML + 0.25, CW - 0.5, 16, white, "ARB", lead=20)
page()

# 12 dashboard guide: overview
base("Canlı Arayüz Rehberi", "Genel Bakış — tesis ve makine resmi", 12)
image_fit(DASH / "overview_fleet.png", ML, 2.18, 7.95, 4.55)
guide_panel(2.18, "NASIL OKUNUR?", [
    "<b>Üst KPI'lar:</b> tesis OEE'si, toplam plansız duruş ve Fanuc tahmin lift'i.",
    "<b>Makine kartları:</b> renk rejimi, yüzde OEE'yi; alt satır duruş saatini gösterir.",
    "<b>Sağ panel:</b> seçilen makinenin A/P/Q ayrışımı ve modelleme rejimi.",
])
page()

# 13 dashboard guide: Pareto
base("Canlı Arayüz Rehberi", "Pareto — arıza ile bağlantıyı ayır", 13)
image_fit(DASH / "overview_pareto.png", ML, 2.28, 8.25, 3.25)
guide_panel(2.28, "KARAR MESAJI", [
    "<b>Kırmızı:</b> giderilebilir makine duruşu.",
    "<b>Gri:</b> System Offline; IT/ağ sahipliğinde.",
    "TurboCut büyük kayıp kaynağıdır fakat telemetrisi yoktur.",
], h=3.25, x=9.35, w=3.13)
rect(ML, 5.78, CW, 0.62, fill=GREEN_SOFT, line=GREEN, lw=1.1)
para("Sunum cümlesi: “Bağlantı kaybını makine arızası sayarsak yanlış ekibe ve yanlış yatırıma gideriz.”",
     5.98, ML + 0.22, CW - 0.44, 11.5, INK)
page()

# 14 dashboard guide: prediction
base("Canlı Arayüz Rehberi", "Tahmin — risk zaman çizgisi ve gerçek duruşlar", 14)
image_fit(DASH / "predict_risk.png", ML, 2.15, 8.25, 4.78)
guide_panel(2.15, "NE GÖSTERİYOR?", [
    "<b>Yeşil çizgi:</b> modelin duruş riski.",
    "<b>Kırmızı kesik:</b> denetlenen alarm eşiği 0,1778.",
    "<b>Kırmızı çarpılar:</b> gerçekleşen ≥15 dk plansız duruşlar.",
    "Alt kutular yüksek-risk dönemlerini inceleme sırasına koyar.",
], h=4.78, x=9.35, w=3.13)
page()

# 15 dashboard guide: RCA
base("Canlı Arayüz Rehberi", "Kök-Neden — alarm kaskadından aksiyona", 15)
image_fit(DASH / "predict_rca.png", ML, 2.28, 8.25, 3.05)
guide_panel(2.28, "ALTIN AKIŞI", [
    "Kaskad nedensel önceliğe göre sıralanır.",
    "<b>AIR PRESSURE</b> kök neden; Z-axis alarmı sonuçtur.",
    "Telemetri ve hipotezler önerilen aksiyonu destekler.",
], h=3.05, x=9.35, w=3.13)
rect(ML, 5.68, CW, 0.72, fill=GREEN_SOFT, line=GREEN, lw=1.1)
para("Sunum cümlesi: “Model yalnız alarm vermiyor; alarmı kanıt, hipotez ve uygulanabilir aksiyona çeviriyor.”",
     5.9, ML + 0.22, CW - 0.44, 11.5, INK)
page()

# 16 dashboard guide: value + what-if
base("Canlı Arayüz Rehberi", "Kestirimci bakım değeri ve What-If", 16)
image_fit(DASH / "predict_value.png", ML, 2.15, 8.0, 2.18)
image_fit(DASH / "predict_whatif.png", ML, 4.52, 8.0, 2.25)
guide_panel(2.15, "İKİ FARKLI HESAP", [
    "<b>Üst panel:</b> yalnız modelin yakaladığı duruşlara atfedilen OEE/€.",
    "Etkililik ve maliyetler varsayımdır; recall/precision held-out ölçümdür.",
    "<b>Alt panel:</b> kullanıcının seçtiği duruş azaltımını genel What-If motoru simüle eder.",
    "Negatif ROI saklanmaz; her gerçek/yanlış alarm maliyet doğurur.",
], h=4.62, x=9.1, w=3.38)
page()

# 17 dashboard guide: scenarios
base("Canlı Arayüz Rehberi", "Senaryo kataloğu — sonuçlar denetlenebilir", 17)
image_fit(DASH / "predict_scenarios.png", ML, 2.25, 8.45, 2.48)
guide_panel(2.25, "TABLO NE İŞE YARAR?", [
    "ΔA / ΔP / ΔQ / ΔOEE birlikte görünür.",
    "Runtime ve schedule kazanımı ayrıdır.",
    "Sütun başlığına tıklayarak sıralanır.",
], h=2.48, x=9.45, w=3.03)
rect(ML, 5.18, CW, 1.18, fill=GREEN_SOFT, line=GREEN, lw=1.1)
para("S1 gerçek zaman/OEE kazanımıdır. S2 yalnız sınıflandırma etkisini, S3 üretim verisi "
     "yokluğundaki inert kolu, S4 ise IT sahipliğindeki schedule görünürlüğünü gösterir.",
     5.48, ML + 0.22, CW - 0.44, 12, INK, lead=16)
page()

# 18 dashboard guide: cross-machine
base("Canlı Arayüz Rehberi", "Çapraz Makine — iddiayı null-model ile sınar", 18)
image_fit(DASH / "cross_machine.png", ML, 2.12, 8.1, 4.82)
guide_panel(2.12, "PLATİN EKRANI", [
    "Eski connectivity sonucu kayıt tekrarı olarak teşhis edilir.",
    "708 eşzamanlı duruş, vardiya ritmini koruyan null'ın üstündedir.",
    "Rejim haritası birlikte modellenebilen makineleri gösterir.",
    "Küme seviyesi güçlü olsa da türev korelasyonu ≈0: akut yayılım iddia edilmez.",
], h=4.82)
page()

c.save()
print(f"kaydedildi: {OUT}")
