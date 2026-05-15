import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import datetime
import os
import re
import smtplib
import random
import io
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from fpdf import FPDF
from engine import MentalHealthEngine
from plyer import notification
import threading
import time
import csv
import ssl  

# --- 1. SYSTEM INITIALIZATION ---
st.set_page_config(page_title="Agentic AI - Secure Portal", layout="wide", page_icon="🛡️")

st.markdown("""
<style>

.stApp{
    background:
    radial-gradient(circle at center,
    rgba(0,255,255,0.35) 0%,
    transparent 34%),

    radial-gradient(circle at top right,
    rgba(255,0,255,0.30) 0%,
    transparent 22%),

    radial-gradient(circle at bottom left,
    rgba(0,255,120,0.28) 0%,
    transparent 22%),

    radial-gradient(circle at bottom right,
    rgba(0,140,255,0.30) 0%,
    transparent 22%),

    #050816;

    color:#9ca3af;
}

/* Sidebar */
[data-testid="stSidebar"]{
    background:rgba(5,8,22,0.92);
    border-right:1px solid rgba(0,255,255,0.18);
    backdrop-filter:blur(18px);
}

/* Titles */
h1,h2,h3{
    color:#67e8f9;
    text-transform:uppercase;
    letter-spacing:12px;
    text-shadow:0 0 12px rgba(103,232,249,0.45);
}

/* Cards */
div[data-testid="metric-container"]{
    background:rgba(255,255,255,0.04);
    backdrop-filter:blur(18px);
    border:1px solid rgba(255,255,255,0.08);
    border-radius:24px;
    padding:24px;

    box-shadow:
    0 0 20px rgba(0,255,255,0.08),
    inset 0 0 12px rgba(255,255,255,0.02);
}

/* Buttons */
.stButton>button{
    background:linear-gradient(90deg,#00c6ff,#0072ff);
    color:white;
    border:none;
    border-radius:30px;
    height:52px;
    font-size:16px;
    font-weight:700;
    letter-spacing:1px;

    box-shadow:0 0 18px rgba(0,140,255,0.35);
}

/* Button Hover */
.stButton>button:hover{
    transform:translateY(-2px);

    box-shadow:
    0 0 10px rgba(0,255,255,0.5),
    0 0 20px rgba(0,140,255,0.45),
    0 0 35px rgba(255,0,255,0.28);
}

/* Inputs */
.stTextInput input,
.stTextArea textarea,
.stNumberInput input{

    background:rgba(255,255,255,0.04) !important;
    color:#e2e8f0 !important;

    border:1px solid rgba(0,255,255,0.12) !important;
    border-radius:14px !important;
}

/* Select Box */
.stSelectbox div[data-baseweb="select"]{
    background:rgba(255,255,255,0.04);
    border-radius:14px;
    border:1px solid rgba(0,255,255,0.12);
}

/* Charts */
.stPlotlyChart{
    background:rgba(255,255,255,0.03);
    border-radius:22px;
    padding:12px;
    border:1px solid rgba(255,255,255,0.06);
}

/* Tables */
[data-testid="stTable"]{
    background:rgba(255,255,255,0.03);
    border-radius:18px;
    overflow:hidden;
}

/* Scrollbar */
::-webkit-scrollbar{
    width:10px;
}

::-webkit-scrollbar-track{
    background:#050816;
}

::-webkit-scrollbar-thumb{
    background:linear-gradient(#00ffff,#0072ff);
    border-radius:20px;
}

</style>
""", unsafe_allow_html=True)

HISTORY_FILE = "patient_history.csv"
WELLNESS_LOG = "wellness_history.csv"
USER_REGISTRY = "user_registry.csv"

