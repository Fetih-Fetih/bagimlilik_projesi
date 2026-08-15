import streamlit as st
from supabase import create_client, Client
from groq import Groq
import uuid
from datetime import datetime, date


# ============================================================
# 1. SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="Alışkanlık Asistanı",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# 2. CSS
# ============================================================

st.markdown("""
<style>

footer {
    visibility: hidden;
}

header {
    visibility: hidden;
}

[data-testid="stSidebarNav"] {
    display: none !important;
}

[data-testid="collapsedControl"] {
    display: none !important;
}

button[data-testid="stSidebarCollapsedControl"] {
    display: none !important;
}

.stButton > button {
    width: 100%;
    border-radius: 8px;
}

div[data-testid="stColumn"] button[key="btn_menu"] {
    background-color: #2e7d32 !important;
    color: white !important;
    font-weight: bold !important;
    border: none !important;
    border-radius: 8px !important;
}

.profile-photo {
    border-radius: 50%;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# 3. SUPABASE
# ============================================================

def get_supabase_client() -> Client | None:

    try:

        url = st.secrets.get(
            "SUPABASE_URL",
            ""
        ).strip().rstrip("/")

        key = st.secrets.get(
            "SUPABASE_KEY",
            ""
        ).strip()

        if not url or not key:
            return None

        return create_client(
            url,
            key
        )

    except Exception:

        return None


supabase = get_supabase_client()


# ============================================================
# 4. SESSION STATE
# ============================================================

if "user" not in st.session_state:
    st.session_state.user = None

if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None

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

if "profile_name" not in st.session_state:
    st.session_state.profile_name = ""

if "birth_date" not in st.session_state:
    st.session_state.birth_date = "2000-01-01"

if "gender" not in st.session_state:
    st.session_state.gender = "Belirtilmedi"

if "avatar_url" not in st.session_state:
    st.session_state.avatar_url = ""

if "profile_saved" not in st.session_state:
    st.session_state.profile_saved = False


# ============================================================
# 5. GİRİŞ YAPILMAMIŞSA
# ============================================================

if not st.session_state.user:

    col_logo, col_space, col_login, col_register = st.columns(
        [3, 4, 1.5, 1.5]
    )

    with col_logo:

        st.markdown(
            "### 🌱 **Karakter & Alışkanlık Koçu**"
        )

    with col_login:

        if st.button(
            "🔑 Giriş Yap",
            use_container_width=True
        ):

            st.session_state.show_auth_modal = "login"
            st.rerun()

    with col_register:

        if st.button(
            "📝 Üye Ol",
            type="primary",
            use_container_width=True
        ):

            st.session_state.show_auth_modal = "register"
            st.rerun()


    st.divider()


    # ========================================================
    # GİRİŞ / KAYIT
    # ========================================================

    if st.session_state.show_auth_modal:

        _, auth_col, _ = st.columns(
            [1, 2, 1]
        )

        with auth_col:

            if not supabase:

                st.error(
                    "Veri tabanı bağlantısı kurulamadı."
                )

            else:

                tab_login, tab_register = st.tabs(
                    [
                        "🔑 Giriş Yap",
                        "📝 Kayıt Ol"
                    ]
                )


                # =================================================
                # GİRİŞ
                # =================================================

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

                            st.warning(
                                "Lütfen tüm alanları doldurun."
                            )

                        else:

                            try:

                                res = (
                                    supabase.auth
                                    .sign_in_with_password(
                                        {
                                            "email": email.strip().lower(),
                                            "password": password
                                        }
                                    )
                                )


                                # ---------------------------------
                                # ÖNCE TOKENLARI AL
                                # ---------------------------------

                                access_token = None
                                refresh_token = None

                                if res.session:

                                    access_token = (
                                        res.session.access_token
                                    )

                                    refresh_token = (
                                        res.session.refresh_token
                                    )


                                # ---------------------------------
                                # STATE TEMİZLE
                                # ---------------------------------

                                st.session_state.clear()


                                # ---------------------------------
                                # TOKENLARI GERİ YAZ
                                # ---------------------------------

                                st.session_state.user = res.user

                                st.session_state.access_token = (
                                    access_token
                                )

                                st.session_state.refresh_token = (
                                    refresh_token
                                )


                                # ---------------------------------
                                # PROFİL BİLGİLERİ
                                # ---------------------------------

                                meta = (
                                    res.user.user_metadata
                                    or {}
                                )


                                st.session_state.profile_name = (
                                    meta.get(
                                        "full_name",
                                        email.split("@")[0]
                                    )
                                )


                                st.session_state.birth_date = (
                                    meta.get(
                                        "birth_date",
                                        "2000-01-01"
                                    )
                                )


                                st.session_state.gender = (
                                    meta.get(
                                        "gender",
                                        "Belirtilmedi"
                                    )
                                )


                                st.session_state.avatar_url = (
                                    meta.get(
                                        "avatar_url",
                                        ""
                                    )
                                )


                                # ---------------------------------
                                # DİĞER STATE'LER
                                # ---------------------------------

                                st.session_state.chats = {}

                                st.session_state.current_chat_id = None

                                st.session_state.gun_sayisi = 1

                                st.session_state.sayfa = (
                                    "🌱 AI Koç & Sohbet"
                                )

                                st.session_state.show_auth_modal = False

                                st.session_state.profile_saved = False


                                st.rerun()


                            except Exception:

                                st.error(
                                    "Giriş Başarısız: "
                                    "Bilgilerinizi kontrol edin."
                                )


                # =================================================
                # KAYIT
                # =================================================

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
                            value=date(
                                2000,
                                1,
                                1
                            ),
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

                            st.error(
                                "Şifreler eşleşmiyor!"
                            )

                        elif (
                            not reg_name
                            or not reg_email
                            or not reg_pass
                        ):

                            st.warning(
                                "Lütfen tüm alanları doldurun."
                            )

                        else:

                            try:

                                supabase.auth.sign_up(
                                    {
                                        "email": (
                                            reg_email
                                            .strip()
                                            .lower()
                                        ),
                                        "password": reg_pass,
                                        "options": {
                                            "data": {
                                                "full_name": (
                                                    reg_name.strip()
                                                ),
                                                "birth_date": (
                                                    str(reg_bdate)
                                                ),
                                                "gender": (
                                                    reg_gender
                                                )
                                            }
                                        }
                                    }
                                )


                                st.success(
                                    "Kayıt başarılı! "
                                    "Giriş yapabilirsiniz."
                                )


                                st.session_state.show_auth_modal = (
                                    "login"
                                )

                                st.rerun()


                            except Exception as err:

                                st.error(
                                    f"Hata: {err}"
                                )


            if st.button(
                "✖ Kapat",
                use_container_width=True
            ):

                st.session_state.show_auth_modal = False

                st.rerun()


    # ========================================================
    # ANA EKRAN
    # ========================================================

    st.markdown(
        "<br>",
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <h1 style='text-align: center; font-size: 2.4rem;'>
        Ekrandan çıkışını değil,<br>
        gerçek hayata girişini keşfet 🚀
        </h1>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <p style='text-align: center; font-size: 1.2rem; color: #555;'>
        Alışkanlıklarını dönüştür, karakterini güçlendir.
        </p>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# 6. GİRİŞ YAPILMIŞSA
# ============================================================

else:

    user_email = st.session_state.user.email

    display_name = st.session_state.get(
        "profile_name",
        user_email.split("@")[0]
    )


    # ========================================================
    # ÜST MENÜ
    # ========================================================

    col_menu_btn, _ = st.columns(
        [1.4, 6]
    )

    with col_menu_btn:

        st.button(
            "☰ Menü",
            key="btn_menu"
        )


    # ========================================================
    # SIDEBAR
    # ========================================================

    with st.sidebar:

        st.title(
            "📌 Menü"
        )

        # Profil fotoğrafı
        if st.session_state.avatar_url:

            try:

                st.image(
                    st.session_state.avatar_url,
                    width=100
                )

            except Exception:

                st.write("👤")

        else:

            st.markdown(
                "## 👤"
            )


        st.write(
            f"**{display_name}**"
        )

        st.caption(
            user_email
        )

        st.divider()


        if st.button(
            "⚙️ Profilimi Düzenle",
            use_container_width=True
        ):

            st.session_state.sayfa = (
                "👤 Profilim"
            )

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
            index=sayfalar.index(
                st.session_state.sayfa
            ),
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
    # 7. AI KOÇ & SOHBET
    # ========================================================

    if st.session_state.sayfa == "🌱 AI Koç & Sohbet":

        col_title, col_new_btn = st.columns(
            [4, 1.2]
        )


        with col_title:

            st.title(
                "🌱 Alışkanlık & Motivasyon Asistanı"
            )


        with col_new_btn:

            if st.button(
                "➕ Yeni Sohbet"
            ):

                st.session_state.current_chat_id = None

                st.rerun()


        st.caption(
            f"Hoş geldin **{display_name}**! "
            f"Bugün **{st.session_state.gun_sayisi}.** "
            "günündesin."
        )


        GROQ_API_KEY = st.secrets.get(
            "GROQ_API_KEY",
            ""
        )


        if not GROQ_API_KEY:

            st.error(
                "GROQ_API_KEY bulunamadı."
            )

        else:

            client = Groq(
                api_key=GROQ_API_KEY
            )


            current_messages = []


            if (
                st.session_state.current_chat_id
                and
                st.session_state.current_chat_id
                in st.session_state.chats
            ):

                current_messages = (
                    st.session_state
                    .chats[
                        st.session_state.current_chat_id
                    ]["messages"]
                )


            for message in current_messages:

                with st.chat_message(
                    message["role"]
                ):

                    st.markdown(
                        message["content"]
                    )


            prompt = st.chat_input(
                "Mesajınızı yazın..."
            )


            if prompt:

                if not st.session_state.current_chat_id:

                    new_id = str(
                        uuid.uuid4()
                    )

                    st.session_state.current_chat_id = new_id


                    title = (
                        prompt[:35]
                        +
                        (
                            "..."
                            if len(prompt) > 35
                            else ""
                        )
                    )


                    now_str = (
                        datetime.now()
                        .strftime(
                            "%d.%m.%Y %H:%M"
                        )
                    )


                    st.session_state.chats[new_id] = {
                        "title": title,
                        "date": now_str,
                        "messages": []
                    }


                st.chat_message(
                    "user"
                ).markdown(
                    prompt
                )


                st.session_state.chats[
                    st.session_state.current_chat_id
                ]["messages"].append(
                    {
                        "role": "user",
                        "content": prompt
                    }
                )


                with st.chat_message(
                    "assistant"
                ):

                    try:

                        system_prompt = (
                            "Sen bir motivasyon ve "
                            "alışkanlık koçusun. "
                            f"Kullanıcı adı: {display_name}."
                        )


                        api_messages = [
                            {
                                "role": "system",
                                "content": system_prompt
                            }
                        ]


                        for msg in (
                            st.session_state
                            .chats[
                                st.session_state
                                .current_chat_id
                            ]["messages"]
                        ):

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


                        st.markdown(
                            ai_reply
                        )


                        st.session_state.chats[
                            st.session_state.current_chat_id
                        ]["messages"].append(
                            {
                                "role": "assistant",
                                "content": ai_reply
                            }
                        )


                    except Exception as e:

                        st.error(
                            f"Sistem Hatası: {e}"
                        )


    # ========================================================
    # 8. İLERLEMELER
    # ========================================================

    elif st.session_state.sayfa == "📊 İlerlemelerim":

        st.title(
            "📊 İlerlemelerim"
        )

        st.info(
            "Bu sayfa henüz geliştirilmedi."
        )


    # ========================================================
    # 9. AI GEÇMİŞİ
    # ========================================================

    elif st.session_state.sayfa == "📜 AI Geçmişim":

        st.title(
            "📜 AI Geçmişim"
        )


        if not st.session_state.chats:

            st.info(
                "Henüz sohbet yok."
            )

        else:

            for chat_id, chat in (
                st.session_state.chats.items()
            ):

                with st.expander(
                    f"{chat['title']} — {chat['date']}"
                ):

                    for msg in chat["messages"]:

                        if msg["role"] == "user":

                            st.markdown(
                                f"**👤 Sen:** "
                                f"{msg['content']}"
                            )

                        else:

                            st.markdown(
                                f"**🤖 AI:** "
                                f"{msg['content']}"
                            )


    # ========================================================
    # 10. PROFİL
    # ========================================================

    elif st.session_state.sayfa == "👤 Profilim":

        st.title(
            "👤 Profilim"
        )


        # ----------------------------------------------------
        # KAYDEDİLDİ MESAJI
        # ----------------------------------------------------

        if st.session_state.profile_saved:

            st.success(
                "✅ Profil bilgileriniz başarıyla kaydedildi!"
            )

            st.session_state.profile_saved = False


        st.markdown("---")


        # ----------------------------------------------------
        # MEVCUT PROFİL FOTOĞRAFI
        # ----------------------------------------------------

        if st.session_state.avatar_url:

            st.image(
                st.session_state.avatar_url,
                width=150
            )

        else:

            st.markdown(
                "### 👤 Profil Fotoğrafı"
            )


        # ----------------------------------------------------
        # FORM
        # ----------------------------------------------------

        with st.form(
            "profile_form"
        ):

            st.subheader(
                "Profil Bilgilerini Düzenle"
            )


            # -----------------------------------------------
            # PROFİL FOTOĞRAFI
            # -----------------------------------------------

            new_avatar = st.file_uploader(
                "📷 Profil Fotoğrafı",
                type=[
                    "jpg",
                    "jpeg",
                    "png",
                    "webp"
                ],
                help=(
                    "JPG, JPEG, PNG veya WEBP "
                    "formatında bir fotoğraf seç."
                )
            )


            # -----------------------------------------------
            # AD SOYAD
            # -----------------------------------------------

            new_name = st.text_input(
                "Ad Soyad",
                value=st.session_state.profile_name
            )


            # -----------------------------------------------
            # DOĞUM TARİHİ
            # -----------------------------------------------

            try:

                current_bdate = datetime.strptime(
                    st.session_state.birth_date,
                    "%Y-%m-%d"
                ).date()

            except Exception:

                current_bdate = date(
                    2000,
                    1,
                    1
                )


            new_bdate = st.date_input(
                "Doğum Tarihi",
                value=current_bdate
            )


            # -----------------------------------------------
            # CİNSİYET
            # -----------------------------------------------

            gender_options = [
                "Kadın",
                "Erkek",
                "Belirtmek İstemiyorum"
            ]


            if (
                st.session_state.gender
                in gender_options
            ):

                current_gender_idx = (
                    gender_options.index(
                        st.session_state.gender
                    )
                )

            else:

                current_gender_idx = 2


            new_gender = st.selectbox(
                "Cinsiyet",
                gender_options,
                index=current_gender_idx
            )


            st.markdown("")


            # -----------------------------------------------
            # BUTONLAR
            # -----------------------------------------------

            col_save, col_cancel = st.columns(
                2
            )


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


        # ====================================================
        # İPTAL
        # ====================================================

        if cancel:

            st.session_state.sayfa = (
                "🌱 AI Koç & Sohbet"
            )

            st.rerun()


        # ====================================================
        # KAYDET
        # ====================================================

        if submitted:

            if not new_name.strip():

                st.error(
                    "Ad Soyad boş olamaz."
                )

            elif not supabase:

                st.error(
                    "Supabase bağlantısı kurulamadı."
                )

            else:

                try:

                    # -----------------------------------------
                    # TOKENLARI AL
                    # -----------------------------------------

                    access_token = (
                        st.session_state.get(
                            "access_token"
                        )
                    )

                    refresh_token = (
                        st.session_state.get(
                            "refresh_token"
                        )
                    )


                    if (
                        not access_token
                        or not refresh_token
                    ):

                        st.error(
                            "Oturum bilgisi bulunamadı. "
                            "Lütfen çıkış yapıp tekrar giriş yap."
                        )

                        st.stop()


                    # -----------------------------------------
                    # SUPABASE SESSION'I GERİ YÜKLE
                    # -----------------------------------------

                    supabase.auth.set_session(
                        access_token,
                        refresh_token
                    )


                    # -----------------------------------------
                    # AVATAR URL
                    # -----------------------------------------

                    avatar_url = (
                        st.session_state.get(
                            "avatar_url",
                            ""
                        )
                    )


                    # -----------------------------------------
                    # YENİ FOTOĞRAF YÜKLENDİYSE
                    # -----------------------------------------

                    if new_avatar is not None:

                        user_id = (
                            st.session_state
                            .user
                            .id
                        )


                        # Dosya uzantısını al
                        file_extension = (
                            new_avatar.name
                            .split(".")[-1]
                            .lower()
                        )


                        # Kullanıcıya özel dosya yolu
                        file_path = (
                            f"{user_id}/profile."
                            f"{file_extension}"
                        )


                        file_bytes = (
                            new_avatar.getvalue()
                        )


                        # -------------------------------------
                        # STORAGE'A YÜKLE
                        # -------------------------------------

                        supabase.storage \
                            .from_("avatars") \
                            .upload(
                                file_path,
                                file_bytes,
                                {
                                    "content-type": (
                                        new_avatar.type
                                    },
                                    "upsert": "true"
                                }
                            )


                        # -------------------------------------
                        # PUBLIC URL
                        # -------------------------------------

                        avatar_url = (
                            supabase.storage
                            .from_("avatars")
                            .get_public_url(
                                file_path
                            )
                        )


                    # -----------------------------------------
                    # USER METADATA GÜNCELLE
                    # -----------------------------------------

                    update_result = (
                        supabase
                        .auth
                        .update_user(
                            {
                                "data": {
                                    "full_name": (
                                        new_name.strip()
                                    ),
                                    "birth_date": (
                                        str(new_bdate)
                                    ),
                                    "gender": (
                                        new_gender
                                    ),
                                    "avatar_url": (
                                        avatar_url
                                    )
                                }
                            }
                        )
                    )


                    # -----------------------------------------
                    # YENİ TOKENLAR GELDİYSE SAKLA
                    # -----------------------------------------

                    if (
                        hasattr(
                            update_result,
                            "session"
                        )
                        and update_result.session
                    ):

                        st.session_state.access_token = (
                            update_result
                            .session
                            .access_token
                        )

                        st.session_state.refresh_token = (
                            update_result
                            .session
                            .refresh_token
                        )


                    # -----------------------------------------
                    # LOCAL STATE GÜNCELLE
                    # -----------------------------------------

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


                    # -----------------------------------------
                    # BAŞARILI
                    # -----------------------------------------

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