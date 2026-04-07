import streamlit as st
from database import init_db

st.set_page_config(
    page_title="Job Search Agent",
    page_icon="briefcase",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize database on first run
init_db()

st.title("Job Search Agent Dashboard")
st.markdown("---")

st.markdown("""
### Welcome to your Job Search Agent

Navigate using the sidebar to:

1. **Dashboard** - Overview of your job search progress and token usage
2. **Onboarding** - Set up your profile, upload CV, and define preferences
3. **Job Search** - Search for jobs across multiple sources
4. **My Jobs** - Track saved, applied, and in-progress applications
5. **CV Manager** - Score your CV against jobs and get AI-powered rewrites

#### Getting Started
1. Go to **Onboarding** to set up your profile and upload your CV
2. Then go to **Job Search** to find matching positions
3. Use **CV Manager** to optimize your CV for specific roles

#### Token Cost Optimization
This agent minimizes LLM costs by:
- Using rule-based approaches where possible (CV parsing, deduplication, filtering)
- Routing to cheap models (Haiku/GPT-4o-mini) for scoring and summarization
- Only using expensive models for CV rewriting (on-demand)
- Caching all LLM responses to avoid repeat calls
- Batching job scoring (5 at a time) to reduce per-job token overhead
""")
