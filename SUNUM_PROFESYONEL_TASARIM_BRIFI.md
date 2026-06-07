# trexCloud Sunum Tasarım ve İçerik Brifi

## 1. Dokümanın Amacı

Bu doküman, `trexCloud_Sunum.pptx` dosyasını daha profesyonel bir görsel dil ve
anlatı yapısıyla yeniden düzenleyecek tasarımcı veya sunum uzmanı için hazırlanmıştır.

Sunumun bilimsel ve analitik içeriği tamamlanmıştır. Beklenen çalışma; mevcut rakamları,
kapsamı ve dürüstlük notlarını koruyarak anlatıyı sadeleştirmek, görsel hiyerarşiyi
güçlendirmek ve jüri karşısında daha hızlı anlaşılır hale getirmektir.

## 2. Projenin Tek Cümlelik Tanımı

**trexCloud, CNC ve lazer üretim tesisinde duruş riskini önceden tahmin eden, olası
kök nedeni açıklayan ve alınacak aksiyonun OEE ile finansal etkisini hesaplayan uçtan
uca bir karar destek sistemidir.**

Önerilen kısa slogan:

> Tahmin eder, açıklar, sayısallaştırır.

## 3. Sunumun Hedefi

- Hackathon değerlendirmesinde özellikle **Altın** ve **Platin** kriterlerini göstermek.
- Sistemin yalnızca model metriği üretmediğini; tahmin, RCA, OEE ve finansal değeri tek
  akışta birleştirdiğini kanıtlamak.
- Veri sınırlamalarını gizlemeyen, ölçülen sonuçlarla varsayımları açıkça ayıran güvenilir
  bir çalışma sunmak.
- Teknik olmayan jüri üyesinin iş değerini; teknik jüri üyesinin ise yöntemsel dürüstlüğü
  hızlıca anlayabilmesini sağlamak.

## 4. Hedef Kitle

- Üretim ve operasyon yöneticileri
- Bakım ve proses mühendisleri
- Veri bilimi / yapay zekâ uzmanları
- Hackathon jürisi
- Finansal etki ve yatırım geri dönüşüyle ilgilenen karar vericiler

## 5. Ana Anlatı

Sunum şu mantıksal sırayı izlemelidir:

1. **Problem:** Plansız duruş var, fakat yalnızca ne zaman durulduğunu bilmek yeterli değil.
2. **Veri gerçeği:** Katalogdaki bazı kondisyon sinyalleri gerçekte akmıyor.
3. **Çözüm:** Gerçekten mevcut sinyallerle tahmin, RCA ve What-If katmanları kuruldu.
4. **Kanıt:** Model held-out gelecekte ölçüldü; alarm kaskadı gerçek vakada kök nedene indi.
5. **İş değeri:** Yakalanan duruşların önlenebilir bölümü OEE ve EUR değerine çevrildi.
6. **Platin:** Çapraz makine bulguları null-model ile sınandı; abartılı iddialardan kaçınıldı.
7. **Sonuç:** Sistem tahmin eder, açıklar ve aksiyonu sayısallaştırır.

## 6. Sunum Yapısı

Sunum iki bölümden oluşur:

- **Ana sunum: Slayt 1–11.** Yaklaşık 7–9 dakikalık jüri anlatımı.
- **Canlı arayüz rehberi: Slayt 12–18.** Demo sırasında veya soru-cevap bölümünde açılacak ekler.

Ana hikâye mümkünse 11 slaytta bitirilmelidir. Arayüz ekranları ana anlatıyı kesmemeli;
kanıt veya açıklama gerektiğinde kullanılmalıdır.

## 7. Değiştirilemez Temel Sonuçlar

Bu rakamlar yeniden tasarım sırasında değiştirilmemeli veya daha olumlu görünmesi için
yuvarlanmamalıdır:

