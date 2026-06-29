/**
 * Kaplan Solutions - Lead Intelligence (Sheet + Drive)
 *
 * Tabs: Dashboard, Alle Leads, Auftraggeber, Auftragnehmer, Outreach-Portfolio,
 *       Matches, Top Matches, Seriositaet, Pipeline
 *
 * Auftraggeber / Auftragnehmer = NUR echte Anfragen (Formular, WhatsApp, manuell).
 * Outreach-Portfolio = Firmen, die nur per Cold-Outreach kontaktiert wurden.
 *
 * Erstes Mal / nach Layout-Update:  Funktion "neuAufsetzen" einmal ausfuehren
 * 24/7 Matching:  Funktion "installTriggers" einmal ausfuehren (stuendlich + Briefing 10:00)
 * CRM Upgrade:    Funktion "crmPipelineMigrieren" einmal ausfuehren (neue Pipeline-Spalten)
 * CRM Admin:      kaplan-solutions.de/admin/crm (Secret in _Meta B7 + ADMIN_CRM_SECRET)
 *   (loescht Testdaten + baut alle Tabs sauber & farbig neu auf).
 * Nach jedem Code-Update:  Bereitstellen -> Bereitstellungen verwalten -> Neue Version
 */

var ROOT_FOLDER_NAME = 'Kaplan Leads';
var FOLDER_DASHBOARD = '00_Dashboard';
var FOLDER_AUFTRAGGEBER = '01_Auftraggeber';
var FOLDER_AUFTRAGNEHMER = '02_Auftragnehmer';
var FOLDER_MATCHES = '03_Matches';
var FOLDER_SERIOSITY = '04_Seriosit\u00e4ts-Reports';
var FOLDER_PRUEFEN = '05_Pr\u00fcfen';

var TAB_DASHBOARD = 'Dashboard';
var TAB_ALL = 'Alle Leads';
var TAB_AUFTRAGGEBER = 'Auftraggeber';
var TAB_AUFTRAGNEHMER = 'Auftragnehmer';
var TAB_PORTFOLIO = 'Outreach-Portfolio';
var TAB_MATCHES = 'Matches';
var TAB_TOP_MATCHES = 'Top Matches';
var TAB_SERIOSITY = 'Seriosit\u00e4t';
var TAB_PIPELINE = 'Pipeline';
var TAB_ACTIVITIES = 'CRM Activities';
var META_SHEET = '_Meta';

var SF_OPP_STAGES = [
  'Qualification', 'Needs Analysis', 'Proposal/Price Quote',
  'Negotiation/Review', 'Closed Won', 'Closed Lost'
];

var SF_LEAD_STATUS = [
  'Open - Not Contacted', 'Working - Contacted', 'Closed - Converted', 'Closed - Not Converted'
];

var ACTIVITY_HEADERS = [
  'Activity-ID', 'Bezug-Typ', 'Bezug-ID', 'Typ', 'Betreff',
  'Faellig/Start', 'Ende', 'Status', 'Beschreibung', 'Erstellt'
];

var ACTIVITY_TYPES = ['Task', 'Call', 'Event', 'Email'];
var ACTIVITY_STATUS = ['Not Started', 'In Progress', 'Completed', 'Waiting'];

var MIN_MATCH_SCORE_TAB = 50;
var MIN_MATCH_SCORE_EMAIL = 35;
var MATCH_FOLDER_MIN = 75;
var MATCH_ALERT_MIN = 75;

var TZ = 'Europe/Berlin';

// Farben
var C_HEAD_BG = '#e8e8e8';
var C_HEAD_FG = '#000000';
var C_GREEN = '#b7e1cd';
var C_GREEN2 = '#d9ead3';
var C_YELLOW = '#ffe599';
var C_RED = '#f4a8a8';
var C_BAND = '#f3f6f4';

var LEAD_HEADERS = [
  'Anfrage-Nr.', 'Eingegangen', 'Rolle', 'Name', 'E-Mail', 'Telefon', 'Firma',
  'Branche', 'Stadt', 'PLZ', 'Projekt/Gewerke', 'Standort', 'Zeitrahmen',
  'Budget/Auftragsvolumen', 'Groesse/Kapazitaet', 'Status/Mitarbeiter',
  'Referenzen', 'Nachricht', 'Dateien',
  'Seriosit\u00e4t %', 'Match-Anzahl', 'Pipeline-Status', 'Flags',
  'Bearbeitung', 'Ordner-Link'
];

var MATCH_HEADERS = [
  'Passung', 'Status', 'Auftraggeber', 'Kontakt Auftraggeber',
  'Auftragnehmer', 'Kontakt Auftragnehmer', 'Branche', 'Region',
  'Warum es passt', 'Anfragen', 'Ordner', 'Erstellt', 'Match-ID'
];

var TOP_MATCH_HEADERS = [
  'Rang', 'Prioritaet', 'Passung %', 'Status',
  'Bauherr / Auftraggeber', 'Kontakt AG', 'Anfrage AG',
  'Partner-Firma', 'Kontakt AN', 'Anfrage AN',
  'Region', 'Branche', 'Warum es passt', 'Naechster Schritt', 'Match-ID'
];

var SERIOSITY_HEADERS = [
  'Anfrage-Nr.', 'Firma / Name', 'Score', 'Bewertung', 'Rechtsform',
  'Handelsregister', 'Firmenalter', 'Google-Bewertung', 'Konfidenz',
  'WARN: Warnungen', 'Quellen', 'Report', 'Geprueft am'
];

var PIPELINE_HEADERS = [
  'Anfrage-Nr.', 'Eingegangen', 'Name', 'Rolle', 'Branche', 'Stadt',
  'Stage', 'Seriosit\u00e4t %', 'Matches', 'Best Match %', 'N\u00e4chster Termin',
  'Quelle', 'N\u00e4chster Schritt', 'Vertrag', 'Intro gesendet', 'Netto \u20ac',
  'Provision \u20ac', 'Rechnung', 'Bezahlt', 'Verloren-Grund', 'Notiz', 'Ordner-Link'
];

var MATCH_STATUS_OPTIONS = ['Neu', 'In Kontakt', 'Vermittelt', 'Abgelehnt'];

var BAUHERR_STAGES = [
  'Neu', 'Kontaktiert', 'Erstgespr\u00e4ch geplant', 'Erstgespr\u00e4ch gef\u00fchrt',
  'Qualifiziert', 'Matching l\u00e4uft', 'Match vorgeschlagen', 'Erstkontakt',
  'In Verhandlung', 'Auftrag erteilt', 'Abgeschlossen', 'Verloren / Pause'
];

var PARTNER_STAGES = [
  'Lead', 'Erstgespr\u00e4ch geplant', 'Erstgespr\u00e4ch gef\u00fchrt', 'Vertrag versendet',
  'Vertrag unterschrieben', 'Im Portfolio', 'Match erhalten', 'Auftrag \u00fcber Vermittlung',
  'Provision f\u00e4llig', 'Provision bezahlt', 'Aktiver Partner', 'Verloren / Inaktiv'
];

var CRM_YES_NO = ['Nein', 'Ja'];
var CRM_STAGE_ALL = BAUHERR_STAGES.concat(PARTNER_STAGES.filter(function (s) {
  return BAUHERR_STAGES.indexOf(s) < 0;
}));

// -- Webhook -----------------------------------------------------------------

function doPost(e) {
  try {
    var data = parsePayload_(e);
    if (data.action === 'seriosity_update') {
      return handleSeriosityUpdate_(data);
    }
    if (data.action === 'match_rescan') {
      return handleMatchRescan_(data);
    }
    if (data.action === 'daily_briefing') {
      return handleDailyBriefingRequest_(data);
    }
    if (data.action === 'import_outreach') {
      return handleImportOutreach_(data);
    }
    if (data.action === 'migrate_outreach') {
      return handleMigrateOutreach_(data);
    }
    if (data.action === 'purge_junk') {
      return handlePurgeJunk_(data);
    }
    if (data.action === 'crm_snapshot') {
      return handleCrmSnapshot_(data);
    }
    if (data.action === 'crm_update') {
      return handleCrmUpdate_(data);
    }
    if (data.action === 'crm_activity_create') {
      return handleCrmActivityCreate_(data);
    }
    if (data.action === 'crm_activity_update') {
      return handleCrmActivityUpdate_(data);
    }
    if (data.action === 'crm_opportunity_update') {
      return handleCrmOpportunityUpdate_(data);
    }
    return handleNewLead_(data);
  } catch (err) {
    return jsonResponse_({ ok: false, error: String(err) });
  }
}

function doGet() {
  return jsonResponse_({ ok: true, service: 'Kaplan Solutions Lead Intelligence v2' });
}

function handleNewLead_(data) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ensureStructure_(ss);

  var junk = assessJunkLead_(data);
  if (junk.junk) {
    Logger.log('Junk-Lead verworfen (' + junk.reasons.join(', ') + '): ' + (data.name || data.email || ''));
    return jsonResponse_({
      ok: true,
      skipped: true,
      junk: true,
      reasons: junk.reasons
    });
  }

  var ref = nextRef_(ss);
  var folderUrl = createLeadFolder_(data, ref);
  var allMatches = findAllMatches_(ss, data, ref);
  var emailMatches = allMatches.filter(function (m) { return m.score >= MIN_MATCH_SCORE_EMAIL; }).slice(0, 3);

  var row = buildLeadRow_(data, ref, folderUrl, allMatches.length, '-', 'Pruefung laeuft');

  appendToTab_(ss, TAB_ALL, row);
  if (data.role_code === 'bauherr') {
    appendToTab_(ss, TAB_AUFTRAGGEBER, row);
  } else {
    appendToTab_(ss, TAB_AUFTRAGNEHMER, row);
  }

  writeMatches_(ss, ref, data, allMatches);
  writeSeriosityPending_(ss, ref, data, folderUrl);
  writePipeline_(ss, ref, data, folderUrl, allMatches.length);
  updateDashboard_(ss);

  var hotPairs = buildHotPairsFromNewLead_(ref, data, allMatches);
  var alertResult = processInstantMatchAlerts_(ss, hotPairs);

  return jsonResponse_({
    ok: true,
    ref: ref,
    folder_url: folderUrl,
    matches: emailMatches,
    alerts_sent: alertResult.sent
  });
}

function handleImportOutreach_(data) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ensureStructure_(ss);

  var email = String(data.email || '').trim().toLowerCase();
  if (!email) throw new Error('email fehlt');

  var existing = findLeadByEmail_(ss, email);
  if (existing) {
    return jsonResponse_({
      ok: true,
      skipped: true,
      ref: existing.ref,
      reason: 'duplicate'
    });
  }

  var leadData = {
    role_code: 'unternehmen',
    eingegangen: data.eingegangen || Utilities.formatDate(new Date(), TZ, 'dd.MM.yyyy HH:mm'),
    rolle: 'Auftragnehmer',
    name: data.contact_name || data.firma || 'Outreach-Kontakt',
    email: email,
    telefon: data.telefon || '\u2014',
    firma: data.firma || '',
    branche: data.branche || 'Sonstiges',
    stadt: data.stadt || '-',
    plz: data.plz || '',
    projekt: data.gewerke || data.branche || '',
    standort: data.stadt || '-',
    zeitrahmen: '\u2014',
    budget: '\u2014',
    groesse: '\u2014',
    status_feld: 'Outreach',
    referenzen: '\u2014',
    nachricht: data.nachricht || 'Automatisch aus Outreach-Portfolio importiert.',
    dateien: '\u2014',
    bearbeitung: 'Outreach'
  };

  var ref = nextRef_(ss);
  var folderUrl = createLeadFolder_(leadData, ref);
  var allMatches = findAllMatches_(ss, leadData, ref);

  var row = buildLeadRow_(leadData, ref, folderUrl, allMatches.length, '-', 'Outreach');

  appendToTab_(ss, TAB_PORTFOLIO, row);
  writeMatches_(ss, ref, leadData, allMatches);
  writeSeriosityPending_(ss, ref, leadData, folderUrl);
  updateDashboard_(ss);

  var hotPairs = buildHotPairsFromNewLead_(ref, leadData, allMatches);
  var alertResult = processInstantMatchAlerts_(ss, hotPairs);

  return jsonResponse_({
    ok: true,
    ref: ref,
    folder_url: folderUrl,
    matches: allMatches.length,
    hot: allMatches.filter(function (m) { return m.score >= MATCH_ALERT_MIN; }).length,
    alerts_sent: alertResult.sent,
    source: 'outreach'
  });
}

function findLeadByEmail_(ss, email) {
  var tabs = [TAB_ALL, TAB_AUFTRAGGEBER, TAB_AUFTRAGNEHMER, TAB_PORTFOLIO];
  email = String(email || '').trim().toLowerCase();
  if (!email) return null;

  for (var t = 0; t < tabs.length; t++) {
    var sheet = ss.getSheetByName(tabs[t]);
    if (!sheet || sheet.getLastRow() < 2) continue;
    var values = sheet.getDataRange().getValues();
    var idx = indexMapLead_(values[0]);
    for (var r = 1; r < values.length; r++) {
      var row = values[r];
      var rowMail = String(row[idx.email] || '').trim().toLowerCase();
      if (rowMail && rowMail === email) {
        return { ref: String(row[idx.ref] || ''), tab: tabs[t] };
      }
    }
  }
  return null;
}

function handleSeriosityUpdate_(data) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ensureStructure_(ss);
  var ref = data.ref || '';
  if (!ref) throw new Error('ref fehlt');

  var score = Number(data.score) || 0;
  var status = data.status || 'Geprueft';
  var flags = data.flags || '';
  var details = data.details || '';
  var reportUrl = data.report_url || createSeriosityReport_(ref, data, score, status, flags, details);

  updateLeadSeriosity_(ss, ref, score, flags, status);
  upsertSeriosityRow_(ss, ref, data, score, status, flags, reportUrl);
  updatePipelineSeriosity_(ss, ref, score, flags);
  if (score > 0 && score < 40) {
    moveToPruefenFolder_(ref, data.firma || data.name || '', score, flags);
  }
  updateDashboard_(ss);

  return jsonResponse_({ ok: true, ref: ref, score: score });
}

// -- Struktur ----------------------------------------------------------------

function ensureStructure_(ss) {
  ensureTab_(ss, TAB_DASHBOARD, null);
  ensureTab_(ss, TAB_ALL, LEAD_HEADERS);
  ensureTab_(ss, TAB_AUFTRAGGEBER, LEAD_HEADERS);
  ensureTab_(ss, TAB_AUFTRAGNEHMER, LEAD_HEADERS);
  ensureTab_(ss, TAB_PORTFOLIO, LEAD_HEADERS);
  ensureTab_(ss, TAB_MATCHES, MATCH_HEADERS);
  ensureTab_(ss, TAB_TOP_MATCHES, TOP_MATCH_HEADERS);
  ensureTab_(ss, TAB_SERIOSITY, SERIOSITY_HEADERS);
  ensureTab_(ss, TAB_PIPELINE, PIPELINE_HEADERS);
  ensureTab_(ss, TAB_ACTIVITIES, ACTIVITY_HEADERS);
  ensurePipelineCrm_(ss);
  ensureMeta_(ss);
  ensureRootFolders_();
  restyleAllTabHeaders_(ss);
}

