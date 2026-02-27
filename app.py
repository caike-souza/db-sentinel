import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import google.generativeai as genai
import plotly.express as px
import time
import smtplib
import hashlib
import hmac
from email.mime.text import MIMEText
from email.message import EmailMessage

# --- CREDENCIAIS (Configuradas via Streamlit Secrets) ---
SUPABASE_HOST = st.secrets["SUPABASE_HOST"]
DB_NAME       = st.secrets["DB_NAME"]
DB_USER       = st.secrets["DB_USER"]
DB_PASS       = st.secrets["DB_PASS"]
GEMINI_KEY    = st.secrets["GEMINI_KEY"]

genai.configure(api_key=GEMINI_KEY)
model_ai = genai.GenerativeModel('gemini-2.0-flash')

# --- SESSÃO DE LOGIN ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "show_splash" not in st.session_state:
    st.session_state.show_splash = False
if "reset_mode" not in st.session_state:
    st.session_state.reset_mode = False

# --- FUNÇÃO DE ENVIO DE E-MAIL ---
def send_reset_email(target_email):
    # Verifica se os secrets de SMTP existem antes de prosseguir
    required_secrets = ["SMTP_SERVER", "SMTP_PORT", "SMTP_USER", "SMTP_PASS"]
    missing = [s for s in required_secrets if s not in st.secrets]
    
    if missing:
        st.error(f"⚠️ Configuração de e-mail incompleta. Faltam os segredos: {', '.join(missing)}")
        st.info("Adicione estas chaves no painel 'Secrets' do Streamlit Cloud.")
        return False

    try:
        smtp_server = st.secrets["SMTP_SERVER"]
        smtp_port   = st.secrets["SMTP_PORT"]
        smtp_user   = st.secrets["SMTP_USER"]
        smtp_pass   = st.secrets["SMTP_PASS"]
        
        # Gera um token simples (Hash do email + segredo)
        secret = st.secrets["DB_PASS"]
        token = hmac.new(secret.encode(), target_email.encode(), hashlib.sha256).hexdigest()
        reset_link = f"https://caike-souza-db-sentinel.streamlit.app/?token={token}&email={target_email}"
        
        msg = EmailMessage()
        msg.set_content(f"Olá,\n\nRecebemos uma solicitação de redefinição de senha para sua conta no DB Sentinel.\n\nClique no link abaixo para criar uma nova senha:\n{reset_link}\n\nSe você não solicitou isso, ignore este e-mail.")
        msg['Subject'] = "DB Sentinel | Redefinição de Senha"
        msg['From'] = smtp_user
        msg['To'] = target_email
        
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False

