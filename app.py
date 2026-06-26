"""
LeadLift Marketing Automation — FastAPI Backend Server
Main application entry point with all API endpoints.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from database import get_db, init_db, run_all_imports, log_activity
from automation import (
    generate_ai_message, send_email, schedule_follow_ups,
    process_pending_follow_ups, get_dashboard_stats, get_analytics_data,
    get_setting, set_setting, get_all_settings, AGENCY_PITCH_HOOKS
)


# ── App Lifecycle ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and import data on startup."""
    print("🚀 Initializing LeadLift Marketing Automation...")
    result = run_all_imports()
    print(f"   ✅ Database ready: {result}")
    yield
    print("👋 Shutting down LeadLift.")


app = FastAPI(
    title="LeadLift Marketing Automation",
    description="Automated marketing pipeline for Cosmasol",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (dashboard)
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ═══════════════════════════════════════════════════════════════
# DASHBOARD HOME
# ═══════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the main dashboard HTML."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Dashboard not found. Place index.html in /static/</h1>")


@app.get("/api/dashboard")
async def dashboard_stats():
    """Get real-time dashboard statistics."""
    return get_dashboard_stats()


@app.get("/api/analytics")
async def analytics():
    """Get detailed analytics data for charts."""
    return get_analytics_data()


# ═══════════════════════════════════════════════════════════════
# LEADS (Agencies + Clinics)
# ═══════════════════════════════════════════════════════════════

@app.get("/api/leads")
async def list_leads(
    lead_type: str = Query("agency", description="agency or clinic"),
    search: str = Query("", description="Search by name"),
    stage: str = Query("", description="Filter by pipeline stage"),
    min_score: int = Query(0, description="Minimum partnership score"),
    sort_by: str = Query("partnership_score", description="Sort field"),
    sort_dir: str = Query("desc", description="asc or desc"),
):
    """List all leads with filtering and sorting."""
    conn = get_db()

    if lead_type == "clinic":
        query = "SELECT * FROM clinics WHERE 1=1"
        params = []
        if search:
            query += " AND (name LIKE ? OR location LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        if stage:
            query += " AND pipeline_stage = ?"
            params.append(stage)
        if min_score > 0:
            query += " AND lead_quality_score >= ?"
            params.append(min_score)
        query += f" ORDER BY {sort_by} {sort_dir}"
    else:
        query = "SELECT * FROM agencies WHERE 1=1"
        params = []
        if search:
            query += " AND (name LIKE ? OR services LIKE ? OR city LIKE ? OR state LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"])
        if stage:
            query += " AND pipeline_stage = ?"
            params.append(stage)
        if min_score > 0:
            query += " AND partnership_score >= ?"
            params.append(min_score)

        # Sanitize sort_by to prevent SQL injection
        allowed_sort = ["partnership_score", "name", "state", "created_at"]
        if sort_by not in allowed_sort:
            sort_by = "partnership_score"
        sort_dir_safe = "DESC" if sort_dir.lower() == "desc" else "ASC"
        query += f" ORDER BY {sort_by} {sort_dir_safe}"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.post("/api/leads")
async def create_lead(request: Request):
    """Create a new lead (agency or clinic)."""
    data = await request.json()
    lead_type = data.pop("lead_type", "agency")
    conn = get_db()

    if lead_type == "clinic":
        fields = ["name", "website", "location", "specialty", "has_chatbot",
                   "social_media_score", "lead_quality_score", "pipeline_stage", "notes"]
        values = {f: data.get(f, "") for f in fields}
        cursor = conn.execute(
            f"INSERT INTO clinics ({', '.join(fields)}) VALUES ({', '.join(['?' for _ in fields])})",
            list(values.values())
        )
    else:
        fields = ["name", "website", "city", "state", "services", "notable_clients",
                   "contact_page_url", "general_email", "phone", "partnership_score",
                   "pipeline_stage", "notes"]
        values = {f: data.get(f, "") for f in fields}
        cursor = conn.execute(
            f"INSERT INTO agencies ({', '.join(fields)}) VALUES ({', '.join(['?' for _ in fields])})",
            list(values.values())
        )

    conn.commit()
    lead_id = cursor.lastrowid
    conn.close()

    log_activity("lead_created", lead_type, lead_id, f"Created {lead_type}: {data.get('name', '')}")
    return {"id": lead_id, "message": f"{lead_type.title()} created successfully"}


