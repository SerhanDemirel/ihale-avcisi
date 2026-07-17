import streamlit as st
import os
import requests
from supabase import create_client
from dotenv import load_dotenv
from groq import Groq
from datetime import datetime, timedelta
import json

# Sayfa ayarları
st.set_page_config(page_title="🦅 İhale Avcısı", page_icon="🦅", layout="wide")

# .env yükle
load_dotenv()

# Bağlantılar
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()
client = Groq(api_key=GROQ_API_KEY)

# Session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'user_email' not in st.session_state:
    st.session_state.user_email = None

# ============================================
# GİRİŞ YAPILMAMIŞSA → LOGIN/KAYIT EKRANI
# ============================================
if not st.session_state.user_id:
    st.title(" İhale Avcısı'na Hoş Geldiniz")
    st.markdown("**Yapay zeka destekli ihale takip sistemi**")
    
    tab1, tab2 = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol"])
    
    # GİRİŞ
    with tab1:
        st.subheader("Giriş Yap")
        login_email = st.text_input("E-posta", key="login_email")
        login_sifre = st.text_input("Şifre", type="password", key="login_sifre")
        
        if st.button("Giriş Yap", type="primary", use_container_width=True):
            if login_email and login_sifre:
                try:
                    user = supabase.table("kullanicilar").select("*").eq("email", login_email).eq("sifre", login_sifre).eq("aktif_mi", True).execute()
                    
                    if user.data:
                        st.session_state.user_id = user.data[0]['id']
                        st.session_state.user_email = user.data[0]['email']
                        
                        # Son giriş tarihini güncelle
                        supabase.table("kullanicilar").update({"son_giris_tarihi": datetime.now().isoformat()}).eq("id", st.session_state.user_id).execute()
                        
                        st.success("✅ Giriş başarılı!")
                        st.rerun()
                    else:
                        st.error("❌ Hatalı e-posta veya şifre!")
                except Exception as e:
                    st.error(f"Hata: {e}")
    
    # KAYIT
    with tab2:
        st.subheader("Yeni Hesap Oluştur")
        st.info("🎁 Kayıt olan herkese **7 gün ücretsiz demo** hediye!")
        
        kayit_email = st.text_input("E-posta", key="kayit_email")
        kayit_sifre = st.text_input("Şifre (min 6 karakter)", type="password", key="kayit_sifre")
        kayit_ad = st.text_input("Ad Soyad", key="kayit_ad")
        kayit_tel = st.text_input("Telefon (Opsiyonel)", key="kayit_tel")
        
        if st.button("Kayıt Ol ve Demo Başlat", type="primary", use_container_width=True):
            if kayit_email and kayit_sifre and kayit_ad:
                if len(kayit_sifre) < 6:
                    st.error("Şifre en az 6 karakter olmalı!")
                else:
                    try:
                        demo_bitis = datetime.now() + timedelta(days=7)
                        
                        user_data = {
                            "email": kayit_email,
                            "sifre": kayit_sifre,
                            "ad_soyad": kayit_ad,
                            "telefon": kayit_tel,
                            "demo_baslangic": datetime.now().isoformat(),
                            "demo_bitis": demo_bitis.isoformat(),
                            "premium_mi": False
                        }
                        
                        result = supabase.table("kullanicilar").insert(user_data).execute()
                        st.success("✅ Kayıt başarılı! Giriş yapabilirsiniz.")
                        
                    except Exception as e:
                        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                            st.error("Bu e-posta zaten kayıtlı!")
                        else:
                            st.error(f"Hata: {e}")
            else:
                st.error("E-posta, şifre ve ad soyad zorunludur!")
    
    st.divider()
    st.caption("🦅 İhale Avcısı v1.0")
    st.stop()  # Giriş yapılmadıysa aşağısını gösterme

# ============================================
# GİRİŞ YAPILDIYSA → ANA PANEL
# ============================================
st.title("🦅 İhale Avcısı Paneli")

# Kullanıcı bilgilerini çek
user = supabase.table("kullanicilar").select("*").eq("id", st.session_state.user_id).execute().data[0]

