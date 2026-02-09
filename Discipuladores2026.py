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
@st.cache_data(ttl=10) # Reduzi para 10 segundos para você ver a mudança na hora
def carregar_dados():
    try:
        df_p = conn.read(spreadsheet=URL_PLANILHA, worksheet="Presencas")
        df_v = conn.read(spreadsheet=URL_PLANILHA, worksheet="Visitantes")
        df_m = conn.read(spreadsheet=URL_PLANILHA, worksheet="Membros")
        
        if df_p is None or df_p.empty:
            df_p = pd.DataFrame(columns=['Data', 'Líder', 'Nome', 'Tipo', 'Célula', 'Culto'])
        if df_v is None or df_v.empty:
            df_v = pd.DataFrame(columns=['Data', 'Líder', 'Vis_Celula', 'Vis_Culto'])
            
        # Conversão robusta de data
        df_p['Data'] = pd.to_datetime(df_p['Data'], dayfirst=True, errors='coerce').dt.tz_localize(None)
        df_v['Data'] = pd.to_datetime(df_v['Data'], dayfirst=True, errors='coerce').dt.tz_localize(None)
        
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
    .alert-danger { background: #450a0a; padding: 10px; border-radius: 5px; border-left: 5px solid #ef4444; margin-bottom: 8px; font-size: 13px; color: #fecaca; }
    .alert-warning { background: #42210b; padding: 10px; border-radius: 5px; border-left: 5px solid #f59e0b; margin-bottom: 8px; font-size: 13px; color: #fef3c7; }
</style>
""", unsafe_allow_html=True)

MESES_NOMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MESES_MAP = {n: i+1 for i, n in enumerate(MESES_NOMES)}

st.markdown('<p class="main-title">🛡️ DISTRITO PRO 2026</p>', unsafe_allow_html=True)

tab_dash, tab_lanc, tab_gestao, tab_ob = st.tabs(["📊 DASHBOARDS", "📝 LANÇAR", "⚙️ GESTÃO", "📋 RELATÓRIO OB"])

# --- TAB DASHBOARDS ---
with tab_dash:
    if st.button("🔄 Sincronizar Agora"):
        st.cache_data.clear()
        st.rerun()

    if st.session_state.db.empty:
        st.info("💡 Sem dados na planilha.")
    else:
        lids_atuais = sorted(list(st.session_state.membros_cadastrados.keys()))
        lids_f = st.multiselect("Filtrar Células:", lids_atuais, default=lids_atuais)
        
        col_m, col_s = st.columns(2)
        mes_sel = col_m.selectbox("Mês:", MESES_NOMES, index=datetime.now().month - 1)
        
        # Filtro de mês mais flexível
        df_mes_f = st.session_state.db[st.session_state.db['Data'].dt.month == MESES_MAP[mes_sel]]
        
        if df_mes_f.empty:
            st.warning(f"Sem dados registrados para {mes_sel}. Tente outro mês ou verifique a planilha.")
        else:
            # Pega as datas únicas do mês e garante que são mostradas
            datas_disp = sorted(df_mes_f['Data'].unique(), reverse=True)
            data_sel = col_s.selectbox("Semana Selecionada:", datas_disp, format_func=lambda x: x.strftime('%d/%m/%Y'))

            df_sem = st.session_state.db[(st.session_state.db['Data'] == data_sel) & (st.session_state.db['Líder'].isin(lids_f))]
            df_v_sem = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data'] == data_sel) & (st.session_state.db_visitantes['Líder'].isin(lids_f))]

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
            
            # Garantir que o gráfico use as datas corretas
            df_p_c = df_mes_f[df_mes_f['Líder'].isin(lids_f)].groupby('Data')['Célula'].sum().reset_index()
            df_v_c = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data'].dt.month == MESES_MAP[mes_sel]) & (st.session_state.db_visitantes['Líder'].isin(lids_f))].groupby('Data')['Vis_Celula'].sum().reset_index()
            df_m_c = pd.merge(df_p_c, df_v_c, on='Data', how='outer').fillna(0).sort_values('Data')
            
            fig1 = px.line(df_m_c, x='Data', y=['Célula', 'Vis_Celula'], title="Célula", markers=True, text='value')
            fig1.update_traces(textposition="top center")
            col_g1.plotly_chart(fig1, use_container_width=True)
            
            df_p_u = df_mes_f[df_mes_f['Líder'].isin(lids_f)].groupby('Data')['Culto'].sum().reset_index()
            df_v_u = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data'].dt.month == MESES_MAP[mes_sel]) & (st.session_state.db_visitantes['Líder'].isin(lids_f))].groupby('Data')['Vis_Culto'].sum().reset_index()
            df_m_u = pd.merge(df_p_u, df_v_u, on='Data', how='outer').fillna(0).sort_values('Data')
            
            fig2 = px.line(df_m_u, x='Data', y=['Culto', 'Vis_Culto'], title="Culto", markers=True, text='value')
            fig2.update_traces(textposition="top center")
            col_g2.plotly_chart(fig2, use_container_width=True)

# --- TABELAS LANÇAR, GESTÃO E OB MANTIDAS ---
with tab_lanc:
    if not st.session_state.membros_cadastrados:
        st.warning("Cadastre líderes em GESTÃO.")
    else:
        cl1, cl2, cl3 = st.columns(3)
        m_l = cl1.selectbox("Mês", MESES_NOMES, index=datetime.now().month-1, key="l_m")
        datas_sab = [date(2026, MESES_MAP[m_l], d) for d in range(1, 32) if (date(2026, MESES_MAP[m_l], 1) + timedelta(days=d-1)).month == MESES_MAP[m_l] and (date(2026, MESES_MAP[m_l], 1) + timedelta(days=d-1)).weekday() == 5]
        d_l = cl2.selectbox("Data", datas_sab, format_func=lambda x: x.strftime('%d/%m'), key="l_d")
        l_l = cl3.selectbox("Sua Célula", sorted(st.session_state.membros_cadastrados.keys()), key="l_l")
        novos = []
        st.markdown(f"**Líder: {l_l}**")
        c_ln, c_le, c_lu = st.columns([2,1,1])
        l_pres_e = c_le.checkbox("Célula", key=f"le_{l_l}", value=True)
        l_pres_u = c_lu.checkbox("Culto", key=f"lu_{l_l}", value=True)
        novos.append({"Data": pd.to_datetime(d_l), "Líder": l_l, "Nome": l_l, "Tipo": "Liderança", "Célula": 1 if l_pres_e else 0, "Culto": 1 if l_pres_u else 0})
        mem = st.session_state.membros_cadastrados.get(l_l, {})
        for n, t in mem.items():
            cn, ce, cu = st.columns([2,1,1])
            cn.write(f"{n} ({t})")
            p_e = ce.checkbox("Célula", key=f"e_{n}_{d_l}")
            p_u = cu.checkbox("Culto", key=f"u_{n}_{d_l}")
            novos.append({"Data": pd.to_datetime(d_l), "Líder": l_l, "Nome": n, "Tipo": t, "Célula": 1 if p_e else 0, "Culto": 1 if p_u else 0})
        v_cel_in = st.number_input("Visitantes Célula", 0, key="v_cel")
        v_cul_in = st.number_input("Visitantes Culto", 0, key="v_cul")
        if st.button("💾 SALVAR", use_container_width=True, type="primary"):
            dt_l = pd.to_datetime(d_l)
            df_p_new = pd.concat([st.session_state.db[~((st.session_state.db['Data']==dt_l) & (st.session_state.db['Líder']==l_l))], pd.DataFrame(novos)])
            df_v_new = pd.concat([st.session_state.db_visitantes[~((st.session_state.db_visitantes['Data']==dt_l) & (st.session_state.db_visitantes['Líder']==l_l))], pd.DataFrame([{"Data": pd.to_datetime(d_l), "Líder": l_l, "Vis_Celula": v_cel_in, "Vis_Culto": v_cul_in}])])
            if salvar_seguro("Presencas", df_p_new) and salvar_seguro("Visitantes", df_v_new):
                st.success("Salvo!")
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()

with tab_gestao:
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        n_l = st.text_input("Novo Líder")
        if st.button("Criar Célula"):
            if n_l: st.session_state.membros_cadastrados[n_l] = {}; sincronizar_membros(); st.rerun()
    with col_g2:
        if st.session_state.membros_cadastrados:
            l_sel = st.selectbox("Célula:", sorted(st.session_state.membros_cadastrados.keys()))
            n_m = st.text_input("Nome Pessoa")
            t_m = st.radio("Tipo", ["Membro", "FA"], horizontal=True)
            if st.button("Adicionar"):
                if n_m: st.session_state.membros_cadastrados[l_sel][n_m] = t_m; sincronizar_membros(); st.rerun()

with tab_ob:
    mes_ob = st.selectbox("Mês Relatório:", MESES_NOMES, index=datetime.now().month-1, key="ob_m")
    if not st.session_state.db.empty:
        df_p_ob = st.session_state.db[st.session_state.db['Data'].dt.month == MESES_MAP[mes_ob]]
        for sem in sorted(df_p_ob['Data'].dropna().unique(), reverse=True):
            st.write(f"📅 **Semana: {pd.to_datetime(sem).strftime('%d/%m/%Y')}**")
            dados_ob = []
            for lid in sorted(st.session_state.membros_cadastrados.keys()):
                f_p = df_p_ob[(df_p_ob['Data'] == sem) & (df_p_ob['Líder'] == lid)]
                f_v = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data'] == sem) & (st.session_state.db_visitantes['Líder'] == lid)]
                m_t = sum(1 for n, t in st.session_state.membros_cadastrados[lid].items() if t == "Membro") + 1
                pres_m = int(f_p[f_p['Tipo'].isin(['Membro', 'Liderança'])]['Célula'].sum())
                dados_ob.append({"Célula": lid, "Líder": "✅" if f_p[f_p['Tipo']=='Liderança']['Célula'].sum() > 0 else "❌", "Freq.": f"{pres_m}/{m_t}", "Vis.": int(f_v['Vis_Celula'].sum())})
            st.table(pd.DataFrame(dados_ob))
