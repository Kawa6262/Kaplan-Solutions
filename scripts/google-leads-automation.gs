/**
 * Kaplan Solutions — Lead Intelligence (Sheet + Drive)
 *
 * Tabs: Dashboard, Alle Leads, Auftraggeber, Auftragnehmer, Matches,
 *       Seriosität, Pipeline
 *
 * Erstes Mal / nach Layout-Update:  Funktion "neuAufsetzen" einmal ausführen
 *   (löscht Testdaten + baut alle Tabs sauber & farbig neu auf).
 * Nach jedem Code-Update:  Bereitstellen → Bereitstellungen verwalten → Neue Version
 */

var ROOT_FOLDER_NAME = 'Kaplan Leads';
var FOLDER_DASHBOARD = '00_Dashboard';
var FOLDER_AUFTRAGGEBER = '01_Auftraggeber';
var FOLDER_AUFTRAGNEHMER = '02_Auftragnehmer';
var FOLDER_MATCHES = '03_Matches';
var FOLDER_SERIOSITY = '04_Seriositäts-Reports';
var FOLDER_PRUEFEN = '05_Prüfen';

var TAB_DASHBOARD = 'Dashboard';
var TAB_ALL = 'Alle Leads';
var TAB_AUFTRAGGEBER = 'Auftraggeber';
var TAB_AUFTRAGNEHMER = 'Auftragnehmer';
var TAB_MATCHES = 'Matches';
var TAB_SERIOSITY = 'Seriosität';
var TAB_PIPELINE = 'Pipeline';
var META_SHEET = '_Meta';

var MIN_MATCH_SCORE_TAB = 50;
var MIN_MATCH_SCORE_EMAIL = 35;
var MATCH_FOLDER_MIN = 75;

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
  'Budget/Auftragsvolumen', 'Größe/Kapazität', 'Status/Mitarbeiter',
  'Referenzen', 'Nachricht', 'Dateien',
  'Seriosität %', 'Match-Anzahl', 'Pipeline-Status', 'Flags',
  'Bearbeitung', 'Ordner-Link'
];

var MATCH_HEADERS = [
  'Passung', 'Status', 'Auftraggeber', 'Kontakt Auftraggeber',
  'Auftragnehmer', 'Kontakt Auftragnehmer', 'Branche', 'Region',
  'Warum es passt', 'Anfragen', 'Ordner', 'Erstellt', 'Match-ID'
];

var SERIOSITY_HEADERS = [
  'Anfrage-Nr.', 'Firma / Name', 'Score', 'Bewertung', 'Rechtsform',
  'Handelsregister', 'Firmenalter', 'Google-Bewertung', 'Konfidenz',
  '⚠️ Warnungen', 'Quellen', 'Report', 'Geprüft am'
];

var PIPELINE_HEADERS = [
  'Anfrage-Nr.', 'Eingegangen', 'Name', 'Rolle', 'Branche', 'Stadt',
  'Pipeline-Status', 'Seriosität %', 'Matches', 'Nächster Schritt', 'Ordner-Link'
];

var MATCH_STATUS_OPTIONS = ['Neu', 'In Kontakt', 'Vermittelt', 'Abgelehnt'];
var PIPELINE_STATUS_OPTIONS = ['Neu', 'In Bearbeitung', 'Vermittelt', 'Abgeschlossen', 'Abgelehnt'];

// ── Webhook ─────────────────────────────────────────────────────────────────

