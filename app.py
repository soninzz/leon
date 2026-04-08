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

SUPABASE_URL = "https://sukeimkqwoboizyweaqt.supabase.co"

SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN1a2VpbWtxd29ib2l6eXdlYXF0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MDMyMDMyMiwiZXhwIjoyMDg1ODk2MzIyfQ.Ji3RaWVV5mCl1pXhKrG6OxEcEoJAV5AD3sg6wyxu_G8" 

SERPER_API_KEY = "13166215d9db87e3e90f42dfdff70e00acb05902" # Your Serper API Key (Paid)



@st.cache_resource

def init_connection():

    try: return create_client(SUPABASE_URL, SUPABASE_KEY)

    except: return None

supabase = init_connection()



st.markdown("""

    <style>

    .stApp { background-color: #0d1117; }

    div[data-testid="stMetric"] { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 8px; }

    .stButton>button { border: none; font-weight: 600; border-radius: 6px; }

    .log-box { font-family: 'Courier New', monospace; background-color: #000; color: #00ff41; padding: 15px; border-radius: 8px; height: 300px; overflow-y: auto; border: 1px solid #30363d; font-size: 13px; margin-bottom: 20px; }

    .log-entry { border-bottom: 1px solid #1a1a1a; padding: 2px 0; }

    .log-time { color: #58a6ff; margin-right: 10px; }

    button:disabled { cursor: not-allowed; opacity: 0.6; }

    </style>

""", unsafe_allow_html=True)



# --- OSINT FUNCTIONS (SERPER) TURBO ---

def buscar_google_serper(dominio, api_key):

    url = "https://google.serper.dev/search"

    query = f'"{dominio}" email format'

    payload = json.dumps({"q": query, "num": 10})

    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}

    try:

        response = requests.request("POST", url, headers=headers, data=payload, timeout=10)

        if response.status_code == 403: return {"error": "API Key Invalid or Out of Credits"}

        if response.status_code == 429: return {"error": "Rate Limit Exceeded"}

        return response.json()

    except Exception as e: return {"error": f"Connection Error: {str(e)}"}



def descobrir_regra_da_empresa(dominio, api_key):

    dados = buscar_google_serper(dominio, api_key)

    

    if "error" in dados:

        return "first.last", f"Medium ({dados['error']})"

        

    if 'organic' not in dados or len(dados['organic']) == 0:

        return "first.last", "Medium (No Google Results)"

        

    texto_google = ""

    for item in dados['organic']:

        texto_google += str(item.get('title', '')).lower() + " " + str(item.get('snippet', '')).lower() + " "

            

    t = texto_google

    

    if re.search(r'first\s*\.\s*last|first_name\s*\.\s*last_name|\[first\]\.\[last\]|\{first\}\.\{last\}|first\.last@', t):

        return "first.last", "High (Public DB: first.last)"

    

    if re.search(r'f\s*\.\s*last|first_initial\s*\.\s*last_name|\[f\]\.\[last\]|\{f\}\.\{last\}|f\.last@', t):

        return "f.last", "High (Public DB: f.last)"

        

    if re.search(r'first\s*_\s*last|first_name\s*_\s*last_name|\[first\]_\[last\]|\{first\}_{last\}|first_last@', t):

        return "first_last", "High (Public DB: first_last)"

        

    if re.search(r'first\s*-\s*last|first_name\s*-\s*last_name|\[first\]-\[last\]|\{first\}-\{last\}|first-last@', t):

        return "first-last", "High (Public DB: first-last)"

        

    if re.search(r'f\s*last|first_initial\s*last_name|\[f\]\[last\]|\{f\}\{last\}|flast@', t):

        return "flast", "High (Public DB: flast)"

        

    if re.search(r'first\s*last|first_name\s*last_name|\[first\]\[last\]|\{first\}\{last\}|firstlast@', t):

        return "firstlast", "High (Public DB: firstlast)"

        

    if re.search(r'first\s*l\b|first_name\s*last_initial|\[first\]\[l\]|\{first\}\{l\}|firstl@', t):

        return "firstl", "High (Public DB: firstl)"

        

    if "first name only" in t or re.search(r'\[first\]@|\{first\}@|first@', t):

        return "first", "High (Public DB: first)"



    padrao = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

    emails = re.findall(padrao, t)

    emails_empresa = [e for e in emails if dominio in e]

    

    padroes_encontrados = []

    for email in emails_empresa:

        prefixo = email.split('@')[0]

        if prefixo in ['info', 'contact', 'support', 'sales', 'hr', 'admin', 'hello', 'press', 'media', 'marketing', 'team', 'jobs', 'careers']:

            continue

            

        if "." in prefixo:

            if len(prefixo.split(".")[0]) == 1: padroes_encontrados.append("f.last")

            else: padroes_encontrados.append("first.last")

        elif "_" in prefixo: padroes_encontrados.append("first_last")

        elif "-" in prefixo: padroes_encontrados.append("first-last")

        else:

            if len(prefixo) <= 6: padroes_encontrados.append("first")

            else: padroes_encontrados.append("flast")

                

    if padroes_encontrados:

        regra_vencedora = Counter(padroes_encontrados).most_common(1)[0][0]

        return regra_vencedora, f"High (OSINT Sampling: {regra_vencedora})"

    

    return "first.last", "Medium (Pattern Not Found)"



