# -*- coding: utf-8 -*-
"""Generate the presentation PLAN as a PDF (slide-by-slide: on-slide content, speaker script,
live-demo action). Targets the Gold + Platinum judging bars. Turkish.

Run: uv run python scripts/build_presentation_plan.py
"""
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                KeepTogether, HRFlowable)

OUT = Path("trexCloud_Sunum_Plani.pdf")

# Turkish-capable fonts (macOS)
pdfmetrics.registerFont(TTFont("AR", "/System/Library/Fonts/Supplemental/Arial.ttf"))
try:
    pdfmetrics.registerFont(TTFont("ARB", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"))
except Exception:
    pdfmetrics.registerFont(TTFont("ARB", "/System/Library/Fonts/Supplemental/Arial.ttf"))

INK = colors.HexColor("#16201c")
GREEN = colors.HexColor("#1f9d57")
GREEN_BG = colors.HexColor("#eaf6ef")
MUTED = colors.HexColor("#5b6b63")
LINE = colors.HexColor("#d6e0da")
MEDAL = {"BRONZ": colors.HexColor("#b07a3a"), "GÜMÜŞ": colors.HexColor("#8a99a3"),
         "ALTIN": colors.HexColor("#d99a2b"), "PLATİN": colors.HexColor("#2f9e8f"),
         "BONUS": colors.HexColor("#4c78a8"), "—": MUTED}

S = ParagraphStyle("body", fontName="AR", fontSize=9.5, leading=13.5, textColor=INK)
SB = ParagraphStyle("bullet", parent=S, leftIndent=8, spaceAfter=1.5)
LBL = ParagraphStyle("lbl", fontName="ARB", fontSize=7.5, leading=10, textColor=GREEN)
TITLE = ParagraphStyle("title", fontName="ARB", fontSize=13, leading=15, textColor=INK)
H1 = ParagraphStyle("h1", fontName="ARB", fontSize=24, leading=27, textColor=INK)
SUB = ParagraphStyle("sub", fontName="AR", fontSize=11, leading=16, textColor=MUTED)


def lbl(t): return Paragraph(t, LBL)
def p(t): return Paragraph(t, S)
def bullets(items): return [Paragraph("•&nbsp;&nbsp;" + b, SB) for b in items]


def slide_card(n, title, medal, on_slide, talk, demo):
    mc = MEDAL.get(medal, MUTED)
    badge = Table([[Paragraph(f'<font color="white"><b>{n:02d}</b></font>', TITLE)]],
                  colWidths=[13 * mm], rowHeights=[13 * mm])
    badge.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GREEN),
                               ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                               ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    tag = Table([[Paragraph(f'<font color="white"><b>{medal}</b></font>',
                            ParagraphStyle("t", fontName="ARB", fontSize=8, textColor=colors.white))]],
                colWidths=[22 * mm])
    tag.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), mc),
                             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                             ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    head = Table([[badge, Paragraph(title, TITLE), tag]],
                 colWidths=[15 * mm, 125 * mm, 24 * mm])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                              ("LEFTPADDING", (1, 0), (1, 0), 6)]))

    body = [head, Spacer(1, 5),
            lbl("SLAYTTA İÇERİK"), *bullets(on_slide), Spacer(1, 4),
            lbl("KONUŞMA METNİ"), p(talk), Spacer(1, 4),
            lbl("DEMO / GÖSTERİM"), p(demo)]
    wrap = Table([[body]], colWidths=[170 * mm])
    wrap.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.7, LINE),
                              ("LEFTPADDING", (0, 0), (-1, -1), 12),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                              ("TOPPADDING", (0, 0), (-1, -1), 10),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                              ("BACKGROUND", (0, 0), (-1, -1), colors.white)]))
    return KeepTogether([wrap, Spacer(1, 9)])


