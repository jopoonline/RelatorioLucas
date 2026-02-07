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

# --- ABA 1: DASHBOARD (MANTIDA) ---
with tab_dash:
    if st.session_state.db.empty:
        st.info("💡 Sem dados. Lance as chamadas para ativar o Dashboard.")
    elif not lids_f:
        st.warning("Selecione uma célula.")
    else:
        mes_dash = st.selectbox("📅 Escolha o Mês:", MESES_NOMES, index=date.today().month - 1)
        mes_num = MESES_MAP[mes_dash]
        df_base = st.session_state.db[st.session_state.db['Líder'].isin(lids_f)]
        df_v_base = st.session_state.db_visitantes[st.session_state.db_visitantes['Líder'].isin(lids_f)]
        df_mes = df_base[df_base['Data'].dt.month == mes_num]
        df_v_mes = df_v_base[df_v_base['Data'].dt.month == mes_num]

        if not df_mes.empty:
            u_dt = df_mes['Data'].max()
            df_u = df_mes[df_mes['Data'] == u_dt]
            df_v_u = df_v_mes[df_v_mes['Data'] == u_dt] if not df_v_mes.empty else pd.DataFrame()

            st.write(f"#### 🏠 Frequência na Célula ({u_dt.strftime('%d/%m')})")
            c1, c2, c3 = st.columns(3)
            total_m_base = sum([list(st.session_state.membros_cadastrados[l].values()).count("Membro") for l in lids_f])
            c1.markdown(f'<div class="metric-card"><p style="color:#94A3B8; font-size:12px">MEMBROS</p><p class="metric-value-cel">{int(df_u[df_u["Tipo"]=="Membro"]["Célula"].sum())} / {total_m_base}</p></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-card"><p style="color:#94A3B8; font-size:12px">FA (PRESENTE)</p><p class="metric-value-cel">{int(df_u[df_u["Tipo"]=="FA"]["Célula"].sum())}</p></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-card"><p style="color:#94A3B8; font-size:12px">VISITANTES</p><p class="metric-value-cel">{int(df_v_u["Vis_Celula"].sum()) if not df_v_u.empty else 0}</p></div>', unsafe_allow_html=True)

            st.write(f"#### ⛪ Frequência no Culto ({u_dt.strftime('%d/%m')})")
            c4, c5, c6 = st.columns(3)
            c4.markdown(f'<div class="metric-card"><p style="color:#94A3B8; font-size:12px">MEMBROS</p><p class="metric-value-cul">{int(df_u[df_u["Tipo"]=="Membro"]["Culto"].sum())}</p></div>', unsafe_allow_html=True)
            c5.markdown(f'<div class="metric-card"><p style="color:#94A3B8; font-size:12px">FA (PRESENTE)</p><p class="metric-value-cul">{int(df_u[df_u["Tipo"]=="FA"]["Culto"].sum())}</p></div>', unsafe_allow_html=True)
            c6.markdown(f'<div class="metric-card"><p style="color:#94A3B8; font-size:12px">VISITANTES</p><p class="metric-value-cul">{int(df_v_u["Vis_Culto"].sum()) if not df_v_u.empty else 0}</p></div>', unsafe_allow_html=True)

            st.write(f"### 📈 Evolução Semanal - {mes_dash}")
            df_s = df_mes.groupby('Data')[['Célula', 'Culto']].sum().reset_index()
            fig_s = go.Figure()
            fig_s.add_trace(go.Scatter(x=df_s['Data'], y=df_s['Célula'], name='Célula', line=dict(color='#00D4FF', width=4), mode='lines+markers'))
            fig_s.add_trace(go.Scatter(x=df_s['Data'], y=df_s['Culto'], name='Culto', line=dict(color='#EF4444', width=4), mode='lines+markers'))
            fig_s.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white", height=300)
            st.plotly_chart(fig_s, use_container_width=True)

        st.divider()
        st.write("### 🚨 Radar Crítico (2 Faltas Seguidas)")
        d_u_global = sorted(df_base['Data'].unique())
        if len(d_u_global) >= 2:
            df_r = df_base[df_base['Data'].isin(d_u_global[-2:])]
            fals = df_r.groupby(['Nome', 'Líder'])['Célula'].sum().reset_index()
            list_v = fals[fals['Célula'] == 0]
            for _, row in list_v.iterrows():
                st.markdown(f'<div class="radar-card">🚩 <b>{row["Nome"]}</b> ({row["Líder"]}) - 2 Faltas!</div>', unsafe_allow_html=True)
        else:
            st.info("O radar aparecerá após 2 sábados de chamadas.")