def aplicar_regra(f_name_raw, l_name_raw, dominio, regra):

    f_parts = str(f_name_raw).split()

    l_parts = str(l_name_raw).split() if str(l_name_raw).strip() and str(l_name_raw).lower() != 'nan' else []

    

    f = unidecode(f_parts[0].lower().replace("-", "")) if f_parts else ""

    l = unidecode(l_parts[-1].lower().replace("-", "")) if l_parts else ""

    

    if not f: return ""

    if not l: return f"{f}@{dominio}"

        

    if regra == "first.last": return f"{f}.{l}@{dominio}"

    if regra == "f.last": return f"{f[0]}.{l}@{dominio}"

    if regra == "first_last": return f"{f}_{l}@{dominio}"

    if regra == "first-last": return f"{f}-{l}@{dominio}"

    if regra == "firstlast": return f"{f}{l}@{dominio}"

    if regra == "flast": return f"{f[0]}{l}@{dominio}" if f else f"{l}@{dominio}"

    if regra == "firstl": return f"{f}{l[0]}@{dominio}" if l else f"{f}@{dominio}"

    if regra == "first": return f"{f}@{dominio}"

    

    return f"{f}.{l}@{dominio}"



# --- LOGIN ---

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:

    c1, c2, c3 = st.columns([1, 2, 1])

    with c2:

        st.markdown("<br><h1 style='text-align: center; color: white;'>⚡ GROWBIGVENTURES LEAD GEN</h1>", unsafe_allow_html=True)

        with st.form("login"):

            e = st.text_input("Email")

            p = st.text_input("Password", type="password")

            if st.form_submit_button("ENTER SYSTEM"):

                if e.lower() == "leon@growbigventures.com" and p == "123":

                    st.session_state.logged_in = True

                    st.rerun()

                else: st.error("Access Denied")

    st.stop()



if "active_mission_id" not in st.session_state: st.session_state["active_mission_id"] = "NEW"



# --- SIDEBAR ---

with st.sidebar:

    st.title("⚡ Missions")

    if st.button("🚨 STOP ALL JOBS", type="primary", use_container_width=True):

        supabase.table("zi_jobs").update({"is_paused": True}).neq("status", "done").execute()

        st.toast("🚫 All systems halted.")

        time.sleep(1); st.rerun()

    st.divider()

    try: 

        res = supabase.table("zi_jobs").select("id, mission_name, created_at, status, total_leads, is_paused").order("created_at", desc=True).limit(40).execute()

        jobs = res.data or []

    except: jobs = []

    

    options = [("➕ Launch New Mission", "NEW")]

    for j in jobs:

        icon = "🏁" if j['status'] == 'done' else ("⏸️" if j['is_paused'] else ("🟢" if j['status']=='processing' else "⏳"))

        options.append((f"{icon} {j.get('mission_name') or 'Job '+j['created_at'][5:16]} ({j['total_leads']})", j['id']))

    

    current_ids = [opt[1] for opt in options]

    idx = current_ids.index(st.session_state["active_mission_id"]) if st.session_state["active_mission_id"] in current_ids else 0

    sel = st.selectbox("History:", options=options, format_func=lambda x: x[0], index=idx)

    if sel[1] != st.session_state["active_mission_id"]: 

        st.session_state["active_mission_id"] = sel[1]

        st.rerun()



# --- MAIN ---

if st.session_state["active_mission_id"] == "NEW":

    st.title("🚀 Launch New Mission")

    with st.container(border=True):

        url = st.text_input("ZoomInfo URL (Full URL):")

        name = st.text_input("Mission Name:")

        if st.button("INITIATE LAUNCH", type="primary", use_container_width=True):

            if url:

                supabase.table("zi_jobs").update({"is_paused": True}).eq("status", "processing").execute()

                res = supabase.table("zi_jobs").insert({"status": "pending", "phase": "zi", "filters": {"url": url, "limit": 300000}, "total_leads": 0, "is_paused": False, "mission_name": name, "updated_at": datetime.now().isoformat()}).execute()

                if res.data: 

                    st.session_state["active_mission_id"] = res.data[0]['id']

                    st.rerun()

            else: st.warning("URL required.")

