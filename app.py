import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client, Client
from groq import Groq
import uuid
import re
import math
import io
import qrcode
import pandas as pd
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
# 1B. SABİT LİSTELER (şehir, hobi, ruh hali)
# ============================================================

TURKISH_CITIES = [
    "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya",
    "Artvin", "Aydın", "Balıkesir", "Bilecik", "Bingöl", "Bitlis", "Bolu",
    "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır",
    "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep",
    "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Isparta", "Mersin", "İstanbul",
    "İzmir", "Kars", "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir", "Kocaeli",
    "Konya", "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla",
    "Muş", "Nevşehir", "Niğde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt",
    "Sinop", "Sivas", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Şanlıurfa",
    "Uşak", "Van", "Yozgat", "Zonguldak", "Aksaray", "Bayburt", "Karaman",
    "Kırıkkale", "Batman", "Şırnak", "Bartın", "Ardahan", "Iğdır", "Yalova",
    "Karabük", "Kilis", "Osmaniye", "Düzce"
]

HOBBY_OPTIONS = [
    "Spor", "Dans", "Müzik", "Sanat", "Kitap & edebiyat", "Sinema & tiyatro",
    "Astronomi & uzay", "Bilim & teknoloji", "Doğa & kamp",
    "Yemek & gastronomi", "El sanatları & tasarım", "Oyun & masa oyunları",
    "Fotoğrafçılık", "Gezi & kültür", "Gönüllülük & sosyal sorumluluk"
]

