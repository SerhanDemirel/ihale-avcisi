import requests
import os
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    print("⚠️ HATA: TELEGRAM_BOT_TOKEN .env dosyasında bulunamadı.")

url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"

response = requests.get(url)
data = response.json()

print("Gelen veri:")
print(data)

if data.get("result"):
    chat_id = data["result"][0]["message"]["chat"]["id"]
    print(f"\n✅ Chat ID'niz: {chat_id}")
else:
    print("\n⚠️ Henüz mesaj bulunamadı. Botuna bir mesaj atıp tekrar dene.")