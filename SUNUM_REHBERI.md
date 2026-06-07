# trexCloud Sunum Rehberi ve Proje Açıklaması

Bu belge iki işi görür. Birinci bölüm, projeyle ilgili sorularınızı tek tek yanıtlar. İkinci bölüm,
sunumdaki her slaytı ve her grafiği ayrıntısıyla açıklar. Üçüncü bölüm, jürideki profesörün sorabileceği
derin teknik soruların yanıtlarını içerir. Amaç, sunumda geçen her sayının nereden geldiğini sizin
tam olarak bilmenizdir.

Jüri üç kişiden oluşuyor. Biri bu projeyi yapan firmanın yazılım sorumlusu, biri bu çözümün müşterisi,
biri de her detayı soran bir akademisyen. Bu yüzden hem teknik derinlik hem de iş değeri net olmalı.

---

## Bölüm 1: Sorularınızın Yanıtları

### 1.1 Pipeline kısaca nedir?

Sistem beş aşamalı tek bir hattır. Her aşama bir öncekinin çıktısını girdi olarak alır.

1. **Kanonik sinyal katmanı.** Farklı markaların ham sinyalleri ortak rollere eşlenir. Örneğin Fanuc
   tarafındaki `IsNotRunning` ile Mitsubishi tarafındaki `RUN_STATUS_START` aynı role bağlanır. Böylece
   marka farkı modelin önünde engel olmaktan çıkar.
2. **Baseline sapma (Anomali Tespiti).** Her sinyalin normal davranışı sağlam istatistiklerle öğrenilir
   (medyan ve çeyrekler açıklığı). Sonra her an için sinyalin bu normalden kaç standart sapma uzakta
   olduğu hesaplanır.
3. **Kök neden analizi (RCA).** Alarmlar ve duruşlar tek bir olay akışında birleştirilir, zaman damgasına
   göre eşleştirilir ve aynı anda gelen alarmlar fiziksel nedensel önceliğe göre bir zincire dizilir.
4. **Duruş tahmini.** Geçmiş özniteliklerden bir HistGBDT (histogram tabanlı gradyan artırma) modeli
   eğitilir. Model, yaklaşan bir plansız duruş için risk üretir.
5. **What-If ve OEE.** Bir düzeltmenin (örneğin en büyük duruş kaleminin azaltılmasının) OEE üzerindeki
   etkisi, aynı OEE formülü yeniden çalıştırılarak sayısallaştırılır ve isteğe bağlı finansal çerçeveye
   bağlanır.

### 1.2 Lift nedir?

Lift, modelin gerçek duruşları kör tahmine göre ne kadar daha iyi ayırdığını gösteren orandır.

- Fanuc hücresinde bir saatlik pencerede plansız duruş görülme tabanı yüzde 17,9'dur. Buna taban oran
  (base rate) denir.
- Modelin PR-AUC değeri (precision-recall eğrisi altındaki alan) bu tabanın 2,38 katıdır. İşte bu 2,38
  sayısı lifttir.
- Lift 1,0 olsaydı model işe yaramaz demekti, çünkü rastgele tahminle aynı olurdu. 2,38 olması, modelin
  riskli dediği pencerelerde gerçek duruşların rastgeleye göre yaklaşık 2,4 kat daha sık görüldüğü
  anlamına gelir.

### 1.3 Recall, ROC ve eğittiğimiz modellerle karşılaştırma

Dağıtılan Fanuc modelinin held-out (modelin hiç görmediği gelecek) dönemdeki ölçümleri:

- ROC-AUC: 0,73. Bu, modelin rastgele bir duruş anını rastgele bir normal andan doğru ayırma olasılığıdır.
  0,5 tesadüf, 1,0 mükemmel demektir.
- Lift: 2,38 kat.
- Recall: yüzde 69. Yani 527 önemli duruşun 364'ünü yakaladı.
- Episode precision: yüzde 44. 722 alarm dönemi içinde isabet oranı budur.

Birden fazla model ve konfigürasyon eğittik. Hepsi `analysis/artifacts/regime_metrics.json` içinde
kayıtlıdır. Özet karşılaştırma:

| Eğitim verisi | Test | Taban oran | ROC | Lift | Recall | Yorum |
|---|---|---:|---:|---:|---:|---|
| Fanuc (ayarlanmış) | Fanuc | 0,18 | 0,73 | 2,38 | 0,69 | Dağıtılan model |
| Fanuc (temel) | Fanuc | 0,18 | 0,68 | 2,0 | 0,59 | Izgara aramadan önce |
| Birleşik, z-norm | Fanuc | 0,18 | 0,72 | 2,33 | 0,48 | Marka transferi denendi |
| Mitsubishi | Mitsubishi | 0,53 | 0,61 | 1,2 | 0,97 | Yüksek recall yanıltıcı |
| Birleşik | Mitsubishi | 0,53 | 0,61 | 1,2 | 0,96 | Marka transferi denendi |

Bu tablodan üç sonuç çıkar:

- Fanuc hücresi gerçekten tahmin edilebilir tek gruptur. Izgara aramasıyla ROC 0,68'den 0,73'e, lift
  2,0'den 2,38'e çıktı.
- Mitsubishi makineleri zamanın yüzde 53'ünde zaten duruyor. Bu yüzden yüzde 97 recall etkileyici
  görünse de bilgi taşımaz, çünkü taban oran çok yüksek ve lift yalnızca 1,2 katıdır.
- İki markayı birleştirip ortak uzaya normalize etmek (z-norm) Fanuc testinde ROC 0,72 verdi. Bu, ayrı
  Fanuc modeline çok yakındır. Yani marka transferi ek bir kazanç sağlamadı.

### 1.4 Ne tahmin ediyoruz, tek etiket sorunu ve Pareto

- **Duruş tahmini.** Evet, plansız bir duruşun yaklaştığını tahmin ediyoruz. Bunu yalnızca Fanuc
  makinelerinde yapıyoruz ve kesin saatini değil, riskin yükseldiğini önceden işaretliyoruz.
- **Tek etiket.** Doğru. Veride her plansız duruş tek bir genel etiket taşıyor, o da "Duruş". Bu yüzden
  MES verisi tek başına nedenini söyleyemez.
- **Pareto ile sıralama.** Pareto analizi "ne ve ne zaman" sorusunu yanıtlar. Yani hangi duruş kalemi
  toplam sürenin en büyük kısmını yiyor, bunu 80/20 kuralıyla sıralar. Cihaz düzeyinde "neden" sorusu
  ise yalnızca alarm verisi bulunan Makine 1 ve Makine 2'de yanıtlanabilir. Orada alarm zincirini
  (kaskad) kurarız. Yani Pareto her makinede vardır, nedensel kök ise sadece M1 ve M2'de.

### 1.5 What-If'te Q neden 1, peki P neden de 1? Sadece A üzerinde mi çalışıyoruz?

Bu önemli bir tespit ve dürüst yanıt evet, pratikte Kullanılabilirlik (A) üzerinde çalışıyoruz. İki
ayrı sebep var.

- **W1 kaldıracının doğası gereği.** "Duruş süresini azalt" işlemi tanımı gereği bir Kullanılabilirlik
  aksiyonudur. OEE üç çarpanın çarpımıdır: ΔOEE = ΔA çarpı P çarpı Q. Bu işlem hızı (P) veya hurdayı (Q)
  değiştirmez, bu yüzden ΔP ve ΔQ sıfırdır. Bu kısım matematiksel olarak doğrudur.
- **P neden tam olarak 1 görünüyor.** Performans şöyle hesaplanır: P = en fazla 1 olacak şekilde
  WorkingTime bölü PlannedTime. Toplulaştırılmış bir makinede WorkingTime, PlannedTime'dan çok büyüktür.
  Makine 1 örneğinde WorkingTime yaklaşık 17,9 milyar milisaniye, PlannedTime yaklaşık 0,21 milyar
  milisaniyedir. Oran yaklaşık 86 çıkar ve 1'e kırpılır. Sonuç P = 1'dir.
