import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="Distrito Pro 2026", layout="wide", page_icon="🛡️")

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
    .member-card {
        background: #1E293B; padding: 12px; border-radius: 15px;
        border: 1px solid #334155; margin-top: 15px;
    }
    .radar-card { 
        background: rgba(239, 68, 68, 0.15); border-left: 5px solid #EF4444; 
        padding: 15px; border-radius: 8px; margin-top: 10px;
    }
    .radar-card-vis { 
        background: rgba(245, 158, 11, 0.15); border-left: 5px solid #F59E0B; 
        padding: 15px; border-radius: 8px; margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. INICIALIZAÇÃO DE DADOS ---
if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=["Data", "Líder", "Nome", "Tipo", "Célula", "Culto"])
if 'db_visitantes' not in st.session_state:
    st.session_state.db_visitantes = pd.DataFrame(columns=["Data", "Líder", "Vis_Celula", "Vis_Culto"])
if 'membros_cadastrados' not in st.session_state:
    st.session_state.membros_cadastrados = {}

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

# --- 3. INTERFACE ---
st.markdown('<p class="main-title">🛡️ DISTRITO PRO 2026</p>', unsafe_allow_html=True)
lids_f = st.multiselect("Filtrar Células:", lideres_lista, default=lideres_lista)

tab_dash, tab_lanc, tab_ob, tab_gestao = st.tabs(["📊 DASHBOARD", "📝 LANÇAR", "📋 RELATÓRIO OB", "⚙️ GESTÃO"])