function ensureTab_(ss, name, headers) {
  var sheet = ss.getSheetByName(name);
  var fresh = false;
  if (!sheet) { sheet = ss.insertSheet(name); fresh = true; }
  if (headers && sheet.getLastRow() === 0) {
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    fresh = true;
  }
  if (fresh && headers) {
    styleHeader_(sheet, headers.length);
    sheet.setFrozenRows(1);
    setupAppearance_(sheet, name, headers.length);
  }
}

function styleHeader_(sheet, cols) {
  sheet.getRange(1, 1, 1, cols)
    .setFontWeight('bold')
    .setBackground(C_HEAD_BG)
    .setFontColor(C_HEAD_FG)
    .setVerticalAlignment('middle')
    .setWrap(true);
  sheet.setRowHeight(1, 34);
}

function setupAppearance_(sheet, name, cols) {
  // Zebra-Streifen ab Zeile 2 — Kopfzeile bleibt schwarz auf hellgrau
  try {
    var bandings = sheet.getBandings();
    for (var b = 0; b < bandings.length; b++) {
      bandings[b].remove();
    }
    var lastRow = Math.max(sheet.getLastRow(), 2);
    if (lastRow > 1) {
      sheet.getRange(2, 1, lastRow, cols).applyRowBanding(
        SpreadsheetApp.BandingTheme.LIGHT_GREY, true, false
      );
    }
  } catch (e) {}
  styleHeader_(sheet, cols);

  if (name === TAB_MATCHES) {
    var wM = [70, 110, 170, 200, 170, 200, 130, 130, 260, 150, 90, 130, 0];
    applyWidths_(sheet, wM);
    sheet.hideColumns(13);
    setDropdown_(sheet, 2, MATCH_STATUS_OPTIONS);
  } else if (name === TAB_TOP_MATCHES) {
    var wT = [50, 90, 70, 100, 180, 200, 100, 180, 200, 100, 110, 120, 240, 200, 0];
    applyWidths_(sheet, wT);
    sheet.hideColumns(15);
    setDropdown_(sheet, 4, MATCH_STATUS_OPTIONS);
  } else if (name === TAB_SERIOSITY) {
    var wS = [110, 220, 70, 130, 150, 140, 130, 150, 90, 220, 90, 90, 130];
    applyWidths_(sheet, wS);
  } else if (name === TAB_PIPELINE) {
    var wP = [110, 130, 170, 130, 130, 110, 160, 90, 70, 90, 130, 120, 220, 80, 100, 90, 90, 100, 80, 140, 200, 90];
    applyWidths_(sheet, wP);
    setDropdown_(sheet, 7, CRM_STAGE_ALL);
    setDropdown_(sheet, 14, CRM_YES_NO);
    setDropdown_(sheet, 15, CRM_YES_NO);
    setDropdown_(sheet, 19, CRM_YES_NO);
  } else if (name === TAB_ALL || name === TAB_AUFTRAGGEBER || name === TAB_AUFTRAGNEHMER || name === TAB_PORTFOLIO) {
    sheet.setColumnWidth(1, 110);
    sheet.setColumnWidth(4, 160);
    sheet.setColumnWidth(7, 160);
  }
}

function applyWidths_(sheet, widths) {
  for (var i = 0; i < widths.length; i++) {
    if (widths[i] > 0) sheet.setColumnWidth(i + 1, widths[i]);
  }
}

function setDropdown_(sheet, col, options) {
  var rule = SpreadsheetApp.newDataValidation()
    .requireValueInList(options, true).setAllowInvalid(true).build();
  sheet.getRange(2, col, 1000, 1).setDataValidation(rule);
}

function ensureMeta_(ss) {
  var meta = ss.getSheetByName(META_SHEET);
  if (!meta) {
    meta = ss.insertSheet(META_SHEET);
    meta.hideSheet();
    meta.getRange('A1:B1').setValues([['key', 'value']]);
    meta.getRange('A2:B2').setValues([['counter_year', new Date().getFullYear()]]);
    meta.getRange('A3:B3').setValues([['counter', 0]]);
    meta.getRange('A4:B4').setValues([['admin_email', 'Kawa.f.Kaplan@gmail.com']]);
    meta.getRange('A5:B5').setValues([['match_alert_url', 'https://kaplan-solutions.de/api/match-alert']]);
    meta.getRange('A6:B6').setValues([['match_alert_secret', '']]);
    meta.getRange('A7:B7').setValues([['crm_secret', '']]);
  } else {
    if (!meta.getRange('A5').getValue()) {
      meta.getRange('A5:B5').setValues([['match_alert_url', 'https://kaplan-solutions.de/api/match-alert']]);
    }
    if (!meta.getRange('A6').getValue()) {
      meta.getRange('A6:B6').setValues([['match_alert_secret', '']]);
    }
    if (!meta.getRange('A7').getValue()) {
      meta.getRange('A7:B7').setValues([['crm_secret', '']]);
    }
  }
}

function ensureRootFolders_() {
  var root = getOrCreateFolder_(DriveApp.getRootFolder(), ROOT_FOLDER_NAME);
  [FOLDER_DASHBOARD, FOLDER_AUFTRAGGEBER, FOLDER_AUFTRAGNEHMER,
   FOLDER_MATCHES, FOLDER_SERIOSITY, FOLDER_PRUEFEN].forEach(function (n) {
    getOrCreateFolder_(root, n);
  });
}

// -- Anfrage-Nr. -------------------------------------------------------------

function nextRef_(ss) {
  var meta = ss.getSheetByName(META_SHEET);
  var year = new Date().getFullYear();
  var storedYear = Number(meta.getRange('B2').getValue()) || year;
  var counter = Number(meta.getRange('B3').getValue()) || 0;
  if (storedYear !== year) {
    storedYear = year;
    counter = 0;
    meta.getRange('B2').setValue(year);
  }
  counter += 1;
  meta.getRange('B3').setValue(counter);
  return 'KS-' + year + '-' + ('0000' + counter).slice(-4);
}

// -- Lead-Zeile & Ordner -----------------------------------------------------

function buildLeadRow_(data, ref, folderUrl, matchCount, seriosStatus, flags) {
  return [
    ref, data.eingegangen || '', data.rolle || '', data.name || '', data.email || '',
    data.telefon || '', data.firma || '', data.branche || 'Sonstiges', data.stadt || '-',
    data.plz || '', data.projekt || '', data.standort || '', data.zeitrahmen || '',
    data.budget || '', data.groesse || '', data.status_feld || '', data.referenzen || '',
    data.nachricht || '', data.dateien || '-',
    seriosStatus, matchCount, 'Neu', flags || '',
    data.bearbeitung || 'Neu', folderUrl || ''
  ];
}

function createLeadFolder_(data, ref) {
  var root = getOrCreateFolder_(DriveApp.getRootFolder(), ROOT_FOLDER_NAME);
  var roleRoot = data.role_code === 'bauherr'
    ? getOrCreateFolder_(root, FOLDER_AUFTRAGGEBER)
    : getOrCreateFolder_(root, FOLDER_AUFTRAGNEHMER);
  var brancheFolder = getOrCreateFolder_(roleRoot, safeName_(data.branche || 'Sonstiges'));
  var stadtFolder = getOrCreateFolder_(brancheFolder, safeName_(data.stadt || 'Unbekannt'));
  var leadName = ref + ' - ' + safeName_(data.name || 'Lead');
  var leadFolder = stadtFolder.createFolder(leadName);

  var info = buildLeadInfoText_(data, ref);
  leadFolder.createFile('Lead-Info.txt', info, MimeType.PLAIN_TEXT);

  return leadFolder.getUrl();
}

function buildLeadInfoText_(data, ref) {
  return [
    'Anfrage-Nr.: ' + ref,
    'Eingegangen: ' + (data.eingegangen || ''),
    'Rolle: ' + (data.rolle || ''),
    'Name: ' + (data.name || ''),
    'E-Mail: ' + (data.email || ''),
    'Telefon: ' + (data.telefon || ''),
    'Rueckruf-Termin: ' + (data.rueckruf || '-'),
    'Firma: ' + (data.firma || ''),
    'Branche: ' + (data.branche || ''),
    'Stadt: ' + (data.stadt || ''),
    'PLZ: ' + (data.plz || ''),
    'Projekt/Gewerke: ' + (data.projekt || ''),
    'Standort: ' + (data.standort || ''),
    'Zeitrahmen: ' + (data.zeitrahmen || ''),
    'Budget/Umfang: ' + (data.budget || ''),
    'Nachricht:', data.nachricht || '-'
  ].join('\n');
}

function createSeriosityReport_(ref, data, score, status, flags, details) {
  try {
    var root = getOrCreateFolder_(DriveApp.getRootFolder(), ROOT_FOLDER_NAME);
    var serRoot = getOrCreateFolder_(root, FOLDER_SERIOSITY);
    var fName = ref + ' - ' + safeName_(data.firma || data.name || 'Lead');
    var folder = serRoot.getFoldersByName(fName).hasNext()
      ? serRoot.getFoldersByName(fName).next()
      : serRoot.createFolder(fName);

    var quellen = data.quellen || [];
    var qLines = quellen.length
      ? quellen.map(function (q) { return '  - ' + (q.label || 'Quelle') + ': ' + (q.url || ''); })
      : ['  - keine externen Quellen gefunden'];

    var header = [
      '+==================================================+',
      '   KAPLAN SOLUTIONS - SERIOSITAeTS-REPORT',
      '+==================================================+',
      '',
      'Anfrage-Nr.: ' + ref,
      'Firma/Name:  ' + (data.firma || data.name || ''),
      'Geprueft am:  ' + Utilities.formatDate(new Date(), TZ, 'dd.MM.yyyy HH:mm'),
      '',
      '--------------------------------------------------',
      ''
    ].join('\n');

    var content = header + (details || '') + '\n\n' +
      '--------------------------------------------------\n' +
      'QUELLENVERZEICHNIS (zum Selbst-Nachpruefen):\n' +
      qLines.join('\n');

    // bestehende Datei ersetzen
    var old = folder.getFilesByName('Seriositaets-Report.txt');
    while (old.hasNext()) old.next().setTrashed(true);
    folder.createFile('Seriositaets-Report.txt', content, MimeType.PLAIN_TEXT);
    return folder.getUrl();
  } catch (err) {
    return '';
  }
}

function moveToPruefenFolder_(ref, name, score, flags) {
  var root = getOrCreateFolder_(DriveApp.getRootFolder(), ROOT_FOLDER_NAME);
  var pruefen = getOrCreateFolder_(root, FOLDER_PRUEFEN);
  var fName = ref + ' - ' + safeName_(name) + ' (' + score + '%)';
  if (pruefen.getFoldersByName(fName).hasNext()) return;
  var folder = pruefen.createFolder(fName);
  folder.createFile('Hinweis.txt',
    'Niedrige Seriositaet: ' + score + '%\nFlags: ' + (flags || '-') +
    '\nLead wurde NICHT blockiert - bitte manuell pruefen.', MimeType.PLAIN_TEXT);
}

// -- Matching -----------------------------------------------------------------

function findAllMatches_(ss, incoming, currentRef) {
  var candidateTabs = incoming.role_code === 'bauherr'
    ? [TAB_AUFTRAGNEHMER, TAB_PORTFOLIO]
    : [TAB_AUFTRAGGEBER];
  var candidates = [];

  candidateTabs.forEach(function (tabName) {
    var sheet = ss.getSheetByName(tabName);
    if (!sheet || sheet.getLastRow() < 2) return;

    var values = sheet.getDataRange().getValues();
    var idx = indexMapLead_(values[0]);

    for (var r = 1; r < values.length; r++) {
      var row = values[r];
      var ref = String(row[idx.ref] || '');
      if (!ref || ref === currentRef) continue;

      var scored = scoreMatch_(incoming, row, idx);
      if (scored.score >= MIN_MATCH_SCORE_TAB) {
        candidates.push({
          name: String(row[idx.name] || ''),
          ref: ref,
          email: String(row[idx.email] || ''),
          role: String(row[idx.rolle] || ''),
          branche: String(row[idx.branche] || ''),
          stadt: String(row[idx.stadt] || ''),
          score: scored.score,
          reason: scored.reasons.join(', ')
        });
      }
    }
  });

  candidates.sort(function (a, b) { return b.score - a.score; });
  return candidates;
}

function scoreMatch_(incoming, row, idx) {
  var score = 0;
  var reasons = [];

  var cityScore = scoreCity_(incoming.stadt, incoming.plz, row[idx.stadt], row[idx.plz]);
  if (cityScore > 0) { score += cityScore; reasons.push('Region'); }

  var brancheScore = scoreBranche_(incoming.branche, row[idx.branche]);
  if (brancheScore > 0) { score += brancheScore; reasons.push('Branche'); }

  var budgetScore = scoreBudget_(incoming.budget, row[idx.budget]);
  if (budgetScore > 0) { score += budgetScore; reasons.push('Budget/Umfang'); }

  var timeScore = scoreTimeline_(incoming.zeitrahmen, row[idx.zeitrahmen]);
  if (timeScore > 0) { score += timeScore; reasons.push('Zeit/Kapazitaet'); }

  var regionScore = scoreRegion_(incoming.standort, row[idx.standort]);
  if (regionScore > 0) { score += regionScore; reasons.push('Einsatzgebiet'); }

  return { score: Math.min(score, 100), reasons: reasons };
}

function writeMatches_(ss, ref, data, matches) {
  if (!matches.length) return;
  var sheet = ss.getSheetByName(TAB_MATCHES);
  var existing = getExistingMatchIds_(sheet);
  var now = Utilities.formatDate(new Date(), TZ, 'dd.MM.yyyy HH:mm');
  var isBauIncoming = data.role_code === 'bauherr';

  matches.forEach(function (m) {
    var matchId = makeMatchId_(ref, m.ref);
    if (existing[matchId]) return;

    var agName, agMail, anName, anMail;
    if (isBauIncoming) {
      agName = data.name || ''; agMail = data.email || '';
      anName = m.name || ''; anMail = m.email || '';
    } else {
      anName = data.name || ''; anMail = data.email || '';
      agName = m.name || ''; agMail = m.email || '';
    }

    var ordnerUrl = m.score >= MATCH_FOLDER_MIN
      ? createMatchFolder_(ref, data, m) : '';

    var row = [
      m.score + '%', 'Neu', agName, agMail, anName, anMail,
      data.branche || m.branche || '', data.stadt || m.stadt || '',
      m.reason, ref + ' <-> ' + m.ref, '', now, matchId
    ];
    sheet.appendRow(row);
    var rowNum = sheet.getLastRow();
    sheet.getRange(rowNum, 1).setBackground(matchColor_(m.score)).setFontWeight('bold');
    if (ordnerUrl) {
      sheet.getRange(rowNum, 11).setFormula('=HYPERLINK("' + ordnerUrl + '";"Oeffnen")');
    }
    existing[matchId] = true;
  });
}

function createMatchFolder_(ref, data, m) {
  try {
    var root = getOrCreateFolder_(DriveApp.getRootFolder(), ROOT_FOLDER_NAME);
    var matchRoot = getOrCreateFolder_(root, FOLDER_MATCHES);
    var fname = ref + ' <-> ' + m.ref + ' (' + m.score + '%)';
    if (matchRoot.getFoldersByName(fname).hasNext()) {
      return matchRoot.getFoldersByName(fname).next().getUrl();
    }
    var folder = matchRoot.createFolder(fname);
    folder.createFile('Match-Info.txt',
      'Match: ' + (data.name || '') + ' <-> ' + m.name + '\nPassung: ' + m.score + '%\n' +
      'Gruende: ' + m.reason + '\nAnfrage A: ' + ref + '\nAnfrage B: ' + m.ref,
      MimeType.PLAIN_TEXT);
    return folder.getUrl();
  } catch (e) {
    return '';
  }
}

