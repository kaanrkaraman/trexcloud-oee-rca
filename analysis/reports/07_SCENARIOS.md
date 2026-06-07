# Inspectable Scenario Catalog

Each machine scenario is recomputed from raw OEE components. Connectivity is short-circuited because System Offline is an IT/collector issue, not machine downtime.

| ID | Scenario | Scope | Owner | dA pp | dP pp | dQ pp | dOEE pp | Runtime h | Schedule h | Extra pieces | Gross EUR | Net EUR | Payback d |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| S1 | En büyük plansız duruş kalemi -%30 | Makine 1 / Duruş / tüm OEE baseline dönemi | Bakım | 17.99 | 0.00 | 0.00 | 17.99 | 625.1 | 0.0 | 374 | 6,914 | 6,614 | 0.0 |
| S2 | En büyük plansız duruş kalemi -%30 | Makine 5 / Duruş / tüm OEE baseline dönemi | Bakım | 15.28 | 0.00 | 0.00 | 15.28 | 420.3 | 0.0 | 211 | 5,797 | 5,497 | 0.0 |
| S3 | Çevrim süresi +%10 | Makine 3 / Tüm OEE baseline dönemi; Performans kaldıracı | Proses mühendisliği | 0.00 | 0.00 | 0.00 | 0.00 | 0.0 | 0.0 | 0 | 0 | -300 | - |
| S4 | Tesis genelinde bağlantı kesintisi giderilir | PLANT / 85 tekilleştirilmiş collector offline penceresi | IT / ağ | 0.00 | 0.00 | 0.00 | 0.00 | 0.0 | 662.8 | 0 | 0 | 0 | - |

## Interpretation

- **S1**: Duruş süresi %30 azaltılır; etki A ve OEE üzerinden hesaplanır.
- **S2**: Duruş süresi %30 azaltılır; ikinci bir makinede de etki A ve OEE üzerinden gelir.
- **S3**: Üretim yapılan 777 makine gününün 605'inde P tam 1, 172'sinde 0 ve arada hiçbir gün yoktur. P bu veride dejeneredir, bu yüzden çevrim iyileştirmesi OEE'yi oynatmaz.
- **S4**: Bağlantı düzeltmesi veri ve program görünürlüğünü geri getirir. Bu bir IT aksiyonudur; makine OEE'sine veya kestirimci bakım değerine yazılmaz.

> USER-PROVIDED ASSUMPTIONS — the dataset contains NO cost/price data; treat all currency figures as hypotheses, not facts.
