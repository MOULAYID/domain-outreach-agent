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
    .stButton>button {
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Database
db = DatabaseManager()

# Initialize Session State
if "scraping_active" not in st.session_state:
    st.session_state["scraping_active"] = False
if "stop_requested" not in st.session_state:
    st.session_state["stop_requested"] = False

# Sidebar Setup
st.sidebar.title("🌐 Outreach Agent")
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ System Configuration")
st.sidebar.info(f"**SMTP Host**: {Config.SMTP_HOST}\n\n**SMTP User**: {Config.SMTP_USER or 'Not Set'}\n\n**Hunter Key**: {'Configured' if Config.HUNTER_API_KEY else 'Not Set'}")

if st.sidebar.button("📥 Sync Hostinger Inbox"):
    with st.spinner("Connecting to Hostinger IMAP inbox..."):
        listener = ImapListener(db)
        summary = listener.sync_inbox()
        st.sidebar.success(f"Sync complete! Replies: {summary['replied']}, Unsubscribes: {summary['unsubscribed']}")

st.sidebar.markdown("---")
st.sidebar.caption("Domain Sales Outreach Pipeline v2.2")

# Main Title Header
st.markdown('<div class="main-header">🌐 Domain Sales Cold Outreach Platform</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Bulk Domain Inventory Management, Automated Scrapers, Pitch Editor & Hostinger SMTP Dispatch</div>', unsafe_allow_html=True)

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
    "📊 Portfolio & Bulk Edit", 
    "🔍 Controlled Lead Scraper", 
    "✉️ Draft Editor & Writer", 
    "🚀 Bulk Campaign Dispatcher"
])

# ---------------------------------------------------------
# TAB 1: Portfolio & Bulk Edit / Delete
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

    st.markdown("---")
    st.subheader("📋 Managed Domain Inventory (Bulk Edit & Delete)")
    if domains:
        dom_df = pd.DataFrame([dict(d) for d in domains])
        dom_df["Select"] = False

        display_cols = ["Select", "id", "domain_name", "category", "created_at"]
        
        edited_dom_df = st.data_editor(
            dom_df[display_cols],
            column_config={
                "Select": st.column_config.CheckboxColumn(required=True),
                "id": st.column_config.NumberColumn(disabled=True),
                "domain_name": st.column_config.TextColumn("Domain Name", required=True),
                "category": st.column_config.TextColumn("Niche / Category"),
                "created_at": st.column_config.TextColumn("Import Date", disabled=True)
            },
            hide_index=True,
            use_container_width=True,
            key="dom_data_editor"
        )

        selected_dom_rows = edited_dom_df[edited_dom_df["Select"] == True]
        selected_dom_ids = selected_dom_rows["id"].tolist() if not selected_dom_rows.empty else []

        col_dom_act1, col_dom_act2 = st.columns(2)
        with col_dom_act1:
            if st.button("💾 Save Table Edits to Database", key="btn_save_dom_edits", use_container_width=True):
                updated_count = 0
                for idx, row in edited_dom_df.iterrows():
                    db.update_domain(int(row["id"]), str(row["domain_name"]), str(row["category"] or ""))
                    updated_count += 1
                st.success(f"Saved edits for {updated_count} domain record(s)!")
                st.rerun()

        with col_dom_act2:
            if st.button("🗑️ Delete Selected Domains", key="btn_delete_doms", use_container_width=True):
                if not selected_dom_ids:
                    st.warning("Please check the 'Select' box for at least 1 domain to delete.")
                else:
                    deleted = db.delete_domains_by_ids(selected_dom_ids)
                    st.success(f"Deleted {deleted} domain asset(s) and their associated leads.")
                    st.rerun()
    else:
        st.info("No domains in database yet. Upload a CSV or TXT file above.")

