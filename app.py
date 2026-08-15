import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client, Client
from groq import Groq
import uuid
import re
from datetime import datetime, date, timedelta


# ============================================================
# 1. SAYFA AYARLARI
# ============================================================

st.set_page_config(
    page_title="Alışkanlık Asistanı",
    page_icon="🌱",
    layout="wide"
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

/* Kendi menümüzü kullandığımız için
   Streamlit'in varsayılan sidebar'ını gizliyoruz. */
section[data-testid="stSidebar"] {
    display: none !important;
}

.menu-button button {
    background-color: #2e7d32 !important;
    color: white !important;
    font-weight: bold !important;
    border: none !important;
    border-radius: 8px !important;
}

.stButton > button {
    border-radius: 8px;
}

.avatar-circle {
    border-radius: 50%;
    object-fit: cover;
    display: block;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# 3. SUPABASE CLIENT
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
# 3B. TARAYICI ÇEREZİ (kalıcı oturum için, saf JS ile)
# ============================================================
# extra_streamlit_components gibi çift yönlü custom component'ler bu
# senaryoda güvenilmez senkronize oluyor. Bunun yerine:
#   - Çerez YAZMA: components.html ile doğrudan JS enjekte ediyoruz.
#   - Çerez OKUMA: sayfa yüklendiğinde JS çerezi kontrol edip varsa
#     URL'e query parametresi olarak ekleyip sayfayı yeniden yüklüyor;
#     Python tarafı bu parametreyi st.query_params ile okuyor.

AUTH_COOKIE_NAME = "habit_coach_refresh_token"
AUTH_QUERY_PARAM = "auth_token"


def set_browser_cookie(name: str, value: str, days: int = 30) -> None:
    """Tarayıcıya doğrudan JS ile kalıcı çerez yazar."""

    js = f"""
    <script>
    document.cookie = "{name}={value}; max-age={days * 24 * 60 * 60}; path=/; SameSite=Lax";
    </script>
    """

    components.html(js, height=0, width=0)


def delete_browser_cookie(name: str) -> None:
    """Tarayıcıdaki çerezi siler."""

    js = f"""
    <script>
    document.cookie = "{name}=; max-age=0; path=/; SameSite=Lax";
    </script>
    """

    components.html(js, height=0, width=0)


def inject_cookie_check_redirect(name: str, query_param: str) -> None:
    """Sayfa ilk açıldığında çerezde token varsa ve URL'de henüz yoksa,
    token'ı URL'e ekleyip sayfayı yeniden yükler (Python bunu okuyabilsin diye)."""

    js = f"""
    <script>
    (function() {{
        var match = document.cookie.match(new RegExp('(^| )' + '{name}' + '=([^;]+)'));
        var params = new URLSearchParams(window.location.search);
        if (match && !params.has('{query_param}')) {{
            params.set('{query_param}', match[2]);
            window.location.search = params.toString();
        }}
    }})();
    </script>
    """

    components.html(js, height=0, width=0)


# ============================================================
# 4. YARDIMCI FONKSİYONLAR
# ============================================================

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email or ""))


def calculate_day_count(created_at_str: str) -> int:
    """Kayıt tarihinden bugüne kaç gün geçtiğini hesaplar."""

    try:

        clean = (created_at_str or "").replace("Z", "+00:00")
        created_date = datetime.fromisoformat(clean).date()

        diff = (date.today() - created_date).days + 1

        return max(diff, 1)

    except Exception:

        return 1


def load_chats_from_db(user_id: str) -> dict:
    """Kullanıcının tüm sohbetlerini ve mesajlarını Supabase'ten yükler."""

    chats = {}

    if not supabase:
        return chats

    try:

        chat_rows = (
            supabase.table("chats")
            .select("*")
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
            .execute()
        )

        for chat in chat_rows.data:

            msg_rows = (
                supabase.table("messages")
                .select("*")
                .eq("chat_id", chat["id"])
                .order("created_at")
                .execute()
            )

            chats[chat["id"]] = {
                "title": chat["title"],
                "date": chat.get("created_at", ""),
                "messages": [
                    {"role": m["role"], "content": m["content"]}
                    for m in msg_rows.data
                ]
            }

    except Exception as e:

        st.warning(f"Sohbet geçmişi yüklenirken hata oluştu: {e}")

    return chats