function doPost(e) {
  try {
    var data = parsePayload_(e);
    if (data.action === 'seriosity_update') {
      return handleSeriosityUpdate_(data);
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

  var row = buildLeadRow_(data, ref, folderUrl, allMatches.length, '—', '🟡 Prüfung läuft');

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

  return jsonResponse_({
    ok: true,
    ref: ref,
    folder_url: folderUrl,
    matches: emailMatches
  });
}

function handleSeriosityUpdate_(data) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ensureStructure_(ss);
  var ref = data.ref || '';
  if (!ref) throw new Error('ref fehlt');

  var score = Number(data.score) || 0;
  var status = data.status || 'Geprüft';
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

// ── Struktur ────────────────────────────────────────────────────────────────

function ensureStructure_(ss) {
  ensureTab_(ss, TAB_DASHBOARD, null);
  ensureTab_(ss, TAB_ALL, LEAD_HEADERS);
  ensureTab_(ss, TAB_AUFTRAGGEBER, LEAD_HEADERS);
  ensureTab_(ss, TAB_AUFTRAGNEHMER, LEAD_HEADERS);
  ensureTab_(ss, TAB_MATCHES, MATCH_HEADERS);
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
  // Zebra-Streifen für bessere Lesbarkeit
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
  }
}

function ensureRootFolders_() {
  var root = getOrCreateFolder_(DriveApp.getRootFolder(), ROOT_FOLDER_NAME);
  [FOLDER_DASHBOARD, FOLDER_AUFTRAGGEBER, FOLDER_AUFTRAGNEHMER,
   FOLDER_MATCHES, FOLDER_SERIOSITY, FOLDER_PRUEFEN].forEach(function (n) {
    getOrCreateFolder_(root, n);
  });
}

// ── Anfrage-Nr. ─────────────────────────────────────────────────────────────

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

// ── Lead-Zeile & Ordner ─────────────────────────────────────────────────────

function buildLeadRow_(data, ref, folderUrl, matchCount, seriosStatus, flags) {
  return [
    ref, data.eingegangen || '', data.rolle || '', data.name || '', data.email || '',
    data.telefon || '', data.firma || '', data.branche || 'Sonstiges', data.stadt || '—',
    data.plz || '', data.projekt || '', data.standort || '', data.zeitrahmen || '',
    data.budget || '', data.groesse || '', data.status_feld || '', data.referenzen || '',
    data.nachricht || '', data.dateien || '—',
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
  var leadName = ref + ' — ' + safeName_(data.name || 'Lead');
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
    'Firma: ' + (data.firma || ''),
    'Branche: ' + (data.branche || ''),
    'Stadt: ' + (data.stadt || ''),
    'PLZ: ' + (data.plz || ''),
    'Projekt/Gewerke: ' + (data.projekt || ''),
    'Standort: ' + (data.standort || ''),
    'Zeitrahmen: ' + (data.zeitrahmen || ''),
    'Budget/Umfang: ' + (data.budget || ''),
    'Nachricht:', data.nachricht || '—'
  ].join('\n');
}

function createSeriosityReport_(ref, data, score, status, flags, details) {
  try {
    var root = getOrCreateFolder_(DriveApp.getRootFolder(), ROOT_FOLDER_NAME);
    var serRoot = getOrCreateFolder_(root, FOLDER_SERIOSITY);
    var fName = ref + ' — ' + safeName_(data.firma || data.name || 'Lead');
    var folder = serRoot.getFoldersByName(fName).hasNext()
      ? serRoot.getFoldersByName(fName).next()
      : serRoot.createFolder(fName);

    var quellen = data.quellen || [];
    var qLines = quellen.length
      ? quellen.map(function (q) { return '  • ' + (q.label || 'Quelle') + ': ' + (q.url || ''); })
      : ['  — keine externen Quellen gefunden'];

    var header = [
      '╔══════════════════════════════════════════════════╗',
      '   KAPLAN SOLUTIONS — SERIOSITÄTS-REPORT',
      '╚══════════════════════════════════════════════════╝',
      '',
      'Anfrage-Nr.: ' + ref,
      'Firma/Name:  ' + (data.firma || data.name || ''),
      'Geprüft am:  ' + Utilities.formatDate(new Date(), TZ, 'dd.MM.yyyy HH:mm'),
      '',
      '──────────────────────────────────────────────────',
      ''
    ].join('\n');

    var content = header + (details || '') + '\n\n' +
      '──────────────────────────────────────────────────\n' +
      'QUELLENVERZEICHNIS (zum Selbst-Nachprüfen):\n' +
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
  var fName = ref + ' — ' + safeName_(name) + ' (' + score + '%)';
  if (pruefen.getFoldersByName(fName).hasNext()) return;
  var folder = pruefen.createFolder(fName);
  folder.createFile('Hinweis.txt',
    'Niedrige Seriosität: ' + score + '%\nFlags: ' + (flags || '—') +
    '\nLead wurde NICHT blockiert — bitte manuell prüfen.', MimeType.PLAIN_TEXT);
}

// ── Matching ─────────────────────────────────────────────────────────────────

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
  if (timeScore > 0) { score += timeScore; reasons.push('Zeit/Kapazität'); }

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
      m.reason, ref + ' ↔ ' + m.ref, '', now, matchId
    ];
    sheet.appendRow(row);
    var rowNum = sheet.getLastRow();
    sheet.getRange(rowNum, 1).setBackground(matchColor_(m.score)).setFontWeight('bold');
    if (ordnerUrl) {
      sheet.getRange(rowNum, 11).setFormula('=HYPERLINK("' + ordnerUrl + '";"Öffnen")');
    }
    existing[matchId] = true;
  });
}

