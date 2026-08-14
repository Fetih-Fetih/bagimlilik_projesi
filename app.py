import streamlit as st
import sqlite3
import hashlib
from groq import Groq

# --- 1. SAYFA VE BİÇİMLENDİRME AYARLARI ---
st.set_page_config(page_title="Alışkanlık Asistanı", page_icon="🌱", layout="wide")

# Streamlit üst/alt menülerini gizleme ve Sağ Üst Buton Tasarımı için CSS
hide_and_custom_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            
            /* Özel Buton Tasarımları */
            .google-btn {
                background-color: #4285F4;
                color: white;
                padding: 10px;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
                cursor: pointer;
            }
            </style>
            """
st.markdown(hide_and_custom_style, unsafe_allow_html=True)

# --- 2. VERİ TABANI İŞLEMLERİ ---
def init_db():
    conn = sqlite3.connect("kullanicilar.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            gun INTEGER DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def add_user(username, password):
    conn = sqlite3.connect("kullanicilar.db")
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users(username, password, gun) VALUES (?,?,?)', (username, make_hashes(password), 1))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def login_user(username, password):
    conn = sqlite3.connect("kullanicilar.db")
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    data = c.fetchall()
    conn.close()
    if data and check_hashes(password, data[0][1]):
        return data[0]
    return None

def update_user_gun(username, gun):
    conn = sqlite3.connect("kullanicilar.db")
    c = conn.cursor()
    c.execute('UPDATE users SET gun = ? WHERE username = ?', (gun, username))
    conn.commit()
    conn.close()

init_db()

# --- 3. OTURUM DURUMU (SESSION STATE) ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "messages" not in st.session_state:
    st.session_state.messages = []
if "show_auth_modal" not in st.session_state:
    st.session_state.show_auth_modal = False

# --- 4. GİRİŞ YAPILMAMIŞSA: TANITIM SAYFASI (LANDING PAGE) ---
if not st.session_state.logged_in:
    
    # Üst Bar (Header): Sol tarafta Logo/İsim, Sağ tarafta Butonlar
    col_logo, col_space, col_login, col_register = st.columns([3, 4, 1.5, 1.5])
    
    with col_logo:
        st.markdown("### 🌱 **Karakter & Alışkanlık Koçu**")
        
    with col_login:
        if st.button("🔑 Giriş Yap", use_container_width=True):
            st.session_state.show_auth_modal = "login"
            
    with col_register:
        if st.button("📝 Üye Ol", type="primary", use_container_width=True):
            st.session_state.show_auth_modal = "register"

    st.divider()

    # --- POPUP / FORM EKRANI (Giriş Yap veya Üye Ol'a basıldığında açılır) ---
    if st.session_state.show_auth_modal:
        auth_col1, auth_col2, auth_col3 = st.columns([1, 2, 1])
        with auth_col2:
            st.info("Devam etmek için hesabınıza giriş yapın veya kayıt olun.")
            tab_login, tab_register = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol"])
            
            with tab_login:
                login_user_input = st.text_input("Kullanıcı Adı", key="l_user")
                login_pass_input = st.text_input("Şifre", type="password", key="l_pass")
                if st.button("Giriş Yap", type="primary", key="btn_l"):
                    user_data = login_user(login_user_input, login_pass_input)
                    if user_data:
                        st.session_state.logged_in = True
                        st.session_state.username = login_user_input
                        st.session_state.gun = user_data[2]
                        st.session_state.show_auth_modal = False
                        st.rerun()
                    else:
                        st.error("Kullanıcı adı veya şifre hatalı.")
                
                st.write("--- veya ---")
                if st.button("🌐 Google ile Giriş Yap (Yakında)", use_container_width=True):
                    st.toast("Google OAuth entegrasyonu yakında eklenecek!")

            with tab_register:
                new_user = st.text_input("Kullanıcı Adı Seçin", key="r_user")
                new_pass = st.text_input("Şifre Seçin", type="password", key="r_pass")
                new_pass_confirm = st.text_input("Şifreyi Tekrar Girin", type="password", key="r_pass_conf")
                if st.button("Kayıt Ol", key="btn_r"):
                    if not new_user or not new_pass:
                        st.warning("Lütfen alanları doldurun.")
                    elif new_pass != new_pass_confirm:
                        st.error("Şifreler eşleşmiyor!")
                    else:
                        if add_user(new_user, new_pass):
                            st.success("Hesap oluşturuldu! Şimdi Giriş Yapabilirsiniz.")
                        else:
                            st.error("Bu kullanıcı adı zaten alınmış.")

            if st.button("✖ Kapat"):
                st.session_state.show_auth_modal = False
                st.rerun()
        st.divider()

    # --- ANA SAYFA TANITIM İÇERİĞİ ---
    st.markdown("<h1 style='text-align: center;'>Kötü Alışkanlıklarından Kurtul, Hayatını Yeniden İnşa Et 🚀</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 18px;'>Yapay zeka destekli kişisel koçun ile her gün geliş, hedeflerine ulaş ve motivasyonunu en üst seviyede tut.</p>", unsafe_allow_html=True)
    
    st.write(" ")
    st.write(" ")

    # 3 Kolonlu Özellik Tanıtımı
    f1, f2, f3 = st.columns(3)
    
    with f1:
        st.markdown("### 🤖 **7/24 Yapay Zeka Koçu**")
        st.write("Zorlandığın anlarda, kriz anlarında veya motivasyona ihtiyaç duyduğunda seni dinleyen ve sana özel çözümler sunan empatik asistan.")

    with f2:
        st.markdown("### 📈 **Gelişim Takibi**")
        st.write("Kaçıncı günde olduğunu takip et. Başarılarını kaydet ve kararlılığını adım adım artır.")

    with f3:
        st.markdown("### 🔒 **Tamamen Gizli ve Güvenli**")
        st.write("Verilerin ve sohbetlerin tamamen sana özel saklanır. Kimseyle paylaşılmaz.")

# --- 5. GİRİŞ YAPILMIŞSA: UYGULAMA EKRANI ---
else:
    # Sol Menü (Sidebar)
    st.sidebar.write(f"👤 **{st.session_state.username}**")
    
    if st.sidebar.button("🚪 Çıkış Yap"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.messages = []
        st.rerun()

    st.sidebar.hr()
    st.sidebar.header("İlerleme Durumun")
    
    yeni_gun = st.sidebar.number_input("Kaçıncı gündesin?", min_value=1, value=int(st.session_state.get("gun", 1)))
    if yeni_gun != st.session_state.get("gun"):
        st.session_state.gun = yeni_gun
        update_user_gun(st.session_state.username, yeni_gun)
        st.sidebar.toast("Gün bilginiz güncellendi! 💾")

    st.sidebar.success(f"Tebrikler! {yeni_gun}. günündesin! 🎉")

    # Yapay Zeka Chat Alanı
    st.title("🌱 Alışkanlık & Motivasyon Asistanı")
    st.write(f"Hoş geldin **{st.session_state.username}**! Bugün nasıl hissediyorsun?")

    GROQ_API_KEY = "gsk_..."  # Buraya kendi Groq API anahtarınızı yapıştırın

    if GROQ_API_KEY and GROQ_API_KEY.startswith("gsk_"):
        client = Groq(api_key=GROQ_API_KEY)

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Mesajınızı yazın..."):
            st.chat_message("user").markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.chat_message("assistant"):
                system_prompt = f"Sen empatik, destekleyici ve motivasyon veren bir yaşam koçusun. Kullanıcının adı {st.session_state.username} ve alışkanlık mücadelesinde {st.session_state.gun}. gününde."
                
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
        st.warning("Lütfen koddaki GROQ_API_KEY kısmına geçerli bir anahtar yazın.")