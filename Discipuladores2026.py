import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAÇÃO E LIGAÇÃO COM GOOGLE SHEETS ---
st.set_page_config(page_title="Distrito Pro 2026", layout="wide", page_icon="🛡️")

# URL da sua planilha enviada
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1y3vAXagtbdzaTHGEkPOuWI3TvzcfFYhfO1JUt0GrhG8/edit?usp=sharing"

# Criando a conexão com o Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        # Tenta ler as abas da planilha DB_lucas_PRO
        df_p = conn.read(spreadsheet=URL_PLANILHA, worksheet="Presencas")
        df_v = conn.read(spreadsheet=URL_PLANILHA, worksheet="Visitantes")
        df_p['Data'] = pd.to_datetime(df_p['Data'])
        df_v['Data'] = pd.to_datetime(df_v['Data'])
        return df_p, df_v
    except:
        # Se as abas não existirem ainda, cria o esqueleto vazio
        df_p = pd.DataFrame(columns=["Data", "Líder", "Nome", "Tipo", "Célula", "Culto"])
        df_v = pd.DataFrame(columns=["Data", "Líder", "Vis_Celula", "Vis_Culto"])
        return df_p, df_v

# Inicialização dos dados (Busca no Google ao carregar/F5)
if 'db' not in st.session_state or 'db_visitantes' not in st.session_state:
    st.session_state.db, st.session_state.db_visitantes = carregar_dados()

if 'membros_cadastrados' not in st.session_state:
    st.session_state.membros_cadastrados = {}

# --- ESTILIZAÇÃO CSS (IGUAL AO ANTERIOR) ---
st.markdown("""
<style>
    .stApp { background-color: #0F172A; color: #F8FAFC; }
    .main-title {
        background: linear-gradient(90deg, #00D4FF 0%, #0072FF 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 900; font-size: 38px; text-align: center; margin-bottom: 20px;
    }
    .metric-card {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        padding: 15px; border-radius: 12px; border: 1px solid #334155;
        text-align: center; margin-bottom: 10px;
    }
    .metric-value-cel { color: #00D4FF; font-size: 24px; font-weight: 800; }
    .metric-value-cul { color: #EF4444; font-size: 24px; font-weight: 800; }
    .radar-card { background: rgba(239, 68, 68, 0.15); border-left: 5px solid #EF4444; padding: 15px; border-radius: 8px; margin-top: 10px; }
    .radar-card-vis { background: rgba(245, 158, 11, 0.15); border-left: 5px solid #F59E0B; padding: 15px; border-radius: 8px; margin-top: 10px; }
    .member-card { background: #1E293B; padding: 12px; border-radius: 15px; border: 1px solid #334155; margin-top: 15px; }
</style>
""", unsafe_allow_html=True)

# --- VARIÁVEIS DE APOIO ---
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

lideres_lista = sorted(list(st.session_state.membros_cadastrados.keys()))

# --- INTERFACE ---
st.markdown('<p class="main-title">🛡️ DISTRITO PRO 2026</p>', unsafe_allow_html=True)
lids_f = st.multiselect("Filtrar Células:", lideres_lista, default=lideres_lista)

tab_dash, tab_lanc, tab_ob, tab_gestao = st.tabs(["📊 DASHBOARD", "📝 LANÇAR", "📋 RELATÓRIO OB", "⚙️ GESTÃO"])

