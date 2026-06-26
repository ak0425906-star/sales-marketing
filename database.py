"""
LeadLift Marketing Automation — Database Layer
SQLite database models, initialization, and CSV data migration.
"""

import sqlite3
import csv
import os
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "leadlift.db"
LOCAL_DATA_DIR = Path(__file__).parent / "data"
LEADLIFT_DATA_DIR = LOCAL_DATA_DIR if LOCAL_DATA_DIR.exists() else Path(r"c:\Users\ak042\OneDrive\Desktop\LeadLift\data")


def get_db():
    """Get a database connection with row_factory for dict-like access."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Initialize all database tables."""
    conn = get_db()
    cursor = conn.cursor()

    # ── Agencies Table ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            website TEXT,
            city TEXT,
            state TEXT,
            services TEXT,
            notable_clients TEXT,
            contact_page_url TEXT,
            general_email TEXT,
            phone TEXT,
            partnership_score INTEGER DEFAULT 0,
            pipeline_stage TEXT DEFAULT 'research',
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── Clinics Table ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clinics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            website TEXT,
            location TEXT,
            specialty TEXT,
            has_chatbot INTEGER DEFAULT 0,
            social_media_score INTEGER DEFAULT 0,
            lead_quality_score INTEGER DEFAULT 0,
            pipeline_stage TEXT DEFAULT 'research',
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── Contacts (Decision Makers) Table ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            title TEXT,
            company TEXT,
            company_id INTEGER,
            lead_type TEXT DEFAULT 'agency',
            email TEXT,
            phone TEXT,
            linkedin_url TEXT,
            confidence_score INTEGER DEFAULT 0,
            pipeline_stage TEXT DEFAULT 'enriched',
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (company_id) REFERENCES agencies(id)
        )
    """)

    # ── Outreach Log Table ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS outreach_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER,
            contact_name TEXT,
            company_name TEXT,
            lead_type TEXT DEFAULT 'agency',
            channel TEXT NOT NULL,
            message_subject TEXT,
            message_body TEXT,
            sent_date TEXT,
            status TEXT DEFAULT 'draft',
            follow_up_count INTEGER DEFAULT 0,
            last_follow_up_date TEXT,
            opened_at TEXT,
            replied_at TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (contact_id) REFERENCES contacts(id)
        )
    """)

    # ── Meetings Table ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER,
            contact_name TEXT,
            company_name TEXT,
            lead_type TEXT DEFAULT 'agency',
            meeting_date TEXT,
            meeting_time TEXT,
            meeting_format TEXT DEFAULT 'Zoom',
            status TEXT DEFAULT 'confirmed',
            pre_meeting_brief TEXT,
            outcome TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (contact_id) REFERENCES contacts(id)
        )
    """)

    # ── Email Templates Table ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'outreach',
            subject TEXT,
            body TEXT,
            channel TEXT DEFAULT 'email',
            sequence_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── Follow-Up Queue Table ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS follow_up_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            outreach_id INTEGER,
            contact_id INTEGER,
            contact_name TEXT,
            company_name TEXT,
            scheduled_date TEXT NOT NULL,
            follow_up_number INTEGER DEFAULT 1,
            template_id INTEGER,
            status TEXT DEFAULT 'pending',
            executed_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (outreach_id) REFERENCES outreach_log(id),
            FOREIGN KEY (contact_id) REFERENCES contacts(id),
            FOREIGN KEY (template_id) REFERENCES email_templates(id)
        )
    """)

    # ── Settings Table (key-value store) ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── Activity Log Table ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            entity_type TEXT,
            entity_id INTEGER,
            details TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()


def log_activity(action: str, entity_type: str = None, entity_id: int = None, details: str = None):
    """Log an activity to the audit trail."""
    conn = get_db()
    conn.execute(
        "INSERT INTO activity_log (action, entity_type, entity_id, details) VALUES (?, ?, ?, ?)",
        (action, entity_type, entity_id, details)
    )
    conn.commit()
    conn.close()