# --- TELA DE LOGIN ---
if not st.session_state.authenticated:
    st.set_page_config(page_title="DB Sentinel | Login", page_icon="🛡️", layout="wide")

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
    
    body, .stApp { background: #f0f0f0 !important; color: #000000 !important; font-family: 'Inter', sans-serif; }
    [data-testid="stAppViewContainer"] { background: #f0f0f0; }
    [data-testid="stHeader"] { background: transparent; }

    /* Centralizar conteúdo verticalmente */
    .stMainBlockContainer {
        display: flex;
        flex-direction: column;
        justify-content: center;
        min-height: 100vh;
        padding-top: 0 !important;
    }

    /* Branding Section */
    .branding-container {
        text-align: center;
        padding-right: 40px;
    }
    .logo-emoji {
        font-size: 160px;
        margin-bottom: 30px;
    }
    .main-title {
        font-family: 'Inter', sans-serif;
        font-size: 52px; font-weight: 800;
        color: #1a1a2e; letter-spacing: -0.025em;
        line-height: 1;
        margin-bottom: 20px;
        text-transform: uppercase;
    }
    .sub-title {
        color: #4b5563; font-size: 16px; font-weight: 600;
        letter-spacing: 0.1em; text-transform: uppercase;
    }

    /* Login Card Section */
    [data-testid="stForm"] {
        background: #ffffff !important;
        padding: 50px !important;
        border-radius: 10px !important;
        box-shadow: 0 15px 35px rgba(0,0,0,0.08) !important;
        border: none !important;
        max-width: 440px;
        margin: 0 auto;
    }

    .login-header {
        font-size: 28px; font-weight: 700;
        color: #111827; margin-bottom: 40px;
        font-family: 'Inter', sans-serif;
    }

    /* Input Styling to match mockup */
    .stTextInput label {
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        color: #4b5563 !important;
        font-size: 13px !important;
        margin-bottom: 12px !important;
        text-transform: uppercase;
    }

    .stTextInput > div > div > input {
        background: #ffffff !important;
        border: 1px solid #e5e7eb !important;
        color: #000000 !important;
        border-radius: 6px !important;
        padding: 14px !important;
        font-size: 14px !important;
        height: 48px !important;
    }
    
    .stTextInput > div > div {
        background: transparent !important;
        border: none !important;
    }

    /* Button Styling (Purple) */
    .stButton > button {
        width: 100%;
        background: #5843e0 !important;
        color: #ffffff !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        padding: 14px !important;
        border-radius: 6px !important;
        border: none !important;
        margin-top: 20px !important;
        height: 50px !important;
        text-transform: uppercase;
        font-size: 13px !important;
        letter-spacing: 0.05em !important;
    }
    .stButton > button:hover { background: #4736b4 !important; }

    /* Links */
    .reset-trigger-button button {
        background: none !important;
        border: none !important;
        color: #5880ec !important; /* Blue-ish purple as in print */
        font-size: 15px !important;
        font-weight: 500 !important;
        padding: 0 !important;
        margin-top: 30px !important;
        box-shadow: none !important;
        text-decoration: none !important;
    }
    .reset-trigger-button button:hover { text-decoration: underline !important; }

    .link-footer {
        text-align: center; margin-top: 50px;
        color: #9ca3af; font-size: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Layout Principal em Colunas com razão mais próxima ao print
    col_l, col_brand, col_gap, col_login, col_r = st.columns([2, 5, 1, 5, 2])

    with col_brand:
        st.markdown("""
        <div class="branding-container">
            <div class="logo-emoji">🛡️</div>
            <div class="main-title">DB SENTINEL</div>
            <div class="sub-title">SECURE ACCESS TERMINAL</div>
        </div>
        """, unsafe_allow_html=True)

    with col_login:
        if st.session_state.reset_mode:
            st.markdown('<div class="login-header">Redefinir Senha</div>', unsafe_allow_html=True)
            with st.form("reset_form"):
                reset_email = st.text_input("E-MAIL")
                submitted = st.form_submit_button("SOLICITAR NOVA SENHA")
                if submitted:
                    if reset_email:
                        send_reset_email(reset_email)
                    else: st.warning("Informe o e-mail.")
            
            st.markdown('<div class="reset-trigger-button" style="text-align:center;">', unsafe_allow_html=True)
            if st.button("Voltar ao Login"):
                st.session_state.reset_mode = False
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="login-header">LOGIN</div>', unsafe_allow_html=True)
            with st.form("login_form"):
                email = st.text_input("E-MAIL", placeholder="seu@email.com")
                password = st.text_input("SENHA", type="password", placeholder="******")
                login_submit = st.form_submit_button("ACESSAR SISTEMA")
                
                if login_submit:
                    if email == "caike@helyo.com.br" and password == "123456":
                        st.session_state.authenticated = True
                        st.session_state.show_splash = True
                        st.rerun()
                    else:
                        st.error("Credenciais inválidas.")

            st.markdown('<div class="reset-trigger-button" style="text-align:center;">', unsafe_allow_html=True)
            if st.button("Redefinir Senha"):
                st.session_state.reset_mode = True
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="link-footer">── development by helyo tools ──</div>', unsafe_allow_html=True)

    st.stop()

# --- TELA SPLASH / HOME ---
if st.session_state.get("show_splash", False):
    st.set_page_config(page_title="DB Sentinel", page_icon="🛡️", layout="centered")
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Share+Tech+Mono&display=swap');
    body, .stApp, [data-testid="stAppViewContainer"] { background: #020408 !important; }
    [data-testid="stHeader"] { background: transparent; }
    @keyframes logoReveal {
        0%  { letter-spacing: 2em; opacity: 0; filter: blur(20px); }
        60% { letter-spacing: .15em; opacity: 1; filter: blur(0); }
        100%{ letter-spacing: .08em; opacity: 1; }
    }
    @keyframes glowPulse {
        0%,100%{ text-shadow: 0 0 20px #00ffc355, 0 0 60px #00ffc322; }
        50%    { text-shadow: 0 0 40px #00ffc388, 0 0 100px #00ffc344; }
    }
    @keyframes fadeUp {
        from{ opacity:0; transform:translateY(20px); }
        to  { opacity:1; transform:translateY(0); }
    }
    @keyframes ringPulse {
        0%  { transform:scale(.5); opacity:.8; }
        100%{ transform:scale(2.5); opacity:0; }
    }
    @keyframes slideHelyo {
        from{ opacity:0; transform:translateX(-20px); }
        to  { opacity:1; transform:translateX(0); }
    }
    .splash-wrap {
        text-align: center; padding: 80px 20px;
        display: flex; flex-direction: column; align-items: center;
    }
    .splash-icon { font-size: 80px; margin-bottom: 24px; filter: drop-shadow(0 0 30px #00ffc388); animation: fadeUp .6s ease both; }
    .splash-title {
        font-family: 'Orbitron', monospace; font-weight: 900;
        font-size: clamp(32px,6vw,64px);
        color: #00ffc3; letter-spacing: .08em;
        animation: logoReveal 1.4s cubic-bezier(.16,1,.3,1) .3s both, glowPulse 3s ease 1.8s infinite;
    }
    .splash-sub {
        font-family: 'Share Tech Mono', monospace;
        color: rgba(0,255,195,0.5); font-size: 12px;
        letter-spacing: .25em; margin-top: 12px;
        animation: fadeUp .6s ease 1.6s both;
    }
    .splash-divider {
        display: flex; align-items: center; gap: 14px; margin: 12px 0;
        animation: fadeUp .6s ease 1.9s both;
    }
    .splash-divider span { font-family:'Share Tech Mono',monospace; color:rgba(0,255,195,0.3); font-size:10px; letter-spacing:.2em; }
    .splash-divider div  { height:1px; width:60px; background:rgba(0,255,195,0.2); }
    .helyo-footer {
        position: fixed; bottom: 28px; width: 100%; text-align: center;
        font-family: 'Share Tech Mono', monospace;
        color: rgba(0,255,195,0.3); font-size: 10px; letter-spacing: .25em;
        animation: slideHelyo 1s ease 2.2s both;
    }
    .stButton > button {
        background: transparent !important;
        border: 1px solid #00ffc3 !important;
        color: #00ffc3 !important;
        font-family: 'Orbitron', monospace !important;
        font-weight: 700 !important; font-size: 12px !important;
        letter-spacing: .2em !important; padding: 16px 48px !important;
        border-radius: 8px !important;
        box-shadow: 0 0 20px rgba(0,255,195,0.2) !important;
        margin-top: 40px !important;
        animation: fadeUp .6s ease 2s both !important;
    }
    .stButton > button:hover {
        background: #00ffc3 !important; color: #020408 !important;
        box-shadow: 0 0 40px rgba(0,255,195,0.5) !important;
    }
    </style>
    <div class="splash-wrap">
        <div class="splash-icon">🛡️</div>
        <div class="splash-title">DB SENTINEL</div>
        <div class="splash-sub">INTELLIGENT DATABASE MONITORING</div>
        <div class="splash-divider">
            <div></div>
            <span>SUPABASE + GEMINI AI</span>
            <div></div>
        </div>
    </div>
    <div class="helyo-footer">── development by helyo tools ──</div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        if st.button("INICIAR MONITORAMENTO ▶"):
            st.session_state.show_splash = False
            st.rerun()
    st.stop()

# --- DASHBOARD PRINCIPAL ---
st.set_page_config(page_title="DB Sentinel | Dashboard", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Share+Tech+Mono&display=swap');
body, .stApp, [data-testid="stAppViewContainer"] { background: #020408 !important; }
[data-testid="stHeader"] { background: rgba(4,8,15,0.95) !important; }
[data-testid="stSidebar"] { background: #04080f !important; border-right: 1px solid rgba(0,255,195,0.1); }
.metric-card { background:#04080f; border-radius:12px; padding:20px; border:1px solid rgba(0,255,195,0.1); }
h1,h2,h3 { font-family:'Orbitron',monospace !important; color:#00ffc3 !important; letter-spacing:.08em !important; }
.stMetric { background: #04080f; border-radius: 12px; padding: 16px; border: 1px solid rgba(0,255,195,0.1); }
.stMetric label { font-family:'Share Tech Mono',monospace !important; color:rgba(0,255,195,0.5) !important; font-size:10px !important; letter-spacing:.15em !important; }
.stMetric [data-testid="metric-container"] > div:first-child { color: #00ffc3 !important; font-family:'Orbitron',monospace !important; }
.stTabs [data-baseweb="tab"] { font-family:'Orbitron',monospace !important; font-size:10px !important; letter-spacing:.1em !important; color:rgba(0,255,195,0.4) !important; }
.stTabs [aria-selected="true"] { color:#00ffc3 !important; }
.stButton > button { background:transparent !important; border:1px solid #00ffc3 !important; color:#00ffc3 !important; font-family:'Orbitron',monospace !important; font-size:11px !important; letter-spacing:.1em !important; border-radius:8px !important; }
.stButton > button:hover { background:#00ffc3 !important; color:#020408 !important; }
.stDataFrame { background:#04080f !important; }
footer { visibility:hidden; }
.helyo-footer { text-align:center; font-family:'Share Tech Mono',monospace; color:rgba(0,255,195,0.2); font-size:10px; letter-spacing:.2em; padding:20px 0; border-top:1px solid rgba(0,255,195,0.05); margin-top:20px; }
</style>
""", unsafe_allow_html=True)

# --- CONEXÃO ---
@st.cache_resource
def get_db_connection():
    return psycopg2.connect(host=SUPABASE_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port="6543", connect_timeout=10)

def fetch_metrics():
    try:
        conn = get_db_connection()
        cur  = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM db_metrics_history ORDER BY timestamp DESC LIMIT 20;")
        history = cur.fetchall()
        cur.execute("""
            SELECT pid, usename as usuario, state as status,
                   COALESCE(query,'') as query,
                   COALESCE((now()-query_start)::text,'N/A') as duracao
            FROM pg_stat_activity WHERE state != 'idle' LIMIT 10;
        """)
        tasks = cur.fetchall()
        cur.close()
        return pd.DataFrame(history), pd.DataFrame(tasks)
    except Exception as e:
        st.error(f"❌ Erro de conexão: {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- TOPBAR ---
col_logo, col_status, col_logout = st.columns([6,1,1])
with col_logo:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:14px;padding:8px 0">
        <span style="font-size:28px">🛡️</span>
        <div>
            <div style="font-family:Orbitron,monospace;font-weight:900;font-size:18px;color:#00ffc3;text-shadow:0 0 15px #00ffc355;letter-spacing:.1em">DB SENTINEL</div>
            <div style="font-family:Share Tech Mono,monospace;font-size:10px;color:rgba(0,255,195,0.4)">lbmmdvlxcpkgfnrhdgwt.supabase.co</div>
        </div>
    </div>""", unsafe_allow_html=True)
with col_status:
    st.markdown('<div style="margin-top:16px;background:rgba(74,222,128,0.1);border:1px solid rgba(74,222,128,0.4);border-radius:8px;padding:6px 12px;text-align:center;font-family:Share Tech Mono,monospace;color:#4ade80;font-size:11px">🟢 ONLINE</div>', unsafe_allow_html=True)
with col_logout:
    if st.button("LOGOUT"):
        st.session_state.authenticated = False
        st.session_state.show_splash   = False
        st.rerun()

st.divider()

df, tasks = fetch_metrics()
if df.empty:
    st.warning("⚠️ Sem dados. Verifique a conexão.")
    st.stop()

latest = df.iloc[0]

# --- KPIs ---
c1,c2,c3,c4 = st.columns(4)
c1.metric("🖥️ CPU LOAD",        f"{latest.get('cpu_usage',0):.1f}%")
c2.metric("🔗 CONEXÕES",        int(latest.get('active_connections',0)))
c3.metric("⏱️ LATÊNCIA",        f"{latest.get('avg_latency_ms',0):.1f}ms")
c4.metric("⚠️ SLOW QUERIES",    int(latest.get('slow_queries_count',0)))

st.divider()

# --- ABAS ---
tab1, tab2, tab3 = st.tabs(["📊  DASHBOARD", "🧠  IA DIAGNÓSTICO", "🔍  PROCESSOS"])

with tab1:
    df_sorted = df.sort_values('timestamp')
    g1,g2 = st.columns(2)
    with g1:
        st.subheader("CPU × TEMPO")
        fig = px.area(df_sorted, x='timestamp', y='cpu_usage', color_discrete_sequence=['#ff4466'], labels={'cpu_usage':'CPU %','timestamp':''})
        fig.update_layout(paper_bgcolor='#04080f', plot_bgcolor='#04080f', font_color='#00ffc377', margin=dict(t=10,b=10))
        fig.update_xaxes(gridcolor='#00ffc308'); fig.update_yaxes(gridcolor='#00ffc308')
        st.plotly_chart(fig, use_container_width=True)
    with g2:
        st.subheader("LATÊNCIA × TEMPO")
        fig2 = px.line(df_sorted, x='timestamp', y='avg_latency_ms', markers=True, color_discrete_sequence=['#00ffc3'], labels={'avg_latency_ms':'ms','timestamp':''})
        fig2.update_layout(paper_bgcolor='#04080f', plot_bgcolor='#04080f', font_color='#00ffc377', margin=dict(t=10,b=10))
        fig2.update_xaxes(gridcolor='#00ffc308'); fig2.update_yaxes(gridcolor='#00ffc308')
        st.plotly_chart(fig2, use_container_width=True)
    st.subheader("CONEXÕES × TEMPO")
    fig3 = px.bar(df_sorted, x='timestamp', y='active_connections', color_discrete_sequence=['#7b2d8b'], labels={'active_connections':'Conexões','timestamp':''})
    fig3.update_layout(paper_bgcolor='#04080f', plot_bgcolor='#04080f', font_color='#00ffc377', margin=dict(t=10,b=10))
    fig3.update_xaxes(gridcolor='#00ffc308'); fig3.update_yaxes(gridcolor='#00ffc308')
    st.plotly_chart(fig3, use_container_width=True)

with tab2:
    st.subheader("DIAGNÓSTICO COM IA")
    st.caption("Análise automática dos dados reais do Supabase via Gemini AI")
    if st.button("🔍 EXECUTAR DIAGNÓSTICO", key="diag"):
        prompt = f"""Você é um DBA Sênior especializado em PostgreSQL e Supabase.
Analise os dados reais de telemetria e forneça um relatório técnico em português:

PROJETO: lbmmdvlxcpkgfnrhdgwt
CPU: {latest.get('cpu_usage')}% | Conexões: {latest.get('active_connections')} | Latência: {latest.get('avg_latency_ms')}ms | Slow Queries: {latest.get('slow_queries_count')}

Forneça:
1. 🏥 DIAGNÓSTICO DE SAÚDE
2. ⚠️ GARGALOS IDENTIFICADOS
3. 🔧 COMANDOS SQL DE TUNING (com blocos de código)
4. 📊 SCORE DE SAÚDE (0-100) com tabela

Seja técnico e direto."""
        with st.spinner("🤖 IA analisando seu banco de dados..."):
            try:
                response = model_ai.generate_content(prompt)
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Erro na API Gemini: {e}")

with tab3:
    st.subheader("PROCESSOS EM EXECUÇÃO")
    if tasks.empty:
        st.info("Nenhum processo ativo.")
    else:
        st.dataframe(tasks, use_container_width=True, hide_index=True)
    with st.expander("📊 Histórico Completo"):
        st.dataframe(df, use_container_width=True, hide_index=True)

# Footer
st.markdown('<div class="helyo-footer">── development by helyo tools ──</div>', unsafe_allow_html=True)
