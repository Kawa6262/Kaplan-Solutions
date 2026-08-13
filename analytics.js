/* Kaplan Solutions — optionale Google-Ads-Conversion (nur nach Cookie-Zustimmung) */
(function () {
    'use strict';

    const CONSENT_KEY = 'ks_cookie_notice_v1';
    let config = null;
    let loaded = false;

    function hasConsent() {
        try {
            return localStorage.getItem(CONSENT_KEY) === '1';
        } catch (_) {
            return false;
        }
    }

    function loadGtag(id) {
        if (loaded || !id || typeof window.gtag === 'function') return;
        const s = document.createElement('script');
        s.async = true;
        s.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(id);
        document.head.appendChild(s);
        window.dataLayer = window.dataLayer || [];
        window.gtag = function gtag() {
            window.dataLayer.push(arguments);
        };
        window.gtag('js', new Date());
        window.gtag('config', id, { anonymize_ip: true });
        loaded = true;
    }

    function maybeInit() {
        if (!config || !hasConsent()) return;
        if (config.googleAdsId) loadGtag(config.googleAdsId);
    }

    function trackLead(role) {
        if (!config || !hasConsent() || typeof window.gtag !== 'function') return;
        const sendTo = config.googleAdsConversion;
        if (sendTo) {
            window.gtag('event', 'conversion', { send_to: sendTo });
        }
        window.gtag('event', 'generate_lead', {
            event_category: 'contact',
            event_label: role || 'unknown',
        });
    }

    window.KaplanAnalytics = { trackLead: trackLead };

    fetch('/api/site-config', { credentials: 'same-origin' })
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => {
            if (!data) return;
            config = data;
            maybeInit();
        })
        .catch(() => {});

    window.addEventListener('ks:cookie-consent', maybeInit);
})();
