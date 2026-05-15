import streamlit as st
import pandas as pd
import time
import requests
import re
import json
from io import BytesIO
from datetime import datetime
from supabase import create_client
from unidecode import unidecode
from urllib.parse import urlparse
from collections import Counter

# --- CONFIG ---
st.set_page_config(page_title="LeadPulse · Intelligence Engine", layout="wide", page_icon="◈")

SUPABASE_URL = "https://sukeimkqwoboizyweaqt.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN1a2VpbWtxd29ib2l6eXdlYXF0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MDMyMDMyMiwiZXhwIjoyMDg1ODk2MzIyfQ.Ji3RaWVV5mCl1pXhKrG6OxEcEoJAV5AD3sg6wyxu_G8"
SERPER_API_KEY = "13166215d9db87e3e90f42dfdff70e00acb05902"

@st.cache_resource
def init_connection():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except:
        return None

supabase = init_connection()

# ─────────────────────────────────────────────
#  GLOBAL CSS
# ─────────────────────────────────────────────
st.html("""
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>

/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; }

html, body, [data-testid="stAppViewContainer"], .main, .block-container {
    background-color: #080C10 !important;
    color: #C9D1D9 !important;
    font-family: 'Syne', sans-serif !important;
}

.block-container { padding: 2rem 2.5rem !important; max-width: 1400px !important; }

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }
[data-testid="stToolbar"] { display: none; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #0D1117 !important;
    border-right: 1px solid #1C2333 !important;
    padding-top: 1.5rem !important;
}
[data-testid="stSidebar"] * { font-family: 'Syne', sans-serif !important; }
[data-testid="stSidebar"] h1 {
    font-size: 0.75rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.18em !important;
    color: #3D8EF5 !important;
    text-transform: uppercase !important;
}
[data-testid="stSidebarContent"] { padding: 0 1rem !important; }

/* ── Selectbox ── */
[data-testid="stSelectbox"] > div > div {
    background: #0D1117 !important;
    border: 1px solid #1C2333 !important;
    border-radius: 6px !important;
    color: #C9D1D9 !important;
    font-family: 'Syne', sans-serif !important;
    font-size: 0.82rem !important;
}

/* ── Text Inputs ── */
[data-testid="stTextInput"] input {
    background: #0D1117 !important;
    border: 1px solid #1C2333 !important;
    border-radius: 6px !important;
    color: #E6EDF3 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.83rem !important;
    padding: 0.6rem 0.9rem !important;
    transition: border-color 0.2s;
}
[data-testid="stTextInput"] input:focus {
    border-color: #3D8EF5 !important;
    box-shadow: 0 0 0 3px rgba(61,142,245,0.12) !important;
    outline: none !important;
}
[data-testid="stTextInput"] label {
    color: #8B949E !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
}

/* ── Password Input ── */
[data-testid="stTextInput"] [type="password"] {
    font-family: 'JetBrains Mono', monospace !important;
}

/* ── Buttons ── */
.stButton > button {
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    border-radius: 6px !important;
    border: 1px solid #1C2333 !important;
    background: #161B22 !important;
    color: #C9D1D9 !important;
    padding: 0.55rem 1.2rem !important;
    transition: all 0.18s ease !important;
    width: 100% !important;
}
.stButton > button:hover {
    background: #1C2333 !important;
    border-color: #3D8EF5 !important;
    color: #E6EDF3 !important;
    box-shadow: 0 0 14px rgba(61,142,245,0.15) !important;
}

/* Primary button */
.stButton > button[kind="primary"] {
    background: #3D8EF5 !important;
    border-color: #3D8EF5 !important;
    color: #ffffff !important;
}
.stButton > button[kind="primary"]:hover {
    background: #5AA0F7 !important;
    border-color: #5AA0F7 !important;
    box-shadow: 0 0 20px rgba(61,142,245,0.35) !important;
}

/* Disabled */
.stButton > button:disabled {
    opacity: 0.35 !important;
    cursor: not-allowed !important;
}

/* ── Download button ── */
[data-testid="stDownloadButton"] > button {
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    background: #0D2A0D !important;
    border: 1px solid #238636 !important;
    color: #3FB950 !important;
    border-radius: 6px !important;
    width: 100% !important;
    transition: all 0.18s !important;
}
[data-testid="stDownloadButton"] > button:hover {
    background: #122A12 !important;
    box-shadow: 0 0 16px rgba(63,185,80,0.25) !important;
}

/* ── Metrics ── */
[data-testid="stMetric"] {
    background: #0D1117 !important;
    border: 1px solid #1C2333 !important;
    border-radius: 8px !important;
    padding: 1.1rem 1.3rem !important;
    position: relative !important;
    overflow: hidden !important;
}
[data-testid="stMetric"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #3D8EF5, transparent);
}
[data-testid="stMetricLabel"] {
    font-size: 0.67rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: #484F58 !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.45rem !important;
    font-weight: 800 !important;
    color: #E6EDF3 !important;
}

/* ── Containers / Cards ── */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #0D1117 !important;
    border: 1px solid #1C2333 !important;
    border-radius: 10px !important;
    padding: 1.4rem !important;
}

/* ── Spinner ── */
[data-testid="stSpinner"] * { color: #3D8EF5 !important; }

/* ── Progress bar ── */
[data-testid="stProgressBar"] > div {
    background: #1C2333 !important;
    border-radius: 99px !important;
}
[data-testid="stProgressBar"] > div > div {
    background: linear-gradient(90deg, #3D8EF5, #58B4FF) !important;
    border-radius: 99px !important;
}

/* ── Alerts ── */
[data-testid="stInfo"] {
    background: #0C1A2E !important;
    border: 1px solid #1A3A5C !important;
    border-left: 3px solid #3D8EF5 !important;
    border-radius: 6px !important;
    color: #8BAECF !important;
    font-size: 0.82rem !important;
}
[data-testid="stSuccess"] {
    background: #0C2016 !important;
    border: 1px solid #1A4028 !important;
    border-left: 3px solid #3FB950 !important;
    border-radius: 6px !important;
    color: #7EC891 !important;
    font-size: 0.82rem !important;
}
[data-testid="stWarning"] {
    background: #1E1600 !important;
    border-left: 3px solid #D29922 !important;
    border-radius: 6px !important;
}
[data-testid="stError"] {
    background: #200E0E !important;
    border-left: 3px solid #DA3633 !important;
    border-radius: 6px !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border: 1px solid #1C2333 !important;
    border-radius: 8px !important;
    overflow: hidden !important;
}

/* ── Divider ── */
hr { border-color: #1C2333 !important; margin: 1.4rem 0 !important; }

/* ── Section headers ── */
h1 { font-size: 1.55rem !important; font-weight: 800 !important; color: #E6EDF3 !important; letter-spacing: -0.02em !important; }
h2 { font-size: 1.1rem !important; font-weight: 700 !important; color: #C9D1D9 !important; }
h3 { font-size: 0.82rem !important; font-weight: 700 !important; color: #8B949E !important; letter-spacing: 0.1em !important; text-transform: uppercase !important; }

/* ── Toast ── */
[data-testid="stToast"] {
    background: #161B22 !important;
    border: 1px solid #1C2333 !important;
    border-radius: 8px !important;
    color: #C9D1D9 !important;
}

</style>
""")


