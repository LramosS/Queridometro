import io
import html
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import streamlit as st
import extra_streamlit_components as stx
from PIL import Image
from streamlit_cropper import st_cropper
from supabase import create_client


# ==================================================
# CONFIGURAÇÃO GERAL
# ==================================================

st.set_page_config(
    page_title="Queridômetro",
    page_icon="🎭",
    layout="centered",
)

TIMEZONE = ZoneInfo("America/Sao_Paulo")

VOTING_START = time(9, 0)
VOTING_END = time(18, 0)

MIN_PARTICIPANTS_FOR_RESULTS = 10

REMEMBER_COOKIE = "queridometro_refresh_token"
LEGACY_EMAIL_COOKIE = "queridometro_email"
COOKIE_DAYS = 365

PHOTO_BUCKET = "profile-photos"

ADMIN_EMAILS = {
    "lucasramoseconomia@gmail.com"
}

# ==================================================
# MODO DE TESTE VISUAL DO MATCH 🔥
# ==================================================
# ATENÇÃO: mantenha True apenas no teste local.
# Antes de publicar, altere para False.
FIRE_TEST_MODE = False
FIRE_TEST_MATCH_NAME = "Andressa"


# ==================================================
# EMOJIS
# ==================================================

EMOJI_OPTIONS = {
    "❤️": {
        "name": "Coração",
        "description": (
            "Pessoa querida, acolhedora ou com quem "
            "a interação foi especialmente positiva."
        ),
    },
    "🌱": {
        "name": "Planta",
        "description": (
            "Pessoa mais quieta, discreta ou que "
            "passou mais despercebida no dia."
        ),
    },
    "🔥": {
        "name": "Foguinho",
        "description": (
            "Pessoa animada, intensa ou que "
            "movimentou o ambiente."
        ),
    },
    "🐍": {
        "name": "Cobrinha",
        "description": (
            "Pessoa que teve uma atitude atravessada, "
            "provocativa ou pouco legal."
        ),
    },
    "🧳": {
        "name": "Mala",
        "description": (
            "Pessoa que esteve chata, cansativa "
            "ou difícil de lidar."
        ),
    },
    "🤝": {
        "name": "Parceria",
        "description": (
            "Pessoa colaborativa, disponível ou "
            "que somou com você ou com o grupo."
        ),
    },
    "😐": {
        "name": "Não interage",
        "description": (
            "Você praticamente não interagiu "
            "com essa pessoa no dia."
        ),
    },
    "🦚": {
        "name": "Pavão",
        "description": (
            "Pessoa que parece estar querendo "
            "chamar atenção ou aparecer."
        ),
    },
    "🍻": {
        "name": "Bora tomar uma?",
        "description": (
            "Pessoa com quem você toparia "
            "esticar a conversa depois do expediente."
        ),
    },
}

FRIDAY_EMOJI = "🍻"

BASE_EMOJIS = [
    "❤️",
    "🌱",
    "🔥",
    "🐍",
    "🧳",
    "🤝",
    "😐",
    "🦚",
]

COUNTED_EMOJIS = BASE_EMOJIS + [FRIDAY_EMOJI]

# Emojis que formam a cartela do BINGO.
# 😐 Não interage e 🍻 Bora tomar uma? ficam de fora.
BINGO_EMOJIS = [
    "❤️",
    "🌱",
    "🔥",
    "🐍",
    "🧳",
    "🤝",
    "🦚",
]


def is_friday():
    return today_br().weekday() == 4


# ==================================================
# SUPABASE
# ==================================================

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"],
)


def get_auth_client():
    """
    Cria um cliente Supabase isolado por sessão do Streamlit.
    Esse cliente é usado exclusivamente para autenticação.
    """
    if "auth_client" not in st.session_state:
        st.session_state.auth_client = create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_KEY"],
        )

    return st.session_state.auth_client


# ==================================================
# COOKIE
# ==================================================

cookie_manager = stx.CookieManager()


# ==================================================
# PROTEÇÃO CONTRA TRADUÇÃO AUTOMÁTICA
# ==================================================

st.markdown(
    """
    <meta name="google" content="notranslate">
    <script>
        document.documentElement.lang = "pt-BR";
        document.documentElement.setAttribute("translate", "no");
    </script>
    """,
    unsafe_allow_html=True,
)


# ==================================================
# ESTADO DA SESSÃO
# ==================================================

DEFAULT_SESSION = {
    "user_email": None,
    "user_id": None,
    "user_name": None,
    "profile_photo_url": None,
    "auth_email": None,
    "auth_otp_sent": False,
    "auth_access_token": None,
    "auth_refresh_token": None,
    "remember_device": False,
    "remember_device_choice": False,
    "page": "home",
    "votes": {},
    "friday_beer_votes": {},
    "current_vote_index": 0,
    "confirm_submission": False,
    "confirm_remove_photo": False,
    "photo_uploader_version": 0,
    "bingo_seen_key": None,
}

for key, value in DEFAULT_SESSION.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ==================================================
# DATA E HORÁRIO
# ==================================================

def now_br():
    return datetime.now(TIMEZONE)


def today_br():
    return now_br().date()


def get_week_id(date_value=None):
    if date_value is None:
        date_value = today_br()

    iso = date_value.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def get_week_dates(date_value=None):
    if date_value is None:
        date_value = today_br()

    monday = date_value - timedelta(
        days=date_value.weekday()
    )

    sunday = monday + timedelta(days=6)

    return monday, sunday


def is_friday(date_value=None):
    if date_value is None:
        date_value = today_br()

    return date_value.weekday() == 4


def voting_status():
    current_time = now_br().time()

    if current_time < VOTING_START:
        return "before"

    if current_time >= VOTING_END:
        return "closed"

    return "open"


def voting_status_label():
    status = voting_status()

    if status == "before":
        return "⏰ Ainda não abriu"

    if status == "open":
        return "🟢 Votação aberta"

    return "🔒 Votação encerrada"


def parse_supabase_datetime(value):
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=TIMEZONE)

        return parsed.astimezone(TIMEZONE)

    except Exception:
        return None


# ==================================================
# ADMIN
# ==================================================

def is_admin():
    return (
        st.session_state.user_email
        in ADMIN_EMAILS
    )


# ==================================================
# MODO DE MANUTENÇÃO
# ==================================================

def get_maintenance_mode():
    try:
        response = (
            supabase
            .table("app_settings")
            .select("setting_value")
            .eq(
                "setting_key",
                "maintenance_mode",
            )
            .limit(1)
            .execute()
        )

        if not response.data:
            return False

        value = str(
            response.data[0]["setting_value"]
        ).strip().lower()

        return value == "true"

    except Exception:
        return False


def set_maintenance_mode(enabled):
    try:
        (
            supabase
            .table("app_settings")
            .update(
                {
                    "setting_value": (
                        "true"
                        if enabled
                        else "false"
                    ),
                    "updated_at": now_br().isoformat(),
                }
            )
            .eq(
                "setting_key",
                "maintenance_mode",
            )
            .execute()
        )

        return True

    except Exception as error:
        st.error(
            "Não foi possível alterar "
            "o modo de manutenção."
        )
        st.code(str(error))
        return False


def show_maintenance_screen():
    st.title("🎭 Queridômetro")

    st.warning(
        "🔧 Estamos fazendo uma atualização rápida."
    )

    st.write(
        "O Queridômetro está temporariamente "
        "pausado para manutenção."
    )

    st.write(
        "Tente novamente em alguns minutos."
    )

    st.caption(
        "Atualize esta página quando "
        "a manutenção terminar."
    )

    st.divider()

    if st.button(
        "Sair",
        use_container_width=True,
    ):
        logout()


# ==================================================
# PARTICIPANTES
# ==================================================

@st.cache_data(ttl=60)
def load_participants():
    response = (
        supabase
        .table("participants")
        .select(
            "id,name,email,photo_url,active"
        )
        .eq("active", True)
        .order("name")
        .execute()
    )

    participants = {}

    for row in response.data:
        email = row["email"].strip().lower()

        participants[email] = {
            "id": row["id"],
            "name": row["name"],
            "email": email,
            "photo_url": row["photo_url"],
            "active": row["active"],
        }

    return participants


def ensure_authenticated_client():
    """
    Reassocia o cliente Supabase isolado à sessão autenticada
    do usuário atual e atualiza os tokens caso haja renovação.
    Se o dispositivo estiver marcado para ser lembrado, também
    atualiza o refresh token persistido no cookie.
    """
    access_token = st.session_state.get("auth_access_token")
    refresh_token = st.session_state.get("auth_refresh_token")

    if not access_token or not refresh_token:
        return None

    auth_client = get_auth_client()

    try:
        auth_response = auth_client.auth.set_session(
            access_token,
            refresh_token,
        )

        session = getattr(auth_response, "session", None)

        if session:
            st.session_state.auth_access_token = session.access_token
            st.session_state.auth_refresh_token = session.refresh_token

            if st.session_state.get("remember_device"):
                save_login_cookie(session.refresh_token)

        return auth_client

    except Exception:
        return None


def get_pending_fire_matches():
    """
    Consulta somente os matches do usuário autenticado que ainda
    não foram confirmados. O Tinder do Foguinho funciona apenas
    às sextas-feiras; o RPC também limita a janela a 18h-19h.
    """
    if not is_friday():
        return []

    auth_client = ensure_authenticated_client()

    if auth_client is None:
        return []

    try:
        response = (
            auth_client
            .rpc("get_my_pending_fire_matches")
            .execute()
        )

        matches = []

        for row in (response.data or []):
            participant_id = row.get("matched_participant_id")

            if participant_id:
                matches.append(str(participant_id))

        return matches

    except Exception:
        # A surpresa nunca deve derrubar o restante do app.
        return []


