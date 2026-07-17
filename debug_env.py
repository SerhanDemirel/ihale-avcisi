import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

print("=" * 50)
print(" .env DOSYASI İÇERİĞİ:")
print("=" * 50)
print(f"SUPABASE_URL: '{url}'")
print(f"SUPABASE_KEY: '{key[:30]}...' (ilk 30 karakter)")
print(f"URL uzunluğu: {len(url) if url else 0}")
print(f"URL https:// ile başlıyor mu? {url.startswith('https://') if url else False}")
print("=" * 50)

# URL'yi parçalarına ayır
if url:
    print(f"Protocol: {url.split('://')[0] if '://' in url else 'YOK'}")
    print(f"Domain: {url.split('://')[1] if '://' in url else 'YOK'}")