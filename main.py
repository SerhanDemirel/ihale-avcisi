import os
import requests
from supabase import create_client
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime, timedelta
import time
import json

# .env yükle
load_dotenv()

# Bağlantılar
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def ihaleleri_scrape_et():
    """Web sitesinden ihaleleri çeker (Test modunda mock veri)"""
    print(" İhale siteleri taranıyor...")
    
    # Gerçek scraping kodu buraya gelecek
    # Şimdilik test için mock veri
    bugun = datetime.now().strftime("%Y-%m-%d")
    
    mock_ihaleler = [
        {
            "baslik": f"İstanbul Büyükşehir Belediyesi Yol Bakım İşi - {bugun}",
            "kurum": "İstanbul Büyükşehir Belediyesi",
            "sehir": "İstanbul",
            "sektor": "İnşaat",
            "butce": 5000000,
            "tarih": (datetime.now() + timedelta(days=15)).isoformat(),
            "link": f"https://ekap.kik.gov.tr/test-{datetime.now().strftime('%Y%m%d')}-1",
            "detay": f"İstanbul ili çeşitli ilçelerinde yol bakım ve onarım işi. Tarih: {bugun}. Firmaların en az 10 yıllık tecrübesi ve ISO 9001 belgesi zorunlu. Geçici teminat %3."
        },
        {
            "baslik": f"Ankara Üniversitesi Bilgisayar Alımı - {bugun}",
            "kurum": "Ankara Üniversitesi",
            "sehir": "Ankara",
            "sektor": "Yazılım",
            "butce": 1500000,
            "tarih": (datetime.now() + timedelta(days=20)).isoformat(),
            "link": f"https://ekap.kik.gov.tr/test-{datetime.now().strftime('%Y%m%d')}-2",
            "detay": f"100 adet masaüstü bilgisayar alımı. Tarih: {bugun}. Geçici teminat 15.000 TL."
        }
    ]
    
    print(f"✅ {len(mock_ihaleler)} adet ihale bulundu.")
    return mock_ihaleler

def ai_ile_ozetle(detay):
    """Groq API ile özetle"""
    prompt = f"""
    Sen kamu ihaleleri uzmanısın. İhale metnini özetle:
    1. 📌 İşin Konusu
    2. 📅 Son Başvuru/Tarih
    3. ⚠️ Kritik Şartlar
    4. 💰 Teminat/Maliyet
    
    Metin: {detay}
    """
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=500
    )
    return response.choices[0].message.content

def veritabanina_kaydet(ihaleler):
    """Yeni ihaleleri veritabanına kaydet"""
    print("\n💾 Veritabanına kaydediliyor...")
    yeni_ihaleler = []
    
    for ihale in ihaleler:
        # Duplicate kontrolü
        existing = supabase.table("ihaleler").select("id").eq("link", ihale["link"]).execute()
        
        if existing.data:
            print(f"️ Atlandı: {ihale['baslik']}")
            continue
        
        print(f"🔄 İşleniyor: {ihale['baslik']}")
        
        # AI özet
        ozet = ai_ile_ozetle(ihale["detay"])
        
        # Kaydet
        ihale_data = {
            "baslik": ihale["baslik"],
            "ozet": ozet,
            "detay": ihale["detay"],
            "sehir": ihale["sehir"],
            "sektor": ihale["sektor"],
            "butce": ihale["butce"],
            "tarih": ihale["tarih"],
            "link": ihale["link"],
            "kurum_adi": ihale["kurum"],
            "kaynak": "otomatik_scraping"
        }
        
        result = supabase.table("ihaleler").insert(ihale_data).execute()
        yeni_ihaleler.append(result.data[0])
        print(f"   ✅ Kaydedildi: {result.data[0]['id']}")
        
        time.sleep(1)
    
    return yeni_ihaleler