# --- ABA 1: DASHBOARD (COM EVOLUÇÃO MENSAL E SEMANAL) ---
with tab_dash:
    if st.session_state.db.empty:
        st.info("💡 Sem dados. Lance as chamadas na aba lateral para alimentar os gráficos.")
    else:
        c_m, c_s = st.columns(2)
        mes_dash = c_m.selectbox("📅 Mês de Referência:", MESES_NOMES, index=date.today().month - 1)
        mes_num = MESES_MAP[mes_dash]
        
        df_base = st.session_state.db[st.session_state.db['Líder'].isin(lids_f)]
        df_v_base = st.session_state.db_visitantes[st.session_state.db_visitantes['Líder'].isin(lids_f)]
        
        # 1. DASHBOARD SEMANAL
        st.write(f"### 📈 Evolução Semanal - {mes_dash}")
        df_mes = df_base[df_base['Data'].dt.month == mes_num]
        df_v_mes = df_v_base[df_v_base['Data'].dt.month == mes_num]

        if not df_mes.empty:
            datas_disp = sorted(df_mes['Data'].unique(), reverse=True)
            data_resumo = c_s.selectbox("🔎 Ver Semana:", datas_disp, format_func=lambda x: x.strftime('%d/%m/%Y'))
            
            df_u = df_mes[df_mes['Data'] == data_resumo]
            df_v_u = df_v_mes[df_v_mes['Data'] == data_resumo] if not df_v_mes.empty else pd.DataFrame()

            # Cartões de Resumo
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**🏠 Célula ({data_resumo.strftime('%d/%m')})**")
                c1, c2, c3 = st.columns(3)
                total_m_base = sum([list(st.session_state.membros_cadastrados[l].values()).count("Membro") for l in lids_f])
                c1.markdown(f'<div class="metric-card"><p style="font-size:11px">MEMBROS</p><p class="metric-value-cel">{int(df_u[df_u["Tipo"]=="Membro"]["Célula"].sum())}/{total_m_base}</p></div>', unsafe_allow_html=True)
                c2.markdown(f'<div class="metric-card"><p style="font-size:11px">FA</p><p class="metric-value-cel">{int(df_u[df_u["Tipo"]=="FA"]["Célula"].sum())}</p></div>', unsafe_allow_html=True)
                c3.markdown(f'<div class="metric-card"><p style="font-size:11px">VISIT.</p><p class="metric-value-cel">{int(df_v_u["Vis_Celula"].sum()) if not df_v_u.empty else 0}</p></div>', unsafe_allow_html=True)
            with col2:
                st.write(f"**⛪ Culto ({data_resumo.strftime('%d/%m')})**")
                c4, c5, c6 = st.columns(3)
                c4.markdown(f'<div class="metric-card"><p style="font-size:11px">MEMBROS</p><p class="metric-value-cul">{int(df_u[df_u["Tipo"]=="Membro"]["Culto"].sum())}</p></div>', unsafe_allow_html=True)
                c5.markdown(f'<div class="metric-card"><p style="font-size:11px">FA</p><p class="metric-value-cul">{int(df_u[df_u["Tipo"]=="FA"]["Culto"].sum())}</p></div>', unsafe_allow_html=True)
                c6.markdown(f'<div class="metric-card"><p style="font-size:11px">VISIT.</p><p class="metric-value-cul">{int(df_v_u["Vis_Culto"].sum()) if not df_v_u.empty else 0}</p></div>', unsafe_allow_html=True)

            # Gráfico Semanal
            df_s = df_mes.groupby('Data')[['Célula', 'Culto']].sum().reset_index()
            fig_s = go.Figure()
            fig_s.add_trace(go.Scatter(x=df_s['Data'], y=df_s['Célula'], name='Célula', line=dict(color='#00D4FF', width=3), mode='lines+markers'))
            fig_s.add_trace(go.Scatter(x=df_s['Data'], y=df_s['Culto'], name='Culto', line=dict(color='#EF4444', width=3), mode='lines+markers'))
            fig_s.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white", height=250)
            st.plotly_chart(fig_s, use_container_width=True)

        # 2. DASHBOARD MENSAL
        st.divider()
        st.write("### 📊 Evolução Mensal (Acumulado)")
        meses_comp = []
        for i in range(2, -1, -1):
            idx = (mes_num - 1 - i)
            if idx >= 0: meses_comp.append(idx + 1)
        
        df_tri = df_base[df_base['Data'].dt.month.isin(meses_comp)].copy()
        if not df_tri.empty:
            df_tri['Mês'] = df_tri['Data'].dt.month.map({v: k for k, v in MESES_MAP.items()})
            comp_m = df_tri.groupby('Mês')[['Célula', 'Culto']].sum().reset_index()
            fig_m = px.bar(comp_m, x='Mês', y=['Célula', 'Culto'], barmode='group', color_discrete_map={'Célula': '#00D4FF', 'Culto': '#EF4444'})
            fig_m.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white", height=300)
            st.plotly_chart(fig_m, use_container_width=True)

        # 3. RADARES
        st.divider()
        st.write("### 🚨 RADARES CRÍTICOS")
        d_u_global = sorted(df_base['Data'].unique())
        if len(d_u_global) >= 2:
            u2 = d_u_global[-2:]
            r1, r2 = st.columns(2)
            with r1:
                st.write("**Faltas de Membros (2 Semanas)**")
                df_r = df_base[df_base['Data'].isin(u2)]
                faltas = df_r.groupby(['Nome', 'Líder'])['Célula'].sum().reset_index()
                for _, row in faltas[faltas['Célula'] == 0].iterrows():
                    st.markdown(f'<div class="radar-card">🚩 <b>{row["Nome"]}</b> ({row["Líder"]})</div>', unsafe_allow_html=True)
            with r2:
                st.write("**Sem Visitantes (2 Semanas)**")
                df_rv = df_v_base[df_v_base['Data'].isin(u2)]
                vis_falta = df_rv.groupby('Líder')['Vis_Celula'].sum().reset_index()
                for _, row in vis_falta[vis_falta['Vis_Celula'] == 0].iterrows():
                    st.markdown(f'<div class="radar-card-vis">⚠️ Célula <b>{row["Líder"]}</b></div>', unsafe_allow_html=True)

