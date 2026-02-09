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
def buscar_dados_google():
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
        return None, None, None

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
res_p, res_v, res_m = buscar_dados_google()
if res_p is not None:
    st.session_state.db = res_p
    st.session_state.db_visitantes = res_v
    st.session_state.membros_cadastrados = res_m
else:
    if 'db' not in st.session_state:
        st.session_state.db = pd.DataFrame(columns=["Data", "Líder", "Nome", "Tipo", "Célula", "Culto"])
        st.session_state.db_visitantes = pd.DataFrame(columns=["Data", "Líder", "Vis_Celula", "Vis_Culto"])
        st.session_state.membros_cadastrados = {}

# --- 4. ESTILO ---
st.markdown("""
<style>
    .stApp { background-color: #0F172A; color: #F8FAFC; }
    .main-title { background: linear-gradient(90deg, #00D4FF 0%, #0072FF 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; font-size: 32px; text-align: center; }
    .metric-card { background: #1E293B; padding: 20px; border-radius: 12px; border-left: 5px solid #00D4FF; }
    .warning-card { background: #450a0a; padding: 10px; border-radius: 8px; border: 1px solid #ef4444; margin-bottom: 5px; }
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
    while d.month == mes_int:
        sats.append(pd.to_datetime(d)); d += timedelta(days=7)
    return sats

# --- 6. INTERFACE ---
st.markdown('<p class="main-title">🛡️ DISTRITO PRO 2026</p>', unsafe_allow_html=True)
tab_dash, tab_lanc, tab_gestao = st.tabs(["📊 DASHBOARD", "📝 LANÇAR", "⚙️ GESTÃO"])

with tab_dash:
    if st.session_state.db.empty:
        st.info("💡 Sem dados para análise.")
    else:
        # Filtros de Dashboard
        lids_atuais = sorted(list(st.session_state.membros_cadastrados.keys()))
        lids_f = st.multiselect("Células:", lids_atuais, default=lids_atuais)
        
        # --- ALERTAS INTELIGENTES ---
        st.subheader("⚠️ Alertas de Atenção")
        col_a1, col_a2 = st.columns(2)
        
        with col_a1:
            st.write("**Faltas Consecutivas (2x Célula)**")
            for lider in lids_f:
                df_l = st.session_state.db[st.session_state.db['Líder'] == lider].sort_values('Data', ascending=False)
                membros_l = df_l['Nome'].unique()
                for m in membros_l:
                    ultimas_2 = df_l[df_l['Nome'] == m].head(2)
                    if len(ultimas_2) == 2 and ultimas_2['Célula'].sum() == 0:
                        st.markdown(f'<div class="warning-card">🚨 {m} ({lider}) faltou as últimas 2 células!</div>', unsafe_allow_html=True)

        with col_a2:
            st.write("**Alerta de Evangelismo (Visitantes)**")
            for lider in lids_f:
                df_v_l = st.session_state.db_visitantes[st.session_state.db_visitantes['Líder'] == lider].sort_values('Data', ascending=False)
                if not df_v_l.empty:
                    ultimas_2_v = df_v_l.head(2)
                    if ultimas_2_v['Vis_Celula'].sum() == 0:
                        st.markdown(f'<div class="warning-card">📉 Célula {lider}: 0 visitantes nas últimas 2 semanas.</div>', unsafe_allow_html=True)

        st.divider()

        # --- GRÁFICOS ---
        df_dash = st.session_state.db[st.session_state.db['Líder'].isin(lids_f)]
        if not df_dash.empty:
            st.subheader("📊 Evolução Mensal")
            df_ev = df_dash.groupby('Data')[['Célula', 'Culto']].sum().reset_index()
            fig = px.area(df_ev, x='Data', y=['Célula', 'Culto'], 
                          title="Crescimento de Frequência", 
                          color_discrete_sequence=["#00D4FF", "#EF4444"],
                          template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

with tab_lanc:
    if not st.session_state.membros_cadastrados:
        st.warning("Adicione líderes na aba GESTÃO.")
    else:
        c1, c2, c3 = st.columns(3)
        m_s = c1.selectbox("Mês", MESES_NOMES)
        d_s = c2.selectbox("Sábado", get_sabados(m_s), format_func=lambda x: x.strftime('%d/%m'))
        l_s = c3.selectbox("Líder", sorted(st.session_state.membros_cadastrados.keys()))
        
        # Lançamento de Visitantes
        st.write("### 👥 Visitantes")
        va, vb = st.columns(2)
        v_cel = va.number_input("Visitantes na Célula", min_value=0, step=1, key="v_cel_in")
        v_cul = vb.number_input("Visitantes no Culto", min_value=0, step=1, key="v_cul_in")
        
        st.divider()
        st.write("### ✅ Chamada de Membros")
        membros = st.session_state.membros_cadastrados[l_s]
        novos_dados = []
        
        for n, t in membros.items():
            with st.container():
                col_n, col_ce, col_cu = st.columns([2,1,1])
                col_n.write(f"**{n}** ({t})")
                p_cel = col_ce.checkbox("Célula", key=f"c_{n}_{d_s}")
                p_cul = col_cu.checkbox("Culto", key=f"u_{n}_{d_s}")
                novos_dados.append({"Data": d_s, "Líder": l_s, "Nome": n, "Tipo": t, "Célula": 1 if p_cel else 0, "Culto": 1 if p_cul else 0})
        
        if st.button("💾 FINALIZAR E ENVIAR PARA NUVEM", use_container_width=True, type="primary"):
            # 1. Salvar Presenças
            df_novos = pd.DataFrame(novos_dados)
            df_clean = st.session_state.db[~((st.session_state.db['Data'] == d_s) & (st.session_state.db['Líder'] == l_s))]
            st.session_state.db = pd.concat([df_clean, df_novos], ignore_index=True)
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Presencas", data=st.session_state.db)
            
            # 2. Salvar Visitantes
            df_v_novo = pd.DataFrame([{"Data": d_s, "Líder": l_s, "Vis_Celula": v_cel, "Vis_Culto": v_cul}])
            df_v_clean = st.session_state.db_visitantes[~((st.session_state.db_visitantes['Data'] == d_s) & (st.session_state.db_visitantes['Líder'] == l_s))]
            st.session_state.db_visitantes = pd.concat([df_v_clean, df_v_novo], ignore_index=True)
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Visitantes", data=st.session_state.db_visitantes)
            
            st.cache_data.clear()
            st.success("Dados Sincronizados com Sucesso!")
            st.rerun()

with tab_gestao:
    # ... (Mesma lógica de criação de líder e membro do código anterior)
    st.write("### ⚙️ Gestão de Células")
    novo_l = st.text_input("Nome do Novo Líder")
    if st.button("Salvar Líder"):
        if novo_l:
            st.session_state.membros_cadastrados[novo_l] = {}
            sincronizar_membros()
            st.rerun()

    st.divider()
    if st.session_state.membros_cadastrados:
        l_edit = st.selectbox("Adicionar Membro em:", sorted(st.session_state.membros_cadastrados.keys()))
        n_m = st.text_input("Nome")
        t_m = st.radio("Tipo", ["Membro", "FA"], horizontal=True)
        if st.button("Salvar Membro"):
            st.session_state.membros_cadastrados[l_edit][n_m] = t_m
            sincronizar_membros()
            st.rerun()
