/**
 * Kaplan Solutions — Lead-Automatisierung
 *
 * EINRICHTUNG (einmalig):
 * 1. Google Sheet "Kaplan Solutions Leads" öffnen
 * 2. Erweiterungen → Apps Script
 * 3. Gesamten Code durch diese Datei ersetzen
 * 4. Bereitstellen → Neue Bereitstellung → Web-App
 *    - Ausführen als: Ich
 *    - Zugriff: Jeder (auch anonym)
 * 5. Webhook-URL in Render als SHEETS_WEBHOOK_URL eintragen (muss mit /exec enden)
 *
 * FUNKTIONEN:
 * - Anfrage-Nr. KS-2026-0042 (fortlaufend)
 * - Tabs: Alle Leads, Auftraggeber, Auftragnehmer
 * - Google-Drive-Ordner: Kaplan Leads / Rolle / Stadt / Branche / Ref-Name
 * - Partner-Matching: Top 3 passende Gegenparteien
 */

var ROOT_FOLDER_NAME = 'Kaplan Leads';
var TAB_ALL = 'Alle Leads';
var TAB_AUFTRAGGEBER = 'Auftraggeber';
var TAB_AUFTRAGNEHMER = 'Auftragnehmer';
var META_SHEET = '_Meta';

var HEADERS = [
  'Anfrage-Nr.', 'Eingegangen', 'Rolle', 'Name', 'E-Mail', 'Telefon', 'Firma',
  'Branche', 'Stadt', 'PLZ', 'Projekt/Gewerke', 'Standort', 'Zeitrahmen',
  'Budget/Auftragsvolumen', 'Größe/Kapazität', 'Status/Mitarbeiter',
  'Referenzen', 'Nachricht', 'Dateien', 'Bearbeitung', 'Ordner-Link'
];

function doPost(e) {
  try {
    var data = parsePayload_(e);
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    ensureStructure_(ss);

    var ref = nextRef_(ss);
    var folderUrl = createLeadFolder_(data, ref);
    var row = buildRow_(data, ref, folderUrl);

    appendToTab_(ss, TAB_ALL, row);
    if (data.role_code === 'bauherr') {
      appendToTab_(ss, TAB_AUFTRAGGEBER, row);
    } else {
      appendToTab_(ss, TAB_AUFTRAGNEHMER, row);
    }

    var matches = findMatches_(ss, data, ref);

    return jsonResponse_({
      ok: true,
      ref: ref,
      folder_url: folderUrl,
      matches: matches
    });
  } catch (err) {
    return jsonResponse_({ ok: false, error: String(err) });
  }
}

function doGet() {
  return jsonResponse_({ ok: true, service: 'Kaplan Solutions Leads' });
}

// ── Struktur ────────────────────────────────────────────────────────────────

function ensureStructure_(ss) {
  ensureTab_(ss, TAB_ALL);
  ensureTab_(ss, TAB_AUFTRAGGEBER);
  ensureTab_(ss, TAB_AUFTRAGNEHMER);
  ensureMeta_(ss);
}

function ensureTab_(ss, name) {
  var sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
  }
  if (sheet.getLastRow() === 0) {
    sheet.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]);
    sheet.getRange(1, 1, 1, HEADERS.length)
      .setFontWeight('bold')
      .setBackground('#1a1a1a')
      .setFontColor('#c9a227');
    sheet.setFrozenRows(1);
  }
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

  var padded = ('0000' + counter).slice(-4);
  return 'KS-' + year + '-' + padded;
}

// ── Zeile & Ordner ──────────────────────────────────────────────────────────

function buildRow_(data, ref, folderUrl) {
  return [
    ref,
    data.eingegangen || '',
    data.rolle || '',
    data.name || '',
    data.email || '',
    data.telefon || '',
    data.firma || '',
    data.branche || 'Sonstiges',
    data.stadt || '—',
    data.plz || '',
    data.projekt || '',
    data.standort || '',
    data.zeitrahmen || '',
    data.budget || '',
    data.groesse || '',
    data.status_feld || '',
    data.referenzen || '',
    data.nachricht || '',
    data.dateien || '—',
    data.bearbeitung || 'Neu',
    folderUrl || ''
  ];
}

function createLeadFolder_(data, ref) {
  var root = getOrCreateFolder_(DriveApp.getRootFolder(), ROOT_FOLDER_NAME);
  var rolleFolder = getOrCreateFolder_(root, safeName_(data.rolle || 'Unbekannt'));
  var stadtFolder = getOrCreateFolder_(rolleFolder, safeName_(data.stadt || 'Unbekannt'));
  var brancheFolder = getOrCreateFolder_(stadtFolder, safeName_(data.branche || 'Sonstiges'));
  var leadName = ref + ' — ' + safeName_(data.name || 'Lead');
  var leadFolder = brancheFolder.createFolder(leadName);

  var info = [
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
    'Nachricht:',
    data.nachricht || '—'
  ].join('\n');

  leadFolder.createFile('Lead-Info.txt', info, MimeType.PLAIN_TEXT);
  return leadFolder.getUrl();
}

