import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAÇÃO E LIGAÇÃO ---
st.set_page_config(page_title="Distrito Pro 2026", layout="wide", page_icon="🛡️")

# URL da sua planilha (Certifique-se que o e-mail do robô é Editor nela)
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1y3vAXagtbdzaTHGEkPOuWI3TvzcfFYhfO1JUt0GrhG8/edit?usp=sharing"

# Criando a conexão com os Secrets que você configurou
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. FUNÇÕES DE DADOS (COM LIMPEZA DE CACHE) ---

def carregar_dados():
    # ttl=0 faz com que ele tente buscar dados novos sempre que possível
    try:
        df_p = conn.read(spreadsheet=URL_PLANILHA, worksheet="Presencas", ttl=0)
        df_v = conn.read(spreadsheet=URL_PLANILHA, worksheet="Visitantes", ttl=0)
        
        # Converter colunas de data para o formato correto
        if not df_p.empty:
            df_p['Data'] = pd.to_datetime(df_p['Data'])
        if not df_v.empty:
            df_v['Data'] = pd.to_datetime(df_v['Data'])
            
        return df_p, df_v
    except Exception as e:
        # Retorna dataframes vazios se a planilha estiver zerada
        df_p = pd.DataFrame(columns=["Data", "Líder", "Nome", "Tipo", "Célula", "Culto"])
        df_v = pd.DataFrame(columns=["Data", "Líder", "Vis_Celula", "Vis_Culto"])
        return df_p, df_v

# INICIALIZAÇÃO: Busca os dados no Google Sheets ao abrir ou dar F5
# Removendo a trava do 'if not in session_state' para garantir atualização no F5
db_p, db_v = carregar_dados()
st.session_state.db = db_p
st.session_state.db_visitantes = db_v

if 'membros_cadastrados' not in st.session_state:
    st.session_state.membros_cadastrados = {}

# --- [RESTANTE DO CÓDIGO DE ESTILO E VARIÁVEIS] ---
st.markdown("""
<style>
    .stApp { background-color: #0F172A; color: #F8FAFC; }
    .main-title { background: linear-gradient(90deg, #00D4FF 0%, #0072FF 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; font-size: 38px; text-align: center; margin-bottom: 20px; }
    .metric-card { background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); padding: 15px; border-radius: 12px; border: 1px solid #334155; text-align: center; margin-bottom: 10px; }
    .metric-value-cel { color: #00D4FF; font-size: 24px; font-weight: 800; }
    .metric-value-cul { color: #EF4444; font-size: 24px; font-weight: 800; }
    .member-card { background: #1E293B; padding: 12px; border-radius: 15px; border: 1px solid #334155; margin-top: 15px; }
</style>
""", unsafe_allow_html=True)

MESES_NOMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MESES_MAP = {n: i+1 for i, n in enumerate(MESES_NOMES)}

def get_sabados(mes_nome, ano=2026):
    mes_int = MESES_MAP[mes_nome]
    d = date(ano, mes_int, 1)
    while d.weekday() != 5: d += timedelta(days=1)
    sats = []
    while d.month == mes_int: sats.append(pd.to_datetime(d)); d += timedelta(days=7)
    return sats

lideres_lista = sorted(list(st.session_state.membros_cadastrados.keys()))

# --- INTERFACE ---
st.markdown('<p class="main-title">🛡️ DISTRITO PRO 2026</p>', unsafe_allow_html=True)
lids_f = st.multiselect("Filtrar Células:", lideres_lista, default=lideres_lista)

tab_dash, tab_lanc, tab_ob, tab_gestao = st.tabs(["📊 DASHBOARD", "📝 LANÇAR", "📋 RELATÓRIO OB", "⚙️ GESTÃO"])

# --- ABA 1: DASHBOARD ---
with tab_dash:
    if st.session_state.db.empty:
        st.info("💡 Sem dados gravados na nuvem. Lance as chamadas primeiro.")
    else:
        # Seletores e lógica de gráficos (igual ao anterior)
        c_m, c_s = st.columns(2)
        mes_dash = c_m.selectbox("📅 Mês de Referência:", MESES_NOMES, index=date.today().month - 1)
        mes_num = MESES_MAP[mes_dash]
        
        df_mes = st.session_state.db[st.session_state.db['Data'].dt.month == mes_num]
        if not df_mes.empty:
            datas_disp = sorted(df_mes['Data'].unique(), reverse=True)
            data_resumo = c_s.selectbox("🔎 Ver Semana:", datas_disp, format_func=lambda x: x.strftime('%d/%m/%Y'))
            st.subheader(f"📍 Resumo: {data_resumo.strftime('%d/%m')}")
            # ... (Cartões de métricas)
            st.success("Dados carregados do Google Sheets ✅")

# --- ABA 2: LANÇAR (A PARTE QUE SALVA) ---
with tab_lanc:
    if not lideres_lista:
        st.info("Cadastre líderes em GESTÃO")
    else:
        la, lb, lc = st.columns(3)
        m_l = la.selectbox("Mês", MESES_NOMES, key="m_l")
        d_l = lb.selectbox("Sábado", get_sabados(m_l), format_func=lambda x: x.strftime('%d/%m'), key="d_l")
        l_l = lc.selectbox("Líder", lideres_lista, key="l_l")
        
        membros = st.session_state.membros_cadastrados.get(l_l, {})
        # ... (interface de botões de check)

        if st.button("💾 SALVAR E SINCRONIZAR", use_container_width=True, type="primary"):
            dt = pd.to_datetime(d_l)
            
            # 1. Prepara novos dados
            novos_p = pd.DataFrame([{"Data": dt, "Líder": l_l, "Nome": n, "Tipo": t, "Célula": 1 if st.session_state.get(f"ce_{l_l}_{n}_{d_l}",0) else 0, "Culto": 1 if st.session_state.get(f"cu_{l_l}_{n}_{d_l}",0) else 0} for n, t in membros.items()])
            novos_v = pd.DataFrame([{"Data": dt, "Líder": l_l, "Vis_Celula": 0, "Vis_Culto": 0}]) # Simplificado para o exemplo
            
            # 2. Atualiza o banco local
            st.session_state.db = pd.concat([st.session_state.db[~((st.session_state.db['Data']==dt) & (st.session_state.db['Líder']==l_l))], novos_p], ignore_index=True)
            st.session_state.db_visitantes = pd.concat([st.session_state.db_visitantes[~((st.session_state.db_visitantes['Data']==dt) & (st.session_state.db_visitantes['Líder']==l_l))], novos_v], ignore_index=True)
            
            # 3. ENVIA PARA O GOOGLE
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Presencas", data=st.session_state.db)
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Visitantes", data=st.session_state.db_visitantes)
            
            # 4. LIMPA O CACHE PARA O F5 FUNCIONAR
            st.cache_data.clear()
            
            st.success("Dados enviados para a Nuvem! Pode dar F5 agora.")
            st.balloons()