- Bu yüzden Makine 1'in OEE değeri olan yüzde 40, tamamen Kullanılabilirlik tarafından belirlenir
  (A = 0,40, P = 1, Q = 1). Q da sıfır hurda yüzünden 1'dir.

Daha da derini: günlük (level=1) ayrıntıda baktığımızda bile Performans dejenere çıkıyor. Üretim yapılan
777 makine gününün 605'inde P tam olarak 1, 172'sinde 0'dır ve **arada hiçbir gün yoktur**. Yani bu
veride Performans ikili bir değişkene dönüşmüş, ayrıştırıcı bilgisini yitirmiştir. Bu yüzden bir çevrim
iyileştirmesi senaryosu OEE'yi hareket ettiremez. Bu bir varsayım değil, ölçülmüş bir sonuçtur.

### 1.6 Senkron Duruşlar: 708, 564 ve 333 sayıları ne anlatıyor?

İki veya daha fazla makinenin aynı saat içinde plansız durduğu saatleri sayıyoruz.

- **708 saat:** gerçekte olan. Yani bu kadar saatte en az iki makine aynı anda plansız durmuş.
- **333 saat:** her makinenin duruşları zaman ekseninde tamamen rastgele dağıtılsaydı, sırf tesadüfen
  beklenecek örtüşme.
- **564 saat:** her makinenin günlük ritmi (vardiya, mola, saat düzeni) korunur ama günler karıştırılırsa
  beklenecek örtüşme. Bu daha akıllı bir kıyastır, çünkü makineler aynı vardiyaları paylaşır, dolayısıyla
  bir miktar birlikte durma zaten "herkes molada" demektir.

Anahtar bulgu şudur: 708, vardiya temelli beklenti olan 564'ün üzerindedir. İstatistik sonucu z = 5,16
ve p küçüktür 0,001'dir. Yani senkronizasyon, ortak vardiya programıyla açıklanamaz.

İçgörü: 708 saatin 564'ünü vardiya açıklıyor, geri kalan yaklaşık 144 saat vardiyayla açıklanamayan
gerçek bir bağdır. Bu, duruşların bir bölümünün makineye özel değil sistemik olduğunu gösterir. Ortak
bir kök neden (örneğin paylaşılan hava beslemesi, elektrik, ya da yukarı akış malzeme akışı) bu birlikte
durmaları yaratıyor olabilir. İş değeri açısından anlamı şudur: tek bir ortak kök nedeni düzeltmek, aynı
anda birden çok makinenin OEE değerini yükseltebilir. Dürüst sınır: bu kök nedeni adlandıramıyoruz,
çünkü tüm duruşlar tek etiket taşıyor ve olay ölçeğindeki (günlük dalgalanma çıkarılmış) korelasyon
sıfıra yakın, yani bu anlık bir zincir değil, yavaş ortak bir eğilimdir.

### 1.7 Tahminden OEE'ye köprü: müdahale etkinliği ve ΔOEE nasıl hesaplandı?

Model held-out dönemde önemli duruşların yüzde 69'unu yakaladı. Bu yakalanan duruşların içindeki toplam
duruş süresi 2062 saattir. Buradan sonrası şöyle işler.

- **Bir duruş ne zaman "yakalandı" sayılır.** Bir duruşun başından geriye doğru 60 dakikalık pencerede,
  modelin risk skoru en az bir kez alarm eşiğini (0,1778) aştıysa o duruş yakalanmış sayılır. Bu, kodda
  `match_stops` fonksiyonudur.
- **Müdahale etkinliği.** Yakalanan 2062 saatin tamamını önlediğimizi iddia etmiyoruz. Önceden uyarılan
  bir bakım ekibinin bu sürenin yalnızca bir kısmını gerçekten önleyebileceğini varsayıyoruz. Bu oranı
  açıkça etiketlenmiş bir varsayım olarak yüzde 35 aldık. Hesap: 2062 çarpı 0,35 yaklaşık 722 saat.
  Bu, önlenebilir kabul edilen süredir.
