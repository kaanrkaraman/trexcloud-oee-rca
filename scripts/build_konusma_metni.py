# -*- coding: utf-8 -*-
"""Konuşma metni + olası jüri soruları (çalışma dökümanı).
Her slayt bir paragraf; ardından o slaytta gelebilecek sorular ve kısa cevaplar.
Run: uv run python scripts/build_konusma_metni.py -> trexCloud_Konusma_Metni.pdf
"""
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, HRFlowable,
                                KeepTogether)


def first_font(*paths):
    return next(str(p) for p in map(Path, paths) if p.exists())


pdfmetrics.registerFont(TTFont("AR", first_font(
    "/System/Library/Fonts/Supplemental/Arial.ttf", "C:/Windows/Fonts/arial.ttf")))
pdfmetrics.registerFont(TTFont("ARB", first_font(
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "C:/Windows/Fonts/arialbd.ttf")))

GREEN = HexColor("#0F7A52")
INK = HexColor("#16201C")
MUTED = HexColor("#5B675F")
HAIR = HexColor("#D9DFDB")

st_title = ParagraphStyle("t", fontName="ARB", fontSize=19, textColor=INK, leading=23, spaceAfter=2)
st_sub = ParagraphStyle("s", fontName="AR", fontSize=10.5, textColor=MUTED, leading=14, spaceAfter=10)
st_h = ParagraphStyle("h", fontName="ARB", fontSize=13, textColor=GREEN, leading=16,
                      spaceBefore=10, spaceAfter=5)
st_body = ParagraphStyle("b", fontName="AR", fontSize=11, textColor=INK, leading=16,
                         alignment=TA_LEFT, spaceAfter=7)
st_qlbl = ParagraphStyle("ql", fontName="ARB", fontSize=9.5, textColor=MUTED, leading=12,
                         spaceBefore=6, spaceAfter=3)
st_q = ParagraphStyle("q", fontName="ARB", fontSize=10, textColor=INK, leading=14, spaceBefore=4,
                      leftIndent=10)
st_a = ParagraphStyle("a", fontName="AR", fontSize=10, textColor=INK, leading=14.5, leftIndent=10,
                      spaceAfter=2)

doc = SimpleDocTemplate("trexCloud_Konusma_Metni.pdf", pagesize=A4,
                        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.6 * cm, bottomMargin=1.6 * cm)
E = []


def slide(title, speech, qa):
    block = [Paragraph(title, st_h), Paragraph(speech, st_body)]
    if qa:
        block.append(Paragraph("OLASI SORULAR VE CEVAPLAR", st_qlbl))
        for q, a in qa:
            block.append(Paragraph("S: " + q, st_q))
            block.append(Paragraph("C: " + a, st_a))
    block.append(Spacer(1, 4))
    E.append(KeepTogether(block))
    E.append(HRFlowable(width="100%", thickness=0.5, color=HAIR, spaceBefore=4, spaceAfter=2))


E.append(Paragraph("trexCloud — Konuşma Metni ve Jüri Soruları", st_title))
E.append(Paragraph("Her başlık bir slayttır. Önce söyleyeceğin paragraf, sonra o slaytta gelebilecek "
                   "sorular ve kısa cevaplar. Sayılar: 2,38× lift · %69 recall · 2062 saat · z = 5,16 · +18 puan.",
                   st_sub))

# ───────────────────────── 1 ─────────────────────────
slide("Slayt 1 — Açılış ve motivasyon",
      "Biz elimizdeki veriyi değerlendirdikten sonra, projenin isterlerini tamamlamanın yanında nasıl "
      "ek bir katkı yapabiliriz diye düşündük. Bu yüzden kök neden analizini (RCA) ve What-If analizini "
      "kestirimci bakım, yani predictive maintenance ile birleştirdik. Böylece sadece olmuş bir duruşu "
      "açıklamakla kalmayıp, duruşu önceden tahmin edip bu iki analizi proaktif hale getirdik.",
      [("İstenen yalnız RCA ve What-If'ti, neden tahmin eklediniz?",
        "İsterleri zaten karşıladık. Üstüne, duruşu önceden işaretleyince RCA ve What-If reaktif olmaktan "
        "çıkıp önleyici hale geliyor. Katkımız tam olarak bu birleştirme."),
       ("Kestirimci bakım gerçekten çalışıyor mu, yoksa slogan mı?",
        "Çalışıyor ama dürüst sınırlarıyla. Yalnız Fanuc hücresinde anlamlı; orada lift 2,38. Bunu birazdan "
        "sayılarla göstereceğim.")])

