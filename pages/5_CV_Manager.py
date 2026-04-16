import streamlit as st
from database import SessionLocal, init_db
from agents.orchestrator import get_profile, get_jobs, has_cv
from agents.cv_scorer import score_single_job
from agents.cv_rewriter import rewrite_cv_for_job

init_db()

st.title("CV Manager")

db = SessionLocal()
try:
    profile = get_profile(db)

    if not profile or not profile.parsed_cv_text:
        st.warning("Upload your CV in Onboarding first.")
        st.page_link("pages/2_Onboarding.py", label="Go to Onboarding")
        st.stop()

    # CV Overview
    st.subheader("Your CV")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Name:** {profile.name}")
        st.markdown(f"**Skills ({len(profile.skills or [])}):** {', '.join((profile.skills or [])[:20])}")
        if profile.experience_summary:
            st.markdown(f"**Experience:** {profile.experience_summary[:300]}")
    with col2:
        st.metric("CV Length", f"{len(profile.parsed_cv_text):,} chars")
        st.metric("Skills Detected", len(profile.skills or []))

    with st.expander("View Full CV Text"):
        st.text(profile.parsed_cv_text)

    st.markdown("---")

    # Score CV against a specific job
    st.subheader("Score CV Against a Job")
    all_jobs = get_jobs(db)
    if not all_jobs:
        st.info("No jobs found. Search for jobs first!")
        st.page_link("pages/3_Job_Search.py", label="Go to Job Search")
    else:
        job_options = {f"{j.title} at {j.company} (ID: {j.id})": j.id for j in all_jobs}
        selected_job_label = st.selectbox("Select a job to score against", list(job_options.keys()))
        selected_job_id = job_options[selected_job_label]
        selected_job = next((j for j in all_jobs if j.id == selected_job_id), None)
        if not selected_job:
            st.error("Selected job not found. Please refresh the page.")
            st.stop()

        score_col, rewrite_col = st.columns(2)

        with score_col:
            if st.button("Score My CV", type="primary", use_container_width=True):
                with st.spinner("Scoring your CV against this job..."):
                    result = score_single_job(db, profile, selected_job)

                score = result.get("score", 0)
                color = "green" if score >= 70 else "orange" if score >= 50 else "red"

                st.markdown(f"### Score: :{color}[{score}%]")
                st.markdown(f"**Analysis:** {result.get('explanation', '')}")

                matches = result.get("matches", [])
                gaps = result.get("gaps", [])
                if matches:
                    st.markdown("**Matching Skills/Experience:**")
                    for m in matches:
                        st.markdown(f"- {m}")
                if gaps:
                    st.markdown("**Gaps to Address:**")
                    for g in gaps:
                        st.markdown(f"- {g}")

        with rewrite_col:
            if st.button("Rewrite CV for This Job", use_container_width=True,
                         help="Uses a more capable (expensive) model to rewrite your CV"):
                with st.spinner("Rewriting your CV (this uses the full model)..."):
                    rewritten = rewrite_cv_for_job(db, profile, selected_job)

                st.success("CV rewritten!")

        # Show existing rewrites
        if selected_job.rewritten_cv_path:
            st.markdown("---")
            st.subheader("Tailored CV")
            try:
                with open(selected_job.rewritten_cv_path) as f:
                    rewritten_content = f.read()
                st.markdown(rewritten_content)

                st.download_button(
                    "Download Tailored CV (Markdown)",
                    data=rewritten_content,
                    file_name=f"cv_for_{selected_job.company.lower().replace(' ', '_')}.md",
                    mime="text/markdown",
                )
            except FileNotFoundError:
                st.warning("Rewritten CV file not found. Try rewriting again.")

    # All rewritten CVs
    st.markdown("---")
    st.subheader("All Tailored CVs")
    jobs_with_rewrites = [j for j in all_jobs if j.rewritten_cv_path] if all_jobs else []
    if jobs_with_rewrites:
        for job in jobs_with_rewrites:
            with st.expander(f"CV for: {job.title} at {job.company}"):
                try:
                    with open(job.rewritten_cv_path) as f:
                        content = f.read()
                    st.markdown(content)
                    st.download_button(
                        "Download",
                        data=content,
                        file_name=f"cv_{job.company.lower().replace(' ', '_')}.md",
                        mime="text/markdown",
                        key=f"dl_{job.id}",
                    )
                except FileNotFoundError:
                    st.warning("File not found")
    else:
        st.info("No tailored CVs yet. Score a job and click 'Rewrite CV' to create one.")

finally:
    db.close()
