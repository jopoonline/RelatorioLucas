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

# --- 4. ESTILO ---
st.markdown("""
<style>
    .stApp { background-color: #0F172A; color: #F8FAFC; }
    .main-title { background: linear-gradient(90deg, #38BDF8 0%, #0284C7 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; font-size: 32px; text-align: center; margin-bottom: 20px;}
    .metric-box { background: #1E293B; padding: 20px; border-radius: 12px; border-top: 5px solid #0284C7; text-align: center; height: 100%; display: flex; flex-direction: column; justify-content: center; }
    .metric-label { font-size: 14px; color: #94A3B8; text-transform: uppercase; font-weight: bold; margin-bottom: 5px; }
    .metric-value { font-size: 42px; font-weight: 900; color: #38BDF8; margin: 0; }
    .alert-danger { background: #450a0a; padding: 10px; border-radius: 5px; border-left: 5px solid #ef4444; margin-bottom: 8px; font-size: 13px; color: #fecaca; }
    hr { border: 0; height: 1px; background: #334155; margin: 30px 0; }
</style>
""", unsafe_allow_html=True)

MESES_NOMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MESES_MAP = {n: i+1 for i, n in enumerate(MESES_NOMES)}

# --- 5. INTERFACE ---
st.markdown('<p class="main-title">🛡️ DISTRITO PRO 2026</p>', unsafe_allow_html=True)
tab_dash, tab_lanc, tab_gestao, tab_ob = st.tabs(["📊 DASHBOARDS", "📝 LANÇAR", "⚙️ GESTÃO", "📋 RELATÓRIO OB"])