# ───────────────────────── 2 ─────────────────────────
slide("Slayt 2 — Veri",
      "Elimizde çeşitli markalardan makineler var; beş makinenin iş mili Fanuc'tan, iki makinenin iş mili "
      "Mitsubishi'den. Bu makinelerden düşük frekanslı MES verileri ve yüksek frekanslı nightwatch verileri "
      "sunulmuş. Geliştirmemiz istenen metrik, üretimin en temel göstergesi olan OEE; yani Kullanılabilirlik "
      "çarpı Performans çarpı Kalite. Bu veri setinde Kalite tamamen 1 olarak tanımlı, yani hiç ıskarta "
      "(scrap) ürün çıkmamış. Dolayısıyla çalışmayı Kullanılabilirlik ve Performans üzerinden yürütebiliyoruz. "
      "Veriyi açıp incelediğimizde, yani EDA aşamasında, en büyük duruş kaynağının arızalardan çok System "
      "Offline durumu olduğunu gördük. Bu da makine arızası değil bağlantı kesintisi olduğu için OEE'ye "
      "yazılmıyor.",
      [("Veriye dayalı gösterimler yapıyorsunuz, veriden nasıl anlam çıkardınız?",
        "Veriyi doğrudan yapay zekaya atmak yerine açıp manuel olarak değerlendirmenin çok değerli olduğunu "
        "düşünüyoruz. Çünkü yapay zeka ne anlatırsa anlatsın, üzerinde çalıştığınız veriyi kendiniz görmeden "
        "bir şeye ikna olmak zor. Bu yüzden CSV ve JSON içeriklerini tek tek açıp ne olduğunu anlamlandırdık "
        "ve makineler arasında içeriğin nasıl değiştiğini gördük."),
       ("Veri senkronizasyonunu, farklı makinelerin sinyallerini nasıl eşleştirdiniz?",
        "Sunumda bize farklı iş millerinin ürettiği sinyalleri eşleştirmemiz için bir matris verilmişti. "
        "Sinyalleri ortak rollere bağlarken o matristen yararlandık. Örneğin Fanuc tarafındaki IsNotRunning "
        "ile Mitsubishi tarafındaki RUN_STATUS_START aynı role karşılık geliyor."),
       ("Neden Kalite üzerinde çalışmadınız?",
        "Veride hurda kaydı sıfır, yani Kalite her zaman tam 1. Elimizde kendi ürettiğimiz sentetik bir hurda "
        "verisi olmadan Kalite kolunu oynatamayız, bu yüzden dürüstçe A ve P'ye odaklandık."),
       ("System Offline'ı neden OEE dışında tuttunuz?",
        "Çünkü o bir makine arızası değil, kollektörün ya da ağın bağlantı kesintisi. Sorumlusu bakım değil "
        "IT. Makine durmadığı için Kullanılabilirlik paydasına da girmemeli, yoksa yanlış ekibe yatırım "
        "yapılır.")])

# ───────────────────────── 3 ─────────────────────────
slide("Slayt 3 — Yöntem (uçtan uca hat)",
      "Kurduğumuz sistem beş aşamalı tek bir hattır ve her aşama bir öncekinin çıktısını kullanır. Önce "
      "farklı markaların sinyallerini ortak rollere eşleyen kanonik sinyal katmanı, sonra her sinyalin "
      "normalinden sapmasını ölçen baseline sapma katmanı, ardından alarmları nedensel zincire dizen kök "
      "neden katmanı, sonra duruşu önceden işaretleyen tahmin modeli ve en sonda düzeltmenin OEE kazanımını "
      "sayısallaştıran What-If katmanı.",
      [("Farklı markaları nasıl ortak modele soktunuz?",
        "İki şeyle: marka bağımsız rol haritası ile aynı işi gören sinyalleri eşledik, ve her makinenin "
        "sinyalini kendi içinde sağlam istatistiklerle (medyan, çeyrekler açıklığı) normalize ederek farklı "
        "ölçekleri ortak bir uzaya taşıdık.")])

