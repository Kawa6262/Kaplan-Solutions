/**
 * Kaplan Solutions - Lead Intelligence (Sheet + Drive)
 *
 * Tabs: Dashboard, Alle Leads, Auftraggeber, Auftragnehmer, Matches, Top Matches,
 *       Seriositaet, Pipeline
 *
 * Erstes Mal / nach Layout-Update:  Funktion "neuAufsetzen" einmal ausfuehren
 * 24/7 Matching:  Funktion "installTriggers" einmal ausfuehren (stuendlich + Briefing 10:00)
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
var TAB_MATCHES = 'Matches';
var TAB_TOP_MATCHES = 'Top Matches';
var TAB_SERIOSITY = 'Seriosit\u00e4t';
var TAB_PIPELINE = 'Pipeline';
var META_SHEET = '_Meta';

var MIN_MATCH_SCORE_TAB = 50;
var MIN_MATCH_SCORE_EMAIL = 35;
var MATCH_FOLDER_MIN = 75;
var MATCH_ALERT_MIN = 75;

var TZ = 'Europe/Berlin';

// Farben
var C_HEAD_BG = '#0b3d2e';
var C_HEAD_FG = '#d9b75a';
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
  'Pipeline-Status', 'Seriosit\u00e4t %', 'Matches', 'N\u00e4chster Schritt', 'Ordner-Link'
];

var MATCH_STATUS_OPTIONS = ['Neu', 'In Kontakt', 'Vermittelt', 'Abgelehnt'];
var PIPELINE_STATUS_OPTIONS = ['Neu', 'In Bearbeitung', 'Vermittelt', 'Abgeschlossen', 'Abgelehnt'];

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

  appendToTab_(ss, TAB_ALL, row);
  appendToTab_(ss, TAB_AUFTRAGNEHMER, row);
  writeMatches_(ss, ref, leadData, allMatches);
  writeSeriosityPending_(ss, ref, leadData, folderUrl);
  writePipeline_(ss, ref, leadData, folderUrl, allMatches.length);
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
  var tabs = [TAB_ALL, TAB_AUFTRAGGEBER, TAB_AUFTRAGNEHMER];
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
  ensureTab_(ss, TAB_MATCHES, MATCH_HEADERS);
  ensureTab_(ss, TAB_TOP_MATCHES, TOP_MATCH_HEADERS);
  ensureTab_(ss, TAB_SERIOSITY, SERIOSITY_HEADERS);
  ensureTab_(ss, TAB_PIPELINE, PIPELINE_HEADERS);
  ensureMeta_(ss);
  ensureRootFolders_();
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
  // Zebra-Streifen fuer bessere Lesbarkeit
  try {
    var range = sheet.getRange(1, 1, Math.max(sheet.getMaxRows(), 2), cols);
    var bandings = sheet.getBandings();
    if (!bandings.length) {
      range.applyRowBanding(SpreadsheetApp.BandingTheme.LIGHT_GREY, true, false);
    }
  } catch (e) {}

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
    var wP = [110, 130, 170, 130, 130, 110, 140, 100, 80, 220, 90];
    applyWidths_(sheet, wP);
    setDropdown_(sheet, 7, PIPELINE_STATUS_OPTIONS);
  } else if (name === TAB_ALL || name === TAB_AUFTRAGGEBER || name === TAB_AUFTRAGNEHMER) {
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
  } else {
    if (!meta.getRange('A5').getValue()) {
      meta.getRange('A5:B5').setValues([['match_alert_url', 'https://kaplan-solutions.de/api/match-alert']]);
    }
    if (!meta.getRange('A6').getValue()) {
      meta.getRange('A6:B6').setValues([['match_alert_secret', '']]);
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
  var oppositeTab = incoming.role_code === 'bauherr' ? TAB_AUFTRAGNEHMER : TAB_AUFTRAGGEBER;
  var sheet = ss.getSheetByName(oppositeTab);
  if (!sheet || sheet.getLastRow() < 2) return [];

  var values = sheet.getDataRange().getValues();
  var idx = indexMapLead_(values[0]);
  var candidates = [];

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
  sheet.appendRow([
    ref, data.eingegangen || '', data.name || '', data.rolle || '',
    data.branche || '', data.stadt || '', 'Neu', '-', matchCount,
    'Seriositaet + Matches pruefen', folderUrl || ''
  ]);
}

function updateLeadSeriosity_(ss, ref, score, flags, status) {
  [TAB_ALL, TAB_AUFTRAGGEBER, TAB_AUFTRAGNEHMER].forEach(function (tabName) {
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
    if (score < 40) sheet.getRange(rowNum, 10).setValue('WARN: Manuell pruefen');
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
  var matches = ss.getSheetByName(TAB_MATCHES);
  var ser = ss.getSheetByName(TAB_SERIOSITY);
  var pipe = ss.getSheetByName(TAB_PIPELINE);

  var agCount = ag ? Math.max(0, ag.getLastRow() - 1) : 0;
  var anCount = an ? Math.max(0, an.getLastRow() - 1) : 0;
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
    ['Auftraggeber (Bauherren)', agCount, 'Auftragnehmer (Firmen)', anCount],
    ['Gefundene Matches', matchCount, 'Pipeline offen', openPipe],
    ['? Seriositaet', serStats.avg > 0 ? serStats.avg + '%' : '-', 'WARN: Prueffaelle (<40%)', serStats.red],
    ['Seriositaet geprueft', serStats.done, 'Pruefung laeuft', serStats.pending]
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
    .setValue('Tabs: Top Matches = Ranking (beste zuerst) - Matches = alle Paare - Pipeline = Status je Lead')
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
  var statuses = sheet.getRange(2, 7, sheet.getLastRow() - 1, 1).getValues();
  var n = 0;
  statuses.forEach(function (r) {
    var s = String(r[0]);
    if (s && s !== 'Abgeschlossen' && s !== 'Abgelehnt' && s !== 'Vermittelt') n++;
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
  var anSheet = ss.getSheetByName(TAB_AUFTRAGNEHMER);
  if (!agSheet || !anSheet || agSheet.getLastRow() < 2 || anSheet.getLastRow() < 2) {
    return [];
  }

  var agValues = agSheet.getDataRange().getValues();
  var anValues = anSheet.getDataRange().getValues();
  var agIdx = indexMapLead_(agValues[0]);
  var anIdx = indexMapLead_(anValues[0]);
  var pairs = [];
  var seen = {};

  for (var a = 1; a < agValues.length; a++) {
    var agRow = agValues[a];
    var agRef = String(agRow[agIdx.ref] || '');
    if (!agRef) continue;
    var agIncoming = rowToIncoming_(agRow, agIdx, 'bauherr');

    for (var n = 1; n < anValues.length; n++) {
      var anRow = anValues[n];
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
}

function updateMatchCountsOnLeads_(ss, pairs) {
  var counts = {};
  pairs.forEach(function (p) {
    counts[p.agRef] = (counts[p.agRef] || 0) + 1;
    counts[p.anRef] = (counts[p.anRef] || 0) + 1;
  });

  [TAB_ALL, TAB_AUFTRAGGEBER, TAB_AUFTRAGNEHMER].forEach(function (tabName) {
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
  var anSheet = ss.getSheetByName(TAB_AUFTRAGNEHMER);
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
  if (anSheet && anSheet.getLastRow() > 1) {
    var anValues = anSheet.getDataRange().getValues();
    var anIdx = indexMapLead_(anValues[0]);
    for (var j = 1; j < anValues.length; j++) {
      if (String(anValues[j][anIdx.ref]) === p.anRef) {
        p.anPhone = String(anValues[j][anIdx.telefon] || p.anPhone || '');
        p.anFirma = String(anValues[j][anIdx.firma] || p.anFirma || p.anName || '');
        break;
      }
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

/**
 * EINMAL ausfuehren fuer sauberen Neustart:
 * Loescht Dashboard/Matches/Seriositaet/Pipeline + leert die Lead-Tabs,
 * baut alles im neuen, uebersichtlichen Layout neu auf.
 * (Anfrage-Zaehler bleibt erhalten.)
 */
function neuAufsetzen() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  [TAB_DASHBOARD, TAB_MATCHES, TAB_TOP_MATCHES, TAB_SERIOSITY, TAB_PIPELINE,
   TAB_ALL, TAB_AUFTRAGGEBER, TAB_AUFTRAGNEHMER].forEach(function (n) {
    var sh = ss.getSheetByName(n);
    if (sh) ss.deleteSheet(sh);
  });
  ensureStructure_(ss);
  rescanAllMatchesFull_();
  updateDashboard_(ss);
  Logger.log('Fertig - alle Tabs sauber & farbig neu aufgebaut. Bitte installTriggers() ausfuehren.');
}
