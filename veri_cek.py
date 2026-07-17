import ssl
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
import urllib3

# SSL uyarılarını kapat
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ekap.kik.gov.tr eski bir cipher seti sunuyor; OpenSSL 3.0'ın varsayılan
# SECLEVEL=2 ayarı bunu reddediyor, bu yüzden seviyeyi düşürüyoruz.
class LegacyTLSAdapter(HTTPAdapter):
    def _build_context(self):
        ctx = ssl.create_default_context()
        ctx.set_ciphers("DEFAULT@SECLEVEL=1")
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = self._build_context()
        return super().init_poolmanager(*args, **kwargs)

    def init_proxy_manager(self, *args, **kwargs):
        kwargs["ssl_context"] = self._build_context()
        return super().init_proxy_manager(*args, **kwargs)

session = requests.Session()
session.mount("https://", LegacyTLSAdapter())

# EKAP İlan Sorgulama Sayfası
url = "https://ekap.kik.gov.tr/EKAP/ihale/ihaleListesi.html"

print("🔍 EKAP (Kamu İhale Kurumu) taranıyor...\n")

try:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    response = session.get(url, headers=headers, verify=False, timeout=10)
    print(f"✅ Durum Kodu: {response.status_code}")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # İhale başlıklarını bul (genellikle h2, h3 veya a etiketlerinde)
    ihale_sayisi = 0
    
    # Tüm linkleri kontrol et
    for link in soup.find_all('a', href=True):
        text = link.get_text().strip()
        href = link['href']
        
        # İhale ile ilgili linkleri filtrele
        if any(keyword in text.lower() for keyword in ['ihale', 'alim', 'hizmet', 'yapim']):
            print(f"✅ BULUNDU: {text}")
            print(f"   Link: {href}")
            print("-" * 60)
            ihale_sayisi += 1
            
            if ihale_sayisi >= 5:
                break
    
    if ihale_sayisi == 0:
        print("❌ İhale bulunamadı. Site yapısı farklı olabilir.")
        print("\n💡 Alternatif: İlan.gov.tr ana sayfasından deneyelim mi?")

except requests.exceptions.Timeout:
    print("⚠️ Siteye bağlanırken zaman aşımı. EKAP yavaş olabilir.")
except Exception as e:
    print(f"⚠️ Bir hata oluştu: {e}")
    import traceback
    traceback.print_exc()