# ─────────────────────────────────────────────
#  TERMINAL LOG COMPONENT
# ─────────────────────────────────────────────
def render_terminal(logs):
    STATUS_COLORS = {
        "🟢": "#3FB950", "✅": "#3FB950", "🏁": "#3FB950",
        "⚠️": "#D29922", "🔍": "#58B4FF", "📊": "#58B4FF",
        "💾": "#A371F7", "⏳": "#8B949E", "🚫": "#DA3633",
        "⚡": "#F0B72F", "💎": "#A371F7", "⛏️": "#58B4FF",
    }

    entries_html = ""
    for l in logs:
        msg = l["message"]
        ts = l["created_at"][11:19]
        color = "#C9D1D9"
        for emoji, c in STATUS_COLORS.items():
            if emoji in msg:
                color = c
                break
        entries_html += f"""
        <div class="t-row">
            <span class="t-ts">{ts}</span>
            <span class="t-msg" style="color:{color}">{msg}</span>
        </div>"""

    st.html(f"""
    <style>
    .terminal-wrap {{
        background: #020408;
        border: 1px solid #1C2333;
        border-radius: 8px;
        overflow: hidden;
        margin-bottom: 1.2rem;
    }}
    .terminal-header {{
        background: #0D1117;
        padding: 0.5rem 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        border-bottom: 1px solid #1C2333;
    }}
    .t-dot {{
        width: 10px; height: 10px;
        border-radius: 50%;
        display: inline-block;
    }}
    .terminal-label {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.68rem;
        color: #484F58;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        margin-left: auto;
    }}
    .terminal-body {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        line-height: 1.7;
        padding: 0.8rem 1rem;
        height: 240px;
        overflow-y: auto;
    }}
    .t-row {{
        display: flex;
        gap: 0.9rem;
        border-bottom: 1px solid #0A0E14;
        padding: 2px 0;
    }}
    .t-ts {{
        color: #3D5A80;
        flex-shrink: 0;
        user-select: none;
    }}
    .t-msg {{ word-break: break-all; }}
    </style>
    <div class="terminal-wrap">
        <div class="terminal-header">
            <span class="t-dot" style="background:#DA3633"></span>
            <span class="t-dot" style="background:#D29922"></span>
            <span class="t-dot" style="background:#3FB950"></span>
            <span class="terminal-label">system log</span>
        </div>
        <div class="terminal-body">{entries_html}</div>
    </div>
    """)


