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
tab_dash, tab_lanc, tab_gestao, tab_ob = st.tabs(["📊 DASHBOARDS", "📝 LANÇAR", "⚙️ GESTÃO", "📋 RELATÓRIO OB"])

# --- TAB DASHBOARDS ---
with tab_dash:
    if st.session_state.db.empty:
        st.info("💡 Sem dados para exibir.")
    else:
        lids_atuais = sorted(list(st.session_state.membros_cadastrados.keys()))
        lids_f = st.multiselect("Filtrar Células:", lids_atuais, default=lids_atuais)
        
        col_m, col_s = st.columns(2)
        mes_sel = col_m.selectbox("Selecione o Mês:", MESES_NOMES, index=datetime.now().month - 1)
        df_mes_f = st.session_state.db[st.session_state.db['Data'].dt.month == MESES_MAP[mes_sel]]
        
        if df_mes_f.empty:
            st.warning(f"Sem dados em {mes_sel}.")
        else:
            datas_disp = sorted(df_mes_f['Data'].unique(), reverse=True)
            data_sel = col_s.selectbox("Selecione a Semana:", datas_disp, format_func=lambda x: pd.to_datetime(x).strftime('%d/%m/%Y'))

            df_sem = st.session_state.db[(st.session_state.db['Data'] == data_sel) & (st.session_state.db['Líder'].isin(lids_f))]
            df_v_sem = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data'] == data_sel) & (st.session_state.db_visitantes['Líder'].isin(lids_f))]

            def get_count_int(tipo):
                total = sum([1 for l in lids_f for n, t in st.session_state.membros_cadastrados.get(l, {}).items() if t == tipo])
                f_cel = int(df_sem[df_sem['Tipo'] == tipo]['Célula'].sum())
                f_cul = int(df_sem[df_sem['Tipo'] == tipo]['Culto'].sum())
                return f"{f_cel}/{total}", f"{f_cul}/{total}"

            m_cel, m_cul = get_count_int("Membro")
            fa_cel, fa_cul = get_count_int("FA")
            v_cel = int(df_v_sem['Vis_Celula'].sum())
            v_cul = int(df_v_sem['Vis_Culto'].sum())

            st.write(f"### 📈 Resumo: {pd.to_datetime(data_sel).strftime('%d/%m')}")
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.markdown(f'<div class="metric-box"><p class="metric-label">Membros Célula</p><p class="metric-value">{m_cel}</p></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-box"><p class="metric-label">Membros Culto</p><p class="metric-value">{m_cul}</p></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-box"><p class="metric-label">FA Célula</p><p class="metric-value">{fa_cel}</p></div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="metric-box"><p class="metric-label">FA Culto</p><p class="metric-value">{fa_cul}</p></div>', unsafe_allow_html=True)
            c5.markdown(f'<div class="metric-box"><p class="metric-label">Visit. Célula</p><p class="metric-value">{v_cel}</p></div>', unsafe_allow_html=True)
            c6.markdown(f'<div class="metric-box"><p class="metric-label">Visit. Culto</p><p class="metric-value">{v_cul}</p></div>', unsafe_allow_html=True)

            col_graf, col_alert = st.columns([2, 1])
            with col_graf:
                # GRÁFICO 1: FREQUÊNCIA SEMANAL - CÉLULA (Linha azul)
                st.write("#### Frequência Semanal - Célula")
                df_mes_p = st.session_state.db[(st.session_state.db['Data'].dt.month == MESES_MAP[mes_sel]) & (st.session_state.db['Líder'].isin(lids_f))].groupby('Data')['Célula'].sum().reset_index()
                df_mes_v = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data'].dt.month == MESES_MAP[mes_sel]) & (st.session_state.db_visitantes['Líder'].isin(lids_f))].groupby('Data')['Vis_Celula'].sum().reset_index()
                df_line_cel = pd.merge(df_mes_p, df_mes_v, on='Data', how='outer').fillna(0).sort_values('Data')

                fig_cel = go.Figure()
                fig_cel.add_trace(go.Scatter(x=df_line_cel['Data'], y=df_line_cel['Célula'], name="Membros+FA", mode='lines+markers', line=dict(color='#38BDF8', width=4)))
                fig_cel.add_trace(go.Scatter(x=df_line_cel['Data'], y=df_line_cel['Vis_Celula'], name="Visitantes", mode='lines+markers', line=dict(color='#60A5FA', width=2, dash='dot')))
                fig_cel.update_layout(template="plotly_dark", height=250, margin=dict(l=10,r=10,b=0,t=20), xaxis=dict(tickformat="%d/%m", tickmode='array', tickvals=df_line_cel['Data']))
                st.plotly_chart(fig_cel, use_container_width=True)

                # GRÁFICO 2: FREQUÊNCIA SEMANAL - CULTO (Linha azul)
                st.write("#### Frequência Semanal - Culto")
                df_mes_p_u = st.session_state.db[(st.session_state.db['Data'].dt.month == MESES_MAP[mes_sel]) & (st.session_state.db['Líder'].isin(lids_f))].groupby('Data')['Culto'].sum().reset_index()
                df_mes_v_u = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data'].dt.month == MESES_MAP[mes_sel]) & (st.session_state.db_visitantes['Líder'].isin(lids_f))].groupby('Data')['Vis_Culto'].sum().reset_index()
                df_line_cul = pd.merge(df_mes_p_u, df_mes_v_u, on='Data', how='outer').fillna(0).sort_values('Data')

                fig_cul = go.Figure()
                fig_cul.add_trace(go.Scatter(x=df_line_cul['Data'], y=df_line_cul['Culto'], name="Membros+FA", mode='lines+markers', line=dict(color='#1D4ED8', width=4)))
                fig_cul.add_trace(go.Scatter(x=df_line_cul['Data'], y=df_line_cul['Vis_Culto'], name="Visitantes", mode='lines+markers', line=dict(color='#3B82F6', width=2, dash='dot')))
                fig_cul.update_layout(template="plotly_dark", height=250, margin=dict(l=10,r=10,b=0,t=20), xaxis=dict(tickformat="%d/%m", tickmode='array', tickvals=df_line_cul['Data']))
                st.plotly_chart(fig_cul, use_container_width=True)

                # GRÁFICO 3: EVOLUÇÃO MENSAL (2 meses anteriores)
                st.write("#### Evolução Mensal Retroativa (2 Meses Anteriores)")
                mes_ref = MESES_MAP[mes_sel]
                meses_anteriores = [(mes_ref - 2), (mes_ref - 1)]
                meses_anteriores = [m if m > 0 else m + 12 for m in meses_anteriores]
                
                df_retro = st.session_state.db[(st.session_state.db['Data'].dt.month.isin(meses_anteriores)) & (st.session_state.db['Líder'].isin(lids_f))].copy()
                if not df_retro.empty:
                    df_retro['Mes_Num'] = df_retro['Data'].dt.month
                    res_retro_p = df_retro.groupby('Mes_Num')['Célula'].sum().reset_index()
                    df_retro_v = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data'].dt.month.isin(meses_anteriores)) & (st.session_state.db_visitantes['Líder'].isin(lids_f))].copy()
                    df_retro_v['Mes_Num'] = df_retro_v['Data'].dt.month
                    res_retro_v = df_retro_v.groupby('Mes_Num')['Vis_Celula'].sum().reset_index()
                    res_final = pd.merge(res_retro_p, res_retro_v, on='Mes_Num', how='outer').fillna(0)
                    res_final['Mes_Nome'] = res_final['Mes_Num'].apply(lambda x: MESES_NOMES[x-1])
                    res_final = res_final.sort_values('Mes_Num')

                    fig_ev = go.Figure()
                    fig_ev.add_trace(go.Scatter(x=res_final['Mes_Nome'], y=res_final['Célula'], name="Interno", mode='lines+markers+text', text=res_final['Célula'], textposition="top center", line=dict(color='#38BDF8', width=4)))
                    fig_ev.add_trace(go.Scatter(x=res_final['Mes_Nome'], y=res_final['Vis_Celula'], name="Visitantes", mode='lines+markers+text', text=res_final['Vis_Celula'], textposition="top center", line=dict(color='#FACC15', width=3)))
                    fig_ev.update_layout(template="plotly_dark", height=300, margin=dict(l=10,r=10,b=0,t=40))
                    st.plotly_chart(fig_ev, use_container_width=True)

            with col_alert:
                st.write("#### 🚨 Alertas")
                for lider in lids_f:
                    df_h = st.session_state.db[st.session_state.db['Líder'] == lider].sort_values('Data', ascending=False)
                    for m in df_h['Nome'].unique():
                        u = df_h[df_h['Nome'] == m].head(2)
                        if len(u) == 2 and u['Célula'].sum() == 0:
                            st.markdown(f'<div class="alert-danger">⚠️ {m} ({lider}): Faltou 2x</div>', unsafe_allow_html=True)
                for lider in lids_f:
                    df_v_h = st.session_state.db_visitantes[st.session_state.db_visitantes['Líder'] == lider].sort_values('Data', ascending=False).head(2)
                    if len(df_v_h) == 2 and df_v_h['Vis_Celula'].sum() == 0:
                        st.markdown(f'<div class="alert-danger">📉 {lider}: 0 Visitantes</div>', unsafe_allow_html=True)