@app.put("/api/leads/{lead_id}")
async def update_lead(lead_id: int, request: Request):
    """Update an existing lead."""
    data = await request.json()
    lead_type = data.pop("lead_type", "agency")
    table = "clinics" if lead_type == "clinic" else "agencies"
    conn = get_db()

    # Build SET clause dynamically
    set_parts = []
    values = []
    for key, value in data.items():
        if key not in ("id", "created_at"):
            set_parts.append(f"{key} = ?")
            values.append(value)

    if set_parts:
        set_parts.append("updated_at = datetime('now')")
        values.append(lead_id)
        conn.execute(f"UPDATE {table} SET {', '.join(set_parts)} WHERE id = ?", values)
        conn.commit()

    conn.close()
    log_activity("lead_updated", lead_type, lead_id)
    return {"message": f"{lead_type.title()} updated successfully"}


@app.delete("/api/leads/{lead_id}")
async def delete_lead(lead_id: int, lead_type: str = Query("agency")):
    """Delete a lead."""
    table = "clinics" if lead_type == "clinic" else "agencies"
    conn = get_db()
    conn.execute(f"DELETE FROM {table} WHERE id = ?", (lead_id,))
    conn.commit()
    conn.close()
    log_activity("lead_deleted", lead_type, lead_id)
    return {"message": "Lead deleted"}


# ═══════════════════════════════════════════════════════════════
# CONTACTS (Decision Makers)
# ═══════════════════════════════════════════════════════════════

@app.get("/api/contacts")
async def list_contacts(
    search: str = Query("", description="Search by name or company"),
    company: str = Query("", description="Filter by company"),
):
    """List all contacts."""
    conn = get_db()
    query = "SELECT * FROM contacts WHERE 1=1"
    params = []

    if search:
        query += " AND (name LIKE ? OR company LIKE ? OR title LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    if company:
        query += " AND company = ?"
        params.append(company)

    query += " ORDER BY confidence_score DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.post("/api/contacts")
