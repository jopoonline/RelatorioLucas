import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta, datetime
from streamlit_gsheets import GSheetsConnection
import time

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Distrito Pro 2026", layout="wide", page_icon="🛡️")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1y3vAXagtbdzaTHGEkPOuWI3TvzcfFYhfO1JUt0GrhG8/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. FUNÇÕES DE DADOS (LIMPEZA RADICAL) ---
@st.cache_data(ttl=2) 
def carregar_dados():
    try:
        df_p = conn.read(spreadsheet=URL_PLANILHA, worksheet="Presencas")
        df_v = conn.read(spreadsheet=URL_PLANILHA, worksheet="Visitantes")
        df_m = conn.read(spreadsheet=URL_PLANILHA, worksheet="Membros")
        
        # Garante que as colunas existam
        if df_p is None or df_p.empty: df_p = pd.DataFrame(columns=['Data', 'Líder', 'Nome', 'Tipo', 'Célula', 'Culto'])
        if df_v is None or df_v.empty: df_v = pd.DataFrame(columns=['Data', 'Líder', 'Vis_Celula', 'Vis_Culto'])

        # CONVERSÃO RADICAL: Transforma tudo em data, limpa hora e depois vira string para comparar sem erro
        df_p['Data_Ref'] = pd.to_datetime(df_p['Data'], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
        df_v['Data_Ref'] = pd.to_datetime(df_v['Data'], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
        
        # Dropa erros de data
        df_p = df_p.dropna(subset=['Data_Ref'])
        df_v = df_v.dropna(subset=['Data_Ref'])

        for col in ['Célula', 'Culto']: df_p[col] = pd.to_numeric(df_p[col], errors='coerce').fillna(0).astype(int)
        for col in ['Vis_Celula', 'Vis_Culto']: df_v[col] = pd.to_numeric(df_v[col], errors='coerce').fillna(0).astype(int)

        m_dict = {}
        if df_m is not None and not df_m.empty:
            for _, row in df_m.iterrows():
                l = row.get('Líder')
                if l and l not in m_dict: m_dict[l] = {}
                if l and row.get('Nome') != "LIDER_INICIAL": m_dict[l][row['Nome']] = row.get('Tipo', 'Membro')
        return df_p, df_v, m_dict
    except Exception as e:
        st.error(f"Erro ao carregar: {e}")
        return pd.DataFrame(), pd.DataFrame(), {}

# --- 3. INICIALIZAÇÃO ---
db_p, db_v, m_dict = carregar_dados()
st.session_state.db = db_p
st.session_state.db_visitantes = db_v
st.session_state.membros_cadastrados = m_dict

# --- 4. ESTILO ---
st.markdown("<style>.stApp { background-color: #0F172A; color: #F8FAFC; } .metric-box { background: #1E293B; padding: 15px; border-radius: 10px; border-top: 4px solid #0284C7; text-align: center; } .metric-value { font-size: 24px; font-weight: 800; color: #38BDF8; }</style>", unsafe_allow_html=True)

MESES_NOMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MESES_MAP = {n: f"{i+1:02d}" for i, n in enumerate(MESES_NOMES)} # Ex: "02" para Fevereiro

st.title("🛡️ DISTRITO PRO 2026")
tab_dash, tab_lanc, tab_gestao, tab_ob = st.tabs(["📊 DASHBOARDS", "📝 LANÇAR", "⚙️ GESTÃO", "📋 RELATÓRIO OB"])

# --- TAB DASHBOARDS ---
with tab_dash:
    if st.button("🔄 Forçar Sincronização"):
        st.cache_data.clear()
        st.rerun()

    if st.session_state.db.empty:
        st.info("💡 Planilha vazia ou datas inválidas.")
    else:
        lids_atuais = sorted(list(st.session_state.membros_cadastrados.keys()))
        lids_f = st.multiselect("Filtrar Células:", lids_atuais, default=lids_atuais)
        
        col_m, col_s = st.columns(2)
        mes_sel_nome = col_m.selectbox("Mês:", MESES_NOMES, index=datetime.now().month - 1)
        mes_prefixo = f"2026-{MESES_MAP[mes_sel_nome]}" # Ex: "2026-02"

        # Filtra todas as linhas que começam com o ano-mês selecionado
        df_mes_f = st.session_state.db[st.session_state.db['Data_Ref'].str.startswith(mes_prefixo)]
        
        if df_mes_f.empty:
            st.warning(f"Nenhum dado encontrado para {mes_sel_nome}.")
            st.write("Datas lidas na planilha:", st.session_state.db['Data_Ref'].unique()) # Ajuda a ver o que está errado
        else:
            # Pega as semanas disponíveis no mês
            datas_disp = sorted(df_mes_f['Data_Ref'].unique(), reverse=True)
            data_escolhida = col_s.selectbox("Semana Selecionada:", datas_disp, format_func=lambda x: datetime.strptime(x, '%Y-%m-%d').strftime('%d/%m/%Y'))

            # Filtros finais para os cards
            df_sem = df_mes_f[(df_mes_f['Data_Ref'] == data_escolhida) & (df_mes_f['Líder'].isin(lids_f))]
            df_v_sem = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data_Ref'] == data_escolhida) & (st.session_state.db_visitantes['Líder'].isin(lids_f))]

            def get_card(tipo, modo='Célula'):
                if tipo == "Membro":
                    total = sum([1 for l in lids_f for n, t in st.session_state.membros_cadastrados.get(l, {}).items() if t == "Membro"]) + len(lids_f)
                    val = int(df_sem[df_sem['Tipo'].isin(['Membro', 'Liderança'])][modo].sum())
                    return f"{val}/{total}"
                elif tipo == "Visitante":
                    val = int(df_v_sem['Vis_Celula' if modo == 'Célula' else 'Vis_Culto'].sum())
                    return f"{val}"
                else: # FA
                    total = sum([1 for l in lids_f for n, t in st.session_state.membros_cadastrados.get(l, {}).items() if t == "FA"])
                    val = int(df_sem[df_sem['Tipo'] == "FA"][modo].sum())
                    return f"{val}/{total}"

            # Layout de Cards
            c1, c2, c3 = st.columns(3)
            c1.markdown(f'<div class="metric-box">Membros Célula<br><span class="metric-value">{get_card("Membro", "Célula")}</span></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-box">FA Célula<br><span class="metric-value">{get_card("FA", "Célula")}</span></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-box">Visitantes Célula<br><span class="metric-value">{get_card("Visitante", "Célula")}</span></div>', unsafe_allow_html=True)
            
            st.write("---")
            
            # Gráficos com números (Rótulos)
            col_g1, col_g2 = st.columns(2)
            
            # Gráfico Célula
            df_g1 = df_mes_f[df_mes_f['Líder'].isin(lids_f)].groupby('Data_Ref')['Célula'].sum().reset_index()
            fig1 = px.line(df_g1, x='Data_Ref', y='Célula', title="Evolução Célula", markers=True, text='Célula')
            fig1.update_traces(textposition="top center")
            col_g1.plotly_chart(fig1, use_container_width=True)

            # Gráfico Culto
            df_g2 = df_mes_f[df_mes_f['Líder'].isin(lids_f)].groupby('Data_Ref')['Culto'].sum().reset_index()
            fig2 = px.line(df_g2, x='Data_Ref', y='Culto', title="Evolução Culto", markers=True, text='Culto')
            fig2.update_traces(textposition="top center")
            col_g2.plotly_chart(fig2, use_container_width=True)

            st.write("---")
            st.write("### 📊 Comparativo Mensal (Média)")
            # Pega o mês atual e os 2 anteriores para comparar
            mes_num_int = int(MESES_MAP[mes_sel_nome])
            meses_alvo = [f"2026-{m:02d}" for m in range(max(1, mes_num_int-2), mes_num_int + 1)]
            
            df_comp = st.session_state.db[st.session_state.db['Data_Ref'].str[:7].isin(meses_alvo)].copy()
            df_comp['Mes'] = df_comp['Data_Ref'].str[5:7]
            
            resumo = []
            for m in meses_alvo:
                m_str = m.split('-')[1]
                nome_m = [k for k, v in MESES_MAP.items() if v == m_str][0]
                temp = df_comp[df_comp['Mes'] == m_str]
                sabs = len(temp['Data_Ref'].unique()) if not temp.empty else 1
                resumo.append({"Mês": nome_m, "Média Célula": round(temp['Célula'].sum()/sabs, 1)})
            
            st.plotly_chart(px.bar(pd.DataFrame(resumo), x='Mês', y='Média Célula', text_auto=True), use_container_width=True)

# As abas LANÇAR, GESTÃO e RELATÓRIO permanecem iguais (omitidas aqui para brevidade, use as do código anterior)
