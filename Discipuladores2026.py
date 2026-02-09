import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Distrito Pro 2026", layout="wide", page_icon="🛡️")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1y3vAXagtbdzaTHGEkPOuWI3TvzcfFYhfO1JUt0GrhG8/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CARREGAMENTO DE DADOS COM CACHE ---
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

# Inicialização
db_p, db_v, m_dict = carregar_dados()
st.session_state.db = db_p
st.session_state.db_visitantes = db_v
st.session_state.membros_cadastrados = m_dict

# --- ESTILIZAÇÃO ---
st.markdown("""
<style>
    .stApp { background-color: #0F172A; color: #F8FAFC; }
    .main-title { background: linear-gradient(90deg, #00D4FF 0%, #0072FF 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; font-size: 32px; text-align: center; }
    .metric-container { background: #1E293B; padding: 15px; border-radius: 12px; border: 1px solid #334155; text-align: center; }
    .label { color: #94A3B8; font-size: 14px; }
    .value { font-size: 24px; font-weight: 800; color: #00D4FF; }
    .warning-card { background: #450a0a; padding: 10px; border-radius: 8px; margin-bottom: 5px; border: 1px solid #ef4444; }
</style>
""", unsafe_allow_html=True)

# --- LOGICA DE DATAS ---
MESES_NOMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MESES_MAP = {n: i+1 for i, n in enumerate(MESES_NOMES)}
def get_sabados(mes_nome, ano=2026):
    mes_int = MESES_MAP[mes_nome]
    d = date(ano, mes_int, 1)
    while d.weekday() != 5: d += timedelta(days=1)
    sats = []
    while d.month == mes_int: sats.append(pd.to_datetime(d)); d += timedelta(days=7)
    return sats

# --- INTERFACE ---
st.markdown('<p class="main-title">🛡️ DISTRITO PRO 2026</p>', unsafe_allow_html=True)
tab_dash, tab_lanc, tab_gestao = st.tabs(["📊 DASHBOARD", "📝 LANÇAR", "⚙️ GESTÃO"])

# --- DASHBOARD ---
with tab_dash:
    if st.session_state.db.empty:
        st.info("💡 Sem dados para exibir.")
    else:
        lids_atuais = sorted(list(st.session_state.membros_cadastrados.keys()))
        lids_f = st.multiselect("Células Selecionadas:", lids_atuais, default=lids_atuais)
        
        # Filtro de Data para o Dash Semanal
        datas_disponiveis = sorted(st.session_state.db['Data'].unique(), reverse=True)
        data_sel = st.selectbox("📅 Selecione a Semana para Raio-X:", datas_disponiveis, format_func=lambda x: pd.to_datetime(x).strftime('%d/%m/%Y'))

        # Lógica de Métricas da Semana Selecionada
        df_sem = st.session_state.db[(st.session_state.db['Data'] == data_sel) & (st.session_state.db['Líder'].isin(lids_f))]
        df_v_sem = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data'] == data_sel) & (st.session_state.db_visitantes['Líder'].isin(lids_f))]
        
        # Cálculos Semanais
        total_membros_ativos = sum([len(st.session_state.membros_cadastrados[l]) for l in lids_f if l in st.session_state.membros_cadastrados])
        presenca_cel = df_sem['Célula'].sum()
        presenca_cul = df_sem['Culto'].sum()
        vis_total = df_v_sem['Vis_Celula'].sum() + df_v_sem['Vis_Culto'].sum()

        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f'<div class="metric-container"><p class="label">Membros Ativos</p><p class="value">{total_membros_ativos}</p></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="metric-container"><p class="label">Presença Célula</p><p class="value" style="color:#22C55E">{presenca_cel} / {total_membros_ativos}</p></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="metric-container"><p class="label">Presença Culto</p><p class="value" style="color:#EF4444">{presenca_cul} / {total_membros_ativos}</p></div>', unsafe_allow_html=True)
        with c4: st.markdown(f'<div class="metric-container"><p class="label">Visitantes</p><p class="value" style="color:#EAB308">{vis_total}</p></div>', unsafe_allow_html=True)

        # Gráfico Semanal por Célula
        st.write("### 📈 Performance por Célula na Semana")
        df_lider_sem = df_sem.groupby('Líder')[['Célula', 'Culto']].sum().reset_index()
        fig_sem = px.bar(df_lider_sem, x='Líder', y=['Célula', 'Culto'], barmode='group', 
                         color_discrete_sequence=["#22C55E", "#EF4444"], template="plotly_dark")
        st.plotly_chart(fig_sem, use_container_width=True)

        # ALERTAS (Faltas 2x e Visitantes 0)
        st.subheader("⚠️ Alertas de Cuidado")
        # [Mesma lógica de alertas anterior...]
        for lider in lids_f:
             df_l = st.session_state.db[st.session_state.db['Líder'] == lider].sort_values('Data', ascending=False)
             for m in df_l['Nome'].unique():
                 ultimas = df_l[df_l['Nome'] == m].head(2)
                 if len(ultimas) == 2 and ultimas['Célula'].sum() == 0:
                     st.markdown(f'<div class="warning-card">🚨 {m} ({lider}) faltou as últimas 2 células!</div>', unsafe_allow_html=True)

# --- LANÇAMENTO ---
with tab_lanc:
    if not st.session_state.membros_cadastrados:
        st.warning("Cadastre líderes em GESTÃO.")
    else:
        ca, cb, cc = st.columns(3)
        m_s = ca.selectbox("Mês", MESES_NOMES)
        d_s = cb.selectbox("Data", get_sabados(m_s), format_func=lambda x: x.strftime('%d/%m'))
        l_s = cc.selectbox("Líder", sorted(st.session_state.membros_cadastrados.keys()))
        
        st.write("### 👥 Visitantes")
        va, vb = st.columns(2)
        v_cel = va.number_input("Visitantes Célula", min_value=0)
        v_cul = vb.number_input("Visitantes Culto", min_value=0)
        
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
            # Salva Presenças
            df_new = pd.DataFrame(novos)
            df_cl = st.session_state.db[~((st.session_state.db['Data']==d_s) & (st.session_state.db['Líder']==l_s))]
            st.session_state.db = pd.concat([df_cl, df_new])
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Presencas", data=st.session_state.db)
            # Salva Visitantes
            df_v_new = pd.DataFrame([{"Data": d_s, "Líder": l_s, "Vis_Celula": v_cel, "Vis_Culto": v_cul}])
            df_vc = st.session_state.db_visitantes[~((st.session_state.db_visitantes['Data']==d_s) & (st.session_state.db_visitantes['Líder']==l_s))]
            st.session_state.db_visitantes = pd.concat([df_vc, df_v_new])
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Visitantes", data=st.session_state.db_visitantes)
            st.cache_data.clear()
            st.success("Salvo!")
            st.rerun()

with tab_gestao:
    # Lógica de Gestão mantida para salvar na aba 'Membros'
    st.write("### Configuração")
    # ... [Mesmo código de gestão que envia para a aba Membros]
