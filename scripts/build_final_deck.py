# -*- coding: utf-8 -*-
"""Final jury presentation, landscape 16:9 PDF, Turkish.
Content-first, single teal accent, real charts drawn from the data bundle.
Run: uv run python scripts/build_final_deck.py  ->  trexCloud_Final_Sunum.pdf
"""

import json
from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

# ---------- data (single source: the bundle the live UI consumes) ----------
B = json.loads(Path("web/public/data/bundle.json").read_text(encoding="utf-8"))
META = B["fanuc"]["meta"]
DEP = B["pm_value"]["deployed"]
ECON = B["pm_value"]["sensitivity"]["economic_optimum"]
SYNC = B["crossmachine"]["synchronization"]
MACHINES = [m for m in B["machines"] if m["has_telemetry"] and m["down_h"] > 0]
MACHINES.sort(key=lambda m: -m["oee"])
RISK = B["fanuc"]["risk"].get("Makine 1", [])
THR = META["threshold"]


def first_font(*paths):
    return next(str(p) for p in map(Path, paths) if p.exists())


pdfmetrics.registerFont(
    TTFont(
        "AR",
        first_font(
            "/System/Library/Fonts/Supplemental/Arial.ttf", "C:/Windows/Fonts/arial.ttf"
        ),
    )
)
pdfmetrics.registerFont(
    TTFont(
        "ARB",
        first_font(
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ),
    )
)

OUT = "trexCloud_Final_Sunum.pdf"
INK = HexColor("#16201C")
GREEN = HexColor("#0F7A52")
GREEN_SOFT = HexColor("#ECF4EF")
MUTED = HexColor("#6B776F")
HAIR = HexColor("#D9DFDB")
RED = HexColor("#C43D3D")
AMBER = HexColor("#E0741C")
GRAY = HexColor("#9AA8A1")

PT = 72.0
SW, SH = 13.333, 7.5
ML, CW = 0.85, 13.333 - 1.7
W, H = SW * PT, SH * PT
c = canvas.Canvas(OUT, pagesize=(W, H))


def X(i):
    return i * PT


def Y(top):
    return (SH - top) * PT


def tu(s):
    """Turkish-correct uppercase (dotted I)."""
    return s.replace("i", "İ").upper()


def tr(x):
    return f"{x}".replace(".", ",")


def para(text, top, x=ML, w=CW, size=15, color=INK, font="AR", align=0, lead=None):
    p = Paragraph(
        text,
        ParagraphStyle(
            "p",
            fontName=font,
            fontSize=size,
            leading=lead or size * 1.22,
            textColor=color,
            alignment=align,
        ),
    )
    p.wrapOn(c, X(w), 6 * PT)
    p.drawOn(c, X(x), Y(top) - p.height)
    return top + p.height / PT


def rect(x, top, w, h, fill=None, line=None, lw=1.0):
    if fill is not None:
        c.setFillColor(fill)
    if line is not None:
        c.setStrokeColor(line)
        c.setLineWidth(lw)
    c.rect(
        X(x),
        Y(top + h),
        X(w),
        X(h),
        stroke=1 if line is not None else 0,
        fill=1 if fill is not None else 0,
    )


def bullets(items, top, x=ML, w=CW, size=14.5, gap=0.17):
    y = top
    for it in items:
        para('<font color="#0F7A52"><b>•</b></font>', y, x, 0.3, size, GREEN)
        nb = para(it, y, x + 0.28, w - 0.28, size, INK)
        y = nb + gap
    return y


def base(section, title, n):
    rect(0, 0, 0.14, SH, fill=GREEN)
    if section:
        para(f"<b>{tu(section)}</b>", 0.55, ML, CW, 11.5, GREEN, "ARB")
    para(f"<b>{title}</b>", 0.92, ML, CW, 26, INK, "ARB", lead=29)
    rect(ML, 1.9, CW, 0.012, fill=HAIR)
    para("trexCloud · Kestirimci OEE ve Kök Neden Analizi", 7.08, ML, 8, 9, MUTED)
    para(f"{n:02d}", 7.08, SW - 1.4, 0.55, 9, MUTED, align=2)


def page():
    c.showPage()


