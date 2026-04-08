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
st.set_page_config(page_title="GrowBigVentures Lead Gen Engine", layout="wide", page_icon="⚡")

# Remova espaços extras nas chaves se houver
SUPABASE_URL = "https://sukeimkqwoboizyweaqt.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN1a2VpbWtxd29ib2l6eXdlYXF0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MDMyMDMyMiwiZXhwIjoyMDg1ODk2MzIyfQ.Ji3RaWVV5mCl1pXhKrG6OxEcEoJAV5AD3sg6wyxu_G8" 
SERPER_API_KEY = "13166215d9db87e3e90f42dfdff70e00acb05902"

@st.cache_resource
def init_connection():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"Erro de conexão Supabase: {e}")
        return None

supabase = init_connection()

# --- CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; }
    div[data-testid="stMetric"] { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 8px; }
    .stButton>button { border: none; font-weight: 600; border-radius: 6px; }
    .log-box { font-family: 'Courier New', monospace; background-color: #000; color: #00ff41; padding: 15px; border-radius: 8px; height: 300px; overflow-y: auto; border: 1px solid #30363d; font-size: 13px; margin-bottom: 20px; }
    .log-entry { border-bottom: 1px solid #1a1a1a; padding: 2px 0; }
    .log-time { color: #58a6ff; margin-right: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE LÓGICA ---
def buscar_google_serper(dominio, api_key):
    url = "https://google.serper.dev/search"
    query = f'"{dominio}" email format'
    payload = json.dumps({"q": query, "num": 10})
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=10)
        if response.status_code == 403: return {"error": "API Key Invalid"}
        if response.status_code == 429: return {"error": "Rate Limit"}
        return response.json()
    except Exception as e: return {"error": str(e)}

def descobrir_regra_da_empresa(dominio, api_key):
    dados = buscar_google_serper(dominio, api_key)
    if "error" in dados: return "first.last", f"Medium ({dados['error']})"
    if 'organic' not in dados or not dados['organic']: return "first.last", "Medium (No Data)"
    
    texto_google = " ".join([str(item.get('snippet', '')).lower() for item in dados['organic']])
    
    # Mapeamento de padrões por Regex
    patterns = {
        "first.last": r'first\s*\.\s*last|first\.last@',
        "f.last": r'f\s*\.\s*last|f\.last@',
        "first_last": r'first\s*_\s*last|first_last@',
        "first-last": r'first\s*-\s*last|first-last@',
        "flast": r'f\s*last|flast@',
        "firstlast": r'first\s*last|firstlast@',
        "firstl": r'first\s*l\b|firstl@',
        "first": r'first@'
    }

    for p_name, p_regex in patterns.items():
        if re.search(p_regex, texto_google):
            return p_name, f"High (OSINT: {p_name})"

    return "first.last", "Medium (Default)"

def aplicar_regra(f_name, l_name, dominio, regra):
    f = unidecode(str(f_name).split()[0].lower().replace("-", "")) if f_name else ""
    l = unidecode(str(l_name).split()[-1].lower().replace("-", "")) if l_name else ""
    if not f: return ""
    
    rules = {
        "first.last": f"{f}.{l}@{dominio}",
        "f.last": f"{f[0]}.{l}@{dominio}",
        "first_last": f"{f}_{l}@{dominio}",
        "first-last": f"{f}-{l}@{dominio}",
        "firstlast": f"{f}{l}@{dominio}",
        "flast": f"{f[0]}{l}@{dominio}",
        "firstl": f"{f}{l[0]}@{dominio}",
        "first": f"{f}@{dominio}"
    }
    return rules.get(regra, f"{f}.{l}@{dominio}")

# --- LOGIN ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h1 style='text-align: center; color: white;'>⚡ GROWBIG</h1>", unsafe_allow_html=True)
        with st.form("login"):
            e = st.text_input("Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("ENTER"):
                if e.lower() == "leon@growbigventures.com" and p == "123":
                    st.session_state.logged_in = True
                    st.rerun()
    st.stop()

# --- INTERFACE PRINCIPAL ---
if "active_mission_id" not in st.session_state: st.session_state["active_mission_id"] = "NEW"

# Sidebar e Missions...
with st.sidebar:
    st.title("⚡ Missions")
    if st.button("🚨 STOP ALL JOBS", type="primary"):
        supabase.table("zi_jobs").update({"is_paused": True}).neq("status", "done").execute()
        st.rerun()
    
    res = supabase.table("zi_jobs").select("id, mission_name, status, total_leads").order("created_at", desc=True).limit(20).execute()
    options = [("➕ New Mission", "NEW")] + [(f"{j['mission_name']} ({j['total_leads']})", j['id']) for j in res.data]
    
    current_ids = [opt[1] for opt in options]
    idx = current_ids.index(st.session_state["active_mission_id"]) if st.session_state["active_mission_id"] in current_ids else 0
    sel = st.selectbox("History:", options=options, format_func=lambda x: x[0], index=idx)
    if sel[1] != st.session_state["active_mission_id"]:
        st.session_state["active_mission_id"] = sel[1]
        st.rerun()

# --- LÓGICA DE ENRIQUECIMENTO (STEP 2) ---
if st.session_state["active_mission_id"] != "NEW":
    job_res = supabase.table("zi_jobs").select("*").eq("id", st.session_state["active_mission_id"]).single().execute()
    job = job_res.data
    
    if job and job['phase'] == 'serper' and job['status'] == 'processing' and not job['is_paused']:
        try:
            # 1. Busca Leads
            all_leads, offset = [], 0
            while True:
                r_leads = supabase.table("zi_leads").select("*").eq("job_id", job['id']).range(offset, offset + 999).execute()
                if not r_leads.data: break
                all_leads.extend(r_leads.data)
                offset += 1000 # INCREMENTO CORRIGIDO
            
            if all_leads:
                df = pd.DataFrame(all_leads)
                df['dominio_limpo'] = df['website'].apply(lambda x: urlparse(x if str(x).startswith('http') else 'http://'+str(x)).netloc.replace('www.', '').lower() if pd.notnull(x) else 'nan')
                dominios = [d for d in df['dominio_limpo'].unique() if d not in ['nan', '', 'none']]
                
                regras_cache = {}
                progress_bar = st.progress(0)
                
                for i, dom in enumerate(dominios):
                    regra, conf = descobrir_regra_da_empresa(dom, SERPER_API_KEY)
                    regras_cache[dom] = (regra, conf)
                    progress_bar.progress((i + 1) / len(dominios))
                    time.sleep(0.1)
                
                # 2. Aplica e Salva
                for row in all_leads:
                    dom_row = urlparse(row['website'] if str(row['website']).startswith('http') else 'http://'+str(row['website'])).netloc.replace('www.', '').lower()
                    regra, conf = regras_cache.get(dom_row, ("first.last", "Default"))
                    
                    if not row.get('email') or "*" in str(row['email']):
                        row['email'] = aplicar_regra(row.get('name'), row.get('last_name'), dom_row, regra)
                        row['guessed_email'] = conf
                    else:
                        row['guessed_email'] = "Direct ZI"

                # Upsert em lotes
                for i in range(0, len(all_leads), 1000):
                    supabase.table("zi_leads").upsert(all_leads[i:i+1000]).execute()
                
                supabase.table("zi_jobs").update({"status": "done"}).eq("id", job['id']).execute()
                st.success("Enriquecimento Finalizado!")
                st.rerun()

        except Exception as e:
            st.error(f"Erro: {e}")
            supabase.table("zi_jobs").update({"is_paused": True}).eq("id", job['id']).execute()