# --- TAB LANÇAR ---
with tab_lanc:
    if not st.session_state.membros_cadastrados:
        st.warning("Cadastre líderes em GESTÃO.")
    else:
        ca, cb, cc = st.columns(3)
        m_l = ca.selectbox("Mês Lançamento", MESES_NOMES, index=datetime.now().month-1)
        d_l = cb.selectbox("Data", [d for d in [date(2026, MESES_MAP[m_l], 1) + timedelta(days=x) for x in range(32)] if d.month == MESES_MAP[m_l] and d.weekday() == 5], format_func=lambda x: x.strftime('%d/%m'))
        l_l = cc.selectbox("Líder", sorted(st.session_state.membros_cadastrados.keys()))
        
        va, vb = st.columns(2)
        v_cel_in = va.number_input("Visitantes Célula", min_value=0, step=1)
        v_cul_in = vb.number_input("Visitantes Culto", min_value=0, step=1)
        
        mem = st.session_state.membros_cadastrados[l_l]
        novos = []
        for n, t in mem.items():
            c_n, c_e, c_u = st.columns([2,1,1])
            c_n.write(f"**{n}** ({t})")
            p_e = c_e.checkbox("Célula", key=f"e_{n}_{d_l}")
            p_u = c_u.checkbox("Culto", key=f"u_{n}_{d_l}")
            novos.append({"Data": d_l, "Líder": l_l, "Nome": n, "Tipo": t, "Célula": 1 if p_e else 0, "Culto": 1 if p_u else 0})
            
        if st.button("💾 SALVAR TUDO", use_container_width=True, type="primary"):
            dt_l = pd.to_datetime(d_l)
            df_p_new = pd.concat([st.session_state.db[~((st.session_state.db['Data']==dt_l) & (st.session_state.db['Líder']==l_l))], pd.DataFrame(novos)])
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Presencas", data=df_p_new)
            df_v_new = pd.concat([st.session_state.db_visitantes[~((st.session_state.db_visitantes['Data']==dt_l) & (st.session_state.db_visitantes['Líder']==l_l))], pd.DataFrame([{"Data": d_l, "Líder": l_l, "Vis_Celula": v_cel_in, "Vis_Culto": v_cul_in}])])
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Visitantes", data=df_v_new)
            st.cache_data.clear()
            st.success("Salvo!")
            st.rerun()