function getExistingMatchIds_(sheet) {
  var map = {};
  if (!sheet || sheet.getLastRow() < 2) return map;
  var col = sheet.getRange(2, 13, sheet.getLastRow() - 1, 1).getValues();
  col.forEach(function (r) { if (r[0]) map[String(r[0])] = true; });
  return map;
}

function makeMatchId_(refA, refB) {
  return [refA, refB].sort().join('__');
}

// -- Seriositaet & Pipeline -----------------------------------------------------

function writeSeriosityPending_(ss, ref, data, folderUrl) {
  var sheet = ss.getSheetByName(TAB_SERIOSITY);
  sheet.appendRow([
    ref, (data.firma && data.firma !== '-' ? data.firma : data.name) || '',
    '', '\u23f3 Pr\u00fcfung l\u00e4uft ...', '', '', '', '', '', '', '', '', ''
  ]);
}

function writePipeline_(ss, ref, data, folderUrl, matchCount) {
  var sheet = ss.getSheetByName(TAB_PIPELINE);
  var roleCode = data.role_code || (String(data.rolle || '').indexOf('Auftraggeber') >= 0 ? 'bauherr' : 'unternehmen');
  var stage = initialCrmStage_(roleCode, data);
  var quelle = formatLeadSource_(data);
  var bestScore = matchCount > 0 ? '-' : '-';
  sheet.appendRow([
    ref, data.eingegangen || '', data.name || '', data.rolle || '',
    data.branche || '', data.stadt || '', stage, '-', matchCount, bestScore,
    data.rueckruf && data.rueckruf !== '\u2014' ? data.rueckruf : '',
    quelle, crmNextStepForStage_(roleCode, stage, 0), 'Nein', 'Nein',
    '', '', '', 'Nein', '', '', folderUrl || ''
  ]);
}

function updateLeadSeriosity_(ss, ref, score, flags, status) {
  [TAB_ALL, TAB_AUFTRAGGEBER, TAB_AUFTRAGNEHMER, TAB_PORTFOLIO].forEach(function (tabName) {
    var sheet = ss.getSheetByName(tabName);
    var rowNum = findRowByRef_(sheet, ref, 1);
    if (rowNum < 1) return;
    sheet.getRange(rowNum, 20).setValue(score + '%').setBackground(scoreColor_(score));
    sheet.getRange(rowNum, 23).setValue((flags || '') + ' ' + (status || ''));
  });
}

function upsertSeriosityRow_(ss, ref, data, score, status, flags, reportUrl) {
  var sheet = ss.getSheetByName(TAB_SERIOSITY);
  var rowNum = findRowByRef_(sheet, ref, 1);
  var now = Utilities.formatDate(new Date(), TZ, 'dd.MM.yyyy HH:mm');
  var firmaName = (data.firma && data.firma !== '-' ? data.firma : data.name) || '';

  var warn = '';
  if (data.negative && data.negative.length) {
    warn = 'WARN: ' + data.negative.join(' | ');
  } else if (score < 40) {
    warn = 'WARN: Wenig verlaessliche Daten';
  } else {
    warn = '-';
  }

  var row = [
    ref, firmaName, score, (flags || '') + ' ' + (status || ''),
    data.rechtsform || '-', data.handelsregister || '-',
    data.domain_alter || '-', data.google_rating || '-',
    data.confidence || '-', warn, '', '', now
  ];

  if (rowNum < 1) {
    sheet.appendRow(row);
    rowNum = sheet.getLastRow();
  } else {
    sheet.getRange(rowNum, 1, 1, row.length).setValues([row]);
  }

  // Score-Zelle farbig
  sheet.getRange(rowNum, 3).setBackground(scoreColor_(score))
    .setFontWeight('bold').setHorizontalAlignment('center');

  // Quellen-Link (erste/Website) + Report-Link
  var primary = data.website || '';
  if (!primary && data.quellen && data.quellen.length) primary = data.quellen[0].url || '';
  if (primary) {
    sheet.getRange(rowNum, 11).setFormula('=HYPERLINK("' + primary + '";"Webseite")');
  } else {
    sheet.getRange(rowNum, 11).setValue('-');
  }
  if (reportUrl) {
    sheet.getRange(rowNum, 12).setFormula('=HYPERLINK("' + reportUrl + '";" Report")');
  } else {
    sheet.getRange(rowNum, 12).setValue('-');
  }
}

function updatePipelineSeriosity_(ss, ref, score, flags) {
  var sheet = ss.getSheetByName(TAB_PIPELINE);
  var rowNum = findRowByRef_(sheet, ref, 1);
  if (rowNum > 0) {
    sheet.getRange(rowNum, 8).setValue(score + '%').setBackground(scoreColor_(score));
    if (score < 40) {
      sheet.getRange(rowNum, 13).setValue('WARN: Manuell pruefen');
    }
  }
}

function findRowByRef_(sheet, ref, refCol) {
  if (!sheet || sheet.getLastRow() < 2) return -1;
  var refs = sheet.getRange(2, refCol, sheet.getLastRow() - 1, 1).getValues();
  for (var i = 0; i < refs.length; i++) {
    if (String(refs[i][0]) === ref) return i + 2;
  }
  return -1;
}

// -- Dashboard -----------------------------------------------------------------

function updateDashboard_(ss) {
  var sheet = ss.getSheetByName(TAB_DASHBOARD);
  if (!sheet) return;

  var ag = ss.getSheetByName(TAB_AUFTRAGGEBER);
  var an = ss.getSheetByName(TAB_AUFTRAGNEHMER);
  var portfolio = ss.getSheetByName(TAB_PORTFOLIO);
  var matches = ss.getSheetByName(TAB_MATCHES);
  var ser = ss.getSheetByName(TAB_SERIOSITY);
  var pipe = ss.getSheetByName(TAB_PIPELINE);

  var agCount = ag ? Math.max(0, ag.getLastRow() - 1) : 0;
  var anCount = an ? Math.max(0, an.getLastRow() - 1) : 0;
  var portfolioCount = portfolio ? Math.max(0, portfolio.getLastRow() - 1) : 0;
  var matchCount = matches ? Math.max(0, matches.getLastRow() - 1) : 0;
  var serStats = seriosityStats_(ser);
  var openPipe = countOpenPipeline_(pipe);

  sheet.clear();
  var widths = [40, 200, 120, 200, 120];
  applyWidths_(sheet, widths);

  // Titel
  sheet.getRange('B2:E2').merge().setValue('KAPLAN SOLUTIONS - LEAD-UeBERSICHT')
    .setFontSize(16).setFontWeight('bold').setFontColor(C_HEAD_FG)
    .setBackground(C_HEAD_BG).setHorizontalAlignment('center').setVerticalAlignment('middle');
  sheet.setRowHeight(2, 40);
  sheet.getRange('B3:E3').merge()
    .setValue('Stand: ' + Utilities.formatDate(new Date(), TZ, 'dd.MM.yyyy HH:mm') + ' Uhr')
    .setFontColor('#666').setHorizontalAlignment('center');

  // KPI-Kacheln (Label / Wert nebeneinander)
  var kpis = [
    ['Auftraggeber (echte Anfragen)', agCount, 'Auftragnehmer (echte Anfragen)', anCount],
    ['Outreach-Portfolio (kontaktiert)', portfolioCount, 'Gefundene Matches', matchCount],
    ['Pipeline offen', openPipe, 'Seriositaet', serStats.avg > 0 ? serStats.avg + '%' : '-'],
    ['WARN: Prueffaelle (<40%)', serStats.red, 'Seriositaet geprueft', serStats.done]
  ];

  var startRow = 5;
  kpis.forEach(function (k, i) {
    var r = startRow + i;
    sheet.getRange(r, 2).setValue(k[0]).setFontColor('#555');
    sheet.getRange(r, 3).setValue(k[1]).setFontSize(14).setFontWeight('bold')
      .setHorizontalAlignment('center').setBackground(C_BAND);
    sheet.getRange(r, 4).setValue(k[2]).setFontColor('#555');
    sheet.getRange(r, 5).setValue(k[3]).setFontSize(14).setFontWeight('bold')
      .setHorizontalAlignment('center').setBackground(C_BAND);
    sheet.setRowHeight(r, 28);
  });

  // Prueffaelle hervorheben
  if (serStats.red > 0) {
    sheet.getRange(startRow + 2, 5).setBackground(C_RED);
  }

  // Hinweis-Zeile
  var noteRow = startRow + kpis.length + 1;
  sheet.getRange(noteRow, 2, 1, 4).merge()
    .setValue('Auftraggeber/Auftragnehmer = echte Anfragen | Outreach-Portfolio = nur kontaktiert | Pipeline = Verkaufsstatus')
    .setFontColor('#888').setFontStyle('italic').setWrap(true);

  sheet.setHiddenGridlines && sheet.setHiddenGridlines(true);
}

function seriosityStats_(sheet) {
  var out = { avg: 0, done: 0, pending: 0, red: 0 };
  if (!sheet || sheet.getLastRow() < 2) return out;
  var data = sheet.getRange(2, 3, sheet.getLastRow() - 1, 2).getValues(); // Score + Bewertung
  var sum = 0, n = 0;
  data.forEach(function (r) {
    var score = Number(r[0]);
    var bew = String(r[1]);
    if (bew.indexOf('laeuft') >= 0 || r[0] === '' || r[0] === null) {
      out.pending++;
    } else {
      out.done++;
      if (!isNaN(score)) { sum += score; n++; if (score < 40) out.red++; }
    }
  });
  out.avg = n ? Math.round(sum / n) : 0;
  return out;
}

function countOpenPipeline_(sheet) {
  if (!sheet || sheet.getLastRow() < 2) return 0;
  var values = sheet.getRange(2, 1, sheet.getLastRow() - 1, 7).getValues();
  var n = 0;
  values.forEach(function (r) {
    var rolle = String(r[3] || '');
    var stage = String(r[6] || '');
    if (!stage) return;
    if (!isTerminalCrmStage_(rolle, stage)) n++;
  });
  return n;
}

// -- Farben --------------------------------------------------------------------

function scoreColor_(score) {
  var s = Number(score);
  if (isNaN(s) || s === 0) return null;
  if (s >= 80) return C_GREEN;
  if (s >= 60) return C_GREEN2;
  if (s >= 40) return C_YELLOW;
  return C_RED;
}

function matchColor_(score) {
  var s = Number(score);
  if (s >= 75) return C_GREEN;
  if (s >= 50) return C_GREEN2;
  return C_YELLOW;
}

// -- Scoring-Hilfen ----------------------------------------------------------

function indexMapLead_(headers) {
  var map = {};
  for (var i = 0; i < headers.length; i++) {
    var h = String(headers[i]).toLowerCase();
    if (h.indexOf('anfrage') === 0) map.ref = i;
    else if (h === 'name') map.name = i;
    else if (h.indexOf('e-mail') === 0) map.email = i;
    else if (h.indexOf('telefon') === 0) map.telefon = i;
    else if (h === 'firma') map.firma = i;
    else if (h === 'rolle') map.rolle = i;
    else if (h === 'branche') map.branche = i;
    else if (h === 'stadt') map.stadt = i;
    else if (h === 'plz') map.plz = i;
    else if (h === 'standort') map.standort = i;
    else if (h.indexOf('budget') === 0 || h.indexOf('auftrags') >= 0) map.budget = i;
    else if (h.indexOf('zeit') === 0 || h.indexOf('kapaz') >= 0) map.zeitrahmen = i;
    else if (h.indexOf('pipeline') === 0) map.pipeline = i;
    else if (h.indexOf('bearbeitung') === 0) map.bearbeitung = i;
    else if (h.indexOf('nachricht') === 0) map.nachricht = i;
    else if (h.indexOf('projekt') === 0) map.projekt = i;
  }
  return map;
}

function norm_(text) {
  return String(text || '')
    .toLowerCase()
    .replace(/ae/g, 'ae').replace(/oe/g, 'oe').replace(/ue/g, 'ue').replace(/ss/g, 'ss')
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function scoreCity_(aStadt, aPlz, bStadt, bPlz) {
  if (aPlz && bPlz && String(aPlz) === String(bPlz)) return 35;
  var a = norm_(aStadt), b = norm_(bStadt);
  if (!a || !b || a === '-' || b === '-') return 0;
  if (a === b) return 35;
  if (a.indexOf(b) >= 0 || b.indexOf(a) >= 0) return 28;
  return 0;
}

function scoreBranche_(a, b) {
  var x = norm_(a), y = norm_(b);
  if (!x || !y) return 0;
  if (x === y) return 30;
  if (x.indexOf(y) >= 0 || y.indexOf(x) >= 0) return 22;
  var related = {
    'neubau': ['wohnungsbau', 'gewerbebau', 'rohbau'],
    'sanierung': ['ausbau', 'shk'],
    'ausbau': ['sanierung', 'trockenbau'],
    'elektro': ['shk'], 'shk': ['elektro', 'sanierung']
  };
  var xa = related[x] || [];
  for (var i = 0; i < xa.length; i++) if (xa[i] === y) return 12;
  return 0;
}

function scoreBudget_(a, b) {
  var x = norm_(a), y = norm_(b);
  if (!x || !y || x === '-' || y === '-') return 0;
  if (x === y) return 15;
  var numsA = x.match(/\d+/g) || [];
  var numsB = y.match(/\d+/g) || [];
  if (!numsA.length || !numsB.length) {
    if (x.indexOf(y) >= 0 || y.indexOf(x) >= 0) return 10;
    return 0;
  }
  var maxA = Math.max.apply(null, numsA.map(Number));
  var maxB = Math.max.apply(null, numsB.map(Number));
  if (!maxA || !maxB) return 0;
  var ratio = maxA > maxB ? maxB / maxA : maxA / maxB;
  if (ratio >= 0.5) return 15;
  if (ratio >= 0.25) return 8;
  return 0;
}

function scoreTimeline_(a, b) {
  var x = norm_(a), y = norm_(b);
  if (!x || !y) return 0;
  var urgent = ['sofort', 'kurzfristig', 'asap', 'naechster', 'naechster'];
  var soon = ['2026', '2027', 'q1', 'q2', 'q3', 'q4'];
  var xU = urgent.some(function (w) { return x.indexOf(w) >= 0; });
  var yU = urgent.some(function (w) { return y.indexOf(w) >= 0; });
  if (xU && yU) return 10;
  if (soon.some(function (w) { return x.indexOf(w) >= 0 && y.indexOf(w) >= 0; })) return 8;
  if (x.indexOf(y) >= 0 || y.indexOf(x) >= 0) return 6;
  return 0;
}

function scoreRegion_(a, b) {
  var x = norm_(a), y = norm_(b);
  if (!x || !y) return 0;
  var wordsA = x.split(' '), wordsB = y.split(' ');
  for (var i = 0; i < wordsA.length; i++) {
    if (wordsA[i].length < 4) continue;
    for (var j = 0; j < wordsB.length; j++) {
      if (wordsA[i] === wordsB[j]) return 10;
    }
  }
  return 0;
}

// -- 24/7 Matching & Tages-Briefing -----------------------------------------

function handleMatchRescan_(data) {
  var result = rescanAllMatchesFull_();
  if (data && data.send_briefing) {
    result.briefing_sent = sendDailyMatchBriefingEmail_(result);
  }
  return jsonResponse_({ ok: true, action: 'match_rescan', result: result });
}

function handleDailyBriefingRequest_(data) {
  var result = rescanAllMatchesFull_();
  var sent = sendDailyMatchBriefingEmail_(result);
  return jsonResponse_({ ok: true, action: 'daily_briefing', briefing_sent: sent, result: result });
}

function rescanAllMatchesScheduled_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  purgeJunkLeadsFromSheet_(ss);
  rescanAllMatchesFull_();
}

