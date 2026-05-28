/**
 * Kaplan Solutions — Kontaktformular
 *
 * Sicherheitsnetz-Prinzip (Formular funktioniert IMMER):
 *   1. Versuch: Server /api/contact (Resend)  → professionelle HTML-Mails
 *   2. Notfall: FormSubmit                     → Mail kommt trotzdem an
 */
(function () {
    'use strict';

    const NOTIFY_EMAIL = 'Kawa.f.Kaplan@gmail.com';
    const BRAND = 'Kaplan Solutions';
    const REPLY_EMAIL = 'Kawa.f.Kaplan@gmail.com';
    const PHONE = '+49 159 01309199';

    const ROLE_LABELS = {
        bauherr: 'Auftraggeber — sucht Bauunternehmen',
        unternehmen: 'Auftragnehmer — sucht Aufträge / Netzwerk',
    };

    const BAUHER_FIELDS = [
        ['Projektart', 'project'],
        ['Standort', 'location'],
        ['Gewünschter Projektstart', 'timeline'],
        ['Budgetrahmen', 'budget'],
        ['Projektgröße', 'project_size'],
        ['Aktueller Stand', 'project_status'],
    ];

    const UNTERNEHMEN_FIELDS = [
        ['Firmenname', 'company_name'],
        ['Gewerke / Spezialisierung', 'trades'],
        ['Einsatzgebiet', 'region'],
        ['Verfügbare Kapazität', 'capacity'],
        ['Typischer Auftragsumfang', 'order_scope'],
        ['Freie Baukapazität', 'team_capacity'],
        ['Mitarbeiterzahl', 'employees'],
        ['Referenzprojekte', 'references'],
    ];

    function val(v) {
        const t = (v || '').trim();
        return t || '—';
    }

    function nowDe() {
        return new Date().toLocaleString('de-DE', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    }

    function roleBadge(role) {
        return role === 'unternehmen' ? 'AUFTRAGNEHMER' : 'AUFTRAGGEBER';
    }

    const form = document.getElementById('contactForm');
    if (!form) return;

    const formError = document.getElementById('formError');
    const formSuccess = document.getElementById('formSuccess');
    const submitBtn = document.getElementById('submitBtn');
    const roleInput = document.getElementById('role');
    const panelBauherr = document.getElementById('panel-bauherr');
    const panelUnternehmen = document.getElementById('panel-unternehmen');

    form.setAttribute('method', 'post');
    form.setAttribute('action', '#contact');

    function setRole(role) {
        if (roleInput) roleInput.value = role;
        form.querySelectorAll('.role-tab').forEach((tab) => {
            tab.classList.toggle('is-active', tab.dataset.role === role);
            tab.setAttribute('aria-pressed', tab.dataset.role === role ? 'true' : 'false');
        });
        if (panelBauherr) {
            const show = role === 'bauherr';
            panelBauherr.hidden = !show;
            panelBauherr.classList.toggle('is-active', show);
        }
        if (panelUnternehmen) {
            const show = role === 'unternehmen';
            panelUnternehmen.hidden = !show;
            panelUnternehmen.classList.toggle('is-active', show);
        }
    }

    form.querySelectorAll('.role-tab').forEach((tab) => {
        tab.setAttribute('type', 'button');
        tab.addEventListener('click', (e) => {
            e.preventDefault();
            setRole(tab.dataset.role || 'bauherr');
        });
    });

    setRole(roleInput?.value || 'bauherr');

    function getRequiredFields(role) {
        const panel = role === 'bauherr' ? panelBauherr : panelUnternehmen;
        if (!panel) return [];
        const attr = role === 'bauherr' ? 'data-required-bauherr' : 'data-required-unternehmen';
        return Array.from(panel.querySelectorAll(`[${attr}]`));
    }

    function collectPayload(role) {
        const get = (id) => form.querySelector('#' + id)?.value?.trim() || '';
        const base = {
            role,
            name: get('name'),
            email: get('email'),
            phone: get('phone'),
            company: get('company'),
            message: get('message'),
            privacy_consent: Boolean(form.querySelector('#privacyConsent')?.checked),
        };
        if (role === 'bauherr') {
            return {
                ...base,
                project: get('project'),
                location: get('location'),
                timeline: get('timeline'),
                budget: get('budget'),
                project_size: get('project_size'),
                project_status: get('project_status'),
            };
        }
        return {
            ...base,
            company_name: get('company_name'),
            trades: get('trades'),
            region: get('region'),
            capacity: get('capacity'),
            order_scope: get('order_scope'),
            team_capacity: get('team_capacity'),
            employees: get('employees'),
            references: get('references'),
        };
    }

    /* ---------- Weg 1: Server (Resend) — schöne HTML-Mails ---------- */
    async function sendViaServer(payload) {
        try {
            const res = await fetch('/api/contact', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
                body: JSON.stringify(payload),
            });
            const data = await res.json().catch(() => ({}));
            return Boolean(res.ok && data.ok);
        } catch {
            return false;
        }
    }

    /* ---------- Weg 2: FormSubmit — Notfall, kommt immer an ---------- */
    async function postFormSubmit(body) {
        const res = await fetch(
            `https://formsubmit.co/ajax/${encodeURIComponent(NOTIFY_EMAIL)}`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
                body: JSON.stringify(body),
            }
        );
        const data = await res.json().catch(() => ({}));
        if (data.message && /activation/i.test(data.message)) {
            throw new Error(
                'Bitte FormSubmit in Gmail bestätigen (Link „Activate Form“ in der Aktivierungs-Mail).'
            );
        }
        if (!res.ok || (data.success !== 'true' && data.success !== true)) {
            throw new Error(data.message || 'E-Mail-Versand fehlgeschlagen.');
        }
    }

    function buildAdminFields(payload, role) {
        const fields = role === 'bauherr' ? BAUHER_FIELDS : UNTERNEHMEN_FIELDS;
        const body = {
            _subject: `[LEAD · ${roleBadge(role)}] ${payload.name} — ${BRAND}`,
            _template: 'box',
            _replyto: payload.email,
            _captcha: 'false',
            name: payload.name,
            email: payload.email,
            phone: val(payload.phone),
            Anfrageart: ROLE_LABELS[role] || role,
            Eingegangen: nowDe(),
            'Firma / Organisation': val(payload.company),
        };
        fields.forEach(([lbl, key]) => {
            body[lbl] = val(payload[key]);
        });
        body['Zusätzliche Angaben'] = val(payload.message);
        return body;
    }

    function buildCustomerText(payload, role) {
        const label = ROLE_LABELS[role] || role;
        const lines = [
            `Sehr geehrte/r ${payload.name},`,
            '',
            'vielen Dank für Ihre Anfrage bei Kaplan Solutions.',
            `Wir bestätigen den Eingang am ${nowDe()}.`,
            'Ein Ansprechpartner meldet sich in der Regel innerhalb von 24 Stunden persönlich bei Ihnen.',
            '',
            '— Ihre Angaben —',
            `Anfrageart: ${label}`,
        ];
        if (role === 'bauherr') {
            if (payload.project) lines.push(`Projektart: ${payload.project}`);
            if (payload.location) lines.push(`Standort: ${payload.location}`);
        } else {
            if (payload.company_name) lines.push(`Unternehmen: ${payload.company_name}`);
            if (payload.trades) lines.push(`Gewerke: ${payload.trades}`);
        }
        lines.push(
            '',
            '— Kontakt —',
            `E-Mail: ${REPLY_EMAIL}`,
            `Telefon: ${PHONE}`,
            '',
            'Mit freundlichen Grüßen',
            'Kaplan Solutions'
        );
        return {
            subject: `Ihre Anfrage bei ${BRAND} — Eingang bestätigt`,
            text: lines.join('\n'),
        };
    }

    async function sendViaFormSubmit(payload, role) {
        await postFormSubmit(buildAdminFields(payload, role));
        try {
            const c = buildCustomerText(payload, role);
            await postFormSubmit({
                _subject: c.subject,
                _template: 'box',
                _cc: payload.email,
                _captcha: 'false',
                name: BRAND,
                email: NOTIFY_EMAIL,
                message: c.text,
                Hinweis: 'Automatische Bestätigung für den Kunden',
            });
        } catch (err) {
            console.warn('Kunden-Bestätigung (Notfall):', err);
        }
    }

    /* ---------- Versand mit Sicherheitsnetz ---------- */
    async function sendInquiry(payload, role) {
        if (await sendViaServer(payload)) return;
        await sendViaFormSubmit(payload, role);
    }

    form.addEventListener(
        'submit',
        async (e) => {
            e.preventDefault();
            e.stopPropagation();

            if (formError) {
                formError.hidden = true;
                formError.textContent = '';
            }

            const role = roleInput?.value || 'bauherr';
            let ok = true;

            ['name', 'email', 'message'].forEach((id) => {
                const el = form.querySelector('#' + id);
                if (!el?.value.trim()) {
                    if (el) el.style.borderColor = '#dc2626';
                    ok = false;
                } else if (el) {
                    el.style.borderColor = '';
                }
            });

            getRequiredFields(role).forEach((el) => {
                if (!el.value.trim()) {
                    el.style.borderColor = '#dc2626';
                    ok = false;
                } else {
                    el.style.borderColor = '';
                }
            });

            if (!form.querySelector('#privacyConsent')?.checked) ok = false;

            if (!ok) {
                if (formError) {
                    formError.textContent = 'Bitte alle Pflichtfelder ausfüllen.';
                    formError.hidden = false;
                }
                return;
            }

            const payload = collectPayload(role);

            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.classList.add('is-loading');
            }

            try {
                await sendInquiry(payload, role);

                form.querySelectorAll('.form-group, .form-row, .form-footer, .role-panel').forEach((el) => {
                    el.style.display = 'none';
                });
                if (formSuccess) formSuccess.hidden = false;
            } catch (err) {
                if (formError) {
                    formError.textContent =
                        err.message ||
                        'Anfrage konnte nicht gesendet werden. Bitte rufen Sie uns an: ' + PHONE;
                    formError.hidden = false;
                }
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.classList.remove('is-loading');
                }
            }
        },
        true
    );

    form.querySelectorAll('input, textarea, select').forEach((field) => {
        field.addEventListener('input', () => {
            field.style.borderColor = '';
            if (formError) formError.hidden = true;
        });
    });
})();