# Sidebar
with st.sidebar:
    st.markdown(f"### 👤 {user['ad_soyad']}")
    st.markdown(f" {user['email']}")
    
    if user['premium_mi']:
        st.success("⭐ Premium Üye")
        if user.get('premium_bitis'):
            st.markdown(f"Bitiş: {user['premium_bitis'][:10]}")
    else:
        st.warning("🎁 Demo Üye")
        if user.get('demo_bitis'):
            kalan = (datetime.fromisoformat(user['demo_bitis'].replace('Z', '+00:00').replace('+00:00', '')) - datetime.now()).days
            st.markdown(f"Kalan süre: **{kalan} gün**")
    
    st.divider()
    menu = st.radio("Menü", ["📋 İhaleler", "⚙️ Tercihlerim", "👤 Profilim", "🚪 Çıkış"])

# ============================================
# MENÜ 1: İHALELER
# ============================================
if menu == "📋 İhaleler":
    st.header("📋 İhaleler")
    
    # Filtreler
    col1, col2 = st.columns(2)
    with col1:
        filtre_sehir = st.multiselect("Şehir", ["İstanbul", "Ankara", "İzmir", "Bursa", "Antalya", "Adana"])
    with col2:
        filtre_sektor = st.multiselect("Sektör", ["İnşaat", "Temizlik", "Yazılım", "Danışmanlık", "Gıda", "Sağlık"])
    
    # İhaleleri getir
    query = supabase.table("ihaleler").select("*").eq("aktif_mi", True).order("olusturulma", desc=True).limit(50)
    
    if filtre_sehir:
        query = query.in_("sehir", filtre_sehir)
    
    response = query.execute()
    ihaleler = response.data
    
    if filtre_sektor:
        ihaleler = [i for i in ihaleler if i.get('sektor') in filtre_sektor]
    
    st.markdown(f"**📊 {len(ihaleler)} ihale bulundu**")
    
    if not ihaleler:
        st.info("Henüz ihale bulunmuyor. Sistem her gün otomatik olarak yeni ihaleleri tarıyor.")
    else:
        for ihale in ihaleler:
            with st.expander(f" {ihale['baslik']}", expanded=False):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**📍 Şehir:** {ihale.get('sehir', '-')}")
                    st.markdown(f"**🏷️ Sektör:** {ihale.get('sektor', '-')}")
                    st.markdown(f"** Bütçe:** {ihale.get('butce', 0):,} TL")
                    st.markdown(f"**🏢 Kurum:** {ihale.get('kurum_adi', '-')}")
                    if ihale.get('tarih'):
                        st.markdown(f"**📅 Tarih:** {ihale['tarih'][:10]}")
                with col2:
                    st.markdown(f"[ Detay]({ihale['link']})")
                
                if ihale.get('ozet'):
                    st.divider()
                    st.markdown("** AI Özeti:**")
                    st.info(ihale['ozet'])

