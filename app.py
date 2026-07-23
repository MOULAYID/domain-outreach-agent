import os
import sys
import pandas as pd
import streamlit as st
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from config import Config
from database import DatabaseManager
from lead_finder import LeadFinder
from email_generator import EmailGenerator
from smtp_sender import SmtpSender
from imap_listener import ImapListener
from email_verifier import EmailVerifier
from main import parse_domains_from_file, parse_leads_from_file

# Page Configuration & Custom CSS
st.set_page_config(
    page_title="Domain Outreach Agent",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #4F46E5;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #6B7280;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #1F2937;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #4F46E5;
        color: #F3F4F6;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Database
db = DatabaseManager()

# Sidebar Setup
st.sidebar.title("🌐 Outreach Agent")
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ System Status")
st.sidebar.info(f"**SMTP Host**: {Config.SMTP_HOST}\n\n**SMTP User**: {Config.SMTP_USER or 'Not Set'}")

if st.sidebar.button("📥 Sync Hostinger Inbox"):
    with st.spinner("Connecting to Hostinger IMAP inbox..."):
        listener = ImapListener(db)
        summary = listener.sync_inbox()
        st.sidebar.success(f"Sync complete! Replies: {summary['replied']}, Unsubscribes: {summary['unsubscribed']}")

st.sidebar.markdown("---")
st.sidebar.caption("Domain Sales Outreach Pipeline v2.0")

# Main Title Header
st.markdown('<div class="main-header">🌐 Domain Sales Cold Outreach Platform</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Automated Domain Portfolio Sales, B2B Prospecting, & Hostinger SMTP Dispatch</div>', unsafe_allow_html=True)

# Metric Summary Row
domains = db.get_all_domains()
leads = db.get_all_leads()
sent_today = db.get_sent_count_today()

status_counts = {"DISCOVERED": 0, "DRAFTED": 0, "SENT": 0, "FAILED": 0, "REPLIED": 0, "UNSUBSCRIBED": 0}
for lead in leads:
    st_val = lead["status"]
    status_counts[st_val] = status_counts.get(st_val, 0) + 1

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Domains Managed", len(domains))
col2.metric("Total Leads", len(leads))
col3.metric("Pending Drafts", status_counts["DRAFTED"])
col4.metric("Sent Today", f"{sent_today} / {Config.MAX_DAILY_EMAILS}")
col5.metric("Prospect Replies", status_counts["REPLIED"])

st.markdown("---")

# Main Interface Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Portfolio & Import", 
    "🔍 Lead Discovery & CSV", 
    "✉️ Draft Pitch Editor", 
    "🚀 Campaign Dispatch"
])

# ---------------------------------------------------------
# TAB 1: Portfolio & Import
# ---------------------------------------------------------
with tab1:
    st.subheader("📁 Import Domain Assets")
    uploaded_domain_file = st.file_uploader(
        "Upload Domain Inventory File (.csv or .txt)", 
        type=["csv", "txt"],
        key="domain_uploader"
    )

    if uploaded_domain_file:
        temp_path = PROJECT_ROOT / f"temp_{uploaded_domain_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_domain_file.getbuffer())

        parsed_doms = parse_domains_from_file(temp_path)
        if parsed_doms:
            st.success(f"Parsed {len(parsed_doms)} domain assets from {uploaded_domain_file.name}.")
            if st.button("Add Domains to Inventory", key="btn_add_doms"):
                added, skipped = db.add_domains(parsed_doms)
                st.success(f"Successfully added {added} new domain(s) ({skipped} duplicates skipped).")
                st.rerun()
        if temp_path.exists():
            temp_path.unlink()

    st.markdown("### 📋 Managed Domain Inventory")
    if domains:
        dom_df = pd.DataFrame([dict(d) for d in domains])
        st.dataframe(dom_df[["domain_name", "category", "created_at"]], use_container_width=True)
    else:
        st.info("No domains in database yet. Upload a CSV or TXT file above.")