- **ΔOEE nasıl çıkıyor.** Beş Fanuc makinesinin toplam OEE bileşen satırını alıyoruz. Plansız duruştan
  (UnPlannedStop) 722 saati düşüyoruz ve tam olarak aynı OEE formülünü (`oee.recompute`) yeniden
  çalıştırıyoruz. Kullanılabilirlik yükseliyor, Performans ve Kalite değişmiyor (zaten 1). Yeni OEE'den
  eski OEE'yi çıkarınca artış +0,1044, yani +10,4 puan çıkıyor.
- **Sınır koşulu.** Önlenen süre, gerçek plansız duruş süresinin üzerine çıkamaz, bu kodda kırpılır.
- **RCA'nın rolü.** RCA hangi duruşların önemli olduğunu ve kök nedenlerini söyler, böylece ekip neye
  müdahale edeceğini bilir. Ama "uyarıldık" ile "duruşu gerçekten önledik" arasındaki köprüyü kuran
  sayı, yüzde 35'lik etkinlik varsayımıdır.

---

## Bölüm 2: Slayt Slayt Açıklama

Sunum 13 slayttır. Renk kimliği tek bir koyu yeşildir. Her slaytta sol kenarda ince yeşil bir şerit,
üstte küçük yeşil bir bölüm etiketi ve büyük bir başlık vardır. Altta sabit bir alt bilgi ve sayfa
numarası bulunur.

### Slayt 1: Kapak
- İçerik: proje adı, kısa tanım, veri dönemi, makine sayısı ve telemetri büyüklüğü.
- Söylenecek: "Bir CNC ve lazer tesisi için uçtan uca duruş tahmini, kök neden ve What-If sistemi
  geliştirdik. Veri Ağustos 2025 ile Mayıs 2026 arasını, 12 makineyi ve yaklaşık 7,4 milyon telemetri
  kaydını kapsıyor."

### Slayt 2: Veri
- İçerik: beş maddelik veri envanteri. Grafik yok, çünkü bu slaytın amacı dürüst veri resmini vermek.
- Anlatılan noktalar: 12 makine ve markalar, OEE'nin A çarpı P çarpı Q olduğu, Kalite'nin sıfır hurda
  yüzünden hep 1 olduğu, üretim sıfır olunca P'nin 0 olduğu, vaat edilen kanıt sinyallerinin boş çıkması
  ve modeli gerçekten akan sinyallere kurmamız, en büyük duruş kaynağının bağlantı kesintisi olması.
- Jüriye mesaj: "Veriyi olduğu gibi gördük. Boş çıkan sinyallere model kurmadık."

### Slayt 3: Yöntem
- İçerik: beş numaralı kutuda pipeline. Kanonik sinyal, baseline sapma, kök neden, duruş tahmini, What-If
  ve OEE. Son kutu yeşil vurguludur.
- Altında üç madde: marka bağımsız rol haritası, makine içi sağlam normalizasyon, sızıntıya karşı korumalı
  eğitim.
- Önemli: kutular ok işareti içermez, numaralarla akışı gösterir. Sızıntı koruması profesör için kritiktir,
  bu yüzden ayrı madde yapıldı.

### Slayt 4: Filo Durumu (Grafik var)
- Grafik: yatay çubuklarla yedi makinenin OEE değeri, büyükten küçüğe sıralı. Yeşil çubuk Fanuc, kehribar
  çubuk Mitsubishi. Her çubuğun sağında yüzde değeri yazılı.
- Grafiğin söylediği: OEE yüzde 0 ile yüzde 74 arasında. En iyi makine Makine 2 ile yüzde 74,2. Makine 8
  yüzde 0, çünkü o dönemde üretim kaydı yok, duruşu gerçek ama Performans çarpanı sıfır.
- Sağdaki yeşil kutu: üç maddeyle grafiği yorumlar. Ana mesaj, tüm makinelerde OEE'nin pratikte
  Kullanılabilirlik tarafından belirlenmesidir.