function getOrCreateFolder_(parent, name) {
  var folders = parent.getFoldersByName(name);
  if (folders.hasNext()) {
    return folders.next();
  }
  return parent.createFolder(name);
}

function safeName_(text) {
  return String(text || 'Unbekannt')
    .replace(/[\\/:*?"<>|]/g, '-')
    .replace(/\s+/g, ' ')
    .trim()
    .substring(0, 80) || 'Unbekannt';
}

function appendToTab_(ss, tabName, row) {
  var sheet = ss.getSheetByName(tabName);
  sheet.appendRow(row);
}

// ── Partner-Matching ────────────────────────────────────────────────────────

function findMatches_(ss, incoming, currentRef) {
  var oppositeTab = incoming.role_code === 'bauherr' ? TAB_AUFTRAGNEHMER : TAB_AUFTRAGGEBER;
  var sheet = ss.getSheetByName(oppositeTab);
  if (!sheet || sheet.getLastRow() < 2) {
    return [];
  }

  var values = sheet.getDataRange().getValues();
  var headers = values[0];
  var idx = indexMap_(headers);
  var candidates = [];

  for (var r = 1; r < values.length; r++) {
    var row = values[r];
    var ref = row[idx.ref];
    if (!ref || ref === currentRef) continue;

    var score = 0;
    var reasons = [];

    var cityScore = scoreCity_(incoming.stadt, incoming.plz, row[idx.stadt], row[idx.plz]);
    if (cityScore > 0) {
      score += cityScore;
      reasons.push('gleiche Region');
    }

    var brancheScore = scoreBranche_(incoming.branche, row[idx.branche]);
    if (brancheScore > 0) {
      score += brancheScore;
      reasons.push('passende Branche');
    }

    var regionScore = scoreRegion_(incoming.standort, row[idx.standort]);
    if (regionScore > 0) {
      score += regionScore;
      reasons.push('ähnliches Einsatzgebiet');
    }

    if (score >= 35) {
      candidates.push({
        name: String(row[idx.name] || ''),
        ref: String(ref),
        email: String(row[idx.email] || ''),
        score: Math.min(score, 100),
        reason: reasons.join(', ') || 'Allgemeine Übereinstimmung'
      });
    }
  }

  candidates.sort(function (a, b) { return b.score - a.score; });
  return candidates.slice(0, 3);
}

function indexMap_(headers) {
  var map = {};
  for (var i = 0; i < headers.length; i++) {
    var h = String(headers[i]).toLowerCase();
    if (h.indexOf('anfrage') === 0) map.ref = i;
    else if (h === 'name') map.name = i;
    else if (h.indexOf('e-mail') === 0) map.email = i;
    else if (h === 'branche') map.branche = i;
    else if (h === 'stadt') map.stadt = i;
    else if (h === 'plz') map.plz = i;
    else if (h === 'standort') map.standort = i;
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
  if (aPlz && bPlz && String(aPlz) === String(bPlz)) return 40;
  var a = norm_(aStadt);
  var b = norm_(bStadt);
  if (!a || !b || a === '—' || b === '—') return 0;
  if (a === b) return 40;
  if (a.indexOf(b) >= 0 || b.indexOf(a) >= 0) return 30;
  return 0;
}

function scoreBranche_(a, b) {
  var x = norm_(a);
  var y = norm_(b);
  if (!x || !y) return 0;
  if (x === y) return 35;
  if (x.indexOf(y) >= 0 || y.indexOf(x) >= 0) return 25;
  var related = {
    'neubau': ['wohnungsbau', 'gewerbebau', 'rohbau'],
    'sanierung': ['ausbau', 'shk'],
    'ausbau': ['sanierung', 'trockenbau'],
    'elektro': ['shk'],
    'shk': ['elektro', 'sanierung']
  };
  var xa = related[x] || [];
  for (var i = 0; i < xa.length; i++) {
    if (xa[i] === y) return 15;
  }
  return 0;
}

function scoreRegion_(a, b) {
  var x = norm_(a);
  var y = norm_(b);
  if (!x || !y) return 0;
  var wordsA = x.split(' ');
  var wordsB = y.split(' ');
  for (var i = 0; i < wordsA.length; i++) {
    if (wordsA[i].length < 4) continue;
    for (var j = 0; j < wordsB.length; j++) {
      if (wordsA[i] === wordsB[j]) return 20;
    }
  }
  return 0;
}

// ── Hilfsfunktionen ─────────────────────────────────────────────────────────

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