# ---------------------------------------------------------
# TAB 2: Controlled Lead Scraper & Importer
# ---------------------------------------------------------
with tab2:
    st.subheader("🔍 Automated Lead Scraper with Run/Stop Controls")
    
    col_sc1, col_sc2 = st.columns(2)
    with col_sc1:
        start_btn = st.button("▶️ Start Lead Scraper", key="btn_start_scraper", use_container_width=True)
    with col_sc2:
        stop_btn = st.button("⏹️ Stop Scraper & Flush to DB", key="btn_stop_scraper", use_container_width=True)

    if stop_btn:
        st.session_state["stop_requested"] = True
        st.warning("🛑 Stop signal sent! Stopping scraper gracefully...")

    if start_btn:
        st.session_state["stop_requested"] = False
        st.session_state["scraping_active"] = True
        
        finder = LeadFinder(db)
        total_found = 0
        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, dom_row in enumerate(domains):
            if st.session_state.get("stop_requested", False):
                status_text.warning(f"🛑 Scraper stopped by user! Processed {idx}/{len(domains)} domains. Database updated.")
                break
            
            target_dom = dom_row["domain_name"]
            status_text.text(f"🔍 Scraped {idx+1}/{len(domains)}: {target_dom} (Found {total_found} leads so far...)")
            total_found += finder.discover_leads_for_domain(target_dom)
            progress_bar.progress((idx + 1) / len(domains))

        st.session_state["scraping_active"] = False
        st.success(f"Scrape completed/flushed! Total new leads saved in DB: {total_found}")
        st.rerun()

    st.markdown("---")
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

# ---------------------------------------------------------
# TAB 3: Draft Editor & Writer
# ---------------------------------------------------------
with tab3:
    st.subheader("✍️ Lead Filter & Pitch Draft Generator")

    # Status Filter
    status_filter = st.selectbox(
        "🔍 Filter Leads by Status:",
        ["ALL", "DISCOVERED", "DRAFTED", "SENT", "REPLIED", "UNSUBSCRIBED", "FAILED"],
        key="draft_status_filter"
    )

    if status_filter == "ALL":
        filtered_leads = leads
    else:
        filtered_leads = [l for l in leads if l["status"] == status_filter]

    st.markdown(f"**Showing {len(filtered_leads)} record(s)** for status filter: `{status_filter}`")

    # Bulk Select to Generate Drafts or Delete Leads
    if filtered_leads:
        lead_df = pd.DataFrame([dict(l) for l in filtered_leads])
        display_cols = [c for c in ["id", "target_domain", "lead_email", "lead_name", "company_name", "status"] if c in lead_df.columns]
        
        st.markdown("#### 🎯 Select Leads for Bulk Actions")
        
        lead_df["Selected"] = False
        edited_df = st.data_editor(
            lead_df[["Selected"] + display_cols],
            column_config={"Selected": st.column_config.CheckboxColumn(required=True)},
            disabled=display_cols,
            hide_index=True,
            use_container_width=True,
            key="lead_data_editor"
        )

        selected_rows = edited_df[edited_df["Selected"] == True]
        selected_ids = selected_rows["id"].tolist() if not selected_rows.empty else []

        col_b1, col_b2, col_b3 = st.columns(3)
        with col_b1:
            if st.button("✍️ Write Drafts for Selected Leads", key="btn_write_selected", use_container_width=True):
                if not selected_ids:
                    st.warning("Please select at least 1 lead using the checkboxes above.")
                else:
                    generator = EmailGenerator(db)
                    written_count = 0
                    for l_id in selected_ids:
                        lead_record = next(l for l in leads if l["id"] == l_id)
                        subj, body = generator.generate_pitch(
                            lead_record["target_domain"], 
                            lead_record["company_name"] or "", 
                            lead_record["lead_name"] or "",
                            lead_record["domain_category"] if "domain_category" in lead_record.keys() else ""
                        )
                        db.update_lead_draft(l_id, subj, body)
                        written_count += 1
                    st.success(f"Generated DomainEpoch pitch drafts for {written_count} selected lead(s)!")
                    st.rerun()

        with col_b2:
            if st.button("✍️ Write Drafts for ALL Pending DISCOVERED Leads", key="btn_write_all", use_container_width=True):
                generator = EmailGenerator(db)
                count = generator.generate_drafts_for_pending_leads()
                st.success(f"Generated {count} pitch draft(s).")
                st.rerun()

        with col_b3:
            if st.button("🗑️ Delete Selected Leads", key="btn_delete_leads", use_container_width=True):
                if not selected_ids:
                    st.warning("Please select at least 1 lead using the checkboxes above.")
                else:
                    deleted_leads = db.delete_leads_by_ids(selected_ids)
                    st.success(f"Deleted {deleted_leads} lead record(s) from database.")
                    st.rerun()

    # Individual Draft Editor Component
    st.markdown("---")
    st.subheader("✏️ Single Draft Inspector & Editor")
    drafted_leads = db.get_leads_by_status("DRAFTED")
    if drafted_leads:
        selected_lead_email = st.selectbox(
            "Select Drafted Lead to Edit:",
            [l["lead_email"] for l in drafted_leads]
        )

        selected_lead = next(l for l in drafted_leads if l["lead_email"] == selected_lead_email)
        st.markdown(f"**Target Domain**: `{selected_lead['target_domain']}` | **Email**: `{selected_lead['lead_email']}`")
        
        edit_subj = st.text_input("Email Subject", value=selected_lead["email_subject"] or "")
        edit_body = st.text_area("Email Body", value=selected_lead["email_body"] or "", height=230)

        if st.button("Save Draft Modifications"):
            db.update_lead_draft(selected_lead["id"], edit_subj, edit_body)
            st.success("Draft saved successfully!")
            st.rerun()

