import streamlit as st
from supabase import create_client, Client
from groq import Groq

# --- 1. SAYFA VE TASARIM AYARLARI ---
st.set_page_config(page_title="Alışkanlık Asistanı", page_icon="🌱", layout="wide")

# CSS ile Menüleri Gizleme ve Temiz Tasarım
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stButton>button { width: 100%; }
    </style>
""", unsafe_allow_html=True)

# --- 2. SUPABASE BULUT BAĞLANTISI ---
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_supabase()
except Exception as e:
    st.error("Veri tabanı bağlantısı kurulamadı. Lütfen Streamlit Secrets ayarlarınızı kontrol edin.")
    st.stop()

# --- 3. OTURUM DURUMLARI (SESSION STATE) ---
if "user" not in st.session_state:
    st.session_state.user = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "show_auth_modal" not in st.session_state:
    st.session_state.show_auth_modal = False

# --- 4. GİRİŞ YAPILMAMIŞSA (LANDING PAGE & AUTH) ---
if not st.session_state.user:
    
    # Üst Menü / Header
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

    # Giriş / Kayıt Ol Form Penceresi (Modal)
    if st.session_state.show_auth_modal:
        _, auth_col, _ = st.columns([1, 2, 1])
        with auth_col:
            st.info("Devam etmek için hesabınıza giriş yapın veya kayıt olun.")
            tab_login, tab_register = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol"])
            
            # --- GİRİŞ YAP SEKMESİ ---
            with tab_login:
                email = st.text_input("E-Posta Adresi", key="l_email")
                password = st.text_input("Şifre", type="password", key="l_pass")
                
                if st.button("Giriş Yap", type="primary", key="btn_l"):
                    try:
                        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                        st.session_state.user = res.user
                        st.session_state.show_auth_modal = False
                        st.success("Giriş başarılı!")
                        st.rerun()
                    except Exception as err:
                        st.error(f"Giriş Başarısız: E-posta veya şifre hatalı.")
                
                st.write("--- veya ---")
                
                if st.button("🌐 Google Hesabı ile Devam Et"):
                    try:
                        res = supabase.auth.sign_in_with_oauth({
                            "provider": "google"
                        })
                        st.markdown(f"[Google ile Giriş Yapmak İçin Tıklayın]({res.url})")
                    except Exception as err:
                        st.error(f"Google ile giriş başlatılamadı: {err}")

            # --- KAYIT OL SEKMESİ ---
            with tab_register:
                reg_email = st.text_input("E-Posta Adresi", key="r_email")
                reg_pass = st.text_input("Şifre (En az 6 karakter)", type="password", key="r_pass")
                reg_pass_conf = st.text_input("Şifre Tekrar", type="password", key="r_conf")
                
                if st.button("Kayıt Ol", key="btn_r"):
                    if reg_pass != reg_pass_conf:
                        st.error("Şifreler eşleşmiyor!")
                    elif len(reg_pass) < 6:
                        st.warning("Şifre en az 6 karakter olmalıdır.")
                    else:
                        try:
                            res = supabase.auth.sign_up({"email": reg_email, "password": reg_pass})
                            st.success("Kayıt başarılı! E-posta adresinize gelen doğrulama bağlantısını onaylayarak giriş yapabilirsiniz.")
                        except Exception as err:
                            st.error(f"Kayıt Hatası: {err}")

            if st.button("✖ Kapat"):
                st.session_state.show_auth_modal = False
                st.rerun()
        st.divider()

    # Tanıtım Sayfası İçeriği (Landing Page)
    st.markdown("<h1 style='text-align: center;'>Kötü Alışkanlıklarından Kurtul, Hayatını Yeniden İnşa Et 🚀</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 18px;'>Yapay zeka destekli kişisel koçun ile her gün geliş, hedeflerine ulaş ve motivasyonunu en üst seviyede tut.</p>", unsafe_allow_html=True)
    
    st.write(" ")
    st.write(" ")
    f1, f2, f3 = st.columns(3)
    with f1:
        st.markdown("### 🤖 **7/24 Yapay Zeka Koçu**")
        st.write("Zorlandığın anlarda seni dinleyen ve sana özel çözümler sunan empatik asistan.")
    with f2:
        st.markdown("### 📈 **Gelişim Takibi**")
        st.write("Kaçıncı günde olduğunu takip et. Başarılarını kaydet ve kararlılığını artır.")
    with f3:
        st.markdown("### 🔒 **Bulut Tabanlı Güvenlik**")
        st.write("Verilerin Supabase altyapısı ile tamamen şifreli ve sana özel saklanır.")

# --- 5. GİRİŞ YAPILMIŞSA (SOHBET VE PANEL) ---
else:
    user_email = st.session_state.user.email
    
    # Sol Menü (Sidebar)
    st.sidebar.write(f"👤 **{user_email}**")
    
    if st.sidebar.button("🚪 Çıkış Yap"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.session_state.messages = []
        st.rerun()

    st.sidebar.hr()
    st.sidebar.header("İlerleme Durumun")
    
    gun_sayisi = st.sidebar.number_input("Kaçıncı gündesin?", min_value=1, value=1)
    st.sidebar.success(f"Tebrikler! {gun_sayisi}. günündesin! 🎉")

    # Yapay Zeka Chat Alanı
    st.title("🌱 Alışkanlık & Motivasyon Asistanı")
    st.write("Hoş geldin! Bugün nasıl hissediyorsun?")

    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")

    if GROQ_API_KEY:
        client = Groq(api_key=GROQ_API_KEY)

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Mesajınızı yazın..."):
            st.chat_message("user").markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.chat_message("assistant"):
                system_prompt = f"Sen empatik, destekleyici ve motivasyon veren bir yaşam koçusun. Kullanıcının e-postası {user_email} ve alışkanlık mücadelesinde {gun_sayisi}. gününde."
                
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.3-70b-versatile",
                )
                
                ai_reply = chat_completion.choices[0].message.content
                st.markdown(ai_reply)
                st.session_state.messages.append({"role": "assistant", "content": ai_reply})
    else:
        st.warning("Lütfen Streamlit Secrets kısmına GROQ_API_KEY ekleyin.")