# ───────────────────────── 4 ─────────────────────────
slide("Slayt 4 — Filo ve OEE",
      "Makinelerin OEE değerlerini incelediğimizde en iyi makinenin bile yüzde 74 OEE ile çalıştığını "
      "görüyoruz. Makineler birbirine yakın bir bantta değil, aralıklı dağılmış durumda. Hatta Makine 8'in "
      "OEE değeri sıfır; bunun sebebi o dönemde üretimin sıfır olması. Üretim sıfır olunca Performans çarpanı "
      "sıfırlanıyor ve tüm OEE değeri sıfıra düşüyor.",
      [("Makine 8 gerçekten boşta mıydı, veri hatası olabilir mi?",
        "Duruşu gerçek, 2027 saat kayıtlı. Ama üretim sayımı sıfır olduğu için Performans 0 çıkıyor ve OEE "
        "formülü gereği çarpım sıfırlanıyor. Yani makine çalışmış ama o dönemde sayılan üretim yok."),
       ("Bu veride OEE'yi en çok ne belirliyor?",
        "Pratikte Kullanılabilirlik. Kalite hep 1, Performans da neredeyse her gün 1 veya 0 olduğu için "
        "ayrıştırıcı değil; dolayısıyla iyileştirme alanı Kullanılabilirlikte.")])

# ───────────────────────── 5 ─────────────────────────
slide("Slayt 5 — Kök neden",
      "Burada bir zaman aralığında yaşanan baseline'dan sapma olayını görüyoruz. Hava basıncında yaşanan bir "
      "problemden dolayı Z ekseninde bir hata oluşuyor. Aynı anda gelen alarmları, dizindeki sıralarına göre "
      "değil, fiziksel nedensel önceliğe göre sıralıyoruz.",
      [("Fiziksel nedensel önceliğe göre sıralama tam olarak nedir?",
        "Bir makinede aynı anda birden çok alarm dizisi (ALERT_ARRAY) tetiklenebilir. Dizideki en küçük "
        "indeksli alarm her zaman kök neden değildir. Biz alarmları fiziksel neden-sonuç sırasına koyuyoruz: "
        "önce pnömatik, sonra mekanik, sonra yazılım veya güvenlik. Bu olayda hava basıncı düşüyor (pnömatik), "
        "bu yüzden Z ekseni referansını kaybediyor (mekanik), o da güvenlik alarmını tetikliyor. Yani kök "
        "AIR PRESSURE, Z ekseni onun sonucu."),
       ("Bunu veriyle nasıl doğruluyorsunuz?",
        "Olay anında baseline'dan sapan sinyallerle. run_state eksi 7,7 standart sapmaya iniyor, yani makine "
        "fiilen duruyor; bu, alarm zincirini doğruluyor."),
       ("Sapma duruştan önce mi geldi, yoksa eş zamanlı mı?",
        "Dürüst cevap: bu olayda sapma eş zamanlı bir kanıttır, öngörücü bir öncül değildir. Onu olduğu gibi "
        "söylüyoruz.")])