def create_chat_in_db(user_id: str, title: str) -> str:
    """Yeni bir sohbet kaydı oluşturur ve id'sini döner."""

    if not supabase:
        return str(uuid.uuid4())

    try:

        result = (
            supabase.table("chats")
            .insert({"user_id": user_id, "title": title})
            .execute()
        )

        return result.data[0]["id"]

    except Exception as e:

        st.warning(f"Sohbet veritabanına kaydedilemedi: {e}")

        return str(uuid.uuid4())


def save_message_to_db(chat_id: str, role: str, content: str) -> None:
    """Bir mesajı veritabanına kaydeder ve sohbetin güncelleme zamanını yeniler."""

    if not supabase:
        return

    try:

        supabase.table("messages").insert(
            {"chat_id": chat_id, "role": role, "content": content}
        ).execute()

        supabase.table("chats").update(
            {"updated_at": datetime.utcnow().isoformat()}
        ).eq("id", chat_id).execute()

    except Exception as e:

        st.warning(f"Mesaj veritabanına kaydedilemedi: {e}")


def upload_avatar(user_id: str, uploaded_file) -> str | None:
    """Profil fotoğrafını Supabase Storage'a yükler ve genel URL'sini döner."""

    if not supabase:
        st.error("Veri tabanı bağlantısı kurulamadı.")
        return None

    access_token = st.session_state.get("access_token")
    refresh_token = st.session_state.get("refresh_token")

    if not access_token or not refresh_token:

        st.error(
            "Oturum süresi dolmuş. Lütfen çıkış yapıp tekrar giriş yap."
        )

        return None

    try:

        # Storage isteğinin RLS politikalarını geçebilmesi için
        # önce oturumu (kullanıcı kimliğini) client'a yüklüyoruz.
        supabase.auth.set_session(access_token, refresh_token)

        ext = uploaded_file.name.split(".")[-1].lower()
        path = f"{user_id}/avatar.{ext}"
        file_bytes = uploaded_file.getvalue()

        supabase.storage.from_("avatars").upload(
            path,
            file_bytes,
            {
                "content-type": uploaded_file.type,
                "upsert": "true"
            }
        )

        public_url = supabase.storage.from_("avatars").get_public_url(path)

        # Aynı dosya adı yeniden kullanıldığında tarayıcı önbelleğini kırmak için
        cache_bust_url = f"{public_url}?t={int(datetime.utcnow().timestamp())}"

        return cache_bust_url

    except Exception as e:

        st.error(f"Fotoğraf yüklenemedi: {e}")

        return None


def apply_auth_session(user, session) -> None:
    """Giriş sonrası ya da çerezden otomatik oturum açarken kullanılan ortak kod:
    kullanıcı, token ve profil bilgilerini session_state'e yazar."""

    st.session_state.user = user

    if session:

        st.session_state.access_token = session.access_token
        st.session_state.refresh_token = session.refresh_token

    meta = user.user_metadata or {}

    st.session_state.profile_name = meta.get(
        "full_name", user.email.split("@")[0]
    )

    st.session_state.birth_date = meta.get("birth_date", "2000-01-01")
    st.session_state.gender = meta.get("gender", "Belirtilmedi")
    st.session_state.avatar_url = meta.get("avatar_url", "")

    created_at = getattr(user, "created_at", None)

    st.session_state.gun_sayisi = calculate_day_count(
        str(created_at) if created_at else ""
    )

    st.session_state.chats = load_chats_from_db(user.id)
    st.session_state.current_chat_id = None
    st.session_state.sayfa = "🌱 AI Koç & Sohbet"
    st.session_state.show_auth_modal = False


# ============================================================
# 5. SESSION STATE
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


# ============================================================
# 5B. TARAYICI ÇEREZİNDEN OTOMATİK OTURUM AÇMA
# ============================================================
# Sayfa yenilendiğinde veya tarayıcı kapatılıp açıldığında,
# daha önce kaydedilmiş refresh token varsa oturumu otomatik geri yükler.

