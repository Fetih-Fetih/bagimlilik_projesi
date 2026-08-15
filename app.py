import streamlit as st
import streamlit.components.v1 as components
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

# CSS: Sol üstteki ok (>>) tamamen gizlenir
st.markdown("""
    <style>
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Streamlit varsayılan sidebar oku (>>) gizleme */
    [data-testid="stSidebarNav"] {display: none !important;}
    [data-testid="collapsedControl"] {display: none !important;}
    button[data-testid="stSidebarCollapsedControl"] {display: none !important;}
    
    .stButton>button { width: 100%; }
    
    /* Sol üstteki Özel Yeşil Menü Kutusu */
    div[data-testid="stColumn"] button[key="btn_toggle_sidebar"] {
        background-color: #2e7d32 !important;
        color: #ffffff !important;
        font-weight: bold !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 8px 16px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;
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

# --- 3. OTURUM KONTROLÜ VE YENİLEME DİRENÇLİLİK ---
if "user" not in st.session_state:
    st.session_state.user = None

# Sayfa yenilendiğinde Supabase yerel oturumunu kontrol et
if supabase and st.session_state.user is None:
    try:
        session = supabase.auth.get_session()
        if session and hasattr(session, 'user') and session.user:
            st.session_state.user = session.user
            meta = session.user.user_metadata or {}
            st.session_state.profile_name = meta.get("full_name", session.user.email.split('@')[0])
            st.session_state.birth_date = meta.get("birth_date", "2000-01-01")
            st.session_state.gender = meta.get("gender", "Belirtilmedi")
    except Exception:
        pass

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
                st.error("Veri tabanı bağlantısı kurulamadı.")
            else:
                tab_login, tab_register = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol"])
                
                with tab_login:
                    email = st.text_input("E-Posta Adresi", key="l_email")
                    password = st.text_input("Şifre", type="password", key="l_pass")
                    
                    if st.button("Giriş Yap", type="primary", key="btn_l"):
                        if not email or not password:
                            st.warning("Lütfen tüm alanları doldurun.")
                        else:
                            try:
                                res = supabase.auth.sign_in_with_password({
                                    "email": email.strip().lower(),
                                    "password": password
                                })
                                st.session_state.clear()
                                st.session_state.user = res.user
                                meta = res.user.user_metadata or {}
                                st.session_state.profile_name = meta.get("full_name", email.split('@')[0])
                                st.session_state.birth_date = meta.get("birth_date", "2000-01-01")
                                st.session_state.gender = meta.get("gender", "Belirtilmedi")
                                st.session_state.chats = {}
                                st.session_state.gun_sayisi = 1
                                st.session_state.sayfa = "🌱 AI Koç & Sohbet"
                                st.session_state.show_auth_modal = False
                                st.rerun()
                            except Exception:
                                st.error("Giriş Başarısız: Bilgilerinizi kontrol edin.")

                with tab_register:
                    reg_name = st.text_input("Ad Soyad", key="r_name")
                    reg_email = st.text_input("E-Posta Adresi", key="r_email")
                    reg_pass = st.text_input("Şifre", type="password", key="r_pass")
                    reg_pass_conf = st.text_input("Şifre Tekrar", type="password", key="r_conf")
                    
                    col_bdate, col_gnd = st.columns(2)
                    with col_bdate:
                        reg_bdate = st.date_input("Doğum Tarihi", key="r_bdate")
                    with col_gnd:
                        reg_gender = st.selectbox("Cinsiyet", ["Kadın", "Erkek", "Belirtmek İstemiyorum"], key="r_gnd")
                    
                    if st.button("Kayıt Ol", key="btn_r"):
                        if reg_pass != reg_pass_conf:
                            st.error("Şifreler eşleşmiyor!")
                        else:
                            try:
                                supabase.auth.sign_up({
                                    "email": reg_email.strip().lower(),
                                    "password": reg_pass,
                                    "options": {
                                        "data": {
                                            "full_name": reg_name,
                                            "birth_date": str(reg_bdate),
                                            "gender": reg_gender
                                        }
                                    }
                                })
                                st.success("Kayıt başarılı! Giriş yapabilirsiniz.")
                            except Exception as err:
                                st.error(f"Hata: {err}")

            if st.button("✖ Kapat"):
                st.session_state.show_auth_modal = False
                st.rerun()
        st.divider()

    st.markdown("<h1 style='text-align: center;'>Ekrandan çıkışını değil, gerçek hayata girişini keşfet 🚀</h1>", unsafe_allow_html=True)

# --- 5. GİRİŞ YAPILMIŞSA ---
else:
    user_email = st.session_state.user.email
    display_name = st.session_state.get("profile_name", user_email.split('@')[0])
    
    col_menu_btn, _ = st.columns([1.5, 6])
    with col_menu_btn:
        # Menü Butonuna Basıldığında JavaScript ile Sidebar Aç/Kapat
        if st.button("☰ Menü", key="btn_toggle_sidebar"):
            components.html("""
                <script>
                    var sidebar = window.parent.document.querySelector('section[data-testid="stSidebar"]');
                    if (sidebar) {
                        var currentWidth = sidebar.clientWidth;
                        if (currentWidth > 0) {
                            sidebar.style.width = "0px";
                            sidebar.style.minWidth = "0px";
                            sidebar.setAttribute('aria-expanded', 'false');
                        } else {
                            sidebar.style.width = "336px";
                            sidebar.style.minWidth = "336px";
                            sidebar.setAttribute('aria-expanded', 'true');
                        }
                    }
                </script>
            """, height=0)

    # YAN PANEL (SIDEBAR)
    with st.sidebar:
        st.title("📌 Menü")
        st.write(f"Kullanıcı: **{display_name}**")
        st.divider()

        if st.button("⚙️ Profilimi Düzenle"):
            st.session_state.sayfa = "👤 Profilim"
            st.rerun()

        st.divider()
        
        secilen_sayfa = st.radio(
            "Sayfalar",
            ["🌱 AI Koç & Sohbet", "📊 İlerlemelerim", "📜 AI Geçmişim", "👤 Profilim"],
            index=["🌱 AI Koç & Sohbet", "📊 İlerlemelerim", "📜 AI Geçmişim", "👤 Profilim"].index(st.session_state.sayfa)
        )
        st.session_state.sayfa = secilen_sayfa
        
        st.divider()
        
        if st.button("🚪 Çıkış Yap"):
            if supabase:
                supabase.auth.sign_out()
            st.session_state.clear()
            st.rerun()

    # --- SOHBET SAYFASI VE DİĞER İÇERİKLER ---
    if st.session_state.sayfa == "🌱 AI Koç & Sohbet":
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
                    st.session_state.chats[new_id] = {"title": title, "date": now_str, "messages": []}

                st.chat_message("user").markdown(prompt)
                st.session_state.chats[st.session_state.current_chat_id]["messages"].append({"role": "user", "content": prompt})

                with st.chat_message("assistant"):
                    try:
                        system_prompt = f"Sen bir motivasyon koçusun. Kullanıcı adı {display_name}."
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
                        st.error(f"Sistem Hatası: {e}")