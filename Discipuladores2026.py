import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta, datetime
import time
import base64
import io
from PIL import Image, ImageOps
from urllib.parse import quote
from zoneinfo import ZoneInfo
from streamlit_gsheets import GSheetsConnection

# =====================================================================
# 1. CONFIGURAÇÃO  (nada mudou na conexão com o Google Sheets)
# =====================================================================
st.set_page_config(page_title=f"Deric Relatorio {datetime.now(ZoneInfo('America/Sao_Paulo')).year}", layout="wide", page_icon="⛪")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1Bb9wK8dwRYjOJ5leTKxT9VQ0Ib7z-aD5MXCHJX0hNXs/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# =====================================================================
# 2. FUNÇÕES DE DADOS  (idênticas às originais — mesmas abas e colunas)
# =====================================================================
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
            df['Ano'] = df['Data_Obj'].dt.year
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
        cols_limpar = ['Data_Obj', 'Data_Ref', 'MesNum', 'Ano']
        df_save = df_save.drop(columns=[c for c in cols_limpar if c in df_save.columns])
        if 'Data' in df_save.columns: df_save['Data'] = df_save['Data'].astype(str)
        conn.update(spreadsheet=URL_PLANILHA, worksheet=worksheet, data=df_save)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}"); return False


# ---------- FOTOS (aba "Fotos" da planilha: colunas Nome e Foto) ----------
ABA_FOTOS = "Fotos"
LADO_FOTO = 160          # a foto vira um quadrado de 160 x 160 pixels
LIMITE_CELULA = 40000    # o Google Sheets aceita até 50.000 caracteres por célula


@st.cache_data(ttl=300, show_spinner=False)
def carregar_fotos():
    """Devolve {nome: foto em base64}. Se a aba Fotos ainda não existir, devolve vazio."""
    try:
        df = conn.read(spreadsheet=URL_PLANILHA, worksheet=ABA_FOTOS, ttl=0)
        df = df.dropna(subset=["Nome", "Foto"])
        return {str(r["Nome"]).strip(): str(r["Foto"]).strip() for _, r in df.iterrows() if str(r["Foto"]).strip()}
    except Exception:
        return {}


def processar_foto(arquivo):
    """Gira conforme o celular, recorta em quadrado, reduz e comprime. Devolve (base64, tamanho em KB)."""
    img = Image.open(arquivo)
    img = ImageOps.exif_transpose(img).convert("RGB")
    img = ImageOps.fit(img, (LADO_FOTO, LADO_FOTO), method=Image.LANCZOS, centering=(0.5, 0.4))
    for qualidade in (82, 72, 62, 50, 40):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=qualidade, optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode()
        if len(b64) < LIMITE_CELULA:
            break
    return b64, len(buf.getvalue()) / 1024


def gravar_foto(nome, b64):
    """Grava (ou remove, se b64 for None) a foto de uma pessoa na aba Fotos. Não mexe em nenhuma outra aba."""
    try:
        atual = conn.read(spreadsheet=URL_PLANILHA, worksheet=ABA_FOTOS, ttl=0)
        atual = atual.dropna(how="all")
        aba_existe = True
    except Exception:
        atual = pd.DataFrame(columns=["Nome", "Foto"])
        aba_existe = False
    if "Nome" not in atual.columns or "Foto" not in atual.columns:
        atual = pd.DataFrame(columns=["Nome", "Foto"])
    atual = atual[["Nome", "Foto"]]
    atual = atual[atual["Nome"].astype(str).str.strip() != nome]
    if b64:
        atual = pd.concat([atual, pd.DataFrame([{"Nome": nome, "Foto": b64}])], ignore_index=True)
    try:
        if not aba_existe:
            planilha = conn.client._open_spreadsheet(spreadsheet=URL_PLANILHA)
            planilha.add_worksheet(title=ABA_FOTOS, rows=max(len(atual) + 1, 50), cols=2)
        conn.update(spreadsheet=URL_PLANILHA, worksheet=ABA_FOTOS, data=atual)
        carregar_fotos.clear()
        return True
    except Exception as e:
        st.error(f"Não foi possível salvar a foto: {e}")
        return False


# =====================================================================
# 3. INICIALIZAÇÃO
# =====================================================================
FUSO = ZoneInfo("America/Sao_Paulo")
ANO_ATUAL = datetime.now(FUSO).year
ANOS = list(range(2026, max(ANO_ATUAL, 2026) + 2))   # sempre oferece o ano seguinte (em 2026 já aparece 2027)

st.sidebar.markdown("### 📆 Ano dos relatórios")
ANO = st.sidebar.selectbox("Ano", ANOS, index=ANOS.index(max(ANO_ATUAL, 2026)), key="ano_view", label_visibility="collapsed")

db_p, db_v, m_dict = carregar_dados()
# Base completa: usada só para GRAVAR (nunca perde os outros anos)
st.session_state.db_full = db_p
st.session_state.db_visitantes_full = db_v
# Base do ano escolhido: usada para mostrar dashboards e relatórios
st.session_state.db = db_p[db_p['Ano'] == ANO] if 'Ano' in db_p.columns else db_p
st.session_state.db_visitantes = db_v[db_v['Ano'] == ANO] if 'Ano' in db_v.columns else db_v
st.session_state.membros_cadastrados = m_dict
FOTOS = carregar_fotos()

