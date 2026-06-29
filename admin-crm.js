/**
 * Kaplan Sales — Salesforce Lightning Experience clone
 */
(function () {
    'use strict';

    const STORAGE_KEY = 'ks_crm_secret';
    const state = {
        data: null,
        route: parseRoute(),
        listView: 'all',
        displayMode: 'table', // table | kanban
        recentRecords: JSON.parse(localStorage.getItem('ks_recent') || '[]'),
    };

    const $ = (sel, root = document) => root.querySelector(sel);
    const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

    function secret() { return sessionStorage.getItem(STORAGE_KEY) || ''; }

    function headers() {
        return { 'Content-Type': 'application/json', 'X-Admin-Crm-Secret': secret() };
    }

    async function api(path, opts = {}) {
        const res = await fetch(path, { ...opts, headers: { ...headers(), ...(opts.headers || {}) } });
        if (res.status === 401) {
            sessionStorage.removeItem(STORAGE_KEY);
            showLogin();
            throw new Error(
                opts.loginAttempt
                    ? 'Passwort falsch — muss exakt wie ADMIN_CRM_SECRET auf Render sein.'
                    : 'Sitzung abgelaufen — bitte erneut anmelden.'
            );
        }
        return res.json();
    }

    function esc(s) {
        return String(s ?? '')
            .replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function parseRoute() {
        const hash = location.hash.replace(/^#/, '') || '/home';
        const parts = hash.split('/').filter(Boolean);
        return { page: parts[0] || 'home', id: parts[1] || null, sub: parts[2] || null };
    }

    function navigate(page, id) {
        location.hash = id ? `#/${page}/${encodeURIComponent(id)}` : `#/${page}`;
    }

    function trackRecent(type, id, name) {
        state.recentRecords = [{ type, id, name, at: Date.now() }, ...state.recentRecords.filter(r => !(r.type === type && r.id === id))].slice(0, 8);
        localStorage.setItem('ks_recent', JSON.stringify(state.recentRecords));
    }

    // ── Auth ──────────────────────────────────────────────────────────────

    function showLogin() {
        $('#login-screen').classList.remove('hidden');
        $('#app-shell').classList.add('hidden');
    }

    function showApp() {
        $('#login-screen').classList.add('hidden');
        $('#app-shell').classList.remove('hidden');
    }

    // ── Path component ───────────────────────────────────────────────────

    function renderPath(stages, current, onClick) {
        const idx = stages.indexOf(current);
        return `<ul class="sf-path">${stages.map((s, i) => {
            let cls = '';
            if (i < idx) cls = 'complete';
            else if (i === idx) cls = 'current';
            return `<li class="${cls}" data-stage="${esc(s)}">${esc(s)}</li>`;
        }).join('')}</ul>`;
    }

    // ── Views ────────────────────────────────────────────────────────────

    function pageHeader(icon, iconClass, title, meta, actions = '') {
        return `<div class="sf-page-header">
            <div class="sf-page-header-top">
                <div>
                    <span class="sf-object-icon ${iconClass}">${icon}</span>
                    <h1 class="sf-page-title">${esc(title)}</h1>
                    ${meta ? `<div class="sf-page-meta">${meta}</div>` : ''}
                </div>
                <div>${actions}</div>
            </div>
        </div>`;
    }

    function renderHome() {
        const s = state.data?.stats || {};
        const topOpps = state.data?.top_opportunities || [];
        const tasks = state.data?.tasks_today || [];
        const events = state.data?.events_today || [];
        const termine = state.data?.termine_heute || [];
        const recent = state.recentRecords;

        return pageHeader('🏠', 'home', 'Home', `Salesforce Home · ${state.data?.updated || ''}`) + `
        <div class="sf-home">
            <div class="sf-kpi-row">
                <div class="sf-kpi"><strong>${s.open || 0}</strong><span>Open Leads</span></div>
                <div class="sf-kpi"><strong>${s.open_opportunities || 0}</strong><span>Open Opps</span></div>
                <div class="sf-kpi"><strong>${s.hot_matches || 0}</strong><span>Hot Matches</span></div>
                <div class="sf-kpi"><strong>${s.tasks_today || 0}</strong><span>Tasks Today</span></div>
            </div>
            <div class="sf-home-grid">
                <div class="sf-widget">
                    <div class="sf-widget-header">Today's Events</div>
                    <div class="sf-widget-body">${(events.length ? events : termine).map(e => `
                        <div class="sf-widget-item">
                            <a href="#/leads/${esc(e.ref || e.related_id)}">${esc(e.name || e.subject || e.ref)}</a>
                            <div>${esc(e.naechster_termin || e.due || '')}</div>
                        </div>`).join('') || '<div class="sf-empty">No events today</div>'}
                </div>
                <div class="sf-widget">
                    <div class="sf-widget-header">Today's Tasks</div>
                    <div class="sf-widget-body">${tasks.map(t => `
                        <div class="sf-widget-item">
                            <strong>${esc(t.subject)}</strong>
                            <div>${esc(t.due)} · ${esc(t.related_id)}</div>
                        </div>`).join('') || '<div class="sf-empty">No tasks due today</div>'}
                </div>
                <div class="sf-widget">
                    <div class="sf-widget-header">Top Opportunities</div>
                    <div class="sf-widget-body">${topOpps.map(o => `
                        <div class="sf-widget-item">
                            <a href="#/opportunities/${esc(o.id)}">${esc(o.name)}</a>
                            <div>${esc(o.stage)} · ${o.probability}%</div>
                        </div>`).join('') || '<div class="sf-empty">No open opportunities</div>'}
                </div>
                <div class="sf-widget">
                    <div class="sf-widget-header">Recent Records</div>
                    <div class="sf-widget-body">${recent.map(r => `
                        <div class="sf-widget-item">
                            <a href="#/${esc(r.type)}/${esc(r.id)}">${esc(r.name)}</a>
                        </div>`).join('') || '<div class="sf-empty">No recent records</div>'}
                </div>
            </div>
        </div>`;
    }

    function filterLeads(leads) {
        const v = state.listView;
        if (v === 'bauherr') return leads.filter(l => l.role_type === 'bauherr');
        if (v === 'partner') return leads.filter(l => l.role_type === 'partner');
        if (v === 'open') return leads.filter(l => !l.terminal);
        if (v === 'hot') return leads.filter(l => (parseInt(String(l.best_match).replace('%', ''), 10) || 0) >= 75 && !l.terminal);
        return leads;
    }

    function listToolbar(objectName, views, showKanban = true) {
        return `<div class="sf-view-toolbar">
            <select id="list-view-select">${views.map(v => `
                <option value="${esc(v.id)}"${state.listView === v.id ? ' selected' : ''}>${esc(v.label)}</option>
            `).join('')}</select>
            <span style="color:var(--sf-muted);margin-left:auto">${esc(objectName)}</span>
            ${showKanban ? `<div class="sf-display-toggle">
                <button type="button" data-mode="table"${state.displayMode === 'table' ? ' class="active"' : ''}>Table</button>
                <button type="button" data-mode="kanban"${state.displayMode === 'kanban' ? ' class="active"' : ''}>Kanban</button>
            </div>` : ''}
        </div>`;
    }

    function renderLeadsList() {
        const leads = filterLeads(state.data?.leads || []);
        const views = [
            { id: 'all', label: 'All Open Leads' },
            { id: 'open', label: 'My Open Leads' },
            { id: 'bauherr', label: 'Bauherr Leads' },
            { id: 'partner', label: 'Partner Leads' },
            { id: 'hot', label: 'Hot Matches' },
        ];

        let body = '';
        if (state.displayMode === 'kanban') {
            const allStages = [...new Set(leads.flatMap(l => l.stages || []))];
            body = `<div class="sf-kanban">${allStages.map(stage => {
                const items = leads.filter(l => l.stage === stage);
                return `<div class="sf-kanban-col" data-stage="${esc(stage)}">
                    <div class="sf-kanban-col-header">${esc(stage)} (${items.length})</div>
                    <div class="sf-kanban-col-body">${items.map(l => kanbanLeadCard(l)).join('')}</div>
                </div>`;
            }).join('')}</div>`;
        } else {
            body = `<div class="sf-list-wrap"><div class="sf-table-wrap"><table class="sf-table">
                <thead><tr>
                    <th>Name</th><th>Company</th><th>Lead Status</th><th>Stage</th>
                    <th>City</th><th>Rating</th><th>Source</th>
                </tr></thead>
                <tbody>${leads.map(l => `<tr data-ref="${esc(l.ref)}">
                    <td><a href="#/leads/${esc(l.ref)}">${esc(l.name)}</a></td>
                    <td>${esc(l.company || l.name)}</td>
                    <td>${esc(l.lead_status)}</td>
                    <td>${esc(l.stage)}</td>
                    <td>${esc(l.stadt)}</td>
                    <td>${esc(l.best_match || l.seriositaet || '—')}</td>
                    <td>${esc(l.quelle)}</td>
                </tr>`).join('') || '<tr><td colspan="7" class="sf-empty">No records</td></tr>'}
                </tbody></table></div></div>`;
        }

        return pageHeader('🎯', 'leads', 'Leads', `${leads.length} items · Updated ${state.data?.updated || ''}`) +
            listToolbar('Lead', views) + body;
    }

    function kanbanLeadCard(l) {
        const hot = (parseInt(String(l.best_match).replace('%', ''), 10) || 0) >= 75;
        return `<div class="sf-kanban-card" draggable="true" data-ref="${esc(l.ref)}" data-type="lead">
            <h4>${esc(l.name)}</h4>
            <div>${esc(l.ref)} · ${esc(l.stadt)}</div>
            ${hot ? '<div class="warn">⚠ Hot Match</div>' : ''}
        </div>`;
    }

    function kanbanOppCard(o) {
        const warn = o.score >= 75 && o.status === 'Neu';
        return `<div class="sf-kanban-card" draggable="true" data-id="${esc(o.id)}" data-type="opp">
            <h4>${esc(o.name)}</h4>
            <div class="amount">${o.probability}% · ${esc(o.stage)}</div>
            ${warn ? '<div class="warn">⚠ No activity</div>' : ''}
        </div>`;
    }

    function renderLeadRecord(ref) {
        const l = (state.data?.leads || []).find(x => x.ref === ref);
        if (!l) return pageHeader('🎯', 'leads', 'Lead not found') + '<div class="sf-empty">Record not found</div>';
        trackRecent('leads', ref, l.name);

        const activities = (state.data?.activities || []).filter(a => a.related_id === ref);
        const opps = (state.data?.opportunities || []).filter(o => o.ag_ref === ref || o.an_ref === ref);
        const upcoming = activities.filter(a => a.status !== 'Completed');
        const past = activities.filter(a => a.status === 'Completed');

        return pageHeader('🎯', 'leads', l.name, `${l.ref} · ${l.record_type} · ${l.lead_status}`) +
            `<div class="sf-path-wrap">${renderPath(l.stages || [], l.stage)}</div>
            <div class="sf-record">
                <div class="sf-highlights">
                    <div class="sf-highlight-item"><label>Lead Status</label><span>${esc(l.lead_status)}</span></div>
                    <div class="sf-highlight-item"><label>Phone</label><span>—</span></div>
                    <div class="sf-highlight-item"><label>Email</label><span>—</span></div>
                    <div class="sf-highlight-item"><label>Rating</label><span>${esc(l.best_match || l.seriositaet || '—')}</span></div>
                    <div class="sf-highlight-item"><label>Source</label><span>${esc(l.quelle)}</span></div>
                </div>
                <div class="sf-record-grid">
                    <div class="sf-panel">
                        <div class="sf-panel-header">Details</div>
                        <div class="sf-panel-body" id="lead-details-form">
                            ${detailField('Stage', 'stage', l.stage, 'select', l.stages)}
                            ${detailField('Next Step', 'naechster_schritt', l.naechster_schritt)}
                            ${detailField('Next Appointment', 'naechster_termin', l.naechster_termin)}
                            ${detailField('Vertrag', 'vertrag', l.vertrag, 'select', ['Nein', 'Ja'])}
                            ${detailField('Intro Sent', 'intro_gesendet', l.intro_gesendet, 'select', ['Nein', 'Ja'])}
                            ${detailField('Net Amount €', 'netto', l.netto)}
                            ${detailField('Provision €', 'provision', l.provision)}
                            ${detailField('Invoice', 'rechnung', l.rechnung)}
                            ${detailField('Paid', 'bezahlt', l.bezahlt, 'select', ['Nein', 'Ja'])}
                            ${detailField('Lost Reason', 'verloren_grund', l.verloren_grund)}
                            ${detailField('Notes', 'notiz', l.notiz, 'textarea')}
                            <button type="button" class="slds-button slds-button_brand" id="save-lead-btn">Save</button>
                        </div>
                    </div>
                    <div class="sf-panel">
                        <div class="sf-panel-header">Activity</div>
                        <div class="sf-composer">
                            <button type="button" data-action="Call" data-related="Lead" data-id="${esc(ref)}">Log a Call</button>
                            <button type="button" data-action="Task" data-related="Lead" data-id="${esc(ref)}">New Task</button>
                            <button type="button" data-action="Event" data-related="Lead" data-id="${esc(ref)}">New Event</button>
                            <button type="button" data-action="Email" data-related="Lead" data-id="${esc(ref)}">Email</button>
                        </div>
                        <div class="sf-timeline-section">Upcoming & Overdue</div>
                        <ul class="sf-timeline">${upcoming.map(actItem).join('') || '<li class="sf-empty">No activities</li>'}</ul>
                        <div class="sf-timeline-section">Past Activity</div>
                        <ul class="sf-timeline">${past.map(actItem).join('') || '<li class="sf-empty">No past activity</li>'}</ul>
                    </div>
                    <div class="sf-panel">
                        <div class="sf-panel-header">Related</div>
                        <div class="sf-panel-body">
                            <strong>Opportunities (${opps.length})</strong>
                            ${opps.map(o => `<div class="sf-related-item"><a href="#/opportunities/${esc(o.id)}">${esc(o.name)}</a><br/>${esc(o.stage)} · ${o.probability}%</div>`).join('') || '<div class="sf-related-item">None</div>'}
                            ${l.ordner_link ? `<div class="sf-related-item"><a href="${esc(l.ordner_link)}" target="_blank" rel="noopener">Google Drive Folder</a></div>` : ''}
                        </div>
                    </div>
                </div>
            </div>`;
    }

    function detailField(label, name, value, type = 'text', options = []) {
        if (type === 'select') {
            return `<div class="sf-detail-field"><label>${esc(label)}</label>
                <select data-field="${esc(name)}">${options.map(o => `
                    <option value="${esc(o)}"${o === value ? ' selected' : ''}>${esc(o)}</option>
                `).join('')}</select></div>`;
        }
        if (type === 'textarea') {
            return `<div class="sf-detail-field"><label>${esc(label)}</label>
                <textarea data-field="${esc(name)}" rows="3">${esc(value)}</textarea></div>`;
        }
        return `<div class="sf-detail-field"><label>${esc(label)}</label>
            <input data-field="${esc(name)}" value="${esc(value)}" /></div>`;
    }

    function actItem(a) {
        const icons = { Task: '✓', Call: '📞', Event: '📅', Email: '✉' };
        return `<li>
            <div class="sf-timeline-icon">${icons[a.type] || '•'}</div>
            <div class="sf-timeline-body">
                <strong>${esc(a.subject)}</strong>
                <span>${esc(a.type)} · ${esc(a.due || a.created)} · ${esc(a.status)}</span>
                ${a.description ? `<div>${esc(a.description)}</div>` : ''}
            </div>
        </li>`;
    }

    function renderOpportunitiesList() {
        const opps = state.data?.opportunities || [];
        const stages = state.data?.opp_stages || [];
        const views = [
            { id: 'all', label: 'All Opportunities' },
            { id: 'open', label: 'Open Opportunities' },
        ];
        let filtered = state.listView === 'open' ? opps.filter(o => !o.terminal) : opps;

        let body = '';
        if (state.displayMode === 'kanban') {
            body = `<div class="sf-kanban">${stages.map(stage => {
                const items = filtered.filter(o => o.stage === stage);
                return `<div class="sf-kanban-col" data-stage="${esc(stage)}">
                    <div class="sf-kanban-col-header">${esc(stage)} (${items.length})</div>
                    <div class="sf-kanban-col-body">${items.map(kanbanOppCard).join('')}</div>
                </div>`;
            }).join('')}</div>`;
        } else {
            body = `<div class="sf-list-wrap"><div class="sf-table-wrap"><table class="sf-table">
                <thead><tr>
                    <th>Opportunity Name</th><th>Stage</th><th>Amount</th>
                    <th>Probability</th><th>Close Date</th><th>Status</th>
                </tr></thead>
                <tbody>${filtered.map(o => `<tr>
                    <td><a href="#/opportunities/${esc(o.id)}">${esc(o.name)}</a></td>
                    <td>${esc(o.stage)}</td>
                    <td>${esc(o.amount || '—')}</td>
                    <td>${o.probability}%</td>
                    <td>${esc(o.close_date || '—')}</td>
                    <td>${esc(o.status)}</td>
                </tr>`).join('') || '<tr><td colspan="6" class="sf-empty">No records</td></tr>'}
                </tbody></table></div></div>`;
        }

        return pageHeader('💰', 'opps', 'Opportunities', `${filtered.length} items`) +
            listToolbar('Opportunity', views) + body;
    }

    function renderOppRecord(id) {
        const o = (state.data?.opportunities || []).find(x => x.id === id);
        if (!o) return pageHeader('💰', 'opps', 'Not found') + '<div class="sf-empty">Record not found</div>';
        trackRecent('opportunities', id, o.name);

        return pageHeader('💰', 'opps', o.name, `${o.id} · ${o.stage} · ${o.probability}%`) +
            `<div class="sf-path-wrap">${renderPath(o.stages || [], o.stage)}</div>
            <div class="sf-record">
                <div class="sf-highlights">
                    <div class="sf-highlight-item"><label>Stage</label><span>${esc(o.stage)}</span></div>
                    <div class="sf-highlight-item"><label>Probability</label><span>${o.probability}%</span></div>
                    <div class="sf-highlight-item"><label>Account</label><span>${esc(o.account_name)}</span></div>
                    <div class="sf-highlight-item"><label>Partner</label><span>${esc(o.partner_name)}</span></div>
                </div>
                <div class="sf-record-grid">
                    <div class="sf-panel">
                        <div class="sf-panel-header">Details</div>
                        <div class="sf-panel-body">
                            ${detailField('Stage', 'stage', o.stage, 'select', o.stages || [])}
                            ${detailField('Next Step', 'next_step', o.next_step)}
                            <div class="sf-detail-field"><label>Bauherr Ref</label><input readonly value="${esc(o.ag_ref)}" /></div>
                            <div class="sf-detail-field"><label>Partner Ref</label><input readonly value="${esc(o.an_ref)}" /></div>
                            <button type="button" class="slds-button slds-button_brand" id="save-opp-btn" data-id="${esc(id)}">Save Stage</button>
                        </div>
                    </div>
                    <div class="sf-panel">
                        <div class="sf-panel-header">Activity</div>
                        <div class="sf-composer">
                            <button type="button" data-action="Call" data-related="Opportunity" data-id="${esc(id)}">Log a Call</button>
                            <button type="button" data-action="Task" data-related="Opportunity" data-id="${esc(id)}">New Task</button>
                            <button type="button" data-action="Event" data-related="Opportunity" data-id="${esc(id)}">New Event</button>
                        </div>
                        <ul class="sf-timeline">${(state.data?.activities || []).filter(a => a.related_id === id).map(actItem).join('') || '<li class="sf-empty">No activities</li>'}</ul>
                    </div>
                    <div class="sf-panel">
                        <div class="sf-panel-header">Related</div>
                        <div class="sf-panel-body">
                            <div class="sf-related-item"><a href="#/leads/${esc(o.ag_ref)}">Bauherr: ${esc(o.account_name)}</a></div>
                            <div class="sf-related-item"><a href="#/leads/${esc(o.an_ref)}">Partner: ${esc(o.partner_name)}</a></div>
                        </div>
                    </div>
                </div>
            </div>`;
    }

    function renderAccounts() {
        const accounts = state.data?.accounts || [];
        return pageHeader('🏢', 'accounts', 'Accounts', `${accounts.length} items`) +
            `<div class="sf-list-wrap"><div class="sf-table-wrap"><table class="sf-table">
                <thead><tr><th>Account Name</th><th>Type</th><th>City</th><th>Industry</th></tr></thead>
                <tbody>${accounts.map(a => `<tr>
                    <td><a href="#/leads/${esc(a.lead_ref)}">${esc(a.name)}</a></td>
                    <td>${esc(a.type)}</td>
                    <td>${esc(a.city)}</td>
                    <td>${esc(a.industry)}</td>
                </tr>`).join('') || '<tr><td colspan="4" class="sf-empty">No accounts</td></tr>'}
                </tbody></table></div></div>`;
    }

    function renderContacts() {
        const contacts = state.data?.contacts || [];
        return pageHeader('👤', 'contacts', 'Contacts', `${contacts.length} items`) +
            `<div class="sf-list-wrap"><div class="sf-table-wrap"><table class="sf-table">
                <thead><tr><th>Name</th><th>Account</th><th>Title</th><th>City</th></tr></thead>
                <tbody>${contacts.map(c => `<tr>
                    <td><a href="#/leads/${esc(c.lead_ref)}">${esc(c.name)}</a></td>
                    <td>${esc(c.account_name)}</td>
                    <td>${esc(c.title)}</td>
                    <td>${esc(c.city)}</td>
                </tr>`).join('') || '<tr><td colspan="4" class="sf-empty">No contacts</td></tr>'}
                </tbody></table></div></div>`;
    }

    function renderTasks() {
        const tasks = (state.data?.activities || []).filter(a => a.type === 'Task');
        return pageHeader('✓', 'home', 'Tasks', `${tasks.length} items`) +
            `<div class="sf-list-wrap"><div class="sf-table-wrap"><table class="sf-table">
                <thead><tr><th>Subject</th><th>Related To</th><th>Due Date</th><th>Status</th></tr></thead>
                <tbody>${tasks.map(t => `<tr>
                    <td>${esc(t.subject)}</td>
                    <td><a href="#/leads/${esc(t.related_id)}">${esc(t.related_id)}</a></td>
                    <td>${esc(t.due)}</td>
                    <td>${esc(t.status)}</td>
                </tr>`).join('') || '<tr><td colspan="4" class="sf-empty">No tasks</td></tr>'}
                </tbody></table></div></div>`;
    }

    function renderCalendar() {
        const events = (state.data?.activities || []).filter(a => a.type === 'Event');
        const leads = state.data?.termine_heute || [];
        const all = [...events, ...leads.map(l => ({ subject: l.name, due: l.naechster_termin, related_id: l.ref, type: 'Event' }))];
        return pageHeader('📅', 'home', 'Calendar', 'Events & Appointments') +
            `<div class="sf-list-wrap"><div class="sf-table-wrap"><table class="sf-table">
                <thead><tr><th>Subject</th><th>Start</th><th>Related To</th></tr></thead>
                <tbody>${all.map(e => `<tr>
                    <td>${esc(e.subject)}</td>
                    <td>${esc(e.due)}</td>
                    <td><a href="#/leads/${esc(e.related_id)}">${esc(e.related_id)}</a></td>
                </tr>`).join('') || '<tr><td colspan="3" class="sf-empty">No events</td></tr>'}
                </tbody></table></div></div>`;
    }

    function renderSearch(q) {
        const ql = q.toLowerCase();
        const leads = (state.data?.leads || []).filter(l =>
            l.name.toLowerCase().includes(ql) || l.ref.toLowerCase().includes(ql) || (l.stadt || '').toLowerCase().includes(ql));
        const opps = (state.data?.opportunities || []).filter(o =>
            o.name.toLowerCase().includes(ql) || o.id.toLowerCase().includes(ql));
        return pageHeader('🔍', 'home', `Search: ${q}`, `${leads.length + opps.length} results`) +
            `<div class="sf-home">
                <div class="sf-widget"><div class="sf-widget-header">Leads</div><div class="sf-widget-body">
                    ${leads.map(l => `<div class="sf-widget-item"><a href="#/leads/${esc(l.ref)}">${esc(l.name)}</a> · ${esc(l.ref)}</div>`).join('') || 'None'}
                </div></div>
                <div class="sf-widget"><div class="sf-widget-header">Opportunities</div><div class="sf-widget-body">
                    ${opps.map(o => `<div class="sf-widget-item"><a href="#/opportunities/${esc(o.id)}">${esc(o.name)}</a></div>`).join('') || 'None'}
                </div></div>
            </div>`;
    }

    function render() {
        state.route = parseRoute();
        const { page, id } = state.route;
        const q = $('#global-search')?.value?.trim();

        $$('.sf-nav a').forEach(a => {
            a.classList.toggle('active', a.dataset.route === page || (page === 'leads' && a.dataset.route === 'leads'));
        });

        let html = '';
        if (q && page === 'home') html = renderSearch(q);
        else if (page === 'home') html = renderHome();
        else if (page === 'leads' && id) html = renderLeadRecord(decodeURIComponent(id));
        else if (page === 'leads') html = renderLeadsList();
        else if (page === 'opportunities' && id) html = renderOppRecord(decodeURIComponent(id));
        else if (page === 'opportunities') html = renderOpportunitiesList();
        else if (page === 'accounts') html = renderAccounts();
        else if (page === 'contacts') html = renderContacts();
        else if (page === 'tasks') html = renderTasks();
        else if (page === 'calendar') html = renderCalendar();
        else html = renderHome();

        $('#sf-main').innerHTML = html;
        bindPageEvents();
    }

    // ── Events ───────────────────────────────────────────────────────────

    function bindPageEvents() {
        const viewSelect = $('#list-view-select');
        if (viewSelect) {
            viewSelect.onchange = () => { state.listView = viewSelect.value; render(); };
        }
        $$('[data-mode]').forEach(btn => {
            btn.onclick = () => { state.displayMode = btn.dataset.mode; render(); };
        });

        // Path click → update stage
        $$('.sf-path li').forEach(li => {
            li.onclick = async () => {
                const stage = li.dataset.stage;
                const route = state.route;
                if (route.page === 'leads' && route.id) {
                    await saveLead(route.id, { stage });
                } else if (route.page === 'opportunities' && route.id) {
                    await saveOpp(route.id, stage);
                }
            };
        });

        // Kanban drag-drop
        setupKanban();

        // Save lead
        const saveLeadBtn = $('#save-lead-btn');
        if (saveLeadBtn) {
            saveLeadBtn.onclick = async () => {
                const fields = {};
                $$('#lead-details-form [data-field]').forEach(el => {
                    fields[el.dataset.field] = el.value;
                });
                await saveLead(state.route.id, fields);
            };
        }

        const saveOppBtn = $('#save-opp-btn');
        if (saveOppBtn) {
            saveOppBtn.onclick = async () => {
                const stage = $(`[data-field="stage"]`)?.value;
                if (stage) await saveOpp(saveOppBtn.dataset.id, stage);
            };
        }

        // Activity composer
        $$('.sf-composer button[data-action]').forEach(btn => {
            btn.onclick = () => openActivityModal(btn.dataset.action, btn.dataset.related, btn.dataset.id);
        });
    }

    function setupKanban() {
        let drag = null;
        $$('.sf-kanban-card').forEach(card => {
            card.addEventListener('dragstart', () => { drag = card; card.classList.add('dragging'); });
            card.addEventListener('dragend', () => { drag = null; card.classList.remove('dragging'); });
        });
        $$('.sf-kanban-col').forEach(col => {
            col.addEventListener('dragover', e => { e.preventDefault(); col.classList.add('drag-over'); });
            col.addEventListener('dragleave', () => col.classList.remove('drag-over'));
            col.addEventListener('drop', async e => {
                e.preventDefault();
                col.classList.remove('drag-over');
                if (!drag) return;
                const stage = col.dataset.stage;
                if (drag.dataset.type === 'lead') {
                    await saveLead(drag.dataset.ref, { stage });
                } else if (drag.dataset.type === 'opp') {
                    await saveOpp(drag.dataset.id, stage);
                }
            });
        });
    }

    async function saveLead(ref, fields) {
        ref = decodeURIComponent(ref);
        const res = await api('/api/crm/update', { method: 'POST', body: JSON.stringify({ ref, fields }) });
        if (!res.ok) { alert(res.error || 'Save failed'); return; }
        await loadData();
        navigate('leads', ref);
    }

    async function saveOpp(id, stage) {
        const res = await api('/api/crm/opportunity', { method: 'POST', body: JSON.stringify({ id, stage }) });
        if (!res.ok) { alert(res.error || 'Save failed'); return; }
        await loadData();
        navigate('opportunities', id);
    }

    function openActivityModal(type, relatedType, relatedId) {
        const titles = { Task: 'New Task', Call: 'Log a Call', Event: 'New Event', Email: 'Log Email' };
        $('#activity-title').textContent = titles[type] || 'New Activity';
        $('#act-type').value = type;
        $('#act-related-type').value = relatedType;
        $('#act-related-id').value = relatedId;
        $('#act-subject').value = '';
        $('#act-due').value = '';
        $('#act-desc').value = '';
        $('#activity-dialog').showModal();
    }

    async function loadData(opts = {}) {
        const data = await api('/api/crm/snapshot', opts);
        if (!data.ok) {
            if (data.error === 'unauthorized') {
                throw new Error(
                    'Google Sheet lehnt ab: _Meta B7 muss denselben Wert haben wie Render. Apps Script neu deployen.'
                );
            }
            throw new Error(data.error || 'Laden fehlgeschlagen');
        }
        state.data = data;
    }

    // ── Init ─────────────────────────────────────────────────────────────

    $('#login-form')?.addEventListener('submit', async e => {
        e.preventDefault();
        $('#login-error').classList.add('hidden');
        sessionStorage.setItem(STORAGE_KEY, $('#crm-secret').value.trim());
        try {
            await loadData({ loginAttempt: true });
            showApp();
            render();
        } catch (err) {
            sessionStorage.removeItem(STORAGE_KEY);
            $('#login-error').textContent = err.message;
            $('#login-error').classList.remove('hidden');
        }
    });

    $('#refresh-btn')?.addEventListener('click', () => loadData().then(render).catch(e => alert(e.message)));
    window.addEventListener('hashchange', render);

    $('#global-search')?.addEventListener('keydown', e => {
        if (e.key === 'Enter') { location.hash = '#/home'; render(); }
    });

    $('#nav-toggle')?.addEventListener('click', () => $('#sf-nav').classList.toggle('open'));

    $$('[data-close]').forEach(btn => btn.addEventListener('click', () => $('#activity-dialog').close()));

    $('#activity-form')?.addEventListener('submit', async e => {
        e.preventDefault();
        const type = $('#act-type').value;
        const res = await api('/api/crm/activity', {
            method: 'POST',
            body: JSON.stringify({
                type,
                related_type: $('#act-related-type').value,
                related_id: $('#act-related-id').value,
                subject: $('#act-subject').value,
                due: $('#act-due').value,
                description: $('#act-desc').value,
                sync_termin: type === 'Event',
            }),
        });
        if (!res.ok) { alert(res.error || 'Failed'); return; }
        $('#activity-dialog').close();
        await loadData();
        render();
    });

    if (secret()) {
        loadData().then(() => { showApp(); render(); }).catch(showLogin);
    } else {
        showLogin();
    }
})();
