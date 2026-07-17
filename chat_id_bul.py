import requests

BOT_TOKEN = "8992270856:AAHp-z-f8TxmULu2ZavqDV8BI3iBAh9HYIY"

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