# =====================================================================
# 4. ESTILO (visual novo)
# =====================================================================
COR_FUNDO = "#080C18"
COR_CARD = "#111827"
COR_BORDA = "rgba(255,255,255,.08)"
COR_TEXTO = "#CBD3E6"
COR_SUAVE = "#8E99B5"
COR_PRIMARIA = "#22D3EE"   # Membros
COR_FA = "#818CF8"         # FA
COR_VIS = "#FBBF24"        # Visitantes
COR_OK = "#34D399"         # verde (bom)
COR_ALERTA = "#FB7185"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
html, body, .stApp, .stApp p, .stApp label, .stApp input, .stApp button, .stApp div { font-family: 'Plus Jakarta Sans', system-ui, -apple-system, 'Segoe UI', sans-serif; }
.stApp { background: radial-gradient(900px 500px at 100% -10%, rgba(129,140,248,.16) 0%, rgba(8,12,24,0) 60%), radial-gradient(900px 500px at 0% 0%, rgba(34,211,238,.12) 0%, rgba(8,12,24,0) 55%), #080C18; color: #E5E9F5; }
.stApp p, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4 { color: #E5E9F5; }
.block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1320px; }
[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }

/* ---------- Cabeçalho ---------- */
.hero { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; flex-wrap: wrap; padding: 26px 28px; border-radius: 24px; margin-bottom: 18px; border: 1px solid rgba(255,255,255,.08); background: linear-gradient(120deg, rgba(34,211,238,.16) 0%, rgba(129,140,248,.14) 55%, rgba(255,255,255,.03) 100%); }
.hero-marca { display: flex; align-items: center; gap: 18px; }
.hero-emoji { font-size: 46px; line-height: 1; }
.hero-kicker { color: #22D3EE; font-size: 12px; font-weight: 700; letter-spacing: 3px; text-transform: uppercase; }
.hero-titulo { color: #FFFFFF; font-size: clamp(28px, 5.5vw, 46px); font-weight: 800; letter-spacing: -1.2px; line-height: 1.05; margin-top: 4px; }
.hero-sub { color: #A5AEC6; font-size: 14px; margin-top: 6px; }
.hero-chip { display: inline-flex; align-items: center; gap: 8px; padding: 8px 14px; border-radius: 999px; background: rgba(8,12,24,.55); border: 1px solid rgba(255,255,255,.1); color: #CBD3E6; font-size: 12px; font-weight: 600; }
.ponto { width: 8px; height: 8px; border-radius: 50%; background: #34D399; box-shadow: 0 0 0 4px rgba(52,211,153,.18); display: inline-block; }

/* ---------- Abas em pílula ---------- */
.stTabs [role="tablist"] { gap: 4px; background: rgba(255,255,255,.04); padding: 5px; border-radius: 999px; border: 1px solid rgba(255,255,255,.08) !important; width: fit-content; max-width: 100%; box-shadow: none !important; overflow-x: auto; scrollbar-width: none; }
.stTabs [role="tab"] { border-radius: 999px !important; padding: 8px 20px; height: auto; background: transparent; border: 0 !important; box-shadow: none !important; white-space: nowrap; flex-shrink: 0; }
.stTabs [role="tab"] p { color: #A5AEC6; font-weight: 700; font-size: 14px; }
.stTabs [role="tab"][aria-selected="true"] { background: #FFFFFF !important; }
.stTabs [role="tab"][aria-selected="true"] p { color: #080C18; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none !important; }
.stTabs [role="tablist"]::before, .stTabs [role="tablist"]::after, .stTabs [role="tab"]::before, .stTabs [role="tab"]::after { display: none !important; }

/* ---------- Títulos de seção ---------- */
.sec { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin: 1.5rem 0 .8rem 0; font-size: 17px; font-weight: 700; color: #FFFFFF; }
.sec::before { content: ""; width: 4px; height: 18px; border-radius: 4px; background: linear-gradient(180deg, #22D3EE, #818CF8); }
.sec small { font-size: 12px; font-weight: 500; color: #8E99B5; }

/* ---------- Cartões de número ---------- */
.kpi { position: relative; overflow: hidden; background: rgba(255,255,255,.035); border: 1px solid rgba(255,255,255,.08); border-radius: 18px; padding: 14px 16px 14px 20px; margin-bottom: 12px; }
.kpi::before { content: ""; position: absolute; left: 0; top: 14px; bottom: 14px; width: 4px; border-radius: 0 4px 4px 0; background: var(--c, #22D3EE); }
.kpi-label { color: #8E99B5; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
.kpi-value { color: #FFFFFF; white-space: nowrap; font-size: clamp(20px, 2.1vw, 26px); font-weight: 800; line-height: 1.25; letter-spacing: -.5px; font-variant-numeric: tabular-nums; }
.kpi-sub { color: #8E99B5; font-size: 12px; min-height: 18px; }
.kpi-bar { height: 6px; background: rgba(8,12,24,.6); border-radius: 999px; margin-top: 8px; overflow: hidden; }
.kpi-bar > div { height: 100%; background: var(--c); border-radius: 999px; }

/* ---------- Avisos ---------- */
.alerta { background: rgba(251,113,133,.08); border: 1px solid rgba(251,113,133,.3); border-radius: 14px; padding: 9px 14px; margin-bottom: 6px; font-size: .9rem; color: #FECDD3; }
.alerta b { color: #FFFFFF; }
.ok { background: rgba(52,211,153,.08); border: 1px solid rgba(52,211,153,.3); border-radius: 14px; padding: 11px 16px; color: #A7F3D0; }

/* ---------- Pessoa (chamada) ---------- */
.pessoa { display: flex; align-items: center; gap: 12px; padding: 4px 0; }
.avatar { width: 42px; height: 42px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 800; color: #080C18; font-size: .95rem; flex-shrink: 0; }
img.avatar { object-fit: cover; padding: 0; background: #111827; }
.foto-previa { display: flex; align-items: center; gap: 16px; padding: 6px 0 10px 0; }
.foto-previa img { width: 96px; height: 96px; border-radius: 50%; object-fit: cover; border: 3px solid #22D3EE; }
.foto-previa div { color: #CBD3E6; font-size: .9rem; }
.pessoa-nome { font-weight: 700; color: #FFFFFF; font-size: 1.02rem; line-height: 1.15; }
.badge { display: inline-block; font-size: .7rem; font-weight: 700; padding: 2px 10px; border-radius: 999px; margin-top: 3px; }

/* ---------- Passos do relatório do líder ---------- */
.passo { display: flex; align-items: center; gap: 10px; font-weight: 700; color: #FFFFFF; font-size: 1.05rem; margin: 22px 0 10px 0; }
.passo span { width: 30px; height: 30px; border-radius: 50%; background: linear-gradient(135deg, #22D3EE, #818CF8); color: #080C18; display: flex; align-items: center; justify-content: center; font-size: .9rem; font-weight: 800; flex-shrink: 0; }
.placar { display: flex; gap: 10px; margin: 4px 0 12px 0; }
.placar > div { flex: 1; background: linear-gradient(135deg, rgba(34,211,238,.16), rgba(129,140,248,.14)); border: 1px solid rgba(34,211,238,.28); border-radius: 18px; padding: 12px; text-align: center; color: #CBD3E6; font-size: 1rem; }
.placar b { color: #FFFFFF; font-size: 1.7rem; font-weight: 800; }
.placar small { display: block; font-size: .75rem; margin-top: 2px; }

/* ---------- Contêineres, gráficos, expanders ---------- */
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 20px !important; border-color: rgba(255,255,255,.08) !important; background: rgba(255,255,255,.03); }
[data-testid="stExpander"] details { background: rgba(255,255,255,.03); border: 1px solid rgba(255,255,255,.08) !important; border-radius: 16px; }
[data-testid="stExpander"] summary p { color: #FFFFFF !important; }
section[data-testid="stSidebar"] { background: #0B1020; border-right: 1px solid rgba(255,255,255,.08); }

/* ---------- Botões ---------- */
.stButton > button { border-radius: 999px !important; font-weight: 800; min-height: 46px; transition: filter .15s; }
.stButton > button[kind="primary"], button[data-testid="stBaseButton-primary"] { background: linear-gradient(90deg, #22D3EE 0%, #818CF8 100%) !important; color: #080C18 !important; border: 0 !important; }
.stButton > button[kind="primary"] p, button[data-testid="stBaseButton-primary"] p { color: #080C18 !important; font-weight: 800; }
div.stButton > button[kind="primary"] { min-height: 58px; font-size: 1.1rem; }
button[data-testid="stBaseButton-secondary"] { background: rgba(255,255,255,.06) !important; color: #FFFFFF !important; border: 1px solid rgba(255,255,255,.1) !important; }
button[data-testid="stBaseButton-secondary"] p { color: #FFFFFF !important; }
.stButton > button:hover { filter: brightness(1.12); }

/* Botões Célula / Culto (seleção), grandes e redondos */
[data-testid="stElementContainer"]:has([data-testid="stButtonGroup"]) { width: 100% !important; }
[data-testid="stButtonGroup"], [data-testid="stButtonGroup"] [role="toolbar"] { width: 100% !important; max-width: none !important; flex: 1 1 auto !important; }
[data-testid="stButtonGroup"] [role="toolbar"] { display: flex; gap: 8px; flex-wrap: nowrap; }
[data-testid="stButtonGroup"] button { flex: 1 1 0 !important; max-width: none !important; min-height: 52px; border-radius: 999px !important; border: 1px solid rgba(255,255,255,.1) !important; background: rgba(8,12,24,.55) !important; color: #A5AEC6 !important; font-weight: 700; }
[data-testid="stButtonGroup"] button p { font-size: 1.05rem !important; color: inherit !important; font-weight: 700; }
[data-testid="stButtonGroup"] button[aria-pressed="true"], [data-testid="stButtonGroup"] button[data-selected="true"], [data-testid="stButtonGroup"] button[kind$="Active"] { background: linear-gradient(90deg, #22D3EE 0%, #818CF8 100%) !important; color: #080C18 !important; border-color: transparent !important; }

/* Atalhos lado a lado, também no celular */
.st-key-atalhos [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; flex-direction: row !important; gap: 8px !important; }
.st-key-atalhos [data-testid="stColumn"], .st-key-atalhos [data-testid="column"] { min-width: 0 !important; width: auto !important; flex: 1 1 0 !important; }
.st-key-atalhos button { min-height: 40px !important; padding: 0 6px !important; }
.st-key-atalhos button p { font-size: .9rem !important; }

/* Botão do WhatsApp */
[data-testid="stLinkButton"] a { background: #25D366 !important; color: #06260F !important; border: none !important; min-height: 54px; border-radius: 999px !important; font-weight: 800 !important; justify-content: center !important; text-align: center !important; }
[data-testid="stLinkButton"] a p { color: #06260F !important; font-size: 1.05rem !important; font-weight: 800 !important; }
.st-key-salvo_ok .ok { margin-bottom: 10px; }

/* ---------- Campos ---------- */
[data-testid="stWidgetLabel"] p, .stRadio label p, .stCheckbox label p, [data-testid="stCaptionContainer"] { color: #CBD3E6 !important; }
[data-testid="stSelectbox"] [role="group"], [data-testid="stMultiSelect"] [role="group"], [data-baseweb="select"] > div, [data-baseweb="input"] > div, [data-testid="stNumberInputContainer"] { background: rgba(8,12,24,.6) !important; border-color: rgba(255,255,255,.1) !important; border-radius: 14px !important; }
[data-testid="stSelectbox"] input, [data-testid="stSelectbox"] [role="group"] *, [data-baseweb="input"] input, [data-testid="stNumberInput"] input { color: #FFFFFF !important; background: transparent !important; }
[data-testid="stNumberInput"] input { font-size: 1.3rem; font-weight: 800; text-align: center; min-height: 48px; }
[data-testid="stNumberInput"] button { background: rgba(255,255,255,.06) !important; color: #FFFFFF !important; border: none !important; min-width: 44px; }
[data-baseweb="tag"] { background: rgba(34,211,238,.18) !important; border-radius: 999px !important; }
[data-baseweb="tag"] span { color: #FFFFFF !important; }

/* ---------- Aba Frequência ---------- */
.cel-card { background: rgba(255,255,255,.035); border: 1px solid rgba(255,255,255,.08); border-radius: 20px; padding: 16px 18px; margin-bottom: 12px; position: relative; overflow: hidden; }
.cel-card::before { content: ""; position: absolute; left: 0; top: 16px; bottom: 16px; width: 4px; border-radius: 0 4px 4px 0; background: var(--c); }
.cel-top { display: flex; align-items: center; gap: 10px; }
.cel-nome { font-weight: 700; color: #FFFFFF; font-size: 1rem; line-height: 1.15; }
.cel-nome small { display: block; color: #8E99B5; font-weight: 500; font-size: .72rem; }
.cel-meio { display: flex; align-items: flex-end; justify-content: space-between; margin: 10px 0 6px 0; }
.cel-big { font-size: 2rem; font-weight: 800; line-height: 1; letter-spacing: -.5px; }
.cel-lbl { font-size: .72rem; color: #8E99B5; margin-top: 3px; }
.cel-rodape { display: flex; gap: 12px; flex-wrap: wrap; font-size: .8rem; color: #8E99B5; border-top: 1px solid rgba(255,255,255,.08); padding-top: 8px; }
.cel-rodape b { color: #FFFFFF; }
.cel-vazio { color: #64748B; font-size: .85rem; padding: 16px 0 6px 0; }
.dest-tit { font-weight: 800; font-size: 1rem; }
.dest-sub { color: #8E99B5; font-size: .75rem; margin-bottom: 8px; }
.dest-linha { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,.08); color: #FFFFFF; font-size: .92rem; }
.dest-cel { font-size: .7rem; background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.08); color: #CBD3E6; padding: 2px 10px; border-radius: 999px; }
.dest-num { margin-left: auto; font-weight: 700; font-size: .82rem; }

/* ---------- Celular ---------- */
@media (max-width: 640px) {
    .hero { padding: 20px; border-radius: 20px; }
    .hero-emoji { font-size: 36px; }
    .block-container { padding-left: .8rem; padding-right: .8rem; }
    .stTabs [role="tab"] { padding: 7px 14px; }
    [data-testid="stVerticalBlockBorderWrapper"] { padding: 2px !important; }
}
</style>
""", unsafe_allow_html=True)

MESES_NOMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MESES_MAP = {n: i+1 for i, n in enumerate(MESES_NOMES)}

MES_PADRAO = datetime.now(FUSO).month - 1 if ANO == ANO_ATUAL else 0

CORES_TIPO = {"Liderança": "#34D399", "Membro": COR_PRIMARIA, "FA": COR_FA}


# ---------- Helpers visuais ----------
def secao(titulo, sub=""):
    st.markdown(f'<div class="sec">{titulo} <small>{sub}</small></div>', unsafe_allow_html=True)


def kpi(col, label, valor, cor, sub="", pct=None):
    barra = f'<div class="kpi-bar"><div style="width:{max(0, min(pct, 100)):.0f}%"></div></div>' if pct is not None else ""
    col.markdown(
        f'<div class="kpi" style="--c:{cor}"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{valor}</div><div class="kpi-sub">{sub}</div>{barra}</div>',
        unsafe_allow_html=True,
    )


def iniciais(nome):
    partes = str(nome).split()
    return (partes[0][0] + (partes[-1][0] if len(partes) > 1 else "")).upper() if partes else "?"


def avatar(nome, cor, tam=42, fonte=".95rem"):
    """Círculo com a foto da pessoa; sem foto, mostra as iniciais."""
    foto = FOTOS.get(str(nome).strip()) if MOSTRAR_FOTOS else None
    if foto:
        return (f'<img class="avatar" alt="{nome}" src="data:image/jpeg;base64,{foto}" '
                f'style="width:{tam}px;height:{tam}px;border:2px solid {cor}">')
    return (f'<div class="avatar" style="background:{cor};width:{tam}px;height:{tam}px;font-size:{fonte}">'
            f'{iniciais(nome)}</div>')


def estilo_grafico(fig, altura=320):
    fig.update_layout(
        height=altura, template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, sans-serif", color=COR_TEXTO, size=13),
        hoverlabel=dict(bgcolor="#0B1020", font_color="#FFFFFF", bordercolor="rgba(255,255,255,.15)"),
        margin=dict(l=12, r=12, t=34, b=8),
        legend=dict(orientation="h", yanchor="top", y=-0.14, xanchor="center", x=0.5, bgcolor="rgba(0,0,0,0)", title_text=""),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, linecolor=COR_BORDA)
    fig.update_yaxes(gridcolor="rgba(255,255,255,.06)", zeroline=False)
    return fig


# =====================================================================
# CABEÇALHO
# =====================================================================
st.markdown(
    '<div class="hero"><div class="hero-marca"><span class="hero-emoji">🛡️</span><div>'
    f'<div class="hero-kicker">Relatório {ANO}</div>'
    '<div class="hero-titulo">Deric e Nayara</div>'
    '<div class="hero-sub">Frequência de células e culto</div></div></div>'
    f'<div class="hero-chip"><span class="ponto"></span>Planilha lida às {datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%H:%M")}</div></div>',
    unsafe_allow_html=True,
)

# =====================================================================
# 5. CONTROLE DE ACESSO
# =====================================================================
st.sidebar.title("🔐 Área Restrita")
acesso_admin = st.sidebar.text_input("Senha de Gestão:", type="password")
SENHA_CORRETA = "Videira@1020"

# Lógica das Abas
# Fotos: True = aparecem para todos (inclusive na tela do líder, que abre sem senha)
#        False = aparecem só para quem entrou com a senha
FOTOS_SEM_SENHA = True
MOSTRAR_FOTOS = FOTOS_SEM_SENHA or acesso_admin == SENHA_CORRETA

if acesso_admin == SENHA_CORRETA:
    tab_dash, tab_freq, tab_lanc, tab_gestao, tab_ob = st.tabs(["📊 Dashboard", "📈 Frequência", "📝 Relatório do Líder", "⚙️ Gestão de Células", "📋 Relatório OB"])
else:
    tab_lanc = st.tabs(["📝 Relatório do Líder"])[0]
    tab_dash, tab_freq, tab_gestao, tab_ob = None, None, None, None
    if acesso_admin != "":
        st.sidebar.error("Senha incorreta!")

# =====================================================================
# ABA DASHBOARD
# =====================================================================
if tab_dash:
    with tab_dash:
        top1, top2 = st.columns([5, 1])
        with top2:
            if st.button("🔄 Sincronizar", use_container_width=True): st.cache_data.clear(); st.rerun()

        if st.session_state.db.empty:
            st.info("Ainda não há lançamentos na planilha.")
        else:
            lids_atuais = sorted(list(st.session_state.membros_cadastrados.keys()))
            with top1:
                lids_f = st.multiselect("Filtrar Células:", lids_atuais, default=lids_atuais)

            # ---- Filtros de período ----
            f1, f2 = st.columns(2)
            m_s = f1.selectbox("Mês de Análise:", MESES_NOMES, index=MES_PADRAO)
            df_m = st.session_state.db[st.session_state.db['MesNum'] == MESES_MAP[m_s]]

            if df_m.empty:
                st.info(f"Nenhum lançamento em {m_s}.")
            else:
                d_m = sorted(df_m['Data_Ref'].unique(), reverse=True)
                s_r = f2.selectbox("Semana Selecionada:", d_m, format_func=lambda x: datetime.strptime(x, '%Y-%m-%d').strftime('%d/%m/%Y'))
                df_s = df_m[(df_m['Data_Ref'] == s_r) & (df_m['Líder'].isin(lids_f))]
                dv_s = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data_Ref'] == s_r) & (st.session_state.db_visitantes['Líder'].isin(lids_f))]

                def get_vals(tipo, modo):
                    if tipo == "M":
                        total = sum([1 for l in lids_f for n, t in st.session_state.membros_cadastrados.get(l, {}).items() if t == "Membro"]) + len(lids_f)
                        pres = int(df_s[df_s['Tipo'].isin(['Membro', 'Liderança'])][modo].sum())
                        return pres, total
                    elif tipo == "FA":
                        total = sum([1 for l in lids_f for n, t in st.session_state.membros_cadastrados.get(l, {}).items() if t == "FA"])
                        pres = int(df_s[df_s['Tipo'] == "FA"][modo].sum())
                        return pres, total
                    else:
                        return (int(dv_s['Vis_Celula' if modo == 'Célula' else 'Vis_Culto'].sum()) if not dv_s.empty else 0), None

                secao("🏠 Célula", f"semana de {datetime.strptime(s_r, '%Y-%m-%d').strftime('%d/%m')}")
                c1, c2, c3 = st.columns(3)
                for col, (tp, lbl, cor) in zip([c1, c2, c3], [("M", "Membros", COR_PRIMARIA), ("FA", "FA", COR_FA), ("V", "Visitantes", COR_VIS)]):
                    p, t = get_vals(tp, "Célula")
                    if t is None: kpi(col, lbl, p, cor, "nesta semana")
                    else: kpi(col, lbl, f"{p}/{t}", cor, f"{(p/t*100 if t else 0):.0f}% de presença", (p/t*100 if t else 0))

                secao("⛪ Culto")
                c4, c5, c6 = st.columns(3)
                for col, (tp, lbl, cor) in zip([c4, c5, c6], [("M", "Membros", COR_PRIMARIA), ("FA", "FA", COR_FA), ("V", "Visitantes", COR_VIS)]):
                    p, t = get_vals(tp, "Culto")
                    if t is None: kpi(col, lbl, p, cor, "nesta semana")
                    else: kpi(col, lbl, f"{p}/{t}", cor, f"{(p/t*100 if t else 0):.0f}% de presença", (p/t*100 if t else 0))

                # ---- Gráficos semanais ----
                secao("📈 Evolução semanal", m_s)
                cg1, cg2 = st.columns(2)
                for col, modo, k, tit in zip([cg1, cg2], ['Célula', 'Culto'], ['chart_cel', 'chart_cul'], ["Célula", "Culto"]):
                    g_d = df_m[df_m['Líder'].isin(lids_f)].groupby('Data_Ref')[modo].sum().reset_index()
                    g_v = st.session_state.db_visitantes[(st.session_state.db_visitantes['MesNum'] == MESES_MAP[m_s]) & (st.session_state.db_visitantes['Líder'].isin(lids_f))].groupby('Data_Ref')['Vis_Celula' if modo == 'Célula' else 'Vis_Culto'].sum().reset_index()
                    mrg = pd.merge(g_d, g_v, on='Data_Ref', how='outer').fillna(0).sort_values('Data_Ref')
                    mrg['D'] = mrg['Data_Ref'].apply(lambda x: datetime.strptime(x, '%Y-%m-%d').strftime('%d/%m'))
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=mrg['D'], y=mrg[modo], name='Membros + FA', mode='lines+markers+text',
                                             text=mrg[modo].astype(int), textposition="top center",
                                             line=dict(color=COR_PRIMARIA, width=3, shape="spline"), marker=dict(size=9),
                                             fill="tozeroy", fillcolor="rgba(34,211,238,.10)"))
                    fig.add_trace(go.Scatter(x=mrg['D'], y=mrg.iloc[:, 2], name='Visitantes', mode='lines+markers+text',
                                             text=mrg.iloc[:, 2].astype(int), textposition="bottom center",
                                             line=dict(color=COR_VIS, width=3, shape="spline"), marker=dict(size=9)))
                    estilo_grafico(fig, 300).update_layout(title=dict(text=tit, x=0, font=dict(size=15)))
                    with col:
                        with st.container(border=True):
                            st.plotly_chart(fig, use_container_width=True, key=k)

                # ---- Comparativo de meses ----
                secao("📊 Comparativo mensal (Célula)", f"{m_s} e 2 meses anteriores")
                idx_analise = MESES_MAP[m_s]
                dados_comp = []
                for idx in [idx_analise - 2, idx_analise - 1, idx_analise]:
                    if idx > 0:
                        nome_m = MESES_NOMES[idx-1]
                        d_mes = st.session_state.db[(st.session_state.db['MesNum'] == idx) & (st.session_state.db['Líder'].isin(lids_f))]
                        v_mes = st.session_state.db_visitantes[(st.session_state.db_visitantes['MesNum'] == idx) & (st.session_state.db_visitantes['Líder'].isin(lids_f))]
                        val_fa = int(d_mes[d_mes['Tipo'] == "FA"]['Célula'].sum())
                        val_mem = int(d_mes[d_mes['Tipo'].isin(['Membro', 'Liderança'])]['Célula'].sum())
                        val_vis = int(v_mes['Vis_Celula'].sum())
                        dados_comp.append({"Mês": nome_m, "Métrica": "Membro + FA", "Valor": val_mem + val_fa})
                        dados_comp.append({"Mês": nome_m, "Métrica": "Visitante", "Valor": val_vis})
                        dados_comp.append({"Mês": nome_m, "Métrica": "Total Geral", "Valor": val_mem + val_fa + val_vis})
                if dados_comp:
                    fig_bar = px.bar(pd.DataFrame(dados_comp), x="Mês", y="Valor", color="Métrica", barmode="group", text_auto=True,
                                     color_discrete_map={"Membro + FA": COR_PRIMARIA, "Visitante": COR_VIS, "Total Geral": "#34D399"})
                    fig_bar.update_traces(marker_line_width=0, textposition="outside")
                    estilo_grafico(fig_bar, 380).update_layout(legend=dict(xanchor="center", x=0.5, title_text=""), bargap=0.25)
                    with st.container(border=True):
                        st.plotly_chart(fig_bar, use_container_width=True)

            # ---- Alertas (agrupados por célula) ----
            datas_u = sorted(st.session_state.db['Data_Ref'].unique(), reverse=True)
            if len(datas_u) >= 2:
                d1, d2 = datas_u[0], datas_u[1]
                alertas = {}
                for lid in lids_f:
                    itens = []
                    v1 = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data_Ref'] == d1) & (st.session_state.db_visitantes['Líder'] == lid)]['Vis_Celula'].sum()
                    v2 = st.session_state.db_visitantes[(st.session_state.db_visitantes['Data_Ref'] == d2) & (st.session_state.db_visitantes['Líder'] == lid)]['Vis_Celula'].sum()
                    if v1 == 0 and v2 == 0: itens.append("🚩 <b>Sem visitantes</b> nas últimas 2 semanas")
                    for n, t in st.session_state.membros_cadastrados.get(lid, {}).items():
                        p1 = st.session_state.db[(st.session_state.db['Data_Ref'] == d1) & (st.session_state.db['Líder'] == lid) & (st.session_state.db['Nome'] == n)]['Célula'].sum()
                        p2 = st.session_state.db[(st.session_state.db['Data_Ref'] == d2) & (st.session_state.db['Líder'] == lid) & (st.session_state.db['Nome'] == n)]['Célula'].sum()
                        if p1 == 0 and p2 == 0: itens.append(f"👤 <b>{n}</b> ausente nas últimas 2 reuniões")
                    if itens: alertas[lid] = itens

                total_alertas = sum(len(v) for v in alertas.values())
                secao("⚠️ Alertas de frequência",
                      f"{datetime.strptime(d2, '%Y-%m-%d').strftime('%d/%m')} e {datetime.strptime(d1, '%Y-%m-%d').strftime('%d/%m')}")
                if not alertas:
                    st.markdown('<div class="ok">✅ Nenhum alerta. Todos presentes e com visitantes!</div>', unsafe_allow_html=True)
                else:
                    cols_al = st.columns(2)
                    for i, (lid, itens) in enumerate(alertas.items()):
                        with cols_al[i % 2]:
                            with st.expander(f"{lid} · {len(itens)} alerta(s)", expanded=False):
                                for it in itens:
                                    st.markdown(f'<div class="alerta">{it}</div>', unsafe_allow_html=True)

# =====================================================================
# ABA FREQUÊNCIA (só leitura — não grava nada na planilha)
# =====================================================================
def sparkline_svg(valores, cor, w=120, h=34):
    vals = [v for v in valores if v is not None]
    if len(vals) < 2:
        return ""
    n = len(vals)
    pts = " ".join(f"{i*(w-6)/(n-1)+3:.1f},{h-3-(v/100)*(h-6):.1f}" for i, v in enumerate(vals))
    ux, uy = pts.split()[-1].split(",")
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<polyline points="{pts}" fill="none" stroke="{cor}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>'
            f'<circle cx="{ux}" cy="{uy}" r="3.5" fill="{cor}"/></svg>')


def pct(serie):
    return float(serie.mean() * 100) if len(serie) else None


def fmt_pct(v):
    return "—" if v is None else f"{v:.0f}%"


def cor_pct(v):
    if v is None: return COR_SUAVE
    return COR_OK if v >= 75 else ("#FBBF24" if v >= 50 else COR_ALERTA)


if tab_freq:
    with tab_freq:
        db = st.session_state.db
        dbv = st.session_state.db_visitantes
        cad = st.session_state.membros_cadastrados

        if db.empty:
            st.info("Ainda não há lançamentos na planilha.")
        else:
            with st.container(border=True):
                fc1, fc2 = st.columns([1, 3])
                mes_f = fc1.selectbox("📅 Mês", MESES_NOMES, index=MES_PADRAO, key="freq_mes")
                cels_todas = sorted(cad.keys())
                cels_f = fc2.multiselect("🏠 Células", cels_todas, default=cels_todas, key="freq_cels")
            n_mes = MESES_MAP[mes_f]
            dm = db[(db['MesNum'] == n_mes) & (db['Líder'].isin(cels_f))].copy()
            dvm = dbv[(dbv['MesNum'] == n_mes) & (dbv['Líder'].isin(cels_f))]
            dm['Grupo'] = dm['Tipo'].map(lambda t: "FA" if t == "FA" else "Membros")

            if dm.empty:
                st.info(f"Nenhum lançamento em {mes_f} para as células escolhidas.")
            else:
                # ---------- Resumo geral ----------
                k1, k2, k3, k4 = st.columns(4)
                p_mc = pct(dm[dm['Grupo'] == "Membros"]['Célula']); p_fc = pct(dm[dm['Grupo'] == "FA"]['Célula'])
                p_cu = pct(dm['Culto'])
                kpi(k1, "Membros na célula", fmt_pct(p_mc), COR_PRIMARIA, "média do mês", p_mc)
                kpi(k2, "FA na célula", fmt_pct(p_fc), COR_FA, "média do mês", p_fc)
                kpi(k3, "Presença no culto", fmt_pct(p_cu), COR_OK, "Membros + FA", p_cu)
                kpi(k4, "Visitantes", int(dvm['Vis_Celula'].sum()), COR_VIS, f"célula · {int(dvm['Vis_Culto'].sum())} no culto")

                # ---------- 1. Cards por célula ----------
                secao("🏠 Como está cada célula", mes_f)
                cards = []
                for cel in cels_f:
                    d = dm[dm['Líder'] == cel]
                    if d.empty:
                        cards.append((cel, None, None, 0, [], 0)); continue
                    semanal = [pct(d[d['Data_Ref'] == s]['Célula']) for s in sorted(d['Data_Ref'].unique())]
                    cards.append((cel, pct(d['Célula']), pct(d['Culto']),
                                  int(dvm[dvm['Líder'] == cel]['Vis_Celula'].sum()), semanal, d['Data_Ref'].nunique()))
                cards.sort(key=lambda c: -1 if c[1] is None else c[1], reverse=True)
                cols_c = st.columns(3)
                for i, (cel, pc, pu, vis, sem, nsem) in enumerate(cards):
                    cor = cor_pct(pc)
                    tend = ""
                    if len(sem) >= 2:
                        dif = sem[-1] - sem[0]
                        tend = f'<span style="color:{COR_OK if dif >= 0 else COR_ALERTA};font-weight:700">{"▲" if dif >= 0 else "▼"} {abs(dif):.0f} pts</span>'
                    corpo = (f'<div class="cel-card" style="--c:{cor}">'
                             f'<div class="cel-top">{avatar(cel, "#22D3EE", 36, ".8rem")}'
                             f'<div class="cel-nome">{cel}<small>{nsem} sábado(s) lançado(s)</small></div></div>')
                    if pc is None:
                        corpo += f'<div class="cel-vazio">Sem lançamentos em {mes_f}</div></div>'
                    else:
                        corpo += (f'<div class="cel-meio"><div><div class="cel-big" style="color:{cor}">{fmt_pct(pc)}</div>'
                                  f'<div class="cel-lbl">presença na célula</div></div>{sparkline_svg(sem, cor)}</div>'
                                  f'<div class="cel-rodape"><span>⛪ Culto <b>{fmt_pct(pu)}</b></span>'
                                  f'<span>✨ Visit. <b>{vis}</b></span>{tend}</div></div>')
                    cols_c[i % 3].markdown(corpo, unsafe_allow_html=True)

                # ---------- 2. Ranking ----------
                secao("🏆 Ranking das células", "% de presença no mês")
                modo_rk = st.radio("Ver presença em:", ["🏠 Célula", "⛪ Culto"], horizontal=True, key="freq_rk_modo")
                col_rk = "Célula" if "Célula" in modo_rk else "Culto"
                rk = (dm.groupby(['Líder', 'Grupo'])[col_rk].mean().mul(100).round(0).reset_index())
                if not rk.empty:
                    ordem = (rk[rk['Grupo'] == "Membros"].sort_values(col_rk)['Líder'].tolist())
                    ordem += [c for c in rk['Líder'].unique() if c not in ordem]
                    fig_rk = px.bar(rk, y='Líder', x=col_rk, color='Grupo', orientation='h', barmode='group', text=col_rk,
                                    color_discrete_map={"Membros": COR_PRIMARIA, "FA": COR_FA},
                                    category_orders={'Líder': ordem[::-1], 'Grupo': ["FA", "Membros"]})
                    fig_rk.update_traces(texttemplate="%{text:.0f}%", textposition="outside", marker_line_width=0, cliponaxis=False)
                    estilo_grafico(fig_rk, max(260, 70 * len(ordem) + 80))
                    fig_rk.update_layout(hovermode="closest", legend_title_text="", legend_traceorder="reversed", bargap=0.3)
                    fig_rk.update_xaxes(range=[0, 115], ticksuffix="%", title=None, showgrid=True, gridcolor="#1E293B")
                    fig_rk.update_yaxes(title=None)
                    with st.container(border=True):
                        st.plotly_chart(fig_rk, use_container_width=True, key="freq_rk")

                # ---------- 4. Mapa de calor por pessoa ----------
                secao("🗓️ Presença de cada pessoa")
                st.caption("🟦 célula e culto · 🟨 só um dos dois · 🟥 faltou · passe o dedo/mouse no quadrado para ver o detalhe")
                cel_hm = st.selectbox("Célula:", cels_f, key="freq_hm_cel")
                dh = dm[dm['Líder'] == cel_hm]
                if dh.empty:
                    st.info(f"A célula de {cel_hm} não tem lançamentos em {mes_f}.")
                else:
                    pessoas_hm = [(cel_hm, "Liderança")] + list(cad.get(cel_hm, {}).items())
                    datas_hm = sorted(dh['Data_Ref'].unique())
                    rotulos_x = [datetime.strptime(d, '%Y-%m-%d').strftime('%d/%m') for d in datas_hm]
                    z, txt, hov, rot_y = [], [], [], []
                    simb = {2: "🏠⛪", 1: "", 0: "✕"}
                    for nome, tipo in pessoas_hm:
                        lz, lt, lh = [], [], []
                        for d in datas_hm:
                            r = dh[(dh['Data_Ref'] == d) & (dh['Nome'] == nome)]
                            if r.empty:
                                lz.append(None); lt.append(""); lh.append("sem lançamento")
                            else:
                                ce, cu = int(r['Célula'].sum() > 0), int(r['Culto'].sum() > 0)
                                lz.append(ce + cu)
                                lt.append("🏠⛪" if ce and cu else ("🏠" if ce else ("⛪" if cu else "✕")))
                                lh.append(f"Célula {'✅' if ce else '❌'} · Culto {'✅' if cu else '❌'}")
                        z.append(lz); txt.append(lt); hov.append(lh)
                        rot_y.append(f"{nome} · {tipo}")
                    escala = [[0, "#9F1239"], [0.33, "#9F1239"], [0.34, "#B45309"], [0.66, "#B45309"], [0.67, "#0E7490"], [1, "#0E7490"]]
                    fig_hm = go.Figure(go.Heatmap(z=z, x=rotulos_x, y=rot_y, text=txt, texttemplate="%{text}",
                                                  customdata=hov, hovertemplate="<b>%{y}</b><br>%{x}: %{customdata}<extra></extra>",
                                                  colorscale=escala, zmin=0, zmax=2, showscale=False, xgap=4, ygap=4, textfont=dict(size=16)))
                    estilo_grafico(fig_hm, max(220, 46 * len(rot_y) + 70))
                    fig_hm.update_layout(hovermode="closest", margin=dict(l=10, r=10, t=20, b=10))
                    fig_hm.update_yaxes(autorange="reversed", showgrid=False)
                    fig_hm.update_xaxes(side="top")
                    with st.container(border=True):
                        st.plotly_chart(fig_hm, use_container_width=True, key="freq_hm")

                # ---------- 5. Destaques ----------
                secao("⭐ Destaques do mês")
                pessoas_mes = []
                for cel in cels_f:
                    for nome, tipo in cad.get(cel, {}).items():
                        r = dm[(dm['Líder'] == cel) & (dm['Nome'] == nome)]
                        if not r.empty:
                            pessoas_mes.append((nome, cel, tipo, int(r['Célula'].sum()), int(r['Culto'].sum()), len(r)))
                prontos = sorted([p for p in pessoas_mes if p[2] == "FA" and p[5] >= 2 and p[3] / p[5] >= 0.75], key=lambda p: -p[3] / p[5])
                atencao = sorted([p for p in pessoas_mes if p[2] == "Membro" and p[3] / p[5] < 0.5], key=lambda p: p[3] / p[5])
                d1c, d2c = st.columns(2)
                with d1c:
                    with st.container(border=True):
                        st.markdown(f'<div class="dest-tit" style="color:{COR_FA}">🌱 FA prontos para virar Membro</div>'
                                    f'<div class="dest-sub">75% ou mais de presença na célula</div>', unsafe_allow_html=True)
                        if not prontos: st.caption("Nenhum FA nessa faixa ainda.")
                        for nome, cel, _, pc, pu, n in prontos:
                            st.markdown(f'<div class="dest-linha"><b>{nome}</b><span class="dest-cel">{cel}</span>'
                                        f'<span class="dest-num" style="color:{COR_OK}">🏠 {pc}/{n} · ⛪ {pu}/{n}</span></div>', unsafe_allow_html=True)
                with d2c:
                    with st.container(border=True):
                        st.markdown(f'<div class="dest-tit" style="color:{COR_ALERTA}">📞 Membros que precisam de atenção</div>'
                                    f'<div class="dest-sub">menos de 50% de presença na célula</div>', unsafe_allow_html=True)
                        if not atencao: st.caption("Nenhum membro abaixo de 50%. 🎉")
                        for nome, cel, _, pc, pu, n in atencao:
                            st.markdown(f'<div class="dest-linha"><b>{nome}</b><span class="dest-cel">{cel}</span>'
                                        f'<span class="dest-num" style="color:{COR_ALERTA}">🏠 {pc}/{n} · ⛪ {pu}/{n}</span></div>', unsafe_allow_html=True)

            # ---------- 3. Evolução do ano ----------
            secao("📈 Evolução no ano", f"% de presença mês a mês em {ANO}")
            da = db[db['Líder'].isin(cels_f)].copy()
            if not da.empty:
                da['Grupo'] = da['Tipo'].map(lambda t: "FA" if t == "FA" else "Membros")
                ev = da.groupby(['MesNum', 'Grupo'])[['Célula', 'Culto']].mean().mul(100).round(0).reset_index()
                fig_ev = go.Figure()
                for grupo, cor in [("Membros", COR_PRIMARIA), ("FA", COR_FA)]:
                    e = ev[ev['Grupo'] == grupo].sort_values('MesNum')
                    x = [MESES_NOMES[int(m)-1][:3] for m in e['MesNum']]
                    fig_ev.add_trace(go.Scatter(x=x, y=e['Célula'], name=f"{grupo} · Célula", mode="lines+markers+text",
                                                text=e['Célula'].map(lambda v: f"{v:.0f}%"), textposition="top center",
                                                line=dict(color=cor, width=3, shape="spline"), marker=dict(size=9)))
                    fig_ev.add_trace(go.Scatter(x=x, y=e['Culto'], name=f"{grupo} · Culto", mode="lines+markers",
                                                line=dict(color=cor, width=2, dash="dot", shape="spline"), marker=dict(size=6), opacity=.75))
                estilo_grafico(fig_ev, 360)
                fig_ev.update_yaxes(range=[0, 110], ticksuffix="%")
                fig_ev.update_xaxes(categoryorder="array", categoryarray=[m[:3] for m in MESES_NOMES])
                with st.container(border=True):
                    st.plotly_chart(fig_ev, use_container_width=True, key="freq_ev")

# =====================================================================
# ABA LANÇAR  (pensada para o celular)
# =====================================================================
OPC_CEL, OPC_CUL = "🏠 Célula", "⛪ Culto"
# ---------------- NÚMEROS DO WHATSAPP ----------------
# Só números, com 55 + DDD (ex.: "5511999999999").
# Se ficar vazio (""), o WhatsApp abre e a pessoa escolhe o contato.
NUMERO_DISCIPULADOR = ""   # recebe o relatório semanal de cada líder
NUMERO_OBREIRO = ""        # recebe o fechamento do mês (aba Relatório OB)

with tab_lanc:
    if not st.session_state.membros_cadastrados:
        st.info("Nenhuma célula cadastrada ainda.")
    else:
        # ---- Passo 1: qual célula e qual sábado ----
        st.markdown('<div class="passo"><span>1</span> Escolha a célula e o sábado</div>', unsafe_allow_html=True)
        with st.container(border=True):
            l_l = st.selectbox("🏠 Sua Célula", sorted(st.session_state.membros_cadastrados.keys()))
            c_a, c_m, c_d = st.columns([1, 1.4, 1.2])
            l_a = c_a.selectbox("📆 Ano", ANOS, index=ANOS.index(max(ANO_ATUAL, 2026)), key="ano_lanc")
            l_m = c_m.selectbox("📅 Mês", MESES_NOMES, index=datetime.now(FUSO).month-1)
            datas_s = [date(l_a, MESES_MAP[l_m], d) for d in range(1, 32) if (date(l_a, MESES_MAP[l_m], 1) + timedelta(days=d-1)).month == MESES_MAP[l_m] and (date(l_a, MESES_MAP[l_m], 1) + timedelta(days=d-1)).weekday() == 5]
            d_l = c_d.selectbox("🗓️ Sábado", datas_s, format_func=lambda x: x.strftime('%d/%m'))

        if "presencas_bt" not in st.session_state: st.session_state.presencas_bt = {}
        pessoas = [(l_l, "Liderança")] + list(st.session_state.membros_cadastrados.get(l_l, {}).items())

        def chave_seg(nome):
            return f"seg_{l_l}_{d_l}_{nome}"

        def marcar_todos(opcoes):
            for n, _ in pessoas:
                st.session_state[chave_seg(n)] = list(opcoes)

        # Passos 2 a 4 ficam num "fragmento": ao tocar, só esta parte recarrega (rápido no celular)
        @st.fragment
        def preencher():
            # ---- Passo 2: chamada ----
            st.markdown('<div class="passo"><span>2</span> Marque quem esteve presente</div>', unsafe_allow_html=True)
            placar = st.empty()

            st.caption("Atalhos para marcar todo mundo de uma vez:")
            with st.container(key="atalhos"):
                a1, a2, a3 = st.columns(3)
                a1.button("✅ Célula", on_click=marcar_todos, args=([OPC_CEL],), use_container_width=True)
                a2.button("✅ Tudo", on_click=marcar_todos, args=([OPC_CEL, OPC_CUL],), use_container_width=True)
                a3.button("↺ Limpar", on_click=marcar_todos, args=([],), use_container_width=True)

            for nome, tipo in pessoas:
                cor = CORES_TIPO.get(tipo, COR_PRIMARIA)
                k = chave_seg(nome)
                if k not in st.session_state:
                    st.session_state[k] = [OPC_CEL, OPC_CUL] if tipo == "Liderança" else []
                with st.container(border=True):
                    st.markdown(
                        f'<div class="pessoa">{avatar(nome, cor)}'
                        f'<div><div class="pessoa-nome">{nome}</div>'
                        f'<span class="badge" style="background:{cor}22;color:{cor}">{tipo}</span></div></div>',
                        unsafe_allow_html=True,
                    )
                    sel = st.segmented_control("Presença", [OPC_CEL, OPC_CUL], selection_mode="multi",
                                               key=k, label_visibility="collapsed") or []
                # mesmo dicionário usado pelo salvamento original
                st.session_state.presencas_bt[f"bt_cel_{nome}"] = OPC_CEL in sel
                st.session_state.presencas_bt[f"bt_cul_{nome}"] = OPC_CUL in sel

            tot_cel = sum(1 for n, _ in pessoas if st.session_state.presencas_bt[f"bt_cel_{n}"])
            tot_cul = sum(1 for n, _ in pessoas if st.session_state.presencas_bt[f"bt_cul_{n}"])
            total = len(pessoas)
            placar.markdown(
                f'<div class="placar">'
                f'<div><b>{tot_cel}</b>/{total}<small>🏠 Célula</small></div>'
                f'<div><b>{tot_cul}</b>/{total}<small>⛪ Culto</small></div>'
                f'</div>', unsafe_allow_html=True)

            # ---- Passo 3: visitantes ----
            st.markdown('<div class="passo"><span>3</span> Visitantes</div>', unsafe_allow_html=True)
            with st.container(border=True):
                col_v1, col_v2 = st.columns(2)
                vce = col_v1.number_input("🏠 Na Célula", 0, key=f"vce_{l_l}_{d_l}")
                vcu = col_v2.number_input("⛪ No Culto", 0, key=f"vcu_{l_l}_{d_l}")

            # ---- Passo 4: salvar e enviar ----
            st.markdown('<div class="passo"><span>4</span> Salve e envie ao Discipulador</div>', unsafe_allow_html=True)
            st.caption(f"Célula de **{l_l}** · sábado **{d_l.strftime('%d/%m/%Y')}**")

            # Mensagem do WhatsApp montada com o que está marcado na tela
            # Mensagem do WhatsApp SEM emojis (emojis chegam como "�" pelo link do WhatsApp)
            def lista(nomes):
                return chr(10).join(f"- {n}" for n in nomes) if nomes else "- ninguém"
            pres_cel = [n for n, _ in pessoas if st.session_state.presencas_bt[f"bt_cel_{n}"]]
            falt_cel = [n for n, _ in pessoas if not st.session_state.presencas_bt[f"bt_cel_{n}"]]
            pres_cul = [n for n, _ in pessoas if st.session_state.presencas_bt[f"bt_cul_{n}"]]
            falt_cul = [n for n, _ in pessoas if not st.session_state.presencas_bt[f"bt_cul_{n}"]]
            linhas = ["*RELATÓRIO DE CÉLULA*",
                      f"Célula: *{l_l}*",
                      f"Sábado: *{d_l.strftime('%d/%m/%Y')}*",
                      "",
                      f"*CÉLULA - presentes ({tot_cel}/{total})*", lista(pres_cel),
                      f"*CÉLULA - faltaram ({len(falt_cel)})*", lista(falt_cel),
                      "",
                      f"*CULTO - presentes ({tot_cul}/{total})*", lista(pres_cul),
                      f"*CULTO - faltaram ({len(falt_cul)})*", lista(falt_cul),
                      "",
                      f"*VISITANTES:* célula {int(vce)} | culto {int(vcu)}"]
            link_wpp = f"https://wa.me/{NUMERO_DISCIPULADOR}?text={quote(chr(10).join(linhas))}"

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
                base_p = st.session_state.db_full; base_v = st.session_state.db_visitantes_full
                dfp = pd.concat([base_p[~((base_p['Data'] == dt_ref) & (base_p['Líder'] == l_l))], pd.DataFrame(novos)])
                dfv = pd.concat([base_v[~((base_v['Data'] == dt_ref) & (base_v['Líder'] == l_l))], pd.DataFrame([{"Data": dt_ref, "Líder": l_l, "Vis_Celula": vce, "Vis_Culto": vcu}])])

                with st.spinner("Salvando na planilha..."):
                    ok = salvar_seguro("Presencas", dfp) and salvar_seguro("Visitantes", dfv)
                if ok:
                    # guarda o link para o botão do WhatsApp continuar aparecendo depois de salvar
                    st.session_state.ultimo_envio = {"link": link_wpp, "cel": l_l, "data": dt_ref}
                    st.session_state.presencas_bt = {}
                    for k in [k for k in st.session_state.keys() if str(k).startswith(("seg_", "vce_", "vcu_"))]:
                        del st.session_state[k]
                    st.cache_data.clear(); st.rerun()

            if "ultimo_envio" not in st.session_state:
                st.link_button("📲 Enviar relatório para o Discipulador", link_wpp, use_container_width=True)

        preencher()

        ult = st.session_state.get("ultimo_envio")
        if ult:
            with st.container(key="salvo_ok"):
                st.markdown(f'<div class="ok">✅ <b>Salvo com sucesso!</b> Célula de {ult["cel"]} · {ult["data"]}<br>'
                            f'Agora toque no botão verde para enviar o relatório ao seu Discipulador.</div>', unsafe_allow_html=True)
                cw1, cw2 = st.columns([3, 1])
                cw1.link_button("📲 Enviar relatório para o Discipulador", ult["link"], use_container_width=True)
                if cw2.button("Fechar", use_container_width=True):
                    del st.session_state["ultimo_envio"]; st.rerun()


# =====================================================================
# ABA GESTÃO
# =====================================================================
if tab_gestao:
    with tab_gestao:
        def sync_membros():
            lista = []
            for ld, ps in st.session_state.membros_cadastrados.items():
                if not ps: lista.append({"Líder": ld, "Nome": "LIDER_INICIAL", "Tipo": "Liderança"})
                else: [lista.append({"Líder": ld, "Nome": n, "Tipo": t}) for n, t in ps.items()]
            salvar_seguro("Membros", pd.DataFrame(lista))

        # Resumo
        cad = st.session_state.membros_cadastrados
        g1, g2, g3 = st.columns(3)
        kpi(g1, "Células", len(cad), COR_OK)
        kpi(g2, "Membros", sum(1 for ps in cad.values() for t in ps.values() if t == "Membro"), COR_PRIMARIA)
        kpi(g3, "FA", sum(1 for ps in cad.values() for t in ps.values() if t == "FA"), COR_FA)

        secao("➕ Adicionar novo")
        c_add1, c_add2 = st.columns(2)
        with c_add1:
            with st.container(border=True):
                st.markdown("**Nova célula**")
                nl = st.text_input("Nome do novo líder")
                if st.button("Criar Célula", use_container_width=True):
                    if nl and nl not in st.session_state.membros_cadastrados:
                        st.session_state.membros_cadastrados[nl] = {}; sync_membros(); st.rerun()
        with c_add2:
            with st.container(border=True):
                st.markdown("**Nova pessoa**")
                if st.session_state.membros_cadastrados:
                    cs = st.selectbox("Célula para Membro:", sorted(st.session_state.membros_cadastrados.keys()))
                    nm = st.text_input("Nome da Pessoa")
                    tm = st.radio("Tipo Inicial", ["Membro", "FA"], horizontal=True)
                    if st.button("Adicionar Pessoa", use_container_width=True):
                        if nm: st.session_state.membros_cadastrados[cs][nm] = tm; sync_membros(); st.rerun()

        secao("🚀 Multiplicação e transferência")
        if st.session_state.membros_cadastrados:
            with st.container(border=True):
                o1, o2 = st.columns(2)
                cel_origem = o1.selectbox("Célula de Origem:", sorted(st.session_state.membros_cadastrados.keys()), key="orig")
                membros_orig = list(st.session_state.membros_cadastrados[cel_origem].keys())
                if not membros_orig:
                    st.caption("Essa célula ainda não tem pessoas cadastradas.")
                else:
                    membro_transf = o2.selectbox("Pessoa:", membros_orig)
                    tipo_membro = st.session_state.membros_cadastrados[cel_origem][membro_transf]
                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        st.caption("Promover a líder de uma nova célula")
                        if st.button(f"🌟 Tornar Líder: {membro_transf}", use_container_width=True):
                            del st.session_state.membros_cadastrados[cel_origem][membro_transf]
                            st.session_state.membros_cadastrados[membro_transf] = {}
                            sync_membros(); st.rerun()
                    with col_t2:
                        cel_dest = [c for c in st.session_state.membros_cadastrados.keys() if c != cel_origem]
                        if cel_dest:
                            cel_destino = st.selectbox("Transferir para:", cel_dest)
                            if st.button("Confirmar Transferência", use_container_width=True):
                                st.session_state.membros_cadastrados[cel_destino][membro_transf] = tipo_membro
                                del st.session_state.membros_cadastrados[cel_origem][membro_transf]
                                sync_membros(); st.rerun()

        # ---------------- FOTOS ----------------
        secao("📷 Fotos das pessoas", "a foto aparece no círculo, no lugar das iniciais")
        with st.container(border=True):
            fo1, fo2 = st.columns(2)
            cel_foto = fo1.selectbox("Célula:", sorted(st.session_state.membros_cadastrados.keys()), key="foto_cel")
            pessoas_foto = [cel_foto] + list(st.session_state.membros_cadastrados.get(cel_foto, {}).keys())
            pessoa_foto = fo2.selectbox("Pessoa:", pessoas_foto, key="foto_pessoa",
                                        format_func=lambda n: f"{n}  ✓ tem foto" if str(n).strip() in FOTOS else n)
            nome_foto = str(pessoa_foto).strip()

            origem = st.radio("Como quer enviar a foto?", ["🖼️ Escolher da galeria", "📸 Tirar foto agora"],
                              horizontal=True, key="foto_origem")
            if origem.startswith("📸"):
                arquivo = st.camera_input("Tire a foto", key=f"cam_{nome_foto}")
            else:
                arquivo = st.file_uploader("Escolha a foto", type=["jpg", "jpeg", "png", "webp"], key=f"up_{nome_foto}")

            if arquivo is not None:
                try:
                    b64, kb = processar_foto(arquivo)
                except Exception:
                    st.error("Não consegui abrir essa imagem. Tente uma foto em JPG ou PNG.")
                else:
                    st.markdown(f'<div class="foto-previa"><img src="data:image/jpeg;base64,{b64}">'
                                f'<div><b>Prévia de {nome_foto}</b><br>Foto reduzida para {LADO_FOTO}×{LADO_FOTO} px '
                                f'· {kb:.0f} KB</div></div>', unsafe_allow_html=True)
                    if st.button(f"💾 Salvar foto de {nome_foto}", type="primary", use_container_width=True, key="salvar_foto"):
                        with st.spinner("Salvando a foto na planilha..."):
                            if gravar_foto(nome_foto, b64):
                                st.toast(f"Foto de {nome_foto} salva!")
                                st.session_state.pop(f"up_{nome_foto}", None)
                                st.session_state.pop(f"cam_{nome_foto}", None)
                                st.rerun()
            elif nome_foto in FOTOS:
                st.markdown(f'<div class="foto-previa"><img src="data:image/jpeg;base64,{FOTOS[nome_foto]}">'
                            f'<div><b>Foto atual de {nome_foto}</b><br>Envie outra para trocar.</div></div>',
                            unsafe_allow_html=True)
                if st.button(f"Remover foto de {nome_foto}", key="remover_foto"):
                    if gravar_foto(nome_foto, None):
                        st.rerun()

        secao("🗂️ Gerenciar e excluir")
        if st.session_state.membros_cadastrados:
            with st.container(border=True):
                cel_edit = st.selectbox("Selecione para Editar/Excluir:", sorted(st.session_state.membros_cadastrados.keys()))
                membros_da_cel = st.session_state.membros_cadastrados.get(cel_edit, {})
                for nome, tipo in list(membros_da_cel.items()):
                    cor = CORES_TIPO.get(tipo, COR_PRIMARIA)
                    c_n, c_b1, c_b2 = st.columns([5, 3, 1], vertical_alignment="center")
                    c_n.markdown(
                        f'<div class="pessoa">{avatar(nome, cor, 36, ".8rem")}'
                        f'<div class="pessoa-nome">{nome} <span class="badge" style="background:{cor}22;color:{cor}">{tipo}</span></div></div>',
                        unsafe_allow_html=True,
                    )
                    novo_t = "FA" if tipo == "Membro" else "Membro"
                    if c_b1.button(f"Mudar para {novo_t}", key=f"t_{nome}", use_container_width=True):
                        st.session_state.membros_cadastrados[cel_edit][nome] = novo_t; sync_membros(); st.rerun()
                    if c_b2.button("🗑️", key=f"x_{nome}", help=f"Remover {nome}", use_container_width=True):
                        del st.session_state.membros_cadastrados[cel_edit][nome]; sync_membros(); st.rerun()

                st.divider()
                if st.button(f"Excluir Célula de {cel_edit}"):
                    del st.session_state.membros_cadastrados[cel_edit]; sync_membros(); st.rerun()

# =====================================================================
# ABA RELATÓRIO OB
# =====================================================================
if tab_ob:
    with tab_ob:
        m_ob = st.selectbox("Mês:", MESES_NOMES, index=MES_PADRAO, key="ob_m_final")
        df_ob = st.session_state.db[st.session_state.db['MesNum'] == MESES_MAP[m_ob]]
        df_v_ob = st.session_state.db_visitantes[st.session_state.db_visitantes['MesNum'] == MESES_MAP[m_ob]]

        if df_ob.empty:
            st.info(f"Nenhum lançamento em {m_ob}.")
        else:
            secao("📊 Totais semanais da rede", "Célula / Culto")
            res_sem = []
            for d_r in sorted(df_ob['Data_Ref'].unique()):
                d_f = datetime.strptime(d_r, '%Y-%m-%d').strftime('%d/%m')
                df_s = df_ob[df_ob['Data_Ref'] == d_r]
                m_ce = df_s[df_s['Tipo'].isin(['Membro', 'Liderança'])]['Célula'].sum()
                m_cu = df_s[df_s['Tipo'].isin(['Membro', 'Liderança'])]['Culto'].sum()
                f_ce, f_cu = df_s[df_s['Tipo'] == "FA"]['Célula'].sum(), df_s[df_s['Tipo'] == "FA"]['Culto'].sum()
                v_ce, v_cu = df_v_ob[df_v_ob['Data_Ref'] == d_r]['Vis_Celula'].sum(), df_v_ob[df_v_ob['Data_Ref'] == d_r]['Vis_Culto'].sum()
                res_sem.append({"Data": d_f, "Membros": f"{m_ce} / {m_cu}", "FA": f"{f_ce} / {f_cu}",
                                "Visitantes": f"{v_ce} / {v_cu}", "Total": f"{m_ce+f_ce+v_ce} / {m_cu+f_cu+v_cu}"})
            st.dataframe(pd.DataFrame(res_sem), use_container_width=True, hide_index=True)

            secao("🕵️ Chamada detalhada", "Célula | Culto")
            cel_sel_ob = st.selectbox("Selecionar Célula:", sorted(st.session_state.membros_cadastrados.keys()), key="ob_c_final")
            m_cel = [{"Nome": cel_sel_ob, "Tipo": "Liderança"}] + [{"Nome": n, "Tipo": t} for n, t in st.session_state.membros_cadastrados.get(cel_sel_ob, {}).items()]
            d_mes = sorted(df_ob['Data_Ref'].unique()); cham_d = []
            for p in m_cel:
                ln = {"Pessoa": f"{p['Nome']} ({p['Tipo']})"}
                for d in d_mes:
                    df_c = df_ob[(df_ob['Data_Ref'] == d) & (df_ob['Nome'] == p['Nome']) & (df_ob['Líder'] == cel_sel_ob)]
                    if not df_c.empty:
                        p_ce = "✅" if df_c['Célula'].sum() > 0 else "❌"
                        p_cu = "✅" if df_c['Culto'].sum() > 0 else "❌"
                        ln[datetime.strptime(d, '%Y-%m-%d').strftime('%d/%m')] = f"{p_ce} | {p_cu}"
                    else: ln[datetime.strptime(d, '%Y-%m-%d').strftime('%d/%m')] = "❌ | ❌"
                cham_d.append(ln)
            st.dataframe(pd.DataFrame(cham_d), use_container_width=True, hide_index=True)

            # ================= FECHAMENTO DO MÊS → OBREIRO =================
            secao("📤 Fechamento do mês", f"enviar o relatório de {m_ob} para o Obreiro")
            n_m = MESES_MAP[m_ob]
            sabados_mes = [date(ANO, n_m, d) for d in range(1, 32)
                           if (date(ANO, n_m, 1) + timedelta(days=d-1)).month == n_m
                           and (date(ANO, n_m, 1) + timedelta(days=d-1)).weekday() == 5]
            sabados_passados = [sb for sb in sabados_mes if sb <= datetime.now(FUSO).date()]
            mes_fechado = len(sabados_passados) == len(sabados_mes)
            cels_rede = sorted(st.session_state.membros_cadastrados.keys())

            # Situação de cada célula: quantos sábados ela lançou
            pend = []
            for cel in cels_rede:
                lanc = df_ob[df_ob['Líder'] == cel]['Data_Ref'].nunique()
                if lanc < len(sabados_passados): pend.append((cel, lanc))

            with st.container(border=True):
                s1, s2, s3 = st.columns(3)
                kpi(s1, "Sábados do mês", f"{len(sabados_passados)}/{len(sabados_mes)}", COR_VIS,
                    "mês encerrado" if mes_fechado else "mês em andamento", len(sabados_passados) / len(sabados_mes) * 100)
                kpi(s2, "Células em dia", f"{len(cels_rede) - len(pend)}/{len(cels_rede)}", COR_OK,
                    "lançaram todos os sábados", (len(cels_rede) - len(pend)) / max(len(cels_rede), 1) * 100)
                tot_ce = int(df_ob['Célula'].sum() + df_v_ob['Vis_Celula'].sum())
                tot_cu = int(df_ob['Culto'].sum() + df_v_ob['Vis_Culto'].sum())
                kpi(s3, "Total do mês", f"{tot_ce} / {tot_cu}", COR_PRIMARIA, "presenças célula / culto")

                if not mes_fechado:
                    st.warning(f"{m_ob} ainda não terminou. Você pode enviar uma parcial, mas o ideal é enviar depois do último sábado "
                               f"({sabados_mes[-1].strftime('%d/%m')}).")
                if pend:
                    st.markdown("".join(f'<div class="alerta">⏳ <b>{c}</b> lançou {l} de {len(sabados_passados)} sábado(s)</div>' for c, l in pend),
                                unsafe_allow_html=True)
                else:
                    st.markdown('<div class="ok">✅ Todas as células lançaram todos os sábados.</div>', unsafe_allow_html=True)

                # ---- Monta a mensagem ----
                msg = [f"*FECHAMENTO DE {m_ob.upper()}/{ANO}*" + ("" if mes_fechado else " _(parcial)_"),
                       "Rede Deric e Nayara", "",
                       "*SEMANA A SEMANA* (célula | culto)"]
                for d_r in sorted(df_ob['Data_Ref'].unique()):
                    df_s = df_ob[df_ob['Data_Ref'] == d_r]
                    mb = df_s[df_s['Tipo'].isin(['Membro', 'Liderança'])]
                    fa = df_s[df_s['Tipo'] == "FA"]
                    vv = df_v_ob[df_v_ob['Data_Ref'] == d_r]
                    mce, mcu, fce, fcu = int(mb['Célula'].sum()), int(mb['Culto'].sum()), int(fa['Célula'].sum()), int(fa['Culto'].sum())
                    vce_, vcu_ = int(vv['Vis_Celula'].sum()), int(vv['Vis_Culto'].sum())
                    msg.append(f"- {datetime.strptime(d_r, '%Y-%m-%d').strftime('%d/%m')}: Memb. {mce}|{mcu}, FA {fce}|{fcu}, "
                               f"Visit. {vce_}|{vcu_}, *Total {mce+fce+vce_}|{mcu+fcu+vcu_}*")
                n_sem = max(df_ob['Data_Ref'].nunique(), 1)
                msg += ["", f"*Total do mês:* célula {tot_ce} | culto {tot_cu}",
                        f"*Média por sábado:* célula {tot_ce / n_sem:.0f} | culto {tot_cu / n_sem:.0f}",
                        f"*Visitantes no mês:* célula {int(df_v_ob['Vis_Celula'].sum())} | culto {int(df_v_ob['Vis_Culto'].sum())}",
                        "", "*POR CÉLULA* (presença célula | culto | visitantes)"]
                for cel in cels_rede:
                    dc = df_ob[df_ob['Líder'] == cel]
                    if dc.empty:
                        msg.append(f"- {cel}: sem lançamentos"); continue
                    msg.append(f"- {cel}: {dc['Célula'].mean()*100:.0f}% | {dc['Culto'].mean()*100:.0f}% | "
                               f"{int(df_v_ob[df_v_ob['Líder'] == cel]['Vis_Celula'].sum())} visit.")
                if pend:
                    msg += ["", "*Lançamentos pendentes:* " + ", ".join(f"{c} ({l}/{len(sabados_passados)})" for c, l in pend)]
                texto = chr(10).join(msg)

                with st.expander("👀 Ver a mensagem antes de enviar"):
                    st.code(texto, language=None, wrap_lines=True)
                st.link_button(f"📲 Enviar fechamento de {m_ob} para o Obreiro",
                               f"https://wa.me/{NUMERO_OBREIRO}?text={quote(texto)}", use_container_width=True)
