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

# --- 3. INICIALIZAÇÃO ---
db_p, db_v, m_dict = carregar_dados()
st.session_state.db = db_p
st.session_state.db_visitantes = db_v
st.session_state.membros_cadastrados = m_dict

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
        st.error(f"Erro: {e}"); return False

# --- 4. ESTILO ---
st.markdown("""<style>.stApp { background-color: #0F172A; color: #F8FAFC; } .metric-box { background: #1E293B; padding: 15px; border-radius: 10px; border-top: 4px solid #0284C7; text-align: center; margin-bottom: 10px; } .metric-value { font-size: 24px; font-weight: 800; color: #38BDF8; display: block; }</style>""", unsafe_allow_html=True)

MESES_NOMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MESES_MAP = {n: i+1 for i, n in enumerate(MESES_NOMES)}

st.title("🛡️ DISTRITO PRO 2026")
tab_dash, tab_lanc, tab_gestao, tab_ob = st.tabs(["📊 DASHBOARDS", "📝 LANÇAR", "⚙️ GESTÃO", "📋 RELATÓRIO OB"])

# --- TAB DASHBOARD ---
with tab_dash:
    if st.button("🔄 Sincronizar"): st.cache_data.clear(); st.rerun()
    if not st.session_state.db.empty:
        lids_atuais = sorted(list(st.session_state.membros_cadastrados.keys()))
        lids_f = st.multiselect("Células:", lids_atuais, default=lids_atuais)
        
        # Alertas
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
        m_s = st.selectbox("Mês:", MESES_NOMES, index=datetime.now().month-1)
        df_m = st.session_state.db[st.session_state.db['MesNum']==MESES_MAP[m_s]]
        if not df_m.empty:
            d_m = sorted(df_m['Data_Ref'].unique(), reverse=True)
            s_r = st.selectbox("Semana:", d_m, format_func=lambda x: datetime.strptime(x, '%Y-%m-%d').strftime('%d/%m/%Y'))
            df_s = df_m[(df_m['Data_Ref']==s_r) & (df_m['Líder'].isin(lids_f))]
            dv_s = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data_Ref']==s_r) & (st.session_state.db_visitantes['Líder'].isin(lids_f))]
            
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            def card(tipo, modo):
                if tipo=="M": return int(df_s[df_s['Tipo'].isin(['Membro','Liderança'])][modo].sum())
                if tipo=="V": return int(dv_s['Vis_Celula' if modo=='Célula' else 'Vis_Culto'].sum() if not dv_s.empty else 0)
                return int(df_s[df_s['Tipo']=="FA"][modo].sum())
            c1.markdown(f'<div class="metric-box">Mem. Célula<br><span class="metric-value">{card("M","Célula")}</span></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-box">FA Célula<br><span class="metric-value">{card("FA","Célula")}</span></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-box">Vis. Célula<br><span class="metric-value">{card("V","Célula")}</span></div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="metric-box">Mem. Culto<br><span class="metric-value">{card("M","Culto")}</span></div>', unsafe_allow_html=True)
            c5.markdown(f'<div class="metric-box">FA Culto<br><span class="metric-value">{card("FA","Culto")}</span></div>', unsafe_allow_html=True)
            c6.markdown(f'<div class="metric-box">Vis. Culto<br><span class="metric-value">{card("V","Culto")}</span></div>', unsafe_allow_html=True)
            
            st.write("### 📈 Evolução Semanal")
            cg1, cg2 = st.columns(2)
            # RESOLUÇÃO DO ERRO: Adicionado 'key' único em plotly_chart
            for col, modo, k in zip([cg1, cg2], ['Célula', 'Culto'], ['chart_cel', 'chart_cul']):
                g_d = df_m[df_m['Líder'].isin(lids_f)].groupby('Data_Ref')[modo].sum().reset_index()
                g_v = st.session_state.db_visitantes[(st.session_state.db_visitantes['MesNum']==MESES_MAP[m_s])&(st.session_state.db_visitantes['Líder'].isin(lids_f))].groupby('Data_Ref')['Vis_Celula' if modo=='Célula' else 'Vis_Culto'].sum().reset_index()
                mrg = pd.merge(g_d, g_v, on='Data_Ref', how='outer').fillna(0).sort_values('Data_Ref')
                mrg['D'] = mrg['Data_Ref'].apply(lambda x: datetime.strptime(x, '%Y-%m-%d').strftime('%d/%m'))
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=mrg['D'], y=mrg[modo], name='Membros+FA', mode='lines+markers+text', text=mrg[modo], textposition="top center"))
                fig.add_trace(go.Scatter(x=mrg['D'], y=mrg.iloc[:,2], name='Visitantes', mode='lines+markers+text', text=mrg.iloc[:,2], textposition="bottom center"))
                fig.update_layout(height=300, margin=dict(l=0,r=0,t=30,b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                col.plotly_chart(fig, use_container_width=True, key=k)

# --- TAB LANÇAR ---
with tab_lanc:
    if st.session_state.membros_cadastrados:
        l_m = st.selectbox("Mês Lançar", MESES_NOMES, index=datetime.now().month-1)
        datas_s = [date(2026, MESES_MAP[l_m], d) for d in range(1, 32) if (date(2026, MESES_MAP[l_m], 1) + timedelta(days=d-1)).month == MESES_MAP[l_m] and (date(2026, MESES_MAP[l_m], 1) + timedelta(days=d-1)).weekday() == 5]
        d_l = st.selectbox("Sábado", datas_s, format_func=lambda x: x.strftime('%d/%m'))
        l_l = st.selectbox("Sua Célula", sorted(st.session_state.membros_cadastrados.keys()))
        novos = []
        cn, ce, cu = st.columns([2,1,1])
        lpce = ce.checkbox("Célula", value=True, key="lpce")
        lpcu = cu.checkbox("Culto", value=True, key="lpcu")
        novos.append({"Data": d_l, "Líder": l_l, "Nome": l_l, "Tipo": "Liderança", "Célula": 1 if lpce else 0, "Culto": 1 if lpcu else 0})
        for n, t in st.session_state.membros_cadastrados.get(l_l, {}).items():
            cn, ce, cu = st.columns([2,1,1]); cn.write(f"{n} ({t})")
            pce, pcu = ce.checkbox("Célula", key=f"c_{n}"), cu.checkbox("Culto", key=f"u_{n}")
            novos.append({"Data": d_l, "Líder": l_l, "Nome": n, "Tipo": t, "Célula": 1 if pce else 0, "Culto": 1 if pcu else 0})
        vce, vcu = st.number_input("Vis. Célula", 0), st.number_input("Vis. Culto", 0)
        if st.button("💾 SALVAR LANÇAMENTO", use_container_width=True):
            dt = d_l.strftime('%Y-%m-%d')
            dfp = pd.concat([st.session_state.db[~((st.session_state.db['Data_Ref']==dt)&(st.session_state.db['Líder']==l_l))], pd.DataFrame(novos)])
            dfv = pd.concat([st.session_state.db_visitantes[~((st.session_state.db_visitantes['Data_Ref']==dt)&(st.session_state.db_visitantes['Líder']==l_l))], pd.DataFrame([{"Data": d_l, "Líder": l_l, "Vis_Celula": vce, "Vis_Culto": vcu}])])
            if salvar_seguro("Presencas", dfp) and salvar_seguro("Visitantes", dfv): st.cache_data.clear(); st.rerun()

# --- TAB GESTÃO ---
with tab_gestao:
    g1, g2 = st.columns(2)
    with g1:
        nl = st.text_input("Novo Líder")
        if st.button("Criar Célula"):
            if nl: st.session_state.membros_cadastrados[nl]={}; lista=[]; 
            for ld, ps in st.session_state.membros_cadastrados.items():
                if not ps: lista.append({"Líder":ld,"Nome":"LIDER_INICIAL","Tipo":"Liderança"})
                else: [lista.append({"Líder":ld,"Nome":n,"Tipo":t}) for n,t in ps.items()]
            salvar_seguro("Membros", pd.DataFrame(lista)); st.rerun()
    with g2:
        if st.session_state.membros_cadastrados:
            cs = st.selectbox("Célula para Membro:", sorted(st.session_state.membros_cadastrados.keys()))
            nm = st.text_input("Nome Pessoa")
            tm = st.radio("Tipo Pessoa", ["Membro", "FA"], horizontal=True)
            if st.button("Adicionar"):
                if nm: st.session_state.membros_cadastrados[cs][nm]=tm; lista=[];
                for ld, ps in st.session_state.membros_cadastrados.items():
                    if not ps: lista.append({"Líder":ld,"Nome":"LIDER_INICIAL","Tipo":"Liderança"})
                    else: [lista.append({"Líder":ld,"Nome":n,"Tipo":t}) for n,t in ps.items()]
                salvar_seguro("Membros", pd.DataFrame(lista)); st.rerun()

# --- TAB RELATÓRIO OB ---
with tab_ob:
    st.header("📋 Relatório Mensal OB")
    m_ob = st.selectbox("Mês OB:", MESES_NOMES, index=datetime.now().month-1)
    df_ob = st.session_state.db[st.session_state.db['MesNum'] == MESES_MAP[m_ob]]
    df_v_ob = st.session_state.db_visitantes[st.session_state.db_visitantes['MesNum'] == MESES_MAP[m_ob]]
    if not df_ob.empty:
        st.subheader("📊 Totais da Rede")
        res_sem = []
        for d_r in sorted(df_ob['Data_Ref'].unique()):
            d_fmt = datetime.strptime(d_r, '%Y-%m-%d').strftime('%d/%m')
            df_s = df_ob[df_ob['Data_Ref'] == d_r]
            m_ce = df_s[df_s['Tipo'].isin(['Membro','Liderança'])]['Célula'].sum()
            m_cu = df_s[df_s['Tipo'].isin(['Membro','Liderança'])]['Culto'].sum()
            fa_ce, fa_cu = df_s[df_s['Tipo']=="FA"]['Célula'].sum(), df_s[df_s['Tipo']=="FA"]['Culto'].sum()
            v_ce, v_cu = df_v_ob[df_v_ob['Data_Ref']==d_r]['Vis_Celula'].sum(), df_v_ob[df_v_ob['Data_Ref']==d_r]['Vis_Culto'].sum()
            res_sem.append({"Data": d_fmt, "Membros (Cel/Cul)": f"{m_ce}/{m_cu}", "FA": f"{fa_ce}/{fa_cu}", "Vis": f"{v_ce}/{v_cu}", "Total": f"{m_ce+fa_ce+v_ce}/{m_cu+fa_cu+v_cu}"})
        st.table(pd.DataFrame(res_sem))
        st.divider()
        st.subheader("🕵️ Chamada por Célula")
        cel_sel = st.selectbox("Ver Célula:", sorted(st.session_state.membros_cadastrados.keys()))
        m_cel = [{"Nome": cel_sel, "Tipo": "Liderança"}] + [{"Nome": n, "Tipo": t} for n, t in st.session_state.membros_cadastrados.get(cel_sel, {}).items()]
        d_mes = sorted(df_ob['Data_Ref'].unique()); cham_d = []
        for p in m_cel:
            ln = {"Pessoa": f"{p['Nome']} ({p['Tipo']})"}
            for d in d_mes:
                df_c = df_ob[(df_ob['Data_Ref']==d)&(df_ob['Nome']==p['Nome'])&(df_ob['Líder']==cel_sel)]
                ln[datetime.strptime(d, '%Y-%m-%d').strftime('%d/%m')] = "✅" if not df_c.empty and df_c['Célula'].sum()>0 else "❌"
            cham_d.append(ln)
        st.dataframe(pd.DataFrame(cham_d), use_container_width=True, hide_index=True)
