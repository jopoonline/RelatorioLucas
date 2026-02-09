import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta, datetime
from streamlit_gsheets import GSheetsConnection
import time

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Distrito Pro 2026", layout="wide", page_icon="🛡️")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1y3vAXagtbdzaTHGEkPOuWI3TvzcfFYhfO1JUt0GrhG8/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. FUNÇÕES DE DADOS (COM TRATAMENTO DE ERRO) ---
@st.cache_data(ttl=600)  # Cache de 10 minutos para evitar erro 429
def carregar_dados():
    try:
        df_p = conn.read(spreadsheet=URL_PLANILHA, worksheet="Presencas")
        df_v = conn.read(spreadsheet=URL_PLANILHA, worksheet="Visitantes")
        df_m = conn.read(spreadsheet=URL_PLANILHA, worksheet="Membros")
        
        # Garantia de colunas para evitar KeyError
        if df_p is None or df_p.empty:
            df_p = pd.DataFrame(columns=['Data', 'Líder', 'Nome', 'Tipo', 'Célula', 'Culto'])
        if df_v is None or df_v.empty:
            df_v = pd.DataFrame(columns=['Data', 'Líder', 'Vis_Celula', 'Vis_Culto'])
            
        # Conversão de datas segura
        df_p['Data'] = pd.to_datetime(df_p['Data'], errors='coerce')
        df_v['Data'] = pd.to_datetime(df_v['Data'], errors='coerce')
        
        # Conversão de números segura
        for col in ['Célula', 'Culto']:
            df_p[col] = pd.to_numeric(df_p[col], errors='coerce').fillna(0).astype(int)
        for col in ['Vis_Celula', 'Vis_Culto']:
            df_v[col] = pd.to_numeric(df_v[col], errors='coerce').fillna(0).astype(int)

        m_dict = {}
        if df_m is not None and not df_m.empty:
            for _, row in df_m.iterrows():
                l = row.get('Líder')
                if l and l not in m_dict: m_dict[l] = {}
                if l and row.get('Nome') != "LIDER_INICIAL":
                    m_dict[l][row['Nome']] = row.get('Tipo', 'Membro')
        return df_p, df_v, m_dict
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame(columns=['Data', 'Líder']), pd.DataFrame(columns=['Data', 'Líder']), {}

def salvar_seguro(worksheet, df):
    """Função central para evitar o crash no update"""
    try:
        df_save = df.copy()
        if 'Data' in df_save.columns:
            df_save['Data'] = df_save['Data'].dt.strftime('%Y-%m-%d')
        conn.update(spreadsheet=URL_PLANILHA, worksheet=worksheet, data=df_save)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar na aba {worksheet}: {e}")
        return False

def sincronizar_membros():
    lista = []
    for lid, pess in st.session_state.membros_cadastrados.items():
        if not pess:
            lista.append({"Líder": lid, "Nome": "LIDER_INICIAL", "Tipo": "Liderança"})
        else:
            for nome, tipo in pess.items():
                lista.append({"Líder": lid, "Nome": nome, "Tipo": tipo})
    if salvar_seguro("Membros", pd.DataFrame(lista)):
        st.cache_data.clear()

# --- 3. INICIALIZAÇÃO ---
db_p, db_v, m_dict = carregar_dados()
st.session_state.db = db_p
st.session_state.db_visitantes = db_v
st.session_state.membros_cadastrados = m_dict

# --- 4. ESTILO ---
st.markdown("""
<style>
    .stApp { background-color: #0F172A; color: #F8FAFC; }
    .main-title { background: linear-gradient(90deg, #38BDF8 0%, #0284C7 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; font-size: 32px; text-align: center; margin-bottom: 20px;}
    .metric-box { background: #1E293B; padding: 10px; border-radius: 10px; border-top: 4px solid #0284C7; text-align: center; }
    .metric-value { font-size: 18px; font-weight: 800; color: #38BDF8; }
    .alert-danger { background: #450a0a; padding: 10px; border-radius: 5px; border-left: 5px solid #ef4444; margin-bottom: 8px; font-size: 13px; color: #fecaca; }
</style>
""", unsafe_allow_html=True)

MESES_NOMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MESES_MAP = {n: i+1 for i, n in enumerate(MESES_NOMES)}

# --- 5. INTERFACE ---
st.markdown('<p class="main-title">🛡️ DISTRITO PRO 2026</p>', unsafe_allow_html=True)

if st.sidebar.button("🔄 Atualizar"):
    st.cache_data.clear()
    st.rerun()

tab_dash, tab_lanc, tab_gestao, tab_ob = st.tabs(["📊 DASHBOARDS", "📝 LANÇAR", "⚙️ GESTÃO", "📋 RELATÓRIO OB"])

# --- TAB DASHBOARDS ---
with tab_dash:
    if st.session_state.db.empty or 'Data' not in st.session_state.db.columns:
        st.info("💡 Sem dados para exibir.")
    else:
        lids_atuais = sorted(list(st.session_state.membros_cadastrados.keys()))
        lids_f = st.multiselect("Células:", lids_atuais, default=lids_atuais)
        
        col_m, col_s = st.columns(2)
        mes_sel = col_m.selectbox("Mês:", MESES_NOMES, index=datetime.now().month - 1)
        
        df_mes_f = st.session_state.db[st.session_state.db['Data'].dt.month == MESES_MAP[mes_sel]]
        
        if df_mes_f.empty:
            st.warning(f"Sem dados em {mes_sel}.")
        else:
            datas_disp = sorted(df_mes_f['Data'].dropna().unique(), reverse=True)
            data_sel = col_s.selectbox("Semana:", datas_disp, format_func=lambda x: pd.to_datetime(x).strftime('%d/%m/%Y'))

            df_sem = st.session_state.db[(st.session_state.db['Data'] == data_sel) & (st.session_state.db['Líder'].isin(lids_f))]
            df_v_sem = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data'] == data_sel) & (st.session_state.db_visitantes['Líder'].isin(lids_f))]

            # Métricas
            def get_count_int(tipo):
                total = sum([1 for l in lids_f for n, t in st.session_state.membros_cadastrados.get(l, {}).items() if t == tipo])
                f_cel = int(df_sem[df_sem['Tipo'] == tipo]['Célula'].sum())
                f_cul = int(df_sem[df_sem['Tipo'] == tipo]['Culto'].sum())
                return f"{f_cel}/{total}", f"{f_cul}/{total}"

            m_cel, m_cul = get_count_int("Membro")
            fa_cel, fa_cul = get_count_int("FA")
            v_cel = int(df_v_sem['Vis_Celula'].sum())
            v_cul = int(df_v_sem['Vis_Culto'].sum())

            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.markdown(f'<div class="metric-box"><p class="metric-value">{m_cel}</p>Membro Cél.</div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-box"><p class="metric-value">{m_cul}</p>Membro Culto</div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-box"><p class="metric-value">{fa_cel}</p>FA Cél.</div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="metric-box"><p class="metric-value">{fa_cul}</p>FA Cult
