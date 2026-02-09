import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Distrito Pro 2026", layout="wide", page_icon="🛡️")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1y3vAXagtbdzaTHGEkPOuWI3TvzcfFYhfO1JUt0GrhG8/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. FUNÇÕES DE SINCRONIZAÇÃO COM CACHE (PARA EVITAR ERRO 429) ---

@st.cache_data(ttl=60)  # Só vai ao Google de verdade 1 vez por minuto
def buscar_dados_google():
    """Lê as informações da planilha com proteção de cota"""
    try:
        # Lendo as 3 abas
        df_p = conn.read(spreadsheet=URL_PLANILHA, worksheet="Presencas")
        df_v = conn.read(spreadsheet=URL_PLANILHA, worksheet="Visitantes")
        df_m = conn.read(spreadsheet=URL_PLANILHA, worksheet="Membros")
        
        # Ajuste de Datas
        if not df_p.empty: df_p['Data'] = pd.to_datetime(df_p['Data'])
        if not df_v.empty: df_v['Data'] = pd.to_datetime(df_v['Data'])
        
        # Formatando Membros para o dicionário do App
        m_dict = {}
        if not df_m.empty:
            for _, row in df_m.iterrows():
                l = row['Líder']
                if l not in m_dict: m_dict[l] = {}
                if row['Nome'] != "LIDER_INICIAL":
                    m_dict[l][row['Nome']] = row['Tipo']
        
        return df_p, df_v, m_dict
    except Exception as e:
        return None, None, None

def sincronizar_membros():
    """Salva líderes e membros na aba Membros"""
    lista = []
    for lid, pess in st.session_state.membros_cadastrados.items():
        if not pess:
            lista.append({"Líder": lid, "Nome": "LIDER_INICIAL", "Tipo": "Liderança"})
        else:
            for nome, tipo in pess.items():
                lista.append({"Líder": lid, "Nome": nome, "Tipo": tipo})
    
    df_m_save = pd.DataFrame(lista)
    conn.update(spreadsheet=URL_PLANILHA, worksheet="Membros", data=df_m_save)
    st.cache_data.clear() # Limpa o cache para a próxima leitura ser atualizada

# --- 3. INICIALIZAÇÃO DOS DADOS ---
# Tenta carregar os dados (usando o cache de 60s se disponível)
res_p, res_v, res_m = buscar_dados_google()

if res_p is not None:
    st.session_state.db = res_p
    st.session_state.db_visitantes = res_v
    st.session_state.membros_cadastrados = res_m
else:
    st.warning("⚠️ Limite do Google atingido. Aguarde 30 segundos para atualizar.")
    if 'db' not in st.session_state:
        st.session_state.db = pd.DataFrame()
        st.session_state.db_visitantes = pd.DataFrame()
        st.session_state.membros_cadastrados = {}

# --- 4. ESTILO E VARIÁVEIS ---
st.markdown("""
<style>
    .stApp { background-color: #0F172A; color: #F8FAFC; }
    .main-title { background: linear-gradient(90deg, #00D4FF 0%, #0072FF 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; font-size: 32px; text-align: center; }
    .card { background: #1E293B; padding: 15px; border-radius: 10px; border: 1px solid #334155; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

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

# --- 5. INTERFACE ---
st.markdown('<p class="main-title">🛡️ DISTRITO PRO 2026</p>', unsafe_allow_html=True)
tab_dash, tab_lanc, tab_gestao = st.tabs(["📊 DASHBOARD", "📝 LANÇAR", "⚙️ GESTÃO"])

# ABA DASHBOARD
with tab_dash:
    if st.session_state.db.empty:
        st.info("💡 Sem dados para exibir. Realize lançamentos ou aguarde a conexão.")
    else:
        lids_atuais = sorted(list(st.session_state.membros_cadastrados.keys()))
        lids_f = st.multiselect("Filtrar Células:", lids_atuais, default=lids_atuais)
        
        df_dash = st.session_state.db[st.session_state.db['Líder'].isin(lids_f)]
        if not df_dash.empty:
            df_ev = df_dash.groupby('Data')[['Célula', 'Culto']].sum().reset_index()
            fig = px.line(df_ev, x='Data', y=['Célula', 'Culto'], title="Evolução de Presenças", markers=True, color_discrete_sequence=["#00D4FF", "#EF4444"])
            st.plotly_chart(fig, use_container_width=True)

# ABA LANÇAR
with tab_lanc:
    if not st.session_state.membros_cadastrados:
        st.warning("Adicione líderes na aba GESTÃO.")
    else:
        c1, c2, c3 = st.columns(3)
        m_s = c1.selectbox("Mês", MESES_NOMES)
        d_s = c2.selectbox("Sábado", get_sabados(m_s), format_func=lambda x: x.strftime('%d/%m'))
        l_s = c3.selectbox("Líder", sorted(st.session_state.membros_cadastrados.keys()))
        
        membros = st.session_state.membros_cadastrados[l_s]
        novos_dados = []
        
        for n, t in membros.items():
            with st.container():
                st.markdown(f'<div class="card"><b>{n}</b> ({t})</div>', unsafe_allow_html=True)
                col_a, col_b = st.columns(2)
                p_cel = col_a.checkbox("Célula", key=f"c_{n}_{d_s}")
                p_cul = col_b.checkbox("Culto", key=f"u_{n}_{d_s}")
                novos_dados.append({"Data": d_s, "Líder": l_s, "Nome": n, "Tipo": t, "Célula": 1 if p_cel else 0, "Culto": 1 if p_cul else 0})
        
        if st.button("💾 SALVAR CHAMADA", use_container_width=True, type="primary"):
            df_novos = pd.DataFrame(novos_dados)
            # Remove duplicados do mesmo dia/líder antes de juntar
            df_clean = st.session_state.db[~((st.session_state.db['Data'] == d_s) & (st.session_state.db['Líder'] == l_s))]
            st.session_state.db = pd.concat([df_clean, df_novos], ignore_index=True)
            
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Presencas", data=st.session_state.db)
            st.cache_data.clear()
            st.success("Sincronizado!")
            st.rerun()

# ABA GESTÃO
with tab_gestao:
    st.write("### 🆕 Cadastrar Líder")
    novo_l = st.text_input("Nome do Líder")
    if st.button("Salvar Líder"):
        if novo_l and novo_l not in st.session_state.membros_cadastrados:
            st.session_state.membros_cadastrados[novo_l] = {}
            sincronizar_membros()
            st.success("Líder salvo!")
            st.rerun()

    st.divider()
    if st.session_state.membros_cadastrados:
        st.write("### 👥 Adicionar Membros")
        l_edit = st.selectbox("Na célula de:", sorted(st.session_state.membros_cadastrados.keys()))
        n_m = st.text_input("Nome do Membro")
        t_m = st.radio("Tipo", ["Membro", "FA"], horizontal=True)
        if st.button("Salvar Membro"):
            if n_m:
                st.session_state.membros_cadastrados[l_edit][n_m] = t_m
                sincronizar_membros()
                st.success("Membro salvo!")
                st.rerun()
