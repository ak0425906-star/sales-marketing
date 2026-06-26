"""
LeadLift Marketing Automation — Automation Engine
AI message generation (Gemini), email sending (SMTP), and follow-up scheduling.
"""

import json
import re
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path

from database import get_db, log_activity


# ── Agency-Specific Pitch Hooks (from AGENCY_SPECIFIC_PITCHES.md) ──
AGENCY_PITCH_HOOKS = {
    "Plastix Marketing": {
        "hook": "Deep Integration with Aesthetix CRM",
        "angle": "They have their own CRM system (Aesthetix CRM). Position Cosmasol as the 'front door' for their CRM — capturing leads before they even enter the system.",
        "key_point": "white-label AI capture engine directly into CRM offering"
    },
    "NKP Medical Marketing": {
        "hook": "Upgrading Legacy/Generic Chat to AI Booking",
        "angle": "Already offers chat solutions but likely outdated manual or live chat. Position as upgrade.",
        "key_point": "side-by-side comparison showing AI booking doubles conversion rates"
    },
    "Studio III Marketing": {
        "hook": "Protecting Premium Web Design Conversions",
        "angle": "15+ years of beautiful, high-end websites. They reject clunky chatbots. Position as sleek, glassmorphic AI that matches premium designs.",
        "key_point": "pilot on one client site to prove design ROI increase"
    },
    "Incredible Marketing": {
        "hook": "Lowering Client CPA Across Channels",
        "angle": "Multi-channel campaigns (SEO + PPC + Social). Lost leads after hours impact CPA.",
        "key_point": "30-day pilot for 3 clients to prove ROI via lower CPA"
    },
    "Plastic Surgery Studios": {
        "hook": "20 Years of SEO — Meeting the Final Conversion Piece",
        "angle": "Massive loyal client base with optimized search traffic. Need to optimize conversion, not traffic.",
        "key_point": "AI lead capture layer for long-tenured surgeon sites"
    },
    "Influx Marketing": {
        "hook": "The Conversion Multiplier for Custom Designs",
        "angle": "Custom high-converting designs. Tech-competitive. Position as technology partnership.",
        "key_point": "co-author case study or joint webinar on AI-Powered Conversion"
    },
    "Rosemont Media": {
        "hook": "In-House Technical Integration Partnership",
        "angle": "All design and dev in-house. Want clean code, easy integrations.",
        "key_point": "single-line script embed, zero heavy lifting for developers"
    },
    "PilotPractice": {
        "hook": "Connecting Front-End AI Chat to Back-End CRM",
        "angle": "Tech-forward with proprietary automated follow-up software. Appreciate automation and APIs.",
        "key_point": "seamless API integration between front-end capture and back-end CRM"
    },
    "PBHS (RevenueWell)": {
        "hook": "Enterprise Platform-Level Integration",
        "angle": "Part of RevenueWell ecosystem. Operates at scale. Position as platform add-on module.",
        "key_point": "new high-margin SaaS revenue stream within PBHS ecosystem"
    },
    "GrowthMed": {
        "hook": "Multiplying SEO Traffic ROI with AI",
        "angle": "Highly technical, SEO-focused. Ranking #1 is half the battle — traffic must convert.",
        "key_point": "30-day pilot tracking conversion lift from SEO traffic"
    },
    "Intrepy Healthcare Marketing": {
        "hook": "Capturing the High-Growth MedSpa Southeast Market",
        "angle": "Offices in GA and FL. MedSpa market booming in Southeast. Cash-pay patients expect instant booking.",
        "key_point": "case study of AI chatbot in cash-pay aesthetic space"
    },
    "MDLogica": {
        "hook": "Luxury-Tier Patient Engagement",
        "angle": "Beverly Hills premium clients. High-net-worth patients expect instant, white-glove responsiveness.",
        "key_point": "AI custom-trained for luxury-tier patient conversations"
    },
    "Thrive Internet Marketing Agency": {
        "hook": "Bulk Deployment Options for Medical Clients",
        "angle": "Massive agency. Needs standardized, scalable solutions for healthcare vertical.",
        "key_point": "bulk partnership program with agency-exclusive wholesale pricing"
    },
    "ClinicGrower": {
        "hook": "The Perfect Tech + Coaching Synergy",
        "angle": "Trains clinic staff to follow up and close leads. Perfect pairing for AI lead capture.",
        "key_point": "AI automates tech capture, they coach the team — ultimate growth bundle"
    },
    "MDConsultingNY": {
        "hook": "Founder-to-Founder / Former MedSpa Owner Connection",
        "angle": "Erica is a former 7-figure MedSpa owner. Understands operational pain of missed calls.",
        "key_point": "automated 24/7 receptionist solving the operational bottleneck"
    },
}


