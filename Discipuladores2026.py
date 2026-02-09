import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta, datetime
from streamlit_gsheets import GSheetsConnection
import time

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Distrito Pro 2026", layout="wide", page_icon="🛡️")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1y3vAXagtbdzaTHGEkPOuWI3TvzcfFYhfO1JUt0GrhG8/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. FUNÇÕES DE DADOS ---
@st.cache_data(ttl=2)
def carregar_dados():
    try:
        df_p = conn.read(spreadsheet=URL_PLANILHA, worksheet="Presencas")
        df_v = conn.read(spreadsheet=URL_PLANILHA, worksheet="Visitantes")
        df_m = conn.read(spreadsheet=URL_PLANILHA, worksheet="Membros")
        
        if df_p is None or df_p.empty: df_p = pd.DataFrame(columns=['Data', 'Líder', 'Nome', 'Tipo', 'Célula', 'Culto'])
        if df_v is None or df_v.empty: df_v = pd.DataFrame(columns=['Data', 'Líder', 'Vis_Celula', 'Vis_Culto'])

        df_p = df_p.loc[:, ~df_p.columns.str.contains('^Data_Ref|^Data_Obj|^MesNum')]
        df_v = df_v.loc[:, ~df_v.columns.str.contains('^Data_Ref|^Data_Obj|^MesNum')]

        def padronizar(df):
            df['Data_Obj'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
            nulos = df['Data_Obj'].isna()
            if nulos.any():
                df.loc[nulos, 'Data_Obj'] = pd.to_datetime(df.loc[nulos, 'Data'], errors='coerce')
            df['Data_Ref'] = df['Data_Obj'].dt.strftime('%Y-%m-%d')
            df['MesNum'] = df['Data_Obj'].dt.month
            return df

        df_p = padronizar(df_p)
        df_v = padronizar(df_v)
        df_p = df_p.dropna(subset=['Data_Obj'])
        df_v = df_v.dropna(subset=['Data_Obj'])

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
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame(), pd.DataFrame(), {}

def salvar_seguro(worksheet, df):
    try:
        df_save = df.copy()
        cols_limpar = ['Data_Obj', 'Data_Ref', 'MesNum']
        df_save = df_save.drop(columns=[c for c in cols_limpar if c in df_save.columns])
        if 'Data' in df_save.columns:
            df_save['Data'] = pd.to_datetime(df_save['Data']).dt.strftime('%Y-%m-%d')
        conn.update(spreadsheet=URL_PLANILHA, worksheet=worksheet, data=df_save)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

# --- 3. INICIALIZAÇÃO ---
db_p, db_v, m_dict = carregar_dados()
st.session_state.db = db_p
st.session_state.db_visitantes = db_v
st.session_state.membros_cadastrados = m_dict

# --- 4. ESTILO ---
st.markdown("""<style>.stApp { background-color: #0F172A; color: #F8FAFC; } .metric-box { background: #1E293B; padding: 15px; border-radius: 10px; border-top: 4px solid #0284C7; text-align: center; margin-bottom: 10px; } .metric-value { font-size: 24px; font-weight: 800; color: #38BDF8; display: block; }</style>""", unsafe_allow_html=True)

MESES_NOMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MESES_MAP = {n: i+1 for i, n in enumerate(MESES_NOMES)}

st.title("🛡️ DISTRITO PRO 2026")
tab_dash, tab_lanc, tab_gestao, tab_ob = st.tabs(["📊 DASHBOARDS", "📝 LANÇAR", "⚙️ GESTÃO", "📋 RELATÓRIO OB"])

# --- TAB DASHBOARDS ---
with tab_dash:
    if st.button("🔄 Sincronizar Planilha"):
        st.cache_data.clear()
        st.rerun()
    
    if st.session_state.db.empty:
        st.info("💡 Nenhuma informação encontrada.")
    else:
        lids_atuais = sorted(list(st.session_state.membros_cadastrados.keys()))
        lids_f = st.multiselect("Filtrar Células:", lids_atuais, default=lids_atuais)

        # --- ALERTAS 2 SEMANAS ---
        datas_unicas = sorted(st.session_state.db['Data_Ref'].unique(), reverse=True)
        if len(datas_unicas) >= 2:
            st.subheader("⚠️ Alertas de Frequência")
            d1, d2 = datas_unicas[0], datas_unicas[1]
            for lid in lids_f:
                v1 = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data_Ref']==d1)&(st.session_state.db_visitantes['Líder']==lid)]['Vis_Celula'].sum()
                v2 = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data_Ref']==d2)&(st.session_state.db_visitantes['Líder']==lid)]['Vis_Celula'].sum()
                if v1 == 0 and v2 == 0: st.error(f"🚩 **{lid}**: Sem visitantes nas últimas 2 semanas.")
                for nome, tipo in st.session_state.membros_cadastrados.get(lid, {}).items():
                    p1 = st.session_state.db[(st.session_state.db['Data_Ref']==d1)&(st.session_state.db['Líder']==lid)&(st.session_state.db['Nome']==nome)]['Célula'].sum()
                    p2 = st.session_state.db[(st.session_state.db['Data_Ref']==d2)&(st.session_state.db['Líder']==lid)&(st.session_state.db['Nome']==nome)]['Célula'].sum()
                    if p1 == 0 and p2 == 0: st.error(f"👤 **{nome}** ({lid}): Ausente nas últimas 2 reuniões.")

        st.divider()
        col_m, col_s = st.columns(2)
        mes_sel = col_m.selectbox("Mês:", MESES_NOMES, index=datetime.now().month - 1)
        df_mes = st.session_state.db[st.session_state.db['MesNum'] == MESES_MAP[mes_sel]]
        
        if not df_mes.empty:
            datas_mes = sorted(df_mes['Data_Ref'].unique(), reverse=True)
            sel_ref = col_s.selectbox("Semana:", datas_mes, format_func=lambda x: datetime.strptime(x, '%Y-%m-%d').strftime('%d/%m/%Y'))
            df_sem = df_mes[(df_mes['Data_Ref'] == sel_ref) & (df_mes['Líder'].isin(lids_f))]
            df_v_sem = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data_Ref'] == sel_ref) & (st.session_state.db_visitantes['Líder'].isin(lids_f))]

            # CARDS SEMANAIS
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            def get_card(tipo, modo):
                if tipo == "M": return int(df_sem[df_sem['Tipo'].isin(['Membro','Liderança'])][modo].sum())
                if tipo == "V": return int(df_v_sem['Vis_Celula' if modo=='Célula' else 'Vis_Culto'].sum() if not df_v_sem.empty else 0)
                return int(df_sem[df_sem['Tipo'] == "FA"][modo].sum())
            
            c1.markdown(f'<div class="metric-box">Mem. Célula<br><span class="metric-value">{get_card("M","Célula")}</span></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-box">FA Célula<br><span class="metric-value">{get_card("FA","Célula")}</span></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-box">Vis. Célula<br><span class="metric-value">{get_card("V","Célula")}</span></div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="metric-box">Mem. Culto<br><span class="metric-value">{get_card("M","Culto")}</span></div>', unsafe_allow_html=True)
            c5.markdown(f'<div class="metric-box">FA Culto<br><span class="metric-value">{get_card("FA","Culto")}</span></div>', unsafe_allow_html=True)
            c6.markdown(f'<div class="metric-box">Vis. Culto<br><span class="metric-value">{get_card("V","Culto")}</span></div>', unsafe_allow_html=True)

            # GRÁFICOS EVOLUTIVOS (MEMBROS+FA vs VISITANTES)
            st.write("### 📈 Evolução Semanal (Apenas Sábados)")
            cg1, cg2 = st.columns(2)
            for col, modo in zip([cg1, cg2], ['Célula', 'Culto']):
                g_data = df_mes[df_mes['Líder'].isin(lids_f)].groupby('Data_Ref')[modo].sum().reset_index()
                g_vis = st.session_state.db_visitantes[(st.session_state.db_visitantes['MesNum']==MESES_MAP[mes_sel])&(st.session_state.db_visitantes['Líder'].isin(lids_f))].groupby('Data_Ref')['Vis_Celula' if modo=='Célula' else 'Vis_Culto'].sum().reset_index()
                merged = pd.merge(g_data, g_vis, on='Data_Ref', how='outer').fillna(0).sort_values('Data_Ref')
                merged['Data_Fmt'] = merged['Data_Ref'].apply(lambda x: datetime.strptime(x, '%Y-%m-%d').strftime('%d/%m'))
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=merged['Data_Fmt'], y=merged[modo], name='Membros+FA', mode='lines+markers+text', text=merged[modo], textposition="top center", line=dict(color='#38BDF8', width=3)))
                fig.add_trace(go.Scatter(x=merged['Data_Fmt'], y=merged.iloc[:, 2], name='Visitantes', mode='lines+markers+text', text=merged.iloc[:, 2], textposition="bottom center", line=dict(color='#F472B6', width=3)))
                fig.update_layout(title=f"Frequência {modo}", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"), margin=dict(l=20,r=20,t=40,b=20), height=350, showlegend=True)
                col.plotly_chart(fig, use_container_width=True)

            # 3º DASHBOARD: MENSAL E COMPARATIVO
            st.divider()
            st.subheader(f"📊 Dashboard Mensal: {mes_sel}")
            m1, m2, m3, m4 = st.columns(4)
            total_cel = df_mes[df_mes['Líder'].isin(lids_f)]['Célula'].sum() + st.session_state.db_visitantes[(st.session_state.db_visitantes['MesNum']==MESES_MAP[mes_sel])&(st.session_state.db_visitantes['Líder'].isin(lids_f))]['Vis_Celula'].sum()
            total_culto = df_mes[df_mes['Líder'].isin(lids_f)]['Culto'].sum() + st.session_state.db_visitantes[(st.session_state.db_visitantes['MesNum']==MESES_MAP[mes_sel])&(st.session_state.db_visitantes['Líder'].isin(lids_f))]['Vis_Culto'].sum()
            m1.metric("Total Acumulado Célula", int(total_cel))
            m2.metric("Total Acumulado Culto", int(total_culto))
            
            # Comparativo 2 meses anteriores
            mes_atual_idx = MESES_MAP[mes_sel]
            comp_data = []
            for i in range(2, -1, -1):
                m_num = mes_atual_idx - i
                if m_num > 0:
                    m_nome = MESES_NOMES[m_num-1]
                    soma = st.session_state.db[(st.session_state.db['MesNum']==m_num)&(st.session_state.db['Líder'].isin(lids_f))]['Célula'].sum()
                    comp_data.append({"Mês": m_nome, "Total Célula": int(soma)})
            
            if len(comp_data) > 1:
                st.write("**Comparativo com Meses Anteriores (Célula)**")
                st.plotly_chart(px.bar(pd.DataFrame(comp_data), x='Mês', y='Total Célula', text_auto=True, color_discrete_sequence=['#0284C7']), use_container_width=True)

# --- TAB LANÇAR (INALTERADO) ---
with tab_lanc:
    if not st.session_state.membros_cadastrados: st.warning("Nenhuma célula cadastrada.")
    else:
        cl1, cl2, cl3 = st.columns(3)
        m_l = cl1.selectbox("Mês", MESES_NOMES, index=datetime.now().month-1, key="l_m")
        datas_sab = [date(2026, MESES_MAP[m_l], d) for d in range(1, 32) if (date(2026, MESES_MAP[m_l], 1) + timedelta(days=d-1)).month == MESES_MAP[m_l] and (date(2026, MESES_MAP[m_l], 1) + timedelta(days=d-1)).weekday() == 5]
        d_l = cl2.selectbox("Sábado", datas_sab, format_func=lambda x: x.strftime('%d/%m'), key="l_d")
        l_l = cl3.selectbox("Sua Célula", sorted(st.session_state.membros_cadastrados.keys()), key="l_l")
        novos = []
        st.subheader(f"Chamada - {l_l}")
        c_n, c_e, c_u = st.columns([2,1,1])
        lp_ce = c_e.checkbox("Célula", value=True, key="lpce_check")
        lp_cu = c_u.checkbox("Culto", value=True, key="lpcu_check")
        novos.append({"Data": d_l, "Líder": l_l, "Nome": l_l, "Tipo": "Liderança", "Célula": 1 if lp_ce else 0, "Culto": 1 if lp_cu else 0})
        for nome, tipo in st.session_state.membros_cadastrados.get(l_l, {}).items():
            cn, ce, cu = st.columns([2,1,1])
            cn.write(f"{nome} ({tipo})")
            p_ce, p_cu = ce.checkbox("Célula", key=f"c_{nome}"), cu.checkbox("Culto", key=f"u_{nome}")
            novos.append({"Data": d_l, "Líder": l_l, "Nome": nome, "Tipo": tipo, "Célula": 1 if p_ce else 0, "Culto": 1 if p_cu else 0})
        v_ce, v_cu = st.number_input("Visitantes Célula", 0, key="vce_in"), st.number_input("Visitantes Culto", 0, key="vcu_in")
        if st.button("💾 ENVIAR LANÇAMENTO", type="primary", use_container_width=True):
            dt_ref = d_l.strftime('%Y-%m-%d')
            df_p_atu = st.session_state.db[~((st.session_state.db['Data_Ref'] == dt_ref) & (st.session_state.db['Líder'] == l_l))]
            df_v_atu = st.session_state.db_visitantes[~((st.session_state.db_visitantes['Data_Ref'] == dt_ref) & (st.session_state.db_visitantes['Líder'] == l_l))]
            if salvar_seguro("Presencas", pd.concat([df_p_atu, pd.DataFrame(novos)])) and salvar_seguro("Visitantes", pd.concat([df_v_atu, pd.DataFrame([{"Data": d_l, "Líder": l_l, "Vis_Celula": v_ce, "Vis_Culto": v_cu}])])):
                st.success("Lançamento salvo!"); st.cache_data.clear(); time.sleep(1); st.rerun()

# --- TAB GESTÃO (INALTERADO) ---
with tab_gestao:
    st.subheader("Configuração da Rede")
    g1, g2 = st.columns(2)
    with g1:
        n_lid = st.text_input("Novo Líder")
        if st.button("Criar Célula"):
            if n_lid:
                st.session_state.membros_cadastrados[n_lid] = {}
                lista_m = []
                for lid, pess in st.session_state.membros_cadastrados.items():
                    if not pess: lista_m.append({"Líder": lid, "Nome": "LIDER_INICIAL", "Tipo": "Liderança"})
                    else:
                        for n, t in pess.items(): lista_m.append({"Líder": lid, "Nome": n, "Tipo": t})
                salvar_seguro("Membros", pd.DataFrame(lista_m)); st.rerun()
    with g2:
        if st.session_state.membros_cadastrados:
            c_sel = st.selectbox("Célula:", sorted(st.session_state.membros_cadastrados.keys()), key="c_sel_gest")
            n_mem = st.text_input("Nome da Pessoa", key="n_mem_gest")
            t_mem = st.radio("Tipo", ["Membro", "FA"], horizontal=True, key="t_mem_gest")
            if st.button("Adicionar à Lista"):
                if n_mem:
                    st.session_state.membros_cadastrados[c_sel][n_mem] = t_mem
                    lista_m = []
                    for lid, pess in st.session_state.membros_cadastrados.items():
                        if not pess: lista_m.append({"Líder": lid, "Nome": "LIDER_INICIAL", "Tipo": "Liderança"})
                        else:
                            for n, t in pess.items(): lista_m.append({"Líder": lid, "Nome": n, "Tipo": t})
                    salvar_seguro("Membros", pd.DataFrame(lista_m)); st.rerun()

# --- TAB RELATÓRIO OB (INALTERADO) ---
with tab_ob:
    m_ob = st.selectbox("Mês do Relatório:", MESES_NOMES, index=datetime.now().month-1, key="m_ob")
    df_ob = st.session_state.db[st.session_state.db['MesNum'] == MESES_MAP[m_ob]]
    if not df_ob.empty:
        for data in sorted(df_ob['Data_Ref'].unique(), reverse=True):
            st.markdown(f"**Semana de {datetime.strptime(data, '%Y-%m-%d').strftime('%d/%m/%Y')}**")
            resumo_ob = []
            for lid in sorted(st.session_state.membros_cadastrados.keys()):
                d_lid = df_ob[(df_ob['Data_Ref'] == data) & (df_ob['Líder'] == lid)]
                pres_l = "✅" if not d_lid[d_lid['Tipo'] == 'Liderança'].empty and d_lid[d_lid['Tipo'] == 'Liderança']['Célula'].sum() > 0 else "❌"
                total_m = sum(1 for n,t in st.session_state.membros_cadastrados[lid].items() if t == "Membro") + 1
                pres_m = int(d_lid[d_lid['Tipo'].isin(['Membro', 'Liderança'])]['Célula'].sum())
                resumo_ob.append({"Célula": lid, "Líder": pres_l, "Freq.": f"{pres_m}/{total_m}"})
            st.table(pd.DataFrame(resumo_ob))
