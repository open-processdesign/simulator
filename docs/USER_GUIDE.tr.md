# Kullanım kılavuzu

Open Process Design tarayıcınızda çalışır: https://open-processdesign.github.io/simulator/
Sonuçlar eğitim ve ön tasarım içindir; kullanmadan önce doğrulayın.

## 1. Bileşenler
Ad, formül veya CAS numarasıyla arayın ve prosesinizin bileşenlerini ekleyin. Tabloda mol kütlesi ve normal kaynama noktası görünür.

## 2. Termodinamik
Bir özellik yöntemi seçin:
- **İdeal (Raoult)**: düşük basınç, benzer moleküller.
- **Peng–Robinson / SRK**: hidrokarbonlar ve gazlar, yüksek basınçta da.
- **NRTL**: düşük basınçta polar, ideal olmayan sıvılar (alkol–su).
- **UNIQUAC**: NRTL gibi; molekül boyutu ve yüzeyi (r, q) UNIFAC gruplarından, çift başına iki parametre.

Tablo ikili parametreleri ve kaynağını gösterir (veritabanı, sizin değeriniz veya yok → nötr değer). Kendi değerinizi yazabilirsiniz; "veritabanı değerini kullan" geri alır.

## 3. Akış şeması
- Paletten üniteleri sürükleyin (veya tıklayın). Akım için bir **çıkışı (sağ)** bir **girişe (sol)** bağlayın.
- Üniteye tıklayınca yan panelde ayarları görünür. Beslemeye tıklayıp sıcaklık (veya buhar kesri), basınç, debi ve bileşim girin.
- Durum noktası: gri = henüz kontrol edilmedi, içi boş yeşil = girdiler tamam, turuncu = eksik var, kırmızı = hata, dolu yeşil = çözüldü.
- Delete veya Backspace seçili ünite ya da akımı siler.

## 4. Çalıştır
Eksik kalanları, her birine bağlantıyla gösterir. **Çalıştır**'a basın.

## 5. Sonuçlar
- Akım tablosu, ünite sonuçları ve mesajlar; bir akıma veya mesaja tıklayınca tuvalde ilgili yere gider.
- Kolonlar ve piston akışlı reaktörler profilleri de gösterir (grafik ve tablo).
- **CSV dışa aktar** sonuçları Excel için kaydeder (Türkçede `;` ve ondalık virgül).

## Birimler ve dil
Sağ üstte birim seti (SI, Metrik, İngiliz) ve dil (English, Türkçe) seçilir. Dosyalar her zaman SI birimiyle saklanır.

## Dosyalar
**Dosya → Dosya olarak kaydet** prosesinizi `.opd.json` olarak saklar; **Dosya → Aç…** geri yükler. **Dosya → Örnekler** hazır prosesler içerir. Son prosesiniz bu tarayıcıda da tutulur.

## Mevcut üniteler
Besleme, ürün, karıştırıcı, ayırıcı, flaş, ısıtıcı/soğutucu, ısı değiştirici, vana, pompa, kompresör, dönüşüm reaktörü, CSTR, PFR, denge reaktörü, kısa yol kolonu (FUG), distilasyon kolonu (rigorous). Geri döngüler otomatik çözülür.

**Denge reaktörü.** Tepkime fazını seçin (gaz veya sıvı). K oluşum verilerinden ya da kendi korelasyonunuzdan (ln K = a + b/T + c·ln T, ör. bir makaleden) gelir. Sıvı fazda aktiflikler saf sıvıya göre x·γ'dır; polar karışımlar için NRTL veya UNIQUAC kullanın. Örnek: *MTBE synthesis*.

**Gövde-boru geometrisi.** Isı değiştiricinin yan panelinde *Gövde-boru geometrisi*ni açın; boru sayısı, geçiş, pitch, gövde çapı, şaşırtma aralığı ve kirlilik değerlerini girin. Kern yöntemi film katsayılarını, U'yu, alanı ve iki basınç düşümünü verir (siz vermediyseniz çıkışlara uygulanır). Değiştiriciyi değerlendirmek için ısıl spesifikasyonu boş bırakın; fazla tasarımı görmek için çıkış sıcaklığı veya görev verin. Örnek: *Toluene cooler*.

**Isı değiştirici bölgeleri.** Değiştirici görevini bölgelere ayırır (varsayılan 10, yan panel → *Bölge analizi*) ve içindeki her kabarcık/çiğ noktasına bir bölge sınırı ekler. UA bölgelerin toplamıdır, *en küçük yaklaşma* iç pinch noktasıdır; Sonuçlar sayfası T–Q ısı eğrilerini çizer. Uçlar sorunsuz görünse bile değiştiricinin içindeki sıcaklık kesişmesi bildirilir. Örnek: *Steam-heated vaporizer*.
