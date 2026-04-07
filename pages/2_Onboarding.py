import streamlit as st
from database import SessionLocal, init_db
from agents.onboarding import save_cv_file, process_cv, save_profile
from agents.orchestrator import get_profile

init_db()

st.title("Profile Setup")

db = SessionLocal()
try:
    existing = get_profile(db)

    # Show current profile if exists
    if existing and existing.name:
        st.success(f"Profile exists for **{existing.name}**. Update below or skip to Job Search.")
        with st.expander("Current Profile", expanded=False):
            st.write(f"**Email:** {existing.email}")
            st.write(f"**Location:** {existing.location}")
            st.write(f"**Roles:** {', '.join(existing.preferred_roles or [])}")
            st.write(f"**Skills:** {', '.join((existing.skills or [])[:15])}")
            if existing.parsed_cv_text:
                st.write(f"**CV:** Uploaded ({len(existing.parsed_cv_text)} chars)")

    st.markdown("---")

    # Step 1: Upload CV
    st.subheader("Step 1: Upload Your CV")
    uploaded_file = st.file_uploader(
        "Upload your CV (PDF, DOCX, or TXT)",
        type=["pdf", "docx", "doc", "txt"],
        help="Your CV will be parsed locally and personal details will be auto-filled."
    )

    cv_data = None
    raw_cv_path = ""
    if uploaded_file:
        with st.spinner("Parsing CV..."):
            file_bytes = uploaded_file.read()
            raw_cv_path = save_cv_file(file_bytes, uploaded_file.name)
            cv_data = process_cv(db, raw_cv_path)

        st.success("CV parsed successfully! Personal details have been auto-filled below.")
        with st.expander("Extracted Skills", expanded=True):
            skills = cv_data.get("skills", [])
            st.write(", ".join(skills) if skills else "No skills detected")
        with st.expander("CV Preview", expanded=False):
            st.text(cv_data["parsed_cv_text"][:2000])

        # Store extracted contact details in session state for auto-fill
        st.session_state["cv_name"] = cv_data.get("name", "")
        st.session_state["cv_email"] = cv_data.get("email", "")
        st.session_state["cv_phone"] = cv_data.get("phone", "")
        st.session_state["cv_location"] = cv_data.get("location", "")
    elif existing and existing.parsed_cv_text:
        cv_data = {
            "parsed_cv_text": existing.parsed_cv_text,
            "structured_cv": existing.structured_cv,
            "skills": existing.skills,
        }
        raw_cv_path = existing.raw_cv_path

    # Determine default values: CV-extracted > existing profile > empty
    def _default(field: str) -> str:
        cv_val = st.session_state.get(f"cv_{field}", "")
        if cv_val:
            return cv_val
        if existing:
            return getattr(existing, field, "") or ""
        return ""

    st.markdown("---")

    # Step 2: Personal Details
    st.subheader("Step 2: Your Details")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Full Name", value=_default("name"))
        email = st.text_input("Email", value=_default("email"))
        phone = st.text_input("Phone", value=_default("phone"))
    with col2:
        location = st.text_input("Current Location", value=_default("location"))
        min_salary = st.number_input(
            "Minimum Expected Salary (INR/year)",
            min_value=0,
            value=int(existing.min_salary or 0) if existing else 0,
            step=50000,
        )

    st.markdown("---")

    # Step 3: Job Preferences
    st.subheader("Step 3: What roles are you looking for?")
    roles_text = st.text_area(
        "Enter roles (one per line)",
        value="\n".join(existing.preferred_roles or []) if existing else "",
        placeholder="Software Engineer\nBackend Developer\nFull Stack Developer",
        help="The agent will search for these roles across job boards."
    )

    st.markdown("---")

    # Step 4: Location Preferences
    st.subheader("Step 4: Location & Remote Preference")
    locations_text = st.text_area(
        "Preferred locations (one per line, leave empty for any)",
        value="\n".join(existing.preferred_locations or []) if existing else "",
        placeholder="Bangalore\nHyderabad\nRemote",
    )
    remote_pref = st.selectbox(
        "Remote preference",
        ["any", "remote", "hybrid", "onsite"],
        index=["any", "remote", "hybrid", "onsite"].index(
            existing.remote_preference if existing else "any"
        ),
    )

    st.markdown("---")

    # Step 5: Projects & Portfolio
    st.subheader("Step 5: Projects & Portfolio")

    portfolio_url = st.text_input(
        "Portfolio URL (GitHub profile, personal website, etc.)",
        value=(existing.portfolio_url if existing and hasattr(existing, 'portfolio_url') else ""),
        placeholder="https://github.com/username",
    )

    if portfolio_url and st.button("Fetch & Fill Projects from Portfolio"):
        with st.spinner("Fetching portfolio..."):
            try:
                from services.portfolio_parser import fetch_portfolio, summarize_portfolio
                raw_content = fetch_portfolio(portfolio_url)
                if raw_content:
                    summary = summarize_portfolio(db, raw_content)
                    st.session_state["portfolio_projects"] = summary
                    st.success("Portfolio fetched! Projects have been filled below.")
                else:
                    st.warning("Could not extract content from the provided URL.")
            except Exception as e:
                st.error(f"Failed to fetch portfolio: {e}")

    # Use portfolio-fetched projects if available
    default_projects = st.session_state.get("portfolio_projects", "")
    if not default_projects:
        default_projects = existing.projects_summary if existing else ""

    projects = st.text_area(
        "Describe 2-3 of your most impactful projects",
        value=default_projects,
        placeholder="Built a real-time data pipeline processing 1M events/day...\nLed a team of 5 to redesign the checkout flow, improving conversion by 15%...",
        height=150,
    )

    st.markdown("---")

    # Save
    if st.button("Save Profile", type="primary", use_container_width=True):
        roles = [r.strip() for r in roles_text.strip().split("\n") if r.strip()]
        locations = [l.strip() for l in locations_text.strip().split("\n") if l.strip()]

        with st.spinner("Saving profile..."):
            save_profile(
                db=db,
                name=name,
                email=email,
                phone=phone,
                location=location,
                preferred_roles=roles,
                preferred_locations=locations,
                remote_preference=remote_pref,
                min_salary=min_salary if min_salary > 0 else None,
                projects_summary=projects,
                cv_data=cv_data,
                raw_cv_path=raw_cv_path,
                portfolio_url=portfolio_url,
            )

        st.success("Profile saved! Head to Job Search to find matching positions.")
        st.page_link("pages/3_Job_Search.py", label="Go to Job Search")

finally:
    db.close()
