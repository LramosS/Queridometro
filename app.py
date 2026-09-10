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

REMEMBER_COOKIE = "queridometro_email"
COOKIE_DAYS = 365

PHOTO_BUCKET = "profile-photos"

ADMIN_EMAILS = {
    "lucasramoseconomia@gmail.com"
}


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


def is_friday():
    return today_br().weekday() == 4


# ==================================================
# SUPABASE
# ==================================================

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"],
)


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
    "page": "home",
    "votes": {},
    "current_vote_index": 0,
    "confirm_submission": False,
    "confirm_remove_photo": False,
    "photo_uploader_version": 0,
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


def try_cookie_login():
    if st.session_state.user_email is not None:
        return

    saved_email = None

    try:
        saved_email = (
            st.context.cookies.get(
                REMEMBER_COOKIE
            )
        )
    except Exception:
        pass

    if not saved_email:
        try:
            saved_email = (
                cookie_manager.get(
                    cookie=REMEMBER_COOKIE
                )
            )
        except Exception:
            saved_email = None

    if saved_email:
        login_user(
            str(saved_email)
        )


def save_login_cookie(email):
    try:
        expiration = (
            datetime.now()
            + timedelta(days=COOKIE_DAYS)
        )

        cookie_manager.set(
            REMEMBER_COOKIE,
            email,
            expires_at=expiration,
            key="set_queridometro_email",
        )

        return True

    except Exception:
        return False


def delete_login_cookie():
    try:
        cookie_manager.delete(
            cookie=REMEMBER_COOKIE,
            key="delete_queridometro_email",
        )

    except Exception:
        pass


def logout():
    delete_login_cookie()

    for key, value in DEFAULT_SESSION.items():
        st.session_state[key] = value

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


def get_today_participation_count():
    response = (
        supabase
        .table("daily_participation")
        .select("id")
        .eq(
            "vote_date",
            today_br().isoformat(),
        )
        .execute()
    )

    return len(response.data)


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

    email = st.text_input(
        "Digite seu e-mail",
        placeholder="nome@email.com",
    )

    remember = st.checkbox(
        "Lembrar neste dispositivo"
    )

    if st.button(
        "Entrar",
        use_container_width=True,
    ):
        email = email.strip().lower()

        if not email:
            st.warning(
                "Digite seu e-mail para continuar."
            )

        elif not login_user(email):
            st.error(
                "Este e-mail não está cadastrado."
            )

        else:

            if remember:
                save_login_cookie(email)

            else:
                delete_login_cookie()

            st.rerun()


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
                "Os resultados de hoje "
                "serão liberados depois das 18h."
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

        st.write(
            "Os resultados de hoje "
            "já estão disponíveis em "
            "**📊 Resultados**."
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

        if st.button(
            "🍻 Bora tomar uma?",
            key=f"vote_{target_email}_beer",
            use_container_width=True,
        ):
            select_vote("🍻")

    selected_vote = (
        st.session_state.votes.get(
            target_email
        )
    )

    if selected_vote:

        st.success(
            f"Selecionado: "
            f"{selected_vote} "
            f"{EMOJI_OPTIONS[selected_vote]['name']}"
        )

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

    date_value = today_br()

    vote_rows = []

    for email in voting_list:

        emoji = (
            st.session_state.votes.get(
                email
            )
        )

        if emoji is None:

            st.error(
                "Existem respostas pendentes."
            )
            return

        vote_rows.append(
            {
                "vote_date": (
                    date_value.isoformat()
                ),
                "week_id": (
                    get_week_id(
                        date_value
                    )
                ),
                "recipient_id": (
                    participants[email]["id"]
                ),
                "emoji": emoji,
            }
        )

    try:

        if vote_rows:

            (
                supabase
                .table("votes")
                .insert(vote_rows)
                .execute()
            )

        (
            supabase
            .table("daily_participation")
            .insert(
                {
                    "participant_id": (
                        st.session_state.user_id
                    ),
                    "vote_date": (
                        date_value.isoformat()
                    ),
                }
            )
            .execute()
        )

        st.session_state.confirm_submission = False
        st.session_state.page = "submitted"

        st.rerun()

    except Exception as error:

        st.error(
            "Não foi possível enviar "
            "a votação."
        )

        st.code(
            str(error)
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


def show_results():

    st.title(
        "📊 Resultados"
    )

    mode = st.radio(
        "Visualização",
        [
            "Hoje",
            "Semana",
        ],
        horizontal=True,
    )

    if mode == "Hoje":

        if voting_status() != "closed":

            st.info(
                "O resultado de hoje "
                "será liberado depois das 18h."
            )
            return

        date_value = today_br()

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

        today = today_br()

        monday, sunday = (
            get_week_dates(today)
        )

        if voting_status() == "closed":
            end_date = today

        else:
            end_date = (
                today
                - timedelta(days=1)
            )

        st.caption(
            f"{monday.strftime('%d/%m')} "
            f"a "
            f"{sunday.strftime('%d/%m/%Y')}"
        )

        if end_date < monday:

            st.info(
                "Ainda não há resultados "
                "encerrados nesta semana."
            )
            return

        results = get_results(
            monday,
            end_date,
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

    weeks = []

    for offset in range(8):

        reference = (
            today
            - timedelta(
                weeks=offset
            )
        )

        monday, sunday = (
            get_week_dates(reference)
        )

        label = (
            f"{monday.strftime('%d/%m/%Y')} "
            f"a "
            f"{sunday.strftime('%d/%m/%Y')}"
        )

        weeks.append(
            (
                label,
                monday,
                sunday,
            )
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
    sunday = selected_week[2]

    if monday <= today <= sunday:

        if voting_status() == "closed":
            end_date = today

        else:
            end_date = (
                today
                - timedelta(days=1)
            )

    else:
        end_date = sunday

    if end_date < monday:

        st.info(
            "Ainda não há resultados "
            "encerrados nesta semana."
        )
        return

    results = get_results(
        monday,
        end_date,
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

if st.session_state.user_email is None:
    try_cookie_login()


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