# ─────────────────────────────────────────────
#  SECTION HEADER COMPONENT
# ─────────────────────────────────────────────
def section_header(icon, title, subtitle=""):
    sub_html = f'<p style="font-family:\'Syne\',sans-serif; font-size:0.77rem; color:#484F58; margin:0; margin-top:0.15rem;">{subtitle}</p>' if subtitle else ""
    st.html(f"""
    <div style="display:flex; align-items:center; gap:0.75rem; margin-bottom:0.9rem;">
        <div style="width:36px; height:36px; background:#0D1117; border:1px solid #1C2333; border-radius:8px;
                    display:flex; align-items:center; justify-content:center; font-size:1rem; flex-shrink:0;">
            {icon}
        </div>
        <div>
            <p style="font-family:'Syne',sans-serif; font-weight:800; font-size:0.92rem;
                      color:#E6EDF3; margin:0; letter-spacing:-0.01em;">{title}</p>
            {sub_html}
        </div>
    </div>
    """)


# ─────────────────────────────────────────────
#  STATUS BADGE COMPONENT
# ─────────────────────────────────────────────
def status_badge(label, color, dot_color):
    st.html(f"""
    <div style="display:inline-flex; align-items:center; gap:0.4rem;
                background:{color}18; border:1px solid {color}40;
                border-radius:99px; padding:0.25rem 0.75rem;
                font-family:'Syne',sans-serif; font-size:0.72rem; font-weight:700;
                color:{color}; letter-spacing:0.06em; text-transform:uppercase;">
        <span style="width:7px;height:7px;border-radius:50%;background:{dot_color};
                     display:inline-block;"></span>
        {label}
    </div>
    """)


# ─────────────────────────────────────────────
#  OSINT FUNCTIONS (SERPER) — UNCHANGED LOGIC
# ─────────────────────────────────────────────
def buscar_google_serper(dominio, api_key):
    if not dominio or dominio.lower() in ['nan', 'N/A', '']:
        return {}
    url = "https://google.serper.dev/search"
    query = f'"{dominio}" "email format" OR site:rocketreach.co "{dominio}" OR "*@{dominio}"'
    payload = json.dumps({"q": query, "num": 20})
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
    try:
        response = requests.request("POST", url, headers=headers, data=payload, timeout=10)
        return response.json()
    except:
        return {}

def descobrir_regra_da_empresa(dominio, api_key):
    dados = buscar_google_serper(dominio, api_key)
    texto_google = ""
    if 'organic' in dados:
        for item in dados['organic']:
            texto_google += str(item.get('title', '')).lower() + " " + str(item.get('snippet', '')).lower() + " "

    if "first.last@" in texto_google or "first_name.last_name" in texto_google or "{first}.{last}" in texto_google or "[first].[last]" in texto_google:
        return "first.last", "High (Public DB: first.last)"
    if "flast@" in texto_google or "firstlast@" in texto_google or "first_initiallast_name" in texto_google or "{f}{last}" in texto_google:
        return "flast", "High (Public DB: flast)"
    if "f.last@" in texto_google or "first_initial.last_name" in texto_google or "{f}.{last}" in texto_google or "[f].[last]" in texto_google:
        return "f.last", "High (Public DB: f.last)"
    if "first_last@" in texto_google or "first_name_last_name" in texto_google or "{first}_{last}" in texto_google:
        return "first_last", "High (Public DB: first_last)"
    if "first-last@" in texto_google or "first_name-last_name" in texto_google or "{first}-{last}" in texto_google:
        return "first-last", "High (Public DB: first-last)"
    if "firstl@" in texto_google or "first_namelast_initial" in texto_google or "{first}{l}" in texto_google:
        return "firstl", "High (Public DB: firstl)"
    if "first@" in texto_google or "first name only" in texto_google or "first_name@" in texto_google:
        return "first", "High (Public DB: first)"

    padrao = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(padrao, texto_google)
    emails_empresa = [e for e in emails if dominio in e]
    padroes_encontrados = []
    for email in emails_empresa:
        prefixo = email.split('@')[0]
        if prefixo in ['info', 'contact', 'support', 'sales', 'hr', 'admin', 'hello', 'press', 'media', 'marketing', 'team', 'jobs', 'careers']:
            continue
        if "." in prefixo:
            partes = prefixo.split(".")
            if len(partes[0]) == 1:
                padroes_encontrados.append("f.last")
            else:
                padroes_encontrados.append("first.last")
        elif "_" in prefixo:
            padroes_encontrados.append("first_last")
        elif "-" in prefixo:
            padroes_encontrados.append("first-last")
        else:
            if len(prefixo) <= 6:
                padroes_encontrados.append("first")
            else:
                padroes_encontrados.append("flast")
    if padroes_encontrados:
        regra_vencedora = Counter(padroes_encontrados).most_common(1)[0][0]
        return regra_vencedora, f"High (OSINT Sampling: {regra_vencedora})"

    return "first.last", "Medium (Global Estimate)"