if st.session_state.user is None and not st.session_state.get("auth_restore_done", False):

    token_from_url = st.query_params.get(AUTH_QUERY_PARAM)

    if token_from_url:

        # Aynı token ile tekrar tekrar denemeyelim (örn. token geçersizse
        # sonsuz döngüye girmesin diye) bir defalık işaretliyoruz.
        st.session_state.auth_restore_done = True

        if supabase:

            try:

                res = supabase.auth.refresh_session(token_from_url)

                if res and res.user and res.session:

                    apply_auth_session(res.user, res.session)
                    st.session_state.auto_restored_notice = True

                    # Yeni (rotate edilmiş) refresh token'ı normal render
                    # sırasında (rerun'dan hemen önce değil) çereze yazacağız.
                    st.session_state.pending_remember_token = res.session.refresh_token

            except Exception:

                delete_browser_cookie(AUTH_COOKIE_NAME)

        # Token'ı adres çubuğundan temizle (orada kalmasın).
        st.query_params.clear()
        st.rerun()

    else:

        # Çerezde token var mı diye bir kere kontrol et; varsa URL'e
        # ekleyip sayfayı otomatik yeniden yükleyecek.
        if not st.session_state.get("cookie_check_injected", False):

            st.session_state.cookie_check_injected = True

            inject_cookie_check_redirect(AUTH_COOKIE_NAME, AUTH_QUERY_PARAM)


# ============================================================
# 6. GİRİŞ YAPILMAMIŞSA
# ============================================================

if not st.session_state.user:

    col_logo, col_space, col_login, col_register = st.columns([3, 4, 1.5, 1.5])

    with col_logo:

        st.markdown("### 🌱 **Karakter & Alışkanlık Koçu**")

    with col_login:

        if st.button("🔑 Giriş Yap", use_container_width=True):

            st.session_state.show_auth_modal = True
            st.rerun()

    with col_register:

        if st.button("📝 Üye Ol", type="primary", use_container_width=True):

            st.session_state.show_auth_modal = True
            st.rerun()

    st.divider()

    # ========================================================
    # GİRİŞ / KAYIT
    # ========================================================

    if st.session_state.show_auth_modal:

        _, auth_col, _ = st.columns([1, 2, 1])

        with auth_col:

            if not supabase:

                st.error("Veri tabanı bağlantısı kurulamadı.")

            else:

                tab_login, tab_register = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol"])

                # =================================================
                # GİRİŞ
                # =================================================

                with tab_login:

                    email = st.text_input("E-Posta Adresi", key="l_email")
                    password = st.text_input("Şifre", type="password", key="l_pass")

                    remember_device = st.checkbox(
                        "🔒 Bu cihazı hatırla",
                        value=False,
                        key="l_remember",
                        help=(
                            "Sadece kendi kişisel cihazında işaretle. "
                            "İşaretlersen 30 gün boyunca tekrar giriş "
                            "istenmez — ortak/paylaşılan bir cihazda "
                            "bunu işaretleme."
                        )
                    )

                    if st.button("Giriş Yap", type="primary", key="btn_l", use_container_width=True):

                        if not email or not password:

                            st.warning("Lütfen tüm alanları doldurun.")

                        elif not is_valid_email(email):

                            st.warning("Lütfen geçerli bir e-posta adresi girin.")

                        else:

                            try:

                                res = supabase.auth.sign_in_with_password(
                                    {
                                        "email": email.strip().lower(),
                                        "password": password
                                    }
                                )

                                # ---------------------------------
                                # KULLANICI, TOKEN VE PROFİL BİLGİLERİ
                                # ---------------------------------

                                apply_auth_session(res.user, res.session)

                                # ---------------------------------
                                # KALICI OTURUM İÇİN TOKEN'I BEKLET
                                # (sadece "Bu cihazı hatırla" işaretliyse)
                                # Gerçek çerez yazma işlemi, ana sayfa
                                # normal şekilde render edilirken yapılır —
                                # aksi halde st.rerun() tarayıcının çerezi
                                # kaydetmesine fırsat vermeden sayfayı kesiyor.
                                # ---------------------------------

                                if res.session and remember_device:

                                    st.session_state.pending_remember_token = (
                                        res.session.refresh_token
                                    )

                                st.rerun()

                            except Exception as e:

                                st.error(f"Giriş başarısız: {e}")

                # =================================================
                # KAYIT
                # =================================================

                with tab_register:

                    reg_name = st.text_input("Ad Soyad", key="r_name")
                    reg_email = st.text_input("E-Posta Adresi", key="r_email")
                    reg_pass = st.text_input("Şifre", type="password", key="r_pass")
                    reg_pass_conf = st.text_input("Şifre Tekrar", type="password", key="r_conf")

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
                            ["Kadın", "Erkek", "Belirtmek İstemiyorum"],
                            key="r_gnd"
                        )

                    if st.button("Kayıt Ol", key="btn_r", type="primary", use_container_width=True):

                        if not reg_name or not reg_email or not reg_pass:

                            st.warning("Lütfen tüm alanları doldurun.")

                        elif not is_valid_email(reg_email):

                            st.warning("Lütfen geçerli bir e-posta adresi girin.")

                        elif len(reg_pass) < 6:

                            st.warning("Şifre en az 6 karakter olmalıdır.")

                        elif reg_pass != reg_pass_conf:

                            st.error("Şifreler eşleşmiyor!")

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
                                                "gender": reg_gender
                                            }
                                        }
                                    }
                                )

                                st.success("Kayıt başarılı! Giriş yapabilirsiniz.")

                            except Exception as e:

                                st.error(f"Kayıt hatası: {e}")

            if st.button("✖ Kapat", use_container_width=True):

                st.session_state.show_auth_modal = False
                st.rerun()

    # ========================================================
    # ANA EKRAN
    # ========================================================

    st.markdown("<br>", unsafe_allow_html=True)

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
# 7. GİRİŞ YAPILMIŞSA
# ============================================================