# --- ABA 2: LANÇAR ---
with tab_lanc:
    if not lideres_lista: st.info("Cadastre células na aba GESTÃO.")
    else:
        la, lb, lc = st.columns(3)
        m_l = la.selectbox("Mês", MESES_NOMES, key="m_l")
        d_l = lb.selectbox("Sábado", get_sabados(m_l), format_func=lambda x: x.strftime('%d/%m'), key="d_l")
        l_l = lc.selectbox("Líder", lideres_lista, key="l_l")
        membros = st.session_state.membros_cadastrados.get(l_l, {})
        for n, t in membros.items():
            k_ce, k_cu = f"ce_{l_l}_{n}_{d_l}", f"cu_{l_l}_{n}_{d_l}"
            if k_ce not in st.session_state: st.session_state[k_ce] = False
            if k_cu not in st.session_state: st.session_state[k_cu] = False
            st.markdown(f'<div class="member-card"><b>{n}</b> ({t})</div>', unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            if b1.button(f"Célula: {'✅' if st.session_state[k_ce] else '❌'}", key=f"btn_ce_{n}_{d_l}"):
                st.session_state[k_ce] = not st.session_state[k_ce]; st.rerun()
            if b2.button(f"Culto: {'✅' if st.session_state[k_cu] else '❌'}", key=f"btn_cu_{n}_{d_l}"):
                st.session_state[k_cu] = not st.session_state[k_cu]; st.rerun()
        v1, v2 = st.columns(2)
        vi_ce = v1.number_input("Visitantes Célula", 0)
        vi_cu = v2.number_input("Visitantes Culto", 0)
        
        if st.button("💾 SALVAR E SINCRONIZAR COM GOOGLE", use_container_width=True, type="primary"):
            dt = pd.to_datetime(d_l)
            novos_p = pd.DataFrame([{"Data": dt, "Líder": l_l, "Nome": n, "Tipo": t, "Célula": 1 if st.session_state[f"ce_{l_l}_{n}_{d_l}"] else 0, "Culto": 1 if st.session_state[f"cu_{l_l}_{n}_{d_l}"] else 0} for n, t in membros.items()])
            novos_v = pd.DataFrame([{"Data": dt, "Líder": l_l, "Vis_Celula": vi_ce, "Vis_Culto": vi_cu}])
            
            # Atualizar Session e Google Sheets
            st.session_state.db = pd.concat([st.session_state.db[~((st.session_state.db['Data']==dt) & (st.session_state.db['Líder']==l_l))], novos_p], ignore_index=True)
            st.session_state.db_visitantes = pd.concat([st.session_state.db_visitantes[~((st.session_state.db_visitantes['Data']==dt) & (st.session_state.db_visitantes['Líder']==l_l))], novos_v], ignore_index=True)
            
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Presencas", data=st.session_state.db)
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Visitantes", data=st.session_state.db_visitantes)
            st.success("Dados salvos na planilha DB_lucas_PRO!"); st.balloons()

# --- ABAS OB E GESTÃO (IGUAIS AO ANTERIOR) ---
with tab_ob:
    if not st.session_state.db.empty:
        st.dataframe(st.session_state.db, use_container_width=True)

with tab_gestao:
    nova = st.text_input("Novo Líder")
    if st.button("Adicionar"):
        if nova: st.session_state.membros_cadastrados[nova] = {}; st.rerun()
    if lideres_lista:
        sel = st.selectbox("Editar Célula:", lideres_lista)
        nm = st.text_input("Nome Pessoa")
        tm = st.radio("Tipo", ["Membro", "FA"], horizontal=True)
        if st.button("Salvar Membro"):
            if nm: st.session_state.membros_cadastrados[sel][nm] = tm; st.rerun()