# --- ABA 1: DASHBOARD ---
with tab_dash:
    if st.session_state.db.empty:
        st.info("💡 Sem dados lançados. Inicie os registros na aba 'LANÇAR'.")
    elif not lids_f:
        st.warning("Selecione uma célula.")
    else:
        # Seletores Superiores
        c_m, c_s = st.columns(2)
        mes_dash = c_m.selectbox("📅 Mês de Referência:", MESES_NOMES, index=date.today().month - 1)
        mes_num = MESES_MAP[mes_dash]
        
        # Filtros de Base
        df_base = st.session_state.db[st.session_state.db['Líder'].isin(lids_f)]
        df_v_base = st.session_state.db_visitantes[st.session_state.db_visitantes['Líder'].isin(lids_f)]
        
        # 1. DASHBOARD SEMANAL
        st.markdown("---")
        st.write(f"### 📈 Evolução Semanal - {mes_dash}")
        
        df_mes = df_base[df_base['Data'].dt.month == mes_num]
        df_v_mes = df_v_base[df_v_base['Data'].dt.month == mes_num]

        if not df_mes.empty:
            datas_disp = sorted(df_mes['Data'].unique(), reverse=True)
            data_resumo = c_s.selectbox("🔎 Ver Semana:", datas_disp, format_func=lambda x: x.strftime('%d/%m/%Y'))
            
            df_u = df_mes[df_mes['Data'] == data_resumo]
            df_v_u = df_v_mes[df_v_mes['Data'] == data_resumo] if not df_v_mes.empty else pd.DataFrame()

            # Resumo da Semana Selecionada
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

            # Gráfico de Linhas do Mês
            df_s = df_mes.groupby('Data')[['Célula', 'Culto']].sum().reset_index()
            fig_s = go.Figure()
            fig_s.add_trace(go.Scatter(x=df_s['Data'], y=df_s['Célula'], name='Célula', line=dict(color='#00D4FF', width=3), mode='lines+markers'))
            fig_s.add_trace(go.Scatter(x=df_s['Data'], y=df_s['Culto'], name='Culto', line=dict(color='#EF4444', width=3), mode='lines+markers'))
            fig_s.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white", height=250, xaxis=dict(tickformat="%d/%m"))
            st.plotly_chart(fig_s, use_container_width=True)
        else:
            st.warning(f"Sem registros semanais para {mes_dash}.")

        # 2. DASHBOARD MENSAL (COMPARATIVO)
        st.markdown("---")
        st.write("### 📊 Evolução Mensal (Comparativo Trimestral)")
        
        # Lógica para pegar o mês selecionado + 2 anteriores
        meses_comp = []
        for i in range(2, -1, -1):
            idx = (mes_num - 1 - i)
            if idx >= 0: meses_comp.append(idx + 1)
        
        df_tri = df_base[df_base['Data'].dt.month.isin(meses_comp)].copy()
        
        if not df_tri.empty:
            df_tri['Mês'] = df_tri['Data'].dt.month.map({v: k for k, v in MESES_MAP.items()})
            # Soma de Membros + FA + Visitantes (Célula e Culto) por Mês
            # Precisamos somar visitantes também
            df_v_tri = df_v_base[df_v_base['Data'].dt.month.isin(meses_comp)].copy()
            df_v_tri['Mês'] = df_v_tri['Data'].dt.month.map({v: k for k, v in MESES_MAP.items()})
            
            mensal_membros = df_tri.groupby('Mês')[['Célula', 'Culto']].sum()
            mensal_vis = df_v_tri.groupby('Mês')[['Vis_Celula', 'Vis_Culto']].sum()
            
            # Unir totais
            df_mensal = mensal_membros.join(mensal_vis).reset_index()
            df_mensal['Total Célula'] = df_mensal['Célula'] + df_mensal['Vis_Celula']
            df_mensal['Total Culto'] = df_mensal['Culto'] + df_mensal['Vis_Culto']
            
            # Ordenar os meses
            df_mensal['Mês'] = pd.Categorical(df_mensal['Mês'], categories=MESES_NOMES, ordered=True)
            df_mensal = df_mensal.sort_values('Mês')

            fig_m = px.bar(df_mensal, x='Mês', y=['Total Célula', 'Total Culto'], 
                           barmode='group', color_discrete_map={'Total Célula': '#00D4FF', 'Total Culto': '#EF4444'})
            fig_m.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white", height=300)
            st.plotly_chart(fig_m, use_container_width=True)
        else:
            st.info("Lance dados de meses diferentes para ver a comparação mensal.")

        # 3. RADARES
        st.markdown("---")
        st.write("### 🚨 RADARES DE ALERTA")
        d_u_global = sorted(df_base['Data'].unique())
        if len(d_u_global) >= 2:
            u2 = d_u_global[-2:]
            r1, r2 = st.columns(2)
            with r1:
                st.write("**Membros/FA (2 Faltas Seguidas)**")
                df_r = df_base[df_base['Data'].isin(u2)]
                faltas = df_r.groupby(['Nome', 'Líder'])['Célula'].sum().reset_index()
                list_f = faltas[faltas['Célula'] == 0]
                for _, row in list_f.iterrows():
                    st.markdown(f'<div class="radar-card">🚩 <b>{row["Nome"]}</b> ({row["Líder"]})</div>', unsafe_allow_html=True)
            with r2:
                st.write("**Células (2 Semanas Sem Visitantes)**")
                df_rv = df_v_base[df_v_base['Data'].isin(u2)]
                fals_v = df_rv.groupby('Líder')['Vis_Celula'].sum().reset_index()
                list_vv = fals_v[fals_v['Vis_Celula'] == 0]
                for _, row in list_vv.iterrows():
                    st.markdown(f'<div class="radar-card-vis">⚠️ Célula <b>{row["Líder"]}</b></div>', unsafe_allow_html=True)

