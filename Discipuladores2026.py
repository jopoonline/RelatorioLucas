import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta, datetime
from streamlit_gsheets import GSheetsConnection
import time

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Distrito Pro 2026", layout="wide", page_icon="🛡️")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1y3vAXagtbdzaTHGEkPOuWI3TvzcfFYhfO1JUt0GrhG8/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CARREGAMENTO DE DADOS ---
@st.cache_data(ttl=300) # Cache de 5 min para poupar cota
def carregar_dados():
    try:
        df_p = conn.read(spreadsheet=URL_PLANILHA, worksheet="Presencas")
        df_v = conn.read(spreadsheet=URL_PLANILHA, worksheet="Visitantes")
        df_m = conn.read(spreadsheet=URL_PLANILHA, worksheet="Membros")
        
        # Sanitização Presenças
        if df_p is None or df_p.empty:
            df_p = pd.DataFrame(columns=['Data', 'Líder', 'Nome', 'Tipo', 'Célula', 'Culto'])
        else:
            df_p['Data'] = pd.to_datetime(df_p['Data'], errors='coerce')
            for col in ['Célula', 'Culto']:
                df_p[col] = pd.to_numeric(df_p[col], errors='coerce').fillna(0).astype(int)
        
        # Sanitização Visitantes
        if df_v is None or df_v.empty:
            df_v = pd.DataFrame(columns=['Data', 'Líder', 'Vis_Celula', 'Vis_Culto'])
        else:
            df_v['Data'] = pd.to_datetime(df_v['Data'], errors='coerce')
            for col in ['Vis_Celula', 'Vis_Culto']:
                df_v[col] = pd.to_numeric(df_v[col], errors='coerce').fillna(0).astype(int)
        
        m_dict = {}
        if df_m is not None and not df_m.empty:
            for _, row in df_m.iterrows():
                l = row.get('Líder')
                if l and l not in m_dict: m_dict[l] = {}
                if l and row.get('Nome') not in [None, "LIDER_INICIAL"]:
                    m_dict[l][row['Nome']] = row.get('Tipo', 'Membro')
        return df_p, df_v, m_dict
    except Exception as e:
        st.error(f"Erro ao ler Planilha: {e}")
        return pd.DataFrame(columns=['Data', 'Líder']), pd.DataFrame(columns=['Data', 'Líder']), {}

# --- INICIALIZAÇÃO ---
db_p, db_v, m_dict = carregar_dados()
st.session_state.db = db_p
st.session_state.db_visitantes = db_v
st.session_state.membros_cadastrados = m_dict

# --- FUNÇÃO DE SALVAMENTO SEGURO ---
def salvar_no_google(worksheet_name, dataframe):
    try:
        # Força conversão de data para string no formato ISO antes de enviar
        df_to_save = dataframe.copy()
        if 'Data' in df_to_save.columns:
            df_to_save['Data'] = df_to_save['Data'].dt.strftime('%Y-%m-%d')
        
        conn.update(spreadsheet=URL_PLANILHA, worksheet=worksheet_name, data=df_to_save)
        return True
    except Exception as e:
        st.error(f"⚠️ Erro de API (Google): Verifique se a planilha está aberta para EDIÇÃO. Detalhes: {e}")
        return False

def sincronizar_membros():
    lista = []
    for lid, pess in st.session_state.membros_cadastrados.items():
        if not pess:
            lista.append({"Líder": lid, "Nome": "LIDER_INICIAL", "Tipo": "Liderança"})
        else:
            for nome, tipo in pess.items():
                lista.append({"Líder": lid, "Nome": nome, "Tipo": tipo})
    if salvar_no_google("Membros", pd.DataFrame(lista)):
        st.cache_data.clear()

# --- ESTILOS E UI ---
st.markdown('<style>.stApp { background-color: #0F172A; color: #F8FAFC; }</style>', unsafe_allow_html=True)
st.title("🛡️ Distrito Pro 2026")

tab_dash, tab_lanc, tab_gestao = st.tabs(["📊 DASHBOARDS", "📝 LANÇAR", "⚙️ GESTÃO"])

# --- TAB LANÇAR (CORRIGIDA) ---
with tab_lanc:
    if not st.session_state.membros_cadastrados:
        st.warning("Cadastre líderes na aba Gestão.")
    else:
        MESES_NOMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        MESES_MAP = {n: i+1 for i, n in enumerate(MESES_NOMES)}
        
        c1, c2, c3 = st.columns(3)
        m_l = c1.selectbox("Mês", MESES_NOMES, index=datetime.now().month-1)
        # Gerador de sábados
        datas_sab = [date(2026, MESES_MAP[m_l], d) for d in range(1, 32) if (date(2026, MESES_MAP[m_l], 1) + timedelta(days=d-1)).month == MESES_MAP[m_l] and (date(2026, MESES_MAP[m_l], 1) + timedelta(days=d-1)).weekday() == 5]
        d_l = c2.selectbox("Data", datas_sab)
        l_l = c3.selectbox("Líder", sorted(st.session_state.membros_cadastrados.keys()))
        
        v_cel = st.number_input("Visitantes Célula", 0)
        v_cul = st.number_input("Visitantes Culto", 0)
        
        mem = st.session_state.membros_cadastrados.get(l_l, {})
        lista_novos = []
        for n, t in mem.items():
            col_n, col_ce, col_cu = st.columns([2,1,1])
            col_n.write(n)
            p_e = col_ce.checkbox("Célula", key=f"ce_{n}")
            p_u = col_cu.checkbox("Culto", key=f"cu_{n}")
            lista_novos.append({"Data": d_l, "Líder": l_l, "Nome": n, "Tipo": t, "Célula": 1 if p_e else 0, "Culto": 1 if p_u else 0})
            
        if st.button("💾 SALVAR PRESENÇAS", type="primary"):
            dt_l = pd.to_datetime(d_l)
            # Presenças
            df_atual = st.session_state.db
            df_novo_p = pd.concat([df_atual[~((df_atual['Data']==dt_l) & (df_atual['Líder']==l_l))], pd.DataFrame(lista_novos)])
            
            # Visitantes
            df_v_atual = st.session_state.db_visitantes
            df_novo_v = pd.concat([df_v_atual[~((df_v_atual['Data']==dt_l) & (df_v_atual['Líder']==l_l))], pd.DataFrame([{"Data": d_l, "Líder": l_l, "Vis_Celula": v_cel, "Vis_Culto": v_cul}])])
            
            if salvar_no_google("Presencas", df_novo_p) and salvar_no_google("Visitantes", df_novo_v):
                st.success("Tudo salvo!")
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()

# --- TAB GESTÃO ---
with tab_gestao:
    st.subheader("⚙️ Gestão de Membros")
    with st.expander("➕ Adicionar Pessoa"):
        l_sel = st.selectbox("Célula", sorted(st.session_state.membros_cadastrados.keys()) if st.session_state.membros_cadastrados else ["Nenhuma"])
        n_m = st.text_input("Nome")
        t_m = st.radio("Tipo", ["Membro", "FA"], horizontal=True)
        if st.button("Adicionar"):
            if n_m and l_sel != "Nenhuma":
                st.session_state.membros_cadastrados[l_sel][n_m] = t_m
                sincronizar_membros()
                st.rerun()
                
    with st.expander("🆕 Criar Célula"):
        n_c = st.text_input("Nome do Líder")
        if st.button("Criar"):
            if n_c:
                st.session_state.membros_cadastrados[n_c] = {}
                sincronizar_membros()
                st.rerun()
