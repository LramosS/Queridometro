import streamlit as st
from supabase import create_client


supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)


print("Conexão com o Supabase criada com sucesso.")

try:
    response = (
        supabase
        .table("participants")
        .select("*")
        .limit(1)
        .execute()
    )

    print("Tabela participants encontrada.")
    print(response.data)

except Exception as error:
    print("A conexão funcionou, mas houve um problema ao acessar a tabela.")
    print(error)