# --- ABAS LANÇAR, OB E GESTÃO (Mantidas Conforme Anterior) ---
with tab_lanc:
    st.subheader("📝 Chamada Mobile")
    if not lideres_lista: st.info("Cadastre células na aba GESTÃO.")
    else:
        la, lb, lc = st.columns(3)
        m_s = la.selectbox("Mês", MESES_NOMES, key="m_lanc")
        d_s = lb.selectbox("Sábado", get_sabados(m_s), format_func=lambda x: x.strftime('%d/%m'), key="d_lanc")
        l_s = lc.selectbox("Líder", lideres_lista, key="l_lanc")
        membros = st.session_state.membros_cadastrados.get(l_s, {})
        for n, t in membros.items():
            k_ce, k_cu = f"ce_{l_s}_{n}_{d_s}", f"cu_{l_s}_{n}_{d_s}"
            if k_ce not in st.session_state: st.session_state[k_ce] = False
            if k_cu not in st.session_state: st.session_state[k_cu] = False
            st.markdown(f'<div class="member-card"><b>{n}</b> ({t})</div>', unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            if b1.button(f"Célula: {'✅' if st.session_state[k_ce] else '❌'}", key=f"bce_{n}_{d_s}", use_container_width=True):
                st.session_state[k_ce] = not st.session_state[k_ce]; st.rerun()
            if b2.button(f"Culto: {'✅' if st.session_state[k_cu] else '❌'}", key=f"bcu_{n}_{d_s}", use_container_width=True):
                st.session_state[k_cu] = not st.session_state[k_cu]; st.rerun()
        v1, v2 = st.columns(2)
        vi_ce = v1.number_input("Visitantes Célula", 0)
        vi_cu = v2.number_input("Visitantes Culto", 0)
        if st.button("💾 SALVAR DADOS", use_container_width=True, type="primary"):
            dt = pd.to_datetime(d_s)
            novos = [{"Data": dt, "Líder": l_s, "Nome": n, "Tipo": t, "Célula": 1 if st.session_state[f"ce_{l_s}_{n}_{d_s}"] else 0, "Culto": 1 if st.session_state[f"cu_{l_s}_{n}_{d_s}"] else 0} for n, t in membros.items()]
            st.session_state.db = pd.concat([st.session_state.db[~((st.session_state.db['Data']==dt) & (st.session_state.db['Líder']==l_s))], pd.DataFrame(novos)], ignore_index=True)
            v_df = pd.DataFrame([{"Data": dt, "Líder": l_s, "Vis_Celula": vi_ce, "Vis_Culto": vi_cu}])
            st.session_state.db_visitantes = pd.concat([st.session_state.db_visitantes[~((st.session_state.db_visitantes['Data']==dt) & (st.session_state.db_visitantes['Líder']==l_s))], v_df], ignore_index=True)
            st.success("Salvo!"); st.balloons()

with tab_ob:
    st.write("### 📋 Relatório Semanal Detalhado")
    if not st.session_state.db.empty:
        df_g = st.session_state.db.groupby(['Data', 'Tipo']).agg({'Célula':'sum', 'Culto':'sum'}).reset_index()
        df_p = df_g.pivot(index='Data', columns='Tipo', values=['Célula', 'Culto']).fillna(0).astype(int)
        df_p.columns = [f'{col[0]}_{col[1]}' for col in df_p.columns]
        df_v = st.session_state.db_visitantes.groupby('Data').agg({'Vis_Celula':'sum', 'Vis_Culto':'sum'}).reset_index()
        df_f = pd.merge(df_p.reset_index(), df_v, on='Data', how='left').fillna(0)
        df_f['Data'] = df_f['Data'].dt.strftime('%d/%m/%Y')
        st.dataframe(df_f, use_container_width=True, hide_index=True)

with tab_gestao:
    st.header("⚙️ Configurações")
    n_c = st.text_input("Novo Líder")
    if st.button("Adicionar Célula"):
        if n_c: st.session_state.membros_cadastrados[n_c] = {}; st.rerun()
    if lideres_lista:
        s_c = st.selectbox("Gerenciar Célula:", lideres_lista)
        nm = st.text_input("Nome do Membro")
        tm = st.radio("Categoria", ["Membro", "FA"], horizontal=True)
        if st.button("Salvar Membro"):
            if nm: st.session_state.membros_cadastrados[s_c][nm] = tm; st.rerun()
        if st.button("Excluir Célula"):
            del st.session_state.membros_cadastrados[s_c]; st.rerun()