def aplicar_regra(f_name_raw, l_name_raw, dominio, regra):
    f_parts = str(f_name_raw).split()
    l_parts = str(l_name_raw).split() if str(l_name_raw).strip() and str(l_name_raw).lower() != 'nan' else []
    f = unidecode(f_parts[0].lower().replace("-", "")) if f_parts else ""
    l = unidecode(l_parts[-1].lower().replace("-", "")) if l_parts else ""
    if not f:
        return ""
    if not l:
        return f"{f}@{dominio}"
    if regra == "first.last":   return f"{f}.{l}@{dominio}"
    if regra == "f.last":       return f"{f[0]}.{l}@{dominio}"
    if regra == "first_last":   return f"{f}_{l}@{dominio}"
    if regra == "first-last":   return f"{f}-{l}@{dominio}"
    if regra in ("firstlast", "flast"): return f"{f}{l}@{dominio}"
    if regra == "firstl":       return f"{f}{l[0]}@{dominio}" if l else f"{f}@{dominio}"
    if regra == "first":        return f"{f}@{dominio}"
    return f"{f}.{l}@{dominio}"

# ─────────────────────────────────────────────
#  FUNÇÃO EXECUTORA (PROCESSO EM LOTES COM CACHE)
# ─────────────────────────────────────────────
def rodar_enriquecimento_seguro(job_id, api_key, supabase_client):
    st.info("Iniciando o enriquecimento em lotes seguros...")
    
    # Criamos uma barra de progresso no Streamlit para você acompanhar
    barra_progresso = st.progress(0)
    status_texto = st.empty()
    
    limite_bloco = 50
    offset = 0
    total_processado = 0
    
    # Dicionário de cache na memória do Streamlit para evitar chamadas repetidas ao Serper
    if 'dominio_cache' not in st.session_state:
        st.session_state['dominio_cache'] = {}

    while True:
        status_texto.text(f"Buscando bloco de leads do banco (Registros: {offset} a {offset + limite_bloco})...")
        
        try:
            # Puxa apenas uma fatia minúscula do banco (Evita o erro 57014 de Timeout)
          res = supabase_client.table('zi_leads') \
               .select('id', 'name', 'last_name', 'website') \
               .eq('job_id', job_id) \
               .is_('email', 'null') \
               .range(offset, offset + limite_bloco - 1) \
               .execute()
                
               leads_bloco = res.data
            
            # Se não voltaram mais leads, significa que a lista acabou
            if not leads_bloco or len(leads_bloco) == 0:
                break
                
            status_texto.text(f"Processando regra de e-mails para {len(leads_bloco)} contatos...")
            
            for lead in leads_bloco:
                # Se o lead já tem e-mail, pula para o próximo
                if lead.get('email'):
                    continue
                    
                dominio = lead.get('website')
                if not dominio or dominio.lower() in ['nan', '', 'n/a']:
                    continue
                
                # Checa se já sabemos o padrão dessa empresa no cache da sessão
                if dominio in st.session_state['dominio_cache']:
                    regra, confidence = st.session_state['dominio_cache'][dominio]
                else:
                    # Só vai no Serper se for um domínio inédito neste clique
                    regra, confidence = descobrir_regra_da_empresa(dominio, api_key)
                    st.session_state['dominio_cache'][dominio] = (regra, confidence)
                
                # Monta o e-mail usando a função que você já tem
                email_gerado = aplicar_regra(lead.get('name', ''), lead.get('last_name', ''), dominio, regra)
                
                if email_gerado:
                    # Salva no banco imediatamente de forma leve
                    supabase_client.table('zi_leads').update({
                        "email": email_gerado,
                        "confidence": confidence
                    }).eq('id', lead['id']).execute()
            
            total_processado += len(leads_bloco)
            offset += limite_bloco
            
            # Dá um pequeno respiro de 100ms para o Postgres respirar entre os blocos
            time.sleep(0.1)
            
        except Exception as e:
            # Se der erro de timeout mesmo no bloco, avisa e tenta o próximo bloco em vez de crashar a tela inteira
            if "57014" in str(e):
                st.warning(f"Timeout temporário detectado no bloco {offset}. Aguardando 3 segundos para retomar...")
                time.sleep(3)
                offset += limite_bloco # Avança para não travar em loop infinito
                continue
            else:
                st.error(f"Erro inesperado no pipeline: {str(e)}")
                break

    status_texto.success(f"🏁 Enriquecimento concluído! {total_processado} registros verificados.")
    barra_progresso.progress(100)

