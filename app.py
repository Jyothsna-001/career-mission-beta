import streamlit as st
from groq import Groq
import docx2txt
import PyPDF2
import io
import re
from streamlit_agraph import agraph, Node, Edge, Config

# --- 1. DYNAMIC UI & STYLING ---
st.set_page_config(page_title="Career Mission Command", page_icon="🎖️", layout="wide")

if "xp" not in st.session_state: st.session_state.xp = 0

sidebar_bg = "#0f172a" 
if st.session_state.xp >= 500:
    sidebar_bg = "linear-gradient(180deg, #0f172a 0%, #451a03 100%)" 
elif st.session_state.xp >= 300:
    sidebar_bg = "linear-gradient(180deg, #0f172a 0%, #1e293b 100%)" 

st.markdown(f"""
    <style>
    .stApp {{ background-color: #f8fafc; }}
    [data-testid="stSidebar"] {{ background: {sidebar_bg} !important; border-right: 3px solid #38bdf8; transition: background 1s ease; }}
    [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] label, [data-testid="stSidebar"] [data-testid="stMetricValue"] {{ color: #ffffff !important; }}
    [data-testid="stSidebar"] button {{ color: #0f172a !important; font-weight: bold; }}
    .stTextInput input {{ border: 2px solid #38bdf8 !important; border-radius: 6px !important; padding: 12px !important; font-size: 1.05rem !important; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 24px; }}
    .stTabs [data-baseweb="tab"] {{ height: 50px; white-space: pre-wrap; font-size: 1.1rem; font-weight: bold; color: #475569; }}
    .stTabs [aria-selected="true"] {{ color: #0f172a !important; border-bottom: 4px solid #38bdf8 !important; }}
    .archive-btn {{ background: #e2e8f0; color: #0f172a; padding: 8px 12px; border-radius: 5px; margin-bottom: 8px; font-size: 0.95rem; border-left: 4px solid #38bdf8; }}
    
    .sticky-note {{
        background-color: #fef08a; 
        color: #1f2937 !important;
        padding: 15px;
        border-radius: 2px 15px 15px 15px;
        box-shadow: 2px 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        font-size: 0.9rem;
        line-height: 1.5;
        border-left: 5px solid #eab308;
    }}
    .sticky-note b {{ color: #1f2937 !important; }}
    
    /* Premium Button Styling */
    .premium-btn {{
        background-color: #f59e0b; color: white !important; font-weight: bold; text-align: center; 
        padding: 10px; border-radius: 5px; text-decoration: none; display: block; margin-top: 10px;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. HEADER ---
st.markdown("<h1 style='text-align: left; color: #0f172a;'>🎖️ Career Mission Command</h1>", unsafe_allow_html=True)

try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ API Key Error.")
    st.stop()

# --- 3. STATE MEMORY ---
if "strat_history" not in st.session_state: st.session_state.strat_history = []
if "strat_questions" not in st.session_state: st.session_state.strat_questions = []
if "arena_history" not in st.session_state: st.session_state.arena_history = [{"role": "assistant", "content": "Welcome to the Proving Grounds. Your selected map target is loaded."}]
if "doc_context" not in st.session_state: st.session_state.doc_context = ""
if "skill_tree" not in st.session_state: st.session_state.skill_tree = {}
if "active_map_node" not in st.session_state: st.session_state.active_map_node = None
if "trigger_quick_test" not in st.session_state: st.session_state.trigger_quick_test = False
if "vault_intel" not in st.session_state: st.session_state.vault_intel = "" 
if "is_premium" not in st.session_state: st.session_state.is_premium = False 

if "audio_strat" not in st.session_state: st.session_state.audio_strat = 0
if "text_strat" not in st.session_state: st.session_state.text_strat = ""
if "audio_arena" not in st.session_state: st.session_state.audio_arena = 0
if "text_arena" not in st.session_state: st.session_state.text_arena = ""

def extract_text(file):
    try:
        if file.name.endswith(".pdf"): return " ".join([p.extract_text() for p in PyPDF2.PdfReader(file).pages])[:5000]
        return docx2txt.process(io.BytesIO(file.read()))[:5000]
    except: return ""

# --- 4. SIDEBAR ---
with st.sidebar:
    if st.session_state.xp >= 500: rank = "Strategic General 🎖️🏆"
    elif st.session_state.xp >= 300: rank = "Intelligence Officer 🕵️🥈"
    else: rank = "Bootcamp Recruit 🥾"
        
    st.markdown(f"## {rank}")
    st.progress(min(st.session_state.xp / 500, 1.0))
    st.write(f"**Total XP:** {st.session_state.xp} / 500")
    
    st.divider()
    model_choice = st.selectbox("Engine:", ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"])
    
    st.markdown("""
    <div class="sticky-note">
        <b>📌 Field Manual</b><br>
        1️⃣ <b>Strategy:</b> Ask for a roadmap to deploy your map.<br>
        2️⃣ <b>Target:</b> Click a node on the map to lock it in.<br>
        3️⃣ <b>Proving Grounds:</b> Hit <i>⚡ Quick Test</i> to answer PYQs & earn XP. You can grind the same subject for multiple points!<br>
        4️⃣ <b>Unlock:</b> Hit 200 XP to crack the Vault. Hit 400 XP for the Boss Battle!
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    st.markdown("### 🔐 Classified Vault")
    if st.session_state.xp >= 200:
        if not st.session_state.is_premium:
            st.warning("🛑 Premium Intel Locked.")
            st.markdown("You have proven your skills. Upgrade to Premium to instantly generate custom cheat sheets for your active subjects.")
            st.markdown("<a href='#' class='premium-btn'>💳 Unlock Premium (₹999)</a>", unsafe_allow_html=True)
            
            if st.button("Unlock for Free (Dev Mode)"):
                st.session_state.is_premium = True
                st.rerun()
        else:
            st.success("🔓 Vault Unlocked!")
            if not st.session_state.vault_intel:
                with st.spinner("Decrypting custom intel..."):
                    active_topics = ", ".join(st.session_state.skill_tree.keys()) if st.session_state.skill_tree else "General Exam Topics"
                    vault_prompt = f"""You are a master tutor. Create a highly useful, dense study cheat sheet for the following topics: {active_topics}. 
                    CRITICAL INSTRUCTION: DO NOT GIVE GENERIC ADVICE. Give actual hard data. 
                    - If the topics are Math/Quant: Provide 10-15 actual mathematical formulas. 
                    - If the topics are English: Provide 10 critical grammar rules or vocabulary words with meanings.
                    - If the topics are Finance/Accounting/Law: Provide 10 key sections, standards, or accounting principles.
                    Output ONLY plain text. Do not use markdown styling."""
                    
                    try:
                        res = client.chat.completions.create(messages=[{"role": "system", "content": vault_prompt}], model=model_choice)
                        st.session_state.vault_intel = res.choices[0].message.content
                    except Exception as e:
                        st.session_state.vault_intel = f"Intel retrieval failed. Error: {e}"

            st.download_button("📥 Download Custom Intel (TXT)", data=st.session_state.vault_intel, file_name="Targeted_CheatSheet.txt")
    else:
        st.warning(f"🔒 Decryption requires 200 XP.")
    
    st.divider()
    up_file = st.file_uploader("Upload Intel", type=["pdf", "docx"])
    if up_file:
        st.session_state.doc_context = extract_text(up_file)
        st.success("✅ Context Synced")
        
    if st.button("🗑️ Reset Application"):
        st.session_state.clear()
        st.rerun()

# --- 5. MAIN LAYOUT ---
col_main, col_tree = st.columns([3, 2], gap="large")

with col_tree:
    st.subheader("🗺️ Interactive Journey Map")
    if not st.session_state.skill_tree:
        st.info("Ask for a roadmap in the Strategy Tab to deploy your interactive map.")
    else:
        nodes = []
        edges = []
        topic_names = list(st.session_state.skill_tree.keys())
        
        for i, topic in enumerate(topic_names):
            data = st.session_state.skill_tree[topic]
            is_boss = "CRUCIBLE" in topic.upper()
            
            if is_boss:
                size = 50
                color = "#fef3c7" if data["status"] == "Mastered" else "#fecaca" 
                font_color = "#d97706" if data["status"] == "Mastered" else "#991b1b" 
            else:
                size = 40 if data["weight"] == "High" else (30 if data["weight"] == "Medium" else 20)
                color = "#fef3c7" if data["status"] == "Mastered" else "#e0f2fe"
                font_color = "#d97706" if data["status"] == "Mastered" else "#0369a1"
            
            nodes.append(Node(id=topic, label=topic, size=size, color=color, shape="dot", font={'color': font_color, 'face': 'sans-serif', 'weight': 'bold'}))
            if i > 0:
                edges.append(Edge(source=topic_names[i-1], target=topic, color="#cbd5e1"))

        config = Config(width="100%", height=400, directed=True, physics=True, hierarchical=False)
        clicked_node = agraph(nodes=nodes, edges=edges, config=config)
        
        if clicked_node:
            st.session_state.active_map_node = clicked_node
            
        if st.session_state.active_map_node:
            st.markdown(f"""
                <div style="background-color: #f1f5f9; padding: 15px; border-radius: 10px; border-left: 5px solid #0f172a; margin-top: 10px;">
                    <h4 style="color: #0f172a; margin-top: 0;">🎯 Target: {st.session_state.active_map_node}</h4>
                    <p style="color: #334155; font-size: 0.95rem;">Switch to the <b>Proving Grounds</b> and hit <b>Quick Test</b>.</p>
                </div>
            """, unsafe_allow_html=True)

with col_main:
    tab_strat, tab_arena = st.tabs(["🗺️ Strategy Command", "⚔️ Proving Grounds"])
    
    # --- TAB 1: STRATEGY ---
    with tab_strat:
        trigger_strat_query = False
        strat_query_payload = ""

        if st.session_state.strat_questions:
            with st.expander("🗂️ Strategy Archive (Click to reload)"):
                for i, q in enumerate(st.session_state.strat_questions):
                    if st.button(f"🔎 {q}", key=f"hist_btn_{i}", use_container_width=True):
                        trigger_strat_query = True
                        strat_query_payload = q
        
        chat_box_strat = st.container(height=350)
        for msg in st.session_state.strat_history:
            chat_box_strat.chat_message(msg["role"]).markdown(msg["content"])
            
        st.markdown("---")
        
        v_col1, t_col1 = st.columns([1, 4])
        with v_col1:
            audio1 = st.audio_input("Mic 1", key=f"mic1_{st.session_state.audio_strat}", label_visibility="collapsed")
            if audio1:
                try:
                    trans = client.audio.transcriptions.create(file=("a.wav", audio1.read()), model="whisper-large-v3-turbo")
                    st.session_state.text_strat = trans.text
                    st.session_state.audio_strat += 1 
                    st.rerun()
                except: st.error("Mic Error")
        
        with t_col1:
            with st.form(key="strat_form", clear_on_submit=True):
                user_strat = st.text_input("Ask for strategy or roadmaps:", value=st.session_state.text_strat)
                sub1, clr1 = st.columns(2)
                
                if sub1.form_submit_button("🚀 SEND TO STRATEGIST") and user_strat.strip():
                    trigger_strat_query = True
                    strat_query_payload = user_strat.strip()
                
                if clr1.form_submit_button("🗑️ CLEAR"): 
                    st.session_state.text_strat = ""
                    st.session_state.strat_history = []
                    st.rerun()
                    
        if trigger_strat_query and strat_query_payload:
            st.session_state.text_strat = ""
            st.session_state.strat_history.append({"role": "user", "content": strat_query_payload})
            if strat_query_payload not in st.session_state.strat_questions:
                st.session_state.strat_questions.append(strat_query_payload)
            
            try:
                sys_msg1 = f"""You are a Career Planner. Context: {st.session_state.doc_context}.
                CRITICAL INSTRUCTIONS:
                1. Keep your conversational advice VERY short (max 2-3 sentences). 
                2. STRICTLY PROSE: You are completely FORBIDDEN from using bullet points, numbered lists, or headings.
                3. FACTUAL ACCURACY: Verify the EXACT level of the examination (e.g., CA Inter vs CA Final). Strictly output ONLY subjects belonging to that specific level.
                """
                
                api_messages = [{"role": "system", "content": sys_msg1}] + st.session_state.strat_history[:-1]
                injected_prompt = st.session_state.strat_history[-1]["content"] + "\n\n[CRITICAL: You MUST end your response with exactly 4 subjects using this exact format on a new line: [TREE: Topic 1 (High) | Topic 2 (Medium) | Topic 3 (Low) | Topic 4 (High)]]"
                api_messages.append({"role": "user", "content": injected_prompt})
                
                res = client.chat.completions.create(messages=api_messages, model=model_choice)
                ans = res.choices[0].message.content
                
                raw_topics = []
                for line in ans.split('\n'):
                    if '|' in line and any(w in line for w in ["(High)", "(Medium)", "(Low)", "(high)", "(medium)", "(low)"]):
                        clean_line = re.sub(r"(?i)\[?TREE:?\]?\s*", "", line)
                        clean_line = clean_line.replace("**", "")
                        raw_topics = clean_line.split("|")
                        ans = ans.replace(line, "") 
                        break
                
                if raw_topics:
                    st.session_state.skill_tree = {}
                    for t in raw_topics:
                        t = re.sub(r"(?i)\[?TREE:?\]?", "", t).replace("**", "").replace("[", "").replace("]", "").strip() 
                        t = re.sub(r"^[-:]\s*", "", t) 
                        
                        weight = "Medium"
                        if "(High)" in t or "(high)" in t: weight = "High"; t = re.sub(r"(?i)\(High\)", "", t).strip()
                        elif "(Low)" in t or "(low)" in t: weight = "Low"; t = re.sub(r"(?i)\(Low\)", "", t).strip()
                        elif "(Medium)" in t or "(medium)" in t: t = re.sub(r"(?i)\(Medium\)", "", t).strip()
                        
                        if len(t) > 2: 
                            st.session_state.skill_tree[t] = {"status": "Active", "weight": weight}
                    
                    st.session_state.active_map_node = None
                    st.session_state.vault_intel = "" 
                    
                    if not ans.strip(): ans = "Roadmap generated. Check the Interactive Map."
                    st.session_state.strat_history.append({"role": "assistant", "content": ans.strip()})
                    st.rerun()
                else:
                    if len(st.session_state.strat_history) > 0:
                        st.session_state.strat_history.pop() 
                    st.error("⚠️ AI Formatting Error: The AI failed to generate the map correctly. Please try again.")
            except Exception as e:
                if len(st.session_state.strat_history) > 0:
                    st.session_state.strat_history.pop()
                st.error(f"⚠️ API Connection Error: {e}")

    # --- TAB 2: PROVING GROUNDS ---
    with tab_arena:
        target_node = st.session_state.active_map_node if st.session_state.active_map_node else "None"
        
        if st.session_state.skill_tree:
            d_col1, d_col2 = st.columns([3, 1])
            with d_col1:
                options = list(st.session_state.skill_tree.keys())
                index = options.index(target_node) if target_node in options else 0
                target_node = st.selectbox("🎯 Target Node:", options, index=index, label_visibility="collapsed")
                st.session_state.active_map_node = target_node
            with d_col2:
                if st.button("⚡ Quick Test", use_container_width=True):
                    st.session_state.trigger_quick_test = True
                    st.rerun()
        else:
            st.warning("Generate a map in the Strategy Tab first.")
        
        chat_box_arena = st.container(height=300)
        for msg in st.session_state.arena_history:
            chat_box_arena.chat_message(msg["role"]).markdown(msg["content"])
            
        st.markdown("---")
        
        v_col2, t_col2 = st.columns([1, 4])
        with v_col2:
            audio2 = st.audio_input("Mic 2", key=f"mic2_{st.session_state.audio_arena}", label_visibility="collapsed")
            if audio2:
                try:
                    trans = client.audio.transcriptions.create(file=("a.wav", audio2.read()), model="whisper-large-v3-turbo")
                    st.session_state.text_arena = trans.text
                    st.session_state.audio_arena += 1 
                    st.rerun()
                except: st.error("Mic Error")
                
        with t_col2:
            with st.form(key="arena_form", clear_on_submit=True):
                user_arena = st.text_input("Answer or request a PYQ:", value=st.session_state.text_arena)
                sub2, clr2 = st.columns(2)
                
                trigger_submit = sub2.form_submit_button("⚔️ SEND TO EXAMINER")
                
                if (trigger_submit and user_arena.strip()) or st.session_state.trigger_quick_test:
                    st.session_state.trigger_quick_test = False
                    st.session_state.text_arena = "" 
                    
                    display_text = f"Deploying test for {target_node}..." if not user_arena.strip() else user_arena
                    api_prompt = f"Give me a PYQ for {target_node}" if not user_arena.strip() else user_arena
                    st.session_state.arena_history.append({"role": "user", "content": display_text})
                    
                    try:
                        is_boss = "CRUCIBLE" in target_node.upper()
                        boss_instruction = "This is the FINAL BOSS. Ask a highly difficult question." if is_boss else "Ask a standard PYQ."
                        
                        sys_msg2 = f"""You are a strict Examiner. Context: {st.session_state.doc_context}. TARGET TOPIC: {target_node}.
                        1. {boss_instruction}
                        2. MANDATORY FORMAT: You MUST ask ONE Multiple Choice Question (MCQ) with exactly four options labeled A, B, C, and D. STRICTLY PROSE: Do NOT use bullet points or headings."""
                        
                        injected_arena_prompt = api_prompt + f"\n\n[CRITICAL: If the user's answer is CORRECT, you MUST output exactly this tag at the very end of your response: [MASTER: {target_node}]. If the user is WRONG, explain why but do NOT output the tag.]"
                        
                        arena_api_messages = [{"role": "system", "content": sys_msg2}] + st.session_state.arena_history[:-1]
                        arena_api_messages.append({"role": "user", "content": injected_arena_prompt})
                        
                        res = client.chat.completions.create(messages=arena_api_messages, model=model_choice)
                        ans = res.choices[0].message.content
                        
                        m_matches = re.findall(r"\[MASTER:\s*(.*?)\s*\]", ans, re.IGNORECASE)
                        if m_matches:
                            st.session_state.xp += 50
                            st.balloons()
                            st.toast("🎯 Correct! +50 XP Earned!", icon="🔥")
                            
                            for match in m_matches:
                                pillar = match.strip().lower()
                                for key in st.session_state.skill_tree.keys():
                                    if pillar in key.lower() or key.lower() in pillar:
                                        if st.session_state.skill_tree[key]["status"] != "Mastered":
                                            st.session_state.skill_tree[key]["status"] = "Mastered"
                                            st.toast(f"⭐ Node Mastered: {key}", icon="🗺️")
                            
                            if st.session_state.xp >= 400 and "👑 THE CRUCIBLE (Boss Exam)" not in st.session_state.skill_tree:
                                st.session_state.skill_tree["👑 THE CRUCIBLE (Boss Exam)"] = {"status": "Active", "weight": "High"}
                                st.toast("🚨 BOSS BATTLE UNLOCKED! 🚨", icon="🚨")
                                
                        ans = re.sub(r"(?i)\[MASTER:.*?\]", "", ans).strip()
                        if not ans: ans = "Correct!"
                        st.session_state.arena_history.append({"role": "assistant", "content": ans})
                        st.rerun()
                    except Exception as e:
                        if len(st.session_state.arena_history) > 0:
                            st.session_state.arena_history.pop() 
                        st.error(f"⚠️ API Connection Error: {e}")
                
                if clr2.form_submit_button("🗑️ CLEAR"): 
                    st.session_state.text_arena = ""
                    st.session_state.arena_history = [{"role": "assistant", "content": "Welcome back."}]
                    st.rerun()