# --- TAB DASHBOARDS ---
with tab_dash:
    if st.session_state.db.empty:
        st.info("💡 Sem dados para exibir.")
    else:
        # Filtros no Topo
        col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
        lids_atuais = sorted(list(st.session_state.membros_cadastrados.keys()))
        lids_f = col_f1.multiselect("Filtrar Células:", lids_atuais, default=lids_atuais)
        
        mes_sel = col_f2.selectbox("Mês:", MESES_NOMES, index=datetime.now().month - 1)
        df_mes_f = st.session_state.db[st.session_state.db['Data'].dt.month == MESES_MAP[mes_sel]]
        
        if df_mes_f.empty:
            st.warning(f"Sem dados em {mes_sel}.")
        else:
            datas_disp = sorted(df_mes_f['Data'].unique(), reverse=True)
            data_sel = col_f3.selectbox("Semana:", datas_disp, format_func=lambda x: x.strftime('%d/%m/%Y'))

            # Processamento de Dados
            df_sem = st.session_state.db[(st.session_state.db['Data'] == data_sel) & (st.session_state.db['Líder'].isin(lids_f))]
            df_v_sem = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data'] == data_sel) & (st.session_state.db_visitantes['Líder'].isin(lids_f))]

            total_cel = int(df_sem['Célula'].sum() + df_v_sem['Vis_Celula'].sum())
            total_cul = int(df_sem['Culto'].sum() + df_v_sem['Vis_Culto'].sum())

            # --- LINHA 1: DASH CÉLULA ---
            st.markdown("### 🏠 1. Dashboard Célula Semanal")
            c1, c2 = st.columns([1, 3])
            with c1:
                st.markdown(f'<div class="metric-box"><p class="metric-label">Total Geral<br>Célula</p><p class="metric-value">{total_cel}</p></div>', unsafe_allow_html=True)
            with c2:
                df_c = df_sem.groupby('Líder')[['Célula']].sum().reset_index()
                df_cv = df_v_sem.groupby('Líder')[['Vis_Celula']].sum().reset_index()
                df_m_c = pd.merge(df_c, df_cv, on='Líder', how='left').fillna(0)
                
                fig_c = go.Figure()
                fig_c.add_trace(go.Bar(x=df_m_c['Líder'], y=df_m_c['Célula'], name="Membros/FA", marker_color='#38BDF8', text=df_m_c['Célula'], textposition='auto'))
                fig_c.add_trace(go.Bar(x=df_m_c['Líder'], y=df_m_c['Vis_Celula'], name="Visitantes", marker_color='#FACC15', text=df_m_c['Vis_Celula'], textposition='auto'))
                fig_c.update_layout(template="plotly_dark", barmode='stack', height=350, margin=dict(l=0,r=0,b=20,t=20), legend=dict(orientation="h", y=1.1, x=1, xanchor='right'))
                st.plotly_chart(fig_c, use_container_width=True)

            st.markdown("<hr>", unsafe_allow_html=True)

            # --- LINHA 2: DASH CULTO ---
            st.markdown("### ⛪ 2. Dashboard Culto Semanal")
            d1, d2 = st.columns([1, 3])
            with d1:
                st.markdown(f'<div class="metric-box" style="border-top-color:#8B5CF6;"><p class="metric-label">Total Geral<br>Culto</p><p class="metric-value" style="color:#A78BFA;">{total_cul}</p></div>', unsafe_allow_html=True)
            with d2:
                df_u = df_sem.groupby('Líder')[['Culto']].sum().reset_index()
                df_uv = df_v_sem.groupby('Líder')[['Vis_Culto']].sum().reset_index()
                df_m_u = pd.merge(df_u, df_uv, on='Líder', how='left').fillna(0)
                
                fig_u = go.Figure()
                fig_u.add_trace(go.Bar(x=df_m_u['Líder'], y=df_m_u['Culto'], name="Membros/FA", marker_color='#8B5CF6', text=df_m_u['Culto'], textposition='auto'))
                fig_u.add_trace(go.Bar(x=df_m_u['Líder'], y=df_m_u['Vis_Culto'], name="Visitantes", marker_color='#FACC15', text=df_m_u['Vis_Culto'], textposition='auto'))
                fig_u.update_layout(template="plotly_dark", barmode='stack', height=350, margin=dict(l=0,r=0,b=20,t=20), legend=dict(orientation="h", y=1.1, x=1, xanchor='right'))
                st.plotly_chart(fig_u, use_container_width=True)

            st.markdown("<hr>", unsafe_allow_html=True)

            # --- LINHA 3: DASH MENSAL (TRIMESTRE) ---
            st.markdown("### 📅 3. Evolução Trimestral (Público Célula)")
            mes_n = MESES_MAP[mes_sel]
            meses_tri = [(mes_n - i) for i in range(3)]
            meses_tri = [m if m > 0 else m + 12 for m in meses_tri]
            
            df_tri_p = st.session_state.db[(st.session_state.db['Data'].dt.month.isin(meses_tri)) & (st.session_state.db['Líder'].isin(lids_f))]
            df_tri_v = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data'].dt.month.isin(meses_tri)) & (st.session_state.db_visitantes['Líder'].isin(lids_f))]
            
            ev_p = df_tri_p.groupby('Data')['Célula'].sum().reset_index()
            ev_v = df_tri_v.groupby('Data')['Vis_Celula'].sum().reset_index()
            df_ev_tri = pd.merge(ev_p, ev_v, on='Data', how='outer').fillna(0).sort_values('Data')

            fig_tri = go.Figure()
            fig_tri.add_trace(go.Scatter(x=df_ev_tri['Data'], y=df_ev_tri['Célula'], name="Presença Membros/FA", mode='lines+markers+text', text=df_ev_tri['Célula'], textposition="top center", line=dict(color='#38BDF8', width=4)))
            fig_tri.add_trace(go.Scatter(x=df_ev_tri['Data'], y=df_ev_tri['Vis_Celula'], name="Visitantes", mode='lines+markers+text', text=df_ev_tri['Vis_Celula'], textposition="top center", line=dict(color='#FACC15', width=3, dash='dot')))
            fig_tri.update_layout(template="plotly_dark", height=400, margin=dict(l=10,r=10,b=20,t=20), legend=dict(orientation="h", y=1.1, x=1, xanchor='right'))
            st.plotly_chart(fig_tri, use_container_width=True)

            # Alertas
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("🚨 Ver Alertas de Atenção"):
                for lider in lids_f:
                    df_h = st.session_state.db[st.session_state.db['Líder'] == lider].sort_values('Data', ascending=False)
                    for m in df_h['Nome'].unique():
                        u = df_h[df_h['Nome'] == m].head(2)
                        if len(u) == 2 and u['Célula'].sum() == 0:
                            st.markdown(f'<div class="alert-danger">⚠️ {m} ({lider}): Faltou 2x seguidas</div>', unsafe_allow_html=True)

# --- TAB LANÇAR ---
with tab_lanc:
    if not st.session_state.membros_cadastrados:
        st.warning("Cadastre líderes em GESTÃO.")
    else:
        ca, cb, cc = st.columns(3)
        m_l = ca.selectbox("Mês Lançamento", MESES_NOMES, index=datetime.now().month-1)
        d_l = cb.selectbox("Data Lançamento", [d for d in [date(2026, MESES_MAP[m_l], 1) + timedelta(days=x) for x in range(32)] if d.month == MESES_MAP[m_l] and d.weekday() == 5], format_func=lambda x: x.strftime('%d/%m'))
        l_l = cc.selectbox("Líder", sorted(st.session_state.membros_cadastrados.keys()))
        
        va, vb = st.columns(2)
        v_cel_in = va.number_input("Visitantes Célula", min_value=0, step=1)
        v_cul_in = vb.number_input("Visitantes Culto", min_value=0, step=1)
        
        mem = st.session_state.membros_cadastrados[l_l]
        novos = []
        for n, t in mem.items():
            c_n, c_e, c_u = st.columns([2,1,1])
            c_n.write(f"**{n}** ({t})")
            p_e = c_e.checkbox("Célula", key=f"e_{n}_{d_l}")
            p_u = c_u.checkbox("Culto", key=f"u_{n}_{d_l}")
            novos.append({"Data": d_l, "Líder": l_l, "Nome": n, "Tipo": t, "Célula": 1 if p_e else 0, "Culto": 1 if p_u else 0})
            
        if st.button("💾 SALVAR TUDO", use_container_width=True, type="primary"):
            df_p_new = pd.concat([st.session_state.db[~((st.session_state.db['Data']==pd.to_datetime(d_l)) & (st.session_state.db['Líder']==l_l))], pd.DataFrame(novos)])
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Presencas", data=df_p_new)
            df_v_new = pd.concat([st.session_state.db_visitantes[~((st.session_state.db_visitantes['Data']==pd.to_datetime(d_l)) & (st.session_state.db_visitantes['Líder']==l_l))], pd.DataFrame([{"Data": d_l, "Líder": l_l, "Vis_Celula": v_cel_in, "Vis_Culto": v_cul_in}])])
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Visitantes", data=df_v_new)
            st.cache_data.clear()
            st.success("Salvo com sucesso!")
            st.rerun()

