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
SERPER_API_KEY = "13166215d9db87e3e90f42dfdff70e00acb05902"

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

# --- OSINT FUNCTIONS ---
def buscar_google_serper(dominio, api_key):
    url = "https://google.serper.dev/search"
    # FIX 2: Query melhorada para encontrar padrões de email reais
    query = f'site:hunter.io {dominio} OR "{dominio}" email pattern'
    payload = json.dumps({"q": query, "num": 10})
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
    try:
        response = requests.request("POST", url, headers=headers, data=payload, timeout=10)
        return response.json()
    except: return {"error": "Connection Error"}

def descobrir_regra_da_empresa(dominio, api_key):
    dados = buscar_google_serper(dominio, api_key)
    if "error" in dados or 'organic' not in dados:
        return "first.last", "Medium (Default)"

    t = ""
    for item in dados['organic']:
        t += str(item.get('title', '')).lower() + " " + str(item.get('snippet', '')).lower() + " "

    # FIX 3: Primeiro tenta extrair emails reais e deduzir o padrão a partir deles
    emails_reais = re.findall(r'[\w.+%-]+@' + re.escape(dominio), t)
    if emails_reais:
        regra_deduzida = deduzir_regra_dos_emails(emails_reais)
        if regra_deduzida:
            return regra_deduzida, f"High (OSINT: real email found)"

    # Fallback: regex de padrão textual
    patterns = {
        "first.last": r'first\s*\.\s*last|first\.last@',
        "f.last":     r'\bf\s*\.\s*last\b|f\.last@',
        "first_last": r'first\s*_\s*last|first_last@',
        "first-last": r'first\s*-\s*last|first-last@',
        "flast":      r'\bflast\b|flast@',
        "firstlast":  r'\bfirstlast\b|firstlast@',
        "firstl":     r'\bfirstl\b|firstl@',
        "first":      r'\[first\]@|\bfirst@'
    }
    for p_name, p_regex in patterns.items():
        if re.search(p_regex, t):
            return p_name, f"High (OSINT: {p_name})"

    return "first.last", "Medium (Pattern Not Found)"

def deduzir_regra_dos_emails(emails):
    """
    Dado uma lista de emails reais encontrados, tenta deduzir o padrão usado.
    Ex: john.doe@empresa.com → first.last
    """
    contagem = Counter()
    for email in emails:
        local = email.split("@")[0]
        if re.match(r'^[a-z]+\.[a-z]+$', local):
            contagem["first.last"] += 1
        elif re.match(r'^[a-z]\.[a-z]+$', local):
            contagem["f.last"] += 1
        elif re.match(r'^[a-z]+_[a-z]+$', local):
            contagem["first_last"] += 1
        elif re.match(r'^[a-z]+-[a-z]+$', local):
            contagem["first-last"] += 1
        elif re.match(r'^[a-z][a-z]+$', local) and len(local) > 4:
            contagem["firstlast"] += 1
        elif re.match(r'^[a-z][a-z]{2,}$', local):
            contagem["flast"] += 1
        elif re.match(r'^[a-z]+$', local):
            contagem["first"] += 1
    if contagem:
        return contagem.most_common(1)[0][0]
    return None

def resolver_nome_campo(row, possiveis_campos):
    """FIX 1: Resolve o nome do campo com fallback para múltiplos nomes possíveis."""
    for campo in possiveis_campos:
        val = row.get(campo)
        if val and str(val).strip().lower() not in ('', 'nan', 'none'):
            return str(val).strip()
    return ""

def aplicar_regra(f_name_raw, l_name_raw, dominio, regra):
    f_parts = str(f_name_raw).split()
    l_parts = str(l_name_raw).split() if str(l_name_raw).strip() and str(l_name_raw).lower() != 'nan' else []

    f = unidecode(f_parts[0].lower().replace("-", "")) if f_parts else ""
    l = unidecode(l_parts[-1].lower().replace("-", "")) if l_parts else ""

    if not f: return ""

    rules = {
        "first.last": f"{f}.{l}@{dominio}" if l else f"{f}@{dominio}",
        "f.last":     f"{f[0]}.{l}@{dominio}" if l else f"{f}@{dominio}",
        "first_last": f"{f}_{l}@{dominio}" if l else f"{f}@{dominio}",
        "first-last": f"{f}-{l}@{dominio}" if l else f"{f}@{dominio}",
        "firstlast":  f"{f}{l}@{dominio}" if l else f"{f}@{dominio}",
        "flast":      f"{f[0]}{l}@{dominio}" if l else f"{f}@{dominio}",
        "firstl":     f"{f}{l[0]}@{dominio}" if l else f"{f}@{dominio}",
        "first":      f"{f}@{dominio}"
    }
    return rules.get(regra, f"{f}.{l}@{dominio}")

