import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta, datetime
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
        if not df_p.empty: 
            df_p['Data'] = pd.to_datetime(df_p['Data'])
            df_p[['Célula', 'Culto']] = df_p[['Célula', 'Culto']].fillna(0).astype(int)
        if not df_v.empty: 
            df_v['Data'] = pd.to_datetime(df_v['Data'])
            df_v[['Vis_Celula', 'Vis_Culto']] = df_v[['Vis_Celula', 'Vis_Culto']].fillna(0).astype(int)
        
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

# --- 4. ESTILO CUSTOMIZADO (MOBILE FIRST) ---
st.markdown("""
<style>
    .stApp { background-color: #0F172A; color: #F8FAFC; }
    .main-title { background: linear-gradient(90deg, #38BDF8 0%, #1D4ED8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; font-size: 28px; text-align: center; margin-bottom: 10px;}
    .metric-box { background: #1E293B; padding: 15px; border-radius: 12px; border-bottom: 4px solid #38BDF8; text-align: center; margin-bottom: 10px; }
    .metric-label { font-size: 12px; color: #94A3B8; text-transform: uppercase; font-weight: bold; }
    .metric-value { font-size: 36px; font-weight: 900; color: #38BDF8; }
    .section-header { font-size: 18px; font-weight: bold; color: #60A5FA; border-left: 4px solid #1D4ED8; padding-left: 10px; margin: 20px 0 10px 0; }
    hr { border: 0; height: 1px; background: #334155; margin: 20px 0; }
    /* Ajustes para Mobile */
    @media (max-width: 640px) {
        .metric-value { font-size: 28px; }
        .stMultiSelect div div { font-size: 12px; }
    }
</style>
""", unsafe_allow_html=True)

MESES_NOMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MESES_MAP = {n: i+1 for i, n in enumerate(MESES_NOMES)}

# --- 5. INTERFACE ---
st.markdown('<p class="main-title">🛡️ DISTRITO PRO 2026</p>', unsafe_allow_html=True)
tab_dash, tab_lanc, tab_gestao, tab_ob = st.tabs(["📊 DASH", "📝 LANÇAR", "⚙️ GESTÃO", "📋 RELATÓRIO"])