def import_agency_leads():
    """Import agency leads from the existing LeadLift CSV."""
    csv_path = LEADLIFT_DATA_DIR / "agency_leads.csv"
    if not csv_path.exists():
        return 0

    conn = get_db()
    cursor = conn.cursor()

    # Check if data already imported
    count = cursor.execute("SELECT COUNT(*) FROM agencies").fetchone()[0]
    if count > 0:
        conn.close()
        return count

    imported = 0
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("Agency Name", "").strip():
                continue
            cursor.execute("""
                INSERT INTO agencies (name, website, city, state, services, notable_clients,
                    contact_page_url, general_email, phone, partnership_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row.get("Agency Name", "").strip(),
                row.get("Website", "").strip(),
                row.get("City", "").strip(),
                row.get("State", "").strip(),
                row.get("Services", "").strip(),
                row.get("Notable Clients", "").strip(),
                row.get("Contact Page URL", "").strip(),
                row.get("General Contact Email", "").strip(),
                row.get("Phone Number", "").strip(),
                int(row.get("Partnership Potential Score", 0) or 0),
            ))
            imported += 1

    conn.commit()
    conn.close()
    log_activity("csv_import", "agencies", details=f"Imported {imported} agency leads")
    return imported


def import_decision_makers():
    """Import decision-maker contacts from the existing LeadLift CSV."""
    csv_path = LEADLIFT_DATA_DIR / "top15_decision_makers.csv"
    if not csv_path.exists():
        return 0

    conn = get_db()
    cursor = conn.cursor()

    # Check if data already imported
    count = cursor.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
    if count > 0:
        conn.close()
        return count

    imported = 0
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("Name", "").strip():
                continue

            company_name = row.get("Company", "").strip()

            # Try to link to an agency record
            agency = cursor.execute(
                "SELECT id FROM agencies WHERE name = ?", (company_name,)
            ).fetchone()
            company_id = agency[0] if agency else None

            cursor.execute("""
                INSERT INTO contacts (name, title, company, company_id, lead_type,
                    email, linkedin_url, confidence_score)
                VALUES (?, ?, ?, ?, 'agency', ?, ?, ?)
            """, (
                row.get("Name", "").strip(),
                row.get("Title", "").strip(),
                company_name,
                company_id,
                row.get("Public Email", "").strip(),
                row.get("LinkedIn URL", "").strip(),
                int(row.get("Contact Confidence Score", 0) or 0),
            ))
            imported += 1

    conn.commit()
    conn.close()
    log_activity("csv_import", "contacts", details=f"Imported {imported} decision makers")
    return imported


def import_email_templates():
    """Seed default email templates from the outreach playbook."""
    conn = get_db()
    cursor = conn.cursor()

    count = cursor.execute("SELECT COUNT(*) FROM email_templates").fetchone()[0]
    if count > 0:
        conn.close()
        return count

    templates = [
        # LinkedIn templates
        {
            "name": "LinkedIn Connect — Compliment + Value Hook",
            "category": "linkedin",
            "channel": "linkedin",
            "subject": "",
            "sequence_order": 1,
            "body": (
                "Hi {first_name},\n\n"
                "I've been following {agency_name}'s work with aesthetic clinics — really impressive portfolio.\n\n"
                "We're helping clinics capture after-hours leads with AI chatbots and calling bots. "
                "I think there's a strong partnership opportunity.\n\n"
                "Would love to connect.\n\n"
                "— {your_name}, Cosmasol"
            )
        },
        {
            "name": "LinkedIn Connect — Mutual Audience",
            "category": "linkedin",
            "channel": "linkedin",
            "subject": "",
            "sequence_order": 1,
            "body": (
                "Hi {first_name},\n\n"
                "We both serve plastic surgery clinics and MedSpas — just from different angles. "
                "We build AI chatbots and calling bots that capture leads your clients' websites are currently missing.\n\n"
                "I'd love to explore a referral or white-label partnership.\n\n"
                "— {your_name}, Cosmasol"
            )
        },
        {
            "name": "LinkedIn Connect — Direct Ask",
            "category": "linkedin",
            "channel": "linkedin",
            "subject": "",
            "sequence_order": 1,
            "body": (
                "Hi {first_name},\n\n"
                "Quick question: do your aesthetic clinic clients lose leads after hours or on weekends?\n\n"
                "We solve that with AI chatbots and calling bots. "
                "I have a partnership model that could add revenue for {agency_name}.\n\n"
                "Happy to share details if you're open to it.\n\n"
                "— {your_name}"
            )
        },
        {
            "name": "LinkedIn Follow-Up Message",
            "category": "linkedin",
            "channel": "linkedin",
            "subject": "",
            "sequence_order": 2,
            "body": (
                "Hey {first_name}, thanks for connecting!\n\n"
                "I'll keep this brief. We're Cosmasol — we build AI-powered lead capture tools "
                "specifically for aesthetic clinics:\n\n"
                "🤖 AI Website Chatbot — captures & qualifies leads 24/7\n"
                "📞 AI Calling Bot — follows up with missed calls automatically\n"
                "📱 Social Media AI Bot — converts DMs into booked consultations\n\n"
                "I've put together a simple partnership model for agencies like {agency_name} — "
                "referral commissions, white-label options, and co-marketing opportunities.\n\n"
                "Would you be open to a quick 15-minute call this week to see if it's a fit?\n\n"
                "Here's my calendar: {calendly_link}\n\n"
                "Either way, happy to be connected. 🙌\n\n"
                "— {your_name}"
            )
        },
        # Email templates
        {
            "name": "First Email — Partnership Intro",
            "category": "email_sequence",
            "channel": "email",
            "subject": "Partnership idea for {agency_name} 🤝",
            "sequence_order": 1,
            "body": (
                "Hi {first_name},\n\n"
                "I came across {agency_name} while researching the best agencies serving plastic surgery clinics "
                "and MedSpas — your work stood out.\n\n"
                "I'm reaching out because we've built something your clients would benefit from, and I think "
                "there's a partnership opportunity worth 15 minutes of your time.\n\n"
                "THE PROBLEM WE SOLVE:\n"
                "Most aesthetic clinics lose 30–50% of website leads because:\n"
                "• No one responds after business hours\n"
                "• Contact forms go unanswered for 24+ hours\n"
                "• Social media DMs sit unread over weekends\n\n"
                "OUR SOLUTION:\n"
                "Cosmasol provides three AI-powered tools that integrate directly into the websites "
                "and marketing funnels you already build:\n\n"
                "1. AI Website Chatbot — engages visitors, answers questions, and books consultations 24/7\n"
                "2. AI Calling Bot — automatically follows up on missed calls and form submissions\n"
                "3. Social Media AI Bot — converts Instagram and Facebook DMs into booked appointments\n\n"
                "THE PARTNERSHIP OPPORTUNITY:\n"
                "• Referral Commission — earn per clinic you introduce\n"
                "• White Label — offer our AI tools under your brand\n"
                "• Revenue Share — ongoing recurring income per active client\n"
                "• Co-Marketing — joint case studies and webinars\n\n"
                "Would you be open to a quick 15-minute call this week to explore whether this makes sense "
                "for {agency_name}?\n\n"
                "Here's my calendar: {calendly_link}\n\n"
                "Or just reply with a time that works and I'll send an invite.\n\n"
                "Best,\n"
                "{your_name}\n"
                "{your_title}\n"
                "Cosmasol"
            )
        },
        {
            "name": "Follow-Up #1 — Day 7 Bump",
            "category": "email_sequence",
            "channel": "email",
            "subject": "Re: Partnership idea for {agency_name} 🤝",
            "sequence_order": 2,
            "body": (
                "Hi {first_name},\n\n"
                "Just floating this back to the top of your inbox — I know things get busy running an agency.\n\n"
                "To make it easy, here's the one-line version:\n\n"
                "→ We help your aesthetic clinic clients capture 30–50% more leads with AI chatbots, "
                "and we'll pay you a referral fee or white-label the solution under your brand.\n\n"
                "If the timing isn't right, no worries — happy to circle back in a few weeks.\n\n"
                "But if you're even slightly curious, I'd love 15 minutes to show you how it works: "
                "{calendly_link}\n\n"
                "Best,\n"
                "{your_name}\n"
                "Cosmasol"
            )
        },
        {
            "name": "Follow-Up #2 — Day 14 Breakup",
            "category": "email_sequence",
            "channel": "email",
            "subject": "Re: Partnership idea for {agency_name} 🤝",
            "sequence_order": 3,
            "body": (
                "Hi {first_name},\n\n"
                "I don't want to be that person who keeps following up, so this will be my last note for now.\n\n"
                "I'll leave you with a quick stat that might be relevant:\n\n"
                "📊 Clinics using AI chatbots see an average 35% increase in booked consultations "
                "from the same website traffic — zero additional ad spend required.\n\n"
                "For an agency building websites and running paid campaigns for aesthetic clinics, "
                "that's a powerful result to offer your clients.\n\n"
                "If you'd ever like to explore a partnership (referral, white-label, or co-marketing), "
                "my door is always open:\n\n"
                "📧 {your_email}\n"
                "📅 {calendly_link}\n\n"
                "Wishing you and the {agency_name} team continued success.\n\n"
                "Best,\n"
                "{your_name}\n"
                "Cosmasol"
            )
        },
    ]

    for t in templates:
        cursor.execute("""
            INSERT INTO email_templates (name, category, subject, body, channel, sequence_order)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (t["name"], t["category"], t["subject"], t["body"], t["channel"], t["sequence_order"]))

    conn.commit()
    conn.close()
    log_activity("seed_templates", "email_templates", details=f"Seeded {len(templates)} templates")
    return len(templates)


def run_all_imports():
    """Run all data imports and return summary."""
    init_db()
    agencies = import_agency_leads()
    contacts = import_decision_makers()
    templates = import_email_templates()
    return {
        "agencies_imported": agencies,
        "contacts_imported": contacts,
        "templates_seeded": templates,
    }


if __name__ == "__main__":
    result = run_all_imports()
    print(f"Database initialized: {result}")
