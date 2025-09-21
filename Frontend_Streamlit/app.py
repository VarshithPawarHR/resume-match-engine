import streamlit as st
import requests
from pathlib import Path

API_URL = "http://localhost:8000"

st.set_page_config(page_title="ATS Resume Scoring", layout="wide")
st.markdown(
    """
    <style>
    .stButton>button {
        background-color: #4CAF50;
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

st.title("Modern ATS Resume Scoring System")

# --- User UUID ---
user_uuid = st.text_input("Enter Your User UUID", "")

# --- Upload Job Description ---
jd_file = st.file_uploader("Upload Job Description (PDF/DOCX)", type=["pdf", "docx"])

# --- Single vs Bulk Upload ---
tab = st.radio("Select Upload Mode:", ["Single Resume", "Bulk Resumes (ZIP)"], horizontal=True)

if tab == "Single Resume":
    resume_file = st.file_uploader("Upload Resume (PDF/DOCX)", type=["pdf", "docx"], key="single")

    if st.button("Analyze Single Resume"):
        if not (jd_file and resume_file and user_uuid):
            st.error("Please provide all inputs!")
        else:
            files = {
                "jd": (jd_file.name, jd_file, jd_file.type),
                "resume": (resume_file.name, resume_file, resume_file.type)
            }
            data = {"user_uuid": user_uuid}

            with st.spinner("Analyzing resume..."):
                response = requests.post(f"{API_URL}/upload/", files=files, data=data)

            if response.status_code == 200:
                results = response.json()["analysis_results"]
                st.success("Analysis completed!")

                for res in results:
                    analysis = res["analysis"]
                    fit_score = analysis.get("overall_fit_score", 0)
                    fit_level = analysis.get("fit_level", "NO_FIT")

                    color = "#4CAF50" if fit_level == "HIGH_FIT" else "#FF9800" if fit_level == "MEDIUM_FIT" else "#F44336"

                    st.markdown(f"###  {res['resume_file']}")
                    st.progress(fit_score / 100.0)
                    st.markdown(f"**Fit Level:** <span style='color:{color}; font-weight:bold'>{fit_level}</span>",
                                unsafe_allow_html=True)
                    st.markdown(f"**Recommendation:** {analysis.get('recommendation')}")

                    with st.expander("Key Strengths"):
                        for s in analysis.get("key_strengths", []):
                            st.markdown(f"-  {s}")
                    with st.expander("Major Concerns"):
                        for c in analysis.get("major_concerns", []):
                            st.markdown(f"-  {c}")

                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Skills Assessment**")
                        skills = analysis.get("skills_assessment", {})
                        st.markdown(f"- Required Skills Match: {skills.get('required_skills_match', 0)}%")
                        st.markdown(f"- Preferred Skills Match: {skills.get('preferred_skills_match', 0)}%")
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

else:  # Bulk Resumes
    resumes_zip = st.file_uploader("Upload Resumes ZIP", type=["zip"], key="bulk")

    if st.button("Analyze Bulk Resumes"):
        if not (jd_file and resumes_zip and user_uuid):
            st.error("Please provide all inputs!")
        else:
            files = {
                "jd": (jd_file.name, jd_file, jd_file, jd_file.type),
                "resumes_zip": (resumes_zip.name, resumes_zip, resumes_zip.type)
            }
            data = {"user_uuid": user_uuid}

            with st.spinner("Analyzing bulk resumes..."):
                response = requests.post(f"{API_URL}/bulk-upload/", files=files, data=data)

            if response.status_code == 200:
                results = response.json()["analysis_results"]
                st.success(f" Bulk analysis completed: {len(results)} resumes")

                for res in results:
                    analysis = res["analysis"]
                    fit_score = analysis.get("overall_fit_score", 0)
                    fit_level = analysis.get("fit_level", "NO_FIT")

                    color = "#4CAF50" if fit_level == "HIGH_FIT" else "#FF9800" if fit_level == "MEDIUM_FIT" else "#F44336"

                    st.markdown(f"###  {res['resume_file']}")
                    st.progress(fit_score / 100.0)
                    st.markdown(f"**Fit Level:** <span style='color:{color}; font-weight:bold'>{fit_level}</span>",
                                unsafe_allow_html=True)
                    st.markdown(f"**Recommendation:** {analysis.get('recommendation')}")

                    with st.expander("Key Strengths"):
                        for s in analysis.get("key_strengths", []):
                            st.markdown(f"-  {s}")
                    with st.expander("Major Concerns"):
                        for c in analysis.get("major_concerns", []):
                            st.markdown(f"-  {c}")

# --- Previous Results ---
st.markdown("---")
st.subheader(" View Previous Results")
user_uuid_view = st.text_input("Enter User UUID to Fetch Results", key="view_uuid")

if st.button("Fetch Results"):
    if not user_uuid_view:
        st.error("Please enter your UUID")
    else:
        with st.spinner("Fetching results..."):
            response = requests.get(f"{API_URL}/results/{user_uuid_view}")

        if response.status_code == 200:
            results = response.json()
            st.success(f"Found {results['total_results']} analyses for {results['user_uuid']}")
            for analysis in results["analyses"]:
                fit_score = analysis.get("overall_fit_score", 0)
                fit_level = analysis.get("fit_level", "NO_FIT")
                color = "#4CAF50" if fit_level == "HIGH_FIT" else "#FF9800" if fit_level == "MEDIUM_FIT" else "#F44336"

                st.markdown(f"###  {analysis.get('candidate_name', 'Unknown')}")
                st.progress(fit_score / 100.0)
                st.markdown(f"**Fit Level:** <span style='color:{color}; font-weight:bold'>{fit_level}</span>",
                            unsafe_allow_html=True)
                st.markdown(f"**Recommendation:** {analysis.get('recommendation')}")