def get_setting(key: str, default: str = "") -> str:
    """Get a setting value from the database."""
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row[0] if row else default


def set_setting(key: str, value: str):
    """Set a setting value in the database."""
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        (key, value)
    )
    conn.commit()
    conn.close()


def get_all_settings() -> dict:
    """Get all settings as a dictionary."""
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}


# ═══════════════════════════════════════════════════════════════
# AI MESSAGE GENERATION (Gemini)
# ═══════════════════════════════════════════════════════════════

def generate_ai_message(contact_name: str, company_name: str, channel: str = "email",
                        template_type: str = "first_email", custom_context: str = "") -> dict:
    """
    Generate a personalized outreach message using Gemini AI.
    Falls back to template-based generation if no API key is configured.
    """
    api_key = get_setting("gemini_api_key")

    # Get agency data for context
    conn = get_db()
    agency = conn.execute(
        "SELECT * FROM agencies WHERE name = ?", (company_name,)
    ).fetchone()
    contact = conn.execute(
        "SELECT * FROM contacts WHERE name = ? AND company = ?", (contact_name, company_name)
    ).fetchone()
    conn.close()

    # Build context
    first_name = contact_name.split()[0] if contact_name else "there"
    agency_data = dict(agency) if agency else {}
    pitch_hook = AGENCY_PITCH_HOOKS.get(company_name, {})

    your_name = get_setting("your_name", "Your Name")
    your_title = get_setting("your_title", "Partnerships")
    your_email = get_setting("your_email", "")
    calendly_link = get_setting("calendly_link", "[Your Calendly Link]")

    if api_key:
        return _generate_with_gemini(
            api_key, first_name, company_name, channel, template_type,
            agency_data, pitch_hook, your_name, your_title, your_email,
            calendly_link, custom_context
        )
    else:
        return _generate_from_template(
            first_name, company_name, channel, template_type,
            agency_data, pitch_hook, your_name, your_title, your_email,
            calendly_link
        )