function sendDailyMatchBriefingScheduled_() {
  var result = rescanAllMatchesFull_();
  sendDailyMatchBriefingEmail_(result);
}

/**
 * Einmal ausfuehren nach Code-Update:
 * Stuendlicher Match-Scan (24/7) + taegliches Briefing 10:00 Uhr.
 */
function installTriggers() {
  var triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(function (t) {
    var fn = t.getHandlerFunction();
    if (fn === 'rescanAllMatchesScheduled_' || fn === 'sendDailyMatchBriefingScheduled_') {
      ScriptApp.deleteTrigger(t);
    }
  });
  ScriptApp.newTrigger('rescanAllMatchesScheduled_')
    .timeBased().everyHours(1).create();
  ScriptApp.newTrigger('sendDailyMatchBriefingScheduled_')
    .timeBased().atHour(10).nearMinute(0).everyDays(1).inTimezone(TZ).create();
  Logger.log('Trigger installiert: Match-Scan stuendlich + Briefing taeglich 10:00 ' + TZ);
}

function getAdminEmail_() {
  var fromProps = PropertiesService.getScriptProperties().getProperty('ADMIN_EMAIL');
  if (fromProps) return fromProps;
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var meta = ss.getSheetByName(META_SHEET);
    if (meta) {
      var val = meta.getRange('B4').getValue();
      if (val) return String(val);
    }
  } catch (e) {}
  return 'Kawa.f.Kaplan@gmail.com';
}

function rescanAllMatchesFull_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ensureStructure_(ss);
  var pairs = computeAllMatchPairs_(ss);
  syncMatchesTabFromPairs_(ss, pairs);
  rebuildTopMatchesTab_(ss, pairs);
  updateMatchCountsOnLeads_(ss, pairs);
  syncCrmPipelineFromMatches_(ss, pairs);
  updateDashboard_(ss);

  var alertResult = processInstantMatchAlerts_(ss, pairs);

  var hot = 0, good = 0;
  pairs.forEach(function (p) {
    if (p.score >= 75) hot++;
    else if (p.score >= 60) good++;
  });

  return {
    total_matches: pairs.length,
    hot: hot,
    good: good,
    top: pairs.slice(0, 10),
    scanned_at: Utilities.formatDate(new Date(), TZ, 'dd.MM.yyyy HH:mm'),
    alerts_sent: alertResult.sent
  };
}

function computeAllMatchPairs_(ss) {
  var agSheet = ss.getSheetByName(TAB_AUFTRAGGEBER);
  if (!agSheet || agSheet.getLastRow() < 2) return [];

  var partnerRows = collectPartnerRows_(ss);
  if (!partnerRows.length) return [];

  var agValues = agSheet.getDataRange().getValues();
  var agIdx = indexMapLead_(agValues[0]);
  var pairs = [];
  var seen = {};

  for (var a = 1; a < agValues.length; a++) {
    var agRow = agValues[a];
    var agRef = String(agRow[agIdx.ref] || '');
    if (!agRef) continue;
    var agIncoming = rowToIncoming_(agRow, agIdx, 'bauherr');

    for (var p = 0; p < partnerRows.length; p++) {
      var anRow = partnerRows[p].row;
      var anIdx = partnerRows[p].idx;
      var anRef = String(anRow[anIdx.ref] || '');
      if (!anRef) continue;

      var scored = scoreMatch_(agIncoming, anRow, anIdx);
      if (scored.score < MIN_MATCH_SCORE_TAB) continue;

      var matchId = makeMatchId_(agRef, anRef);
      if (seen[matchId]) continue;
      seen[matchId] = true;

      pairs.push({
        score: scored.score,
        reasons: scored.reasons.join(', '),
        matchId: matchId,
        agRef: agRef,
        agName: String(agRow[agIdx.name] || ''),
        agEmail: String(agRow[agIdx.email] || ''),
        agFirma: String(agRow[agIdx.firma] || agRow[agIdx.name] || ''),
        anRef: anRef,
        anName: String(anRow[anIdx.name] || ''),
        anEmail: String(anRow[anIdx.email] || ''),
        anFirma: String(anRow[anIdx.firma] || anRow[anIdx.name] || ''),
        branche: String(agRow[agIdx.branche] || anRow[anIdx.branche] || ''),
        stadt: String(agRow[agIdx.stadt] || anRow[anIdx.stadt] || '')
      });
    }
  }

  pairs.sort(function (x, y) { return y.score - x.score; });
  return pairs;
}

function collectPartnerRows_(ss) {
  var out = [];
  [TAB_AUFTRAGNEHMER, TAB_PORTFOLIO].forEach(function (tabName) {
    var sheet = ss.getSheetByName(tabName);
    if (!sheet || sheet.getLastRow() < 2) return;
    var values = sheet.getDataRange().getValues();
    var idx = indexMapLead_(values[0]);
    for (var r = 1; r < values.length; r++) {
      out.push({ row: values[r], idx: idx, tab: tabName });
    }
  });
  return out;
}

function rowToIncoming_(row, idx, roleCode) {
  return {
    role_code: roleCode,
    stadt: row[idx.stadt],
    plz: row[idx.plz],
    branche: row[idx.branche],
    budget: row[idx.budget],
    zeitrahmen: row[idx.zeitrahmen],
    standort: row[idx.standort]
  };
}

function priorityLabel_(score) {
  if (score >= 75) return 'HEISS';
  if (score >= 60) return 'GUT';
  return 'OK';
}

function priorityLabelEmail_(score) {
  if (score >= 75) return 'HEISS';
  if (score >= 60) return 'GUT';
  return 'OK';
}

function nextStepLabel_(score) {
  if (score >= 75) return 'Jetzt anrufen und Erstgespraech koordinieren';
  if (score >= 60) return 'Kurz anrufen und Passung pruefen';
  return 'Beobachten - bei besserem Lead nachfassen';
}

function nextStepLabelSheet_(score) {
  if (score >= 75) return 'Jetzt anrufen & Erstgespraech koordinieren';
  if (score >= 60) return 'Kurz anrufen und Passung pruefen';
  return 'Beobachten - bei besserem Lead nachfassen';
}

