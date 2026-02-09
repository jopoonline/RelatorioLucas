import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta, datetime
import time 
from streamlit_gsheets import GSheetsConnection

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

        def padronizar(df):
            df['Data_Obj'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
            df['Data_Ref'] = df['Data_Obj'].dt.strftime('%Y-%m-%d')
            df['MesNum'] = df['Data_Obj'].dt.month
            return df

        df_p = padronizar(df_p)
        df_v = padronizar(df_v)
        
        for col in ['Célula', 'Culto']: df_p[col] = pd.to_numeric(df_p[col], errors='coerce').fillna(0).astype(int)
        for col in ['Vis_Celula', 'Vis_Culto']: df_v[col] = pd.to_numeric(df_v[col], errors='coerce').fillna(0).astype(int)

        m_dict = {}
        if df_m is not None and not df_m.empty:
            for _, row in df_m.iterrows():
                l = row.get('Líder')
                if l and l not in m_dict: m_dict[l] = {}
                if l and row.get('Nome') != "LIDER_INICIAL": m_dict[l][row['Nome']] = row.get('Tipo', 'Membro')
        return df_p.dropna(subset=['Data_Obj']), df_v.dropna(subset=['Data_Obj']), m_dict
    except Exception as e:
        st.error(f"Erro ao carregar: {e}")
        return pd.DataFrame(), pd.DataFrame(), {}

def salvar_seguro(worksheet, df):
    try:
        df_save = df.copy()
        cols_limpar = ['Data_Obj', 'Data_Ref', 'MesNum']
        df_save = df_save.drop(columns=[c for c in cols_limpar if c in df_save.columns])
        if 'Data' in df_save.columns: df_save['Data'] = df_save['Data'].astype(str)
        conn.update(spreadsheet=URL_PLANILHA, worksheet=worksheet, data=df_save)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}"); return False

# --- 3. INICIALIZAÇÃO ---
db_p, db_v, m_dict = carregar_dados()
st.session_state.db = db_p
st.session_state.db_visitantes = db_v
st.session_state.membros_cadastrados = m_dict

# --- 4. ESTILO ---
st.markdown("""<style>
    .stApp { background-color: #0F172A; color: #F8FAFC; } 
    .metric-box { background: #1E293B; padding: 15px; border-radius: 10px; border-top: 4px solid #0284C7; text-align: center; margin-bottom: 10px; } 
    .metric-value { font-size: 24px; font-weight: 800; color: #38BDF8; display: block; }
    /* Ajuste para forçar colunas lado a lado no mobile */
    [data-testid="column"] { min-width: 0px !important; }
</style>""", unsafe_allow_html=True)

MESES_NOMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MESES_MAP = {n: i+1 for i, n in enumerate(MESES_NOMES)}

st.title("Lucas e Rosana")
tab_dash, tab_lanc, tab_gestao, tab_ob = st.tabs(["📊 Dados", "📝 Lançar", "⚙️ Gestão", "📋 Relatórios"])