def numbox(items, top, h=1.45, gap=0.4):
    """Numbered process boxes, no arrows."""
    n = len(items)
    bw = (CW - (n - 1) * gap) / n
    for i, (head, sub) in enumerate(items):
        x = ML + i * (bw + gap)
        last = i == n - 1
        rect(
            x,
            top,
            bw,
            h,
            fill=(GREEN_SOFT if last else white),
            line=(GREEN if last else HAIR),
            lw=(1.5 if last else 1),
        )
        para(
            f"<b>{i+1}</b>",
            top + 0.18,
            x + 0.16,
            0.5,
            12,
            GREEN if last else MUTED,
            "ARB",
        )
        para(
            f"<b>{head}</b>",
            top + 0.55,
            x + 0.16,
            bw - 0.3,
            13,
            GREEN if last else INK,
            "ARB",
            lead=15,
        )
        para(sub, top + h - 0.42, x + 0.16, bw - 0.3, 10, MUTED, lead=12)


def statcards(stats, top, h=1.35):
    n = len(stats)
    gap = 0.25
    swd = (CW - (n - 1) * gap) / n
    for i, (v, l) in enumerate(stats):
        x = ML + i * (swd + gap)
        rect(x, top, swd, h, fill=white, line=HAIR, lw=1.0)
        para(f"<b>{v}</b>", top + 0.27, x, swd, 27, GREEN, "ARB", align=1)
        para(l, top + 0.9, x + 0.08, swd - 0.16, 10.5, MUTED, align=1, lead=12)


def oee_bars(rows, x, top, w, h):
    """Horizontal OEE-by-machine bars from real data."""
    n = len(rows)
    rh = h / n
    for i, m in enumerate(rows):
        y = top + i * rh
        col = GREEN if m["regime"].startswith("Fanuc") else AMBER
        para(m["name"].replace("Makine", "M"), y + rh * 0.28, x, 0.9, 10.5, INK)
        track_x = x + 0.95
        track_w = w - 2.3
        rect(track_x, y + rh * 0.18, track_w, rh * 0.5, fill=HexColor("#EEF2F0"))
        rect(track_x, y + rh * 0.18, max(0.02, track_w * m["oee"]), rh * 0.5, fill=col)
        para(
            f'<b>{m["oee"]*100:.1f}%</b>',
            y + rh * 0.26,
            track_x + track_w + 0.1,
            1.1,
            10.5,
            INK,
            "ARB",
        )