def kullanıcılara_bildir():
    """Kullanıcı tercihlerine göre bildirim gönder"""
    print("\n📱 Kullanıcılara bildirim gönderiliyor...")
    
    now = datetime.now()
    gun = now.weekday()  # 0=Pazartesi, 6=Pazar
    
    # Tüm aktif premium kullanıcıları getir
    users = supabase.table("kullanicilar").select("*").eq("premium_mi", True).eq("aktif_mi", True).execute()
    
    for user in users.data:
        user_id = user['id']
        
        # Kullanıcının tercihlerini getir
        prefs = supabase.table("tercihler").select("*").eq("kullanici_id", user_id).eq("aktif_mi", True).execute()
        
        if not prefs.data:
            continue
        
        tercih = prefs.data[0]
        bildirim_tipi = tercih['bildirim_tipi']
        
        # Günlük mü haftalık mı kontrol et
        gonder = False
        if bildirim_tipi == 'gunluk':
            gonder = True
            baslik = "📅 GÜNLÜK İHALE ÖZETİ"
        elif bildirim_tipi == 'haftalik' and gun == 0:  # Pazartesi
            gonder = True
            baslik = " HAFTALIK İHALE ÖZETİ"
        
        if not gonder:
            continue
        
        # Zaman aralığını belirle
        if bildirim_tipi == 'gunluk':
            baslangic = (now - timedelta(days=1)).isoformat()
        else:  # haftalik
            baslangic = (now - timedelta(days=7)).isoformat()
        
        # Kullanıcının tercihlerine uygun ihaleleri bul
        sehirler = tercih['sehirler']
        sektorler = tercih['sektorler']
        min_butce = tercih['min_butce']
        max_butce = tercih['max_butce']
        
        query = supabase.table("ihaleler").select("*").gte("olusturulma", baslangic).eq("aktif_mi", True)
        
        if sehirler:
            query = query.in_("sehir", sehirler)
        
        response = query.execute()
        ihaleler = response.data
        
        # Client-side filtreleme
        ihaleler = [i for i in ihaleler if i.get('sektor') in sektorler and min_butce <= i.get('butce', 0) <= max_butce]
        
        # Daha önce gönderilmemiş olanları filtrele
        gonderilmis = supabase.table("gonderilen_ihaleler").select("ihale_id").eq("kullanici_id", user_id).execute()
        gonderilmis_ids = [g['ihale_id'] for g in gonderilmis.data]
        ihaleler = [i for i in ihaleler if i['id'] not in gonderilmis_ids]
        
        if not ihaleler:
            print(f"   ⏭️ {user['email']} için yeni ihale yok.")
            continue
        
        print(f"   📨 {user['email']} için {len(ihaleler)} ihale gönderilecek.")
        
        # Telegram bildirimi
        if tercih['bildirim_kanali'] == 'telegram' and tercih.get('telegram_chat_id'):
            chat_id = tercih['telegram_chat_id']
            
            mesaj = f"🔔 *{baslik}*\n\n"
            mesaj += f"👤 {user['ad_soyad']}\n"
            mesaj += f"📊 {len(ihaleler)} yeni ihale bulundu\n\n"
            mesaj += "-" * 40 + "\n\n"
            
            for ihale in ihaleler[:5]:  # Max 5 ihale
                mesaj += f" *{ihale['baslik']}*\n\n"
                mesaj += f"{ihale.get('ozet', 'Özet yok')}\n\n"
                mesaj += f"💰 {ihale.get('butce', 0):,} TL | 📍 {ihale.get('sehir', '-')}\n"
                mesaj += f"🔗 [Detay]({ihale['link']})\n\n"
                mesaj += "-" * 40 + "\n\n"
            
            if len(ihaleler) > 5:
                mesaj += f"\n⚠️ ve {len(ihaleler) - 5} ihale daha... Web panelinden görüntüleyin."
            
            tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            tg_payload = {
                "chat_id": chat_id,
                "text": mesaj,
                "parse_mode": "Markdown"
            }
            
            tg_response = requests.post(tg_url, json=tg_payload)
            
            if tg_response.status_code == 200:
                print(f"   ✅ Telegram gönderildi!")
                
                # Gönderim geçmişini kaydet
                for ihale in ihaleler:
                    supabase.table("gonderilen_ihaleler").insert({
                        "kullanici_id": user_id,
                        "ihale_id": ihale['id'],
                        "kanal": "telegram"
                    }).execute()
            else:
                print(f"   ⚠️ Telegram hatası: {tg_response.text}")

def main():
    print("="*60)
    print("🦅 İHALE AVCISI - OTOMATİK TARAMA")
    print(f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print(f"📅 Gün: {['Pazartesi','Salı','Çarşamba','Perşembe','Cuma','Cumartesi','Pazar'][datetime.now().weekday()]}")
    print("="*60)
    
    # 1. İhaleleri çek
    ihaleler = ihaleleri_scrape_et()
    
    # 2. Veritabanına kaydet
    yeni_ihaleler = veritabanina_kaydet(ihaleler)
    print(f"\n✅ {len(yeni_ihaleler)} yeni ihale kaydedildi.")
    
    # 3. Kullanıcılara bildir
    kullanıcılara_bildir()
    
    print("\n" + "="*60)
    print("✅ TAMAMLANDI!")
    print("="*60)

if __name__ == "__main__":
    main()