# --- ABA DASHBOARD ---
with tab_dash:
    if st.button("🔄 Sincronizar"): st.cache_data.clear(); st.rerun()
    if not st.session_state.db.empty:
        lids_atuais = sorted(list(st.session_state.membros_cadastrados.keys()))
        lids_f = st.multiselect("Filtrar Células:", lids_atuais, default=lids_atuais)
        datas_u = sorted(st.session_state.db['Data_Ref'].unique(), reverse=True)
        if len(datas_u) >= 2:
            st.subheader("⚠️ Alertas de Frequência")
            d1, d2 = datas_u[0], datas_u[1]
            for lid in lids_f:
                v1 = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data_Ref']==d1)&(st.session_state.db_visitantes['Líder']==lid)]['Vis_Celula'].sum()
                v2 = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data_Ref']==d2)&(st.session_state.db_visitantes['Líder']==lid)]['Vis_Celula'].sum()
                if v1 == 0 and v2 == 0: st.error(f"🚩 **{lid}**: Sem visitantes.")
                for n, t in st.session_state.membros_cadastrados.get(lid, {}).items():
                    p1 = st.session_state.db[(st.session_state.db['Data_Ref']==d1)&(st.session_state.db['Líder']==lid)&(st.session_state.db['Nome']==n)]['Célula'].sum()
                    p2 = st.session_state.db[(st.session_state.db['Data_Ref']==d2)&(st.session_state.db['Líder']==lid)&(st.session_state.db['Nome']==n)]['Célula'].sum()
                    if p1 == 0 and p2 == 0: st.error(f"👤 **{n}** ({lid}): Ausente.")
        st.divider()
        m_s = st.selectbox("Mês de Análise:", MESES_NOMES, index=datetime.now().month-1)
        df_m = st.session_state.db[st.session_state.db['MesNum']==MESES_MAP[m_s]]
        if not df_m.empty:
            d_m = sorted(df_m['Data_Ref'].unique(), reverse=True)
            s_r = st.selectbox("Semana Selecionada:", d_m, format_func=lambda x: datetime.strptime(x, '%Y-%m-%d').strftime('%d/%m/%Y'))
            df_s = df_m[(df_m['Data_Ref']==s_r) & (df_m['Líder'].isin(lids_f))]
            dv_s = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data_Ref']==s_r) & (st.session_state.db_visitantes['Líder'].isin(lids_f))]
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            def get_card_val(tipo, modo):
                if tipo == "M":
                    total = sum([1 for l in lids_f for n, t in st.session_state.membros_cadastrados.get(l, {}).items() if t == "Membro"]) + len(lids_f)
                    pres = int(df_s[df_s['Tipo'].isin(['Membro', 'Liderança'])][modo].sum())
                    return f"{pres}/{total}"
                elif tipo == "FA":
                    total = sum([1 for l in lids_f for n, t in st.session_state.membros_cadastrados.get(l, {}).items() if t == "FA"])
                    pres = int(df_s[df_s['Tipo'] == "FA"][modo].sum())
                    return f"{pres}/{total}"
                else: return str(int(dv_s['Vis_Celula' if modo == 'Célula' else 'Vis_Culto'].sum()) if not dv_s.empty else 0)
            c1.markdown(f'<div class="metric-box">Mem. Célula<br><span class="metric-value">{get_card_val("M","Célula")}</span></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-box">FA Célula<br><span class="metric-value">{get_card_val("FA","Célula")}</span></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-box">Vis. Célula<br><span class="metric-value">{get_card_val("V","Célula")}</span></div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="metric-box">Mem. Culto<br><span class="metric-value">{get_card_val("M","Culto")}</span></div>', unsafe_allow_html=True)
            c5.markdown(f'<div class="metric-box">FA Culto<br><span class="metric-value">{get_card_val("FA","Culto")}</span></div>', unsafe_allow_html=True)
            c6.markdown(f'<div class="metric-box">Vis. Culto<br><span class="metric-value">{get_card_val("V","Culto")}</span></div>', unsafe_allow_html=True)
            cg1, cg2 = st.columns(2)
            for col, modo, k, tit in zip([cg1, cg2], ['Célula', 'Culto'], ['chart_cel', 'chart_cul'], ["evolução semanal celula", "evolução semanal culto"]):
                col.write(f"### 📈 {tit}")
                g_d = df_m[df_m['Líder'].isin(lids_f)].groupby('Data_Ref')[modo].sum().reset_index()
                g_v = st.session_state.db_visitantes[(st.session_state.db_visitantes['MesNum']==MESES_MAP[m_s])&(st.session_state.db_visitantes['Líder'].isin(lids_f))].groupby('Data_Ref')['Vis_Celula' if modo=='Célula' else 'Vis_Culto'].sum().reset_index()
                mrg = pd.merge(g_d, g_v, on='Data_Ref', how='outer').fillna(0).sort_values('Data_Ref')
                mrg['D'] = mrg['Data_Ref'].apply(lambda x: datetime.strptime(x, '%Y-%m-%d').strftime('%d/%m'))
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=mrg['D'], y=mrg[modo], name='Membros+FA', mode='lines+markers+text', text=mrg[modo], textposition="top center"))
                fig.add_trace(go.Scatter(x=mrg['D'], y=mrg.iloc[:,2], name='Visitantes', mode='lines+markers+text', text=mrg.iloc[:,2], textposition="bottom center"))
                fig.update_layout(height=300, margin=dict(l=0,r=0,t=30,b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                col.plotly_chart(fig, use_container_width=True, key=k)

            st.divider()
            st.subheader(f"📊 Performance: {m_s} e Meses Anteriores")
            idx_analise = MESES_MAP[m_s]
            indices_comparar = [idx_analise - 2, idx_analise - 1, idx_analise]
            dados_comp = []
            for idx in indices_comparar:
                if idx > 0:
                    nome_m = MESES_NOMES[idx-1]
                    d_mes = st.session_state.db[(st.session_state.db['MesNum']==idx) & (st.session_state.db['Líder'].isin(lids_f))]
                    v_mes = st.session_state.db_visitantes[(st.session_state.db_visitantes['MesNum']==idx) & (st.session_state.db_visitantes['Líder'].isin(lids_f))]
                    val_fa = int(d_mes[d_mes['Tipo']=="FA"]['Célula'].sum())
                    val_mem = int(d_mes[d_mes['Tipo'].isin(['Membro','Liderança'])]['Célula'].sum())
                    val_vis = int(v_mes['Vis_Celula'].sum())
                    dados_comp.append({"Mês": nome_m, "Métrica": "Membro + FA", "Valor": val_mem + val_fa})
                    dados_comp.append({"Mês": nome_m, "Métrica": "Visitante", "Valor": val_vis})
                    dados_comp.append({"Mês": nome_m, "Métrica": "Total Geral", "Valor": val_mem + val_fa + val_vis})
            if dados_comp:
                df_barras = pd.DataFrame(dados_comp)
                fig_bar = px.bar(df_barras, x="Mês", y="Valor", color="Métrica", barmode="group", text_auto=True, 
                                 color_discrete_map={"Membro + FA": "#38BDF8", "Visitante": "#0284C7", "Total Geral": "#F8FAFC"}, height=400)
                fig_bar.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color="#F8FAFC", 
                                     legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5))
                st.plotly_chart(fig_bar, use_container_width=True)