def _generate_with_gemini(api_key, first_name, company_name, channel, template_type,
                           agency_data, pitch_hook, your_name, your_title, your_email,
                           calendly_link, custom_context) -> dict:
    """Generate message using Gemini API."""
    try:
        from google import genai

        client = genai.Client(api_key=api_key)

        services = agency_data.get("services", "aesthetic clinic marketing")
        notable_clients = agency_data.get("notable_clients", "aesthetic clinics")
        hook = pitch_hook.get("hook", "AI-powered lead capture")
        angle = pitch_hook.get("angle", "")
        key_point = pitch_hook.get("key_point", "")

        prompt = f"""You are a business development expert writing outreach messages for Cosmasol,
a company that builds AI-powered lead capture tools for aesthetic clinics (AI Website Chatbot,
AI Calling Bot, Social Media AI Bot).

Generate a personalized {channel} message for:
- Contact: {first_name} at {company_name}
- Agency services: {services}
- Agency's notable clients: {notable_clients}
- Pitch hook: {hook}
- Pitch angle: {angle}
- Key talking point: {key_point}
- Message type: {template_type}
- Your name: {your_name}
- Your title: {your_title}
- Calendly link: {calendly_link}
{f'- Additional context: {custom_context}' if custom_context else ''}

Rules:
1. Be professional but warm — peer-to-peer tone, not salesy
2. Lead with value, not features
3. Reference something specific about {company_name}
4. Keep it concise (under 200 words for email, under 300 chars for LinkedIn connection)
5. Include a clear CTA (15-minute call)
6. {"Include a compelling subject line" if channel == "email" else "Stay within 300 characters" if "connect" in template_type else ""}

Return ONLY a JSON object with keys: "subject" (empty string if not email), "body"
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        text = response.text.strip()
        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            result = json.loads(json_match.group())
            return {
                "subject": result.get("subject", ""),
                "body": result.get("body", ""),
                "generated_by": "gemini",
                "success": True
            }
        else:
            return {
                "subject": "",
                "body": text,
                "generated_by": "gemini",
                "success": True
            }

    except Exception as e:
        # Fall back to template
        result = _generate_from_template(
            first_name, company_name, channel, template_type,
            {}, pitch_hook, your_name, your_title, your_email, calendly_link
        )
        result["error"] = str(e)
        result["generated_by"] = "template_fallback"
        return result


def _generate_from_template(first_name, company_name, channel, template_type,
                             agency_data, pitch_hook, your_name, your_title,
                             your_email, calendly_link) -> dict:
    """Generate message from pre-built templates (no AI needed)."""
    conn = get_db()

    # Map template_type to a category/sequence
    if channel == "linkedin":
        if "connect" in template_type:
            templates = conn.execute(
                "SELECT * FROM email_templates WHERE channel = 'linkedin' AND sequence_order = 1"
            ).fetchall()
        else:
            templates = conn.execute(
                "SELECT * FROM email_templates WHERE channel = 'linkedin' AND sequence_order = 2"
            ).fetchall()
    else:
        if "follow_up_2" in template_type or "breakup" in template_type:
            templates = conn.execute(
                "SELECT * FROM email_templates WHERE channel = 'email' AND sequence_order = 3"
            ).fetchall()
        elif "follow_up" in template_type:
            templates = conn.execute(
                "SELECT * FROM email_templates WHERE channel = 'email' AND sequence_order = 2"
            ).fetchall()
        else:
            templates = conn.execute(
                "SELECT * FROM email_templates WHERE channel = 'email' AND sequence_order = 1"
            ).fetchall()

    conn.close()

    if not templates:
        return {
            "subject": f"Partnership idea for {company_name}",
            "body": f"Hi {first_name},\n\nI'd love to discuss a partnership opportunity between {company_name} and Cosmasol.\n\nBest,\n{your_name}",
            "generated_by": "fallback",
            "success": True
        }

    template = dict(templates[0])

    # Replace placeholders
    replacements = {
        "{first_name}": first_name,
        "{agency_name}": company_name,
        "{your_name}": your_name,
        "{your_title}": your_title,
        "{your_email}": your_email,
        "{calendly_link}": calendly_link,
    }

    subject = template.get("subject", "")
    body = template.get("body", "")

    for placeholder, value in replacements.items():
        subject = subject.replace(placeholder, value)
        body = body.replace(placeholder, value)

    return {
        "subject": subject,
        "body": body,
        "generated_by": "template",
        "template_name": template.get("name", ""),
        "success": True
    }


# ═══════════════════════════════════════════════════════════════
# EMAIL SENDING (SMTP)
# ═══════════════════════════════════════════════════════════════

def send_email(to_email: str, subject: str, body: str, contact_id: int = None,
               contact_name: str = "", company_name: str = "") -> dict:
    """
    Send an email via SMTP. Returns success/failure status.
    Logs the outreach activity automatically.
    """
    smtp_host = get_setting("smtp_host", "smtp.gmail.com")
    smtp_port = int(get_setting("smtp_port", "587"))
    smtp_user = get_setting("smtp_user")
    smtp_pass = get_setting("smtp_password")
    from_email = get_setting("from_email", smtp_user)
    from_name = get_setting("your_name", "Cosmasol")

    if not smtp_user or not smtp_pass:
        return {
            "success": False,
            "error": "SMTP credentials not configured. Go to Settings to add your email credentials.",
            "mode": "no_smtp"
        }

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = to_email

        # Plain text version
        msg.attach(MIMEText(body, "plain"))

        # HTML version (basic formatting)
        html_body = body.replace("\n", "<br>")
        html = f"""<html><body style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
            {html_body}
        </body></html>"""
        msg.attach(MIMEText(html, "html"))

        # Send
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls(context=context)
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        # Log the outreach
        conn = get_db()
        conn.execute("""
            INSERT INTO outreach_log (contact_id, contact_name, company_name, lead_type,
                channel, message_subject, message_body, sent_date, status)
            VALUES (?, ?, ?, 'agency', 'email', ?, ?, datetime('now'), 'sent')
        """, (contact_id, contact_name, company_name, subject, body))
        conn.commit()
        conn.close()

        log_activity("email_sent", "outreach", details=f"Email to {to_email}: {subject}")

        return {"success": True, "message": f"Email sent to {to_email}"}

    except Exception as e:
        log_activity("email_failed", "outreach", details=f"Failed to send to {to_email}: {str(e)}")
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════
# FOLLOW-UP SCHEDULING
# ═══════════════════════════════════════════════════════════════

def schedule_follow_ups(outreach_id: int, contact_id: int, contact_name: str,
                        company_name: str) -> list:
    """
    Schedule follow-up emails at Day 7 and Day 14 after initial outreach.
    """
    conn = get_db()

    now = datetime.now()
    follow_ups = [
        {
            "follow_up_number": 1,
            "scheduled_date": (now + timedelta(days=7)).strftime("%Y-%m-%d"),
        },
        {
            "follow_up_number": 2,
            "scheduled_date": (now + timedelta(days=14)).strftime("%Y-%m-%d"),
        },
    ]

    created = []
    for fu in follow_ups:
        # Find the matching template
        template = conn.execute(
            "SELECT id FROM email_templates WHERE channel = 'email' AND sequence_order = ?",
            (fu["follow_up_number"] + 1,)
        ).fetchone()
        template_id = template[0] if template else None

        conn.execute("""
            INSERT INTO follow_up_queue (outreach_id, contact_id, contact_name, company_name,
                scheduled_date, follow_up_number, template_id, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (
            outreach_id, contact_id, contact_name, company_name,
            fu["scheduled_date"], fu["follow_up_number"], template_id
        ))
        created.append(fu)

    conn.commit()
    conn.close()

    log_activity("follow_ups_scheduled", "follow_up_queue",
                 details=f"Scheduled {len(created)} follow-ups for {contact_name} at {company_name}")
    return created


