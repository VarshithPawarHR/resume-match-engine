import streamlit as st
import requests
import uuid
import pandas as pd

API_URL = "https://08b745788978.ngrok-free.app/"  # Replace with your FastAPI backend

# --- Streamlit Page Config ---
st.set_page_config(page_title="ATS Resume Scoring", layout="wide")
st.markdown("""
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
    .skill-bar {
        height: 25px;
        border-radius: 12px;
        margin-bottom: 8px;
        background-color: #e0e0e0;
        overflow: hidden;
    }
    .skill-fill {
        height: 100%;
        border-radius: 12px;
        text-align: right;
        padding-right: 10px;
        color: white;
        font-weight: bold;
        line-height: 25px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("ATS Resume Scoring System")

# --- Generate per-session UUID ---
if "user_uuid" not in st.session_state:
    st.session_state.user_uuid = str(uuid.uuid4())
st.markdown(f"**Session UUID:** `{st.session_state.user_uuid}`")

# --- Upload Job Description ---
jd_file = st.file_uploader("Upload Job Description (PDF/DOCX)", type=["pdf", "docx"])

# --- Single vs Bulk Resume Upload ---
upload_mode = st.radio("Select Upload Mode:", ["Single Resume", "Bulk Resumes (ZIP)"], horizontal=True)

if upload_mode == "Single Resume":
    resume_file = st.file_uploader("Upload Resume (PDF/DOCX)", type=["pdf", "docx"], key="single")
else:
    resumes_zip = st.file_uploader("Upload Resumes ZIP", type=["zip"], key="bulk")

# --- Analyze Button ---
if st.button("Analyze"):
    if not jd_file:
        st.error("Please upload the Job Description.")
    elif upload_mode == "Single Resume" and not resume_file:
        st.error("Please upload a Resume file.")
    elif upload_mode == "Bulk Resumes (ZIP)" and not resumes_zip:
        st.error("Please upload a ZIP of Resumes.")
    else:
        files = {"jd": (jd_file.name, jd_file, jd_file.type)}
        endpoint = ""
        if upload_mode == "Single Resume":
            files["resume"] = (resume_file.name, resume_file, resume_file.type)
            endpoint = "/upload/"
        else:
            files["resumes_zip"] = (resumes_zip.name, resumes_zip, resumes_zip.type)
            endpoint = "/bulk-upload/"

        data = {"user_uuid": st.session_state.user_uuid}

        with st.spinner("Analyzing resumes..."):
            response = requests.post(f"{API_URL}{endpoint}", files=files, data=data)

        if response.status_code == 200:
            results = response.json().get("analysis_results") or response.json().get("analyses")
            st.success(f"✅ Analysis completed: {len(results)} resume(s) processed")

            for res in results:
                analysis = res.get("analysis") if "analysis" in res else res
                resume_name = res.get("resume_file") if "resume_file" in res else "Single Resume"

                st.markdown(f"## {resume_name}")

                # --- Fit Score ---
                fit_score = analysis.get("overall_fit_score", 0)
                fit_level = analysis.get("fit_level", "NO_FIT")
                color = "green" if fit_level == "HIGH_FIT" else "orange" if fit_level == "MEDIUM_FIT" else "red"
                st.markdown(f"**Fit Level:** <span style='color:{color}; font-weight:bold'>{fit_level}</span>",
                            unsafe_allow_html=True)
                st.progress(fit_score / 100.0)
                st.markdown(f"**Recommendation:** {analysis.get('recommendation')}")

                # --- Key Strengths & Concerns ---
                with st.expander("Key Strengths"):
                    for s in analysis.get("key_strengths", []):
                        st.markdown(f"- {s}")
                with st.expander("Major Concerns"):
                    for c in analysis.get("major_concerns", []):
                        st.markdown(f"- {c}")

                # --- Skills Assessment (Progress Bars) ---
                st.markdown("### Skills Assessment")
                skills = analysis.get("skills_assessment", {})
                for skill_type, value in [("Required Skills Match", skills.get("required_skills_match", 0)),
                                          ("Preferred Skills Match", skills.get("preferred_skills_match", 0))]:
                    st.markdown(f"**{skill_type}: {value}%**")
                    st.markdown(f"""
                        <div class="skill-bar">
                            <div class="skill-fill" style="width:{value}%; background-color:#1f77b4">{value}%</div>
                        </div>
                    """, unsafe_allow_html=True)

                if skills.get("critical_skills_missing"):
                    st.markdown(f"- Missing Critical Skills: {', '.join(skills.get('critical_skills_missing'))}")

                # --- Experience Fit (Progress Bars) ---
                st.markdown("### Experience Fit")
                exp = analysis.get("experience_fit", {})
                years_required = exp.get("years_required", 0)
                years_candidate = exp.get("years_candidate_has", 0)
                exp_percent = min(100, int((years_candidate / max(1, years_required)) * 100))
                st.markdown(f"**Experience Fit: {exp_percent}%**")
                st.markdown(f"""
                    <div class="skill-bar">
                        <div class="skill-fill" style="width:{exp_percent}%; background-color:#ff7f0e">{exp_percent}%</div>
                    </div>
                """, unsafe_allow_html=True)
                st.markdown(f"- Experience Relevance: {exp.get('experience_relevance', '')}")
                st.markdown(f"- Project Quality: {exp.get('project_quality', '')}")

                # --- Hiring Decision Factors ---
                factors = analysis.get("hiring_decision_factors", {})
                if factors:
                    st.markdown("### Hiring Decision Factors")
                    for factor, score in factors.items():
                        st.markdown(f"**{factor}: {score}%**")
                        st.markdown(f"""
                            <div class="skill-bar">
                                <div class="skill-fill" style="width:{score}%; background-color:#2ca02c">{score}%</div>
                            </div>
                        """, unsafe_allow_html=True)

        else:
            st.error(f"Error: {response.status_code} - {response.text}")