| Gösterge | Değer | Açıklama |
|---|---:|---|
| Model kapsamı | Fanuc {1,2,3,5,9} | Yalnız ortak tahmin sinyali bulunan hücre |
| ROC-AUC | 0,7311 | Held-out gelecek |
| PR-AUC | 0,4263 | Held-out gelecek |
| Lift | 2,38× | PR-AUC / taban oranı |
| Dağıtılan eşik | 0,1778 | Denetlenen ana çalışma noktası |
| Anlamlı duruş | 527 | Held-out test dönemi |
| Yakalanan duruş | 364 | Strict 60 dakika öncesi pencere |
| Event recall | %69,1 | 364 / 527 |
| Alarm dönemi | 722 | Her biri kontrol maliyeti doğurur |
| Alarm dönemi isabeti | %44,0 | Held-out ölçüm |
| Yanlış alarm dönemi | 404 | Gizlenmemeli |
| Yakalanan duruş süresi | 2.062,5 saat | Ölçülen |
| Müdahale etkililiği | %35 | **Varsayım** |
| Atfedilen geri kazanım | 721,9 saat | Test dönemi |
| Atfedilen OEE artışı | +10,44 puan | ΔA = ΔOEE; ΔP/ΔQ = 0 |
| Yıllık projeksiyon | 2.329,7 saat | Ölçüm değil, 365 güne ölçekleme |
| Varsayılan yıllık net | -512.666 EUR | 300 EUR/alarm varsayımında |
| Retrospektif ekonomik eşik | 0,78 | Canlı eşik değildir |
| Retrospektif yıllık net | +11.013 EUR | Held-out duyarlılık analizi |

## 8. Varsayım ve Dürüstlük Kuralları

Sunumda aşağıdaki ayrımlar açıkça görünmelidir:

- Veri setinde maliyet, fiyat veya gerçek müdahale etkililiği yoktur.
- `%35 etkililik`, `80 EUR/saat`, `300 EUR/alarm` ve `12 EUR/parça` kullanıcı
  varsayımlarıdır.
- Varsayılan çalışma noktasındaki finansal sonuç negatiftir. Bu sonuç gizlenmemeli veya
  pozitif bir sonuçla değiştirilmemelidir.
- `0,78` ekonomik eşik yalnızca held-out pencere üzerinde yapılan retrospektif duyarlılık
  analizidir; dağıtılan model eşiği değildir.
- Yıllık değerler gerçekleşmiş yıllık sonuç değil, held-out dönemden 365 güne projeksiyondur.
- AD, denetimsiz RCA kanıt katmanıdır. Tahmin değeri yalnız denetimli Fanuc modeline aittir.
- Mitsubishi ve telemetrisiz makineler tahmin değerine dahil değildir; RCA ve OEE
  What-If kapsamındadır.
- System Offline bir makine arızası değil, IT/ağ bağlantı sorunudur.
- Q gerçek veride 1'dir; kalite senaryosu ancak simülasyon olarak gösterilebilir.

Tasarım önerisi: Varsayımları amber renkli **VARSAYIM**, held-out ölçümleri yeşil
**ÖLÇÜLEN**, yıllık sonuçları mavi/gri **PROJEKSİYON** etiketiyle ayırmak.

## 9. Görsel Dil Önerisi

### Genel yaklaşım

- Format: 16:9
- Stil: endüstriyel, kurumsal, sade, veri odaklı
- Ana sunum açık zeminli kalabilir; arayüz ekran görüntüleri koyu zeminleriyle kontrast oluşturur.
- Tek ana vurgu rengi: derin yeşil
- Uyarı / varsayım: amber
- Risk / hata / yanlış alarm: kırmızı
- Bağlantı / pasif / kapsam dışı: gri

### Tipografi

- Başlıklar kısa, büyük ve tek mesajlı olmalı.
- Teknik metinlerde mümkün olduğunca 12 punto altına inilmemeli.
- Her slaytta en fazla bir ana sonuç ve üç destekleyici mesaj bulunmalı.
- Ondalık gösterim Türkçe sunumda virgülle yazılmalı: `0,73`, `%69,1`, `+10,44 puan`.

### Grafik yaklaşımı

- Grafikler dekoratif değil, karar mesajını taşımalıdır.
- Ölçülen ve varsayılan değerler aynı görsel kodla sunulmamalıdır.
- Negatif değerler kırmızıyla belirtilmeli ancak dramatize edilmemelidir.
- Dashboard ekran görüntüleri tam sayfa küçültülmemeli; ilgili panel kırpılarak kullanılmalıdır.

## 10. Slayt Bazında Tasarım Brifi

### Slayt 1 — Kapak

**Amaç:** Projeyi tek cümlede konumlandırmak.

**Ana mesaj:** Üretim duruşlarını tahmin ediyor, nedenini açıklıyor ve OEE/finansal etkisini ölçüyoruz.

**Önerilen içerik:**

- trexCloud Hackathon
- Öngörücü OEE & Kök-Neden Analizi
- Alt başlık: “Tahmin → Kök-Neden → What-If → Finansal Değer”
- 12 makine, Ağustos 2025–Mayıs 2026

**Tasarım önerisi:** Büyük başlık, minimal üretim/telemetri motifi, çok az metin.

### Slayt 2 — Madalya Hedefi