def process_pending_follow_ups() -> list:
    """
    Process any follow-ups that are due today. Send emails if SMTP is configured,
    otherwise mark them as 'ready' for manual sending.
    """
    conn = get_db()
    today = datetime.now().strftime("%Y-%m-%d")

    pending = conn.execute("""
        SELECT fq.*, et.subject, et.body
        FROM follow_up_queue fq
        LEFT JOIN email_templates et ON fq.template_id = et.id
        WHERE fq.status = 'pending' AND fq.scheduled_date <= ?
    """, (today,)).fetchall()

    results = []
    for fu in pending:
        fu = dict(fu)
        contact = conn.execute(
            "SELECT * FROM contacts WHERE id = ?", (fu["contact_id"],)
        ).fetchone()

        if not contact:
            conn.execute(
                "UPDATE follow_up_queue SET status = 'skipped' WHERE id = ?", (fu["id"],)
            )
            continue

        contact = dict(contact)
        email = contact.get("email", "")

        if not email:
            conn.execute(
                "UPDATE follow_up_queue SET status = 'no_email' WHERE id = ?", (fu["id"],)
            )
            results.append({"id": fu["id"], "status": "no_email", "contact": fu["contact_name"]})
            continue

        # Generate the message
        template_type = "follow_up" if fu["follow_up_number"] == 1 else "follow_up_2"
        message = generate_ai_message(
            fu["contact_name"], fu["company_name"],
            channel="email", template_type=template_type
        )

        smtp_configured = bool(get_setting("smtp_user"))

        if smtp_configured:
            result = send_email(
                email, message["subject"], message["body"],
                contact_id=fu["contact_id"],
                contact_name=fu["contact_name"],
                company_name=fu["company_name"]
            )
            status = "sent" if result["success"] else "failed"
        else:
            status = "ready"

        conn.execute(
            "UPDATE follow_up_queue SET status = ?, executed_at = datetime('now') WHERE id = ?",
            (status, fu["id"])
        )

        results.append({
            "id": fu["id"],
            "status": status,
            "contact": fu["contact_name"],
            "company": fu["company_name"],
            "follow_up_number": fu["follow_up_number"],
            "message": message
        })

    conn.commit()
    conn.close()
    return results


# ═══════════════════════════════════════════════════════════════
# ANALYTICS & REPORTING
# ═══════════════════════════════════════════════════════════════

