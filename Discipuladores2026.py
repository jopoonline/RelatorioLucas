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
    .metric-box { background: #1E293B; padding: 10px; border-radius: 10px; border-top: 4px solid #0284C7; text-align: center; }
    .metric-label { font-size: 11px; color: #94A3B8; text-transform: uppercase; }
    .metric-value { font-size: 18px; font-weight: 800; color: #38BDF8; }
    .alert-danger { background: #450a0a; padding: 10px; border-radius: 5px; border-left: 5px solid #ef4444; margin-bottom: 8px; font-size: 13px; color: #fecaca; }
</style>
""", unsafe_allow_html=True)

MESES_NOMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MESES_MAP = {n: i+1 for i, n in enumerate(MESES_NOMES)}

# --- 5. INTERFACE ---
st.markdown('<p class="main-title">🛡️ DISTRITO PRO 2026</p>', unsafe_allow_html=True)
tab_dash, tab_ob, tab_lanc, tab_gestao = st.tabs(["📊 DASHBOARDS", "📋 RELATÓRIO OB", "📝 LANÇAR", "⚙️ GESTÃO"])

with tab_dash:
    if st.session_state.db.empty:
        st.info("💡 Sem dados para exibir.")
    else:
        lids_atuais = sorted(list(st.session_state.membros_cadastrados.keys()))
        lids_f = st.multiselect("Filtrar Células:", lids_atuais, default=lids_atuais)
        
        # --- FILTROS DE DATA LADO A LADO ---
        col_m, col_s = st.columns(2)
        
        # Mês atual automático
        mes_atual_idx = datetime.now().month - 1
        mes_sel = col_m.selectbox("Selecione o Mês:", MESES_NOMES, index=mes_atual_idx)
        
        # Filtrar semanas que existem no banco de dados para o mês selecionado
        mes_num = MESES_MAP[mes_sel]
        df_mes_filtrado = st.session_state.db[st.session_state.db['Data'].dt.month == mes_num]
        
        if df_mes_filtrado.empty:
            st.warning(f"Sem dados registrados para o mês de {mes_sel}.")
            data_sel = None
        else:
            datas_disp = sorted(df_mes_filtrado['Data'].unique(), reverse=True)
            data_sel = col_s.selectbox("Selecione a Semana:", datas_disp, format_func=lambda x: x.strftime('%d/%m/%Y'))

        if data_sel:
            # --- PROCESSAMENTO DE DADOS ---
            df_sem = st.session_state.db[(st.session_state.db['Data'] == data_sel) & (st.session_state.db['Líder'].isin(lids_f))]
            df_v_sem = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data'] == data_sel) & (st.session_state.db_visitantes['Líder'].isin(lids_f))]

            def get_count_int(tipo):
                total = sum([1 for l in lids_f for n, t in st.session_state.membros_cadastrados.get(l, {}).items() if t == tipo])
                freq_cel = int(df_sem[df_sem['Tipo'] == tipo]['Célula'].sum())
                freq_cul = int(df_sem[df_sem['Tipo'] == tipo]['Culto'].sum())
                return f"{freq_cel}/{total}", f"{freq_cul}/{total}"

            m_cel, m_cul = get_count_int("Membro")
            fa_cel, fa_cul = get_count_int("FA")
            v_cel = int(df_v_sem['Vis_Celula'].sum())
            v_cul = int(df_v_sem['Vis_Culto'].sum())

            # --- MÉTRICAS ---
            st.write(f"### 📈 Resumo: Semana {data_sel.strftime('%d/%m')}")
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.markdown(f'<div class="metric-box"><p class="metric-label">Membros Célula</p><p class="metric-value">{m_cel}</p></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-box"><p class="metric-label">Membros Culto</p><p class="metric-value">{m_cul}</p></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-box"><p class="metric-label">FA Célula</p><p class="metric-value">{fa_cel}</p></div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="metric-box"><p class="metric-label">FA Culto</p><p class="metric-value">{fa_cul}</p></div>', unsafe_allow_html=True)
            c5.markdown(f'<div class="metric-box"><p class="metric-label">Visit. Célula</p><p class="metric-value">{v_cel}</p></div>', unsafe_allow_html=True)
            c6.markdown(f'<div class="metric-box"><p class="metric-label">Visit. Culto</p><p class="metric-value">{v_cul}</p></div>', unsafe_allow_html=True)

            # --- GRÁFICOS E ALERTAS ---
            col_graf, col_alert = st.columns([2, 1])
            with col_graf:
                st.write("#### Evolução Semanal (Frequência Bruta)")
                df_l_sem = df_sem.groupby('Líder')[['Célula', 'Culto']].sum().reset_index()
                fig_sem = go.Figure()
                fig_sem.add_trace(go.Scatter(x=df_l_sem['Líder'], y=df_l_sem['Célula'], name="Célula", mode='lines+markers+text', text=df_l_sem['Célula'], textposition="top center", line=dict(color='#38BDF8', width=3)))
                fig_sem.add_trace(go.Scatter(x=df_l_sem['Líder'], y=df_l_sem['Culto'], name="Culto", mode='lines+markers+text', text=df_l_sem['Culto'], textposition="top center", line=dict(color='#0284C7', width=3)))
                fig_sem.update_layout(template="plotly_dark", height=320, margin=dict(l=10,r=10,b=0,t=40))
                st.plotly_chart(fig_sem, use_container_width=True)
                
                st.write("#### Evolução Mensal")
                df_ev = st.session_state.db[st.session_state.db['Líder'].isin(lids_f)].groupby('Data')[['Célula', 'Culto']].sum().reset_index()
                fig_mes = px.line(df_ev, x='Data', y=['Célula', 'Culto'], markers=True, color_discrete_sequence=['#38BDF8', '#0284C7'])
                fig_mes.update_layout(template="plotly_dark", height=280)
                st.plotly_chart(fig_mes, use_container_width=True)

            with col_alert:
                st.write("#### 🚨 Alertas de Atenção")
                for lider in lids_f:
                    df_h = st.session_state.db[st.session_state.db['Líder'] == lider].sort_values('Data', ascending=False)
                    for m in df_h['Nome'].unique():
                        u = df_h[df_h['Nome'] == m].head(2)
                        if len(u) == 2 and u['Célula'].sum() == 0:
                            st.markdown(f'<div class="alert-danger">⚠️ {m} ({lider}): Faltou 2x na Célula</div>', unsafe_allow_html=True)
                for lider in lids_f:
                    df_v_h = st.session_state.db_visitantes[st.session_state.db_visitantes['Líder'] == lider].sort_values('Data', ascending=False).head(2)
                    if len(df_v_h) == 2 and df_v_h['Vis_Celula'].sum() == 0:
                        st.markdown(f'<div class="alert-danger">📉 {lider}: 0 Visitantes nas últimas 2 semanas</div>', unsafe_allow_html=True)

# --- OUTRAS ABAS (LANCAR, GESTAO, OB) MANTIDAS ---
with tab_ob:
    st.subheader("📋 Resumo Operacional")
    if not st.session_state.db.empty and 'data_sel' in locals() and data_sel:
        ob_res = []
        for l in lids_f:
            m_total = len(st.session_state.membros_cadastrados.get(l, {}))
            d_l = st.session_state.db[(st.session_state.db['Líder'] == l) & (st.session_state.db['Data'] == data_sel)]
            ob_res.append({"Célula": l, "Membros": m_total, "Pres. Célula": int(d_l['Célula'].sum()), "Pres. Culto": int(d_l['Culto'].sum())})
        st.table(pd.DataFrame(ob_res))

with tab_lanc:
    if not st.session_state.membros_cadastrados:
        st.warning("Cadastre líderes em GESTÃO.")
    else:
        ca, cb, cc = st.columns(3)
        def get_sabados_list(mes_nome, ano=2026):
            mes_int = MESES_MAP[mes_nome]
            d = date(ano, mes_int, 1)
            while d.weekday() != 5: d += timedelta(days=1)
            sats = []
            while d.month == mes_int: sats.append(pd.to_datetime(d)); d += timedelta(days=7)
            return sats

        m_l = ca.selectbox("Mês Lançamento", MESES_NOMES, index=datetime.now().month-1)
        d_l = cb.selectbox("Data", get_sabados_list(m_l), format_func=lambda x: x.strftime('%d/%m'))
        l_l = cc.selectbox("Líder", sorted(st.session_state.membros_cadastrados.keys()))
        
        st.write("### 👥 Visitantes")
        va, vb = st.columns(2)
        v_cel_in = va.number_input("Visitantes Célula", min_value=0, step=1)
        v_cul_in = vb.number_input("Visitantes Culto", min_value=0, step=1)
        
        st.write("### ✅ Chamada")
        mem = st.session_state.membros_cadastrados[l_l]
        novos = []
        for n, t in mem.items():
            c_n, c_e, c_u = st.columns([2,1,1])
            c_n.write(f"**{n}** ({t})")
            p_e = c_e.checkbox("Célula", key=f"e_{n}_{d_l}")
            p_u = c_u.checkbox("Culto", key=f"u_{n}_{d_l}")
            novos.append({"Data": d_l, "Líder": l_l, "Nome": n, "Tipo": t, "Célula": 1 if p_e else 0, "Culto": 1 if p_u else 0})
            
        if st.button("💾 SALVAR TUDO", use_container_width=True, type="primary"):
            df_p_new = pd.concat([st.session_state.db[~((st.session_state.db['Data']==d_l) & (st.session_state.db['Líder']==l_l))], pd.DataFrame(novos)])
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Presencas", data=df_p_new)
            df_v_new = pd.concat([st.session_state.db_visitantes[~((st.session_state.db_visitantes['Data']==d_l) & (st.session_state.db_visitantes['Líder']==l_l))], pd.DataFrame([{"Data": d_l, "Líder": l_l, "Vis_Celula": v_cel_in, "Vis_Culto": v_cul_in}])])
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Visitantes", data=df_v_new)
            st.cache_data.clear()
            st.success("Salvo!")
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