# ───────────────────────── 6 ─────────────────────────
slide("Slayt 6 — Bizim katkımız: tahmin modeli",
      "Tanıtım kısmını geçip katkımızı anlatmak istiyorum. Veri setinde hatalar zaten etiketlenmiş olduğu "
      "için, bu hataları maskeleyerek bir anomali tespiti modeli eğittik. Eğittiğimiz modelde data leakage "
      "olmaması için kronolojik bir bölme yaptık: her makinenin en eski yüzde 60'ı eğitime, en yeni yüzde "
      "40'ı teste gitti, hiç karıştırma yapmadık. Eğitim esnasında da yalnızca geçmişe ait öznitelikleri "
      "kullandık, normalizasyon ve ölçekleme istatistiklerini sadece eğitim verisinden hesapladık ve devam "
      "eden bir duruşun içindeki anları çıkardık ki zaten olmakta olan bir duruşu tahmin etmiş gibi "
      "görünmeyelim. Sonuç olarak elde ettiğimiz model 0,73 ROC-AUC değerine ulaştı ve rastgele bir modele "
      "göre yaklaşık 2,5 kat daha net tahminler yaptı.",
      [("Maskeleme ile tam olarak ne yaptınız?",
        "Etiketli duruş ve alarm pencerelerini eğitim sırasında bir kenara ayırdık. Modeli normal davranış "
        "üzerinden öğrettik, böylece sapmayı kendisi yakalıyor; etiketleri de doğrulama için kullandık, "
        "hedef olarak ezberletmedik."),
       ("Data leakage'a karşı somut olarak ne yaptınız?",
        "Üç önlem: kronolojik makine bazlı bölme, yalnızca geçmiş öznitelik, ve tüm ön işleme istatistiklerini "
        "sadece eğitimden hesaplama. Ayrıca devam eden duruş içindeki kovaları attık; ilginç olan, bunları "
        "atınca skor yükseldi, bu da liftin gerçek duruş öncesi sinyalden geldiğini kanıtlıyor."),
       ("2,5 kat derken neyi kastediyorsunuz, doğruluk mu?",
        "Doğruluk değil, lift. Yani PR-AUC değerimizin taban orana oranı. Modelin riskli dediği yerlerde "
        "gerçek duruşlar rastgeleye göre yaklaşık 2,4 kat daha sık. Tam değer 2,38."),
       ("Recall yüzde 69, kaçırdığınız duruşlar ne oluyor?",
        "527 önemli duruşun 364'ünü yakaladık. Kaçırdıklarımız çoğunlukla kondisyon sinyali olmayan, ani "
        "operasyonel duruşlar. Bunu da sınır olarak söylüyoruz.")])

# ───────────────────────── 7 ─────────────────────────
slide("Slayt 7 — Algoritma seçimi",
      "Burada eğittiğimiz diğer modellerle yaptığımız kıyaslamayı görebilirsiniz. Aynı held-out gelecekte ve "
      "aynı özniteliklerle Lojistik Regresyon, Random Forest, MLP ve Histogram tabanlı Gradient Boosting'i "
      "yarıştırdık. Bu kıyas sonucunda Histogram GBDT modelini seçtik.",
      [("Neden HistGBDT, MLP veya başka bir model değil?",
        "Çünkü aynı testte en yüksek PR-AUC ve ROC'u o verdi. Eksik değeri kendisi işliyor, ki bizim "
        "veride bol eksik var; ölçekleme istemiyor ve doğrusal olmayan eşikleri yakalıyor. MLP en zayıf "
        "öğrenen oldu, çünkü bu tür tablo ve eksik değer ağırlıklı veride gradyan artırma sinir ağını geçer."),
       ("Derin öğrenme, CNN veya transformer denediniz mi?",
        "Evet, ama denetimsiz anomali autoencoder tarafında. Tahmin için avantaj sağlamadı, çünkü gerçek "
        "kondisyon sinyalleri boştu; bu yüzden tabloya dayalı gradyan artırmada karar kıldık."),
       ("HistGBDT bir ensemble mı?",
        "Evet, gradyan artırmalı karar ağaçlarından oluşan bir topluluk modeli.")])

# ───────────────────────── 8 ─────────────────────────
slide("Slayt 8 — Risk zaman çizgisi",
      "Aşağıdaki eğriye baktığımızda, modelin ileriyi görmeden, yani held-out dönemde yaptığı tahminlerde "
      "ürettiği duruş riskini görebiliyoruz. Bu eğriyi, elde ettiğimiz modelin çıktısına somut bir örnek "
      "olması için koyduk. Kırmızı kesikli çizgi alarm eşiği; risk bu çizgiyi aştığında bir uyarı üretiliyor.",
      [("Alarm eşiği neden bu kadar sık geçilmiş?",
        "Çünkü bu makine, dönemin ikinci yarısında çok daha kararsız çalışmış; gerçek duruş sıklığı artmış. "
        "Model de buna paralel olarak sık sık eşiği aşıyor. Eşik bilinçli olarak düşük seçildi ki önemli "
        "duruşları kaçırmayalım; bu da daha çok uyarı demek."),
       ("Neden başta düz başlayıp ilerleyen haftalarda pik yapıyor?",
        "Dönemin başında makine daha kararlı ve duruşlar seyrek, bu yüzden risk düşük ve düz. İlerleyen "
        "haftalarda duruş rejimi değişiyor, mikro duruşlar ve plansız duruşlar artıyor; model bu bozulmayı "
        "yükselen riskle yansıtıyor. Yani eğri verinin durağan olmadığını da gösteriyor."),
       ("Bu eğri eğitim verisinden mi?",
        "Hayır, tamamen held-out. Model bu dönemi hiç görmedi; gördüğümüz tahminler gerçek bir gelecek "
        "üzerinde.")])

