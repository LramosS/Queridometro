import streamlit as st
from supabase import create_client

from participants import PARTICIPANTS


supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)


rows = []

for email, data in PARTICIPANTS.items():
    rows.append(
        {
            "name": data["name"],
            "email": email,
            "photo_url": None,
            "active": True
        }
    )


try:
    response = (
        supabase
        .table("participants")
        .insert(rows)
        .execute()
    )

    print("Participantes importados com sucesso.")
    print(f"Total enviado: {len(rows)}")

except Exception as error:
    print("Erro ao importar participantes:")
    print(error)