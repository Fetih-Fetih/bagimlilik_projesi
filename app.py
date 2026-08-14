import streamlit as st
from groq import Groq

# Sayfa Tasarımı ve Başlık
st.set_page_config(page_title="Destek Asistanı", page_icon="🌱")
st.title("🌱 Alışkanlık & Motivasyon Asistanı")
st.write("Hoş geldin! Bugün kendini nasıl hissediyorsun? Sana nasıl destek olabilirim?")

# Yan Menü (Sidebar) - İlerleme Takibi
st.sidebar.header("İlerleme Durumun")
gun_sayisi = st.sidebar.number_input("Kaçıncı gündesin?", min_value=1, value=1)
st.sidebar.success(f"Tebrikler! {gun_sayisi}. günündesin! 🎉")

# Groq API Anahtarın
GROQ_API_KEY = "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"

# Şartı düzelttik: API anahtarı girildiyse çalışır
if GROQ_API_KEY and GROQ_API_KEY != "BURAYA_GROQ_API_KEYINIZI_YAZIN":
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
    st.warning("Lütfen koddaki 'GROQ_API_KEY' kısmına geçerli bir anahtar yazın.")