# --- TAB GESTÃO ---
with tab_gestao:
    st.subheader("⚙️ Cadastro")
    col1, col2 = st.columns(2)
    with col1:
        n_l = st.text_input("Novo Líder")
        if st.button("Criar Célula"):
            if n_l: st.session_state.membros_cadastrados[n_l] = {}; sincronizar_membros(); st.rerun()
    with col2:
        if st.session_state.membros_cadastrados:
            l_sel = st.selectbox("Na Célula:", sorted(st.session_state.membros_cadastrados.keys()))
            n_m = st.text_input("Nome Pessoa")
            t_m = st.radio("Tipo", ["Membro", "FA"], horizontal=True)
            if st.button("Salvar Pessoa"):
                st.session_state.membros_cadastrados[l_sel][n_m] = t_m
                sincronizar_membros(); st.rerun()

    st.divider()
    st.subheader("🗑️ Área de Exclusão / Edição")
    lids_lista = sorted(st.session_state.membros_cadastrados.keys())
    if lids_lista:
        col_ed1, col_ed2 = st.columns(2)
        with col_ed1:
            l_ed = st.selectbox("Célula da Pessoa:", lids_lista, key="l_ed")
            if l_ed in st.session_state.membros_cadastrados and st.session_state.membros_cadastrados[l_ed]:
                p_ed = st.selectbox("Selecione a Pessoa:", sorted(st.session_state.membros_cadastrados[l_ed].keys()))
                tipo_atual = st.session_state.membros_cadastrados[l_ed][p_ed]
                st.info(f"Tipo atual: {tipo_atual}")
                ce1, ce2 = st.columns(2)
                if ce1.button(f"Mudar para {'FA' if tipo_atual == 'Membro' else 'Membro'}"):
                    st.session_state.membros_cadastrados[l_ed][p_ed] = "FA" if tipo_atual == "Membro" else "Membro"
                    sincronizar_membros(); st.rerun()
                if ce2.button("Excluir Pessoa", type="primary"):
                    del st.session_state.membros_cadastrados[l_ed][p_ed]
                    sincronizar_membros(); st.rerun()
            else:
                st.write("Célula vazia.")
        with col_ed2:
            l_del = st.selectbox("Célula a excluir:", lids_lista, key="l_del")
            if st.button("EXCLUIR CÉLULA INTEIRA", type="primary"):
                if l_del in st.session_state.membros_cadastrados:
                    del st.session_state.membros_cadastrados[l_del]
                    sincronizar_membros(); st.rerun()

