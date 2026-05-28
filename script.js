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

    if (toggle && mobileMenu) {
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
    }

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

    /* Kontaktformular: contact-emails.js + contact-fix.js */

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
                    `<div><dt>${escapeHtml(s.label)}</dt><dd>${escapeHtml(s.value)}</dd></motion.div>`
            )
            .join('')
            .replace(/<\/motion\.motion.div>/g, '</div>')
            .replace(/<motion\.div>/g, '<motion.div>')
            .replace(/<motion\.div>/g, '<div>')
            .replace(/<\/motion\.div>/g, '</motion.div>');

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