# --- TAB GESTÃO ---
with tab_gestao:
    st.subheader("⚙️ Cadastro de Membros e Líderes")
    col1, col2 = st.columns(2)
    with col1:
        n_l = st.text_input("Novo Líder")
        if st.button("Criar Célula"):
            if n_l: st.session_state.membros_cadastrados[n_l] = {}; sincronizar_membros(); st.rerun()
    with col2:
        if st.session_state.membros_cadastrados:
            l_sel = st.selectbox("Na Célula:", sorted(st.session_state.membros_cadastrados.keys()))
            n_m = st.text_input("Nome da Pessoa")
            t_m = st.radio("Tipo", ["Membro", "FA"], horizontal=True)
            if st.button("Salvar Pessoa"):
                st.session_state.membros_cadastrados[l_sel][n_m] = t_m
                sincronizar_membros(); st.rerun()

    st.divider()
    st.subheader("🗑️ Área de Exclusão / Edição")
    col_ed1, col_ed2 = st.columns(2)
    with col_ed1:
        st.write("**Gerenciar Pessoas**")
        l_ed = st.selectbox("Célula:", sorted(st.session_state.membros_cadastrados.keys()), key="l_ed")
        if st.session_state.membros_cadastrados[l_ed]:
            p_ed = st.selectbox("Pessoa:", sorted(st.session_state.membros_cadastrados[l_ed].keys()))
            tipo_at = st.session_state.membros_cadastrados[l_ed][p_ed]
            st.info(f"Status atual: {tipo_at}")
            ce1, ce2 = st.columns(2)
            if ce1.button(f"Mudar para {'FA' if tipo_at == 'Membro' else 'Membro'}"):
                st.session_state.membros_cadastrados[l_ed][p_ed] = "FA" if tipo_at == "Membro" else "Membro"
                sincronizar_membros(); st.rerun()
            if ce2.button("Excluir Pessoa", type="primary"):
                del st.session_state.membros_cadastrados[l_ed][p_ed]
                sincronizar_membros(); st.rerun()
    with col_ed2:
        st.write("**Remover Unidade**")
        l_del = st.selectbox("Célula para excluir:", sorted(st.session_state.membros_cadastrados.keys()), key="l_del")
        if st.button("EXCLUIR CÉLULA COMPLETA", type="primary"):
            del st.session_state.membros_cadastrados[l_del]
            sincronizar_membros(); st.rerun()

# --- TAB RELATÓRIO OB ---
with tab_ob:
    st.subheader("📋 Relatório Semanal Detalhado")
    mes_ob = st.selectbox("Mês do Relatório:", MESES_NOMES, index=datetime.now().month-1, key="m_ob")
    df_p_ob = st.session_state.db[st.session_state.db['Data'].dt.month == MESES_MAP[mes_ob]]
    if not df_p_ob.empty:
        for sem in sorted(df_p_ob['Data'].unique(), reverse=True):
            st.write(f"#### 📅 Semana: {sem.strftime('%d/%m/%Y')}")
            dados_ob = []
            for lid in sorted(st.session_state.membros_cadastrados.keys()):
                f_p = df_p_ob[(df_p_ob['Data'] == sem) & (df_p_ob['Líder'] == lid)]
                f_v = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data'] == sem) & (st.session_state.db_visitantes['Líder'] == lid)]
                m_t = sum(1 for n, t in st.session_state.membros_cadastrados[lid].items() if t == "Membro")
                fa_t = sum(1 for n, t in st.session_state.membros_cadastrados[lid].items() if t == "FA")
                dados_ob.append({
                    "Líder": lid,
                    "Membros Cél/Cult": f"{int(f_p[f_p['Tipo']=='Membro']['Célula'].sum())}/{m_t} | {int(f_p[f_p['Tipo']=='Membro']['Culto'].sum())}/{m_t}",
                    "FA Cél/Cult": f"{int(f_p[f_p['Tipo']=='FA']['Célula'].sum())}/{fa_t} | {int(f_p[f_p['Tipo']=='FA']['Culto'].sum())}/{fa_t}",
                    "Vis. Cél/Cult": f"{int(f_v['Vis_Celula'].sum())} | {int(f_v['Vis_Culto'].sum())}"
                })
            st.table(pd.DataFrame(dados_ob))