# --- TAB RELATÓRIO OB ---
with tab_ob:
    st.subheader("📋 Relatório Semanal")
    mes_ob = st.selectbox("Relatório de:", MESES_NOMES, index=datetime.now().month-1, key="m_ob")
    df_p_ob = st.session_state.db[st.session_state.db['Data'].dt.month == MESES_MAP[mes_ob]]
    if not df_p_ob.empty:
        for sem in sorted(df_p_ob['Data'].unique(), reverse=True):
            st.write(f"#### 📅 Semana: {pd.to_datetime(sem).strftime('%d/%m/%Y')}")
            dados_ob = []
            for lid in sorted(st.session_state.membros_cadastrados.keys()):
                f_p = df_p_ob[(df_p_ob['Data'] == sem) & (df_p_ob['Líder'] == lid)]
                f_v = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data'] == sem) & (st.session_state.db_visitantes['Líder'] == lid)]
                m_t = sum(1 for n, t in st.session_state.membros_cadastrados[lid].items() if t == "Membro")
                fa_t = sum(1 for n, t in st.session_state.membros_cadastrados[lid].items() if t == "FA")
                dados_ob.append({
                    "Líder": lid,
                    "Membros Cél/Cult": f"{int(f_p[f_p['Tipo']=='Membro']['Célula'].sum())}/{m_t} | {int(f_p[f_p['Tipo']=='Membro']['Culto'].sum())}/{m_t}",
                    "FA Cél/Cult": f"{int(f_p[f_p['Tipo']=='FA']['Célula'].sum())}/{fa_t} | {int(f_p[f_p['Tipo']=='FA']['Culto'].sum())}/{fa_t}",
                    "Vis. Cél/Cult": f"{int(f_v['Vis_Celula'].sum())} | {int(f_v['Vis_Culto'].sum())}"
                })
            st.table(pd.DataFrame(dados_ob))
