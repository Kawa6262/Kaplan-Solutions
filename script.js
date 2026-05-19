/* Kaplan Solutions — Landing Page Scripts */

(function () {
    'use strict';

    const header = document.getElementById('site-header');
    const onScroll = () => {
        if (window.scrollY > 60) {
            header.classList.remove('is-top');
            header.classList.add('is-scrolled');
        } else {
            header.classList.add('is-top');
            header.classList.remove('is-scrolled');
        }
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();

    const toggle = document.querySelector('.menu-toggle');
    const mobileMenu = document.querySelector('.mobile-menu');

    toggle.addEventListener('click', () => {
        const open = toggle.classList.toggle('is-open');
        mobileMenu.classList.toggle('is-open', open);
        mobileMenu.setAttribute('aria-hidden', !open);
        toggle.setAttribute('aria-expanded', open);
        document.body.style.overflow = open ? 'hidden' : '';
    });

    mobileMenu.querySelectorAll('a').forEach((link) => {
        link.addEventListener('click', () => {
            toggle.classList.remove('is-open');
            mobileMenu.classList.remove('is-open');
            mobileMenu.setAttribute('aria-hidden', 'true');
            toggle.setAttribute('aria-expanded', 'false');
            document.body.style.overflow = '';
        });
    });

    const revealEls = document.querySelectorAll('.reveal');
    const revealObserver = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                    revealObserver.unobserve(entry.target);
                }
            });
        },
        { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
    );
    revealEls.forEach((el) => revealObserver.observe(el));

    document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
        anchor.addEventListener('click', (e) => {
            const target = document.querySelector(anchor.getAttribute('href'));
            if (!target) return;
            e.preventDefault();
            const offset = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--header-h')) || 80;
            const top = target.getBoundingClientRect().top + window.scrollY - offset;
            window.scrollTo({ top, behavior: 'smooth' });
        });
    });

    const roleInput = document.getElementById('role');
    const roleTabs = document.querySelectorAll('.role-tab');
    const panelBauherr = document.getElementById('panel-bauherr');
    const panelUnternehmen = document.getElementById('panel-unternehmen');

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
        tab.addEventListener('click', () => setRole(tab.dataset.role || 'bauherr'));
    });

    function getRequiredFields(role) {
        const panel = role === 'bauherr' ? panelBauherr : panelUnternehmen;
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

    const form = document.getElementById('contactForm');
    const formError = document.getElementById('formError');
    const formSuccess = document.getElementById('formSuccess');
    const submitBtn = document.getElementById('submitBtn');

    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            if (formError) {
                formError.hidden = true;
                formError.textContent = '';
            }

            const role = roleInput ? roleInput.value : 'bauherr';
            let valid = true;
            const missing = [];

            ['name', 'email', 'message'].forEach((id) => {
                const el = document.getElementById(id);
                if (!el?.value.trim()) {
                    el.style.borderColor = '#dc2626';
                    valid = false;
                } else {
                    el.style.borderColor = '';
                }
            });

            getRequiredFields(role).forEach((el) => {
                if (!el.value.trim()) {
                    el.style.borderColor = '#dc2626';
                    valid = false;
                    const label = el.closest('.form-group')?.querySelector('.form-label')?.textContent || 'Feld';
                    missing.push(label.replace(' *', ''));
                } else {
                    el.style.borderColor = '';
                }
            });

            const privacyEl = document.getElementById('privacyConsent');
            const privacyLabel = document.getElementById('privacyConsentLabel');
            if (privacyEl && !privacyEl.checked) {
                valid = false;
                missing.push('Datenschutzerklärung');
                privacyLabel?.classList.add('is-error');
            } else {
                privacyLabel?.classList.remove('is-error');
            }

            if (!valid) {
                if (formError) {
                    formError.textContent = missing.length
                        ? `Bitte ausfüllen: ${missing.slice(0, 3).join(', ')}${missing.length > 3 ? ' …' : ''}`
                        : 'Bitte füllen Sie alle Pflichtfelder aus.';
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
                const res = await fetch('/api/contact', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });

                const data = await res.json().catch(() => ({}));

                if (!res.ok || !data.ok) {
                    throw new Error(data.error || 'Anfrage konnte nicht gesendet werden.');
                }

                form.querySelectorAll('.form-group, .form-row, .form-footer, .role-panel').forEach((el) => {
                    el.style.display = 'none';
                });
                if (formSuccess) formSuccess.hidden = false;
            } catch (err) {
                if (formError) {
                    formError.textContent = err.message || 'Ein Fehler ist aufgetreten.';
                    formError.hidden = false;
                }
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.classList.remove('is-loading');
                }
            }
        });

        form.querySelectorAll('input, textarea, select').forEach((field) => {
            field.addEventListener('input', () => {
                field.style.borderColor = '';
                if (formError) formError.hidden = true;
            });
            field.addEventListener('change', () => {
                field.style.borderColor = '';
                if (field.id === 'privacyConsent') {
                    document.getElementById('privacyConsentLabel')?.classList.remove('is-error');
                }
            });
        });
    }

    setRole('bauherr');

    const yearEl = document.getElementById('year');
    if (yearEl) yearEl.textContent = new Date().getFullYear();

    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function renderReferenceCard(item) {
        const stats = (item.stats || [])
            .map(
                (s) =>
                    `<div><dt>${escapeHtml(s.label)}</dt><dd>${escapeHtml(s.value)}</dd></div>`
            )
            .join('');

        return `
            <article class="reference-card reveal">
                <span class="reference-tag">${escapeHtml(item.tag)}</span>
                <h3>${escapeHtml(item.title)}</h3>
                <p class="reference-location">${escapeHtml(item.location)}</p>
                <p class="reference-desc">${escapeHtml(item.description)}</p>
                <dl class="reference-stats">${stats}</dl>
            </article>`;
    }

    async function loadReferences() {
        const grid = document.getElementById('referencesGrid');
        if (!grid) return;

        try {
            const res = await fetch('/data/references.json');
            if (!res.ok) throw new Error('not found');
            const items = await res.json();
            grid.innerHTML = items.map(renderReferenceCard).join('');
            grid.querySelectorAll('.reveal').forEach((el) => revealObserver.observe(el));
        } catch {
            grid.innerHTML =
                '<p class="references-note">Referenzen werden geladen … Bitte Seite über den lokalen Server öffnen.</p>';
        }
    }

    loadReferences();

})();