# --- TAB DASHBOARDS ---
with tab_dash:
    if st.session_state.db.empty:
        st.info("💡 Sem dados para exibir.")
    else:
        # Filtros Compactos
        lids_atuais = sorted(list(st.session_state.membros_cadastrados.keys()))
        lids_f = st.multiselect("Filtrar Células:", lids_atuais, default=lids_atuais)
        
        col_m, col_s = st.columns(2)
        mes_sel = col_m.selectbox("Mês:", MESES_NOMES, index=datetime.now().month - 1)
        df_mes_f = st.session_state.db[st.session_state.db['Data'].dt.month == MESES_MAP[mes_sel]]
        
        if df_mes_f.empty:
            st.warning(f"Sem dados em {mes_sel}.")
        else:
            datas_disp = sorted(df_mes_f['Data'].unique(), reverse=True)
            data_sel = col_s.selectbox("Semana:", datas_disp, format_func=lambda x: x.strftime('%d/%m/%Y'))

            # Dados
            df_sem = st.session_state.db[(st.session_state.db['Data'] == data_sel) & (st.session_state.db['Líder'].isin(lids_f))]
            df_v_sem = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data'] == data_sel) & (st.session_state.db_visitantes['Líder'].isin(lids_f))]
            total_cel = int(df_sem['Célula'].sum() + df_v_sem['Vis_Celula'].sum())
            total_cul = int(df_sem['Culto'].sum() + df_v_sem['Vis_Culto'].sum())

            # --- LINHA 1: CÉLULA ---
            st.markdown('<p class="section-header">🏠 SEMANAL: CÉLULA</p>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-box"><p class="metric-label">Total Célula (Membros + Vis)</p><p class="metric-value">{total_cel}</p></div>', unsafe_allow_html=True)
            
            df_c = df_sem.groupby('Líder')[['Célula']].sum().reset_index()
            df_cv = df_v_sem.groupby('Líder')[['Vis_Celula']].sum().reset_index()
            df_m_c = pd.merge(df_c, df_cv, on='Líder', how='left').fillna(0)
            
            fig_c = go.Figure()
            fig_c.add_trace(go.Bar(x=df_m_c['Líder'], y=df_m_c['Célula'], name="Membros/FA", marker_color='#1E40AF'))
            fig_c.add_trace(go.Bar(x=df_m_c['Líder'], y=df_m_c['Vis_Celula'], name="Visitantes", marker_color='#60A5FA'))
            fig_c.update_layout(template="plotly_dark", barmode='stack', height=300, margin=dict(l=0,r=0,b=0,t=10), legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig_c, use_container_width=True, config={'displayModeBar': False})

            # --- LINHA 2: CULTO ---
            st.markdown('<p class="section-header">⛪ SEMANAL: CULTO</p>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-box"><p class="metric-label">Total Culto (Membros + Vis)</p><p class="metric-value" style="color:#60A5FA;">{total_cul}</p></div>', unsafe_allow_html=True)
            
            df_u = df_sem.groupby('Líder')[['Culto']].sum().reset_index()
            df_uv = df_v_sem.groupby('Líder')[['Vis_Culto']].sum().reset_index()
            df_m_u = pd.merge(df_u, df_uv, on='Líder', how='left').fillna(0)
            
            fig_u = go.Figure()
            fig_u.add_trace(go.Bar(x=df_m_u['Líder'], y=df_m_u['Culto'], name="Membros/FA", marker_color='#1D4ED8'))
            fig_u.add_trace(go.Bar(x=df_m_u['Líder'], y=df_m_u['Vis_Culto'], name="Visitantes", marker_color='#93C5FD'))
            fig_u.update_layout(template="plotly_dark", barmode='stack', height=300, margin=dict(l=0,r=0,b=0,t=10), legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig_u, use_container_width=True, config={'displayModeBar': False})

            # --- LINHA 3: EVOLUÇÃO ---
            st.markdown('<p class="section-header">📅 EVOLUÇÃO TRIMESTRAL</p>', unsafe_allow_html=True)
            mes_n = MESES_MAP[mes_sel]
            meses_tri = [(mes_n - i) for i in range(3)]
            meses_tri = [m if m > 0 else m + 12 for m in meses_tri]
            
            df_tri_p = st.session_state.db[(st.session_state.db['Data'].dt.month.isin(meses_tri)) & (st.session_state.db['Líder'].isin(lids_f))]
            df_tri_v = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data'].dt.month.isin(meses_tri)) & (st.session_state.db_visitantes['Líder'].isin(lids_f))]
            
            ev_p = df_tri_p.groupby('Data')['Célula'].sum().reset_index()
            ev_v = df_tri_v.groupby('Data')['Vis_Celula'].sum().reset_index()
            df_ev_tri = pd.merge(ev_p, ev_v, on='Data', how='outer').fillna(0).sort_values('Data')

            fig_tri = go.Figure()
            fig_tri.add_trace(go.Scatter(x=df_ev_tri['Data'], y=df_ev_tri['Célula'], name="Membros", mode='lines+markers', line=dict(color='#38BDF8', width=3)))
            fig_tri.add_trace(go.Scatter(x=df_ev_tri['Data'], y=df_ev_tri['Vis_Celula'], name="Vis", mode='lines+markers', line=dict(color='#1D4ED8', width=2, dash='dot')))
            fig_tri.update_layout(template="plotly_dark", height=300, margin=dict(l=0,r=0,b=0,t=10), legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig_tri, use_container_width=True, config={'displayModeBar': False})

            with st.expander("🚨 ALERTAS"):
                for lider in lids_f:
                    df_h = st.session_state.db[st.session_state.db['Líder'] == lider].sort_values('Data', ascending=False)
                    for m in df_h['Nome'].unique():
                        u = df_h[df_h['Nome'] == m].head(2)
                        if len(u) == 2 and u['Célula'].sum() == 0:
                            st.markdown(f'<div class="alert-danger">⚠️ {m} ({lider}): Faltou 2x</div>', unsafe_allow_html=True)