# ───────────────────────── 9 ─────────────────────────
slide("Slayt 9 — Tahminden OEE'ye köprü",
      "Peki bu sonucu OEE verisine nasıl döktük? Önce elde ettiğimiz recall değerinden yakaladığımız "
      "duruşların oranını saate çevirdik ve 2062 saatlik önceden yakalanmış bir duruş süresi elde ettik. "
      "Sonra, bu duruşlar için önceden müdahale planları oluşturulması durumunda Kullanılabilirliğin nasıl "
      "değişeceğini analiz ettik. Yani duruşların önceden bilinmesi durumunda OEE'nin nasıl değişeceğini "
      "görmüş olduk. Duruş sürelerinin azaltılmasını ise What-If senaryolarıyla simüle ettik.",
      [("2062 saati nasıl buldunuz?",
        "Modelin yakaladığı önemli duruşların içindeki toplam duruş süresini topladık. Bir duruş, başından "
        "geriye 60 dakikalık pencerede risk eşiği en az bir kez aşıldıysa yakalanmış sayılıyor. Bu 2062 saat, "
        "Fanuc hücresinin tüm plansız duruş süresinin yaklaşık yüzde 75'i."),
       ("Bu kazanımı garanti ediyor musunuz?",
        "Hayır. Tek iddiamız şu: bu duruşlar artık körlemesine yaşanmıyor, önceden biliniyor, yani ele "
        "alınabilir bir hedefe dönüşüyor. Ne kadarının giderileceği bir bakım kararı; somut OEE etkisini de "
        "What-If senaryolarında ölçüyoruz."),
       ("Neden tek bir net OEE rakamı vermiyorsunuz?",
        "Çünkü tek rakam vermek için bir müdahale etkinliği varsaymamız gerekir ve veride bunu destekleyecek "
        "bilgi yok. Varsayım üretmek yerine ölçülen miktarı, 2062 saati, ve What-If senaryolarını gösteriyoruz.")])

# ───────────────────────── 10 ─────────────────────────
slide("Slayt 10 — Makineler arası örüntü",
      "Tek makineyle yetinmeyip diğer makineler arasında da örüntü yakalamaya çalıştık. Şu soruyu sorduk: "
      "iki ya da daha fazla makine aynı saatte plansız durduğunda, bu durum şansla ve ortak vardiya "
      "programıyla açıklanabilir mi? En az iki makinenin aynı anda durduğu saatleri saydık ve 708 saat "
      "bulduk. Sonra iki tane kıyas modeli (null model) kurduk: makinelerin duruşları tamamen rastgele "
      "dağılsaydı 333 saat, sadece ortak vardiya ritmi korunsaydı 564 saat beklenirdi. Gözlenen 708 değeri, "
      "vardiyayı koruyan beklentinin bile üzerinde; z değeri 5,16 çıktı.",
      [("Bu slaytta tam olarak ne yaptınız, kısaca?",
        "Makinelerin birlikte durmasının tesadüf mü yoksa gerçek bir bağ mı olduğunu istatistiksel olarak "
        "test ettik. İki null model permütasyonla kuruldu; gözlenen birliktelik (708) hem rastgeleyi (333) "
        "hem de ortak vardiyayı (564) anlamlı biçimde aşıyor."),
       ("z = 5,16 sonucu bize ne anlatıyor?",
        "Makinelerin aynı anda durmasının ortak vardiya programıyla açıklanamayacak kadar güçlü olduğunu, "
        "yani aralarında sistemik bir bağ bulunduğunu gösteriyor. Pratik anlamı: tek bir ortak kök nedeni "
        "(örneğin paylaşılan hava beslemesi veya altyapı) düzeltmek birden çok makineyi aynı anda iyileştirebilir."),
       ("Null model neden iki tane?",
        "Çünkü makineler aynı vardiyaları paylaşıyor, yani bir miktar birlikte durma zaten 'herkes molada' "
        "demek. Rastgele null bunu görmezden gelirdi. Vardiyayı koruyan null bu etkiyi içeride bırakıyor; onu "
        "bile aştığımız için sonuç gerçek."),
       ("Kökü adlandırabiliyor musunuz?",
        "Hayır, ve bunu saklamıyoruz. Tüm plansız duruşlar tek etiket taşıdığı için 'aynı neden' bağını MES "
        "verisiyle isimlendiremiyoruz. Eski yöntemin 'sistemik' bulgusunun aslında bir kayıt tekrarı olduğunu "
        "da gösterip ayıkladık.")])

