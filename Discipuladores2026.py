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

# --- 2. FUNÇÕES DE DADOS (LIMPEZA DEFINITIVA) ---
@st.cache_data(ttl=2)
def carregar_dados():
    try:
        df_p = conn.read(spreadsheet=URL_PLANILHA, worksheet="Presencas")
        df_v = conn.read(spreadsheet=URL_PLANILHA, worksheet="Visitantes")
        df_m = conn.read(spreadsheet=URL_PLANILHA, worksheet="Membros")
        
        if df_p is None or df_p.empty: df_p = pd.DataFrame(columns=['Data', 'Líder', 'Nome', 'Tipo', 'Célula', 'Culto'])
        if df_v is None or df_v.empty: df_v = pd.DataFrame(columns=['Data', 'Líder', 'Vis_Celula', 'Vis_Culto'])

        # CONVERSÃO ROBUSTA: Transforma qualquer formato em objeto de data real
        def limpar_data(col):
            # Tenta converter tratando dia primeiro (Brasil) e depois ISO (Internacional)
            datas = pd.to_datetime(col, dayfirst=True, errors='coerce')
            return datas

        df_p['Data_Obj'] = limpar_data(df_p['Data'])
        df_v['Data_Obj'] = limpar_data(df_v['Data'])
        
        # Cria a Data_Ref como string padronizada YYYY-MM-DD para o seletor
        df_p['Data_Ref'] = df_p['Data_Obj'].dt.strftime('%Y-%m-%d')
        df_v['Data_Ref'] = df_v['Data_Obj'].dt.strftime('%Y-%m-%d')
        
        df_p = df_p.dropna(subset=['Data_Obj'])
        df_v = df_v.dropna(subset=['Data_Obj'])

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
        # Remove colunas auxiliares antes de enviar para a planilha
        for col in ['Data_Obj', 'Data_Ref', 'MesNum']:
            if col in df_save.columns: df_save = df_save.drop(columns=[col])
        
        # Garante que a coluna Data vá como string formatada para evitar confusão no Sheets
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

# --- 4. INTERFACE ---
st.markdown("<style>.stApp { background-color: #0F172A; color: #F8FAFC; } .metric-box { background: #1E293B; padding: 15px; border-radius: 10px; border-top: 4px solid #0284C7; text-align: center; margin-bottom: 10px;} .metric-value { font-size: 24px; font-weight: 800; color: #38BDF8; display: block; }</style>", unsafe_allow_html=True)

MESES_NOMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MESES_MAP = {n: i+1 for i, n in enumerate(MESES_NOMES)}

st.title("🛡️ DISTRITO PRO 2026")
tab_dash, tab_lanc, tab_gestao, tab_ob = st.tabs(["📊 DASHBOARDS", "📝 LANÇAR", "⚙️ GESTÃO", "📋 RELATÓRIO OB"])

# --- TAB DASHBOARD ---
with tab_dash:
    if st.button("🔄 Sincronizar"):
        st.cache_data.clear()
        st.rerun()
    
    if st.session_state.db.empty:
        st.info("💡 Sem dados registrados.")
    else:
        lids_atuais = sorted(list(st.session_state.membros_cadastrados.keys()))
        lids_f = st.multiselect("Células:", lids_atuais, default=lids_atuais)
        
        col_m, col_s = st.columns(2)
        mes_sel = col_m.selectbox("Mês:", MESES_NOMES, index=datetime.now().month - 1)
        
        # Filtro usando o objeto de data real
        df_mes = st.session_state.db[st.session_state.db['Data_Obj'].dt.month == MESES_MAP[mes_sel]]
        
        if df_mes.empty:
            st.warning(f"Sem dados para {mes_sel}.")
        else:
            datas_disp = sorted(df_mes['Data_Ref'].unique(), reverse=True)
            sel_ref = col_s.selectbox("Semana:", datas_disp, format_func=lambda x: datetime.strptime(x, '%Y-%m-%d').strftime('%d/%m/%Y'))

            df_sem = df_mes[(df_mes['Data_Ref'] == sel_ref) & (df_mes['Líder'].isin(lids_f))]
            df_v_sem = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data_Ref'] == sel_ref) & (st.session_state.db_visitantes['Líder'].isin(lids_f))]

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

            st.divider()
            cg1, cg2 = st.columns(2)
            df_g1 = df_mes[df_mes['Líder'].isin(lids_f)].groupby('Data_Ref')['Célula'].sum().reset_index()
            fig1 = px.line(df_g1, x='Data_Ref', y='Célula', title="Evolução Célula", markers=True, text='Célula')
            cg1.plotly_chart(fig1, use_container_width=True)

            df_g2 = df_mes[df_mes['Líder'].isin(lids_f)].groupby('Data_Ref')['Culto'].sum().reset_index()
            fig2 = px.line(df_g2, x='Data_Ref', y='Culto', title="Evolução Culto", markers=True, text='Culto')
            cg2.plotly_chart(fig2, use_container_width=True)