# --- LOGIN ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<br><h1 style='text-align: center; color: white;'>⚡ GROWBIGVENTURES</h1>", unsafe_allow_html=True)
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
                if job['status'] == 'done': st.success("✅ Mining Complete")
                elif job['is_paused']:
                    if st.button("▶️ RESUME MINER", use_container_width=True):
                        supabase.table("zi_jobs").update({"phase": "zi", "is_paused": False, "status": "pending", "updated_at": datetime.now().isoformat()}).eq("id", job['id']).execute()
                        st.rerun()
                else:
                    if st.button("⏸️ PAUSE MINER", use_container_width=True):
                        supabase.table("zi_jobs").update({"is_paused": True}).eq("id", job['id']).execute()
                        st.rerun()
            else: st.info("🔒 Locked")

        with c_r:
            st.subheader("💎 Step 2: Enrichment")

            # --- BOTÃO DE EMERGÊNCIA: gera emails sem Serper ---
            with st.expander("⚡ Geração Rápida (sem Serper)", expanded=False):
                st.caption("Gera emails com padrão first.last para todos os leads sem email. Não consulta API externa.")
                if st.button("🚀 GERAR EMAILS AGORA", use_container_width=True):
                    with st.spinner("Gerando emails..."):
                        all_leads, offset = [], 0
                        while True:
                            res_leads = supabase.table("zi_leads").select("*").eq("job_id", job['id']).range(offset, offset + 999).execute()
                            if not res_leads.data: break
                            all_leads.extend(res_leads.data)
                            offset += 1000

                        atualizados = 0
                        for row in all_leads:
                            email_original = str(row.get('email', '') or '')
                            guessed_zi     = str(row.get('guessed_email', '') or '')
                            tem_email      = email_original and "XXXX" not in email_original and "@" in email_original
                            tem_guessed    = guessed_zi and "XXXX" not in guessed_zi and "@" in guessed_zi

                            if tem_email:
                                row['guessed_email'] = "Direct from ZI"
                            elif tem_guessed:
                                row['email'] = guessed_zi
                                row['guessed_email'] = "High (ZI Predicted)"
                                atualizados += 1
                            else:
                                site_raw = str(row.get('website', ''))
                                dominio = urlparse(site_raw if site_raw.startswith('http') else 'http://'+site_raw).netloc.replace('www.', '').lower()
                                if dominio and dominio != 'nan':
                                    primeiro = resolver_nome_campo(row, ['first_name', 'firstName', 'name', 'primeiro_nome'])
                                    ultimo   = resolver_nome_campo(row, ['last_name', 'lastName', 'surname', 'ultimo_nome'])
                                    email_gerado = aplicar_regra(primeiro, ultimo, dominio, "first.last")
                                    if email_gerado:
                                        row['email'] = email_gerado
                                        row['guessed_email'] = "Medium (first.last default)"
                                        atualizados += 1

                        for i in range(0, len(all_leads), 1000):
                            supabase.table("zi_leads").upsert(all_leads[i:i+1000]).execute()

                        st.success(f"✅ {atualizados} emails gerados!")
                        st.rerun()

            if job['phase'] == 'serper':
                if job['status'] == 'done': st.success("✨ Completed")
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

                    # FIX 1: Debug — mostra colunas reais na primeira execução
                    with st.expander("🔍 Debug: colunas da tabela", expanded=False):
                        sample = supabase.table("zi_leads").select("*").eq("job_id", job['id']).limit(1).execute()
                        if sample.data:
                            st.write("Colunas detectadas:", list(sample.data[0].keys()))
                            st.write("Exemplo:", sample.data[0])

                    try:
                        progress_text.text("⏳ Collecting total data...")
                        all_leads, offset = [], 0
                        while True:
                            res_leads = supabase.table("zi_leads").select("*").eq("job_id", job['id']).range(offset, offset + 999).execute()
                            if not res_leads.data: break
                            all_leads.extend(res_leads.data)
                            offset += 1000

                        # Agrupa leads por domínio
                        from collections import defaultdict
                        leads_por_dominio = defaultdict(list)
                        for row in all_leads:
                            site_raw = str(row.get('website', ''))
                            dominio = urlparse(site_raw if site_raw.startswith('http') else 'http://'+site_raw).netloc.replace('www.', '').lower()
                            leads_por_dominio[dominio].append(row)

                        dominios_unicos = [d for d in leads_por_dominio.keys() if d and d != 'nan']
                        total = len(dominios_unicos)

                        for i, dominio in enumerate(dominios_unicos):
                            # Checa se foi pausado a cada domínio
                            check = supabase.table("zi_jobs").select("is_paused").eq("id", job['id']).single().execute()
                            if check.data and check.data.get("is_paused"):
                                progress_text.text("⏸️ Pausado. Progresso salvo.")
                                break

                            progress_text.text(f"🔍 ({i+1}/{total}) Investigating: {dominio}")
                            regra, confianca = descobrir_regra_da_empresa(dominio, SERPER_API_KEY)
                            p_bar.progress((i + 1) / total)

                            # Aplica e salva imediatamente os leads desse domínio
                            batch = leads_por_dominio[dominio]
                            for row in batch:
                                email_original = str(row.get('email', '') or '')
                                guessed_zi     = str(row.get('guessed_email', '') or '')
                                tem_email   = email_original and "XXXX" not in email_original and "@" in email_original
                                tem_guessed = guessed_zi and "XXXX" not in guessed_zi and "@" in guessed_zi

                                if tem_email:
                                    row['guessed_email'] = "Direct from ZI"
                                elif tem_guessed:
                                    row['email'] = guessed_zi
                                    row['guessed_email'] = "High (ZI Predicted)"
                                else:
                                    primeiro = resolver_nome_campo(row, ['first_name', 'firstName', 'name', 'primeiro_nome'])
                                    ultimo   = resolver_nome_campo(row, ['last_name', 'lastName', 'surname', 'ultimo_nome'])
                                    row['email'] = aplicar_regra(primeiro, ultimo, dominio, regra)
                                    row['guessed_email'] = confianca

                            # Deduplica por id antes de salvar (evita conflito de upsert)
                            seen_ids = set()
                            batch_unico = []
                            for r in batch:
                                rid = r.get('id')
                                if rid not in seen_ids:
                                    seen_ids.add(rid)
                                    batch_unico.append(r)
                            supabase.table("zi_leads").upsert(batch_unico).execute()
                            time.sleep(0.1)

                        supabase.table("zi_jobs").update({"status": "done"}).eq("id", job['id']).execute()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                if st.button("✨ START ENRICHMENT", type="primary", use_container_width=True):
                    supabase.table("zi_jobs").update({"phase": "serper", "status": "processing"}).eq("id", job['id']).execute()
                    st.rerun()

        st.markdown("---")
        # --- SMART EXPORT ---
        with st.container(border=True):
            st.subheader("📤 Finalização e Exportação")
            st.info(f"Leads detectados: {job['total_leads']}")
            col_down1, col_down2 = st.columns(2)
            with col_down1:
                if st.button("🔄 GERAR ARQUIVO FINAL", use_container_width=True):
                    with st.spinner("Sincronizando..."):
                        all_leads, offset = [], 0
                        while True:
                            res_leads = supabase.table("zi_leads").select("*").eq("job_id", job['id']).range(offset, offset + 999).execute()
                            if not res_leads.data: break
                            all_leads.extend(res_leads.data)
                            offset += 1000
                        if all_leads:
                            csv_buffer = pd.DataFrame(all_leads).to_csv(index=False).encode('utf-8')
                            file_path = f"leads_{job['id']}.csv"
                            supabase.storage.from_('leads_exports').upload(path=file_path, file=csv_buffer, file_options={"upsert": "true"})
                            public_url = f"{SUPABASE_URL}/storage/v1/object/public/leads_exports/{file_path}"
                            supabase.table("zi_jobs").update({"file_url": public_url}).eq("id", job['id']).execute()
                            st.rerun()
            with col_down2:
                if job.get('file_url'): st.link_button("📥 BAIXAR CSV ATUALIZADO", job['file_url'], use_container_width=True)
                else: st.warning("Gere o arquivo primeiro")