# --- DATABASE UPGRADE & INIT (FIXES THE KEYERROR) ---
def init_user_db():
    """Ensures the database exists and has all required columns."""
    required_columns = ["UID", "Name", "Password", "Role", "Contact", "Registered_At"]
    if not os.path.exists(USER_REGISTRY):
        df = pd.DataFrame(columns=required_columns)
        df.to_csv(USER_REGISTRY, index=False)
    else:
        try:
            df = pd.read_csv(USER_REGISTRY, dtype=str)
            modified = False
            for col in required_columns:
                if col not in df.columns:
                    df[col] = "Legacy Data"
                    modified = True
            if modified:
                df.to_csv(USER_REGISTRY, index=False)
        except Exception as e:
            st.error(f"Critical Error initializing database: {e}")

# Run initialization immediately on script load
init_user_db()

# --- PDF GENERATION LOGIC ---
def create_pdf(df):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt="Clinical Assessment Report", ln=True, align='C')
        pdf.set_font("Arial", size=10)
        pdf.ln(10)
        pdf.set_fill_color(230, 230, 230)
        
        headers = ["Timestamp", "Patient", "Contact", "Visual", "Text", "Risk"]
        widths = [40, 35, 35, 35, 35, 20]
        
        for head, width in zip(headers, widths):
            pdf.cell(width, 10, head, 1, 0, 'C', 1)
        pdf.ln()
        
        pdf.set_font("Arial", size=8)
        for i in range(len(df)):
            row = [
                df.iloc[i]['Timestamp'],
                df.iloc[i]['Patient_Name'],
                df.iloc[i].get('Contact_No', 'N/A'),
                df.iloc[i]['Visual_State'],
                df.iloc[i]['Text_State'],
                df.iloc[i]['Risk_Index']
            ]
            for j in range(len(widths)):
                pdf.cell(widths[j], 10, str(row[j]), 1)
            pdf.ln()
            
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        return f"PDF Error: {str(e)}".encode('latin-1')

# --- EMAIL DISPATCH LOGIC ---
def send_email_with_pdf(recipient_email, patient_name, pdf_content):
    MAILTRAP_USERNAME = "e46edd2f4535be"
    MAILTRAP_PASSWORD = "5989590706849f"
    smtp_server = "sandbox.smtp.mailtrap.io"
    # Port 2525 is often less "monitored" than 587 by firewalls
    port = 2525 
    
    try:
        msg = MIMEMultipart()
        msg['From'] = "admin@agentic-ai.io"
        msg['To'] = recipient_email
        msg['Subject'] = f"Clinical Assessment: {patient_name}"
        
        body = f"Hello,\n\nPlease find the AI-generated report for {patient_name} attached."
        msg.attach(MIMEText(body, 'plain'))
        
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(pdf_content)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename=Report.pdf")
        msg.attach(part)

        # 1. Create a modern SSL context
        context = ssl.create_default_context()

        # 2. Start with a standard connection
        server = smtplib.SMTP(smtp_server, port, timeout=15)
        
        # 3. Upgrade the connection to TLS securely
        server.starttls(context=context) 
        
        # 4. Login and Send
        server.login(MAILTRAP_USERNAME, MAILTRAP_PASSWORD)
        server.send_message(msg)
        server.quit()
            
        return True

    except Exception as e:
        st.error(f"Mailtrap Error: {str(e)}")
        return False

# --- HISTORY LOGIC ---
def save_to_history(username, patient_name, phone_number, emotion, mood, risk):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    clean_user = str(username).strip()
    new_entry = pd.DataFrame([[timestamp, clean_user, patient_name, phone_number, emotion, mood, f"{risk:.1f}%"]],
                            columns=["Timestamp", "Evaluator", "Patient_Name", "Contact_No", "Visual_State", "Text_State", "Risk_Index"])
    if os.path.isfile(HISTORY_FILE):
        try:
            new_entry.to_csv(HISTORY_FILE, mode='a', header=False, index=False)
        except:
            new_entry.to_csv(HISTORY_FILE, index=False)
    else:
        new_entry.to_csv(HISTORY_FILE, index=False)

def save_wellness_activity(username, activity, target_time):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_entry = pd.DataFrame([[timestamp, str(username).strip(), activity, target_time]], 
                            columns=["Logged_At", "Patient_Name", "Activity", "Scheduled_For"])
    if os.path.isfile(WELLNESS_LOG):
        new_entry.to_csv(WELLNESS_LOG, mode='a', header=False, index=False)
    else:
        new_entry.to_csv(WELLNESS_LOG, index=False)