# ───────────────────────── 11 ─────────────────────────
slide("Slayt 11 — What-If senaryoları",
      "Burada What-If senaryolarını görebilirsiniz; dört farklı senaryo belirledik. Az önce dediğim gibi "
      "Makine 1'de en büyük plansız duruş kalemini yüzde 30 azaltabilirsek OEE 18 puan yükseliyor; aynı "
      "azaltmayı Makine 5'te yaptığımızda yüzde 15'lik bir artış oluyor. Veri Performans kolu için uygun "
      "olmadığından, elimizde kendi ürettiğimiz sentetik bir veri olmadan Performans'ı artırıp OEE'yi "
      "hesaplayamıyoruz; bunu da dürüstçe belirtmek istedik. Ayrıca tesiste elektrik veya bağlantı kesintisi "
      "giderilmesi senaryosunu da koymak istedik, ancak bu üretimin kendisinden kaynaklanmadığı için delta "
      "OEE hesabına dahil olmuyor.",
      [("En büyük plansız duruş kalemi ne demek?",
        "Bir makinenin plansız duruşlarını nedenine göre topladığımızda en çok saat tutan tek kalem. Yani "
        "toplam plansız duruş süresinin en büyük dilimini oluşturan duruş türü. 80/20 mantığıyla en çok "
        "kazancı buraya müdahale verir."),
       ("Performans'ı neden hesaplayamıyorsunuz?",
        "Çünkü bu veride Performans dejenere. Üretim yapılan 777 makine gününün 605'inde tam 1, 172'sinde 0, "
        "arada hiç değer yok. Yani çevrim iyileştirmesi Performans'ı kıpırdatmıyor. Sentetik veri üretmeden "
        "bu kolu sahte bir biçimde oynatmak istemedik."),
       ("S4 neden sıfır puan?",
        "Çünkü bağlantı kesintisinin giderilmesi bir IT aksiyonu. 663 saatlik bağlantı görünürlüğü geri "
        "geliyor ama bu makine OEE'sine yazılmıyor; biz de olduğu gibi gösteriyoruz.")])

# ───────────────────────── 12 ─────────────────────────
slide("Slayt 12 — Sonuç",
      "Özetlemek gerekirse: bir ensemble model kullanarak duruş zamanlarını normale göre yaklaşık 2,5 kat "
      "daha kesin tahmin ettik, bu duruşlar için önceden müdahale planlanması durumunda Kullanılabilirliğin "
      "ve dolayısıyla OEE'nin nasıl değişeceğini analiz ettik. Makineler arası analizde elde ettiğimiz "
      "z = 5,16 sonucu, duruşların aynı anda olmasının vardiyayla açıklanamayacağını, sistemik bir bağ "
      "bulunduğunu gösterdi. En iyi What-If senaryosunda ise 18 puanlık bir OEE kazanımı elde ettik.",
      [("Tek cümlede projeniz nedir?",
        "Hangi makine ne zaman duracak, neden duracak ve düzeltirsek OEE ne kadar artar; üçünü tek ekranda "
        "ve dürüstçe yanıtlıyoruz."),
       ("Sıradaki adım ne olurdu?",
        "Makine bazlı olasılık kalibrasyonu, Mitsubishi için daha kısa ufuklu hedef ve kondisyon sinyalleri "
        "gerçekten gelmeye başlarsa modelin tavanını yükseltmek.")])