# ---------------------------------------------------------
# TAB 2: Lead Discovery & CSV
# ---------------------------------------------------------
with tab2:
    st.subheader("📥 Import Pre-Qualified Leads CSV (Semi-Manual Mode)")
    uploaded_lead_file = st.file_uploader(
        "Upload Leads CSV (domain, email, name, company, field)", 
        type=["csv"],
        key="lead_uploader"
    )

    if uploaded_lead_file:
        temp_path = PROJECT_ROOT / f"temp_lead_{uploaded_lead_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_lead_file.getbuffer())

        parsed_leads = parse_leads_from_file(temp_path)
        if parsed_leads:
            st.success(f"Parsed {len(parsed_leads)} lead contact(s) from {uploaded_lead_file.name}.")
            st.dataframe(pd.DataFrame(parsed_leads), use_container_width=True)
            if st.button("Import Leads into Pipeline", key="btn_add_leads"):
                added, skipped = db.add_manual_leads(parsed_leads)
                st.success(f"Successfully imported {added} lead(s) ({skipped} skipped).")
                st.rerun()
        if temp_path.exists():
            temp_path.unlink()

    st.markdown("---")
    st.subheader("🔍 Automated Lead Scraper")
    if st.button("Run Lead Discovery Across Inventory", key="btn_run_discover"):
        with st.spinner("Searching for leads across domain portfolio..."):
            finder = LeadFinder(db)
            total_found = 0
            for dom_row in domains:
                total_found += finder.discover_leads_for_domain(dom_row["domain_name"])
            st.success(f"Lead discovery complete! Discovered {total_found} new lead(s).")
            st.rerun()

# ---------------------------------------------------------
# TAB 3: Draft Pitch Editor
# ---------------------------------------------------------
with tab3:
    st.subheader("✉️ Pitch Draft Generator & Editor")
    
    col_gen1, col_gen2 = st.columns([1, 4])
    with col_gen1:
        if st.button("Draft Pending Pitches", key="btn_draft_pitches"):
            generator = EmailGenerator(db)
            count = generator.generate_drafts_for_pending_leads()
            st.success(f"Generated {count} pitch draft(s).")
            st.rerun()

    drafted_leads = db.get_leads_by_status("DRAFTED")
    if drafted_leads:
        st.info(f"Showing {len(drafted_leads)} draft(s) ready for review:")
        
        selected_lead_email = st.selectbox(
            "Select Lead Draft to Preview / Edit:",
            [l["lead_email"] for l in drafted_leads]
        )

        selected_lead = next(l for l in drafted_leads if l["lead_email"] == selected_lead_email)

        st.markdown(f"**Target Domain**: `{selected_lead['target_domain']}` | **Company**: `{selected_lead['company_name'] or 'N/A'}`")
        
        edit_subj = st.text_input("Email Subject", value=selected_lead["email_subject"] or "")
        edit_body = st.text_area("Email Body", value=selected_lead["email_body"] or "", height=250)

        if st.button("Save Draft Changes"):
            db.update_lead_draft(selected_lead["id"], edit_subj, edit_body)
            st.success("Draft updated successfully!")
            st.rerun()
    else:
        st.info("No pending DRAFTED leads available. Import or discover leads first, then click 'Draft Pending Pitches'.")

# ---------------------------------------------------------
# TAB 4: Campaign Dispatch
# ---------------------------------------------------------
with tab4:
    st.subheader("🚀 Campaign Dispatch Center")
    
    mode_is_live = st.checkbox("🔥 Enable LIVE Hostinger SMTP Dispatch Mode", value=False)
    
    if mode_is_live:
        st.warning("⚠️ LIVE MODE ACTIVE: Real outreach emails will be sent via smtp.hostinger.com!")
    else:
        st.info("🧪 DRY-RUN SIMULATION MODE: Email payloads will be validated without sending real emails.")

    if st.button("🚀 Start Campaign Dispatch", key="btn_start_campaign"):
        sender = SmtpSender(db)
        with st.spinner("Dispatching campaign..."):
            dispatched = sender.execute_campaign(dry_run=not mode_is_live)
            st.success(f"Campaign execution complete! Processed: {dispatched} lead(s).")
            st.rerun()

    st.markdown("### 📊 All Lead Records")
    if leads:
        lead_df = pd.DataFrame([dict(l) for l in leads])
        display_cols = [c for c in ["target_domain", "lead_email", "lead_name", "company_name", "status", "created_at"] if c in lead_df.columns]
        st.dataframe(lead_df[display_cols], use_container_width=True)