MOOD_OPTIONS = {
    "Enerjik": "⚡",
    "Üzgün": "😔",
    "Stresli": "😖",
    "Yorgun": "🥱"
}


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
    token'ı ÜST (asıl) sayfanın URL'ine ekleyip yeniden yükler."""

    js = f"""
    <script>
    (function() {{
        var match = document.cookie.match(new RegExp('(^| )' + '{name}' + '=([^;]+)'));
        var topParams = new URLSearchParams(window.top.location.search);
        if (match && !topParams.has('{query_param}')) {{
            topParams.set('{query_param}', match[2]);
            var newUrl = window.top.location.pathname + '?' + topParams.toString()
                + window.top.location.hash;
            window.top.location.href = newUrl;
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

        cache_bust_url = f"{public_url}?t={int(datetime.utcnow().timestamp())}"

        return cache_bust_url

    except Exception as e:

        st.error(f"Fotoğraf yüklenemedi: {e}")

        return None


def apply_auth_session(user, session) -> None:
    """Giriş sonrası ya da çerezden otomatik oturum açarken kullanılan ortak kod."""

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
    st.session_state.city = meta.get("city", "İstanbul")
    st.session_state.hobbies = meta.get("hobbies", [])

    created_at = getattr(user, "created_at", None)

    st.session_state.gun_sayisi = calculate_day_count(
        str(created_at) if created_at else ""
    )

    st.session_state.chats = load_chats_from_db(user.id)
    st.session_state.current_chat_id = None
    st.session_state.sayfa = "🌱 AI Koç & Sohbet"
    st.session_state.show_auth_modal = False

    st.session_state.municipality = get_municipality_info(user.id)
    st.session_state.business = get_business_info(user.id)


# ============================================================
# 4B. ETKİNLİK YARDIMCI FONKSİYONLARI (YENİ)
# ============================================================

def load_active_events(city: str | None = None) -> list:
    """Aktif (tarihi geçmemiş) etkinlikleri Supabase'ten çeker.
    city verilirse sadece o şehirdekileri getirir."""

    if not supabase:
        return []

    try:

        query = (
            supabase.table("events")
            .select("*")
            .eq("is_active", True)
            .gte("event_date", str(date.today()))
            .order("event_date")
        )

        if city:
            query = query.eq("city", city)

        result = query.execute()

        return result.data

    except Exception as e:

        st.warning(f"Etkinlikler yüklenirken hata oluştu: {e}")

        return []


def deactivate_expired_events() -> None:
    """Tarihi geçmiş etkinlikleri otomatik olarak pasife çeker.
    Her sayfa yüklemesinde çalışır, hafif bir sorgu olduğu için sorun yaratmaz."""

    if not supabase:
        return

    try:

        supabase.table("events").update({"is_active": False}).lt(
            "event_date", str(date.today())
        ).eq("is_active", True).execute()

    except Exception:

        pass


def get_event_by_id(event_id: str) -> dict | None:
    """Tek bir etkinliğin detayını id'sine göre çeker."""

    if not supabase:
        return None

    try:

        result = (
            supabase.table("events")
            .select("*")
            .eq("id", event_id)
            .single()
            .execute()
        )

        return result.data

    except Exception:

        return None


# ============================================================
# 4D. İŞLETME (SPONSOR) YARDIMCI FONKSİYONLARI (YENİ)
# ============================================================

def get_business_info(auth_user_id: str) -> dict | None:
    """Giriş yapan hesabın bir işletme hesabı olup olmadığını kontrol eder."""

    if not supabase or not auth_user_id:
        return None

    try:

        result = (
            supabase.table("businesses")
            .select("*")
            .eq("auth_user_id", auth_user_id)
            .execute()
        )

        if result.data:

            return result.data[0]

        return None

    except Exception:

        return None


def load_business_rewards(business_id: str) -> list:
    """Bir işletmenin eklediği tüm ödülleri (aktif + pasif) getirir."""

    if not supabase:
        return []

    try:

        result = (
            supabase.table("rewards")
            .select("*")
            .eq("business_id", business_id)
            .order("created_at", desc=True)
            .execute()
        )

        return result.data

    except Exception as e:

        st.warning(f"Ödüller yüklenirken hata oluştu: {e}")

        return []


def insert_reward(business_id: str, data: dict) -> bool:
    """İşletme adına yeni bir ödül/kampanya ekler."""

    if not supabase:
        return False

    try:

        payload = dict(data)
        payload["business_id"] = business_id

        supabase.table("rewards").insert(payload).execute()

        return True

    except Exception as e:

        st.error(f"Ödül eklenemedi: {e}")

        return False


def set_reward_active(reward_id: str, is_active: bool) -> bool:
    """Bir ödülü aktif/pasif yapar."""

    if not supabase:
        return False

    try:

        supabase.table("rewards").update({"is_active": is_active}).eq(
            "id", reward_id
        ).execute()

        return True

    except Exception as e:

        st.error(f"Ödül güncellenemedi: {e}")

        return False


def load_active_rewards() -> list:
    """Kullanıcıya gösterilecek, aktif olan tüm ödülleri işletme adıyla getirir."""

    if not supabase:
        return []

    try:

        result = (
            supabase.table("rewards")
            .select("*, businesses(name, category)")
            .eq("is_active", True)
            .order("points_cost")
            .execute()
        )

        return result.data

    except Exception as e:

        st.warning(f"Ödüller yüklenirken hata oluştu: {e}")

        return []


def redeem_reward(user_id: str, reward_id: str, points_cost: int) -> str | None:
    """Kullanıcının puanını harcayarak ödülü talep etmesini sağlar.
    Başarılıysa işletmede gösterilecek 6 haneli kodu döner."""

    if not supabase:
        return None

    try:

        current_points = get_user_total_points(user_id)

        if current_points < points_cost:

            st.error("Yeterli puanın yok.")

            return None

        code = str(uuid.uuid4().int)[:6]

        supabase.table("reward_redemptions").insert(
            {
                "user_id": user_id,
                "reward_id": reward_id,
                "redemption_code": code,
                "used": False
            }
        ).execute()

        new_total = current_points - points_cost

        supabase.table("user_points").update(
            {"total_points": new_total, "updated_at": datetime.utcnow().isoformat()}
        ).eq("user_id", user_id).execute()

        return code

    except Exception as e:

        st.error(f"Ödül talep edilemedi: {e}")

        return None


def load_user_redemptions(user_id: str) -> list:
    """Kullanıcının geçmiş ödül taleplerini getirir."""

    if not supabase:
        return []

    try:

        result = (
            supabase.table("reward_redemptions")
            .select("*, rewards(title, points_cost, businesses(name))")
            .eq("user_id", user_id)
            .order("redeemed_at", desc=True)
            .execute()
        )

        return result.data

    except Exception:

        return []


def verify_redemption_code(business_id: str, code: str) -> dict | None:
    """İşletmenin girdiği kodun geçerli olup olmadığını, kendi ödüllerinden
    biri için mi olduğunu kontrol eder. Geçerliyse kaydı döner."""

    if not supabase:
        return None

    try:

        result = (
            supabase.table("reward_redemptions")
            .select("*, rewards(title, business_id)")
            .eq("redemption_code", code)
            .execute()
        )

        if not result.data:

            return None

        redemption = result.data[0]

        if redemption["rewards"]["business_id"] != business_id:

            return None

        return redemption

    except Exception:

        return None


def mark_redemption_used(redemption_id: str) -> bool:
    """Ödül kodunu 'kullanıldı' olarak işaretler."""

    if not supabase:
        return False

    try:

        supabase.table("reward_redemptions").update({"used": True}).eq(
            "id", redemption_id
        ).execute()

        return True

    except Exception:

        return False


def render_business_panel(business: dict) -> None:
    """İşletme hesabıyla giriş yapıldığında gösterilen tam ayrı panel."""

    col_title, col_logout = st.columns([4, 1.2])

    with col_title:

        st.title(f"🏪 {business['name']} — İşletme Paneli")

        if business.get("category"):

            st.caption(business["category"])

    with col_logout:

        if st.button("🚪 Çıkış Yap", type="primary", use_container_width=True):

            if supabase:

                try:

                    supabase.auth.sign_out()

                except Exception:

                    pass

            st.session_state.clear()
            st.rerun()

    st.divider()

    tab_rewards, tab_new, tab_verify = st.tabs(
        ["🎁 Ödüllerim", "➕ Yeni Ödül Ekle", "✅ Kod Doğrula"]
    )

    # ------------------------------------------------------
    # ÖDÜLLERİM
    # ------------------------------------------------------

    with tab_rewards:

        rewards = load_business_rewards(business["id"])

        if not rewards:

            st.info("Henüz hiç ödül eklemediniz.")

        else:

            for reward in rewards:

                status_label = "🟢 Aktif" if reward.get("is_active") else "⚪ Pasif"

                with st.container(border=True):

                    col_info, col_toggle = st.columns([4, 1])

                    with col_info:

                        st.subheader(f"{reward['title']}  —  {status_label}")
                        st.caption(f"🏆 {reward['points_cost']} puan")

                        if reward.get("description"):

                            st.write(reward["description"])

                    with col_toggle:

                        if reward.get("is_active"):

                            if st.button(
                                "Pasife Al",
                                key=f"deact_reward_{reward['id']}",
                                use_container_width=True
                            ):

                                if set_reward_active(reward["id"], False):

                                    st.rerun()

                        else:

                            if st.button(
                                "Aktif Et",
                                key=f"act_reward_{reward['id']}",
                                use_container_width=True
                            ):

                                if set_reward_active(reward["id"], True):

                                    st.rerun()

    # ------------------------------------------------------
    # YENİ ÖDÜL EKLE
    # ------------------------------------------------------

    with tab_new:

        with st.form("new_reward_form", clear_on_submit=True):

            rw_title = st.text_input("Kampanya Adı * (örn: %20 Kahve İndirimi)")
            rw_description = st.text_area("Açıklama")

            rw_points = st.number_input(
                "Kaç puana mal olsun?",
                min_value=1,
                value=20,
                step=5
            )

            submitted_reward = st.form_submit_button(
                "✅ Ödülü Yayınla", type="primary", use_container_width=True
            )

        if submitted_reward:

            if not rw_title.strip():

                st.error("Kampanya adı boş olamaz.")

            else:

                success = insert_reward(
                    business["id"],
                    {
                        "title": rw_title.strip(),
                        "description": rw_description.strip(),
                        "points_cost": int(rw_points),
                        "is_active": True
                    }
                )

                if success:

                    st.success("Ödül başarıyla yayınlandı!")
                    st.rerun()

    # ------------------------------------------------------
    # KOD DOĞRULA (müşteri geldiğinde kasiyer burayı kullanır)
    # ------------------------------------------------------

    with tab_verify:

        st.write("Müşterinin gösterdiği 6 haneli kodu girin:")

        entered_code = st.text_input("Doğrulama Kodu", max_chars=6, key="verify_code_input")

        if st.button("Kontrol Et", type="primary"):

            if not entered_code.strip():

                st.warning("Lütfen bir kod girin.")

            else:

                redemption = verify_redemption_code(business["id"], entered_code.strip())

                if not redemption:

                    st.error("Kod geçersiz veya bu işletmeye ait değil.")

                elif redemption.get("used"):

                    st.warning("Bu kod daha önce kullanılmış.")

                else:

                    st.success(
                        f"✅ Geçerli kod! Kampanya: "
                        f"**{redemption['rewards']['title']}**"
                    )

                    if st.button("Kullanıldı Olarak İşaretle", type="primary"):

                        if mark_redemption_used(redemption["id"]):

                            st.success("Kod kullanıldı olarak işaretlendi.")
                            st.rerun()


# ============================================================
# 4E. BELEDİYE PANELİ YARDIMCI FONKSİYONLARI (YENİ)
# ============================================================

# ============================================================
# 4C. KATILIM / PUAN / QR YARDIMCI FONKSİYONLARI (YENİ)
# ============================================================

def generate_qr_image(event_id: str, qr_code: str) -> bytes | None:
    """Bir etkinlik için, taratıldığında uygulamayı doğrulama linkiyle
    açacak bir QR kod görseli üretir (PNG bytes olarak döner)."""

    if not qr_code:
        return None

    try:

        verify_url = f"https://relivee.com.tr/?verify_event={event_id}&code={qr_code}"

        qr = qrcode.QRCode(box_size=8, border=2)
        qr.add_data(verify_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")

        return buffer.getvalue()

    except Exception:

        return None


def haversine_distance_m(lat1, lon1, lat2, lon2) -> float:
    """İki koordinat arasındaki mesafeyi metre cinsinden hesaplar."""

    R = 6371000  # Dünya yarıçapı, metre

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def has_user_participated(user_id: str, event_id: str) -> bool:
    """Kullanıcının bu etkinliğe daha önce katılıp katılmadığını kontrol eder."""

    if not supabase:
        return False

    try:

        result = (
            supabase.table("participations")
            .select("id")
            .eq("user_id", user_id)
            .eq("event_id", event_id)
            .execute()
        )

        return len(result.data) > 0

    except Exception:

        return False


def record_participation(user_id: str, event_id: str, method: str, points: int) -> bool:
    """Katılımı kaydeder ve kullanıcının toplam puanını günceller."""

    if not supabase:
        return False

    try:

        supabase.table("participations").insert(
            {
                "user_id": user_id,
                "event_id": event_id,
                "verified": True,
                "verification_method": method,
                "points_earned": points
            }
        ).execute()

        # Toplam puanı güncelle (kayıt yoksa oluştur, varsa üstüne ekle)
        existing = (
            supabase.table("user_points")
            .select("total_points")
            .eq("user_id", user_id)
            .execute()
        )

        if existing.data:

            new_total = existing.data[0]["total_points"] + points

            supabase.table("user_points").update(
                {"total_points": new_total, "updated_at": datetime.utcnow().isoformat()}
            ).eq("user_id", user_id).execute()

        else:

            supabase.table("user_points").insert(
                {"user_id": user_id, "total_points": points}
            ).execute()

        return True

    except Exception as e:

        st.error(f"Katılım kaydedilemedi: {e}")

        return False


def get_user_total_points(user_id: str) -> int:
    """Kullanıcının güncel toplam puanını döner."""

    if not supabase:
        return 0

    try:

        result = (
            supabase.table("user_points")
            .select("total_points")
            .eq("user_id", user_id)
            .execute()
        )

        if result.data:

            return result.data[0]["total_points"]

        return 0

    except Exception:

        return 0


def load_user_participations(user_id: str) -> list:
    """Kullanıcının katılım geçmişini, etkinlik bilgileriyle birlikte getirir."""

    if not supabase:
        return []

    try:

        result = (
            supabase.table("participations")
            .select("*, events(title, event_date, city)")
            .eq("user_id", user_id)
            .order("participated_at", desc=True)
            .execute()
        )

        return result.data

    except Exception:

        return []


def trigger_geolocation_participation(event_id: str) -> None:
    """Tarayıcıdan konum izni isteyip, alınan koordinatları sayfa
    URL'ine ekleyerek yeniden yükleyen JS butonu render eder."""

    js = f"""
    <button id="loc-btn" style="
        background-color:#2e7d32;color:white;border:none;
        padding:0.6rem 1rem;border-radius:8px;font-weight:bold;
        cursor:pointer;width:100%;">
        📍 Konumumla Katıl
    </button>
    <p id="loc-status" style="font-size:0.85rem;color:#555;"></p>
    <script>
    document.getElementById('loc-btn').addEventListener('click', function() {{
        document.getElementById('loc-status').innerText = 'Konum alınıyor...';
        navigator.geolocation.getCurrentPosition(function(pos) {{
            var lat = pos.coords.latitude;
            var lon = pos.coords.longitude;
            var topParams = new URLSearchParams(window.top.location.search);
            topParams.set('verify_location_event', '{event_id}');
            topParams.set('user_lat', lat);
            topParams.set('user_lon', lon);
            var newUrl = window.top.location.pathname + '?' + topParams.toString();
            window.top.location.href = newUrl;
        }}, function(err) {{
            document.getElementById('loc-status').innerText =
                'Konum alınamadı: ' + err.message;
        }});
    }});
    </script>
    """

    components.html(js, height=90)


def get_municipality_info(auth_user_id: str) -> dict | None:
    """Giriş yapan hesabın bir belediye hesabı olup olmadığını kontrol eder.
    Belediye ise bilgilerini döner, değilse None döner."""

    if not supabase or not auth_user_id:
        return None

    try:

        result = (
            supabase.table("municipalities")
            .select("*")
            .eq("auth_user_id", auth_user_id)
            .execute()
        )

        if result.data:

            return result.data[0]

        return None

    except Exception:

        return None


def load_municipality_events(municipality_id: str) -> list:
    """Bir belediyenin eklediği TÜM etkinlikleri (aktif + pasif) getirir."""

    if not supabase:
        return []

    try:

        result = (
            supabase.table("events")
            .select("*")
            .eq("municipality_id", municipality_id)
            .order("event_date", desc=True)
            .execute()
        )

        return result.data

    except Exception as e:

        st.warning(f"Etkinlikler yüklenirken hata oluştu: {e}")

        return []


def insert_event(municipality_id: str, data: dict) -> bool:
    """Belediye adına yeni bir etkinlik ekler. Her etkinliğe otomatik
    benzersiz bir QR doğrulama kodu atanır."""

    if not supabase:
        return False

    try:

        payload = dict(data)
        payload["municipality_id"] = municipality_id
        payload["qr_code"] = uuid.uuid4().hex

        supabase.table("events").insert(payload).execute()

        return True

    except Exception as e:

        st.error(f"Etkinlik eklenemedi: {e}")

        return False


def set_event_active(event_id: str, is_active: bool) -> bool:
    """Bir etkinliği aktif/pasif yapar (belediye kendi etkinliğini kapatabilsin)."""

    if not supabase:
        return False

    try:

        supabase.table("events").update({"is_active": is_active}).eq(
            "id", event_id
        ).execute()

        return True

    except Exception as e:

        st.error(f"Etkinlik güncellenemedi: {e}")

        return False


def render_municipality_panel(municipality: dict) -> None:
    """Belediye hesabı ile giriş yapıldığında gösterilen tam ayrı panel.
    Normal kullanıcı arayüzünün yerine geçer."""

    col_title, col_logout = st.columns([4, 1.2])

    with col_title:

        st.title(f"🏛️ {municipality['name']} — Etkinlik Paneli")
        st.caption(f"Şehir: {municipality['city']}")

    with col_logout:

        if st.button("🚪 Çıkış Yap", type="primary", use_container_width=True):

            if supabase:

                try:

                    supabase.auth.sign_out()

                except Exception:

                    pass

            st.session_state.clear()
            st.rerun()

    st.divider()

    tab_list, tab_new = st.tabs(["📋 Etkinliklerim", "➕ Yeni Etkinlik Ekle"])

    # ------------------------------------------------------
    # ETKİNLİKLERİM (LİSTE)
    # ------------------------------------------------------

    with tab_list:

        events = load_municipality_events(municipality["id"])

        if not events:

            st.info("Henüz hiç etkinlik eklemediniz.")

        else:

            for event in events:

                status_label = "🟢 Aktif" if event.get("is_active") else "⚪ Pasif"

                with st.container(border=True):

                    col_info, col_toggle = st.columns([4, 1])

                    with col_info:

                        st.subheader(f"{event['title']}  —  {status_label}")
                        st.caption(
                            f"📅 {event['event_date']}  •  🕐 {event['event_time']}  •  "
                            f"📍 {event.get('address', event['city'])}  •  "
                            f"🏆 {event.get('points_reward', 10)} puan"
                        )

                        if event.get("category"):

                            st.badge(event["category"])

                        if event.get("description"):

                            st.write(event["description"])

                        with st.popover("📱 QR Kodunu Göster"):

                            qr_image = generate_qr_image(event["id"], event.get("qr_code", ""))

                            if qr_image:

                                st.image(qr_image, width=200)
                                st.caption(
                                    "Bu QR kodu etkinlik alanında basılı olarak "
                                    "bulundurun. Katılımcılar telefon kamerasıyla "
                                    "okutunca katılımları otomatik onaylanır."
                                )

                    with col_toggle:

                        if event.get("is_active"):

                            if st.button(
                                "Pasife Al",
                                key=f"deactivate_{event['id']}",
                                use_container_width=True
                            ):

                                if set_event_active(event["id"], False):

                                    st.rerun()

                        else:

                            if st.button(
                                "Aktif Et",
                                key=f"activate_{event['id']}",
                                use_container_width=True
                            ):

                                if set_event_active(event["id"], True):

                                    st.rerun()

    # ------------------------------------------------------
    # YENİ ETKİNLİK EKLE
    # ------------------------------------------------------

    with tab_new:

        with st.form("new_event_form", clear_on_submit=True):

            ev_title = st.text_input("Etkinlik Adı *")
            ev_description = st.text_area("Açıklama")

            ev_category = st.selectbox(
                "Kategori",
                HOBBY_OPTIONS
            )

            col_date, col_time = st.columns(2)

            with col_date:

                ev_date = st.date_input(
                    "Etkinlik Tarihi *",
                    value=date.today() + timedelta(days=1)
                )

            with col_time:

                ev_time = st.time_input("Etkinlik Saati *")

            ev_address = st.text_input(
                "Adres",
                value=f"{municipality['city']} Merkez"
            )

            col_lat, col_lon = st.columns(2)

            with col_lat:

                ev_lat = st.number_input(
                    "Enlem (latitude)",
                    format="%.6f",
                    value=0.0,
                    help="Google Maps'te konuma sağ tıklayıp koordinatları kopyalayabilirsiniz."
                )

            with col_lon:

                ev_lon = st.number_input(
                    "Boylam (longitude)",
                    format="%.6f",
                    value=0.0
                )

            ev_points = st.number_input(
                "Katılım Ödülü (puan)",
                min_value=1,
                value=10,
                step=5
            )

            submitted_event = st.form_submit_button(
                "✅ Etkinliği Yayınla", type="primary", use_container_width=True
            )

        if submitted_event:

            if not ev_title.strip():

                st.error("Etkinlik adı boş olamaz.")

            else:

                success = insert_event(
                    municipality["id"],
                    {
                        "title": ev_title.strip(),
                        "description": ev_description.strip(),
                        "category": ev_category,
                        "city": municipality["city"],
                        "address": ev_address.strip(),
                        "latitude": ev_lat if ev_lat != 0.0 else None,
                        "longitude": ev_lon if ev_lon != 0.0 else None,
                        "event_date": str(ev_date),
                        "event_time": ev_time.strftime("%H:%M"),
                        "points_reward": int(ev_points),
                        "is_active": True
                    }
                )

                if success:

                    st.success("Etkinlik başarıyla yayınlandı!")
                    st.rerun()


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

if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"

if "reset_email_pending" not in st.session_state:
    st.session_state.reset_email_pending = None

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

if "city" not in st.session_state:
    st.session_state.city = "İstanbul"

if "hobbies" not in st.session_state:
    st.session_state.hobbies = []

if "mood" not in st.session_state:
    st.session_state.mood = None

if "selected_event_id" not in st.session_state:
    st.session_state.selected_event_id = None

if "municipality" not in st.session_state:
    st.session_state.municipality = None

if "business" not in st.session_state:
    st.session_state.business = None

if "last_redemption_code" not in st.session_state:
    st.session_state.last_redemption_code = None

if "last_redemption_title" not in st.session_state:
    st.session_state.last_redemption_title = None


# ============================================================
# 5A. HER ÇALIŞTIRMADA SUPABASE OTURUMUNU YENİDEN YÜKLE
# ============================================================

if supabase and st.session_state.get("user") and st.session_state.get("access_token"):

    try:

        supabase.auth.set_session(
            st.session_state.access_token,
            st.session_state.refresh_token
        )

    except Exception:

        pass


# ============================================================
# 5AB. QR / KONUM İLE KATILIM DOĞRULAMA (URL parametrelerinden)
# ============================================================
# Kullanıcı zaten giriş yapmışsa ve URL'de doğrulama parametreleri
# varsa (QR taratıldığında veya konum butonuna basıldığında oluşur),
# katılımı burada kaydedip parametreleri temizliyoruz.

if st.session_state.get("user"):

    verify_event_id = st.query_params.get("verify_event")
    verify_code = st.query_params.get("code")

    if verify_event_id and verify_code:

        event = get_event_by_id(verify_event_id)

        if event and event.get("qr_code") == verify_code:

            if has_user_participated(st.session_state.user.id, verify_event_id):

                st.session_state.participation_notice = (
                    "info", "Bu etkinliğe zaten daha önce katılım sağladınız."
                )

            else:

                ok = record_participation(
                    st.session_state.user.id,
                    verify_event_id,
                    "qr",
                    event.get("points_reward", 10)
                )

                if ok:

                    st.session_state.participation_notice = (
                        "success",
                        f"🎉 Katılımın onaylandı! "
                        f"{event.get('points_reward', 10)} puan kazandın."
                    )

        else:

            st.session_state.participation_notice = (
                "error", "QR kod geçersiz veya etkinlik bulunamadı."
            )

        st.query_params.clear()
        st.rerun()

    verify_loc_event_id = st.query_params.get("verify_location_event")
    user_lat = st.query_params.get("user_lat")
    user_lon = st.query_params.get("user_lon")

    if verify_loc_event_id and user_lat and user_lon:

        event = get_event_by_id(verify_loc_event_id)

        if not event or not event.get("latitude") or not event.get("longitude"):

            st.session_state.participation_notice = (
                "error", "Bu etkinlik için konum bilgisi tanımlı değil."
            )

        elif has_user_participated(st.session_state.user.id, verify_loc_event_id):

            st.session_state.participation_notice = (
                "info", "Bu etkinliğe zaten daha önce katılım sağladınız."
            )

        else:

            distance = haversine_distance_m(
                float(user_lat), float(user_lon),
                event["latitude"], event["longitude"]
            )

            if distance <= 300:

                ok = record_participation(
                    st.session_state.user.id,
                    verify_loc_event_id,
                    "location",
                    event.get("points_reward", 10)
                )

                if ok:

                    st.session_state.participation_notice = (
                        "success",
                        f"🎉 Konumun doğrulandı! "
                        f"{event.get('points_reward', 10)} puan kazandın."
                    )

            else:

                st.session_state.participation_notice = (
                    "error",
                    f"Etkinlik konumuna çok uzaksın "
                    f"({int(distance)} metre). Etkinlik alanında tekrar dene."
                )

        st.session_state.sayfa = "📍 Etkinlik Detay"
        st.session_state.selected_event_id = verify_loc_event_id

        st.query_params.clear()
        st.rerun()


# ============================================================
# 5B. TARAYICI ÇEREZİNDEN OTOMATİK OTURUM AÇMA
# ============================================================

if st.session_state.user is None and not st.session_state.get("auth_restore_done", False):

    token_from_url = st.query_params.get(AUTH_QUERY_PARAM)

    if token_from_url:

        st.session_state.auth_restore_done = True

        if supabase:

            try:

                res = supabase.auth.refresh_session(token_from_url)

                if res and res.user and res.session:

                    apply_auth_session(res.user, res.session)
                    st.session_state.auto_restored_notice = True

                    st.session_state.pending_remember_token = res.session.refresh_token

            except Exception:

                delete_browser_cookie(AUTH_COOKIE_NAME)

        st.query_params.clear()
        st.rerun()

    else:

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
            st.session_state.auth_mode = "login"
            st.rerun()

    with col_register:

        if st.button("📝 Üye Ol", type="primary", use_container_width=True):

            st.session_state.show_auth_modal = True
            st.session_state.auth_mode = "register"
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

                if st.session_state.auth_mode not in ("reset_request", "reset_verify"):

                    seg_login, seg_register = st.columns(2)

                    with seg_login:

                        if st.button(
                            "🔑 Giriş Yap",
                            key="seg_login_btn",
                            type="primary" if st.session_state.auth_mode == "login" else "secondary",
                            use_container_width=True
                        ):

                            st.session_state.auth_mode = "login"
                            st.rerun()

                    with seg_register:

                        if st.button(
                            "📝 Kayıt Ol",
                            key="seg_register_btn",
                            type="primary" if st.session_state.auth_mode == "register" else "secondary",
                            use_container_width=True
                        ):

                            st.session_state.auth_mode = "register"
                            st.rerun()

                    st.markdown("")

                # =================================================
                # GİRİŞ
                # =================================================

                if st.session_state.auth_mode == "login":

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

                                apply_auth_session(res.user, res.session)

                                if res.session and remember_device:

                                    st.session_state.pending_remember_token = (
                                        res.session.refresh_token
                                    )

                                st.rerun()

                            except Exception as e:

                                st.error(f"Giriş başarısız: {e}")

                    if st.button("Şifremi unuttum", key="btn_forgot", use_container_width=True):

                        st.session_state.auth_mode = "reset_request"
                        st.rerun()

                # =================================================
                # ŞİFRE SIFIRLAMA — 1. ADIM: E-POSTA GİR, KOD GÖNDER
                # =================================================

                if st.session_state.auth_mode == "reset_request":

                    st.markdown("**Şifre Sıfırlama**")
                    st.caption("Giriş yaptığın e-posta adresini yaz, sana bir doğrulama kodu gönderelim.")

                    reset_email = st.text_input("E-Posta Adresi", key="reset_email")

                    if st.button("Doğrulama Kodu Gönder", type="primary", key="btn_reset_send", use_container_width=True):

                        if not reset_email or not is_valid_email(reset_email):

                            st.warning("Lütfen geçerli bir e-posta adresi girin.")

                        else:

                            try:

                                supabase.auth.reset_password_email(reset_email.strip().lower())

                                st.session_state.reset_email_pending = reset_email.strip().lower()
                                st.session_state.auth_mode = "reset_verify"
                                st.success("Kod gönderildi! E-postanı kontrol et.")
                                st.rerun()

                            except Exception as e:

                                st.error(f"Kod gönderilemedi: {e}")

                    if st.button("← Girişe dön", key="btn_back_to_login_1", use_container_width=True):

                        st.session_state.auth_mode = "login"
                        st.rerun()

                # =================================================
                # ŞİFRE SIFIRLAMA — 2. ADIM: KODU GİR, YENİ ŞİFRE BELİRLE
                # =================================================

                if st.session_state.auth_mode == "reset_verify":

                    st.markdown("**Şifre Sıfırlama**")
                    st.caption(
                        f"**{st.session_state.get('reset_email_pending', '')}** adresine "
                        "gönderilen 6 haneli kodu ve yeni şifreni gir."
                    )

                    reset_code = st.text_input("Doğrulama Kodu", key="reset_code")
                    new_pass_1 = st.text_input("Yeni Şifre", type="password", key="reset_new_pass")
                    new_pass_2 = st.text_input("Yeni Şifre (Tekrar)", type="password", key="reset_new_pass_2")

                    if st.button("Şifreyi Sıfırla", type="primary", key="btn_reset_confirm", use_container_width=True):

                        if not reset_code or not new_pass_1:

                            st.warning("Lütfen kodu ve yeni şifreni gir.")

                        elif len(new_pass_1) < 6:

                            st.warning("Şifre en az 6 karakter olmalıdır.")

                        elif new_pass_1 != new_pass_2:

                            st.error("Şifreler eşleşmiyor!")

                        else:

                            try:

                                verify_res = supabase.auth.verify_otp(
                                    {
                                        "email": st.session_state.get("reset_email_pending", ""),
                                        "token": reset_code.strip(),
                                        "type": "recovery"
                                    }
                                )

                                if verify_res.session:

                                    supabase.auth.set_session(
                                        verify_res.session.access_token,
                                        verify_res.session.refresh_token
                                    )

                                supabase.auth.update_user({"password": new_pass_1})

                                st.session_state.auth_mode = "login"
                                st.session_state.reset_email_pending = None

                                st.success("Şifren güncellendi! Şimdi yeni şifrenle giriş yapabilirsin.")
                                st.rerun()

                            except Exception as e:

                                st.error(f"Kod geçersiz ya da süresi dolmuş: {e}")

                    if st.button("← Girişe dön", key="btn_back_to_login_2", use_container_width=True):

                        st.session_state.auth_mode = "login"
                        st.rerun()

                # =================================================
                # KAYIT
                # =================================================

                if st.session_state.auth_mode == "register":

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

                    reg_city = st.selectbox(
                        "Yaşadığın Şehir",
                        TURKISH_CITIES,
                        index=TURKISH_CITIES.index("İstanbul"),
                        key="r_city"
                    )

                    reg_hobbies = st.multiselect(
                        "İlgi Alanların (birden fazla seçebilirsin)",
                        HOBBY_OPTIONS,
                        key="r_hobbies"
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

                                signup_res = supabase.auth.sign_up(
                                    {
                                        "email": reg_email.strip().lower(),
                                        "password": reg_pass,
                                        "options": {
                                            "data": {
                                                "full_name": reg_name.strip(),
                                                "birth_date": str(reg_bdate),
                                                "gender": reg_gender,
                                                "city": reg_city,
                                                "hobbies": reg_hobbies
                                            }
                                        }
                                    }
                                )

                                identities = getattr(signup_res.user, "identities", None)

                                if signup_res.user and identities is not None and len(identities) == 0:

                                    st.warning(
                                        "Bu e-posta adresi zaten kayıtlı. "
                                        "Giriş yapmayı dener misin?"
                                    )

                                else:

                                    st.success("Kayıt başarılı! Giriş yapabilirsiniz.")

                            except Exception as e:

                                error_text = str(e).lower()

                                if "already registered" in error_text or "already exists" in error_text or "user_already_exists" in error_text:

                                    st.warning(
                                        "Bu e-posta adresi zaten kayıtlı. "
                                        "Giriş yapmayı dener misin?"
                                    )

                                else:

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

    if st.session_state.get("pending_remember_token"):

        token_to_save = st.session_state.pending_remember_token
        st.session_state.pending_remember_token = None

        set_browser_cookie(AUTH_COOKIE_NAME, token_to_save, days=30)

    # ========================================================
    # OTOMATİK GİRİŞ UYARISI
    # ========================================================

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
    # BELEDİYE HESABIYSA, TAMAMEN AYRI PANELİ GÖSTER VE DUR
    # ========================================================

    if st.session_state.get("municipality"):

        render_municipality_panel(st.session_state.municipality)
        st.stop()

    if st.session_state.get("business"):

        render_business_panel(st.session_state.business)
        st.stop()

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

            if st.button("📍 Etkinlikler", use_container_width=True):

                st.session_state.sayfa = "📍 Etkinlikler"
                st.rerun()

            if st.button("🏆 Puanlarım", use_container_width=True):

                st.session_state.sayfa = "🏆 Puanlarım"
                st.rerun()

            if st.button("🎁 Ödüller", use_container_width=True):

                st.session_state.sayfa = "🎁 Ödüller"
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
        # RUH HALİ SEÇİMİ (AI önerilerini kişiselleştirmek için)
        # ====================================================

        st.markdown("**Şu an nasıl hissediyorsun?**")

        mood_cols = st.columns(len(MOOD_OPTIONS))

        for mood_col, (mood_name, mood_emoji) in zip(mood_cols, MOOD_OPTIONS.items()):

            with mood_col:

                is_selected = st.session_state.mood == mood_name

                if st.button(
                    f"{mood_emoji} {mood_name}",
                    key=f"mood_{mood_name}",
                    type="primary" if is_selected else "secondary",
                    use_container_width=True
                ):

                    st.session_state.mood = mood_name
                    st.rerun()

        st.markdown("")

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
                            f"Kullanıcı adı: {display_name}. "
                            f"Yaşadığı şehir: {st.session_state.city}. "
                        )

                        if st.session_state.hobbies:

                            system_prompt += (
                                f"İlgi alanları: {', '.join(st.session_state.hobbies)}. "
                            )

                        if st.session_state.mood:

                            system_prompt += (
                                f"Şu anki ruh hali: {st.session_state.mood}. "
                                "Cevaplarını ve önerilerini bu ruh haline, "
                                "şehrine ve ilgi alanlarına göre kişiselleştir."
                            )

                        # -----------------------------------------------
                        # GERÇEK ETKİNLİKLERİ AI'A TANIT (YENİ)
                        # -----------------------------------------------
                        # Kullanıcının şehrindeki aktif etkinlikleri çekip,
                        # AI'ın bunlardan gerçek öneriler yapabilmesi için
                        # sistem promptuna ekliyoruz.

                        nearby_events = load_active_events(city=st.session_state.city)

                        if nearby_events:

                            events_text = "\n".join(
                                f"- {e['title']} | Kategori: {e.get('category', 'Belirtilmemiş')} | "
                                f"Tarih: {e['event_date']} {e['event_time']} | "
                                f"Yer: {e.get('address', e['city'])} | "
                                f"Katılım ödülü: {e.get('points_reward', 10)} puan"
                                for e in nearby_events[:15]
                            )

                            system_prompt += (
                                "\n\nKullanıcının şehrinde şu anda gerçekleşecek "
                                "gerçek etkinlikler var:\n"
                                f"{events_text}\n\n"
                                "Kullanıcının ruh haline ve ilgi alanlarına en uygun "
                                "olan 1-3 etkinliği isimleriyle, tarihleriyle ve "
                                "neden uygun olduğunu açıklayarak öner. Etkinlik "
                                "önerirken bu listede OLMAYAN bir etkinlik uydurma. "
                                "Kullanıcıya, etkinliğin tüm detaylarını ve katılım "
                                "onayını uygulamadaki '📍 Etkinlikler' sayfasından "
                                "görebileceğini hatırlat."
                            )

                        else:

                            system_prompt += (
                                "\n\nKullanıcının şehrinde şu an aktif bir etkinlik "
                                "bulunmuyor. Bunu nazikçe belirt ve genel bir "
                                "alışkanlık/motivasyon önerisi ver."
                            )

                        api_messages = [{"role": "system", "content": system_prompt}]

                        for msg in st.session_state.chats[chat_id]["messages"]:

                            api_messages.append(
                                {"role": msg["role"], "content": msg["content"]}
                            )

                        chat_completion = client.chat.completions.create(
                            messages=api_messages,
                            model="openai/gpt-oss-120b"
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
    # 8B. ETKİNLİKLER (YENİ)
    # ========================================================

    elif st.session_state.sayfa == "📍 Etkinlikler":

        deactivate_expired_events()

        st.title("📍 Yakınındaki Etkinlikler")

        show_only_my_city = st.checkbox(
            f"Sadece {st.session_state.city} şehrindekileri göster",
            value=True
        )

        events = load_active_events(
            city=st.session_state.city if show_only_my_city else None
        )

        if not events:

            st.info("Şu an aktif etkinlik bulunmuyor.")

        else:

            # -----------------------------------------------
            # LİSTE
            # -----------------------------------------------

            for event in events:

                with st.container(border=True):

                    col_info, col_action = st.columns([4, 1])

                    with col_info:

                        st.subheader(event["title"])
                        st.caption(
                            f"📅 {event['event_date']}  •  🕐 {event['event_time']}  •  "
                            f"📍 {event.get('address', event['city'])}"
                        )

                        if event.get("category"):

                            st.badge(event["category"])

                        if event.get("description"):

                            st.write(event["description"])

                        st.caption(f"🏆 Katılım ödülü: {event.get('points_reward', 10)} puan")

                    with col_action:

                        if st.button(
                            "Detay",
                            key=f"detay_{event['id']}",
                            use_container_width=True
                        ):

                            st.session_state.selected_event_id = event["id"]
                            st.session_state.sayfa = "📍 Etkinlik Detay"
                            st.rerun()

    # ========================================================
    # 8C. ETKİNLİK DETAY (YENİ)
    # ========================================================

    elif st.session_state.sayfa == "📍 Etkinlik Detay":

        # Bekleyen katılım bildirimini göster (QR/konum doğrulamasından sonra)
        if st.session_state.get("participation_notice"):

            notice_type, notice_text = st.session_state.participation_notice
            st.session_state.participation_notice = None

            if notice_type == "success":
                st.success(notice_text)
            elif notice_type == "info":
                st.info(notice_text)
            else:
                st.error(notice_text)

        event_id = st.session_state.get("selected_event_id")
        event = get_event_by_id(event_id) if event_id else None

        if st.button("← Etkinliklere dön"):

            st.session_state.sayfa = "📍 Etkinlikler"
            st.rerun()

        if not event:

            st.warning("Etkinlik bulunamadı.")

        else:

            st.title(event["title"])

            st.caption(
                f"📅 {event['event_date']}  •  🕐 {event['event_time']}  •  "
                f"📍 {event.get('address', event['city'])}"
            )

            if event.get("category"):

                st.badge(event["category"])

            st.markdown("---")

            if event.get("description"):

                st.write(event["description"])

            # -----------------------------------------------
            # HARİTA (sadece bu etkinliğin konumu)
            # -----------------------------------------------

            if event.get("latitude") and event.get("longitude"):

                st.map(pd.DataFrame(
                    [{"lat": event["latitude"], "lon": event["longitude"]}]
                ))

            st.markdown("---")

            already_joined = has_user_participated(st.session_state.user.id, event["id"])

            if already_joined:

                st.success("✅ Bu etkinliğe katılımın onaylanmış durumda.")

            else:

                st.info(f"🏆 Bu etkinliğe katılıp doğrulama yaparsan **{event.get('points_reward', 10)} puan** kazanırsın.")

                st.markdown("**Katılımını nasıl doğrulamak istersin?**")

                st.caption(
                    "📱 **QR ile:** Etkinlik alanında asılı QR kodu telefonunun "
                    "kamerasıyla okut, katılımın otomatik onaylanır."
                )

                st.caption("📍 **Konum ile:** Etkinlik alanındaysan aşağıdaki butona bas.")

                trigger_geolocation_participation(event["id"])

    # ========================================================
    # 8D. PUANLARIM (YENİ)
    # ========================================================

    elif st.session_state.sayfa == "🏆 Puanlarım":

        st.title("🏆 Puanlarım")

        total_points = get_user_total_points(st.session_state.user.id)

        st.metric("Toplam Puan", total_points)

        st.markdown("---")

        st.subheader("📜 Katılım Geçmişi")

        participations = load_user_participations(st.session_state.user.id)

        if not participations:

            st.info("Henüz hiçbir etkinliğe katılmadın.")

        else:

            for p in participations:

                event_info = p.get("events") or {}

                method_label = "📱 QR" if p.get("verification_method") == "qr" else "📍 Konum"

                with st.container(border=True):

                    st.write(f"**{event_info.get('title', 'Etkinlik')}**")
                    st.caption(
                        f"{event_info.get('event_date', '')}  •  "
                        f"{method_label} ile doğrulandı  •  "
                        f"🏆 +{p.get('points_earned', 0)} puan"
                    )

    # ========================================================
    # 8E. ÖDÜLLER (YENİ)
    # ========================================================

    elif st.session_state.sayfa == "🎁 Ödüller":

        st.title("🎁 Ödüller")

        current_points = get_user_total_points(st.session_state.user.id)

        st.metric("Kullanılabilir Puan", current_points)

        st.markdown("---")

        tab_available, tab_history = st.tabs(["🛍️ Mevcut Ödüller", "📜 Geçmiş Taleplerim"])

        # -----------------------------------------------
        # MEVCUT ÖDÜLLER
        # -----------------------------------------------

        with tab_available:

            rewards = load_active_rewards()

            if not rewards:

                st.info("Şu an aktif bir ödül bulunmuyor.")

            else:

                for reward in rewards:

                    business_info = reward.get("businesses") or {}

                    with st.container(border=True):

                        col_info, col_action = st.columns([4, 1.2])

                        with col_info:

                            st.subheader(reward["title"])
                            st.caption(
                                f"🏪 {business_info.get('name', 'İşletme')}  •  "
                                f"🏆 {reward['points_cost']} puan"
                            )

                            if reward.get("description"):

                                st.write(reward["description"])

                        with col_action:

                            can_afford = current_points >= reward["points_cost"]

                            if st.button(
                                "Talep Et",
                                key=f"redeem_{reward['id']}",
                                use_container_width=True,
                                disabled=not can_afford
                            ):

                                code = redeem_reward(
                                    st.session_state.user.id,
                                    reward["id"],
                                    reward["points_cost"]
                                )

                                if code:

                                    st.session_state.last_redemption_code = code
                                    st.session_state.last_redemption_title = reward["title"]
                                    st.rerun()

        if st.session_state.get("last_redemption_code"):

            st.success(
                f"🎉 **{st.session_state.get('last_redemption_title')}** talep edildi! "
                f"İşletmede şu kodu göster:"
            )

            st.markdown(
                f"<h1 style='text-align:center;letter-spacing:0.3em;'>"
                f"{st.session_state.last_redemption_code}</h1>",
                unsafe_allow_html=True
            )

            if st.button("Kapat"):

                st.session_state.last_redemption_code = None
                st.session_state.last_redemption_title = None
                st.rerun()

        # -----------------------------------------------
        # GEÇMİŞ TALEPLERİM
        # -----------------------------------------------

        with tab_history:

            redemptions = load_user_redemptions(st.session_state.user.id)

            if not redemptions:

                st.info("Henüz hiç ödül talep etmedin.")

            else:

                for r in redemptions:

                    reward_info = r.get("rewards") or {}
                    business_info = (reward_info.get("businesses") or {})

                    used_label = "✅ Kullanıldı" if r.get("used") else "⏳ Bekliyor"

                    with st.container(border=True):

                        st.write(f"**{reward_info.get('title', 'Ödül')}** — {used_label}")
                        st.caption(
                            f"🏪 {business_info.get('name', '')}  •  "
                            f"Kod: {r.get('redemption_code', '')}  •  "
                            f"🏆 {reward_info.get('points_cost', 0)} puan"
                        )

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

            # -----------------------------------------------
            # ŞEHİR
            # -----------------------------------------------

            if st.session_state.city in TURKISH_CITIES:

                current_city_idx = TURKISH_CITIES.index(st.session_state.city)

            else:

                current_city_idx = TURKISH_CITIES.index("İstanbul")

            new_city = st.selectbox("Yaşadığın Şehir", TURKISH_CITIES, index=current_city_idx)

            # -----------------------------------------------
            # İLGİ ALANLARI
            # -----------------------------------------------

            new_hobbies = st.multiselect(
                "İlgi Alanların",
                HOBBY_OPTIONS,
                default=[h for h in st.session_state.hobbies if h in HOBBY_OPTIONS]
            )

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
                                "gender": new_gender,
                                "city": new_city,
                                "hobbies": new_hobbies
                            }
                        }
                    )

                    if hasattr(update_result, "session") and update_result.session:

                        st.session_state.access_token = update_result.session.access_token
                        st.session_state.refresh_token = update_result.session.refresh_token

                    st.session_state.profile_name = new_name.strip()
                    st.session_state.birth_date = str(new_bdate)
                    st.session_state.gender = new_gender
                    st.session_state.city = new_city
                    st.session_state.hobbies = new_hobbies

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