def risk_line(points, x, top, w, h):
    """Risk timeline polyline + alarm threshold, drawn from real model output."""
    rect(x, top, w, h, fill=white, line=HAIR, lw=1.0)
    pad = 0.18
    px, py, pw, ph = x + pad + 0.25, top + pad, w - 2 * pad - 0.3, h - 2 * pad - 0.25
    # y gridlines 0 / 0.5 / 1.0
    for gv in (0.0, 0.5, 1.0):
        gy = py + ph * (1 - gv)
        c.setStrokeColor(HAIR)
        c.setLineWidth(0.4)
        c.line(X(px), Y(gy), X(px + pw), Y(gy))
        para(tr(f"{gv:.1f}"), gy - 0.07, x + pad - 0.05, 0.32, 8, MUTED, align=2)
    # threshold
    ty = py + ph * (1 - THR)
    c.setStrokeColor(RED)
    c.setLineWidth(0.8)
    c.setDash(3, 3)
    c.line(X(px), Y(ty), X(px + pw), Y(ty))
    c.setDash()
    para("alarm eşiği", ty - 0.02, px + pw - 1.0, 1.0, 8, RED, align=2)
    # polyline
    pts = points[:: max(1, len(points) // 380)] if points else []
    if pts:
        path = c.beginPath()
        for j, p in enumerate(pts):
            xx = px + pw * (j / (len(pts) - 1))
            yy = py + ph * (1 - max(0.0, min(1.0, p["r"])))
            (path.moveTo if j == 0 else path.lineTo)(X(xx), Y(yy))
        c.setStrokeColor(GREEN)
        c.setLineWidth(0.9)
        c.setDash()
        c.drawPath(path)


# ═══════════════════════════ 01 cover ═══════════════════════════
rect(0, 0, 0.14, SH, fill=GREEN)
para("<b>TREXCLOUD · ULUDAĞ HACKATHON</b>", 2.35, ML, CW, 13, GREEN, "ARB")
para("<b>Kestirimci OEE ve Kök Neden Analizi</b>", 2.9, ML, CW, 38, INK, "ARB", lead=42)
para(
    "Bir CNC ve lazer tesisi için uçtan uca duruş tahmini, kök neden ve What-If sistemi",
    4.45,
    ML,
    CW,
    16,
    MUTED,
)
rect(ML, 5.2, 2.2, 0.025, fill=GREEN)
para(
    "Veri dönemi Ağustos 2025 - Mayıs 2026  ·  12 makine  ·  yaklaşık 7,4 milyon telemetri kaydı",
    5.45,
    ML,
    CW,
    12.5,
    MUTED,
)
para("trexCloud · Kestirimci OEE ve Kök Neden Analizi", 7.08, ML, 8, 9, MUTED)
page()

# ═══════════════════════════ 02 problem & veri ═══════════════════════════
base("Veri", "Önce veriyi dürüstçe envanterledik", 2)
bullets(
    [
        "Tesiste 12 makine var (Fanuc, Mitsubishi, Nukon). Yaklaşık 7,4 milyon telemetri kaydı ve "
        "153 bin MES olayı işlendi. Tüm süreler milisaniye cinsindendir.",
        "OEE üç bileşenin çarpımıdır: Kullanılabilirlik (A) çarpı Performans (P) çarpı Kalite (Q).",
        "Veride hurda kaydı sıfırdır, bu yüzden Kalite her zaman 1 çıkar. Üretim sayımı sıfır olan "
        "günlerde Performans 0 olur.",
        "Dokümanın işaret ettiği kanıt sinyalleri (servo sıcaklığı, yük) pratikte boştur. Modeli "
        "gerçekten akan sinyallerin üzerine kurduk: cycle_time, run_state, run_time, axis_position.",
        "En büyük duruş kaynağı bir makine arızası değil, System Offline yani bağlantı kesintisidir. "
        "Bunu ayrı tuttuk; çözümü bakım değil IT ekibindedir ve makine OEE'sine yazılmaz.",
    ],
    2.3,
    gap=0.2,
)
page()

# ═══════════════════════════ 03 yöntem ═══════════════════════════
base("Yöntem", "Sinyalden öneriye uzanan tek hat", 3)
para(
    "Sistem beş aşamadan oluşur. Her aşama bir öncekinin çıktısını kullanır.",
    2.25,
    ML,
    CW,
    14.5,
    INK,
)
numbox(
    [
        ("Kanonik sinyal", "Farklı markaların sinyalleri ortak rollere eşlenir"),
        ("Baseline sapma", "Her sinyalin normalinden sapması ölçülür"),
        ("Kök neden", "Alarmlar nedensel zincire dizilir"),
        ("Duruş tahmini", "HistGBDT modeli riski önceden işaretler"),
        ("What-If ve OEE", "Düzeltmenin OEE kazanımı sayısallaşır"),
    ],
    2.9,
)
bullets(
    [
        "Marka bağımsız rol haritası makineler arası karşılaştırmayı mümkün kılar. Örneğin Fanuc "
        "IsNotRunning sinyali ile Mitsubishi RUN_STATUS_START sinyali aynı role eşlenir.",
        "Her makinenin sinyalleri kendi içinde sağlam istatistiklerle (medyan, çeyrekler açıklığı) "
        "normalize edilir, böylece farklı marka ölçekleri ortak bir uzaya taşınır.",
        "Model eğitimi sızıntıya karşı korumalıdır. Zaman sırasına göre bölünür, yalnızca geçmiş "
        "öznitelikler kullanılır ve normalizasyon istatistikleri yalnızca eğitim verisinden hesaplanır.",
    ],
    4.65,
    gap=0.15,
)
page()

# ═══════════════════════════ 04 filo & OEE (chart) ═══════════════════════════
base("Filo Durumu", "Makine bazında OEE ve ana kayıp kaynağı", 4)
para(
    "Telemetrisi olan ve duruşu kaydedilen yedi makine, OEE değerine göre sıralanmıştır. "
    "Yeşil Fanuc, turuncu Mitsubishi iş miline sahip makineleri gösterir.",
    2.25,
    ML,
    CW,
    13.5,
    INK,
    lead=17,
)
oee_bars(MACHINES, ML, 2.95, 6.0, 3.3)
rect(7.4, 2.95, 5.05, 3.3, fill=GREEN_SOFT, line=GREEN, lw=1.1)
para("<b>Ne görüyoruz?</b>", 3.2, 7.62, 4.7, 12, GREEN, "ARB")
bullets(
    [
        "OEE değerleri yüzde 0 ile yüzde 74 arasında dağılır. En iyi makine bile yüzde 75'in altındadır, "
        "yani iyileştirme alanı geniştir.",
        "Makine 8'in OEE değeri 0'dır çünkü o dönemde üretim kaydı yoktur. Duruşu gerçektir, fakat "
        "Performans çarpanı 0 olduğu için OEE sıfırlanır.",
        "Tüm makinelerde OEE pratikte Kullanılabilirlik tarafından belirlenir.",
    ],
    3.55,
    x=7.62,
    w=4.6,
    size=10.5,
    gap=0.12,
)
page()

# ═══════════════════════════ 05 kök neden ═══════════════════════════
base("Kök Neden", "Baseline sapma ve alarm zinciri", 5)
para("Örnek olay: Makine 1, 12 Ocak 2026 saat 04:47.", 2.25, ML, CW, 14, MUTED)
rect(ML, 2.85, 3.6, 0.9, fill=GREEN_SOFT, line=GREEN, lw=1.5)
para("<b>AIR PRESSURE FAILED</b>", 3.08, ML, 3.6, 13.5, GREEN, "ARB", align=1)
para("kök neden", 3.38, ML, 3.6, 11, GREEN, align=1)
rect(ML + 4.35, 2.85, 3.6, 0.9, fill=white, line=HAIR, lw=1.0)
para("<b>Z-AXIS ZERO RETURN</b>", 3.08, ML + 4.35, 3.6, 13.5, INK, "ARB", align=1)
para("bu alarmın sonucu", 3.38, ML + 4.35, 3.6, 11, MUTED, align=1)
bullets(
    [
        "Olay anında birden fazla sinyal baseline değerinden sapar. run_state sinyali eksi 7,7 standart "
        "sapmaya iner, yani makine durur. cycle_time eksi 0,8 standart sapma gösterir.",
        "Aynı anda gelen alarmlar dizine göre değil, fiziksel nedensel önceliğe göre sıralanır. "
        "Kök neden hava basıncıdır, Z ekseni hatası onun sonucudur.",
        "Sistemin çıktısı yalnızca bir alarm değildir. Kanıtı, sıralı hipotezleri ve uygulanabilir "
        "bakım aksiyonunu içeren bir kök neden kartıdır.",
    ],
    4.1,
    gap=0.16,
)
page()

# ═══════════════════════════ 06 model + karşılaştırma ═══════════════════════════
base("Tahmin", "Duruş tahmin modeli ve eğitilen alternatifler", 6)
statcards(
    [
        ("0,73", "ROC-AUC · Fanuc"),
        ("2,38×", "Lift · Fanuc"),
        (f"%{DEP['recall']*100:.0f}", "Recall · held-out"),
        ("1,2×", "Lift · Mitsubishi"),
    ],
    2.25,
    h=1.2,
)
# comparison table
rows = [
    ("Fanuc (ayarlanmış)", "Fanuc", "0,73", "2,38×", "%69", "Dağıtılan model"),
    ("Fanuc (temel)", "Fanuc", "0,68", "2,0×", "%59", "Izgara aramadan önce"),
    (
        "Birleşik + z-norm",
        "Fanuc",
        "0,72",
        "2,33×",
        "%48",
        "Marka transferi katkı vermedi",
    ),
    (
        "Mitsubishi",
        "Mitsubishi",
        "0,61",
        "1,2×",
        "%97",
        "Taban %53, yüksek recall yanıltıcı",
    ),
]
cols = [
    ("Eğitim verisi", 3.0),
    ("Test", 1.7),
    ("ROC", 1.0),
    ("Lift", 1.0),
    ("Recall", 1.1),
    ("Not", 3.83),
]
x = ML
for label, wd in cols:
    rect(x, 3.7, wd, 0.4, fill=INK)
    para(f"<b>{label}</b>", 3.81, x + 0.1, wd - 0.18, 10, white, "ARB")
    x += wd
for i, r in enumerate(rows):
    y = 4.1 + i * 0.46
    fill = GREEN_SOFT if i == 0 else white
    vals = list(zip(r, [w for _, w in cols]))
    x = ML
    for j, (value, wd) in enumerate(vals):
        rect(x, y, wd, 0.46, fill=fill, line=HAIR, lw=0.6)
        para(
            value,
            y + 0.13,
            x + 0.1,
            wd - 0.18,
            10,
            GREEN if i == 0 else INK,
            "ARB" if i == 0 else "AR",
        )
        x += wd
para(
    "Fanuc hücresi {1,2,3,5,9} tek gerçek tahmin edilebilir gruptur. Mitsubishi makineleri zamanın "
    "yüzde 53'ünde zaten durur, bu yüzden yüksek recall değeri bilgi taşımaz ve lift yalnızca 1,2 katıdır.",
    6.35,
    ML,
    CW,
    12,
    MUTED,
    lead=15.5,
)
page()

# ═══════════════════════════ 07 model family (table) ═══════════════════════════
base("Tahmin", "Hangi algoritmayı neden seçtik", 7)
para(
    "Aynı held-out gelecekte, aynı öznitelik kümesiyle dört model ailesini ve iki saçma tabanı "
    "yarıştırdık. Karşılaştırma birleşik veride yapıldı (taban oran yüzde 25).",
    2.25, ML, CW, 13.5, INK, lead=17,
)
mcols = [("Model ailesi", 3.7), ("ROC", 1.2), ("Lift", 1.2), ("Not", 5.53)]
x = ML
for label, wd in mcols:
    rect(x, 2.78, wd, 0.42, fill=INK)
    para(f"<b>{label}</b>", 2.9, x + 0.1, wd - 0.18, 10.5, white, "ARB")
    x += wd
mrows = [
    ("HistGBDT (gradyan artırma)", "0,76", "2,09", "Seçilen aile, eksik değeri yerel işler", True),
    ("Random Forest", "0,75", "2,00", "Yakın ikinci", False),
    ("Lojistik Regresyon", "0,74", "1,98", "Doğrusal taban", False),
    ("MLP (sinir ağı, 64-24)", "0,68", "1,72", "Tablo veride en zayıf öğrenen", False),
    ("Denetimsiz AD skoru", "0,51", "1,07", "Tahminci olarak tesadüf seviyesi", False),
    ("Her zaman pozitif (taban)", "0,50", "1,00", "Anlamsız referans", False),
]
for i, (m, roc, lift, note, hi) in enumerate(mrows):
    y = 3.2 + i * 0.44
    fill = GREEN_SOFT if hi else white
    vals = [(m, 3.7, 0), (roc, 1.2, 1), (lift, 1.2, 1), (note, 5.53, 0)]
    x = ML
    for value, wd, align in vals:
        rect(x, y, wd, 0.44, fill=fill, line=HAIR, lw=0.6)
        para(value, y + 0.12, x + 0.1, wd - 0.18, 10, GREEN if hi else INK,
             "ARB" if hi else "AR", align=align)
        x += wd
rect(ML, 6.0, CW, 0.52, fill=GREEN_SOFT, line=GREEN, lw=1.1)
para(
    "<b>Neden HistGBDT:</b> en yüksek PR-AUC ve ROC. Eksik değeri kendisi işler, ölçekleme istemez ve "
    "doğrusal olmayan eşikleri yakalar. CNN ile transformer yalnızca denetimsiz anomali otokodlayıcısında "
    "denendi, tahmin için avantaj sağlamadı.",
    6.13, ML + 0.22, CW - 0.44, 10, INK, lead=12.5,
)
page()

# ═══════════════════════════ 08 risk timeline (chart) ═══════════════════════════
base("Tahmin", "Modelin ürettiği risk zaman çizgisi", 8)
para(
    "Aşağıdaki eğri, Makine 1 için modelin held-out dönemde ürettiği duruş riskidir. Bu, hiçbir "
    "müdahale yapılmadığında beklenen riski gösterir.",
    2.25,
    ML,
    CW,
    13.5,
    INK,
    lead=17,
)
risk_line(RISK, ML, 2.9, CW, 2.35)
bullets(
    [
        "Yeşil eğri modelin tahmin ettiği duruş riskidir, 0 ile 1 arasında değişir.",
        "Kırmızı kesikli çizgi alarm eşiğidir. Risk bu çizgiyi aştığında bir uyarı üretilir.",
        "Dönemin başında risk düşük ve düzdür. İlerleyen haftalarda risk sık sık eşiğin üzerine çıkar; "
        "model bu noktalarda yaklaşan duruşları işaretler.",
    ],
    5.45,
    gap=0.14,
)
page()

# ═══════════════════════════ 08 bridge ═══════════════════════════
base("OEE Kazanımı", "Tahmin OEE kazanımına nasıl bağlanıyor", 9)
para(
    "Tahminin OEE değeriyle bağı, ölçülmüş üç gerçeğe dayanır.",
    2.25,
    ML,
    CW,
    14,
    INK,
)
numbox(
    [
        (f"%{DEP['recall']*100:.0f} recall", "önemli duruşların yakalanan oranı"),
        (f"{DEP['caught_downtime_h']:.0f} saat", "yakalanan duruşların toplam süresi"),
        ("Önceden işaretlenir", "körlemesine değil, önceden bilinerek ele alınır"),
    ],
    2.85,
    h=1.45,
)
bullets(
    [
        "Model held-out dönemde önemli duruşların yüzde 69'unu yakaladı. Bu duruşların içindeki toplam "
        "duruş süresi 2062 saattir; bu, Fanuc hücresinin tüm plansız duruş süresinin yaklaşık yüzde 75'idir.",
        "Yakalanan duruşlar artık körlemesine yaşanmaz, önceden bilinir. Böylece duruş süresi ele "
        "alınabilir bir hedefe dönüşür.",
        "Bu sürenin azaltılmasının OEE etkisi What-If senaryolarında somutlaşır. En büyük plansız duruş "
        "kalemini yüzde 30 azaltmak Makine 1'de OEE'yi 18, Makine 5'te 15 puan yükseltir.",
    ],
    4.75,
    gap=0.15,
)
page()

# ═══════════════════════════ 09 makineler arası örüntü (chart) ═══════════════════════════
base("Örüntü", "Makineler arası örüntü, senkron duruşlar", 10)
para(
    "Soru şu: iki veya daha fazla makine aynı saatte plansız durduğunda, bu durum şansın ve ortak "
    "vardiya programının ötesinde bir bağ mıdır?",
    2.25,
    ML,
    CW,
    14,
    INK,
    lead=17,
)
bars = [
    (
        "Gözlemlenen",
        SYNC["observed_co_stop_hours"],
        GREEN,
        "gerçekte yaşanan eş zamanlı duruş",
    ),
    (
        "Beklenen, vardiya ritmi",
        round(SYNC["daily"]["exp"]),
        AMBER,
        "yalnız ortak saat düzeni açıklasaydı",
    ),
    ("Beklenen, rastgele", round(SYNC["free"]["exp"]), GRAY, "tamamen tesadüf olsaydı"),
]
for i, (lab, v, col, note) in enumerate(bars):
    y = 3.05 + i * 0.62
    para(lab, y + 0.02, ML, 3.0, 12, INK, "ARB" if i == 0 else "AR")
    rect(ML + 3.05, y, (v / 760) * 5.4, 0.38, fill=col)
    para(
        f"<b>{v} saat</b>", y + 0.05, ML + 3.2 + (v / 760) * 5.4, 1.2, 11.5, INK, "ARB"
    )
    para(note, y + 0.06, ML + 3.2 + (v / 760) * 5.4 + 1.0, 3.6, 10, MUTED)
para(
    f"İstatistik sonucu: z eşittir {tr(SYNC['daily']['z'])}, p küçüktür 0,001. Senkronizasyon ortak "
    "vardiya programıyla açıklanamıyor.",
    5.0,
    ML,
    CW,
    13.5,
    INK,
    lead=17,
)
rect(ML, 5.5, CW, 0.95, fill=GREEN_SOFT, line=GREEN, lw=1.2)
para(
    "<b>İçgörü:</b> 708 saatlik eş zamanlı duruşun 564 saati ortak vardiya ile açıklanır. Geri kalan "
    "yaklaşık 144 saat vardiyayla açıklanamayan gerçek bir bağdır. Bu, duruşların bir bölümünün "
    "makineye özel değil sistemik olduğunu gösterir. Ortak bir kök nedeni (örneğin paylaşılan besleme "
    "veya altyapı) düzeltmek, aynı anda birden çok makinenin OEE değerini yükseltebilir.",
    5.68,
    ML + 0.22,
    CW - 0.44,
    11.5,
    INK,
    lead=15,
)
page()

# ═══════════════════════════ 10 senaryolar ═══════════════════════════
base("Senaryolar", "What-If senaryoları, fiziksel kazanım", 11)
para(
    "Her senaryo ham OEE bileşenlerinden aynı formülle yeniden hesaplanır. Değerler fiziksel "
    "kazanımdır; para birimi içermez.",
    2.2,
    ML,
    CW,
    13.5,
    INK,
    lead=17,
)
cols = [("Senaryo", 5.6), ("Kaldıraç", 1.6), ("ΔOEE", 1.3), ("Kazanılan süre", 2.13)]
x = ML
for label, wd in cols:
    rect(x, 2.78, wd, 0.42, fill=INK)
    para(f"<b>{label}</b>", 2.9, x + 0.1, wd - 0.18, 10.5, white, "ARB")
    x += wd
srows = [
    (
        "S1 · Makine 1 · en büyük plansız kalem -%30",
        "Kullanılabilirlik",
        "+18,0 pp",
        "625 saat çalışma",
        GREEN,
        GREEN_SOFT,
    ),
    (
        "S2 · Makine 5 · en büyük plansız kalem -%30",
        "Kullanılabilirlik",
        "+15,3 pp",
        "420 saat çalışma",
        INK,
        white,
    ),
    (
        "S3 · Makine 3 · çevrim süresi +%10",
        "Performans",
        "0,0 pp",
        "veri P kolunu desteklemiyor",
        MUTED,
        white,
    ),
    (
        "S4 · Tesis · bağlantı kesintisi giderilir",
        "Bağlantı / IT",
        "makine dışı",
        "663 saat bağlantı",
        MUTED,
        white,
    ),
]
for i, (name, lev, doee, recov, colr, fill) in enumerate(srows):
    y = 3.2 + i * 0.54
    vals = [(name, 5.6, 0), (lev, 1.6, 0), (doee, 1.3, 2), (recov, 2.13, 0)]
    x = ML
    for value, wd, align in vals:
        rect(x, y, wd, 0.5, fill=fill, line=HAIR, lw=0.6)
        para(
            value,
            y + 0.13,
            x + 0.1,
            wd - 0.2,
            10,
            colr,
            "ARB" if i == 0 else "AR",
            align=align,
        )
        x += wd
bullets(
    [
        "S1 ve S2 Kullanılabilirlik kaldıracıdır ve gerçek kazanım üretir. En büyük plansız duruş kalemini "
        "azaltmak iki farklı makinede de OEE'yi belirgin biçimde yükseltir.",
        "S3 Performans kaldıracını test eder ve ölçülen sonuç sıfırdır. Üretim yapılan 777 makine gününün "
        "605'inde Performans tam olarak 1, 172'sinde 0'dır ve arada hiçbir gün yoktur. Bu veride Performans "
        "ayrıştırıcı değildir, bu yüzden çevrim iyileştirmesi OEE'yi hareket ettiremez.",
        "S4 bağlantı kesintisinin giderilmesidir. 663 saatlik bağlantı görünürlüğü geri kazanılır, fakat "
        "bu bir IT aksiyonudur ve makine OEE'sine yazılmaz. Kalite kaldıracı da hurda kaydı sıfır olduğu "
        "için inerttir.",
    ],
    5.45,
    size=10.5,
    gap=0.11,
)
page()

# ═══════════════════════════ 12 sonuç ═══════════════════════════
base("Sonuç", "Tahmin eder, açıklar, sayısallaştırır", 12)
statcards(
    [
        ("2,38×", "Fanuc duruş tahmini lift"),
        ("2062 saat", "önceden yakalanan duruş süresi"),
        ("z = 5,16", "senkron duruş anlamlılığı"),
        ("+18 puan", "en iyi What-If OEE kazanımı"),
    ],
    2.45,
)
bullets(
    [
        "Sistem tek bir hatta üç işi birlikte yapar: Fanuc hücresinde duruşu önceden tahmin eder, kök "
        "nedeni alarm zinciriyle açıklar ve düzeltmenin OEE kazanımını sayısallaştırır.",
        "Her iddia bir null model ile sınanmıştır. Olumsuz bulguları gizlemedik, çünkü güven dürüstlükten "
        "gelir.",
        "Canlı arayüz tahminden kök nedene ve What-If analizine uzanan akışı uçtan uca gösterir.",
    ],
    4.5,
    gap=0.18,
)
page()

c.save()
print(f"kaydedildi: {OUT}  ({c.getPageNumber()-1} sayfa)")