async def create_contact(request: Request):
    """Create a new contact."""
    data = await request.json()
    conn = get_db()

    # Link to agency if possible
    company_name = data.get("company", "")
    agency = conn.execute(
        "SELECT id FROM agencies WHERE name = ?", (company_name,)
    ).fetchone()
    company_id = agency[0] if agency else None

    cursor = conn.execute("""
        INSERT INTO contacts (name, title, company, company_id, lead_type,
            email, phone, linkedin_url, confidence_score, pipeline_stage, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("name", ""), data.get("title", ""), company_name, company_id,
        data.get("lead_type", "agency"), data.get("email", ""), data.get("phone", ""),
        data.get("linkedin_url", ""), data.get("confidence_score", 5),
        data.get("pipeline_stage", "enriched"), data.get("notes", "")
    ))

    conn.commit()
    contact_id = cursor.lastrowid
    conn.close()

    log_activity("contact_created", "contact", contact_id, f"Created: {data.get('name', '')}")
    return {"id": contact_id, "message": "Contact created successfully"}


@app.put("/api/contacts/{contact_id}")
async def update_contact(contact_id: int, request: Request):
    """Update an existing contact."""
    data = await request.json()
    conn = get_db()

    set_parts = []
    values = []
    for key, value in data.items():
        if key not in ("id", "created_at", "company_id"):
            set_parts.append(f"{key} = ?")
            values.append(value)

    if set_parts:
        set_parts.append("updated_at = datetime('now')")
        values.append(contact_id)
        conn.execute(f"UPDATE contacts SET {', '.join(set_parts)} WHERE id = ?", values)
        conn.commit()

    conn.close()
    log_activity("contact_updated", "contact", contact_id)
    return {"message": "Contact updated successfully"}


@app.delete("/api/contacts/{contact_id}")
async def delete_contact(contact_id: int):
    """Delete a contact."""
    conn = get_db()
    conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
    conn.commit()
    conn.close()
    log_activity("contact_deleted", "contact", contact_id)
    return {"message": "Contact deleted"}


# ═══════════════════════════════════════════════════════════════
# OUTREACH
# ═══════════════════════════════════════════════════════════════

@app.get("/api/outreach")
async def list_outreach(
    status: str = Query("", description="Filter by status"),
    channel: str = Query("", description="Filter by channel"),
):
    """List all outreach activities."""
    conn = get_db()
    query = "SELECT * FROM outreach_log WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if channel:
        query += " AND channel = ?"
        params.append(channel)

    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.post("/api/outreach")
async def create_outreach(request: Request):
    """Log a new outreach activity."""
    data = await request.json()
    conn = get_db()

    cursor = conn.execute("""
        INSERT INTO outreach_log (contact_id, contact_name, company_name, lead_type,
            channel, message_subject, message_body, sent_date, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("contact_id"), data.get("contact_name", ""), data.get("company_name", ""),
        data.get("lead_type", "agency"), data.get("channel", "email"),
        data.get("message_subject", ""), data.get("message_body", ""),
        data.get("sent_date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        data.get("status", "sent"), data.get("notes", "")
    ))

    conn.commit()
    outreach_id = cursor.lastrowid
    conn.close()

    # Auto-schedule follow-ups if this is a first email
    if data.get("auto_follow_up", False) and data.get("contact_id"):
        schedule_follow_ups(
            outreach_id, data["contact_id"],
            data.get("contact_name", ""), data.get("company_name", "")
        )

    log_activity("outreach_logged", "outreach", outreach_id,
                 f"{data.get('channel', 'email')} to {data.get('contact_name', '')}")
    return {"id": outreach_id, "message": "Outreach logged successfully"}


@app.put("/api/outreach/{outreach_id}")
async def update_outreach(outreach_id: int, request: Request):
    """Update outreach status (e.g., mark as replied)."""
    data = await request.json()
    conn = get_db()

    set_parts = []
    values = []
    for key, value in data.items():
        if key not in ("id", "created_at"):
            set_parts.append(f"{key} = ?")
            values.append(value)

    if set_parts:
        values.append(outreach_id)
        conn.execute(f"UPDATE outreach_log SET {', '.join(set_parts)} WHERE id = ?", values)
        conn.commit()

    # If marking as replied, update pipeline stage
    if data.get("status") == "replied":
        row = conn.execute("SELECT contact_id FROM outreach_log WHERE id = ?", (outreach_id,)).fetchone()
        if row and row[0]:
            conn.execute(
                "UPDATE contacts SET pipeline_stage = 'responded', updated_at = datetime('now') WHERE id = ?",
                (row[0],)
            )
            conn.commit()

    conn.close()
    log_activity("outreach_updated", "outreach", outreach_id, f"Status: {data.get('status', '')}")
    return {"message": "Outreach updated"}


# ═══════════════════════════════════════════════════════════════
# AI MESSAGE GENERATION
# ═══════════════════════════════════════════════════════════════

@app.post("/api/generate-message")
async def generate_message(request: Request):
    """Generate a personalized outreach message using AI or templates."""
    data = await request.json()
    result = generate_ai_message(
        contact_name=data.get("contact_name", ""),
        company_name=data.get("company_name", ""),
        channel=data.get("channel", "email"),
        template_type=data.get("template_type", "first_email"),
        custom_context=data.get("custom_context", "")
    )
    return result


@app.get("/api/pitch-hooks")
async def get_pitch_hooks():
    """Get all agency-specific pitch hooks."""
    return AGENCY_PITCH_HOOKS


# ═══════════════════════════════════════════════════════════════
# EMAIL SENDING
# ═══════════════════════════════════════════════════════════════

@app.post("/api/send-email")
async def send_email_endpoint(request: Request):
    """Send an email via SMTP."""
    data = await request.json()
    result = send_email(
        to_email=data.get("to_email", ""),
        subject=data.get("subject", ""),
        body=data.get("body", ""),
        contact_id=data.get("contact_id"),
        contact_name=data.get("contact_name", ""),
        company_name=data.get("company_name", "")
    )
    return result


# ═══════════════════════════════════════════════════════════════
# FOLLOW-UPS
# ═══════════════════════════════════════════════════════════════

@app.get("/api/follow-ups")
async def list_follow_ups(status: str = Query("", description="Filter by status")):
    """List all scheduled follow-ups."""
    conn = get_db()
    query = "SELECT * FROM follow_up_queue WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY scheduled_date ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.post("/api/follow-ups/process")
async def process_follow_ups():
    """Process all pending follow-ups that are due today."""
    results = process_pending_follow_ups()
    return {"processed": len(results), "results": results}


@app.post("/api/schedule-followup")
async def schedule_followup_endpoint(request: Request):
    """Schedule follow-ups for a specific outreach."""
    data = await request.json()
    result = schedule_follow_ups(
        outreach_id=data.get("outreach_id", 0),
        contact_id=data.get("contact_id", 0),
        contact_name=data.get("contact_name", ""),
        company_name=data.get("company_name", "")
    )
    return {"scheduled": len(result), "follow_ups": result}


# ═══════════════════════════════════════════════════════════════
# MEETINGS
# ═══════════════════════════════════════════════════════════════

@app.get("/api/meetings")
async def list_meetings(status: str = Query("")):
    """List all meetings."""
    conn = get_db()
    query = "SELECT * FROM meetings WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY meeting_date ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.post("/api/meetings")
async def create_meeting(request: Request):
    """Book a new meeting."""
    data = await request.json()
    conn = get_db()

    cursor = conn.execute("""
        INSERT INTO meetings (contact_id, contact_name, company_name, lead_type,
            meeting_date, meeting_time, meeting_format, status, pre_meeting_brief, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("contact_id"), data.get("contact_name", ""), data.get("company_name", ""),
        data.get("lead_type", "agency"), data.get("meeting_date", ""),
        data.get("meeting_time", ""), data.get("meeting_format", "Zoom"),
        data.get("status", "confirmed"), data.get("pre_meeting_brief", ""),
        data.get("notes", "")
    ))

    conn.commit()
    meeting_id = cursor.lastrowid

    # Update contact pipeline stage
    if data.get("contact_id"):
        conn.execute(
            "UPDATE contacts SET pipeline_stage = 'meeting_booked', updated_at = datetime('now') WHERE id = ?",
            (data["contact_id"],)
        )
        conn.commit()

    conn.close()

    log_activity("meeting_booked", "meeting", meeting_id,
                 f"Meeting with {data.get('contact_name', '')} at {data.get('company_name', '')}")
    return {"id": meeting_id, "message": "Meeting booked successfully"}


@app.put("/api/meetings/{meeting_id}")
async def update_meeting(meeting_id: int, request: Request):
    """Update a meeting."""
    data = await request.json()
    conn = get_db()

    set_parts = []
    values = []
    for key, value in data.items():
        if key not in ("id", "created_at"):
            set_parts.append(f"{key} = ?")
            values.append(value)

    if set_parts:
        set_parts.append("updated_at = datetime('now')")
        values.append(meeting_id)
        conn.execute(f"UPDATE meetings SET {', '.join(set_parts)} WHERE id = ?", values)
        conn.commit()

    conn.close()
    log_activity("meeting_updated", "meeting", meeting_id, f"Status: {data.get('status', '')}")
    return {"message": "Meeting updated"}


@app.delete("/api/meetings/{meeting_id}")
async def delete_meeting(meeting_id: int):
    """Delete a meeting."""
    conn = get_db()
    conn.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
    conn.commit()
    conn.close()
    log_activity("meeting_deleted", "meeting", meeting_id)
    return {"message": "Meeting deleted"}


# ═══════════════════════════════════════════════════════════════
# TEMPLATES
# ═══════════════════════════════════════════════════════════════

@app.get("/api/templates")
async def list_templates(channel: str = Query("")):
    """List all email/message templates."""
    conn = get_db()
    query = "SELECT * FROM email_templates WHERE 1=1"
    params = []
    if channel:
        query += " AND channel = ?"
        params.append(channel)
    query += " ORDER BY channel, sequence_order"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.post("/api/templates")
async def create_template(request: Request):
    """Create a new template."""
    data = await request.json()
    conn = get_db()
    cursor = conn.execute("""
        INSERT INTO email_templates (name, category, subject, body, channel, sequence_order)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data.get("name", ""), data.get("category", "custom"),
        data.get("subject", ""), data.get("body", ""),
        data.get("channel", "email"), data.get("sequence_order", 0)
    ))
    conn.commit()
    conn.close()
    return {"id": cursor.lastrowid, "message": "Template created"}


