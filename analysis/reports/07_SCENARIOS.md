# Inspectable Scenario Catalog

Each machine scenario is recomputed from raw OEE components. Connectivity is short-circuited because System Offline is an IT/collector issue, not machine downtime.

| ID | Scenario | Scope | Owner | dA pp | dP pp | dQ pp | dOEE pp | Runtime h | Schedule h | Extra pieces | Gross EUR | Net EUR | Payback d |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| S1 | En büyük plansız duruş kalemi -%30 | Makine 1 / Duruş / tüm OEE baseline dönemi | Bakım | 17.99 | 0.00 | 0.00 | 17.99 | 625.1 | 0.0 | 374 | 6,914 | 6,614 | 0.0 |
| S2 | 8 saat plansız -> planlı bakım | Makine 2 / Tüm OEE baseline dönemi; sınıflandırma/program değişikliği | Bakım planlama | 0.32 | 0.00 | 0.00 | 0.32 | 0.0 | 0.0 | 0 | 0 | -300 | - |
| S3 | Performans/çevrim +%10 | Makine 4 / Tüm OEE baseline dönemi; ProductSum=0 | Proses mühendisliği | 0.00 | 0.00 | 0.00 | 0.00 | 0.0 | 0.0 | 0 | 0 | -300 | - |
| S4 | Tesis genelinde bağlantı düzeltildi | PLANT / 85 tekilleştirilmiş collector offline penceresi | IT / ağ | 0.00 | 0.00 | 0.00 | 0.00 | 0.0 | 662.8 | 0 | 0 | 0 | - |

## Interpretation

- **S1**: Duruş süresi %30 azaltılır; etki A ve OEE üzerinden hesaplanır.
- **S2**: 8 saat plansız duruş planlı bakıma taşınır; A yükselir fakat runtime kazanılmaz.
- **S3**: ProductSum=0 olduğu için P kolu inerttir; OEE veya finansal fayda üretmez.
- **S4**: Bağlantı düzeltmesi veri ve program görünürlüğünü geri getirir. Bu bir IT aksiyonudur; makine OEE'sine veya kestirimci bakım değerine yazılmaz.

> USER-PROVIDED ASSUMPTIONS — the dataset contains NO cost/price data; treat all currency figures as hypotheses, not facts.