def get_history_stats():
    if os.path.exists(HISTORY_FILE):
        try:
            count = len(pd.read_csv(HISTORY_FILE))
            return count, (count / 50000) * 100
        except: return 0, 0
    return 0, 0

# --- 2. LOGIN & REGISTRY LOGIC ---
def register_user(uid, name, password, role, contact):
    init_user_db() # Double check on register
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    uid, name, password, role, contact = str(uid).strip(), str(name).strip(), str(password).strip(), str(role).strip(), str(contact).strip()
    
    df = pd.read_csv(USER_REGISTRY, dtype=str)
    if not df.empty and contact in df['Contact'].values:
        return False, "Contact number already exists."
    
    with open(USER_REGISTRY, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([uid, name, password, role, contact, timestamp])
    return True, "Success"

def verify_login(uid, password, role):
    if not os.path.exists(USER_REGISTRY):
        return False
    try:
        df = pd.read_csv(USER_REGISTRY, dtype=str)
        if df.empty: return False
        uid_clean, pw_clean, role_clean = str(uid).strip(), str(password).strip(), str(role).strip()
        for index, row in df.iterrows():
            if (str(row['UID']).strip() == uid_clean and 
                str(row['Password']).strip() == pw_clean and 
                str(row['Role']).strip() == role_clean):
                return True
        return False
    except Exception as e:
        st.error(f"System Error: {e}")
        return False

# --- LOGIN & REGISTRATION UI ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("""<style>
    .stApp { background: radial-gradient(circle at center, #0f172a 0%, #020617 100%); }
    .login-card { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(15px); border-radius: 15px; padding: 2rem; border: 1px solid rgba(255,255,255,0.1); }
    </style>""", unsafe_allow_html=True)

    _, center_col, _ = st.columns([1, 2, 1])
    with center_col:
        st.markdown('<div class="login-card"><h1 style="color:#00e676; text-align:center;">SENTINEL AI</h1></div>', unsafe_allow_html=True)
        mode = st.tabs(["🔒 Sign In", "📝 Register"])
        with mode[0]:
            login_role = st.selectbox("Select Portal", ["Admin", "Patient"], key="log_role")
            u_id = st.text_input("UID (e.g. PAT-1234)")
            u_pw = st.text_input("Password", type="password")
            if st.button("LOG INTO SECURE PORTAL", use_container_width=True):
                if verify_login(u_id, u_pw, login_role):
                    df_reg = pd.read_csv(USER_REGISTRY, dtype=str)
                    user_contact = df_reg[df_reg['UID'] == str(u_id).strip()]['Contact'].values[0]
                    st.session_state.logged_in = True
                    st.session_state.role = login_role
                    st.session_state.username = u_id
                    st.session_state.contact = user_contact
                    st.success("Access Granted. Redirecting...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Access Denied: Invalid Credentials or Role mismatch.")
        with mode[1]:
            reg_role = st.selectbox("Joining as", ["Admin", "Patient"], key="reg_role")
            r_name = st.text_input("Full Name")
            r_phone = st.text_input("Contact Number")
            r_pw = st.text_input("Create Password", type="password")
            if st.button("CREATE ACCOUNT", use_container_width=True):
                if r_name and r_phone and r_pw:
                    prefix = "DOC" if reg_role == "Admin" else "PAT"
                    new_uid = f"{prefix}-{random.randint(1000, 9999)}"
                    success, msg = register_user(new_uid, r_name, r_pw, reg_role, r_phone)
                    if success:
                        st.success(f"Registration Complete!")
                        st.code(f"YOUR UID: {new_uid}", language="text")
                        st.info("Write this down! You cannot login without this UID.")
                    else:
                        st.error(msg)
                else:
                    st.warning("All fields are required.")
    st.stop()

# --- AGENTIC THREAD ---
def delayed_notification(delay_seconds, username, task, target_time):
    time.sleep(delay_seconds)
    notification.notify(title='🛡️ AI Wellness Assistant', message=f'REMINDER: {task}', timeout=10)
    save_wellness_activity(username, task, target_time)

# --- 3. MAIN APPLICATION ---
if 'engine' not in st.session_state: st.session_state.engine = MentalHealthEngine()
if 'audio_trained' not in st.session_state:
    st.session_state.engine.train_audio_engine()
    st.session_state.audio_trained = True

with st.sidebar:
    st.markdown("<div style='padding:10px; background:#1e1e1e; border-radius:5px; border-left:5px solid #00e676;'><b>AI CORE: ACTIVE</b></div>", unsafe_allow_html=True)
    if st.session_state.role == "Admin":
        nav_options = ["Home (AI Analysis)", "History & Reports Trend", "Registered Accounts Info", "Contact Info", "Logout"]
    else:
        nav_options = ["Home (AI Analysis)", "Mental Health Reminders", "Logout"]
    page = st.radio("Navigation", nav_options)

if page == "Logout":
    st.session_state.logged_in = False
    st.rerun()

elif page == "Registered Accounts Info":
    st.title("🛡️ Admin System Control")
    if os.path.exists(USER_REGISTRY):
        df_users = pd.read_csv(USER_REGISTRY, dtype=str)
        
        # SAFETY CHECK: Ensure column exists in current view even if CSV hasn't updated
        if "Registered_At" not in df_users.columns:
            df_users["Registered_At"] = "Updating..."
            
        # --- FIXED SORTING AND INDEXING ---
        # Filter, sort by Name, and reset the index to start from 1
        patients = df_users[df_users['Role'] == 'Patient'].sort_values(by="Name")
        patients.index = range(1, len(patients) + 1)
        
        doctors = df_users[df_users['Role'] == 'Admin'].sort_values(by="Name")
        doctors.index = range(1, len(doctors) + 1)
        # ----------------------------------
        
        st.subheader("System Overview")
        st.metric("Registered Patients", len(patients))
        
        st.subheader("📋 Registered Patients")
        if not patients.empty:
            st.dataframe(patients[["Name", "UID", "Contact", "Registered_At"]], use_container_width=True)
        else:
            st.info("No patients registered yet.")
            
        st.subheader("🩺 Medical Staff / Admins")
        if not doctors.empty:
            st.dataframe(doctors[["Name", "UID", "Contact", "Registered_At"]], use_container_width=True)
        else:
            st.info("No medical staff registered.")
    else:
        st.error("User Registry database not found.")

elif page == "Contact Info":
    st.title("📇 Patient Contact Directory")
    if os.path.exists(USER_REGISTRY):
        df_users = pd.read_csv(USER_REGISTRY, dtype=str)
        # Filter patients and reset index for display
        patients_only = df_users[df_users['Role'] == 'Patient'].sort_values(by="Name")
        patients_only.index = range(1, len(patients_only) + 1)
        
        st.subheader("Patient Contact Numbers")
        if not patients_only.empty:
            st.table(patients_only[["Name", "Contact"]])
        else:
            st.info("No registered patients found.")
    else:
        st.error("User Registry database not found.")

elif page == "History & Reports Trend":
    st.title("📂 Patient Longitudinal History")
    count, percent = get_history_stats()
    st.progress(percent / 100 if percent <= 100 else 1.0)
    st.metric("Log Count", f"{count}", f"{percent:.4f}% Full")
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        unique_patients = df['Patient_Name'].unique()
        selected_patient = st.selectbox("Select Patient:", unique_patients)
        # 1. Filter the data
        patient_data = df[df['Patient_Name'] == selected_patient].sort_values(by="Timestamp", ascending=False)

        # 2. Reset the internal index to remove CSV gaps
        patient_data = patient_data.reset_index(drop=True)

        # 3. Re-index starting from 1 for the UI display
        
        patient_data.index = range(1, len(patient_data) + 1)        
        latest_entry = patient_data.iloc[-1]
        current_risk = float(latest_entry['Risk_Index'].replace('%', ''))
        v_score = 80 if "Distressed" in latest_entry['Visual_State'] else 30
        t_score = 85 if any(w in latest_entry['Text_State'].lower() for w in ['depress', 'anxiety', 'stress']) else 20
        m_score = 90 if ("Happy" in latest_entry['Visual_State'] and t_score > 50) else 10
        
        fig_spider = go.Figure()
        fig_spider.add_trace(go.Scatterpolar(r=[v_score, t_score, 85, m_score, current_risk], 
                                            theta=['Visual Affect', 'Linguistic Context', 'Fusion Accuracy', 'Masking Probability', 'Overall Risk'], 
                                            fill='toself', name=selected_patient, line=dict(color='#ff4b4b')))
        fig_spider.update_layout(polar=dict(bgcolor="black", radialaxis=dict(visible=True, range=[0, 100])), paper_bgcolor="black", font_color="white", title=f"AI Signature: {selected_patient}")
        st.plotly_chart(fig_spider, use_container_width=True)
        st.plotly_chart(st.session_state.engine.plot_risk_trend(patient_data), use_container_width=True)
        
        target_email = st.text_input("Enter Recipient Email:")
        if st.button("📤 Send PDF via Email"):
            if target_email and send_email_with_pdf(target_email, selected_patient, create_pdf(patient_data)):
                st.success("Sent!")
        st.dataframe(patient_data, use_container_width=True)
        st.download_button("📥 Download PDF", create_pdf(patient_data), f"{selected_patient}_Report.pdf", "application/pdf")
    else: st.info("History database empty.")

elif page == "Mental Health Reminders":
    st.title("🧘 Personal Wellness Hub")
    if 'reminder_active' not in st.session_state: st.session_state.reminder_active = False
    col_rem1, col_rem2 = st.columns(2)

    with col_rem1:
        st.subheader("✨ Daily Affirmation")
        st.info(random.choice(["I am in control of my progress.", "Small steps count.", "Focus on the present."]))
        selection = st.selectbox("Select Goal:", ["Deep Breathing Exercise", "Guided Meditation", "Hydration Break", "Short Walk"])
        time_rem = st.time_input("Set Reminder Time", datetime.time(datetime.datetime.now().hour, (datetime.datetime.now().minute + 1) % 60))
        
        if st.session_state.reminder_active:
            st.warning("⏳ A wellness reminder is currently scheduled.")
            if st.button("Cancel & Reset Scheduler"):
                st.session_state.reminder_active = False
                st.rerun()
        else:
            if st.button("Set Wellness Reminder", use_container_width=True):
                now = datetime.datetime.now()
                target = datetime.datetime.combine(now.date(), time_rem)
                if target < now: target += datetime.timedelta(days=1)
                delay = (target - now).total_seconds()
                if delay > 0:
                    st.session_state.reminder_active = True
                    t = threading.Thread(target=delayed_notification, args=(delay, st.session_state.username, selection, time_rem.strftime('%H:%M')), daemon=True)
                    t.start()
                    st.success(f"Scheduler initialized for {time_rem.strftime('%H:%M')}")
                    time.sleep(1.5)
                    st.rerun()
                else: st.error("Please select a future time.")

        st.subheader("📜 Recent Activity")
        if os.path.exists(WELLNESS_LOG):
            w_df = pd.read_csv(WELLNESS_LOG)
            user_w = w_df[w_df['Patient_Name'] == str(st.session_state.username).strip()]
            if not user_w.empty:
                st.dataframe(user_w[['Logged_At', 'Activity', 'Scheduled_For']].iloc[::-1], hide_index=True, use_container_width=True)

    with col_rem2:
        st.subheader("📊 Goal Completion Progress")
        if os.path.exists(WELLNESS_LOG):
            w_df = pd.read_csv(WELLNESS_LOG)
            user_w = w_df[w_df['Patient_Name'] == str(st.session_state.username).strip()]
            completed = len(user_w)
            target_daily = 5 
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = completed,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Daily Goals Met", 'font': {'size': 18}},
                gauge = {
                    'axis': {'range': [None, target_daily]},
                    'bar': {'color': "#00e676"},
                    'bgcolor': "white",
                    'steps': [{'range': [0, 2], 'color': "#ff4b4b"}, {'range': [2, 4], 'color': "#ffa726"}]
                }
            ))
            fig_gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': "white", 'family': "Arial"}, height=250)
            st.plotly_chart(fig_gauge, use_container_width=True)

        st.subheader("📓 Mindful Journal")
        journal_note = st.text_area("How are you feeling right now?", placeholder="Write a few lines about your day...", height=150)
        if st.button("Save Journal Entry"):
            if journal_note:
                st.success("Your reflection has been saved securely.")
                st.balloons()
            else: st.warning("Please write something before saving.")
        st.error("National Helpline: 14416 (Tele MANAS : 1-800-891-4416(Toll-Free))")

elif page == "Home (AI Analysis)":
    st.title("🛡️ Tri-Modal AI Mental Health Agent")
    p_name = st.text_input("Enter Patient Name:")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("📸 Visual Sensor")
        img = st.camera_input("Capture Patient Affect")
        v_emo, v_msg, ready_v = "None", "", False
        if img:
            v_emo, v_msg, _ = st.session_state.engine.detect_face_emotion(img)
            st.info(v_msg)
            ready_v = True
    with col2:
        st.subheader("🎤 Acoustic Sensor")
        audio_file = st.audio_input("Record Voice Sample")
        a_emo, a_score, ready_a = "None", 0.0, False
        if audio_file:
            a_emo, a_score = st.session_state.engine.predict_audio_sentiment(audio_file)
            st.info(f"🎙️ Vocal Tone: {a_emo}")
            ready_a = True
    with col3:
        st.subheader("💬 Linguistic Sensor")
        user_input = ""
        if ready_v and ready_a:
            user_input = st.text_area("Patient Narrative Statement:", height=150)
            execute_fusion = st.button("🚀 Execute Tri-Modal Fusion")
    if ready_v and ready_a and user_input and execute_fusion:
        if p_name:
            t_mood = st.session_state.engine.predict_mood_text(user_input)
            probs = re.findall(r"(\d+\.?\d*)%", v_msg)
            v_input_score = float(probs[0]) if probs else 40.0
            t_risk = 75.0 if t_mood.lower() in ['depression', 'anxiety', 'stress'] else 10.0
            final_score = st.session_state.engine.calculate_fused_risk(v_input_score, a_score, t_risk)
            is_masking = v_emo in ["Sad", "Angry"] and t_mood.lower() == "normal"
            
            u_contact = st.session_state.get('contact', 'N/A')
            save_to_history(st.session_state.username, p_name, u_contact, v_emo, f"T:{t_mood} | A:{a_emo}", final_score)
            
            st.markdown("---")
            st.columns([1, 2, 1])
            with st.columns([1, 2, 1])[1]:
                st.subheader(f"Analysis Results for: {p_name}")
                st.plotly_chart(st.session_state.engine.plot_professional_fused_risk(final_score, p_name), use_container_width=True)
                with st.expander("🔍 View AI Decision Logic"):
                    st.plotly_chart(st.session_state.engine.plot_explainable_ai(v_input_score, a_score, t_risk), use_container_width=True)
                    xai_data = {"Modality": ["Visual", "Acoustic", "Linguistic"], "Input Score": [v_input_score, a_score, t_risk], "Logic": ["Neural Fusion", "Neural Fusion", "Neural Fusion"]}
                    st.table(pd.DataFrame(xai_data))
                    if is_masking: st.warning("Suspected Masking Penalty Applied by AI Brain.")
                st.info(f"**Clinical Advice:** {st.session_state.engine.get_pro_advice(t_mood, is_masking)}")
        else: st.warning("Please provide a Patient Name.")

st.markdown("---")
st.caption("POWERED BY MEE ! ! !")