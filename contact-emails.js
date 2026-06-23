/* Professionelle E-Mail-Vorlagen für FormSubmit (Admin + Kunden-Bestätigung) */
(function (global) {
    'use strict';

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

    function roleLabel(role) {
        return ROLE_LABELS[role] || role;
    }

    function roleBadge(role) {
        return role === 'unternehmen' ? 'AUFTRAGNEHMER' : 'AUFTRAGGEBER';
    }

    function detailRows(payload, role) {
        const fields = role === 'bauherr' ? BAUHER_FIELDS : UNTERNEHMEN_FIELDS;
        return fields
            .map(([label, key]) => {
                const v = val(payload[key]);
                return `<tr>
          <td style="padding:10px 14px;background:#141414;color:#737373;font-family:Arial,sans-serif;font-size:11px;letter-spacing:0.12em;text-transform:uppercase;width:38%;border-bottom:1px solid #262626">${esc(label)}</td>
          <td style="padding:10px 14px;background:#0a0a0a;color:#f5f5f5;font-family:Arial,sans-serif;font-size:14px;border-bottom:1px solid #262626">${esc(v)}</td>
        </tr>`;
            })
            .join('');
    }

    function buildAdminLeadEmail(payload, role) {
        const ts = nowDe();
        const label = roleLabel(role);
        const badge = roleBadge(role);
        const sectionTitle =
            role === 'bauherr' ? 'Projektdetails' : 'Unternehmensprofil';

        const subject = `[LEAD · ${badge}] ${payload.name} — ${BRAND}`;

        const textLines = [
            `NEUE LEAD-ANFRAGE — ${BRAND}`,
            `Eingegangen: ${ts}`,
            '',
            `Anfrageart: ${label}`,
            `Name: ${payload.name}`,
            `E-Mail: ${payload.email}`,
            `Telefon: ${val(payload.phone)}`,
            `Firma: ${val(payload.company)}`,
            '',
            `— ${sectionTitle.toUpperCase()} —`,
        ];

        const fields = role === 'bauherr' ? BAUHER_FIELDS : UNTERNEHMEN_FIELDS;
        fields.forEach(([l, k]) => textLines.push(`${l}: ${val(payload[k])}`));
        textLines.push('', 'Zusätzliche Angaben:', payload.message || '—', '', `Antworten an: ${payload.email}`);

        const html = `<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f0f0f0">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f0f0f0;padding:28px 12px">
<tr><td align="center">
<table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width:600px;width:100%;background:#0a0a0a">

<tr><td style="padding:28px 32px 20px;border-bottom:1px solid #262626">
  <p style="margin:0 0 8px;font-family:Arial,sans-serif;font-size:10px;letter-spacing:0.35em;text-transform:uppercase;color:${GOLD}">${esc(BRAND)}</p>
  <p style="margin:0;font-family:Georgia,'Times New Roman',serif;font-size:22px;color:#f5f5f5;font-weight:400">Neue Lead-Anfrage</p>
  <p style="margin:12px 0 0;font-family:Arial,sans-serif;font-size:12px;color:#737373">${esc(ts)}</p>
  <span style="display:inline-block;margin-top:14px;padding:6px 12px;background:#1a1a1a;border:1px solid ${GOLD};color:${GOLD};font-family:Arial,sans-serif;font-size:10px;letter-spacing:0.2em">${esc(badge)}</span>
</td></tr>

<tr><td style="padding:24px 32px">
  <p style="margin:0 0 16px;font-family:Arial,sans-serif;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:${GOLD}">Kontakt</p>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #262626">
    <tr><td style="padding:10px 14px;background:#141414;color:#737373;font-family:Arial,sans-serif;font-size:11px;width:38%">Anfrageart</td>
        <td style="padding:10px 14px;background:#0a0a0a;color:#f5f5f5;font-family:Arial,sans-serif;font-size:14px">${esc(label)}</td></tr>
    <tr><td style="padding:10px 14px;background:#141414;color:#737373;font-family:Arial,sans-serif;font-size:11px">Name</td>
        <td style="padding:10px 14px;background:#0a0a0a;color:#f5f5f5;font-family:Arial,sans-serif;font-size:14px"><strong>${esc(payload.name)}</strong></td></tr>
    <tr><td style="padding:10px 14px;background:#141414;color:#737373;font-family:Arial,sans-serif;font-size:11px">E-Mail</td>
        <td style="padding:10px 14px;background:#0a0a0a;font-family:Arial,sans-serif;font-size:14px"><a href="mailto:${esc(payload.email)}" style="color:${GOLD};text-decoration:none">${esc(payload.email)}</a></td></tr>
    <tr><td style="padding:10px 14px;background:#141414;color:#737373;font-family:Arial,sans-serif;font-size:11px">Telefon</td>
        <td style="padding:10px 14px;background:#0a0a0a;color:#f5f5f5;font-family:Arial,sans-serif;font-size:14px">${esc(val(payload.phone))}</td></tr>
    <tr><td style="padding:10px 14px;background:#141414;color:#737373;font-family:Arial,sans-serif;font-size:11px">Firma</td>
        <td style="padding:10px 14px;background:#0a0a0a;color:#f5f5f5;font-family:Arial,sans-serif;font-size:14px">${esc(val(payload.company))}</td></tr>
  </table>
</td></tr>

<tr><td style="padding:0 32px 24px">
  <p style="margin:0 0 12px;font-family:Arial,sans-serif;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:${GOLD}">${esc(sectionTitle)}</p>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #262626">
    ${detailRows(payload, role)}
  </table>
</td></tr>

<tr><td style="padding:0 32px 28px">
  <p style="margin:0 0 10px;font-family:Arial,sans-serif;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:${GOLD}">Nachricht</p>
  <p style="margin:0;padding:16px 18px;background:#141414;border-left:3px solid ${GOLD};color:#d4d4d4;font-family:Arial,sans-serif;font-size:14px;line-height:1.65;white-space:pre-wrap">${esc(payload.message || '—')}</p>
</td></tr>

<tr><td style="padding:20px 32px;background:#141414;border-top:1px solid #262626">
  <p style="margin:0;font-family:Arial,sans-serif;font-size:12px;color:#737373">Direkt antworten: <a href="mailto:${esc(payload.email)}" style="color:${GOLD}">${esc(payload.email)}</a></p>
</td></tr>

</table>
</td></tr>
</table>
</body></html>`;

        return { subject, text: textLines.join('\n'), html };
    }

    function buildCustomerConfirmationEmail(payload, role) {
        const ts = nowDe();
        const label = roleLabel(role);
        const name = payload.name;
        const subject = `Ihre Anfrage bei ${BRAND} — Eingang bestätigt`;

        const summary = [];
        summary.push(`Anfrageart: ${label}`);
        if (role === 'bauherr') {
            if (payload.project) summary.push(`Projektart: ${payload.project}`);
            if (payload.location) summary.push(`Standort: ${payload.location}`);
            if (payload.timeline) summary.push(`Geplanter Start: ${payload.timeline}`);
        } else {
            if (payload.company_name) summary.push(`Unternehmen: ${payload.company_name}`);
            if (payload.trades) summary.push(`Gewerke: ${payload.trades}`);
            if (payload.region) summary.push(`Einsatzgebiet: ${payload.region}`);
        }

        const summaryText = summary.map((l) => `  • ${l}`).join('\n');
        const summaryHtml = summary
            .map((l) => `<li style="margin-bottom:8px;color:#d4d4d4">${esc(l)}</li>`)
            .join('');

        const text = `Sehr geehrte/r ${name},

vielen Dank für Ihre Anfrage bei ${BRAND}.

Wir bestätigen den Eingang Ihrer Nachricht am ${ts}. Ein fachkundiger Ansprechpartner meldet sich zeitnah persönlich bei Ihnen.

Ihre Angaben im Überblick:
${summaryText}

Bei Rückfragen:
E-Mail: ${REPLY_EMAIL}
Telefon: ${PHONE}

Mit freundlichen Grüßen
${BRAND}
www.kaplan-solutions.onrender.com

—
Diese E-Mail wurde automatisch erstellt.`;

        const html = `<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f0f0f0">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f0f0f0;padding:32px 16px">
<tr><td align="center">
<table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width:600px;width:100%;background:#0a0a0a">

<tr><td style="padding:40px 40px 24px;border-bottom:1px solid #262626">
  <p style="margin:0;font-family:Arial,sans-serif;font-size:11px;letter-spacing:0.35em;text-transform:uppercase;color:${GOLD}">${esc(BRAND)}</p>
  <p style="margin:10px 0 0;font-family:Georgia,'Times New Roman',serif;font-size:22px;color:#f5f5f5">Eingang Ihrer Anfrage bestätigt</p>
</td></tr>

<tr><td style="padding:32px 40px;font-family:Arial,sans-serif;font-size:15px;line-height:1.75;color:#d4d4d4">
  <p style="margin:0 0 20px;color:#f5f5f5">Sehr geehrte/r ${esc(name)},</p>
  <p style="margin:0 0 20px">vielen Dank für Ihr Vertrauen in <strong style="color:#f5f5f5">${esc(BRAND)}</strong>. Wir bestätigen den Eingang Ihrer Anfrage am <strong style="color:${GOLD}">${esc(ts)}</strong>.</p>
  <p style="margin:0 0 28px">Ihre Angaben wurden an unser Team weitergeleitet. Ein Ansprechpartner meldet sich <strong style="color:#f5f5f5">zeitnah persönlich</strong> bei Ihnen.</p>

  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#141414;border:1px solid #262626;margin-bottom:28px">
  <tr><td style="padding:20px 24px">
    <p style="margin:0 0 12px;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:${GOLD}">Ihre Angaben im Überblick</p>
    <ul style="margin:0;padding-left:18px;font-size:14px;line-height:1.6">${summaryHtml}</ul>
  </td></tr>
  </table>

  <p style="margin:0 0 8px;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:#737373">Kontakt</p>
  <p style="margin:0;font-size:14px;color:#a3a3a3">
    E-Mail: <a href="mailto:${esc(REPLY_EMAIL)}" style="color:${GOLD};text-decoration:none">${esc(REPLY_EMAIL)}</a><br>
    Telefon: <span style="color:#f5f5f5">${esc(PHONE)}</span>
  </p>
</td></tr>

<tr><td style="padding:24px 40px 40px;border-top:1px solid #262626;font-family:Arial,sans-serif;font-size:13px;color:#737373">
  <p style="margin:0 0 4px;color:#a3a3a3">Mit freundlichen Grüßen</p>
  <p style="margin:0;font-family:Georgia,serif;font-size:16px;color:#f5f5f5">${esc(BRAND)}</p>
  <p style="margin:16px 0 0;font-size:11px;color:#525252">Diese Nachricht wurde automatisch erstellt. Für Rückfragen: ${esc(REPLY_EMAIL)}</p>
</td></tr>

</table>
</td></tr>
</table>
</body></html>`;

        return { subject, text, html };
    }

    global.KaplanContactEmails = {
        buildAdminLeadEmail,
        buildCustomerConfirmationEmail,
        roleLabel,
        nowDe,
    };
})(typeof window !== 'undefined' ? window : globalThis);