function escapeHtml_(text) {
  return String(text || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function syncMatchesTabFromPairs_(ss, pairs) {
  var sheet = ss.getSheetByName(TAB_MATCHES);
  var existingStatus = {};
  if (sheet.getLastRow() > 1) {
    var ids = sheet.getRange(2, 13, sheet.getLastRow() - 1, 1).getValues();
    var statuses = sheet.getRange(2, 2, sheet.getLastRow() - 1, 1).getValues();
    for (var i = 0; i < ids.length; i++) {
      if (ids[i][0]) existingStatus[String(ids[i][0])] = String(statuses[i][0] || 'Neu');
    }
  }

  if (sheet.getLastRow() > 1) {
    sheet.getRange(2, 1, sheet.getLastRow() - 1, MATCH_HEADERS.length).clearContent();
  }

  var now = Utilities.formatDate(new Date(), TZ, 'dd.MM.yyyy HH:mm');
  pairs.forEach(function (p) {
    var status = existingStatus[p.matchId] || 'Neu';
    var row = [
      p.score + '%', status, p.agName, p.agEmail, p.anFirma || p.anName, p.anEmail,
      p.branche, p.stadt, p.reasons, p.agRef + ' <-> ' + p.anRef, '', now, p.matchId
    ];
    sheet.appendRow(row);
    var rowNum = sheet.getLastRow();
    sheet.getRange(rowNum, 1).setBackground(matchColor_(p.score)).setFontWeight('bold');
  });
  styleHeader_(sheet, MATCH_HEADERS.length);
}

function rebuildTopMatchesTab_(ss, pairs) {
  var sheet = ss.getSheetByName(TAB_TOP_MATCHES);
  if (!sheet) return;

  var existingStatus = {};
  if (sheet.getLastRow() > 1) {
    var ids = sheet.getRange(2, 15, sheet.getLastRow() - 1, 1).getValues();
    var statuses = sheet.getRange(2, 4, sheet.getLastRow() - 1, 1).getValues();
    for (var i = 0; i < ids.length; i++) {
      if (ids[i][0]) existingStatus[String(ids[i][0])] = String(statuses[i][0] || 'Neu');
    }
  }

  if (sheet.getLastRow() > 1) {
    sheet.getRange(2, 1, sheet.getLastRow() - 1, TOP_MATCH_HEADERS.length).clearContent();
  }

  pairs.forEach(function (p, i) {
    var rank = i + 1;
    var status = existingStatus[p.matchId] || 'Neu';
    var row = [
      rank,
      priorityLabel_(p.score),
      p.score,
      status,
      p.agFirma || p.agName,
      p.agEmail,
      p.agRef,
      p.anFirma || p.anName,
      p.anEmail,
      p.anRef,
      p.stadt,
      p.branche,
      p.reasons,
      nextStepLabelSheet_(p.score),
      p.matchId
    ];
    sheet.appendRow(row);
    var rowNum = sheet.getLastRow();
    var bg = matchColor_(p.score);
    sheet.getRange(rowNum, 1, 1, 4).setBackground(bg).setFontWeight('bold');
    if (p.score >= 75) {
      sheet.getRange(rowNum, 2).setFontColor('#b45309').setFontWeight('bold');
    }
  });

  sheet.setFrozenRows(1);
  styleHeader_(sheet, TOP_MATCH_HEADERS.length);
}

function updateMatchCountsOnLeads_(ss, pairs) {
  var counts = {};
  pairs.forEach(function (p) {
    counts[p.agRef] = (counts[p.agRef] || 0) + 1;
    counts[p.anRef] = (counts[p.anRef] || 0) + 1;
  });

  [TAB_ALL, TAB_AUFTRAGGEBER, TAB_AUFTRAGNEHMER, TAB_PORTFOLIO].forEach(function (tabName) {
    var sheet = ss.getSheetByName(tabName);
    if (!sheet || sheet.getLastRow() < 2) return;
    var refs = sheet.getRange(2, 1, sheet.getLastRow() - 1, 1).getValues();
    for (var i = 0; i < refs.length; i++) {
      var ref = String(refs[i][0] || '');
      if (!ref) continue;
      sheet.getRange(i + 2, 21).setValue(counts[ref] || 0);
    }
  });
}

// -- Sofort-Alerts bei heißem Match (>= 75%) -----------------------------------

function buildHotPairsFromNewLead_(ref, data, matches) {
  var pairs = [];
  matches.forEach(function (m) {
    if (m.score < MATCH_ALERT_MIN) return;
    if (data.role_code === 'bauherr') {
      pairs.push({
        score: m.score,
        reasons: m.reason,
        matchId: makeMatchId_(ref, m.ref),
        agRef: ref,
        agName: data.name || '',
        agEmail: data.email || '',
        agFirma: data.firma || data.name || '',
        agPhone: data.telefon || '',
        anRef: m.ref,
        anName: m.name || '',
        anEmail: m.email || '',
        anFirma: m.name || '',
        anPhone: '',
        branche: data.branche || m.branche || '',
        stadt: data.stadt || m.stadt || ''
      });
    } else {
      pairs.push({
        score: m.score,
        reasons: m.reason,
        matchId: makeMatchId_(ref, m.ref),
        agRef: m.ref,
        agName: m.name || '',
        agEmail: m.email || '',
        agFirma: m.name || '',
        agPhone: '',
        anRef: ref,
        anName: data.name || '',
        anEmail: data.email || '',
        anFirma: data.firma || data.name || '',
        anPhone: data.telefon || '',
        branche: data.branche || m.branche || '',
        stadt: data.stadt || m.stadt || ''
      });
    }
  });
  return pairs;
}

function getAlertedMatchIds_() {
  var raw = PropertiesService.getScriptProperties().getProperty('alerted_match_ids') || '';
  var map = {};
  raw.split(',').forEach(function (id) {
    if (id) map[id.trim()] = true;
  });
  return map;
}

function saveAlertedMatchIds_(map) {
  var ids = Object.keys(map);
  if (ids.length > 500) ids = ids.slice(ids.length - 500);
  PropertiesService.getScriptProperties().setProperty('alerted_match_ids', ids.join(','));
}

function getMatchAlertUrl_() {
  try {
    var meta = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(META_SHEET);
    if (meta) {
      var val = meta.getRange('B5').getValue();
      if (val) return String(val).trim();
    }
  } catch (e) {}
  return 'https://kaplan-solutions.de/api/match-alert';
}

function getMatchAlertSecret_() {
  try {
    var meta = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(META_SHEET);
    if (meta) {
      var val = meta.getRange('B6').getValue();
      if (val) return String(val).trim();
    }
  } catch (e) {}
  return PropertiesService.getScriptProperties().getProperty('MATCH_ALERT_SECRET') || '';
}

function enrichPairFromSheet_(ss, p) {
  var agSheet = ss.getSheetByName(TAB_AUFTRAGGEBER);
  if (agSheet && agSheet.getLastRow() > 1) {
    var agValues = agSheet.getDataRange().getValues();
    var agIdx = indexMapLead_(agValues[0]);
    for (var i = 1; i < agValues.length; i++) {
      if (String(agValues[i][agIdx.ref]) === p.agRef) {
        p.agPhone = String(agValues[i][agIdx.telefon] || p.agPhone || '');
        p.agFirma = String(agValues[i][agIdx.firma] || p.agFirma || p.agName || '');
        break;
      }
    }
  }
  var partnerRows = collectPartnerRows_(ss);
  for (var j = 0; j < partnerRows.length; j++) {
    if (String(partnerRows[j].row[partnerRows[j].idx.ref]) === p.anRef) {
      p.anPhone = String(partnerRows[j].row[partnerRows[j].idx.telefon] || p.anPhone || '');
      p.anFirma = String(partnerRows[j].row[partnerRows[j].idx.firma] || p.anFirma || p.anName || '');
      break;
    }
  }
}

function ensureMatchFolderForPair_(p) {
  try {
    var root = getOrCreateFolder_(DriveApp.getRootFolder(), ROOT_FOLDER_NAME);
    var matchRoot = getOrCreateFolder_(root, FOLDER_MATCHES);
    var fname = p.agRef + ' <-> ' + p.anRef + ' (' + p.score + '%)';
    if (matchRoot.getFoldersByName(fname).hasNext()) {
      return matchRoot.getFoldersByName(fname).next().getUrl();
    }
    var folder = matchRoot.createFolder(fname);
    folder.createFile('Match-Info.txt',
      'HEISSER MATCH\nPassung: ' + p.score + '%\n' +
      'Bauherr: ' + (p.agFirma || p.agName) + ' (' + p.agEmail + ')\n' +
      'Partner: ' + (p.anFirma || p.anName) + ' (' + p.anEmail + ')\n' +
      'Region: ' + p.stadt + '\nGruende: ' + p.reasons + '\n' +
      'Anfragen: ' + p.agRef + ' <-> ' + p.anRef + '\n\n' +
      'CHECKLISTE:\n' +
      '[ ] Partner-Vertrag unterschrieben\n' +
      '[ ] Intro-Mail (CC beide Parteien)\n' +
      '[ ] Termin Erstgespraech\n' +
      '[ ] Anlage Vermittelter Kontakt\n',
      MimeType.PLAIN_TEXT);
    return folder.getUrl();
  } catch (e) {
    return '';
  }
}

function pairToAlertPayload_(p) {
  return {
    match_id: p.matchId,
    score: p.score,
    ag_ref: p.agRef,
    ag_name: p.agName,
    ag_firma: p.agFirma || p.agName,
    ag_email: p.agEmail,
    ag_phone: p.agPhone || '',
    an_ref: p.anRef,
    an_name: p.anName,
    an_firma: p.anFirma || p.anName,
    an_email: p.anEmail,
    an_phone: p.anPhone || '',
    stadt: p.stadt,
    branche: p.branche,
    reasons: p.reasons,
    folder_url: p.folder_url || ''
  };
}

function postMatchAlert_(p) {
  var url = getMatchAlertUrl_();
  var secret = getMatchAlertSecret_();
  var admin = getAdminEmail_();
  if (url && secret) {
    try {
      var resp = UrlFetchApp.fetch(url, {
        method: 'post',
        contentType: 'application/json',
        headers: { 'X-Match-Alert-Secret': secret },
        payload: JSON.stringify({ match: pairToAlertPayload_(p), admin_email: admin }),
        muteHttpExceptions: true
      });
      var code = resp.getResponseCode();
      if (code >= 200 && code < 300) return true;
      Logger.log('Match-Alert HTTP ' + code + ': ' + resp.getContentText().substring(0, 200));
    } catch (e) {
      Logger.log('Match-Alert Fehler: ' + e);
    }
  }
  return sendHotMatchAdminFallback_(p);
}

function sendHotMatchAdminFallback_(p) {
  var to = getAdminEmail_();
  if (!to) return false;
  var subject = 'HEISSER MATCH ' + p.score + '% — ' + (p.agFirma || p.agName) + ' / ' + (p.anFirma || p.anName);
  var body = buildMatchBriefingText_({
    scanned_at: Utilities.formatDate(new Date(), TZ, 'dd.MM.yyyy HH:mm'),
    hot: 1,
    good: 0,
    total_matches: 1,
    top: [p]
  }, 1, 1);
  MailApp.sendEmail({ to: to, subject: subject, body: body, name: 'Kaplan Solutions' });
  return true;
}

function processInstantMatchAlerts_(ss, pairs) {
  var sent = 0;
  var alerted = getAlertedMatchIds_();
  (pairs || []).forEach(function (p) {
    if (p.score < MATCH_ALERT_MIN) return;
    if (alerted[p.matchId]) return;
    enrichPairFromSheet_(ss, p);
    p.folder_url = ensureMatchFolderForPair_(p);
    if (postMatchAlert_(p)) {
      alerted[p.matchId] = true;
      sent++;
    }
  });
  saveAlertedMatchIds_(alerted);
  return { sent: sent };
}

function sendDailyMatchBriefingEmail_(result) {
  result = result || rescanAllMatchesFull_();
  var to = getAdminEmail_();
  if (!to) return false;

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var agSheet = ss.getSheetByName(TAB_AUFTRAGGEBER);
  var anSheet = ss.getSheetByName(TAB_AUFTRAGNEHMER);
  var agCount = agSheet ? Math.max(0, agSheet.getLastRow() - 1) : 0;
  var anCount = anSheet ? Math.max(0, anSheet.getLastRow() - 1) : 0;

  var subject = 'Kaplan Solutions | Matching-Briefing | ' + result.scanned_at +
    ' | ' + result.hot + ' heisse Matches';

  var body = buildMatchBriefingText_(result, agCount, anCount);
  var html = buildMatchBriefingHtml_(result, agCount, anCount);

  MailApp.sendEmail({
    to: to,
    subject: subject,
    body: body,
    htmlBody: html,
    name: 'Kaplan Solutions'
  });
  return true;
}

function buildMatchBriefingText_(result, agCount, anCount) {
  var lines = [
    'KAPLAN SOLUTIONS - MATCHING-BRIEFING',
    'Stand: ' + result.scanned_at,
    '',
    'PORTFOLIO',
    '  Bauherren (Auftraggeber):  ' + agCount,
    '  Partner-Firmen:            ' + anCount,
    '  Matches gesamt (ab 50%):   ' + result.total_matches,
    '  Heiss (ab 75%):            ' + result.hot,
    '  Gut (60-74%):              ' + result.good,
    '',
    'TOP MATCHES - JETZT VERMITTELN',
    '----------------------------------------'
  ];

  if (!result.top || !result.top.length) {
    lines.push('  Noch keine Matches ab 50%. Portfolio waechst - weiter sammeln.');
  } else {
    result.top.forEach(function (p, i) {
      lines.push(
        (i + 1) + '. [' + p.score + '%] ' + priorityLabelEmail_(p.score) +
        ' - ' + (p.agFirma || p.agName) + ' / ' + (p.anFirma || p.anName) +
        '\n     Region: ' + p.stadt + ' | ' + p.reasons +
        '\n     AG: ' + p.agEmail + ' | AN: ' + p.anEmail +
        '\n     -> ' + nextStepLabel_(p.score) + '\n'
      );
    });
  }

  lines.push('', 'Google Sheet oeffnen: Tab "Top Matches" fuer das vollstaendige Ranking.');
  return lines.join('\n');
}

function buildMatchBriefingHtml_(result, agCount, anCount) {
  var GOLD = '#b87333';
  var GREEN = '#0b3d2e';
  var MUTED = '#666666';
  var TEXT = '#1a1a1a';

  var kpi = function (label, value, highlight) {
    var bg = highlight ? '#faf6f0' : '#ffffff';
    var border = highlight ? 'border:1px solid ' + GOLD + ';' : 'border:1px solid #e8e8e8;';
    return '<td width="50%" style="padding:6px;vertical-align:top">' +
      '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="' + border + 'background:' + bg + '">' +
      '<tr><td style="padding:14px 16px">' +
      '<p style="margin:0 0 4px;font-family:Arial,Helvetica,sans-serif;font-size:10px;letter-spacing:0.15em;text-transform:uppercase;color:' + MUTED + '">' + escapeHtml_(label) + '</p>' +
      '<p style="margin:0;font-family:Georgia,\'Times New Roman\',serif;font-size:28px;color:' + TEXT + ';font-weight:400">' + escapeHtml_(String(value)) + '</p>' +
      '</td></tr></table></td>';
  };

  var htmlRows = '';
  (result.top || []).forEach(function (p, i) {
    var prio = priorityLabelEmail_(p.score);
    var prioColor = p.score >= 75 ? GOLD : (p.score >= 60 ? GREEN : MUTED);
    var rowBg = i % 2 === 0 ? '#ffffff' : '#fafafa';
    htmlRows +=
      '<tr style="background:' + rowBg + '">' +
      '<td style="padding:12px 10px;font-family:Arial,Helvetica,sans-serif;font-size:13px;color:' + TEXT + ';border-bottom:1px solid #eeeeee;text-align:center;font-weight:bold">' + (i + 1) + '</td>' +
      '<td style="padding:12px 10px;font-family:Arial,Helvetica,sans-serif;font-size:11px;font-weight:bold;letter-spacing:0.08em;color:' + prioColor + ';border-bottom:1px solid #eeeeee">' + escapeHtml_(prio) + '</td>' +
      '<td style="padding:12px 10px;font-family:Georgia,serif;font-size:16px;font-weight:bold;color:' + GREEN + ';border-bottom:1px solid #eeeeee;text-align:center">' + p.score + '%</td>' +
      '<td style="padding:12px 10px;font-family:Arial,Helvetica,sans-serif;font-size:13px;color:' + TEXT + ';border-bottom:1px solid #eeeeee">' +
        '<strong>' + escapeHtml_(p.agFirma || p.agName) + '</strong><br>' +
        '<a href="mailto:' + escapeHtml_(p.agEmail) + '" style="color:' + GOLD + ';text-decoration:none;font-size:12px">' + escapeHtml_(p.agEmail) + '</a></td>' +
      '<td style="padding:12px 10px;font-family:Arial,Helvetica,sans-serif;font-size:13px;color:' + TEXT + ';border-bottom:1px solid #eeeeee">' +
        '<strong>' + escapeHtml_(p.anFirma || p.anName) + '</strong><br>' +
        '<a href="mailto:' + escapeHtml_(p.anEmail) + '" style="color:' + GOLD + ';text-decoration:none;font-size:12px">' + escapeHtml_(p.anEmail) + '</a></td>' +
      '<td style="padding:12px 10px;font-family:Arial,Helvetica,sans-serif;font-size:12px;color:' + MUTED + ';border-bottom:1px solid #eeeeee">' +
        escapeHtml_(p.stadt) + '<br><span style="color:#999999">' + escapeHtml_(p.reasons) + '</span></td>' +
      '<td style="padding:12px 10px;font-family:Arial,Helvetica,sans-serif;font-size:12px;color:' + TEXT + ';border-bottom:1px solid #eeeeee;line-height:1.5">' +
        escapeHtml_(nextStepLabel_(p.score)) + '</td></tr>';
  });

  if (!htmlRows) {
    htmlRows = '<tr><td colspan="7" style="padding:24px 16px;font-family:Arial,Helvetica,sans-serif;font-size:14px;color:' + MUTED + ';text-align:center;border-bottom:1px solid #eeeeee">' +
      'Noch keine Matches ab 50% Passung. Das Portfolio w\u00e4chst \u2014 neue Leads werden laufend gepr\u00fcft.</td></tr>';
  }

  return '<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>' +
    '<body style="margin:0;padding:0;background:#f0f0f0">' +
    '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f0f0f0;padding:28px 12px">' +
    '<tr><td align="center">' +
    '<table role="presentation" width="640" cellspacing="0" cellpadding="0" style="max-width:640px;width:100%;background:#ffffff;border:1px solid #e0e0e0">' +

    '<tr><td style="padding:28px 32px 24px;background:' + GREEN + ';border-bottom:3px solid ' + GOLD + '">' +
    '<p style="margin:0 0 6px;font-family:Arial,Helvetica,sans-serif;font-size:10px;letter-spacing:0.35em;text-transform:uppercase;color:' + GOLD + '">Kaplan Solutions</p>' +
    '<p style="margin:0;font-family:Georgia,\'Times New Roman\',serif;font-size:24px;color:#ffffff;font-weight:400">Matching-Briefing</p>' +
    '<p style="margin:10px 0 0;font-family:Arial,Helvetica,sans-serif;font-size:12px;color:#c8d4ce">Stand: ' + escapeHtml_(result.scanned_at) + ' Uhr</p>' +
    '</td></tr>' +

    '<tr><td style="padding:24px 32px 8px">' +
    '<p style="margin:0 0 14px;font-family:Arial,Helvetica,sans-serif;font-size:10px;letter-spacing:0.2em;text-transform:uppercase;color:' + GOLD + '">Portfolio-\u00dcbersicht</p>' +
    '<table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr>' +
    kpi('Bauherren', agCount, false) +
    kpi('Partner-Firmen', anCount, false) +
    '</tr><tr><td colspan="2" style="height:8px"></td></tr><tr>' +
    kpi('Matches gesamt', result.total_matches, false) +
    kpi('Hei\u00dfe Matches', result.hot, true) +
    '</tr></table>' +
    '</td></tr>' +

    '<tr><td style="padding:16px 32px 8px">' +
    '<p style="margin:0 0 14px;font-family:Arial,Helvetica,sans-serif;font-size:10px;letter-spacing:0.2em;text-transform:uppercase;color:' + GOLD + '">Top Matches \u2014 Vermittlungspriorit\u00e4t</p>' +
    '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #e8e8e8">' +
    '<tr style="background:' + GREEN + '">' +
    '<th style="padding:10px 8px;font-family:Arial,Helvetica,sans-serif;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:#d9b75a;font-weight:normal">#</th>' +
    '<th style="padding:10px 8px;font-family:Arial,Helvetica,sans-serif;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:#d9b75a;font-weight:normal">Prio</th>' +
    '<th style="padding:10px 8px;font-family:Arial,Helvetica,sans-serif;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:#d9b75a;font-weight:normal">Passung</th>' +
    '<th style="padding:10px 8px;font-family:Arial,Helvetica,sans-serif;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:#d9b75a;font-weight:normal;text-align:left">Bauherr</th>' +
    '<th style="padding:10px 8px;font-family:Arial,Helvetica,sans-serif;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:#d9b75a;font-weight:normal;text-align:left">Partner</th>' +
    '<th style="padding:10px 8px;font-family:Arial,Helvetica,sans-serif;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:#d9b75a;font-weight:normal;text-align:left">Region</th>' +
    '<th style="padding:10px 8px;font-family:Arial,Helvetica,sans-serif;font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:#d9b75a;font-weight:normal;text-align:left">N\u00e4chster Schritt</th>' +
    '</tr>' + htmlRows +
    '</table></td></tr>' +

    '<tr><td style="padding:8px 32px 28px">' +
    '<p style="margin:0;font-family:Arial,Helvetica,sans-serif;font-size:12px;color:#999999;line-height:1.6">' +
    'Vollst\u00e4ndiges Ranking im Google Sheet unter dem Tab <strong style="color:' + TEXT + '">Top Matches</strong>. ' +
    'Automatischer Scan alle 60 Minuten.</p>' +
    '</td></tr>' +

    '<tr><td style="padding:20px 32px;background:#fafafa;border-top:1px solid #e8e8e8">' +
    '<p style="margin:0;font-family:Arial,Helvetica,sans-serif;font-size:11px;color:#aaaaaa;line-height:1.5">' +
    'Kaplan Solutions &middot; Partnervermittlung Bau &middot; kaplan-solutions.de</p>' +
    '</td></tr>' +

    '</table></td></tr></table></body></html>';
}

// -- Hilfsfunktionen -----------------------------------------------------------

function getOrCreateFolder_(parent, name) {
  var folders = parent.getFoldersByName(name);
  return folders.hasNext() ? folders.next() : parent.createFolder(name);
}

function safeName_(text) {
  return String(text || 'Unbekannt')
    .replace(/[\\/:*?"<>|]/g, '-')
    .replace(/\s+/g, ' ')
    .trim()
    .substring(0, 80) || 'Unbekannt';
}

function appendToTab_(ss, tabName, row) {
  ss.getSheetByName(tabName).appendRow(row);
}

function parsePayload_(e) {
  if (!e || !e.postData || !e.postData.contents) {
    throw new Error('Keine POST-Daten');
  }
  return JSON.parse(e.postData.contents);
}

function jsonResponse_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

// -- Einmalige Wartungs-Funktionen ---------------------------------------------

/** Manuell ausfuehren: Matching-Briefing per E-Mail senden (Test) */
function testMatchingBriefing() {
  sendDailyMatchBriefingScheduled_();
  Logger.log('Briefing gesendet an: ' + getAdminEmail_());
}

/** Manuell ausfuehren: Match-Scan sofort starten */
function testMatchScan() {
  rescanAllMatchesScheduled_();
  Logger.log('Match-Scan abgeschlossen.');
}

/** Einmal ausfuehren -> Berechtigungen erteilen */
function testBerechtigung() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var root = DriveApp.getRootFolder();
  var test = root.createFolder('_kaplan_test');
  test.setTrashed(true);
  Logger.log('Alles OK - Sheet: ' + ss.getName() + ' / Drive Schreiben funktioniert');
}

// -- CRM Pipeline (Salesforce-aehnlich) ----------------------------------------

function isBauherrRole_(rolle) {
  var r = String(rolle || '').toLowerCase();
  return r.indexOf('auftraggeber') >= 0 || r.indexOf('bauherr') >= 0;
}

function crmStagesForRole_(rolle) {
  return isBauherrRole_(rolle) ? BAUHERR_STAGES : PARTNER_STAGES;
}

function initialCrmStage_(roleCode, data) {
  if (roleCode === 'bauherr') return 'Neu';
  if (data.bearbeitung === 'Outreach' || String(data.status_feld || '') === 'Outreach') {
    return 'Im Portfolio';
  }
  return 'Lead';
}

function formatLeadSource_(data) {
  var src = String(data.lead_source || data.quelle || '').trim();
  if (src) return src;
  var utm = [data.utm_source, data.utm_medium, data.utm_campaign].filter(Boolean).join(' / ');
  return utm || 'Website';
}

function stageIndex_(stages, stage) {
  var i = stages.indexOf(stage);
  return i >= 0 ? i : -1;
}

function isTerminalCrmStage_(rolle, stage) {
  stage = String(stage || '');
  if (isBauherrRole_(rolle)) {
    return stage === 'Abgeschlossen' || stage === 'Verloren / Pause' || stage === 'Auftrag erteilt';
  }
  return stage === 'Provision bezahlt' || stage === 'Verloren / Inaktiv';
}

function crmNextStepForStage_(roleCode, stage, bestScore) {
  var isBh = roleCode === 'bauherr';
  if (bestScore >= 75) {
    return isBh ? 'Jetzt anrufen & Erstgespraech koordinieren' : 'Partner-Vertrag + Intro vorbereiten';
  }
  if (bestScore >= 60) {
    return 'Kurz anrufen und Passung pruefen';
  }
  var map = {
    'Neu': 'Follow-up senden / anrufen',
    'Lead': 'Erstgespraech anbieten',
    'Kontaktiert': 'Erstgespraech terminieren',
    'Erstgespr\u00e4ch geplant': 'Termin im Kalender bestaetigen',
    'Erstgespr\u00e4ch gef\u00fchrt': isBh ? 'Qualifizieren (Budget, Timing)' : 'Vertrag versenden',
    'Qualifiziert': 'Matching abwarten',
    'Matching l\u00e4uft': 'Top Matches pruefen',
    'Match vorgeschlagen': 'Erstkontakt CC beide Parteien',
    'Match erhalten': 'Intro mit Anlage senden',
    'Vertrag versendet': 'Vertrag nachfassen',
    'Vertrag unterschrieben': 'Matching aktiv halten',
    'Im Portfolio': 'Bei Hot Match sofort melden',
    'Erstkontakt': 'Verhandlung begleiten',
    'In Verhandlung': 'Abschluss pruefen',
    'Auftrag \u00fcber Vermittlung': 'Provision berechnen',
    'Provision f\u00e4llig': 'Rechnung senden',
    'Provision bezahlt': 'Fertig — Beziehung pflegen',
    'Abgeschlossen': 'Optional: Zufriedenheit checken',
    'Verloren / Pause': 'Reaktivieren-Datum setzen',
    'Verloren / Inaktiv': 'Reaktivieren-Datum setzen'
  };
  return map[stage] || 'Seriositaet + Matches pruefen';
}

function mapLegacyPipelineStatus_(rolle, oldStatus) {
  var isBh = isBauherrRole_(rolle);
  var s = String(oldStatus || '').trim();
  if (s === 'In Bearbeitung') return isBh ? 'Kontaktiert' : 'Erstgespr\u00e4ch geplant';
  if (s === 'Vermittelt') return isBh ? 'Match vorgeschlagen' : 'Match erhalten';
  if (s === 'Abgeschlossen') return isBh ? 'Abgeschlossen' : 'Provision bezahlt';
  if (s === 'Abgelehnt') return isBh ? 'Verloren / Pause' : 'Verloren / Inaktiv';
  if (s === 'Neu') return isBh ? 'Neu' : 'Lead';
  return s || (isBh ? 'Neu' : 'Lead');
}

function ensurePipelineCrm_(ss) {
  var sheet = ss.getSheetByName(TAB_PIPELINE);
  if (!sheet) return;
  var lastCol = sheet.getLastColumn();
  var headers = sheet.getRange(1, 1, 1, Math.max(lastCol, 1)).getValues()[0];

  if (String(headers[6] || '') === 'Pipeline-Status') {
    headers[6] = 'Stage';
    sheet.getRange(1, 7).setValue('Stage');
  }

  if (headers.length < PIPELINE_HEADERS.length ||
      String(headers[headers.length - 1] || '') !== 'Ordner-Link') {
    sheet.getRange(1, 1, 1, PIPELINE_HEADERS.length).setValues([PIPELINE_HEADERS]);
    styleHeader_(sheet, PIPELINE_HEADERS.length);
    sheet.setFrozenRows(1);
  }

  if (sheet.getLastRow() > 1) {
    var rows = sheet.getLastRow() - 1;
    var block = sheet.getRange(2, 1, rows, PIPELINE_HEADERS.length).getValues();
    for (var i = 0; i < block.length; i++) {
      var rolle = String(block[i][3] || '');
      var roleCode = isBauherrRole_(rolle) ? 'bauherr' : 'unternehmen';
      if (!block[i][6]) {
        block[i][6] = isBauherrRole_(rolle) ? 'Neu' : 'Lead';
      } else if (BAUHERR_STAGES.indexOf(block[i][6]) < 0 && PARTNER_STAGES.indexOf(block[i][6]) < 0) {
        block[i][6] = mapLegacyPipelineStatus_(rolle, block[i][6]);
      }
      if (!block[i][11]) block[i][11] = 'Website';
      if (!block[i][13]) block[i][13] = 'Nein';
      if (!block[i][14]) block[i][14] = 'Nein';
      if (!block[i][18]) block[i][18] = 'Nein';
      if (!block[i][12]) {
        var best = parseInt(String(block[i][9] || '0').replace('%', ''), 10) || 0;
        block[i][12] = crmNextStepForStage_(roleCode, block[i][6], best);
      }
    }
    sheet.getRange(2, 1, rows, PIPELINE_HEADERS.length).setValues(block);
  }

  setupAppearance_(sheet, TAB_PIPELINE, PIPELINE_HEADERS.length);
}

function bestMatchScoreForRef_(pairs, ref) {
  var best = 0;
  pairs.forEach(function (p) {
    if (p.agRef === ref || p.anRef === ref) {
      if (p.score > best) best = p.score;
    }
  });
  return best;
}

function syncCrmPipelineFromMatches_(ss, pairs) {
  var sheet = ss.getSheetByName(TAB_PIPELINE);
  if (!sheet || sheet.getLastRow() < 2) return;
  var values = sheet.getRange(2, 1, sheet.getLastRow() - 1, PIPELINE_HEADERS.length).getValues();

  for (var i = 0; i < values.length; i++) {
    var ref = String(values[i][0] || '');
    if (!ref) continue;
    var rolle = String(values[i][3] || '');
    var roleCode = isBauherrRole_(rolle) ? 'bauherr' : 'unternehmen';
    var stages = crmStagesForRole_(rolle);
    var stage = String(values[i][6] || '');
    var best = bestMatchScoreForRef_(pairs, ref);
    var rowNum = i + 2;

    if (best > 0) {
      sheet.getRange(rowNum, 10).setValue(best + '%').setBackground(matchColor_(best));
    }

    var matchCount = 0;
    pairs.forEach(function (p) {
      if (p.agRef === ref || p.anRef === ref) matchCount++;
    });
    if (matchCount > 0) sheet.getRange(rowNum, 9).setValue(matchCount);

    var targetStage = '';
    if (best >= 75) {
      targetStage = roleCode === 'bauherr' ? 'Match vorgeschlagen' : 'Match erhalten';
    } else if (best >= 50 && matchCount > 0) {
      targetStage = roleCode === 'bauherr' ? 'Matching l\u00e4uft' : stage;
    }

    if (targetStage && stageIndex_(stages, targetStage) > stageIndex_(stages, stage)) {
      stage = targetStage;
      sheet.getRange(rowNum, 7).setValue(stage);
    }

    if (String(values[i][18] || '') === 'Ja' && roleCode === 'unternehmen') {
      stage = 'Provision bezahlt';
      sheet.getRange(rowNum, 7).setValue(stage).setBackground(C_GREEN);
    }

    sheet.getRange(rowNum, 13).setValue(crmNextStepForStage_(roleCode, stage, best));
  }
}

function verifyCrmSecret_(data) {
  var secret = String(data.crm_secret || data.secret || '');
  if (!secret) return false;
  try {
    var meta = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(META_SHEET);
    var stored = meta ? String(meta.getRange('B7').getValue() || '') : '';
    if (stored && secret === stored) return true;
  } catch (e) {}
  var prop = PropertiesService.getScriptProperties().getProperty('CRM_SECRET');
  return prop && secret === prop;
}

function pipelineRowToCrmObject_(row) {
  var lead = {
    ref: String(row[0] || ''),
    eingegangen: String(row[1] || ''),
    name: String(row[2] || ''),
    rolle: String(row[3] || ''),
    branche: String(row[4] || ''),
    stadt: String(row[5] || ''),
    stage: String(row[6] || ''),
    seriositaet: String(row[7] || ''),
    matches: row[8] || 0,
    best_match: String(row[9] || ''),
    naechster_termin: String(row[10] || ''),
    quelle: String(row[11] || ''),
    naechster_schritt: String(row[12] || ''),
    vertrag: String(row[13] || ''),
    intro_gesendet: String(row[14] || ''),
    netto: String(row[15] || ''),
    provision: String(row[16] || ''),
    rechnung: String(row[17] || ''),
    bezahlt: String(row[18] || ''),
    verloren_grund: String(row[19] || ''),
    notiz: String(row[20] || ''),
    ordner_link: String(row[21] || ''),
    role_type: isBauherrRole_(row[3]) ? 'bauherr' : 'partner',
    stages: crmStagesForRole_(row[3]),
    terminal: isTerminalCrmStage_(row[3], row[6])
  };
  lead.lead_status = sfLeadStatusFromStage_(lead);
  lead.company = lead.name;
  lead.record_type = lead.role_type === 'bauherr' ? 'Bauherr Lead' : 'Partner Lead';
  return lead;
}

function sfLeadStatusFromStage_(lead) {
  var s = String(lead.stage || '');
  if (s.indexOf('Verloren') >= 0) return 'Closed - Not Converted';
  if (lead.terminal || s === 'Abgeschlossen' || s === 'Provision bezahlt' || s === 'Auftrag erteilt') {
    return 'Closed - Converted';
  }
  if (s.indexOf('Kontakt') >= 0 || s.indexOf('Erstgespr') >= 0 || s.indexOf('Qualifiziert') >= 0 ||
      s.indexOf('Vertrag') >= 0 || s.indexOf('Match') >= 0) {
    return 'Working - Contacted';
  }
  return 'Open - Not Contacted';
}

function sfOppStageFromMatch_(status, score) {
  status = String(status || 'Neu');
  if (status === 'Vermittelt') return 'Closed Won';
  if (status === 'Abgelehnt') return 'Closed Lost';
  if (status === 'In Kontakt') return 'Negotiation/Review';
  if (score >= 75) return 'Proposal/Price Quote';
  if (score >= 60) return 'Needs Analysis';
  return 'Qualification';
}

function buildCrmOpportunities_(ss) {
  var sheet = ss.getSheetByName(TAB_TOP_MATCHES);
  var opps = [];
  if (!sheet || sheet.getLastRow() < 2) return opps;
  var values = sheet.getDataRange().getValues();
  for (var i = 1; i < values.length; i++) {
    var r = values[i];
    var matchId = String(r[14] || '');
    if (!matchId) continue;
    var score = Number(r[2]) || 0;
    var status = String(r[3] || 'Neu');
    var stage = sfOppStageFromMatch_(status, score);
    var amount = '';
    opps.push({
      id: matchId,
      name: (r[4] || '') + ' \u2194 ' + (r[7] || ''),
      account_name: String(r[4] || ''),
      partner_name: String(r[7] || ''),
      ag_ref: String(r[6] || ''),
      an_ref: String(r[9] || ''),
      stage: stage,
      stages: SF_OPP_STAGES,
      amount: amount,
      probability: score,
      close_date: '',
      status: status,
      score: score,
      priority: String(r[1] || ''),
      region: String(r[10] || ''),
      branche: String(r[11] || ''),
      next_step: String(r[13] || ''),
      terminal: stage === 'Closed Won' || stage === 'Closed Lost'
    });
  }
  return opps;
}

function buildCrmAccounts_(leads) {
  var map = {};
  leads.forEach(function (l) {
    var key = (l.company || l.name || l.ref).toLowerCase();
    if (!key) return;
    if (!map[key]) {
      map[key] = {
        id: 'ACC-' + l.ref,
        name: l.company || l.name,
        type: l.role_type === 'bauherr' ? 'Bauherr' : 'Partner',
        city: l.stadt,
        industry: l.branche,
        lead_ref: l.ref,
        phone: '',
        website: l.ordner_link || ''
      };
    }
  });
  return Object.keys(map).map(function (k) { return map[k]; });
}

function buildCrmContacts_(leads) {
  return leads.map(function (l) {
    return {
      id: 'CON-' + l.ref,
      name: l.name,
      account_name: l.company || l.name,
      email: l.email || '',
      phone: l.telefon || '',
      lead_ref: l.ref,
      title: l.rolle,
      city: l.stadt
    };
  });
}

function loadCrmActivities_(ss) {
  var sheet = ss.getSheetByName(TAB_ACTIVITIES);
  var out = [];
  if (!sheet || sheet.getLastRow() < 2) return out;
  var values = sheet.getDataRange().getValues();
  for (var i = 1; i < values.length; i++) {
    var r = values[i];
    if (!r[0]) continue;
    out.push({
      id: String(r[0]),
      related_type: String(r[1] || ''),
      related_id: String(r[2] || ''),
      type: String(r[3] || 'Task'),
      subject: String(r[4] || ''),
      due: String(r[5] || ''),
      end: String(r[6] || ''),
      status: String(r[7] || 'Not Started'),
      description: String(r[8] || ''),
      created: String(r[9] || '')
    });
  }
  return out;
}

function nextActivityId_(ss) {
  var sheet = ss.getSheetByName(TAB_ACTIVITIES);
  var n = Math.max(0, (sheet ? sheet.getLastRow() : 1) - 1) + 1;
  return 'ACT-' + Utilities.formatDate(new Date(), TZ, 'yyyy') + '-' + ('0000' + n).slice(-4);
}

function handleCrmActivityCreate_(data) {
  if (!verifyCrmSecret_(data)) return jsonResponse_({ ok: false, error: 'unauthorized' });
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ensureStructure_(ss);
  var sheet = ss.getSheetByName(TAB_ACTIVITIES);
  var id = nextActivityId_(ss);
  var now = Utilities.formatDate(new Date(), TZ, 'dd.MM.yyyy HH:mm');
  sheet.appendRow([
    id,
    String(data.related_type || 'Lead'),
    String(data.related_id || ''),
    String(data.type || 'Task'),
    String(data.subject || ''),
    String(data.due || data.start || ''),
    String(data.end || ''),
    String(data.status || 'Not Started'),
    String(data.description || ''),
    now
  ]);
  if (data.sync_termin && data.related_type === 'Lead') {
    handleCrmUpdate_({ crm_secret: data.crm_secret, ref: data.related_id,
      fields: { naechster_termin: String(data.due || data.start || '') } });
  }
  return jsonResponse_({ ok: true, action: 'crm_activity_create', activity: {
    id: id, related_type: data.related_type, related_id: data.related_id,
    type: data.type, subject: data.subject, due: data.due, status: data.status || 'Not Started',
    description: data.description, created: now
  }});
}

function handleCrmActivityUpdate_(data) {
  if (!verifyCrmSecret_(data)) return jsonResponse_({ ok: false, error: 'unauthorized' });
  var id = String(data.id || '').trim();
  if (!id) return jsonResponse_({ ok: false, error: 'id fehlt' });
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(TAB_ACTIVITIES);
  if (!sheet) return jsonResponse_({ ok: false, error: 'Activities tab fehlt' });
  var values = sheet.getDataRange().getValues();
  for (var i = 1; i < values.length; i++) {
    if (String(values[i][0]) !== id) continue;
    var fields = data.fields || {};
    if (fields.status) sheet.getRange(i + 1, 8).setValue(fields.status);
    if (fields.subject) sheet.getRange(i + 1, 5).setValue(fields.subject);
    if (fields.due) sheet.getRange(i + 1, 6).setValue(fields.due);
    if (fields.description) sheet.getRange(i + 1, 9).setValue(fields.description);
    return jsonResponse_({ ok: true, action: 'crm_activity_update', id: id });
  }
  return jsonResponse_({ ok: false, error: 'Activity nicht gefunden' });
}

function handleCrmOpportunityUpdate_(data) {
  if (!verifyCrmSecret_(data)) return jsonResponse_({ ok: false, error: 'unauthorized' });
  var id = String(data.id || data.match_id || '').trim();
  if (!id) return jsonResponse_({ ok: false, error: 'id fehlt' });
  var stage = String(data.stage || '');
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var statusMap = {
    'Closed Won': 'Vermittelt',
    'Closed Lost': 'Abgelehnt',
    'Negotiation/Review': 'In Kontakt',
    'Proposal/Price Quote': 'In Kontakt',
    'Needs Analysis': 'Neu',
    'Qualification': 'Neu'
  };
  var newStatus = statusMap[stage] || String(data.status || 'Neu');
  [TAB_TOP_MATCHES, TAB_MATCHES].forEach(function (tabName) {
    var sheet = ss.getSheetByName(tabName);
    if (!sheet || sheet.getLastRow() < 2) return;
    var idCol = tabName === TAB_TOP_MATCHES ? 15 : 13;
    var statusCol = tabName === TAB_TOP_MATCHES ? 4 : 2;
    var ids = sheet.getRange(2, idCol, sheet.getLastRow() - 1, 1).getValues();
    for (var i = 0; i < ids.length; i++) {
      if (String(ids[i][0]) === id) {
        sheet.getRange(i + 2, statusCol).setValue(newStatus);
        break;
      }
    }
  });
  return jsonResponse_({ ok: true, action: 'crm_opportunity_update', id: id, stage: stage, status: newStatus });
}

function buildLeadDetailMap_(ss) {
  var map = {};
  [TAB_ALL, TAB_AUFTRAGGEBER, TAB_AUFTRAGNEHMER, TAB_PORTFOLIO].forEach(function (tabName) {
    var sheet = ss.getSheetByName(tabName);
    if (!sheet || sheet.getLastRow() < 2) return;
    var values = sheet.getDataRange().getValues();
    var idx = indexMapLead_(values[0]);
    for (var r = 1; r < values.length; r++) {
      var row = values[r];
      var ref = String(row[idx.ref] || '');
      if (!ref) continue;
      map[ref] = {
        email: String(row[idx.email] || ''),
        telefon: String(row[idx.telefon] || ''),
        firma: String(row[idx.firma] || ''),
        budget: idx.budget >= 0 ? String(row[idx.budget] || '') : '',
        projekt: idx.projekt >= 0 ? String(row[idx.projekt] || '') : '',
        nachricht: idx.nachricht >= 0 ? String(row[idx.nachricht] || '') : ''
      };
    }
  });
  return map;
}

function enrichLeadFromDetail_(lead, detailMap) {
  var d = detailMap[lead.ref];
  if (!d) return lead;
  if (d.email) lead.email = d.email;
  if (d.telefon && d.telefon !== '\u2014') lead.telefon = d.telefon;
  if (d.firma && d.firma !== '\u2014') lead.company = d.firma;
  if (d.budget) lead.budget = d.budget;
  if (d.projekt) lead.projekt = d.projekt;
  if (d.nachricht) lead.nachricht = d.nachricht;
  return lead;
}

function portfolioRowToCrmObject_(row) {
  var ref = String(row[0] || '');
  var stage = String(row[21] || '').trim();
  if (!stage || stage === 'Outreach' || stage === '-') stage = 'Im Portfolio';
  var lead = {
    ref: ref,
    eingegangen: String(row[1] || ''),
    name: String(row[3] || ''),
    rolle: String(row[2] || 'Auftragnehmer'),
    branche: String(row[7] || ''),
    stadt: String(row[8] || ''),
    stage: stage,
    seriositaet: String(row[19] || '-'),
    matches: row[20] || 0,
    best_match: '-',
    naechster_termin: '',
    quelle: 'Outreach',
    naechster_schritt: 'Cold Lead kontaktieren / qualifizieren',
    vertrag: 'Nein',
    intro_gesendet: 'Nein',
    netto: '',
    provision: '',
    rechnung: '',
    bezahlt: 'Nein',
    verloren_grund: '',
    notiz: String(row[17] || '').substring(0, 300),
    ordner_link: String(row[24] || ''),
    role_type: 'partner',
    stages: PARTNER_STAGES,
    terminal: isTerminalCrmStage_(row[2], stage),
    cold_lead: true,
    email: String(row[4] || ''),
    telefon: String(row[5] || ''),
    company: String(row[6] || row[3] || '')
  };
  lead.lead_status = sfLeadStatusFromStage_(lead);
  lead.record_type = 'Cold Outreach Lead';
  return lead;
}

function buildColdLeadsFromPortfolio_(ss, pipelineRefSet, detailMap) {
  var sheet = ss.getSheetByName(TAB_PORTFOLIO);
  var out = [];
  if (!sheet || sheet.getLastRow() < 2) return out;
  var values = sheet.getDataRange().getValues();
  for (var r = 1; r < values.length; r++) {
    var ref = String(values[r][0] || '');
    if (!ref || pipelineRefSet[ref]) continue;
    out.push(enrichLeadFromDetail_(portfolioRowToCrmObject_(values[r]), detailMap));
  }
  return out;
}

function ensurePipelineRowForColdLead_(ss, ref) {
  var pipeSheet = ss.getSheetByName(TAB_PIPELINE);
  var existing = findRowByRef_(pipeSheet, ref, 1);
  if (existing > 0) return existing;

  var portSheet = ss.getSheetByName(TAB_PORTFOLIO);
  var portRow = findRowByRef_(portSheet, ref, 1);
  if (portRow < 1) return -1;

  var row = portSheet.getRange(portRow, 1, 1, LEAD_HEADERS.length).getValues()[0];
  var data = {
    role_code: 'unternehmen',
    eingegangen: String(row[1] || ''),
    rolle: String(row[2] || 'Auftragnehmer'),
    name: String(row[3] || ''),
    email: String(row[4] || ''),
    telefon: String(row[5] || ''),
    firma: String(row[6] || ''),
    branche: String(row[7] || ''),
    stadt: String(row[8] || ''),
    source: 'outreach'
  };
  var folderUrl = String(row[24] || '');
  var matchCount = Number(row[20]) || 0;
  var serios = String(row[19] || '-');
  var stage = String(row[21] || '').trim();
  if (!stage || stage === 'Outreach' || stage === '-') stage = 'Im Portfolio';

  pipeSheet.appendRow([
    ref, data.eingegangen, data.name || data.firma, data.rolle,
    data.branche, data.stadt, stage, serios, matchCount, '-',
    '', 'Outreach', crmNextStepForStage_('unternehmen', stage, 0),
    'Nein', 'Nein', '', '', '', 'Nein', '', String(row[17] || '').substring(0, 300),
    folderUrl
  ]);
  return pipeSheet.getLastRow();
}

function computeCrmFingerprint_(leads, opportunities, activities) {
  var parts = [
    leads.length,
    opportunities.length,
    activities.length,
    leads.map(function (l) { return l.ref + ':' + l.stage; }).join('|'),
    opportunities.map(function (o) { return o.id + ':' + o.stage; }).join('|')
  ];
  return Utilities.base64EncodeWebSafe(String(parts.join('::')).substring(0, 500));
}

function handleCrmSnapshot_(data) {
  if (!verifyCrmSecret_(data)) {
    return jsonResponse_({ ok: false, error: 'unauthorized' });
  }
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var detailMap = buildLeadDetailMap_(ss);
  var sheet = ss.getSheetByName(TAB_PIPELINE);
  var leads = [];
  var pipelineRefSet = {};
  if (sheet && sheet.getLastRow() > 1) {
    var values = sheet.getRange(2, 1, sheet.getLastRow() - 1, PIPELINE_HEADERS.length).getValues();
    values.forEach(function (row) {
      if (!row[0]) return;
      pipelineRefSet[String(row[0])] = true;
      leads.push(enrichLeadFromDetail_(pipelineRowToCrmObject_(row), detailMap));
    });
  }
  var coldLeads = buildColdLeadsFromPortfolio_(ss, pipelineRefSet, detailMap);
  leads = leads.concat(coldLeads);
  var today = Utilities.formatDate(new Date(), TZ, 'dd.MM.yyyy');
  var termine_heute = leads.filter(function (l) {
    return l.naechster_termin && l.naechster_termin.indexOf(today) >= 0;
  });
  var hot = leads.filter(function (l) {
    var s = parseInt(String(l.best_match).replace('%', ''), 10) || 0;
    return s >= 75 && !l.terminal;
  });
  var opportunities = buildCrmOpportunities_(ss);
  var accounts = buildCrmAccounts_(leads);
  var contacts = buildCrmContacts_(leads);
  var activities = loadCrmActivities_(ss);
  var tasks_today = activities.filter(function (a) {
    return a.type === 'Task' && a.due && a.due.indexOf(today) >= 0 && a.status !== 'Completed';
  });
  var events_today = activities.filter(function (a) {
    return a.type === 'Event' && a.due && a.due.indexOf(today) >= 0;
  });
  return jsonResponse_({
    ok: true,
    action: 'crm_snapshot',
    platform: 'Salesforce Lightning (Kaplan)',
    updated: Utilities.formatDate(new Date(), TZ, 'dd.MM.yyyy HH:mm'),
    snapshot_fingerprint: computeCrmFingerprint_(leads, opportunities, activities),
    bauherr_stages: BAUHERR_STAGES,
    partner_stages: PARTNER_STAGES,
    opp_stages: SF_OPP_STAGES,
    lead_statuses: SF_LEAD_STATUS,
    leads: leads,
    opportunities: opportunities,
    accounts: accounts,
    contacts: contacts,
    activities: activities,
    stats: {
      total: leads.length,
      open: leads.filter(function (l) { return !l.terminal; }).length,
      bauherr: leads.filter(function (l) { return l.role_type === 'bauherr'; }).length,
      partner: leads.filter(function (l) { return l.role_type === 'partner'; }).length,
      cold: leads.filter(function (l) { return l.cold_lead; }).length,
      termine_heute: termine_heute.length,
      hot_matches: hot.length,
      opportunities: opportunities.length,
      open_opportunities: opportunities.filter(function (o) { return !o.terminal; }).length,
      accounts: accounts.length,
      tasks_today: tasks_today.length,
      events_today: events_today.length
    },
    termine_heute: termine_heute,
    hot_matches: hot,
    top_opportunities: opportunities.filter(function (o) { return !o.terminal; }).slice(0, 5),
    tasks_today: tasks_today,
    events_today: events_today
  });
}

function handleCrmUpdate_(data) {
  if (!verifyCrmSecret_(data)) {
    return jsonResponse_({ ok: false, error: 'unauthorized' });
  }
  var ref = String(data.ref || '').trim();
  if (!ref) return jsonResponse_({ ok: false, error: 'ref fehlt' });

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ensureStructure_(ss);
  var sheet = ss.getSheetByName(TAB_PIPELINE);
  var rowNum = findRowByRef_(sheet, ref, 1);
  if (rowNum < 1) {
    rowNum = ensurePipelineRowForColdLead_(ss, ref);
    if (rowNum < 1) return jsonResponse_({ ok: false, error: 'Lead nicht gefunden' });
  }

  var fields = data.fields || data.updates || {};
  var colMap = {
    stage: 7,
    naechster_termin: 11,
    quelle: 12,
    naechster_schritt: 13,
    vertrag: 14,
    intro_gesendet: 15,
    netto: 16,
    provision: 17,
    rechnung: 18,
    bezahlt: 19,
    verloren_grund: 20,
    notiz: 21
  };

  Object.keys(fields).forEach(function (key) {
    var col = colMap[key];
    if (!col) return;
    sheet.getRange(rowNum, col).setValue(fields[key]);
  });

  var row = sheet.getRange(rowNum, 1, 1, PIPELINE_HEADERS.length).getValues()[0];
  var roleCode = isBauherrRole_(row[3]) ? 'bauherr' : 'unternehmen';
  var stage = String(fields.stage || row[6] || '');
  var best = parseInt(String(row[9] || '0').replace('%', ''), 10) || 0;

  if (fields.bezahlt === 'Ja' && roleCode === 'unternehmen') {
    stage = 'Provision bezahlt';
    sheet.getRange(rowNum, 7).setValue(stage).setBackground(C_GREEN);
  }

  if (fields.stage || fields.bezahlt) {
    sheet.getRange(rowNum, 13).setValue(crmNextStepForStage_(roleCode, stage, best));
  }

  if (fields.stage && isTerminalCrmStage_(row[3], stage)) {
    sheet.getRange(rowNum, 7).setBackground(
      stage.indexOf('Verloren') >= 0 ? C_RED : C_GREEN2
    );
  }

  syncLeadPipelineStatus_(ss, ref, stage);
  updateDashboard_(ss);

  return jsonResponse_({
    ok: true,
    action: 'crm_update',
    ref: ref,
    lead: pipelineRowToCrmObject_(sheet.getRange(rowNum, 1, 1, PIPELINE_HEADERS.length).getValues()[0])
  });
}

function syncLeadPipelineStatus_(ss, ref, stage) {
  [TAB_ALL, TAB_AUFTRAGGEBER, TAB_AUFTRAGNEHMER, TAB_PORTFOLIO].forEach(function (tabName) {
    var sheet = ss.getSheetByName(tabName);
    var rowNum = findRowByRef_(sheet, ref, 1);
    if (rowNum > 0) sheet.getRange(rowNum, 22).setValue(stage);
  });
}

/** EINMAL ausfuehren: Pipeline auf CRM-Spalten upgraden + Stages migrieren. */
function crmPipelineMigrieren() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ensurePipelineCrm_(ss);
  var pairs = computeAllMatchPairs_(ss);
  syncCrmPipelineFromMatches_(ss, pairs);
  updateDashboard_(ss);
  Logger.log('CRM-Pipeline migriert. Leads: ' + (ss.getSheetByName(TAB_PIPELINE).getLastRow() - 1));
}

// -- Junk / Test-Leads -------------------------------------------------------

function isExplicitJunkName_(name) {
  name = String(name || '').trim();
  if (!name) return false;
  if (/test[\-\s]?anfrage/i.test(name)) return true;
  if (/^(max|maria|peter|anna)\s+mustermann$/i.test(name)) return true;
  if (/^(test|testing|dummy|fake|asdf|xxx)$/i.test(name)) return true;
  return false;
}

function looksLikeRealLead_(data) {
  var message = String(data.message || data.nachricht || '').trim();
  var phone = String(data.telefon || data.phone || '').replace(/\D/g, '');
  var budget = String(data.budget || '').trim();
  var timeline = String(data.zeitrahmen || data.timeline || '').trim();
  var projekt = String(data.projekt || data.project || '').trim();
  var location = String(data.standort || data.location || data.stadt || '').trim();

  if (message.length >= 45) return true;
  if (phone.length >= 9 && message.length >= 18) return true;
  if (projekt && timeline && budget && budget !== '\u2014' && budget !== '-') return true;
  if (location.length >= 4 && message.length >= 25 && phone.length >= 9) return true;
  return false;
}

/**
 * Konservative Junk-Erkennung: lieber ein Test-Lead behalten als einen echten loeschen.
 * Loeschen nur bei klarem Signal (strong) oder zwei schwachen Hinweisen — nie wenn es wie echt aussieht.
 */
function assessJunkLead_(data) {
  var name = String(data.name || '').trim();

  // Explizite Test-Namen immer entfernen — auch bei ausgefuelltem Formular
  if (isExplicitJunkName_(name)) {
    return { junk: true, reasons: ['name:test-anfrage'], confidence: 'high' };
  }

  if (looksLikeRealLead_(data)) {
    return { junk: false, reasons: [], confidence: 'protected-real' };
  }

  var email = String(data.email || '').trim().toLowerCase();
  var message = String(data.message || data.nachricht || '').trim();
  var msgLower = message.toLowerCase();
  var strong = [];
  var weak = [];

  if (!name && !email) strong.push('leer');

  if (/^test@|@example\.(com|org|de)|mailinator|yopmail|tempmail|guerrillamail|10minutemail|discard\.|trashmail/i.test(email)) {
    strong.push('email:wegwerf');
  }

  if (/^(test|nur test|dies ist ein test|bitte ignorieren|ignore this|formular test|testeintrag|nur ein test)\.?$/i.test(msgLower)) {
    strong.push('nachricht:explizit-test');
  }

  if (data.is_test === true || data.test_lead === true) strong.push('flag:test');

  var admin = String(getAdminEmail_() || '').trim().toLowerCase();
  if (admin && email === admin && /test[\-\s]?anfrage|nur test|formular test/i.test(name + ' ' + msgLower)) {
    strong.push('admin:self-test');
  }

  if (/^(test|probe|dummy)\b/i.test(name) && name.length < 35) weak.push('name:test-prefix');
  if (/\b(mustermann|musterfrau|john doe|jane doe|lorem ipsum)\b/i.test(name + ' ' + msgLower)) {
    weak.push('dummy-text');
  }
  if (/\btest\b/i.test(msgLower) && msgLower.length < 35) weak.push('nachricht:enthaelt-test');

  if (strong.length > 0) {
    return { junk: true, reasons: strong, confidence: 'high' };
  }
  if (weak.length >= 2) {
    return { junk: true, reasons: weak, confidence: 'medium' };
  }
  return { junk: false, reasons: weak, confidence: weak.length ? 'low' : 'ok' };
}

function leadRowToData_(row, idx) {
  return {
    name: row[idx.name],
    email: row[idx.email],
    telefon: row[idx.telefon],
    firma: row[idx.firma],
    nachricht: row[idx.nachricht],
    message: row[idx.nachricht],
    projekt: row[idx.projekt],
    budget: row[idx.budget],
    zeitrahmen: row[idx.zeitrahmen],
    standort: row[idx.standort],
    stadt: row[idx.stadt]
  };
}

function purgeJunkLeadsFromSheet_(ss) {
  ensureStructure_(ss);
  var removed = [];
  var refs = {};
  var leadTabs = [TAB_ALL, TAB_AUFTRAGGEBER, TAB_AUFTRAGNEHMER];

  leadTabs.forEach(function (tabName) {
    var sheet = ss.getSheetByName(tabName);
    if (!sheet || sheet.getLastRow() < 2) return;
    var values = sheet.getDataRange().getValues();
    var idx = indexMapLead_(values[0]);

    for (var r = values.length - 1; r >= 1; r--) {
      var row = values[r];
      var junk = assessJunkLead_(leadRowToData_(row, idx));
      if (!junk.junk) continue;
      if (junk.confidence !== 'high' && junk.confidence !== 'medium') continue;

      var ref = String(row[idx.ref] || '');
      sheet.deleteRow(r + 1);
      if (ref) {
        if (!refs[ref]) refs[ref] = junk.reasons;
        removed.push({ ref: ref, tab: tabName, reasons: junk.reasons });
      }
    }
  });

  Object.keys(refs).forEach(function (ref) {
    deleteLeadArtifacts_(ss, ref);
  });

  var pipelineRemoved = purgeJunkPipelineAndOrphans_(ss);
  if (pipelineRemoved) {
    removed = removed.concat(pipelineRemoved);
  }

  if (removed.length) {
    rescanAllMatchesFull_();
  } else {
    updateDashboard_(ss);
  }
  return { removed: removed.length, details: removed };
}

function collectValidLeadRefs_(ss) {
  var refs = {};
  [TAB_ALL, TAB_AUFTRAGGEBER, TAB_AUFTRAGNEHMER].forEach(function (tabName) {
    var sheet = ss.getSheetByName(tabName);
    if (!sheet || sheet.getLastRow() < 2) return;
    var vals = sheet.getRange(2, 1, sheet.getLastRow() - 1, 1).getValues();
    for (var i = 0; i < vals.length; i++) {
      var ref = String(vals[i][0] || '').trim();
      if (ref) refs[ref] = true;
    }
  });
  return refs;
}

/** Pipeline/Seriositaet: Test-Namen, leere Outreach-Ueberreste, verwaiste Zeilen. */
function purgeJunkPipelineAndOrphans_(ss) {
  var removed = [];
  var validRefs = collectValidLeadRefs_(ss);
  var junkRefs = {};

  var pipe = ss.getSheetByName(TAB_PIPELINE);
  if (pipe && pipe.getLastRow() > 1) {
    var values = pipe.getDataRange().getValues();
    for (var r = values.length - 1; r >= 1; r--) {
      var ref = String(values[r][0] || '').trim();
      var name = String(values[r][2] || '').trim();
      var rolle = String(values[r][3] || '').trim();
      var serios = String(values[r][7] || '').trim();
      var reason = '';

      if (isExplicitJunkName_(name)) {
        reason = 'pipeline:test-name';
      } else if (!name && !rolle) {
        reason = 'pipeline:leer';
      } else if (ref && !validRefs[ref] && !name) {
        reason = 'pipeline:verwaist-ohne-name';
      } else if (ref && !validRefs[ref] && serios === '-') {
        reason = 'pipeline:verwaist-outreach';
      }

      if (reason) {
        pipe.deleteRow(r + 1);
        if (ref) junkRefs[ref] = reason;
        removed.push({ ref: ref || '(leer)', tab: TAB_PIPELINE, reasons: [reason] });
      }
    }
  }

  Object.keys(junkRefs).forEach(function (ref) {
    deleteLeadArtifacts_(ss, ref);
  });

  return removed;
}

function deleteLeadArtifacts_(ss, ref) {
  deleteRowsByRef_(ss.getSheetByName(TAB_PIPELINE), ref, 1);
  deleteRowsByRef_(ss.getSheetByName(TAB_SERIOSITY), ref, 1);
  purgeMatchesForRef_(ss, ref);
}

function deleteRowsByRef_(sheet, ref, refCol) {
  if (!sheet) return;
  var rowNum = findRowByRef_(sheet, ref, refCol);
  while (rowNum > 0) {
    sheet.deleteRow(rowNum);
    rowNum = findRowByRef_(sheet, ref, refCol);
  }
}

function purgeMatchesForRef_(ss, ref) {
  [TAB_MATCHES, TAB_TOP_MATCHES].forEach(function (tabName) {
    var sheet = ss.getSheetByName(tabName);
    if (!sheet || sheet.getLastRow() < 2) return;
    var values = sheet.getDataRange().getValues();
    var idCol = tabName === TAB_MATCHES ? 12 : 14;
    var anfragenCol = tabName === TAB_MATCHES ? 9 : -1;

    for (var r = values.length - 1; r >= 1; r--) {
      var matchId = String(values[r][idCol] || '');
      var anfragen = anfragenCol >= 0 ? String(values[r][anfragenCol] || '') : '';
      var agRef = tabName === TAB_TOP_MATCHES ? String(values[r][6] || '') : '';
      var anRef = tabName === TAB_TOP_MATCHES ? String(values[r][9] || '') : '';
      if (matchId.indexOf(ref) >= 0 || anfragen.indexOf(ref) >= 0 ||
          agRef === ref || anRef === ref) {
        sheet.deleteRow(r + 1);
      }
    }
  });
}

function handlePurgeJunk_(data) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var result = purgeJunkLeadsFromSheet_(ss);
  updateDashboard_(ss);
  return jsonResponse_({ ok: true, action: 'purge_junk', removed: result.removed, details: result.details });
}

/** EINMAL oder bei Bedarf: Test-/Unsinn-Leads aus allen Tabs entfernen. */
function junkLeadsEntfernen() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var result = purgeJunkLeadsFromSheet_(ss);
  updateDashboard_(ss);
  Logger.log('Junk-Leads entfernt: ' + result.removed);
  return result;
}

