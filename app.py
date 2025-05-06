import streamlit as st
import pandas as pd
import numpy as np
import sys

# ==============================
# 🔐 AUTENTICAÇÃO BÁSICA (CGX / x)
# ==============================
def autenticar_usuario():
    st.sidebar.title("🔐 Login - COGEX")
    usuario = st.sidebar.text_input("Usuário")
    senha = st.sidebar.text_input("Senha", type="password")

    usuarios_validos = {
        "CGX": "x"
    }

    if st.sidebar.button("Entrar"):
        if usuario in usuarios_validos and senha == usuarios_validos[usuario]:
            st.session_state["autenticado"] = True
            st.session_state["usuario"] = usuario
            st.experimental_rerun()
        else:
            st.sidebar.error("Usuário ou senha incorretos.")

if "autenticado" not in st.session_state or not st.session_state["autenticado"]:
    autenticar_usuario()
    st.stop()

# -------------------- CONFIGURAÇÕES INICIAIS --------------------
st.set_page_config(page_title="COGEX Almoxarifado", layout="wide")

# Informações de depuração (opcional)
if st.sidebar.checkbox("Mostrar Informações de Sistema"):
    st.sidebar.write("### Informações de Sistema")
    st.sidebar.write(f"Python: {sys.version}")
    st.sidebar.write(f"Pandas: {pd.__version__}")
    st.sidebar.write(f"NumPy: {np.__version__}")
    st.sidebar.write(f"Streamlit: {st.__version__}")

st.title("📦 COGEX ALMOXARIFADO")
st.markdown("**Sistema Web - Controle Matemático de Estoque - Pedido Automatizado com Critérios Reais**")

# -------------------- CONFIGURAÇÕES --------------------
DICIONARIO_LOGICO = {
    'dias_cobertura': [7, 15, 30, 45],
    'critico_limite': 0,
    'alerta_limite': 1
}

# -------------------- CARREGAMENTO DE DADOS --------------------
@st.cache_data(show_spinner="Carregando dados do Google Sheets...")
def load_data():
    # URLs atualizados para CSV publicado - SUBSTITUA PELOS URLS CORRETOS
    url_inventory = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vRuJKYNnhiA5ikZ4-fx0P1kC1Y4ZCJ4VdnP9J9ZzuDj3Ct-5EXbgZRiBnRtCSPHfGSShbLkKLJlQTQ0/pub?output=csv'
    url_items = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vRuJKYNnhiA5ikZ4-fx0P1kC1Y4ZCJ4VdnP9J9ZzuDj3Ct-5EXbgZRiBnRtCSPHfGSShbLkKLJlQTQ0/pub?gid=1011017078&single=true&output=csv'
    
    try:
        inventory = pd.read_csv(url_inventory)
        inventory['DateTime'] = pd.to_datetime(inventory['DateTime'], errors='coerce')
        inventory.dropna(subset=['Item ID', 'Amount'], inplace=True)

        items = pd.read_csv(url_items)
        items.dropna(subset=['Item ID', 'Name'], inplace=True)

        return items, inventory
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame(), pd.DataFrame()

# Testa URLs das planilhas
def testar_conexao_planilhas():
    if st.sidebar.checkbox("Testar conexão com planilhas"):
        st.subheader("Teste de URLs das Planilhas")
        
        # Use os mesmos URLs da função load_data
        url_inventory = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vRuJKYNnhiA5ikZ4-fx0P1kC1Y4ZCJ4VdnP9J9ZzuDj3Ct-5EXbgZRiBnRtCSPHfGSShbLkKLJlQTQ0/pub?output=csv'
        url_items = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vRuJKYNnhiA5ikZ4-fx0P1kC1Y4ZCJ4VdnP9J9ZzuDj3Ct-5EXbgZRiBnRtCSPHfGSShbLkKLJlQTQ0/pub?gid=1011017078&single=true&output=csv'
        
        st.write("### URL do Inventário:")
        st.code(url_inventory)
        
        try:
            inventory = pd.read_csv(url_inventory)
            st.success(f"✅ Conectado com sucesso! Linhas: {len(inventory)}, Colunas: {len(inventory.columns)}")
            st.write("Amostra:")
            st.dataframe(inventory.head(3))
        except Exception as e:
            st.error(f"❌ Erro ao conectar: {str(e)}")
        
        st.write("### URL dos Itens:")
        st.code(url_items)
        
        try:
            items = pd.read_csv(url_items)
            st.success(f"✅ Conectado com sucesso! Linhas: {len(items)}, Colunas: {len(items.columns)}")
            st.write("Amostra:")
            st.dataframe(items.head(3))
        except Exception as e:
            st.error(f"❌ Erro ao conectar: {str(e)}")

# Carrega dados
testar_conexao_planilhas()
items_df, inventory_df = load_data()

# -------------------- FUNÇÕES MATEMÁTICAS --------------------
def calcular_consumo_medio(inventory):
    consumo = inventory[inventory['Amount'] < 0].groupby('Item ID')['Amount'].sum().abs()
    dias = max(1, (inventory['DateTime'].max() - inventory['DateTime'].min()).days)  # Evita divisão por zero
    consumo_medio = consumo / dias
    return consumo_medio

def calcular_saldo_atual(inventory):
    saldo = inventory.groupby('Item ID')['Amount'].sum()
    return saldo

