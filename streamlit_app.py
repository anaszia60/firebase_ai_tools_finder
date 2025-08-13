# streamlit_app.py
import os, time, requests
import streamlit as st
from streamlit_lottie import st_lottie
from firebase_client import auth, db  # db imported in case you add "saved" later

# -------------------------------------------------
# Page
# -------------------------------------------------
st.set_page_config(page_title="AI Tools Finder", layout="wide", page_icon="🧰")

# -------------------------------------------------
# Styles
# -------------------------------------------------
st.markdown("""
<style>
:root { --bg:#121212; --text:#fff; --muted:#bbbbbb; --accent:#13a3b3; --accent2:#764ba2; }

html, body, [data-testid="stAppViewContainer"] { background: var(--bg) !important; color: var(--text) !important; }
h1,h2,h3,h4,h5 { color: var(--text) !important; }
small, .helper { color: var(--muted); }

.center-wrap { display:flex; align-items:center; justify-content:center; min-height: 70vh; }
.card {
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 16px;
  padding: 24px;
  backdrop-filter: blur(10px);
  box-shadow: 0 12px 36px rgba(0,0,0,.25);
  width: 480px;
}

.hero {
  padding: 28px 24px; margin-bottom: 14px;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  border-radius: 18px; color: white; position: relative; overflow: hidden;
  box-shadow: 0 20px 40px rgba(118,75,162,.25);
}
.hero::after {
  content:""; position:absolute; inset:-35%;
  background: radial-gradient(closest-side, rgba(255,255,255,.12), transparent 60%);
  animation: float 8s ease-in-out infinite;
}
@keyframes float { 0%,100%{ transform: translateY(-8px);} 50%{ transform: translateY(8px);} }

.glass-card {
  padding: 18px; margin: 10px 0; opacity: 0; transform: translateY(8px);
  transition: opacity .35s ease, transform .35s ease, box-shadow .35s ease;
  background: rgba(255,255,255,0.06);
  border-radius: 16px; border: 1px solid rgba(255,255,255,0.12);
  backdrop-filter: blur(10px);
}
.glass-card.show { opacity: 1; transform: translateY(0); }
.glass-card h3 { margin: 0 0 8px; }
.glass-card a { color: #b3e9ff; text-decoration: none; }
.glass-card a:hover { text-decoration: underline; }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# Lottie
# -------------------------------------------------
@st.cache_data(show_spinner=False)
def load_lottieurl(url: str):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    return None

lottie_ai = load_lottieurl("https://assets2.lottiefiles.com/packages/lf20_tfb3estd.json")

# -------------------------------------------------
# Session
# -------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None
if "results" not in st.session_state:
    st.session_state.results = []

# -------------------------------------------------
# Auth helpers
# -------------------------------------------------
def parse_auth_error(e: Exception) -> str:
    s = str(e)
    if "EMAIL_EXISTS" in s: return "Email already in use."
    if "EMAIL_NOT_FOUND" in s: return "No account for this email."
    if "INVALID_PASSWORD" in s or "INVALID_LOGIN_CREDENTIALS" in s: return "Wrong password."
    if "USER_DISABLED" in s: return "This account is disabled."
    if "PASSWORD_LOGIN_DISABLED" in s: return "Password login is disabled for this project."
    return f"Auth error: {e}"

def do_login(email: str, password: str):
    try:
        user = auth().sign_in_with_email_and_password(email.strip(), password)
        st.session_state.user = user
        st.toast("Logged in")
    except Exception as e:
        st.error(parse_auth_error(e))

def do_signup(email: str, password: str):
    try:
        auth().create_user_with_email_and_password(email.strip(), password)
        st.success("Account created. You can login now.")
    except Exception as e:
        st.error(parse_auth_error(e))

def do_reset(email: str):
    try:
        auth().send_password_reset_email(email.strip())
        st.success("Password reset email sent.")
    except Exception as e:
        st.error(parse_auth_error(e))

# -------------------------------------------------
# 1) LOGIN-FIRST SCREEN
# -------------------------------------------------
def render_auth_screen():
    st.markdown('<div class="center-wrap">', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)

        # Lottie & Title
        if lottie_ai:
            st_lottie(lottie_ai, height=140, key="ai_anim_login")
        title_ph = st.empty()
        typed = ""
        for ch in "AI Tools Finder":
            typed += ch
            title_ph.markdown(f"<h2 style='text-align:center'>{typed}</h2>", unsafe_allow_html=True)
            time.sleep(0.02)

        # Tabs: Login / Sign up / Forgot
        tabs = st.tabs(["Login", "Sign up", "Forgot password"])
        with tabs[0]:
            em = st.text_input("Email", key="login_email")
            pw = st.text_input("Password", type="password", key="login_pass")
            if st.button("Login", type="primary", use_container_width=True):
                do_login(em, pw)
        with tabs[1]:
            em = st.text_input("Email", key="signup_email")
            pw = st.text_input("Password (min 6 chars)", type="password", key="signup_pass")
            if st.button("Create account", type="primary", use_container_width=True):
                do_signup(em, pw)
        with tabs[2]:
            em = st.text_input("Enter your email", key="reset_email")
            if st.button("Send reset email", type="primary", use_container_width=True):
                if not em.strip():
                    st.warning("Enter your email first.")
                else:
                    do_reset(em)

        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# -------------------------------------------------
# 2) TOOL FINDER (shown only after login)
# -------------------------------------------------
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000/recommend")

def fetch_tools(q: str):
    try:
        resp = requests.post(BACKEND_URL, json={"query": q}, timeout=20)
        if resp.status_code == 200:
            return resp.json().get("tools", [])
        st.error("Backend error. Please try again.")
        return []
    except Exception as e:
        st.error(f"Error connecting to backend: {e}")
        return []

def show_card(tool: dict, delay: float = 0.10):
    with st.container():
        st.markdown('<div class="glass-card show">', unsafe_allow_html=True)
        st.markdown(f"### {tool.get('name','—')}")
        st.write(f"**Year:** {tool.get('year','—')}")
        if tool.get("strengths"):
            st.write(tool["strengths"])
        url = tool.get("website")
        if url:
            st.markdown(f"[Visit]({url})")
        st.markdown('</div>', unsafe_allow_html=True)
    time.sleep(delay)

def ghost_grid(n=6):
    cols = st.columns(3)
    for i in range(n):
        with cols[i % 3]:
            st.markdown('<div class="glass-card show"><h3>—</h3><div class="helper">Waiting for a search…</div></div>', unsafe_allow_html=True)
            time.sleep(0.03)

def render_tool_finder():
    # top bar with logout
    top_left, top_right = st.columns([3,1])
    with top_left:
        if lottie_ai:
            st_lottie(lottie_ai, height=120, key="ai_animation_header")
    with top_right:
        if st.button("Logout", use_container_width=True):
            st.session_state.user = None
            st.toast("Logged out")

    # hero
    st.markdown("""
    <div class="hero">
      <h3>Find the best AI tool for your task</h3>
      <div class="helper">Search by need, budget, or category. Results appear as sleek cards with quick actions.</div>
    </div>
    """, unsafe_allow_html=True)

    # search
    query = st.text_input(
        "What do you need help with? (e.g. remove background, video editing, coding assistant)",
        key="query",
    )
    search_clicked = st.button("Find Tools", type="primary")
    if query and not search_clicked:
        search_clicked = True  # support Enter key

    if search_clicked and query:
        with st.spinner("Finding the best tools for you..."):
            st.session_state.results = fetch_tools(query)

    # cards
    tools = st.session_state.results
    if tools:
        cols = st.columns(3)
        for idx, tool in enumerate(tools):
            with cols[idx % 3]:
                show_card(tool)
    else:
        ghost_grid()

# -------------------------------------------------
# ROUTING: show login first; only show tool finder after auth
# -------------------------------------------------
if st.session_state.user is None:
    render_auth_screen()
else:
    render_tool_finder()
