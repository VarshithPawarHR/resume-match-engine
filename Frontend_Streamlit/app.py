import streamlit as st
import requests
import uuid

API_URL = "http://localhost:8000"  # FastAPI backend

st.set_page_config(page_title="ATS Resume Scoring", layout="wide")
st.markdown(
    """
    <style>
    .stButton>button {
        background-color: #1f77b4;
        color: white;
        height:3em;
        width:100%;
        font-size:16px;
        border-radius:8px;
    }
    .stProgress>div>div>div>div {
        background-color: #1f77b4;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("ATS Resume Scoring System")

# --- Generate per-session UUID ---
if "user_uuid" not in st.session_state:
    st.session_state.user_uuid = str(uuid.uuid4())

st.markdown(f"**Your Session UUID:** `{st.session_state.user_uuid}`")

# --- Upload Job Description ---
jd_file = st.file_uploader("Upload Job Description (PDF/DOCX)", type=["pdf", "docx"])

# --- Single vs Bulk Resume Upload ---
tab = st.radio("Select Upload Mode:", ["Single Resume", "Bulk Resumes (ZIP)"], horizontal=True)

# --- Upload Resume(s) ---
if tab == "Single Resume":
    resume_file = st.file_uploader("Upload Resume (PDF/DOCX)", type=["pdf", "docx"], key="single")
elif tab == "Bulk Resumes (ZIP)":
    resumes_zip = st.file_uploader("Upload Resumes ZIP", type=["zip"], key="bulk")

# --- Analyze Button ---
if st.button("Analyze"):
    if not jd_file:
        st.error("Please upload the Job Description.")
    elif tab == "Single Resume" and not resume_file:
        st.error("Please upload a Resume file.")
    elif tab == "Bulk Resumes (ZIP)" and not resumes_zip:
        st.error("Please upload a ZIP of Resumes.")
    else:
        # Prepare files
        files = {"jd": (jd_file.name, jd_file, jd_file.type)}
        if tab == "Single Resume":
            files["resume"] = (resume_file.name, resume_file, resume_file.type)
            endpoint = "/upload/"
        else:
            files["resumes_zip"] = (resumes_zip.name, resumes_zip, resumes_zip.type)
            endpoint = "/bulk-upload/"

        data = {"user_uuid": st.session_state.user_uuid}

        with st.spinner("Analyzing resumes..."):
            response = requests.post(f"{API_URL}{endpoint}", files=files, data=data)

        if response.status_code == 200:
            results = response.json()["analysis_results"]
            st.success(f" Analysis completed: {len(results)} resume(s) processed")

            # --- Display each resume nicely ---
            for res in results:
                analysis = res["analysis"]
                fit_score = analysis.get("overall_fit_score", 0)
                fit_level = analysis.get("fit_level", "NO_FIT")
                color = "#4CAF50" if fit_level=="HIGH_FIT" else "#FF9800" if fit_level=="MEDIUM_FIT" else "#F44336"

                st.markdown(f"###  {res['resume_file']}")
                st.progress(fit_score / 100.0)
                st.markdown(f"**Fit Level:** <span style='color:{color}; font-weight:bold'>{fit_level}</span>", unsafe_allow_html=True)
                st.markdown(f"**Recommendation:** {analysis.get('recommendation')}")

                # --- Strengths & Concerns ---
                with st.expander("Key Strengths"):
                    for s in analysis.get("key_strengths", []):
                        st.markdown(f"-  {s}")
                with st.expander("Major Concerns"):
                    for c in analysis.get("major_concerns", []):
                        st.markdown(f"-  {c}")

                # --- Skills & Experience ---
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Skills Assessment**")
                    skills = analysis.get("skills_assessment", {})
                    st.markdown(f"- Required Skills Match: {skills.get('required_skills_match',0)}%")
                    st.markdown(f"- Preferred Skills Match: {skills.get('preferred_skills_match',0)}%")
                    missing = skills.get("critical_skills_missing", [])
                    if missing:
                        st.markdown(f"- Missing Critical Skills: {', '.join(missing)}")
                with col2:
                    st.markdown("**Experience Fit**")
                    exp = analysis.get("experience_fit", {})
                    st.markdown(f"- Years Required: {exp.get('years_required')}")
                    st.markdown(f"- Candidate Experience: {exp.get('years_candidate_has')}")
                    st.markdown(f"- Experience Relevance: {exp.get('experience_relevance')}")
        else:
            st.error(f"Error: {response.status_code} - {response.text}")