# ---------------------------------------------------------
# TAB 4: Bulk Campaign Dispatcher
# ---------------------------------------------------------
with tab4:
    st.subheader("🚀 Bulk Campaign Dispatcher")

    disp_filter = st.selectbox(
        "Filter Campaign Leads by Status:",
        ["DRAFTED", "ALL", "DISCOVERED", "SENT", "REPLIED", "UNSUBSCRIBED", "FAILED"],
        key="disp_status_filter"
    )

    if disp_filter == "ALL":
        dispatch_leads = leads
    else:
        dispatch_leads = [l for l in leads if l["status"] == disp_filter]

    st.markdown(f"**Showing {len(dispatch_leads)} lead(s)** ready for campaign selection.")

    mode_is_live = st.checkbox("🔥 Enable LIVE Hostinger SMTP Dispatch Mode", value=False, key="chk_live_mode")
    
    if mode_is_live:
        st.warning("⚠️ LIVE MODE ACTIVE: Real emails will be dispatched over Hostinger SMTP (smtp.hostinger.com:465)!")
    else:
        st.info("🧪 DRY-RUN SIMULATION MODE: Payloads will be validated without sending real emails.")

    if dispatch_leads:
        disp_df = pd.DataFrame([dict(l) for l in dispatch_leads])
        disp_cols = [c for c in ["id", "target_domain", "lead_email", "company_name", "status", "email_subject"] if c in disp_df.columns]
        
        disp_df["Bulk Select"] = False
        edited_disp_df = st.data_editor(
            disp_df[["Bulk Select"] + disp_cols],
            column_config={"Bulk Select": st.column_config.CheckboxColumn(required=True)},
            disabled=disp_cols,
            hide_index=True,
            use_container_width=True,
            key="disp_data_editor"
        )

        selected_disp_rows = edited_disp_df[edited_disp_df["Bulk Select"] == True]
        selected_disp_ids = selected_disp_rows["id"].tolist() if not selected_disp_rows.empty else []

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            if st.button("🚀 Send Selected Drafted Emails", key="btn_send_selected", use_container_width=True):
                if not selected_disp_ids:
                    st.warning("Please check the 'Bulk Select' box for at least 1 lead.")
                else:
                    sender = SmtpSender(db)
                    dry_run = not mode_is_live
                    sent_count = 0
                    with st.spinner("Dispatching selected campaign emails..."):
                        for l_id in selected_disp_ids:
                            lead_rec = next(l for l in leads if l["id"] == l_id)
                            if lead_rec["status"] != "DRAFTED":
                                continue
                            if sender.send_email(
                                lead_rec["lead_email"],
                                lead_rec["email_subject"],
                                lead_rec["email_body"],
                                dry_run=dry_run
                            ):
                                db.mark_lead_sent(l_id)
                                sent_count += 1
                    st.success(f"Campaign execution complete! Processed {sent_count} selected email(s).")
                    st.rerun()

        with col_d2:
            if st.button("🚀 Send ALL DRAFTED Campaign Emails", key="btn_send_all_drafts", use_container_width=True):
                sender = SmtpSender(db)
                with st.spinner("Dispatching all pending drafted campaign emails..."):
                    dispatched = sender.execute_campaign(dry_run=not mode_is_live)
                    st.success(f"Dispatched {dispatched} pending campaign email(s).")
                    st.rerun()
