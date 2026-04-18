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
        help="Your CV will be parsed locally - no LLM call for text extraction."
    )

    cv_data = None
    raw_cv_path = ""
    extracted = {}  # structured data from CV LLM call

    if uploaded_file:
        with st.spinner("Parsing CV and extracting your details..."):
            file_bytes = uploaded_file.read()
            raw_cv_path = save_cv_file(file_bytes, uploaded_file.name)
            cv_data = process_cv(db, raw_cv_path)
            extracted = cv_data.get("structured_cv", {}) or {}

        st.success("CV parsed! Fields below have been auto-filled — review and adjust as needed.")
        with st.expander("Extracted Skills", expanded=True):
            skills = cv_data.get("skills", [])
            st.write(", ".join(skills) if skills else "No skills detected")
        with st.expander("CV Preview", expanded=False):
            st.text(cv_data["parsed_cv_text"][:2000])
    elif existing and existing.parsed_cv_text:
        cv_data = {
            "parsed_cv_text": existing.parsed_cv_text,
            "structured_cv": existing.structured_cv,
            "skills": existing.skills,
        }
        raw_cv_path = existing.raw_cv_path

    st.markdown("---")

    # Helper: prefer existing saved value, then CV-extracted, then empty
    def prefill(field, extracted_key=None):
        saved = getattr(existing, field, "") if existing else ""
        if saved:
            return saved
        return extracted.get(extracted_key or field, "") or ""

    # Wrap all profile inputs in a single form — no "Press Enter" needed
    suggested_roles = extracted.get("suggested_roles", [])
    saved_roles = existing.preferred_roles or [] if existing else []
    default_roles = saved_roles or suggested_roles

    with st.form("profile_form"):
        # Step 2: Personal Details
        st.subheader("Step 2: Your Details")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name", value=prefill("name"))
            email = st.text_input("Email", value=prefill("email"))
            phone = st.text_input("Phone", value=prefill("phone"))
        with col2:
            location = st.text_input("Current Location", value=prefill("location"))
            min_salary = st.number_input(
                "Minimum Salary (USD/year)",
                min_value=0,
                value=int(existing.min_salary or 0) if existing else 0,
                step=5000,
            )

        st.markdown("---")

        # Step 3: Job Preferences
        st.subheader("Step 3: What roles are you looking for?")
        if suggested_roles and not saved_roles:
            st.info(f"Suggested based on your CV: **{', '.join(suggested_roles)}** — edit below as needed.")
        roles_text = st.text_area(
            "Enter roles (one per line)",
            value="\n".join(default_roles),
            placeholder="Software Engineer\nBackend Developer\nFull Stack Developer",
            help="The agent will search for these roles across job boards."
        )

        st.markdown("---")

        # Step 4: Location Preferences
        st.subheader("Step 4: Location & Remote Preference")
        locations_text = st.text_area(
            "Preferred locations (one per line, leave empty for any)",
            value="\n".join(existing.preferred_locations or []) if existing else "",
            placeholder="San Francisco, CA\nNew York, NY\nRemote",
        )
        remote_pref = st.selectbox(
            "Remote preference",
            ["any", "remote", "hybrid", "onsite"],
            index=["any", "remote", "hybrid", "onsite"].index(
                existing.remote_preference if existing else "any"
            ),
        )

        st.markdown("---")

        # Step 5: Projects
        st.subheader("Step 5: Tell us about your key projects")
        projects = st.text_area(
            "Describe 2-3 of your most impactful projects",
            value=existing.projects_summary if existing else "",
            placeholder="Built a real-time data pipeline processing 1M events/day...\nLed a team of 5 to redesign the checkout flow, improving conversion by 15%...",
            height=150,
        )

        st.markdown("---")
        submitted = st.form_submit_button("Save Profile", type="primary", use_container_width=True)

    if submitted:
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
            )

        st.success("Profile saved! Head to Job Search to find matching positions.")
        st.page_link("pages/3_Job_Search.py", label="Go to Job Search")

finally:
    db.close()
