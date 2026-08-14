import streamlit as st
from supabase import create_client, Client
from groq import Groq
import base64
import uuid
from datetime import datetime

# --- 1. SAYFA VE TASARIM AYARLARI ---
st.set_page_config(
    page_title="Alışkanlık Asistanı", 
    page_icon="🌱", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS Tasarımları
st.markdown("""
    <style>
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stButton>button { width: 100%; }
    
    /* Sol üstteki sabit Yeşil Menü Kutusu */
    div[data-testid="stColumn"] button[key="btn_toggle_sidebar"] {
        background-color: #2e7d32 !important;
        color: #ffffff !important;
        font-weight: bold !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 8px 16px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;
    }
    
    /* Geçmiş Sohbet Kartı Tasarımı */
    .chat-card {
        background-color: #f9f9f9;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #2e7d32;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. SUPABASE BAĞLANTISI ---
@st.cache_resource
def get_supabase_client():
    try:
        url = st.secrets.get("SUPABASE_URL", "").strip().rstrip("/")
        key = st.secrets.get("SUPABASE_KEY", "").strip()
        if not url or not key:
            return None
        return create_client(url, key)
    except Exception:
        return None

supabase = get_supabase_client()

# --- 3. OTURUM VE SESSION OTOMATİK KONTROLÜ ---
if "user" not in st.session_state:
    st.session_state.user = None

if supabase and not st.session_state.user:
    try:
        session = supabase.auth.get_session()
        if session and session.user:
            st.session_state.user = session.user
            meta = session.user.user_metadata or {}
            st.session_state.profile_name = meta.get("full_name", session.user.email.split('@')[0])
            st.session_state.birth_date = meta.get("birth_date", "2000-01-01")
            st.session_state.gender = meta.get("gender", "Belirtilmedi")
    except Exception:
        pass

# --- SOHBET GRUPLAMA MİMARİSİ ---
if "chats" not in st.session_state:
    st.session_state.chats = {}

if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None

if "show_auth_modal" not in st.session_state:
    st.session_state.show_auth_modal = False
if "gun_sayisi" not in st.session_state:
    st.session_state.gun_sayisi = 1
if "sayfa" not in st.session_state:
    st.session_state.sayfa = "🌱 AI Koç & Sohbet"
if "sidebar_open" not in st.session_state:
    st.session_state.sidebar_open = False

# Profil Bilgileri
if "profile_name" not in st.session_state:
    st.session_state.profile_name = ""
if "profile_pic" not in st.session_state:
    st.session_state.profile_pic = None
if "birth_date" not in st.session_state:
    st.session_state.birth_date = "2000-01-01"
if "gender" not in st.session_state:
    st.session_state.gender = "Belirtilmedi"

# --- 4. GİRİŞ YAPILMAMIŞSA ---
if not st.session_state.user:
    
    col_logo, col_space, col_login, col_register = st.columns([3, 4, 1.5, 1.5])
    
    with col_logo:
        st.markdown("### 🌱 **Karakter & Alışkanlık Koçu**")
        
    with col_login:
        if st.button("🔑 Giriş Yap"):
            st.session_state.show_auth_modal = "login"
            
    with col_register:
        if st.button("📝 Üye Ol", type="primary"):
            st.session_state.show_auth_modal = "register"

    st.divider()

    if st.session_state.show_auth_modal:
        _, auth_col, _ = st.columns([1, 2, 1])
        with auth_col:
            if not supabase:
                st.error("Veri tabanı bağlantısı kurulamadı. Secrets ayarlarını kontrol edin.")
            else:
                st.info("Devam etmek için hesabınıza giriş yapın veya kayıt olun.")
                tab_login, tab_register = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol"])
                
                # GİRİŞ YAP
                with tab_login:
                    email = st.text_input("E-Posta Adresi", key="l_email")
                    password = st.text_input("Şifre", type="password", key="l_pass")
                    
                    if st.button("Giriş Yap", type="primary", key="btn_l"):
                        if not email or not password:
                            st.warning("Lütfen tüm alanları doldurun.")
                        else:
                            try:
                                clean_email = email.strip().lower()
                                res = supabase.auth.sign_in_with_password({
                                    "email": clean_email,
                                    "password": password
                                })
                                st.session_state.user = res.user
                                meta = res.user.user_metadata or {}
                                st.session_state.profile_name = meta.get("full_name", clean_email.split('@')[0])
                                st.session_state.birth_date = meta.get("birth_date", "2000-01-01")
                                st.session_state.gender = meta.get("gender", "Belirtilmedi")
                                st.session_state.show_auth_modal = False
                                st.success("Giriş başarılı!")
                                st.rerun()
                            except Exception as err:
                                st.error("Giriş Başarısız: E-posta/şifre hatalı veya hesabınız henüz doğrulanmamış.")

                # KAYIT OL (E-POSTA DOĞRULAMA UYARISI İLE)
                with tab_register:
                    reg_name = st.text_input("Ad Soyad", key="r_name")
                    reg_email = st.text_input("E-Posta Adresi", key="r_email")
                    reg_pass = st.text_input("Şifre (En az 6 karakter)", type="password", key="r_pass")
                    reg_pass_conf = st.text_input("Şifre Tekrar", type="password", key="r_conf")
                    
                    col_bdate, col_gnd = st.columns(2)
                    with col_bdate:
                        reg_bdate = st.date_input("Doğum Tarihi", key="r_bdate")
                    with col_gnd:
                        reg_gender = st.selectbox("Cinsiyet", ["Kadın", "Erkek", "Belirtmek İstemiyorum"], key="r_gnd")
                    
                    if st.button("Kayıt Ol", key="btn_r"):
                        if not reg_email or not reg_pass or not reg_name:
                            st.warning("Lütfen tüm alanları doldurun.")
                        elif reg_pass != reg_pass_conf:
                            st.error("Şifreler eşleşmiyor!")
                        elif len(reg_pass) < 6:
                            st.warning("Şifre en az 6 karakter olmalıdır.")
                        else:
                            try:
                                clean_reg_email = reg_email.strip().lower()
                                res = supabase.auth.sign_up({
                                    "email": clean_reg_email,
                                    "password": reg_pass,
                                    "options": {
                                        "data": {
                                            "full_name": reg_name,
                                            "birth_date": str(reg_bdate),
                                            "gender": reg_gender
                                        }
                                    }
                                })
                                st.session_state.profile_name = reg_name
                                st.session_state.birth_date = str(reg_bdate)
                                st.session_state.gender = reg_gender
                                st.success("📧 Kayıt başarılı! Lütfen e-posta kutunuzu (ve spam klasörünü) kontrol ederek hesabınızı doğrulayın. Ardından giriş yapabilirsiniz.")
                            except Exception as err:
                                st.error(f"Kayıt Hatası: {err}")

            if st.button("✖ Kapat"):
                st.session_state.show_auth_modal = False
                st.rerun()
        st.divider()

    st.markdown("<h1 style='text-align: center;'>Kötü Alışkanlıklarından Kurtul, Hayatını Yeniden İnşa Et 🚀</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 18px;'>Yapay zeka destekli kişisel koçun ile her gün geliş, hedeflerine ulaş ve motivasyonunu en üst seviyede tut.</p>", unsafe_allow_html=True)

# --- 5. GİRİŞ YAPILMIŞSA ---
else:
    user_email = st.session_state.user.email
    display_name = st.session_state.profile_name if st.session_state.profile_name else user_email.split('@')[0]
    
    # SOL ÜSTTEKİ YEŞİL "☰ Menü" KUTUSU
    col_menu_btn, _ = st.columns([1, 6])
    with col_menu_btn:
        if st.button("☰ Menü", key="btn_toggle_sidebar"):
            st.session_state.sidebar_open = not st.session_state.sidebar_open

    # Menü Açıksa Yan Paneli Göster
    if st.session_state.sidebar_open:
        with st.sidebar:
            if st.button("✖ Menüyü Kapat"):
                st.session_state.sidebar_open = False
                st.rerun()

            st.divider()

            if st.button("⚙️ Profilimi Düzenle"):
                st.session_state.sayfa = "👤 Profilim"
                st.session_state.sidebar_open = False
                st.rerun()

            st.divider()
            
            secilen_sayfa = st.radio(
                "📌 Sayfalar",
                ["🌱 AI Koç & Sohbet", "📊 İlerlemelerim", "📜 AI Geçmişim", "👤 Profilim"],
                index=["🌱 AI Koç & Sohbet", "📊 İlerlemelerim", "📜 AI Geçmişim", "👤 Profilim"].index(st.session_state.sayfa)
            )
            st.session_state.sayfa = secilen_sayfa
            
            st.divider()
            
            if st.button("🚪 Çıkış Yap"):
                if supabase:
                    supabase.auth.sign_out()
                st.session_state.user = None
                st.session_state.chats = {}
                st.session_state.current_chat_id = None
                st.session_state.sidebar_open = False
                st.rerun()

    # --- SAYFA: PROFİLİM ---
    if st.session_state.sayfa == "👤 Profilim":
        st.title("👤 Profil Bilgilerim")
        st.write("Profil bilgilerinizi ve profil fotoğrafınızı buradan düzenleyebilirsiniz.")
        st.divider()
        
        col_p1, col_p2 = st.columns([1, 2])
        
        with col_p1:
            st.subheader("Profil Fotoğrafı")
            if st.session_state.profile_pic:
                st.image(st.session_state.profile_pic, width=160)
            else:
                st.info("Henüz profil fotoğrafı yüklenmedi.")
            
            uploaded_file = st.file_uploader("Fotoğraf Yükle/Değiştir", type=["jpg", "jpeg", "png"])
            if uploaded_file is not None:
                bytes_data = uploaded_file.getvalue()
                base64_image = f"data:image/png;base64,{base64.b64encode(bytes_data).decode()}"
                st.session_state.profile_pic = base64_image
                st.success("Profil fotoğrafı güncellendi! 📸")
                st.rerun()

        with col_p2:
            st.subheader("Kişisel Bilgiler")
            
            yeni_ad = st.text_input("Ad Soyad", value=st.session_state.profile_name)
            st.text_input("E-Posta (Değiştirilemez)", value=user_email, disabled=True)
            yeni_dogum = st.text_input("Doğum Tarihi", value=str(st.session_state.birth_date))
            
            cinsiyet_index = 2
            if st.session_state.gender == "Kadın": cinsiyet_index = 0
            elif st.session_state.gender == "Erkek": cinsiyet_index = 1
            
            yeni_cinsiyet = st.selectbox("Cinsiyet", ["Kadın", "Erkek", "Belirtmek İstemiyorum"], index=cinsiyet_index)
            
            if st.button("💾 Bilgileri Kaydet", type="primary"):
                st.session_state.profile_name = yeni_ad
                st.session_state.birth_date = yeni_dogum
                st.session_state.gender = yeni_cinsiyet
                
                try:
                    supabase.auth.update_user({
                        "data": {
                            "full_name": yeni_ad,
                            "birth_date": yeni_dogum,
                            "gender": yeni_cinsiyet
                        }
                    })
                    st.success("Profil bilgileriniz kaydedildi! 🎉")
                    st.rerun()
                except Exception as e:
                    st.error(f"Güncelleme Hatası: {e}")

    # --- SAYFA: AI KOÇ & SOHBET ---
    elif st.session_state.sayfa == "🌱 AI Koç & Sohbet":
        
        col_title, col_new_btn = st.columns([4, 1.2])
        with col_title:
            st.title("🌱 Alışkanlık & Motivasyon Asistanı")
        with col_new_btn:
            if st.button("➕ Yeni Sohbet"):
                st.session_state.current_chat_id = None
                st.rerun()

        st.caption(f"Hoş geldin **{display_name}**! Bugün **{st.session_state.gun_sayisi}.** günündesin.")

        GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")

        if GROQ_API_KEY:
            client = Groq(api_key=GROQ_API_KEY)

            current_messages = []
            if st.session_state.current_chat_id and st.session_state.current_chat_id in st.session_state.chats:
                current_messages = st.session_state.chats[st.session_state.current_chat_id]["messages"]

            for message in current_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            if prompt := st.chat_input("Mesajınızı yazın..."):
                if not st.session_state.current_chat_id:
                    new_id = str(uuid.uuid4())
                    st.session_state.current_chat_id = new_id
                    title = prompt[:35] + ("..." if len(prompt) > 35 else "")
                    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
                    st.session_state.chats[new_id] = {
                        "title": title,
                        "date": now_str,
                        "messages": []
                    }

                st.chat_message("user").markdown(prompt)
                st.session_state.chats[st.session_state.current_chat_id]["messages"].append({"role": "user", "content": prompt})

                with st.chat_message("assistant"):
                    try:
                        system_prompt = f"Sen empatik, destekleyici ve motivasyon veren bir yaşam koçusun. Kullanıcının adı {display_name} ve mücadelesinde {st.session_state.gun_sayisi}. gününde."
                        
                        api_messages = [{"role": "system", "content": system_prompt}]
                        for msg in st.session_state.chats[st.session_state.current_chat_id]["messages"]:
                            api_messages.append({"role": msg["role"], "content": msg["content"]})

                        chat_completion = client.chat.completions.create(
                            messages=api_messages,
                            model="llama-3.3-70b-versatile",
                        )
                        
                        ai_reply = chat_completion.choices[0].message.content
                        st.markdown(ai_reply)
                        st.session_state.chats[st.session_state.current_chat_id]["messages"].append({"role": "assistant", "content": ai_reply})
                    except Exception as e:
                        st.error(f"Yapay zeka yanıt oluştururken bir sorun yaşandı: {e}")
        else:
            st.warning("Lütfen Streamlit Secrets kısmına GROQ_API_KEY ekleyin.")

    # --- SAYFA: İLERLEMELERİM ---
    elif st.session_state.sayfa == "📊 İlerlemelerim":
        st.title("📊 İlerleme ve Hedef Takibi")
        st.divider()

        yeni_gun = st.number_input(
            "Kaçıncı gündesin?", 
            min_value=1, 
            value=int(st.session_state.gun_sayisi),
            step=1
        )
        if yeni_gun != st.session_state.gun_sayisi:
            st.session_state.gun_sayisi = yeni_gun
            st.toast("Gün bilginiz güncellendi! 💾")

        st.success(f"Tebrikler **{display_name}**! Kararlılıkla **{st.session_state.gun_sayisi}.** güne ulaştın! 🎉")
        st.progress(min(st.session_state.gun_sayisi / 30, 1.0), text=f"30 Günlük Hedefin %{int((st.session_state.gun_sayisi/30)*100)} tamamlandı!")

    # --- SAYFA: AI GEÇMİŞİM ---
    elif st.session_state.sayfa == "📜 AI Geçmişim":
        st.title("📜 AI Sohbet Geçmişim")
        st.write("Eski sohbet başlıklarınız aşağıda listelenmiştir. Devam etmek istediğiniz sohbetin yanındaki butona tıklayın:")
        st.divider()

        if not st.session_state.chats:
            st.info("Henüz geçmiş bir sohbetiniz bulunmuyor.")
        else:
            for chat_id, chat_data in reversed(list(st.session_state.chats.items())):
                col_info, col_btn = st.columns([4, 1.2])
                
                with col_info:
                    st.markdown(f"### 💬 {chat_data['title']}")
                    st.caption(f"📅 {chat_data.get('date', 'Tarih Yok')} | 💬 {len(chat_data['messages'])} Mesaj")
                
                with col_btn:
                    if st.button("💬 Sohbete Git", key=f"btn_go_{chat_id}"):
                        st.session_state.current_chat_id = chat_id
                        st.session_state.sayfa = "🌱 AI Koç & Sohbet"
                        st.rerun()
                
                st.divider()