/* ═══════════════════════════════════════════════════════════════
   LeadLift Marketing Automation — Frontend Application Logic
   SPA Router, API Integration, Charts, Kanban, and UI Logic
   ═══════════════════════════════════════════════════════════════ */

const API = '';  // Same origin

// ── State ──
let dashboardData = {};
let leadsData = [];
let contactsData = [];
let outreachData = [];
let meetingsData = [];
let templatesData = [];
let followUpsData = [];
let currentPage = 'dashboard';

// ═══════════════════════════════════════════════════════════════
// INITIALIZATION
// ═══════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    // Route from hash
    const hash = window.location.hash.replace('#', '') || 'dashboard';
    navigateTo(hash, false);
    refreshDashboard();
});

window.addEventListener('hashchange', () => {
    const hash = window.location.hash.replace('#', '') || 'dashboard';
    navigateTo(hash, false);
});


// ═══════════════════════════════════════════════════════════════
// NAVIGATION / SPA ROUTER
// ═══════════════════════════════════════════════════════════════

function navigateTo(page, pushHash = true) {
    currentPage = page;

    // Hide all pages
    document.querySelectorAll('.page-view').forEach(p => p.classList.remove('active'));
    // Show target
    const target = document.getElementById('page-' + page);
    if (target) target.classList.add('active');

    // Update nav
    document.querySelectorAll('.nav-item').forEach(n => {
        n.classList.toggle('active', n.dataset.page === page);
    });

    if (pushHash) window.location.hash = page;

    // Load page data
    switch (page) {
        case 'dashboard': loadDashboard(); break;
        case 'pipeline': loadPipeline(); break;
        case 'leads': loadLeads(); break;
        case 'contacts': loadContacts(); break;
        case 'outreach': loadOutreach(); break;
        case 'meetings': loadMeetings(); break;
        case 'templates': loadTemplates(); break;
        case 'settings': loadSettings(); break;
    }
}


// ═══════════════════════════════════════════════════════════════
// API HELPER
// ═══════════════════════════════════════════════════════════════

async function api(endpoint, method = 'GET', body = null) {
    const opts = {
        method,
        headers: { 'Content-Type': 'application/json' },
    };
    if (body) opts.body = JSON.stringify(body);

    try {
        const res = await fetch(API + endpoint, opts);
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || res.statusText);
        }
        const ct = res.headers.get('content-type');
        if (ct && ct.includes('text/csv')) {
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            const disp = res.headers.get('content-disposition') || '';
            const match = disp.match(/filename=(.+)/);
            a.download = match ? match[1] : 'export.csv';
            a.click();
            URL.revokeObjectURL(url);
            return { success: true };
        }
        return await res.json();
    } catch (e) {
        console.error('API Error:', e);
        showToast(e.message || 'API request failed', 'error');
        throw e;
    }
}


