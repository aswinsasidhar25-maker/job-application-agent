import streamlit as st
import plotly.graph_objects as go
from database import SessionLocal, init_db
from agents.orchestrator import get_dashboard_stats, has_profile

init_db()

st.title("Dashboard")

db = SessionLocal()
try:
    if not has_profile(db):
        st.info("Complete onboarding first to start tracking your job search.")
        st.page_link("pages/2_Onboarding.py", label="Go to Onboarding")
        st.stop()

    stats = get_dashboard_stats(db)

    # Stats cards
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Jobs Found", stats["total_jobs"])
    col2.metric("New", stats["new_jobs"])
    col3.metric("Saved", stats["saved_jobs"])
    col4.metric("Applied", stats["applied_jobs"])
    col5.metric("Interviewing", stats["interviewing"])

    st.markdown("---")

    # Token usage
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Monthly Token Usage")
        st.metric("Total Cost (USD)", f"${stats['monthly_cost']:.4f}")
        st.metric("Total Tokens", f"{stats['monthly_tokens']:,}")

        if stats["cost_by_task"]:
            fig = go.Figure(data=[
                go.Bar(
                    x=list(stats["cost_by_task"].keys()),
                    y=list(stats["cost_by_task"].values()),
                    marker_color=["#4CAF50", "#2196F3", "#FF9800", "#F44336", "#9C27B0"],
                )
            ])
            fig.update_layout(
                title="Cost by Task Type",
                xaxis_title="Task",
                yaxis_title="Cost (USD)",
                height=300,
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Job Pipeline")
        pipeline_data = {
            "New": stats["new_jobs"],
            "Saved": stats["saved_jobs"],
            "Applied": stats["applied_jobs"],
            "Interviewing": stats["interviewing"],
        }
        non_zero = {k: v for k, v in pipeline_data.items() if v > 0}
        if non_zero:
            fig2 = go.Figure(data=[
                go.Pie(
                    labels=list(non_zero.keys()),
                    values=list(non_zero.values()),
                    hole=0.4,
                )
            ])
            fig2.update_layout(title="Jobs by Status", height=300)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No jobs tracked yet. Start a job search!")

    # Recent high-scoring jobs
    st.markdown("---")
    st.subheader("Top Matching Jobs")
    from agents.orchestrator import get_jobs
    top_jobs = get_jobs(db, min_score=50)[:10]
    if top_jobs:
        for job in top_jobs:
            score = job.cv_score or 0
            color = "green" if score >= 70 else "orange" if score >= 50 else "red"
            with st.expander(f"{'[' + str(int(score)) + '%]'} {job.title} at {job.company}"):
                st.markdown(f"**Location:** {job.location}")
                st.markdown(f"**Score:** :{color}[{int(score)}%]")
                st.markdown(f"**Status:** {job.status}")
                if job.description_summary:
                    st.markdown(job.description_summary)
                if job.url:
                    st.markdown(f"[View Job]({job.url})")
    else:
        st.info("No scored jobs yet. Search for jobs and score them!")

finally:
    db.close()