def gerar_pedido(dias_cobertura):
    consumo_medio = calcular_consumo_medio(inventory_df)
    saldo = calcular_saldo_atual(inventory_df)

    pedido_df = pd.merge(items_df[['Item ID', 'Name', 'Description']], saldo.reset_index(), on='Item ID', how='left')
    pedido_df = pd.merge(pedido_df, consumo_medio.reset_index(), on='Item ID', how='left', suffixes=('_Estoque', '_Consumo'))
    pedido_df = pedido_df.fillna({'Amount_Estoque': 0, 'Amount_Consumo': 0})

    pedido_df['Consumo Médio Diário'] = pedido_df['Amount_Consumo']
    pedido_df['Estoque Atual'] = pedido_df['Amount_Estoque']

    for dias in dias_cobertura:
        pedido_df[f'Necessidade {dias} dias'] = (pedido_df['Consumo Médio Diário'] * dias).round()  # Corrigido: adicionados parênteses
    
    # Cálculo de status baseado em limites
    pedido_df['Status'] = pd.cut(
        pedido_df['Estoque Atual'] / (pedido_df['Consumo Médio Diário'] + 0.001),  # +0.001 para evitar divisão por zero
        bins=[-float('inf'), DICIONARIO_LOGICO['critico_limite'], DICIONARIO_LOGICO['alerta_limite'], float('inf')],
        labels=['CRÍTICO', 'ALERTA', 'NORMAL']
    )
    
    # Cálculo da Quantidade a Pedir
    for dias in dias_cobertura:
        pedido_df[f'Pedir para {dias} dias'] = (
            pedido_df[f'Necessidade {dias} dias'] - pedido_df['Estoque Atual']
        ).apply(lambda x: max(0, x))  # Não permitir valores negativos
    
    return pedido_df

# -------------------- INTERFACE DO USUÁRIO --------------------
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📋 Pedidos", "📝 Dados Brutos"])

with tab1:
    st.header("Dashboard de Estoque")
    
    # Verificar se temos dados carregados
    if inventory_df.empty or items_df.empty:
        st.error("Não foi possível carregar os dados. Verifique as URLs das planilhas.")
    else:
        # Cálculos gerais
        total_items = len(items_df)
        total_movimentos = len(inventory_df)
        saldo_atual = calcular_saldo_atual(inventory_df)
        itens_em_estoque = len(saldo_atual[saldo_atual > 0])
        
        # Layout em colunas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total de Itens", total_items)
        with col2:
            st.metric("Movimentos Registrados", total_movimentos)
        with col3:
            st.metric("Itens em Estoque", itens_em_estoque)
        with col4:
            st.metric("Itens Sem Estoque", total_items - itens_em_estoque)
        
        # Gráfico de status
        st.subheader("Status do Estoque")
        pedido_df = gerar_pedido(DICIONARIO_LOGICO['dias_cobertura'])
        status_count = pedido_df['Status'].value_counts()
        
        st.bar_chart(status_count)
        
        # Exibir itens críticos
        st.subheader("Itens Críticos")
        itens_criticos = pedido_df[pedido_df['Status'] == 'CRÍTICO'][['Item ID', 'Name', 'Estoque Atual', 'Consumo Médio Diário']]
        
        if len(itens_criticos) > 0:
            st.dataframe(itens_criticos)
        else:
            st.success("Não há itens em estado crítico!")

with tab2:
    st.header("Geração de Pedidos")
    
    if inventory_df.empty or items_df.empty:
        st.error("Não foi possível carregar os dados. Verifique as URLs das planilhas.")
    else:
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.subheader("Configuração")
            dias_selecionados = st.multiselect(
                "Selecione os dias de cobertura:",
                options=DICIONARIO_LOGICO['dias_cobertura'],
                default=[30]
            )
            
            filtro_status = st.multiselect(
                "Filtrar por status:",
                options=['CRÍTICO', 'ALERTA', 'NORMAL'],
                default=['CRÍTICO', 'ALERTA']
            )
            
            mostrar_apenas_necessarios = st.checkbox("Mostrar apenas itens com necessidade de pedido", value=True)
        
        with col2:
            st.subheader("Pedido Gerado")
            
            if not dias_selecionados:
                st.warning("Selecione pelo menos um período de cobertura.")
            else:
                pedido_df = gerar_pedido(dias_selecionados)
                
                # Aplicar filtros
                pedido_filtrado = pedido_df[pedido_df['Status'].isin(filtro_status)]
                
                if mostrar_apenas_necessarios:
                    colunas_pedir = [col for col in pedido_filtrado.columns if col.startswith('Pedir para')]
                    tem_necessidade = False
                    for col in colunas_pedir:
                        tem_necessidade = tem_necessidade | (pedido_filtrado[col] > 0)
                    pedido_filtrado = pedido_filtrado[tem_necessidade]
                
                # Selecionar colunas para exibição
                colunas_exibir = ['Item ID', 'Name', 'Estoque Atual', 'Consumo Médio Diário', 'Status']
                for dias in dias_selecionados:
                    colunas_exibir.append(f'Necessidade {dias} dias')
                    colunas_exibir.append(f'Pedir para {dias} dias')
                
                st.dataframe(pedido_filtrado[colunas_exibir])
                
                # Botão para exportar
                if st.button("Exportar para CSV"):
                    csv = pedido_filtrado[colunas_exibir].to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "Baixar arquivo CSV",
                        csv,
                        f"pedido_cogex_{dias_selecionados[0]}_dias.csv",
                        "text/csv",
                        key='download-csv'
                    )

with tab3:
    st.header("Dados Brutos")
    
    if inventory_df.empty or items_df.empty:
        st.error("Não foi possível carregar os dados. Verifique as URLs das planilhas.")
    else:
        subtab1, subtab2 = st.tabs(["Inventário", "Itens"])
        
        with subtab1:
            st.subheader("Movimentações de Inventário")
            st.dataframe(inventory_df)
        
        with subtab2:
            st.subheader("Catálogo de Itens")
            st.dataframe(items_df)

# Rodapé
st.markdown("---")
st.markdown("**COGEX Almoxarifado** | Sistema desenvolvido para controle de estoque")
