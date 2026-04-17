import streamlit as st
from database import SessionLocal, init_db
from agents.orchestrator import get_profile, has_profile, has_cv, get_jobs, update_job_status
from agents.job_search import search_jobs
from agents.cv_scorer import score_batch
from services.csv_export import load_running_sheet

init_db()

st.title("Job Search")

db = SessionLocal()
try:
    if not has_profile(db):
        st.warning("Please complete onboarding first.")
        st.page_link("pages/2_Onboarding.py", label="Go to Onboarding")
        st.stop()

    profile = get_profile(db)

    # Search controls
    st.subheader("Search for Jobs")
    col1, col2 = st.columns([3, 1])
    with col1:
        custom_query = st.text_input(
            "Search query (leave empty to use your profile preferences)",
            placeholder=f"e.g., {', '.join(profile.preferred_roles[:2]) if profile.preferred_roles else 'Software Engineer'}",
        )
    with col2:
        custom_location = st.text_input(
            "Location",
            placeholder="e.g., Remote, Bangalore",
        )

    # JobSpy site selection
    available_sites = ["indeed", "linkedin", "glassdoor", "zip_recruiter", "google"]
    selected_sites = st.multiselect(
        "Job boards to search",
        available_sites,
        default=["indeed", "linkedin", "glassdoor"],
        help="Select which job boards to scrape",
    )

    results_wanted = st.slider("Results per site", min_value=5, max_value=25, value=10)

    col_search, col_score = st.columns(2)

    with col_search:
        if st.button("Search Jobs", type="primary", use_container_width=True):
            if not selected_sites:
                st.warning("Please select at least one job board.")
            else:
                with st.spinner("Scraping job boards (this may take a minute)..."):
                    new_jobs = search_jobs(
                        db, profile, custom_query, custom_location,
                        sites=selected_sites, results_wanted=results_wanted,
                    )
                if new_jobs:
                    st.success(f"Found {len(new_jobs)} new jobs!")
                else:
                    st.info("No new jobs found. Try different search terms or job boards.")

    with col_score:
        unscored = [j for j in get_jobs(db, status="new") if j.cv_score is None]
        if st.button(
            f"Score Unscored Jobs ({len(unscored)})",
            use_container_width=True,
            disabled=not unscored or not has_cv(db),
        ):
            with st.spinner(f"Scoring {len(unscored)} jobs in batches..."):
                score_batch(db, profile, unscored)
            st.success("Scoring complete!")
            st.rerun()

    st.markdown("---")

    # Running Sheet Export
    st.subheader("Running Sheet")
    running_sheet = load_running_sheet()
    if running_sheet is not None and not running_sheet.empty:
        col_dl, col_info = st.columns([1, 3])
        with col_dl:
            csv_data = running_sheet.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name="jobs_running_sheet.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with col_info:
            st.caption(f"{len(running_sheet)} total jobs tracked across all searches")

        with st.expander("Preview Running Sheet"):
            display_cols = [c for c in ["title", "company", "location", "source", "match_score", "status", "date_posted"] if c in running_sheet.columns]
            st.dataframe(running_sheet[display_cols].tail(200), use_container_width=True)
    else:
        st.caption("No running sheet yet. Run a search to start tracking jobs.")

    st.markdown("---")

    # Filters
    st.subheader("Results")
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        status_filter = st.selectbox("Status", ["all", "new", "saved", "applied", "dismissed"])
    with filter_col2:
        min_score = st.slider("Minimum Score", 0, 100, 0)
    with filter_col3:
        sort_by = st.selectbox("Sort by", ["Score (High)", "Score (Low)", "Newest"])

    # Get filtered jobs
    jobs = get_jobs(db, status=status_filter if status_filter != "all" else None,
                    min_score=min_score if min_score > 0 else None)

    if sort_by == "Score (Low)":
        jobs = sorted(jobs, key=lambda j: j.cv_score or 0)
    elif sort_by == "Newest":
        jobs = sorted(jobs, key=lambda j: j.discovered_at or j.created_at, reverse=True)

    st.write(f"Showing {len(jobs)} jobs")

    # Display jobs
    for job in jobs:
        score = job.cv_score
        score_display = f"[{int(score)}%] " if score is not None else ""
        status_badge = f" ({job.status})" if job.status != "new" else ""

        with st.expander(f"{score_display}{job.title} at {job.company}{status_badge}"):
            info_col, action_col = st.columns([3, 1])

            with info_col:
                st.markdown(f"**Company:** {job.company}")
                st.markdown(f"**Location:** {job.location}")
                if job.remote_type and job.remote_type != "unknown":
                    st.markdown(f"**Type:** {job.remote_type}")
                if job.salary_min or job.salary_max:
                    salary = ""
                    if job.salary_min:
                        salary += f"₹{job.salary_min:,.0f}"
                    if job.salary_max:
                        salary += f" - ₹{job.salary_max:,.0f}"
                    st.markdown(f"**Salary:** {salary}")
                st.markdown(f"**Source:** {job.source}")

                if job.description_summary:
                    st.markdown("**Summary:**")
                    st.markdown(job.description_summary)

                if job.score_explanation:
                    st.markdown(f"**Score Analysis:** {job.score_explanation}")

                if job.score_details:
                    details = job.score_details if isinstance(job.score_details, dict) else {}
                    matches = details.get("matches", [])
                    gaps = details.get("gaps", [])
                    if matches:
                        st.markdown("**Matches:** " + ", ".join(matches[:5]))
                    if gaps:
                        st.markdown("**Gaps:** " + ", ".join(gaps[:5]))

                if job.url:
                    st.markdown(f"[View Original Posting]({job.url})")

            with action_col:
                st.markdown("**Actions:**")
                if job.status != "saved":
                    if st.button("Save", key=f"save_{job.id}"):
                        update_job_status(db, job.id, "saved")
                        st.rerun()
                if job.status != "applied":
                    if st.button("Mark Applied", key=f"apply_{job.id}"):
                        update_job_status(db, job.id, "applied")
                        st.rerun()
                if job.status != "dismissed":
                    if st.button("Dismiss", key=f"dismiss_{job.id}"):
                        update_job_status(db, job.id, "dismissed")
                        st.rerun()

finally:
    db.close()
