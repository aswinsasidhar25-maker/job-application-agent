import streamlit as st
from database import SessionLocal, init_db
from agents.orchestrator import get_jobs, update_job_status

init_db()

st.title("My Jobs")

db = SessionLocal()
try:
    # Tabs for different statuses
    tab_saved, tab_applied, tab_interview, tab_rejected = st.tabs(
        ["Saved", "Applied", "Interviewing", "Rejected"]
    )

    def render_job_list(jobs, tab_name):
        if not jobs:
            st.info(f"No {tab_name.lower()} jobs yet.")
            return

        for job in jobs:
            score = job.cv_score
            score_text = f" - Score: {int(score)}%" if score is not None else ""
            with st.expander(f"{job.title} at {job.company}{score_text}"):
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.markdown(f"**Location:** {job.location}")
                    if job.salary_min or job.salary_max:
                        salary = ""
                        if job.salary_min:
                            salary += f"${job.salary_min:,.0f}"
                        if job.salary_max:
                            salary += f" - ${job.salary_max:,.0f}"
                        st.markdown(f"**Salary:** {salary}")
                    if job.description_summary:
                        st.markdown(job.description_summary)
                    if job.score_explanation:
                        st.markdown(f"**Match Analysis:** {job.score_explanation}")
                    if job.url:
                        st.markdown(f"[View Posting]({job.url})")
                    if job.rewritten_cv_path:
                        st.markdown("**Tailored CV available** - see CV Manager")

                with col2:
                    st.markdown("**Move to:**")
                    statuses = ["new", "saved", "applied", "interviewing", "rejected", "dismissed"]
                    for s in statuses:
                        if s != job.status:
                            label = s.capitalize()
                            if st.button(label, key=f"{tab_name}_{s}_{job.id}"):
                                update_job_status(db, job.id, s)
                                st.rerun()

    with tab_saved:
        render_job_list(get_jobs(db, status="saved"), "Saved")

    with tab_applied:
        render_job_list(get_jobs(db, status="applied"), "Applied")

    with tab_interview:
        render_job_list(get_jobs(db, status="interviewing"), "Interviewing")

    with tab_rejected:
        render_job_list(get_jobs(db, status="rejected"), "Rejected")

    # Summary
    st.markdown("---")
    all_tracked = get_jobs(db)
    status_counts = {}
    for j in all_tracked:
        status_counts[j.status] = status_counts.get(j.status, 0) + 1

    if status_counts:
        st.subheader("Pipeline Summary")
        cols = st.columns(len(status_counts))
        for i, (status, count) in enumerate(status_counts.items()):
            cols[i].metric(status.capitalize(), count)

finally:
    db.close()
