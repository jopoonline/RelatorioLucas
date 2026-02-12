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
    .mobile-row { text-align: center; padding: 10px; margin-bottom: 5px; background: #1E293B; border-radius: 10px; }
    .name-text { font-size: 1.1rem; font-weight: bold; color: #38BDF8; margin-bottom: 2px; }
    .type-text { font-size: 0.75rem; color: #94A3B8; margin-bottom: 8px; }
</style>""", unsafe_allow_html=True)

MESES_NOMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MESES_MAP = {n: i+1 for i, n in enumerate(MESES_NOMES)}

st.title("Lucas e Rosana")

# --- 5. CONTROLE DE ACESSO ---
st.sidebar.title("🔐 Área Restrita")
acesso_admin = st.sidebar.text_input("Senha de Gestão:", type="password")
SENHA_CORRETA = "Videira@1020"

# Lógica das Abas
if acesso_admin == SENHA_CORRETA:
    tab_dash, tab_lanc, tab_gestao, tab_ob = st.tabs(["📊 Dados Célula e Culto", "📝 Preencher Relatorio Lider", "⚙️ GESTÃO Células", "📋 RELATÓRIO OB e Chamada"])
else:
    # Se não tem senha, cria apenas uma aba (o retorno de st.tabs é uma lista)
    tab_lanc = st.tabs(["📝 Preencher Relatorio Lider"])[0]
    tab_dash, tab_gestao, tab_ob = None, None, None
    if acesso_admin != "":
        st.sidebar.error("Senha incorreta!")

# --- CONTEÚDO DAS ABAS ---

# --- ABA DASHBOARD ---
if tab_dash:
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
                    if v1 == 0 and v2 == 0: st.error(f"🚩 **{lid}**: Sem visitantes nas últimas 2 semanas.")
                    for n, t in st.session_state.membros_cadastrados.get(lid, {}).items():
                        p1 = st.session_state.db[(st.session_state.db['Data_Ref']==d1)&(st.session_state.db['Líder']==lid)&(st.session_state.db['Nome']==n)]['Célula'].sum()
                        p2 = st.session_state.db[(st.session_state.db['Data_Ref']==d2)&(st.session_state.db['Líder']==lid)&(st.session_state.db['Nome']==n)]['Célula'].sum()
                        if p1 == 0 and p2 == 0: st.error(f"👤 **{n}** ({lid}): Ausente nas últimas 2 reuniões.")
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

# --- ABA LANÇAR ---
with tab_lanc:
    if st.session_state.membros_cadastrados:
        l_m = st.selectbox("Mês Lançar", MESES_NOMES, index=datetime.now().month-1)
        col_data, col_cel = st.columns(2)
        with col_data:
            datas_s = [date(2026, MESES_MAP[l_m], d) for d in range(1, 32) if (date(2026, MESES_MAP[l_m], 1) + timedelta(days=d-1)).month == MESES_MAP[l_m] and (date(2026, MESES_MAP[l_m], 1) + timedelta(days=d-1)).weekday() == 5]
            d_l = st.selectbox("Sábado", datas_s, format_func=lambda x: x.strftime('%d/%m'))
        with col_cel:
            l_l = st.selectbox("Sua Célula", sorted(st.session_state.membros_cadastrados.keys()))
        
        st.divider()
        if "presencas_bt" not in st.session_state: st.session_state.presencas_bt = {}

        def criar_linha_mobile(nome, tipo):
            k_cel = f"bt_cel_{nome}"
            k_cul = f"bt_cul_{nome}"
            if k_cel not in st.session_state.presencas_bt: st.session_state.presencas_bt[k_cel] = (tipo == "Liderança")
            if k_cul not in st.session_state.presencas_bt: st.session_state.presencas_bt[k_cul] = (tipo == "Liderança")

            st.markdown(f'''<div class="mobile-row">
                <div class="name-text">{nome}</div>
                <div class="type-text">({tipo})</div>
            </div>''', unsafe_allow_html=True)
            
            b1, b2, b3, b4 = st.columns([1, 2, 2, 1])
            label_cel = "🏠 ✅" if st.session_state.presencas_bt[k_cel] else "🏠 ❌"
            if b2.button(label_cel, key=f"btn_{k_cel}", use_container_width=True):
                st.session_state.presencas_bt[k_cel] = not st.session_state.presencas_bt[k_cel]
                st.rerun()

            label_cul = "⛪ ✅" if st.session_state.presencas_bt[k_cul] else "⛪ ❌"
            if b3.button(label_cul, key=f"btn_{k_cul}", use_container_width=True):
                st.session_state.presencas_bt[k_cul] = not st.session_state.presencas_bt[k_cul]
                st.rerun()
            st.markdown("---")

        criar_linha_mobile(l_l, "Liderança")
        for n, t in st.session_state.membros_cadastrados.get(l_l, {}).items():
            criar_linha_mobile(n, t)

        st.divider()
        st.subheader("✨ Visitantes")
        col_v1, col_v2 = st.columns(2)
        vce = col_v1.number_input("🏠 Vis. Célula", 0)
        vcu = col_v2.number_input("⛪ Vis. Culto", 0)
        
        if st.button("💾 SALVAR LANÇAMENTO", use_container_width=True, type="primary"):
            novos = []
            novos.append({
                "Data": d_l.strftime('%d/%m/%Y'), "Líder": l_l, "Nome": l_l, "Tipo": "Liderança", 
                "Célula": 1 if st.session_state.presencas_bt[f"bt_cel_{l_l}"] else 0, 
                "Culto": 1 if st.session_state.presencas_bt[f"bt_cul_{l_l}"] else 0
            })
            for n, t in st.session_state.membros_cadastrados.get(l_l, {}).items():
                novos.append({
                    "Data": d_l.strftime('%d/%m/%Y'), "Líder": l_l, "Nome": n, "Tipo": t, 
                    "Célula": 1 if st.session_state.presencas_bt[f"bt_cel_{n}"] else 0, 
                    "Culto": 1 if st.session_state.presencas_bt[f"bt_cul_{n}"] else 0
                })
            
            dt_ref = d_l.strftime('%d/%m/%Y')
            dfp = pd.concat([st.session_state.db[~((st.session_state.db['Data']==dt_ref)&(st.session_state.db['Líder']==l_l))], pd.DataFrame(novos)])
            dfv = pd.concat([st.session_state.db_visitantes[~((st.session_state.db_visitantes['Data']==dt_ref)&(st.session_state.db_visitantes['Líder']==l_l))], pd.DataFrame([{"Data": dt_ref, "Líder": l_l, "Vis_Celula": vce, "Vis_Culto": vcu}])])
            
            if salvar_seguro("Presencas", dfp) and salvar_seguro("Visitantes", dfv): 
                st.success("Salvo com sucesso!")
                st.session_state.presencas_bt = {} 
                time.sleep(1)
                st.cache_data.clear(); st.rerun()

# --- ABA GESTÃO ---
if tab_gestao:
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
            nl = st.text_input("Novo Líder Externo")
            if st.button("Criar Célula"):
                if nl and nl not in st.session_state.membros_cadastrados:
                    st.session_state.membros_cadastrados[nl] = {}; sync_membros(); st.rerun()
        with c_add2:
            if st.session_state.membros_cadastrados:
                cs = st.selectbox("Célula para Membro:", sorted(st.session_state.membros_cadastrados.keys()))
                nm = st.text_input("Nome da Pessoa")
                tm = st.radio("Tipo Inicial", ["Membro", "FA"], horizontal=True)
                if st.button("Adicionar Pessoa"):
                    if nm: st.session_state.membros_cadastrados[cs][nm]=tm; sync_membros(); st.rerun()
        st.divider()
        st.subheader("🚀 Multiplicação e Transferência")
        if st.session_state.membros_cadastrados:
            cel_origem = st.selectbox("Célula de Origem:", sorted(st.session_state.membros_cadastrados.keys()), key="orig")
            membros_orig = list(st.session_state.membros_cadastrados[cel_origem].keys())
            if membros_orig:
                membro_transf = st.selectbox("Selecionar Pessoa para Mover/Promover:", membros_orig)
                tipo_membro = st.session_state.membros_cadastrados[cel_origem][membro_transf]
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    if st.button(f"🌟 Tornar Líder (Nova Célula: {membro_transf})"):
                        del st.session_state.membros_cadastrados[cel_origem][membro_transf]
                        st.session_state.membros_cadastrados[membro_transf] = {}
                        sync_membros(); st.rerun()
                with col_t2:
                    cel_dest = [c for c in st.session_state.membros_cadastrados.keys() if c != cel_origem]
                    if cel_dest:
                        cel_destino = st.selectbox("Transferir para Célula Existente:", cel_dest)
                        if st.button("Confirmar Transferência"):
                            st.session_state.membros_cadastrados[cel_destino][membro_transf] = tipo_membro
                            del st.session_state.membros_cadastrados[cel_origem][membro_transf]
                            sync_membros(); st.rerun()
        st.divider()
        st.subheader("🗑️ Gerenciar e Excluir")
        if st.session_state.membros_cadastrados:
            cel_edit = st.selectbox("Selecione para Editar/Excluir:", sorted(st.session_state.membros_cadastrados.keys()))
            if st.button(f"Excluir Célula de {cel_edit}"):
                del st.session_state.membros_cadastrados[cel_edit]; sync_membros(); st.rerun()
            membros_da_cel = st.session_state.membros_cadastrados.get(cel_edit, {})
            for nome, tipo in list(membros_da_cel.items()):
                c_n, c_t, c_b1, c_b2 = st.columns([3, 2, 3, 2])
                c_n.write(nome); c_t.write(f"({tipo})")
                novo_t = "FA" if tipo == "Membro" else "Membro"
                if c_b1.button(f"Mudar para {novo_t}", key=f"t_{nome}"):
                    st.session_state.membros_cadastrados[cel_edit][nome] = novo_t; sync_membros(); st.rerun()
                if c_b2.button("❌", key=f"x_{nome}"):
                    del st.session_state.membros_cadastrados[cel_edit][nome]; sync_membros(); st.rerun()

# --- ABA RELATÓRIO OB ---
if tab_ob:
    with tab_ob:
        st.header("📋 Relatório OB")
        m_ob = st.selectbox("Mês OB:", MESES_NOMES, index=datetime.now().month-1, key="ob_m_final")
        df_ob = st.session_state.db[st.session_state.db['MesNum'] == MESES_MAP[m_ob]]
        df_v_ob = st.session_state.db_visitantes[st.session_state.db_visitantes['MesNum'] == MESES_MAP[m_ob]]
        if not df_ob.empty:
            st.subheader("📊 Totais Semanais da Rede")
            res_sem = []
            for d_r in sorted(df_ob['Data_Ref'].unique()):
                d_f = datetime.strptime(d_r, '%Y-%m-%d').strftime('%d/%m')
                df_s = df_ob[df_ob['Data_Ref'] == d_r]
                m_ce = df_s[df_s['Tipo'].isin(['Membro','Liderança'])]['Célula'].sum()
                m_cu = df_s[df_s['Tipo'].isin(['Membro','Liderança'])]['Culto'].sum()
                f_ce, f_cu = df_s[df_s['Tipo']=="FA"]['Célula'].sum(), df_s[df_s['Tipo']=="FA"]['Culto'].sum()
                v_ce, v_cu = df_v_ob[df_v_ob['Data_Ref']==d_r]['Vis_Celula'].sum(), df_v_ob[df_v_ob['Data_Ref']==d_r]['Vis_Culto'].sum()
                res_sem.append({"Data": d_f, "Membros": f"{m_ce}/{m_cu}", "FA": f"{f_ce}/{f_cu}", "Vis": f"{v_ce}/{v_cu}", "Total": f"{m_ce+f_ce+v_ce}/{m_cu+f_cu+v_cu}"})
            st.table(pd.DataFrame(res_sem))
            st.divider(); st.subheader("🕵️ Chamada Detalhada (Célula | Culto)")
            cel_sel_ob = st.selectbox("Selecionar Célula:", sorted(st.session_state.membros_cadastrados.keys()), key="ob_c_final")
            m_cel = [{"Nome": cel_sel_ob, "Tipo": "Liderança"}] + [{"Nome": n, "Tipo": t} for n, t in st.session_state.membros_cadastrados.get(cel_sel_ob, {}).items()]
            d_mes = sorted(df_ob['Data_Ref'].unique()); cham_d = []
            for p in m_cel:
                ln = {"Pessoa": f"{p['Nome']} ({p['Tipo']})"}
                for d in d_mes:
                    df_c = df_ob[(df_ob['Data_Ref']==d)&(df_ob['Nome']==p['Nome'])&(df_ob['Líder']==cel_sel_ob)]
                    if not df_c.empty:
                        p_ce = "✅" if df_c['Célula'].sum() > 0 else "❌"
                        p_cu = "✅" if df_c['Culto'].sum() > 0 else "❌"
                        ln[datetime.strptime(d, '%Y-%m-%d').strftime('%d/%m')] = f"{p_ce} | {p_cu}"
                    else: ln[datetime.strptime(d, '%Y-%m-%d').strftime('%d/%m')] = "❌ | ❌"
                cham_d.append(ln)
            st.dataframe(pd.DataFrame(cham_d), use_container_width=True, hide_index=True)
