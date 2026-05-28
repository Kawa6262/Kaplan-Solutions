/**
 * Kaplan Solutions — Kontaktformular (eine Datei, keine Abhängigkeiten)
 * Rollenwahl, FormSubmit, professionelle E-Mails
 */
(function () {
    'use strict';

    const NOTIFY_EMAIL = 'Kawa.f.Kaplan@gmail.com';
    const BRAND = 'Kaplan Solutions';
    const GOLD = '#b87333';
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

    function esc(s) {
        return String(s ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

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

    function buildAdminLeadEmail(payload, role) {
        const ts = nowDe();
        const label = ROLE_LABELS[role] || role;
        const badge = roleBadge(role);
        const sectionTitle = role === 'bauherr' ? 'Projektdetails' : 'Unternehmensprofil';
        const fields = role === 'bauherr' ? BAUHER_FIELDS : UNTERNEHMEN_FIELDS;

        const detailRows = fields
            .map(([lbl, key]) => {
                return `<tr>
          <td style="padding:10px 14px;background:#141414;color:#737373;font-family:Arial,sans-serif;font-size:11px;letter-spacing:0.12em;text-transform:uppercase;width:38%;border-bottom:1px solid #262626">${esc(lbl)}</td>
          <td style="padding:10px 14px;background:#0a0a0a;color:#f5f5f5;font-family:Arial,sans-serif;font-size:14px;border-bottom:1px solid #262626">${esc(val(payload[key]))}</td>
        </tr>`;
            })
            .join('');

        const subject = `[LEAD · ${badge}] ${payload.name} — ${BRAND}`;
        const html = `<!DOCTYPE html><html lang="de"><body style="margin:0;padding:0;background:#f0f0f0">
<table role="presentation" width="100%" style="background:#f0f0f0;padding:28px 12px"><tr><td align="center">
<table role="presentation" width="600" style="max-width:600px;width:100%;background:#0a0a0a">
<tr><td style="padding:28px 32px 20px;border-bottom:1px solid #262626">
  <p style="margin:0 0 8px;font-family:Arial,sans-serif;font-size:10px;letter-spacing:0.35em;text-transform:uppercase;color:${GOLD}">${esc(BRAND)}</p>
  <p style="margin:0;font-family:Georgia,serif;font-size:22px;color:#f5f5f5">Neue Lead-Anfrage</p>
  <p style="margin:12px 0 0;font-family:Arial,sans-serif;font-size:12px;color:#737373">${esc(ts)}</p>
  <span style="display:inline-block;margin-top:14px;padding:6px 12px;border:1px solid ${GOLD};color:${GOLD};font-family:Arial,sans-serif;font-size:10px;letter-spacing:0.2em">${esc(badge)}</span>
</td></tr>
<tr><td style="padding:24px 32px">
  <table role="presentation" width="100%" style="border:1px solid #262626">
    <tr><td style="padding:10px 14px;background:#141414;color:#737373;font-size:11px;width:38%">Anfrageart</td>
        <td style="padding:10px 14px;background:#0a0a0a;color:#f5f5f5;font-size:14px">${esc(label)}</td></tr>
    <tr><td style="padding:10px 14px;background:#141414;color:#737373;font-size:11px">Name</td>
        <td style="padding:10px 14px;background:#0a0a0a;color:#f5f5f5;font-size:14px"><strong>${esc(payload.name)}</strong></td></tr>
    <tr><td style="padding:10px 14px;background:#141414;color:#737373;font-size:11px">E-Mail</td>
        <td style="padding:10px 14px;background:#0a0a0a;font-size:14px"><a href="mailto:${esc(payload.email)}" style="color:${GOLD}">${esc(payload.email)}</a></td></tr>
    <tr><td style="padding:10px 14px;background:#141414;color:#737373;font-size:11px">Telefon</td>
        <td style="padding:10px 14px;background:#0a0a0a;color:#f5f5f5;font-size:14px">${esc(val(payload.phone))}</td></tr>
  </table>
</td></tr>
<tr><td style="padding:0 32px 24px">
  <p style="margin:0 0 12px;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:${GOLD}">${esc(sectionTitle)}</p>
  <table role="presentation" width="100%" style="border:1px solid #262626">${detailRows}</table>
</td></tr>
<tr><td style="padding:0 32px 28px">
  <p style="margin:0 0 10px;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:${GOLD}">Nachricht</p>
  <p style="margin:0;padding:16px;background:#141414;border-left:3px solid ${GOLD};color:#d4d4d4;font-size:14px;white-space:pre-wrap">${esc(payload.message || '—')}</p>
</td></tr>
</table></td></tr></table></body></html>`;

        return { subject, html };
    }

    function buildCustomerConfirmationEmail(payload, role) {
        const ts = nowDe();
        const label = ROLE_LABELS[role] || role;
        const summary = [`Anfrageart: ${label}`];
        if (role === 'bauherr') {
            if (payload.project) summary.push(`Projektart: ${payload.project}`);
            if (payload.location) summary.push(`Standort: ${payload.location}`);
        } else {
            if (payload.company_name) summary.push(`Unternehmen: ${payload.company_name}`);
            if (payload.trades) summary.push(`Gewerke: ${payload.trades}`);
        }
        const summaryHtml = summary.map((l) => `<li style="margin-bottom:8px;color:#d4d4d4">${esc(l)}</li>`).join('');
        const subject = `Ihre Anfrage bei ${BRAND} — Eingang bestätigt`;
        const html = `<!DOCTYPE html><html lang="de"><body style="margin:0;background:#f0f0f0">
<table role="presentation" width="100%" style="background:#f0f0f0;padding:32px 16px"><tr><td align="center">
<table role="presentation" width="600" style="max-width:600px;background:#0a0a0a">
<tr><td style="padding:40px;border-bottom:1px solid #262626">
  <p style="margin:0;font-family:Arial,sans-serif;font-size:11px;letter-spacing:0.35em;color:${GOLD}">${esc(BRAND)}</p>
  <p style="margin:10px 0 0;font-family:Georgia,serif;font-size:22px;color:#f5f5f5">Eingang Ihrer Anfrage bestätigt</p>
</td></tr>
<tr><td style="padding:32px 40px;font-family:Arial,sans-serif;font-size:15px;line-height:1.75;color:#d4d4d4">
  <p style="color:#f5f5f5">Sehr geehrte/r ${esc(payload.name)},</p>
  <p>vielen Dank für Ihre Anfrage. Wir bestätigen den Eingang am <strong style="color:${GOLD}">${esc(ts)}</strong>.</p>
  <p>Ein Ansprechpartner meldet sich <strong style="color:#f5f5f5">innerhalb von 24 Stunden</strong> bei Ihnen.</p>
  <ul style="padding-left:18px;margin:24px 0">${summaryHtml}</ul>
  <p>E-Mail: <a href="mailto:${esc(REPLY_EMAIL)}" style="color:${GOLD}">${esc(REPLY_EMAIL)}</a><br>Telefon: ${esc(PHONE)}</p>
</td></tr>
</table></td></tr></table></body></html>`;
        return { subject, html };
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

    async function sendAdminLead(payload, role) {
        const mail = buildAdminLeadEmail(payload, role);
        await postFormSubmit({
            name: payload.name,
            email: payload.email,
            phone: payload.phone || '',
            _subject: mail.subject,
            _replyto: payload.email,
            _captcha: 'false',
            message: mail.html,
        });
    }

    async function sendCustomerConfirmation(payload, role) {
        const mail = buildCustomerConfirmationEmail(payload, role);
        await postFormSubmit({
            name: BRAND,
            email: NOTIFY_EMAIL,
            _subject: mail.subject,
            _cc: payload.email,
            _captcha: 'false',
            message: mail.html,
        });
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
                await sendAdminLead(payload, role);
                try {
                    await sendCustomerConfirmation(payload, role);
                } catch (err) {
                    console.warn('Kunden-Bestätigung:', err);
                }

                form.querySelectorAll('.form-group, .form-row, .form-footer, .role-panel').forEach((el) => {
                    el.style.display = 'none';
                });
                if (formSuccess) formSuccess.hidden = false;
            } catch (err) {
                if (formError) {
                    formError.textContent = err.message || 'Fehler beim Senden.';
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
})();