def get_dashboard_stats() -> dict:
    """Get real-time dashboard statistics."""
    conn = get_db()

    stats = {
        "total_agencies": conn.execute("SELECT COUNT(*) FROM agencies").fetchone()[0],
        "total_clinics": conn.execute("SELECT COUNT(*) FROM clinics").fetchone()[0],
        "total_contacts": conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0],
        "outreach_sent": conn.execute(
            "SELECT COUNT(*) FROM outreach_log WHERE status != 'draft'"
        ).fetchone()[0],
        "outreach_replied": conn.execute(
            "SELECT COUNT(*) FROM outreach_log WHERE status = 'replied'"
        ).fetchone()[0],
        "meetings_booked": conn.execute(
            "SELECT COUNT(*) FROM meetings WHERE status IN ('confirmed', 'completed')"
        ).fetchone()[0],
        "meetings_held": conn.execute(
            "SELECT COUNT(*) FROM meetings WHERE status = 'completed'"
        ).fetchone()[0],
        "pending_follow_ups": conn.execute(
            "SELECT COUNT(*) FROM follow_up_queue WHERE status = 'pending'"
        ).fetchone()[0],
        "pipeline": {
            "research": conn.execute(
                "SELECT COUNT(*) FROM agencies WHERE pipeline_stage = 'research'"
            ).fetchone()[0],
            "enriched": conn.execute(
                "SELECT COUNT(*) FROM contacts WHERE pipeline_stage = 'enriched'"
            ).fetchone()[0],
            "contacted": conn.execute(
                "SELECT COUNT(*) FROM outreach_log WHERE status = 'sent'"
            ).fetchone()[0],
            "responded": conn.execute(
                "SELECT COUNT(*) FROM outreach_log WHERE status = 'replied'"
            ).fetchone()[0],
            "meeting_booked": conn.execute(
                "SELECT COUNT(*) FROM meetings WHERE status = 'confirmed'"
            ).fetchone()[0],
            "partner_signed": conn.execute(
                "SELECT COUNT(*) FROM meetings WHERE status = 'completed' AND outcome = 'signed'"
            ).fetchone()[0],
        },
        "channel_stats": {},
        "recent_activity": [],
    }

    # Channel breakdown
    channels = conn.execute("""
        SELECT channel, COUNT(*) as total,
            SUM(CASE WHEN status = 'replied' THEN 1 ELSE 0 END) as replies
        FROM outreach_log
        WHERE status != 'draft'
        GROUP BY channel
    """).fetchall()

    for ch in channels:
        ch = dict(ch)
        stats["channel_stats"][ch["channel"]] = {
            "sent": ch["total"],
            "replied": ch["replies"],
            "reply_rate": round((ch["replies"] / ch["total"] * 100), 1) if ch["total"] > 0 else 0
        }

    # Recent activity
    activities = conn.execute("""
        SELECT * FROM activity_log ORDER BY created_at DESC LIMIT 20
    """).fetchall()
    stats["recent_activity"] = [dict(a) for a in activities]

    # Days remaining until July 20
    deadline = datetime(2026, 7, 20)
    days_remaining = (deadline - datetime.now()).days
    stats["days_remaining"] = max(0, days_remaining)
    stats["deadline"] = "2026-07-20"

    # Response rate
    if stats["outreach_sent"] > 0:
        stats["response_rate"] = round(
            (stats["outreach_replied"] / stats["outreach_sent"]) * 100, 1
        )
    else:
        stats["response_rate"] = 0

    conn.close()
    return stats


def get_analytics_data() -> dict:
    """Get detailed analytics for charts and reports."""
    conn = get_db()

    # Outreach over time
    outreach_timeline = conn.execute("""
        SELECT DATE(sent_date) as date, COUNT(*) as count, channel
        FROM outreach_log
        WHERE status != 'draft' AND sent_date IS NOT NULL
        GROUP BY DATE(sent_date), channel
        ORDER BY date
    """).fetchall()

    # Pipeline funnel
    funnel = {
        "Research": conn.execute("SELECT COUNT(*) FROM agencies").fetchone()[0],
        "Enriched": conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0],
        "Contacted": conn.execute("SELECT COUNT(*) FROM outreach_log WHERE status = 'sent'").fetchone()[0],
        "Responded": conn.execute("SELECT COUNT(*) FROM outreach_log WHERE status = 'replied'").fetchone()[0],
        "Meeting Booked": conn.execute("SELECT COUNT(*) FROM meetings").fetchone()[0],
        "Partner Signed": conn.execute(
            "SELECT COUNT(*) FROM meetings WHERE outcome = 'signed'"
        ).fetchone()[0],
    }

    # Score distribution
    score_dist = conn.execute("""
        SELECT partnership_score, COUNT(*) as count
        FROM agencies
        GROUP BY partnership_score
        ORDER BY partnership_score
    """).fetchall()

    conn.close()

    return {
        "outreach_timeline": [dict(row) for row in outreach_timeline],
        "funnel": funnel,
        "score_distribution": [dict(row) for row in score_dist],
    }