**Amaç:** Jüri kriterleriyle projenin kapsamını eşlemek.

**Ana mesaj:** Bronz ve Gümüş temel; proje Altın ve Platin kriterlerine odaklanıyor.

**Görsel önerisi:** Dört aşamalı yatay yol veya olgunluk merdiveni. Altın ve Platin daha
güçlü vurgulanmalı.

### Slayt 3 — Veri Gerçeği

**Amaç:** Model kapsamının neden böyle seçildiğini açıklamak.

**Ana mesaj:** Model, dokümanda vaat edilen değil gerçekten akan sinyaller üzerine kuruldu.

**Korunacak bilgiler:**

- 12 makine, yaklaşık 7,4 milyon telemetri kaydı
- Servo sıcaklığı/güç sinyalleri 0 satır
- Path-load yalnız 28 satır
- Gerçek sinyaller: cycle_time, run_state, run_time, axis_position
- Nightwatch–MES eşleşmesi 162/162

**Görsel önerisi:** “Beklenen veri / Gerçekte mevcut veri” karşılaştırması.

### Slayt 4 — Mimari

**Amaç:** Sistemin uçtan uca akışını bir bakışta göstermek.

**Akış:**

`Kanonik sinyal katmanı → AD/RCA kanıtı → Kök-Neden → What-If/OEE → Tahmin ve değer`

**Görsel önerisi:** Beş kutulu akış; “denetimsiz AD” ve “denetimli tahmin” farklı görsel
etiketlerle ayrılmalı.

### Slayt 5 — Bronz ve Gümüş Temel

**Amaç:** Olay akışı, alarm-duruş eşleştirmesi ve Pareto temelini göstermek.

**Ana mesaj:** Arıza ile bağlantı kaybını ayırmadan doğru aksiyon sahibi seçilemez.

**Görsel önerisi:** Pareto ekran görüntüsü veya kırmızı/gri iki kategorili sade bar grafik.

**Konuşma cümlesi:**

> Bağlantı kaybını makine arızası sayarsak yanlış ekibe ve yanlış yatırıma gideriz.

### Slayt 6 — Altın: Kök-Neden

**Amaç:** Gerçek bir alarm kaskadında neden-sonuç ayrımını göstermek.

**Vaka:** Makine 1, 12 Ocak 2026 04:47.

**Nedensellik:**

`AIR PRESSURE FAILED → Z AXIS ZERO RETURN`

Kök neden hava basıncıdır; Z ekseni alarmı sonuçtur.

**Görsel önerisi:** Alarm kaskadı + küçük telemetri kanıtı + önerilen aksiyon.

**Dürüst not:** Baseline sapması bu vakada eşzamanlı kanıttır; öngörücü öncül değildir.

### Slayt 7 — Tahminin OEE ve Finansal Değeri

**Amaç:** ROC/lift katmanını operasyonel değere bağlamak.

**Ana metrikler:** ROC 0,7311; lift 2,38×; recall %69,1; +10,44 OEE puanı.

**Ana mesaj:** Recall kazanılabilecek duruş havuzunu, alarm sayısı ve precision ise
müdahale maliyetini belirler.

**Önemli anlatı:** Varsayılan 300 EUR kontrol maliyetinde sonuç negatiftir. Sistem bunu
gizlemek yerine ekonomik eşik duyarlılığını ayrıca gösterir.

**Görsel önerisi:** Soldan sağa zincir:

`ROC/Lift → 364/527 yakalama → 722 alarm / %44 precision → +10,44 OEE → EUR`

### Slayt 8 — Platin: Çapraz Makine

**Amaç:** Sistemik örüntünün şans veya vardiya ritminden farklı olduğunu göstermek.

**Ana sonuç:** 708 gözlenen eşzamanlı duruş; saat-içi ritmi koruyan null beklentisi 564;
`z=5,16, p<0,001`.

**Dürüst okuma:** {1,2,3,9} kümesi güçlü ortak zarf gösterse de türev korelasyonu yaklaşık
sıfırdır; akut arıza yayılımı iddia edilmemelidir.

**Görsel önerisi:** Gözlenen / vardiya-null / rastgele-null üç barı ve küçük dürüstlük notu.

### Slayt 9 — Senaryo Kataloğu

**Amaç:** What-If sonuçlarının seçilmiş tek bir örnek değil, denetlenebilir katalog olduğunu göstermek.