# --- TAB LANÇAR ---
with tab_lanc:
    if not st.session_state.membros_cadastrados:
        st.warning("Cadastre líderes em GESTÃO.")
    else:
        cl1, cl2, cl3 = st.columns(3)
        m_l = cl1.selectbox("Selecione o Mês", MESES_NOMES, index=datetime.now().month-1, key="l_m_sel")
        datas_sab = [date(2026, MESES_MAP[m_l], d) for d in range(1, 32) if (date(2026, MESES_MAP[m_l], 1) + timedelta(days=d-1)).month == MESES_MAP[m_l] and (date(2026, MESES_MAP[m_l], 1) + timedelta(days=d-1)).weekday() == 5]
        d_l = cl2.selectbox("Data (Sábado)", datas_sab, format_func=lambda x: x.strftime('%d/%m'), key="l_d_sel")
        l_l = cl3.selectbox("Célula", sorted(st.session_state.membros_cadastrados.keys()), key="l_l_sel")
        
        st.subheader(f"Chamada: {l_l}")
        novos_dados = []
        
        # Liderança
        col_n, col_ce, col_cu = st.columns([2,1,1])
        lp_ce = col_ce.checkbox("Célula", value=True, key="lpce_c")
        lp_cu = col_cu.checkbox("Culto", value=True, key="lpcu_c")
        novos_dados.append({"Data": d_l, "Líder": l_l, "Nome": l_l, "Tipo": "Liderança", "Célula": 1 if lp_ce else 0, "Culto": 1 if lp_cu else 0})
        
        # Membros da célula
        membros_da_cel = st.session_state.membros_cadastrados.get(l_l, {})
        for nome, tipo in membros_da_cel.items():
            cn, ce, cu = st.columns([2,1,1])
            cn.write(f"{nome} ({tipo})")
            p_ce = ce.checkbox("Célula", key=f"ce_{nome}_{d_l}")
            p_cu = cu.checkbox("Culto", key=f"cu_{nome}_{d_l}")
            novos_dados.append({"Data": d_l, "Líder": l_l, "Nome": nome, "Tipo": tipo, "Célula": 1 if p_ce else 0, "Culto": 1 if p_cu else 0})
        
        v_ce = st.number_input("Visitantes na Célula", 0, key="v_ce_in")
        v_cu = st.number_input("Visitantes no Culto", 0, key="v_cu_in")
        
        if st.button("💾 SALVAR TUDO", type="primary", use_container_width=True):
            dt_ref_str = d_l.strftime('%Y-%m-%d')
            # Filtra e remove o que já existe para essa data/líder antes de salvar
            df_p_limpo = st.session_state.db[~((st.session_state.db['Data_Ref'] == dt_ref_str) & (st.session_state.db['Líder'] == l_l))]
            df_p_final = pd.concat([df_p_limpo, pd.DataFrame(novos_dados)])
            
            df_v_limpo = st.session_state.db_visitantes[~((st.session_state.db_visitantes['Data_Ref'] == dt_ref_str) & (st.session_state.db_visitantes['Líder'] == l_l))]
            df_v_final = pd.concat([df_v_limpo, pd.DataFrame([{"Data": d_l, "Líder": l_l, "Vis_Celula": v_ce, "Vis_Culto": v_cu}])])
            
            if salvar_seguro("Presencas", df_p_final) and salvar_seguro("Visitantes", df_v_final):
                st.success("Dados enviados com sucesso!")
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()

# --- TAB GESTÃO ---
with tab_gestao:
    st.subheader("Gerenciar Líderes e Membros")
    col1, col2 = st.columns(2)
    with col1:
        n_lider = st.text_input("Novo Líder de Célula")
        if st.button("Criar Célula"):
            if n_lider:
                st.session_state.membros_cadastrados[n_lider] = {}
                sincronizar_membros()
                st.rerun()
    with col2:
        if st.session_state.membros_cadastrados:
            c_escolhida = st.selectbox("Escolha a Célula:", sorted(st.session_state.membros_cadastrados.keys()))
            n_membro = st.text_input("Nome do Membro")
            t_membro = st.radio("Tipo:", ["Membro", "FA"], horizontal=True)
            if st.button("Adicionar Pessoa"):
                if n_membro:
                    st.session_state.membros_cadastrados[c_escolhida][n_membro] = t_membro
                    sincronizar_membros()
                    st.rerun()

# --- TAB RELATÓRIO OB ---
with tab_ob:
    m_rel = st.selectbox("Mês do Relatório:", MESES_NOMES, index=datetime.now().month-1, key="rel_m")
    df_rel = st.session_state.db[st.session_state.db['Data_Obj'].dt.month == MESES_MAP[m_rel]]
    
    if df_rel.empty:
        st.info("Nenhum dado para gerar relatório.")
    else:
        for d_ref in sorted(df_rel['Data_Ref'].unique(), reverse=True):
            st.markdown(f"### 🗓️ Semana: {datetime.strptime(d_ref, '%Y-%m-%d').strftime('%d/%m/%Y')}")
            resumo_semanal = []
            for lid in sorted(st.session_state.membros_cadastrados.keys()):
                dados_lid = df_rel[(df_rel['Data_Ref'] == d_ref) & (df_rel['Líder'] == lid)]
                pres_lider = "✅" if not dados_lid[dados_lid['Tipo'] == 'Liderança'].empty and dados_lid[dados_lid['Tipo'] == 'Liderança']['Célula'].sum() > 0 else "❌"
                
                total_m = sum(1 for n,t in st.session_state.membros_cadastrados[lid].items() if t == "Membro") + 1
                pres_m = int(dados_lid[dados_lid['Tipo'].isin(['Membro', 'Liderança'])]['Célula'].sum())
                
                resumo_semanal.append({"Célula": lid, "Líder": pres_lider, "Frequência": f"{pres_m}/{total_m}"})
            st.table(pd.DataFrame(resumo_semanal))