def get_participant_name_by_id(participant_id):
    participants = load_participants()

    for participant in participants.values():
        if str(participant["id"]) == str(participant_id):
            return participant["name"]

    return None


def acknowledge_fire_match(matched_participant_id):
    auth_client = ensure_authenticated_client()

    if auth_client is None:
        return False

    try:
        response = (
            auth_client
            .rpc(
                "ack_my_fire_match",
                {
                    "p_matched_participant_id": (
                        matched_participant_id
                    )
                },
            )
            .execute()
        )

        return bool(response.data)

    except Exception:
        return False


def show_fire_match_surprise(matched_participant_id):
    matched_name = get_participant_name_by_id(
        matched_participant_id
    )

    if not matched_name:
        return False

    safe_name = html.escape(matched_name)

    st.title("🔥 Deu match!")

    st.markdown(
        (
            '<div style="'
            'padding:22px 18px;'
            'border-radius:16px;'
            'background-color:rgba(255,99,71,0.12);'
            'text-align:center;'
            'margin:12px 0 18px 0;'
            '">'
            '<div style="font-size:42px;margin-bottom:8px;">🔥</div>'
            '<div style="font-size:18px;line-height:1.5;">'
            'Você e <strong>'
            f'{safe_name}'
            '</strong> trocaram Foguinho hoje.'
            '</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )

    st.write(
        "Vocês tiveram algo em comum. 👀 "
        "O Queridômetro só mostra matches recíprocos."
    )

    st.caption(
        "Essa surpresa fica disponível apenas entre 18h e 19h "
        "e não entra no histórico."
    )

    if st.button(
        "Entendi 🔥",
        type="primary",
        use_container_width=True,
        key=f"ack_fire_{matched_participant_id}",
    ):
        if acknowledge_fire_match(matched_participant_id):
            st.rerun()
        else:
            st.error(
                "Não foi possível concluir a visualização agora. "
                "Tente novamente."
            )

    return True


def show_fire_match_test_preview():
    """
    Prévia visual local do match.

    Não consulta nem grava nada no Supabase e só aparece para
    administradores quando FIRE_TEST_MODE = True. Serve apenas
    para validar a experiência visual antes da publicação.
    """
    safe_name = html.escape(FIRE_TEST_MATCH_NAME)

    st.caption("🧪 MODO DE TESTE LOCAL")
    st.title("🔥 Deu match!")

    st.markdown(
        (
            '<div style="'
            'padding:22px 18px;'
            'border-radius:16px;'
            'background-color:rgba(255,99,71,0.12);'
            'text-align:center;'
            'margin:12px 0 18px 0;'
            '">'
            '<div style="font-size:42px;margin-bottom:8px;">🔥</div>'
            '<div style="font-size:18px;line-height:1.5;">'
            'Você e <strong>'
            f'{safe_name}'
            '</strong> trocaram Foguinho hoje.'
            '</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )

    st.write(
        "Vocês tiveram algo em comum. 👀 "
        "O Queridômetro só mostra matches recíprocos."
    )

    st.caption(
        "Na versão real, esta surpresa fica disponível apenas "
        "entre 18h e 19h e não entra no histórico."
    )

    if st.button(
        "Entendi 🔥",
        type="primary",
        use_container_width=True,
        key="ack_fire_test_preview",
    ):
        st.session_state.fire_test_preview_dismissed = True
        st.rerun()

    st.info(
        "Esta é apenas uma prévia visual local. "
        "Nenhum match, voto ou recibo foi criado no banco."
    )

    return True


def login_authenticated_user(auth_user):
    """
    Vincula o usuário autenticado do Supabase Auth ao participante
    correspondente por auth_user_id.
    """
    if not auth_user:
        return False

    auth_user_id = str(auth_user.id)
    auth_client = get_auth_client()

    try:
        response = (
            auth_client
            .table("participants")
            .select(
                "id,name,email,photo_url,active,auth_user_id"
            )
            .eq(
                "auth_user_id",
                auth_user_id,
            )
            .eq(
                "active",
                True,
            )
            .limit(1)
            .execute()
        )

        if not response.data:
            return False

        participant = response.data[0]

        st.session_state.user_email = (
            participant["email"]
            .strip()
            .lower()
        )
        st.session_state.user_id = participant["id"]
        st.session_state.user_name = participant["name"]
        st.session_state.profile_photo_url = (
            participant["photo_url"]
        )

        st.session_state.page = "home"
        st.session_state.current_vote_index = 0

        return True

    except Exception as error:
        st.error(
            "Não foi possível localizar "
            "seu cadastro no Queridômetro."
        )
        st.code(str(error))
        return False


def get_voting_list():
    participants = load_participants()

    return [
        email
        for email in participants
        if email != st.session_state.user_email
    ]


# ==================================================
# LOGIN
# ==================================================

def login_user(email):
    participants = load_participants()

    email = email.strip().lower()

    if email not in participants:
        return False

    participant = participants[email]

    st.session_state.user_email = email
    st.session_state.user_id = participant["id"]
    st.session_state.user_name = participant["name"]
    st.session_state.profile_photo_url = (
        participant["photo_url"]
    )

    st.session_state.page = "home"
    st.session_state.current_vote_index = 0

    return True


def get_saved_refresh_token():
    """Lê o refresh token salvo neste navegador, se houver."""
    saved_token = None

    try:
        saved_token = st.context.cookies.get(REMEMBER_COOKIE)
    except Exception:
        pass

    if not saved_token:
        try:
            saved_token = cookie_manager.get(
                cookie=REMEMBER_COOKIE
            )
        except Exception:
            saved_token = None

    return str(saved_token) if saved_token else None


def save_login_cookie(refresh_token):
    """Persiste somente o refresh token do Supabase neste navegador."""
    if not refresh_token:
        return False

    try:
        expiration = datetime.now() + timedelta(days=COOKIE_DAYS)

        cookie_manager.set(
            REMEMBER_COOKIE,
            refresh_token,
            expires_at=expiration,
            key="set_queridometro_refresh_token",
        )

        return True

    except Exception:
        return False


def delete_login_cookie():
    """Remove o cookie atual e também o cookie antigo de e-mail."""
    for cookie_name, key_name in (
        (REMEMBER_COOKIE, "delete_queridometro_refresh_token"),
        (LEGACY_EMAIL_COOKIE, "delete_queridometro_legacy_email"),
    ):
        try:
            cookie_manager.delete(
                cookie=cookie_name,
                key=key_name,
            )
        except Exception:
            pass


def try_persistent_login():
    """
    Tenta restaurar a sessão do Supabase usando o refresh token
    persistido no navegador. Se funcionar, entra sem novo OTP e
    grava imediatamente o refresh token rotacionado.
    """
    if st.session_state.user_email is not None:
        return True

    refresh_token = get_saved_refresh_token()

    if not refresh_token:
        return False

    auth_client = get_auth_client()

    try:
        response = auth_client.auth.refresh_session(refresh_token)
        session = getattr(response, "session", None)
        user = getattr(response, "user", None)

        if not session or not user:
            delete_login_cookie()
            return False

        st.session_state.auth_access_token = session.access_token
        st.session_state.auth_refresh_token = session.refresh_token
        st.session_state.remember_device = True

        if not login_authenticated_user(user):
            delete_login_cookie()
            return False

        # Refresh tokens podem ser rotacionados a cada renovação.
        # Guardamos imediatamente o token novo.
        save_login_cookie(session.refresh_token)
        return True

    except Exception:
        delete_login_cookie()
        return False


def logout():
    try:
        auth_client = get_auth_client()
        auth_client.auth.sign_out()
    except Exception:
        pass

    delete_login_cookie()

    for key, value in DEFAULT_SESSION.items():
        st.session_state[key] = value

    if "auth_client" in st.session_state:
        del st.session_state["auth_client"]

    st.rerun()


# ==================================================
# FOTO
# ==================================================

def image_to_bytes(image):
    buffer = io.BytesIO()

    image = image.convert("RGB")

    image.save(
        buffer,
        format="JPEG",
        quality=90,
        optimize=True,
    )

    return buffer.getvalue()


def get_photo_path():
    return (
        f"{st.session_state.user_id}/avatar.jpg"
    )


def save_profile_photo(image):
    photo_bytes = image_to_bytes(image)
    photo_path = get_photo_path()

    try:
        (
            supabase.storage
            .from_(PHOTO_BUCKET)
            .upload(
                path=photo_path,
                file=photo_bytes,
                file_options={
                    "content-type": "image/jpeg",
                    "cache-control": "3600",
                    "upsert": "true",
                },
            )
        )

        base_public_url = (
            supabase.storage
            .from_(PHOTO_BUCKET)
            .get_public_url(photo_path)
        )

        version = now_br().strftime(
            "%Y%m%d%H%M%S%f"
        )

        public_url = (
            f"{base_public_url}?v={version}"
        )

        (
            supabase
            .table("participants")
            .update(
                {
                    "photo_url": public_url
                }
            )
            .eq(
                "id",
                st.session_state.user_id,
            )
            .execute()
        )

        st.session_state.profile_photo_url = (
            public_url
        )

        st.session_state.confirm_remove_photo = False
        st.session_state.photo_uploader_version += 1

        load_participants.clear()

        return True

    except Exception as error:
        st.error(
            "Não foi possível salvar a foto."
        )
        st.code(str(error))
        return False


def remove_profile_photo():
    photo_path = get_photo_path()

    try:
        (
            supabase.storage
            .from_(PHOTO_BUCKET)
            .remove([photo_path])
        )

        (
            supabase
            .table("participants")
            .update(
                {
                    "photo_url": None
                }
            )
            .eq(
                "id",
                st.session_state.user_id,
            )
            .execute()
        )

        st.session_state.profile_photo_url = None
        st.session_state.confirm_remove_photo = False
        st.session_state.photo_uploader_version += 1

        load_participants.clear()

        return True

    except Exception as error:
        st.error(
            "Não foi possível remover a foto."
        )
        st.code(str(error))
        return False


# ==================================================
# NOMES
# ==================================================

def show_name(name, tag="h2"):
    safe_name = html.escape(name)

    name_html = (
        f'<{tag} '
        'translate="no" '
        'class="notranslate" '
        'style="text-align:center;">'
        f'{safe_name}'
        f'</{tag}>'
    )

    st.markdown(
        name_html,
        unsafe_allow_html=True,
    )


# ==================================================
# CENTRAL DE COMUNICADOS
# ==================================================

def load_announcements():
    try:
        response = (
            supabase
            .table("app_announcements")
            .select(
                "id,version,title,message,status,"
                "scheduled_at,published_at,"
                "created_at,updated_at"
            )
            .order(
                "created_at",
                desc=False,
            )
            .execute()
        )

        return response.data or []

    except Exception:
        return []


def announcement_already_seen(
    announcement_id,
):
    try:
        response = (
            supabase
            .table("announcement_views")
            .select("id")
            .eq(
                "announcement_id",
                announcement_id,
            )
            .eq(
                "participant_id",
                st.session_state.user_id,
            )
            .limit(1)
            .execute()
        )

        return len(response.data) > 0

    except Exception:
        return False


def mark_announcement_as_seen(
    announcement_id,
):
    try:
        (
            supabase
            .table("announcement_views")
            .upsert(
                {
                    "announcement_id": (
                        announcement_id
                    ),
                    "participant_id": (
                        st.session_state.user_id
                    ),
                    "viewed_at": (
                        now_br().isoformat()
                    ),
                },
                on_conflict=(
                    "announcement_id,"
                    "participant_id"
                ),
            )
            .execute()
        )

        return True

    except Exception as error:
        st.error(
            "Não foi possível concluir "
            "a leitura da mensagem."
        )
        st.code(str(error))
        return False


def announcement_is_available(
    announcement,
):
    status = announcement.get("status")

    if status == "published":
        return True

    if status == "scheduled":
        scheduled_at = parse_supabase_datetime(
            announcement.get("scheduled_at")
        )

        if (
            scheduled_at
            and scheduled_at <= now_br()
        ):
            return True

    return False


def get_pending_announcement_for_user():
    if not st.session_state.user_id:
        return None

    announcements = load_announcements()

    for announcement in announcements:

        if not announcement_is_available(
            announcement
        ):
            continue

        if not announcement_already_seen(
            announcement["id"]
        ):
            return announcement

    return None


def show_announcement(
    announcement,
):
    version = announcement.get("version")

    if version:
        st.caption(
            f"Versão {version}"
        )

    st.title(
        announcement["title"]
    )

    st.markdown(
        announcement["message"]
    )

    st.divider()

    if st.button(
        "Entendi",
        type="primary",
        use_container_width=True,
        key=(
            f"announcement_understood_"
            f"{announcement['id']}"
        ),
    ):
        if mark_announcement_as_seen(
            announcement["id"]
        ):
            st.rerun()


def get_announcement_view_count(
    announcement_id,
):
    try:
        response = (
            supabase
            .table("announcement_views")
            .select("id")
            .eq(
                "announcement_id",
                announcement_id,
            )
            .execute()
        )

        return len(response.data)

    except Exception:
        return 0


def save_announcement_draft(
    version,
    title,
    message,
):
    try:
        (
            supabase
            .table("app_announcements")
            .insert(
                {
                    "version": (
                        version.strip()
                        if version.strip()
                        else None
                    ),
                    "title": title.strip(),
                    "message": message.strip(),
                    "status": "draft",
                    "scheduled_at": None,
                    "published_at": None,
                    "updated_at": (
                        now_br().isoformat()
                    ),
                }
            )
            .execute()
        )

        return True

    except Exception as error:
        st.error(
            "Não foi possível salvar "
            "o rascunho."
        )
        st.code(str(error))
        return False


def publish_announcement(
    version,
    title,
    message,
):
    try:
        (
            supabase
            .table("app_announcements")
            .insert(
                {
                    "version": (
                        version.strip()
                        if version.strip()
                        else None
                    ),
                    "title": title.strip(),
                    "message": message.strip(),
                    "status": "published",
                    "scheduled_at": None,
                    "published_at": (
                        now_br().isoformat()
                    ),
                    "updated_at": (
                        now_br().isoformat()
                    ),
                }
            )
            .execute()
        )

        return True

    except Exception as error:
        st.error(
            "Não foi possível publicar "
            "a mensagem."
        )
        st.code(str(error))
        return False


def schedule_announcement(
    version,
    title,
    message,
    scheduled_at,
):
    try:
        (
            supabase
            .table("app_announcements")
            .insert(
                {
                    "version": (
                        version.strip()
                        if version.strip()
                        else None
                    ),
                    "title": title.strip(),
                    "message": message.strip(),
                    "status": "scheduled",
                    "scheduled_at": (
                        scheduled_at.isoformat()
                    ),
                    "published_at": None,
                    "updated_at": (
                        now_br().isoformat()
                    ),
                }
            )
            .execute()
        )

        return True

    except Exception as error:
        st.error(
            "Não foi possível agendar "
            "a mensagem."
        )
        st.code(str(error))
        return False


def update_announcement_schedule(
    announcement_id,
    scheduled_at,
):
    try:
        (
            supabase
            .table("app_announcements")
            .update(
                {
                    "scheduled_at": scheduled_at.isoformat(),
                    "status": "scheduled",
                    "updated_at": now_br().isoformat(),
                }
            )
            .eq(
                "id",
                announcement_id,
            )
            .execute()
        )

        return True

    except Exception as error:
        st.error(
            "Não foi possível alterar "
            "o agendamento."
        )
        st.code(str(error))
        return False


def deactivate_announcement(
    announcement_id,
):
    try:
        (
            supabase
            .table("app_announcements")
            .update(
                {
                    "status": "inactive",
                    "updated_at": (
                        now_br().isoformat()
                    ),
                }
            )
            .eq(
                "id",
                announcement_id,
            )
            .execute()
        )

        return True

    except Exception as error:
        st.error(
            "Não foi possível desativar "
            "a mensagem."
        )
        st.code(str(error))
        return False


def format_announcement_version(
    announcement,
):
    version = announcement.get("version")

    if version:
        return f" • versão {version}"

    return ""


# ==================================================
# PARTICIPAÇÃO DIÁRIA
# ==================================================

def has_voted_today():
    if not st.session_state.user_id:
        return False

    response = (
        supabase
        .table("daily_participation")
        .select("id")
        .eq(
            "participant_id",
            st.session_state.user_id,
        )
        .eq(
            "vote_date",
            today_br().isoformat(),
        )
        .limit(1)
        .execute()
    )

    return len(response.data) > 0


def get_participation_count(date_value):
    response = (
        supabase
        .table("daily_participation")
        .select("id")
        .eq(
            "vote_date",
            date_value.isoformat(),
        )
        .execute()
    )

    return len(response.data)


def get_today_participation_count():
    return get_participation_count(
        today_br()
    )


def results_are_unlocked(date_value):
    return (
        get_participation_count(date_value)
        >= MIN_PARTICIPANTS_FOR_RESULTS
    )


def get_eligible_result_dates(
    start_date,
    end_date,
):
    response = (
        supabase
        .table("daily_participation")
        .select("vote_date")
        .gte(
            "vote_date",
            start_date.isoformat(),
        )
        .lte(
            "vote_date",
            end_date.isoformat(),
        )
        .execute()
    )

    counts = {}

    for row in (response.data or []):
        vote_date = row.get("vote_date")

        if vote_date:
            counts[vote_date] = (
                counts.get(vote_date, 0)
                + 1
            )

    return {
        vote_date
        for vote_date, count in counts.items()
        if count >= MIN_PARTICIPANTS_FOR_RESULTS
    }


def get_today_votes_count():
    response = (
        supabase
        .table("votes")
        .select("id")
        .eq(
            "vote_date",
            today_br().isoformat(),
        )
        .execute()
    )

    return len(response.data)


# ==================================================
# LOGIN
# ==================================================

def show_login():
    st.title(
        "🎭 Queridômetro"
    )

    st.write(
        "Bem-vinde ao Queridômetro"
    )

    auth_client = get_auth_client()

    # ==================================================
    # ETAPA 1: E-MAIL
    # ==================================================

    if not st.session_state.auth_otp_sent:

        email = st.text_input(
            "Digite seu e-mail",
            placeholder="nome@email.com",
            key="auth_login_email",
        )

        st.checkbox(
            "Lembrar neste dispositivo",
            key="remember_device",
            help=(
                "Mantém sua sessão neste navegador para que você "
                "não precise pedir um novo código a cada visita. "
                "Use apenas em um dispositivo pessoal ou confiável."
            ),
        )

        if st.button(
            "Receber código",
            type="primary",
            use_container_width=True,
        ):

            email = (
                email
                .strip()
                .lower()
            )

            if not email:
                st.warning(
                    "Digite seu e-mail "
                    "para continuar."
                )
                return

            participants = load_participants()

            if email not in participants:
                st.error(
                    "Este e-mail não está "
                    "cadastrado no Queridômetro."
                )
                return

            try:
                auth_client.auth.sign_in_with_otp(
                    {
                        "email": email,
                        "options": {
                            "should_create_user": False,
                        },
                    }
                )

                st.session_state.auth_email = email
                st.session_state.auth_otp_sent = True

                # Guarda a escolha fora do widget.
                # O checkbox deixa de existir na etapa do OTP e,
                # sem esta cópia, o Streamlit pode perder o valor.
                st.session_state.remember_device_choice = bool(
                    st.session_state.get(
                        "remember_device",
                        False,
                    )
                )

                st.success(
                    "Código enviado para seu e-mail."
                )
                st.rerun()

            except Exception as error:
                st.error(
                    "Não foi possível enviar "
                    "o código de acesso."
                )
                st.code(str(error))

    # ==================================================
    # ETAPA 2: CÓDIGO OTP
    # ==================================================

    else:
        st.success(
            "📨 Enviamos um código para:"
        )

        safe_email = html.escape(
            st.session_state.auth_email or ""
        )

        st.markdown(
            f"**{safe_email}**"
        )

        otp_code = st.text_input(
            "Digite o código recebido",
            placeholder="Digite o código recebido por e-mail",
            max_chars=8,
            key="auth_otp_code",
        )

        if st.button(
            "Entrar",
            type="primary",
            use_container_width=True,
        ):

            otp_code = otp_code.strip()

            if not otp_code:
                st.warning(
                    "Digite o código recebido."
                )
                return

            try:
                response = (
                    auth_client
                    .auth
                    .verify_otp(
                        {
                            "email": (
                                st.session_state.auth_email
                            ),
                            "token": otp_code,
                            "type": "email",
                        }
                    )
                )

                if (
                    not response
                    or not response.user
                    or not response.session
                ):
                    st.error(
                        "Não foi possível validar "
                        "o código."
                    )
                    return

                st.session_state.auth_access_token = (
                    response.session.access_token
                )
                st.session_state.auth_refresh_token = (
                    response.session.refresh_token
                )

                # Primeiro conclui o login dentro do app.
                # O OTP é de uso único; não podemos depender de
                # uma segunda tentativa para terminar esta etapa.
                if not login_authenticated_user(
                    response.user
                ):
                    st.error(
                        "Usuário autenticado, "
                        "mas sem participante vinculado."
                    )
                    return

                # Só depois de o usuário já estar identificado no app
                # persistimos (ou removemos) a sessão do navegador.
                remember_choice = bool(
                    st.session_state.get(
                        "remember_device_choice",
                        False,
                    )
                )

                st.session_state.remember_device = remember_choice

                if remember_choice:
                    save_login_cookie(
                        response.session.refresh_token
                    )
                else:
                    delete_login_cookie()

                st.session_state.auth_otp_sent = False
                st.session_state.auth_email = None

                st.rerun()

            except Exception as error:
                st.error(
                    "Código inválido ou expirado."
                )
                st.code(str(error))

        st.divider()

        if st.button(
            "← Usar outro e-mail",
            use_container_width=True,
        ):
            st.session_state.auth_email = None
            st.session_state.auth_otp_sent = False
            st.rerun()

        if st.button(
            "Reenviar código",
            use_container_width=True,
        ):
            try:
                auth_client.auth.sign_in_with_otp(
                    {
                        "email": (
                            st.session_state.auth_email
                        ),
                        "options": {
                            "should_create_user": False,
                        },
                    }
                )

                st.success(
                    "Novo código enviado."
                )

            except Exception as error:
                st.error(
                    "Não foi possível reenviar "
                    "o código."
                )
                st.code(str(error))


# ==================================================
# NAVEGAÇÃO
# ==================================================

def show_navigation():
    options = [
        "🏠 Hoje",
        "📊 Resultados",
        "🗓️ Histórico",
        "📖 Emojis",
        "👤 Perfil",
    ]

    page_map = {
        "🏠 Hoje": "home",
        "📊 Resultados": "results",
        "🗓️ Histórico": "history",
        "📖 Emojis": "emojis",
        "👤 Perfil": "profile",
    }

    if is_admin():
        options.append(
            "⚙️ Manutenção"
        )

        page_map[
            "⚙️ Manutenção"
        ] = "maintenance"

    reverse_map = {
        value: key
        for key, value
        in page_map.items()
    }

    current_page = (
        st.session_state.page
    )

    current_label = reverse_map.get(
        current_page,
        "🏠 Hoje",
    )

    index = (
        options.index(current_label)
        if current_label in options
        else 0
    )

    selected = st.radio(
        "Navegação",
        options,
        index=index,
        horizontal=True,
        label_visibility="collapsed",
        key="main_navigation",
    )

    selected_page = (
        page_map[selected]
    )

    if (
        selected_page
        != st.session_state.page
    ):
        st.session_state.page = (
            selected_page
        )
        st.rerun()

    st.divider()


# ==================================================
# HOME
# ==================================================

def show_home():
    status = voting_status()
    already_voted = has_voted_today()

    st.title(
        "🎭 Queridômetro"
    )

    safe_user_name = html.escape(
        st.session_state.user_name
    )

    greeting_html = (
        '<div '
        'translate="no" '
        'class="notranslate" '
        'style="'
        'padding:14px 16px;'
        'border-radius:8px;'
        'background-color:rgba(40,167,69,0.18);'
        'margin-bottom:16px;'
        '">'
        'Olá, '
        '<strong>'
        f'{safe_user_name}'
        '</strong>!'
        '</div>'
    )

    st.markdown(
        greeting_html,
        unsafe_allow_html=True,
    )

    st.caption(
        today_br().strftime(
            "%d/%m/%Y"
        )
    )

    if status == "before":

        st.info(
            "⏰ A votação de hoje "
            "abre às 09h."
        )

    elif status == "open":

        st.success(
            "🟢 Votação aberta até 18h."
        )

        if already_voted:

            st.success(
                "✅ Você já participou hoje."
            )

            st.caption(
                "Os resultados de hoje serão liberados "
                f"quando {MIN_PARTICIPANTS_FOR_RESULTS} pessoas "
                "concluírem a votação."
            )

        else:

            total_to_vote = len(
                get_voting_list()
            )

            st.write(
                f"Hoje você tem "
                f"**{total_to_vote} pessoas** "
                f"para avaliar."
            )

            if st.button(
                "Participar do Queridômetro",
                type="primary",
                use_container_width=True,
            ):

                st.session_state.page = "voting"
                st.session_state.current_vote_index = 0

                st.rerun()

    else:

        st.info(
            "🔒 A votação de hoje "
            "foi encerrada."
        )

        if already_voted:
            st.success(
                "✅ Você participou hoje."
            )

        participation_count = (
            get_today_participation_count()
        )

        if (
            participation_count
            >= MIN_PARTICIPANTS_FOR_RESULTS
        ):
            st.write(
                "Os resultados de hoje "
                "já estão disponíveis em "
                "**📊 Resultados**."
            )
        else:
            st.write(
                "Os resultados permanecem fechados "
                "porque hoje ainda não foram registradas "
                f"{MIN_PARTICIPANTS_FOR_RESULTS} "
                "participações concluídas."
            )


# ==================================================
# EMOJIS
# ==================================================

def show_emojis():
    st.title(
        "📖 Emojis"
    )

    st.write(
        "Consulte aqui o significado "
        "de cada opção do Queridômetro."
    )

    st.divider()

    for emoji, data in EMOJI_OPTIONS.items():
        if emoji == FRIDAY_EMOJI and not is_friday():
            continue

        emoji_name = html.escape(
            data["name"]
        )

        emoji_description = html.escape(
            data["description"]
        )

        card_html = (
            '<div style="'
            'display:flex;'
            'align-items:flex-start;'
            'gap:16px;'
            'padding:14px 0;'
            '">'
            '<div style="font-size:34px;min-width:46px;">'
            f'{emoji}'
            '</div>'
            '<div>'
            '<div style="'
            'font-size:20px;'
            'font-weight:700;'
            'margin-bottom:4px;'
            '">'
            f'{emoji_name}'
            '</div>'
            '<div style="'
            'font-size:16px;'
            'line-height:1.5;'
            'opacity:0.85;'
            '">'
            f'{emoji_description}'
            '</div>'
            '</div>'
            '</div>'
        )

        st.markdown(
            card_html,
            unsafe_allow_html=True,
        )

        st.divider()


# ==================================================
# PERFIL
# ==================================================

def show_profile():
    st.title(
        "👤 Meu perfil"
    )

    show_name(
        st.session_state.user_name,
        "h3",
    )

    if st.session_state.profile_photo_url:

        col1, col2, col3 = (
            st.columns([1, 1, 1])
        )

        with col2:

            st.image(
                st.session_state.profile_photo_url,
                width=180,
            )

    else:

        st.info(
            "Você ainda não adicionou "
            "uma foto."
        )

    st.divider()

    uploader_key = (
        "edit_photo_"
        f"{st.session_state.photo_uploader_version}"
    )

    cropper_key = (
        "edit_cropper_"
        f"{st.session_state.photo_uploader_version}"
    )

    uploaded_photo = st.file_uploader(
        "Adicionar ou trocar foto",
        type=[
            "jpg",
            "jpeg",
            "png",
            "webp",
        ],
        key=uploader_key,
    )

    if uploaded_photo is not None:

        image = Image.open(
            uploaded_photo
        )

        st.subheader(
            "Ajuste sua foto"
        )

        st.caption(
            "Arraste e redimensione "
            "o quadrado."
        )

        cropped_image = st_cropper(
            image,
            realtime_update=True,
            box_color="white",
            aspect_ratio=(1, 1),
            key=cropper_key,
        )

        st.write(
            "Prévia"
        )

        st.image(
            cropped_image,
            width=220,
        )

        if st.button(
            "Salvar foto",
            use_container_width=True,
        ):

            if save_profile_photo(
                cropped_image
            ):

                st.success(
                    "Foto atualizada."
                )

                st.rerun()

    if st.session_state.profile_photo_url:

        if not st.session_state.confirm_remove_photo:

            if st.button(
                "Remover foto",
                use_container_width=True,
            ):

                st.session_state.confirm_remove_photo = True
                st.rerun()

        else:

            st.warning(
                "⚠️ Tem certeza que deseja "
                "remover a foto?"
            )

            col_cancel, col_confirm = (
                st.columns(2)
            )

            with col_cancel:

                if st.button(
                    "Cancelar",
                    use_container_width=True,
                    key="cancel_remove_photo",
                ):

                    st.session_state.confirm_remove_photo = False
                    st.rerun()

            with col_confirm:

                if st.button(
                    "Sim, remover",
                    type="primary",
                    use_container_width=True,
                    key="confirm_remove_photo_button",
                ):

                    if remove_profile_photo():
                        st.rerun()

    st.divider()

    if st.button(
        "Sair do Queridômetro",
        use_container_width=True,
    ):
        logout()


# ==================================================
# VOTAÇÃO
# ==================================================

def show_voting():

    if st.button(
        "← Voltar para início",
        use_container_width=True,
        key="back_to_home_from_voting",
    ):

        st.session_state.page = "home"
        st.rerun()

    if voting_status() != "open":

        st.warning(
            "A votação não está disponível "
            "neste horário."
        )
        return

    if has_voted_today():

        st.warning(
            "Você já enviou "
            "sua votação de hoje."
        )
        return

    participants = load_participants()
    voting_list = get_voting_list()

    total_people = len(voting_list)

    if total_people == 0:

        st.info(
            "Não há outros participantes "
            "disponíveis para votação."
        )
        return

    current_index = (
        st.session_state.current_vote_index
    )

    current_index = max(
        0,
        min(
            current_index,
            total_people - 1,
        ),
    )

    st.session_state.current_vote_index = (
        current_index
    )

    target_email = (
        voting_list[current_index]
    )

    target = participants[target_email]

    target_name = target["name"]
    target_photo = target["photo_url"]

    st.title(
        "🎭 Queridômetro"
    )

    st.caption(
        f"Pessoa "
        f"{current_index + 1} "
        f"de {total_people}"
    )

    st.progress(
        (current_index + 1)
        / total_people
    )

    if target_photo:

        col1, col2, col3 = (
            st.columns([1, 1, 1])
        )

        with col2:

            st.image(
                target_photo,
                width=150,
            )

    show_name(
        target_name,
        "h2",
    )

    st.write(
        "Como foi sua interação "
        "com essa pessoa hoje?"
    )

    def select_vote(emoji):

        st.session_state.votes[
            target_email
        ] = emoji

        st.session_state.page = "voting"
        st.session_state.confirm_submission = False

        st.rerun()

    col1, col2, col3 = (
        st.columns(3)
    )

    with col1:

        if st.button(
            "❤️ Coração",
            key=f"vote_{target_email}_heart",
            use_container_width=True,
        ):
            select_vote("❤️")

    with col2:

        if st.button(
            "🌱 Planta",
            key=f"vote_{target_email}_plant",
            use_container_width=True,
        ):
            select_vote("🌱")

    with col3:

        if st.button(
            "🔥 Foguinho",
            key=f"vote_{target_email}_fire",
            use_container_width=True,
        ):
            select_vote("🔥")

    col4, col5, col6 = (
        st.columns(3)
    )

    with col4:

        if st.button(
            "🐍 Cobrinha",
            key=f"vote_{target_email}_snake",
            use_container_width=True,
        ):
            select_vote("🐍")

    with col5:

        if st.button(
            "🧳 Mala",
            key=f"vote_{target_email}_bag",
            use_container_width=True,
        ):
            select_vote("🧳")

    with col6:

        if st.button(
            "🤝 Parceria",
            key=f"vote_{target_email}_partner",
            use_container_width=True,
        ):
            select_vote("🤝")

    col7, col8 = (
        st.columns(2)
    )

    with col7:

        if st.button(
            "😐 Não interage",
            key=f"vote_{target_email}_neutral",
            use_container_width=True,
        ):
            select_vote("😐")

    with col8:

        if st.button(
            "🦚 Pavão",
            key=f"vote_{target_email}_peacock",
            use_container_width=True,
        ):
            select_vote("🦚")

    if is_friday():

        st.divider()

        st.caption(
            "🍻 Especial de sexta-feira"
        )

        beer_selected = bool(
            st.session_state.friday_beer_votes.get(
                target_email,
                False,
            )
        )

        beer_label = (
            "✅ 🍻 Bora tomar uma?"
            if beer_selected
            else "🍻 Bora tomar uma?"
        )

        if st.button(
            beer_label,
            key=f"vote_{target_email}_beer",
            use_container_width=True,
        ):
            st.session_state.friday_beer_votes[
                target_email
            ] = not beer_selected

            st.session_state.page = "voting"
            st.session_state.confirm_submission = False

            st.rerun()

        st.caption(
            "Opcional: este voto é extra e não substitui "
            "o emoji principal."
        )

    selected_vote = (
        st.session_state.votes.get(
            target_email
        )
    )

    if selected_vote:

        selected_text = (
            f"Selecionado: "
            f"{selected_vote} "
            f"{EMOJI_OPTIONS[selected_vote]['name']}"
        )

        if (
            is_friday()
            and st.session_state.friday_beer_votes.get(
                target_email,
                False,
            )
        ):
            selected_text += " + 🍻 Bora tomar uma?"

        st.success(selected_text)

    else:

        st.warning(
            "Escolha uma opção "
            "para continuar."
        )

    st.divider()

    col_back, col_next = (
        st.columns(2)
    )

    with col_back:

        if st.button(
            "← Voltar",
            use_container_width=True,
            disabled=(
                current_index == 0
            ),
            key=f"previous_person_{current_index}",
        ):

            st.session_state.current_vote_index -= 1
            st.session_state.page = "voting"

            st.rerun()

    with col_next:

        is_last = (
            current_index
            == total_people - 1
        )

        if not is_last:

            if st.button(
                "Próxima →",
                use_container_width=True,
                disabled=(
                    selected_vote is None
                ),
                key=f"next_person_{current_index}",
            ):

                st.session_state.current_vote_index += 1
                st.session_state.page = "voting"

                st.rerun()

        else:

            if st.button(
                "Revisar votação",
                type="primary",
                use_container_width=True,
                disabled=(
                    selected_vote is None
                ),
                key="open_vote_review",
            ):

                st.session_state.page = "review"
                st.session_state.confirm_submission = False

                st.rerun()

    answered = sum(
        1
        for email in voting_list
        if email in st.session_state.votes
    )

    st.caption(
        f"{answered} de "
        f"{total_people} respondidos."
    )


# ==================================================
# REVISÃO
# ==================================================

def show_review():

    participants = load_participants()
    voting_list = get_voting_list()

    total_people = len(voting_list)

    answered = sum(
        1
        for email in voting_list
        if email in st.session_state.votes
    )

    st.title(
        "Revisar votação"
    )

    st.write(
        f"Você respondeu "
        f"**{answered} de "
        f"{total_people}** avaliações."
    )

    st.divider()

    for index, email in enumerate(
        voting_list,
        start=1,
    ):

        name = participants[email]["name"]

        vote = (
            st.session_state.votes.get(
                email
            )
        )

        col_info, col_edit = (
            st.columns([4, 1])
        )

        with col_info:

            safe_name = html.escape(name)

            if vote:

                vote_name = html.escape(
                    EMOJI_OPTIONS[vote]["name"]
                )

                beer_extra = (
                    is_friday()
                    and st.session_state.friday_beer_votes.get(
                        email,
                        False,
                    )
                )

                extra_html = (
                    '<br>🍻 Bora tomar uma?'
                    if beer_extra
                    else ''
                )

                review_html = (
                    '<div '
                    'translate="no" '
                    'class="notranslate" '
                    'style="'
                    'font-size:16px;'
                    'line-height:1.6;'
                    '">'
                    '<strong>'
                    f'{index}. {safe_name}'
                    '</strong>'
                    '<br>'
                    f'{vote} {vote_name}'
                    f'{extra_html}'
                    '</div>'
                )

            else:

                review_html = (
                    '<div '
                    'translate="no" '
                    'class="notranslate" '
                    'style="'
                    'font-size:16px;'
                    'line-height:1.6;'
                    '">'
                    '<strong>'
                    f'{index}. {safe_name}'
                    '</strong>'
                    '<br>'
                    'Não respondido'
                    '</div>'
                )

            st.markdown(
                review_html,
                unsafe_allow_html=True,
            )

        with col_edit:

            if st.button(
                "Editar",
                key=f"edit_{email}",
                use_container_width=True,
            ):

                st.session_state.current_vote_index = (
                    voting_list.index(
                        email
                    )
                )

                st.session_state.page = "voting"
                st.session_state.confirm_submission = False

                st.rerun()

        st.divider()

    if answered < total_people:

        st.warning(
            "Complete todas as respostas "
            "antes de enviar."
        )

        if st.button(
            "Voltar para votação",
            use_container_width=True,
        ):

            for email in voting_list:

                if email not in st.session_state.votes:

                    st.session_state.current_vote_index = (
                        voting_list.index(
                            email
                        )
                    )
                    break

            st.session_state.page = "voting"
            st.rerun()

        return

    if not st.session_state.confirm_submission:

        if st.button(
            "Enviar votação",
            type="primary",
            use_container_width=True,
            key="start_submission",
        ):

            st.session_state.confirm_submission = True
            st.rerun()

    else:

        st.warning(
            "Depois do envio, as respostas "
            "não poderão mais ser alteradas."
        )

        col_cancel, col_confirm = (
            st.columns(2)
        )

        with col_cancel:

            if st.button(
                "Cancelar",
                use_container_width=True,
                key="cancel_submission",
            ):

                st.session_state.confirm_submission = False
                st.rerun()

        with col_confirm:

            if st.button(
                "Confirmar envio",
                type="primary",
                use_container_width=True,
                key="confirm_submission_button",
            ):

                submit_votes()


# ==================================================
# ENVIO DOS VOTOS
# ==================================================

def submit_votes():

    participants = load_participants()
    voting_list = get_voting_list()

    # ==============================================
    # MONTA O PACOTE FINAL DE VOTOS
    # ==============================================

    votes_payload = []

    for email in voting_list:

        emoji = st.session_state.votes.get(
            email
        )

        if emoji is None:

            st.error(
                "Existem respostas pendentes."
            )
            return

        votes_payload.append(
            {
                "recipient_id": (
                    participants[email]["id"]
                ),
                "emoji": emoji,
                "beer": (
                    bool(
                        st.session_state.friday_beer_votes.get(
                            email,
                            False,
                        )
                    )
                    if is_friday()
                    else False
                ),
            }
        )

    # ==============================================
    # PRECISA ESTAR AUTENTICADO
    # ==============================================

    if not st.session_state.get(
        "auth_access_token"
    ):

        st.error(
            "Sua sessão de acesso não está válida. "
            "Entre novamente no Queridômetro."
        )
        return

    if not st.session_state.get(
        "auth_refresh_token"
    ):

        st.error(
            "Sua sessão de acesso precisa ser renovada. "
            "Entre novamente no Queridômetro."
        )
        return

    try:

        # ==============================================
        # CLIENTE AUTH DA PRÓPRIA SESSÃO
        # ==============================================

        auth_client = ensure_authenticated_client()

        if auth_client is None:
            st.error(
                "Sua sessão expirou. "
                "Entre novamente no Queridômetro."
            )
            return

        # ==============================================
        # ENVIO ATÔMICO PARA O SUPABASE
        # ==============================================

        response = (
            auth_client
            .rpc(
                "submit_my_daily_votes",
                {
                    "p_votes": votes_payload
                },
            )
            .execute()
        )

        # ==============================================
        # SUCESSO
        # ==============================================

        st.session_state.confirm_submission = False
        st.session_state.page = "submitted"

        st.rerun()

    except Exception as error:

        error_text = str(error)
        error_lower = error_text.lower()

        if "já concluiu a votação" in error_lower:

            st.warning(
                "Você já concluiu "
                "a votação de hoje."
            )

        elif "somente entre 09h e 18h" in error_lower:

            st.warning(
                "A votação está disponível "
                "somente entre 09h e 18h."
            )

        elif "usuário não autenticado" in error_lower:

            st.error(
                "Sua sessão expirou. "
                "Entre novamente no Queridômetro."
            )

        else:

            st.error(
                "Não foi possível enviar "
                "a votação."
            )

            st.code(
                error_text
            )
# ==================================================
# ENVIO CONCLUÍDO
# ==================================================

def show_submitted():

    st.title(
        "🎭 Queridômetro"
    )

    st.success(
        "Votação enviada com sucesso!"
    )

    st.write(
        "Sua participação de hoje "
        "foi registrada."
    )

    st.caption(
        "Os resultados serão liberados "
        "depois das 18h."
    )

    if st.button(
        "Voltar ao início",
        use_container_width=True,
    ):

        st.session_state.votes = {}
        st.session_state.friday_beer_votes = {}
        st.session_state.page = "home"

        st.rerun()


# ==================================================
# RESULTADOS
# ==================================================

def get_results(
    start_date,
    end_date,
):

    participants = load_participants()

    response = (
        supabase
        .table("votes")
        .select(
            "recipient_id,emoji,vote_date"
        )
        .gte(
            "vote_date",
            start_date.isoformat(),
        )
        .lte(
            "vote_date",
            end_date.isoformat(),
        )
        .execute()
    )

    eligible_dates = get_eligible_result_dates(
        start_date,
        end_date,
    )

    results = {}

    for participant in participants.values():

        results[
            participant["id"]
        ] = {
            "name": participant["name"],
            "photo_url": participant["photo_url"],
            "counts": {
                emoji: 0
                for emoji in COUNTED_EMOJIS
            },
        }

    for vote in response.data:

        vote_date = vote.get("vote_date")

        if vote_date not in eligible_dates:
            continue

        recipient_id = vote["recipient_id"]
        emoji = vote["emoji"]

        if (
            recipient_id in results
            and emoji in COUNTED_EMOJIS
        ):

            results[
                recipient_id
            ]["counts"][emoji] += 1

    return results


def show_result_card(
    name,
    counts,
    photo_url=None,
):

    if photo_url:

        col1, col2, col3 = (
            st.columns([1, 1, 1])
        )

        with col2:

            st.image(
                photo_url,
                width=110,
            )

    safe_name = html.escape(name)

    result_name_html = (
        '<div '
        'translate="no" '
        'class="notranslate" '
        'style="'
        'font-size:22px;'
        'font-weight:700;'
        'margin-top:18px;'
        'margin-bottom:14px;'
        '">'
        f'{safe_name}'
        '</div>'
    )

    st.markdown(
        result_name_html,
        unsafe_allow_html=True,
    )

    emoji_items = ""

    visible_emojis = BASE_EMOJIS.copy()

    if counts.get(FRIDAY_EMOJI, 0) > 0:
        visible_emojis.append(FRIDAY_EMOJI)

    for emoji in visible_emojis:

        emoji_items += (
            '<div style="'
            'text-align:center;'
            'min-width:0;'
            '">'
            '<div style="'
            'font-size:22px;'
            'line-height:1.2;'
            '">'
            f'{emoji}'
            '</div>'
            '<div style="'
            'font-size:16px;'
            'font-weight:700;'
            'margin-top:6px;'
            '">'
            f'{counts[emoji]}'
            '</div>'
            '</div>'
        )

    result_html = (
        '<div style="'
        'display:grid;'
        f'grid-template-columns:repeat({len(visible_emojis)},minmax(0,1fr));'
        'width:100%;'
        'gap:2px;'
        'align-items:center;'
        'margin-bottom:20px;'
        '">'
        f'{emoji_items}'
        '</div>'
    )

    st.markdown(
        result_html,
        unsafe_allow_html=True,
    )

    st.divider()


def get_bingo_winners(results):

    winners = []

    for participant_id, data in results.items():

        counts = data.get("counts", {})

        completed = all(
            counts.get(emoji, 0) > 0
            for emoji in BINGO_EMOJIS
        )

        if completed:
            winners.append(
                {
                    "id": participant_id,
                    "name": data.get("name", "Participante"),
                }
            )

    return winners


def _render_bingo_content(winners, bingo_key):

    st.markdown(
        "<div style='text-align:center;font-size:54px;line-height:1'>🎉</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div style='text-align:center;font-size:38px;font-weight:900;"
        "letter-spacing:2px;margin:8px 0 16px 0'>"
        "BINGOOOOO!"
        "</div>",
        unsafe_allow_html=True,
    )

    if len(winners) == 1:

        safe_name = html.escape(
            winners[0]["name"]
        )

        st.markdown(
            f"<div style='text-align:center;font-size:18px'>"
            f"<strong>{safe_name}</strong> completou a cartela do Queridômetro "
            f"e recebeu pelo menos um voto em cada emoji do Bingo!"
            f"</div>",
            unsafe_allow_html=True,
        )

    else:

        safe_names = ", ".join(
            html.escape(item["name"])
            for item in winners
        )

        st.markdown(
            f"<div style='text-align:center;font-size:18px'>"
            f"Hoje teve Bingo coletivo! 🎊<br><br>"
            f"<strong>{safe_names}</strong> completaram a cartela do Queridômetro."
            f"</div>",
            unsafe_allow_html=True,
        )

    st.caption(
        "Vale ❤️ 🌱 🔥 🐍 🧳 🤝 🦚. "
        "😐 Não interage e 🍻 Bora tomar uma? não entram na cartela."
    )

    if st.button(
        "AEEEE! 🎉",
        type="primary",
        use_container_width=True,
        key=f"dismiss_bingo_{bingo_key}",
    ):

        st.session_state.bingo_seen_key = bingo_key
        st.rerun()


if hasattr(st, "dialog"):

    @st.dialog("🎉 Festa no Queridômetro!")
    def show_bingo_dialog(winners, bingo_key):
        _render_bingo_content(
            winners,
            bingo_key,
        )

else:

    def show_bingo_dialog(winners, bingo_key):
        st.success("🎉 BINGOOOOO!")
        _render_bingo_content(
            winners,
            bingo_key,
        )


def show_results():

    st.title(
        "📊 Resultados"
    )

    today = today_br()

    # O consolidado semanal só é liberado na sexta,
    # depois do encerramento da votação.
    result_options = ["Hoje"]

    if is_friday(today):
        result_options.append("Semana")

    mode = st.radio(
        "Visualização",
        result_options,
        horizontal=True,
    )

    if not is_friday(today):
        st.caption(
            "O consolidado semanal é fechado e liberado às sextas-feiras."
        )

    if mode == "Hoje":

        date_value = today
        participation_count = (
            get_participation_count(
                date_value
            )
        )

        if (
            participation_count
            < MIN_PARTICIPANTS_FOR_RESULTS
        ):
            remaining = (
                MIN_PARTICIPANTS_FOR_RESULTS
                - participation_count
            )

            st.info(
                "🔒 Resultados ainda fechados"
            )

            st.write(
                "Os resultados serão liberados "
                "quando pelo menos "
                f"**{MIN_PARTICIPANTS_FOR_RESULTS} pessoas** "
                "concluírem a votação de hoje."
            )

            st.progress(
                min(
                    participation_count
                    / MIN_PARTICIPANTS_FOR_RESULTS,
                    1.0,
                )
            )

            st.caption(
                f"{participation_count} de "
                f"{MIN_PARTICIPANTS_FOR_RESULTS} "
                "participações registradas. "
                f"Faltam {remaining}."
            )
            return

        st.success(
            "📊 Resultados liberados!"
        )

        st.caption(
            date_value.strftime(
                "%d/%m/%Y"
            )
        )

        results = get_results(
            date_value,
            date_value,
        )

    else:

        if voting_status() != "closed":
            st.info(
                "O fechamento semanal será liberado hoje depois das 18h."
            )
            return

        monday, _ = (
            get_week_dates(today)
        )

        # A semana do Queridômetro fecha na sexta.
        friday = monday + timedelta(days=4)

        st.caption(
            f"{monday.strftime('%d/%m')} "
            f"a "
            f"{friday.strftime('%d/%m/%Y')}"
        )

        eligible_dates = get_eligible_result_dates(
            monday,
            friday,
        )

        if not eligible_dates:
            st.info(
                "🔒 Nenhum dia desta semana atingiu "
                f"o mínimo de {MIN_PARTICIPANTS_FOR_RESULTS} "
                "participações."
            )
            return

        st.caption(
            "O consolidado considera apenas os dias "
            f"com pelo menos {MIN_PARTICIPANTS_FOR_RESULTS} "
            "participações concluídas."
        )

        results = get_results(
            monday,
            friday,
        )

    # ==================================================
    # BINGO DO DIA 🎉
    # ==================================================
    # A celebração vale apenas para o resultado diário.
    # Semana e histórico continuam sem popup.
    if mode == "Hoje":

        bingo_winners = get_bingo_winners(
            results
        )

        if bingo_winners:

            winner_ids = sorted(
                item["id"]
                for item in bingo_winners
            )

            bingo_key = (
                f"{date_value.isoformat()}|"
                + "|".join(winner_ids)
            )

            if (
                st.session_state.get(
                    "bingo_seen_key"
                )
                != bingo_key
            ):

                st.balloons()

                show_bingo_dialog(
                    bingo_winners,
                    bingo_key,
                )

    for data in results.values():

        show_result_card(
            data["name"],
            data["counts"],
            data["photo_url"],
        )


# ==================================================
# HISTÓRICO
# ==================================================

def show_history():

    st.title(
        "🗓️ Histórico"
    )

    today = today_br()
    current_monday, _ = get_week_dates(today)
    current_friday = current_monday + timedelta(days=4)

    weeks = []

    for offset in range(8):

        reference = (
            today
            - timedelta(
                weeks=offset
            )
        )

        monday, _ = (
            get_week_dates(reference)
        )

        friday = monday + timedelta(days=4)

        # A semana atual só entra no Histórico depois do
        # fechamento de sexta-feira às 18h.
        if (
            monday == current_monday
            and (
                today < current_friday
                or voting_status() != "closed"
            )
        ):
            continue

        label = (
            f"{monday.strftime('%d/%m/%Y')} "
            f"a "
            f"{friday.strftime('%d/%m/%Y')}"
        )

        weeks.append(
            (
                label,
                monday,
                friday,
            )
        )

    if not weeks:
        st.info(
            "O histórico semanal é fechado às sextas-feiras, depois das 18h."
        )
        return

    st.caption(
        "Cada semana do histórico considera segunda a sexta-feira."
    )

    labels = [
        week[0]
        for week in weeks
    ]

    selected_label = (
        st.selectbox(
            "Escolha a semana",
            labels,
        )
    )

    selected_week = next(
        week
        for week in weeks
        if week[0] == selected_label
    )

    monday = selected_week[1]
    friday = selected_week[2]

    eligible_dates = get_eligible_result_dates(
        monday,
        friday,
    )

    if not eligible_dates:
        st.info(
            "Esta semana não possui dias com o mínimo de "
            f"{MIN_PARTICIPANTS_FOR_RESULTS} participações "
            "concluídas."
        )
        return

    st.caption(
        "O histórico considera apenas dias que atingiram "
        f"o mínimo de {MIN_PARTICIPANTS_FOR_RESULTS} participações."
    )

    results = get_results(
        monday,
        friday,
    )

    for data in results.values():

        show_result_card(
            data["name"],
            data["counts"],
            data["photo_url"],
        )


# ==================================================
# MANUTENÇÃO
# ==================================================

def show_maintenance():

    if not is_admin():

        st.error(
            "Acesso não autorizado."
        )
        return

    st.title(
        "⚙️ Manutenção"
    )

    st.caption(
        "Área técnica do Queridômetro"
    )

    # ==================================================
    # CONTROLE DO APP
    # ==================================================

    maintenance_active = (
        get_maintenance_mode()
    )

    st.subheader(
        "Controle do app"
    )

    if maintenance_active:

        st.error(
            "🔴 App pausado para manutenção"
        )

        st.write(
            "Os demais participantes estão "
            "temporariamente sem acesso."
        )

        if st.button(
            "🟢 Reativar app",
            type="primary",
            use_container_width=True,
        ):

            if set_maintenance_mode(False):

                st.success(
                    "App reativado."
                )
                st.rerun()

    else:

        st.success(
            "🟢 App ativo"
        )

        st.write(
            "O Queridômetro está disponível "
            "normalmente para os participantes."
        )

        if st.button(
            "🔴 Pausar app",
            use_container_width=True,
        ):

            if set_maintenance_mode(True):

                st.success(
                    "App pausado."
                )
                st.rerun()

    # ==================================================
    # CENTRAL DE COMUNICADOS
    # ==================================================

    st.divider()

    st.subheader(
        "📣 Comunicados"
    )

    st.caption(
        "Publique agora ou programe comunicados "
        "para todos os participantes."
    )

    announcement_title = st.text_input(
        "Título",
        placeholder=(
            "Ex.: 🎭 O Queridômetro "
            "tem novidades!"
        ),
        key="new_announcement_title",
    )

    announcement_message = st.text_area(
        "Mensagem",
        height=240,
        placeholder=(
            "Escreva aqui o comunicado."
        ),
        key="new_announcement_message",
    )

    announcement_version = st.text_input(
        "Versão do app (opcional)",
        placeholder="Ex.: 1.2",
        key="new_announcement_version",
    )

    publication_mode = st.radio(
        "Publicação",
        [
            "Publicar agora",
            "Agendar",
        ],
        horizontal=True,
        key="announcement_publication_mode",
    )

    scheduled_datetime = None

    # ==================================================
    # AGENDAMENTO EM PADRÃO BRASILEIRO
    # ==================================================

    if publication_mode == "Agendar":

        col_date, col_time = (
            st.columns(2)
        )

        with col_date:

            default_date = (
                today_br()
                + timedelta(days=1)
            )

            scheduled_date_text = st.text_input(
                "Data",
                value=default_date.strftime(
                    "%d/%m/%Y"
                ),
                placeholder="DD/MM/AAAA",
                key="announcement_date_text",
            )

        with col_time:

            scheduled_time = st.time_input(
                "Hora",
                value=time(9, 0),
                key="announcement_time",
            )

        try:

            scheduled_date = datetime.strptime(
                scheduled_date_text,
                "%d/%m/%Y",
            ).date()

            scheduled_datetime = datetime.combine(
                scheduled_date,
                scheduled_time,
                tzinfo=TIMEZONE,
            )

        except ValueError:

            st.warning(
                "Digite a data no formato "
                "DD/MM/AAAA."
            )

        st.caption(
            "Horário de Brasília / São Paulo."
        )

    col_draft, col_action = (
        st.columns(2)
    )

    with col_draft:

        if st.button(
            "Salvar rascunho",
            use_container_width=True,
            key="save_new_announcement_draft",
        ):

            title = announcement_title.strip()
            message = announcement_message.strip()
            version = announcement_version.strip()

            if not title or not message:

                st.warning(
                    "Preencha título e mensagem."
                )

            else:

                if save_announcement_draft(
                    version,
                    title,
                    message,
                ):

                    st.success(
                        "Rascunho salvo."
                    )

                    st.rerun()

    with col_action:

        action_label = (
            "Publicar mensagem"
            if publication_mode == "Publicar agora"
            else "Agendar mensagem"
        )

        if st.button(
            action_label,
            type="primary",
            use_container_width=True,
            key="publish_or_schedule_announcement",
        ):

            title = announcement_title.strip()
            message = announcement_message.strip()
            version = announcement_version.strip()

            if not title or not message:

                st.warning(
                    "Preencha título e mensagem."
                )

            elif publication_mode == "Agendar":

                if scheduled_datetime is None:

                    st.warning(
                        "Informe uma data válida "
                        "no formato DD/MM/AAAA."
                    )

                elif scheduled_datetime <= now_br():

                    st.warning(
                        "Escolha uma data e hora futuras."
                    )

                elif schedule_announcement(
                    version,
                    title,
                    message,
                    scheduled_datetime,
                ):

                    st.success(
                        "Mensagem agendada."
                    )

                    st.rerun()

            else:

                if publish_announcement(
                    version,
                    title,
                    message,
                ):

                    st.success(
                        "Mensagem publicada."
                    )

                    st.rerun()

    # ==================================================
    # LISTAGEM DE COMUNICADOS
    # ==================================================

    announcements = load_announcements()

    published = []
    scheduled = []
    drafts = []

    for announcement in announcements:

        status = announcement.get("status")

        if status == "draft":

            drafts.append(
                announcement
            )

        elif status == "scheduled":

            scheduled_at = parse_supabase_datetime(
                announcement.get(
                    "scheduled_at"
                )
            )

            if (
                scheduled_at
                and scheduled_at <= now_br()
            ):

                published.append(
                    announcement
                )

            else:

                scheduled.append(
                    announcement
                )

        elif status == "published":

            published.append(
                announcement
            )

    st.divider()

    st.subheader(
        "🟢 Em exibição"
    )

    if not published:

        st.caption(
            "Nenhum comunicado em exibição."
        )

    for announcement in published:

        version_text = (
            format_announcement_version(
                announcement
            )
        )

        st.markdown(
            f"**{announcement['title']}**"
            f"{version_text}"
        )

        views = (
            get_announcement_view_count(
                announcement["id"]
            )
        )

        total = len(
            load_participants()
        )

        if announcement.get("status") == "scheduled":

            scheduled_at = parse_supabase_datetime(
                announcement.get(
                    "scheduled_at"
                )
            )

            if scheduled_at:

                st.caption(
                    "Publicação automática: "
                    f"{scheduled_at.strftime('%d/%m/%Y às %H:%M')}"
                )

        st.caption(
            f"Visualizada por "
            f"{views} de {total} participantes."
        )

        if st.button(
            "Desativar",
            key=(
                f"deactivate_"
                f"{announcement['id']}"
            ),
            use_container_width=True,
        ):

            if deactivate_announcement(
                announcement["id"]
            ):

                st.success(
                    "Mensagem desativada."
                )
                st.rerun()

        st.divider()

    st.subheader(
        "🕒 Agendadas"
    )

    if not scheduled:

        st.caption(
            "Nenhuma mensagem agendada."
        )

    for announcement in scheduled:

        version_text = (
            format_announcement_version(
                announcement
            )
        )

        st.markdown(
            f"**{announcement['title']}**"
            f"{version_text}"
        )

        scheduled_at = parse_supabase_datetime(
            announcement.get(
                "scheduled_at"
            )
        )

        if scheduled_at:

            st.caption(
                f"{scheduled_at.strftime('%d/%m/%Y às %H:%M')}"
            )

        col_edit, col_cancel = st.columns(2)

        with col_edit:

            if st.button(
                "✏️ Editar agendamento",
                key=(
                    f"edit_schedule_"
                    f"{announcement['id']}"
                ),
                use_container_width=True,
            ):

                st.session_state[
                    "editing_announcement_schedule"
                ] = announcement["id"]

                st.rerun()

        with col_cancel:

            if st.button(
                "Cancelar agendamento",
                key=(
                    f"cancel_schedule_"
                    f"{announcement['id']}"
                ),
                use_container_width=True,
            ):

                if deactivate_announcement(
                    announcement["id"]
                ):

                    st.success(
                        "Agendamento cancelado."
                    )

                    st.rerun()

        if (
            st.session_state.get(
                "editing_announcement_schedule"
            )
            == announcement["id"]
        ):

            st.info(
                "✏️ Alterar data e horário"
            )

            current_date = (
                scheduled_at.date()
                if scheduled_at
                else today_br() + timedelta(days=1)
            )

            current_time = (
                scheduled_at.time().replace(
                    tzinfo=None
                )
                if scheduled_at
                else time(9, 0)
            )

            col_date, col_time = st.columns(2)

            with col_date:

                new_date_text = st.text_input(
                    "Nova data",
                    value=current_date.strftime(
                        "%d/%m/%Y"
                    ),
                    key=(
                        f"edit_date_"
                        f"{announcement['id']}"
                    ),
                )

            with col_time:

                new_time = st.time_input(
                    "Novo horário",
                    value=current_time,
                    key=(
                        f"edit_time_"
                        f"{announcement['id']}"
                    ),
                )

            new_scheduled_datetime = None

            try:

                new_date = datetime.strptime(
                    new_date_text,
                    "%d/%m/%Y",
                ).date()

                new_scheduled_datetime = (
                    datetime.combine(
                        new_date,
                        new_time,
                        tzinfo=TIMEZONE,
                    )
                )

            except ValueError:

                st.warning(
                    "Digite a data no formato "
                    "DD/MM/AAAA."
                )

            col_save, col_close = st.columns(2)

            with col_save:

                if st.button(
                    "💾 Salvar alteração",
                    type="primary",
                    use_container_width=True,
                    key=(
                        f"save_schedule_"
                        f"{announcement['id']}"
                    ),
                ):

                    if new_scheduled_datetime is None:

                        st.warning(
                            "Informe uma data válida."
                        )

                    elif (
                        new_scheduled_datetime
                        <= now_br()
                    ):

                        st.warning(
                            "Escolha uma data "
                            "e horário futuros."
                        )

                    elif update_announcement_schedule(
                        announcement["id"],
                        new_scheduled_datetime,
                    ):

                        st.session_state.pop(
                            "editing_announcement_schedule",
                            None,
                        )

                        st.success(
                            "Agendamento alterado."
                        )

                        st.rerun()

            with col_close:

                if st.button(
                    "Fechar",
                    use_container_width=True,
                    key=(
                        f"close_schedule_"
                        f"{announcement['id']}"
                    ),
                ):

                    st.session_state.pop(
                        "editing_announcement_schedule",
                        None,
                    )

                    st.rerun()

        st.divider()

    st.subheader(
        "📝 Rascunhos"
    )

    if not drafts:

        st.caption(
            "Nenhum rascunho salvo."
        )

    for announcement in drafts:

        version_text = (
            format_announcement_version(
                announcement
            )
        )

        st.markdown(
            f"**{announcement['title']}**"
            f"{version_text}"
        )

        st.caption(
            "Rascunho não visível "
            "aos participantes."
        )

        if st.button(
            "Descartar rascunho",
            key=(
                f"discard_draft_"
                f"{announcement['id']}"
            ),
            use_container_width=True,
        ):

            if deactivate_announcement(
                announcement["id"]
            ):

                st.success(
                    "Rascunho descartado."
                )
                st.rerun()

        st.divider()

    # ==================================================
    # STATUS DA VOTAÇÃO
    # ==================================================

    st.subheader(
        "Status da votação"
    )

    st.write(
        voting_status_label()
    )

    st.caption(
        "Janela diária: 09h às 18h"
    )

    st.divider()

    # ==================================================
    # PARTICIPAÇÃO
    # ==================================================

    participants = load_participants()

    total_participants = len(
        participants
    )

    try:

        participation_today = (
            get_today_participation_count()
        )

        votes_today = (
            get_today_votes_count()
        )

        database_ok = True

    except Exception:

        participation_today = 0
        votes_today = 0
        database_ok = False

    st.subheader(
        "Participação de hoje"
    )

    st.metric(
        "Participantes que concluíram",
        f"{participation_today} / "
        f"{total_participants}",
    )

    if total_participants > 0:

        participation_rate = (
            participation_today
            / total_participants
        )

        st.progress(
            min(
                participation_rate,
                1.0,
            )
        )

        st.caption(
            f"{participation_rate * 100:.0f}% "
            f"de participação"
        )

    st.divider()

    # ==================================================
    # PARTICIPANTES
    # ==================================================

    st.subheader(
        "Participantes"
    )

    st.metric(
        "Ativos",
        total_participants,
    )

    st.caption(
        "A gestão de participantes "
        "será adicionada nesta área."
    )

    st.divider()

    # ==================================================
    # BANCO
    # ==================================================

    st.subheader(
        "Banco de dados"
    )

    if database_ok:

        st.success(
            "Supabase conectado"
        )

        st.write(
            f"Registros de votos "
            f"recebidos hoje: "
            f"**{votes_today}**"
        )

    else:

        st.error(
            "Não foi possível consultar "
            "o Supabase."
        )

    st.divider()

    st.info(
        "A área de manutenção não possui "
        "acesso à autoria dos votos. "
        "O banco não registra quem deu "
        "cada emoji."
    )


# ==================================================
# LOGIN AUTOMÁTICO
# ==================================================

# Se houver um refresh token válido salvo neste navegador,
# restaura a sessão do Supabase sem pedir um novo OTP.
if st.session_state.user_email is None:
    try_persistent_login()


# ==================================================
# CONTROLE PRINCIPAL
# ==================================================

if st.session_state.user_email is None:

    show_login()

else:

    maintenance_active = (
        get_maintenance_mode()
    )

    if (
        maintenance_active
        and not is_admin()
    ):

        show_maintenance_screen()

    else:

        show_test_fire = (
            FIRE_TEST_MODE
            and is_admin()
            and not st.session_state.get(
                "fire_test_preview_dismissed",
                False,
            )
        )

        if show_test_fire:

            show_fire_match_test_preview()

        else:

            pending_fire_matches = (
                get_pending_fire_matches()
            )

            if pending_fire_matches:

                show_fire_match_surprise(
                    pending_fire_matches[0]
                )

            else:

                announcement = (
                    get_pending_announcement_for_user()
                )

                if announcement:

                    show_announcement(
                        announcement
                    )

                else:

                    special_pages = {
                        "voting",
                        "review",
                        "submitted",
                    }

                    if (
                        st.session_state.page
                        not in special_pages
                    ):

                        show_navigation()

                    if st.session_state.page == "home":

                        show_home()

                    elif st.session_state.page == "results":

                        show_results()

                    elif st.session_state.page == "history":

                        show_history()

                    elif st.session_state.page == "emojis":

                        show_emojis()

                    elif st.session_state.page == "profile":

                        show_profile()

                    elif st.session_state.page == "maintenance":

                        show_maintenance()

                    elif st.session_state.page == "voting":

                        show_voting()

                    elif st.session_state.page == "review":

                        show_review()

                    elif st.session_state.page == "submitted":

                        show_submitted()

                    else:

                        st.session_state.page = "home"
                        st.rerun()