# ─────────────────────────────────────────────
#  SESSION STATE INIT
# ─────────────────────────────────────────────
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if "active_mission_id" not in st.session_state:
    st.session_state["active_mission_id"] = "NEW"


# ─────────────────────────────────────────────
#  LOGIN SCREEN
# ─────────────────────────────────────────────
if not st.session_state.logged_in:
    st.html("""
    <style>
    .login-outer {
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; min-height: 88vh; gap: 0;
    }
    .login-logo {
        font-family: 'Syne', sans-serif;
        font-weight: 800;
        font-size: 2.6rem;
        color: #E6EDF3;
        letter-spacing: -0.04em;
        margin-bottom: 0.2rem;
        text-align: center;
    }
    .login-logo span { color: #3D8EF5; }
    .login-sub {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        color: #484F58;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        text-align: center;
        margin-bottom: 2.5rem;
    }
    .login-card {
        background: #0D1117;
        border: 1px solid #1C2333;
        border-radius: 12px;
        padding: 2.2rem 2.4rem;
        width: 100%;
        max-width: 380px;
    }
    </style>
    <div class="login-outer">
        <div class="login-logo">◈ Lead<span>Pulse</span></div>
        <div class="login-sub">Intelligence · Enrichment · Export</div>
    </div>
    """)

    col_l, col_c, col_r = st.columns([1, 1.2, 1])
    with col_c:
        with st.container(border=True):
            st.html("<p style='font-family:\"Syne\",sans-serif; font-size:0.72rem; font-weight:700; color:#484F58; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:1rem;'>Access Required</p>")
            with st.form("login_form"):
                e = st.text_input("Email", placeholder="you@company.com")
                p = st.text_input("Password", type="password", placeholder="••••••••")
                st.html("<br>")
                submitted = st.form_submit_button("AUTHENTICATE →", type="primary", use_container_width=True)
                if submitted:
                    if e.lower() == "leon@growbigventures.com" and p == "123":
                        st.session_state.logged_in = True
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Access denied.")
    st.stop()


# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.html("""
    <div style="padding: 0 0.2rem 1.2rem;">
        <div style="font-family:'Syne',sans-serif; font-weight:800; font-size:1.1rem;
                    color:#E6EDF3; letter-spacing:-0.02em;">◈ LeadPulse</div>
        <div style="font-family:'JetBrains Mono',monospace; font-size:0.65rem;
                    color:#3D8EF5; letter-spacing:0.12em; text-transform:uppercase;
                    margin-top:0.15rem;">Intelligence Engine</div>
    </div>
    """)

    if st.button("⏹  HALT ALL JOBS", type="primary", use_container_width=True):
        supabase.table("zi_jobs").update({"is_paused": True}).neq("status", "done").execute()
        st.toast("All jobs halted.")
        time.sleep(1)
        st.rerun()

    st.html("<div style='height:0.8rem'></div>")
    st.html("<p style='font-family:\"JetBrains Mono\",monospace; font-size:0.62rem; color:#30363D; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.4rem;'>Missions</p>")

    try:
        res = supabase.table("zi_jobs").select("id, mission_name, created_at, status, total_leads, is_paused").order("created_at", desc=True).limit(40).execute()
        jobs = res.data or []
    except:
        jobs = []

    options = [("＋  New Mission", "NEW")]
    for j in jobs:
        if j['status'] == 'done':
            icon = "●"
        elif j['is_paused']:
            icon = "◫"
        elif j['status'] == 'processing':
            icon = "▶"
        else:
            icon = "◌"
        label = j.get('mission_name') or f"Mission {j['created_at'][5:16]}"
        options.append((f"{icon}  {label}  ({j['total_leads']})", j['id']))

    current_ids = [opt[1] for opt in options]
    idx = current_ids.index(st.session_state["active_mission_id"]) if st.session_state["active_mission_id"] in current_ids else 0

    sel = st.selectbox("", options=options, format_func=lambda x: x[0], index=idx, label_visibility="collapsed")
    if sel[1] != st.session_state["active_mission_id"]:
        st.session_state["active_mission_id"] = sel[1]
        st.rerun()

    st.html("""
    <div style="position:fixed; bottom:1.2rem; left:0; width:240px; padding: 0 1rem;">
        <div style="font-family:'JetBrains Mono',monospace; font-size:0.6rem; color:#30363D;
                    border-top:1px solid #1C2333; padding-top:0.7rem;">
            OSINT · SERPER · SUPABASE
        </div>
    </div>
    """)


# ─────────────────────────────────────────────
#  MAIN — NEW MISSION
# ─────────────────────────────────────────────
if st.session_state["active_mission_id"] == "NEW":

    st.html("""
    <div style="margin-bottom:2rem;">
        <h1 style="margin:0; margin-bottom:0.3rem;">New Mission</h1>
        <p style="font-family:'JetBrains Mono',monospace; font-size:0.75rem; color:#484F58; margin:0;">
            Configure a ZoomInfo target and deploy the extraction pipeline.
        </p>
    </div>
    """)

    with st.container(border=True):
        section_header("🎯", "Target Configuration", "Paste the full ZoomInfo search URL to begin.")
        url = st.text_input("ZoomInfo Search URL", placeholder="https://app.zoominfo.com/...")
        name = st.text_input("Mission Name", placeholder="e.g. US SaaS CTOs · Q3 2025")
        st.html("<br>")
        if st.button("DEPLOY MISSION →", type="primary", use_container_width=True):
            if url:
                supabase.table("zi_jobs").update({"is_paused": True}).eq("status", "processing").execute()
                res = supabase.table("zi_jobs").insert({
                    "status": "pending", "phase": "zi",
                    "filters": {"url": url, "limit": 300000},
                    "total_leads": 0, "is_paused": False,
                    "mission_name": name,
                    "updated_at": datetime.now().isoformat()
                }).execute()
                if res.data:
                    st.session_state["active_mission_id"] = res.data[0]['id']
                    st.rerun()
            else:
                st.warning("A ZoomInfo URL is required to proceed.")


# ─────────────────────────────────────────────
#  MAIN — MISSION DETAIL
# ─────────────────────────────────────────────
else:
    r = supabase.table("zi_jobs").select("*").eq("id", st.session_state["active_mission_id"]).single().execute()
    job = r.data

    if job:

        # ── Header ──
        col_title, col_archive = st.columns([5, 1])
        with col_title:
            n = st.text_input(
                "Mission Name",
                value=job.get('mission_name') or "",
                label_visibility="collapsed",
                placeholder="Untitled Mission"
            )
            if n != job.get('mission_name'):
                supabase.table("zi_jobs").update({"mission_name": n}).eq("id", job['id']).execute()
                st.rerun()
        with col_archive:
            if job['status'] != 'done':
                if st.button("ARCHIVE ✓", use_container_width=True):
                    supabase.table("zi_jobs").update({"status": "done", "is_paused": True}).eq("id", job['id']).execute()
                    st.rerun()

        st.html("<div style='height:0.2rem'></div>")

        # ── Status Badge ──
        if job['status'] == 'done':
            status_badge("Archived", "#3FB950", "#3FB950")
        elif job['is_paused']:
            status_badge("Paused", "#D29922", "#D29922")
        elif job['status'] == 'processing':
            status_badge("Running", "#3D8EF5", "#3D8EF5")
        else:
            status_badge("Queued", "#8B949E", "#8B949E")

        st.html("<div style='height:1.2rem'></div>")

        # ── Metrics ──
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Leads", f"{job['total_leads']:,}")

        if job['status'] == 'done':
            m2.metric("Status", "Archived")
        elif job['is_paused']:
            m2.metric("Status", "Paused")
        elif job['status'] == 'processing':
            m2.metric("Status", "Running")
        else:
            m2.metric("Status", "Queued")

        m3.metric("Pipeline Phase", "Mining" if job['phase'] == 'zi' else "Enrichment")
        m4.metric("Last Update", job['updated_at'][11:19] + " UTC")

        st.html("<div style='height:0.4rem'></div>")
        st.markdown("---")

        # ── Terminal ──
        section_header("🖥", "System Log", "Live output from the extraction and enrichment pipeline.")
        try:
            logs = supabase.table("zi_logs").select("created_at, message").eq("job_id", job['id']).order("created_at", desc=True).limit(50).execute().data or []
        except:
            logs = []
        render_terminal(logs)

        # ── Pipeline Controls ──
        c_m, spacer, c_r = st.columns([1, 0.05, 1])

        with c_m:
            with st.container(border=True):
                section_header("⛏", "Step 1 · Mining", "Extract leads from ZoomInfo.")
                if job['status'] != 'done':
                    if not job['is_paused'] and job['phase'] == 'zi':
                        st.button("⏸  PAUSE MINER", use_container_width=True,
                                  on_click=lambda: supabase.table("zi_jobs").update({"is_paused": True}).eq("id", job['id']).execute() or st.rerun())
                    else:
                        if st.button("▶  START MINER", use_container_width=True):
                            supabase.table("zi_jobs").update({"phase": "zi", "is_paused": False, "status": "pending", "updated_at": datetime.now().isoformat()}).eq("id", job['id']).execute()
                            st.rerun()
                else:
                    st.html("<p style='font-family:\"JetBrains Mono\",monospace; font-size:0.72rem; color:#3FB950;'>✓ Mission archived</p>")

        with c_r:
            with st.container(border=True):
                section_header("💎", "Step 2 · Enrichment", "Discover and construct email addresses via OSINT.")
                if job['status'] != 'done':
                    if not job['is_paused'] and job['phase'] == 'serper':
                        if st.button("⏸  PAUSE ENRICHMENT", use_container_width=True):
                            supabase.table("zi_jobs").update({"is_paused": True}).eq("id", job['id']).execute()
                            st.rerun()
                    else:
                        enrichment_disabled = job['total_leads'] == 0
                        if st.button("✦  RUN OSINT ENRICHMENT", type="primary",
                                     disabled=enrichment_disabled, use_container_width=True):

                            supabase.table("zi_jobs").update({"phase": "serper", "status": "processing", "updated_at": datetime.now().isoformat()}).eq("id", job['id']).execute()
                            supabase.table("zi_logs").insert({"job_id": job['id'], "message": "Starting OSINT Turbo Enrichment (Serper)..."}).execute()

                            progress_text = st.empty()
                            p_bar = st.progress(0)

                            try:
                                progress_text.text("Collecting data from database...")
                                all_leads, offset = [], 0
                                while True:
                                    res_leads = supabase.table("zi_leads").select("*").eq("job_id", job['id']).range(offset, offset + 999).execute()
                                    if not res_leads.data:
                                        break
                                    all_leads.extend(res_leads.data)
                                    if len(res_leads.data) < 1000:
                                        break
                                    offset += 1000

                                df = pd.DataFrame(all_leads)
                                progress_text.text("Analyzing company domains...")
                                df['dominio_limpo'] = df['website'].astype(str).apply(
                                    lambda x: urlparse(x if x.startswith('http') else 'http://' + x).netloc.replace('www.', '').lower()
                                )
                                dominios_unicos = df[df['dominio_limpo'] != 'nan']['dominio_limpo'].unique()

                                supabase.table("zi_logs").insert({"job_id": job['id'], "message": f"📊 {len(dominios_unicos)} unique domains identified."}).execute()

                                regras_empresas = {}
                                confianca_empresas = {}

                                for i, dominio in enumerate(dominios_unicos):
                                    progress_text.text(f"Investigating {i+1}/{len(dominios_unicos)}: {dominio}")
                                    if len(dominio) > 3 and dominio not in ('none', 'nan'):
                                        regra, confianca = descobrir_regra_da_empresa(dominio, SERPER_API_KEY)
                                        regras_empresas[dominio] = regra
                                        confianca_empresas[dominio] = confianca
                                        time.sleep(0.05)
                                    p_bar.progress((i + 1) / len(dominios_unicos))

                                progress_text.text("Constructing email addresses...")
                                for row in all_leads:
                                    site_raw = str(row.get('website', ''))
                                    dominio = urlparse(site_raw if site_raw.startswith('http') else 'http://' + site_raw).netloc.replace('www.', '').lower()
                                    nome = str(row.get('name', ''))
                                    sobrenome = str(row.get('last_name', ''))
                                    regra = regras_empresas.get(dominio, "first.last")
                                    confianca = confianca_empresas.get(dominio, "Medium (Global Estimate)")

                                    if dominio and nome and nome.lower() not in ['nan', 'none', '']:
                                        email_gerado = aplicar_regra(nome, sobrenome, dominio, regra)
                                    else:
                                        email_gerado = ""
                                        confianca = "Error: No Name or Website"

                                    email_original = row.get('email', '')
                                    if "Medium" in confianca and email_original and "XXXXX" not in email_original:
                                        row['email'] = email_original
                                        row['guessed_email'] = "Medium (Leveraged from ZoomInfo)"
                                    else:
                                        row['email'] = email_gerado
                                        row['guessed_email'] = confianca

                                progress_text.text("Persisting results to database...")
                                supabase.table("zi_logs").insert({"job_id": job['id'], "message": "💾 Saving enriched leads to database..."}).execute()
                                for i in range(0, len(all_leads), 1000):
                                    supabase.table("zi_leads").upsert(all_leads[i:i+1000]).execute()

                                supabase.table("zi_logs").insert({"job_id": job['id'], "message": "🏁 OSINT Enrichment 100% complete."}).execute()
                                supabase.table("zi_jobs").update({"status": "done", "updated_at": datetime.now().isoformat()}).eq("id", job['id']).execute()

                                st.success("Enrichment complete. All emails generated.")
                                time.sleep(2)
                                st.rerun()

                            except Exception as e:
                                st.error(f"Pipeline error: {e}")
                                supabase.table("zi_jobs").update({"status": "error", "is_paused": True}).eq("id", job['id']).execute()
                else:
                    st.html("<p style='font-family:\"JetBrains Mono\",monospace; font-size:0.72rem; color:#3FB950;'>✓ Mission archived</p>")

        st.markdown("---")

        # ── Export ──
        with st.container(border=True):
            section_header("📤", "Export", f"{job['total_leads']:,} leads ready for extraction.")

            col_info, col_btn = st.columns([3, 1])
            with col_info:
                st.info(f"All {job['total_leads']:,} leads will be exported as a CSV file, including enriched email addresses and confidence scores.")
            with col_btn:
                st.html("<div style='height:0.3rem'></div>")
                if st.button(f"EXTRACT {job['total_leads']:,} LEADS", type="primary", use_container_width=True):
                    with st.spinner("Generating export file..."):
                        try:
                            all_leads, offset = [], 0
                            while True:
                                res_leads = supabase.table("zi_leads").select("*").eq("job_id", job['id']).range(offset, offset + 999).execute()
                                if not res_leads.data:
                                    break
                                all_leads.extend(res_leads.data)
                                if len(res_leads.data) < 1000:
                                    break
                                offset += 1000

                            if all_leads:
                                df_export = pd.DataFrame(all_leads)
                                if 'guessed_email' in df_export.columns:
                                    df_export.rename(columns={'guessed_email': 'Confidence Level'}, inplace=True)
                                st.download_button(
                                    "⬇  DOWNLOAD CSV",
                                    df_export.to_csv(index=False).encode('utf-8'),
                                    f"leadpulse_export_{job['id'][:8]}.csv",
                                    use_container_width=True
                                )
                            else:
                                st.error("No leads found for this mission.")
                        except Exception as e:
                            st.error(f"Export error: {e}")

        st.html("<div style='height:0.6rem'></div>")

        # ── Preview ──
        section_header("🔬", "Lead Preview", "Last 25 captured leads.")
        headers = ['Name', 'Last Name', 'Job Title', 'Company', 'Email', 'Source', 'Phone', 'City', 'State', 'Location']
        preview_data = job.get('last_leads_preview') or []
        df_preview = pd.DataFrame(preview_data)
        if not df_preview.empty:
            df_preview.columns = headers[:len(df_preview.columns)]
            st.dataframe(df_preview, use_container_width=True, hide_index=True)
        else:
            st.html("""
            <div style="background:#0D1117; border:1px dashed #1C2333; border-radius:8px;
                        padding:2rem; text-align:center;">
                <p style="font-family:'JetBrains Mono',monospace; font-size:0.75rem;
                           color:#30363D; margin:0;">No lead data yet — start the miner to begin extraction.</p>
            </div>
            """)

        # ── Auto-refresh ──
        if not job['is_paused'] and job['status'] != 'done':
            time.sleep(4)
            st.rerun()