# --- ABA 2: LANÇAR (MANTIDA) ---
with tab_lanc:
    if not lideres_lista:
        st.info("Cadastre células na aba 'GESTÃO'.")
    else:
        st.subheader("📝 Chamada Mobile")
        la, lb, lc = st.columns(3)
        mes_sel = la.selectbox("Mês", MESES_NOMES, key="m_l")
        data_sel = lb.selectbox("Sábado", get_sabados(mes_sel), format_func=lambda x: x.strftime('%d/%m'), key="d_l")
        lider_sel = lc.selectbox("Líder", lideres_lista, key="l_l")
        membros_do_lider = st.session_state.membros_cadastrados.get(lider_sel, {})
        for nome, tipo in membros_do_lider.items():
            key_cel, key_cul = f"cel_{lider_sel}_{nome}_{data_sel}", f"cul_{lider_sel}_{nome}_{data_sel}"
            if key_cel not in st.session_state: st.session_state[key_cel] = False
            if key_cul not in st.session_state: st.session_state[key_cul] = False
            st.markdown(f'<div class="member-card"><b>{nome}</b> <small>({tipo})</small></div>', unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            if b1.button(f"🏠 Célula: {'✅' if st.session_state[key_cel] else '❌'}", key=f"btn_cel_{nome}_{data_sel}", use_container_width=True):
                st.session_state[key_cel] = not st.session_state[key_cel]; st.rerun()
            if b2.button(f"⛪ Culto: {'✅' if st.session_state[key_cul] else '❌'}", key=f"btn_cul_{nome}_{data_sel}", use_container_width=True):
                st.session_state[key_cul] = not st.session_state[key_cul]; st.rerun()
        st.write("---")
        v1, v2 = st.columns(2)
        vis_cel = v1.number_input("Visitantes Célula", 0)
        vis_cul = v2.number_input("Visitantes Culto", 0)
        if st.button("💾 SALVAR CHAMADA", use_container_width=True, type="primary"):
            dt = pd.to_datetime(data_sel)
            novos = [{"Data": dt, "Líder": lider_sel, "Nome": n, "Tipo": t, "Célula": 1 if st.session_state[f"cel_{lider_sel}_{n}_{data_sel}"] else 0, "Culto": 1 if st.session_state[f"cul_{lider_sel}_{n}_{data_sel}"] else 0} for n, t in membros_do_lider.items()]
            st.session_state.db = pd.concat([st.session_state.db[~((st.session_state.db['Data']==dt) & (st.session_state.db['Líder']==lider_sel))], pd.DataFrame(novos)], ignore_index=True)
            v_df = pd.DataFrame([{"Data": dt, "Líder": lider_sel, "Vis_Celula": vis_cel, "Vis_Culto": vis_cul}])
            st.session_state.db_visitantes = pd.concat([st.session_state.db_visitantes[~((st.session_state.db_visitantes['Data']==dt) & (st.session_state.db_visitantes['Líder']==lider_sel))], v_df], ignore_index=True)
            st.success("Salvo!"); st.balloons()

# --- ABA 3: RELATÓRIO OB (ATUALIZADA) ---
with tab_ob:
    st.write("### 📋 Relatório Semanal Detalhado")
    if not st.session_state.db.empty:
        # 1. Agrupar dados de Membros e FAs
        df_group = st.session_state.db.groupby(['Data', 'Tipo']).agg({'Célula':'sum', 'Culto':'sum'}).reset_index()
        
        # 2. Pivotar para ter colunas separadas por Tipo
        df_pivot = df_group.pivot(index='Data', columns='Tipo', values=['Célula', 'Culto']).fillna(0).astype(int)
        
        # Achatar os nomes das colunas após o pivot
        df_pivot.columns = [f'{col[0]}_{col[1]}' for col in df_pivot.columns]
        df_pivot = df_pivot.reset_index()
        
        # 3. Adicionar Visitantes
        df_v_sum = st.session_state.db_visitantes.groupby('Data').agg({'Vis_Celula':'sum', 'Vis_Culto':'sum'}).reset_index()
        
        # 4. Mesclar tudo
        df_final = pd.merge(df_pivot, df_v_sum, on='Data', how='left').fillna(0)
        df_final['Data'] = df_final['Data'].dt.strftime('%d/%m/%Y')
        
        # Organizar e renomear colunas para o usuário
        col_map = {
            'Data': 'Sábado',
            'Célula_Membro': 'Célula: Membros',
            'Célula_FA': 'Célula: FA',
            'Vis_Celula': 'Célula: Visitantes',
            'Culto_Membro': 'Culto: Membros',
            'Culto_FA': 'Culto: FA',
            'Vis_Culto': 'Culto: Visitantes'
        }
        # Garantir que todas as colunas existem antes de renomear
        cols_presentes = [c for c in col_map.keys() if c in df_final.columns]
        df_relatorio = df_final[cols_presentes].rename(columns=col_map)
        
        st.dataframe(df_relatorio, use_container_width=True, hide_index=True)
        
        # Botão para baixar em Excel/CSV
        csv = df_relatorio.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar Relatório (CSV)", csv, "relatorio_ob.csv", "text/csv")
    else:
        st.info("Nenhum dado lançado para gerar o relatório.")

# --- ABA 4: GESTÃO (MANTIDA) ---
with tab_gestao:
    st.header("⚙️ Gestão")
    with st.expander("📂 Células"):
        c1, c2 = st.columns(2)
        with c1:
            nova = st.text_input("Novo Líder")
            if st.button("➕ Adicionar"):
                if nova: st.session_state.membros_cadastrados[nova] = {}; st.rerun()
        with c2:
            if lideres_lista:
                rem = st.selectbox("Remover Célula", lideres_lista)
                if st.button("🗑️ Remover"): del st.session_state.membros_cadastrados[rem]; st.rerun()
    if lideres_lista:
        sel = st.selectbox("Editar Célula:", lideres_lista)
        c3, c4 = st.columns(2)
        with c3:
            n_p = st.text_input("Nome")
            t_p = st.radio("Categoria", ["Membro", "FA"], horizontal=True)
            if st.button("✅ Salvar Pessoa"): 
                if n_p: st.session_state.membros_cadastrados[sel][n_p] = t_p; st.rerun()
        with c4:
            lista_p = list(st.session_state.membros_cadastrados[sel].keys())
            p_r = st.selectbox("Pessoa para remover:", lista_p if lista_p else ["Vazio"])
            if st.button("❌ Excluir Pessoa"): del st.session_state.membros_cadastrados[sel][p_r]; st.rerun()