# ───────────────────────── genel / kıl sorular ─────────────────────────
E.append(Paragraph("Genel ve Zorlayıcı Sorular", st_h))
gen = [
    ("Veriyi yapay zekaya mı analiz ettirdiniz?",
     "Hayır. Önce CSV ve JSON'ları elle açıp içeriği anlamlandırdık. Yapay zeka ne derse desin, veriyi "
     "kendiniz görmeden ikna olmak zor. Makineler arası farkları, Fanuc ile Mitsubishi telemetrisinin "
     "ayrıştığını ve TurboCut gibi makinelerde hiç telemetri olmadığını böyle gördük; o makineleri "
     "discard ettik."),
    ("Sonuçlarınız neden finansal değil?",
     "Veri setinde hiçbir maliyet veya satış bilgisi yok. Bu yüzden öne çıkardığımız her şey fiziksel "
     "kazanım: saat, parça ve OEE puanı. Para birimi koymak veriyle desteklenmeyen bir varsayım olurdu, "
     "biz de koymadık."),
    ("Modeliniz neden sadece beş makinede çalışıyor?",
     "Çünkü lift yalnız Fanuc hücresinde 1'in belirgin üzerinde. Mitsubishi makineleri zamanın yüzde 53'ünde "
     "zaten durduğu için orada tahmin doygun; yüksek recall yanıltıcı olur. Mitsubishi'yi yine de kök neden "
     "ve OEE tarafında tuttuk, sadece tahmin iddiasının dışında bıraktık."),
    ("ROC 0,76 da gördüm, 0,73 de; hangisi doğru?",
     "İkisi de doğru, farklı kümeler. 0,76 dört modeli kıyasladığımız birleşik veri sonucu. 0,73 ise sahaya "
     "koyduğumuz, yalnız Fanuc'ta ayarlanmış modelin held-out sonucu. Konuştuğumuz dağıtılan model 0,73."),
    ("Lift 2,38 ile recall 0,69 birbirini tutuyor mu?",
     "Evet, ikisi farklı şeyi ölçer. Lift sıralama kalitesini, recall seçtiğimiz eşikte yakaladığımız "
     "duruş oranını ölçer. Eşiği düşürürsek recall artar ama yanlış alarm da artar; bu bir denge ve eşiği "
     "bilinçli seçtik."),
    ("Overfitting yok diye nereden eminsiniz?",
     "Held-out gelecekte ölçtük, eğitimde görmediği dönemde. Ayrıca devam eden duruş içindeki anları atınca "
     "skor düştü değil yükseldi; bu, sinyalin gerçek ve duruş öncesi olduğunu gösterir, ezber değil."),
    ("OEE'yi neden hep Kullanılabilirlikten kazanıyorsunuz, bu bir kısıt değil mi?",
     "Bir kısıt ve onu söylüyoruz. Kalite sıfır hurda yüzünden 1, Performans da bu veride dejenere. "
     "Dolayısıyla bu veri setinde gerçek kaldıraç Kullanılabilirlik. Bu bizim tercihimiz değil, verinin "
     "dayattığı bir gerçek."),
    ("En zayıf noktanız ne?",
     "Kondisyon sinyallerinin boş olması. Servo sıcaklığı, yük gibi sinyaller sıfır satır olduğu için "
     "tahminin tavanını model değil veri belirliyor. Daha iyi sinyalle model de iyileşir."),
]
for q, a in gen:
    E.append(Paragraph("S: " + q, st_q))
    E.append(Paragraph("C: " + a, st_a))

# değerlendirme
E.append(Paragraph("Metnin Değerlendirmesi (kısa)", st_h))
for line in [
    "Akış güçlü: önce problem ve veri, sonra katkı, sonra OEE ve örüntü. Jüriye net.",
    "Sık düzeltilmesi gereken tek nokta: 2,5 kat ifadesini söylerken bunun doğruluk değil lift olduğunu bir "
    "kez belirt; hoca kesin sorar.",
    "Köprü slaytında varsayım vermediğin için güçlüsün; soru gelirse 'müdahale etkinliği varsaymadık, "
    "ölçülen 2062 saati ve What-If'i gösteriyoruz' de.",
    "Eksik bilgi yok; yalnız episode precision'ı (yüzde 44) bilmen iyi olur, çünkü yanlış alarm sorulursa "
    "elinde hazır rakam olur.",
]:
    E.append(Paragraph("• " + line, st_a))

doc.build(E)
print("kaydedildi: trexCloud_Konusma_Metni.pdf")
