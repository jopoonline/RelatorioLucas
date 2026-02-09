import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta, datetime
from streamlit_gsheets import GSheetsConnection
import time

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Distrito Pro 2026", layout="wide", page_icon="🛡️")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1y3vAXagtbdzaTHGEkPOuWI3TvzcfFYhfO1JUt0GrhG8/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. FUNÇÕES DE DADOS ---
@st.cache_data(ttl=5)
def carregar_dados():
    try:
        df_p = conn.read(spreadsheet=URL_PLANILHA, worksheet="Presencas")
        df_v = conn.read(spreadsheet=URL_PLANILHA, worksheet="Visitantes")
        df_m = conn.read(spreadsheet=URL_PLANILHA, worksheet="Membros")
        
        if df_p is None or df_p.empty: df_p = pd.DataFrame(columns=['Data', 'Líder', 'Nome', 'Tipo', 'Célula', 'Culto'])
        if df_v is None or df_v.empty: df_v = pd.DataFrame(columns=['Data', 'Líder', 'Vis_Celula', 'Vis_Culto'])

        # Padronização Crítica de Datas para String (Evita erros de fuso horário)
        df_p['Data_Ref'] = pd.to_datetime(df_p['Data'], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
        df_v['Data_Ref'] = pd.to_datetime(df_v['Data'], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
        
        df_p = df_p.dropna(subset=['Data_Ref'])
        df_v = df_v.dropna(subset=['Data_Ref'])

        # Conversão de números
        for col in ['Célula', 'Culto']: df_p[col] = pd.to_numeric(df_p[col], errors='coerce').fillna(0).astype(int)
        for col in ['Vis_Celula', 'Vis_Culto']: df_v[col] = pd.to_numeric(df_v[col], errors='coerce').fillna(0).astype(int)

        m_dict = {}
        if df_m is not None and not df_m.empty:
            for _, row in df_m.iterrows():
                l = row.get('Líder')
                if l and l not in m_dict: m_dict[l] = {}
                if l and row.get('Nome') != "LIDER_INICIAL": m_dict[l][row['Nome']] = row.get('Tipo', 'Membro')
        return df_p, df_v, m_dict
    except Exception as e:
        st.error(f"Erro ao carregar: {e}")
        return pd.DataFrame(), pd.DataFrame(), {}

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
    .metric-box { background: #1E293B; padding: 15px; border-radius: 10px; border-top: 4px solid #0284C7; text-align: center; margin-bottom: 10px;}
    .metric-value { font-size: 24px; font-weight: 800; color: #38BDF8; display: block; }
</style>
""", unsafe_allow_html=True)

MESES_NOMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MESES_MAP = {n: f"{i+1:02d}" for i, n in enumerate(MESES_NOMES)}

st.title("🛡️ DISTRITO PRO 2026")
tab_dash, tab_lanc, tab_gestao, tab_ob = st.tabs(["📊 DASHBOARDS", "📝 LANÇAR", "⚙️ GESTÃO", "📋 RELATÓRIO OB"])

# --- TAB DASHBOARDS ---
with tab_dash:
    st.button("🔄 Sincronizar Agora", on_click=st.cache_data.clear)
    
    if st.session_state.db.empty:
        st.info("💡 Sem dados carregados.")
    else:
        lids_atuais = sorted(list(st.session_state.membros_cadastrados.keys()))
        lids_f = st.multiselect("Filtrar Células:", lids_atuais, default=lids_atuais)
        
        col_m, col_s = st.columns(2)
        mes_sel = col_m.selectbox("Mês:", MESES_NOMES, index=datetime.now().month - 1)
        mes_prefixo = f"2026-{MESES_MAP[mes_sel]}"

        df_mes_f = st.session_state.db[st.session_state.db['Data_Ref'].str.startswith(mes_prefixo)]
        
        if df_mes_f.empty:
            st.warning(f"Sem dados para {mes_sel}.")
        else:
            datas_disp = sorted(df_mes_f['Data_Ref'].unique(), reverse=True)
            data_sel = col_s.selectbox("Semana:", datas_disp, format_func=lambda x: datetime.strptime(x, '%Y-%m-%d').strftime('%d/%m/%Y'))

            df_sem = df_mes_f[(df_mes_f['Data_Ref'] == data_sel) & (df_mes_f['Líder'].isin(lids_f))]
            df_v_sem = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data_Ref'] == data_sel) & (st.session_state.db_visitantes['Líder'].isin(lids_f))]

            def get_val(tipo, modo='Célula'):
                if tipo == "Membro":
                    total = sum([1 for l in lids_f for n, t in st.session_state.membros_cadastrados.get(l, {}).items() if t == "Membro"]) + len(lids_f)
                    val = int(df_sem[df_sem['Tipo'].isin(['Membro', 'Liderança'])][modo].sum())
                    return f"{val}/{total}"
                elif tipo == "Visitante":
                    return str(int(df_v_sem['Vis_Celula' if modo == 'Célula' else 'Vis_Culto'].sum()))
                else:
                    total = sum([1 for l in lids_f for n, t in st.session_state.membros_cadastrados.get(l, {}).items() if t == "FA"])
                    val = int(df_sem[df_sem['Tipo'] == "FA"][modo].sum())
                    return f"{val}/{total}"

            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.markdown(f'<div class="metric-box">Mem. Célula<br><span class="metric-value">{get_val("Membro", "Célula")}</span></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-box">FA Célula<br><span class="metric-value">{get_val("FA", "Célula")}</span></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-box">Vis. Célula<br><span class="metric-value">{get_val("Visitante", "Célula")}</span></div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="metric-box">Mem. Culto<br><span class="metric-value">{get_val("Membro", "Culto")}</span></div>', unsafe_allow_html=True)
            c5.markdown(f'<div class="metric-box">FA Culto<br><span class="metric-value">{get_val("FA", "Culto")}</span></div>', unsafe_allow_html=True)
            c6.markdown(f'<div class="metric-box">Vis. Culto<br><span class="metric-value">{get_val("Visitante", "Culto")}</span></div>', unsafe_allow_html=True)

            st.write("---")
            cg1, cg2 = st.columns(2)
            # Gráficos com Números
            df_g1 = df_mes_f[df_mes_f['Líder'].isin(lids_f)].groupby('Data_Ref')['Célula'].sum().reset_index()
            fig1 = px.line(df_g1, x='Data_Ref', y='Célula', title="Evolução Célula", markers=True, text='Célula')
            fig1.update_traces(textposition="top center")
            cg1.plotly_chart(fig1, use_container_width=True)

            df_g2 = df_mes_f[df_mes_f['Líder'].isin(lids_f)].groupby('Data_Ref')['Culto'].sum().reset_index()
            fig2 = px.line(df_g2, x='Data_Ref', y='Culto', title="Evolução Culto", markers=True, text='Culto')
            fig2.update_traces(textposition="top center")
            cg2.plotly_chart(fig2, use_container_width=True)
            
            # Comparativo Mensal
            st.write("### 📊 Resultado Mensal (Médias)")
            mes_num = int(MESES_MAP[mes_sel])
            comp_m = [f"2026-{i:02d}" for i in range(max(1, mes_num-2), mes_num+1)]
            res = []
            for m_p in comp_m:
                temp = st.session_state.db[st.session_state.db['Data_Ref'].str.startswith(m_p)]
                sabs = len(temp['Data_Ref'].unique()) if not temp.empty else 1
                nome = [k for k,v in MESES_MAP.items() if v == m_p.split('-')[1]][0]
                res.append({"Mês": nome, "Média": round(temp['Célula'].sum()/sabs, 1)})
            st.plotly_chart(px.bar(pd.DataFrame(res), x='Mês', y='Média', text_auto=True), use_container_width=True)

# --- TAB LANÇAR ---
with tab_lanc:
    if not st.session_state.membros_cadastrados:
        st.warning("Cadastre líderes em GESTÃO.")
    else:
        cl1, cl2, cl3 = st.columns(3)
        m_l = cl1.selectbox("Mês", MESES_NOMES, index=datetime.now().month-1, key="lanc_m")
        # Gera apenas sábados do mês
        datas_sab = [date(2026, int(MESES_MAP[m_l]), d) for d in range(1, 32) if (date(2026, int(MESES_MAP[m_l]), 1) + timedelta(days=d-1)).month == int(MESES_MAP[m_l]) and (date(2026, int(MESES_MAP[m_l]), 1) + timedelta(days=d-1)).weekday() == 5]
        d_l = cl2.selectbox("Data (Sábado)", datas_sab, format_func=lambda x: x.strftime('%d/%m'), key="lanc_d")
        l_l = cl3.selectbox("Sua Célula", sorted(st.session_state.membros_cadastrados.keys()), key="lanc_l")
        
        st.subheader(f"Lista de Presença: {l_l}")
        novos = []
        # Líder
        col_n, col_ce, col_cu = st.columns([2,1,1])
        lp_ce = col_ce.checkbox("Célula", value=True, key="lpce")
        lp_cu = col_cu.checkbox("Culto", value=True, key="lpcu")
        novos.append({"Data": d_l, "Líder": l_l, "Nome": l_l, "Tipo": "Liderança", "Célula": 1 if lp_ce else 0, "Culto": 1 if lp_cu else 0})
        
        # Membros
        membros = st.session_state.membros_cadastrados.get(l_l, {})
        for n, t in membros.items():
            cn, ce, cu = st.columns([2,1,1])
            cn.write(f"{n} ({t})")
            p_ce = ce.checkbox("Célula", key=f"ce_{n}")
            p_cu = cu.checkbox("Culto", key=f"cu_{n}")
            novos.append({"Data": d_l, "Líder": l_l, "Nome": n, "Tipo": t, "Célula": 1 if p_ce else 0, "Culto": 1 if p_cu else 0})
        
        v_ce = st.number_input("Visitantes Célula", 0)
        v_cu = st.number_input("Visitantes Culto", 0)
        
        if st.button("💾 SALVAR LANÇAMENTO", type="primary", use_container_width=True):
            dt_str = d_l.strftime('%Y-%m-%d')
            # Presença
            df_p_atu = st.session_state.db[~((st.session_state.db['Data_Ref'] == dt_str) & (st.session_state.db['Líder'] == l_l))]
            df_p_new = pd.concat([df_p_atu, pd.DataFrame(novos).drop(columns=['Data_Ref'], errors='ignore')])
            # Visitantes
            df_v_atu = st.session_state.db_visitantes[~((st.session_state.db_visitantes['Data_Ref'] == dt_str) & (st.session_state.db_visitantes['Líder'] == l_l))]
            df_v_new = pd.concat([df_v_atu, pd.DataFrame([{"Data": d_l, "Líder": l_l, "Vis_Celula": v_ce, "Vis_Culto": v_cu}])])
            
            if salvar_seguro("Presencas", df_p_new) and salvar_seguro("Visitantes", df_v_new):
                st.success("Salvo com sucesso!")
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()

# --- TAB GESTÃO ---
with tab_gestao:
    st.subheader("Configuração de Células")
    g1, g2 = st.columns(2)
    with g1:
        novo_l = st.text_input("Nome do Novo Líder")
        if st.button("Criar Nova Célula"):
            if novo_l and novo_l not in st.session_state.membros_cadastrados:
                st.session_state.membros_cadastrados[novo_l] = {}
                sincronizar_membros()
                st.rerun()
    with g2:
        if st.session_state.membros_cadastrados:
            cel_sel = st.selectbox("Selecionar Célula para Membros:", sorted(st.session_state.membros_cadastrados.keys()))
            nome_m = st.text_input("Nome do Membro/FA")
            tipo_m = st.radio("Categoria", ["Membro", "FA"], horizontal=True)
            if st.button("Adicionar à Célula"):
                if nome_m:
                    st.session_state.membros_cadastrados[cel_sel][nome_m] = tipo_m
                    sincronizar_membros()
                    st.rerun()
    st.divider()
    if st.button("🗑️ Limpar Todos os Membros (Cuidado)"):
        st.session_state.membros_cadastrados = {}
        sincronizar_membros()
        st.rerun()

# --- TAB RELATÓRIO OB ---
with tab_ob:
    m_ob = st.selectbox("Mês do Relatório:", MESES_NOMES, index=datetime.now().month-1, key="ob_m")
    prefixo_ob = f"2026-{MESES_MAP[m_ob]}"
    df_ob = st.session_state.db[st.session_state.db['Data_Ref'].str.startswith(prefixo_ob)]
    
    if df_ob.empty:
        st.info("Sem dados para este mês.")
    else:
        for data in sorted(df_ob['Data_Ref'].unique(), reverse=True):
            st.subheader(f"Data: {datetime.strptime(data, '%Y-%m-%d').strftime('%d/%m/%Y')}")
            linhas = []
            for lid in sorted(st.session_state.membros_cadastrados.keys()):
                f_p = df_ob[(df_ob['Data_Ref'] == data) & (df_ob['Líder'] == lid)]
                f_v = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data_Ref'] == data) & (st.session_state.db_visitantes['Líder'] == lid)]
                
                # Cálculo de frequência
                total_m = sum(1 for n,t in st.session_state.membros_cadastrados[lid].items() if t == "Membro") + 1
                pres_m = int(f_p[f_p['Tipo'].isin(['Membro', 'Liderança'])]['Célula'].sum())
                vis = int(f_v['Vis_Celula'].sum()) if not f_v.empty else 0
                
                linhas.append({
                    "Célula": lid,
                    "Líder": "✅" if f_p[f_p['Tipo'] == 'Liderança']['Célula'].sum() > 0 else "❌",
                    "Freq. Membros": f"{pres_m}/{total_m}",
                    "Visitantes": vis
                })
            st.table(pd.DataFrame(linhas))