| Senaryo | Ana sonuç |
|---|---|
| S1 Makine 1, Duruş -%30 | +17,99 puan OEE; 625,1 saat runtime; +6.614 EUR net |
| S2 Makine 2, 8 saat plansız→planlı | +0,32 puan A/OEE; runtime yok; -300 EUR |
| S3 Makine 4, performans +%10 | ProductSum=0 nedeniyle inert; -300 EUR |
| S4 bağlantı düzeltme | 662,8 saat schedule görünürlüğü; OEE ve finansal değer 0 |

**Tasarım önerisi:** Dört satırlı tablo veya dört yatay kart. S1 yeşil, S2/S3 nötr,
S4 IT/ağ etiketiyle ayrılmalı.

### Slayt 10 — Sınırlar

**Amaç:** Çalışmanın neyi yapmadığını açıkça söyleyerek güven oluşturmak.

**Korunacak mesajlar:**

- Kondisyon sinyalleri boş; tahmin tavanını veri belirliyor.
- Mitsubishi 60 dakikalık hedefte doygun; makineler RCA/OEE'den çıkarılmadı.
- Plansız duruşların çoğu yalnız “Duruş” etiketi taşıyor.
- Kalite kaydı yok; Q simülasyonu gerçek ölçüm değildir.

**Tasarım önerisi:** “Biliyoruz / Bilmiyoruz / Sonraki veri ihtiyacı” üç sütunu.

### Slayt 11 — Sonuç

**Amaç:** Tek bir güçlü mesajla bitirmek.

**Önerilen kapanış:**

> Duruşu tahmin ediyoruz, nedenini açıklıyoruz ve aksiyonun OEE ile finansal etkisini
> denetlenebilir biçimde hesaplıyoruz.

**Görsel önerisi:** Üç büyük fiil: **Tahmin Et — Açıkla — Sayısallaştır**.

## 11. Canlı Arayüz Ekleri

Slayt 12–18 ana sunumun devamı değil, demo ve soru-cevap ekidir.

### Slayt 12 — Genel Bakış

- Tesis KPI'ları
- Rejime göre makine kartları
- Seçilen makinenin OEE/A/P/Q ayrışımı

Kaynak görsel: `analysis/reports/dashboard/overview_fleet.png`

### Slayt 13 — Pareto

- Kırmızı: makine duruşu
- Gri: bağlantı/IT
- Aksiyon sahibinin ayrıştırılması

Kaynak görsel: `analysis/reports/dashboard/overview_pareto.png`

### Slayt 14 — Tahmin Zaman Çizgisi

- Yeşil: tahmin edilen risk
- Kırmızı kesik: eşik 0,1778
- Kırmızı işaretler: gerçek ≥15 dakika plansız duruşlar

Kaynak görsel: `analysis/reports/dashboard/predict_risk.png`

### Slayt 15 — RCA

- Alarm kaskadı
- Telemetri kanıtı
- Sıralı hipotezler
- Önerilen aksiyon

Kaynak görsel: `analysis/reports/dashboard/predict_rca.png`

### Slayt 16 — Kestirimci Bakım Değeri ve What-If

- Üst panel model-atfedilebilir değerdir.
- Alt panel genel operasyon What-If senaryosudur.
- Bu iki hesap aynı şeymiş gibi birleştirilmemelidir.

Kaynak görseller:

- `analysis/reports/dashboard/predict_value.png`
- `analysis/reports/dashboard/predict_whatif.png`

### Slayt 17 — Senaryo Kataloğu

- ΔA, ΔP, ΔQ, ΔOEE
- Runtime ve schedule saatleri
- Net EUR ve geri ödeme
- Sıralanabilir tablo

Kaynak görsel: `analysis/reports/dashboard/predict_scenarios.png`

### Slayt 18 — Çapraz Makine

- Eski connectivity totolojisi
- Null-model destekli senkronizasyon
- Veri rejimleri
- Dürüst küme yorumu

Kaynak görsel: `analysis/reports/dashboard/cross_machine.png`

## 12. Önerilen Konuşma Akışı

### 30 saniyelik açılış

“Bu projede yalnızca bir tahmin modeli kurmadık. Duruş riskini önceden tahmin eden,
alarm ve telemetri kanıtıyla olası kök nedeni açıklayan, ardından alınacak aksiyonun OEE
ve finansal etkisini hesaplayan uçtan uca bir sistem geliştirdik.”

### 90 saniyelik teknik özet

“Önce veri envanterini çıkardık ve katalogda görünen kondisyon sinyallerinin gerçekte
akmadığını doğruladık. Bu nedenle denetimli tahmini ortak cycle-time ve run-state
sinyalleri bulunan Fanuc hücresiyle sınırladık. Modeli kronolojik held-out gelecekte
değerlendirdik. ROC 0,7311, lift 2,38 ve event recall %69,1 elde ettik. AD katmanını
tahmin modeli gibi sunmadık; RCA kanıtı olarak ayrı tuttuk.”

