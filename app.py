import streamlit as st
from supabase import create_client, Client
from groq import Groq

# --- 1. SAYFA VE TASARIM AYARLARI ---
st.set_page_config(page_title="Alışkanlık Asistanı", page_icon="🌱", layout="wide")

# Streamlit Menülerini Gizleme ve Temiz Tasarım (CSS)
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stButton>button { width: 100%; }
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

# --- 3. OTURUM DURUMLARI (SESSION STATE) ---
if "user" not in st.session_state:
    st.session_state.user = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "show_auth_modal" not in st.session_state:
    st.session_state.show_auth_modal = False

# --- 4. GİRİŞ YAPILMAMIŞSA (LANDING PAGE & AUTH) ---
if not st.session_state.user:
    
    # Üst Bar (Header)
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

    # Giriş / Kayıt Ol Formu (Modal/Açılır Pencere)
    if st.session_state.show_auth_modal:
        _, auth_col, _ = st.columns([1, 2, 1])
        with auth_col:
            if not supabase:
                st.error("Veri tabanı bağlantısı henüz kurulamadı. Lütfen Streamlit Secrets alanını kontrol edin.")
            else:
                st.info("Devam etmek için hesabınıza giriş yapın veya kayıt olun.")
                tab_login, tab_register = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol"])
                
                # --- GİRİŞ YAP SEKMESİ ---
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
                                st.session_state.show_auth_modal = False
                                st.success("Giriş başarılı!")
                                st.rerun()
                            except Exception as err:
                                st.error("Giriş Başarısız: E-posta veya şifre hatalı.")

                # --- KAYIT OL SEKMESİ ---
                with tab_register:
                    reg_email = st.text_input("E-Posta Adresi", key="r_email")
                    reg_pass = st.text_input("Şifre (En az 6 karakter)", type="password", key="r_pass")
                    reg_pass_conf = st.text_input("Şifre Tekrar", type="password", key="r_conf")
                    
                    if st.button("Kayıt Ol", key="btn_r"):
                        if not reg_email or not reg_pass:
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
                                    "password": reg_pass
                                })
                                st.success("Kayıt başarılı! Şimdi 'Giriş Yap' sekmesinden giriş yapabilirsiniz.")
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
        st.write("Verilerin Supabase altyapısı ile tamamen şifreli saklanır.")

# --- 5. GİRİŞ YAPILMIŞSA (SOHBET VE PANEL) ---
else:
    user_email = st.session_state.user.email
    
    # Sol Yan Menü (Sidebar)
    st.sidebar.write(f"👤 **{user_email}**")
    
    if st.sidebar.button("🚪 Çıkış Yap"):
        if supabase:
            supabase.auth.sign_out()
        st.session_state.user = None
        st.session_state.messages = []
        st.rerun()

    # DÜZELTİLEN SATIR: st.sidebar.hr() yerine st.sidebar.divider() kullanıldı.
    st.sidebar.divider()

    st.sidebar.header("İlerleme Durumun")
    gun_sayisi = st.sidebar.number_input("Kaçıncı gündesin?", min_value=1, value=1)
    st.sidebar.success(f"Tebrikler! {gun_sayisi}. günündesin! 🎉")

    # Yapay Zeka Chat Ekranı
    st.title("🌱 Alışkanlık & Motivasyon Asistanı")
    st.write("Hoş geldin! Bugün nasıl hissediyorsun? Sana nasıl destek olabilirim?")

    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")

    if GROQ_API_KEY:
        client = Groq(api_key=GROQ_API_KEY)

        # Eski sohbet mesajlarını ekrana yazdır
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Kullanıcıdan mesaj al
        if prompt := st.chat_input("Mesajınızı yazın..."):
            st.chat_message("user").markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})

            # AI Yanıtı Üret
            with st.chat_message("assistant"):
                try:
                    system_prompt = f"Sen empatik, destekleyici ve motivasyon veren bir yaşam koçusun. Kullanıcının e-postası {user_email} ve kötü alışkanlıkla mücadelesinde {gun_sayisi}. gününde."
                    
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
                except Exception as e:
                    st.error(f"Yapay zeka yanıt oluştururken bir sorun yaşandı: {e}")
    else:
        st.warning("Lütfen Streamlit Secrets kısmına GROQ_API_KEY ekleyin.")