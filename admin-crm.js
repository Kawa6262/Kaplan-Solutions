/**
 * Kaplan Sales — Salesforce Lightning Experience clone
 */
(function () {
    'use strict';

    const STORAGE_KEY = 'ks_crm_secret';
    const SYNC_MS = 60000;
    const SYNC_MS_ACTIVE = 15000;
    const state = {
        data: null,
        route: parseRoute(),
        listView: localStorage.getItem('ks_list_view') || 'inbound',
        displayMode: 'table',
        recentRecords: JSON.parse(localStorage.getItem('ks_recent') || '[]'),
        lastFingerprint: '',
        renderedFingerprint: '',
        lastSyncAt: null,
        syncErrors: 0,
        pendingNewLeads: [],
        refFilter: '',
        formDirty: false,
        staleData: false,
        undoLead: null,
    };
    let syncTimer = null;
    let syncing = false;

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
        let data;
        try {
            data = await res.json();
        } catch {
            throw new Error('Server-Antwort ungültig (HTTP ' + res.status + ')');
        }
        if (!res.ok && data && !data.error) {
            data.error = 'HTTP ' + res.status;
        }
        return data;
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

    // ── Live Sync ─────────────────────────────────────────────────────────

    function setSyncUI(mode, label) {
        const dot = $('#sync-dot');
        const lbl = $('#sync-label');
        if (!dot) return;
        dot.className = 'sf-sync-dot ' + mode;
        if (lbl) lbl.textContent = label;
    }

    function showToast(msg, type = '') {
        const root = $('#toast-root');
        if (!root) return;
        const el = document.createElement('div');
        el.className = 'sf-toast' + (type ? ' ' + type : '');
        el.textContent = msg;
        root.appendChild(el);
        setTimeout(() => el.remove(), 5000);
    }

    function isUserEditing() {
        const ae = document.activeElement;
        if (state.formDirty) return true;
        if (ae?.closest('#lead-details-form, #activity-dialog, #ref-filter, #global-search')) return true;
        return false;
    }

    function showStaleBanner() {
        let el = $('#stale-data-banner');
        if (el) return;
        el = document.createElement('div');
        el.id = 'stale-data-banner';
        el.className = 'sf-stale-banner';
        el.innerHTML = '<span>Neue Daten im Sheet verfügbar</span><button type="button" id="stale-refresh-btn">Jetzt aktualisieren</button>';
        $('#app-shell')?.prepend(el);
        el.querySelector('#stale-refresh-btn').onclick = () => {
            state.staleData = false;
            state.formDirty = false;
            el.remove();
            refreshData({ forceRender: true }).catch(e => showToast(e.message, 'warn'));
        };
    }

    function removeStaleBanner() {
        $('#stale-data-banner')?.remove();
        state.staleData = false;
    }

    function showSaved() {
        const el = document.createElement('div');
        el.className = 'sf-save-toast';
        el.textContent = 'Gespeichert';
        document.body.appendChild(el);
        setTimeout(() => el.remove(), 2000);
    }

    function detectChanges(prev, next) {
        if (!prev || !next) return;
        const prevRefs = new Set((prev.leads || []).map(l => l.ref));
        const newLeads = (next.leads || []).filter(l => !prevRefs.has(l.ref));
        if (newLeads.length) {
            newLeads.forEach(l => showToast('Neuer Lead: ' + l.name + ' (' + l.ref + ')', 'success'));
            state.pendingNewLeads = newLeads;
            if (document.hidden && 'Notification' in window && Notification.permission === 'granted') {
                new Notification('Kaplan Sales', { body: newLeads.length + ' neuer Lead(s)' });
            }
        }
        const prevHot = prev.stats?.hot_matches || 0;
        const nextHot = next.stats?.hot_matches || 0;
        if (nextHot > prevHot) {
            showToast('Neuer Hot Match (' + nextHot + ' gesamt)', 'warn');
        }
    }

    function startAutoSync() {
        stopAutoSync();
        const tick = () => {
            if (document.hidden) return;
            refreshData({ silent: true });
        };
        syncTimer = setInterval(tick, SYNC_MS);
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) refreshData({ silent: true });
        });
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission().catch(() => {});
        }
    }

    function stopAutoSync() {
        if (syncTimer) clearInterval(syncTimer);
        syncTimer = null;
    }

    async function refreshData(opts = {}) {
        if (syncing && opts.silent) return;
        syncing = true;
        if (!opts.silent) $('#loading-bar')?.classList.add('active');
        setSyncUI('syncing', 'Sync…');
        try {
            const prev = state.data;
            const prevFp = prev?.snapshot_fingerprint || '';
            await loadData(opts);
            if (prev && state.data?.snapshot_fingerprint !== prevFp) {
                detectChanges(prev, state.data);
            }
            state.lastFingerprint = state.data?.snapshot_fingerprint || '';
            state.lastSyncAt = Date.now();
            state.syncErrors = 0;
            setSyncUI('live', 'Live · ' + (state.data?.updated || ''));

            const dataChanged = prev && state.data?.snapshot_fingerprint !== prevFp;
            const shouldRender = opts.forceRender || (!opts.silent && !isUserEditing());

            if (shouldRender) {
                removeStaleBanner();
                render();
                state.renderedFingerprint = state.lastFingerprint;
            } else if (opts.silent) {
                updateNavBadges();
                if (dataChanged) {
                    state.staleData = true;
                    showStaleBanner();
                }
            }
        } catch (e) {
            state.syncErrors++;
            setSyncUI(state.syncErrors > 2 ? 'error' : 'stale', 'Sync-Fehler');
            if (!opts.silent) showToast(e.message, 'warn');
        } finally {
            syncing = false;
            $('#loading-bar')?.classList.remove('active');
        }
    }

    function updateNavBadges() {
        const hot = state.data?.stats?.hot_matches || 0;
        const openInbound = state.data?.stats?.open_inbound ?? state.data?.stats?.open ?? 0;
        const openCold = state.data?.stats?.open_cold || 0;
        $$('.sf-nav a').forEach(a => {
            a.querySelector('.sf-badge')?.remove();
            if (a.dataset.route === 'leads' && openInbound) {
                a.insertAdjacentHTML('beforeend', `<span class="sf-badge">${openInbound}</span>`);
            }
            if (a.dataset.route === 'leads' && openCold) {
                a.insertAdjacentHTML('beforeend', `<span class="sf-badge cold">${openCold}</span>`);
            }
            if (a.dataset.route === 'opportunities' && hot) {
                a.insertAdjacentHTML('beforeend', `<span class="sf-badge hot">${hot}</span>`);
            }
        });
    }

    function renderNewLeadsBanner() {
        if (!state.pendingNewLeads.length) return '';
        return `<div class="sf-new-banner" id="new-leads-banner">
            <span>${state.pendingNewLeads.length} neue Anfrage(n) — ${state.pendingNewLeads.map(l => l.name).join(', ')}</span>
            <button type="button" id="view-new-leads">Anzeigen</button>
        </div>`;
    }

    function sanitizeField(val) {
        const s = String(val ?? '').trim();
        if (!s || s === '—' || s === '-' || s.startsWith('#')) return '';
        return s;
    }

    function contactLink(type, value) {
        value = sanitizeField(value);
        if (!value) return '—';
        if (type === 'email') return `<a class="sf-link-action" href="mailto:${esc(value)}">${esc(value)}</a>`;
        if (type === 'phone') {
            const tel = value.replace(/\s/g, '');
            return `<a class="sf-link-action" href="tel:${esc(tel)}">${esc(value)}</a>`;
        }
        return esc(value);
    }

    function refBadge(ref, opts = {}) {
        if (!ref) return '';
        const small = opts.small ? ' sm' : '';
        const inner = opts.link === false
            ? esc(ref)
            : `<a href="#/leads/${esc(ref)}">${esc(ref)}</a>`;
        return `<span class="sf-ref-badge${small}">${inner}<button type="button" class="sf-ref-copy" data-copy-ref="${esc(ref)}" title="Anfrage-Nr. kopieren">⎘</button></span>`;
    }

    function recordHeader(icon, iconClass, title, ref, metaParts = []) {
        const meta = metaParts.filter(Boolean).map(p => `<span>${p}</span>`).join('<span class="dot">·</span>');
        return `<div class="sf-record-header">
            <div class="sf-record-header-top">
                <span class="sf-object-icon ${iconClass}">${icon}</span>
                <div class="sf-record-header-main">
                    ${ref ? `<div style="margin-bottom:8px">${refBadge(ref)}</div>` : ''}
                    <h1>${esc(title)}</h1>
                    ${meta ? `<div class="sf-record-header-meta">${meta}</div>` : ''}
                </div>
            </div>
        </div>`;
    }

    function highlightField(label, valueHtml, truncate = false) {
        return `<div class="sf-highlight-item">
            <label>${esc(label)}</label>
            <span class="sf-highlight-value${truncate ? ' truncate' : ''}" title="${typeof valueHtml === 'string' && !valueHtml.includes('<') ? esc(valueHtml) : ''}">${valueHtml}</span>
        </div>`;
    }

    function formatRating(l) {
        const match = l.best_match && !/^[-—]$/.test(String(l.best_match).trim()) ? String(l.best_match).trim() : '';
        const ser = l.seriositaet && !/^[-—]$/.test(String(l.seriositaet).trim()) ? String(l.seriositaet).trim() : '';
        if (match && ser) return match + ' · ' + ser;
        return match || ser || '—';
    }

    function formatTermin(val) {
        if (!val || val === '—' || val === '-') return '';
        const s = String(val).trim();
        if (/^https?:\/\//i.test(s) || s.includes('drive.google')) return '';
        return s;
    }

    function leadMatchesQuery(l, q) {
        if (!q) return true;
        const norm = q.toLowerCase().replace(/\s+/g, '');
        const parts = [l.ref, l.name, l.company, l.email, l.telefon, l.stadt, l.quelle, l.lead_status, l.stage]
            .map(x => String(x || '').toLowerCase());
        return parts.some(p => p.includes(norm) || p.replace(/\s+/g, '').includes(norm));
    }

    function resolveSearchNav(q) {
        const leads = state.data?.leads || [];
        const exact = leads.find(l => l.ref.toLowerCase() === q.toLowerCase());
        if (exact) {
            navigate('leads', exact.ref);
            return true;
        }
        return false;
    }

    function getSearchQuery() {
        return ($('#global-search')?.value || '').trim();
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

    function renderPath(stages, current) {
        const idx = Math.max(0, stages.indexOf(current));
        return `<p class="sf-path-hint">Sales Path · Schritt ${idx + 1} von ${stages.length}: ${esc(current)}</p>
            <ul class="sf-path">${stages.map((s, i) => {
            let cls = '';
            if (i < idx) cls = 'complete';
            else if (i === idx) cls = 'current';
            return `<li class="${cls}" data-stage="${esc(s)}" title="${esc(s)}">${esc(s)}</li>`;
        }).join('')}</ul>`;
    }

    function getNextStage(stages, current) {
        const idx = stages.indexOf(current);
        if (idx < 0 || idx >= stages.length - 1) return null;
        return stages[idx + 1];
    }

    function renderPathActions(stages, current, roleType = 'partner') {
        const idx = stages.indexOf(current);
        const next = getNextStage(stages, current);
        const prev = idx > 0 ? stages[idx - 1] : null;
        const resetStage = roleType === 'bauherr' ? 'Neu' : 'Lead';
        return `<div class="sf-path-actions">
            ${prev ? `<button type="button" class="slds-button slds-button_neutral" id="path-prev-btn" data-stage="${esc(prev)}">← ${esc(prev)}</button>` : ''}
            ${next ? `<button type="button" class="slds-button slds-button_brand" id="path-advance-btn" data-next="${esc(next)}">Nächster Schritt → ${esc(next)}</button>` : '<span class="sf-path-done">Letzter Schritt im Pfad</span>'}
            <button type="button" class="slds-button slds-button_neutral" id="path-reset-btn" data-stage="${esc(resetStage)}" title="Stage manuell zurücksetzen">↩ ${esc(resetStage)}</button>
        </div>`;
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

        return pageHeader('🏠', 'home', 'Home', `Kaplan Sales · ${state.data?.updated || ''}`) +
        (renderNewLeadsBanner() || '') + `
        <div class="sf-home">
            <div class="sf-kpi-row">
                <div class="sf-kpi"><strong>${s.total || 0}</strong><span>Leads gesamt</span></div>
                <div class="sf-kpi"><strong>${s.cold || 0}</strong><span>Cold / Outreach</span></div>
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
                            ${e.ref ? refBadge(e.ref, { small: true }) + ' ' : ''}
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
                            ${r.type === 'leads' ? refBadge(r.id, { small: true }) + ' ' : ''}
                            <a href="#/${esc(r.type)}/${esc(r.id)}">${esc(r.name)}</a>
                        </div>`).join('') || '<div class="sf-empty">No recent records</div>'}
                </div>
            </div>
        </div>`;
    }

    function filterLeads(leads) {
        const v = state.listView;
        let filtered = leads;
        if (v === 'bauherr') filtered = filtered.filter(l => l.role_type === 'bauherr');
        else if (v === 'partner') filtered = filtered.filter(l => l.role_type === 'partner' && !l.cold_lead && l.quelle !== 'Outreach');
        else if (v === 'cold') filtered = filtered.filter(l => l.cold_lead || l.quelle === 'Outreach');
        else if (v === 'inbound') filtered = filtered.filter(l => !l.cold_lead && l.quelle !== 'Outreach');
        else if (v === 'open') filtered = filtered.filter(l => !l.terminal);
        else if (v === 'hot') filtered = filtered.filter(l => (parseInt(String(l.best_match).replace('%', ''), 10) || 0) >= 75 && !l.terminal);
        if (state.refFilter) filtered = filtered.filter(l => leadMatchesQuery(l, state.refFilter));
        return filtered;
    }

    function listToolbar(objectName, views, showKanban = true) {
        return `<div class="sf-view-toolbar">
            <select id="list-view-select">${views.map(v => `
                <option value="${esc(v.id)}"${state.listView === v.id ? ' selected' : ''}>${esc(v.label)}</option>
            `).join('')}</select>
            <div class="sf-ref-search-wrap">
                <input type="search" id="ref-filter" placeholder="Anfrage-Nr. filtern…" value="${esc(state.refFilter)}" autocomplete="off" />
            </div>
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
            { id: 'inbound', label: 'Website-Anfragen (warm)' },
            { id: 'cold', label: 'Cold / Outreach' },
            { id: 'all', label: 'Alle Leads' },
            { id: 'open', label: 'Offene Leads' },
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
                    <th class="col-ref">Anfrage-Nr.</th><th>Name</th><th>Typ</th><th>Company</th><th>Lead Status</th><th>Stage</th>
                    <th>City</th><th>Rating</th><th>Source</th>
                </tr></thead>
                <tbody>${leads.map(l => {
                    const hot = (parseInt(String(l.best_match).replace('%', ''), 10) || 0) >= 75;
                    const typeBadge = l.cold_lead || l.quelle === 'Outreach'
                        ? '<span class="badge-cold">COLD</span>'
                        : '<span class="badge-warm">WARM</span>';
                    return `<tr data-ref="${esc(l.ref)}">
                    <td class="col-ref"><a href="#/leads/${esc(l.ref)}">${esc(l.ref)}</a></td>
                    <td><a href="#/leads/${esc(l.ref)}">${esc(l.name)}</a>${hot ? '<span class="badge-hot">HOT</span>' : ''}</td>
                    <td>${typeBadge || esc(l.record_type || 'Lead')}</td>
                    <td>${esc(l.company || l.name)}</td>
                    <td>${esc(l.lead_status)}</td>
                    <td>${esc(l.stage)}</td>
                    <td>${esc(l.stadt)}</td>
                    <td>${esc(formatRating(l))}</td>
                    <td>${esc(l.quelle)}</td>
                </tr>`;
                }).join('') || '<tr><td colspan="9" class="sf-empty">Keine Einträge</td></tr>'}
                </tbody></table></div></div>`;
        }

        return pageHeader('🎯', 'leads', 'Leads', `${leads.length} items · Updated ${state.data?.updated || ''}`) +
            listToolbar('Lead', views) + body;
    }

    function kanbanLeadCard(l) {
        const hot = (parseInt(String(l.best_match).replace('%', ''), 10) || 0) >= 75;
        return `<div class="sf-kanban-card" draggable="true" data-ref="${esc(l.ref)}" data-type="lead">
            <div style="margin-bottom:4px">${refBadge(l.ref, { small: true })}</div>
            <h4>${esc(l.name)}</h4>
            <div>${esc(l.stadt)} · ${esc(l.stage)}</div>
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
        const termin = formatTermin(l.naechster_termin);
        const driveLink = l.ordner_link || (/^https?:\/\//i.test(String(l.naechster_termin || '')) ? l.naechster_termin : '');

        return recordHeader('🎯', 'leads', l.name, l.ref, [
            l.cold_lead ? '<span class="badge-cold inline">Cold Outreach</span>' : '',
            esc(l.record_type),
            esc(l.lead_status),
            l.stadt ? esc(l.stadt) : '',
        ].filter(Boolean)) +
            `<div class="sf-path-wrap">${renderPath(l.stages || [], l.stage)}${renderPathActions(l.stages || [], l.stage, l.role_type)}</div>
            <div class="sf-record">
                <div class="sf-highlights">
                    ${highlightField('Status', esc(l.lead_status), true)}
                    ${highlightField('Telefon', contactLink('phone', l.telefon), true)}
                    ${highlightField('E-Mail', contactLink('email', l.email), true)}
                    ${highlightField('Match / Rating', esc(formatRating(l)), true)}
                    ${highlightField('Quelle', esc(l.quelle || '—'), true)}
                    ${highlightField('Firma', esc(l.company || l.name), false)}
                </div>
                <div class="sf-record-grid">
                    <div class="sf-panel">
                        <div class="sf-panel-header">Details</div>
                        <div class="sf-panel-body" id="lead-details-form">
                            <div class="sf-details-section">
                                <h4>Anfrage & Pipeline</h4>
                                <div class="sf-detail-field"><label>Anfrage-Nr.</label><input readonly value="${esc(l.ref)}" /></div>
                                ${detailField('Stage', 'stage', l.stage, 'select', l.stages)}
                                ${detailField('Nächster Schritt', 'naechster_schritt', l.naechster_schritt)}
                                ${detailField('Nächster Termin', 'naechster_termin', termin)}
                            </div>
                            <div class="sf-details-section">
                                <h4>Vertrag & Abrechnung</h4>
                                ${detailField('Vertrag', 'vertrag', l.vertrag, 'select', ['Nein', 'Ja'])}
                                ${detailField('Intro gesendet', 'intro_gesendet', l.intro_gesendet, 'select', ['Nein', 'Ja'])}
                                ${detailField('Netto €', 'netto', l.netto)}
                                ${detailField('Provision €', 'provision', l.provision)}
                                ${detailField('Rechnung', 'rechnung', l.rechnung)}
                                ${detailField('Bezahlt', 'bezahlt', l.bezahlt, 'select', ['Nein', 'Ja'])}
                            </div>
                            <div class="sf-details-section">
                                <h4>Notizen</h4>
                                ${detailField('Verloren — Grund', 'verloren_grund', l.verloren_grund)}
                                ${detailField('Notiz', 'notiz', l.notiz, 'textarea')}
                            </div>
                            <div class="sf-form-actions">
                                ${l.role_type === 'partner' && l.netto ? `<button type="button" class="slds-button slds-button_brand" id="invoice-btn" title="Rechnung generieren & versenden">Rechnung senden</button>` : ''}
                                ${l.cold_lead ? `<button type="button" class="slds-button slds-button_neutral" id="activate-cold-btn">In Pipeline aktivieren</button>` : ''}
                                <button type="button" class="slds-button slds-button_neutral" id="undo-lead-btn"${state.undoLead?.ref === l.ref ? '' : ' disabled'}>Rückgängig</button>
                                <button type="button" class="slds-button slds-button_brand" id="save-lead-btn">Speichern</button>
                            </div>
                        </div>
                    </div>
                    <div class="sf-panel">
                        <div class="sf-panel-header">Activity</div>
                        <div class="sf-composer">
                            <button type="button" data-action="Call" data-related="Lead" data-id="${esc(ref)}">Anruf protokollieren</button>
                            <button type="button" data-action="Task" data-related="Lead" data-id="${esc(ref)}">Neue Aufgabe</button>
                            <button type="button" data-action="Event" data-related="Lead" data-id="${esc(ref)}">Neuer Termin</button>
                            <button type="button" data-action="Email" data-related="Lead" data-id="${esc(ref)}">E-Mail</button>
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
                            ${driveLink ? `<div class="sf-related-item"><a href="${esc(driveLink)}" target="_blank" rel="noopener">Google Drive Ordner</a></div>` : ''}
                        </div>
                    </div>
                </div>
            </div>`;
    }

    function detailField(label, name, value, type = 'text', options = []) {
        if (type === 'select') {
            const opts = [...options];
            if (value && !opts.includes(value)) opts.unshift(value);
            return `<div class="sf-detail-field"><label>${esc(label)}</label>
                <select data-field="${esc(name)}">${opts.map(o => `
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

        return recordHeader('💰', 'opps', o.name, o.ag_ref || o.an_ref || '', [
            esc(o.id),
            esc(o.stage),
            o.probability + '%',
        ]) +
            `<div class="sf-path-wrap">${renderPath(o.stages || [], o.stage)}</div>
            <div class="sf-record">
                <div class="sf-highlights">
                    ${highlightField('Stage', esc(o.stage), true)}
                    ${highlightField('Probability', esc(o.probability + '%'), true)}
                    ${highlightField('Bauherr', esc(o.account_name || '—'), true)}
                    ${highlightField('Partner', esc(o.partner_name || '—'), true)}
                    ${highlightField('Bauherr-Nr.', o.ag_ref ? refBadge(o.ag_ref, { small: true }) : '—', true)}
                    ${highlightField('Partner-Nr.', o.an_ref ? refBadge(o.an_ref, { small: true }) : '—', true)}
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
                <thead><tr><th>Name</th><th>Account</th><th>E-Mail</th><th>Telefon</th><th>Stadt</th></tr></thead>
                <tbody>${contacts.map(c => `<tr>
                    <td><a href="#/leads/${esc(c.lead_ref)}">${esc(c.name)}</a></td>
                    <td>${esc(c.account_name)}</td>
                    <td>${contactLink('email', c.email)}</td>
                    <td>${contactLink('phone', c.phone)}</td>
                    <td>${esc(c.city)}</td>
                </tr>`).join('') || '<tr><td colspan="5" class="sf-empty">Keine Kontakte</td></tr>'}
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
        const actEvents = (state.data?.activities || []).filter(a => a.type === 'Event' && a.due);
        const actTasks = (state.data?.activities || []).filter(a => a.type === 'Task' && a.due);
        const leadTermine = (state.data?.leads || [])
            .filter(l => formatTermin(l.naechster_termin))
            .map(l => ({
                subject: l.name + ' — Termin',
                due: l.naechster_termin,
                related_id: l.ref,
                type: 'Termin',
                sort: l.naechster_termin,
            }));
        const all = [
            ...actEvents.map(e => ({ ...e, sort: e.due })),
            ...actTasks.map(t => ({ ...t, subject: t.subject + ' (Task)', sort: t.due })),
            ...leadTermine,
        ].sort((a, b) => String(a.sort).localeCompare(String(b.sort), 'de'));

        const grouped = {};
        all.forEach(e => {
            const day = String(e.due || '').split(' ')[0] || 'Ohne Datum';
            if (!grouped[day]) grouped[day] = [];
            grouped[day].push(e);
        });

        const body = Object.keys(grouped).map(day => `
            <div class="sf-cal-day">
                <h3 class="sf-cal-day-header">${esc(day)}</h3>
                <table class="sf-table">
                    <thead><tr><th>Zeit / Typ</th><th>Betreff</th><th>Kunde</th></tr></thead>
                    <tbody>${grouped[day].map(e => `<tr>
                        <td>${esc(e.due)} · ${esc(e.type)}</td>
                        <td>${esc(e.subject)}</td>
                        <td><a href="#/leads/${esc(e.related_id)}">${refBadge(e.related_id, { small: true })}</a></td>
                    </tr>`).join('')}</tbody>
                </table>
            </div>`).join('');

        return pageHeader('📅', 'home', 'Kalender', `${all.length} Termine & Events`) +
            `<div class="sf-list-wrap">${body || '<div class="sf-empty">Keine Termine — im Lead-Profil „Neuer Termin“ anlegen</div>'}</div>`;
    }

    function renderSearch(q) {
        const ql = q.trim();
        const leads = (state.data?.leads || []).filter(l => leadMatchesQuery(l, ql));
        const opps = (state.data?.opportunities || []).filter(o =>
            o.name.toLowerCase().includes(ql.toLowerCase()) ||
            o.id.toLowerCase().includes(ql.toLowerCase()) ||
            (o.ag_ref || '').toLowerCase().includes(ql.toLowerCase()) ||
            (o.an_ref || '').toLowerCase().includes(ql.toLowerCase()));
        return pageHeader('🔍', 'home', 'Suche', `${leads.length + opps.length} Ergebnisse für „${esc(ql)}“`) +
            `<div class="sf-home">
                <div class="sf-widget"><div class="sf-widget-header">Leads (${leads.length})</div><div class="sf-widget-body">
                    ${leads.map(l => `<div class="sf-widget-item">
                        ${refBadge(l.ref, { small: true })}
                        <a href="#/leads/${esc(l.ref)}" style="margin-left:8px;font-weight:600">${esc(l.name)}</a>
                        <div>${esc(l.company || '')} · ${esc(l.stadt || '')} · ${esc(l.lead_status)}</div>
                    </div>`).join('') || '<div class="sf-empty">Keine Leads gefunden</div>'}
                </div></div>
                <div class="sf-widget"><div class="sf-widget-header">Opportunities (${opps.length})</div><div class="sf-widget-body">
                    ${opps.map(o => `<div class="sf-widget-item">
                        <a href="#/opportunities/${esc(o.id)}">${esc(o.name)}</a>
                        <div>${esc(o.stage)} · ${o.ag_ref ? esc(o.ag_ref) : ''}${o.an_ref ? ' / ' + esc(o.an_ref) : ''}</div>
                    </div>`).join('') || '<div class="sf-empty">Keine Opportunities gefunden</div>'}
                </div></div>
            </div>`;
    }

    function render() {
        state.route = parseRoute();
        const { page, id } = state.route;
        const q = getSearchQuery();

        $$('.sf-nav a').forEach(a => {
            a.classList.toggle('active', a.dataset.route === page || (page === 'search' && a.dataset.route === 'home'));
        });

        let html = '';
        if (page === 'search' && q) html = renderSearch(q);
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
        updateNavBadges();
        $('#view-new-leads')?.addEventListener('click', () => {
            state.pendingNewLeads = [];
            state.listView = 'all';
            navigate('leads');
        });
    }

    // ── Events ───────────────────────────────────────────────────────────

    function bindPageEvents() {
        const viewSelect = $('#list-view-select');
        if (viewSelect) {
            viewSelect.onchange = () => {
                state.listView = viewSelect.value;
                localStorage.setItem('ks_list_view', state.listView);
                render();
            };
        }
        $$('[data-mode]').forEach(btn => {
            btn.onclick = () => { state.displayMode = btn.dataset.mode; render(); };
        });

        // Path click → update stage
        $$('.sf-path li').forEach(li => {
            li.onclick = async () => {
                const stage = li.dataset.stage;
                const route = state.route;
                try {
                    if (route.page === 'leads' && route.id) {
                        await saveLead(route.id, { stage });
                    } else if (route.page === 'opportunities' && route.id) {
                        await saveOpp(route.id, stage);
                    }
                } catch (err) {
                    showToast(err.message, 'warn');
                }
            };
        });

        const pathAdvance = $('#path-advance-btn');
        if (pathAdvance) {
            pathAdvance.onclick = async () => {
                const next = pathAdvance.dataset.next;
                if (!next || !state.route.id) return;
                pathAdvance.disabled = true;
                try {
                    await saveLead(state.route.id, { stage: next });
                } catch (err) {
                    showToast(err.message, 'warn');
                } finally {
                    pathAdvance.disabled = false;
                }
            };
        }

        const pathPrev = $('#path-prev-btn');
        if (pathPrev) {
            pathPrev.onclick = async () => {
                const stage = pathPrev.dataset.stage;
                if (!stage || !state.route.id) return;
                pathPrev.disabled = true;
                try {
                    await saveLead(state.route.id, { stage });
                } catch (err) {
                    showToast(err.message, 'warn');
                } finally {
                    pathPrev.disabled = false;
                }
            };
        }

        const pathReset = $('#path-reset-btn');
        if (pathReset) {
            pathReset.onclick = async () => {
                const stage = pathReset.dataset.stage;
                if (!stage || !state.route.id) return;
                if (!confirm('Stage wirklich auf „' + stage + '“ zurücksetzen?')) return;
                pathReset.disabled = true;
                try {
                    await saveLead(state.route.id, {
                        stage,
                        vertrag: 'Nein',
                        intro_gesendet: 'Nein',
                        naechster_schritt: stage === 'Lead' ? 'Erstgespräch anbieten' : 'Follow-up senden / anrufen',
                    });
                } catch (err) {
                    showToast(err.message, 'warn');
                } finally {
                    pathReset.disabled = false;
                }
            };
        }

        // Kanban drag-drop
        setupKanban();

        // Save lead
        const saveLeadBtn = $('#save-lead-btn');
        if (saveLeadBtn) {
            saveLeadBtn.onclick = async () => {
                saveLeadBtn.disabled = true;
                try {
                    const fields = collectLeadFormFields();
                    await saveLead(state.route.id, fields);
                } catch (err) {
                    showToast(err.message, 'warn');
                } finally {
                    saveLeadBtn.disabled = false;
                }
            };
        }

        const invoiceBtn = $('#invoice-btn');
        if (invoiceBtn) {
            invoiceBtn.onclick = async () => {
                if (!confirm('Rechnung jetzt generieren und an den Partner senden?')) return;
                invoiceBtn.disabled = true;
                try {
                    const res = await api('/crm/invoice', {
                        method: 'POST',
                        body: JSON.stringify({ ref: state.route.id }),
                    });
                    if (!res.ok) throw new Error(res.error || 'Rechnung fehlgeschlagen');
                    showToast('Rechnung ' + (res.invoice_no || '') + ' gesendet', 'success');
                    await loadData({ silent: true });
                    render();
                } catch (err) {
                    showToast(err.message, 'warn');
                } finally {
                    invoiceBtn.disabled = false;
                }
            };
        }

        const undoBtn = $('#undo-lead-btn');
        if (undoBtn && !undoBtn.disabled) {
            undoBtn.onclick = async () => {
                if (!state.undoLead) return;
                undoBtn.disabled = true;
                try {
                    await saveLead(state.undoLead.ref, state.undoLead.fields);
                    showToast('Rückgängig gemacht', 'success');
                    state.undoLead = null;
                } catch (err) {
                    showToast(err.message, 'warn');
                } finally {
                    undoBtn.disabled = false;
                }
            };
        }

        $$('#lead-details-form [data-field]').forEach(el => {
            el.addEventListener('input', () => { state.formDirty = true; });
            el.addEventListener('change', () => { state.formDirty = true; });
        });

        const activateColdBtn = $('#activate-cold-btn');
        if (activateColdBtn) {
            activateColdBtn.onclick = async () => {
                activateColdBtn.disabled = true;
                try {
                    await saveLead(state.route.id, { stage: 'Lead', naechster_schritt: 'Cold Lead aktiviert — Erstkontakt planen' });
                    showToast('Lead in Pipeline aktiviert', 'success');
                } catch (err) {
                    showToast(err.message, 'warn');
                } finally {
                    activateColdBtn.disabled = false;
                }
            };
        }

        const saveOppBtn = $('#save-opp-btn');
        if (saveOppBtn) {
            saveOppBtn.onclick = async () => {
                saveOppBtn.disabled = true;
                try {
                    const stage = $(`[data-field="stage"]`)?.value;
                    if (stage) await saveOpp(saveOppBtn.dataset.id, stage);
                } catch (err) {
                    showToast(err.message, 'warn');
                } finally {
                    saveOppBtn.disabled = false;
                }
            };
        }

        // Activity composer
        $$('.sf-composer button[data-action]').forEach(btn => {
            btn.onclick = () => openActivityModal(btn.dataset.action, btn.dataset.related, btn.dataset.id);
        });

        $$('[data-copy-ref]').forEach(btn => {
            btn.onclick = e => {
                e.preventDefault();
                e.stopPropagation();
                navigator.clipboard.writeText(btn.dataset.copyRef).then(
                    () => showToast('Anfrage-Nr. kopiert: ' + btn.dataset.copyRef, 'success'),
                    () => showToast('Kopieren fehlgeschlagen', 'warn')
                );
            };
        });

        const refFilter = $('#ref-filter');
        if (refFilter) {
            refFilter.oninput = () => {
                const pos = refFilter.selectionStart;
                state.refFilter = refFilter.value.trim();
                render();
                const el = $('#ref-filter');
                if (el) {
                    el.focus();
                    el.setSelectionRange(pos, pos);
                }
            };
        }
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

    function collectLeadFormFields() {
        const fields = {};
        $$('#lead-details-form [data-field]').forEach(el => {
            if (el.dataset.field === 'naechster_termin' && !el.value.trim()) return;
            fields[el.dataset.field] = el.value;
        });
        return fields;
    }

    function snapshotLeadFields(ref) {
        const l = (state.data?.leads || []).find(x => x.ref === decodeURIComponent(ref));
        if (!l) return null;
        return {
            stage: l.stage,
            naechster_schritt: l.naechster_schritt,
            naechster_termin: l.naechster_termin,
            vertrag: l.vertrag,
            intro_gesendet: l.intro_gesendet,
            netto: l.netto,
            provision: l.provision,
            rechnung: l.rechnung,
            bezahlt: l.bezahlt,
            verloren_grund: l.verloren_grund,
            notiz: l.notiz,
        };
    }

    async function saveLead(ref, fields) {
        ref = decodeURIComponent(ref);
        state.undoLead = { ref, fields: snapshotLeadFields(ref) };
        const res = await api('/api/crm/update', { method: 'POST', body: JSON.stringify({ ref, fields }) });
        if (!res.ok) throw new Error(res.error || 'Speichern fehlgeschlagen');
        showSaved();
        state.formDirty = false;
        removeStaleBanner();
        await refreshData({ silent: true });
        render();
    }

    async function saveOpp(id, stage) {
        const res = await api('/api/crm/opportunity', { method: 'POST', body: JSON.stringify({ id, stage }) });
        if (!res.ok) throw new Error(res.error || 'Speichern fehlgeschlagen');
        showSaved();
        await refreshData({ silent: true });
        render();
    }

    function openActivityModal(type, relatedType, relatedId) {
        const titles = {
            Task: 'Neue Aufgabe',
            Call: 'Anruf protokollieren',
            Event: 'Neuer Termin',
            Email: 'E-Mail protokollieren',
        };
        const dialog = $('#activity-dialog');
        if (!dialog || typeof dialog.showModal !== 'function') {
            showToast('Dialog nicht unterstützt — Browser aktualisieren', 'warn');
            return;
        }
        $('#activity-title').textContent = titles[type] || 'Neue Aktivität';
        $('#act-type').value = type;
        $('#act-related-type').value = relatedType;
        $('#act-related-id').value = relatedId;
        $('#act-subject').value = type === 'Call' ? 'Telefonat' : type === 'Event' ? 'Termin' : '';
        $('#act-due').value = '';
        $('#act-desc').value = '';
        dialog.showModal();
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
        state.lastFingerprint = data.snapshot_fingerprint || '';
    }

    // ── Init ─────────────────────────────────────────────────────────────

    $('#login-form')?.addEventListener('submit', async e => {
        e.preventDefault();
        $('#login-error').classList.add('hidden');
        sessionStorage.setItem(STORAGE_KEY, $('#crm-secret').value.trim());
        try {
            await loadData({ loginAttempt: true });
            showApp();
            startAutoSync();
            render();
        } catch (err) {
            sessionStorage.removeItem(STORAGE_KEY);
            $('#login-error').textContent = err.message;
            $('#login-error').classList.remove('hidden');
        }
    });

    $('#refresh-btn')?.addEventListener('click', () => {
        state.formDirty = false;
        refreshData({ forceRender: true }).catch(e => showToast(e.message, 'warn'));
    });
    window.addEventListener('hashchange', render);

    $('#global-search')?.addEventListener('keydown', e => {
        if (e.key !== 'Enter') return;
        e.preventDefault();
        const q = e.target.value.trim();
        if (!q) {
            location.hash = '#/home';
            render();
            return;
        }
        if (resolveSearchNav(q)) return;
        location.hash = '#/search';
        render();
    });

    $('#global-search')?.addEventListener('search', e => {
        if (!e.target.value.trim()) {
            location.hash = '#/home';
            render();
        }
    });

    $('#nav-toggle')?.addEventListener('click', () => $('#sf-nav').classList.toggle('open'));

    $$('[data-close]').forEach(btn => btn.addEventListener('click', () => $('#activity-dialog')?.close()));

    $('#activity-form')?.addEventListener('submit', async e => {
        e.preventDefault();
        const submitBtn = $('#activity-save-btn');
        const subject = $('#act-subject')?.value?.trim();
        if (!subject) {
            showToast('Bitte Betreff eingeben', 'warn');
            $('#act-subject')?.focus();
            return;
        }
        if (submitBtn) submitBtn.disabled = true;
        try {
            const type = $('#act-type').value;
            const res = await api('/api/crm/activity', {
                method: 'POST',
                body: JSON.stringify({
                    type,
                    related_type: $('#act-related-type').value,
                    related_id: $('#act-related-id').value,
                    subject,
                    due: $('#act-due').value,
                    description: $('#act-desc').value,
                    sync_termin: type === 'Event',
                }),
            });
            if (!res.ok) throw new Error(res.error || 'Speichern fehlgeschlagen');
            $('#activity-dialog').close();
            showSaved();
            await refreshData({ silent: true });
            render();
        } catch (err) {
            showToast(err.message, 'warn');
        } finally {
            if (submitBtn) submitBtn.disabled = false;
        }
    });

    if (secret()) {
        loadData().then(() => {
            showApp();
            startAutoSync();
            setSyncUI('live', 'Live');
            render();
        }).catch(showLogin);
    } else {
        showLogin();
    }
})();