- Neden bu makineler: yalnızca telemetrisi olan ve duruşu kaydedilen makineler gösterildi. Telemetrisiz
  olanlar (TurboCut, ARES) ve duruşu sıfır olanlar (Makine 4, 6, 10) filtrelendi.

### Slayt 5: Kök Neden
- İçerik: gerçek bir olay üzerinden Altın seviye gösterimi. Makine 1, 12 Ocak 2026, saat 04:47.
- İki kutu: solda yeşil "AIR PRESSURE FAILED" (kök neden), sağda "Z-AXIS ZERO RETURN" (bu alarmın sonucu).
- Üç madde: olay anında run_state sinyalinin eksi 7,7 standart sapmaya inmesi (makine durur), alarmların
  dizine göre değil nedensel önceliğe göre sıralanması, çıktının bir kök neden kartı olması.
- Anlatılacak fikir: aynı anda birçok alarm gelir. En küçük dizine sahip olan her zaman kök değildir.
  Fiziksel mantık (önce pnömatik, sonra mekanik, sonra yazılım) zinciri sıralar. Burada hava basıncı
  düştüğü için Z ekseni referansını kaybeder.

### Slayt 6: Tahmin Modeli ve Karşılaştırma (Tablo var)
- Üstte dört özet kart: ROC 0,73, Lift 2,38, Recall yüzde 69, Mitsubishi lift 1,2.
- Tablo: eğittiğimiz dört konfigürasyonun ROC, lift, recall ve not karşılaştırması. İlk satır (dağıtılan
  Fanuc modeli) yeşil vurgulu.
- Altta tek cümlelik özet: Fanuc tek gerçek tahmin edilebilir gruptur, Mitsubishi'nin yüksek recall'u
  taban oranın yüksekliğinden gelir ve yanıltıcıdır.
- Bu slayt, "kaç model denediniz" sorusunun yanıtıdır.

### Slayt 7: Risk Zaman Çizgisi (Grafik var)
- Grafik: Makine 1 için modelin held-out dönemde ürettiği risk eğrisi. Yeşil çizgi risktir (0 ile 1
  arası), kırmızı kesikli çizgi alarm eşiğidir.
- Grafiğin söylediği: dönemin başında risk düşük ve düz. İlerleyen haftalarda risk sık sık eşiğin üzerine
  çıkar. Model bu noktalarda yaklaşan duruşları işaretler. Bu grafik canlı arayüzde de görülebilir.
- Üç madde grafiği okur: yeşil eğri ne, kırmızı çizgi ne, ve zaman içindeki davranış ne.

### Slayt 8: Tahminden OEE Kazanımına (Köprü)
- İçerik: beş numaralı kutuda hesap zinciri. Recall yüzde 69, yakalanan 2062 saat, yüzde 35 etkinlik,
  önlenen 722 saat, sonuç +10,4 puan. Son kutu yeşil vurgulu.
- Üç madde, Bölüm 1.7'deki hesabı anlatır: yakalama, etkinlik varsayımı, OEE'nin yeniden hesaplanması.
- Bu slayt jürinin en çok soracağı yerdir. Sayıların her birinin kaynağını biliyor olmanız gerekir.

### Slayt 9: Makineler Arası Örüntü (Grafik var)
- Grafik: üç yatay çubuk. Gözlemlenen 708 saat (yeşil), vardiya beklentisi 564 saat (kehribar), rastgele
  beklenti 333 saat (gri). Her çubuğun yanında kısa açıklama.
- Altında istatistik: z eşittir 5,16, p küçüktür 0,001.
- Yeşil kutu: içgörü. 564'ü vardiya açıklar, kalan yaklaşık 144 saat gerçek bağdır, bu sistemik bir
  durumdur, ortak kökü düzeltmek birden çok makineyi iyileştirir.
- Bu, Bölüm 1.6'nın slayt karşılığıdır.