else:

    r = supabase.table("zi_jobs").select("*").eq("id", st.session_state["active_mission_id"]).single().execute()

    job = r.data

    if job:

        c1, c2 = st.columns([5, 1])

        with c1: 

            n = st.text_input("Mission Name", value=job.get('mission_name') or "", label_visibility="collapsed")

            if n != job.get('mission_name'): 

                supabase.table("zi_jobs").update({"mission_name": n}).eq("id", job['id']).execute()

                st.rerun()

        with c2: 

            if job['status']!='done' and st.button("🏁 ARCHIVE"): 

                supabase.table("zi_jobs").update({"status": "done", "is_paused": True}).eq("id", job['id']).execute()

                st.rerun()

        

        m1, m2, m3, m4 = st.columns(4)

        m1.metric("Total Leads", job['total_leads'])

        m2.metric("Status", "🏁 CLOSED" if job['status']=='done' else ("⏸️" if job['is_paused'] else ("🚀 RUNNING" if job['status']=='processing' else "⏳ QUEUED")))

        m3.metric("Mode", "MINING (Step 1)" if job['phase']=='zi' else "ENRICHING (Step 2)")

        m4.metric("Last Update", job['updated_at'][11:19])



        st.markdown("### 🖥️ Terminal")

        try: 

            logs = supabase.table("zi_logs").select("created_at, message").eq("job_id", job['id']).order("created_at", desc=True).limit(50).execute().data or []

        except: logs = []

        log_h = '<div class="log-box">' + "".join([f'<div class="log-entry"><span class="log-time">[{l["created_at"][11:19]}]</span> {l["message"]}</div>' for l in logs]) + '</div>'

        st.markdown(log_h, unsafe_allow_html=True)

        

        c_m, c_r = st.columns(2)

        

        with c_m:

            st.subheader("⛏️ Step 1: Mining")

            if job['phase'] == 'zi':

                if job['status'] == 'done':

                    st.success("✅ Mining Complete")

                elif job['is_paused']:

                    if st.button("▶️ RESUME MINER", use_container_width=True): 

                        supabase.table("zi_jobs").update({"phase": "zi", "is_paused": False, "status": "pending", "updated_at": datetime.now().isoformat()}).eq("id", job['id']).execute()

                        st.rerun()

                else:

                    if st.button("⏸️ PAUSE MINER", use_container_width=True): 

                        supabase.table("zi_jobs").update({"is_paused": True}).eq("id", job['id']).execute()

                        st.rerun()

            else:

                st.info("🔒 Locked (Enrichment Active)")



        with c_r:

            st.subheader("💎 Step 2: Enrichment")

            if job['phase'] == 'serper':

                if job['status'] == 'done':

                    st.success("✨ Enrichment Completed")

                elif job['is_paused']:

                    if st.button("▶️ RESUME REFINERY", use_container_width=True): 

                        supabase.table("zi_jobs").update({"is_paused": False, "status": "processing"}).eq("id", job['id']).execute()

                        st.rerun()

                else:

                    st.info("⏳ Enrichment running...")

                    if st.button("⏸️ PAUSE REFINERY", use_container_width=True): 

                        supabase.table("zi_jobs").update({"is_paused": True}).eq("id", job['id']).execute()

                        st.rerun()



                    progress_text = st.empty()

                    p_bar = st.progress(0)

                    

                    try:

                        progress_text.text("⏳ Collecting total data from the database...")

                        all_leads, offset = [], 0

                        while True:

                            res_leads = supabase.table("zi_leads").select("*").eq("job_id", job['id']).range(offset, offset + 999).execute()

                            if not res_leads.data: break

                            all_leads.extend(res_leads.data)

                            if len(res_leads.data) < 1000: break

                            offset += 1000

                            

                        df = pd.DataFrame(all_leads)

                        

                        progress_text.text("🧹 Analyzing companies...")

                        df['dominio_limpo'] = df['website'].astype(str).apply(

                            lambda x: urlparse(x if x.startswith('http') else 'http://'+x).netloc.replace('www.', '').lower()

                        )

                        dominios_unicos = df[df['dominio_limpo'] != 'nan']['dominio_limpo'].unique()

                        

                        supabase.table("zi_logs").insert({"job_id": job['id'], "message": f"📊 {len(dominios_unicos)} unique domains identified. Searching Google..."}).execute()

                        

                        regras_empresas = {}

                        confianca_empresas = {}

                        

                        for i, dominio in enumerate(dominios_unicos):

                            progress_text.text(f"🔍 Investigating company {i+1}/{len(dominios_unicos)}: {dominio}")

                            if len(dominio) > 3 and dominio != 'none' and dominio != 'nan':

                                regra, confianca = descobrir_regra_da_empresa(dominio, SERPER_API_KEY)

                                regras_empresas[dominio] = regra

                                confianca_empresas[dominio] = confianca

                                

                                time.sleep(0.15) 

                            p_bar.progress((i + 1) / len(dominios_unicos))

                            

                        progress_text.text("⚡ Building exact emails...")

                        

                        for row in all_leads:

                            site_raw = str(row.get('website', ''))

                            dominio = urlparse(site_raw if site_raw.startswith('http') else 'http://'+site_raw).netloc.replace('www.', '').lower()

                            

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

                            

                            # --- NOVA LÓGICA DE DECISÃO INTEGRADA ---

                            if not email_original or "XXXXX" in email_original or "*" in email_original:

                                row['email'] = email_gerado

                                row['guessed_email'] = confianca

                            else:

                                # Caso o ZoomInfo entregue um email real, priorizamos ele

                                row['email'] = email_original

                                row['guessed_email'] = "Direct from ZI"

                            

                        progress_text.text("💾 Saving securely to the database...")

                        supabase.table("zi_logs").insert({"job_id": job['id'], "message": "💾 Updating leads in the database..."}).execute()

                        

                        for i in range(0, len(all_leads), 1000):

                            supabase.table("zi_leads").upsert(all_leads[i:i+1000]).execute()

                            

                        supabase.table("zi_logs").insert({"job_id": job['id'], "message": "🏁 OSINT Enrichment 100% Completed!"}).execute()

                        supabase.table("zi_jobs").update({"status": "done", "updated_at": datetime.now().isoformat()}).eq("id", job['id']).execute()

                        

                        st.success("✨ High Confidence emails generated successfully!")

                        time.sleep(2)

                        st.rerun()

                        

                    except Exception as e:

                        st.error(f"Critical processing error: {e}")

                        supabase.table("zi_jobs").update({"status": "error", "is_paused": True}).eq("id", job['id']).execute()



            else:

                if job['status'] == 'done' or job['is_paused']:

                    if st.button("✨ START ENRICHMENT (SERPER)", type="primary", disabled=job['total_leads']==0, use_container_width=True): 

                        supabase.table("zi_jobs").update({"phase": "serper", "status": "processing", "updated_at": datetime.now().isoformat()}).eq("id", job['id']).execute()

                        supabase.table("zi_logs").insert({"job_id": job['id'], "message": "Starting OSINT Turbo Enrichment (Serper)..."}).execute()

                        st.rerun()

                else:

                    st.warning("⏸️ Pause or finish the Miner first to unlock Enrichment.")



        st.markdown("---")



        # --- SMART EXPORT ---

        with st.container(border=True):

            st.subheader("📤 Finalização e Exportação")

            st.info(f"O banco de dados detectou {job['total_leads']} leads. Utilize os botões abaixo para gerir o arquivo final.")

            

            col_down1, col_down2 = st.columns(2)

            

            with col_down1:

                if st.button("🔄 GERAR ARQUIVO FINAL (Sincronizar)", use_container_width=True):

                    with st.spinner("Sincronizando banco de dados com o CSV..."):

                        try:

                            # 1. Busca os leads atualizados do Supabase

                            all_leads, offset = [], 0

                            while True:

                                res_leads = supabase.table("zi_leads").select("*").eq("job_id", job['id']).range(offset, offset + 999).execute()

                                if not res_leads.data: break

                                all_leads.extend(res_leads.data)

                                if len(res_leads.data) < 1000: break

                                offset += 1000



                            if all_leads:

                                df_final = pd.DataFrame(all_leads)

                                csv_buffer = df_final.to_csv(index=False).encode('utf-8')

                                

                                # 2. Faz o upload para o Storage

                                file_path = f"leads_{job['id']}.csv"

                                supabase.storage.from_('leads_exports').upload(

                                    path=file_path,

                                    file=csv_buffer,

                                    file_options={"upsert": "true"}

                                )

                                

                                # 3. Gera a URL pública e salva no job

                                public_url = f"{SUPABASE_URL}/storage/v1/object/public/leads_exports/{file_path}"

                                supabase.table("zi_jobs").update({"file_url": public_url}).eq("id", job['id']).execute()

                                

                                st.success("✅ Arquivo atualizado!")

                                time.sleep(1)

                                st.rerun()

                            else:

                                st.error("Nenhum lead encontrado.")

                        except Exception as e:

                            st.error(f"Erro: {str(e)}")



            with col_down2:

                if job.get('file_url'):

                    st.link_button("📥 BAIXAR CSV ATUALIZADO", job['file_url'], use_container_width=True)

                else:

                    st.warning("Gere o arquivo primeiro ➔")
