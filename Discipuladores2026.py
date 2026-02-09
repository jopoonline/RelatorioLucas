import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Distrito Pro 2026", layout="wide", page_icon="🛡️")

# URL da sua planilha (Certifique-se de que o robô é EDITOR nela)
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1y3vAXagtbdzaTHGEkPOuWI3TvzcfFYhfO1JUt0GrhG8/edit?usp=sharing"

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. FUNÇÕES DE SINCRONIZAÇÃO (O SEGREDO DO F5) ---

def carregar_dados_nuvem():
    """Busca todas as informações do Google Sheets"""
    try:
        # ttl=0 força a leitura do dado mais recente
        df_p = conn.read(spreadsheet=URL_PLANILHA, worksheet="Presencas", ttl=0)
        df_v = conn.read(spreadsheet=URL_PLANILHA, worksheet="Visitantes", ttl=0)
        df_m = conn.read(spreadsheet=URL_PLANILHA, worksheet="Membros", ttl=0)
        
        # Converter datas
        if not df_p.empty: df_p['Data'] = pd.to_datetime(df_p['Data'])
        if not df_v.empty: df_v['Data'] = pd.to_datetime(df_v['Data'])
        
        # Converter aba Membros para o formato do App
        membros_dict = {}
        if not df_m.empty:
            for _, row in df_m.iterrows():
                l = row['Líder']
                if l not in membros_dict: membros_dict[l] = {}
                # Ignora placeholders de líderes vazios
                if row['Nome'] != "LIDER_INICIAL":
                    membros_dict[l][row['Nome']] = row['Tipo']
                elif l not in membros_dict:
                    membros_dict[l] = {}
                    
        return df_p, df_v, membros_dict
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame(), pd.DataFrame(), {}

def salvar_membros_nuvem():
    """Salva a estrutura de células e membros no Google"""
    lista = []
    for lider, pessoas in st.session_state.membros_cadastrados.items():
        if not pessoas:
            lista.append({"Líder": lider, "Nome": "LIDER_INICIAL", "Tipo": "Liderança"})
        else:
            for nome, tipo in pessoas.items():
                lista.append({"Líder": lider, "Nome": nome, "Tipo": tipo})
    
    df_m_save = pd.DataFrame(lista)
    conn.update(spreadsheet=URL_PLANILHA, worksheet="Membros", data=df_m_save)
    st.cache_data.clear()

# --- 3. INICIALIZAÇÃO ---
# Isso roda toda vez que o app inicia ou dá F5
db_p, db_v, m_dict = carregar_dados_nuvem()
st.session_state.db = db_p
st.session_state.db_visitantes = db_v
st.session_state.membros_cadastrados = m_dict

# --- 4. ESTILIZAÇÃO CSS ---
st.markdown("""
<style>
    .stApp { background-color: #0F172A; color: #F8FAFC; }
    .main-title { background: linear-gradient(90deg, #00D4FF 0%, #0072FF 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; font-size: 30px; text-align: center; }
    .card { background: #1E293B; padding: 15px; border-radius: 10px; border: 1px solid #334155; margin-bottom: 10px; }
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

# --- ABA DASHBOARD ---
with tab_dash:
    if st.session_state.db.empty:
        st.info("Aguardando dados da nuvem...")
    else:
        lideres_atuais = sorted(list(st.session_state.membros_cadastrados.keys()))
        lids_f = st.multiselect("Células:", lideres_atuais, default=lideres_atuais)
        
        df_f = st.session_state.db[st.session_state.db['Líder'].isin(lids_f)]
        if not df_f.empty:
            # Exemplo de gráfico de evolução
            df_ev = df_f.groupby('Data')[['Célula', 'Culto']].sum().reset_index()
            fig = px.line(df_ev, x='Data', y=['Célula', 'Culto'], title="Frequência Geral", markers=True)
            st.plotly_chart(fig, use_container_width=True)

# --- ABA LANÇAR ---
with tab_lanc:
    if not st.session_state.membros_cadastrados:
        st.warning("Cadastre líderes na aba GESTÃO.")
    else:
        c1, c2, c3 = st.columns(3)
        mes_sel = c1.selectbox("Mês", MESES_NOMES)
        data_sel = c2.selectbox("Sábado", get_sabados(mes_sel), format_func=lambda x: x.strftime('%d/%m'))
        lider_sel = c3.selectbox("Líder", sorted(st.session_state.membros_cadastrados.keys()))
        
        membros = st.session_state.membros_cadastrados[lider_sel]
        novos_registros = []
        
        for nome, tipo in membros.items():
            st.markdown(f'<div class="card"><b>{nome}</b> ({tipo})</div>', unsafe_allow_html=True)
            col_ce, col_cu = st.columns(2)
            pres_ce = col_ce.checkbox("Célula", key=f"ce_{nome}_{data_sel}")
            pres_cu = col_cu.checkbox("Culto", key=f"cu_{nome}_{data_sel}")
            novos_registros.append({"Data": data_sel, "Líder": lider_sel, "Nome": nome, "Tipo": tipo, "Célula": 1 if pres_ce else 0, "Culto": 1 if pres_cu else 0})
            
        if st.button("💾 SALVAR CHAMADA NO GOOGLE", use_container_width=True, type="primary"):
            df_novos = pd.DataFrame(novos_registros)
            # Remove dados antigos do mesmo dia/líder para não duplicar
            df_limpo = st.session_state.db[~((st.session_state.db['Data'] == data_sel) & (st.session_state.db['Líder'] == lider_sel))]
            st.session_state.db = pd.concat([df_limpo, df_novos], ignore_index=True)
            
            # Atualiza o Google Sheets
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Presencas", data=st.session_state.db)
            st.cache_data.clear()
            st.success("Chamada Sincronizada!")
            st.rerun()

# --- ABA GESTÃO ---
with tab_gestao:
    st.subheader("Células")
    n_lid = st.text_input("Nome do Líder da Célula:")
    if st.button("Criar Nova Célula"):
        if n_lid and n_lid not in st.session_state.membros_cadastrados:
            st.session_state.membros_cadastrados[n_lid] = {}
            salvar_membros_nuvem()
            st.success("Célula salva na nuvem!")
            st.rerun()

    st.divider()
    if st.session_state.membros_cadastrados:
        st.subheader("Membros")
        l_edit = st.selectbox("Adicionar em:", sorted(st.session_state.membros_cadastrados.keys()))
        n_mem = st.text_input("Nome do Membro:")
        t_mem = st.radio("Tipo", ["Membro", "FA"], horizontal=True)
        if st.button("Salvar Membro na Nuvem"):
            if n_mem:
                st.session_state.membros_cadastrados[l_edit][n_mem] = t_mem
                salvar_membros_nuvem()
                st.success(f"{n_mem} salvo com sucesso!")
                st.rerun()
