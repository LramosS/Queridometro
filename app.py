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
    layout="centered"
)

TIMEZONE = ZoneInfo("America/Sao_Paulo")

VOTING_START = time(9, 0)
VOTING_END = time(18, 0)

REMEMBER_COOKIE = "queridometro_email"

PHOTO_BUCKET = "profile-photos"

ADMIN_EMAILS = {
    "lucasramoseconomia@gmail.com"
}

EMOJI_OPTIONS = {
    "❤️": "Coração",
    "🌱": "Planta",
    "🔥": "Foguinho",
    "🐍": "Cobrinha",
    "🧳": "Mala",
    "🤝": "Parceria",
    "➖": "Não interagi",
}

COUNTED_EMOJIS = [
    "❤️",
    "🌱",
    "🔥",
    "🐍",
    "🧳",
    "🤝",
]


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
    "cookie_checked": False,
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
    if st.session_state.cookie_checked:
        return

    st.session_state.cookie_checked = True

    saved_email = cookie_manager.get(
        cookie=REMEMBER_COOKIE
    )

    if saved_email:
        login_user(saved_email)


def logout():
    try:
        cookie_manager.delete(
            cookie=REMEMBER_COOKIE,
            key="delete_queridometro_email",
        )
    except Exception:
        pass

    for key, value in DEFAULT_SESSION.items():
        st.session_state[key] = value

    st.session_state.cookie_checked = True

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

        public_url = (
            supabase.storage
            .from_(PHOTO_BUCKET)
            .get_public_url(photo_path)
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

        load_participants.clear()

        return True

    except Exception as error:
        st.error(
            "Não foi possível remover a foto."
        )

        st.code(str(error))

        return False


# ==================================================
# EXIBIÇÃO
# ==================================================

def show_name(name, tag="h2"):
    safe_name = html.escape(name)

    st.markdown(
        f"""
        <{tag}
            translate="no"
            class="notranslate"
            style="text-align:center;"
        >
            {safe_name}
        </{tag}>
        """,
        unsafe_allow_html=True,
    )


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
    st.title("🎭 Queridômetro")

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
                expiration = (
                    datetime.now()
                    + timedelta(days=30)
                )

                cookie_manager.set(
                    REMEMBER_COOKIE,
                    email,
                    expires_at=expiration,
                    key="set_queridometro_email",
                )

            st.rerun()


# ==================================================
# NAVEGAÇÃO PRINCIPAL
# ==================================================

def show_navigation():
    options = [
        "🏠 Hoje",
        "📊 Resultados",
        "🗓️ Histórico",
        "👤 Perfil",
    ]

    page_map = {
        "🏠 Hoje": "home",
        "📊 Resultados": "results",
        "🗓️ Histórico": "history",
        "👤 Perfil": "profile",
    }

    if (
        st.session_state.user_email
        in ADMIN_EMAILS
    ):
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

    index = options.index(
        current_label
    ) if current_label in options else 0

    selected = st.radio(
        "Navegação",
        options,
        index=index,
        horizontal=True,
        label_visibility="collapsed",
        key="main_navigation",
    )

    selected_page = page_map[selected]

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
# HOME / HOJE
# ==================================================

def show_home():
    status = voting_status()

    already_voted = (
        has_voted_today()
    )

    st.title(
        "🎭 Queridômetro"
    )

    st.markdown(
        f"""
        <div
            translate="no"
            class="notranslate"
            style="
                padding:14px 16px;
                border-radius:8px;
                background-color:
                    rgba(40,167,69,0.18);
                margin-bottom:16px;
            "
        >
            Olá,
            <strong>
                {
                    html.escape(
                        st.session_state.user_name
                    )
                }
            </strong>!
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        today_br().strftime(
            "%d/%m/%Y"
        )
    )

    if status == "before":
        st.info(
            "⏰ A votação de hoje abre às 09h."
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
                st.session_state.page = (
                    "voting"
                )

                st.session_state.current_vote_index = 0

                st.session_state.votes = {}

                st.rerun()

    else:
        st.info(
            "🔒 A votação de hoje foi encerrada."
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

    uploaded_photo = st.file_uploader(
        "Adicionar ou trocar foto",
        type=[
            "jpg",
            "jpeg",
            "png",
            "webp",
        ],
        key="edit_photo",
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
            key="edit_cropper",
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
                    "Foto salva."
                )

                st.rerun()

    if st.session_state.profile_photo_url:
        if st.button(
            "Remover foto",
            use_container_width=True,
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
    if voting_status() != "open":
        st.warning(
            "A votação não está disponível "
            "neste horário."
        )

        if st.button(
            "Voltar"
        ):
            st.session_state.page = "home"
            st.rerun()

        return

    if has_voted_today():
        st.warning(
            "Você já enviou "
            "sua votação de hoje."
        )

        if st.button(
            "Voltar"
        ):
            st.session_state.page = "home"
            st.rerun()

        return

    participants = (
        load_participants()
    )

    voting_list = (
        get_voting_list()
    )

    total_people = len(
        voting_list
    )

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

    target = (
        participants[target_email]
    )

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

    col1, col2, col3 = (
        st.columns(3)
    )

    first_row = [
        ("❤️", "Coração", col1),
        ("🌱", "Planta", col2),
        ("🔥", "Foguinho", col3),
    ]

    for emoji, label, column in first_row:
        with column:
            if st.button(
                f"{emoji} {label}",
                key=(
                    f"{target_email}_{emoji}"
                ),
                use_container_width=True,
            ):
                st.session_state.votes[
                    target_email
                ] = emoji

                st.rerun()

    col4, col5, col6 = (
        st.columns(3)
    )

    second_row = [
        ("🐍", "Cobrinha", col4),
        ("🧳", "Mala", col5),
        ("🤝", "Parceria", col6),
    ]

    for emoji, label, column in second_row:
        with column:
            if st.button(
                f"{emoji} {label}",
                key=(
                    f"{target_email}_{emoji}"
                ),
                use_container_width=True,
            ):
                st.session_state.votes[
                    target_email
                ] = emoji

                st.rerun()

    if st.button(
        "➖ Não interagi",
        key=f"{target_email}_none",
        use_container_width=True,
    ):
        st.session_state.votes[
            target_email
        ] = "➖"

        st.rerun()

    selected_vote = (
        st.session_state.votes.get(
            target_email
        )
    )

    if selected_vote:
        st.success(
            f"Selecionado: "
            f"{selected_vote} "
            f"{EMOJI_OPTIONS[selected_vote]}"
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
        ):
            st.session_state.current_vote_index -= 1

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
            ):
                st.session_state.current_vote_index += 1

                st.rerun()

        else:
            if st.button(
                "Revisar votação",
                use_container_width=True,
                disabled=(
                    selected_vote is None
                ),
            ):
                st.session_state.page = (
                    "review"
                )

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
    participants = (
        load_participants()
    )

    voting_list = (
        get_voting_list()
    )

    total_people = len(
        voting_list
    )

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
        name = (
            participants[email]["name"]
        )

        vote = (
            st.session_state.votes.get(
                email
            )
        )

        col_info, col_edit = (
            st.columns([4, 1])
        )

        with col_info:
            if vote:
                st.markdown(
                    f"""
                    <strong
                        translate="no"
                        class="notranslate"
                    >
                        {index}.
                        {html.escape(name)}
                    </strong>
                    <br>
                    {vote}
                    {EMOJI_OPTIONS[vote]}
                    """,
                    unsafe_allow_html=True,
                )

            else:
                st.write(
                    f"{index}. {name} "
                    f"• Não respondido"
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

                st.session_state.page = (
                    "voting"
                )

                st.rerun()

        st.divider()

    if answered < total_people:
        st.warning(
            "Complete todas as respostas "
            "antes de enviar."
        )

        return

    if not st.session_state.confirm_submission:
        if st.button(
            "Enviar votação",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.confirm_submission = (
                True
            )

            st.rerun()

    else:
        st.warning(
            "Depois do envio, "
            "as respostas não poderão "
            "mais ser alteradas."
        )

        col_cancel, col_confirm = (
            st.columns(2)
        )

        with col_cancel:
            if st.button(
                "Cancelar",
                use_container_width=True,
            ):
                st.session_state.confirm_submission = (
                    False
                )

                st.rerun()

        with col_confirm:
            if st.button(
                "Confirmar envio",
                type="primary",
                use_container_width=True,
            ):
                submit_votes()


# ==================================================
# ENVIO DOS VOTOS
# ==================================================

def submit_votes():
    participants = (
        load_participants()
    )

    voting_list = (
        get_voting_list()
    )

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

        if emoji == "➖":
            continue

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
            .table(
                "daily_participation"
            )
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

        st.session_state.confirm_submission = (
            False
        )

        st.session_state.page = (
            "submitted"
        )

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

        st.session_state.page = (
            "home"
        )

        st.rerun()


# ==================================================
# RESULTADOS
# ==================================================

def get_results(
    start_date,
    end_date,
):
    participants = (
        load_participants()
    )

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
            "name": (
                participant["name"]
            ),
            "photo_url": (
                participant["photo_url"]
            ),
            "counts": {
                emoji: 0
                for emoji in COUNTED_EMOJIS
            },
        }

    for vote in response.data:
        recipient_id = (
            vote["recipient_id"]
        )

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

    st.markdown(
        f"""
        <div
            translate="no"
            class="notranslate"
            style="
                font-size:22px;
                font-weight:700;
                margin-top:18px;
                margin-bottom:12px;
            "
        >
            {html.escape(name)}
        </div>
        """,
        unsafe_allow_html=True,
    )

    columns = st.columns(
        len(COUNTED_EMOJIS)
    )

    for column, emoji in zip(
        columns,
        COUNTED_EMOJIS,
    ):
        with column:
            st.markdown(
                f"""
                <div style="
                    text-align:center;
                    font-size:24px;
                ">
                    {emoji}
                </div>

                <div style="
                    text-align:center;
                    font-size:18px;
                    font-weight:700;
                ">
                    {counts[emoji]}
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.divider()


# ==================================================
# RESULTADOS
# ==================================================

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

        date_value = (
            today_br()
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
        today = today_br()

        monday, sunday = (
            get_week_dates(today)
        )

        if voting_status() == "open":
            end_date = (
                today
                - timedelta(days=1)
            )
        else:
            end_date = today

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
            get_week_dates(
                reference
            )
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

    selected_label = st.selectbox(
        "Escolha a semana",
        labels,
    )

    selected_week = next(
        week
        for week in weeks
        if week[0] == selected_label
    )

    monday = selected_week[1]
    sunday = selected_week[2]

    if monday <= today <= sunday:
        if voting_status() == "open":
            end_date = (
                today
                - timedelta(days=1)
            )
        else:
            end_date = today
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
    if (
        st.session_state.user_email
        not in ADMIN_EMAILS
    ):
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

    participants = (
        load_participants()
    )

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
        "Status do sistema"
    )

    st.write(
        voting_status_label()
    )

    st.caption(
        "Janela diária: "
        "09h às 18h"
    )

    st.divider()

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

    st.subheader(
        "Participantes"
    )

    st.metric(
        "Ativos",
        total_participants,
    )

    st.divider()

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
        "Esta área não possui acesso "
        "à autoria dos votos. "
        "O banco não registra quem deu "
        "cada emoji."
    )

    st.caption(
        "Gerenciamento de participantes "
        "e diagnóstico técnico serão "
        "adicionados nas próximas etapas."
    )


# ==================================================
# LOGIN AUTOMÁTICO
# ==================================================

if st.session_state.user_email is None:
    try_cookie_login()


# ==================================================
# CONTROLE DAS TELAS
# ==================================================

if st.session_state.user_email is None:

    show_login()

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