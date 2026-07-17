import json
import os
import requests
from groq import Groq
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# Bilgileri .env'den oku
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not GROQ_API_KEY or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("⚠️ HATA: .env dosyasında gerekli API anahtarları eksik!")
    exit(1)

print("🤖 Yapay zeka ihale metnini okuyor...\n")

try:
    # 1. Mock veriyi oku
    with open('ornek_ihale.json', 'r', encoding='utf-8') as file:
        ihale = json.load(file)
    
    print(f"📄 Okunan İhale: {ihale['baslik']}\n")

    # 2. Groq client oluştur
    client = Groq(api_key=GROQ_API_KEY)

    # 3. Prompt hazırla
    prompt = f"""
    Sen deneyimli bir kamu ihaleleri uzmanısın. 
    Aşağıdaki ihale metnini oku ve bir şirket sahibine sunmak üzere 
    SADECE şu 4 başlık altında, kısa ve net maddeler halinde özetle:
    
    1. 📌 İşin Konusu
    2. 📅 Son Başvuru/Tarih
    3. ⚠️ Kritik Şartlar
    4. 💰 Teminat/Maliyet

    İhale Metni:
    {ihale['detay']}
    """

    # 4. Groq'a gönder
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=500
    )
    
    ozet_metni = response.choices[0].message.content
    
    print("✅ YAPAY ZEKA ÖZETİ:")
    print("-" * 50)
    print(ozet_metni)
    print("-" * 50)

    # 5. TELEGRAM'A GÖNDERME BÖLÜMÜ
    print("\n📱 Telegram bildirimi hazırlanıyor...")
    
    telegram_mesaji = f"🔔 *YENİ İHALE FIRSATI!* 🔔\n\n📌 *{ihale['baslik']}*\n\n{ozet_metni}\n\n🔗 Detaylar için sistemimizi ziyaret edin."
    
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": telegram_mesaji,
        "parse_mode": "Markdown"
    }
    
    telegram_response = requests.post(telegram_url, json=payload)
    
    if telegram_response.status_code == 200:
        print("✅ BAŞARILI! Özet telefonuna Telegram bildirimi olarak gönderildi.")
    else:
        print(f"⚠️ Telegram hatası: {telegram_response.text}")

    print("\n🎉 Tebrikler! İhale Avcısı MVP'si tam kapasite çalıştı!")

except Exception as e:
    print(f"⚠️ Bir hata oluştu: {e}")