/* Kontaktformular — FormSubmit (Admin + Kunden-Bestätigung), Rollenwahl, professionelle E-Mails */
(function () {
    'use strict';

    const NOTIFY_EMAIL = 'Kawa.f.Kaplan@gmail.com';
    const emails = window.KaplanContactEmails;
    if (!emails) return;

    const form = document.getElementById('contactForm');
    if (!form) return;

    const formError = document.getElementById('formError');
    const formSuccess = document.getElementById('formSuccess');
    const submitBtn = document.getElementById('submitBtn');

    function getRoleInput(root) {
        return (root || document).querySelector('#role');
    }

    function getPanel(root, role) {
        return (root || document).getElementById(
            role === 'bauherr' ? 'panel-bauherr' : 'panel-unternehmen'
        );
    }

    function initRoleSwitcher(root) {
        const scope = root || form;
        const roleInput = getRoleInput(scope);
        const roleTabs = scope.querySelectorAll('.role-tab');
        const panelBauherr = getPanel(scope, 'bauherr');
        const panelUnternehmen = getPanel(scope, 'unternehmen');

        function setRole(role) {
            if (roleInput) roleInput.value = role;

            roleTabs.forEach((t) => {
                t.classList.toggle('is-active', t.dataset.role === role);
            });

            if (panelBauherr) {
                const show = role === 'bauherr';
                panelBauherr.classList.toggle('is-active', show);
                panelBauherr.hidden = !show;
            }
            if (panelUnternehmen) {
                const show = role === 'unternehmen';
                panelUnternehmen.classList.toggle('is-active', show);
                panelUnternehmen.hidden = !show;
            }
        }

        roleTabs.forEach((tab) => {
            tab.addEventListener('click', () => {
                setRole(tab.dataset.role || 'bauherr');
            });
        });

        const current = roleInput?.value || 'bauherr';
        setRole(current);
        return setRole;
    }

    function getRequiredFields(role, root) {
        const panel = getPanel(root, role);
        if (!panel) return [];
        const attr =
            role === 'bauherr' ? 'data-required-bauherr' : 'data-required-unternehmen';
        return Array.from(panel.querySelectorAll(`[${attr}]`));
    }

    function collectPayload(role, root) {
        const scope = root || document;
        const get = (id) => scope.querySelector(`#${id}`)?.value?.trim() || '';

        const base = {
            role,
            name: get('name'),
            email: get('email'),
            phone: get('phone'),
            company: get('company'),
            message: get('message'),
            privacy_consent: Boolean(scope.querySelector('#privacyConsent')?.checked),
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
                headers: {
                    'Content-Type': 'application/json',
                    Accept: 'application/json',
                },
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
        const mail = emails.buildAdminLeadEmail(payload, role);
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
        const mail = emails.buildCustomerConfirmationEmail(payload, role);

        try {
            const res = await fetch('/api/send-confirmation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
                body: JSON.stringify({ ...payload, role }),
            });
            if (res.ok) return;
        } catch {
            /* Server nicht erreichbar — FormSubmit-Fallback */
        }

        await postFormSubmit({
            name: BRAND_NAME(),
            email: NOTIFY_EMAIL,
            _subject: mail.subject,
            _cc: payload.email,
            _captcha: 'false',
            message: mail.html,
        });
    }

    function BRAND_NAME() {
        return 'Kaplan Solutions';
    }

    const clone = form.cloneNode(true);
    form.replaceWith(clone);
    clone.classList.add('is-visible');
    clone.querySelectorAll('.reveal').forEach((el) => el.classList.add('is-visible'));

    const setRole = initRoleSwitcher(clone);

    clone.addEventListener('submit', async (e) => {
        e.preventDefault();
        e.stopImmediatePropagation();

        if (formError) {
            formError.hidden = true;
            formError.textContent = '';
        }

        const roleInput = getRoleInput(clone);
        const role = roleInput?.value || 'bauherr';
        let ok = true;

        ['name', 'email', 'message'].forEach((id) => {
            const el = clone.querySelector(`#${id}`);
            if (!el?.value.trim()) {
                el.style.borderColor = '#dc2626';
                ok = false;
            } else {
                el.style.borderColor = '';
            }
        });

        getRequiredFields(role, clone).forEach((el) => {
            if (!el.value.trim()) {
                el.style.borderColor = '#dc2626';
                ok = false;
            } else {
                el.style.borderColor = '';
            }
        });

        if (!clone.querySelector('#privacyConsent')?.checked) ok = false;

        if (!ok) {
            if (formError) {
                formError.textContent = 'Bitte alle Pflichtfelder ausfüllen.';
                formError.hidden = false;
            }
            return;
        }

        const payload = collectPayload(role, clone);

        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.classList.add('is-loading');
        }

        try {
            await sendAdminLead(payload, role);
            try {
                await sendCustomerConfirmation(payload, role);
            } catch (confirmErr) {
                console.warn('Kunden-Bestätigung:', confirmErr);
            }

            clone
                .querySelectorAll('.form-group, .form-row, .form-footer, .role-panel')
                .forEach((el) => {
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

    clone.querySelectorAll('input, textarea, select').forEach((field) => {
        field.addEventListener('input', () => {
            field.style.borderColor = '';
            if (formError) formError.hidden = true;
        });
    });

    if (typeof setRole === 'function') {
        setRole(getRoleInput(clone)?.value || 'bauherr');
    }
})();
