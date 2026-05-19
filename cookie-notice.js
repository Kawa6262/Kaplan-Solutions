/* Kaplan Solutions — Cookie-Hinweis (kein Tracking) */
(function () {
    'use strict';

    const STORAGE_KEY = 'ks_cookie_notice_v1';
    const notice = document.getElementById('cookieNotice');
    const acceptBtn = document.getElementById('cookieNoticeAccept');

    if (!notice || !acceptBtn) return;

    function dismiss() {
        notice.classList.remove('is-visible');
        notice.setAttribute('aria-hidden', 'true');
        try {
            localStorage.setItem(STORAGE_KEY, '1');
        } catch (_) {
            /* private browsing */
        }
        setTimeout(() => {
            notice.hidden = true;
        }, 400);
    }

    acceptBtn.addEventListener('click', dismiss);

    try {
        if (localStorage.getItem(STORAGE_KEY) === '1') {
            notice.hidden = true;
            return;
        }
    } catch (_) {
        /* ignore */
    }

    notice.hidden = false;
    requestAnimationFrame(() => {
        notice.classList.add('is-visible');
        notice.setAttribute('aria-hidden', 'false');
    });
})();