else:

    user_email = st.session_state.user.email
    display_name = st.session_state.get("profile_name", user_email.split("@")[0])

    # ========================================================
    # BEKLEYEN "BU CİHAZI HATIRLA" ÇEREZİNİ ŞİMDİ YAZ
    # ========================================================
    # Bu, sayfa zorla yeniden başlatılmadan (st.rerun() olmadan) çalışan
    # normal bir render turu olduğu için tarayıcı çerezi gerçekten kaydedebiliyor.

    if st.session_state.get("pending_remember_token"):

        token_to_save = st.session_state.pending_remember_token
        st.session_state.pending_remember_token = None

        set_browser_cookie(AUTH_COOKIE_NAME, token_to_save, days=30)

    # ========================================================
    # OTOMATİK GİRİŞ UYARISI
    # ========================================================
    # Çerezden otomatik giriş yapıldıysa, bu cihazın hesabı olup
    # olmadığını kullanıcının fark etmesi için bir kez göster.

    if st.session_state.get("auto_restored_notice", False):

        st.session_state.auto_restored_notice = False

        notice_col, notice_btn_col = st.columns([5, 1.3])

        with notice_col:

            st.info(
                f"🔒 Bu cihazda **{display_name}** ({user_email}) "
                "olarak otomatik giriş yapıldı. Bu sen değilsen "
                "hemen çıkış yap."
            )

        with notice_btn_col:

            if st.button("🚪 Ben değilim, çıkış yap", use_container_width=True):

                if supabase:

                    try:

                        supabase.auth.sign_out()

                    except Exception:

                        pass

                try:

                    delete_browser_cookie(AUTH_COOKIE_NAME)

                except Exception:

                    pass

                st.session_state.clear()
                st.rerun()

    # ========================================================
    # MENÜ
    # ========================================================

    col_menu, col_space = st.columns([1.5, 6])

    with col_menu:

        st.markdown('<div class="menu-button">', unsafe_allow_html=True)

        with st.popover("☰ Menü", use_container_width=True):

            st.markdown("### 📌 Menü")

            if st.session_state.avatar_url:

                st.markdown(
                    f'<img src="{st.session_state.avatar_url}" '
                    f'class="avatar-circle" width="64" height="64">',
                    unsafe_allow_html=True
                )

            st.write(f"**{display_name}**")
            st.caption(user_email)

            st.divider()

            # -----------------------------------------------
            # SAYFALAR
            # -----------------------------------------------

            if st.button("🌱 AI Koç & Sohbet", use_container_width=True):

                st.session_state.sayfa = "🌱 AI Koç & Sohbet"
                st.rerun()

            if st.button("📊 İlerlemelerim", use_container_width=True):

                st.session_state.sayfa = "📊 İlerlemelerim"
                st.rerun()

            if st.button("📜 AI Geçmişim", use_container_width=True):

                st.session_state.sayfa = "📜 AI Geçmişim"
                st.rerun()

            if st.button("👤 Profilim", use_container_width=True):

                st.session_state.sayfa = "👤 Profilim"
                st.rerun()

            st.divider()

            # -----------------------------------------------
            # ÇIKIŞ
            # -----------------------------------------------

            if st.button("🚪 Çıkış Yap", type="primary", use_container_width=True):

                if supabase:

                    try:

                        supabase.auth.sign_out()

                    except Exception:

                        pass

                try:

                    delete_browser_cookie(AUTH_COOKIE_NAME)

                except Exception:

                    pass

                st.session_state.clear()
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    # ========================================================
    # 8. AI KOÇ & SOHBET
    # ========================================================

    if st.session_state.sayfa == "🌱 AI Koç & Sohbet":

        col_title, col_new_btn = st.columns([4, 1.2])

        with col_title:

            st.title("🌱 Alışkanlık & Motivasyon Asistanı")

        with col_new_btn:

            if st.button("➕ Yeni Sohbet", use_container_width=True):

                st.session_state.current_chat_id = None
                st.rerun()

        st.caption(
            f"Hoş geldin **{display_name}**! "
            f"Bugün **{st.session_state.gun_sayisi}.** günündesin."
        )

        # ====================================================
        # GROQ
        # ====================================================

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

            # -----------------------------------------------
            # MESAJLARI GÖSTER
            # -----------------------------------------------

            for message in current_messages:

                with st.chat_message(message["role"]):

                    st.markdown(message["content"])

            # -----------------------------------------------
            # MESAJ GİRİŞİ
            # -----------------------------------------------

            prompt = st.chat_input("Mesajınızı yazın...")

            if prompt:

                # -------------------------------------------
                # YENİ CHAT
                # -------------------------------------------

                if not st.session_state.current_chat_id:

                    title = prompt[:35] + ("..." if len(prompt) > 35 else "")

                    new_id = create_chat_in_db(st.session_state.user.id, title)

                    st.session_state.current_chat_id = new_id

                    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")

                    st.session_state.chats[new_id] = {
                        "title": title,
                        "date": now_str,
                        "messages": []
                    }

                chat_id = st.session_state.current_chat_id

                # -------------------------------------------
                # USER MESAJI
                # -------------------------------------------

                st.session_state.chats[chat_id]["messages"].append(
                    {"role": "user", "content": prompt}
                )

                save_message_to_db(chat_id, "user", prompt)

                with st.chat_message("user"):

                    st.markdown(prompt)

                # -------------------------------------------
                # AI CEVABI
                # -------------------------------------------

                with st.chat_message("assistant"):

                    try:

                        system_prompt = (
                            "Sen bir motivasyon ve alışkanlık koçusun. "
                            f"Kullanıcı adı: {display_name}."
                        )

                        api_messages = [{"role": "system", "content": system_prompt}]

                        for msg in st.session_state.chats[chat_id]["messages"]:

                            api_messages.append(
                                {"role": msg["role"], "content": msg["content"]}
                            )

                        chat_completion = client.chat.completions.create(
                            messages=api_messages,
                            model="llama-3.3-70b-versatile"
                        )

                        ai_reply = chat_completion.choices[0].message.content

                        st.markdown(ai_reply)

                        st.session_state.chats[chat_id]["messages"].append(
                            {"role": "assistant", "content": ai_reply}
                        )

                        save_message_to_db(chat_id, "assistant", ai_reply)

                    except Exception as e:

                        st.error(f"Sistem Hatası: {e}")

    # ========================================================
    # 9. İLERLEMELER
    # ========================================================

    elif st.session_state.sayfa == "📊 İlerlemelerim":

        st.title("📊 İlerlemelerim")
        st.info("Bu sayfa henüz geliştirilmedi.")

    # ========================================================
    # 10. AI GEÇMİŞİ
    # ========================================================

    elif st.session_state.sayfa == "📜 AI Geçmişim":

        st.title("📜 AI Geçmişim")

        if not st.session_state.chats:

            st.info("Henüz sohbet yok.")

        else:

            # En son güncellenen sohbet en üstte görünsün
            for chat_id, chat in st.session_state.chats.items():

                with st.expander(f"{chat['title']} — {chat['date']}"):

                    for msg in chat["messages"]:

                        if msg["role"] == "user":

                            st.markdown(f"**👤 Sen:** {msg['content']}")

                        else:

                            st.markdown(f"**🤖 AI:** {msg['content']}")

    # ========================================================
    # 11. PROFİL
    # ========================================================

    elif st.session_state.sayfa == "👤 Profilim":

        st.title("👤 Profilim")
        st.markdown("---")

        # ====================================================
        # PROFİL FOTOĞRAFI
        # ====================================================

        st.subheader("Profil Fotoğrafı")

        col_avatar, col_upload = st.columns([1, 3])

        with col_avatar:

            if st.session_state.avatar_url:

                st.markdown(
                    f'<img src="{st.session_state.avatar_url}" '
                    f'class="avatar-circle" width="120" height="120">',
                    unsafe_allow_html=True
                )

            else:

                st.markdown("🙍 Henüz fotoğraf yüklenmedi.")

        with col_upload:

            avatar_file = st.file_uploader(
                "Yeni fotoğraf seç (jpg, jpeg, png)",
                type=["png", "jpg", "jpeg"],
                key="avatar_uploader"
            )

            if avatar_file is not None:

                if st.button("📤 Fotoğrafı Yükle", use_container_width=True):

                    with st.spinner("Yükleniyor..."):

                        new_avatar_url = upload_avatar(
                            st.session_state.user.id, avatar_file
                        )

                    if new_avatar_url:

                        access_token = st.session_state.get("access_token")
                        refresh_token = st.session_state.get("refresh_token")

                        if not access_token or not refresh_token:

                            st.error(
                                "Oturum süresi dolmuş. "
                                "Lütfen çıkış yapıp tekrar giriş yap."
                            )

                        else:

                            try:

                                supabase.auth.set_session(access_token, refresh_token)

                                supabase.auth.update_user(
                                    {"data": {"avatar_url": new_avatar_url}}
                                )

                                st.session_state.avatar_url = new_avatar_url

                                st.success("Profil fotoğrafı güncellendi!")
                                st.rerun()

                            except Exception as e:

                                st.error(f"Profil güncellenemedi: {e}")

        st.markdown("---")

        # ====================================================
        # PROFİL BİLGİLERİ FORMU
        # ====================================================

        with st.form("profile_form"):

            st.subheader("Profil Bilgilerini Düzenle")

            # -----------------------------------------------
            # İSİM
            # -----------------------------------------------

            new_name = st.text_input("Ad Soyad", value=st.session_state.profile_name)

            # -----------------------------------------------
            # DOĞUM TARİHİ
            # -----------------------------------------------

            try:

                current_bdate = datetime.strptime(
                    st.session_state.birth_date, "%Y-%m-%d"
                ).date()

            except Exception:

                current_bdate = date(2000, 1, 1)

            new_bdate = st.date_input("Doğum Tarihi", value=current_bdate)

            # -----------------------------------------------
            # CİNSİYET
            # -----------------------------------------------

            gender_options = ["Kadın", "Erkek", "Belirtmek İstemiyorum"]

            if st.session_state.gender in gender_options:

                current_gender_idx = gender_options.index(st.session_state.gender)

            else:

                current_gender_idx = 2

            new_gender = st.selectbox("Cinsiyet", gender_options, index=current_gender_idx)

            st.markdown("")

            # -----------------------------------------------
            # FORM BUTONLARI
            # -----------------------------------------------

            col_save, col_cancel = st.columns(2)

            with col_save:

                submitted = st.form_submit_button(
                    "💾 Kaydet", type="primary", use_container_width=True
                )

            with col_cancel:

                cancel = st.form_submit_button("İptal", use_container_width=True)

        # ====================================================
        # KAYDET
        # ====================================================

        if submitted:

            if not new_name.strip():

                st.error("Ad Soyad boş olamaz.")

            elif not supabase:

                st.error("Veri tabanı bağlantısı kurulamadı.")

            else:

                try:

                    access_token = st.session_state.get("access_token")
                    refresh_token = st.session_state.get("refresh_token")

                    if not access_token or not refresh_token:

                        st.error(
                            "Oturum süresi dolmuş. "
                            "Lütfen çıkış yapıp tekrar giriş yap."
                        )

                        st.stop()

                    supabase.auth.set_session(access_token, refresh_token)

                    update_result = supabase.auth.update_user(
                        {
                            "data": {
                                "full_name": new_name.strip(),
                                "birth_date": str(new_bdate),
                                "gender": new_gender
                            }
                        }
                    )

                    if hasattr(update_result, "session") and update_result.session:

                        st.session_state.access_token = update_result.session.access_token
                        st.session_state.refresh_token = update_result.session.refresh_token

                    st.session_state.profile_name = new_name.strip()
                    st.session_state.birth_date = str(new_bdate)
                    st.session_state.gender = new_gender

                    st.success("Profil başarıyla güncellendi!")
                    st.rerun()

                except Exception as e:

                    st.error(f"Güncelleme hatası: {e}")

        # ====================================================
        # İPTAL
        # ====================================================

        if cancel:

            st.session_state.sayfa = "🌱 AI Koç & Sohbet"
            st.rerun()

        st.markdown("---")

        st.write(f"**E-posta:** {user_email}")
        st.caption("E-posta adresi değiştirilemez.")