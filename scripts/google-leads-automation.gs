/**
 * Kaplan Solutions — Lead Intelligence (Sheet + Drive)
 *
 * Tabs: Dashboard, Alle Leads, Auftraggeber, Auftragnehmer, Matches,
 *       Seriosität, Pipeline
 *
 * Nach Code-Update: Bereitstellen → Bereitstellungen verwalten → Neue Version
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

var LEAD_HEADERS = [
  'Anfrage-Nr.', 'Eingegangen', 'Rolle', 'Name', 'E-Mail', 'Telefon', 'Firma',
  'Branche', 'Stadt', 'PLZ', 'Projekt/Gewerke', 'Standort', 'Zeitrahmen',
  'Budget/Auftragsvolumen', 'Größe/Kapazität', 'Status/Mitarbeiter',
  'Referenzen', 'Nachricht', 'Dateien',
  'Seriosität %', 'Match-Anzahl', 'Pipeline-Status', 'Flags',
  'Bearbeitung', 'Ordner-Link'
];

var MATCH_HEADERS = [
  'Match-ID', 'Erstellt', 'Ref A', 'Name A', 'Rolle A', 'Ref B', 'Name B', 'Rolle B',
  'Score %', 'Gründe', 'Status', 'Ordner-Link'
];

var SERIOSITY_HEADERS = [
  'Anfrage-Nr.', 'Name', 'Firma', 'Rolle', 'Score %', 'Status', 'Flags',
  'Report-Link', 'Zuletzt geprüft', 'Details'
];

var PIPELINE_HEADERS = [
  'Anfrage-Nr.', 'Eingegangen', 'Name', 'Rolle', 'Branche', 'Stadt',
  'Pipeline-Status', 'Seriosität %', 'Matches', 'Nächster Schritt', 'Ordner-Link'
];

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
  return jsonResponse_({ ok: true, service: 'Kaplan Solutions Lead Intelligence' });
}

function handleNewLead_(data) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ensureStructure_(ss);

  var ref = nextRef_(ss);
  var folderUrl = createLeadFolder_(data, ref);
  var allMatches = findAllMatches_(ss, data, ref);
  var emailMatches = allMatches.filter(function (m) { return m.score >= MIN_MATCH_SCORE_EMAIL; }).slice(0, 3);

  var row = buildLeadRow_(data, ref, folderUrl, allMatches.length, 'Ausstehend', seriosityFlag_(null));

  appendToTab_(ss, TAB_ALL, row);
  if (data.role_code === 'bauherr') {
    appendToTab_(ss, TAB_AUFTRAGGEBER, row);
  } else {
    appendToTab_(ss, TAB_AUFTRAGNEHMER, row);
  }

  writeMatches_(ss, ref, data, allMatches);
  writeSeriosityPending_(ss, ref, data, folderUrl);
  writePipeline_(ss, ref, data, folderUrl, allMatches.length);
  createMatchFolders_(ref, data, allMatches);
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

  updateLeadSeriosity_(ss, ref, score, flags);
  upsertSeriosityRow_(ss, ref, data, score, status, flags, details, reportUrl);
  updatePipelineSeriosity_(ss, ref, score, flags);
  if (score > 0 && score < 40) {
    moveToPruefenFolder_(ref, data.name || '', score, flags);
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
  if (!sheet) sheet = ss.insertSheet(name);
  if (headers && sheet.getLastRow() === 0) {
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    styleHeader_(sheet, headers.length);
    sheet.setFrozenRows(1);
  }
}

function styleHeader_(sheet, cols) {
  sheet.getRange(1, 1, 1, cols)
    .setFontWeight('bold')
    .setBackground('#1a1a1a')
    .setFontColor('#c9a227');
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
    var content = [
      'SERIOSITÄTS-REPORT',
      '==================',
      'Anfrage-Nr.: ' + ref,
      'Firma/Name: ' + (data.firma || data.name || ''),
      'Score: ' + score + '% (' + status + ') ' + (flags || ''),
      '',
      details || ''
    ].join('\n');
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
  var now = Utilities.formatDate(new Date(), 'Europe/Berlin', 'dd.MM.yyyy HH:mm');

  matches.forEach(function (m) {
    var matchId = makeMatchId_(ref, m.ref);
    if (existing[matchId]) return;
    var row = [
      matchId, now, ref, data.name || '', data.rolle || '',
      m.ref, m.name, m.role || '', m.score, m.reason, 'Neu', ''
    ];
    sheet.appendRow(row);
    existing[matchId] = true;
  });
}

function createMatchFolders_(ref, data, matches) {
  var root = getOrCreateFolder_(DriveApp.getRootFolder(), ROOT_FOLDER_NAME);
  var matchRoot = getOrCreateFolder_(root, FOLDER_MATCHES);
  matches.filter(function (m) { return m.score >= MATCH_FOLDER_MIN; }).forEach(function (m) {
    var fname = ref + ' ↔ ' + m.ref + ' (' + m.score + '%)';
    if (matchRoot.getFoldersByName(fname).hasNext()) return;
    var folder = matchRoot.createFolder(fname);
    folder.createFile('Match-Info.txt',
      'Match: ' + (data.name || '') + ' ↔ ' + m.name + '\nScore: ' + m.score + '%\n' +
      'Gründe: ' + m.reason + '\nRef A: ' + ref + '\nRef B: ' + m.ref,
      MimeType.PLAIN_TEXT);
  });
}

function getExistingMatchIds_(sheet) {
  var map = {};
  if (!sheet || sheet.getLastRow() < 2) return map;
  var col = sheet.getRange(2, 1, sheet.getLastRow() - 1, 1).getValues();
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
    ref, data.name || '', data.firma || '', data.rolle || '',
    '—', 'Ausstehend', '', folderUrl || '', '', 'Hintergrund-Prüfung läuft…'
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

function seriosityFlag_(score) {
  if (score === null || score === undefined || score === '—') return '🟡 Prüfung ausstehend';
  if (score >= 70) return '🟢';
  if (score >= 40) return '🟡';
  return '🔴 Vorsicht';
}

function updateLeadSeriosity_(ss, ref, score, flags) {
  [TAB_ALL, TAB_AUFTRAGGEBER, TAB_AUFTRAGNEHMER].forEach(function (tabName) {
    updateColumnByRef_(ss.getSheetByName(tabName), ref, {
      20: score + '%',
      23: flags || seriosityFlag_(score)
    });
  });
}

function upsertSeriosityRow_(ss, ref, data, score, status, flags, details, reportUrl) {
  var sheet = ss.getSheetByName(TAB_SERIOSITY);
  var rowNum = findRowByRef_(sheet, ref, 1);
  var now = Utilities.formatDate(new Date(), 'Europe/Berlin', 'dd.MM.yyyy HH:mm');
  var row = [
    ref, data.name || '', data.firma || '', data.rolle || '',
    score + '%', status, flags || seriosityFlag_(score), reportUrl || '',
    now, details || ''
  ];
  if (rowNum > 0) {
    sheet.getRange(rowNum, 1, 1, row.length).setValues([row]);
  } else {
    sheet.appendRow(row);
  }
}

function updatePipelineSeriosity_(ss, ref, score, flags) {
  var sheet = ss.getSheetByName(TAB_PIPELINE);
  var rowNum = findRowByRef_(sheet, ref, 1);
  if (rowNum > 0) {
    sheet.getRange(rowNum, 8).setValue(score + '%');
    if (flags) sheet.getRange(rowNum, 10).setValue('Manuell prüfen: ' + flags);
  }
}

function updateColumnByRef_(sheet, ref, colValueMap) {
  if (!sheet) return;
  var rowNum = findRowByRef_(sheet, ref, 1);
  if (rowNum < 1) return;
  Object.keys(colValueMap).forEach(function (col) {
    sheet.getRange(rowNum, Number(col)).setValue(colValueMap[col]);
  });
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

  var all = ss.getSheetByName(TAB_ALL);
  var matches = ss.getSheetByName(TAB_MATCHES);
  var ser = ss.getSheetByName(TAB_SERIOSITY);
  var pipe = ss.getSheetByName(TAB_PIPELINE);

  var leadCount = all ? Math.max(0, all.getLastRow() - 1) : 0;
  var matchCount = matches ? Math.max(0, matches.getLastRow() - 1) : 0;
  var pendingSer = countPendingSeriosity_(ser);
  var openPipe = countOpenPipeline_(pipe);

  var rows = [
    ['Kaplan Solutions — Lead Dashboard', ''],
    ['Stand', Utilities.formatDate(new Date(), 'Europe/Berlin', 'dd.MM.yyyy HH:mm')],
    ['', ''],
    ['Leads gesamt', leadCount],
    ['Matches gesamt', matchCount],
    ['Seriosität ausstehend', pendingSer],
    ['Pipeline offen', openPipe],
    ['', ''],
    ['Tabs', 'Alle Leads · Auftraggeber · Auftragnehmer · Matches · Seriosität · Pipeline'],
    ['Drive', ROOT_FOLDER_NAME + ' / 01_Auftraggeber · 02_Auftragnehmer · 03_Matches']
  ];

  sheet.clear();
  sheet.getRange(1, 1, rows.length, 2).setValues(rows);
  sheet.getRange(1, 1).setFontWeight('bold').setFontSize(14);
  sheet.setColumnWidth(1, 220);
  sheet.setColumnWidth(2, 320);
}

function countPendingSeriosity_(sheet) {
  if (!sheet || sheet.getLastRow() < 2) return 0;
  var statuses = sheet.getRange(2, 6, sheet.getLastRow() - 1, 1).getValues();
  var n = 0;
  statuses.forEach(function (r) {
    if (String(r[0]).indexOf('Ausstehend') >= 0) n++;
  });
  return n;
}

function countOpenPipeline_(sheet) {
  if (!sheet || sheet.getLastRow() < 2) return 0;
  var statuses = sheet.getRange(2, 7, sheet.getLastRow() - 1, 1).getValues();
  var n = 0;
  statuses.forEach(function (r) {
    var s = String(r[0]);
    if (s && s !== 'Abgeschlossen' && s !== 'Abgelehnt') n++;
  });
  return n;
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

/** Einmal ausführen → Berechtigungen erteilen */
function testBerechtigung() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var root = DriveApp.getRootFolder();
  var test = root.createFolder('_kaplan_test');
  test.setTrashed(true);
  Logger.log('Alles OK — Sheet: ' + ss.getName() + ' / Drive Schreiben funktioniert');
}