# --- ABA LANÇAR (OTIMIZADA PARA MOBILE) ---
with tab_lanc:
    if st.session_state.membros_cadastrados:
        l_m = st.selectbox("Mês Lançar", MESES_NOMES, index=datetime.now().month-1)
        c_dt, c_cl = st.columns(2)
        datas_s = [date(2026, MESES_MAP[l_m], d) for d in range(1, 32) if (date(2026, MESES_MAP[l_m], 1) + timedelta(days=d-1)).month == MESES_MAP[l_m] and (date(2026, MESES_MAP[l_m], 1) + timedelta(days=d-1)).weekday() == 5]
        d_l = c_dt.selectbox("Sábado", datas_s, format_func=lambda x: x.strftime('%d/%m'))
        l_l = c_cl.selectbox("Sua Célula", sorted(st.session_state.membros_cadastrados.keys()))
        
        st.divider()
        # Cabeçalho compacto com ícones
        h1, h2, h3 = st.columns([3, 1, 1])
        h1.caption("👤 NOME")
        h2.caption("🏠 CEL")
        h3.caption("⛪ CUL")

        novos = []
        def criar_linha_compacta(nome, tipo, chave):
            # Colunas com proporção fixa para não quebrar no mobile
            c_nome, c_cel, c_cul = st.columns([3, 1, 1])
            
            # Coluna 1: Nome
            c_nome.markdown(f"**{nome}**")
            
            # Coluna 2: Célula (Checkbox invisível com ícone)
            p_ce = c_cel.checkbox(" ", key=f"ce_{chave}", value=(tipo == "Liderança"), label_visibility="collapsed")
            
            # Coluna 3: Culto (Checkbox invisível com ícone)
            p_cu = c_cul.checkbox(" ", key=f"cu_{chave}", value=(tipo == "Liderança"), label_visibility="collapsed")
            
            return {"Data": d_l.strftime('%d/%m/%Y'), "Líder": l_l, "Nome": nome, "Tipo": tipo, "Célula": 1 if p_ce else 0, "Culto": 1 if p_cu else 0}

        # Listagem
        novos.append(criar_linha_compacta(l_l, "Liderança", "lider_row"))
        for n, t in st.session_state.membros_cadastrados.get(l_l, {}).items():
            novos.append(criar_linha_compacta(n, t, n))
        
        st.divider()
        st.write("✨ **Visitantes**")
        v_c1, v_c2 = st.columns(2)
        vce = v_c1.number_input("🏠 Célula", 0)
        vcu = v_c2.number_input("⛪ Culto", 0)
        
        if st.button("💾 SALVAR LANÇAMENTO", use_container_width=True, type="primary"):
            dt_ref = d_l.strftime('%d/%m/%Y')
            dfp = pd.concat([st.session_state.db[~((st.session_state.db['Data']==dt_ref)&(st.session_state.db['Líder']==l_l))], pd.DataFrame(novos)])
            dfv = pd.concat([st.session_state.db_visitantes[~((st.session_state.db_visitantes['Data']==dt_ref)&(st.session_state.db_visitantes['Líder']==l_l))], pd.DataFrame([{"Data": dt_ref, "Líder": l_l, "Vis_Celula": vce, "Vis_Culto": vcu}])])
            if salvar_seguro("Presencas", dfp) and salvar_seguro("Visitantes", dfv): 
                st.success("Salvo!")
                time.sleep(1)
                st.cache_data.clear(); st.rerun()

