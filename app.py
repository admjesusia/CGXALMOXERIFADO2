import streamlit as st
import pandas as pd
import datetime
import math
import csv
import io
import base64

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
st.set_page_config(page_title="COGEX Almoxarifado", layout="wide", page_icon="📦")

# Estilo CSS personalizado
st.markdown("""
<style>
    .css-18e3th9 {
        padding-top: 0rem;
        padding-bottom: 0rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        border-radius: 4px 4px 0px 0px;
        margin-right: 2px;
    }
    .item-card {
        border: 1px solid #e6e6e6;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 10px;
        background-color: #f9f9f9;
    }
    .critico {
        border-left: 5px solid #ff4b4b;
    }
    .alerta {
        border-left: 5px solid #ffa62b;
    }
    .normal {
        border-left: 5px solid #00cc96;
    }
    .status-badge {
        color: white;
        padding: 3px 8px;
        border-radius: 3px;
        font-weight: bold;
        font-size: 0.8em;
    }
    .critico-bg {
        background-color: #ff4b4b;
    }
    .alerta-bg {
        background-color: #ffa62b;
    }
    .normal-bg {
        background-color: #00cc96;
    }
    .cabecalho {
        display: flex;
        align-items: center;
        margin-bottom: 20px;
    }
    .logo {
        font-size: 40px;
        margin-right: 15px;
    }
    .titulo {
        flex-grow: 1;
    }
    .data-hora {
        color: #666;
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)

# Cabeçalho personalizado
data_atual = datetime.datetime.now().strftime("%d/%m/%Y - %H:%M")
st.markdown(f"""
<div class="cabecalho">
    <div class="logo">📦</div>
    <div class="titulo">
        <h1 style="margin: 0;">COGEX ALMOXARIFADO</h1>
        <p style="margin: 0; color: #666;">Sistema Web - Controle Matemático de Estoque - Pedido Automatizado</p>
    </div>
    <div class="data-hora">
        Atualizado em: {data_atual}
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------- CONFIGURAÇÕES --------------------
# Parâmetros para cálculos de estoque
CONFIGURACOES = {
    'dias_cobertura': [7, 15, 30, 45],
    'critico_limite': 7,           # Nível crítico em dias
    'alerta_limite': 15,           # Nível de alerta em dias
    'lead_time_medio': 5,          # Tempo médio em dias para recebimento após pedido
    'fator_seguranca': 1.2,        # Fator de segurança para cálculo de estoque
    'periodo_analise': 90          # Período para análise de consumo (dias)
}

# -------------------- CARREGAMENTO DE DADOS --------------------
@st.cache_data(ttl=300)
def load_data():
    """Carrega os dados das planilhas do Google Sheets ou usa dados offline"""
    # URLs das planilhas (substitua pelos URLs reais)
    url_items = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vRuJKYNnhiA5ikZ4-fx0P1kC1Y4ZCJ4VdnP9J9ZzuDj3Ct-5EXbgZRiBnRtCSPHfGSShbLkKLJlQTQ0/pub?output=csv'
    url_inventory = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vRuJKYNnhiA5ikZ4-fx0P1kC1Y4ZCJ4VdnP9J9ZzuDj3Ct-5EXbgZRiBnRtCSPHfGSShbLkKLJlQTQ0/pub?gid=1&single=true&output=csv'
    
    try:
        # Carrega os dados de itens
        items = pd.read_csv(url_items)
        items.dropna(subset=['Item ID', 'Name'], inplace=True)
        
        # Carrega os dados de inventário
        inventory = pd.read_csv(url_inventory)
        
        # Processamento de dados do inventário
        inventory['DateTime'] = pd.to_datetime(inventory['DateTime'], errors='coerce')
        inventory.dropna(subset=['Item ID', 'Amount'], inplace=True)
        
        # Converter ID para string para garantir compatibilidade
        items['Item ID'] = items['Item ID'].astype(str)
        inventory['Item ID'] = inventory['Item ID'].astype(str)
        
        return items, inventory
    
    except Exception as e:
        # Dados offline de backup para teste
        items = pd.DataFrame({
            'Item ID': ['4c44f391', 'cdb7c49d', 'a31fa3e6', '7185e46c', '4f0b6e6d', '874f4c45', 
                        '03bcd290', '22355245', '3809b5ae', 'f539ee95', '4551c5df', 'cadc39ff',
                        'e3886da9', 'c125aed6', 'faa39ab7', 'a500234e', '732098bc', '1e85205e',
                        '72e50b91', 'f4336c9', 'e9499711'],
            'Name': ['Água sanitária', 'Álcool gel', 'Álcool líquido', 'Copo Descartável 100 un', 
                     'Desinfetante', 'Desodorizador de Ambiente', 'Desentupidor', 'Detergente 500ml',
                     'Escova para Sanitário', 'Esponja dupla face', 'Flanela', 'Galão de Água',
                     'Guardanapo de Papel', 'Interfolhas pacote', 'Limpa porcelanato', 'Limpa vidros 1L',
                     'Lustra móveis', 'Luva de Borracha', 'Limpador multiuso', 'Pá de luxo', 'Palha de Aço'],
            'Description': ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
            'Image': ['Items_Images/4c44f391.Image.171510.jpg', 'Items_Images/cdb7c49d.Image.171546.jpg', 
                      'Items_Images/a31fa3e6.Image.171626.jpg', 'Items_Images/7185e46c.Image.171704.jpg',
                      'Items_Images/4f0b6e6d.Image.063627.jpg', 'Items_Images/874f4c45.Image.171913.jpg',
                      'Items_Images/03bcd290.Image.172037.jpg', '', 'Items_Images/3809b5ae.Image.172235.jpg',
                      'Items_Images/f539ee95.Image.172327.jpg', 'Items_Images/4551c5df.Image.172409.jpg',
                      'Items_Images/cadc39ff.Image.172842.jpg', 'Items_Images/e3886da9.Image.172956.jpg',
                      'Items_Images/c125aed6.Image.173055.jpg', 'Items_Images/faa39ab7.Image.173133.jpg',
                      'Items_Images/a500234e.Image.173237.jpg', 'Items_Images/732098bc.Image.173323.jpg',
                      'Items_Images/1e85205e.Image.173402.jpg', 'Items_Images/72e50b91.Image.173455.jpg',
                      'Items_Images/f4336c9.Image.173542.jpg', 'Items_Images/e9499711.Image.173636.jpg']
        })
        
        # Gerar dados realistas de inventário
        inventory_data = []
        
        # Entradas
        for i, item_id in enumerate(items['Item ID']):
            # Entradas iniciais
            inventory_data.append({
                'Inventory ID': f'a{i+100000}',
                'Item ID': item_id,
                'DateTime': '2025-04-01 10:00:00',
                'Amount': 20 + i % 10  # Estoque inicial variado
            })
            
            # Algumas entradas adicionais
            if i % 3 == 0:  # Para alguns itens, adicionar mais entradas
                inventory_data.append({
                    'Inventory ID': f'b{i+100000}',
                    'Item ID': item_id,
                    'DateTime': '2025-04-20 14:30:00',
                    'Amount': 5 + i % 5
                })
        
        # Saídas (consumo)
        for i, item_id in enumerate(items['Item ID']):
            # Várias saídas para simular consumo
            for j in range(3 + i % 5):  # Número variado de saídas
                amount = -(1 + i % 3)  # Consumo variado
                
                # Data da saída
                day = 5 + j * 2 + i % 5
                hour = 8 + j % 8
                
                inventory_data.append({
                    'Inventory ID': f'c{i*10+j+100000}',
                    'Item ID': item_id,
                    'DateTime': f'2025-04-{day:02d} {hour:02d}:00:00',
                    'Amount': amount
                })
        
        inventory = pd.DataFrame(inventory_data)
        inventory['DateTime'] = pd.to_datetime(inventory['DateTime'])
        
        # Registrar mensagem de uso de dados offline
        st.warning("Usando dados offline para testes. A conexão com o Google Sheets falhou.")
        
        return items, inventory

# Função para testar conexão com planilhas
def testar_conexao_planilhas():
    """Função para testar a conexão com as planilhas"""
    if st.sidebar.checkbox("Testar conexão com planilhas"):
        st.subheader("Teste de URLs das Planilhas")
        
        # URLs das planilhas
        url_items = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vRuJKYNnhiA5ikZ4-fx0P1kC1Y4ZCJ4VdnP9J9ZzuDj3Ct-5EXbgZRiBnRtCSPHfGSShbLkKLJlQTQ0/pub?output=csv'
        url_inventory = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vRuJKYNnhiA5ikZ4-fx0P1kC1Y4ZCJ4VdnP9J9ZzuDj3Ct-5EXbgZRiBnRtCSPHfGSShbLkKLJlQTQ0/pub?gid=1&single=true&output=csv'
        
        st.write("### URL dos Itens:")
        st.code(url_items)
        
        try:
            items = pd.read_csv(url_items)
            st.success(f"✅ Conectado com sucesso! Linhas: {len(items)}, Colunas: {len(items.columns)}")
            st.write("Amostra:")
            st.dataframe(items.head(3))
        except Exception as e:
            st.error(f"❌ Erro ao conectar: {str(e)}")
        
        st.write("### URL do Inventário:")
        st.code(url_inventory)
        
        try:
            inventory = pd.read_csv(url_inventory)
            st.success(f"✅ Conectado com sucesso! Linhas: {len(inventory)}, Colunas: {len(inventory.columns)}")
            st.write("Amostra:")
            st.dataframe(inventory.head(3))
        except Exception as e:
            st.error(f"❌ Erro ao conectar: {str(e)}")

# -------------------- FUNÇÕES MATEMÁTICAS --------------------
def calcular_consumo_medio(inventory, periodo_dias=90):
    """
    Calcula o consumo médio diário de cada item com base em dados históricos.
    
    Args:
        inventory: DataFrame com os dados de movimentação
        periodo_dias: Período em dias para considerar no cálculo
    
    Returns:
        Series com o consumo médio diário por Item ID
    """
    # Define o período de análise
    data_atual = inventory['DateTime'].max()
    data_inicio = data_atual - pd.Timedelta(days=periodo_dias)
    
    # Filtra movimentações do período
    periodo_inventory = inventory[inventory['DateTime'] >= data_inicio]
    
    # Se não houver dados no período, usa todos os dados disponíveis
    if len(periodo_inventory) == 0:
        periodo_inventory = inventory
    
    # Calcula o consumo (apenas saídas - valores negativos)
    consumo = periodo_inventory[periodo_inventory['Amount'] < 0].groupby('Item ID')['Amount'].sum().abs()
    
    # Calcula o período real em dias
    dias_reais = max(1, (periodo_inventory['DateTime'].max() - periodo_inventory['DateTime'].min()).days)
    dias_reais = min(dias_reais, periodo_dias)  # Limita ao período máximo definido
    
    # Calcula o consumo médio diário
    consumo_medio = consumo / dias_reais
    
    return consumo_medio

def calcular_saldo_atual(inventory):
    """
    Calcula o saldo atual de cada item somando todas as movimentações.
    
    Args:
        inventory: DataFrame com os dados de movimentação
    
    Returns:
        Series com o saldo atual por Item ID
    """
    saldo = inventory.groupby('Item ID')['Amount'].sum()
    return saldo

def calcular_estoque_seguranca(consumo_medio, lead_time=5, fator_seguranca=1.2):
    """
    Calcula o estoque de segurança para cada item.
    
    Args:
        consumo_medio: Series com o consumo médio diário
        lead_time: Tempo médio em dias para recebimento após pedido
        fator_seguranca: Fator multiplicador para garantir margem de segurança
    
    Returns:
        Series com o estoque de segurança por Item ID
    """
    return (consumo_medio * lead_time * fator_seguranca).round()

def calcular_ponto_pedido(consumo_medio, estoque_seguranca, lead_time=5):
    """
    Calcula o ponto de pedido para cada item.
    
    Args:
        consumo_medio: Series com o consumo médio diário
        estoque_seguranca: Series com o estoque de segurança
        lead_time: Tempo médio em dias para recebimento após pedido
    
    Returns:
        Series com o ponto de pedido por Item ID
    """
    return (consumo_medio * lead_time + estoque_seguranca).round()

def calcular_dias_estoque(saldo, consumo_medio):
    """
    Calcula por quantos dias o estoque atual durará.
    
    Args:
        saldo: Series com o saldo atual
        consumo_medio: Series com o consumo médio diário
    
    Returns:
        Series com os dias estimados de estoque por Item ID
    """
    dias = saldo / consumo_medio
    # Onde consumo_medio é zero, estabelece um valor grande
    dias = dias.replace([float('inf'), -float('inf')], float('nan'))
    return dias.fillna(999)  # 999 significa "estoque suficiente por muito tempo"

def gerar_pedido():
    """
    Gera dados para o pedido com base no consumo médio e saldo atual.
    
    Returns:
        DataFrame com os dados do pedido
    """
    # Calcular consumo médio considerando período de análise
    periodo = CONFIGURACOES['periodo_analise']
    consumo_medio = calcular_consumo_medio(inventory_df, periodo_dias=periodo)
    
    # Calcular saldo atual
    saldo = calcular_saldo_atual(inventory_df)
    
    # Calcular estoque de segurança e ponto de pedido
    estoque_seguranca = calcular_estoque_seguranca(
        consumo_medio, 
        lead_time=CONFIGURACOES['lead_time_medio'], 
        fator_seguranca=CONFIGURACOES['fator_seguranca']
    )
    
    ponto_pedido = calcular_ponto_pedido(
        consumo_medio, 
        estoque_seguranca, 
        lead_time=CONFIGURACOES['lead_time_medio']
    )
    
    # Calcular dias estimados de estoque
    dias_estoque = calcular_dias_estoque(saldo, consumo_medio)
    
    # Criar DataFrame base
    pedido_df = pd.merge(
        items_df[['Item ID', 'Name', 'Description']], 
        saldo.reset_index(), 
        on='Item ID', 
        how='left'
    )
    
    # Adicionar consumo médio
    pedido_df = pd.merge(
        pedido_df, 
        consumo_medio.reset_index(), 
        on='Item ID', 
        how='left', 
        suffixes=('_Estoque', '_Consumo')
    )
    
    # Preencher valores ausentes
    pedido_df = pedido_df.fillna({'Amount_Estoque': 0, 'Amount_Consumo': 0})
    
    # Renomear colunas
    pedido_df.rename(columns={
        'Amount_Estoque': 'Estoque Atual',
        'Amount_Consumo': 'Consumo Médio Diário'
    }, inplace=True)
    
    # Adicionar estoque de segurança e ponto de pedido
    pedido_df = pd.merge(
        pedido_df,
        estoque_seguranca.rename('Estoque Segurança').reset_index(),
        on='Item ID',
        how='left'
    )
    
    pedido_df = pd.merge(
        pedido_df,
        ponto_pedido.rename('Ponto de Pedido').reset_index(),
        on='Item ID',
        how='left'
    )
    
    # Adicionar dias estimados
    pedido_df = pd.merge(
        pedido_df,
        dias_estoque.rename('Dias Estimados').reset_index(),
        on='Item ID',
        how='left'
    )
    
    # Preencher valores ausentes
    pedido_df = pedido_df.fillna({
        'Estoque Segurança': 0,
        'Ponto de Pedido': 0,
        'Dias Estimados': 999
    })
    
    # Definir status baseado nos dias estimados
    pedido_df['Status'] = pd.cut(
        pedido_df['Dias Estimados'],
        bins=[0, CONFIGURACOES['critico_limite'], CONFIGURACOES['alerta_limite'], float('inf')],
        labels=['CRÍTICO', 'ALERTA', 'NORMAL']
    )
    
    # Adicionar flag para indicar se precisa pedir
    pedido_df['Precisa Pedir'] = pedido_df['Estoque Atual'] < pedido_df['Ponto de Pedido']
    
    # Calcular necessidade para cada período de cobertura
    for dias in CONFIGURACOES['dias_cobertura']:
        pedido_df[f'Necessidade {dias} dias'] = (pedido_df['Consumo Médio Diário'] * dias).round()
        
        # Calcular quantidade a pedir
        pedido_df[f'Pedir para {dias} dias'] = (
            pedido_df[f'Necessidade {dias} dias'] + 
            pedido_df['Estoque Segurança'] - 
            pedido_df['Estoque Atual']
        ).apply(lambda x: max(0, x))
    
    return pedido_df

# Função para exportar para CSV
def get_table_download_link(df, filename="dados.csv", text="Baixar CSV"):
    """
    Gera um link para download de um DataFrame como CSV
    """
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href

# -------------------- COMPONENTES DE INTERFACE --------------------
def criar_card_item(row):
    """
    Cria um card HTML para exibir informações de um item
    """
    status_class = row['Status'].lower() if isinstance(row['Status'], str) else 'normal'
    
    # Formatação de valores
    estoque_atual = int(row['Estoque Atual'])
    ponto_pedido = int(row['Ponto de Pedido'])
    consumo_diario = f"{row['Consumo Médio Diário']:.2f}"
    
    # Cálculo de porcentagem para a barra de progresso
    if ponto_pedido > 0:
        porcentagem = min(100, (estoque_atual / ponto_pedido) * 100)
    else:
        porcentagem = 100
    
    # Cor da barra de progresso baseada no status
    if status_class == 'critico':
        cor_barra = "#ff4b4b"
    elif status_class == 'alerta':
        cor_barra = "#ffa62b"
    else:
        cor_barra = "#00cc96"
    
    # Formatação dos dias estimados
    if row['Dias Estimados'] >= 100:
        dias_texto = "99+"
    else:
        dias_texto = f"{row['Dias Estimados']:.1f}"
    
    # Criar o card HTML
    html = f"""
    <div class="item-card {status_class}">
        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
            <h3 style="margin: 0;">{row['Name']}</h3>
            <span class="status-badge {status_class}-bg">{row['Status']}</span>
        </div>
        <p style="color: #666; margin: 5px 0;">ID: {row['Item ID']}</p>
        <div style="margin: 10px 0;">
            <p style="margin: 0; font-size: 0.9em;">Nível de Estoque:</p>
            <div style="background-color: #e6e6e6; border-radius: 3px; height: 10px; width: 100%;">
                <div style="background-color: {cor_barra}; width: {porcentagem}%; height: 100%; border-radius: 3px;"></div>
            </div>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 10px;">
            <div>
                <p style="margin: 0; font-size: 0.8em;">Estoque Atual</p>
                <p style="margin: 0; font-weight: bold;">{estoque_atual}</p>
            </div>
            <div>
                <p style="margin: 0; font-size: 0.8em;">Ponto de Pedido</p>
                <p style="margin: 0; font-weight: bold;">{ponto_pedido}</p>
            </div>
            <div>
                <p style="margin: 0; font-size: 0.8em;">Consumo Diário</p>
                <p style="margin: 0; font-weight: bold;">{consumo_diario}</p>
            </div>
            <div>
                <p style="margin: 0; font-size: 0.8em;">Dias Restantes</p>
                <p style="margin: 0; font-weight: bold;">{dias_texto}</p>
            </div>
        </div>
    </div>
    """
    return html

def mostrar_barra_status(valor, maximo, cor="#00cc96", texto=""):
    """
    Exibe uma barra de progresso estilizada
    """
    percentual = min(1.0, valor / max(1, maximo))
    st.markdown(f"""
        <div style="margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <span>{texto}</span>
                <span>{valor}/{maximo} ({percentual:.1%})</span>
            </div>
            <div style="background-color: #e6e6e6; border-radius: 3px; height: 10px; width: 100%;">
                <div style="background-color: {cor}; width: {percentual * 100}%; height: 100%; border-radius: 3px;"></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# Opções no sidebar
def sidebar_settings():
    """Configurações no sidebar"""
    st.sidebar.title("Configurações")
    
    if st.sidebar.checkbox("Mostrar Informações de Sistema"):
        st.sidebar.write("### Sistema")
        st.sidebar.write(f"Usuário: {st.session_state.get('usuario', 'N/A')}")
        st.sidebar.write(f"Python: {pd.__version__}")
        st.sidebar.write(f"Streamlit: {st.__version__}")
    
    # Período de análise
    st.sidebar.subheader("Parâmetros de Cálculo")
    periodo = st.sidebar.slider(
        "Período de análise (dias):",
        min_value=30,
        max_value=180,
        value=CONFIGURACOES['periodo_analise'],
        step=15
    )
    
    # Lead time
    lead_time = st.sidebar.slider(
        "Lead time médio (dias):",
        min_value=1,
        max_value=30,
        value=CONFIGURACOES['lead_time_medio']
    )
    
    # Fator de segurança
    fator_seguranca = st.sidebar.slider(
        "Fator de segurança:",
        min_value=1.0,
        max_value=2.0,
        value=CONFIGURACOES['fator_seguranca'],
        step=0.1
    )
    
    # Atualizar configurações
    CONFIGURACOES['periodo_analise'] = periodo
    CONFIGURACOES['lead_time_medio'] = lead_time
    CONFIGURACOES['fator_seguranca'] = fator_seguranca
    
    return CONFIGURACOES

# Carrega dados e configurações
sidebar_settings()
testar_conexao_planilhas()
items_df, inventory_df = load_data()

# -------------------- INTERFACE DO USUÁRIO --------------------
tabs = st.tabs(["📊 Dashboard", "🚨 Alerta de Estoque", "📋 Pedidos", "📉 Consumo", "📝 Dados Brutos"])

with tabs[0]:  # Dashboard
    st.header("Dashboard de Estoque")
    
    # Verificar se temos dados carregados
    if inventory_df.empty or items_df.empty:
        st.error("Não foi possível carregar os dados. Verifique as URLs das planilhas.")
    else:
        # Gerar dados para o dashboard
        pedido_df = gerar_pedido()
        
        # Métricas gerais
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_items = len(items_df)
            st.metric("Total de Itens", total_items)
        
        with col2:
            itens_criticos = len(pedido_df[pedido_df['Status'] == 'CRÍTICO'])
            st.metric("Itens Críticos", itens_criticos, 
                     delta="-" if itens_criticos == 0 else None,
                     delta_color="inverse")
        
        with col3:
            itens_alerta = len(pedido_df[pedido_df['Status'] == 'ALERTA'])
            st.metric("Itens em Alerta", itens_alerta)
        
        with col4:
            itens_abaixo_ponto = len(pedido_df[pedido_df['Precisa Pedir']])
            st.metric("Abaixo do Ponto de Pedido", itens_abaixo_ponto)
        
        # Gráfico de status
        st.subheader("Status do Estoque")
        
        status_count = pedido_df['Status'].value_counts()
        status_data = pd.DataFrame({
            'Status': status_count.index,
            'Quantidade': status_count.values
        })
        
        # Criar gráfico de barras horizontal usando barras estilizadas
        cores_status = {
            'CRÍTICO': '#ff4b4b',
            'ALERTA': '#ffa62b',
            'NORMAL': '#00cc96'
        }
        
        for idx, row in status_data.iterrows():
            status = row['Status']
            quantidade = row['Quantidade']
            mostrar_barra_status(
                quantidade, 
                total_items, 
                cor=cores_status.get(status, '#00cc96'),
                texto=status
            )
        
        # Painel de itens críticos
        st.subheader("🚨 Itens Críticos")
        
        # Filtrar itens críticos que precisam de pedido
        itens_criticos_df = pedido_df[pedido_df['Status'] == 'CRÍTICO'].sort_values('Dias Estimados')
        
        if len(itens_criticos_df) > 0:
            # Limitar aos 3 mais críticos para o dashboard
            top3_criticos = itens_criticos_df.head(3)
            
            col1, col2, col3 = st.columns(3)
            cols = [col1, col2, col3]
            
            for i, (idx, row) in enumerate(top3_criticos.iterrows()):
                with cols[i % 3]:
                    html_card = criar_card_item(row)
                    st.markdown(html_card, unsafe_allow_html=True)
            
            if len(itens_criticos_df) > 3:
                with st.expander(f"Ver mais {len(itens_criticos_df) - 3} itens críticos"):
                    for idx, row in itens_criticos_df.iloc[3:].iterrows():
                        st.markdown(criar_card_item(row), unsafe_allow_html=True)
        else:
            st.success("Não há itens críticos no momento!")
        
        # Resumo de consumo
        st.subheader("📊 Resumo de Consumo")
        
        # Itens mais consumidos
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Top 5 Itens Mais Consumidos:**")
            
            # Filtrar itens com consumo e ordenar
            top_consumo = pedido_df[pedido_df['Consumo Médio Diário'] > 0].sort_values('Consumo Médio Diário', ascending=False).head(5)
            
            if len(top_consumo) > 0:
                for idx, row in top_consumo.iterrows():
                    st.markdown(f"**{row['Name']}**: {row['Consumo Médio Diário']:.2f}/dia")
            else:
                st.info("Não há dados de consumo disponíveis.")
        
        with col2:
            st.write("**Itens com Baixo Giro:**")
            
            # Filtrar itens com baixo giro (consumo baixo e estoque alto)
            baixo_giro = pedido_df[
                (pedido_df['Consumo Médio Diário'] > 0) & 
                (pedido_df['Dias Estimados'] > 60)
            ].sort_values('Dias Estimados', ascending=False).head(5)
            
            if len(baixo_giro) > 0:
                for idx, row in baixo_giro.iterrows():
                    dias = row['Dias Estimados']
                    if dias >= 100:
                        dias_texto = "99+ dias"
                    else:
                        dias_texto = f"{dias:.1f} dias"
                    
                    st.markdown(f"**{row['Name']}**: Estoque para {dias_texto}")
            else:
                st.info("Não há itens com baixo giro identificados.")

with tabs[1]:  # Alerta de Estoque
    st.header("Alerta de Estoque")
    
    if inventory_df.empty or items_df.empty:
        st.error("Não foi possível carregar os dados. Verifique as URLs das planilhas.")
    else:
        # Gerar dados
        pedido_df = gerar_pedido()
        
        # Filtros
        col1, col2 = st.columns(2)
        
        with col1:
            filtro_status = st.multiselect(
                "Filtrar por status:",
                options=['CRÍTICO', 'ALERTA', 'NORMAL'],
                default=['CRÍTICO', 'ALERTA']
            )
        
        with col2:
            apenas_abaixo_ponto = st.checkbox(
                "Mostrar apenas itens abaixo do ponto de pedido", 
                value=True
            )
        
        # Aplicar filtros
        itens_filtrados = pedido_df[pedido_df['Status'].isin(filtro_status)].copy()
        
        if apenas_abaixo_ponto:
            itens_filtrados = itens_filtrados[itens_filtrados['Precisa Pedir']]
        
        # Ordenar por criticidade
        itens_filtrados = itens_filtrados.sort_values(['Status', 'Dias Estimados'])
        
        # Exibir resultados
        if len(itens_filtrados) > 0:
            st.write(f"Encontrados **{len(itens_filtrados)}** itens que atendem aos critérios.")
            
            # Agrupar por status
            for status in filtro_status:
                itens_status = itens_filtrados[itens_filtrados['Status'] == status]
                
                if len(itens_status) > 0:
                    st.subheader(f"{status} ({len(itens_status)} itens)")
                    
                    # Criar uma grade de 3 colunas para os cards
                    cols = st.columns(3)
                    
                    for i, (idx, row) in enumerate(itens_status.iterrows()):
                        with cols[i % 3]:
                            html_card = criar_card_item(row)
                            st.markdown(html_card, unsafe_allow_html=True)
        else:
            st.success("Não há itens que atendam aos critérios de filtro!")
        
        # Exportar resultados
        if len(itens_filtrados) > 0:
            st.markdown("### Exportar Resultados")
            
            colunas_exportar = [
                'Item ID', 'Name', 'Estoque Atual', 'Consumo Médio Diário', 
                'Ponto de Pedido', 'Dias Estimados', 'Status'
            ]
            
            csv = itens_filtrados[colunas_exportar].to_csv(index=False).encode('utf-8')
            
            data_atual = datetime.datetime.now().strftime("%Y%m%d")
            st.download_button(
                "📄 Baixar Relatório de Alerta (CSV)",
                csv,
                f"alerta_estoque_cogex_{data_atual}.csv",
                "text/csv"
            )

with tabs[2]:  # Pedidos
    st.header("Geração de Pedidos")
    
    if inventory_df.empty or items_df.empty:
        st.error("Não foi possível carregar os dados. Verifique as URLs das planilhas.")
    else:
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.subheader("Configuração do Pedido")
            
            dias_selecionados = st.multiselect(
                "Selecione os dias de cobertura:",
                options=CONFIGURACOES['dias_cobertura'],
                default=[30]
            )
            
            filtro_status = st.multiselect(
                "Filtrar por status:",
                options=['CRÍTICO', 'ALERTA', 'NORMAL'],
                default=['CRÍTICO', 'ALERTA']
            )
            
            mostrar_apenas_necessarios = st.checkbox(
                "Mostrar apenas itens com necessidade", 
                value=True
            )
            
            apenas_abaixo_ponto_pedido = st.checkbox(
                "Mostrar apenas itens abaixo do ponto de pedido", 
                value=True
            )
            
            data_pedido = st.date_input(
                "Data do Pedido",
                value=datetime.datetime.now().date()
            )
            
            responsavel = st.text_input(
                "Responsável",
                value="Administrador COGEX"
            )
        
        with col2:
            st.subheader("Pedido Gerado")
            
            if not dias_selecionados:
                st.warning("Selecione pelo menos um período de cobertura.")
            else:
                pedido_df = gerar_pedido()
                
                # Aplicar filtros
                pedido_filtrado = pedido_df[pedido_df['Status'].isin(filtro_status)].copy()
                
                if apenas_abaixo_ponto_pedido:
                    pedido_filtrado = pedido_filtrado[pedido_filtrado['Precisa Pedir']]
                
                if mostrar_apenas_necessarios:
                    colunas_pedir = [col for col in pedido_filtrado.columns if col.startswith('Pedir para')]
                    dias_selecionados_cols = [f'Pedir para {dias} dias' for dias in dias_selecionados if f'Pedir para {dias} dias' in colunas_pedir]
                    
                    if dias_selecionados_cols:
                        tem_necessidade = pedido_filtrado[dias_selecionados_cols].sum(axis=1) > 0
                        pedido_filtrado = pedido_filtrado[tem_necessidade]
                
                # Selecionar colunas para exibição
                colunas_exibir = [
                    'Item ID', 'Name', 'Estoque Atual', 'Consumo Médio Diário', 
                    'Ponto de Pedido', 'Status'
                ]
                
                # Adicionar colunas de necessidade e pedido para os dias selecionados
                for dias in dias_selecionados:
                    colunas_exibir.append(f'Pedir para {dias} dias')
                
                # Exibir dados do pedido
                if len(pedido_filtrado) > 0:
                    st.dataframe(pedido_filtrado[colunas_exibir], hide_index=True)
                    
                    # Resumo do pedido
                    st.subheader("Resumo do Pedido")
                    
                    resumo_col1, resumo_col2, resumo_col3 = st.columns(3)
                    
                    with resumo_col1:
                        st.info(f"**Total de Itens:** {len(pedido_filtrado)}")
                    
                    with resumo_col2:
                        st.info(f"**Data do Pedido:** {data_pedido.strftime('%d/%m/%Y')}")
                    
                    with resumo_col3:
                        st.info(f"**Responsável:** {responsavel}")
                    
                    # Botões para exportar
                    col_btn1, col_btn2 = st.columns(2)
                    
                    with col_btn1:
                        csv = pedido_filtrado[colunas_exibir].to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "📄 Baixar Pedido (CSV)",
                            csv,
                            f"pedido_cogex_{data_pedido.strftime('%Y%m%d')}_{dias_selecionados[0]}_dias.csv",
                            "text/csv",
                            key='download-csv'
                        )
                    
                    with col_btn2:
                        # Criar versão para impressão
                        colunas_impressao = ['Item ID', 'Name', 'Estoque Atual']
                        for dias in dias_selecionados:
                            colunas_impressao.append(f'Pedir para {dias} dias')
                        
                        pdf_data = pedido_filtrado[colunas_impressao].copy()
                        
                        # Adicionar colunas para controle manual
                        pdf_data['Quantidade Pedida'] = ""
                        pdf_data['Fornecedor'] = ""
                        pdf_data['Data Prevista'] = ""
                        
                        csv_print = pdf_data.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "🖨️ Versão para Impressão (CSV)",
                            csv_print,
                            f"pedido_impressao_cogex_{data_pedido.strftime('%Y%m%d')}.csv",
                            "text/csv",
                            key='download-print'
                        )
                else:
                    st.success("Não há itens que atendam aos critérios selecionados.")

with tabs[3]:  # Consumo
    st.header("Análise de Consumo")
    
    if inventory_df.empty or items_df.empty:
        st.error("Não foi possível carregar os dados. Verifique as URLs das planilhas.")
    else:
        # Calcular consumo médio
        pedido_df = gerar_pedido()
        
        # Filtrar itens com consumo
        itens_com_consumo = pedido_df[pedido_df['Consumo Médio Diário'] > 0].copy()
        
        if len(itens_com_consumo) > 0:
            # Mostrar top consumidores
            st.subheader("Top 10 Itens Mais Consumidos")
            
            # Ordenar por consumo
            top_consumo = itens_com_consumo.sort_values('Consumo Médio Diário', ascending=False).head(10)
            
            # Criar gráfico de barras horizontais estilizado
            max_consumo = top_consumo['Consumo Médio Diário'].max()
            
            for idx, row in top_consumo.iterrows():
                col1, col2, col3 = st.columns([2, 3, 1])
                
                with col1:
                    st.write(f"**{row['Name']}**")
                
                with col2:
                    # Determinar cor baseada no status
                    if row['Status'] == 'CRÍTICO':
                        cor = '#ff4b4b'
                    elif row['Status'] == 'ALERTA':
                        cor = '#ffa62b'
                    else:
                        cor = '#00cc96'
                    
                    # Calcular largura da barra
                    percentual = row['Consumo Médio Diário'] / max_consumo
                    
                    # Criar barra estilizada
                    st.markdown(f"""
                        <div style="background-color: #e6e6e6; border-radius: 3px; height: 20px; width: 100%;">
                            <div style="background-color: {cor}; width: {percentual * 100}%; height: 100%; border-radius: 3px;"></div>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.write(f"{row['Consumo Médio Diário']:.2f}/dia")
            
            # Análise por Item
            st.subheader("Detalhes por Item")
            
            # Seleção de item
            item_selecionado = st.selectbox(
                "Selecione um item para análise detalhada:",
                options=itens_com_consumo['Item ID'].tolist(),
                format_func=lambda x: f"{x} - {itens_com_consumo[itens_com_consumo['Item ID'] == x]['Name'].iloc[0]}"
            )
            
            # Exibir detalhes do item selecionado
            if item_selecionado:
                # Obter dados do item
                item_dados = itens_com_consumo[itens_com_consumo['Item ID'] == item_selecionado].iloc[0]
                
                # Filtrar movimentações do item
                item_movs = inventory_df[inventory_df['Item ID'] == item_selecionado].sort_values('DateTime')
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"### {item_dados['Name']}")
                    st.markdown(f"**ID:** {item_dados['Item ID']}")
                    st.markdown(f"**Consumo Médio:** {item_dados['Consumo Médio Diário']:.2f} unidades/dia")
                    st.markdown(f"**Estoque Atual:** {item_dados['Estoque Atual']:.0f} unidades")
                    st.markdown(f"**Ponto de Pedido:** {item_dados['Ponto de Pedido']:.0f} unidades")
                    
                    # Status formatado
                    status = item_dados['Status']
                    cor_status = {
                        'CRÍTICO': '#ff4b4b',
                        'ALERTA': '#ffa62b',
                        'NORMAL': '#00cc96'
                    }.get(status, '#00cc96')
                    
                    st.markdown(f"""
                        <div style="margin-top: 10px;">
                            <span style="background-color: {cor_status}; color: white; padding: 3px 8px; border-radius: 3px;">
                                {status}
                            </span>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    # Calcular estatísticas
                    total_entradas = item_movs[item_movs['Amount'] > 0]['Amount'].sum()
                    total_saidas = abs(item_movs[item_movs['Amount'] < 0]['Amount'].sum())
                    dias_cobertos = min(999, item_dados['Estoque Atual'] / max(0.001, item_dados['Consumo Médio Diário']))
                    
                    # Exibir métricas
                    st.metric("Total de Entradas", f"{total_entradas:.0f}")
                    st.metric("Total de Saídas", f"{total_saidas:.0f}")
                    st.metric("Dias de Cobertura", f"{dias_cobertos:.1f}")
                
                # Movimentações recentes
                st.subheader("Movimentações Recentes")
                
                if len(item_movs) > 0:
                    # Calcular saldo acumulado
                    item_movs['Saldo Acumulado'] = item_movs['Amount'].cumsum()
                    
                    # Exibir tabela de movimentações
                    st.dataframe(
                        item_movs[['DateTime', 'Amount', 'Saldo Acumulado']].rename(
                            columns={
                                'DateTime': 'Data/Hora',
                                'Amount': 'Quantidade',
                                'Saldo Acumulado': 'Saldo'
                            }
                        ),
                        hide_index=True
                    )
                else:
                    st.info("Não há movimentações registradas para este item.")
        else:
            st.info("Não há dados de consumo disponíveis para análise.")

with tabs[4]:  # Dados Brutos
    st.header("Dados Brutos")
    
    if inventory_df.empty or items_df.empty:
        st.error("Não foi possível carregar os dados. Verifique as URLs das planilhas.")
    else:
        subtab1, subtab2 = st.tabs(["Inventário", "Itens"])
        
        with subtab1:
            st.subheader("Movimentações de Inventário")
            
            # Opções de filtro
            col1, col2 = st.columns(2)
            
            with col1:
                filtro_periodo = st.selectbox(
                    "Filtrar por período:",
                    ["Todas as movimentações", "Últimos 7 dias", "Últimos 30 dias", "Últimos 90 dias"]
                )
            
            with col2:
                filtro_tipo = st.multiselect(
                    "Filtrar por tipo:",
                    ["Entradas", "Saídas"],
                    default=["Entradas", "Saídas"]
                )
            
            # Aplicar filtros
            inventory_filtrado = inventory_df.copy()
            
            # Filtro de período
            if filtro_periodo == "Últimos 7 dias":
                data_limite = inventory_df['DateTime'].max() - pd.Timedelta(days=7)
                inventory_filtrado = inventory_filtrado[inventory_filtrado['DateTime'] >= data_limite]
            elif filtro_periodo == "Últimos 30 dias":
                data_limite = inventory_df['DateTime'].max() - pd.Timedelta(days=30)
                inventory_filtrado = inventory_filtrado[inventory_filtrado['DateTime'] >= data_limite]
            elif filtro_periodo == "Últimos 90 dias":
                data_limite = inventory_df['DateTime'].max() - pd.Timedelta(days=90)
                inventory_filtrado = inventory_filtrado[inventory_filtrado['DateTime'] >= data_limite]
            
            # Filtro de tipo
            filtros_aplicados = []
            if "Entradas" in filtro_tipo:
                filtros_aplicados.append(inventory_filtrado['Amount'] > 0)
            if "Saídas" in filtro_tipo:
                filtros_aplicados.append(inventory_filtrado['Amount'] < 0)
            
            if filtros_aplicados:
                mask = pd.concat(filtros_aplicados, axis=1).any(axis=1)
                inventory_filtrado = inventory_filtrado[mask]
            
            # Adicionar nomes dos itens
            inventory_view = pd.merge(
                inventory_filtrado,
                items_df[['Item ID', 'Name']],
                on='Item ID',
                how='left'
            ).fillna({'Name': 'Item não cadastrado'})
            
            inventory_view['Tipo'] = inventory_view['Amount'].apply(lambda x: 'Entrada' if x > 0 else 'Saída')
            
            # Ordenar por data (mais recente primeiro)
            inventory_view = inventory_view.sort_values('DateTime', ascending=False)
            
            # Exibir dados
            st.dataframe(
                inventory_view[['Inventory ID', 'Item ID', 'Name', 'DateTime', 'Amount', 'Tipo']].rename(
                    columns={
                        'Inventory ID': 'ID Movimentação',
                        'Item ID': 'ID Item',
                        'Name': 'Nome do Item',
                        'DateTime': 'Data/Hora',
                        'Amount': 'Quantidade',
                        'Tipo': 'Tipo de Movimentação'
                    }
                ),
                hide_index=True
            )
            
            # Botão para exportar
            if len(inventory_view) > 0:
                csv = inventory_view.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📄 Exportar Movimentações (CSV)",
                    csv,
                    f"movimentacoes_cogex_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
        
        with subtab2:
            st.subheader("Catálogo de Itens")
            
            # Opção de busca
            busca = st.text_input("Buscar item por nome ou ID:")
            
            # Aplicar filtro de busca
            if busca:
                items_filtrado = items_df[
                    items_df['Item ID'].str.contains(busca, case=False) |
                    items_df['Name'].str.contains(busca, case=False)
                ]
            else:
                items_filtrado = items_df
            
            # Exibir dados
            st.dataframe(
                items_filtrado,
                hide_index=True
            )
            
            # Botão para exportar
            if len(items_filtrado) > 0:
                csv = items_filtrado.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📄 Exportar Catálogo de Itens (CSV)",
                    csv,
                    f"catalogo_itens_cogex_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )

# Rodapé
st.markdown("---")
st.markdown(f"""
<div style="display: flex; justify-content: space-between; align-items: center;">
    <div>**COGEX Almoxarifado** | Sistema de Controle de Estoque - v1.0</div>
    <div style="color: #666;">Desenvolvido para gerenciamento eficiente de estoque</div>
</div>
""", unsafe_allow_html=True)
