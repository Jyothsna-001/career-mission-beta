import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
import docx2txt
import PyPDF2
import io
import re
import json
import os
from streamlit_agraph import agraph, Node, Edge, Config

# --- 1. STATE MEMORY, PROFILES & EXAM DATABASE ---
st.set_page_config(page_title="AI Exam Coach", page_icon="🎓", layout="wide")

PROFILE_FILE = "user_profiles.json"

def init_state():
    """CRITICAL FIX: Forces all variables to exist to prevent AttributeErrors."""
    defaults = {
        "current_user": "Guest",
        "current_password": "",
        "xp": 0,
        "audio_strat": 0,
        "audio_arena": 0,
        "just_leveled_up": False,
        "last_answer_correct": False,
        "show_wrong_animation": False,
        "play_correct_anim": False,
        "play_wrong_anim": False,
        "reached_max_level": False,
        "is_premium": False,
        "trigger_quick_test": False,
        "vault_celebrated": False,
        "tour_done": False,
        "boss_popup_cleared": False,
        "auto_scroll_strat": False,
        "auto_scroll_arena": False,
        "arena_tour_done": False,
        "just_unlocked_200": False,
        "is_paused": False,
        "current_file": None,
        "active_map_node": None,
        "active_main_tab": "🗺️ Step 1: Study Planner",
        "archive_trigger_payload": None,
        "scroll_target": None,
        "doc_context": "",
        "vault_intel": "",
        "text_strat": "",
        "text_arena": "",
        "tour_step": 0,
        "strat_history": [],
        "strat_questions": [],
        "skill_tree": {},
        "full_skill_tree": {},
        "arena_history": [{"role": "assistant", "content": "Welcome to the Practice Arena. Select a phase from the map above and hit Quick Test!"}]
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# Initialize all variables immediately
init_state()

def get_save_data():
    """Bundles user data for saving."""
    return {
        "xp": st.session_state.xp,
        "skill_tree": st.session_state.skill_tree,
        "full_skill_tree": st.session_state.full_skill_tree,
        "strat_history": st.session_state.strat_history,
        "strat_questions": st.session_state.strat_questions,
        "arena_history": st.session_state.arena_history,
        "active_map_node": st.session_state.active_map_node,
        "is_premium": st.session_state.is_premium
    }

def load_profiles():
    if os.path.exists(PROFILE_FILE):
        try:
            with open(PROFILE_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_profile(username, password, data):
    profiles = load_profiles()
    profiles[username] = {"password": password, "data": data}
    with open(PROFILE_FILE, "w") as f:
        json.dump(profiles, f)

EXAM_DATABASE = {
    "ca inter": "CA Intermediate (ICAI): Group 1 (Adv Accounting, Corporate & Other Laws, Taxation) and Group 2 (Cost & Mgmt Accounting, Auditing & Ethics, FM & SM). CRITICAL RULE: All 6 papers are mandatory. DO NOT ask the user to choose a specialization or branch.",
    "rrb clerk": "IBPS RRB Clerk: 1. Reasoning Ability, 2. Numerical Aptitude, 3. General Awareness, 4. English Language. CRITICAL: Focus on English. DO NOT INCLUDE COMPUTER KNOWLEDGE.",
    "rrb po": "RRB PO: Reasoning Ability (High), Quantitative Aptitude (High), General Awareness (Medium), English Language (Medium), Computer Knowledge (Low).",
    "ssc cgl": "SSC CGL Tier 1: General Intelligence and Reasoning, General Awareness, Quantitative Aptitude, English Comprehension.",
    "eamcet bipc": "EAMCET BiPC (Medical): Botany, Zoology, Physics, Chemistry. STRICTLY NO MATHS.",
    "jee": "JEE Main: Physics, Chemistry, Mathematics.",
    "bank po": "Bank PO Prelims: English Language, Quantitative Aptitude, Reasoning Ability.",
    "kv": "Kendriya Vidyalaya (KVS) Teaching Interview: Subject Pedagogy, Classroom Management, Child Psychology & NEP 2020, Demo Teaching.",
    "teaching": "Teaching Interview: Subject Knowledge, Lesson Planning, Classroom Management, Student Assessment.",
    "interview": "Corporate Job Interview Prep: Technical Skills Assessment, HR & Behavioral Questions, Company Research & Culture Fit, Resume Walkthrough.",
    "ugc net": "UGC NET: Paper 1 (Teaching & Research Aptitude, Reasoning, Reading Comp). Paper 2 (Candidate's chosen specialized subject)."
}

# GLOBAL LOCKS
is_touring = st.session_state.tour_step > 0
is_locked = is_touring or st.session_state.is_paused

# DYNAMIC JS SCROLLER
if st.session_state.scroll_target:
    components.html(f"""
        <script>
        setTimeout(function() {{
            const el = window.parent.document.getElementById('{st.session_state.scroll_target}');
            if(el) {{ el.scrollIntoView({{behavior: 'smooth', block: 'center'}}); }}
        }}, 400);
        </script>
    """, height=0, width=0)
    st.session_state.scroll_target = None 

# BUTTON COLOR SCRIPT
if is_touring:
    components.html("""
        <script>
        const observer = new MutationObserver(() => {
            const buttons = window.parent.document.querySelectorAll('button');
            buttons.forEach(btn => {
                if(btn.innerText.includes('Go to Step 2')) { btn.style.backgroundColor = '#3b82f6'; btn.style.color = 'white'; btn.style.border = 'none'; btn.style.fontWeight = 'bold';}
                if(btn.innerText.includes('Go to Step 3')) { btn.style.backgroundColor = '#10b981'; btn.style.color = 'white'; btn.style.border = 'none'; btn.style.fontWeight = 'bold';}
                if(btn.innerText.includes('Go to Step 4')) { btn.style.backgroundColor = '#8b5cf6'; btn.style.color = 'white'; btn.style.border = 'none'; btn.style.fontWeight = 'bold';}
                if(btn.innerText.includes('Go to Step 5')) { btn.style.backgroundColor = '#f97316'; btn.style.color = 'white'; btn.style.border = 'none'; btn.style.fontWeight = 'bold';}
                if(btn.innerText.includes('Go to Step 6')) { btn.style.backgroundColor = '#ec4899'; btn.style.color = 'white'; btn.style.border = 'none'; btn.style.fontWeight = 'bold';}
                if(btn.innerText.includes('End Tour')) { btn.style.backgroundColor = '#06b6d4'; btn.style.color = 'white'; border: 'none'; font-weight: 'bold';}
            });
        });
        observer.observe(window.parent.document.body, {childList: true, subtree: true});
        </script>
    """, height=0, width=0)

# --- APP TOUR ONBOARDING MODAL ---
if not st.session_state.tour_done:
    st.markdown("""
        <style>
        .tour-container { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 40px; border-radius: 20px; text-align: center; color: white; box-shadow: 0px 20px 40px rgba(0,0,0,0.3); margin-bottom: 30px; border: 2px solid #38bdf8; }
        .tour-step { font-size: 1.1rem; margin: 12px 0; text-align: left; padding-left: 20px;}
        </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown("""
            <div class="tour-container">
                <h1 style="color: white; font-size: 3rem;">👋 Welcome to your AI Exam Coach!</h1>
                <p style="font-size: 1.2rem; color: #cbd5e1;">Your personalized, gamified study companion. Here is how it works:</p>
                <div style="background: rgba(255,255,255,0.1); padding: 20px; border-radius: 15px; display: inline-block; text-align: left; margin-top: 15px;">
                    <div class="tour-step"><b>1️⃣ Study Planner:</b> Tell the AI what you are studying to get a strategy.</div>
                    <div class="tour-step"><b>2️⃣ Interactive Map:</b> The AI builds a custom visual syllabus roadmap.</div>
                    <div class="tour-step"><b>3️⃣ Practice Arena:</b> Click a circle on your map to take dynamic practice tests.</div>
                    <div class="tour-step"><b>4️⃣ Resume & Notes:</b> Upload your CV or syllabus for the AI to analyze.</div>
                    <div class="tour-step"><b>5️⃣ Rewards Center:</b> Earn XP to unlock Cheat Sheets and the Final Boss Exam!</div>
                    <div class="tour-step"><b>6️⃣ Profiles & Saving:</b> Save your progress locally so you never lose your spot.</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("🚀 Got it! Start the Tour", use_container_width=True, type="primary"):
            st.session_state.tour_done = True
            st.session_state.tour_step = 1
            st.session_state.scroll_target = "step-1-anchor"
            st.rerun()
    st.stop() 

# --- BOSS EXAM HARD STOP POPUP ---
if st.session_state.xp >= 500 and not st.session_state.boss_popup_cleared:
    st.markdown("""
        <style>
        .boss-container { background: linear-gradient(135deg, #4c0519 0%, #881337 100%); padding: 50px; border-radius: 20px; text-align: center; color: white; box-shadow: 0px 20px 40px rgba(0,0,0,0.6); margin-top: 50px; border: 4px solid #f43f5e; }
        .boss-text { font-size: 1.3rem; margin: 20px 0; line-height: 1.7; }
        </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown("""
            <div class="boss-container">
                <h1 style="color: #fecdd3; font-size: 3.5rem;">🎉 500 XP REACHED! 🎉</h1>
                <h2 style="color: white; margin-top: 0;">👑 THE CRUCIBLE UNLOCKED</h2>
                <p class="boss-text">You have proven your mastery by earning 500 points! As a reward, a new, special red node called <b>"👑 THE CRUCIBLE (Boss Exam)"</b> has been added to your Interactive Map.</p>
                <p class="boss-text">If you click it and ask for a Quick Test, the AI switches into <b>Final Boss</b> mode.</p>
                <p class="boss-text">Instead of asking a basic question about just one topic, the AI will generate a highly difficult, integrated question that combines multiple subjects at once to truly test your preparation!</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("⚔️ Continue to The Crucible", use_container_width=True, type="primary"):
            st.session_state.boss_popup_cleared = True
            st.session_state.full_skill_tree = st.session_state.skill_tree.copy()
            st.session_state.skill_tree = {"👑 THE CRUCIBLE (Boss Exam)": {"status": "Active", "weight": "High"}}
            st.session_state.active_map_node = "👑 THE CRUCIBLE (Boss Exam)"
            st.session_state.active_main_tab = "⚔️ Step 2: Practice Arena"
            st.rerun()
    st.stop() 

# --- AUDIO & VISUAL INJECTION SYSTEM ---
if st.session_state.get("play_correct_anim", False):
    st.balloons()
    st.markdown("""
        <div style="position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(0,0,0,0.6); z-index:9999; display:flex; justify-content:center; align-items:center; animation: fadeOut 1.5s forwards; pointer-events: none;">
            <div style="font-size: 80px; animation: popIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); background: white; padding: 40px; border-radius: 30px; text-align: center; box-shadow: 0px 20px 40px rgba(0,0,0,0.5);">
                🎉 🏆 <br><span style="font-size: 45px; color: #16a34a; font-family: sans-serif; font-weight: bold;">BOOM! Correct! +50 XP</span>
            </div>
        </div>
        <style>@keyframes popIn { 0% { transform: scale(0); opacity: 0; } 100% { transform: scale(1); opacity: 1; } } @keyframes fadeOut { 0% { opacity: 1; } 70% { opacity: 1; } 100% { opacity: 0; } }</style>
    """, unsafe_allow_html=True)
    st.session_state.play_correct_anim = False 

if st.session_state.get("play_wrong_anim", False):
    st.snow()
    st.markdown("""
        <div style="position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(0,0,0,0.6); z-index:9999; display:flex; justify-content:center; align-items:center; animation: fadeOut 1.5s forwards; pointer-events: none;">
            <div style="font-size: 100px; animation: popIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); background: white; padding: 40px; border-radius: 30px; text-align: center; box-shadow: 0px 20px 40px rgba(0,0,0,0.5);">
                😢 ❌ <br><span style="font-size: 35px; color: #e11d48; font-family: sans-serif; font-weight: bold;">Incorrect! Read the hint!</span>
            </div>
        </div>
        <style>@keyframes popIn { 0% { transform: scale(0); opacity: 0; } 100% { transform: scale(1); opacity: 1; } } @keyframes fadeOut { 0% { opacity: 1; } 70% { opacity: 1; } 100% { opacity: 0; } }</style>
    """, unsafe_allow_html=True)
    st.session_state.play_wrong_anim = False 

# --- 2. DYNAMIC UI & STYLING ---
sidebar_bg = "#0f172a" 
if st.session_state.xp >= 500: sidebar_bg = "linear-gradient(180deg, #0f172a 0%, #451a03 100%)" 
elif st.session_state.xp >= 300: sidebar_bg = "linear-gradient(180deg, #0f172a 0%, #1e293b 100%)" 

bg_css = "linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)" 
bg_emoji = "🎯 🚀 📚 🎓 " * 40 

history_text = " ".join([msg["content"] for msg in st.session_state.strat_history]).lower()
is_junior = any(w in history_text for w in ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th", "class", "grade", "school", "kid", "child"])

if st.session_state.active_map_node:
    topic_lower = str(st.session_state.active_map_node).lower()
    if any(w in topic_lower for w in ["math", "quant", "algebra", "calculus", "equation", "number", "numer", "data", "arithmetic", "circuit"]):
        bg_css = "linear-gradient(135deg, #a5f3fc 0%, #7dd3fc 100%)" if is_junior else "linear-gradient(135deg, #f1f5f9 0%, #e0f2fe 100%)"
        bg_emoji = "📐 🔢 ➗ 📊 " * 40
    elif any(w in topic_lower for w in ["english", "verbal", "grammar", "reading", "comprehension", "vocab", "hindi", "language"]):
        bg_css = "linear-gradient(135deg, #fdba74 0%, #fca5a5 100%)" if is_junior else "linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%)"
        bg_emoji = "📚 ✍️ 🗣️ 📝 " * 40
    elif any(w in topic_lower for w in ["reasoning", "logic", "intelligence", "analytical"]):
        bg_css = "linear-gradient(135deg, #e9d5ff 0%, #d8b4fe 100%)" if is_junior else "linear-gradient(135deg, #fdf4ff 0%, #f3e8ff 100%)"
        bg_emoji = "🧩 🧠 💡 🔍 " * 40

# DIM OVERLAY FOR PAUSE STATE
pause_overlay = ""
if st.session_state.is_paused:
    pause_overlay = """
    <div style="position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(0,0,0,0.3); z-index:999; pointer-events:none; display:flex; justify-content:center; align-items:center;">
        <div style="background:white; padding:20px 40px; border-radius:10px; border:4px solid #3b82f6; font-size:2rem; font-weight:bold; color:#1e40af; box-shadow:0px 10px 30px rgba(0,0,0,0.5);">
            ⏸️ SESSION PAUSED - Awaiting your return.
        </div>
    </div>
    """

st.markdown(f"""
    <div style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 0; opacity: 0.15; font-size: 90px; display: flex; flex-wrap: wrap; justify-content: center; align-items: center; pointer-events: none; user-select: none; text-align: center; line-height: 1.6; text-shadow: 2px 2px 4px rgba(0,0,0,0.1);">
        {bg_emoji}
    </div>
    {pause_overlay}
""", unsafe_allow_html=True)

# --- SIDEBAR SPOTLIGHT CSS FOR TOUR STEPS 4, 5, AND 6 ---
if st.session_state.tour_step >= 4:
    st.markdown("""<style>.main { filter: brightness(0.4) blur(2px) !important; pointer-events: none !important; transition: all 0.5s ease; } [data-testid="stSidebar"] { z-index: 99999 !important; box-shadow: 0 0 0 9999px rgba(0,0,0,0.7) !important; border-right: 5px solid #f97316 !important; transition: all 0.5s ease; }</style>""", unsafe_allow_html=True)
if st.session_state.tour_step == 6:
    st.markdown("""<style>[data-testid="stSidebar"] { border-right: 5px solid #06b6d4 !important; }</style>""", unsafe_allow_html=True)

st.markdown(f"""
    <style>
    .stApp {{ background: {bg_css} !important; transition: background 0.8s ease-in-out; }}
    .main {{ z-index: 1; position: relative; }} 
    
    [data-testid="stChatMessageContent"] div {{ font-size: 1.3rem !important; line-height: 1.7 !important; color: #0f172a !important; }}
    h1 {{ font-size: 2.8rem !important; }} h2 {{ font-size: 2.2rem !important; }} h3 {{ font-size: 1.6rem !important; }}
    
    /* CUSTOM LOCKED TABS */
    .st-key-main_tabs [role="radiogroup"] {{ flex-direction: row !important; flex-wrap: nowrap !important; border-bottom: 4px solid #cbd5e1; gap: 30px; }}
    .st-key-main_tabs div[role="radio"] {{ display: none !important; }} 
    .st-key-main_tabs label {{ cursor: pointer; padding-bottom: 10px; white-space: nowrap !important; display: inline-block !important; }}
    .st-key-main_tabs label p {{ font-size: 1.6rem !important; font-weight: bold !important; color: #475569 !important; white-space: nowrap !important; margin:0; }}
    .st-key-main_tabs label[data-checked="true"] p {{ color: #0f172a !important; border-bottom: 5px solid #38bdf8; padding-bottom: 5px; }}
    
    /* ENHANCED RADIO CHECKBOXES - FIXED OPTIONS SQUISHING */
    .st-key-arena_radio [role="radiogroup"] {{ display: flex; flex-direction: row !important; gap: 15px; flex-wrap: wrap; margin-bottom: 15px; }}
    .st-key-arena_radio [role="radiogroup"] > label {{ background-color: #f8fafc !important; border: 2px solid #cbd5e1 !important; border-radius: 8px !important; padding: 10px 20px !important; cursor: pointer !important; transition: all 0.2s !important; width: 80px; text-align: center; display:flex; align-items:center; justify-content:center;}}
    .st-key-arena_radio [role="radiogroup"] > label:hover {{ border-color: #38bdf8 !important; background: #f0f9ff !important; }}
    .st-key-arena_radio [role="radiogroup"] > label[data-checked="true"] {{ border-color: #0ea5e9 !important; background-color: #bae6fd !important; border-width: 3px !important; box-shadow: 0 4px 6px rgba(2, 132, 199, 0.2) !important; }}
    .st-key-arena_radio [role="radiogroup"] > label p {{ font-size: 1.3rem !important; font-weight: bold !important; color: #0f172a !important; margin: 0 !important; text-align: center; width: 100%; }}
    .st-key-arena_radio div[data-testid="stMarkdownContainer"] {{ width: 100%; }}
    
    /* FIX THE "Options" MAIN LABEL */
    .st-key-arena_radio > label {{ width: 100% !important; background: transparent !important; border: none !important; padding: 0 !important; text-align: left !important; display: block !important; margin-bottom: 5px !important; box-shadow: none !important; }}
    .st-key-arena_radio > label p {{ font-size: 1.1rem !important; font-weight: bold !important; color: #475569 !important; }}

    [data-testid="stForm"] {{ padding: 10px !important; margin-bottom: 0 !important; }}

    [data-testid="stSidebar"] {{ background: {sidebar_bg} !important; border-right: 3px solid #38bdf8; transition: background 1s ease; z-index: 2; }}
    [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] label, [data-testid="stSidebar"] [data-testid="stMetricValue"] {{ color: #ffffff !important; }}
    [data-testid="stSidebar"] button {{ color: #0f172a !important; font-weight: bold; }}
    
    /* FIX EXPANDER TEXT VISIBILITY IN SIDEBAR */
    [data-testid="stSidebar"] [data-testid="stExpander"] details summary p {{ color: #ffffff !important; font-weight: bold !important; font-size: 1.1rem !important; text-shadow: 1px 1px 2px rgba(0,0,0,0.5); }}
    [data-testid="stSidebar"] [data-testid="stExpander"] details summary svg {{ color: #ffffff !important; fill: #ffffff !important; }}
    .st-key-profile_radio p {{ color: #ffffff !important; font-weight: bold !important; }}
    
    .stTextInput input {{ border: 2px solid #38bdf8 !important; border-radius: 8px !important; padding: 15px !important; font-size: 1.25rem !important; background-color: rgba(255,255,255,0.95) !important; font-weight: 500; color: #0f172a; height: 50px; }}
    .sticky-note {{ background-color: #fef08a; color: #1f2937 !important; padding: 15px; border-radius: 2px 15px 15px 15px; box-shadow: 2px 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; font-size: 0.9rem; line-height: 1.5; border-left: 5px solid #eab308; }}
    
    /* PULSING BATTLE LOG CSS */
    @keyframes pulse-log {{ 0% {{ box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.7); }} 70% {{ box-shadow: 0 0 0 15px rgba(245, 158, 11, 0); }} 100% {{ box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }} }}
    .battle-log-pulse {{ border-radius: 10px; animation: pulse-log 2s infinite; background-color: #ffffff; padding: 5px; border: 3px solid #f59e0b; margin-top: 20px; }}
    
    /* BLINKING REWARD CSS */
    @keyframes superBlink {{ 0%, 100% {{ box-shadow: 0 0 10px #fcd34d; border-color: #fcd34d; }} 50% {{ box-shadow: 0 0 30px #f59e0b, inset 0 0 15px #f59e0b; border-color: #f59e0b; transform: scale(1.02); }} }}
    .blinking-reward {{ animation: superBlink 1.5s infinite !important; border: 4px solid #fcd34d !important; padding: 15px; border-radius: 12px; background: rgba(255,255,255,0.1); margin-top: 15px; }}

    /* UI GUIDANCE ANIMATIONS */
    @keyframes pointDown {{ 0%, 100% {{ transform: translateY(0); }} 50% {{ transform: translateY(10px); }} }}
    .anim-down {{ animation: pointDown 1s infinite ease-in-out; display: inline-block; font-size: 2.5rem; }}
    @keyframes pointLeft {{ 0%, 100% {{ transform: translateX(0); }} 50% {{ transform: translateX(-10px); }} }}
    .anim-left {{ animation: pointLeft 1s infinite ease-in-out; display: inline-block; font-size: 1.8rem; }}
    
    .xp-highlight {{ color: #fcd34d !important; font-weight: bold; text-shadow: 0px 0px 10px #fcd34d; }}
    .xp-normal {{ color: #fcd34d !important; font-weight: bold; }}
    .vault-glow {{ background: linear-gradient(90deg, #f59e0b, #d97706); color: white !important; padding: 15px; border-radius: 8px; text-align: center; font-weight: bold; font-size: 1.2rem; margin-bottom: 15px; border: 2px solid #fbbf24; }}
    </style>
""", unsafe_allow_html=True)

# --- 3. HEADER ---
st.markdown("<h1 style='text-align: left; color: #0f172a; margin-bottom: 5px; position: relative; z-index: 1;'>🎓 AI Exam Coach</h1>", unsafe_allow_html=True)

st.markdown("""
    <div style="position: relative; z-index: 1; color: #475569; font-size: 1.15rem; line-height: 1.6; margin-bottom: 25px; border-left: 4px solid #38bdf8; padding-left: 15px; background-color: rgba(255,255,255,0.85); padding-top: 10px; padding-bottom: 10px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
        <b>What this is:</b> An AI coach that helps you pass your hardest exams and interviews without getting bored.<br>
        <b>How it works:</b> Tell the AI your goal. It builds a map of your core subjects. Click a circle, switch to the "Practice Arena", and answer questions to clear the level.<br>
        <b>What you get:</b> Win points to unlock secret cheat sheets and face the Boss Exam!
    </div>
""", unsafe_allow_html=True)

if st.session_state.get("just_unlocked_200", False):
    st.markdown("""
    <div style='background-color: #fef08a; padding: 15px; border-radius: 10px; border: 3px solid #eab308; text-align: center; font-size: 1.5rem; font-weight: bold; color: #b45309; margin-bottom: 20px; box-shadow: 0px 10px 20px rgba(0,0,0,0.1); animation: popIn 0.5s ease-out;'>
        <span class='anim-left'>👈</span> CHEAT SHEETS UNLOCKED! Look at the Sidebar on the left to claim your reward!
    </div>
    """, unsafe_allow_html=True)

try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ API Key Error.")
    st.stop()

def extract_text(file):
    try:
        if file.name.endswith(".pdf"): return " ".join([p.extract_text() for p in PyPDF2.PdfReader(file).pages])[:5000]
        return docx2txt.process(io.BytesIO(file.read()))[:5000]
    except: return ""

# --- 4. SIDEBAR & PROFILE SYSTEM ---
with st.sidebar:
    
    st.markdown("<div id='step-6-anchor'></div>", unsafe_allow_html=True)
    
    st.markdown(f"### 👤 Student Profile")
    profiles = load_profiles()

    if st.session_state.current_user == "Guest":
        st.info("⚠️ Playing as Guest. Create a profile to save progress!")
        
        prof_tab = st.radio("Action:", ["Login", "Create New"], horizontal=True, key="profile_radio")
        
        if prof_tab == "Login":
            if not profiles:
                st.warning("No profiles found. Please click 'Create New'.")
            else:
                with st.form(key="login_form", clear_on_submit=True):
                    sel_user = st.selectbox("Select Profile", list(profiles.keys()))
                    sel_pw = st.text_input("Password", type="password")
                    if st.form_submit_button("🔓 Login", use_container_width=True):
                        stored_pw = profiles[sel_user].get("password", "")
                        if sel_pw == stored_pw or (stored_pw == "" and "data" not in profiles[sel_user]):
                            user_blob = profiles[sel_user]
                            user_data = user_blob.get("data", user_blob)
                            
                            st.session_state.clear()
                            init_state()
                            load_user_profile(sel_user, user_data, stored_pw)
                            
                            st.toast(f"Welcome back, {sel_user}!", icon="👋")
                            st.rerun()
                        else:
                            st.error("❌ Incorrect Password!")
        else: # Create New
            with st.form(key="create_form", clear_on_submit=True):
                new_user = st.text_input("New Username", placeholder="e.g. Jyothsna")
                new_pw = st.text_input("Create Password", type="password")
                if st.form_submit_button("✨ Create & Login", use_container_width=True):
                    clean_user = new_user.strip()
                    if not clean_user:
                        st.error("❌ Please enter a username.")
                    elif clean_user in profiles:
                        st.error("❌ Profile already exists! Use the Login tab.")
                    else:
                        st.session_state.clear()
                        init_state()
                        
                        st.session_state.current_user = clean_user
                        st.session_state.current_password = new_pw
                        
                        save_profile(clean_user, new_pw, get_save_data())
                        
                        st.toast(f"Profile created!", icon="✨")
                        st.rerun()
    else:
        st.success(f"✅ Secure session active.")
        c1, c2 = st.columns(2)
        if c1.button("💾 Save", use_container_width=True, disabled=is_locked):
            save_profile(st.session_state.current_user, st.session_state.current_password, get_save_data())
            st.toast("Progress saved securely!", icon="💾")
            
        if c2.button("🚪 Logout", use_container_width=True, disabled=is_locked):
            save_profile(st.session_state.current_user, st.session_state.current_password, get_save_data())
            reset_to_guest()
            st.toast("Logged out successfully.", icon="🔒")
            st.rerun()

    with st.expander("🛠️ App Settings & Reset"):
        if st.button("🚨 Factory Reset (Wipe All Profiles)", use_container_width=True, type="secondary"):
            if os.path.exists(PROFILE_FILE):
                os.remove(PROFILE_FILE)
            reset_to_guest()
            st.toast("All profiles wiped from disk.", icon="🗑️")
            st.rerun()

    if st.session_state.tour_step == 6:
        st.markdown("""
            <div style='background-color: #06b6d4; color: white; padding: 20px; border-radius: 10px; margin-bottom: 5px; border: 3px solid #67e8f9; box-shadow: 0px 10px 20px rgba(0,0,0,0.2); text-align: center;'>
                <h3 style='color: white; margin-top: 0;'>💾 Step 6: Profiles & Saving</h3>
                <p style='font-size: 1rem;'>Your progress is tied to your <b>Student Profile</b>. Hit <b>Save</b> before closing the app. Need a break right now? Hit <b>Pause Session</b> below to freeze the screen. Sharing the PC? Hit <b>Logout</b> to safely auto-store your data and let someone else log in!</p>
            </div>
            <div style='text-align: center; margin-bottom: 10px;'><span class='anim-down' style='color: #06b6d4;'>👇</span></div>
        """, unsafe_allow_html=True)
        if st.button("✅ End Tour & Start App", key="btn_tour6", use_container_width=True):
            st.session_state.tour_step = 0
            st.session_state.active_main_tab = "🗺️ Step 1: Study Planner"
            st.session_state.scroll_target = "step-1-anchor"
            st.rerun()

    if st.session_state.xp >= 500: rank = "Master Scholar 🎓🏆"
    elif st.session_state.xp >= 300: rank = "Advanced Student 📚🥈"
    else: rank = "Beginner Explorer 📝"
        
    st.markdown(f"## {rank}")
    st.progress(min(st.session_state.xp / 500, 1.0))
    
    xp_class = "xp-highlight" if st.session_state.just_leveled_up else "xp-normal"
    xp_icon = "🎉🎈" if st.session_state.just_leveled_up else ""
    st.markdown(f"<div class='{xp_class}' style='font-size: 1.15rem; margin-bottom: 5px;'><b>Total XP:</b> {st.session_state.xp} / 500 {xp_icon}</div>", unsafe_allow_html=True)
    
    st.session_state.just_leveled_up = False 
    
    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
    
    pause_btn_text = "▶️ Resume Session" if st.session_state.is_paused else "⏸️ Pause Session"
    if st.button(pause_btn_text, use_container_width=True, type="primary" if st.session_state.is_paused else "secondary"):
        st.session_state.is_paused = not st.session_state.is_paused
        st.rerun()
        
    st.markdown("<div style='font-size: 0.8rem; color:#94a3b8; text-align:center; margin-bottom:10px;'><i>Note: Closing your browser tab will reset your progress. Save your Profile first!</i></div>", unsafe_allow_html=True)
        
    if st.button("▶️ Replay Tutorial Tour", use_container_width=True, disabled=is_locked):
        st.session_state.tour_step = 1
        st.session_state.tour_done = False
        st.session_state.active_main_tab = "🗺️ Step 1: Study Planner"
        st.session_state.scroll_target = "step-1-anchor"
        st.rerun()
        
    st.divider()
    model_choice = st.selectbox("Engine:", ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"], disabled=is_locked)
    
    st.markdown("""
    <div class="sticky-note">
        <b>📌 Field Manual</b><br>
        1️⃣ <b>Strategy:</b> Tell the AI your specific exam.<br>
        2️⃣ <b>Target:</b> Click a node on the map.<br>
        3️⃣ <b>Practice:</b> Hit <i>⚡ Quick Test</i> in the Arena.<br>
        4️⃣ <b>Unlock:</b> Hit 200 XP for the Vault.<br>
        5️⃣ <b>Mastery:</b> Hit 500 XP for Boss Exam!<br>
        6️⃣ <b>Save:</b> Save your Profile before closing!
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    st.markdown("<div id='step-4-anchor'></div>", unsafe_allow_html=True)
    if st.session_state.tour_step == 4:
        st.markdown("""
            <div style='background-color: #f97316; color: white; padding: 20px; border-radius: 10px; margin-bottom: 5px; border: 3px solid #fdba74; box-shadow: 0px 10px 20px rgba(0,0,0,0.2); text-align: center;'>
                <h3 style='color: white; margin-top: 0;'>📄 Step 4: Upload Notes</h3>
                <p style='font-size: 1rem;'>Want highly customized questions? Upload your own study materials, PDF notes, or Syllabus here. The AI will read your document and generate questions strictly based on your notes!</p>
            </div>
            <div style='text-align: center; margin-bottom: 10px;'><span class='anim-down' style='color: #f97316;'>👇</span></div>
        """, unsafe_allow_html=True)
        if st.button("➔ Go to Step 5", key="btn_tour4", use_container_width=True):
            st.session_state.tour_step = 5
            st.session_state.scroll_target = "step-5-anchor"
            st.rerun()
            
    st.markdown("### 📄 Upload Knowledge Base")
    up_file = st.file_uploader("Upload Notes or Resume (PDF/Docx)", type=["pdf", "docx"], label_visibility="collapsed", disabled=is_locked)
    if up_file and not is_locked:
        if st.session_state.current_file != up_file.name:
            st.session_state.current_file = up_file.name
            st.session_state.doc_context = extract_text(up_file)
            st.balloons()
            st.toast("💥 File Synced!", icon="🚀")
        st.markdown("<div class='doc-highlight'>✅ File Synced to AI Brain!</div>", unsafe_allow_html=True)
    
    st.divider()

    st.markdown("<div id='step-5-anchor'></div>", unsafe_allow_html=True)
    if st.session_state.tour_step == 5:
        st.markdown("""
            <div style='background-color: #ec4899; color: white; padding: 20px; border-radius: 10px; margin-bottom: 5px; border: 3px solid #fbcfe8; box-shadow: 0px 10px 20px rgba(0,0,0,0.2); text-align: center;'>
                <h3 style='color: white; margin-top: 0;'>🎁 Step 5: Rewards Center</h3>
                <p style='font-size: 1rem;'>As you answer questions correctly in the Arena, you earn XP. Hit 200 XP to unlock a custom, downloadable Cheat Sheet. Hit 500 XP to face the ultimate Boss Exam!</p>
            </div>
            <div style='text-align: center; margin-bottom: 10px;'><span class='anim-down' style='color: #ec4899;'>👇</span></div>
        """, unsafe_allow_html=True)
        if st.button("➔ Go to Step 6", key="btn_tour5", use_container_width=True):
            st.session_state.tour_step = 6
            st.session_state.scroll_target = "step-6-anchor"
            st.rerun()

    st.markdown("### 🎁 Rewards Center")
    if st.session_state.xp >= 500:
        if not st.session_state.reached_max_level:
            st.balloons()
            st.snow()
            st.session_state.reached_max_level = True
        
        st.markdown("<div class='vault-glow' style='background: linear-gradient(90deg, #10b981, #059669); border-color:#34d399;'>🏆 ULTIMATE PRACTICE UNLOCKED</div>", unsafe_allow_html=True)
        st.success("You are an Advanced Scholar. The Practice Arena will now generate Ultimate Boss-Level questions based on multiple subjects at once!")

    st.markdown("<div id='reward-anchor'></div>", unsafe_allow_html=True)
    
    if st.session_state.xp < 200:
        pts_needed = 200 - st.session_state.xp
        st.markdown(f"<div style='color:#cbd5e1; font-size:0.9rem; margin-bottom: 15px;'><i>Earn {pts_needed} more XP to unlock custom Cheat Sheets!</i></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='color:#4ade80; font-size:0.9rem; margin-bottom: 15px; font-weight:bold;'><i>✅ Cheat Sheets Unlocked! Keep going for Mastery!</i></div>", unsafe_allow_html=True)

    if st.session_state.xp >= 200:
        if not st.session_state.is_premium:
            st.markdown("<div class='blinking-reward'>", unsafe_allow_html=True)
            st.warning("🔒 Cheat Sheets Locked.")
            st.markdown("You have proven your skills! Claim your free reward below.")
            if st.button("🔓 Unlock Cheat Sheets", use_container_width=True, disabled=is_locked):
                st.session_state.is_premium = True
                st.session_state.just_unlocked_200 = False 
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            if not st.session_state.vault_celebrated:
                st.balloons()
                st.toast("💥 BOOM! Reward Unlocked!", icon="🎉")
                st.session_state.vault_celebrated = True

            st.markdown("<div class='blinking-reward' style='padding-top:5px; border: 4px solid #fcd34d;'>", unsafe_allow_html=True)
            st.markdown("<div class='vault-glow'>🔓 REWARDS UNLOCKED!</div>", unsafe_allow_html=True)
            
            st.markdown("<div style='text-align: center;'><span class='anim-down' style='font-size: 2.5rem; color: #f59e0b;'>👇</span><br><b style='color: #f59e0b;'>Download your custom cheat sheet below!</b></div>", unsafe_allow_html=True)
            
            if not st.session_state.vault_intel:
                with st.spinner("Generating custom cheat sheets..."):
                    active_topics = ", ".join(st.session_state.skill_tree.keys()) if st.session_state.skill_tree else "General Exam Topics"
                    exam_context_str = " ".join([m["content"] for m in st.session_state.strat_history[:3]]) if st.session_state.strat_history else "General Studies"
                    
                    vault_prompt = f"""Create a highly dense, expert-level study cheat sheet specifically for: {exam_context_str}.
                    Focus strictly on these exact phases/topics: {active_topics}.
                    Provide core principles, key formulas, definitions, or essential concepts relevant ONLY to this specific subject matter. Do not include generic math or english unless it is explicitly part of the user's topic.
                    Output ONLY plain text format."""
                    
                    try:
                        res = client.chat.completions.create(messages=[{"role": "system", "content": vault_prompt}], model=model_choice)
                        st.session_state.vault_intel = res.choices[0].message.content
                    except Exception as e:
                        st.session_state.vault_intel = f"Reward generation failed. Error: {e}"

            st.download_button("📥 Download Custom Cheat Sheet (TXT)", data=st.session_state.vault_intel, file_name="Targeted_CheatSheet.txt", disabled=is_locked, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

# --- 5. MAIN TABS LOGIC ---

st.markdown("<div id='step-3-anchor'></div>", unsafe_allow_html=True)
if st.session_state.tour_step == 3:
    st.markdown("""
        <div style='background-color: #8b5cf6; color: white; padding: 20px; border-radius: 10px; margin-bottom: 5px; border: 3px solid #c4b5fd; box-shadow: 0px 10px 20px rgba(0,0,0,0.2); text-align: center;'>
            <h3 style='color: white; margin-top: 0;'>⚔️ Step 3: Practice Arena</h3>
            <p style='font-size: 1.1rem;'>Now that you have your roadmap, it's time to practice! Click the "Practice Arena" tab below to enter the testing zone.</p>
        </div>
        <div style='text-align: center; margin-bottom: 5px;'><span class='anim-down' style='color: #8b5cf6;'>👇</span><br><b style='color:#8b5cf6;'>Click 'Step 2: Practice Arena' Tab below!</b></div>
    """, unsafe_allow_html=True)
    if st.button("➔ Go to Step 4", key="btn_tour3", use_container_width=True):
        st.session_state.tour_step = 4
        st.session_state.active_main_tab = "⚔️ Step 2: Practice Arena"
        st.session_state.scroll_target = "step-4-anchor"
        st.rerun()

selected_tab = st.radio("Navigation", ["🗺️ Step 1: Study Planner", "⚔️ Step 2: Practice Arena"], index=["🗺️ Step 1: Study Planner", "⚔️ Step 2: Practice Arena"].index(st.session_state.active_main_tab), label_visibility="collapsed", key="main_tabs")

if selected_tab != st.session_state.active_main_tab:
    st.session_state.active_main_tab = selected_tab
    st.rerun()

# ==========================================
# --- TAB 1: STRATEGY PLANNER (ROADMAP) ---
# ==========================================
if st.session_state.active_main_tab == "🗺️ Step 1: Study Planner":
    
    col_strat_chat, col_strat_map = st.columns([3, 2], gap="large")
    
    with col_strat_chat:
        st.markdown("<div style='background: rgba(255,255,255,0.85); padding: 15px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>", unsafe_allow_html=True)

        st.markdown("<div id='step-1-anchor'></div>", unsafe_allow_html=True)
        if st.session_state.tour_step == 1:
            st.markdown("""
                <div style='background-color: #3b82f6; color: white; padding: 20px; border-radius: 10px; margin-bottom: 5px; border: 3px solid #93c5fd; box-shadow: 0px 10px 20px rgba(0,0,0,0.2); text-align: center;'>
                    <h3 style='color: white; margin-top: 0;'>👋 Step 1: The Study Planner</h3>
                    <p style='font-size: 1.1rem;'>Type your specific exam name (e.g., 'Interview', 'GATE') or use the Voice Mic below. The AI will instantly analyze the exam syllabus and standard weightages.</p>
                </div>
            """, unsafe_allow_html=True)
            if st.button("➔ Go to Step 2", key="btn_tour1", use_container_width=True):
                st.session_state.tour_step = 2
                st.session_state.scroll_target = "step-2-anchor"
                st.rerun()
                
        trigger_strat_query = False
        strat_query_payload = ""

        if st.session_state.strat_questions:
            with st.expander("🗂️ Planner Archive (Click to reload)"):
                for i, q in enumerate(st.session_state.strat_questions):
                    if st.button(f"🔎 {q}", key=f"hist_btn_{i}", use_container_width=True, disabled=is_locked):
                        st.session_state.archive_trigger_payload = q
        
        chat_box_strat = st.container(height=350)
        for msg in st.session_state.strat_history:
            chat_box_strat.chat_message(msg["role"]).markdown(msg["content"])
            
        st.markdown("---")
        
        if not st.session_state.skill_tree:
            st.markdown("<div style='color: #d97706; font-weight: bold; font-size: 1.1rem; background: #fef3c7; padding: 10px; border-radius: 8px; border-left: 4px solid #f59e0b; margin-bottom: 15px;'>👉 Tell me what SPECIFIC exam or goal you are preparing for down below! (e.g. 'Interview prep' or 'Exam prep')</div>", unsafe_allow_html=True)
        
        v_col1, t_col1 = st.columns([1, 5]) 
        with v_col1:
            if st.session_state.tour_step == 1:
                st.markdown("<div style='text-align: center; margin-top: -10px; margin-bottom: 5px;'><span class='anim-down' style='color: #3b82f6;'>👇</span><br><b style='color:#3b82f6; font-size: 1rem; white-space: nowrap;'>Mic</b></div>", unsafe_allow_html=True)
            
            audio1 = st.audio_input("Mic", key=f"mic1_{st.session_state.audio_strat}", label_visibility="collapsed", disabled=is_locked)
            if audio1 and not is_locked:
                try:
                    trans = client.audio.transcriptions.create(file=("a.wav", audio1.read()), model="whisper-large-v3-turbo")
                    st.session_state.text_strat = trans.text
                    st.session_state.audio_strat += 1 
                    st.rerun()
                except: st.error("Mic Error")
        
        with t_col1:
            if st.session_state.tour_step == 1:
                st.markdown("<div style='text-align: center; margin-top: -10px; margin-bottom: 5px;'><span class='anim-down' style='color: #3b82f6;'>👇</span><br><b style='color:#3b82f6; font-size: 1rem;'>Type here!</b></div>", unsafe_allow_html=True)
            
            with st.form(key="strat_form", clear_on_submit=True):
                user_strat = st.text_input("Ask for strategy or roadmaps:", value=st.session_state.text_strat, disabled=is_locked)
                sub1, clr1 = st.columns(2)
                
                trigger_submit = sub1.form_submit_button("🚀 SEND TO COACH", disabled=is_locked)
                trigger_clear = clr1.form_submit_button("🗑️ CLEAR", disabled=is_locked)
                
                if trigger_clear: 
                    st.session_state.text_strat = ""
                    st.session_state.strat_history = []
                    st.rerun()

        active_payload = None
        if st.session_state.archive_trigger_payload:
            active_payload = st.session_state.archive_trigger_payload
            st.session_state.archive_trigger_payload = None
        elif trigger_submit and user_strat.strip() and not is_locked:
            active_payload = user_strat.strip()
            
        if active_payload:
            st.session_state.text_strat = ""
            st.session_state.strat_history.append({"role": "user", "content": active_payload})
            if active_payload not in st.session_state.strat_questions:
                st.session_state.strat_questions.append(active_payload)
            
            try:
                injected_facts = ""
                db_keys = sorted(EXAM_DATABASE.keys(), key=len, reverse=True) 
                for key in db_keys:
                    if key in active_payload.lower() or key in " ".join([m["content"].lower() for m in st.session_state.strat_history]):
                        injected_facts = f"\n\n[CRITICAL DATABASE FACT: Use EXACTLY this data for the exam: {EXAM_DATABASE[key]}]"
                        break

                sys_msg1 = f"""You are an elite, highly disciplined Educational Strategy Coach. Context: {st.session_state.doc_context}.
                {injected_facts}
                CRITICAL GUARDRAILS - OBEY STRICTLY:
                1. DO NOT GUESS EXAM PATTERNS: Use the exact weightage provided in the Database Fact above.
                2. YOU ARE NOT THE EXAMINER: NEVER give practice questions, timers, or quizzes in this planner tab. That is strictly for the Practice Arena.
                3. NEVER ASK THE USER TO PICK SUBJECTS: You are the expert. Do not offer a list of choices.
                4. A ROADMAP IS A TIMELINE: When building the map, do not just list subjects. Your `[TREE: ...]` output MUST represent chronological milestones. KEEP PHASE NAMES SHORT. DO NOT output the literal word 'TREE:' inside the nodes.
                5. NO FAKE URLs: When providing study resources, ONLY recommend famous, real platforms (e.g., Bankers Adda, Testbook, Coursera). DO NOT generate fake domains. Provide the name only if unsure.
                6. NO META-COMMENTARY: Just immediately execute the next funnel step.
                7. EXAM LEVEL STRICTNESS: If the user asks for an Intermediate level exam (like CA Inter), YOU MUST NEVER include topics, structures, or questions meant for the Final level (like CA Final). Keep the scope strictly bound to the requested level."""
                
                user_msg_lower = active_payload.lower()
                history_str = " ".join([m["content"].lower() for m in st.session_state.strat_history])
                last_ai_msg = st.session_state.strat_history[-2]["content"].lower() if len(st.session_state.strat_history) >= 2 else ""
                
                user_wants_change = any(w in user_msg_lower for w in ["change", "actually i want", "instead", "wrong exam", "correct"])
                
                if user_wants_change:
                     injected_prompt = active_payload + "\n\n[CRITICAL OVERRIDE: The user is changing their exam. Acknowledge the NEW exam, state its specific pattern/weightage from the Database, and ask EXACTLY: 'How many days/weeks until your target date?'. DO NOT output a map yet.]"
                elif not st.session_state.skill_tree:
                    if "resources" in last_ai_msg or "study materials" in last_ai_msg or "yes" in user_msg_lower or "no" in user_msg_lower:
                        injected_prompt = st.session_state.strat_history[-1]["content"] + "\n\n[CRITICAL FUNNEL STEP: 1. Give the resources. 2. YOU MUST NOW BUILD THE MAP for their specific stream. Output at the VERY END of your message exactly: [TREE: Phase 1 (High) | Phase 2 (Medium) | Final Phase (Low)]. Separate with pipes. Keep phase names under 4 words. 3. End by stating exactly: 'Your Strategy Roadmap is ready! Switch to the Practice Arena tab to start your test.']"
                    elif "day" in last_ai_msg or "week" in last_ai_msg or "target date" in last_ai_msg or any(w in user_msg_lower for w in ["day", "week", "month", "year"]):
                        injected_prompt = st.session_state.strat_history[-1]["content"] + "\n\n[CRITICAL FUNNEL STEP: 1. Write the study strategy based on their timeline using bullet points. DO NOT output a TREE map yet. 2. End by asking EXACTLY: 'Shall I give you some free resources to prepare?']"
                    elif "stream" in last_ai_msg or "subject" in last_ai_msg or "specialization" in last_ai_msg or "branch" in last_ai_msg:
                        injected_prompt = st.session_state.strat_history[-1]["content"] + "\n\n[CRITICAL FUNNEL STEP: 1. Acknowledge their stream and state the standard exam weightage/structure for that stream. DO NOT output a TREE map yet. 2. End your message EXACTLY with this question and nothing else: 'How many days/weeks until your target date?']"
                    else:
                        injected_prompt = st.session_state.strat_history[-1]["content"] + "\n\n[CRITICAL FUNNEL STEP: 1. Evaluate the exam type. If the exam requires a specific stream/branch (like GATE, UGC NET) AND the user HAS NOT explicitly named it, ask EXACTLY: 'What is your specific specialized subject/branch?'. Do not ask this for exams with mandatory standard subjects (like PLACEMENT Exam, GATE, Bank). 2. IF the exam has mandatory subjects OR the branch is already provided, state the weightage and ask EXACTLY: 'How many days/weeks until your target date?']"
                else:
                    injected_prompt = st.session_state.strat_history[-1]["content"] + "\n\n[CRITICAL: The map is built. If the user asks a general question, answer it. IF the user wants to change their exam or clicked a past topic from the archive, you MUST output a new [TREE: Sub1 | Sub2 | Sub3] at the end of your response to redraw the map.]"
                
                api_messages = [{"role": "system", "content": sys_msg1}]
                for msg in st.session_state.strat_history[-5:-1]: 
                    api_messages.append({"role": msg["role"], "content": msg["content"]})
                
                api_messages.append({"role": "user", "content": injected_prompt})
                
                with st.spinner("⏳ The AI Coach is analyzing your strategy..."):
                    res = client.chat.completions.create(messages=api_messages, model=model_choice)
                ans = res.choices[0].message.content
                
                map_match = re.search(r"\[(?:TREE:)?\s*([^\]]+\|[^\]]+)\]", ans, re.IGNORECASE)
                if map_match:
                    tree_raw = map_match.group(1).replace("**", "").replace("\n", " ")
                    raw_topics = tree_raw.split("|")
                    
                    st.session_state.skill_tree = {} 
                    for t in raw_topics:
                        t = re.sub(r"(?i)TREE:", "", t).strip()
                        weight = "Medium"
                        if re.search(r"(?i)\(high\)", t): weight = "High"
                        elif re.search(r"(?i)\(low\)", t): weight = "Low"
                        
                        clean_t = re.sub(r"\(.*?\)", "", t).strip()
                        clean_t = re.sub(r"\d+%.*", "", clean_t).strip()
                        clean_t = re.sub(r'([a-z])([A-Z])', r'\1 \2', clean_t)
                        
                        if len(clean_t) > 2 and clean_t != "]": 
                            st.session_state.skill_tree[clean_t] = {"status": "Active", "weight": weight}
                    
                    st.session_state.active_map_node = None
                    st.session_state.vault_intel = "" 
                    
                    st.session_state.arena_history = [{"role": "assistant", "content": "Welcome to the Practice Arena. Select a phase from the map above and hit Quick Test!"}]
                    st.session_state.last_answer_correct = False
                    
                    ans = ans.replace(map_match.group(0), "").strip()
                        
                st.session_state.strat_history.append({"role": "assistant", "content": ans})
                st.rerun()
                    
            except Exception as e:
                if len(st.session_state.strat_history) > 0: st.session_state.strat_history.pop()
                st.error(f"⚠️ API Error: {e}. If the app is stuck, change the 'Engine' in the sidebar and try again!")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_strat_map:
        st.markdown("<div style='background: rgba(255,255,255,0.85); padding: 15px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>", unsafe_allow_html=True)
        st.markdown("<div id='step-2-anchor'></div>", unsafe_allow_html=True)
        
        if st.session_state.tour_step == 2:
            st.markdown("""
                <div style='background-color: #10b981; color: white; padding: 20px; border-radius: 10px; margin-bottom: 5px; border: 3px solid #6ee7b7; box-shadow: 0px 10px 20px rgba(0,0,0,0.2); text-align: center;'>
                    <h3 style='color: white; margin-top: 0;'>🗺️ Step 2: Strategy Roadmap</h3>
                    <p style='font-size: 1.1rem;'>The AI has analyzed your exam and built a Chronological Strategy Roadmap. This tree diagram shows the exact phases of study you need to follow.</p>
                </div>
            """, unsafe_allow_html=True)
            if st.button("➔ Go to Step 3", key="btn_tour2", use_container_width=True):
                st.session_state.tour_step = 3
                st.session_state.scroll_target = "step-3-anchor"
                st.rerun()
            st.markdown("<div style='text-align: center; margin-bottom: 10px;'><span class='anim-down' style='color: #10b981;'>👇</span><br><b style='color:#10b981;'>Roadmap Appears Here!</b></div>", unsafe_allow_html=True)

        st.subheader("🗺️ Strategy Roadmap")
        if not st.session_state.skill_tree:
            st.info("🗺️ Your Interactive Roadmap will be generated after we finalize your study strategy! Follow the AI's questions on the left.")
        else:
            nodes = []
            edges = []
            topic_names = list(st.session_state.skill_tree.keys())
            
            for i, topic in enumerate(topic_names):
                data = st.session_state.skill_tree[topic]
                is_boss = "CRUCIBLE" in topic.upper()
                is_active = (topic == st.session_state.active_map_node)
                
                if is_boss:
                    size = 55 if is_active else 50
                    node_bg = "#fca5a5" if is_active else ("#fef3c7" if data["status"] == "Mastered" else "#fecaca")
                    node_border = "#9f1239" if is_active else ("#d97706" if data["status"] == "Mastered" else "#991b1b")
                else:
                    size = 45 if is_active else (40 if data["weight"] == "High" else (30 if data["weight"] == "Medium" else 20))
                    node_bg = "#fbcfe8" if is_active else ("#fef3c7" if data["status"] == "Mastered" else "#e0f2fe")
                    node_border = "#e11d48" if is_active else ("#d97706" if data["status"] == "Mastered" else "#0369a1")
                    
                border_width = 4 if is_active else 1
                font_color = "#4c0519" if is_active else node_border
                
                nodes.append(Node(id=topic, label=topic, size=size, color={"background": node_bg, "border": node_border}, borderWidth=border_width, shape="dot", font={'color': font_color, 'face': 'sans-serif', 'weight': 'bold', 'size': 16}))
                if i > 0:
                    edges.append(Edge(source=topic_names[i-1], target=topic, color="#cbd5e1"))

            config_planner = Config(width="100%", height=400, directed=True, physics=False, hierarchical=True, direction="LR", nodeSpacing=150)
            agraph(nodes=nodes, edges=edges, config=config_planner)
            
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# --- TAB 2: PRACTICE ARENA ---
# ==========================================
elif st.session_state.active_main_tab == "⚔️ Step 2: Practice Arena":
    
    st.markdown("<div style='position: relative; z-index: 1; background: rgba(255,255,255,0.85); padding: 15px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>", unsafe_allow_html=True)
        
    if not st.session_state.skill_tree and st.session_state.tour_step == 0:
        st.warning("🔒 Please generate a study map in the Planner Tab first to unlock this arena!")
    else:
        
        if not st.session_state.get("arena_tour_done", False) and not is_touring:
            st.markdown("""
                <div style='background: linear-gradient(135deg, #1e3a8a, #312e81); padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px; box-shadow: 0 10px 20px rgba(0,0,0,0.2);'>
                    <h3 style='color: white; margin-top:0;'>⚔️ Welcome to the Practice Arena!</h3>
                    <p style='font-size: 1.1rem;'><b>Interactive Map Integration!</b> Click the map directly in the arena to pick your subject.</p>
                    <ul style='font-size: 1.1rem; line-height: 1.6;'>
                        <li><b>Quick Test:</b> Click this button to instantly spawn a Multiple Choice Question.</li>
                        <li><b>Hybrid Answers:</b> Click the A, B, C, D buttons for fast answers, OR type "Hint" in the text box to ask for help!</li>
                    </ul>
                    <div style='background: rgba(255,255,255,0.2); padding: 15px; border-radius: 8px; margin-top: 15px; border: 2px dashed #fcd34d;'>
                        <h4 style='color: #fcd34d; margin: 0;'><span class='anim-down'>👇</span> SCROLL TO THE VERY BOTTOM: The Battle Log!</h4>
                        <p style='margin-bottom: 0;'>We save every single question and explanation inside the glowing orange <b>Battle Log</b> at the bottom of your screen. Check it anytime to review your mistakes!</p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("⚔️ Got it! Let's Fight!", use_container_width=True, type="primary"):
                st.session_state.arena_tour_done = True
                st.rerun()
            st.stop()
        
        target_node = st.session_state.active_map_node if st.session_state.active_map_node else "None"
        is_boss = "CRUCIBLE" in target_node.upper()
        
        st.markdown("#### 🗺️ Select Your Target Phase")
        nodes = []
        edges = []
        topic_names = list(st.session_state.skill_tree.keys())
        for i, topic in enumerate(topic_names):
            data = st.session_state.skill_tree[topic]
            is_active = (topic == st.session_state.active_map_node)
            if "CRUCIBLE" in topic.upper():
                node_bg, node_border = ("#fca5a5", "#9f1239") if is_active else ("#fecaca", "#991b1b")
                size = 45
            else:
                node_bg, node_border = ("#fbcfe8", "#e11d48") if is_active else ("#e0f2fe", "#0369a1")
                size = 35
            nodes.append(Node(id=topic, label=topic, size=size, color={"background": node_bg, "border": node_border}, borderWidth=4 if is_active else 1, shape="dot", font={'color': node_border, 'face': 'sans-serif', 'weight': 'bold', 'size': 14}))
            if i > 0: edges.append(Edge(source=topic_names[i-1], target=topic, color="#cbd5e1"))
        
        config_arena = Config(width="100%", height=150, directed=True, physics=True, hierarchical=False, nodeSpacing=100)
        clicked_node_arena = agraph(nodes=nodes, edges=edges, config=config_arena)
        
        if clicked_node_arena and not is_touring:
            st.session_state.active_map_node = clicked_node_arena
            st.session_state.last_answer_correct = False
            target_node = clicked_node_arena
            st.rerun()

        d_col1, d_col2 = st.columns([3, 1])
        with d_col1:
            st.markdown(f"<div style='font-size:1.3rem; font-weight:bold; color:#e11d48; margin-top:5px;'>🎯 Current Target: {target_node}</div>", unsafe_allow_html=True)
        with d_col2:
            if st.session_state.active_map_node and len(st.session_state.arena_history) <= 1:
                st.markdown("<div style='text-align: center; margin-bottom: -10px;'><span class='anim-down' style='color: #22c55e;'>👇</span></div>", unsafe_allow_html=True)
            trigger_quick = st.button("⚡ Quick Test", use_container_width=True, disabled=is_locked)
            
            if trigger_quick and not is_locked:
                st.session_state.last_answer_correct = False
                st.session_state.trigger_quick_test = True
                
        if st.session_state.last_answer_correct:
             st.success("🎉 **CORRECT! +50 XP.** Great job! Want a new challenge? Select a new topic from the map, or hit Quick Test to keep going!")
        elif st.session_state.get("show_wrong_animation", False):
             st.error("❌ **INCORRECT!** Don't worry, read the coach's hint below and try again, or ask for an explanation!")
        
        chat_box_arena = st.container(height=250)
        for msg in st.session_state.arena_history:
            chat_box_arena.chat_message(msg["role"]).markdown(msg["content"])
            
        with st.form(key="arena_form", clear_on_submit=True):
            radio_col, text_col = st.columns([1.5, 3.5])
            with radio_col:
                user_choice = st.radio("Options:", ["A", "B", "C", "D"], index=None, horizontal=True, label_visibility="collapsed", key="arena_radio", disabled=is_locked)
            with text_col:
                user_arena = st.text_input("Or type hint/question:", value=st.session_state.text_arena, disabled=is_locked, label_visibility="collapsed", placeholder="Type 'hint' if you are stuck...")
            
            sub2, clr2 = st.columns(2)
            trigger_arena_submit = sub2.form_submit_button("⚔️ SEND", disabled=is_locked)
            trigger_arena_clear = clr2.form_submit_button("🗑️ CLEAR", disabled=is_locked)
            
            if trigger_arena_clear:
                st.session_state.text_arena = ""
                st.session_state.arena_history = [{"role": "assistant", "content": "Welcome back."}]
                st.session_state.last_answer_correct = False
                st.rerun()
                
            if (trigger_arena_submit or st.session_state.trigger_quick_test) and not is_locked:
                
                final_submission = ""
                if user_arena.strip():
                    final_submission = user_arena.strip()
                elif user_choice:
                    final_submission = f"My answer is {user_choice}"
                
                if final_submission or st.session_state.trigger_quick_test:
                    is_quick_test = st.session_state.trigger_quick_test
                    st.session_state.trigger_quick_test = False
                    st.session_state.text_arena = "" 
                    st.session_state.last_answer_correct = False 
                    
                    display_text = f"Deploying test for {target_node}..." if is_quick_test else final_submission
                    st.session_state.arena_history.append({"role": "user", "content": display_text})
                    
                    try:
                        is_boss = "CRUCIBLE" in target_node.upper()
                        active_subjects = ", ".join([k for k in st.session_state.full_skill_tree.keys() if "CRUCIBLE" not in k.upper()][:4]) if is_boss else ""
                        boss_instruction = f"This is the FINAL BOSS EXAM. Generate a highly difficult, integrated question combining elements of: {active_subjects}. DO NOT ask about a literal 'Crucible'." if is_boss else "If the target topic is a 'Phase' or timeframe, ask a question relevant to the competitive exam subjects taught in that timeframe."
                        
                        context_msgs = st.session_state.strat_history[:2] + st.session_state.strat_history[-2:]
                        exam_context_str = " ".join([m["content"] for m in context_msgs])
                        
                        sys_msg2 = f"""You are a strict Examiner for competitive exams. 
                        EXAM CONTEXT: The user is preparing based on this discussion: {exam_context_str}
                        TARGET TOPIC/PHASE: {target_node}. CRITICAL: The question MUST be strictly related to {target_node} within the context of the exam.
                        
                        1. {boss_instruction}
                        2. FORMAT: You MUST ask exactly ONE Multiple Choice Question (MCQ).
                        3. OPTIONS FORMAT: You ABSOLUTELY MUST provide 4 options as bullet points on NEW LINES exactly like this:
                           - A) [Option Text]
                           - B) [Option Text]
                           - C) [Option Text]
                           - D) [Option Text]
                        4. EVALUATION PROTOCOL: If the user provides an answer (A, B, C, D), you MUST evaluate it. 
                           - If CORRECT: Explain why, then your VERY LAST LINE MUST BE EXACTLY: [MASTER: {target_node}]
                           - If INCORRECT: Give a hint, then your VERY LAST LINE MUST BE EXACTLY: [WRONG]
                        5. HINTS OVERRIDE: If the user asks for a 'hint', 'help', or asks a question, YOU ARE FORBIDDEN from evaluating them. DO NOT output [MASTER] or [WRONG]. Just provide a helpful clue."""
                        
                        if is_quick_test:
                            injected_arena_prompt = f"Please generate a NEW, completely different MCQ practice question for the topic: {target_node}.\n\n[CRITICAL RULE: Do NOT evaluate past answers. DO NOT output [MASTER] or [WRONG] tags. Just output the new question and its 4 options.]"
                        else:
                            injected_arena_prompt = final_submission + f"\n\n[CRITICAL REQUIREMENT: Evaluate the answer. If correct, the last line MUST BE exactly [MASTER: {target_node}]. If incorrect, the last line MUST BE exactly [WRONG]. DO NOT forget brackets. IF the user asked for a hint, DO NOT use these tags!]"
                        
                        arena_api_messages = [{"role": "system", "content": sys_msg2}]
                        for msg in st.session_state.arena_history[-6:-1]:
                            arena_api_messages.append({"role": msg["role"], "content": msg["content"]})
                        arena_api_messages.append({"role": "user", "content": injected_arena_prompt})
                        
                        with st.spinner("⏳ The AI is evaluating your answer... Please wait!"):
                            res = client.chat.completions.create(messages=arena_api_messages, model=model_choice)
                        ans = res.choices[0].message.content
                        
                        ans_upper = ans.upper()
                        is_hint_request = any(w in final_submission.lower() for w in ["hint", "help", "explain", "?", "why"])
                        
                        m_matches = re.findall(r"\[\s*\*?(?:MASTER|CORRECT)[\s:]*(.*?)\*?\s*\]", ans, re.IGNORECASE)
                        w_matches = re.findall(r"\[\s*\*?(?:W[RO]+N?G?|INCORRECT)\*?\s*\]", ans, re.IGNORECASE)
                        
                        is_correct = bool(m_matches) or ("[MASTER" in ans_upper) or ("CORRECT" in ans_upper and "INCORRECT" not in ans_upper and "NOT CORRECT" not in ans_upper)
                        is_wrong = bool(w_matches) or ("[WRONG" in ans_upper) or ("INCORRECT" in ans_upper)

                        if is_correct and not is_wrong and not is_quick_test and not is_hint_request:
                            old_xp = st.session_state.xp
                            st.session_state.xp += 50
                            
                            if old_xp < 200 and st.session_state.xp >= 200:
                                st.session_state.just_unlocked_200 = True
                                st.session_state.scroll_target = "reward-anchor"
                                
                            st.session_state.just_leveled_up = True
                            st.session_state.last_answer_correct = True 
                            st.session_state.play_correct_anim = True 
                            st.session_state.show_wrong_animation = False
                            
                            for key in st.session_state.skill_tree.keys():
                                if target_node.lower() in key.lower():
                                    if st.session_state.skill_tree[key]["status"] != "Mastered":
                                        st.session_state.skill_tree[key]["status"] = "Mastered"
                            
                        elif is_wrong and not is_quick_test and not is_hint_request:
                            st.session_state.last_answer_correct = False
                            st.session_state.show_wrong_animation = True
                            st.session_state.play_wrong_anim = True
                        else:
                            st.session_state.last_answer_correct = False
                            st.session_state.show_wrong_animation = False

                        ans = re.sub(r"(?i)\[\s*\*?(?:MASTER|CORRECT).*?\*?\s*\]\.?", "", ans).strip()
                        ans = re.sub(r"(?i)\[\s*\*?(?:W[RO]+N?G?|INCORRECT)\*?\s*\]\.?", "", ans).strip()
                        
                        st.session_state.arena_history.append({"role": "assistant", "content": ans})
                        st.rerun()
                    except Exception as e:
                        if len(st.session_state.arena_history) > 0: st.session_state.arena_history.pop() 
                        st.error(f"⚠️ API Error: {e}. If the app is stuck, change the 'Engine' in the sidebar and try again!")

        st.markdown("<div class='battle-log-pulse'>", unsafe_allow_html=True)
        with st.expander("📜 Battle Log (Review Past Questions & Explanations)"):
            st.markdown("<div style='background-color: #ffffff; padding: 20px; border-radius: 10px; border: 2px solid #e2e8f0; box-shadow: 0px 4px 6px rgba(0,0,0,0.05);'>", unsafe_allow_html=True)
            if len(st.session_state.arena_history) <= 1:
                st.info("Your practice history will appear here once you start answering questions.")
            else:
                for msg in st.session_state.arena_history[1:]:
                    if msg["role"] == "user":
                        st.markdown(f"**You:** {msg['content']}")
                    else:
                        st.markdown(f"**Coach:** {msg['content']}")
                        st.divider()
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
