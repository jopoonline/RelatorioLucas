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
    .metric-value { color: #00D4FF; font-size: 24px; font-weight: 800; }
    .member-card {
        background: #1E293B; padding: 12px; border-radius: 15px;
        border: 1px solid #334155; margin-top: 15px;
    }
    .radar-card { background: rgba(239, 68, 68, 0.15); border-left: 5px solid #EF4444; padding: 12px; border-radius: 8px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 2. INICIALIZAÇÃO DE DADOS (AGORA EM BRANCO) ---
if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=["Data", "Líder", "Nome", "Tipo", "Célula", "Culto"])
if 'db_visitantes' not in st.session_state:
    st.session_state.db_visitantes = pd.DataFrame(columns=["Data", "Líder", "Vis_Celula", "Vis_Culto"])

# Dicionário de membros começa vazio para integração futura
if 'membros_cadastrados' not in st.session_state:
    st.session_state.membros_cadastrados = {}

MESES_NOMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MESES_MAP = {n: i+1 for i, n in enumerate(MESES_NOMES)}

def get_sabados(mes):
    d = date(2026, MESES_MAP[mes], 1)
    while d.weekday() != 5: d += timedelta(days=1)
    sats = []
    while d.month == MESES_MAP[mes]:
        sats.append(d); d += timedelta(days=7)
    return sats

lideres_lista = list(st.session_state.membros_cadastrados.keys())

# --- 3. INTERFACE ---
st.markdown('<p class="main-title">🛡️ DISTRITO PRO 2026</p>', unsafe_allow_html=True)

if not lideres_lista:
    st.warning("⚠️ Nenhuma célula cadastrada. Vá na aba 'GESTÃO' para adicionar líderes e membros.")

lids_f = st.multiselect("Filtrar Células:", lideres_lista, default=lideres_lista)

tab_dash, tab_lanc, tab_ob, tab_gestao = st.tabs(["📊 DASHBOARD", "📝 LANÇAR", "📋 RELATÓRIO OB", "⚙️ GESTÃO"])

# --- ABA 1: DASHBOARD ---
with tab_dash:
    if st.session_state.db.empty:
        st.info("💡 Lance os dados para ver os indicadores.")
    elif not lids_f:
        st.info("Selecione uma célula no filtro acima.")
    else:
        df = st.session_state.db[st.session_state.db['Líder'].isin(lids_f)]
        df_v = st.session_state.db_visitantes[st.session_state.db_visitantes['Líder'].isin(lids_f)]
        u_dt = df['Data'].max()
        df_u = df[df['Data'] == u_dt]
        df_v_u = df_v[df_v['Data'] == u_dt] if not df_v.empty else pd.DataFrame()

        st.write("#### 🏠 Frequência na Célula (Hoje)")
        c1, c2, c3 = st.columns(3)
        total_m_base = sum([list(st.session_state.membros_cadastrados[l].values()).count("Membro") for l in lids_f])
        
        c1.markdown(f'<div class="metric-card"><p style="color:#94A3B8; font-size:12px">MEMBROS</p><p class="metric-value">{int(df_u[df_u["Tipo"]=="Membro"]["Célula"].sum())} / {total_m_base}</p></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="metric-card"><p style="color:#94A3B8; font-size:12px">FA (PRESENTE)</p><p class="metric-value">{int(df_u[df_u["Tipo"]=="FA"]["Célula"].sum())}</p></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="metric-card"><p style="color:#94A3B8; font-size:12px">VISITANTES</p><p class="metric-value">{int(df_v_u["Vis_Celula"].sum()) if not df_v_u.empty else 0}</p></div>', unsafe_allow_html=True)

        st.write("#### ⛪ Frequência no Culto (Hoje)")
        c4, c5, c6 = st.columns(3)
        c4.markdown(f'<div class="metric-card"><p style="color:#FF4B4B; font-size:12px">MEMBROS</p><p class="metric-value">{int(df_u[df_u["Tipo"]=="Membro"]["Culto"].sum())}</p></div>', unsafe_allow_html=True)
        c5.markdown(f'<div class="metric-card"><p style="color:#FF4B4B; font-size:12px">FA (PRESENTE)</p><p class="metric-value">{int(df_u[df_u["Tipo"]=="FA"]["Culto"].sum())}</p></div>', unsafe_allow_html=True)
        c6.markdown(f'<div class="metric-card"><p style="color:#FF4B4B; font-size:12px">VISITANTES</p><p class="metric-value">{int(df_v_u["Vis_Culto"].sum()) if not df_v_u.empty else 0}</p></div>', unsafe_allow_html=True)

        st.write("### 📈 Evolução Geral")
        df_s = df.groupby('Data')[['Célula', 'Culto']].sum().reset_index()
        fig_s = go.Figure()
        fig_s.add_trace(go.Scatter(x=df_s['Data'], y=df_s['Célula'], name='Célula', line=dict(color='#00D4FF', width=4), mode='lines+markers'))
        fig_s.add_trace(go.Scatter(x=df_s['Data'], y=df_s['Culto'], name='Culto', line=dict(color='#FF4B4B', width=4), mode='lines+markers'))
        fig_s.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white", height=300)
        st.plotly_chart(fig_s, use_container_width=True)

# --- ABA 2: LANÇAMENTO ---
with tab_lanc:
    if not lideres_lista:
        st.info("Cadastre células na aba Gestão para habilitar o lançamento.")
    else:
        st.subheader("📝 Chamada Mobile")
        la, lb, lc = st.columns(3)
        mes_sel = la.selectbox("Mês", MESES_NOMES)
        data_sel = lb.selectbox("Sábado", get_sabados(mes_sel), format_func=lambda x: x.strftime('%d/%m'))
        lider_sel = lc.selectbox("Líder", lideres_lista)
        
        membros_do_lider = st.session_state.membros_cadastrados.get(lider_sel, {})
        
        if not membros_do_lider:
            st.warning("Este líder não possui membros cadastrados.")
        
        for nome, tipo in membros_do_lider.items():
            key_cel, key_cul = f"cel_{lider_sel}_{nome}_{data_sel}", f"cul_{lider_sel}_{nome}_{data_sel}"
            if key_cel not in st.session_state: st.session_state[key_cel] = False
            if key_cul not in st.session_state: st.session_state[key_cul] = False
            
            st.markdown(f'<div class="member-card"><b>{nome}</b> <small style="color:#94A3B8">({tipo})</small></div>', unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            if b1.button(f"🏠 Célula: {'✅' if st.session_state[key_cel] else '❌'}", key=f"btn_{key_cel}", use_container_width=True):
                st.session_state[key_cel] = not st.session_state[key_cel]; st.rerun()
            if b2.button(f"⛪ Culto: {'✅' if st.session_state[key_cul] else '❌'}", key=f"btn_{key_cul}", use_container_width=True):
                st.session_state[key_cul] = not st.session_state[key_cul]; st.rerun()

        st.write("---")
        v1, v2 = st.columns(2)
        vis_cel = v1.number_input("Visitantes na Célula", 0)
        vis_cul = v2.number_input("Visitantes no Culto", 0)
        
        if st.button("💾 SALVAR CHAMADA", use_container_width=True, type="primary"):
            if not membros_do_lider:
                st.error("Não há dados para salvar.")
            else:
                dt = pd.to_datetime(data_sel)
                novos_dados = [{"Data": dt, "Líder": lider_sel, "Nome": n, "Tipo": t, "Célula": 1 if st.session_state[f"cel_{lider_sel}_{n}_{data_sel}"] else 0, "Culto": 1 if st.session_state[f"cul_{lider_sel}_{n}_{data_sel}"] else 0} for n, t in membros_do_lider.items()]
                st.session_state.db = pd.concat([st.session_state.db[~((st.session_state.db['Data']==dt) & (st.session_state.db['Líder']==lider_sel))], pd.DataFrame(novos_dados)], ignore_index=True)
                v_df = pd.DataFrame([{"Data": dt, "Líder": lider_sel, "Vis_Celula": vis_cel, "Vis_Culto": vis_cul}])
                st.session_state.db_visitantes = pd.concat([st.session_state.db_visitantes[~((st.session_state.db_visitantes['Data']==dt) & (st.session_state.db_visitantes['Líder']==lider_sel))], v_df], ignore_index=True)
                st.success("Salvo!"); st.balloons()

# --- ABA 3: RELATÓRIO OB ---
with tab_ob:
    if not st.session_state.db.empty:
        df_ob = st.session_state.db.groupby('Data').agg({'Célula':'sum', 'Culto':'sum'}).reset_index()
        df_ob['Sábado'] = df_ob['Data'].dt.strftime('%d/%m')
        st.dataframe(df_ob[['Sábado', 'Célula', 'Culto']], use_container_width=True, hide_index=True)
    else:
        st.info("Aguardando lançamentos.")

# --- ABA 4: GESTÃO ---
with tab_gestao:
    st.header("⚙️ Gestão")
    with st.expander("📂 Células"):
        c1, c2 = st.columns(2)
        with c1:
            nova = st.text_input("Nova Célula (Líder)")
            if st.button("➕ Criar"):
                if nova: st.session_state.membros_cadastrados[nova] = {}; st.rerun()
        with c2:
            rem = st.selectbox("Remover Célula", lideres_lista) if lideres_lista else st.selectbox("Remover Célula", ["-"])
            if st.button("🗑️ Excluir") and rem != "-":
                del st.session_state.membros_cadastrados[rem]; st.rerun()
    
    st.divider()
    
    if lideres_lista:
        sel = st.selectbox("Editar Célula:", lideres_lista)
        c3, c4 = st.columns(2)
        with c3:
            n_p = st.text_input("Nome da Pessoa")
            t_p = st.radio("Categoria", ["Membro", "FA"], horizontal=True)
            if st.button("✅ Salvar"): 
                if n_p: st.session_state.membros_cadastrados[sel][n_p] = t_p; st.rerun()
        with c4:
            lista = list(st.session_state.membros_cadastrados[sel].keys())
            p_r = st.selectbox("Remover:", lista if lista else ["Vazio"])
            if st.button("❌ Excluir Pessoa") and p_r != "Vazio":
                del st.session_state.membros_cadastrados[sel][p_r]; st.rerun()
    else:
        st.info("Crie uma célula primeiro.")
