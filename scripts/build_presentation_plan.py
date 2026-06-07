# -*- coding: utf-8 -*-
"""Generate the presentation PLAN as a PDF (slide-by-slide: on-slide content, speaker script,
live-demo action). Targets the Gold + Platinum judging bars. Turkish.

Run: uv run python scripts/build_presentation_plan.py
"""
import json
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
PM = json.loads(Path("analysis/artifacts/pm_value.json").read_text(encoding="utf-8"))
SCENARIOS = json.loads(Path("analysis/artifacts/scenarios.json").read_text(encoding="utf-8"))["rows"]
DEPLOYED = PM["deployed"]
ECON = PM["sensitivity"]["economic_optimum"]


def first_font(*paths):
    return next(str(p) for p in map(Path, paths) if p.exists())


pdfmetrics.registerFont(TTFont("AR", first_font(
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "C:/Windows/Fonts/arial.ttf")))
pdfmetrics.registerFont(TTFont("ARB", first_font(
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf")))

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

    (7, "Tahmin → OEE → Finansal Değer", "BONUS",
     [f"Fanuc HistGBDT: <b>ROC 0.73, lift 2.38×</b>; held-out duruş recall "
      f"<b>%{DEPLOYED['recall']*100:.1f}</b> ({DEPLOYED['caught_stops']}/{DEPLOYED['significant_stops']}).",
      f"e=%35 varsayımıyla <b>+{DEPLOYED['oee']['delta']['dOEE']*100:.2f} puan OEE</b> ve "
      f"{DEPLOYED['financial']['annualized']['prevented_h']:.0f} saat/yıl projeksiyonu.",
      f"722 kontrol × 300 € varsayımı neti negatife çeker; retrospektif eşik "
      f"{ECON['threshold']:.2f} → <b>{ECON['annualized_net_eur']:,.0f} €/yıl</b>."],
     "“Recall yakalanabilecek duruş havuzunu belirliyor; alarm sayısı ve isabeti ise kontrol "
     "maliyetini. Böylece ROC/lift katmanını ilk kez doğrudan OEE ve euroya bağlıyoruz. "
     "Varsayılan maliyetlerde dağıtılan eşiğin ekonomik olmadığını saklamıyoruz.”",
     "‘Tahmin → Aksiyon’: risk zaman çizgisi → Kestirimci Bakım Getirisi kartı → varsayım kaydırıcıları."),

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

    (9, "PLATİN — İncelenebilir Senaryo Kataloğu", "PLATİN",
     [f"S1 Makine 1 / Duruş −30%: <b>+{SCENARIOS[0]['delta_OEE_pp']:.2f} puan OEE</b>, "
      f"{SCENARIOS[0]['recovered_runtime_h']:.0f} saat runtime.",
      "S2: plansız→planlı sınıflandırma A'yı değiştirir ama runtime yaratmaz. "
      "S3: ProductSum=0 olduğundan performans kolu inerttir.",
      f"S4: {SCENARIOS[3]['recovered_schedule_h']:.0f} saat bağlantı görünürlüğü; "
      "<b>IT aksiyonu, makine OEE'si değil</b>. Tüm € değerleri VARSAYIM."],
     "“Katalog yalnız iyi görünen senaryoları seçmiyor. Runtime yaratmayan sınıflandırmayı, "
     "veri olmadığı için inert kalan performans kolunu ve OEE'ye yazılmayan bağlantı aksiyonunu "
     "aynı tabloda gösteriyoruz.”",
     "‘Senaryo Kataloğu’ tablosunu ΔOEE veya net € sütununa göre sırala."),

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

    (12, "Canlı Arayüz — Genel Bakış", "—",
     ["Üst KPI'lar: tesis OEE'si, toplam plansız duruş ve Fanuc tahmin lift'i.",
      "Makine kartları rejim rengini, OEE'yi ve duruş saatini gösterir.",
      "Seçilen makinenin A/P/Q ayrışımı sağ panelde açılır."],
     "Yeşil Fanuc tahmin hücresini, kehribar Mitsubishi RCA/OEE grubunu ve gri telemetrisiz "
     "makineleri açıkla. Bir makine seçerek KPI ayrışımını göster.",
     "Genel Bakış ekranı — makine filosu ve KPI ayrışımı."),

    (13, "Canlı Arayüz — Pareto", "GÜMÜŞ",
     ["Kırmızı = giderilebilir makine duruşu.",
      "Gri = System Offline; IT/ağ aksiyonu.",
      "TurboCut büyük kayıp kaynağıdır fakat telemetrisi yoktur."],
     "Bağlantı kaybını makine arızası saymanın yanlış ekibe ve yanlış yatırıma götüreceğini söyle.",
     "Genel Bakış ekranı — Duruş Pareto grafiği."),

    (14, "Canlı Arayüz — Tahmin Zaman Çizgisi", "BONUS",
     ["Yeşil çizgi model riski; kırmızı kesik çizgi dağıtılan eşik 0.1778.",
      "Kırmızı çarpılar gerçekleşen ≥15 dk plansız duruşlar.",
      "Alt kutular yüksek-risk dönemlerini inceleme sırasına koyar."],
     "Modelin bu geleceği eğitimde görmediğini ve işaretlerin gerçek held-out duruşlar olduğunu vurgula.",
     "Tahmin → Aksiyon, bölüm 1."),

    (15, "Canlı Arayüz — Kök-Neden", "ALTIN",
     ["Alarm kaskadı nedensel önceliğe göre sıralanır.",
      "AIR PRESSURE kök neden; Z-axis alarmı sonuçtur.",
      "Telemetri, hipotez ve önerilen aksiyon aynı paneldedir."],
     "Modelin yalnız alarm vermediğini; kanıtı, hipotezi ve uygulanabilir aksiyonu bağladığını söyle.",
     "Tahmin → Aksiyon, bölüm 2."),

    (16, "Canlı Arayüz — Kestirimci Bakım Değeri + What-If", "BONUS",
     ["Üst kart yalnız yakalanan duruşlara model-atfedilebilir OEE/€ yazar.",
      "Etkililik ve maliyetler varsayım; recall/precision held-out ölçümdür.",
      "Alt kart genel What-If motorudur; kullanıcı yüzde ve maliyetleri değiştirir."],
     "Model-atfedilebilir değer ile genel operasyon senaryosunun iki farklı hesap olduğunu açıkla. "
     "Negatif ROI'nin saklanmadığını özellikle belirt.",
     "Tahmin → Aksiyon, bölümler 3 ve 4."),

    (17, "Canlı Arayüz — Senaryo Kataloğu", "PLATİN",
     ["ΔA / ΔP / ΔQ / ΔOEE aynı tabloda denetlenir.",
      "Runtime ve schedule kazanımı ayrıdır.",
      "Tablo herhangi bir sütuna göre sıralanabilir."],
     "S1-S4 satırlarının neden farklı davrandığını kısaca yorumla; özellikle S4'ün IT sahipliğini söyle.",
     "Tahmin → Aksiyon, bölüm 5."),

    (18, "Canlı Arayüz — Çapraz Makine", "PLATİN",
     ["Eski connectivity sonucu kayıt tekrarı olarak teşhis edilir.",
      "708 eşzamanlı duruş null-model beklentisinin üstündedir.",
      "Rejim haritası ve türev korelasyonu iddianın sınırlarını gösterir."],
     "Gerçek senkronizasyonu gösterirken akut arıza yayılımı iddia etmediğimizi söyle. "
     "Bu ekran projenin dürüst Platin kanıtıdır.",
     "Çapraz Makine ekranı."),
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
