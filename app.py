import streamlit as st
from groq import Groq

# Sayfa Tasarımı
st.set_page_config(page_title="Destek Asistanı", page_icon="🌱")

# Streamlit varsayılan menü ve alt bilgileri gizleme
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- BASİT GİRİŞ SİSTEMİ (Session State ile) ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔑 Giriş Yap")
    username = st.text_input("Kullanıcı Adı")
    password = st.text_input("Şifre", type="password")
    
    if st.button("Giriş Yap"):
        # Şimdilik sabit bir kullanıcı adı ve şifre belirleyelim:
        if username == "admin" and password == "1234":
            st.session_state.logged_in = True
            st.success("Giriş başarılı!")
            st.rerun()
        else:
            st.error("Kullanıcı adı veya şifre hatalı!")
else:
    # --- GİRİŞ BAŞARILI İSE AÇILACAK ANA EKRAN ---
    
    # Çıkış Butonu
    if st.sidebar.button("Çıkış Yap"):
        st.session_state.logged_in = False
        st.rerun()

    st.title("🌱 Alışkanlık & Motivasyon Asistanı")
    st.write("Hoş geldin! Bugün kendini nasıl hissediyorsun? Sana nasıl destek olabilirim?")

    # Yan Menü (Sidebar) - İlerleme Takibi
    st.sidebar.header("İlerleme Durumun")
    gun_sayisi = st.sidebar.number_input("Kaçıncı gündesin?", min_value=1, value=1)
    st.sidebar.success(f"Tebrikler! {gun_sayisi}. günündesin! 🎉")

    # Groq API Anahtarın
    GROQ_API_KEY = "gsk_..."  # Kendi Groq API anahtarını buraya yaz

    if GROQ_API_KEY and GROQ_API_KEY.startswith("gsk_"):
        client = Groq(api_key=GROQ_API_KEY)

        # Sohbet Geçmişini Saklama
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Eski Mesajları Ekrana Yazdırma
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Kullanıcıdan Mesaj Alma
        if prompt := st.chat_input("Mesajınızı yazın..."):
            st.chat_message("user").markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})

            # AI Yanıtı Alma
            with st.chat_message("assistant"):
                system_prompt = "Sen empatik, destekleyici ve motivasyon veren bir yaşam koçusun. Kullanıcının kötü alışkanlıklarla mücadelesinde ona destek oluyorsun."
                
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