### 90 saniyelik iş değeri özeti

“Model 527 anlamlı duruşun 364'ünü yakaladı. Varsayılan %35 müdahale etkililiğinde
test döneminde 721,9 saat ve +10,44 OEE puanı atfedilebiliyor. Ancak her alarm bir
kontrol maliyeti doğuruyor. 722 alarm ve 300 EUR kontrol maliyetinde varsayılan eşik
ekonomik değil. Bu negatif sonucu gizlemedik; ayrıca yalnız retrospektif duyarlılık olarak
daha ekonomik çalışma noktasını gösterdik.”

### 30 saniyelik kapanış

“Sonuç olarak sistem tahmin ediyor, açıklıyor ve sayısallaştırıyor. Üstelik hangi sonucun
ölçüm, hangisinin varsayım ve hangisinin kapsam dışı olduğunu açıkça gösteriyor.”

## 13. Tasarımcının Değiştirebileceği Alanlar

- Slayt sıralaması, ana anlatı korunmak şartıyla sadeleştirilebilir.
- Metinler kısaltılabilir ve görsel hiyerarşi güçlendirilebilir.
- Grafik ve tablolar yeniden çizilebilir.
- Dashboard görselleri daha iyi maskelenebilir veya cihaz çerçevesine alınabilir.
- İkonlar, tipografi ve geçişler kurumsal seviyeye taşınabilir.
- Slayt 12–18 tek bir “Demo” bölümü veya yedek slayt grubu olarak yeniden tasarlanabilir.

## 14. Tasarımcının Değiştirmemesi Gereken Alanlar

- Model kapsamı ve Fanuc-only ifadesi
- Held-out metrikler
- Eşik 0,1778
- 364/527 recall hesabı
- 722 alarm ve %44 alarm dönemi isabeti
- Negatif varsayılan finansal sonuç
- Retrospektif eşiğin canlı eşik olmadığı bilgisi
- EUR değerlerinin ve müdahale etkililiğinin varsayım olduğu bilgisi
- System Offline'ın makine arızası olmadığı bilgisi
- AD ile supervised predictor ayrımı
- S1–S4 senaryo sonuçları

## 15. Mevcut Dosyalar

| Dosya | Kullanım |
|---|---|
| `trexCloud_Sunum.pptx` | Düzenlenecek ana PowerPoint |
| `trexCloud_Sunum.pdf` | Mevcut sunumun PDF karşılığı |
| `trexCloud_Sunum_Plani.pdf` | Slayt bazlı konuşma ve demo planı |
| `SUNUM_PROFESYONEL_TASARIM_BRIFI.md` | Bu düzenlenebilir brif |
| `analysis/reports/07_SCENARIOS.md` | Senaryo hesaplarının kaynağı |
| `analysis/reports/08_PM_VALUE.md` | Tahmin→OEE/finansal değer kaynağı |
| `analysis/reports/dashboard/` | Sunumda kullanılabilecek kırpılmış ekran görüntüleri |

## 16. Beklenen Profesyonel Teslim

- Düzenlenebilir 16:9 PPTX
- Aynı tasarımın PDF çıktısı
- Ana sunum ve appendix ayrımı
- Sunucu notlarının korunması
- Tüm grafik ve tabloların düzenlenebilir olması
- Varsayım/ölçüm/projeksiyon görsel etiket sisteminin tutarlı kullanılması
- Türkçe karakter ve ondalık biçimlerinin korunması
- Ekranda ve projeksiyonda okunabilecek minimum yazı boyutu

## 17. Son Kontrol Listesi

- [ ] Ana hikâye 7–9 dakikada anlatılabiliyor mu?
- [ ] İlk 30 saniyede proje değeri anlaşılıyor mu?
- [ ] AD ve tahmin modeli birbirinden ayrılıyor mu?
- [ ] Fanuc-only kapsamı görünür mü?
- [ ] Ölçüm, varsayım ve projeksiyon ayrımı görünür mü?
- [ ] Negatif varsayılan ROI saklanmadan açıklanıyor mu?
- [ ] Retrospektif eşik canlı eşik gibi sunulmuyor mu?
- [ ] S1–S4 sonuçları doğru mu?
- [ ] Dashboard ekranlarında metinler projeksiyonda okunuyor mu?
- [ ] Konuşmacı notları yeni tasarımda korunmuş mu?
