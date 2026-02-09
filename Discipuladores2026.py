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

# --- 2. FUNÇÕES DE DADOS ---
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
    .main-title { background: linear-gradient(90deg, #38BDF8 0%, #0284C7 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; font-size: 32px; text-align: center; margin-bottom: 20px;}
    .metric-box { background: #1E293B; padding: 10px; border-radius: 10px; border-top: 4px solid #0284C7; text-align: center; }
    .metric-label { font-size: 12px; color: #94A3B8; text-transform: uppercase; }
    .metric-value { font-size: 20px; font-weight: 800; color: #38BDF8; }
    .warning-box { background: #0c4a6e; padding: 8px; border-radius: 5px; border-left: 4px solid #0ea5e9; margin-bottom: 5px; font-size: 13px; }
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

with tab_dash:
    if st.session_state.db.empty:
        st.info("💡 Sem dados para exibir.")
    else:
        lids_atuais = sorted(list(st.session_state.membros_cadastrados.keys()))
        lids_f = st.multiselect("Filtrar Células:", lids_atuais, default=lids_atuais)
        
        datas_disp = sorted(st.session_state.db['Data'].unique(), reverse=True)
        data_sel = st.selectbox("Escolha a Semana:", datas_disp, format_func=lambda x: pd.to_datetime(x).strftime('%d/%m/%Y'))

        df_sem = st.session_state.db[(st.session_state.db['Data'] == data_sel) & (st.session_state.db['Líder'].isin(lids_f))]
        df_v_sem = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data'] == data_sel) & (st.session_state.db_visitantes['Líder'].isin(lids_f))]

        def get_count(tipo):
            total = sum([1 for l in lids_f for n, t in st.session_state.membros_cadastrados.get(l, {}).items() if t == tipo])
            freq_cel = df_sem[df_sem['Tipo'] == tipo]['Célula'].sum()
            freq_cul = df_sem[df_sem['Tipo'] == tipo]['Culto'].sum()
            return f"{freq_cel}/{total}", f"{freq_cul}/{total}"

        m_cel, m_cul = get_count("Membro")
        fa_cel, fa_cul = get_count("FA")
        v_cel = df_v_sem['Vis_Celula'].sum()
        v_cul = df_v_sem['Vis_Culto'].sum()

        st.write("### 📈 Resumo da Semana")
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.markdown(f'<div class="metric-box"><p class="metric-label">Membros Célula</p><p class="metric-value">{m_cel}</p></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="metric-box"><p class="metric-label">Membros Culto</p><p class="metric-value">{m_cul}</p></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="metric-box"><p class="metric-label">FA Célula</p><p class="metric-value">{fa_cel}</p></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="metric-box"><p class="metric-label">FA Culto</p><p class="metric-value">{fa_cul}</p></div>', unsafe_allow_html=True)
        c5.markdown(f'<div class="metric-box"><p class="metric-label">Visit. Célula</p><p class="metric-value">{v_cel}</p></div>', unsafe_allow_html=True)
        c6.markdown(f'<div class="metric-box"><p class="metric-label">Visit. Culto</p><p class="metric-value">{v_cul}</p></div>', unsafe_allow_html=True)

        col_graf, col_alert = st.columns([2, 1])
        with col_graf:
            st.write("#### Evolução Semanal (Presença Total)")
            df_l_sem = df_sem.groupby('Líder')[['Célula', 'Culto']].sum().reset_index()
            fig_sem = go.Figure()
            fig_sem.add_trace(go.Scatter(x=df_l_sem['Líder'], y=df_l_sem['Célula'], name="Célula", mode='lines+markers+text', text=df_l_sem['Célula'], textposition="top center", line=dict(color='#38BDF8')))
            fig_sem.add_trace(go.Scatter(x=df_l_sem['Líder'], y=df_l_sem['Culto'], name="Culto", mode='lines+markers+text', text=df_l_sem['Culto'], textposition="top center", line=dict(color='#0284C7')))
            fig_sem.update_layout(template="plotly_dark", height=300, margin=dict(l=0,r=0,b=0,t=30))
            st.plotly_chart(fig_sem, use_container_width=True)
            
            st.write("#### Evolução Mensal")
            df_ev = st.session_state.db[st.session_state.db['Líder'].isin(lids_f)].groupby('Data')[['Célula', 'Culto']].sum().reset_index()
            fig_mes = px.line(df_ev, x='Data', y=['Célula', 'Culto'], markers=True, color_discrete_sequence=['#38BDF8', '#0284C7'])
            fig_mes.update_layout(template="plotly_dark", height=250)
            st.plotly_chart(fig_mes, use_container_width=True)

        with col_alert:
            st.write("#### ⚠️ Alertas e Atenção")
            for lider in lids_f:
                df_h = st.session_state.db[st.session_state.db['Líder'] == lider].sort_values('Data', ascending=False)
                for m in df_h['Nome'].unique():
                    u = df_h[df_h['Nome'] == m].head(2)
                    if len(u) == 2 and u['Célula'].sum() == 0:
                        st.markdown(f'<div class="warning-box">🚨 {m} ({lider}): Faltou 2x na Célula</div>', unsafe_allow_html=True)
            for lider in lids_f:
                df_v_h = st.session_state.db_visitantes[st.session_state.db_visitantes['Líder'] == lider].sort_values('Data', ascending=False).head(2)
                if len(df_v_h) == 2 and df_v_h['Vis_Celula'].sum() == 0:
                    st.markdown(f'<div class="warning-box">📉 {lider}: 0 Visitantes nas últimas 2 semanas</div>', unsafe_allow_html=True)

with tab_ob:
    st.subheader("📋 Relatório por Célula")
    if not st.session_state.db.empty:
        ob_res = []
        for l in lids_f:
            m_total = len(st.session_state.membros_cadastrados.get(l, {}))
            d_l = st.session_state.db[(st.session_state.db['Líder'] == l) & (st.session_state.db['Data'] == data_sel)]
            ob_res.append({"Célula": l, "Total Membros": m_total, "Pres. Célula": d_l['Célula'].sum(), "Pres. Culto": d_l['Culto'].sum()})
        st.dataframe(pd.DataFrame(ob_res), use_container_width=True)

with tab_lanc:
    if not st.session_state.membros_cadastrados:
        st.warning("Cadastre líderes em GESTÃO.")
    else:
        ca, cb, cc = st.columns(3)
        m_s = ca.selectbox("Mês", MESES_NOMES, key="m_l")
        d_s = cb.selectbox("Data", get_sabados(m_s), format_func=lambda x: x.strftime('%d/%m'), key="d_l")
        l_s = cc.selectbox("Líder", sorted(st.session_state.membros_cadastrados.keys()), key="l_l")
        
        st.write("### 👥 Visitantes")
        va, vb = st.columns(2)
        v_cel_in = va.number_input("Visitantes Célula", min_value=0, key="vc_in")
        v_cul_in = vb.number_input("Visitantes Culto", min_value=0, key="vu_in")
        
        st.write("### ✅ Chamada")
        mem = st.session_state.membros_cadastrados[l_s]
        novos = []
        for n, t in mem.items():
            c_n, c_e, c_u = st.columns([2,1,1])
            c_n.write(f"**{n}** ({t})")
            p_e = c_e.checkbox("Célula", key=f"e_{n}_{d_s}")
            p_u = c_u.checkbox("Culto", key=f"u_{n}_{d_s}")
            novos.append({"Data": d_s, "Líder": l_s, "Nome": n, "Tipo": t, "Célula": 1 if p_e else 0, "Culto": 1 if p_u else 0})
            
        if st.button("💾 SALVAR TUDO", use_container_width=True, type="primary"):
            df_cl = st.session_state.db[~((st.session_state.db['Data']==d_s) & (st.session_state.db['Líder']==l_s))]
            st.session_state.db = pd.concat([df_cl, pd.DataFrame(novos)])
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Presencas", data=st.session_state.db)
            df_vc = st.session_state.db_visitantes[~((st.session_state.db_visitantes['Data']==d_s) & (st.session_state.db_visitantes['Líder']==l_s))]
            st.session_state.db_visitantes = pd.concat([df_vc, pd.DataFrame([{"Data": d_s, "Líder": l_s, "Vis_Celula": v_cel_in, "Vis_Culto": v_cul_in}])])
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Visitantes", data=st.session_state.db_visitantes)
            st.cache_data.clear()
            st.success("Sincronizado!")
            st.rerun()

with tab_gestao:
    st.write("### ⚙️ Gestão")
    n_l = st.text_input("Novo Líder")
    if st.button("Criar Célula"):
        if n_l:
            st.session_state.membros_cadastrados[n_l] = {}
            sincronizar_membros()
            st.rerun()
    st.divider()
    if st.session_state.membros_cadastrados:
        l_sel = st.selectbox("Célula:", sorted(st.session_state.membros_cadastrados.keys()))
        n_m = st.text_input("Nome")
        t_m = st.radio("Tipo", ["Membro", "FA"], horizontal=True)
        if st.button("Salvar Membro"):
            st.session_state.membros_cadastrados[l_sel][n_m] = t_m
            sincronizar_membros()
            st.rerun()
