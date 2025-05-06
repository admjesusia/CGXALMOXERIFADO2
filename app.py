import os
import time

# Instalar dependências necessárias antes da importação
os.system("pip install --upgrade pip")
os.system("pip install streamlit pandas plotly gspread oauth2client pyngrok")

try:
    import streamlit as st
    import pandas as pd
    import plotly.express as px
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    from pyngrok import ngrok
except ImportError as e:
    print(f"Erro ao importar bibliotecas: {e}")
    exit()

# Configuração do Dashboard
st.set_page_config(page_title="📦 Dashboard de Inventário", layout="wide")
st.title("📦 Dashboard de Inventário e Itens")

# Configurar acesso ao Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
try:
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    client = gspread.authorize(creds)
except Exception as e:
    st.error(f"Erro ao autenticar no Google Sheets: {e}")
    st.stop()

# URL da planilha do Google Sheets
gsheet_url = "https://docs.google.com/spreadsheets/d/1NLLZoIxIZ2u-liHGKM5P8WNXdu3ycCoUUiD3f0FsR84/edit?usp=sharing"

# Abrir planilha e carregar dados
try:
    doc = client.open_by_url(gsheet_url)
    df_items = pd.DataFrame(doc.worksheet("Items").get_all_records())
    df_inventory = pd.DataFrame(doc.worksheet("Inventory").get_all_records())
except Exception as e:
    st.error(f"Erro ao carregar os dados da planilha: {e}")
    st.stop()

# Criar filtros interativos na barra lateral
st.sidebar.header("🔎 Filtros")

# Filtro por Nome do Item
item_names = df_items["Name"].dropna().unique()
selected_items = st.sidebar.multiselect("Nome do Item", item_names, default=item_names[:5])

# Aplicar filtro
filtered_items = df_items[df_items["Name"].isin(selected_items)]

# Exibir dados filtrados
st.write(f"### 📌 {filtered_items.shape[0]} Itens Selecionados")
st.dataframe(filtered_items)

# Gráfico de movimentação de estoque
st.write("### 📊 Movimentação de Estoque")
df_inventory['DateTime'] = pd.to_datetime(df_inventory['DateTime'])
fig = px.line(df_inventory, x='DateTime', y='Amount', color='Item ID', title="Histórico de Estoque")
st.plotly_chart(fig, use_container_width=True)

# Criar botão para download
download_data = filtered_items.to_csv(index=False)
st.sidebar.download_button("📥 Baixar Itens Filtrados", download_data, "itens_filtrados.csv", "text/csv")
st.success("✅ Dashboard carregado com sucesso!")

# Configurar e iniciar o ngrok
time.sleep(5)
try:
    os.system("ngrok authtoken 2uINiHVg1G0p91CQXLvndb4SpuZ_3Wo8EtbWLkHWYfFDXnkrm")
    public_url = ngrok.connect(8501, "http").public_url
    st.write(f"🔗 [Acesse o Dashboard Aqui]({public_url})")
except Exception as e:
    st.error(f"Erro ao conectar com ngrok: {e}")
