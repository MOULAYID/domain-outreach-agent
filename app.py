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

# Streamlit Page Setup
st.set_page_config(
    page_title="DomainEpoch Outreach Command Center",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Design Engine (Sleek Dark Mode, Indigo Accents, Responsive Layouts)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background-color: #0F172A;
        color: #F8FAFC;
    }
    
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #818CF8;
        letter-spacing: -0.02em;
        margin-bottom: 0.2rem;
    }
    
    .sub-title {
        font-size: 0.95rem;
        color: #94A3B8;
        margin-bottom: 1.5rem;
    }
    
    .metric-card {
        background-color: #1E293B;
        padding: 1.2rem;
        border-radius: 0.75rem;
        border: 1px solid #334155;
        border-left: 4px solid #6366F1;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    .metric-card h4 {
        margin: 0;
        font-size: 0.85rem;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .metric-card p {
        margin: 0.4rem 0 0 0;
        font-size: 1.8rem;
        font-weight: 700;
        color: #F8FAFC;
    }
    
    .stButton > button {
        background-color: #4F46E5;
        color: white;
        font-weight: 600;
        border-radius: 0.5rem;
        border: none;
        padding: 0.5rem 1rem;
        transition: all 0.2s ease-in-out;
    }
    
    .stButton > button:hover {
        background-color: #4338CA;
        border: none;
        transform: translateY(-1px);
    }
    
    .stTextInput > div > div > input, .stTextArea > div > div > textarea, .stSelectbox > div > div > div {
        background-color: #1E293B !important;
        color: #F8FAFC !important;
        border: 1px solid #334155 !important;
        border-radius: 0.5rem !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Database
db = DatabaseManager()

# Session State Initialization
if "scraping_active" not in st.session_state:
    st.session_state["scraping_active"] = False
if "stop_requested" not in st.session_state:
    st.session_state["stop_requested"] = False

# Sidebar Navigation & Global Controls
st.sidebar.markdown("## 🌐 Command Center")
st.sidebar.markdown("---")

view_selection = st.sidebar.radio(
    "Navigation Menu",
    [
        "📊 Analytics & Dashboard",
        "📁 Domain Portfolio Manager",
        "🔍 Controlled Scraper & Importer",
        "✉️ Campaign Studio (Draft & Dispatch)",
        "📥 Hostinger IMAP Monitor",
        "⚙️ System Settings & Diagnostics"
    ],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🛡️ Global Safeguards")

mode_is_live = st.sidebar.checkbox("🔥 Enable LIVE Hostinger SMTP", value=False, help="Uncheck for safe Dry-Run simulation mode")
enforce_test_email = st.sidebar.checkbox("🛡️ Enforce Test Email Guard", value=True, help="When checked, live dispatches are ONLY sent to medido25@gmail.com")

if mode_is_live:
    st.sidebar.warning("⚠️ LIVE DISPATCH MODE: Real emails will be sent via smtp.hostinger.com!")
else:
    st.sidebar.info("🧪 DRY-RUN SIMULATION: No real emails will leave your server.")

if enforce_test_email:
    st.sidebar.caption("🔒 Test Safeguard Active: All test emails locked to `medido25@gmail.com`")

st.sidebar.markdown("---")
domains = db.get_all_domains()
leads = db.get_all_leads()
sent_today = db.get_sent_count_today()
stats = db.get_lead_stats()

st.sidebar.caption(f"Emails Sent Today: **{sent_today} / {Config.MAX_DAILY_EMAILS}**")
st.sidebar.progress(min(sent_today / Config.MAX_DAILY_EMAILS, 1.0))

# Header Component
st.markdown('<div class="main-title">🌐 DomainEpoch Sales Outreach Command Center</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Automated B2B Lead Scraping, Multi-Touch Pitch Generator & Hostinger SMTP Campaign Dispatcher</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# VIEW 1: 📊 Analytics & Dashboard
# ---------------------------------------------------------
if view_selection == "📊 Analytics & Dashboard":
    st.subheader("📊 Executive Analytics & Campaign Performance")
    
    col_m1, col_m2, col_m3, col_m4, col_m5, col_m6 = st.columns(6)
    
    with col_m1:
        st.markdown(f'<div class="metric-card"><h4>Domains</h4><p>{len(domains)}</p></div>', unsafe_allow_html=True)
    with col_m2:
        st.markdown(f'<div class="metric-card"><h4>Total Leads</h4><p>{len(leads)}</p></div>', unsafe_allow_html=True)
    with col_m3:
        st.markdown(f'<div class="metric-card"><h4>Pending Drafts</h4><p>{stats["DRAFTED"]}</p></div>', unsafe_allow_html=True)
    with col_m4:
        st.markdown(f'<div class="metric-card"><h4>Sent Today</h4><p>{sent_today}</p></div>', unsafe_allow_html=True)
    with col_m5:
        st.markdown(f'<div class="metric-card"><h4>Replies</h4><p>{stats["REPLIED"]}</p></div>', unsafe_allow_html=True)
    with col_m6:
        st.markdown(f'<div class="metric-card"><h4>Opted Out</h4><p>{stats["UNSUBSCRIBED"]}</p></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📈 Lead Status Pipeline Breakdown")
    
    status_df = pd.DataFrame([
        {"Status": k, "Count": v} for k, v in stats.items()
    ])
    
    st.bar_chart(status_df.set_index("Status"), height=250)

    st.markdown("### 🕒 Recent Lead Activity Feed")
    if leads:
        lead_df = pd.DataFrame([dict(l) for l in leads[:15]])
        disp_cols = [c for c in ["target_domain", "lead_email", "company_name", "status", "created_at"] if c in lead_df.columns]
        st.dataframe(lead_df[disp_cols], use_container_width=True)

# ---------------------------------------------------------
# VIEW 2: 📁 Domain Portfolio Manager
# ---------------------------------------------------------
elif view_selection == "📁 Domain Portfolio Manager":
    st.subheader("📁 Domain Portfolio Manager & CSV Importer")

    col_dom1, col_dom2 = st.columns([2, 1])
    
    with col_dom1:
        st.markdown("#### 📤 Bulk Upload Domains File")
        uploaded_dom_file = st.file_uploader("Upload CSV or TXT file of domain names:", type=["csv", "txt"], key="dom_file_up")
        if uploaded_dom_file:
            temp_path = PROJECT_ROOT / f"temp_{uploaded_dom_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_dom_file.getbuffer())
            parsed_doms = parse_domains_from_file(temp_path)
            if parsed_doms:
                st.success(f"Parsed {len(parsed_doms)} domains from {uploaded_dom_file.name}")
                if st.button("Import Parsed Domains", key="btn_import_parsed_doms"):
                    added, skipped = db.add_domains(parsed_doms)
                    st.success(f"Added {added} new domain(s) ({skipped} skipped).")
                    st.rerun()
            if temp_path.exists():
                temp_path.unlink()

    with col_dom2:
        st.markdown("#### ➕ Add Single Domain Asset")
        new_dom_name = st.text_input("Domain Name (e.g. cloudai.com)")
        new_dom_cat = st.text_input("Categories (e.g. AI, SaaS)")
        if st.button("Add Single Domain"):
            if new_dom_name:
                if db.add_single_domain(new_dom_name, new_dom_cat):
                    st.success(f"Added {new_dom_name} to database!")
                    st.rerun()
                else:
                    st.error("Domain already exists in database.")

    st.markdown("---")
    st.subheader("📋 Managed Domain Inventory (Inline Edit & Bulk Delete)")
    
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
                "category": st.column_config.TextColumn("Niche / Categories"),
                "created_at": st.column_config.TextColumn("Import Date", disabled=True)
            },
            hide_index=True,
            use_container_width=True,
            key="dom_editor_table"
        )

        selected_dom_rows = edited_dom_df[edited_dom_df["Select"] == True]
        selected_dom_ids = selected_dom_rows["id"].tolist() if not selected_dom_rows.empty else []

        col_act1, col_act2 = st.columns(2)
        with col_act1:
            if st.button("💾 Save Table Edits", key="btn_save_dom_changes", use_container_width=True):
                updated = 0
                for idx, row in edited_dom_df.iterrows():
                    db.update_domain(int(row["id"]), str(row["domain_name"]), str(row["category"] or ""))
                    updated += 1
                st.success(f"Saved modifications for {updated} domain(s)!")
                st.rerun()

        with col_act2:
            if st.button("🗑️ Delete Selected Domains", key="btn_del_doms", use_container_width=True):
                if not selected_dom_ids:
                    st.warning("Please check the 'Select' box for at least 1 domain.")
                else:
                    deleted = db.delete_domains_by_ids(selected_dom_ids)
                    st.success(f"Deleted {deleted} domain asset(s) and their associated leads.")
                    st.rerun()
    else:
        st.info("No domains in database yet. Import domains above.")

# ---------------------------------------------------------
# VIEW 3: 🔍 Controlled Scraper & Importer
# ---------------------------------------------------------
elif view_selection == "🔍 Controlled Scraper & Importer":
    st.subheader("🔍 Automated Lead Scraper with Real-Time Run/Stop Controls")
    
    col_sc1, col_sc2 = st.columns(2)
    with col_sc1:
        start_btn = st.button("▶️ Start Lead Scraper", key="btn_start_scr", use_container_width=True)
    with col_sc2:
        stop_btn = st.button("⏹️ Stop Scraper & Flush DB", key="btn_stop_scr", use_container_width=True)

    if stop_btn:
        st.session_state["stop_requested"] = True
        st.warning("🛑 Stop signal requested! Halting scraper...")

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
        st.success(f"Scrape completed/flushed! Total new leads saved: {total_found}")
        st.rerun()

    st.markdown("---")
    st.subheader("📥 Import Pre-Qualified Leads CSV (Semi-Manual Mode)")
    
    col_ld1, col_ld2 = st.columns([2, 1])
    with col_ld1:
        st.markdown("#### 📤 Bulk Upload Leads CSV")
        uploaded_lead_file = st.file_uploader("Upload CSV (domain, email, name, company, field):", type=["csv"], key="lead_file_up")
        if uploaded_lead_file:
            temp_path = PROJECT_ROOT / f"temp_lead_{uploaded_lead_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_lead_file.getbuffer())

            parsed_leads = parse_leads_from_file(temp_path)
            if parsed_leads:
                st.success(f"Parsed {len(parsed_leads)} lead contact(s).")
                st.dataframe(pd.DataFrame(parsed_leads), use_container_width=True)
                if st.button("Import Leads into Database", key="btn_import_parsed_leads"):
                    added, skipped = db.add_manual_leads(parsed_leads)
                    st.success(f"Imported {added} lead(s) ({skipped} duplicates skipped).")
                    st.rerun()
            if temp_path.exists():
                temp_path.unlink()

    with col_ld2:
        st.markdown("#### ➕ Quick Add Single Lead")
        single_dom = st.text_input("Target Domain", value="cloudfinance.io")
        single_email = st.text_input("Lead Email", value="alex.rivera@fintechsolutions.com")
        single_name = st.text_input("Lead Name", value="Alex Rivera")
        single_company = st.text_input("Company", value="Fintech Solutions")
        if st.button("Add Single Lead"):
            if single_dom and single_email:
                if db.add_single_lead(single_dom, single_email, single_name, single_company):
                    st.success(f"Added lead {single_email} to database!")
                    st.rerun()
                else:
                    st.error("Lead email already exists in database.")

# ---------------------------------------------------------
# VIEW 4: ✉️ Campaign Studio (Draft & Dispatch)
# ---------------------------------------------------------
elif view_selection == "✉️ Campaign Studio (Draft & Dispatch)":
    st.subheader("✉️ Outreach Campaign Studio (Bulk Draft, Single Copy Editor & Dispatch)")

    # Status Filter
    status_filter = st.selectbox(
        "🔍 Filter Leads Table by Status:",
        ["ALL", "DRAFTED", "DISCOVERED", "SENT", "REPLIED", "UNSUBSCRIBED", "FAILED"],
        key="studio_filter_select"
    )

    if status_filter == "ALL":
        studio_leads = leads
    else:
        studio_leads = [l for l in leads if l["status"] == status_filter]

    search_query = st.text_input("🔍 Search Leads by Domain, Email, or Company:", "").strip().lower()
    if search_query:
        studio_leads = [l for l in studio_leads if search_query in l["target_domain"].lower() or search_query in l["lead_email"].lower() or (l["company_name"] and search_query in l["company_name"].lower())]

    st.markdown(f"**Showing {len(studio_leads)} lead record(s)**")

    if studio_leads:
        lead_df = pd.DataFrame([dict(l) for l in studio_leads])
        disp_cols = [c for c in ["id", "target_domain", "lead_email", "lead_name", "company_name", "status", "email_subject"] if c in lead_df.columns]
        
        lead_df["Select"] = False
        edited_df = st.data_editor(
            lead_df[["Select"] + disp_cols],
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
            key="studio_data_editor_table"
        )

        selected_rows = edited_df[edited_df["Select"] == True]
        selected_ids = selected_rows["id"].tolist() if not selected_rows.empty else []

        col_st_act1, col_st_act2, col_st_act3 = st.columns(3)
        
        with col_st_act1:
            if st.button("✍️ Write / Re-Write Drafts for Selected", key="btn_studio_write", use_container_width=True):
                if not selected_ids:
                    st.warning("Please check the 'Select' box for at least 1 lead.")
                else:
                    generator = EmailGenerator(db)
                    written = 0
                    for l_id in selected_ids:
                        lead_rec = next(l for l in leads if l["id"] == l_id)
                        subj, body = generator.generate_pitch(
                            lead_rec["target_domain"],
                            lead_rec["company_name"] or "",
                            lead_rec["lead_name"] or "",
                            lead_rec["domain_category"] if "domain_category" in lead_rec.keys() else ""
                        )
                        db.update_lead_draft(l_id, subj, body)
                        written += 1
                    st.success(f"Generated DomainEpoch pitch drafts for {written} lead(s)!")
                    st.rerun()

        with col_st_act2:
            if st.button("🚀 Send Selected Emails (Auto-Drafts & Re-Sends)", key="btn_studio_send", use_container_width=True):
                if not selected_ids:
                    st.warning("Please check the 'Select' box for at least 1 lead to send.")
                else:
                    generator = EmailGenerator(db)
                    sender = SmtpSender(db)
                    dry_run = not mode_is_live
                    
                    sent_count = 0
                    auto_drafted_count = 0
                    resent_count = 0

                    with st.spinner("Dispatching selected campaign emails..."):
                        for l_id in selected_ids:
                            lead_rec = db.get_connection().cursor().execute("SELECT l.*, d.category as domain_category FROM leads l LEFT JOIN domains d ON l.target_domain = d.domain_name WHERE l.id = ?", (l_id,)).fetchone()
                            if not lead_rec:
                                continue

                            subj = lead_rec["email_subject"]
                            body = lead_rec["email_body"]

                            # Auto-Draft condition if pitch missing
                            if not subj or not body or lead_rec["status"] == "DISCOVERED":
                                subj, body = generator.generate_pitch(
                                    lead_rec["target_domain"],
                                    lead_rec["company_name"] or "",
                                    lead_rec["lead_name"] or "",
                                    lead_rec["domain_category"] if "domain_category" in lead_rec.keys() else ""
                                )
                                db.update_lead_draft(l_id, subj, body)
                                auto_drafted_count += 1

                            # Re-send tracking
                            if lead_rec["status"] in ["SENT", "INITIAL_SENT", "FOLLOWUP_SENT"]:
                                resent_count += 1

                            # Test Safeguard Enforcement
                            target_recipient = "medido25@gmail.com" if enforce_test_email else lead_rec["lead_email"]

                            try:
                                if sender.send_email(target_recipient, subj, body, dry_run=dry_run):
                                    db.mark_lead_sent(l_id)
                                    sent_count += 1
                            except Exception as err:
                                db.mark_lead_failed(l_id, str(err))
                                st.error(f"Failed sending to {target_recipient}: {err}")

                    mode_str = "[LIVE Hostinger SMTP]" if mode_is_live else "[DRY-RUN Simulation]"
                    st.success(f"Campaign execution complete {mode_str}! Processed {sent_count} email(s) ({auto_drafted_count} auto-drafted, {resent_count} re-sent).")
                    st.rerun()

        with col_st_act3:
            if st.button("🗑️ Delete Selected Leads", key="btn_studio_del", use_container_width=True):
                if not selected_ids:
                    st.warning("Please check the 'Select' box for at least 1 lead to delete.")
                else:
                    deleted = db.delete_leads_by_ids(selected_ids)
                    st.success(f"Deleted {deleted} lead contact(s) from database.")
                    st.rerun()

    # Single Lead Copy Inspector & Manual Editor
    st.markdown("---")
    st.subheader("✏️ Single Lead Inspector & Manual Copy Editor")
    if leads:
        lead_options = {f"{l['lead_email']} ({l['target_domain']}) - [{l['status']}]": l for l in leads}
        selected_opt = st.selectbox("Select Lead to Inspect / Edit:", list(lead_options.keys()))
        target_lead = lead_options[selected_opt]

        st.markdown(f"**Target Domain**: `{target_lead['target_domain']}` | **Lead Email**: `{target_lead['lead_email']}` | **Status**: `{target_lead['status']}`")

        edit_subj = st.text_input("Email Subject Line", value=target_lead["email_subject"] or f"{target_lead['target_domain']}", key="single_subj_input")
        edit_body = st.text_area("Email Body Copy", value=target_lead["email_body"] or "", height=230, key="single_body_input")

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            if st.button("💾 Save Copy Modifications", key="btn_save_single_copy"):
                db.update_lead_draft(target_lead["id"], edit_subj, edit_body)
                st.success("Updated copy saved to database!")
                st.rerun()
        with col_s2:
            if st.button("🚀 Send Single Email Now", key="btn_send_single_now"):
                sender = SmtpSender(db)
                dry_run = not mode_is_live
                target_recipient = "medido25@gmail.com" if enforce_test_email else target_lead["lead_email"]
                try:
                    if sender.send_email(target_recipient, edit_subj, edit_body, dry_run=dry_run):
                        db.mark_lead_sent(target_lead["id"])
                        mode_str = "[LIVE Hostinger SMTP]" if mode_is_live else "[DRY-RUN Simulation]"
                        st.success(f"Dispatched email {mode_str} to recipient: {target_recipient}")
                        st.rerun()
                except Exception as err:
                    db.mark_lead_failed(target_lead["id"], str(err))
                    st.error(f"Hostinger SMTP Error: {err}")

# ---------------------------------------------------------
# VIEW 5: 📥 Hostinger IMAP Monitor
# ---------------------------------------------------------
elif view_selection == "📥 Hostinger IMAP Monitor":
    st.subheader("📥 Hostinger IMAP Inbox Listener & Reply Tracker")

    col_imp1, col_imp2 = st.columns([2, 1])
    with col_imp1:
        st.markdown("Click below to connect to `imap.hostinger.com:993` over SSL and parse incoming prospect replies or unsubscribes:")
        if st.button("📥 Execute Hostinger IMAP Inbox Sync Now", key="btn_sync_imap_now"):
            with st.spinner("Connecting to Hostinger IMAP..."):
                listener = ImapListener(db)
                summary = listener.sync_inbox()
                st.success(f"Sync complete! Detected {summary['replied']} prospect reply(ies) and {summary['unsubscribed']} unsubscribe(s).")
                st.rerun()

    with col_imp2:
        st.info(f"**IMAP Host**: imap.hostinger.com\n\n**Port**: 993 (SSL)\n\n**Account**: {Config.SMTP_USER}")

    st.markdown("---")
    st.subheader("💬 Prospect Replies Log (REPLIED Status)")
    replied_leads = db.get_leads_by_status("REPLIED")
    if replied_leads:
        st.dataframe(pd.DataFrame([dict(r) for r in replied_leads]), use_container_width=True)
    else:
        st.info("No prospect replies recorded yet.")

    st.markdown("---")
    st.subheader("🚫 Opted-Out Prospects (UNSUBSCRIBED Status)")
    unsub_leads = db.get_leads_by_status("UNSUBSCRIBED")
    if unsub_leads:
        st.dataframe(pd.DataFrame([dict(u) for u in unsub_leads]), use_container_width=True)
    else:
        st.info("No unsubscribes recorded yet.")

# ---------------------------------------------------------
# VIEW 6: ⚙️ System Settings & Diagnostics
# ---------------------------------------------------------
elif view_selection == "⚙️ System Settings & Diagnostics":
    st.subheader("⚙️ System Credentials & SMTP Diagnostics")

    col_set1, col_set2 = st.columns(2)
    
    with col_set1:
        st.markdown("#### ✉️ Hostinger SMTP Configuration")
        st.text_input("SMTP Host", value=Config.SMTP_HOST, disabled=True)
        st.text_input("SMTP Port", value=str(Config.SMTP_PORT), disabled=True)
        st.text_input("SMTP Username", value=Config.SMTP_USER, disabled=True)
        st.text_input("Sender Name Signature", value=Config.SENDER_NAME, disabled=True)

        if st.button("🧪 Test Hostinger SMTP Connection"):
            sender = SmtpSender(db)
            ok, msg = sender.test_connection()
            if ok:
                st.success(f"✅ SMTP Connection Success! {msg}")
            else:
                st.error(f"❌ SMTP Connection Error: {msg}")

    with col_set2:
        st.markdown("#### 🔑 B2B API Credentials")
        st.text_input("Hunter API Key", value=Config.HUNTER_API_KEY or "Not Configured (Optional)", disabled=True)
        st.markdown("#### 🛡️ Rate Limits & Safeguards")
        st.number_input("Max Daily Emails", value=Config.MAX_DAILY_EMAILS, disabled=True)
        st.number_input("Min Delay (Seconds)", value=Config.MIN_DELAY_SECONDS, disabled=True)
        st.number_input("Max Delay (Seconds)", value=Config.MAX_DELAY_SECONDS, disabled=True)