// ═══════════════════════════════════════════════════════════════
// TOAST NOTIFICATIONS
// ═══════════════════════════════════════════════════════════════

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
        <span class="toast-message">${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">✕</button>
    `;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}


// ═══════════════════════════════════════════════════════════════
// MODAL
// ═══════════════════════════════════════════════════════════════

function openModal(title, bodyHtml, footerHtml = '', large = false) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').innerHTML = bodyHtml;
    document.getElementById('modal-footer').innerHTML = footerHtml;
    const modal = document.getElementById('modal');
    modal.classList.toggle('modal-lg', large);
    document.getElementById('modal-overlay').classList.add('active');
}

function closeModal() {
    document.getElementById('modal-overlay').classList.remove('active');
}

function closeModalBackdrop(e) {
    if (e.target === e.currentTarget) closeModal();
}


// ═══════════════════════════════════════════════════════════════
// DASHBOARD
// ═══════════════════════════════════════════════════════════════

async function refreshDashboard() {
    await loadDashboard();
    showToast('Dashboard refreshed', 'success');
}

async function loadDashboard() {
    try {
        dashboardData = await api('/api/dashboard');
    } catch { return; }

    // KPI Values
    setText('kpi-agencies', dashboardData.total_agencies || 0);
    setText('kpi-contacts', dashboardData.total_contacts || 0);
    setText('kpi-outreach', dashboardData.outreach_sent || 0);
    setText('kpi-response', (dashboardData.response_rate || 0) + '%');
    setText('kpi-meetings', dashboardData.meetings_booked || 0);
    setText('kpi-days', dashboardData.days_remaining ?? '—');
    setText('deadline-days', dashboardData.days_remaining ?? '—');

    // Nav badges
    setText('nav-badge-leads', dashboardData.total_agencies || 0);
    setText('nav-badge-contacts', dashboardData.total_contacts || 0);
    setText('nav-badge-meetings', dashboardData.meetings_booked || 0);

    // Progress bar
    const booked = dashboardData.meetings_booked || 0;
    setText('progress-booked', booked);
    const pct = Math.min(100, (booked / 8) * 100);
    const fill = document.getElementById('progress-fill');
    fill.style.width = pct + '%';
    fill.className = 'progress-bar-fill' + (pct >= 100 ? ' success' : pct >= 50 ? '' : ' warning');

    // Pipeline funnel
    renderFunnel(dashboardData.pipeline || {});

    // Activity feed
    renderActivityFeed(dashboardData.recent_activity || []);
}

function renderFunnel(pipeline) {
    const container = document.getElementById('funnel-chart');
    const stages = [
        { label: 'Researched', key: 'research', color: 'var(--gradient-primary)' },
        { label: 'Enriched', key: 'enriched', color: 'var(--gradient-info)' },
        { label: 'Contacted', key: 'contacted', color: 'var(--gradient-warning)' },
        { label: 'Responded', key: 'responded', color: 'var(--gradient-success)' },
        { label: 'Meeting Booked', key: 'meeting_booked', color: 'var(--gradient-secondary)' },
        { label: 'Partner Signed', key: 'partner_signed', color: 'var(--gradient-danger)' },
    ];

    const max = Math.max(1, ...stages.map(s => pipeline[s.key] || 0));

    container.innerHTML = stages.map(s => {
        const count = pipeline[s.key] || 0;
        const width = Math.max(8, (count / max) * 100);
        return `
            <div class="funnel-stage">
                <span class="funnel-label">${s.label}</span>
                <div class="funnel-bar" style="width: ${width}%; background: ${s.color};">${count}</div>
            </div>
        `;
    }).join('');
}

function renderActivityFeed(activities) {
    const container = document.getElementById('activity-feed');
    if (!activities.length) {
        container.innerHTML = `
            <div class="empty-state" style="padding: var(--space-xl);">
                <div class="empty-icon">📭</div>
                <p>No activity yet. Start outreach to see updates here.</p>
            </div>`;
        return;
    }

    const icons = {
        csv_import: '📦', seed_templates: '📝', lead_created: '🏢', contact_created: '👤',
        outreach_logged: '✉️', email_sent: '📤', email_failed: '❌', meeting_booked: '📅',
        settings_updated: '⚙️', follow_ups_scheduled: '🔔',
    };

    container.innerHTML = activities.slice(0, 10).map(a => `
        <div class="activity-item">
            <div class="activity-icon">${icons[a.action] || '📌'}</div>
            <div class="activity-content">
                <div class="activity-text"><strong>${formatAction(a.action)}</strong> ${a.details || ''}</div>
                <div class="activity-time">${timeAgo(a.created_at)}</div>
            </div>
        </div>
    `).join('');
}

function formatAction(action) {
    return action.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function timeAgo(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr + 'Z');
    const diff = (Date.now() - d.getTime()) / 1000;
    if (diff < 60) return 'Just now';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
    return Math.floor(diff / 86400) + 'd ago';
}


// ═══════════════════════════════════════════════════════════════
// PIPELINE (KANBAN)
// ═══════════════════════════════════════════════════════════════

async function loadPipeline() {
    try {
        contactsData = await api('/api/contacts');
    } catch { return; }

    const stages = [
        { id: 'enriched', title: '📋 Enriched', color: 'var(--accent-info)' },
        { id: 'contacted', title: '✉️ Contacted', color: 'var(--accent-warning)' },
        { id: 'responded', title: '💬 Responded', color: 'var(--accent-success)' },
        { id: 'meeting_booked', title: '📅 Meeting', color: 'var(--accent-secondary)' },
        { id: 'partner_signed', title: '🤝 Signed', color: 'var(--accent-danger)' },
    ];

    const board = document.getElementById('kanban-board');
    board.innerHTML = stages.map(stage => {
        const cards = contactsData.filter(c => c.pipeline_stage === stage.id);
        return `
            <div class="kanban-column" data-stage="${stage.id}"
                 ondragover="onDragOver(event)" ondrop="onDrop(event, '${stage.id}')">
                <div class="kanban-column-header">
                    <span class="kanban-column-title">
                        ${stage.title}
                        <span class="kanban-column-count">${cards.length}</span>
                    </span>
                </div>
                <div class="kanban-column-body">
                    ${cards.map(c => renderKanbanCard(c)).join('')}
                    ${cards.length === 0 ? '<div style="text-align:center;padding:var(--space-xl);color:var(--text-muted);font-size:0.75rem;">Drop cards here</div>' : ''}
                </div>
            </div>
        `;
    }).join('');
}

function renderKanbanCard(contact) {
    const scoreClass = contact.confidence_score >= 8 ? 'score-high' : contact.confidence_score >= 6 ? 'score-mid' : 'score-low';
    return `
        <div class="kanban-card" draggable="true"
             ondragstart="onDragStart(event, ${contact.id})"
             data-contact-id="${contact.id}">
            <div class="kanban-card-title">${esc(contact.name)}</div>
            <div class="kanban-card-company">${esc(contact.company)} — ${esc(contact.title)}</div>
            <div class="kanban-card-meta">
                <span class="score-badge ${scoreClass}">${contact.confidence_score}</span>
                ${contact.email ? '<span class="badge badge-success">📧</span>' : ''}
                ${contact.linkedin_url ? '<span class="badge badge-info">💼</span>' : ''}
            </div>
        </div>
    `;
}

// Drag & Drop
function onDragStart(e, contactId) {
    e.dataTransfer.setData('text/plain', contactId);
    e.target.classList.add('dragging');
}

function onDragOver(e) {
    e.preventDefault();
}

async function onDrop(e, newStage) {
    e.preventDefault();
    const contactId = parseInt(e.dataTransfer.getData('text/plain'));
    document.querySelectorAll('.kanban-card.dragging').forEach(c => c.classList.remove('dragging'));

    try {
        await api(`/api/contacts/${contactId}`, 'PUT', { pipeline_stage: newStage });
        showToast('Contact moved to ' + newStage.replace('_', ' '), 'success');
        loadPipeline();
    } catch (err) {
        showToast('Failed to update stage', 'error');
    }
}


// ═══════════════════════════════════════════════════════════════
// LEADS
// ═══════════════════════════════════════════════════════════════

async function loadLeads() {
    const search = document.getElementById('leads-search')?.value || '';
    const minScore = parseInt(document.getElementById('leads-score-filter')?.value || '0');

    try {
        leadsData = await api(`/api/leads?search=${encodeURIComponent(search)}&min_score=${minScore}`);
    } catch { return; }

    renderLeadsTable();
}

function searchLeads() {
    loadLeads();
}

function renderLeadsTable() {
    const tbody = document.getElementById('leads-tbody');
    if (!leadsData.length) {
        tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><div class="empty-icon">🏢</div><h3>No agencies found</h3><p>Adjust your filters or add new leads.</p></div></td></tr>`;
        return;
    }

    tbody.innerHTML = leadsData.map(a => {
        const scoreClass = a.partnership_score >= 9 ? 'score-high' : a.partnership_score >= 7 ? 'score-mid' : 'score-low';
        const stageColors = { research: 'badge-neutral', enriched: 'badge-info', contacted: 'badge-warning', responded: 'badge-success', meeting_booked: 'badge-secondary', partner_signed: 'badge-danger' };
        return `
            <tr>
                <td>
                    <span class="table-cell-name">${esc(a.name)}</span>
                    ${a.website ? `<br><a class="table-cell-link" href="${esc(a.website)}" target="_blank">${esc(a.website)}</a>` : ''}
                </td>
                <td>${esc(a.city || '')}${a.city && a.state ? ', ' : ''}${esc(a.state || '')}</td>
                <td style="max-width:200px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${esc(a.services || '')}">${esc(a.services || '—')}</td>
                <td><span class="score-badge ${scoreClass}">${a.partnership_score}</span></td>
                <td><span class="badge ${stageColors[a.pipeline_stage] || 'badge-neutral'}">${esc(a.pipeline_stage || 'research')}</span></td>
                <td>${a.general_email ? `<a href="mailto:${esc(a.general_email)}" class="table-cell-link">${esc(a.general_email)}</a>` : '<span style="color:var(--text-muted);">—</span>'}</td>
                <td>
                    <div style="display:flex; gap:4px;">
                        <button class="btn btn-sm btn-ghost" onclick="viewLead(${a.id})" title="View">👁️</button>
                        <button class="btn btn-sm btn-ghost" onclick="composeForAgency('${esc(a.name)}')" title="Compose outreach">✉️</button>
                        <button class="btn btn-sm btn-danger" onclick="deleteLead(${a.id})" title="Delete">🗑️</button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function openAddLeadModal() {
    openModal('Add New Lead', `
        <div class="form-group">
            <label class="form-label">Agency Name *</label>
            <input type="text" class="form-input" id="new-lead-name" placeholder="Agency name">
        </div>
        <div class="settings-grid">
            <div class="form-group">
                <label class="form-label">Website</label>
                <input type="url" class="form-input" id="new-lead-website" placeholder="https://...">
            </div>
            <div class="form-group">
                <label class="form-label">Email</label>
                <input type="email" class="form-input" id="new-lead-email" placeholder="info@agency.com">
            </div>
        </div>
        <div class="settings-grid">
            <div class="form-group">
                <label class="form-label">City</label>
                <input type="text" class="form-input" id="new-lead-city">
            </div>
            <div class="form-group">
                <label class="form-label">State</label>
                <input type="text" class="form-input" id="new-lead-state">
            </div>
        </div>
        <div class="form-group">
            <label class="form-label">Services</label>
            <input type="text" class="form-input" id="new-lead-services" placeholder="SEO, Web Design, PPC...">
        </div>
        <div class="form-group">
            <label class="form-label">Partnership Score (1-10)</label>
            <input type="number" class="form-input" id="new-lead-score" min="1" max="10" value="5">
        </div>
        <div class="form-group">
            <label class="form-label">Notes</label>
            <textarea class="form-textarea" id="new-lead-notes" rows="2"></textarea>
        </div>
    `, `
        <button class="btn" onclick="closeModal()">Cancel</button>
        <button class="btn btn-primary" onclick="saveNewLead()">Save Lead</button>
    `);
}

async function saveNewLead() {
    const name = document.getElementById('new-lead-name').value.trim();
    if (!name) { showToast('Agency name is required', 'warning'); return; }

    try {
        await api('/api/leads', 'POST', {
            lead_type: 'agency',
            name,
            website: document.getElementById('new-lead-website').value.trim(),
            general_email: document.getElementById('new-lead-email').value.trim(),
            city: document.getElementById('new-lead-city').value.trim(),
            state: document.getElementById('new-lead-state').value.trim(),
            services: document.getElementById('new-lead-services').value.trim(),
            partnership_score: parseInt(document.getElementById('new-lead-score').value) || 5,
            notes: document.getElementById('new-lead-notes').value.trim(),
        });
        closeModal();
        showToast('Lead added successfully!', 'success');
        loadLeads();
    } catch {}
}

function viewLead(id) {
    const lead = leadsData.find(l => l.id === id);
    if (!lead) return;

    openModal(lead.name, `
        <div class="settings-grid" style="margin-bottom: var(--space-md);">
            <div><strong style="color:var(--text-muted);font-size:0.7rem;">WEBSITE</strong><br>
                ${lead.website ? `<a href="${esc(lead.website)}" target="_blank">${esc(lead.website)}</a>` : '—'}</div>
            <div><strong style="color:var(--text-muted);font-size:0.7rem;">LOCATION</strong><br>
                ${esc(lead.city || '')}${lead.city && lead.state ? ', ' : ''}${esc(lead.state || '')}</div>
            <div><strong style="color:var(--text-muted);font-size:0.7rem;">SCORE</strong><br>
                <span class="score-badge ${lead.partnership_score >= 9 ? 'score-high' : lead.partnership_score >= 7 ? 'score-mid' : 'score-low'}">${lead.partnership_score}</span></div>
            <div><strong style="color:var(--text-muted);font-size:0.7rem;">EMAIL</strong><br>
                ${lead.general_email || '—'}</div>
        </div>
        <div style="margin-bottom: var(--space-md);">
            <strong style="color:var(--text-muted);font-size:0.7rem;">SERVICES</strong><br>
            <span style="font-size:0.85rem;">${esc(lead.services || '—')}</span>
        </div>
        <div style="margin-bottom: var(--space-md);">
            <strong style="color:var(--text-muted);font-size:0.7rem;">NOTABLE CLIENTS</strong><br>
            <span style="font-size:0.85rem;">${esc(lead.notable_clients || '—')}</span>
        </div>
        <div>
            <strong style="color:var(--text-muted);font-size:0.7rem;">PHONE</strong><br>
            <span style="font-size:0.85rem;">${esc(lead.phone || '—')}</span>
        </div>
    `, `
        <button class="btn" onclick="closeModal()">Close</button>
        <button class="btn btn-primary" onclick="closeModal(); composeForAgency('${esc(lead.name)}')">✉️ Compose Outreach</button>
    `, true);
}

async function deleteLead(id) {
    if (!confirm('Delete this lead?')) return;
    try {
        await api(`/api/leads/${id}?lead_type=agency`, 'DELETE');
        showToast('Lead deleted', 'info');
        loadLeads();
    } catch {}
}


// ═══════════════════════════════════════════════════════════════
// CONTACTS
// ═══════════════════════════════════════════════════════════════

async function loadContacts() {
    const search = document.getElementById('contacts-search')?.value || '';
    try {
        contactsData = await api(`/api/contacts?search=${encodeURIComponent(search)}`);
    } catch { return; }
    renderContactsTable();
    populateComposeContacts();
}

function searchContacts() { loadContacts(); }

function renderContactsTable() {
    const tbody = document.getElementById('contacts-tbody');
    if (!contactsData.length) {
        tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><div class="empty-icon">👤</div><h3>No contacts yet</h3></div></td></tr>`;
        return;
    }

    tbody.innerHTML = contactsData.map(c => {
        const scoreClass = c.confidence_score >= 8 ? 'score-high' : c.confidence_score >= 6 ? 'score-mid' : 'score-low';
        return `
            <tr>
                <td class="table-cell-name">${esc(c.name)}</td>
                <td>${esc(c.title || '—')}</td>
                <td>${esc(c.company || '—')}</td>
                <td>${c.email ? `<a href="mailto:${esc(c.email)}" class="table-cell-link">${esc(c.email)}</a>` : '<span style="color:var(--text-muted);">—</span>'}</td>
                <td>${c.linkedin_url ? `<a href="${esc(c.linkedin_url)}" target="_blank" class="table-cell-link">View Profile</a>` : '—'}</td>
                <td><span class="score-badge ${scoreClass}">${c.confidence_score}</span></td>
                <td>
                    <div style="display:flex; gap:4px;">
                        <button class="btn btn-sm btn-ghost" onclick="composeForContact(${c.id})" title="Compose">✉️</button>
                        <button class="btn btn-sm btn-danger" onclick="deleteContact(${c.id})" title="Delete">🗑️</button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function openAddContactModal() {
    openModal('Add New Contact', `
        <div class="settings-grid">
            <div class="form-group">
                <label class="form-label">Name *</label>
                <input type="text" class="form-input" id="new-contact-name" placeholder="Full name">
            </div>
            <div class="form-group">
                <label class="form-label">Title</label>
                <input type="text" class="form-input" id="new-contact-title" placeholder="CEO, Founder...">
            </div>
        </div>
        <div class="form-group">
            <label class="form-label">Company</label>
            <input type="text" class="form-input" id="new-contact-company" placeholder="Agency name">
        </div>
        <div class="settings-grid">
            <div class="form-group">
                <label class="form-label">Email</label>
                <input type="email" class="form-input" id="new-contact-email">
            </div>
            <div class="form-group">
                <label class="form-label">LinkedIn URL</label>
                <input type="url" class="form-input" id="new-contact-linkedin">
            </div>
        </div>
        <div class="form-group">
            <label class="form-label">Confidence Score (1-10)</label>
            <input type="number" class="form-input" id="new-contact-score" min="1" max="10" value="7">
        </div>
    `, `
        <button class="btn" onclick="closeModal()">Cancel</button>
        <button class="btn btn-primary" onclick="saveNewContact()">Save Contact</button>
    `);
}

async function saveNewContact() {
    const name = document.getElementById('new-contact-name').value.trim();
    if (!name) { showToast('Name is required', 'warning'); return; }
    try {
        await api('/api/contacts', 'POST', {
            name,
            title: document.getElementById('new-contact-title').value.trim(),
            company: document.getElementById('new-contact-company').value.trim(),
            email: document.getElementById('new-contact-email').value.trim(),
            linkedin_url: document.getElementById('new-contact-linkedin').value.trim(),
            confidence_score: parseInt(document.getElementById('new-contact-score').value) || 7,
        });
        closeModal();
        showToast('Contact added!', 'success');
        loadContacts();
    } catch {}
}

async function deleteContact(id) {
    if (!confirm('Delete this contact?')) return;
    try {
        await api(`/api/contacts/${id}`, 'DELETE');
        showToast('Contact deleted', 'info');
        loadContacts();
    } catch {}
}


// ═══════════════════════════════════════════════════════════════
// OUTREACH CENTER
// ═══════════════════════════════════════════════════════════════

async function loadOutreach() {
    try {
        [contactsData, outreachData, followUpsData] = await Promise.all([
            api('/api/contacts'),
            api('/api/outreach'),
            api('/api/follow-ups'),
        ]);
    } catch { return; }

    populateComposeContacts();
    renderOutreachLog();
    renderFollowUps();
}

function populateComposeContacts() {
    const select = document.getElementById('compose-contact');
    if (!select) return;

    const currentVal = select.value;
    const opts = contactsData.map(c =>
        `<option value="${c.id}" data-name="${esc(c.name)}" data-company="${esc(c.company)}" data-email="${esc(c.email || '')}">${esc(c.name)} — ${esc(c.company)}</option>`
    ).join('');
    select.innerHTML = '<option value="">Select a contact...</option>' + opts;
    if (currentVal) select.value = currentVal;
}

function onComposeContactChange() {
    // Pre-fill channel based on contact info
}

function switchOutreachTab(tab) {
    document.querySelectorAll('#page-outreach .tab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');

    document.getElementById('outreach-tab-compose').style.display = tab === 'compose' ? '' : 'none';
    document.getElementById('outreach-tab-log').style.display = tab === 'log' ? '' : 'none';
    document.getElementById('outreach-tab-followups').style.display = tab === 'followups' ? '' : 'none';
}

// Generate AI message
async function generateMessage() {
    const select = document.getElementById('compose-contact');
    const opt = select.selectedOptions[0];
    if (!select.value) { showToast('Select a contact first', 'warning'); return; }

    const contactName = opt.dataset.name;
    const companyName = opt.dataset.company;
    const channel = document.getElementById('compose-channel').value;
    const templateType = document.getElementById('compose-type').value;
    const customContext = document.getElementById('compose-context').value;

    // Show loading
    document.getElementById('compose-body').innerHTML = '<div style="text-align:center;padding:var(--space-xl);"><div class="loading-shimmer" style="height:20px;width:60%;margin:0 auto var(--space-md);border-radius:4px;"></div><div class="loading-shimmer" style="height:14px;width:80%;margin:0 auto var(--space-sm);border-radius:4px;"></div><div class="loading-shimmer" style="height:14px;width:70%;margin:0 auto var(--space-sm);border-radius:4px;"></div><div class="loading-shimmer" style="height:14px;width:75%;margin:0 auto;border-radius:4px;"></div><p style="color:var(--text-muted);margin-top:var(--space-md);font-size:0.8rem;">✨ Generating personalized message...</p></div>';

    try {
        const result = await api('/api/generate-message', 'POST', {
            contact_name: contactName,
            company_name: companyName,
            channel,
            template_type: templateType,
            custom_context: customContext,
        });

        if (result.subject) {
            document.getElementById('compose-subject').style.display = '';
            document.getElementById('compose-subject-text').textContent = result.subject;
        } else {
            document.getElementById('compose-subject').style.display = 'none';
        }

        document.getElementById('compose-body').textContent = result.body;

        const genLabel = result.generated_by === 'gemini' ? '🤖 AI Generated' : '📝 From Template';
        showToast(`Message generated (${genLabel})`, 'success');

    } catch {
        document.getElementById('compose-body').innerHTML = '<div class="empty-state"><div class="empty-icon">❌</div><h3>Generation failed</h3><p>Check your Gemini API key in Settings, or try again.</p></div>';
    }
}

async function loadTemplate() {
    const channel = document.getElementById('compose-channel').value;
    const select = document.getElementById('compose-contact');
    const opt = select.selectedOptions[0];
    const contactName = opt?.dataset?.name || '{first_name}';
    const companyName = opt?.dataset?.company || '{agency_name}';

    try {
        const result = await api('/api/generate-message', 'POST', {
            contact_name: contactName,
            company_name: companyName,
            channel,
            template_type: document.getElementById('compose-type').value,
        });

        if (result.subject) {
            document.getElementById('compose-subject').style.display = '';
            document.getElementById('compose-subject-text').textContent = result.subject;
        }
        document.getElementById('compose-body').textContent = result.body;
        showToast('Template loaded', 'info');
    } catch {}
}

function copyMessage() {
    const body = document.getElementById('compose-body').textContent;
    const subject = document.getElementById('compose-subject-text')?.textContent || '';
    const full = subject ? `Subject: ${subject}\n\n${body}` : body;

    navigator.clipboard.writeText(full).then(() => {
        showToast('Message copied to clipboard!', 'success');
    }).catch(() => {
        showToast('Copy failed — select and copy manually', 'warning');
    });
}

async function sendMessage() {
    const select = document.getElementById('compose-contact');
    const opt = select.selectedOptions[0];
    if (!select.value) { showToast('Select a contact first', 'warning'); return; }

    const contactId = parseInt(select.value);
    const contactName = opt.dataset.name;
    const companyName = opt.dataset.company;
    const email = opt.dataset.email;
    const channel = document.getElementById('compose-channel').value;
    const subject = document.getElementById('compose-subject-text')?.textContent || '';
    const body = document.getElementById('compose-body').textContent;

    if (!body || body.includes('Ready to compose')) {
        showToast('Generate a message first', 'warning');
        return;
    }

    if (channel === 'email' && email) {
        // Try to send via SMTP
        try {
            const result = await api('/api/send-email', 'POST', {
                to_email: email,
                subject,
                body,
                contact_id: contactId,
                contact_name: contactName,
                company_name: companyName,
            });

            if (result.success) {
                showToast('Email sent successfully!', 'success');
                // Schedule follow-ups
                await api('/api/outreach', 'POST', {
                    contact_id: contactId,
                    contact_name: contactName,
                    company_name: companyName,
                    channel: 'email',
                    message_subject: subject,
                    message_body: body,
                    status: 'sent',
                    auto_follow_up: true,
                });
            } else {
                // Log as manual
                await logManualOutreach(contactId, contactName, companyName, channel, subject, body);
                showToast(result.error || 'SMTP not configured — logged as manual outreach', 'warning');
            }
        } catch {
            await logManualOutreach(contactId, contactName, companyName, channel, subject, body);
        }
    } else {
        // Log as manual (LinkedIn or no email)
        await logManualOutreach(contactId, contactName, companyName, channel, subject, body);
        showToast(`Outreach logged as ${channel}. Copy the message and send manually.`, 'info');
    }

    loadOutreach();
}

async function logManualOutreach(contactId, contactName, companyName, channel, subject, body) {
    try {
        await api('/api/outreach', 'POST', {
            contact_id: contactId,
            contact_name: contactName,
            company_name: companyName,
            channel,
            message_subject: subject,
            message_body: body,
            status: 'sent',
            auto_follow_up: channel === 'email',
        });
    } catch {}
}

function composeForAgency(agencyName) {
    navigateTo('outreach');
    setTimeout(() => {
        const select = document.getElementById('compose-contact');
        if (!select) return;
        for (const opt of select.options) {
            if (opt.dataset.company === agencyName) {
                select.value = opt.value;
                break;
            }
        }
    }, 300);
}

function composeForContact(contactId) {
    navigateTo('outreach');
    setTimeout(() => {
        const select = document.getElementById('compose-contact');
        if (select) select.value = contactId;
    }, 300);
}

function renderOutreachLog() {
    const tbody = document.getElementById('outreach-tbody');
    if (!outreachData.length) {
        tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><div class="empty-icon">📭</div><h3>No outreach yet</h3><p>Compose and send your first message!</p></div></td></tr>`;
        return;
    }

    tbody.innerHTML = outreachData.map(o => {
        const statusColors = { draft: 'badge-neutral', sent: 'badge-warning', opened: 'badge-info', replied: 'badge-success', no_response: 'badge-danger' };
        const channelIcons = { email: '📧', linkedin: '💼', phone: '📞', form: '📋' };
        return `
            <tr>
                <td class="table-cell-name">${esc(o.contact_name || '—')}</td>
                <td>${esc(o.company_name || '—')}</td>
                <td>${channelIcons[o.channel] || '📧'} ${esc(o.channel)}</td>
                <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${esc(o.message_subject || '')}">${esc(o.message_subject || '—')}</td>
                <td style="font-size:0.75rem;color:var(--text-muted);">${o.sent_date ? new Date(o.sent_date).toLocaleDateString() : '—'}</td>
                <td><span class="badge ${statusColors[o.status] || 'badge-neutral'}">${esc(o.status)}</span></td>
                <td>
                    <div style="display:flex; gap:4px;">
                        <button class="btn btn-sm btn-ghost" onclick="markOutreach(${o.id}, 'replied')" title="Mark replied">💬</button>
                        <button class="btn btn-sm btn-ghost" onclick="markOutreach(${o.id}, 'opened')" title="Mark opened">👁️</button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

async function markOutreach(id, status) {
    try {
        await api(`/api/outreach/${id}`, 'PUT', { status });
        showToast(`Marked as ${status}`, 'success');
        loadOutreach();
    } catch {}
}

function renderFollowUps() {
    const tbody = document.getElementById('followups-tbody');
    if (!followUpsData.length) {
        tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><div class="empty-icon">🔔</div><h3>No follow-ups scheduled</h3><p>Follow-ups are auto-scheduled when you send emails.</p></div></td></tr>`;
        return;
    }

    tbody.innerHTML = followUpsData.map(f => {
        const statusColors = { pending: 'badge-warning', sent: 'badge-success', ready: 'badge-info', failed: 'badge-danger', skipped: 'badge-neutral', no_email: 'badge-neutral' };
        return `
            <tr>
                <td class="table-cell-name">${esc(f.contact_name || '—')}</td>
                <td>${esc(f.company_name || '—')}</td>
                <td>#${f.follow_up_number}</td>
                <td style="font-size:0.82rem;">${f.scheduled_date || '—'}</td>
                <td><span class="badge ${statusColors[f.status] || 'badge-neutral'}">${esc(f.status)}</span></td>
            </tr>
        `;
    }).join('');
}

async function processFollowUps() {
    try {
        const result = await api('/api/follow-ups/process', 'POST');
        showToast(`Processed ${result.processed} follow-ups`, 'success');
        loadOutreach();
    } catch {}
}


// ═══════════════════════════════════════════════════════════════
// MEETINGS
// ═══════════════════════════════════════════════════════════════

async function loadMeetings() {
    try {
        meetingsData = await api('/api/meetings');
    } catch { return; }
    renderMeetingsTable();
}

function renderMeetingsTable() {
    const tbody = document.getElementById('meetings-tbody');
    if (!meetingsData.length) {
        tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><div class="empty-icon">📅</div><h3>No meetings booked yet</h3><p>Book your first meeting to start tracking.</p></div></td></tr>`;
        return;
    }

    tbody.innerHTML = meetingsData.map(m => {
        const statusColors = { confirmed: 'badge-success', rescheduled: 'badge-warning', completed: 'badge-primary', no_show: 'badge-danger', cancelled: 'badge-neutral' };
        return `
            <tr>
                <td class="table-cell-name">${esc(m.contact_name || '—')}</td>
                <td>${esc(m.company_name || '—')}</td>
                <td>${m.meeting_date || '—'}</td>
                <td>${m.meeting_time || '—'}</td>
                <td><span class="badge badge-info">${esc(m.meeting_format || 'Zoom')}</span></td>
                <td><span class="badge ${statusColors[m.status] || 'badge-neutral'}">${esc(m.status)}</span></td>
                <td>
                    <div style="display:flex; gap:4px;">
                        <button class="btn btn-sm btn-success" onclick="updateMeetingStatus(${m.id}, 'completed')" title="Mark completed">✅</button>
                        <button class="btn btn-sm btn-danger" onclick="updateMeetingStatus(${m.id}, 'no_show')" title="No show">❌</button>
                        <button class="btn btn-sm btn-ghost" onclick="deleteMeeting(${m.id})" title="Delete">🗑️</button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function openAddMeetingModal() {
    // Load contacts for dropdown
    const contactOpts = contactsData.map(c =>
        `<option value="${c.id}" data-name="${esc(c.name)}" data-company="${esc(c.company)}">${esc(c.name)} — ${esc(c.company)}</option>`
    ).join('');

    openModal('Book a Meeting', `
        <div class="form-group">
            <label class="form-label">Contact</label>
            <select class="form-select" id="new-meeting-contact">
                <option value="">Select contact...</option>
                ${contactOpts}
            </select>
        </div>
        <div class="settings-grid">
            <div class="form-group">
                <label class="form-label">Date</label>
                <input type="date" class="form-input" id="new-meeting-date">
            </div>
            <div class="form-group">
                <label class="form-label">Time</label>
                <input type="time" class="form-input" id="new-meeting-time">
            </div>
        </div>
        <div class="form-group">
            <label class="form-label">Format</label>
            <select class="form-select" id="new-meeting-format">
                <option value="Zoom">🖥️ Zoom</option>
                <option value="Phone">📞 Phone</option>
                <option value="Google Meet">📹 Google Meet</option>
                <option value="In-Person">🤝 In-Person</option>
            </select>
        </div>
        <div class="form-group">
            <label class="form-label">Pre-Meeting Brief</label>
            <textarea class="form-textarea" id="new-meeting-brief" rows="3" placeholder="Key talking points, pitch hooks..."></textarea>
        </div>
    `, `
        <button class="btn" onclick="closeModal()">Cancel</button>
        <button class="btn btn-primary" onclick="saveNewMeeting()">Book Meeting</button>
    `);
}

async function saveNewMeeting() {
    const select = document.getElementById('new-meeting-contact');
    const opt = select.selectedOptions[0];
    if (!select.value) { showToast('Select a contact', 'warning'); return; }

    try {
        await api('/api/meetings', 'POST', {
            contact_id: parseInt(select.value),
            contact_name: opt.dataset.name,
            company_name: opt.dataset.company,
            meeting_date: document.getElementById('new-meeting-date').value,
            meeting_time: document.getElementById('new-meeting-time').value,
            meeting_format: document.getElementById('new-meeting-format').value,
            pre_meeting_brief: document.getElementById('new-meeting-brief').value,
        });
        closeModal();
        showToast('Meeting booked! 🎉', 'success');
        loadMeetings();
    } catch {}
}

async function updateMeetingStatus(id, status) {
    try {
        await api(`/api/meetings/${id}`, 'PUT', { status });
        showToast(`Meeting marked as ${status}`, 'success');
        loadMeetings();
    } catch {}
}

async function deleteMeeting(id) {
    if (!confirm('Delete this meeting?')) return;
    try {
        await api(`/api/meetings/${id}`, 'DELETE');
        showToast('Meeting deleted', 'info');
        loadMeetings();
    } catch {}
}


// ═══════════════════════════════════════════════════════════════
// TEMPLATES
// ═══════════════════════════════════════════════════════════════

async function loadTemplates() {
    try {
        templatesData = await api('/api/templates');
    } catch { return; }
    renderTemplates();
}

function filterTemplates(channel) {
    document.querySelectorAll('#template-tabs .tab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
    renderTemplates(channel);
}

function renderTemplates(filterChannel = 'all') {
    const container = document.getElementById('templates-list');
    const filtered = filterChannel === 'all' ? templatesData : templatesData.filter(t => t.channel === filterChannel);

    if (!filtered.length) {
        container.innerHTML = `<div class="empty-state"><div class="empty-icon">📝</div><h3>No templates</h3></div>`;
        return;
    }

    container.innerHTML = filtered.map(t => `
        <div class="card" style="margin-bottom: var(--space-md);">
            <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom: var(--space-sm);">
                <div>
                    <span style="font-weight:600; font-size:0.9rem;">${esc(t.name)}</span>
                    <span class="badge ${t.channel === 'email' ? 'badge-primary' : 'badge-info'}" style="margin-left:8px;">${t.channel === 'email' ? '📧 Email' : '💼 LinkedIn'}</span>
                    ${t.sequence_order ? `<span class="badge badge-neutral" style="margin-left:4px;">Step ${t.sequence_order}</span>` : ''}
                </div>
                <button class="btn btn-sm btn-danger" onclick="deleteTemplate(${t.id})">🗑️</button>
            </div>
            ${t.subject ? `<div style="font-size:0.8rem;color:var(--accent-primary);margin-bottom:var(--space-sm);"><strong>Subject:</strong> ${esc(t.subject)}</div>` : ''}
            <pre style="font-size:0.78rem;color:var(--text-secondary);white-space:pre-wrap;word-wrap:break-word;background:var(--bg-tertiary);padding:var(--space-md);border-radius:var(--radius-md);max-height:200px;overflow-y:auto;">${esc(t.body)}</pre>
        </div>
    `).join('');
}

function openAddTemplateModal() {
    openModal('Create Template', `
        <div class="form-group">
            <label class="form-label">Template Name *</label>
            <input type="text" class="form-input" id="new-tpl-name" placeholder="e.g. Cold Email — Tech Agency">
        </div>
        <div class="settings-grid">
            <div class="form-group">
                <label class="form-label">Channel</label>
                <select class="form-select" id="new-tpl-channel">
                    <option value="email">📧 Email</option>
                    <option value="linkedin">💼 LinkedIn</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Sequence Order</label>
                <input type="number" class="form-input" id="new-tpl-order" value="1" min="0">
            </div>
        </div>
        <div class="form-group">
            <label class="form-label">Subject Line (email only)</label>
            <input type="text" class="form-input" id="new-tpl-subject" placeholder="Use {agency_name}, {first_name} as placeholders">
        </div>
        <div class="form-group">
            <label class="form-label">Message Body *</label>
            <textarea class="form-textarea" id="new-tpl-body" rows="8" placeholder="Use placeholders: {first_name}, {agency_name}, {your_name}, {calendly_link}"></textarea>
        </div>
    `, `
        <button class="btn" onclick="closeModal()">Cancel</button>
        <button class="btn btn-primary" onclick="saveNewTemplate()">Save Template</button>
    `, true);
}

async function saveNewTemplate() {
    const name = document.getElementById('new-tpl-name').value.trim();
    const body = document.getElementById('new-tpl-body').value.trim();
    if (!name || !body) { showToast('Name and body are required', 'warning'); return; }

    try {
        await api('/api/templates', 'POST', {
            name,
            channel: document.getElementById('new-tpl-channel').value,
            subject: document.getElementById('new-tpl-subject').value.trim(),
            body,
            sequence_order: parseInt(document.getElementById('new-tpl-order').value) || 0,
        });
        closeModal();
        showToast('Template created!', 'success');
        loadTemplates();
    } catch {}
}

async function deleteTemplate(id) {
    if (!confirm('Delete this template?')) return;
    try {
        await api(`/api/templates/${id}`, 'DELETE');
        showToast('Template deleted', 'info');
        loadTemplates();
    } catch {}
}


// ═══════════════════════════════════════════════════════════════
// SETTINGS
// ═══════════════════════════════════════════════════════════════

async function loadSettings() {
    try {
        const settings = await api('/api/settings');

        const fields = [
            'your_name', 'your_title', 'your_email', 'calendly_link',
            'gemini_api_key', 'smtp_host', 'smtp_port', 'smtp_user',
            'smtp_password', 'from_email',
            'signalhire_api_key', 'instantly_api_key', 'instantly_default_campaign_id',
            'outbound_webhook_url', 'allowed_domains'
        ];

        fields.forEach(key => {
            const el = document.getElementById('setting-' + key);
            if (el && settings[key]) {
                if (!settings[key].includes('•')) {
                    el.value = settings[key];
                } else {
                    el.placeholder = 'Configured (hidden)';
                }
            }
        });

        // Update status indicators
        if (settings.gemini_api_key) {
            document.getElementById('gemini-status').innerHTML = '<span class="status-dot connected"></span><span style="color:var(--accent-success);">Connected — AI generation active</span>';
        }
        if (settings.smtp_user) {
            document.getElementById('smtp-status').innerHTML = '<span class="status-dot connected"></span><span style="color:var(--accent-success);">Connected — auto-send active</span>';
        }
    } catch {}
}

async function saveSettings() {
    const fields = [
        'your_name', 'your_title', 'your_email', 'calendly_link',
        'gemini_api_key', 'smtp_host', 'smtp_port', 'smtp_user',
        'smtp_password', 'from_email',
        'signalhire_api_key', 'instantly_api_key', 'instantly_default_campaign_id',
        'outbound_webhook_url', 'allowed_domains'
    ];

    const data = {};
    fields.forEach(key => {
        const el = document.getElementById('setting-' + key);
        if (el && el.value.trim() && !el.value.includes('•')) {
            data[key] = el.value.trim();
        }
    });

    try {
        await api('/api/settings', 'POST', data);
        showToast('Settings saved! 🎉', 'success');
        loadSettings();
    } catch {}
}

function exportData(tableName) {
    window.open(`${API}/api/export/${tableName}`, '_blank');
}


// ═══════════════════════════════════════════════════════════════
// AI ASSISTANT DRAWER CONTROLLER
// ═══════════════════════════════════════════════════════════════

function toggleAIDrawer() {
    document.getElementById('ai-drawer').classList.toggle('active');
}

function runAISuggestion(text) {
    document.getElementById('ai-prompt-input').value = text;
    document.getElementById('ai-prompt-input').focus();
}

async function submitAICommand(e) {
    if (e) e.preventDefault();
    const input = document.getElementById('ai-prompt-input');
    const prompt = input.value.trim();
    if (!prompt) return;
    
    input.value = '';
    appendAIMessage(prompt, 'user');
    
    const loadingId = appendAIMessage('Thinking...', 'assistant loading');
    
    try {
        const res = await fetch('/api/ai/command', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + (localStorage.getItem('leadlift_token') || '')
            },
            body: JSON.stringify({ prompt })
        });
        
        const data = await res.json();
        removeLoadingMessage(loadingId);
        
        if (!res.ok) {
            appendAIMessage('Error: ' + (data.detail || 'Failed to process AI command'), 'assistant error');
            return;
        }
        
        if (data.type === 'chat') {
            appendAIMessage(data.response, 'assistant');
        } else if (data.type === 'sql') {
            let html = `<div class="ai-message-explanation">${esc(data.explanation)}</div>`;
            html += `<pre class="ai-message-sql">${esc(data.query)}</pre>`;
            
            if (Array.isArray(data.data) && data.data.length > 0) {
                // Render table
                html += `<div style="overflow-x:auto; margin-top:8px; border:1px solid var(--border-default); border-radius:var(--radius-sm);">`;
                html += `<table style="width:100%; border-collapse:collapse; font-size:0.72rem; text-align:left;">`;
                // Headers
                const headers = Object.keys(data.data[0]);
                html += `<tr style="background:rgba(0,0,0,0.02); border-bottom:1px solid var(--border-default);">`;
                headers.forEach(h => {
                    html += `<th style="padding:6px; font-weight:600;">${esc(h)}</th>`;
                });
                html += `</tr>`;
                // Rows
                data.data.forEach(row => {
                    html += `<tr style="border-bottom:1px solid var(--border-default);">`;
                    headers.forEach(h => {
                        html += `<td style="padding:6px; color:var(--text-secondary);">${esc(row[h])}</td>`;
                    });
                    html += `</tr>`;
                });
                html += `</table></div>`;
            } else if (typeof data.data === 'object') {
                html += `<div style="font-size:0.75rem; color:var(--text-secondary); margin-top:6px;">Result: ${JSON.stringify(data.data)}</div>`;
            } else {
                html += `<div style="font-size:0.75rem; color:var(--text-secondary); margin-top:6px;">No rows returned.</div>`;
            }
            appendAIMessage(html, 'assistant raw-html');
        } else if (data.type === 'error') {
            let html = `<div style="color:var(--accent-danger); font-weight:600;">Execution Failed</div>`;
            html += `<div style="font-size:0.75rem; color:var(--text-secondary); margin-top:4px;">${esc(data.error)}</div>`;
            if (data.query) {
                html += `<pre class="ai-message-sql">${esc(data.query)}</pre>`;
            }
            appendAIMessage(html, 'assistant raw-html');
        } else {
            appendAIMessage(JSON.stringify(data), 'assistant');
        }
    } catch (err) {
        removeLoadingMessage(loadingId);
        appendAIMessage('Request failed: ' + err.message, 'assistant error');
    }
}

function appendAIMessage(content, type) {
    const chat = document.getElementById('ai-chat-messages');
    const msg = document.createElement('div');
    const id = 'msg_' + Math.random().toString(36).substring(2, 11);
    msg.id = id;
    
    if (type === 'assistant loading') {
        msg.className = 'ai-message assistant';
        msg.innerHTML = '<span style="animation:pulse 1s infinite;">Thinking...</span>';
    } else if (type === 'assistant raw-html') {
        msg.className = 'ai-message assistant';
        msg.innerHTML = content;
    } else {
        msg.className = 'ai-message ' + type;
        msg.textContent = content;
    }
    
    chat.appendChild(msg);
    chat.scrollTop = chat.scrollHeight;
    return id;
}

function removeLoadingMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}


// ═══════════════════════════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════════════════════════

function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function esc(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = String(str);
    return div.innerHTML;
}