SLIDES = [
    (1, "Kapak — trexCloud: Öngörücü OEE &amp; Kök-Neden Analizi", "—",
     ["Proje adı, takım, tek cümle: <b>“Duruşu önce tahmin et, nedenini açıkla, OEE/€ etkisini ölç.”</b>",
      "Hedef rozeti: <b>Altın + Platin</b>."],
     "Kısa ve iddialı bir giriş: “Bir CNC + lazer tesisinin verisinden uçtan uca bir öngörücü "
     "OEE ve kök-neden sistemi kurduk; hedefimiz Altın ve Platin seviyeleri.”",
     "Açılış ekranı: React panosu (siyah-yeşil), ‘Tahmin → Aksiyon’ görünümü açık."),

    (2, "Problem &amp; Madalya Hedefi", "—",
     ["İki görev: <b>What-If/OEE</b> (MES) ve <b>Kök-Neden</b> (makine izleme).",
      "Madalya merdiveni: Bronz (listele) → Gümüş (eşleştir+Pareto) → <b>Altın</b> (baseline sapma + "
      "nedensellik) → <b>Platin</b> (çapraz-makine + ΔOEE + finansal).",
      "Biz Altın ve Platin’i hedefliyoruz; aşağısı zaten kapsanıyor."],
     "Jüriye yol haritasını ver: her rozetin ne istediğini bir cümlede söyle ve “biz en üst iki "
     "rozeti hedefliyoruz, alttakileri de eksiksiz yapıyoruz” de.",
     "Madalya kriterleri görseli (verilen fotoğraf)."),

    (3, "Veri Gerçeği — Dürüstlük farkımız", "—",
     ["12 makine, ~7.4M telemetri satırı, cp1254 (Türkçe), UTC, ms.",
      "Katalogun vaat ettiği ‘kanıt sinyalleri’ (servo sıcaklık / path-load) <b>gerçekte boş</b> "
      "(en yoğun makine Makine 7’de bile 0 / 28 satır).",
      "Gerçekte akan: cycle_time, run_state, run_time, axis_position. Nightwatch↔MES eşleşmesi 162/162 (%100)."],
     "En güçlü farkımız bu: “Jüri veriyi bizden iyi biliyor. O yüzden önce dürüst bir veri "
     "envanteri çıkardık — dokümanın vaat ettiği sinyallerin akmadığını tespit ettik ve modeli "
     "gerçekten akan sinyaller üzerine kurduk.” Bu güven inşa eder.",
     "İsteğe bağlı: sinyal kullanılabilirliği tablosu (rapor 01)."),

    (4, "Mimari — Uçtan uca hat", "—",
     ["Kanonik sinyal katmanı (vendor-bağımsız roller) → çapraz-makine’yi mümkün kılar.",
      "Akış: <b>AD (baseline sapma)</b> → <b>RCA</b> → <b>What-If/OEE</b> → <b>Tahmin</b>.",
      "Rejim ayrımı: Fanuc {1,2,3,5,9} · Mitsubishi {7,8} · telemetrisiz {4,6,10,TurboCut,ARES}."],
     "Sistemi bir resimde anlat: Fanuc IsNotRunning ile Mitsubishi RUN_STATUS_START aynı role "
     "haritalanıyor; bu sayede makineler arası ortak bir dil kuruyoruz.",
     "Mimari diyagram (statik görsel)."),

    (5, "Bronz + Gümüş — temel sorgular &amp; Pareto", "GÜMÜŞ",
     ["Birleşik olay akışı: alarm + duruş + offline + AD penceresi tek şemada.",
      "Alarm↔duruş zaman-damgası eşleştirme (merge_asof).",
      "Pareto: <b>arıza vs bağlantı</b> ayrımı. TurboCut en büyük kaynak — ama bağlantı kesintisi (IT)."],
     "Hızlı geç: “Bronz ve Gümüş bizde temel; ama kritik bir ayrım yaptık — en büyük duruş "
     "kalemi aslında bir makine arızası değil, bağlantı kesintisi. Bunu ayırmazsanız yanlış "
     "yatırım yaparsınız.”",
     "Genel Bakış panosu → Pareto grafiği (kırmızı=arıza, gri=bağlantı)."),

    (6, "ALTIN — Baseline sapma + çok-sinyal → nedensellik (canlı)", "ALTIN",
     ["Vaka: <b>Makine 1, 12 Oca 2026 04:47</b>.",
      "Baseline sapma imzası (robust-z): <b>run_state ▼7.7σ</b> (makine duruyor), cycle_time sapıyor.",
      "Alarm kaskadı nedensel önceliğe göre: <b>AIR PRESSURE FAILED → Z-AXIS ZERO RETURN</b>, "
      "kök = <b>AIR PRESSURE</b> (indeks değil, nedensellik kuralı).",
      "Dürüst not: sapma burada eşzamanlı kanıt, öngörücü değil."],
     "Altın’ın kalbi: “Birden çok sinyalin baseline’dan saptığını saptıyoruz, sonra alarmları "
     "nedensel önceliğe göre sıralayıp kök nedene iniyoruz. Z-ekseni hatası bir sonuç; gerçek "
     "kök neden hava basıncı.” Dürüstlük: sapmanın eşzamanlı olduğunu açıkça söyle.",
     "‘Tahmin → Aksiyon’ panosu, bölüm 2: kaskad + sapma çubukları + hipotezler."),

    (7, "Bonus — Duruş tahmini (madalyanın ötesi)", "BONUS",
     ["Fanuc HistGBDT: <b>ROC 0.73, 2.38× kazanç, %44 dönem isabeti</b> (taban %18).",
      "Sızıntısız: makine-içi kronolojik split, geçmiş-yalnız öznitelik, makine-içi z-norm.",
      "Dürüst: makine-içi ROC ≈0.72 — ‘mükemmel’ değil, kullanışlı bir <b>risk sıralayıcı</b>."],
     "“Madalya tahmin istemiyordu ama biz bir adım öteye gidip duruşu 60 dk önceden tahmin "
     "ediyoruz. Abartmıyoruz: bu iyi bir risk sıralayıcı, kâhin değil — ve neden Fanuc’a "
     "sınırlı olduğunu da biliyoruz (sinyal kullanılabilirliği).”",
     "‘Tahmin → Aksiyon’: risk zaman çizgisi + gerçek duruş ×’leri + dönem seçimi."),

    (8, "PLATİN — Çapraz-makine örüntüleri (null-model’li)", "PLATİN",
     ["Eşzamanlı duruşlar: <b>z=5.16, p&lt;0.001</b> — saat-içi ritmini koruyan null’ın bile ötesinde "
      "(yani ‘herkes vardiyada durdu’ değil).",
      "CONNECTIVITY totolojisini düzelttik: eski #1 ‘sistemik’ bulgu, tek kaydın kopyalanmasıydı.",
      "Rejim haritası (sinyalden türetildi). Kümeleme dürüst okuması: {1,2,3,9} <b>yavaş ortak zarf</b>, "
      "akut arıza yayılımı DEĞİL (türev alınınca r≈0)."],
     "Platin’in en kritik kriteri. “Her çapraz-makine iddiamızı bir null-model’den geçirdik. "
     "Eşzamanlı duruşlar şansın ve vardiya programının ötesinde gerçek. Ama kümeyi abartmadık — "
     "bu ortak bir çalışma ritmi, eşzamanlı arıza değil. Doğru olmayanı söylemiyoruz.”",
     "‘Çapraz Makine’ panosu: senkronizasyon çubukları + rejim haritası + dürüst kümeleme."),

    (9, "PLATİN — What-If + Finansal öneri (canlı)", "PLATİN",
     ["W1 senaryosu: bir makinenin plansız duruşunu %X azalt → A yükselir.",
      "ΔOEE ayrışımı (A/P/Q ayrı ayrı), geri kazanılan saat + ek parça.",
      "Finansal: net fayda / geri ödeme — <b>tüm € değerleri açıkça VARSAYIM</b> (veride maliyet yok)."],
     "“Çözümün etkisini sadece anlatmıyoruz, sayısallaştırıyoruz. Kaydırıcıyı oynatınca OEE ve "
     "€ canlı güncelleniyor. Maliyet verisi olmadığı için varsayımları açıkça etiketliyoruz — "
     "bu da dürüstlüğün parçası.”",
     "‘What-If’ kaydırıcısını canlı oynat: ΔOEE çubukları + € kartı anında değişiyor."),

    (10, "Dürüst Limitler — neden güveniyorsunuz", "—",
     ["Kondisyon sinyalleri (sıcaklık/yük) boş → tavanı veri belirliyor, model değil.",
      "Mitsubishi {7,8}: 60dk’da %53 duruş → tahmin doygun; 30dk ufkunda lift 1.59 (atılmadı, RCA/OEE’de).",
      "Tüm plansız duruşlar tek etiket (‘Duruş’) → ‘ne/ne zaman’ var, ‘neden’ yok (alarm yalnız M1&amp;2).",
      "Q simüle (hurda kaydı yok), kör makineler MES-yalnız."],
     "Bunu biz söyleyince güven artar: “Neyi tahmin EDEMEDİĞİMİZİ de biliyoruz. Limitleri jüri "
     "bulmadan biz koyuyoruz — çünkü dürüst bir analiz, parlak ama yanlış bir analizden iyidir.”",
     "—"),

    (11, "Sonuç &amp; Etki", "—",
     ["Bronz → Platin: dört seviye de kapsandı, en üst ikisi güçlü.",
      "Çıktı: tahmin (Fanuc 2.38×) + kök-neden (kaskad) + sayısal ΔOEE/€ önerisi.",
      "Sonraki adım: makine-bazlı kalibrasyon, Mitsubishi için kısa-ufuk / time-to-stop."],
     "Kapanış: “Dürüst, çalışan, uçtan uca bir sistem kurduk — tahmin eder, açıklar, "
     "sayısallaştırır. Ve filodaki her makine için neden öyle davrandığımızı biliyoruz.”",
     "Panoda ‘Genel Bakış’a dön — bütünlüğü göster."),

    (12, "Yedek — Teknik Ek (soru gelirse)", "—",
     ["Sızıntı kontrolleri: kronolojik split, geçmiş-yalnız öznitelik, iç-CV ile hiperparametre.",
      "Rejim-model tablosu: birleşik vs Fanuc vs Mitsubishi; z-norm kazancı.",
      "Metodoloji: robust-z/EWMA zarflar, nedensel-öncelik kaskad, circular-shift null."],
     "Sadece soru gelirse aç. Metrikleri ve sızıntı önlemlerini burada savun.",
     "Raporlar: 03–06 (analysis/reports)."),
]