function createMatchFolder_(ref, data, m) {
  try {
    var root = getOrCreateFolder_(DriveApp.getRootFolder(), ROOT_FOLDER_NAME);
    var matchRoot = getOrCreateFolder_(root, FOLDER_MATCHES);
    var fname = ref + ' ↔ ' + m.ref + ' (' + m.score + '%)';
    if (matchRoot.getFoldersByName(fname).hasNext()) {
      return matchRoot.getFoldersByName(fname).next().getUrl();
    }
    var folder = matchRoot.createFolder(fname);
    folder.createFile('Match-Info.txt',
      'Match: ' + (data.name || '') + ' ↔ ' + m.name + '\nPassung: ' + m.score + '%\n' +
      'Gründe: ' + m.reason + '\nAnfrage A: ' + ref + '\nAnfrage B: ' + m.ref,
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

// ── Seriosität & Pipeline ─────────────────────────────────────────────────────

function writeSeriosityPending_(ss, ref, data, folderUrl) {
  var sheet = ss.getSheetByName(TAB_SERIOSITY);
  sheet.appendRow([
    ref, (data.firma && data.firma !== '—' ? data.firma : data.name) || '',
    '', '⏳ Prüfung läuft …', '', '', '', '', '', '', '', '', ''
  ]);
}

function writePipeline_(ss, ref, data, folderUrl, matchCount) {
  var sheet = ss.getSheetByName(TAB_PIPELINE);
  sheet.appendRow([
    ref, data.eingegangen || '', data.name || '', data.rolle || '',
    data.branche || '', data.stadt || '', 'Neu', '—', matchCount,
    'Seriosität + Matches prüfen', folderUrl || ''
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
  var firmaName = (data.firma && data.firma !== '—' ? data.firma : data.name) || '';

  var warn = '';
  if (data.negative && data.negative.length) {
    warn = '⚠️ ' + data.negative.join(' | ');
  } else if (score < 40) {
    warn = '⚠️ Wenig verlässliche Daten';
  } else {
    warn = '—';
  }

  var row = [
    ref, firmaName, score, (flags || '') + ' ' + (status || ''),
    data.rechtsform || '—', data.handelsregister || '—',
    data.domain_alter || '—', data.google_rating || '—',
    data.confidence || '—', warn, '', '', now
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
    sheet.getRange(rowNum, 11).setValue('—');
  }
  if (reportUrl) {
    sheet.getRange(rowNum, 12).setFormula('=HYPERLINK("' + reportUrl + '";"📄 Report")');
  } else {
    sheet.getRange(rowNum, 12).setValue('—');
  }
}

function updatePipelineSeriosity_(ss, ref, score, flags) {
  var sheet = ss.getSheetByName(TAB_PIPELINE);
  var rowNum = findRowByRef_(sheet, ref, 1);
  if (rowNum > 0) {
    sheet.getRange(rowNum, 8).setValue(score + '%').setBackground(scoreColor_(score));
    if (score < 40) sheet.getRange(rowNum, 10).setValue('⚠️ Manuell prüfen');
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

// ── Dashboard ─────────────────────────────────────────────────────────────────

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
  sheet.getRange('B2:E2').merge().setValue('KAPLAN SOLUTIONS — LEAD-ÜBERSICHT')
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
    ['Ø Seriosität', serStats.avg > 0 ? serStats.avg + '%' : '—', '⚠️ Prüffälle (<40%)', serStats.red],
    ['Seriosität geprüft', serStats.done, 'Prüfung läuft', serStats.pending]
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

  // Prüffälle hervorheben
  if (serStats.red > 0) {
    sheet.getRange(startRow + 2, 5).setBackground(C_RED);
  }

  // Hinweis-Zeile
  var noteRow = startRow + kpis.length + 1;
  sheet.getRange(noteRow, 2, 1, 4).merge()
    .setValue('Tabs unten: Matches = Vermittlungs-Vorschläge · Seriosität = Background-Checks mit Quellen · Pipeline = Status je Lead')
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
    if (bew.indexOf('läuft') >= 0 || r[0] === '' || r[0] === null) {
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

// ── Farben ────────────────────────────────────────────────────────────────────

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

// ── Scoring-Hilfen ──────────────────────────────────────────────────────────

function indexMapLead_(headers) {
  var map = {};
  for (var i = 0; i < headers.length; i++) {
    var h = String(headers[i]).toLowerCase();
    if (h.indexOf('anfrage') === 0) map.ref = i;
    else if (h === 'name') map.name = i;
    else if (h.indexOf('e-mail') === 0) map.email = i;
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
    .replace(/ä/g, 'ae').replace(/ö/g, 'oe').replace(/ü/g, 'ue').replace(/ß/g, 'ss')
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function scoreCity_(aStadt, aPlz, bStadt, bPlz) {
  if (aPlz && bPlz && String(aPlz) === String(bPlz)) return 35;
  var a = norm_(aStadt), b = norm_(bStadt);
  if (!a || !b || a === '—' || b === '—') return 0;
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
  if (!x || !y || x === '—' || y === '—') return 0;
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
  var urgent = ['sofort', 'kurzfristig', 'asap', 'nächster', 'naechster'];
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

// ── Hilfsfunktionen ───────────────────────────────────────────────────────────

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

// ── Einmalige Wartungs-Funktionen ─────────────────────────────────────────────

/** Einmal ausführen → Berechtigungen erteilen */
function testBerechtigung() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var root = DriveApp.getRootFolder();
  var test = root.createFolder('_kaplan_test');
  test.setTrashed(true);
  Logger.log('Alles OK — Sheet: ' + ss.getName() + ' / Drive Schreiben funktioniert');
}

/**
 * EINMAL ausführen für sauberen Neustart:
 * Löscht Dashboard/Matches/Seriosität/Pipeline + leert die Lead-Tabs,
 * baut alles im neuen, übersichtlichen Layout neu auf.
 * (Anfrage-Zähler bleibt erhalten.)
 */
function neuAufsetzen() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  [TAB_DASHBOARD, TAB_MATCHES, TAB_SERIOSITY, TAB_PIPELINE,
   TAB_ALL, TAB_AUFTRAGGEBER, TAB_AUFTRAGNEHMER].forEach(function (n) {
    var sh = ss.getSheetByName(n);
    if (sh) ss.deleteSheet(sh);
  });
  ensureStructure_(ss);
  updateDashboard_(ss);
  Logger.log('Fertig — alle Tabs sauber & farbig neu aufgebaut.');
}