@app.put("/api/templates/{template_id}")
async def update_template(template_id: int, request: Request):
    """Update a template."""
    data = await request.json()
    conn = get_db()
    set_parts = []
    values = []
    for key, value in data.items():
        if key not in ("id", "created_at"):
            set_parts.append(f"{key} = ?")
            values.append(value)
    if set_parts:
        values.append(template_id)
        conn.execute(f"UPDATE email_templates SET {', '.join(set_parts)} WHERE id = ?", values)
        conn.commit()
    conn.close()
    return {"message": "Template updated"}


@app.delete("/api/templates/{template_id}")
async def delete_template(template_id: int):
    """Delete a template."""
    conn = get_db()
    conn.execute("DELETE FROM email_templates WHERE id = ?", (template_id,))
    conn.commit()
    conn.close()
    return {"message": "Template deleted"}


# ═══════════════════════════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════════════════════════

@app.get("/api/settings")
async def get_settings():
    """Get all settings (masks sensitive values)."""
    settings = get_all_settings()
    # Mask sensitive keys
    masked = {}
    sensitive_keys = ["gemini_api_key", "smtp_password"]
    for key, value in settings.items():
        if key in sensitive_keys and value:
            masked[key] = value[:4] + "•" * (len(value) - 8) + value[-4:] if len(value) > 8 else "••••"
        else:
            masked[key] = value
    return masked