DEMO_FLOW = ("<b>Demo akışı (4 dakika):</b> Genel Bakış (Pareto: arıza vs bağlantı) → "
             "Tahmin→Aksiyon (risk zaman çizgisi → Altın: kaskad + sapma) → "
             "What-If (kaydırıcı: ΔOEE + €) → Çapraz Makine (Platin: senkronizasyon + rejimler).")


def build():
    doc = SimpleDocTemplate(str(OUT), pagesize=A4,
                            leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=18 * mm, bottomMargin=16 * mm,
                            title="trexCloud — Sunum Planı")
    el = []
    # title page band
    band = Table([[Paragraph('<font color="white"><b>trexCloud</b></font>',
                             ParagraphStyle("b", fontName="ARB", fontSize=20, textColor=colors.white))]],
                 colWidths=[170 * mm], rowHeights=[16 * mm])
    band.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), INK),
                              ("LEFTPADDING", (0, 0), (-1, -1), 14),
                              ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    el += [band, Spacer(1, 10),
           Paragraph("Sunum Planı — Öngörücü OEE &amp; Kök-Neden", H1), Spacer(1, 4),
           Paragraph("Slayt-slayt: ne yazılacak · ne konuşulacak · demoda ne gösterilecek. "
                     "Hedef: <b>Altın</b> + <b>Platin</b>.", SUB),
           Spacer(1, 10), HRFlowable(width="100%", color=LINE), Spacer(1, 8)]
    flow = Table([[Paragraph(DEMO_FLOW, ParagraphStyle("d", parent=S, textColor=INK))]],
                 colWidths=[170 * mm])
    flow.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GREEN_BG),
                              ("BOX", (0, 0), (-1, -1), 0.7, GREEN),
                              ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                              ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9)]))
    el += [flow, Spacer(1, 14)]
    for s in SLIDES:
        el.append(slide_card(*s))

    def footer(canvas, d):
        canvas.setFont("AR", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(20 * mm, 10 * mm, "trexCloud · Sunum Planı")
        canvas.drawRightString(190 * mm, 10 * mm, f"s. {d.page}")

    doc.build(el, onFirstPage=footer, onLaterPages=footer)
    print(f"wrote {OUT}  ({OUT.stat().st_size//1024} KB, {len(SLIDES)} slayt)")


if __name__ == "__main__":
    build()
