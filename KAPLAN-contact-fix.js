/* Kontaktformular — E-Mail direkt an Gmail (FormSubmit), ohne Server/Resend */
(function () {
    'use strict';

    const NOTIFY_EMAIL = 'Kawa.f.Kaplan@gmail.com';
    const form = document.getElementById('contactForm');
    if (!form) return;

    const formError = document.getElementById('formError');
    const formSuccess = document.getElementById('formSuccess');
    const submitBtn = document.getElementById('submitBtn');
    const roleInput = document.getElementById('roleInput');

    function getRequiredFields(role) {
        const panel = document.querySelector(`.role-panel[data-role-panel="${role}"]`);
        if (!panel) return [];
        const attr = role === 'bauherr' ? 'data-required-bauherr' : 'data-required-unternehmen';
        return Array.from(panel.querySelectorAll(`[${attr}]`));
    }

    function collectPayload(role) {
        const get = (id) => document.getElementById(id)?.value?.trim() || '';
        const base = {
            role,
            name: get('name'),
            email: get('email'),
            phone: get('phone'),
            company: get('company'),
            message: get('message'),
            privacy_consent: Boolean(document.getElementById('privacyConsent')?.checked),
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

    function formatText(payload, role) {
        const label =
            role === 'bauherr' ? 'Auftraggeber' : 'Auftragnehmer';
        const lines = [
            `Anfrageart: ${label}`,
            `Name: ${payload.name}`,
            `E-Mail: ${payload.email}`,
            `Telefon: ${payload.phone || '—'}`,
        ];
        if (role === 'bauherr') {
            lines.push(
                `Projekt: ${payload.project || '—'}`,
                `Ort: ${payload.location || '—'}`,
                `Start: ${payload.timeline || '—'}`,
                `Budget: ${payload.budget || '—'}`,
                `Größe: ${payload.project_size || '—'}`,
                `Stand: ${payload.project_status || '—'}`
            );
        } else {
            lines.push(
                `Firma: ${payload.company_name || '—'}`,
                `Gewerke: ${payload.trades || '—'}`,
                `Region: ${payload.region || '—'}`
            );
        }
        lines.push('', payload.message || '');
        return lines.join('\n');
    }

    async function sendEmail(payload, role) {
        const res = await fetch(
            `https://formsubmit.co/ajax/${encodeURIComponent(NOTIFY_EMAIL)}`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
                body: JSON.stringify({
                    name: payload.name,
                    email: payload.email,
                    phone: payload.phone || '',
                    message: formatText(payload, role),
                    _subject: `[Kaplan Solutions] Neue Anfrage — ${payload.name}`,
                    _captcha: 'false',
                    _template: 'table',
                }),
            }
        );
        const data = await res.json().catch(() => ({}));
        if (data.message && /activation/i.test(data.message)) {
            throw new Error('Bitte FormSubmit-Aktivierung in Gmail bestätigen (Link „Activate Form“).');
        }
        if (!res.ok || (data.success !== 'true' && data.success !== true)) {
            throw new Error(data.message || 'Versand fehlgeschlagen.');
        }
    }

    const clone = form.cloneNode(true);
    form.replaceWith(clone);

    clone.addEventListener('submit', async (e) => {
        e.preventDefault();
        e.stopImmediatePropagation();
        if (formError) {
            formError.hidden = true;
            formError.textContent = '';
        }

        const role = roleInput?.value || 'bauherr';
        let ok = true;
        ['name', 'email', 'message'].forEach((id) => {
            const el = document.getElementById(id);
            if (!el?.value.trim()) {
                el.style.borderColor = '#dc2626';
                ok = false;
            }
        });
        getRequiredFields(role).forEach((el) => {
            if (!el.value.trim()) {
                el.style.borderColor = '#dc2626';
                ok = false;
            }
        });
        if (!document.getElementById('privacyConsent')?.checked) ok = false;
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
            await sendEmail(payload, role);
            clone.querySelectorAll('.form-group, .form-row, .form-footer, .role-panel').forEach((el) => {
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
    });
})();