# --- ABA GESTÃO ---
with tab_gestao:
    def sync_membros():
        lista = []
        for ld, ps in st.session_state.membros_cadastrados.items():
            if not ps: lista.append({"Líder":ld,"Nome":"LIDER_INICIAL","Tipo":"Liderança"})
            else: [lista.append({"Líder":ld,"Nome":n,"Tipo":t}) for n,t in ps.items()]
        salvar_seguro("Membros", pd.DataFrame(lista))
    st.subheader("➕ Adicionar Novo")
    c_add1, c_add2 = st.columns(2)
    with c_add1:
        nl = st.text_input("Novo Líder")
        if st.button("Criar Célula"):
            if nl and nl not in st.session_state.membros_cadastrados:
                st.session_state.membros_cadastrados[nl] = {}; sync_membros(); st.rerun()
    with c_add2:
        if st.session_state.membros_cadastrados:
            cs = st.selectbox("Célula:", sorted(st.session_state.membros_cadastrados.keys()))
            nm = st.text_input("Nome")
            tm = st.radio("Tipo", ["Membro", "FA"], horizontal=True)
            if st.button("Adicionar"):
                if nm: st.session_state.membros_cadastrados[cs][nm]=tm; sync_membros(); st.rerun()
    st.divider()
    st.subheader("🗑️ Gerenciar")
    if st.session_state.membros_cadastrados:
        cel_edit = st.selectbox("Editar Célula:", sorted(st.session_state.membros_cadastrados.keys()))
        membros_da_cel = st.session_state.membros_cadastrados.get(cel_edit, {})
        for nome, tipo in list(membros_da_cel.items()):
            c_n, c_t, c_b1, c_b2 = st.columns([3, 2, 3, 1])
            c_n.write(nome); c_t.write(f"({tipo})")
            novo_t = "FA" if tipo == "Membro" else "Membro"
            if c_b1.button(f"Para {novo_t}", key=f"t_{nome}"):
                st.session_state.membros_cadastrados[cel_edit][nome] = novo_t; sync_membros(); st.rerun()
            if c_b2.button("❌", key=f"x_{nome}"):
                del st.session_state.membros_cadastrados[cel_edit][nome]; sync_membros(); st.rerun()

# --- ABA RELATÓRIO OB ---
with tab_ob:
    st.header("📋 Relatórios")
    m_ob = st.selectbox("Mês:", MESES_NOMES, index=datetime.now().month-1, key="ob_m")
    df_ob = st.session_state.db[st.session_state.db['MesNum'] == MESES_MAP[m_ob]]
    df_v_ob = st.session_state.db_visitantes[st.session_state.db_visitantes['MesNum'] == MESES_MAP[m_ob]]
    if not df_ob.empty:
        st.subheader("📊 Totais")
        res_sem = []
        for d_r in sorted(df_ob['Data_Ref'].unique()):
            d_f = datetime.strptime(d_r, '%Y-%m-%d').strftime('%d/%m')
            df_s = df_ob[df_ob['Data_Ref'] == d_r]
            m_ce = df_s[df_s['Tipo'].isin(['Membro','Liderança'])]['Célula'].sum()
            m_cu = df_s[df_s['Tipo'].isin(['Membro','Liderança'])]['Culto'].sum()
            f_ce = df_s[df_s['Tipo']=="FA"]['Célula'].sum()
            v_ce = df_v_ob[df_v_ob['Data_Ref']==d_r]['Vis_Celula'].sum()
            res_sem.append({"Data": d_f, "Membros": f"{m_ce}/{m_cu}", "FA": f"{f_ce}", "Vis": f"{v_ce}"})
        st.table(pd.DataFrame(res_sem))
