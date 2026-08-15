import streamlit as st
from supabase import create_client, Client
from groq import Groq
import uuid
from datetime import datetime, date


# ============================================================
# SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="Alışkanlık Asistanı",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CSS
# ============================================================

st.markdown("""
<style>
footer { visibility: hidden; }
header { visibility: hidden; }

[data-testid="stSidebarNav"] {
    display: none !important;
}

.stButton > button {
    width: 100%;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# SUPABASE
# ============================================================

def get_supabase_client() -> Client | None:
    try:
        url = st.secrets.get("SUPABASE_URL", "").strip().rstrip("/")
        key = st.secrets.get("SUPABASE_KEY", "").strip()

        if not url or not key:
            return None

        return create_client(url, key)
    except Exception:
        return None


supabase = get_supabase_client()


# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "user": None,
    "access_token": None,
    "refresh_token": None,
    "chats": {},
    "current_chat_id": None,
    "show_auth_modal": False,
    "gun_sayisi": 1,
    "sayfa": "🌱 AI Koç & Sohbet",
    "profile_name": "",
    "birth_date": "2000-01-01",
    "gender": "Belirtilmedi",
    "avatar_url": "",
    "profile_saved": False,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# GİRİŞ YAPILMAMIŞSA
# ============================================================

if not st.session_state.user:

    col_logo, col_space, col_login, col_register = st.columns(
        [3, 4, 1.5, 1.5]
    )

    with col_logo:
        st.markdown("### 🌱 **Karakter & Alışkanlık Koçu**")

    with col_login:
        if st.button("🔑 Giriş Yap", use_container_width=True):
            st.session_state.show_auth_modal = "login"
            st.rerun()

    with col_register:
        if st.button("📝 Üye Ol", type="primary", use_container_width=True):
            st.session_state.show_auth_modal = "register"
            st.rerun()

    st.divider()

    if st.session_state.show_auth_modal:

        _, auth_col, _ = st.columns([1, 2, 1])

        with auth_col:

            if not supabase:
                st.error("Veri tabanı bağlantısı kurulamadı.")

            else:

                tab_login, tab_register = st.tabs(
                    ["🔑 Giriş Yap", "📝 Kayıt Ol"]
                )

                # ------------------------------------------------
                # GİRİŞ
                # ------------------------------------------------

                with tab_login:

                    email = st.text_input(
                        "E-Posta Adresi",
                        key="l_email"
                    )

                    password = st.text_input(
                        "Şifre",
                        type="password",
                        key="l_pass"
                    )

                    if st.button(
                        "Giriş Yap",
                        type="primary",
                        key="btn_l",
                        use_container_width=True
                    ):

                        if not email or not password:
                            st.warning("Lütfen tüm alanları doldurun.")

                        else:

                            try:

                                res = supabase.auth.sign_in_with_password(
                                    {
                                        "email": email.strip().lower(),
                                        "password": password
                                    }
                                )

                                # Session bilgilerini clear'dan önce al
                                access_token = None
                                refresh_token = None

                                if res.session:
                                    access_token = res.session.access_token
                                    refresh_token = res.session.refresh_token

                                meta = res.user.user_metadata or {}

                                # Eski state'i temizle
                                st.session_state.clear()

                                # Kullanıcı ve session
                                st.session_state.user = res.user
                                st.session_state.access_token = access_token
                                st.session_state.refresh_token = refresh_token

                                # Profil
                                st.session_state.profile_name = meta.get(
                                    "full_name",
                                    email.split("@")[0]
                                )

                                st.session_state.birth_date = meta.get(
                                    "birth_date",
                                    "2000-01-01"
                                )

                                st.session_state.gender = meta.get(
                                    "gender",
                                    "Belirtilmedi"
                                )

                                st.session_state.avatar_url = meta.get(
                                    "avatar_url",
                                    ""
                                )

                                # Diğer state
                                st.session_state.chats = {}
                                st.session_state.current_chat_id = None
                                st.session_state.gun_sayisi = 1
                                st.session_state.sayfa = "🌱 AI Koç & Sohbet"
                                st.session_state.show_auth_modal = False
                                st.session_state.profile_saved = False

                                st.rerun()

                            except Exception as e:
                                st.error(f"Giriş başarısız: {e}")

                # ------------------------------------------------
                # KAYIT
                # ------------------------------------------------

                with tab_register:

                    reg_name = st.text_input(
                        "Ad Soyad",
                        key="r_name"
                    )

                    reg_email = st.text_input(
                        "E-Posta Adresi",
                        key="r_email"
                    )

                    reg_pass = st.text_input(
                        "Şifre",
                        type="password",
                        key="r_pass"
                    )

                    reg_pass_conf = st.text_input(
                        "Şifre Tekrar",
                        type="password",
                        key="r_conf"
                    )

                    col_bdate, col_gnd = st.columns(2)

                    with col_bdate:
                        reg_bdate = st.date_input(
                            "Doğum Tarihi",
                            value=date(2000, 1, 1),
                            key="r_bdate"
                        )

                    with col_gnd:
                        reg_gender = st.selectbox(
                            "Cinsiyet",
                            [
                                "Kadın",
                                "Erkek",
                                "Belirtmek İstemiyorum"
                            ],
                            key="r_gnd"
                        )

                    if st.button(
                        "Kayıt Ol",
                        key="btn_r",
                        type="primary",
                        use_container_width=True
                    ):

                        if reg_pass != reg_pass_conf:
                            st.error("Şifreler eşleşmiyor!")

                        elif not reg_name or not reg_email or not reg_pass:
                            st.warning("Lütfen tüm alanları doldurun.")

                        else:

                            try:

                                supabase.auth.sign_up(
                                    {
                                        "email": reg_email.strip().lower(),
                                        "password": reg_pass,
                                        "options": {
                                            "data": {
                                                "full_name": reg_name.strip(),
                                                "birth_date": str(reg_bdate),
                                                "gender": reg_gender,
                                                "avatar_url": ""
                                            }
                                        }
                                    }
                                )

                                st.success(
                                    "Kayıt başarılı! Giriş yapabilirsiniz."
                                )

                                st.session_state.show_auth_modal = "login"
                                st.rerun()

                            except Exception as e:
                                st.error(f"Kayıt hatası: {e}")

            if st.button("✖ Kapat", use_container_width=True):
                st.session_state.show_auth_modal = False
                st.rerun()

    # ----------------------------------------------------------
    # ANA EKRAN
    # ----------------------------------------------------------

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        """
        <h1 style='text-align:center; font-size:2.4rem;'>
        Ekrandan çıkışını değil,<br>
        gerçek hayata girişini keşfet 🚀
        </h1>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <p style='text-align:center; font-size:1.2rem; color:#555;'>
        Alışkanlıklarını dönüştür, karakterini güçlendir.
        </p>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# GİRİŞ YAPILMIŞSA
# ============================================================

else:

    user_email = st.session_state.user.email

    display_name = st.session_state.get(
        "profile_name",
        user_email.split("@")[0]
    )

    # ----------------------------------------------------------
    # ÜST MENÜ
    # ----------------------------------------------------------

    col_menu_btn, _ = st.columns([1.4, 6])

    with col_menu_btn:
        st.button("☰ Menü", key="btn_menu")

    # ----------------------------------------------------------
    # SIDEBAR
    # ----------------------------------------------------------

    with st.sidebar:

        st.title("📌 Menü")

        avatar_url = st.session_state.get("avatar_url", "")

        if avatar_url:
            try:
                st.image(avatar_url, width=100)
            except Exception:
                st.markdown("## 👤")
        else:
            st.markdown("## 👤")

        st.write(f"**{display_name}**")
        st.caption(user_email)

        st.divider()

        if st.button(
            "⚙️ Profilimi Düzenle",
            use_container_width=True
        ):
            st.session_state.sayfa = "👤 Profilim"
            st.rerun()

        st.divider()

        sayfalar = [
            "🌱 AI Koç & Sohbet",
            "📊 İlerlemelerim",
            "📜 AI Geçmişim",
            "👤 Profilim"
        ]

        secilen_sayfa = st.radio(
            "Sayfalar",
            sayfalar,
            index=sayfalar.index(st.session_state.sayfa),
            key="nav_radio"
        )

        if secilen_sayfa != st.session_state.sayfa:
            st.session_state.sayfa = secilen_sayfa
            st.rerun()

        st.divider()

        if st.button(
            "🚪 Çıkış Yap",
            type="primary",
            use_container_width=True
        ):

            if supabase:
                try:
                    supabase.auth.sign_out()
                except Exception:
                    pass

            st.session_state.clear()
            st.rerun()

    # ========================================================
    # AI KOÇ & SOHBET
    # ========================================================

    if st.session_state.sayfa == "🌱 AI Koç & Sohbet":

        col_title, col_new_btn = st.columns([4, 1.2])

        with col_title:
            st.title("🌱 Alışkanlık & Motivasyon Asistanı")

        with col_new_btn:

            if st.button(
                "➕ Yeni Sohbet",
                use_container_width=True
            ):
                st.session_state.current_chat_id = None
                st.rerun()

        st.caption(
            f"Hoş geldin **{display_name}**! "
            f"Bugün **{st.session_state.gun_sayisi}.** günündesin."
        )

        GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "").strip()

        if not GROQ_API_KEY:

            st.error("GROQ_API_KEY bulunamadı.")

        else:

            client = Groq(api_key=GROQ_API_KEY)

            current_messages = []

            if (
                st.session_state.current_chat_id
                and st.session_state.current_chat_id in st.session_state.chats
            ):
                current_messages = st.session_state.chats[
                    st.session_state.current_chat_id
                ]["messages"]

            for message in current_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            prompt = st.chat_input("Mesajınızı yazın...")

            if prompt:

                if not st.session_state.current_chat_id:

                    new_id = str(uuid.uuid4())

                    st.session_state.current_chat_id = new_id

                    title = (
                        prompt[:35]
                        + ("..." if len(prompt) > 35 else "")
                    )

                    now_str = datetime.now().strftime(
                        "%d.%m.%Y %H:%M"
                    )

                    st.session_state.chats[new_id] = {
                        "title": title,
                        "date": now_str,
                        "messages": []
                    }

                st.session_state.chats[
                    st.session_state.current_chat_id
                ]["messages"].append(
                    {
                        "role": "user",
                        "content": prompt
                    }
                )

                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):

                    try:

                        system_prompt = (
                            "Sen bir motivasyon ve alışkanlık koçusun. "
                            f"Kullanıcı adı: {display_name}."
                        )

                        api_messages = [
                            {
                                "role": "system",
                                "content": system_prompt
                            }
                        ]

                        for msg in st.session_state.chats[
                            st.session_state.current_chat_id
                        ]["messages"]:

                            api_messages.append(
                                {
                                    "role": msg["role"],
                                    "content": msg["content"]
                                }
                            )

                        chat_completion = (
                            client
                            .chat
                            .completions
                            .create(
                                messages=api_messages,
                                model="llama-3.3-70b-versatile"
                            )
                        )

                        ai_reply = (
                            chat_completion
                            .choices[0]
                            .message
                            .content
                        )

                        st.markdown(ai_reply)

                        st.session_state.chats[
                            st.session_state.current_chat_id
                        ]["messages"].append(
                            {
                                "role": "assistant",
                                "content": ai_reply
                            }
                        )

                    except Exception as e:
                        st.error(f"Sistem Hatası: {e}")

    # ========================================================
    # İLERLEMELER
    # ========================================================

    elif st.session_state.sayfa == "📊 İlerlemelerim":

        st.title("📊 İlerlemelerim")

        st.info("Bu sayfa henüz geliştirilmedi.")

    # ========================================================
    # AI GEÇMİŞİ
    # ========================================================

    elif st.session_state.sayfa == "📜 AI Geçmişim":

        st.title("📜 AI Geçmişim")

        if not st.session_state.chats:

            st.info("Henüz sohbet yok.")

        else:

            for chat_id, chat in st.session_state.chats.items():

                with st.expander(
                    f"{chat['title']} — {chat['date']}"
                ):

                    for msg in chat["messages"]:

                        if msg["role"] == "user":
                            st.markdown(
                                f"**👤 Sen:** {msg['content']}"
                            )
                        else:
                            st.markdown(
                                f"**🤖 AI:** {msg['content']}"
                            )

    # ========================================================
    # PROFİL
    # ========================================================

    elif st.session_state.sayfa == "👤 Profilim":

        st.title("👤 Profilim")

        # Başarılı kayıt mesajı
        if st.session_state.get("profile_saved", False):

            st.success(
                "✅ Profil bilgileriniz başarıyla kaydedildi!"
            )

            st.session_state.profile_saved = False

        st.markdown("---")

        # ------------------------------------------------------
        # MEVCUT FOTOĞRAF
        # ------------------------------------------------------

        current_avatar = st.session_state.get("avatar_url", "")

        if current_avatar:

            try:
                st.image(
                    current_avatar,
                    width=150
                )
            except Exception:
                st.markdown("### 👤 Profil Fotoğrafı")

        else:
            st.markdown("### 👤 Profil Fotoğrafı")

        # ------------------------------------------------------
        # FORM
        # ------------------------------------------------------

        with st.form("profile_form"):

            st.subheader("Profil Bilgilerini Düzenle")

            new_avatar = st.file_uploader(
                "📷 Profil Fotoğrafı",
                type=["jpg", "jpeg", "png", "webp"],
                help="JPG, JPEG, PNG veya WEBP seçebilirsin."
            )

            new_name = st.text_input(
                "Ad Soyad",
                value=st.session_state.profile_name
            )

            try:
                current_bdate = datetime.strptime(
                    st.session_state.birth_date,
                    "%Y-%m-%d"
                ).date()
            except Exception:
                current_bdate = date(2000, 1, 1)

            new_bdate = st.date_input(
                "Doğum Tarihi",
                value=current_bdate
            )

            gender_options = [
                "Kadın",
                "Erkek",
                "Belirtmek İstemiyorum"
            ]

            if st.session_state.gender in gender_options:
                current_gender_idx = gender_options.index(
                    st.session_state.gender
                )
            else:
                current_gender_idx = 2

            new_gender = st.selectbox(
                "Cinsiyet",
                gender_options,
                index=current_gender_idx
            )

            st.markdown("")

            col_save, col_cancel = st.columns(2)

            with col_save:
                submitted = st.form_submit_button(
                    "💾 Kaydet",
                    type="primary",
                    use_container_width=True
                )

            with col_cancel:
                cancel = st.form_submit_button(
                    "İptal",
                    use_container_width=True
                )

        # ------------------------------------------------------
        # İPTAL
        # ------------------------------------------------------

        if cancel:

            st.session_state.sayfa = "🌱 AI Koç & Sohbet"
            st.rerun()

        # ------------------------------------------------------
        # KAYDET
        # ------------------------------------------------------

        if submitted:

            if not new_name.strip():

                st.error("Ad Soyad boş olamaz.")

            elif not supabase:

                st.error("Supabase bağlantısı kurulamadı.")

            else:

                try:

                    access_token = st.session_state.get(
                        "access_token"
                    )

                    refresh_token = st.session_state.get(
                        "refresh_token"
                    )

                    if not access_token or not refresh_token:

                        st.error(
                            "Oturum bilgisi bulunamadı. "
                            "Lütfen çıkış yapıp tekrar giriş yap."
                        )

                        st.stop()

                    # Session'ı Supabase'e geri yükle
                    session_result = supabase.auth.set_session(
                        access_token,
                        refresh_token
                    )

                    # Refresh edilmiş token varsa state'i güncelle
                    if session_result and getattr(
                        session_result,
                        "session",
                        None
                    ):

                        st.session_state.access_token = (
                            session_result.session.access_token
                        )

                        st.session_state.refresh_token = (
                            session_result.session.refresh_token
                        )

                    # Mevcut avatar
                    avatar_url = st.session_state.get(
                        "avatar_url",
                        ""
                    )

                    # ------------------------------------------------
                    # FOTOĞRAF YÜKLE
                    # ------------------------------------------------

                    if new_avatar is not None:

                        user_id = st.session_state.user.id

                        extension = (
                            new_avatar.name
                            .rsplit(".", 1)[-1]
                            .lower()
                        )

                        file_path = (
                            f"{user_id}/profile.{extension}"
                        )

                        file_bytes = new_avatar.getvalue()

                        # Önce aynı kullanıcının eski olası
                        # dosyalarını silmeye çalış
                        old_extensions = [
                            "jpg",
                            "jpeg",
                            "png",
                            "webp"
                        ]

                        old_files = [
                            f"{user_id}/profile.{ext}"
                            for ext in old_extensions
                            if ext != extension
                        ]

                        try:
                            supabase.storage.from_(
                                "avatars"
                            ).remove(old_files)
                        except Exception:
                            pass

                        # Yeni fotoğrafı yükle
                        supabase.storage.from_(
                            "avatars"
                        ).upload(
                            file_path,
                            file_bytes,
                            {
                                "content-type": new_avatar.type,
                                "upsert": True
                            }
                        )

                        # Public URL al
                        avatar_url = (
                            supabase.storage
                            .from_("avatars")
                            .get_public_url(file_path)
                        )

                    # ------------------------------------------------
                    # AUTH METADATA GÜNCELLE
                    # ------------------------------------------------

                    update_result = (
                        supabase
                        .auth
                        .update_user(
                            {
                                "data": {
                                    "full_name": new_name.strip(),
                                    "birth_date": str(new_bdate),
                                    "gender": new_gender,
                                    "avatar_url": avatar_url
                                }
                            }
                        )
                    )

                    # Yeni session döndüyse tokenları güncelle
                    if (
                        update_result
                        and getattr(
                            update_result,
                            "session",
                            None
                        )
                    ):

                        st.session_state.access_token = (
                            update_result.session.access_token
                        )

                        st.session_state.refresh_token = (
                            update_result.session.refresh_token
                        )

                    # Kullanıcı state'ini de güncelle
                    if (
                        update_result
                        and getattr(
                            update_result,
                            "user",
                            None
                        )
                    ):

                        st.session_state.user = (
                            update_result.user
                        )

                    # Local profil bilgileri
                    st.session_state.profile_name = (
                        new_name.strip()
                    )

                    st.session_state.birth_date = (
                        str(new_bdate)
                    )

                    st.session_state.gender = (
                        new_gender
                    )

                    st.session_state.avatar_url = (
                        avatar_url
                    )

                    # Yeşil başarı kutusu için flag
                    st.session_state.profile_saved = True

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Profil kaydedilirken hata oluştu: {e}"
                    )

        st.markdown("---")

        st.write(
            f"**E-posta:** {user_email}"
        )

        st.caption(
            "E-posta adresi değiştirilemez."
        )