# --- TABELAS RESTANTES (LANÇAR, GESTÃO, RELATÓRIO) ---
with tab_lanc:
    if not st.session_state.membros_cadastrados:
        st.warning("Cadastre líderes em GESTÃO.")
    else:
        l_l = st.selectbox("Líder", sorted(st.session_state.membros_cadastrados.keys()))
        m_l = st.selectbox("Mês", MESES_NOMES, index=datetime.now().month-1)
        d_l = st.selectbox("Data", [d for d in [date(2026, MESES_MAP[m_l], 1) + timedelta(days=x) for x in range(32)] if d.month == MESES_MAP[m_l] and d.weekday() == 5], format_func=lambda x: x.strftime('%d/%m'))
        
        va, vb = st.columns(2)
        v_cel_in = va.number_input("Vis. Célula", min_value=0, step=1)
        v_cul_in = vb.number_input("Vis. Culto", min_value=0, step=1)
        
        mem = st.session_state.membros_cadastrados[l_l]
        novos = []
        for n, t in mem.items():
            c_n, c_c = st.columns([3, 2])
            c_n.write(f"**{n}**")
            p_e = c_c.checkbox("Cél", key=f"e_{n}")
            p_u = c_c.checkbox("Cul", key=f"u_{n}")
            novos.append({"Data": d_l, "Líder": l_l, "Nome": n, "Tipo": t, "Célula": 1 if p_e else 0, "Culto": 1 if p_u else 0})
            
        if st.button("💾 SALVAR", use_container_width=True, type="primary"):
            df_p_new = pd.concat([st.session_state.db[~((st.session_state.db['Data']==pd.to_datetime(d_l)) & (st.session_state.db['Líder']==l_l))], pd.DataFrame(novos)])
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Presencas", data=df_p_new)
            df_v_new = pd.concat([st.session_state.db_visitantes[~((st.session_state.db_visitantes['Data']==pd.to_datetime(d_l)) & (st.session_state.db_visitantes['Líder']==l_l))], pd.DataFrame([{"Data": d_l, "Líder": l_l, "Vis_Celula": v_cel_in, "Vis_Culto": v_cul_in}])])
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Visitantes", data=df_v_new)
            st.cache_data.clear()
            st.success("Salvo!"); st.rerun()

with tab_gestao:
    st.subheader("⚙️ GESTÃO")
    with st.expander("➕ Adicionar Novo"):
        n_l = st.text_input("Nova Célula (Líder)")
        if st.button("Criar"): 
            if n_l: st.session_state.membros_cadastrados[n_l] = {}; sincronizar_membros(); st.rerun()
        st.divider()
        l_s = st.selectbox("Na Célula:", sorted(st.session_state.membros_cadastrados.keys()))
        n_m = st.text_input("Nome")
        t_m = st.radio("Tipo", ["Membro", "FA"], horizontal=True)
        if st.button("Salvar Pessoa"):
            st.session_state.membros_cadastrados[l_s][n_m] = t_m
            sincronizar_membros(); st.rerun()
    
    with st.expander("🗑️ Editar / Excluir"):
        l_e = st.selectbox("Célula:", sorted(st.session_state.membros_cadastrados.keys()), key="le")
        if st.session_state.membros_cadastrados[l_e]:
            p_e = st.selectbox("Pessoa:", sorted(st.session_state.membros_cadastrados[l_e].keys()))
            at = st.session_state.membros_cadastrados[l_e][p_e]
            if st.button(f"Mudar para {'FA' if at == 'Membro' else 'Membro'}"):
                st.session_state.membros_cadastrados[l_e][p_e] = "FA" if at == "Membro" else "Membro"
                sincronizar_membros(); st.rerun()
            if st.button("Remover Pessoa", type="primary"):
                del st.session_state.membros_cadastrados[l_e][p_e]; sincronizar_membros(); st.rerun()

with tab_ob:
    m_o = st.selectbox("Relatório Mês:", MESES_NOMES, index=datetime.now().month-1)
    df_p_o = st.session_state.db[st.session_state.db['Data'].dt.month == MESES_MAP[m_o]]
    if not df_p_o.empty:
        for s in sorted(df_p_o['Data'].unique(), reverse=True):
            st.write(f"📅 **{s.strftime('%d/%m')}**")
            d_o = []
            for lid in sorted(st.session_state.membros_cadastrados.keys()):
                f_p = df_p_o[(df_p_o['Data'] == s) & (df_p_o['Líder'] == lid)]
                f_v = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data'] == s) & (st.session_state.db_visitantes['Líder'] == lid)]
                d_o.append({"Líder": lid, "Célula": int(f_p['Célula'].sum() + f_v['Vis_Celula'].sum()), "Culto": int(f_p['Culto'].sum() + f_v['Vis_Culto'].sum())})
            st.dataframe(pd.DataFrame(d_o), use_container_width=True)
