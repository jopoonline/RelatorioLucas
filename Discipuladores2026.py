import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Distrito Pro 2026", layout="wide", page_icon="🛡️")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1y3vAXagtbdzaTHGEkPOuWI3TvzcfFYhfO1JUt0GrhG8/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. FUNÇÕES DE DADOS (COM CACHE) ---
@st.cache_data(ttl=60)
def carregar_dados():
    try:
        df_p = conn.read(spreadsheet=URL_PLANILHA, worksheet="Presencas")
        df_v = conn.read(spreadsheet=URL_PLANILHA, worksheet="Visitantes")
        df_m = conn.read(spreadsheet=URL_PLANILHA, worksheet="Membros")
        if not df_p.empty: df_p['Data'] = pd.to_datetime(df_p['Data'])
        if not df_v.empty: df_v['Data'] = pd.to_datetime(df_v['Data'])
        
        m_dict = {}
        if not df_m.empty:
            for _, row in df_m.iterrows():
                l = row['Líder']
                if l not in m_dict: m_dict[l] = {}
                if row['Nome'] != "LIDER_INICIAL":
                    m_dict[l][row['Nome']] = row['Tipo']
        return df_p, df_v, m_dict
    except:
        return pd.DataFrame(), pd.DataFrame(), {}

def sincronizar_membros():
    lista = []
    for lid, pess in st.session_state.membros_cadastrados.items():
        if not pess:
            lista.append({"Líder": lid, "Nome": "LIDER_INICIAL", "Tipo": "Liderança"})
        else:
            for nome, tipo in pess.items():
                lista.append({"Líder": lid, "Nome": nome, "Tipo": tipo})
    conn.update(spreadsheet=URL_PLANILHA, worksheet="Membros", data=pd.DataFrame(lista))
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
    .main-title { background: linear-gradient(90deg, #38BDF8 0%, #0284C7 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; font-size: 32px; text-align: center; }
    .metric-container { background: #1E293B; padding: 15px; border-radius: 12px; border: 1px solid #334155; text-align: center; }
    .warning-card { background: #0c4a6e; padding: 10px; border-radius: 8px; margin-bottom: 5px; border: 1px solid #0ea5e9; font-size: 14px; }
</style>
""", unsafe_allow_html=True)

# --- 5. LOGICA DE DATAS ---
MESES_NOMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MESES_MAP = {n: i+1 for i, n in enumerate(MESES_NOMES)}
def get_sabados(mes_nome, ano=2026):
    mes_int = MESES_MAP[mes_nome]
    d = date(ano, mes_int, 1)
    while d.weekday() != 5: d += timedelta(days=1)
    sats = []
    while d.month == mes_int: sats.append(pd.to_datetime(d)); d += timedelta(days=7)
    return sats

# --- 6. INTERFACE ---
st.markdown('<p class="main-title">🛡️ DISTRITO PRO 2026</p>', unsafe_allow_html=True)
tab_dash, tab_ob, tab_lanc, tab_gestao = st.tabs(["📊 DASHBOARDS", "📋 RELATÓRIO OB", "📝 LANÇAR", "⚙️ GESTÃO"])

# --- TAB DASHBOARDS ---
with tab_dash:
    if st.session_state.db.empty:
        st.info("💡 Sem dados para exibir.")
    else:
        lids_atuais = sorted(list(st.session_state.membros_cadastrados.keys()))
        lids_f = st.multiselect("Filtrar Células:", lids_atuais, default=lids_atuais)
        
        # --- DASHBOARD SEMANAL (LINHA COM NÚMEROS) ---
        st.subheader("📍 Dashboard Semanal")
        datas_disponiveis = sorted(st.session_state.db['Data'].unique(), reverse=True)
        data_sel = st.selectbox("Escolha a Semana:", datas_disponiveis, format_func=lambda x: pd.to_datetime(x).strftime('%d/%m/%Y'))
        
        df_sem = st.session_state.db[(st.session_state.db['Data'] == data_sel) & (st.session_state.db['Líder'].isin(lids_f))]
        df_lider_sem = df_sem.groupby('Líder')[['Célula', 'Culto']].sum().reset_index()
        
        fig_sem = go.Figure()
        fig_sem.add_trace(go.Scatter(x=df_lider_sem['Líder'], y=df_lider_sem['Célula'], name="Célula", mode='lines+markers+text', text=df_lider_sem['Célula'], textposition="top center", line=dict(color='#38BDF8', width=3)))
        fig_sem.add_trace(go.Scatter(x=df_lider_sem['Líder'], y=df_lider_sem['Culto'], name="Culto", mode='lines+markers+text', text=df_lider_sem['Culto'], textposition="top center", line=dict(color='#0284C7', width=3)))
        fig_sem.update_layout(template="plotly_dark", height=400, margin=dict(t=20))
        st.plotly_chart(fig_sem, use_container_width=True)

        # --- DASHBOARD MENSAL ---
        st.divider()
        st.subheader("🗓️ Dashboard Mensal (Evolução)")
        df_mes = st.session_state.db[st.session_state.db['Líder'].isin(lids_f)]
        df_ev = df_mes.groupby('Data')[['Célula', 'Culto']].sum().reset_index()
        
        fig_mes = px.line(df_ev, x='Data', y=['Célula', 'Culto'], markers=True, color_discrete_sequence=['#38BDF8', '#0284C7'])
        fig_mes.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig_mes, use_container_width=True)

# --- TAB RELATÓRIO OB ---
with tab_ob:
    st.subheader("📋 Resumo Operacional")
    if not st.session_state.db.empty:
        # Tabela comparativa Membros vs Frequência
        rel_data = []
        for lid in lids_f:
            total_m = len(st.session_state.membros_cadastrados.get(lid, {}))
            df_l = st.session_state.db[(st.session_state.db['Líder'] == lid) & (st.session_state.db['Data'] == data_sel)]
            p_cel = df_l['Célula'].sum()
            p_cul = df_l['Culto'].sum()
            rel_data.append({"Célula": lid, "Membros": total_m, "Pres. Célula": p_cel, "Pres. Culto": p_cul, "% Freq": f"{(p_cel/total_m*100 if total_m > 0 else 0):.0f}%"})
        
        st.table(pd.DataFrame(rel_data))
        
        st.subheader("🚨 Faltas Consecutivas (Últimas 2 Semanas)")
        for lider in lids_f:
            df_hist = st.session_state.db[st.session_state.db['Líder'] == lider].sort_values('Data', ascending=False)
            for m in df_hist['Nome'].unique():
                ultimas = df_hist[df_hist['Nome'] == m].head(2)
                if len(ultimas) == 2 and ultimas['Célula'].sum() == 0:
                    st.markdown(f'<div class="warning-card">⚠️ {m} ({lider}) faltou as últimas 2 células.</div>', unsafe_allow_html=True)

# --- TAB LANÇAR ---
with tab_lanc:
    if not st.session_state.membros_cadastrados:
        st.warning("Cadastre líderes em GESTÃO.")
    else:
        ca, cb, cc = st.columns(3)
        m_s = ca.selectbox("Mês", MESES_NOMES, key="m_s_l")
        d_s = cb.selectbox("Data", get_sabados(m_s), format_func=lambda x: x.strftime('%d/%m'), key="d_s_l")
        l_s = cc.selectbox("Líder", sorted(st.session_state.membros_cadastrados.keys()), key="l_s_l")
        
        st.write("### 👥 Visitantes")
        va, vb = st.columns(2)
        v_cel = va.number_input("Visitantes Célula", min_value=0, key="vc_in")
        v_cul = vb.number_input("Visitantes Culto", min_value=0, key="vu_in")
        
        st.write("### ✅ Chamada")
        membros = st.session_state.membros_cadastrados[l_s]
        novos = []
        for n, t in membros.items():
            col_n, col_ce, col_cu = st.columns([2,1,1])
            col_n.write(f"**{n}**")
            p_ce = col_ce.checkbox("Célula", key=f"ce_{n}_{d_s}")
            p_cu = col_cu.checkbox("Culto", key=f"cu_{n}_{d_s}")
            novos.append({"Data": d_s, "Líder": l_s, "Nome": n, "Tipo": t, "Célula": 1 if p_ce else 0, "Culto": 1 if p_cu else 0})
            
        if st.button("💾 SALVAR DADOS", use_container_width=True, type="primary"):
            df_new = pd.DataFrame(novos)
            df_cl = st.session_state.db[~((st.session_state.db['Data']==d_s) & (st.session_state.db['Líder']==l_s))]
            st.session_state.db = pd.concat([df_cl, df_new])
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Presencas", data=st.session_state.db)
            
            df_v_new = pd.DataFrame([{"Data": d_s, "Líder": l_s, "Vis_Celula": v_cel, "Vis_Culto": v_cul}])
            df_vc = st.session_state.db_visitantes[~((st.session_state.db_visitantes['Data']==d_s) & (st.session_state.db_visitantes['Líder']==l_s))]
            st.session_state.db_visitantes = pd.concat([df_vc, df_v_new])
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Visitantes", data=st.session_state.db_visitantes)
            
            st.cache_data.clear()
            st.success("Salvo com sucesso!")
            st.rerun()

# --- TAB GESTÃO ---
with tab_gestao:
    st.write("### ⚙️ Gestão de Membros")
    n_lid = st.text_input("Novo Líder")
    if st.button("Salvar Líder"):
        if n_lid:
            st.session_state.membros_cadastrados[n_lid] = {}
            sincronizar_membros()
            st.rerun()
    
    st.divider()
    if st.session_state.membros_cadastrados:
        l_ed = st.selectbox("Célula:", sorted(st.session_state.membros_cadastrados.keys()))
        n_me = st.text_input("Nome Membro")
        t_me = st.radio("Tipo", ["Membro", "FA"], horizontal=True)
        if st.button("Salvar Membro"):
            st.session_state.membros_cadastrados[l_ed][n_me] = t_me
            sincronizar_membros()
            st.rerun()