/**
 * EINMAL ausfuehren: alle Tab-Kopfzeilen schwarz auf hellgrau setzen.
 */
function headerSchwarzAktualisieren() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  restyleAllTabHeaders_(ss);
  updateDashboard_(ss);
  Logger.log('Header-Schrift auf schwarz aktualisiert.');
}

function restyleAllTabHeaders_(ss) {
  var specs = [
    [TAB_ALL, LEAD_HEADERS.length],
    [TAB_AUFTRAGGEBER, LEAD_HEADERS.length],
    [TAB_AUFTRAGNEHMER, LEAD_HEADERS.length],
    [TAB_PORTFOLIO, LEAD_HEADERS.length],
    [TAB_MATCHES, MATCH_HEADERS.length],
    [TAB_TOP_MATCHES, TOP_MATCH_HEADERS.length],
    [TAB_SERIOSITY, SERIOSITY_HEADERS.length],
    [TAB_PIPELINE, PIPELINE_HEADERS.length],
    [TAB_ACTIVITIES, ACTIVITY_HEADERS.length]
  ];
  specs.forEach(function (spec) {
    var sheet = ss.getSheetByName(spec[0]);
    if (sheet && sheet.getLastRow() > 0) {
      styleHeader_(sheet, spec[1]);
    }
  });
}

