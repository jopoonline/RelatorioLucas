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

# --- 2. FUNÇÕES DE DADOS ---
@st.cache_data(ttl=5) # Cache baixíssimo para teste
def carregar_dados():
    try:
        df_p = conn.read(spreadsheet=URL_PLANILHA, worksheet="Presencas")
        df_v = conn.read(spreadsheet=URL_PLANILHA, worksheet="Visitantes")
        df_m = conn.read(spreadsheet=URL_PLANILHA, worksheet="Membros")
        
        if df_p is None or df_p.empty:
            df_p = pd.DataFrame(columns=['Data', 'Líder', 'Nome', 'Tipo', 'Célula', 'Culto'])
        if df_v is None or df_v.empty:
            df_v = pd.DataFrame(columns=['Data', 'Líder', 'Vis_Celula', 'Vis_Culto'])
            
        # Força conversão de data e remove informações de hora/fuso
        df_p['Data'] = pd.to_datetime(df_p['Data'], dayfirst=True, errors='coerce').dt.normalize()
        df_v['Data'] = pd.to_datetime(df_v['Data'], dayfirst=True, errors='coerce').dt.normalize()
        
        df_p = df_p.dropna(subset=['Data'])
        df_v = df_v.dropna(subset=['Data'])
        
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
    try:
        df_save = df.copy()
        if 'Data' in df_save.columns:
            df_save['Data'] = pd.to_datetime(df_save['Data']).dt.strftime('%Y-%m-%d')
        conn.update(spreadsheet=URL_PLANILHA, worksheet=worksheet, data=df_save)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
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
    .metric-box { background: #1E293B; padding: 15px; border-radius: 10px; border-top: 4px solid #0284C7; text-align: center; margin-bottom: 10px; }
    .metric-value { font-size: 22px; font-weight: 800; color: #38BDF8; display: block; }
</style>
""", unsafe_allow_html=True)

MESES_NOMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MESES_MAP = {n: i+1 for i, n in enumerate(MESES_NOMES)}

st.markdown('<p class="main-title">🛡️ DISTRITO PRO 2026</p>', unsafe_allow_html=True)

tab_dash, tab_lanc, tab_gestao, tab_ob = st.tabs(["📊 DASHBOARDS", "📝 LANÇAR", "⚙️ GESTÃO", "📋 RELATÓRIO OB"])

# --- TAB DASHBOARDS ---
with tab_dash:
    col_refresh, col_info = st.columns([1, 2])
    if col_refresh.button("🔄 Sincronizar Planilha"):
        st.cache_data.clear()
        st.rerun()
    
    total_linhas = len(st.session_state.db)
    col_info.write(f"📊 Total de registros lidos: {total_linhas}")

    if st.session_state.db.empty:
        st.info("💡 Nenhuma presença encontrada na planilha.")
    else:
        lids_atuais = sorted(list(st.session_state.membros_cadastrados.keys()))
        lids_f = st.multiselect("Filtrar Células:", lids_atuais, default=lids_atuais)
        
        col_m, col_s = st.columns(2)
        mes_sel_nome = col_m.selectbox("Mês:", MESES_NOMES, index=datetime.now().month - 1)
        mes_num = MESES_MAP[mes_sel_nome]
        
        # Filtro de mês robusto
        df_mes_total = st.session_state.db.copy()
        df_mes_total['MesNum'] = df_mes_total['Data'].dt.month
        df_mes_f = df_mes_total[df_mes_total['MesNum'] == mes_num]
        
        if df_mes_f.empty:
            st.warning(f"Não existem dados para {mes_sel_nome} na planilha.")
            # Debug: Mostrar quais meses existem na planilha
            meses_existentes = df_mes_total['MesNum'].unique()
            nomes_existentes = [MESES_NOMES[int(m)-1] for m in meses_existentes if not pd.isna(m)]
            st.write(f"Meses encontrados na planilha: {', '.join(nomes_existentes)}")
        else:
            # Pega TODAS as datas únicas do mês filtrado
            datas_unicas = sorted(df_mes_f['Data'].dt.date.unique(), reverse=True)
            data_sel = col_s.selectbox("Semana Selecionada:", datas_unicas, format_func=lambda x: x.strftime('%d/%m/%Y'))

            # Filtra os dados da semana e células selecionadas
            data_sel_dt = pd.to_datetime(data_sel)
            df_sem = st.session_state.db[(st.session_state.db['Data'] == data_sel_dt) & (st.session_state.db['Líder'].isin(lids_f))]
            
            # Busca visitantes para a mesma data
            df_v_total = st.session_state.db_visitantes.copy()
            df_v_sem = df_v_total[(df_v_total['Data'] == data_sel_dt) & (df_v_total['Líder'].isin(lids_f))]

            def get_count_int(tipo, modo='Célula'):
                if tipo == "Membro":
                    total = sum([1 for l in lids_f for n, t in st.session_state.membros_cadastrados.get(l, {}).items() if t == "Membro"]) + len(lids_f)
                    f_val = int(df_sem[df_sem['Tipo'].isin(['Membro', 'Liderança'])][modo].sum())
                elif tipo == "Visitante":
                    total = 0
                    f_val = int(df_v_sem['Vis_Celula' if modo == 'Célula' else 'Vis_Culto'].sum())
                else: 
                    total = sum([1 for l in lids_f for n, t in st.session_state.membros_cadastrados.get(l, {}).items() if t == tipo])
                    f_val = int(df_sem[df_sem['Tipo'] == tipo][modo].sum())
                return f"{f_val}/{total}" if total > 0 else f"{f_val}"

            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.markdown(f'<div class="metric-box"><span class="metric-value">{get_count_int("Membro", "Célula")}</span>Membro Cél.</div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-box"><span class="metric-value">{get_count_int("FA", "Célula")}</span>FA Cél.</div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-box"><span class="metric-value">{get_count_int("Visitante", "Célula")}</span>Vis. Cél.</div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="metric-box"><span class="metric-value">{get_count_int("Membro", "Culto")}</span>Membro Culto</div>', unsafe_allow_html=True)
            c5.markdown(f'<div class="metric-box"><span class="metric-value">{get_count_int("FA", "Culto")}</span>FA Culto</div>', unsafe_allow_html=True)
            c6.markdown(f'<div class="metric-box"><span class="metric-value">{get_count_int("Visitante", "Culto")}</span>Vis. Culto</div>', unsafe_allow_html=True)

            st.write("---")
            st.write("### 📈 Evolução Semanal")
            col_g1, col_g2 = st.columns(2)
            
            # Gráficos ajustados para o novo filtro
            df_p_c = df_mes_f[df_mes_f['Líder'].isin(lids_f)].groupby('Data')['Célula'].sum().reset_index()
            df_v_c = df_v_total[(df_v_total['Data'].dt.month == mes_num) & (df_v_total['Líder'].isin(lids_f))].groupby('Data')['Vis_Celula'].sum().reset_index()
            df_m_c = pd.merge(df_p_c, df_v_c, on='Data', how='outer').fillna(0).sort_values('Data')
            
            fig1 = px.line(df_m_c, x='Data', y=['Célula', 'Vis_Celula'], title="Célula", markers=True, text='value')
            fig1.update_traces(textposition="top center")
            col_g1.plotly_chart(fig1, use_container_width=True)
            
            df_p_u = df_mes_f[df_mes_f['Líder'].isin(lids_f)].groupby('Data')['Culto'].sum().reset_index()
            df_v_u = df_v_total[(df_v_total['Data'].dt.month == mes_num) & (df_v_total['Líder'].isin(lids_f))].groupby('Data')['Vis_Culto'].sum().reset_index()
            df_m_u = pd.merge(df_p_u, df_v_u, on='Data', how='outer').fillna(0).sort_values('Data')
            
            fig2 = px.line(df_m_u, x='Data', y=['Culto', 'Vis_Culto'], title="Culto", markers=True, text='value')
            fig2.update_traces(textposition="top center")
            col_g2.plotly_chart(fig2, use_container_width=True)

# As outras abas (Lançar, Gestão, Relatório OB) permanecem exatamente como no seu código original.
