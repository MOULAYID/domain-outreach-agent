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
st.sidebar.caption("Domain Sales Outreach Pipeline v2.3")

# Main Title Header
st.markdown('<div class="main-header">🌐 Domain Sales Cold Outreach Platform</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Unified Draft & Dispatch Studio, Controlled Scrapers, Bulk Portfolio Manager & Hostinger SMTP</div>', unsafe_allow_html=True)

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
tab1, tab2, tab3 = st.tabs([
    "📊 Portfolio & Bulk Edit", 
    "🔍 Controlled Lead Scraper", 
    "✉️ Campaign Studio (Draft & Dispatch)"
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
# TAB 3: Unified Campaign Studio (Draft & Dispatch)
# ---------------------------------------------------------
with tab3:
    st.subheader("✉️ Outreach Campaign Studio (Draft & Dispatch)")

    # Status Filter & Sending Mode Controls Header
    col_hdr1, col_hdr2 = st.columns([2, 2])
    with col_hdr1:
        status_filter = st.selectbox(
            "🔍 Filter Leads by Status:",
            ["ALL", "DRAFTED", "DISCOVERED", "SENT", "REPLIED", "UNSUBSCRIBED", "FAILED"],
            key="studio_status_filter"
        )
    with col_hdr2:
        mode_is_live = st.checkbox("🔥 Enable LIVE Hostinger SMTP Mode", value=False, key="studio_chk_live")
        if mode_is_live:
            st.warning("⚠️ LIVE MODE: Emails will be sent live via smtp.hostinger.com!")
        else:
            st.info("🧪 DRY-RUN MODE: Payloads will be validated without sending real emails.")

    if status_filter == "ALL":
        studio_leads = leads
    else:
        studio_leads = [l for l in leads if l["status"] == status_filter]

    st.markdown(f"**Showing {len(studio_leads)} record(s)** for filter `{status_filter}`")

    if studio_leads:
        lead_df = pd.DataFrame([dict(l) for l in studio_leads])
        display_cols = [c for c in ["id", "target_domain", "lead_email", "lead_name", "company_name", "status", "email_subject"] if c in lead_df.columns]
        
        lead_df["Select"] = False
        edited_df = st.data_editor(
            lead_df[["Select"] + display_cols],
            column_config={
                "Select": st.column_config.CheckboxColumn(required=True),
                "id": st.column_config.NumberColumn(disabled=True),
                "target_domain": st.column_config.TextColumn("Target Domain", disabled=True),
                "lead_email": st.column_config.TextColumn("Lead Email", disabled=True),
                "lead_name": st.column_config.TextColumn("Lead Name", disabled=True),
                "company_name": st.column_config.TextColumn("Company", disabled=True),
                "status": st.column_config.TextColumn("Status", disabled=True),
                "email_subject": st.column_config.TextColumn("Subject Line")
            },
            hide_index=True,
            use_container_width=True,
            key="studio_data_editor"
        )

        selected_rows = edited_df[edited_df["Select"] == True]
        selected_ids = selected_rows["id"].tolist() if not selected_rows.empty else []

        # Bulk Actions Row
        col_act1, col_act2, col_act3 = st.columns(3)
        
        with col_act1:
            if st.button("✍️ Write / Re-Write Drafts for Selected", key="btn_studio_draft_selected", use_container_width=True):
                if not selected_ids:
                    st.warning("Please check the 'Select' box for at least 1 lead.")
                else:
                    generator = EmailGenerator(db)
                    written_count = 0
                    for l_id in selected_ids:
                        lead_rec = next(l for l in leads if l["id"] == l_id)
                        subj, body = generator.generate_pitch(
                            lead_rec["target_domain"],
                            lead_rec["company_name"] or "",
                            lead_rec["lead_name"] or "",
                            lead_rec["domain_category"] if "domain_category" in lead_rec.keys() else ""
                        )
                        db.update_lead_draft(l_id, subj, body)
                        written_count += 1
                    st.success(f"Generated DomainEpoch pitch drafts for {written_count} selected lead(s)!")
                    st.rerun()

        with col_act2:
            if st.button("🚀 Send Selected Emails (Auto-Drafts & Re-Sends)", key="btn_studio_send_selected", use_container_width=True):
                if not selected_ids:
                    st.warning("Please check the 'Select' box for at least 1 lead to send.")
                else:
                    generator = EmailGenerator(db)
                    sender = SmtpSender(db)
                    dry_run = not mode_is_live
                    
                    sent_count = 0
                    auto_drafted_count = 0
                    resent_count = 0

                    with st.spinner("Processing & dispatching selected emails..."):
                        for l_id in selected_ids:
                            lead_rec = db.get_connection().cursor().execute("SELECT l.*, d.category as domain_category FROM leads l LEFT JOIN domains d ON l.target_domain = d.domain_name WHERE l.id = ?", (l_id,)).fetchone()
                            if not lead_rec:
                                continue

                            # Safeguard Condition 1: Auto-Draft pitch if email subject/body missing
                            subj = lead_rec["email_subject"]
                            body = lead_rec["email_body"]

                            if not subj or not body or lead_rec["status"] == "DISCOVERED":
                                subj, body = generator.generate_pitch(
                                    lead_rec["target_domain"],
                                    lead_rec["company_name"] or "",
                                    lead_rec["lead_name"] or "",
                                    lead_rec["domain_category"] if "domain_category" in lead_rec.keys() else ""
                                )
                                db.update_lead_draft(l_id, subj, body)
                                auto_drafted_count += 1

                            # Safeguard Condition 2: Track if this is a Re-Send of a previously SENT email
                            if lead_rec["status"] in ["SENT", "INITIAL_SENT", "FOLLOWUP_SENT"]:
                                resent_count += 1

                            # Dispatch email payload over Hostinger SMTP
                            if sender.send_email(lead_rec["lead_email"], subj, body, dry_run=dry_run):
                                db.mark_lead_sent(l_id)
                                sent_count += 1

                    mode_str = "[LIVE Hostinger SMTP]" if mode_is_live else "[DRY-RUN Simulation]"
                    st.success(f"Campaign execution complete {mode_str}! Processed: {sent_count} email(s) ({auto_drafted_count} auto-drafted, {resent_count} re-sent).")
                    st.rerun()

        with col_act3:
            if st.button("🗑️ Delete Selected Leads", key="btn_studio_delete_selected", use_container_width=True):
                if not selected_ids:
                    st.warning("Please check the 'Select' box for at least 1 lead to delete.")
                else:
                    deleted = db.delete_leads_by_ids(selected_ids)
                    st.success(f"Deleted {deleted} lead contact(s) from database.")
                    st.rerun()

    # Individual Single Lead Draft Inspector & Manual Editor
    st.markdown("---")
    st.subheader("✏️ Single Lead Inspector & Manual Copy Editor")
    if leads:
        lead_options = {f"{l['lead_email']} ({l['target_domain']}) - [{l['status']}]": l for l in leads}
        selected_option = st.selectbox("Select Lead to Inspect / Edit Copy:", list(lead_options.keys()))
        
        target_lead = lead_options[selected_option]
        st.markdown(f"**Target Domain**: `{target_lead['target_domain']}` | **Lead Email**: `{target_lead['lead_email']}` | **Status**: `{target_lead['status']}`")

        edit_subj = st.text_input("Email Subject Line", value=target_lead["email_subject"] or f"{target_lead['target_domain']}")
        edit_body = st.text_area("Email Body Copy", value=target_lead["email_body"] or "", height=230)

        col_ed1, col_ed2 = st.columns(2)
        with col_ed1:
            if st.button("💾 Save Manual Copy Changes", key="btn_save_manual_copy"):
                db.update_lead_draft(target_lead["id"], edit_subj, edit_body)
                st.success("Pitch copy updated and saved to database!")
                st.rerun()
        with col_ed2:
            if st.button("🚀 Send THIS Single Email Now", key="btn_send_single_lead"):
                sender = SmtpSender(db)
                dry_run = not mode_is_live
                if sender.send_email(target_lead["lead_email"], edit_subj, edit_body, dry_run=dry_run):
                    db.mark_lead_sent(target_lead["id"])
                    mode_str = "[LIVE]" if mode_is_live else "[DRY-RUN]"
                    st.success(f"Email dispatched {mode_str} to {target_lead['lead_email']}!")
                    st.rerun()