/**
 * EINMAL ausfuehren: Outreach-Eintraege aus Auftragnehmer/Alle Leads
 * nach Outreach-Portfolio verschieben (saubere Trennung).
 */
function outreachNachPortfolioVerschieben() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var result = migrateOutreachRows_(ss);
  updateDashboard_(ss);
  Logger.log('Verschoben: ' + result.moved + ' | Auftragnehmer verbleibend: ' + result.an_remaining);
  return result;
}

function handleMigrateOutreach_(data) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var result = migrateOutreachRows_(ss);
  updateDashboard_(ss);
  return jsonResponse_({ ok: true, moved: result.moved, an_remaining: result.an_remaining });
}

function isOutreachLeadRow_(row, idx) {
  var bearbeitung = String(row[idx.bearbeitung] || '').trim();
  var pipeline = String(row[idx.pipeline] || '').trim();
  var nachricht = String(row[idx.nachricht] || '').toLowerCase();
  if (bearbeitung === 'Outreach' || pipeline === 'Outreach') return true;
  if (nachricht.indexOf('outreach') >= 0 && nachricht.indexOf('importiert') >= 0) return true;
  if (nachricht.indexOf('google places') >= 0) return true;
  return false;
}

function migrateOutreachRows_(ss) {
  ensureStructure_(ss);
  var portfolio = ss.getSheetByName(TAB_PORTFOLIO);
  var moved = 0;
  var existingEmails = {};

  if (portfolio.getLastRow() > 1) {
    var pVals = portfolio.getDataRange().getValues();
    var pIdx = indexMapLead_(pVals[0]);
    for (var p = 1; p < pVals.length; p++) {
      existingEmails[String(pVals[p][pIdx.email] || '').trim().toLowerCase()] = true;
    }
  }

  [TAB_AUFTRAGNEHMER, TAB_ALL].forEach(function (tabName) {
    var sheet = ss.getSheetByName(tabName);
    if (!sheet || sheet.getLastRow() < 2) return;
    var values = sheet.getDataRange().getValues();
    var idx = indexMapLead_(values[0]);
    var cols = values[0].length;

    for (var r = values.length - 1; r >= 1; r--) {
      var row = values[r];
      if (!isOutreachLeadRow_(row, idx)) continue;

      var email = String(row[idx.email] || '').trim().toLowerCase();
      if (email && !existingEmails[email]) {
        portfolio.appendRow(row.slice(0, cols));
        existingEmails[email] = true;
        moved++;
      }
      sheet.deleteRow(r + 1);
    }
  });

  var an = ss.getSheetByName(TAB_AUFTRAGNEHMER);
  return {
    moved: moved,
    an_remaining: an ? Math.max(0, an.getLastRow() - 1) : 0
  };
}

/**
 * EINMAL ausfuehren fuer sauberen Neustart:
 * Loescht Dashboard/Matches/Seriositaet/Pipeline + leert die Lead-Tabs,
 * baut alles im neuen, uebersichtlichen Layout neu auf.
 * (Anfrage-Zaehler bleibt erhalten.)
 */
function neuAufsetzen() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  [TAB_DASHBOARD, TAB_MATCHES, TAB_TOP_MATCHES, TAB_SERIOSITY, TAB_PIPELINE,
   TAB_ALL, TAB_AUFTRAGGEBER, TAB_AUFTRAGNEHMER, TAB_PORTFOLIO].forEach(function (n) {
    var sh = ss.getSheetByName(n);
    if (sh) ss.deleteSheet(sh);
  });
  ensureStructure_(ss);
  rescanAllMatchesFull_();
  updateDashboard_(ss);
  Logger.log('Fertig - alle Tabs sauber & farbig neu aufgebaut. Bitte installTriggers() ausfuehren.');
}