### Slayt 10: What-If Senaryoları (Tablo var)
- Tablo: dört senaryo, fiziksel kazanım sütunlarıyla. Para birimi yok, çünkü fiziksel kazanım ölçülmüş
  veridir.
  - S1, Makine 1, en büyük plansız kalem yüzde 30 azaltılır: +18,0 puan, 625 saat çalışma. İlk satır
    yeşil vurgulu, gerçek kazanım.
  - S2, Makine 5, aynı kaldıraç farklı makinede: +15,3 puan, 420 saat. Genelliği gösterir.
  - S3, Makine 3, çevrim süresi yüzde 10 iyileştirme: 0,0 puan. Performans kaldıracı bu veride çalışmıyor.
  - S4, tesis geneli bağlantı düzeltilir: makine OEE'sine yazılmaz, 663 saat bağlantı görünürlüğü geri gelir.
- Üç madde, her senaryoyu bilimsel olarak açıklar. Özellikle S3'ün neden sıfır çıktığını (605/172/0 gün
  dağılımı) ve S4'ün neden makine dışı olduğunu anlatır.

### Slayt 11: Finansal Çerçeve
- İçerik: dört madde. Veride maliyet olmadığı için para biriminin neden ayrı tutulduğu, varsayımların ne
  olduğu, değer ile maliyetin aynı eşikte bağlandığı ve eşik seçiminin finansal bir karar olduğu.
- Anahtar dürüstlük: "Veride maliyet yok, bu yüzden öne çıkardığımız sonuç fiziksel kazanımdır. Para
  birimi katmanı varsayımdır ve etiketlidir."
- Ekonomik optimum eşik 0,78'dir. Bu noktada yıllık yaklaşık 33 müdahale ile pozitif bir net projeksiyon
  oluşur. Düşük eşikte yanlış alarm maliyeti kazanımı aşar.

### Slayt 12: Sınırlar
- İçerik: dört madde, tam cümlelerle. Kondisyon sinyallerinin boş olması, tek etiket sorunu, Performans
  ve Kalite'nin doygunluğu yüzünden OEE'nin Kullanılabilirlik baskın olması, Mitsubishi'nin zayıflığı.
- Bu slayt güven kazandırır. Profesör sınırları sormadan biz söyleriz.

### Slayt 13: Sonuç
- Üstte dört özet kart: lift 2,38, OEE etkisi +10,4 puan, senkron anlamlılık z 5,16, en iyi senaryo +18
  puan.
- Üç madde: sistemin üç işi tek hatta yaptığı, her iddianın null model ile sınandığı, canlı arayüzün
  akışı uçtan uca gösterdiği.

---

## Bölüm 3: Profesör İçin Teknik Derinlik

### 3.1 Veri gerçekleri
- Tüm süre değerleri milisaniyedir, saniye değil. Kodlama cp1254, zaman UTC.
- Nightwatch tarafında gerçekten akan sayısal sinyaller: run_time (yaklaşık 2,8 milyon satır),
  axis_position (yaklaşık 1,3 milyon, çoklu eksen), cycle_time (yaklaşık 1,1 milyon), run_state
  (yaklaşık 868 bin). Dokümanın vaat ettiği servo sıcaklığı, güç ve path-load sinyalleri sıfır satırdır.
- Nightwatch ile MES eşleşmesi unit_uid ve reading_def anahtarlarıyla yüzde 100 tutar.

### 3.2 OEE matematiği
- A eşittir (WorkTotal eksi PlannedStop eksi UnPlannedStop) bölü (WorkTotal eksi PlannedStop).
- P eşittir en fazla 1 olacak şekilde WorkingTime bölü PlannedTime. ProductSum sıfırsa P sıfırdır.
- Q eşittir (ProductSum eksi ScrapeSum) bölü ProductSum. ScrapeSum her zaman sıfır olduğu için Q hep 1.
- Planlı duruşlar Kullanılabilirliği düşürmez, doğrudan paydayı küçültür. Bu yüzden bir duruşu plansızdan
  planlıya taşımak A'yı yükseltir (Senaryo S2 mantığı).

