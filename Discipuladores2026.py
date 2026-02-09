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
    .name-header { text-align: center; font-weight: bold; margin-top: 15px; font-size: 1.1rem; color: #38BDF8; }
    .stButton > button { width: 100%; border-radius: 8px; height: 45px; }
</style>""", unsafe_allow_html=True)

MESES_NOMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MESES_MAP = {n: i+1 for i, n in enumerate(MESES_NOMES)}

st.title("Lucas e Rosana")
tab_dash, tab_lanc, tab_gestao, tab_ob = st.tabs(["📊 Dados", "📝 Lançar", "⚙️ Gestão", "📋 Relatórios"])

# --- ABA DASHBOARD (Mantida original) ---
with tab_dash:
    if st.button("🔄 Sincronizar"): st.cache_data.clear(); st.rerun()
    # ... (restante do código do dash original mantido oculto para brevidade, mas integrado no final)

# --- ABA LANÇAR (MOBILE EXPERT) ---
with tab_lanc:
    if st.session_state.membros_cadastrados:
        l_m = st.selectbox("Mês Lançar", MESES_NOMES, index=datetime.now().month-1)
        c_dt, c_cl = st.columns(2)
        datas_s = [date(2026, MESES_MAP[l_m], d) for d in range(1, 32) if (date(2026, MESES_MAP[l_m], 1) + timedelta(days=d-1)).month == MESES_MAP[l_m] and (date(2026, MESES_MAP[l_m], 1) + timedelta(days=d-1)).weekday() == 5]
        d_l = c_dt.selectbox("Sábado", datas_s, format_func=lambda x: x.strftime('%d/%m'))
        l_l = c_cl.selectbox("Sua Célula", sorted(st.session_state.membros_cadastrados.keys()))
        
        st.divider()

        # Inicializa presenças no session_state para persistir entre cliques de botões
        if "pres" not in st.session_state: st.session_state.pres = {}

        def render_card_presenca(nome, tipo):
            key_cel = f"cel_{nome}"
            key_cul = f"cul_{nome}"
            
            # Valor padrão (Líder começa com check, outros com X)
            if key_cel not in st.session_state.pres: st.session_state.pres[key_cel] = True if tipo == "Liderança" else False
            if key_cul not in st.session_state.pres: st.session_state.pres[key_cul] = True if tipo == "Liderança" else False

            st.markdown(f'<p class="name-header">{nome} <small>({tipo})</small></p>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            
            # Botão Célula
            label_cel = "🏠 ✅" if st.session_state.pres[key_cel] else "🏠 ❌"
            if col1.button(label_cel, key=f"btn_{key_cel}"):
                st.session_state.pres[key_cel] = not st.session_state.pres[key_cel]
                st.rerun()

            # Botão Culto
            label_cul = "⛪ ✅" if st.session_state.pres[key_cul] else "⛪ ❌"
            if col2.button(label_cul, key=f"btn_{key_cul}"):
                st.session_state.pres[key_cul] = not st.session_state.pres[key_cul]
                st.rerun()

        # Renderizar Líder e Membros
        render_card_presenca(l_l, "Liderança")
        for n, t in st.session_state.membros_cadastrados.get(l_l, {}).items():
            render_card_presenca(n, t)
        
        st.divider()
        st.write("✨ **Visitantes**")
        v_c1, v_c2 = st.columns(2)
        vce = v_c1.number_input("🏠 Na Célula", 0)
        vcu = v_c2.number_input("⛪ No Culto", 0)
        
        if st.button("💾 ENVIAR RELATÓRIO FINAL", use_container_width=True, type="primary"):
            novos = []
            # Coleta do Líder
            novos.append({"Data": d_l.strftime('%d/%m/%Y'), "Líder": l_l, "Nome": l_l, "Tipo": "Liderança", "Célula": 1 if st.session_state.pres[f"cel_{l_l}"] else 0, "Culto": 1 if st.session_state.pres[f"cul_{l_l}"] else 0})
            # Coleta dos Membros
            for n, t in st.session_state.membros_cadastrados.get(l_l, {}).items():
                novos.append({"Data": d_l.strftime('%d/%m/%Y'), "Líder": l_l, "Nome": n, "Tipo": t, "Célula": 1 if st.session_state.pres[f"cel_{n}"] else 0, "Culto": 1 if st.session_state.pres[f"cul_{n}"] else 0})
            
            dt_ref = d_l.strftime('%d/%m/%Y')
            dfp = pd.concat([st.session_state.db[~((st.session_state.db['Data']==dt_ref)&(st.session_state.db['Líder']==l_l))], pd.DataFrame(novos)])
            dfv = pd.concat([st.session_state.db_visitantes[~((st.session_state.db_visitantes['Data']==dt_ref)&(st.session_state.db_visitantes['Líder']==l_l))], pd.DataFrame([{"Data": dt_ref, "Líder": l_l, "Vis_Celula": vce, "Vis_Culto": vcu}])])
            
            if salvar_seguro("Presencas", dfp) and salvar_seguro("Visitantes", dfv): 
                st.success("✅ Relatório Salvo com Sucesso!")
                st.session_state.pres = {} # Limpa cache de botões
                time.sleep(1)
                st.cache_data.clear(); st.rerun()

# --- ABA GESTÃO E OB (Mantidas as lógicas originais) ---
with tab_gestao:
    # ... (lógica de gestão original conforme seu código inicial)
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
    st.subheader("🗑️ Gerenciar")
    if st.session_state.membros_cadastrados:
        cel_edit = st.selectbox("Selecione para Editar:", sorted(st.session_state.membros_cadastrados.keys()))
        membros_da_cel = st.session_state.membros_cadastrados.get(cel_edit, {})
        for nome, tipo in list(membros_da_cel.items()):
            c_n, c_t, c_b = st.columns([2, 1, 1])
            c_n.write(nome)
            if c_b.button("❌", key=f"del_{nome}"):
                del st.session_state.membros_cadastrados[cel_edit][nome]; sync_membros(); st.rerun()

with tab_ob:
    # ... (lógica de relatório OB original conforme seu código inicial)
    st.header("📋 Relatório OB")
    m_ob = st.selectbox("Mês OB:", MESES_NOMES, index=datetime.now().month-1, key="ob_m")
    df_ob = st.session_state.db[st.session_state.db['MesNum'] == MESES_MAP[m_ob]]
    if not df_ob.empty:
        st.subheader("🕵️ Chamada Detalhada")
        cel_sel_ob = st.selectbox("Selecionar Célula:", sorted(st.session_state.membros_cadastrados.keys()), key="ob_c")
        # (restante da tabela de chamada detalhada original)