# ============================================
# MENÜ 2: TERCİHLERİM
# ============================================
elif menu == "️ Tercihlerim":
    st.header("⚙️ Bildirim Tercihlerim")
    
    if not user['premium_mi']:
        st.warning("⚠️ Tercihleri ayarlamak için **Premium üyelik** gereklidir.")
        st.info("Demo süreniz bittikten sonra veya şimdi yükselterek tercihlerinizi ayarlayabilirsiniz.")
        
        if st.button("⭐ Premium'a Yükselt (Test)", type="primary"):
            # Test için direkt premium yap
            premium_bitis = datetime.now() + timedelta(days=30)
            supabase.table("kullanicilar").update({
                "premium_mi": True,
                "premium_baslangic": datetime.now().isoformat(),
                "premium_bitis": premium_bitis.isoformat()
            }).eq("id", st.session_state.user_id).execute()
            st.success("✅ Premium üyelik aktif edildi!")
            st.rerun()
    else:
        st.success("⭐ Premium üye olarak tercihlerinizi ayarlayabilirsiniz.")
        
        # Mevcut tercihleri çek
        prefs = supabase.table("tercihler").select("*").eq("kullanici_id", st.session_state.user_id).execute()
        tercih = prefs.data[0] if prefs.data else None
        
        with st.form("tercih_formu"):
            st.subheader("📍 Şehir Tercihleri")
            sehirler = st.multiselect(
                "İlgilendiğiniz şehirler",
                ["İstanbul", "Ankara", "İzmir", "Bursa", "Antalya", "Adana", "Konya", "Gaziantep"],
                default=tercih['sehirler'] if tercih else []
            )
            
            st.subheader("🏷️ Sektör Tercihleri")
            sektorler = st.multiselect(
                "İlgilendiğiniz sektörler",
                ["İnşaat", "Temizlik", "Yazılım", "Danışmanlık", "Gıda", "Sağlık", "Eğitim", "Enerji"],
                default=tercih['sektorler'] if tercih else []
            )
            
            st.subheader(" Bütçe Aralığı")
            col1, col2 = st.columns(2)
            with col1:
                min_butce = st.number_input("Minimum Bütçe (TL)", min_value=0, value=tercih['min_butce'] if tercih else 0, step=100000)
            with col2:
                max_butce = st.number_input("Maksimum Bütçe (TL)", min_value=0, value=tercih['max_butce'] if tercih else 100000000, step=100000)
            
            st.subheader("📱 Bildirim Ayarları")
            bildirim_tipi = st.radio(
                "Bildirim Sıklığı",
                ["gunluk", "haftalik"],
                format_func=lambda x: "📅 Günlük (Her gün 08:00)" if x == "gunluk" else "📆 Haftalık (Her Pazartesi 08:00)",
                index=0 if (tercih and tercih['bildirim_tipi'] == 'gunluk') else 1
            )
            
            bildirim_kanali = st.radio(
                "Bildirim Kanalı",
                ["telegram", "email"],
                format_func=lambda x: "📱 Telegram" if x == "telegram" else "📧 E-posta",
                index=0 if (tercih and tercih['bildirim_kanali'] == 'telegram') else 1
            )
            
            if bildirim_kanali == "telegram":
                telegram_chat_id = st.text_input(
                    "Telegram Chat ID",
                    value=tercih['telegram_chat_id'] if tercih and tercih.get('telegram_chat_id') else "",
                    help="Telegram'da @userinfobot'a /start yazarak Chat ID'nizi öğrenebilirsiniz."
                )
            else:
                telegram_chat_id = None
            
            submitted = st.form_submit_button(" Tercihleri Kaydet", type="primary", use_container_width=True)
            
            if submitted:
                if not sehirler or not sektorler:
                    st.error("En az bir şehir ve bir sektör seçmelisiniz!")
                else:
                    tercih_data = {
                        "kullanici_id": st.session_state.user_id,
                        "sehirler": sehirler,
                        "sektorler": sektorler,
                        "min_butce": min_butce,
                        "max_butce": max_butce,
                        "bildirim_tipi": bildirim_tipi,
                        "bildirim_kanali": bildirim_kanali,
                        "telegram_chat_id": telegram_chat_id,
                        "aktif_mi": True
                    }
                    
                    try:
                        if tercih:
                            supabase.table("tercihler").update(tercih_data).eq("id", tercih['id']).execute()
                        else:
                            supabase.table("tercihler").insert(tercih_data).execute()
                        st.success("✅ Tercihleriniz kaydedildi!")
                    except Exception as e:
                        st.error(f"Hata: {e}")

# ============================================
# MENÜ 3: PROFİLİM
# ============================================
elif menu == "👤 Profilim":
    st.header("👤 Profilim")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**E-posta:** {user['email']}")
        st.markdown(f"**Ad Soyad:** {user['ad_soyad']}")
        if user.get('telefon'):
            st.markdown(f"**Telefon:** {user['telefon']}")
    
    with col2:
        if user['premium_mi']:
            st.success("⭐ Premium Üye")
            st.markdown(f"Başlangıç: {user.get('premium_baslangic', '-')[:10]}")
            st.markdown(f"Bitiş: {user.get('premium_bitis', '-')[:10]}")
        else:
            st.warning(" Demo Üye")
            st.markdown(f"Demo Başlangıç: {user.get('demo_baslangic', '-')[:10]}")
            st.markdown(f"Demo Bitiş: {user.get('demo_bitis', '-')[:10]}")
    
    st.divider()
    
    # Gönderilen ihale sayısı
    gonderilen = supabase.table("gonderilen_ihaleler").select("*", count="exact").eq("kullanici_id", st.session_state.user_id).execute()
    st.metric("Size Gönderilen İhale Sayısı", gonderilen.count if hasattr(gonderilen, 'count') else 0)

# ============================================
# MENÜ 4: ÇIKIŞ
# ============================================
elif menu == "🚪 Çıkış":
    if st.button("Çıkış Yap"):
        st.session_state.user_id = None
        st.session_state.user_email = None
        st.success("Çıkış yapıldı!")
        st.rerun()

# Footer
st.divider()
st.caption("🦅 İhale Avcısı v2.0 | Kullanıcı Sistemi Aktif")