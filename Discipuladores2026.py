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

# --- 4. ESTILO AZUL ---
st.markdown("""
<style>
    .stApp { background-color: #0F172A; color: #F8FAFC; }
    .main-title { background: linear-gradient(90deg, #60A5FA 0%, #1D4ED8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; font-size: 26px; text-align: center; margin-bottom: 5px;}
    .metric-box { background: #1E293B; padding: 15px; border-radius: 12px; border-left: 5px solid #3B82F6; text-align: center; margin-bottom: 10px; }
    .metric-label { font-size: 11px; color: #94A3B8; text-transform: uppercase; font-weight: bold; }
    .metric-value { font-size: 32px; font-weight: 900; color: #3B82F6; }
    .section-header { font-size: 16px; font-weight: bold; color: #60A5FA; margin: 15px 0 5px 0; border-bottom: 1px solid #334155; padding-bottom: 5px; }
</style>
""", unsafe_allow_html=True)

MESES_NOMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MESES_MAP = {n: i+1 for i, n in enumerate(MESES_NOMES)}

# --- 5. INTERFACE ---
st.markdown('<p class="main-title">🛡️ DISTRITO PRO 2026</p>', unsafe_allow_html=True)
tab_dash, tab_lanc, tab_gestao, tab_rel = st.tabs(["📊 DASH", "📝 LANÇAR", "⚙️ GESTÃO", "📋 RELATÓRIO"])

# --- TAB DASHBOARDS ---
with tab_dash:
    if st.session_state.db.empty:
        st.info("💡 Sem dados.")
    else:
        lids_f = st.multiselect("Células:", sorted(st.session_state.membros_cadastrados.keys()), default=list(st.session_state.membros_cadastrados.keys()))
        mes_sel = st.selectbox("Mês:", MESES_NOMES, index=datetime.now().month - 1)
        
        df_filtro_m = st.session_state.db[(st.session_state.db['Data'].dt.month == MESES_MAP[mes_sel]) & (st.session_state.db['Líder'].isin(lids_f))]
        df_v_filtro_m = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data'].dt.month == MESES_MAP[mes_sel]) & (st.session_state.db_visitantes['Líder'].isin(lids_f))]

        if df_filtro_m.empty:
            st.warning("Sem dados.")
        else:
            # --- 1. DASH CÉLULA (LINHA SEMANAL) ---
            st.markdown('<p class="section-header">🏠 CÉLULA: TENDÊNCIA DO MÊS</p>', unsafe_allow_html=True)
            ev_cel_sem = df_filtro_m.groupby('Data')['Célula'].sum().reset_index()
            ev_vis_sem = df_v_filtro_m.groupby('Data')['Vis_Celula'].sum().reset_index()
            df_tend_cel = pd.merge(ev_cel_sem, ev_vis_sem, on='Data', how='outer').fillna(0).sort_values('Data')

            # Card Total do Mês Selecionado
            st.markdown(f'<div class="metric-box"><p class="metric-label">Média de Público Célula no Mês</p><p class="metric-value">{int(df_tend_cel["Célula"].mean() + df_tend_cel["Vis_Celula"].mean())}</p></div>', unsafe_allow_html=True)

            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(x=df_tend_cel['Data'], y=df_tend_cel['Célula'], name="Membros", mode='lines+markers+text', text=df_tend_cel['Célula'], textposition="top center", line=dict(color='#2563EB', width=4)))
            fig1.add_trace(go.Scatter(x=df_tend_cel['Data'], y=df_tend_cel['Vis_Celula'], name="Visitantes", mode='lines+markers+text', text=df_tend_cel['Vis_Celula'], textposition="top center", line=dict(color='#60A5FA', width=3, dash='dot')))
            fig1.update_layout(template="plotly_dark", height=280, margin=dict(l=0,r=0,b=0,t=20), legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})

            # --- 2. DASH CULTO (LINHA SEMANAL) ---
            st.markdown('<p class="section-header">⛪ CULTO: TENDÊNCIA DO MÊS</p>', unsafe_allow_html=True)
            ev_cul_sem = df_filtro_m.groupby('Data')['Culto'].sum().reset_index()
            ev_vis_cul = df_v_filtro_m.groupby('Data')['Vis_Culto'].sum().reset_index()
            df_tend_cul = pd.merge(ev_cul_sem, ev_vis_cul, on='Data', how='outer').fillna(0).sort_values('Data')

            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=df_tend_cul['Data'], y=df_tend_cul['Culto'], name="Membros", mode='lines+markers+text', text=df_tend_cul['Culto'], textposition="top center", line=dict(color='#1D4ED8', width=4)))
            fig2.add_trace(go.Scatter(x=df_tend_cul['Data'], y=df_tend_cul['Vis_Culto'], name="Visitantes", mode='lines+markers+text', text=df_tend_cul['Vis_Culto'], textposition="top center", line=dict(color='#93C5FD', width=3, dash='dot')))
            fig2.update_layout(template="plotly_dark", height=280, margin=dict(l=0,r=0,b=0,t=20), legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})

            # --- 3. EVOLUÇÃO TRIMESTRAL (MENSALIZADO) ---
            st.markdown('<p class="section-header">📅 EVOLUÇÃO TRIMESTRAL (POR MÊS)</p>', unsafe_allow_html=True)
            mes_n = MESES_MAP[mes_sel]
            meses_tri = [(mes_n - i) for i in range(3)]
            meses_tri = [m if m > 0 else m + 12 for m in meses_tri]
            
            df_tri = st.session_state.db[(st.session_state.db['Data'].dt.month.isin(meses_tri)) & (st.session_state.db['Líder'].isin(lids_f))].copy()
            df_tri['Mes_Nome'] = df_tri['Data'].dt.month.map({v: k for k, v in MESES_MAP.items()})
            
            resumo_mensal = df_tri.groupby('Mes_Nome', sort=False)['Célula'].sum().reset_index()
            # Ordenar para garantir que o trimestre siga a ordem cronológica
            resumo_mensal['Mes_Idx'] = resumo_mensal['Mes_Nome'].map(MESES_MAP)
            resumo_mensal = resumo_mensal.sort_values('Mes_Idx')

            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(x=resumo_mensal['Mes_Nome'], y=resumo_mensal['Célula'], mode='lines+markers+text', text=resumo_mensal['Célula'], textposition="top center", line=dict(color='#3B82F6', width=5), fill='tozeroy'))
            fig3.update_layout(template="plotly_dark", height=250, margin=dict(l=0,r=0,b=0,t=20), yaxis=dict(showgrid=False))
            st.plotly_chart(fig3, use_container_width=True, config={'displayModeBar': False})

