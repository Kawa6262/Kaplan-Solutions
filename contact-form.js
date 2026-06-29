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
    const fileInput = document.getElementById('attachments');
    const fileList = document.getElementById('fileList');
    const fileUpload = document.getElementById('fileUpload');

    const MAX_FILES = 3;
    const MAX_FILE_BYTES = 8 * 1024 * 1024;
    const MAX_TOTAL_BYTES = 15 * 1024 * 1024;
    const ALLOWED_EXT = ['.pdf', '.jpg', '.jpeg', '.png', '.webp', '.heic', '.doc', '.docx', '.xls', '.xlsx'];
    let selectedFiles = [];

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

    const urlParams = new URLSearchParams(window.location.search);
    const roleParam = urlParams.get('role');
    if (roleParam === 'bauherr' || roleParam === 'unternehmen') {
        setRole(roleParam);
    }
    if (document.body.dataset.formRole === 'bauherr') {
        setRole('bauherr');
    }

    function utmFields() {
        const keys = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'gclid'];
        const out = {};
        keys.forEach((k) => {
            const v = urlParams.get(k);
            if (v) out[k] = v;
        });
        return out;
    }

    function formatBytes(n) {
        if (n < 1024 * 1024) return Math.round(n / 1024) + ' KB';
        return (n / (1024 * 1024)).toFixed(1) + ' MB';
    }

    function fileExt(name) {
        const i = (name || '').lastIndexOf('.');
        return i >= 0 ? name.slice(i).toLowerCase() : '';
    }

    function renderFileList() {
        if (!fileList) return;
        fileList.innerHTML = '';
        if (!selectedFiles.length) {
            fileList.hidden = true;
            return;
        }
        fileList.hidden = false;
        selectedFiles.forEach((file, idx) => {
            const li = document.createElement('li');
            li.className = 'file-upload-item';
            li.innerHTML =
                '<span class="file-upload-item-name"></span>' +
                '<span class="file-upload-item-size"></span>' +
                '<button type="button" class="file-upload-remove" aria-label="Datei entfernen">×</button>';
            li.querySelector('.file-upload-item-name').textContent = file.name;
            li.querySelector('.file-upload-item-size').textContent = formatBytes(file.size);
            li.querySelector('.file-upload-remove').addEventListener('click', () => {
                selectedFiles = selectedFiles.filter((f) => f !== file);
                renderFileList();
            });
            fileList.appendChild(li);
        });
    }

    function addFiles(fileListLike) {
        const incoming = Array.from(fileListLike || []);
        if (!incoming.length) return null;
        const merged = selectedFiles.slice();
        for (const file of incoming) {
            const ext = fileExt(file.name);
            if (!ALLOWED_EXT.includes(ext)) {
                return `Dateityp nicht erlaubt: ${file.name}`;
            }
            if (file.size > MAX_FILE_BYTES) {
                return `Datei zu groß (max. 8 MB): ${file.name}`;
            }
            if (merged.length >= MAX_FILES) {
                return `Maximal ${MAX_FILES} Dateien erlaubt.`;
            }
            merged.push(file);
        }
        let total = merged.reduce((s, f) => s + f.size, 0);
        if (total > MAX_TOTAL_BYTES) {
            return 'Anhänge gesamt zu groß (max. 15 MB).';
        }
        selectedFiles = merged;
        renderFileList();
        if (fileInput) fileInput.value = '';
        return null;
    }

    if (fileInput) {
        fileInput.addEventListener('change', () => {
            const err = addFiles(fileInput.files);
            if (err && formError) {
                formError.textContent = err;
                formError.hidden = false;
            } else if (formError) {
                formError.hidden = true;
            }
        });
    }

    if (fileUpload) {
        ['dragenter', 'dragover'].forEach((ev) => {
            fileUpload.addEventListener(ev, (e) => {
                e.preventDefault();
                fileUpload.classList.add('is-dragover');
            });
        });
        ['dragleave', 'drop'].forEach((ev) => {
            fileUpload.addEventListener(ev, (e) => {
                e.preventDefault();
                fileUpload.classList.remove('is-dragover');
            });
        });
        fileUpload.addEventListener('drop', (e) => {
            const err = addFiles(e.dataTransfer?.files);
            if (err && formError) {
                formError.textContent = err;
                formError.hidden = false;
            }
        });
    }

    function readFileBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
                const result = reader.result || '';
                const base64 = String(result).split(',')[1] || '';
                resolve(base64);
            };
            reader.onerror = () => reject(new Error('Datei konnte nicht gelesen werden.'));
            reader.readAsDataURL(file);
        });
    }

    async function filesToAttachments() {
        const out = [];
        for (const file of selectedFiles) {
            out.push({
                filename: file.name,
                content: await readFileBase64(file),
            });
        }
        return out;
    }

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
            callback_slot: get('callback_slot'),
            message: get('message'),
            company_website: get('company_website'),
            privacy_consent: Boolean(form.querySelector('#privacyConsent')?.checked),
            lead_source:
                get('lead_source') ||
                (urlParams.get('utm_source') === 'whatsapp'
                    ? 'whatsapp-empfehlung'
                    : document.body.dataset.formRole === 'bauherr'
                      ? 'bauherr-landing'
                      : 'website'),
            ...utmFields(),
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

    function friendlyNetworkError(err) {
        const msg = err?.message || '';
        if (/failed|network|abort|timeout|load/i.test(msg)) {
            return (
                'Verbindung unterbrochen. Bitte erneut senden — oder rufen Sie uns an: ' + PHONE
            );
        }
        return msg || 'Anfrage konnte nicht gesendet werden.';
    }

    /* ---------- Weg 1: Server (Resend) — schöne HTML-Mails ---------- */
    async function sendViaServer(payload, attempt = 1) {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 45000);
        try {
            const res = await fetch('/api/contact', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
                body: JSON.stringify(payload),
                signal: controller.signal,
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok && data.error) {
                throw new Error(data.error);
            }
            if (res.ok && data.ok) {
                return { ok: true, ref: data.ref || null };
            }
            return { ok: false, ref: null };
        } catch (err) {
            if (attempt < 2 && /failed|network|abort|timeout|load/i.test(err?.message || '')) {
                await new Promise((r) => setTimeout(r, 1200));
                return sendViaServer(payload, attempt + 1);
            }
            if (err.message && !/failed|network|abort|timeout|load/i.test(err.message)) {
                throw err;
            }
            return { ok: false, ref: null, networkError: true };
        } finally {
            clearTimeout(timer);
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
        if (payload.lead_source) {
            body['Quelle'] = payload.lead_source;
        }
        const utmParts = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'gclid']
            .filter((k) => payload[k])
            .map((k) => `${k}=${payload[k]}`);
        if (utmParts.length) {
            body['Marketing'] = utmParts.join(' · ');
        }
        if (payload.attachment_names?.length) {
            body['Anhänge'] =
                payload.attachment_names.join(', ') +
                ' (im Notfallmodus nicht übermittelt — bitte erneut senden)';
        }
        return body;
    }

    function buildCustomerText(payload, role) {
        const label = ROLE_LABELS[role] || role;
        const lines = [
            `Sehr geehrte/r ${payload.name},`,
            '',
            'vielen Dank für Ihre Anfrage bei Kaplan Solutions.',
            `Wir bestätigen den Eingang am ${nowDe()}.`,
            'Ein Ansprechpartner meldet sich zeitnah persönlich bei Ihnen.',
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
        let serverResult = { ok: false, ref: null };
        try {
            serverResult = await sendViaServer(payload);
            if (serverResult.ok) return serverResult.ref;
        } catch (err) {
            if (payload.attachments?.length) {
                throw new Error(
                    err.message ||
                        'Anfrage mit Anhängen konnte nicht gesendet werden. Bitte rufen Sie uns an.'
                );
            }
            throw err;
        }
        if (payload.attachments?.length) {
            throw new Error(
                'Anhänge konnten nicht übermittelt werden. Bitte senden Sie uns die Dateien per E-Mail an ' +
                    REPLY_EMAIL
            );
        }
        try {
            await sendViaFormSubmit(payload, role);
            return null;
        } catch (err) {
            if (serverResult.networkError) {
                throw new Error(friendlyNetworkError(err));
            }
            throw new Error(friendlyNetworkError(err));
        }
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

            if (selectedFiles.length) {
                try {
                    payload.attachments = await filesToAttachments();
                    payload.attachment_names = selectedFiles.map((f) => f.name);
                } catch {
                    if (formError) {
                        formError.textContent = 'Dateien konnten nicht gelesen werden.';
                        formError.hidden = false;
                    }
                    return;
                }
            }

            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.classList.add('is-loading');
            }

            try {
                const ref = await sendInquiry(payload, role);

                form.querySelectorAll('.form-group, .form-row, .form-footer, .role-panel').forEach((el) => {
                    el.style.display = 'none';
                });
                if (formSuccess) {
                    if (ref) {
                        formSuccess.innerHTML =
                            '<strong>Vielen Dank!</strong> Ihre Anfrage wurde erfolgreich übermittelt.' +
                            ' Ihre Anfrage-Nr. lautet: <strong>' + ref + '</strong>.' +
                            ' Sie erhalten in Kürze eine Bestätigung per E-Mail.' +
                            ' Unser Team meldet sich zeitnah persönlich bei Ihnen.';
                    }
                    formSuccess.hidden = false;
                }
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