### 3.3 Model ve sızıntı koruması
- Model HistGBDT'dir, 41 öznitelik kullanır. Öznitelikler yalnızca geçmiş bilgisinden türetilir.
- Bölme kronolojiktir ve makine bazlıdır. Eğitim yaklaşık 186 bin, test yaklaşık 124 bin örnektir.
- Normalizasyon istatistikleri yalnızca eğitim verisinden hesaplanır, böylece test bilgisi sızmaz.
- Izgara araması (rastgele arama) en iyi parametreleri iç çapraz doğrulamayla seçti. En iyi konfigürasyon:
  öğrenme oranı 0,02, en fazla 300 ağaç, yaprak başına en az 200 örnek, L2 düzenlileştirme 1,0.

### 3.4 Null model mekaniği (senkron duruşlar)
- Önemli plansız duruşlar (en az 15 dakika) saatlik kovalara yerleştirilir. En az iki makinenin dolu
  olduğu kova sayısı gözlemdir (708).
- İki null kurulur. Serbest null her makinenin örüntüsünü herhangi bir miktarda dairesel kaydırır. Günlük
  null yalnızca tam gün katlarında kaydırır, böylece saat düzenini korur.
- 400 permütasyon çalıştırılır, ortalama ve standart sapma bulunur, z skoru hesaplanır. Serbest null için
  z 8,05, günlük null için z 5,16 çıkar. İkisi de p küçüktür 0,001'dir.
- Neden iki null: serbest null herhangi bir hizalanmayı test eder, günlük null ortak saat düzenini
  aşan hizalanmayı test eder. Aradaki fark, "aynı vardiyada durdular" ile "vardiyanın ötesinde birlikte
  durdular" arasını ayırır.

### 3.5 Eski connectivity bulgusunun neden geçersiz olduğu
- İlk yaklaşımdaki en güçlü görünen sistemik bulgu, bağlantı kesintilerinin makineler arası tekrarıydı.
- Bunun bir veri tekrarı olduğu ortaya çıktı. 85 offline kaydın yaklaşık yüzde 82'si instance_id üzerinden
  birden çok makineye fan-out yapıyor, yani aynı olay birden çok satır olarak görünüyor.
- Tekilleştirilmiş haliyle toplam 663 saat bağlantı kesintisi vardır. Bu, slayttaki S4 sayısının kaynağıdır.

### 3.6 P'nin dejenere olması (en sık gelecek itiraz)
- Üretim yapılan 777 makine gününde P değeri yalnızca 0 veya 1'dir. 605 günde tam 1, 172 günde 0, arada
  sıfır gün.
- Bunun nedeni WorkingTime bölü PlannedTime oranının çoğu günde 1'i aşıp kırpılması, üretim olmayan
  günlerde ise P'nin tanımı gereği 0 olmasıdır.
- Sonuç: bu veride Performans bir OEE kaldıracı olarak kullanılamaz. Kalite de sıfır hurda yüzünden
  kullanılamaz. Bu yüzden tüm gerçek iyileştirme Kullanılabilirlik üzerinden gelir. Bu bir tasarım
  tercihi değil, verinin dayattığı bir gerçektir.

### 3.7 Olası jüri soruları ve kısa yanıtlar
- "Modeli neden tüm makinelere uygulamadınız?" Çünkü yalnızca Fanuc hücresinde lift 1'in belirgin
  üzerindedir. Mitsubishi'de tahmin doygundur, bunu dürüstçe gösterdik ve makineleri yine de RCA ve OEE
  tarafında tuttuk.
- "ΔOEE neden hep A'dan geliyor?" Çünkü bu veride P ve Q dejeneredir. Bunu sayılarla kanıtlıyoruz.
- "Finansal sayılar gerçek mi?" Hayır, veride maliyet yok. Öne çıkardığımız fiziksel kazanımdır, para
  birimi açıkça etiketlenmiş varsayımdır.
- "Senkron duruşlar gerçekten anlamlı mı, yoksa vardiya etkisi mi?" Vardiyayı koruyan null bile aşıldı,
  z 5,16. Yani vardiya etkisinin ötesinde gerçek bir bağ var.
- "Sızıntı (data leakage) var mı?" Hayır. Kronolojik bölme, yalnız geçmiş öznitelik ve eğitimden
  hesaplanan normalizasyon ile koruduk.