@app.post("/api/settings")
async def update_settings(request: Request):
    """Update settings (key-value pairs)."""
    data = await request.json()
    for key, value in data.items():
        # Don't overwrite with masked values
        if "•" not in str(value):
            set_setting(key, str(value))

    log_activity("settings_updated", "settings", details=f"Updated keys: {', '.join(data.keys())}")
    return {"message": "Settings updated successfully"}


# ═══════════════════════════════════════════════════════════════
# DATA EXPORT
# ═══════════════════════════════════════════════════════════════

@app.get("/api/export/{table_name}")
async def export_csv(table_name: str):
    """Export a table as CSV."""
    allowed = ["agencies", "clinics", "contacts", "outreach_log", "meetings"]
    if table_name not in allowed:
        raise HTTPException(status_code=400, detail=f"Cannot export '{table_name}'")

    conn = get_db()
    rows = conn.execute(f"SELECT * FROM {table_name}").fetchall()
    conn.close()

    if not rows:
        return {"message": "No data to export"}

    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(rows[0].keys())
    for row in rows:
        writer.writerow(dict(row).values())

    headers = {
        "Content-Disposition": f"attachment; filename={table_name}_{datetime.now().strftime('%Y%m%d')}.csv",
        "Content-Type": "text/csv",
    }
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers=headers
    )


# ═══════════════════════════════════════════════════════════════
# ACTIVITY LOG
# ═══════════════════════════════════════════════════════════════

@app.get("/api/activity")
async def get_activity_log(limit: int = Query(50)):
    """Get recent activity log."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM activity_log ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ═══════════════════════════════════════════════════════════════
# RUN SERVER
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    print("\n" + "=" * 60)
    print("  [*] LeadLift Marketing Automation System")
    print("  [>] Dashboard: http://localhost:8000")
    print("  [>] API Docs:  http://localhost:8000/docs")
    print("=" * 60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