# --- TAB LANÇAR ---
with tab_lanc:
    if not st.session_state.membros_cadastrados:
        st.warning("Configure a Célula em Gestão.")
    else:
        l_l = st.selectbox("Líder", sorted(st.session_state.membros_cadastrados.keys()))
        d_l = st.date_input("Data (Sábado)", value=date.today())
        v_ce = st.number_input("Vis. Célula", 0)
        v_cu = st.number_input("Vis. Culto", 0)
        
        novos = []
        for n, t in st.session_state.membros_cadastrados[l_l].items():
            col_a, col_b = st.columns([3, 2])
            p_e = col_b.checkbox("Cél", key=f"e_{n}")
            p_u = col_b.checkbox("Cul", key=f"u_{n}")
            novos.append({"Data": d_l, "Líder": l_l, "Nome": n, "Tipo": t, "Célula": 1 if p_e else 0, "Culto": 1 if p_u else 0})
            
        if st.button("💾 SALVAR", use_container_width=True, type="primary"):
            df_p_new = pd.concat([st.session_state.db[~((st.session_state.db['Data']==pd.to_datetime(d_l)) & (st.session_state.db['Líder']==l_l))], pd.DataFrame(novos)])
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Presencas", data=df_p_new)
            df_v_new = pd.concat([st.session_state.db_visitantes[~((st.session_state.db_visitantes['Data']==pd.to_datetime(d_l)) & (st.session_state.db_visitantes['Líder']==l_l))], pd.DataFrame([{"Data": d_l, "Líder": l_l, "Vis_Celula": v_ce, "Vis_Culto": v_cu}])])
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Visitantes", data=df_v_new)
            st.cache_data.clear(); st.success("Salvo!"); st.rerun()

# --- TAB GESTÃO ---
with tab_gestao:
    st.markdown('<p class="section-header">⚙️ CONFIGURAÇÃO</p>', unsafe_allow_html=True)
    with st.expander("➕ Adicionar"):
        n_l = st.text_input("Nova Célula")
        if st.button("Criar"):
            if n_l: st.session_state.membros_cadastrados[n_l] = {}; sincronizar_membros(); st.rerun()
        st.divider()
        l_s = st.selectbox("Célula:", sorted(st.session_state.membros_cadastrados.keys()))
        n_m = st.text_input("Nome Pessoa")
        t_m = st.radio("Tipo", ["Membro", "FA"], horizontal=True)
        if st.button("Adicionar Pessoa"):
            st.session_state.membros_cadastrados[l_s][n_m] = t_m
            sincronizar_membros(); st.rerun()
            
    with st.expander("🗑️ Editar / Excluir"):
        l_e = st.selectbox("Escolha a Célula:", sorted(st.session_state.membros_cadastrados.keys()), key="le")
        if st.session_state.membros_cadastrados[l_e]:
            p_e = st.selectbox("Escolha a Pessoa:", sorted(st.session_state.membros_cadastrados[l_e].keys()))
            at = st.session_state.membros_cadastrados[l_e][p_e]
            if st.button(f"Mudar para {'FA' if at == 'Membro' else 'Membro'}"):
                st.session_state.membros_cadastrados[l_e][p_e] = "FA" if at == "Membro" else "Membro"
                sincronizar_membros(); st.rerun()
            if st.button("Excluir", type="primary"):
                del st.session_state.membros_cadastrados[l_e][p_e]; sincronizar_membros(); st.rerun()

# --- TAB RELATÓRIO ---
with tab_rel:
    m_r = st.selectbox("Mês:", MESES_NOMES, index=datetime.now().month-1, key="rel")
    df_r = st.session_state.db[st.session_state.db['Data'].dt.month == MESES_MAP[m_r]]
    if not df_r.empty:
        for s in sorted(df_r['Data'].unique(), reverse=True):
            st.write(f"📅 **{s.strftime('%d/%m')}**")
            res = []
            for lid in sorted(st.session_state.membros_cadastrados.keys()):
                f_p = df_r[(df_r['Data'] == s) & (df_r['Líder'] == lid)]
                f_v = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data'] == s) & (st.session_state.db_visitantes['Líder'] == lid)]
                res.append({"Líder": lid, "Cél": int(f_p['Célula'].sum() + f_v['Vis_Celula'].sum()), "Cul": int(f_p['Culto'].sum() + f_v['Vis_Culto'].sum())})
            st.dataframe(pd.DataFrame(res), use_container_width=True)
