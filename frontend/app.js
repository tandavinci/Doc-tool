
/* ╔══════════════════════════════════════════════════════════════════════════════╗
   ║  PHASE 2 — BUSINESS LOGIC BOUNDARY CLASSIFICATION                          ║
   ║                                                                            ║
   ║  Each section is marked:                                                   ║
   ║    [FRONTEND: UI]       → stays in app.js (DOM, rendering, events)         ║
   ║    [BACKEND: Logic]     → migrates to Python in Phase 3                    ║
   ║    [SHARED: Utility]    → may be duplicated or kept in both layers         ║
   ║                                                                            ║
   ║  DO NOT move code yet. This is documentation only.                         ║
   ╚══════════════════════════════════════════════════════════════════════════════╝ */


/* ============================================================
   TAB SWITCHING
   [FRONTEND: UI] — DOM manipulation, stays in app.js
   ============================================================ */
function openTab(id, e) {
  ['converter','analyzer','contentAnalysis','rewrite','markitdown'].forEach(t =>
    document.getElementById(t).style.display = 'none');
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  e.target.classList.add('active');
  document.getElementById(id).style.display = 'block';

  // Restore editor focus when switching back to Initial Draft tab
  if (id === 'rewrite') {
    setTimeout(function() {
      var page = document.getElementById('wr-page');
      if (page) page.focus();
    }, 50);
  }
}

/* ============================================================
   UTILITY — FILENAME SANITIZATION
   [SHARED: Utility] — used by save functions to derive filenames
   ============================================================ */

/**
 * Sanitizes a string for use as a filename.
 * Removes invalid Windows filename characters, collapses whitespace,
 * trims, and truncates to 100 characters without splitting a word.
 * @param {string} text - Raw text (e.g., heading content)
 * @returns {string} Sanitized filename, or "Untitled" if result is empty
 */
function sanitizeFilename(text) {
  if (!text) return 'Untitled';

  // 1. Remove characters invalid in Windows filenames: \ / : * ? " < > |
  var result = text.replace(/[\\/:*?"<>|]/g, '');

  // 2. Collapse consecutive whitespace into a single space
  result = result.replace(/\s+/g, ' ');

  // 3. Trim leading and trailing whitespace
  result = result.trim();

  // 4. Return "Untitled" if the result is empty after sanitization
  if (!result) return 'Untitled';

  // 5. Truncate to 100 characters without splitting a word
  if (result.length > 100) {
    result = result.substring(0, 100);
    var lastSpace = result.lastIndexOf(' ');
    if (lastSpace > 0) {
      result = result.substring(0, lastSpace);
    }
    result = result.trim();
  }

  // Final safety check — if truncation left nothing
  return result || 'Untitled';
}

/**
 * Derives a filename from the first heading in the editor canvas.
 * Finds the first h1–h4 element, sanitizes its text content,
 * and appends the provided extension.
 * @param {string} extension - File extension including dot (e.g., ".docx")
 * @returns {string} Derived filename with extension
 */
function deriveFilename(extension) {
  var page = document.getElementById('wr-page');
  if (!page) return 'Untitled' + extension;
  var heading = page.querySelector('h1, h2, h3, h4');
  var text = heading ? (heading.textContent || heading.innerText || '') : '';
  return sanitizeFilename(text) + extension;
}

/* ============================================================
   DITA CONVERTER
   [BACKEND: Logic] — XML generation handled by Python backend
   Frontend handles: UI state, IPC calls, result display
   Supports rich text paste (from Word/Docs) and .docx upload
   ============================================================ */
var _ditaLastFormat = '';

/* ── File upload handler for .docx ── */
(function() {
  function setupDitaFileInput() {
    var fileInput = document.getElementById('dita-file-input');
    if (!fileInput) return;
    fileInput.addEventListener('change', function(e) {
      var file = e.target.files[0];
      if (!file) return;
      var nameEl = document.getElementById('dita-file-name');
      nameEl.textContent = file.name;
      nameEl.style.display = 'inline';

      if (file.name.endsWith('.docx') || file.name.endsWith('.doc')) {
        // Use mammoth.js to convert .docx to HTML
        var reader = new FileReader();
        reader.onload = function(ev) {
          mammoth.convertToHtml({ arrayBuffer: ev.target.result })
            .then(function(result) {
              document.getElementById('docInput').innerHTML = result.value;
            })
            .catch(function() {
              // Fallback: extract raw text
              mammoth.extractRawText({ arrayBuffer: ev.target.result })
                .then(function(res) {
                  document.getElementById('docInput').innerText = res.value;
                });
            });
        };
        reader.readAsArrayBuffer(file);
      } else if (file.name.endsWith('.html') || file.name.endsWith('.htm')) {
        var reader = new FileReader();
        reader.onload = function(ev) {
          document.getElementById('docInput').innerHTML = ev.target.result;
        };
        reader.readAsText(file);
      } else {
        // Plain text
        var reader = new FileReader();
        reader.onload = function(ev) {
          document.getElementById('docInput').innerText = ev.target.result;
        };
        reader.readAsText(file);
      }
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupDitaFileInput);
  } else {
    setupDitaFileInput();
  }
})();

function convertConcept() {
  _ditaConvert('concept');
}

function convertTask() {
  _ditaConvert('task');
}

function _ditaGetInputContent() {
  /**
   * Extract content from the contenteditable div.
   * Returns both the rich HTML and a plain-text fallback.
   * The backend will receive the HTML for better structure detection.
   */
  var el = document.getElementById('docInput');
  var html = el.innerHTML || '';
  var text = el.innerText || el.textContent || '';
  return { html: html.trim(), text: text.trim() };
}

function _ditaConvert(format) {
  var content = _ditaGetInputContent();
  if (!content.text) {
    _ditaShowAlert('Please paste some content to convert.', 'error');
    return;
  }

  // Show loading state
  document.getElementById('dita-loading').style.display = 'inline-flex';
  document.getElementById('dita-concept-btn').disabled = true;
  document.getElementById('dita-task-btn').disabled = true;
  _ditaHideAlert();

  // Send HTML content to backend for richer conversion;
  // fall back to plain text if HTML is trivial
  var payload = content.html.indexOf('<') !== -1 ? content.html : content.text;

  if (window.api && window.api.convertDita) {
    window.api.convertDita(payload, format).then(function(response) {
      _ditaHideLoading();
      if (response && response.success) {
        _ditaShowOutput(response.data.xml, format);
      } else {
        var errMsg = (response && response.error) ? response.error.message : 'Conversion failed.';
        _ditaShowAlert(errMsg, 'error');
        // Fallback to local conversion with plain text
        _ditaShowOutput(_convertLocal(content.text, format), format);
      }
    }).catch(function(err) {
      _ditaHideLoading();
      _ditaShowOutput(_convertLocal(content.text, format), format);
    });
  } else {
    _ditaHideLoading();
    _ditaShowOutput(_convertLocal(content.text, format), format);
  }
}

function _convertLocal(text, format) {
  // Basic local fallback when backend is not available
  var lines = text.split('\n');
  if (format === 'task') {
    var xml = '<taskbody>\n<steps>\n';
    lines.forEach(function(l) {
      if (l.match(/^\d+\./)) {
        xml += '<step>\n<cmd>' + xEsc(l.replace(/^\d+\./, '').trim()) + '</cmd>\n</step>\n';
      }
    });
    return xml + '</steps>\n</taskbody>';
  } else {
    var xml = '<conbody>\n';
    lines.forEach(function(l) { l = l.trim(); if (l) xml += '<p>' + xEsc(l) + '</p>\n'; });
    return xml + '</conbody>';
  }
}

function _ditaShowOutput(xml, format) {
  _ditaLastFormat = format;
  document.getElementById('xmlOutput').value = xml;
  document.getElementById('dita-output-section').style.display = 'block';
  document.getElementById('dita-format-badge').textContent = format === 'task' ? 'Task' : 'Concept';
}

function _ditaHideLoading() {
  document.getElementById('dita-loading').style.display = 'none';
  document.getElementById('dita-concept-btn').disabled = false;
  document.getElementById('dita-task-btn').disabled = false;
}

function _ditaShowAlert(message, type) {
  var el = document.getElementById('dita-alert');
  el.textContent = message;
  el.style.display = 'block';
  if (type === 'success') {
    el.style.background = '#d4edda'; el.style.border = '1px solid #c3e6cb'; el.style.color = '#155724';
    setTimeout(_ditaHideAlert, 3000);
  } else {
    el.style.background = '#f8d7da'; el.style.border = '1px solid #f5c6cb'; el.style.color = '#721c24';
  }
}

function _ditaHideAlert() {
  document.getElementById('dita-alert').style.display = 'none';
}

function clearDitaConverter() {
  document.getElementById('docInput').innerHTML = '';
  document.getElementById('xmlOutput').value = '';
  document.getElementById('dita-output-section').style.display = 'none';
  var nameEl = document.getElementById('dita-file-name');
  if (nameEl) { nameEl.style.display = 'none'; nameEl.textContent = ''; }
  var fileInput = document.getElementById('dita-file-input');
  if (fileInput) fileInput.value = '';
  _ditaHideAlert();
  _ditaLastFormat = '';
}

function xEsc(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function copyDitaXml() {
  var xml = document.getElementById('xmlOutput').value;
  if (!xml) { _ditaShowAlert('No XML output to copy.', 'error'); return; }
  navigator.clipboard.writeText(xml).then(function() {
    _ditaShowAlert('XML copied to clipboard.', 'success');
  }).catch(function() { _ditaShowAlert('Copy failed.', 'error'); });
}

function downloadDitaXml() {
  var xml = document.getElementById('xmlOutput').value;
  if (!xml) { _ditaShowAlert('No XML output to download.', 'error'); return; }
  var filename = 'output_' + (_ditaLastFormat || 'dita') + '.xml';
  var blob = new Blob([xml], { type: 'application/xml;charset=utf-8' });
  saveAs(blob, filename);
}

/* ============================================================
   IMPACT ANALYZER  —  JIRA + DITA MAP
   ============================================================ */

/* ── State ── */
/* [FRONTEND: UI] — application state, stays in app.js */
var _jiraRows    = [];   // parsed from Excel
var _ditaTopics  = [];   // parsed from ZIP
var _createList  = [];
var _updateList  = [];

/* ── Excel column detection ── */
/* [FRONTEND: UI] — file upload handling, SheetJS parsing, DOM updates */
document.getElementById('jiraFile').addEventListener('change', async function(e) {
  var file = e.target.files[0];
  if (!file) return;
  var ab = await file.arrayBuffer();
  var wb = XLSX.read(ab, { type: 'array' });
  var ws = wb.Sheets[wb.SheetNames[0]];
  var rows = XLSX.utils.sheet_to_json(ws, { defval: '' });
  _jiraRows = rows;
  var cols = rows.length ? Object.keys(rows[0]) : [];
  ['jiraSummaryCol','jiraDescCol','jiraTypeCol'].forEach(function(id) {
    var sel = document.getElementById(id);
    sel.innerHTML = '<option value="">(none)</option>' +
      cols.map(function(c){ return '<option value="'+hEsc(c)+'">'+hEsc(c)+'</option>'; }).join('');
  });
  /* Auto-detect common column names */
  function autoSelect(id, hints) {
    var sel = document.getElementById(id);
    for (var i = 0; i < hints.length; i++) {
      var h = hints[i].toLowerCase();
      for (var j = 0; j < cols.length; j++) {
        if (cols[j].toLowerCase().includes(h)) { sel.value = cols[j]; return; }
      }
    }
  }
  autoSelect('jiraSummaryCol', ['summary','title','subject','name','headline']);
  autoSelect('jiraDescCol',    ['description','detail','body','desc','notes']);
  autoSelect('jiraTypeCol',    ['issuetype','issue type','type','kind','category']);
  document.getElementById('jira-col-row').style.display = 'block';
  document.getElementById('jira-preview').textContent = '\u2705 ' + rows.length + ' JIRA rows loaded';
});

/* ── ZIP parsing ── */
/* [FRONTEND: UI] — file upload handling, JSZip parsing, DOM updates */
document.getElementById('ditaZipFile').addEventListener('change', async function(e) {
  var file = e.target.files[0];
  if (!file) return;
  var ab = await file.arrayBuffer();
  var zip = await JSZip.loadAsync(ab);
  var topics = [];
  var htmlFiles = Object.keys(zip.files).filter(function(n){ return n.match(/\.html?$/i); });
  for (var i = 0; i < htmlFiles.length; i++) {
    var name = htmlFiles[i];
    var content = await zip.files[name].async('string');
    var titleMatch = content.match(/<title[^>]*>([^<]+)<\/title>/i);
    var h1Match    = content.match(/<h1[^>]*>([\s\S]*?)<\/h1>/i);
    var title = (titleMatch && titleMatch[1].trim()) ||
                (h1Match && h1Match[1].replace(/<[^>]+>/g,'').trim()) ||
                name.replace(/.*[\\/]/,'').replace(/\.html?$/i,'');
    var bodyMatch = content.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
    var bodyText  = bodyMatch ? bodyMatch[1].replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').trim().substring(0,800) : '';
    topics.push({ file: name, title: title, body: bodyText });
  }
  _ditaTopics = topics;
  document.getElementById('dita-preview').textContent = '\u2705 ' + topics.length + ' topic files found in ZIP';
});

/* ── Similarity helpers ── */
/* [BACKEND: Logic] — tokenization and Jaccard similarity migrate to Python (utils.py)
   Functions to extract: tokenise, jaccardSim */
function tokenise(str) {
  return (str || '').toLowerCase()
    .replace(/[^a-z0-9\s]/g,' ')
    .split(/\s+/)
    .filter(function(w){ return w.length > 2; });
}
function jaccardSim(a, b) {
  if (!a.length && !b.length) return 0;
  var setA = {}, setB = {};
  a.forEach(function(w){ setA[w]=1; });
  b.forEach(function(w){ setB[w]=1; });
  var inter = 0;
  Object.keys(setA).forEach(function(w){ if (setB[w]) inter++; });
  var union = Object.keys(setA).length + Object.keys(setB).length - inter;
  return union > 0 ? inter / union : 0;
}

/* ── Main analysis ── */
/* [MIXED] — runImpactAnalysis contains:
   - [FRONTEND: UI] input validation, DOM reads, threshold selection, result rendering call
   - [BACKEND: Logic] tokenization loop, Jaccard comparison, create/update classification
   In Phase 3: the comparison/classification logic moves to Python (analyzer.py),
   frontend calls window.api.impactAnalyze() and renders results */
async function runImpactAnalysis() {
  var errEl = document.getElementById('impact-error');
  errEl.style.display = 'none';

  if (!_jiraRows.length)  { showImpactError('Please upload a JIRA Excel file first.'); return; }
  if (!_ditaTopics.length){ showImpactError('Please upload the DITA map ZIP file first.'); return; }

  var summaryCol = document.getElementById('jiraSummaryCol').value;
  if (!summaryCol) { showImpactError('Please select the JIRA Summary column.'); return; }
  var descCol    = document.getElementById('jiraDescCol').value;
  var typeCol    = document.getElementById('jiraTypeCol').value;

  var sensVal    = document.querySelector('input[name="sensitivity"]:checked').value;
  var thresholds = { strict:0.30, normal:0.18, loose:0.10 };
  var threshold  = thresholds[sensVal];

  _createList = [];
  _updateList = [];

  // Prepare JIRA items for backend
  var jiraItems = _jiraRows.map(function(row, idx) {
    var summary  = String(row[summaryCol] || '');
    var desc     = descCol ? String(row[descCol] || '') : '';
    var issueType= typeCol ? String(row[typeCol] || '') : '';
    var jiraKey  = '';
    Object.keys(row).forEach(function(k){
      if (!jiraKey && /^[A-Z]+-\d+$/.test(String(row[k]||'').trim())) jiraKey = row[k];
    });
    if (!jiraKey) jiraKey = 'ROW-' + (idx+1);
    return { key: jiraKey, summary: summary, description: desc, issueType: issueType };
  });

  // Use backend via Electron IPC if available, otherwise use local JS
  if (window.api && window.api.impactAnalyze) {
    try {
      var response = await window.api.impactAnalyze(jiraItems, _ditaTopics, threshold);
      if (response.success) {
        // Map backend response to frontend format
        _createList = (response.data.topicsToCreate || []).map(function(r) {
          var suggested = r.summary
            .replace(/^\[.*?\]\s*/,'')
            .replace(/^(feat|fix|chore|docs|refactor|update|add|new|create|improve):\s*/i,'')
            .trim();
          if (suggested.length > 80) suggested = suggested.substring(0,77) + '\u2026';
          return { key: r.jiraKey, type: r.issueType, summary: r.summary, suggested: suggested, score: r.bestMatchScore };
        });
        _updateList = (response.data.topicsToUpdate || []).map(function(r) {
          return { key: r.jiraKey, type: r.issueType, summary: r.summary, matchedFile: '', matchedTitle: r.matchedTopic, score: r.confidence };
        });
        renderImpactResults();
        return;
      }
    } catch(e) { /* fall through to local */ }
  }

  // Local fallback
  _runImpactAnalysisLocal(jiraItems, threshold);
  renderImpactResults();
}

function _runImpactAnalysisLocal(jiraItems, threshold) {
  var topicTokens = _ditaTopics.map(function(t){
    return tokenise(t.title + ' ' + t.body);
  });

  jiraItems.forEach(function(item) {
    var jiraTokens = tokenise(item.summary + ' ' + item.description);
    var bestScore = 0, bestTopic = null;
    _ditaTopics.forEach(function(topic, ti) {
      var score = jaccardSim(jiraTokens, topicTokens[ti]);
      if (score > bestScore) { bestScore = score; bestTopic = topic; }
    });

    var suggested = item.summary
      .replace(/^\[.*?\]\s*/,'')
      .replace(/^(feat|fix|chore|docs|refactor|update|add|new|create|improve):\s*/i,'')
      .trim();
    if (suggested.length > 80) suggested = suggested.substring(0,77) + '\u2026';

    if (bestScore >= threshold) {
      _updateList.push({
        key: item.key, type: item.issueType, summary: item.summary,
        matchedFile: bestTopic ? bestTopic.file : '',
        matchedTitle: bestTopic ? bestTopic.title : '',
        score: bestScore
      });
    } else {
      _createList.push({
        key: item.key, type: item.issueType, summary: item.summary,
        suggested: suggested, score: bestScore
      });
    }
  });
}

/* [FRONTEND: UI] — error display, stays in app.js */
function showImpactError(msg) {
  var el = document.getElementById('impact-error');
  el.textContent = msg;
  el.style.display = 'block';
}

/* [FRONTEND: UI] — result rendering, stays in app.js */
function renderImpactResults() {
  /* Summary strip */
  var strip = document.getElementById('impact-summary-strip');
  strip.innerHTML = [
    ['Total JIRAs', _jiraRows.length, '#343a40', 'white'],
    ['Topics to Create', _createList.length, '#28a745', 'white'],
    ['Topics to Update', _updateList.length, '#ffc107', '#333'],
    ['DITA Topics in ZIP', _ditaTopics.length, '#007cba', 'white']
  ].map(function(d){
    return '<div style="background:'+d[2]+';color:'+d[3]+';padding:10px 18px;border-radius:8px;text-align:center;">' +
           '<div style="font-size:22px;font-weight:700;">'+d[1]+'</div>' +
           '<div style="font-size:12px;opacity:.9;">'+d[0]+'</div></div>';
  }).join('');

  /* CREATE table */
  document.getElementById('create-count').textContent = _createList.length;
  var ctbody = document.getElementById('create-tbody');
  ctbody.innerHTML = _createList.length ? _createList.map(function(r,i){
    var conf = r.score > 0.08 ? 'Possible duplicate' : 'New topic';
    var confColor = r.score > 0.08 ? '#856404' : '#155724';
    var confBg    = r.score > 0.08 ? '#fff3cd' : '#d4edda';
    return '<tr>' +
      '<td>'+(i+1)+'</td>' +
      '<td style="font-family:monospace;font-size:12px;">'+hEsc(r.key)+'</td>' +
      '<td><span style="font-size:11px;background:#e2e3e5;padding:2px 6px;border-radius:10px;">'+hEsc(r.type||'—')+'</span></td>' +
      '<td style="font-size:13px;">'+hEsc(r.summary)+'</td>' +
      '<td style="font-size:13px;color:#007cba;font-style:italic;">'+hEsc(r.suggested)+'</td>' +
      '<td><span style="font-size:11px;background:'+confBg+';color:'+confColor+';padding:3px 8px;border-radius:10px;">'+conf+'</span></td>' +
      '</tr>';
  }).join('') : '<tr><td colspan="6" style="text-align:center;color:#888;padding:20px;">No new topics needed — all JIRAs matched existing content.</td></tr>';

  /* UPDATE table */
  document.getElementById('update-count').textContent = _updateList.length;
  var utbody = document.getElementById('update-tbody');
  utbody.innerHTML = _updateList.length ? _updateList.map(function(r,i){
    var pct = Math.round(r.score * 100);
    var barColor = pct > 50 ? '#28a745' : pct > 30 ? '#ffc107' : '#007cba';
    return '<tr>' +
      '<td>'+(i+1)+'</td>' +
      '<td style="font-family:monospace;font-size:12px;">'+hEsc(r.key)+'</td>' +
      '<td><span style="font-size:11px;background:#e2e3e5;padding:2px 6px;border-radius:10px;">'+hEsc(r.type||'—')+'</span></td>' +
      '<td style="font-size:13px;">'+hEsc(r.summary)+'</td>' +
      '<td style="font-size:12px;color:#555;">'+hEsc(r.matchedTitle || r.matchedFile)+'<br><span style="font-size:11px;color:#888;">'+hEsc(r.matchedFile)+'</span></td>' +
      '<td><div style="font-size:12px;font-weight:700;color:'+barColor+';">'+pct+'%</div>' +
           '<div style="height:5px;background:#eee;border-radius:3px;margin-top:3px;">' +
           '<div style="width:'+Math.min(pct,100)+'%;height:5px;background:'+barColor+';border-radius:3px;"></div></div></td>' +
      '</tr>';
  }).join('') : '<tr><td colspan="6" style="text-align:center;color:#888;padding:20px;">No topics matched for update.</td></tr>';

  document.getElementById('impact-results').style.display = 'block';
}

/* [FRONTEND: UI] — DOM reset, stays in app.js */
function clearImpactAnalysis() {
  _jiraRows = []; _ditaTopics = []; _createList = []; _updateList = [];
  document.getElementById('jiraFile').value = '';
  document.getElementById('ditaZipFile').value = '';
  document.getElementById('jira-col-row').style.display = 'none';
  document.getElementById('jira-preview').textContent = '';
  document.getElementById('dita-preview').textContent = '';
  document.getElementById('impact-results').style.display = 'none';
  document.getElementById('impact-error').style.display = 'none';
}

/* [FRONTEND: UI] — CSV export and file download, stays in app.js */
function exportImpactCSV(which) {
  var rows = [], header = '';
  if (which === 'create' || which === 'all') {
    header = 'Action,JIRA Key,Issue Type,JIRA Summary,Suggested Topic Title\n';
    rows = rows.concat(_createList.map(function(r){
      return 'CREATE,'+csvCell(r.key)+','+csvCell(r.type)+','+csvCell(r.summary)+','+csvCell(r.suggested);
    }));
  }
  if (which === 'update' || which === 'all') {
    if (!rows.length) header = 'Action,JIRA Key,Issue Type,JIRA Summary,Matched Topic File,Match Score\n';
    rows = rows.concat(_updateList.map(function(r){
      return 'UPDATE,'+csvCell(r.key)+','+csvCell(r.type)+','+csvCell(r.summary)+','+csvCell(r.matchedFile)+','+(Math.round(r.score*100)+'%');
    }));
  }
  if (!rows.length) { alert('Nothing to export.'); return; }
  var csv = header + rows.join('\n');
  var blob = new Blob([csv], { type: 'text/csv' });
  saveAs(blob, 'impact-analysis-' + which + '.csv');
}

/* [SHARED: Utility] — CSV escaping helper */
function csvCell(v) {
  v = String(v||'');
  if (v.includes(',') || v.includes('"') || v.includes('\n')) return '"' + v.replace(/"/g,'""') + '"';
  return v;
}


/* ============================================================
   CONTENT ANALYSIS — RULE DEFINITIONS
   [BACKEND: Logic] — CA_RULES array migrates to Python (rules.py)
   All rule definitions: id, category, pattern, message, fix, color
   ============================================================ */
const CA_RULES = [

  /* ── 1. GRAMMAR ── */
  { id:'double_negative', cat:'Grammar',
    pattern:/\b(not|never|no)\b[^.!?\n]{0,90}\b(not|never|no|neither|nor)\b/gi,
    msg:'Double negative detected. Rewrite using positive phrasing.', color:'ca-warn' },
  { id:'subjunctive', cat:'Grammar',
    pattern:/\b(if I were|if he were|if she were|if they were|if it were|were to)\b/gi,
    msg:'Avoid subjunctive mood. Rewrite in indicative or imperative mood.', color:'ca-warn' },
  { id:'discontinuous_phrasal', cat:'Grammar',
    pattern:/\b(turn|switch|shut|close)\s+(?:the\s+)?\w+\s+(off|on|up|down)\b/gi,
    msg:'Keep phrasal verbs together (e.g., "turn off the device", not "turn the device off").', color:'ca-warn' },
  { id:'missing_that', cat:'Grammar',
    pattern:/\b(ensure|confirm|specify|note|verify|check)\s+(it|the|a|an|this|that|these|those|you|we|they|he|she)\b/gi,
    msg:'Include "that" in relative clauses (e.g., "Ensure that the file is saved").', color:'ca-warn' },

  /* ── 2. WORD USAGE ── */
  { id:'in_order_to', cat:'Word Usage', pattern:/\bin order to\b/gi,
    msg:'Replace "in order to" with "to".', fix:'to', color:'ca-replace' },
  { id:'due_to_fact', cat:'Word Usage', pattern:/\bdue to the fact that\b/gi,
    msg:'Replace "due to the fact that" with "because".', fix:'because', color:'ca-replace' },
  { id:'as_consequence', cat:'Word Usage', pattern:/\bas a consequence of\b/gi,
    msg:'Replace "as a consequence of" with "because of".', fix:'because of', color:'ca-replace' },
  { id:'you_have_to', cat:'Word Usage', pattern:/\byou have to\b/gi,
    msg:'Use "you must" to express a requirement.', fix:'you must', color:'ca-replace' },
  { id:'you_ought_to', cat:'Word Usage', pattern:/\byou ought to\b/gi,
    msg:'Use "you should" to express a recommendation.', fix:'you should', color:'ca-replace' },
  { id:'recommended_that', cat:'Word Usage', pattern:/\bit is recommended that you\b/gi,
    msg:'Replace with "you should".', fix:'you should', color:'ca-replace' },
  { id:'simply',    cat:'Word Usage', pattern:/\bsimply\b/gi,    msg:'Remove vague modifier "simply".',    fix:'', color:'ca-remove' },
  { id:'easily',    cat:'Word Usage', pattern:/\beasily\b/gi,    msg:'Remove vague modifier "easily".',    fix:'', color:'ca-remove' },
  { id:'quickly',   cat:'Word Usage', pattern:/\bquickly\b/gi,   msg:'Remove vague modifier "quickly".',   fix:'', color:'ca-remove' },
  { id:'very',      cat:'Word Usage', pattern:/\bvery\b/gi,      msg:'Remove vague modifier "very".',      fix:'', color:'ca-remove' },
  { id:'really',    cat:'Word Usage', pattern:/\breally\b/gi,    msg:'Remove vague modifier "really".',    fix:'', color:'ca-remove' },
  { id:'quite',     cat:'Word Usage', pattern:/\bquite\b/gi,     msg:'Remove vague modifier "quite".',     fix:'', color:'ca-remove' },
  { id:'obviously', cat:'Word Usage', pattern:/\bobviously\b/gi, msg:'Remove vague modifier "obviously".',  fix:'', color:'ca-remove' },
  { id:'actually',  cat:'Word Usage', pattern:/\bactually\b/gi,  msg:'Remove vague modifier "actually".',  fix:'', color:'ca-remove' },
  { id:'just',      cat:'Word Usage', pattern:/\bjust\b/gi,
    msg:'Remove vague modifier "just" unless meaning changes without it.', fix:'', color:'ca-remove' },
  { id:'leverage', cat:'Word Usage', pattern:/\bleverage\b/gi, msg:'Replace jargon "leverage" with "use".', fix:'use', color:'ca-replace' },
  { id:'utilize',  cat:'Word Usage', pattern:/\butilize\b/gi,  msg:'Replace "utilize" with "use".', fix:'use', color:'ca-replace' },
  { id:'login_ui', cat:'Word Usage', pattern:/\b(login|log[\s\-]in)\b/gi,
    msg:'Use "sign in". "Login" and "log in" are not permitted.', fix:'sign in', color:'ca-replace' },
  { id:'logout_ui', cat:'Word Usage', pattern:/\b(logout|log[\s\-]out|logoff|log[\s\-]off)\b/gi,
    msg:'Use "sign out". "Logout", "log out", and "logoff" are not permitted.', fix:'sign out', color:'ca-replace' },
  { id:'click_on', cat:'Word Usage', pattern:/\bclick on\b/gi,
    msg:'Use "click" for buttons, not "click on".', fix:'click', color:'ca-replace' },
  { id:'default_adj', cat:'Word Usage',
    pattern:/\bdefault\s+(value|setting|option|behavior|behaviour|state|mode|view)\b/gi,
    msg:'"Default" must be used as a noun only. Do not use it as an adjective.', color:'ca-warn' },

  /* ── 2b. WORD USAGE — controlled language ruleset ── */
  { id:'if_when',        cat:'Word Usage', pattern:/\bif\/when\b/gi,
    msg:'Avoid "if/when". Use "if" or "when" depending on the context.', color:'ca-warn' },
  { id:'either_or_slash',cat:'Word Usage', pattern:/\beither\/or\b/gi,
    msg:'Avoid "either/or". Use "and" or "or".', color:'ca-warn' },
  { id:'eg',             cat:'Word Usage', pattern:/\be\.g\./gi,
    msg:'Replace "e.g." with "for example".', fix:'for example', color:'ca-replace' },
  { id:'ie',             cat:'Word Usage', pattern:/\bi\.e\./gi,
    msg:'Replace "i.e." with "that is".', fix:'that is', color:'ca-replace' },
  { id:'ampersand',      cat:'Word Usage', pattern:/(?<![A-Za-z0-9#&])&(?![A-Za-z0-9#;])/g,
    msg:'Replace "&" with "and".', fix:'and', color:'ca-replace' },
  { id:'etc_warn',       cat:'Word Usage', pattern:/\betc\./gi,
    msg:'Avoid "etc." unless the list follows a clear logical progression. Use "such as" to introduce partial lists.', color:'ca-warn' },
  { id:'and_so_on',      cat:'Word Usage', pattern:/\band so on\b/gi,
    msg:'Replace "and so on" with "such as" or list items explicitly.', fix:'such as', color:'ca-replace' },
  { id:'via',            cat:'Word Usage', pattern:/\bvia\b/gi,
    msg:'Replace "via" with "by", "through", or "with".', color:'ca-warn' },
  { id:'able_to',        cat:'Word Usage', pattern:/\bable to\b/gi,
    msg:'Replace "able to" with "can".', fix:'can', color:'ca-replace' },
  { id:'activate',       cat:'Word Usage', pattern:/\bactivate\b/gi,
    msg:'Replace "activate" with "start" or "run".', fix:'start', color:'ca-replace' },
  { id:'amend',          cat:'Word Usage', pattern:/\bamend\b/gi,
    msg:'Replace "amend" with "change".', fix:'change', color:'ca-replace' },
  { id:'appears',        cat:'Word Usage', pattern:/\bappears?\b/gi,
    msg:'Replace "appear/appears" with "is displayed" (passive) or "shows" (active).', color:'ca-warn' },
  { id:'as_a_result',    cat:'Word Usage', pattern:/\bas a result\b/gi,
    msg:'Replace "as a result" with "therefore".', fix:'therefore', color:'ca-replace' },
  { id:'due_to',         cat:'Word Usage', pattern:/\bdue to\b(?!\s+the\s+fact)/gi,
    msg:'Replace "due to" with "because of".', fix:'because of', color:'ca-replace' },
  { id:'make_sure',      cat:'Word Usage', pattern:/\b(?:make sure|be sure|take care)\b/gi,
    msg:'Replace with "ensure".', fix:'ensure', color:'ca-replace' },
  { id:'execute_prog',   cat:'Word Usage', pattern:/\bexecute\b/gi,
    msg:'Replace "execute" with "run" (programs) or "perform" or "complete" (actions).', fix:'run', color:'ca-replace' },
  { id:'finalize',       cat:'Word Usage', pattern:/\bfinalize\b/gi,
    msg:'Replace "finalize" with "finish" or "complete".', fix:'complete', color:'ca-replace' },
  { id:'fetch',          cat:'Word Usage', pattern:/\bfetch\b/gi,
    msg:'Replace "fetch" with "retrieve" or "get".', fix:'retrieve', color:'ca-replace' },
  { id:'hang_resp',      cat:'Word Usage', pattern:/\bhang(?:s|ing)?\b(?!\s+(?:over|on|out|around|tight))/gi,
    msg:'Replace "hang" with "stop responding".', fix:'stop responding', color:'ca-replace' },
  { id:'hard_adj',       cat:'Word Usage', pattern:/\bhard to\b/gi,
    msg:'Replace "hard to" with "difficult to".', fix:'difficult to', color:'ca-replace' },
  { id:'have_to',        cat:'Word Usage', pattern:/\bhave to\b/gi,
    msg:'Replace "have to" with "must".', fix:'must', color:'ca-replace' },
  { id:'impact_verb',    cat:'Word Usage', pattern:/\bimpact(?:s|ed|ing)?\b/gi,
    msg:'Use "affect" (verb) or "effect" (noun) instead of "impact".', color:'ca-warn' },
  { id:'log_onto',       cat:'Word Usage', pattern:/\blog\s+onto\b/gi,
    msg:'Use "sign in" instead of "log onto".', fix:'sign in', color:'ca-replace' },
  { id:'populate',       cat:'Word Usage', pattern:/\bpopulate\b/gi,
    msg:'Replace "populate" with "fill".', fix:'fill', color:'ca-replace' },
  { id:'prior_to',       cat:'Word Usage', pattern:/\bprior to\b/gi,
    msg:'Replace "prior to" with "before".', fix:'before', color:'ca-replace' },
  { id:'toggle',         cat:'Word Usage', pattern:/\btoggle\b/gi,
    msg:'Replace "toggle" with "switch" or "change".', fix:'switch', color:'ca-replace' },
  { id:'whether_or_not', cat:'Word Usage', pattern:/\bwhether or not\b/gi,
    msg:'Replace "whether or not" with "whether".', fix:'whether', color:'ca-replace' },
  { id:'hover_no_over',  cat:'Word Usage', pattern:/\bhover\b(?!\s+over)/gi,
    msg:'Use "hover over", not just "hover".', fix:'hover over', color:'ca-replace' },
  { id:'such_as_etc',    cat:'Word Usage', pattern:/\bsuch as\b[^.!?\n]{0,80}\betc\./gi,
    msg:'Do not combine "such as" with "etc." Use one or the other.', color:'ca-warn' },

  /* ── 3. PRONOUNS ── */
  { id:'vague_this', cat:'Pronouns',
    pattern:/\bThis\s+(is|was|can|will|has|have|enables|allows|means|refers|indicates|helps|provides|ensures|makes|requires)\b/g,
    msg:'Vague pronoun "This". Add a noun to clarify (e.g., "This process is…").', color:'ca-warn' },
  { id:'vague_these', cat:'Pronouns',
    pattern:/\bThese\s+(are|were|can|will|have|enable|allow|include|ensure|make|require)\b/g,
    msg:'Vague pronoun "These". Add a noun (e.g., "These settings are…").', color:'ca-warn' },
  { id:'vague_those', cat:'Pronouns',
    pattern:/\bThose\s+(are|were|can|will|have|enable|allow|include|require)\b/g,
    msg:'Vague pronoun "Those". Add a noun to clarify the antecedent.', color:'ca-warn' },
  { id:'which_clause', cat:'Pronouns', pattern:/,\s*which\b/gi,
    msg:'"Which" after a comma may refer to the entire preceding clause. Split into two sentences.', color:'ca-warn' },
  { id:'gender_pronoun', cat:'Pronouns', pattern:/\b(he|she|he\/she|s\/he)\b/g,
    msg:'Use gender-neutral language. Replace gendered pronouns with "they", "their", or rewrite using plural forms.', color:'ca-warn' },

  /* ── 4. STYLE & TONE ── */
  { id:'please', cat:'Style & Tone', pattern:/\bplease\b/gi,
    msg:'Remove politeness marker "please". Technical writing must be direct and neutral.', fix:'', color:'ca-remove' },
  { id:'kindly', cat:'Style & Tone', pattern:/\bkindly\b/gi,
    msg:'Remove politeness marker "kindly".', fix:'', color:'ca-remove' },
  { id:'blacklist', cat:'Style & Tone', pattern:/\bblacklist(?:ed|ing|s)?\b/gi,
    msg:'Replace biased term "blacklist" with "blocklist" or "denylist".', fix:'blocklist', color:'ca-remove' },
  { id:'whitelist', cat:'Style & Tone', pattern:/\bwhitelist(?:ed|ing|s)?\b/gi,
    msg:'Replace biased term "whitelist" with "allowlist".', fix:'allowlist', color:'ca-remove' },
  { id:'master_slave', cat:'Style & Tone', pattern:/\b(master|slave)\b/gi,
    msg:'Replace "master" or "slave" with "primary/secondary" or "controller/worker".', color:'ca-remove' },
  { id:'manpower', cat:'Style & Tone', pattern:/\bmanpower\b/gi,
    msg:'Replace "manpower" with "workforce" or "staff".', fix:'workforce', color:'ca-remove' },
  { id:'kill_term', cat:'Style & Tone', pattern:/\bkill\b/gi,
    msg:'Replace violent term "kill" with "stop", "end", or "terminate".', fix:'stop', color:'ca-remove' },
  { id:'abort_term', cat:'Style & Tone', pattern:/\babort\b/gi,
    msg:'Replace "abort" with "cancel" or "stop".', fix:'cancel', color:'ca-remove' },
  { id:'below_ref',      cat:'Style & Tone', pattern:/\bbelow\b/gi,
    msg:'Avoid "below". Reference content by name or section title.', color:'ca-warn' },
  { id:'following_ref',  cat:'Style & Tone', pattern:/\bthe following\b/gi,
    msg:'Avoid "the following". Use a specific heading or label instead.', color:'ca-warn' },
  { id:'little_mod',     cat:'Style & Tone', pattern:/\blittle\b/gi,
    msg:'Avoid vague modifier "little". Be specific.', fix:'', color:'ca-remove' },
  { id:'greatly_mod',    cat:'Style & Tone', pattern:/\bgreatly\b/gi,
    msg:'Avoid vague modifier "greatly". Be specific.', fix:'', color:'ca-remove' },
  { id:'also_start',     cat:'Style & Tone', pattern:/\bAlso\b/g,
    msg:'Avoid starting a sentence with "Also". Restructure the sentence.', color:'ca-warn' },
  { id:'minorities',     cat:'Style & Tone', pattern:/\bminorities\b/gi,
    msg:'Replace "minorities" with "underrepresented groups".', fix:'underrepresented groups', color:'ca-replace' },
  { id:'bomb_term',      cat:'Style & Tone', pattern:/\bbomb\b/gi,
    msg:'Avoid violent term "bomb". Rephrase to describe the actual action or event.', color:'ca-warn' },

  /* ── 5. PUNCTUATION ── */
  { id:'semicolon', cat:'Punctuation', pattern:/;/g,
    msg:'Avoid semicolons. Rewrite as two separate sentences.', color:'ca-warn' },
  { id:'em_dash', cat:'Punctuation', pattern:/\u2014|\u2013/g,
    msg:'Avoid em and en dashes. Use a comma or split the sentence.', color:'ca-warn' },

  /* ── 6. NUMBERS ── */
  { id:'digit_small', cat:'Numbers',
    pattern:/(?<![A-Za-z0-9.\/\-#@v])([1-9])(?!\s*(?:st|nd|rd|th)|[0-9%\u00b0\/.:\-])/g,
    msg:'Spell out numbers less than 10 (e.g., write "five" instead of "5").', color:'ca-warn' },
  { id:'approx_about', cat:'Numbers', pattern:/\babout\s+\d+\b/gi,
    msg:'Avoid approximations. Use the exact number instead of "about N".', color:'ca-warn' },
  { id:'approx_around', cat:'Numbers', pattern:/\baround\s+\d+\b/gi,
    msg:'Avoid approximations. Use the exact number instead of "around N".', color:'ca-warn' },
  { id:'approx_approx', cat:'Numbers', pattern:/\bapproximately\s+\d+\b/gi,
    msg:'Avoid approximations. Use the exact number.', color:'ca-warn' },

  /* ── 8. TRANSLATION & CONSISTENCY ── */
  { id:'based_on', cat:'Translation', pattern:/\bbased on\b/gi,
    msg:'Ambiguous "based on". Clarify explicitly (e.g., "calculated from", "derived from").', color:'ca-warn' },
  { id:'need_not', cat:'Translation', pattern:/\bneed not\b/gi,
    msg:'Ambiguous "need not". Rephrase (e.g., "do not need to").', fix:'do not need to', color:'ca-warn' },
  { id:'must_have_been', cat:'Translation', pattern:/\bmust have been\b/gi,
    msg:'Ambiguous modal "must have been". Rephrase to remove ambiguity.', color:'ca-warn' },
  { id:'ambig_it', cat:'Translation',
    pattern:/\bIt\s+(is|was|can|will|has|have|ensures|enables|allows|provides|means)\b/g,
    msg:'Possible vague "It". Ensure the antecedent is explicit and unambiguous.', color:'ca-warn' },

  /* ── Additional WORD USAGE ── */
  { id:'rather_mod', cat:'Word Usage', pattern:/\brather\b/gi,
    msg:'Remove vague modifier "rather".', fix:'', color:'ca-remove' },
  { id:'need_to', cat:'Word Usage', pattern:/\bneed to\b/gi,
    msg:'"Need to" implies personal necessity. Use "must" for required actions or "should" for recommended actions.', color:'ca-warn' },
  { id:'on_premise', cat:'Word Usage', pattern:/\bon-premise(?!s)\b/gi,
    msg:'Use "on-premises" (with an "s"), not "on-premise".', fix:'on-premises', color:'ca-replace' },
  { id:'need_personal', cat:'Word Usage', pattern:/\b(I|you|we|they)\s+need\b/gi,
    msg:'"Need" implies personal necessity. Use "require" in formal or technical contexts.', color:'ca-warn' },
  { id:'displayed_use', cat:'Word Usage', pattern:/\bdisplayed\b/gi,
    msg:'Avoid "displayed" for screen navigation. Use "access" (e.g., "You can access this screen only if...").', color:'ca-warn' },

  /* ── Additional STYLE & TONE ── */
  { id:'foreman_word', cat:'Style & Tone', pattern:/\bforeman\b/gi,
    msg:'Replace "foreman" with the gender-neutral term "supervisor".', fix:'supervisor', color:'ca-remove' },
  { id:'you_must_not', cat:'Style & Tone', pattern:/\byou must not\b/gi,
    msg:'Use "do not" instead of "you must not". Write positively.', fix:'do not', color:'ca-replace' },

  /* ── Additional PUNCTUATION ── */
  { id:'ellipsis', cat:'Punctuation', pattern:/\.{3}|…/g,
    msg:'Avoid ellipses. Rewrite the sentence to be complete.', color:'ca-warn' },
  { id:'and_or_slash', cat:'Punctuation', pattern:/\band\/or\b/gi,
    msg:'Avoid "and/or". Use "and" or "or" depending on the context.', color:'ca-warn' },
  { id:'contraction', cat:'Punctuation',
    pattern:/\b(don't|can't|won't|isn't|aren't|wasn't|weren't|hasn't|haven't|hadn't|doesn't|didn't|wouldn't|couldn't|shouldn't|I'm|I've|I'll|I'd|you're|you've|you'll|you'd|he's|she's|it's|we're|we've|we'll|we'd|they're|they've|they'll|they'd|that's|what's|there's|here's|let's|who's|how's)\b/g,
    msg:'Expand this contraction. Technical writing must not use contractions.', color:'ca-replace' },

  /* ── 7. UI CONVENTIONS ── */
  { id:'hit_key', cat:'UI Conventions', pattern:/\bhit\b/gi,
    msg:'Use "press" for keyboard keys, not "hit".', fix:'press', color:'ca-replace' },
  { id:'push_button', cat:'UI Conventions', pattern:/\bpush\b/gi,
    msg:'Use "click" for buttons, not "push".', fix:'click', color:'ca-replace' },
  { id:'click_at', cat:'UI Conventions', pattern:/\bclick\s+at\b/gi,
    msg:'Use "click", not "click at".', fix:'click', color:'ca-replace' },
  { id:'dialog_no_box', cat:'UI Conventions', pattern:/\bdialog(?!\s*box)\b/gi,
    msg:'Use "dialog box", not just "dialog". The full term is required.', fix:'dialog box', color:'ca-replace' },
  { id:'submenu_word', cat:'UI Conventions', pattern:/\bsubmenu\b/gi,
    msg:'Avoid "submenu". Describe the specific menu path instead.', color:'ca-warn' },
  { id:'navigate_to', cat:'UI Conventions', pattern:/\bnavigate to\b/gi,
    msg:'Use "access" instead of "navigate to" when referring to screens or pages.', fix:'access', color:'ca-replace' },
  { id:'screen_displayed', cat:'UI Conventions', pattern:/\b(?:screen|page|window|session)\s+(?:is|are)\s+displayed\b/gi,
    msg:'Use "access" when referring to navigating to a screen, page, or session (e.g., "You can access this screen only if...").', color:'ca-warn' },

  /* ── STYLE & TONE — additional inclusive language ── */
  { id:'elderly_seniors', cat:'Style & Tone',
    pattern:/\b(the elderly|elderly people|senior citizens|seniors(?!\s+(?:manager|developer|executive|analyst|architect|vice|director|level|leadership|position|role|staff|member|team)))\b/gi,
    msg:'Replace "the elderly" or "seniors" with "older adults".', fix:'older adults', color:'ca-replace' },

  /* ── WORD USAGE — website, amount vs quantity ── */
  { id:'web_site', cat:'Word Usage', pattern:/\bweb\s+site\b/gi,
    msg:'Use "website" as one word, not "web site".', fix:'website', color:'ca-replace' },
  { id:'amount_for_qty', cat:'Word Usage',
    pattern:/\bamount\s+of\s+(?:items|records|entries|rows|documents|files|users|accounts|lines|tasks|results|transactions|orders|products|parts|units|tickets|requests)\b/gi,
    msg:'Use "quantity" for countable items, not "amount". "Amount" is for uncountable or monetary values.', fix:'quantity of', color:'ca-replace' },
  { id:'qty_for_amount', cat:'Word Usage',
    pattern:/\bquantity\s+of\s+(?:money|dollars|euros|pounds|currency|funds|budget|costs?|prices?|revenue|payment|expenses?|fees?|charges?)\b/gi,
    msg:'Use "amount" for monetary values, not "quantity". "Quantity" is for countable items.', fix:'amount of', color:'ca-replace' },
  { id:'number_of_money', cat:'Word Usage',
    pattern:/\bnumber\s+of\s+(?:money|dollars|euros|pounds|currency|funds|budget|costs?|prices?|revenue|payment|expenses?)\b/gi,
    msg:'Use "amount" for monetary values, not "number of".', fix:'amount of', color:'ca-replace' },
  { id:'dialog_standalone', cat:'Word Usage', pattern:/\bdialog\b(?!\s*box)/gi,
    msg:'Use "dialog box" (the full term), not "dialog" alone.', fix:'dialog box', color:'ca-replace' },

  /* ── UI CONVENTIONS — clear/select/specify/press ── */
  { id:'uncheck_word', cat:'UI Conventions', pattern:/\buncheck\b/gi,
    msg:'Use "Clear" to deselect a check box, not "uncheck".', fix:'Clear', color:'ca-replace' },
  { id:'deselect_word', cat:'UI Conventions', pattern:/\bdeselect\b/gi,
    msg:'Use "Clear" to deselect an option, not "deselect".', fix:'Clear', color:'ca-replace' },
  { id:'check_checkbox', cat:'UI Conventions',
    pattern:/\bcheck\s+(?:the\s+|a\s+)?(?:\w+\s+)?(?:check\s*box|checkbox)\b/gi,
    msg:'Use "Select" for check boxes, not "check". Example: "Select the check box."', fix:'Select the check box', color:'ca-replace' },
  { id:'tick_checkbox', cat:'UI Conventions', pattern:/\btick\s+(?:the\s+|a\s+)?(?:\w+\s+)?(?:check\s*box|checkbox)\b/gi,
    msg:'Use "Select" for check boxes, not "tick".', fix:'Select', color:'ca-replace' },
  { id:'press_enter_vs_click', cat:'UI Conventions',
    pattern:/\bclick\s+(?:the\s+)?(?:Enter|Return|Tab|Escape|Esc|Delete|Backspace|Ctrl|Alt|Shift|Spacebar|Space bar|F\d{1,2})\b/gi,
    msg:'Use "Press" for keyboard keys, not "Click".', fix:'Press', color:'ca-replace' },
  { id:'select_from_menu', cat:'UI Conventions', pattern:/\bchoose\s+(?:from\s+)?(?:the\s+)?(?:\w+\s+)?(?:menu|list|drop-?down)\b/gi,
    msg:'Use "Select" when choosing from a menu or list.', fix:'Select', color:'ca-replace' },
  { id:'specify_text_field', cat:'UI Conventions',
    pattern:/\b(?:type|enter)\s+(?:the\s+|a\s+|your\s+)?\w[\w\s]{0,30}(?:in(?:to)?\s+the\s+\w+\s+field|in(?:to)?\s+the\s+\w+\s+box)\b/gi,
    msg:'Use "Specify" when instructing users to fill in a text field. Example: "Specify the name in the Name field."', color:'ca-warn' },
  { id:'open_vs_access', cat:'UI Conventions', pattern:/\bopen\s+(?:the\s+)?(?:\w+\s+)?(?:screen|page|window|form|tab)\b/gi,
    msg:'Use "access" instead of "open" when navigating to a screen, page, or window.', fix:'access', color:'ca-replace' },

  /* ── GRAMMAR — task steps, future tense, noun-as-verb ── */
  { id:'step_not_verb', cat:'Grammar',
    pattern:/^(?:\d+[.)]\s+)(?:The |A |An |This |These |Your |My |Our |Their |Its |All |Each |Every )/gm,
    msg:'Task steps must start with a verb (imperative mood). This step appears to start with a noun, article, or possessive.', color:'ca-warn' },
  { id:'future_tense_ui', cat:'Grammar',
    pattern:/\bwill\s+(?:be\s+)?(?:display|show|appear|open|close|update|refresh|load|save|create|delete|add|remove|enable|disable|generate|populate|calculate|validate|process)\b/gi,
    msg:'Use simple present tense for current software actions. Use future tense only for actions clearly occurring in the future.', color:'ca-warn' },
  { id:'action_noun_as_verb', cat:'Grammar', pattern:/\bto\s+action\b/gi,
    msg:'Do not use "action" as a verb. Rewrite using "perform", "complete", or a specific action verb.', color:'ca-warn' },
  { id:'solution_verb', cat:'Grammar', pattern:/\bsolution\s+(?:this|that|the)\b/gi,
    msg:'Do not use "solution" as a verb. Use "resolve" or "fix".', color:'ca-warn' },
  { id:'impact_as_verb', cat:'Grammar', pattern:/\b(?:this|that|it|the\s+\w+)\s+impact(?:s|ed)?\b/gi,
    msg:'Do not use "impact" as a verb. Use "affect" (verb) or "effect" (noun).', fix:'affects', color:'ca-replace' },

  /* ── PUNCTUATION — dependent clause comma, double space ── */
  { id:'double_space', cat:'Punctuation', pattern:/[ \t]{2,}/g,
    msg:'Use a single space between words. Remove the extra space.', fix:' ', color:'ca-replace' },
  { id:'dep_clause_if', cat:'Punctuation',
    pattern:/(?:^|\.\s+)If\s+[^,\n.]{20,}[^,\n]\s+(?:you\b|the\b|a\b|an\b|it\b|select\b|click\b|type\b|enter\b|specify\b|choose\b)/gm,
    msg:'Add a comma after an introductory "If" clause. Example: "If the field is empty, specify a value."', color:'ca-warn' },
  { id:'dep_clause_when', cat:'Punctuation',
    pattern:/(?:^|\.\s+)When\s+[^,\n.]{20,}[^,\n]\s+(?:you\b|the\b|a\b|an\b|it\b|select\b|click\b|type\b|enter\b|specify\b|choose\b)/gm,
    msg:'Add a comma after an introductory "When" clause. Example: "When the process completes, the status changes."', color:'ca-warn' },
  { id:'dep_clause_after', cat:'Punctuation',
    pattern:/(?:^|\.\s+)After\s+[^,\n.]{15,}[^,\n]\s+(?:you\b|the\b|a\b|an\b|it\b|select\b|click\b|type\b|enter\b|specify\b|choose\b)/gm,
    msg:'Add a comma after an introductory "After" clause. Example: "After you save the record, the list refreshes."', color:'ca-warn' },
  { id:'slash_separator', cat:'Punctuation',
    pattern:/\b\w+\/\w+\b(?<!(?:https?:|ftp:)\/\/\w)/g,
    msg:'Avoid using a slash as a separator. Rewrite using "and", "or", or rewrite the sentence.', color:'ca-warn' },

  /* ── NUMBERS — ordinals below 10 ── */
  { id:'ordinal_spell_small', cat:'Numbers',
    pattern:/\b(1st|2nd|3rd|4th|5th|6th|7th|8th|9th)\b/g,
    msg:'Spell out ordinal numbers below 10 (e.g., "first", "second", "third").', color:'ca-warn' },

  /* ── READABILITY — paragraph length ── */
  /* (paragraph-level check is handled in checkSentenceLevel below) */

  /* ── TRANSLATION — additional ambiguity checks ── */
  { id:'may_ambig', cat:'Translation', pattern:/\b(?:you\s+)?may\s+(?:also\s+)?(?:want\s+to\s+|wish\s+to\s+)?(?:[a-z]+)\b/gi,
    msg:'"May" is ambiguous — it can mean permission or possibility. Use "can" for permission or "might" for possibility.', color:'ca-warn' },
  { id:'should_ambig_passive', cat:'Translation', pattern:/\bshould\s+be\s+(?:noted|mentioned|understood|known|remembered|highlighted)\b/gi,
    msg:'Avoid passive constructions with "should be noted". Rewrite as an active statement.', color:'ca-warn' },
  { id:'once_ambig', cat:'Translation', pattern:/\bonce\b/gi,
    msg:'"Once" is ambiguous — it can mean "after" (temporal) or "one time only". Use "after" or "when" for clarity.', color:'ca-warn' },
  { id:'since_ambig', cat:'Translation', pattern:/\bsince\b/gi,
    msg:'"Since" is ambiguous — it can mean "because" or "from that time". Use "because" or "after" to remove ambiguity.', color:'ca-warn' },
  { id:'while_ambig', cat:'Translation', pattern:/\bwhile\b/gi,
    msg:'"While" is ambiguous — it can mean "although" or "at the same time as". Use "although" or "when" for clarity.', color:'ca-warn' }
];


/* ── Undo/Redo State ── */
/* [FRONTEND: UI] — global undo/redo stacks for Content Analysis fixes */

var _caGlobalUndoStack = [];
var _caGlobalRedoStack = [];

/**
 * Records an undo entry when a fix is applied.
 * @param {number} violationIndex - Violation index
 * @param {string} originalText - Original matched text before the fix
 * @param {string} replacementText - Replacement text applied
 * @param {number} offset - Character offset in the text
 */
function pushUndoEntry(violationIndex, originalText, replacementText, offset) {
  _caGlobalUndoStack.push({ violationIndex: violationIndex, originalText: originalText, replacementText: replacementText, offset: offset });
  _caGlobalRedoStack = [];
}

/**
 * Clears all undo/redo stacks (called on new analysis or manual text edit).
 */
function clearAllUndoStacks() {
  _caGlobalUndoStack = [];
  _caGlobalRedoStack = [];
}

/**
 * Global undo: reverts the most recent CA fix action.
 */
function caGlobalUndo() {
  if (_caGlobalUndoStack.length === 0) return;
  var entry = _caGlobalUndoStack.pop();
  // Handle full text swap entries (from contenteditable manual edits)
  if (entry.isFullTextSwap) {
    _text = entry.originalText;
    _caGlobalRedoStack.push(entry);
    document.getElementById('caInput').value = _text;
    rerunCA();
    return;
  }
  // Verify text at offset matches replacement
  var textAtOffset = _text.substring(entry.offset, entry.offset + entry.replacementText.length);
  if (textAtOffset !== entry.replacementText) return; // stale entry
  // Revert: replace replacementText with originalText
  _text = _text.substring(0, entry.offset) + entry.originalText + _text.substring(entry.offset + entry.replacementText.length);
  _caGlobalRedoStack.push(entry);
  document.getElementById('caInput').value = _text;
  rerunCA();
}

/**
 * Global redo: re-applies the most recently undone CA fix action.
 */
function caGlobalRedo() {
  if (_caGlobalRedoStack.length === 0) return;
  var entry = _caGlobalRedoStack.pop();
  // Handle full text swap entries (from contenteditable manual edits)
  if (entry.isFullTextSwap) {
    _text = entry.replacementText;
    _caGlobalUndoStack.push(entry);
    document.getElementById('caInput').value = _text;
    rerunCA();
    return;
  }
  // Verify text at offset matches original
  var textAtOffset = _text.substring(entry.offset, entry.offset + entry.originalText.length);
  if (textAtOffset !== entry.originalText) return; // stale entry
  // Re-apply: replace originalText with replacementText
  _text = _text.substring(0, entry.offset) + entry.replacementText + _text.substring(entry.offset + entry.originalText.length);
  _caGlobalUndoStack.push(entry);
  document.getElementById('caInput').value = _text;
  rerunCA();
}


/* ── Sentence-level checks ── */
/* [BACKEND: Logic] — sentence analysis migrates to Python (rules.py)
   Functions to extract: checkSentenceLevel */
function checkSentenceLevel(text) {
  const out = [];
  const sentPat = /[^.!?\n]+[.!?]/g;
  let m;
  while ((m = sentPat.exec(text)) !== null) {
    const words = m[0].trim().split(/\s+/).filter(w => w);
    if (words.length > 25) {
      out.push({
        start: m.index, end: m.index + m[0].length,
        ruleId:'sentence_length', cat:'Grammar',
        msg:'Sentence is ' + words.length + ' words (maximum: 25). Split into shorter sentences.',
        matchText: m[0].slice(0,60) + '\u2026',
        color:'ca-structure'
      });
    }
  }
  const numStart = /(?:^|[.!?]\s{1,4})(\d+)\s/gm;
  while ((m = numStart.exec(text)) !== null) {
    const idx = text.indexOf(m[1], m.index);
    out.push({
      start: idx, end: idx + m[1].length,
      ruleId:'number_sentence_start', cat:'Numbers',
      msg:'Spell out numbers at the start of a sentence.',
      matchText: m[1], color:'ca-warn'
    });
  }
  return out;
}


/* ── Collect all violations ── */
/* [BACKEND: Logic] — violation collection and overlap resolution migrates to Python (analyzer.py)
   Functions to extract: collectViolations */
function collectViolations(text) {
  const all = [];
  for (const rule of CA_RULES) {
    const rx = new RegExp(rule.pattern.source, rule.pattern.flags);
    let m;
    while ((m = rx.exec(text)) !== null) {
      all.push({
        start: m.index, end: m.index + m[0].length,
        ruleId: rule.id, cat: rule.cat,
        msg: rule.msg, fix: rule.fix,
        color: rule.color, matchText: m[0]
      });
    }
  }
  all.push(...checkSentenceLevel(text));
  all.sort((a, b) => a.start - b.start);
  const clean = [];
  let cursor = 0;
  for (const v of all) {
    if (v.start >= cursor) { clean.push(v); cursor = v.end; }
  }
  return clean;
}


/* ── HTML / JS escape helpers ── */
/* [FRONTEND: UI] — rendering helpers, stay in app.js */
function hEsc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function aEsc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function escJs(s) {
  return String(s).replace(/\\/g,'\\\\').replace(/'/g,"\\'").replace(/"/g,'\\"').replace(/\n/g,'\\n');
}


/* ═══════════════════════════════════════════════════════════
   CONTEXT EXTRACTION
   [FRONTEND: UI] — rendering helper for violation context display, stays in app.js
   ═══════════════════════════════════════════════════════════ */
function getContextHtml(text, v) {
  /* find sentence start */
  var sStart = v.start;
  while (sStart > 0 && !/[.!?\n]/.test(text[sStart-1])) sStart--;
  /* find sentence end */
  var sEnd = v.end;
  while (sEnd < text.length && !/[.!?\n]/.test(text[sEnd])) sEnd++;
  if (sEnd < text.length && /[.!?]/.test(text[sEnd])) sEnd++;

  var relStart = v.start - sStart;
  var relEnd   = v.end   - sStart;
  var sentence = text.slice(sStart, sEnd);

  /* truncate very long sentences */
  if (sentence.length > 220) {
    var pad  = 70;
    var from = Math.max(0, relStart - pad);
    var to   = Math.min(sentence.length, relEnd + pad);
    var pre  = from > 0 ? '…' : '';
    var suf  = to < sentence.length ? '…' : '';
    relStart -= from;
    relEnd   -= from;
    sentence  = sentence.slice(from, to);
    return hEsc(pre) +
      hEsc(sentence.slice(0, relStart)) +
      '<mark class="ctx-highlight">' + hEsc(sentence.slice(relStart, relEnd)) + '</mark>' +
      hEsc(sentence.slice(relEnd)) + hEsc(suf);
  }
  return hEsc(sentence.slice(0, relStart)) +
    '<mark class="ctx-highlight">' + hEsc(sentence.slice(relStart, relEnd)) + '</mark>' +
    hEsc(sentence.slice(relEnd));
}


/* ═══════════════════════════════════════════════════════════
   3-SUGGESTION ALTERNATIVES MAP
   [FRONTEND: UI] — UI display data for suggestion buttons, stays in app.js
   ═══════════════════════════════════════════════════════════ */
const RULE_ALTS = {
  'in_order_to':      [{l:'to',v:'to'},{l:'so that',v:'so that'},{l:'for',v:'for'}],
  'due_to_fact':      [{l:'because',v:'because'},{l:'since',v:'since'},{l:'as',v:'as'}],
  'as_consequence':   [{l:'because of',v:'because of'},{l:'due to',v:'due to'},{l:'owing to',v:'owing to'}],
  'you_have_to':      [{l:'you must',v:'you must'},{l:'you are required to',v:'you are required to'},{l:'you need to',v:'you need to'}],
  'you_ought_to':     [{l:'you should',v:'you should'},{l:'you are advised to',v:'you are advised to'},{l:'you are recommended to',v:'you are recommended to'}],
  'recommended_that': [{l:'you should',v:'you should'},{l:'you must',v:'you must'},{l:'it is advised to',v:'it is advised to'}],
  'simply':           [{l:'✕ Remove',v:''},{l:'only',v:'only'}],
  'easily':           [{l:'✕ Remove',v:''}],
  'quickly':          [{l:'✕ Remove',v:''},{l:'promptly',v:'promptly'}],
  'very':             [{l:'✕ Remove',v:''}],
  'really':           [{l:'✕ Remove',v:''}],
  'quite':            [{l:'✕ Remove',v:''},{l:'rather',v:'rather'}],
  'obviously':        [{l:'✕ Remove',v:''},{l:'clearly',v:'clearly'}],
  'actually':         [{l:'✕ Remove',v:''},{l:'in fact',v:'in fact'}],
  'just':             [{l:'✕ Remove',v:''},{l:'only',v:'only'}],
  'leverage':         [{l:'use',v:'use'},{l:'apply',v:'apply'},{l:'employ',v:'employ'}],
  'utilize':          [{l:'use',v:'use'},{l:'apply',v:'apply'},{l:'employ',v:'employ'}],
  'login_ui':         [{l:'sign in',v:'sign in'},{l:'log in',v:'log in'},{l:'access',v:'access'}],
  'logout_ui':        [{l:'sign out',v:'sign out'},{l:'log out',v:'log out'},{l:'exit',v:'exit'}],
  'click_on':         [{l:'click',v:'click'},{l:'select',v:'select'},{l:'choose',v:'choose'}],
  'please':           [{l:'✕ Remove',v:''}],
  'kindly':           [{l:'✕ Remove',v:''},{l:'note that',v:'note that'}],
  'blacklist':        [{l:'blocklist',v:'blocklist'},{l:'denylist',v:'denylist'},{l:'exclusion list',v:'exclusion list'}],
  'whitelist':        [{l:'allowlist',v:'allowlist'},{l:'permit list',v:'permit list'},{l:'inclusion list',v:'inclusion list'}],
  'master_slave':     [{l:'primary',v:'primary'},{l:'controller',v:'controller'},{l:'main',v:'main'}],
  'manpower':         [{l:'workforce',v:'workforce'},{l:'staff',v:'staff'},{l:'personnel',v:'personnel'}],
  'kill_term':        [{l:'stop',v:'stop'},{l:'terminate',v:'terminate'},{l:'end',v:'end'}],
  'abort_term':       [{l:'cancel',v:'cancel'},{l:'stop',v:'stop'},{l:'terminate',v:'terminate'}],
  'based_on':         [{l:'calculated from',v:'calculated from'},{l:'derived from',v:'derived from'},{l:'determined by',v:'determined by'}],
  'need_not':         [{l:'do not need to',v:'do not need to'},{l:'are not required to',v:'are not required to'},{l:'do not have to',v:'do not have to'}],
  'double_negative':  [],
  'subjunctive':      [],
  'missing_that':     [],
  'vague_this':       [],
  'vague_these':      [],
  'vague_those':      [],
  'which_clause':     [],
  'semicolon':        [],
  'em_dash':          [],
  'digit_small':      [],
  'approx_about':     [],
  'approx_around':    [],
  'approx_approx':    [],
  'must_have_been':   [],
  'ambig_it':         [],
  'sentence_length':  [],
  'number_sentence_start': [],

  /* ── Controlled language ruleset additions ── */
  'if_when':         [],
  'either_or_slash': [],
  'eg':              [{l:'for example',v:'for example'},{l:'such as',v:'such as'}],
  'ie':              [{l:'that is',v:'that is'},{l:'specifically',v:'specifically'}],
  'ampersand':       [{l:'and',v:'and'}],
  'etc_warn':        [],
  'and_so_on':       [{l:'such as',v:'such as'},{l:'✕ Remove',v:''}],
  'via':             [{l:'by',v:'by'},{l:'through',v:'through'},{l:'with',v:'with'}],
  'able_to':         [{l:'can',v:'can'},{l:'is able to',v:'is able to'}],
  'activate':        [{l:'start',v:'start'},{l:'run',v:'run'},{l:'enable',v:'enable'}],
  'amend':           [{l:'change',v:'change'},{l:'update',v:'update'},{l:'modify',v:'modify'}],
  'appears':         [{l:'is displayed',v:'is displayed'},{l:'shows',v:'shows'}],
  'as_a_result':     [{l:'therefore',v:'therefore'},{l:'consequently',v:'consequently'},{l:'thus',v:'thus'}],
  'due_to':          [{l:'because of',v:'because of'},{l:'because',v:'because'},{l:'owing to',v:'owing to'}],
  'make_sure':       [{l:'ensure',v:'ensure'},{l:'verify',v:'verify'},{l:'confirm',v:'confirm'}],
  'execute_prog':    [{l:'run',v:'run'},{l:'perform',v:'perform'},{l:'complete',v:'complete'}],
  'finalize':        [{l:'complete',v:'complete'},{l:'finish',v:'finish'}],
  'fetch':           [{l:'retrieve',v:'retrieve'},{l:'get',v:'get'},{l:'obtain',v:'obtain'}],
  'hang_resp':       [{l:'stop responding',v:'stop responding'},{l:'become unresponsive',v:'become unresponsive'}],
  'hard_adj':        [{l:'difficult to',v:'difficult to'},{l:'challenging to',v:'challenging to'}],
  'have_to':         [{l:'must',v:'must'},{l:'are required to',v:'are required to'}],
  'impact_verb':     [{l:'affect',v:'affect'},{l:'effect',v:'effect'}],
  'log_onto':        [{l:'sign in',v:'sign in'},{l:'sign in to',v:'sign in to'}],
  'populate':        [{l:'fill',v:'fill'},{l:'complete',v:'complete'},{l:'add',v:'add'}],
  'prior_to':        [{l:'before',v:'before'},{l:'preceding',v:'preceding'}],
  'toggle':          [{l:'switch',v:'switch'},{l:'change',v:'change'},{l:'turn on or off',v:'turn on or off'}],
  'whether_or_not':  [{l:'whether',v:'whether'}],
  'hover_no_over':   [{l:'hover over',v:'hover over'}],
  'such_as_etc':     [],
  'gender_pronoun':  [{l:'they',v:'they'},{l:'their',v:'their'}],
  'below_ref':       [],
  'following_ref':   [],
  'little_mod':      [{l:'✕ Remove',v:''}],
  'greatly_mod':     [{l:'✕ Remove',v:''},{l:'significantly',v:'significantly'}],
  'also_start':      [],
  'minorities':      [{l:'underrepresented groups',v:'underrepresented groups'},{l:'marginalized groups',v:'marginalized groups'}],
  'bomb_term':       [],

  /* ── Additional Word Usage ── */
  'rather_mod':       [{l:'✕ Remove',v:''}],
  'need_to':          [{l:'must',v:'must'},{l:'should',v:'should'},{l:'are required to',v:'are required to'}],
  'on_premise':       [{l:'on-premises',v:'on-premises'}],
  'need_personal':    [{l:'require',v:'require'},{l:'must',v:'must'}],
  'displayed_use':    [],

  /* ── Additional Style & Tone ── */
  'foreman_word':     [{l:'supervisor',v:'supervisor'},{l:'team lead',v:'team lead'},{l:'manager',v:'manager'}],
  'you_must_not':     [{l:'do not',v:'do not'},{l:'must not',v:'must not'}],

  /* ── Additional Punctuation ── */
  'ellipsis':         [],
  'and_or_slash':     [{l:'and',v:'and'},{l:'or',v:'or'}],
  'contraction':      [],

  /* ── UI Conventions ── */
  'hit_key':          [{l:'press',v:'press'},{l:'use',v:'use'}],
  'push_button':      [{l:'click',v:'click'},{l:'select',v:'select'}],
  'click_at':         [{l:'click',v:'click'}],
  'dialog_no_box':    [{l:'dialog box',v:'dialog box'}],
  'submenu_word':     [],
  'navigate_to':      [{l:'access',v:'access'},{l:'open',v:'open'}],
  'screen_displayed': []
};

function getAlternatives(v) {
  var alts = RULE_ALTS[v.ruleId];
  if (alts && alts.length > 0) return alts;
  if (v.fix !== undefined) {
    return v.fix === '' ? [{l:'✕ Remove',v:''}] : [{l: v.fix, v: v.fix}];
  }
  return [];
}


/* ═══════════════════════════════════════════════════════════
   BUILD ANNOTATED HTML
   [FRONTEND: UI] — DOM rendering of highlighted violations, stays in app.js
   ═══════════════════════════════════════════════════════════ */
function buildAnnotated(text, violations) {
  let html = '', pos = 0;
  for (var i = 0; i < violations.length; i++) {
    var v = violations[i];
    if (_ignoredSet.has(i)) {
      html += hEsc(text.slice(pos, v.end));
      pos = v.end;
      continue;
    }
    html += hEsc(text.slice(pos, v.start));
    var fixHint = v.fix !== undefined
      ? (v.fix === '' ? ' → [remove]' : ' → "' + v.fix + '"')
      : '';
    html += '<span class="ca-violation ' + v.color + '"' +
            ' data-vidx="' + i + '"' +
            ' data-tooltip="' + aEsc('[' + v.cat + '] ' + v.msg + fixHint) + '"' +
            ' onclick="showFixPopup(' + i + ', this, event)">' +
            hEsc(text.slice(v.start, v.end)) + '</span>';
    pos = v.end;
  }
  html += hEsc(text.slice(pos));
  return html;
}


/* ═══════════════════════════════════════════════════════════
   BUILD SUMMARY BADGES
   [FRONTEND: UI] — DOM rendering of category badges, stays in app.js
   ═══════════════════════════════════════════════════════════ */
function buildBadges(violations) {
  const clsMap = {
    'Grammar':'badge-grammar','Word Usage':'badge-wordusage',
    'Pronouns':'badge-pronouns','Style & Tone':'badge-style',
    'Punctuation':'badge-punctuation','Numbers':'badge-numbers',
    'Translation':'badge-translation','UI Conventions':'badge-uiconv'
  };
  const counts = {};
  var active = 0;
  for (var i = 0; i < violations.length; i++) {
    if (_ignoredSet.has(i)) continue;
    var v = violations[i];
    counts[v.cat] = (counts[v.cat]||0) + 1;
    active++;
  }
  let html = '';
  for (const [cat, n] of Object.entries(counts)) {
    html += '<span class="ca-badge ' + (clsMap[cat]||'badge-total') + '">' + cat + ': ' + n + '</span>';
  }
  html += '<span class="ca-badge badge-total">Total: ' + active + '</span>';
  return html;
}


/* ═══════════════════════════════════════════════════════════
   BUILD VIOLATIONS TABLE (enhanced)
   [FRONTEND: UI] — DOM rendering of violations table, stays in app.js
   ═══════════════════════════════════════════════════════════ */
function buildVTable(violations) {
  const roleMap = {
    'ca-remove':    {label:'Remove',    cls:'role-remove'},
    'ca-replace':   {label:'Replace',   cls:'role-replace'},
    'ca-warn':      {label:'Review',    cls:'role-warn'},
    'ca-structure': {label:'Structure', cls:'role-struct'}
  };
  const catMap = {
    'Grammar':'badge-grammar','Word Usage':'badge-wordusage',
    'Pronouns':'badge-pronouns','Style & Tone':'badge-style',
    'Punctuation':'badge-punctuation','Numbers':'badge-numbers',
    'Translation':'badge-translation','UI Conventions':'badge-uiconv'
  };

  var rows = '';
  var visibleIdx = 0;

  for (var i = 0; i < violations.length; i++) {
    var v = violations[i];
    if (_ignoredSet.has(i)) {
      rows += '<tr class="vrow vrow-ignored" id="vrow-' + i + '">' +
        '<td style="color:#aaa;">' + (visibleIdx+1) + '</td>' +
        '<td colspan="5" style="color:#aaa;font-style:italic;">Ignored: ' + hEsc(v.matchText||'') + '</td>' +
        '</tr>';
      visibleIdx++;
      continue;
    }

    var role = roleMap[v.color] || {label:'Review', cls:'role-warn'};
    var alts = getAlternatives(v);
    var ctxHtml = getContextHtml(_text, v);

    /* Suggestion pills for table detail row */
    var pills = '';
    if (alts.length > 0) {
      pills = alts.map(function(a) {
        var cls = (a.v === '') ? 'sugg-pill remove-pill' : 'sugg-pill';
        return '<button class="' + cls + '" onclick="applyOneFix(' + i + ',\'' + escJs(a.v) + '\');event.stopPropagation();">' + hEsc(a.l) + '</button>';
      }).join('');
    } else {
      pills = '<span class="sugg-none">Manual review required — edit text above.</span>';
    }

    /* Apply button: applies primary fix if available, else toggles detail */
    var applyBtn = '';
    if (v.fix !== undefined) {
      applyBtn = '<button class="btn-sm btn-green" title="Apply fix" ' +
        'onclick="applyOneFix(' + i + ',\'' + escJs(v.fix) + '\');event.stopPropagation();">✓ Apply</button>';
    } else {
      applyBtn = '<button class="btn-sm" style="background:#6f42c1;" title="Show suggestions" ' +
        'onclick="toggleDetailRow(' + i + ');event.stopPropagation();">💡 Suggest</button>';
    }

    /* Main row */
    rows += '<tr class="vrow" id="vrow-' + i + '" onclick="toggleDetailRow(' + i + ')" style="cursor:pointer;">' +
      '<td><strong>' + (visibleIdx+1) + '</strong></td>' +
      '<td><span class="ca-badge ' + (catMap[v.cat]||'badge-total') + '" style="font-size:11px;padding:3px 8px;">' + hEsc(v.cat) + '</span></td>' +
      '<td><span class="ca-violation ' + v.color + '" style="padding:2px 6px;border-radius:3px;font-size:12px;cursor:default;">' + hEsc((v.matchText||'').slice(0,40)) + '</span></td>' +
      '<td><span class="role-badge ' + role.cls + '">' + role.label + '</span></td>' +
      '<td style="font-size:12px;color:#444;max-width:240px;">' + hEsc(v.msg.length > 80 ? v.msg.slice(0,80)+'…' : v.msg) + '</td>' +
      '<td style="white-space:nowrap;">' +
        applyBtn + ' ' +
        '<button class="btn-sm btn-grey" title="Ignore this issue" onclick="ignoreFix(' + i + ');event.stopPropagation();">✗ Ignore</button>' +
      '</td>' +
      '</tr>';

    /* Detail row */
    rows += '<tr class="vdetail-row" id="vdetail-' + i + '">' +
      '<td colspan="6">' +
        '<div class="vdetail-content">' +
          '<div class="vdetail-left">' +
            '<div class="vdetail-label">Rule</div>' +
            '<div class="vdetail-rule">' + hEsc(v.msg) + '</div>' +
            '<div class="vdetail-label">Context Sentence</div>' +
            '<div class="vdetail-ctx">' + ctxHtml + '</div>' +
          '</div>' +
          '<div class="vdetail-right">' +
            '<div class="vdetail-label">Replace with:</div>' +
            '<div class="sugg-pills">' + pills + '</div>' +
            '<div class="vdetail-label" style="margin-top:6px;">Custom replacement:</div>' +
            '<div class="custom-replace-row">' +
              '<input type="text" id="custom-' + i + '" placeholder="Type your own replacement…" value="' + aEsc(v.fix !== undefined ? v.fix : '') + '">' +
              '<button class="btn-sm btn-green" onclick="applyCustomFromTable(' + i + ');event.stopPropagation();">Apply</button>' +
            '</div>' +
          '</div>' +
        '</div>' +
      '</td>' +
      '</tr>';

    visibleIdx++;
  }

  return rows || '<tr><td colspan="6" style="text-align:center;color:#888;padding:20px;">No issues found.</td></tr>';
}


/* ═══════════════════════════════════════════════════════════
   AUTO-FIX (apply all)
   [BACKEND: Logic] — rule-based text transformation migrates to Python (analyzer.py)
   Functions to extract: computeFixed
   ═══════════════════════════════════════════════════════════ */
function computeFixed(text) {
  let out = text;
  for (const rule of CA_RULES) {
    if (rule.fix === undefined) continue;
    const rx = new RegExp(rule.pattern.source, rule.pattern.flags);
    out = out.replace(rx, rule.fix);
  }
  return out.replace(/[ \t]{2,}/g, ' ').replace(/ ([,.:!?])/g, '$1').trim();
}


/* ═══════════════════════════════════════════════════════════
   SINGLE-FIX APPLY
   [FRONTEND: UI] — DOM manipulation for applying individual fixes, stays in app.js
   ═══════════════════════════════════════════════════════════ */
function applyOneFix(vidx, replacement) {
  var v = _violations[vidx];
  if (!v) return;

  // Record undo entry before modifying text
  var originalText = _text.slice(v.start, v.end);
  _caGlobalUndoStack.push({ violationIndex: vidx, originalText: originalText, replacementText: replacement, offset: v.start });
  _caGlobalRedoStack = []; // new action clears redo

  var before = _text.slice(0, v.start);
  var after  = _text.slice(v.end);
  _text = (before + replacement + after).replace(/[ \t]{2,}/g,' ').replace(/ ([,.:!?])/g,'$1');
  document.getElementById('caInput').value = _text;
  closeFixPopup();
  rerunCA();
}

function applyCustomFromTable(vidx) {
  var inp = document.getElementById('custom-' + vidx);
  if (!inp) return;
  applyOneFix(vidx, inp.value);
}

function ignoreFix(vidx) {
  _ignoredSet.add(vidx);
  refreshCADisplay();
}

function revertIgnore(vidx) {
  _ignoredSet.delete(vidx);
  refreshCADisplay();
}

function toggleDetailRow(vidx) {
  var det = document.getElementById('vdetail-' + vidx);
  if (!det) return;
  det.classList.toggle('open');
}


/* ═══════════════════════════════════════════════════════════
   GRAMMARLY-LIKE POPUP
   [FRONTEND: UI] — popup rendering and interaction, stays in app.js
   ═══════════════════════════════════════════════════════════ */
var _popupVidx = -1;

function showFixPopup(vidx, el, e) {
  if (e) e.stopPropagation();
  _popupVidx = vidx;
  var v = _violations[vidx];
  if (!v) return;

  var popup = document.getElementById('ca-fix-popup');

  /* Category badge */
  var catMap = {
    'Grammar':'badge-grammar','Word Usage':'badge-wordusage','Pronouns':'badge-pronouns',
    'Style & Tone':'badge-style','Punctuation':'badge-punctuation',
    'Numbers':'badge-numbers','Translation':'badge-translation'
  };
  var roleMap = {
    'ca-remove':    {label:'Remove',    cls:'role-remove'},
    'ca-replace':   {label:'Replace',   cls:'role-replace'},
    'ca-warn':      {label:'Review',    cls:'role-warn'},
    'ca-structure': {label:'Structure', cls:'role-struct'}
  };
  var role = roleMap[v.color] || {label:'Review', cls:'role-warn'};

  document.getElementById('fp-cat').innerHTML =
    '<span class="ca-badge ' + (catMap[v.cat]||'badge-total') + '" style="font-size:11px;">' + hEsc(v.cat) + '</span>';
  document.getElementById('fp-role').innerHTML =
    '<span class="role-badge ' + role.cls + '">' + role.label + '</span>';
  document.getElementById('fp-msg').textContent = v.msg;

  /* Suggestion buttons */
  var alts = getAlternatives(v);
  var btns = '';
  if (alts.length > 0) {
    btns = alts.map(function(a) {
      var cls = (a.v === '') ? 'sugg-pill remove-pill' : 'sugg-pill';
      return '<button class="' + cls + '" onclick="applyFromPopup(\'' + escJs(a.v) + '\')">' + hEsc(a.l) + '</button>';
    }).join('');
  } else {
    btns = '<span class="sugg-none">Manual review required — no automatic fix available.</span>';
  }
  document.getElementById('fp-sugg-btns').innerHTML = btns;
  document.getElementById('fp-custom-input').value = (v.fix !== undefined ? v.fix : '');

  /* Position near the clicked element */
  var rect = el.getBoundingClientRect();
  popup.style.display = 'block';
  var pw = 340, ph = 280;
  var top = rect.bottom + 8;
  var left = rect.left;
  if (left + pw > window.innerWidth - 10) left = window.innerWidth - pw - 10;
  if (left < 10) left = 10;
  if (top + ph > window.innerHeight - 10) top = rect.top - ph - 8;
  if (top < 10) top = 10;
  popup.style.top  = top  + 'px';
  popup.style.left = left + 'px';
}

function closeFixPopup() {
  document.getElementById('ca-fix-popup').style.display = 'none';
  _popupVidx = -1;
}

function applyFromPopup(value) {
  if (_popupVidx < 0) return;
  applyOneFix(_popupVidx, value);
}

function applyPopupCustom() {
  if (_popupVidx < 0) return;
  var val = document.getElementById('fp-custom-input').value;
  applyOneFix(_popupVidx, val);
}

function applyPopupDefault() {
  if (_popupVidx < 0) return;
  var v = _violations[_popupVidx];
  if (!v) return;
  var alts = getAlternatives(v);
  var rep = (alts.length > 0) ? alts[0].v : (v.fix !== undefined ? v.fix : '');
  applyOneFix(_popupVidx, rep);
}

function ignoreFromPopup() {
  if (_popupVidx < 0) return;
  ignoreFix(_popupVidx);
  closeFixPopup();
}

/* Close popup when clicking outside */
document.addEventListener('click', function(e) {
  if (!e.target.closest('#ca-fix-popup') && !e.target.closest('.ca-violation')) {
    closeFixPopup();
  }
});


/* ═══════════════════════════════════════════════════════════
   CA STATE & MAIN ACTIONS
   [FRONTEND: UI] — state management and action triggers, stays in app.js
   (runCA/rerunCA will call window.api.analyze() in Phase 5 instead of collectViolations)
   ═══════════════════════════════════════════════════════════ */
var _text = '', _violations = [], _fixed = '';
var _ignoredSet = new Set();
var _caPanelFilter = 'All';



/* ── Docked Panel: Category Filters ── */
function buildPanelFilters() {
  var filtersEl = document.getElementById('ca-panel-filters');
  if (!filtersEl) return;

  // Count by category
  var counts = { 'All': 0 };
  for (var i = 0; i < _violations.length; i++) {
    if (_ignoredSet.has(i)) continue;
    var cat = _violations[i].cat;
    counts[cat] = (counts[cat] || 0) + 1;
    counts['All']++;
  }

  var cats = ['All', 'Grammar', 'Word Usage', 'Pronouns', 'Style & Tone', 'Punctuation', 'Numbers', 'Translation', 'UI Conventions'];
  var html = '';
  for (var c = 0; c < cats.length; c++) {
    var catName = cats[c];
    var count = counts[catName] || 0;
    if (catName !== 'All' && count === 0) continue;
    var activeClass = (_caPanelFilter === catName) ? ' active' : '';
    html += '<button class="ca-filter-btn' + activeClass + '" onclick="setCAPanelFilter(\'' + catName + '\')">' +
            catName + ' (' + count + ')</button>';
  }
  filtersEl.innerHTML = html;
}

function setCAPanelFilter(cat) {
  _caPanelFilter = cat;
  buildPanelFilters();
  buildPanelCards(cat);
}

/* ── Docked Panel: Issue Cards ── */
function buildPanelCards(filterCat) {
  var listEl = document.getElementById('ca-panel-list');
  if (!listEl) return;

  var catClsMap = {
    'Grammar':'badge-grammar','Word Usage':'badge-wordusage',
    'Pronouns':'badge-pronouns','Style & Tone':'badge-style',
    'Punctuation':'badge-punctuation','Numbers':'badge-numbers',
    'Translation':'badge-translation','UI Conventions':'badge-uiconv'
  };
  var roleMap = {
    'ca-remove':  {label:'Remove',  cls:'role-remove'},
    'ca-replace': {label:'Replace', cls:'role-replace'},
    'ca-warn':    {label:'Review',  cls:'role-warn'},
    'ca-structure':{label:'Structure',cls:'role-struct'}
  };

  var html = '';
  for (var i = 0; i < _violations.length; i++) {
    var v = _violations[i];
    if (filterCat !== 'All' && v.cat !== filterCat) continue;

    var ignored = _ignoredSet.has(i);
    var ignoredClass = ignored ? ' ignored' : '';
    var role = roleMap[v.color] || {label:'Review', cls:'role-warn'};
    var catCls = catClsMap[v.cat] || 'badge-total';
    var matchText = hEsc((v.matchText || '').slice(0, 30));
    var msg = hEsc((v.msg || '').slice(0, 80));

    // Action buttons
    var actions = '';
    if (!ignored) {
      if (v.fix !== undefined) {
        actions += '<button class="btn-sm btn-green" onclick="applyOneFix(' + i + ',\'' + escJs(v.fix) + '\');event.stopPropagation();">✓ Fix</button>';
      } else {
        actions += '<button class="btn-sm" style="background:var(--accent);" onclick="showFixPopup(' + i + ',document.querySelector(\'[data-vidx=\\x22' + i + '\\x22]\'),event);event.stopPropagation();">💡</button>';
      }
      actions += '<button class="btn-sm btn-grey" onclick="ignoreFix(' + i + ');event.stopPropagation();">✗</button>';
    } else {
      actions += '<button class="btn-sm" style="background:#6c757d;color:#fff;" onclick="revertIgnore(' + i + ');event.stopPropagation();">↩ Revert</button>';
    }

    html += '<div class="ca-issue-card' + ignoredClass + '" data-vidx="' + i + '" onclick="panelCardClick(' + i + ')">' +
      '<div class="ca-issue-card-top">' +
        '<span class="ca-issue-card-match">' + matchText + '</span>' +
        '<span class="ca-issue-card-cat ca-badge ' + catCls + '">' + hEsc(v.cat) + '</span>' +
      '</div>' +
      '<div class="ca-issue-card-msg">' + msg + '</div>' +
      '<div class="ca-issue-card-actions">' + actions + '</div>' +
    '</div>';
  }

  if (!html) {
    html = '<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:13px;">No issues found.</div>';
  }
  listEl.innerHTML = html;
}

/* ── Panel card click: highlight corresponding text ── */
function panelCardClick(vidx) {
  var el = document.querySelector('#ca-annotated [data-vidx="' + vidx + '"]');
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    el.style.boxShadow = '0 0 0 3px rgba(79,70,229,.4)';
    setTimeout(function() { el.style.boxShadow = ''; }, 1500);
  }
}

function refreshCADisplay() {
  document.getElementById('ca-annotated').innerHTML = buildAnnotated(_text, _violations);
  document.getElementById('ca-badges').innerHTML    = buildBadges(_violations);
  document.getElementById('vtbody').innerHTML       = buildVTable(_violations);
  var active = _violations.filter(function(v,i){ return !_ignoredSet.has(i); }).length;
  document.getElementById('vcount').textContent = active;
  document.getElementById('vlist-toggle') && (
    document.getElementById('vlist-toggle').textContent =
      'Hide Issues (' + active + ')'
  );

  // Populate docked violations panel
  buildPanelFilters();
  buildPanelCards(_caPanelFilter);
}

function runCA() {
  var text = document.getElementById('caInput').value.trim();
  if (!text) { alert('Paste or upload content to analyze.'); return; }
  _text       = text;

  // Clear all undo/redo stacks on new analysis
  clearAllUndoStacks();

  // Use backend via Electron IPC if available, otherwise use local JS
  if (window.api && window.api.analyze) {
    window.api.analyze(text).then(function(response) {
      if (response.success) {
        _violations = response.data.violations;
      } else {
        // Fallback to local on error
        _violations = collectViolations(text);
      }
      _ignoredSet = new Set();
      _fixed      = '';
      document.getElementById('ca-fixed-section').style.display = 'none';
      document.getElementById('ca-results').style.display       = 'block';
      refreshCADisplay();
    }).catch(function() {
      // Fallback to local JS on failure
      _violations = collectViolations(text);
      _ignoredSet = new Set();
      _fixed      = '';
      document.getElementById('ca-fixed-section').style.display = 'none';
      document.getElementById('ca-results').style.display       = 'block';
      refreshCADisplay();
    });
  } else {
    _violations = collectViolations(text);
    _ignoredSet = new Set();
    _fixed      = '';
    document.getElementById('ca-fixed-section').style.display = 'none';
    document.getElementById('ca-results').style.display       = 'block';
    refreshCADisplay();
  }
}

function rerunCA() {
  // Use backend via Electron IPC if available, otherwise use local JS
  if (window.api && window.api.analyze) {
    window.api.analyze(_text).then(function(response) {
      if (response.success) {
        _violations = response.data.violations;
      } else {
        _violations = collectViolations(_text);
      }
      _ignoredSet = new Set();
      _fixed      = '';
      refreshCADisplay();
    }).catch(function() {
      _violations = collectViolations(_text);
      _ignoredSet = new Set();
      _fixed      = '';
      refreshCADisplay();
    });
  } else {
    _violations = collectViolations(_text);
    _ignoredSet = new Set();
    _fixed      = '';
    refreshCADisplay();
  }
}

function clearCA() {
  document.getElementById('caInput').value = '';
  document.getElementById('ca-results').style.display = 'none';
  _text = ''; _violations = []; _fixed = '';
  _ignoredSet = new Set();
  closeFixPopup();
}

function applyFixes() {
  if (!_text) return;
  _fixed = computeFixed(_text);
  document.getElementById('ca-fixed-output').textContent = _fixed;
  document.getElementById('ca-fixed-section').style.display = 'block';
  document.getElementById('ca-fixed-section').scrollIntoView({ behavior:'smooth', block:'nearest' });
}

function copyFixed() {
  navigator.clipboard.writeText(_fixed || document.getElementById('ca-fixed-output').innerText);
  alert('Fixed text copied to clipboard.');
}

function downloadFixed() {
  var D = docx.Document, P = docx.Paragraph, K = docx.Packer;
  var lines = (_fixed || document.getElementById('ca-fixed-output').innerText).split('\n');
  var doc = new D({ sections:[{ children: lines.map(function(l){ return new P(l); }) }] });
  K.toBlob(doc).then(function(blob){ saveAs(blob, 'fixed_content.docx'); });
}


/* ═══════════════════════════════════════════════════════════
   ZOOM CONTROL — Ctrl+Scroll Wheel
   [FRONTEND: UI] — zoom state and DOM updates, stays in app.js
   ═══════════════════════════════════════════════════════════ */
var _appZoomLevel = 100;

document.addEventListener('wheel', function(e) {
  if (!e.ctrlKey) return; // normal scroll — do nothing
  e.preventDefault();
  if (e.deltaY < 0) {
    _appZoomLevel = Math.min(_appZoomLevel + 10, 200);
  } else {
    _appZoomLevel = Math.max(_appZoomLevel - 10, 50);
  }
  // Apply zoom to the active tab's content
  document.body.style.zoom = _appZoomLevel / 100;
}, { passive: false });

/* ═══════════════════════════════════════════════════════════
   GLOBAL UNDO/REDO — Ctrl+Z / Ctrl+Y (Content Analysis tab only)
   [FRONTEND: UI] — keyboard shortcut handling, stays in app.js
   ═══════════════════════════════════════════════════════════ */
document.addEventListener('keydown', function(e) {
  // Only intercept in Content Analysis tab
  var caTab = document.getElementById('contentAnalysis');
  if (!caTab || caTab.style.display === 'none') return;

  if (e.ctrlKey && e.key === 'z' && !e.shiftKey) {
    e.preventDefault();
    caGlobalUndo();
  } else if (e.ctrlKey && e.key === 'y') {
    e.preventDefault();
    caGlobalRedo();
  }
});


/* ═══════════════════════════════════════════════════════════
   TOOLTIP (hover, not popup — suppressed when popup open)
   [FRONTEND: UI] — tooltip rendering, stays in app.js
   ═══════════════════════════════════════════════════════════ */
var _tip = document.getElementById('ca-tooltip');

document.addEventListener('mouseover', function(e) {
  if (_popupVidx >= 0) return; /* popup is open */
  var el = e.target.closest('.ca-violation');
  if (el && el.dataset.tooltip) {
    _tip.textContent = el.dataset.tooltip;
    _tip.style.display = 'block';
  }
});
document.addEventListener('mouseout', function(e) {
  if (!e.target.closest('.ca-violation')) _tip.style.display = 'none';
});
document.addEventListener('mousemove', function(e) {
  if (_tip.style.display !== 'block') return;
  var x = e.clientX + 16, y = e.clientY + 16;
  if (x + 340 > window.innerWidth)  x = e.clientX - 345;
  if (y + 100 > window.innerHeight) y = e.clientY - 85;
  _tip.style.left = x + 'px';
  _tip.style.top  = y + 'px';
});


/* ═══════════════════════════════════════════════════════════
   CA FILE UPLOAD
   [FRONTEND: UI] — file upload handling with mammoth.js, stays in app.js
   ═══════════════════════════════════════════════════════════ */
document.getElementById('caFile').addEventListener('change', function(e) {
  var file = e.target.files[0];
  if (!file) return;
  if (file.name.endsWith('.docx')) {
    var r = new FileReader();
    r.onload = function(ev) {
      mammoth.extractRawText({ arrayBuffer: ev.target.result })
        .then(function(res) { document.getElementById('caInput').value = res.value; });
    };
    r.readAsArrayBuffer(file);
  } else if (file.name.endsWith('.txt')) {
    var r2 = new FileReader();
    r2.onload = function(ev) { document.getElementById('caInput').value = ev.target.result; };
    r2.readAsText(file);
  }
});


/* ============================================================
   REWRITE & PROOFREAD  —  offline rule engine
   [BACKEND: Logic] — RW_RULES array migrates to Python (rules.py)
   ============================================================ */
var RW_RULES = [
  { type:'replace', pattern:/\bin order (?:to|for)\b/gi,        fix:'to',           msg:'in order to → to' },
  { type:'replace', pattern:/\bdue to the fact that\b/gi,       fix:'because',      msg:'due to the fact that → because' },
  { type:'replace', pattern:/\bfor the reason that\b/gi,        fix:'because',      msg:'for the reason that → because' },
  { type:'replace', pattern:/\bas a consequence of\b/gi,        fix:'because of',   msg:'as a consequence of → because of' },
  { type:'replace', pattern:/\byou have to\b/gi,                fix:'you must',     msg:'you have to → you must' },
  { type:'replace', pattern:/\byou ought to\b/gi,               fix:'you should',   msg:'you ought to → you should' },
  { type:'replace', pattern:/\bit is recommended that you\b/gi, fix:'you should',   msg:'it is recommended that you → you should' },
  { type:'replace', pattern:/\bif you want to\b/gi,             fix:'to',           msg:'if you want to → to' },
  { type:'replace', pattern:/\bto be able to\b/gi,              fix:'to',           msg:'to be able to → to' },
  { type:'remove',  pattern:/\bin some (?:cases|circumstances)\b[,]?\s*/gi,         msg:'remove: in some cases' },
  { type:'replace', pattern:/\bon the basis of\b/gi,            fix:'based on',     msg:'on the basis of → based on' },
  { type:'replace', pattern:/\bprior to\b/gi,                   fix:'before',       msg:'prior to → before' },
  { type:'replace', pattern:/\bonce\s+(you|the|a|an|it|they|we|this)\b/gi, fix:'After $1', msg:'once (temporal) → after' },
  { type:'replace', pattern:/\bvia\b/gi,                        fix:'through',      msg:'via → through' },
  { type:'replace', pattern:/\bby means of\b/gi,                fix:'using',        msg:'by means of → using' },
  { type:'replace', pattern:/\bin relation to\b/gi,             fix:'about',        msg:'in relation to → about' },
  { type:'replace', pattern:/\bwhether or not\b/gi,             fix:'whether',      msg:'whether or not → whether' },
  { type:'remove',  pattern:/\b(?:this|which) means that\b[,]?\s*/gi,              msg:'remove: this/which means that' },
  { type:'remove',  pattern:/\bthe system requires you to\b\s*/gi,                 msg:'remove: the system requires you to' },
  { type:'remove',  pattern:/\btake these steps\b[:]?\s*/gi,                       msg:'remove: take these steps' },
  { type:'replace', pattern:/\bkeep in mind(?:\s+that)?\b/gi,   fix:'Note:',        msg:'keep in mind → Note:' },
  { type:'replace', pattern:/\bat all times\b/gi,               fix:'always',       msg:'at all times → always' },
  { type:'replace', pattern:/\bsanity check\b/gi,               fix:'verification', msg:'sanity check → verification' },
  { type:'remove',  pattern:/\bback burner\b/gi,                                    msg:'remove: back burner' },
  { type:'replace', pattern:/\bballpark figure\b/gi,            fix:'estimate',     msg:'ballpark figure → estimate' },
  { type:'replace', pattern:/\bclick\s+(?:on|at)\b/gi,          fix:'click',        msg:'click on/at → click' },
  { type:'replace', pattern:/\bhit\s+(the\s+)?(?=\w)/gi,        fix:'click the ',   msg:'hit → click' },
  { type:'replace', pattern:/\b(?:login|log[\s\-]in|log[\s\-]on)\b/gi,  fix:'sign in',  msg:'login/log in → sign in' },
  { type:'replace', pattern:/\b(?:logout|log[\s\-]out|log[\s\-]off|logoff)\b/gi, fix:'sign out', msg:'logout/log out → sign out' },
  { type:'replace', pattern:/\benter\s+(the|a|an|your)\b/gi,    fix:'specify $1',   msg:'enter → specify (for text fields)' },
  { type:'replace', pattern:/\btoggle\b/gi,                     fix:'switch',       msg:'toggle → switch' },
  { type:'replace', pattern:/\b(?:grayed[\s\-]out|dimmed)\b/gi, fix:'not available',msg:'grayed out/dimmed → not available' },
  { type:'replace', pattern:/\bdialog(?!\s+box)\b/gi,           fix:'dialog box',   msg:'dialog → dialog box' },
  { type:'replace', pattern:/\bsub[\-]?menu\b/gi,               fix:'menu',         msg:'submenu → menu' },
  { type:'replace', pattern:/\bfilename\b/gi,                   fix:'file name',    msg:'filename → file name' },
  { type:'replace', pattern:/\b[Ww]eb\s+[Ss]ite\b/g,           fix:'website',      msg:'web site → website' },
  { type:'replace', pattern:/\bon[\-]premise(?!s)\b/gi,         fix:'on-premises',  msg:'on-premise → on-premises' },
  { type:'replace', pattern:/\bon[\-]line\b/gi,                 fix:'online',       msg:'on-line → online' },
  { type:'replace', pattern:/\bpopulate\b/gi,                   fix:'add',          msg:'populate → add' },
  { type:'replace', pattern:/\bexecute\b/gi,                    fix:'run',          msg:'execute → run' },
  { type:'replace', pattern:/\bleverage\b/gi,                   fix:'use',          msg:'leverage → use' },
  { type:'replace', pattern:/\butilize\b/gi,                    fix:'use',          msg:'utilize → use' },
  { type:'replace', pattern:/\bimpact\b(?!\s+(?:analysis|report|assessment))/gi, fix:'affect', msg:'impact (verb) → affect' },
  { type:'replace', pattern:/\bdesigned to\b/gi,                fix:'',             msg:'designed to → (remove)' },
  { type:'replace', pattern:/\bkill\b/gi,                       fix:'stop',         msg:'kill → stop' },
  { type:'replace', pattern:/\babort\b/gi,                      fix:'cancel',       msg:'abort → cancel' },
  { type:'replace', pattern:/\bstop\s+responding\b/gi,          fix:'not respond',  msg:'stop responding → not respond' },
  { type:'replace', pattern:/\bprogram\b/gi,                    fix:'application',  msg:'program → application' },
  { type:'replace', pattern:/\bblacklist(?:ed|ing|s)?\b/gi,     fix:'blocklist',    msg:'blacklist → blocklist' },
  { type:'replace', pattern:/\bwhitelist(?:ed|ing|s)?\b/gi,     fix:'allowlist',    msg:'whitelist → allowlist' },
  { type:'replace', pattern:/\bmaster\b(?!\s+(?:class|copy|plan|data))/gi, fix:'primary', msg:'master → primary' },
  { type:'replace', pattern:/\bslave\b/gi,                      fix:'secondary',    msg:'slave → secondary' },
  { type:'replace', pattern:/\bmanpower\b/gi,                   fix:'workforce',    msg:'manpower → workforce' },
  { type:'replace', pattern:/\bmanmade\b/gi,                    fix:'manufactured', msg:'manmade → manufactured' },
  { type:'replace', pattern:/\bman[\s\-]hours?\b/gi,            fix:'work hours',   msg:'man hours → work hours' },
  { type:'replace', pattern:/\bmankind\b/gi,                    fix:'people',       msg:'mankind → people' },
  { type:'replace', pattern:/\bchairman\b/gi,                   fix:'chair',        msg:'chairman → chair' },
  { type:'replace', pattern:/\bhe\/she\b/gi,                    fix:'they',         msg:'he/she → they' },
  { type:'replace', pattern:/\bhe or she\b/gi,                  fix:'they',         msg:'he or she → they' },
  { type:'replace', pattern:/\bdummy\b/gi,                      fix:'sample',       msg:'dummy → sample' },
  { type:'remove',  pattern:/\bplease\b[,]?\s*/gi,                                  msg:'remove: please' },
  { type:'remove',  pattern:/\bkindly\b[,]?\s*/gi,                                  msg:'remove: kindly' },
  { type:'remove',  pattern:/\bvery\b\s*/gi,                                        msg:'remove: very' },
  { type:'remove',  pattern:/\breally\b\s*/gi,                                      msg:'remove: really' },
  { type:'remove',  pattern:/\bquite\b\s*/gi,                                       msg:'remove: quite' },
  { type:'remove',  pattern:/\bsimply\b\s*/gi,                                      msg:'remove: simply' },
  { type:'remove',  pattern:/\beasily\b\s*/gi,                                      msg:'remove: easily' },
  { type:'remove',  pattern:/\bquickly\b\s*/gi,                                     msg:'remove: quickly' },
  { type:'remove',  pattern:/\bobviously\b[,]?\s*/gi,                               msg:'remove: obviously' },
  { type:'remove',  pattern:/\bactually\b[,]?\s*/gi,                                msg:'remove: actually' },
  { type:'remove',  pattern:/\bjust\b\s*/gi,                                        msg:'remove: just' },
  { type:'replace', pattern:/\bi\.e\.,?\s*/gi,                  fix:'that is, ',    msg:'i.e. → that is' },
  { type:'replace', pattern:/\be\.g\.,?\s*/gi,                  fix:'for example, ',msg:'e.g. → for example' },
  { type:'replace', pattern:/\bdefault(?:s|ed|ing)?\s+to\b/gi,  fix:'sets the default to', msg:'default (verb) → sets the default to' },
  { type:'replace', pattern:/;\s*/g,                            fix:'. ',           msg:'semicolon → period' },
  { type:'replace', pattern:/\bcan't\b/gi,    fix:"cannot",     msg:"can't → cannot" },
  { type:'replace', pattern:/\bwon't\b/gi,    fix:"do not",     msg:"won't → do not" },
  { type:'replace', pattern:/\bdon't\b/gi,    fix:"do not",     msg:"don't → do not" },
  { type:'replace', pattern:/\bdoesn't\b/gi,  fix:"does not",   msg:"doesn't → does not" },
  { type:'replace', pattern:/\bdidn't\b/gi,   fix:"did not",    msg:"didn't → did not" },
  { type:'replace', pattern:/\bisn't\b/gi,    fix:"is not",     msg:"isn't → is not" },
  { type:'replace', pattern:/\baren't\b/gi,   fix:"are not",    msg:"aren't → are not" },
  { type:'replace', pattern:/\bwasn't\b/gi,   fix:"was not",    msg:"wasn't → was not" },
  { type:'replace', pattern:/\bweren't\b/gi,  fix:"were not",   msg:"weren't → were not" },
  { type:'replace', pattern:/\bhasn't\b/gi,   fix:"has not",    msg:"hasn't → has not" },
  { type:'replace', pattern:/\bhaven't\b/gi,  fix:"have not",   msg:"haven't → have not" },
  { type:'replace', pattern:/\bhadn't\b/gi,   fix:"had not",    msg:"hadn't → had not" },
  { type:'replace', pattern:/\bit's\b/gi,     fix:"it is",      msg:"it's → it is" },
  { type:'replace', pattern:/\bthat's\b/gi,   fix:"that is",    msg:"that's → that is" },
  { type:'replace', pattern:/\bthere's\b/gi,  fix:"there is",   msg:"there's → there is" },
  { type:'replace', pattern:/\bthey're\b/gi,  fix:"they are",   msg:"they're → they are" },
  { type:'replace', pattern:/\bwe're\b/gi,    fix:"we are",     msg:"we're → we are" },
  { type:'replace', pattern:/\byou're\b/gi,   fix:"you are",    msg:"you're → you are" },
  { type:'replace', pattern:/\bwe've\b/gi,    fix:"we have",    msg:"we've → we have" },
  { type:'replace', pattern:/\bthey've\b/gi,  fix:"they have",  msg:"they've → they have" },
  { type:'replace', pattern:/\byou've\b/gi,   fix:"you have",   msg:"you've → you have" },
  { type:'replace', pattern:/\bI'm\b/g,       fix:"I am",       msg:"I'm → I am" },
  { type:'replace', pattern:/\bwouldn't\b/gi, fix:"do not",     msg:"wouldn't → do not" },
  { type:'replace', pattern:/\bcouldn't\b/gi, fix:"cannot",     msg:"couldn't → cannot" },
  { type:'replace', pattern:/\bshouldn't\b/gi,fix:"must not",   msg:"shouldn't → must not" },
  { type:'replace', pattern:/\bwill\s+be\s+able\s+to\b/gi,     fix:'can',          msg:'will be able to → can' },
  { type:'replace', pattern:/\bwill\s+not\b/gi,                 fix:'does not',     msg:'will not → does not' },
  { type:'replace', pattern:/\bcould\b\s/gi,                    fix:'can ',         msg:'could → can' },
  { type:'replace', pattern:/\b(?:may|might)\s+be\b/gi,         fix:'is',           msg:'may/might be → is' },
  { type:'replace', pattern:/\bright\b(?!\s*(?:click|arrow|side|panel|column|margin|hand))/gi, fix:'correct', msg:'right → correct' },
  { type:'replace', pattern:/\bwrong\b/gi,                      fix:'incorrect',    msg:'wrong → incorrect' },
  { type:'replace', pattern:/\band\/or\b/gi,                    fix:'and',          msg:'and/or → and' },
  { type:'replace', pattern:/\s*[\u2013\u2014]\s*/g,            fix:', ',           msg:'em/en dash → comma' },
  { type:'replace', pattern:/[ \t]{2,}/g,                       fix:' ',            msg:'double space → single space' },
  { type:'replace', pattern:/\s+([,.!?:;])/g,                   fix:'$1',           msg:'space before punctuation removed' }
];

/* [BACKEND: Logic] — UI element bolding logic migrates to Python (utils.py)
   Functions to extract: boldUIElements */
var UI_CONTEXT_WORDS = [
  'field','fields','tab','tabs','button','buttons',
  'screen','screens','window','windows','box','boxes',
  'panel','panels','page','pages','section','sections',
  'list','lists','menu','menus','icon','icons',
  'link','links','option','options','column','columns',
  'dialog box','check box','check boxes','drop-down','drop-down list'
];

function boldUIElements(text) {
  var result = text;
  UI_CONTEXT_WORDS.forEach(function(ctx) {
    var esc = ctx.replace(/ /g,'\\s+');
    var rx = new RegExp(
      '(?<!<strong>)(?:<\\/strong>\\s+)?' +
      '([A-Z][A-Za-z0-9]*(?:\\s+[A-Z][A-Za-z0-9]*)?)' +
      '(\\s+' + esc + '\\b)', 'g'
    );
    result = result.replace(rx, function(m, label, suffix) {
      if (m.indexOf('<strong>') !== -1) return m;
      return '<strong>' + label + '</strong>' + suffix;
    });
  });
  return result;
}

/* [BACKEND: Logic] — sentence length checking migrates to Python (rules.py)
   Functions to extract: checkSentenceLength */
function checkSentenceLength(text) {
  var violations = [];
  var rx = /[^.!?\n]+[.!?]/g, m;
  while ((m = rx.exec(text)) !== null) {
    var words = m[0].trim().split(/\s+/).filter(Boolean);
    if (words.length > 25) {
      violations.push({
        original: m[0].trim(),
        note: 'Sentence has ' + words.length + ' words. Split into ≤25 words.'
      });
    }
  }
  return violations;
}

/* [BACKEND: Logic] — rewrite rule application migrates to Python (analyzer.py)
   Functions to extract: applyRWRules
   Calls boldUIElements and checkSentenceLength (also backend) */
function applyRWRules(text) {
  var out = text, changes = [];
  RW_RULES.forEach(function(rule) {
    var rx = new RegExp(rule.pattern.source, rule.pattern.flags);
    out = out.replace(rx, function(m) {
      if (rule.type === 'remove') {
        changes.push({ from: m.trim(), to: '(removed)', msg: rule.msg });
        return '';
      } else {
        var rep = rule.fix;
        var args = Array.from(arguments);
        for (var i = 1; i < args.length - 2; i++) {
          if (args[i] !== undefined) rep = rep.replace('$' + i, args[i]);
        }
        if (m.trim().toLowerCase() !== rep.trim().toLowerCase()) {
          changes.push({ from: m.trim(), to: rep.trim(), msg: rule.msg });
        }
        return rep;
      }
    });
  });
  out = out.replace(/[ \t]{2,}/g,' ').replace(/\s+([,.!?])/g,'$1').trim();
  out = boldUIElements(out);
  var sentWarnings = checkSentenceLength(out.replace(/<[^>]+>/g,''));
  return { rewritten: out, changes: changes, sentWarnings: sentWarnings };
}

/* [FRONTEND: UI] — diff rendering helper, stays in app.js */
function buildSideBySide(origText, rewrittenHtml) {
  var rewrittenText = rewrittenHtml.replace(/<[^>]+>/g,'');
  var oWords = origText.split(/(\s+)/);
  var rWords = rewrittenText.split(/(\s+)/);
  var oSet = {}, rSet = {};
  oWords.forEach(function(w){ if(w.trim()) oSet[w.toLowerCase()] = true; });
  rWords.forEach(function(w){ if(w.trim()) rSet[w.toLowerCase()] = true; });
  var oHtml = oWords.map(function(w){
    if (/^\s+$/.test(w)) return w;
    if (!rSet[w.toLowerCase()]) return '<span class="diff-removed">' + hEsc(w) + '</span>';
    return hEsc(w);
  }).join('');
  var rPlainWords = rewrittenText.split(/(\s+)/);
  var rMarked = rPlainWords.map(function(w){
    if (/^\s+$/.test(w)) return w;
    if (!oSet[w.toLowerCase()]) return '<span class="diff-added">' + hEsc(w) + '</span>';
    return hEsc(w);
  }).join('');
  return { orig: oHtml, rewr: rMarked };
}

/* [FRONTEND: UI] — rewrite action triggers and result rendering, stays in app.js
   (runRewrite/doRewrite will call window.api.rewrite() in Phase 5 instead of applyRWRules) */
var _rwOrig = '', _rwResult = '';

function runRewrite() {
  var text = document.getElementById('rwInput').value.trim();
  if (!text) { alert('Paste or upload content to rewrite.'); return; }
  _rwOrig = text;

  // Use backend via Electron IPC if available, otherwise use local JS
  if (window.api && window.api.rewrite) {
    window.api.rewrite(text).then(function(response) {
      if (response.success) {
        doRewriteWithResult(text, response.data);
      } else {
        doRewrite(text);
      }
    }).catch(function() {
      doRewrite(text);
    });
  } else {
    doRewrite(text);
  }
}

function doRewriteWithResult(text, result) {
  _rwResult = result;
  document.getElementById('rw-result-box').innerHTML = result.rewritten;
  var changeCount = result.changes.length;
  var summaryEl = document.getElementById('rw-change-summary');
  summaryEl.textContent = changeCount + ' change' + (changeCount !== 1 ? 's' : '') + ' applied.';
  if (result.sentenceWarnings && result.sentenceWarnings.length) {
    summaryEl.textContent += '  ' + result.sentenceWarnings.length + ' sentence(s) exceed 25 words \u2014 manual split needed.';
  }
  var diff = buildSideBySide(text, result.rewritten);
  document.getElementById('rw-original').innerHTML  = diff.orig;
  document.getElementById('rw-rewritten').innerHTML = diff.rewr;
  var logHtml = result.changes.map(function(c,i){
    return '<tr><td>' + (i+1) + '</td>' +
      '<td><span class="diff-removed">' + hEsc(c.from) + '</span></td>' +
      '<td><span class="diff-added">'   + hEsc(c.to)   + '</span></td>' +
      '<td style="color:#555;font-size:12px;">' + hEsc(c.msg) + '</td></tr>';
  }).join('');
  document.getElementById('rw-log-body').innerHTML = logHtml ||
    '<tr><td colspan="4" style="color:#888;">No automatic changes. Review manually.</td></tr>';
  document.getElementById('rw-log-count').textContent = changeCount;
  var warnEl = document.getElementById('rw-sent-warnings');
  if (result.sentenceWarnings && result.sentenceWarnings.length) {
    var warnHtml = '<strong>Sentences exceeding 25 words (split manually):</strong><ul style="margin:6px 0 0 18px;">' +
      result.sentenceWarnings.map(function(w){ return '<li style="font-size:13px;margin-bottom:4px;">' + hEsc(w.original.slice(0,120)) + '&hellip; <em style="color:#e67e22;">(' + w.note + ')</em></li>'; }).join('') +
      '</ul>';
    warnEl.innerHTML = warnHtml;
    warnEl.style.display = 'block';
  } else {
    warnEl.style.display = 'none';
  }
  document.getElementById('rw-results').style.display = 'block';
  document.getElementById('rw-log-list').classList.remove('open');
  document.getElementById('rw-log-toggle').textContent = 'Show change log (' + changeCount + ')';
}

function doRewrite(text) {
  var result = applyRWRules(text);
  _rwResult = result;
  document.getElementById('rw-result-box').innerHTML = result.rewritten;
  var changeCount = result.changes.length;
  var summaryEl = document.getElementById('rw-change-summary');
  summaryEl.textContent = changeCount + ' change' + (changeCount !== 1 ? 's' : '') + ' applied.';
  if (result.sentWarnings.length) {
    summaryEl.textContent += '  ' + result.sentWarnings.length + ' sentence(s) exceed 25 words — manual split needed.';
  }
  var diff = buildSideBySide(text, result.rewritten);
  document.getElementById('rw-original').innerHTML  = diff.orig;
  document.getElementById('rw-rewritten').innerHTML = diff.rewr;
  var logHtml = result.changes.map(function(c,i){
    return '<tr><td>' + (i+1) + '</td>' +
      '<td><span class="diff-removed">' + hEsc(c.from) + '</span></td>' +
      '<td><span class="diff-added">'   + hEsc(c.to)   + '</span></td>' +
      '<td style="color:#555;font-size:12px;">' + hEsc(c.msg) + '</td></tr>';
  }).join('');
  document.getElementById('rw-log-body').innerHTML = logHtml ||
    '<tr><td colspan="4" style="color:#888;">No automatic changes. Review manually.</td></tr>';
  document.getElementById('rw-log-count').textContent = changeCount;
  var warnEl = document.getElementById('rw-sent-warnings');
  if (result.sentWarnings.length) {
    var warnHtml = '<strong>Sentences exceeding 25 words (split manually):</strong><ul style="margin:6px 0 0 18px;">' +
      result.sentWarnings.map(function(w){ return '<li style="font-size:13px;margin-bottom:4px;">' + hEsc(w.original.slice(0,120)) + '&hellip; <em style="color:#e67e22;">(' + w.note + ')</em></li>'; }).join('') +
      '</ul>';
    warnEl.innerHTML = warnHtml;
    warnEl.style.display = 'block';
  } else {
    warnEl.style.display = 'none';
  }
  document.getElementById('rw-results').style.display = 'block';
  document.getElementById('rw-log-list').classList.remove('open');
  document.getElementById('rw-log-toggle').textContent = 'Show change log (' + changeCount + ')';
}

function clearRewrite() {
  document.getElementById('rwInput').value = '';
  document.getElementById('rw-results').style.display = 'none';
  _rwOrig = ''; _rwResult = null;
}
function copyRwResult() {
  var text = document.getElementById('rw-result-box').innerText;
  navigator.clipboard.writeText(text).then(function(){
    alert('Result copied to clipboard.');
  }).catch(function(){ alert('Copy failed. Select and copy manually.'); });
}
function downloadRwWord() {
  var D = docx.Document, P = docx.Paragraph, K = docx.Packer;
  var lines = document.getElementById('rw-result-box').innerText.split('\n');
  var doc = new D({ sections:[{ children: lines.map(function(l){ return new P(l); }) }] });
  K.toBlob(doc).then(function(blob){ saveAs(blob,'rewritten_content.docx'); });
}
function toggleRwLog() {
  var el = document.getElementById('rw-log-list');
  var open = el.classList.toggle('open');
  document.getElementById('rw-log-toggle').textContent =
    (open ? 'Hide' : 'Show') + ' change log (' + (_rwResult ? _rwResult.changes.length : 0) + ')';
}

/* [FRONTEND: UI] — rewrite file upload handling with mammoth.js, stays in app.js */
var _rwFileEl = document.getElementById('rwFile');
if (_rwFileEl) {
  _rwFileEl.addEventListener('change', function(e) {
    var file = e.target.files[0];
    if (!file) return;
    if (file.name.endsWith('.docx')) {
      var r = new FileReader();
      r.onload = function(ev) {
        mammoth.extractRawText({ arrayBuffer: ev.target.result })
          .then(function(res){ document.getElementById('rwInput').value = res.value; });
      };
      r.readAsArrayBuffer(file);
    } else if (file.name.endsWith('.txt')) {
      var r2 = new FileReader();
      r2.onload = function(ev){ document.getElementById('rwInput').value = ev.target.result; };
      r2.readAsText(file);
    }
  });
}

/* ============================================================
   WRITE TAB — lightweight offline Word processor
   [FRONTEND: UI] — entire Write Editor stays in app.js
   All functions below are DOM/editor interactions: formatting,
   file I/O, find/replace, word count, table insertion, etc.
   ============================================================ */

/* ── execCommand wrapper ── */
function wrCmd(cmd, val) {
  document.getElementById('wr-page').focus();
  document.execCommand(cmd, false, val || null);
  wrUpdateToolbarState();
  wrUpdate();
}

/* ── Font size via fontSize + span workaround ── */
function wrSetSize(pt) {
  document.getElementById('wr-page').focus();
  /* Map pt to legacy fontSize 1-7, then override with style */
  document.execCommand('fontSize', false, '4');
  var spans = document.getElementById('wr-page').querySelectorAll('font[size="4"]');
  spans.forEach(function(s){ s.removeAttribute('size'); s.style.fontSize = pt + 'pt'; });
  wrUpdate();
}

/* ── Apply block style (heading / paragraph) ── */
function wrApplyStyle(tag) {
  document.getElementById('wr-page').focus();
  document.execCommand('formatBlock', false, '<' + tag + '>');
  wrUpdate();
}

/* ── Update word/char/para counts ── */
var _titleUpdateTimer = null;
function wrUpdate() {
  var page = document.getElementById('wr-page');
  var raw  = page.innerText || '';
  var words = raw.trim() === '' ? 0 : raw.trim().split(/\s+/).filter(Boolean).length;
  var chars = raw.replace(/\n/g,'').length;
  var paras = page.querySelectorAll('p,h1,h2,h3,h4,h5,li').length;
  document.getElementById('wr-wc').textContent = words;
  document.getElementById('wr-cc').textContent = chars;
  document.getElementById('wr-pc').textContent = paras;

  // Debounced title bar update (500ms)
  clearTimeout(_titleUpdateTimer);
  _titleUpdateTimer = setTimeout(updateTitleBar, 500);
}

/* ── Title bar display ── */

/**
 * Extracts the document title from the first heading in the editor.
 * Looks for h1–h4 in #wr-page and returns its text content,
 * truncated to 60 characters with ellipsis if needed.
 * @returns {string} Title text or empty string
 */
function extractDocumentTitle() {
  var page = document.getElementById('wr-page');
  if (!page) return '';
  var heading = page.querySelector('h1, h2, h3, h4');
  if (!heading) return '';
  var text = (heading.textContent || heading.innerText || '').trim();
  if (!text) return '';
  if (text.length > 60) text = text.substring(0, 60) + '\u2026';
  return text;
}

/**
 * Updates the document title bar using the extracted title.
 * Format: "My Document — Documentation Tool" or just "Documentation Tool" if no heading.
 * Also sends the title via IPC if available (Electron environment).
 */
function updateTitleBar() {
  var title = extractDocumentTitle();
  var appName = 'Documentation Tool';
  var fullTitle = title ? title + ' \u2014 ' + appName : appName;
  document.title = fullTitle;
  // Also try IPC if available
  if (window.api && window.api.setTitle) {
    window.api.setTitle(fullTitle);
  }
}

/* ── Update toolbar active states ── */
function wrUpdateToolbarState() {
  var cmds = ['bold','italic','underline','strikeThrough','justifyLeft','justifyCenter','justifyRight','justifyFull'];
  var ids  = ['btn-bold','btn-italic','btn-underline','btn-strike','btn-alignleft','btn-aligncenter','btn-alignright','btn-alignjustify'];
  cmds.forEach(function(cmd, i) {
    var el = document.getElementById(ids[i]);
    if (el) {
      try { el.classList.toggle('active', document.queryCommandState(cmd)); } catch(e){}
    }
  });
  /* Sync paragraph style select */
  try {
    var block = document.queryCommandValue('formatBlock').toLowerCase().replace(/[<>]/g,'');
    var styleMap = { p:'p', h1:'h1', h2:'h2', h3:'h3', h4:'h4', pre:'pre' };
    var sel = document.getElementById('wr-style');
    if (sel && styleMap[block]) sel.value = styleMap[block];
  } catch(e){}
}

/* ── Tab key → indent in editor ── */
function wrKeyDown(e) {
  if (e.key === 'Tab') {
    e.preventDefault();
    document.execCommand('insertHTML', false, '&nbsp;&nbsp;&nbsp;&nbsp;');
  }
  /* Ctrl+B/I/U handled natively by execCommand */
}

/* ── New document ── */
function wrNew() {
  if ((document.getElementById('wr-page').innerText || '').trim().length > 20) {
    if (!confirm('Start a new document? Unsaved changes will be lost.')) return;
  }
  document.getElementById('wr-page').innerHTML = '<p><br></p>';

  // Reset comment state for new document
  _wrComments = [];
  _wrCommentId = 0;
  _wrPendingRange = null;
  _wrPopoverOpen = false;
  wrHideCommentPopover();
  try {
    localStorage.removeItem('wr-comments-data');
  } catch (e) {
    console.warn('[Comments] Could not clear localStorage:', e.message);
  }
  wrRenderComments();

  wrUpdate();
  updateTitleBar();
}

/* ── Open file ── */
function wrOpen() { document.getElementById('wr-open-file').click(); }
function wrFileOpened(inp) {
  var file = inp.files[0];
  if (!file) return;
  if (file.name.endsWith('.docx')) {
    var r = new FileReader();
    r.onload = function(ev) {
      mammoth.convertToHtml({ arrayBuffer: ev.target.result })
        .then(function(res) {
          document.getElementById('wr-page').innerHTML = res.value || '<p><br></p>';
          wrUpdate();
        });
    };
    r.readAsArrayBuffer(file);
  } else {
    var r2 = new FileReader();
    r2.onload = function(ev) {
      var lines = (ev.target.result || '').split('\n');
      document.getElementById('wr-page').innerHTML =
        lines.map(function(l){ return '<p>' + hEsc(l) + '</p>'; }).join('') || '<p><br></p>';
      wrUpdate();
    };
    r2.readAsText(file);
  }
  inp.value = '';
}

/* ── Save as .docx ── */
function wrSaveDocx() {
  var D = docx.Document, P = docx.Paragraph, R = docx.TextRun, K = docx.Packer,
      H1 = docx.HeadingLevel;
  var page = document.getElementById('wr-page');
  var children = [];

  /* Walk top-level nodes and convert to docx paragraphs */
  Array.from(page.childNodes).forEach(function(node) {
    if (node.nodeType === 3) { /* text node */
      if (node.textContent.trim()) children.push(new P({ children:[new R(node.textContent)] }));
      return;
    }
    var tag = (node.tagName || '').toLowerCase();
    var txt = node.innerText || node.textContent || '';
    if (tag === 'h1') { children.push(new P({ heading: H1.HEADING_1, children:[new R({text:txt,bold:true})] })); }
    else if (tag === 'h2') { children.push(new P({ heading: H1.HEADING_2, children:[new R({text:txt,bold:true})] })); }
    else if (tag === 'h3') { children.push(new P({ heading: H1.HEADING_3, children:[new R({text:txt,bold:true})] })); }
    else if (tag === 'h4') { children.push(new P({ heading: H1.HEADING_4, children:[new R({text:txt,bold:true})] })); }
    else if (tag === 'ul' || tag === 'ol') {
      Array.from(node.querySelectorAll('li')).forEach(function(li) {
        children.push(new P({ bullet:{level:0}, children:[new R(li.innerText||'')] }));
      });
    }
    else if (tag === 'table') {
      /* Flatten table rows as tab-separated lines */
      Array.from(node.querySelectorAll('tr')).forEach(function(tr) {
        var cells = Array.from(tr.querySelectorAll('td,th')).map(function(c){ return c.innerText||''; });
        children.push(new P({ children:[new R(cells.join('\t'))] }));
      });
    }
    else {
      /* p / div / span / pre */
      if (txt.trim() || tag === 'p') {
        children.push(new P({ children:[new R(txt)] }));
      }
    }
  });

  if (!children.length) children.push(new P({ children:[new R('')] }));

  var doc = new D({ sections:[{ children: children }] });
  K.toBlob(doc).then(function(blob){ saveAs(blob, deriveFilename('.docx')); });

  var msg = document.getElementById('wr-saved-msg');
  msg.style.display = 'inline';
  setTimeout(function(){ msg.style.display = 'none'; }, 2000);
}

/* ── Save as .txt ── */
function wrSaveTxt() {
  var txt = document.getElementById('wr-page').innerText || '';
  var blob = new Blob([txt], { type: 'text/plain' });
  saveAs(blob, deriveFilename('.txt'));
}

/* ── Print ── */
function wrPrint() { window.print(); }

/* ── Find & Replace ── */
var _wrFindResults = [], _wrFindIdx = 0;

function wrToggleFindBar() {
  var bar = document.getElementById('wr-findbar');
  var visible = bar.style.display === 'flex';
  bar.style.display = visible ? 'none' : 'flex';
  if (!visible) document.getElementById('wr-find-input').focus();
}
function wrCloseFindBar() {
  document.getElementById('wr-findbar').style.display = 'none';
  document.getElementById('wr-find-msg').textContent = '';
}
function wrFindNext() {
  var term = document.getElementById('wr-find-input').value;
  if (!term) return;
  var page = document.getElementById('wr-page');
  page.focus();
  var found = window.find(term, false, false, true, false, false, false);
  document.getElementById('wr-find-msg').textContent = found ? '' : 'Not found.';
}
function wrReplaceOne() {
  var find = document.getElementById('wr-find-input').value;
  var rep  = document.getElementById('wr-replace-input').value;
  if (!find) return;
  var page = document.getElementById('wr-page');
  page.focus();
  var found = window.find(find, false, false, true, false, false, false);
  if (found) { document.execCommand('insertText', false, rep); wrUpdate(); }
  else document.getElementById('wr-find-msg').textContent = 'Not found.';
}
function wrReplaceAll() {
  var find = document.getElementById('wr-find-input').value;
  var rep  = document.getElementById('wr-replace-input').value;
  if (!find) return;
  var page = document.getElementById('wr-page');
  var html = page.innerHTML;
  var esc  = find.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  var rx   = new RegExp(esc, 'gi');
  var count = (html.match(rx) || []).length;
  page.innerHTML = html.replace(rx, rep);
  document.getElementById('wr-find-msg').textContent = count + ' replacement(s) made.';
  wrUpdate();
}

/* ── Insert Table ── */
function wrInsertTable() {
  document.getElementById('wr-table-overlay').style.display = 'block';
  document.getElementById('wr-table-dialog').style.display = 'block';
}
function wrCloseTableDialog() {
  document.getElementById('wr-table-overlay').style.display = 'none';
  document.getElementById('wr-table-dialog').style.display = 'none';
}
function wrDoInsertTable() {
  var rows = parseInt(document.getElementById('wr-tbl-rows').value) || 3;
  var cols = parseInt(document.getElementById('wr-tbl-cols').value) || 3;
  var html = '<table><thead><tr>' +
    Array(cols).fill(0).map(function(_,i){ return '<th>Column ' + (i+1) + '</th>'; }).join('') +
    '</tr></thead><tbody>';
  for (var r = 0; r < rows - 1; r++) {
    html += '<tr>' + Array(cols).fill('<td><br></td>').join('') + '</tr>';
  }
  html += '</tbody></table><p><br></p>';
  document.getElementById('wr-page').focus();
  document.execCommand('insertHTML', false, html);
  wrCloseTableDialog();
  wrUpdate();
}

/* ── Insert Horizontal Rule ── */
function wrInsertHR() {
  document.getElementById('wr-page').focus();
  document.execCommand('insertHTML', false, '<hr><p><br></p>');
  wrUpdate();
}

/* ── Insert Link ── */
function wrInsertLink() {
  var url = prompt('Enter URL:', 'https://');
  if (!url) return;
  document.getElementById('wr-page').focus();
  document.execCommand('createLink', false, url);
  wrUpdate();
}

/* ── Send editor content to Content Analysis tab ── */
function wrSendToAnalysis() {
  var page = document.getElementById('wr-page');
  var text = (page.innerText || '').trim();
  if (!text) { alert('Editor is empty. Write or paste content first.'); return; }
  var caInput = document.getElementById('caInput');
  if (caInput.value.trim() && !confirm('Content Analysis already has text. Replace it?')) return;
  caInput.value = text;
  // Switch to Content Analysis tab
  var caTab = document.querySelector('.tab[onclick*="contentAnalysis"]');
  if (caTab) caTab.click();
}

/* ── Send Content Analysis text to Doc to DITA tab ── */
function caSendToDita() {
  // Priority: fixed text > current working text (_text with applied fixes) > raw input
  var text = '';
  if (_fixed) {
    text = _fixed;
  } else if (_text) {
    text = _text;
  } else {
    text = document.getElementById('caInput').value.trim();
  }
  if (!text) { alert('No content to send. Run analysis or apply fixes first.'); return; }
  var ditaInput = document.getElementById('docInput');
  if (ditaInput.value.trim() && !confirm('Doc to DITA already has text. Replace it?')) return;
  ditaInput.value = text;
  var ditaTab = document.querySelector('.tab[onclick*="converter"]');
  if (ditaTab) ditaTab.click();
}

/* ── Copy Content Analysis results to clipboard ── */
function caCopyResults() {
  var text = _fixed || _text || document.getElementById('caInput').value.trim();
  if (!text) { alert('No content to copy.'); return; }
  navigator.clipboard.writeText(text).then(function() {
    alert('Results copied to clipboard.');
  }).catch(function() { alert('Copy failed. Select and copy manually.'); });
}

/* ── Download Content Analysis results as .txt ── */
function caDownloadResults() {
  var original = document.getElementById('caInput').value.trim();
  if (!original && !_text) { alert('No content to download.'); return; }

  var lines = [];
  lines.push('=== CONTENT ANALYSIS RESULTS ===');
  lines.push('');
  lines.push('--- ORIGINAL TEXT ---');
  lines.push(original || _text);
  lines.push('');

  // Violations summary
  if (_violations && _violations.length) {
    lines.push('--- VIOLATIONS SUMMARY ---');
    lines.push('Total issues: ' + _violations.length);
    var cats = {};
    _violations.forEach(function(v) { cats[v.cat] = (cats[v.cat] || 0) + 1; });
    Object.keys(cats).forEach(function(c) { lines.push('  ' + c + ': ' + cats[c]); });
    lines.push('');
    lines.push('--- ISSUES ---');
    _violations.forEach(function(v, i) {
      lines.push((i+1) + '. [' + v.cat + '] "' + (v.matchText || '').slice(0,40) + '" — ' + v.msg);
    });
    lines.push('');
  }

  // Fixed text
  if (_fixed) {
    lines.push('--- FIXED TEXT ---');
    lines.push(_fixed);
    lines.push('');
  } else if (_text && _text !== original) {
    lines.push('--- CURRENT TEXT (with applied fixes) ---');
    lines.push(_text);
    lines.push('');
  }

  var blob = new Blob([lines.join('\n')], { type: 'text/plain' });
  saveAs(blob, 'content-analysis-results.txt');
}

/* ── Keyboard shortcut: Ctrl+S → save docx ── */
document.addEventListener('keydown', function(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    var activeTab = document.getElementById('rewrite');
    if (activeTab && activeTab.style.display !== 'none') {
      e.preventDefault();
      wrSaveDocx();
    }
  }
  if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
    var activeTab2 = document.getElementById('rewrite');
    if (activeTab2 && activeTab2.style.display !== 'none') {
      e.preventDefault();
      wrToggleFindBar();
    }
  }
});

/* ── Init on load ── */
(function() {
  function wrInitOnLoad() {
    wrUpdate();
    wrLoadComments();
    updateTitleBar();

    // Focus the editor canvas after a short delay to ensure DOM is ready (Req 1.3)
    setTimeout(function() {
      var editor = document.getElementById('wr-page');
      if (editor) editor.focus();
    }, 50);

  // Clear undo/redo stacks when user manually edits the CA text input (Req 4.8)
  var caInputEl = document.getElementById('caInput');
  if (caInputEl) {
    caInputEl.addEventListener('input', function() {
      clearAllUndoStacks();
    });
  }

  // Sync manual edits in annotated area back to _text and undo stack
  var caAnnotated = document.getElementById('ca-annotated');
  if (caAnnotated) {
    caAnnotated.addEventListener('input', function() {
      var oldText = _text;
      // Get plain text from the contenteditable div
      _text = caAnnotated.innerText || caAnnotated.textContent || '';
      document.getElementById('caInput').value = _text;
      // Record the edit in undo stack (simplified: store full text swap)
      if (oldText !== _text) {
        _caGlobalUndoStack.push({ violationIndex: -1, originalText: oldText, replacementText: _text, offset: 0, isFullTextSwap: true });
        _caGlobalRedoStack = [];
      }
    });
  }

  // Listen for backend crash notifications (Electron only)
  if (window.api && window.api.onBackendError) {
    window.api.onBackendError(function(data) {
      alert('Backend Error: ' + (data.message || 'Backend process is unavailable. Please restart the application.'));
    });
  }

  /* ── Hover interaction: highlight → card (Req 2.3) ── */
  var wrPage = document.getElementById('wr-page');
  if (wrPage) {
    wrPage.addEventListener('mouseover', function(e) {
      var highlight = e.target.closest('.wr-comment-highlight');
      if (!highlight) return;
      var commentId = highlight.getAttribute('data-comment-id');
      if (!commentId) return;
      var card = document.querySelector('.wr-comment-card[data-comment-id="' + commentId + '"]');
      if (card) card.classList.add('hovered');
    });
    wrPage.addEventListener('mouseout', function(e) {
      var highlight = e.target.closest('.wr-comment-highlight');
      if (!highlight) return;
      // Only remove if we're actually leaving the highlight (not entering a child)
      var related = e.relatedTarget;
      if (related && highlight.contains(related)) return;
      var commentId = highlight.getAttribute('data-comment-id');
      if (!commentId) return;
      var card = document.querySelector('.wr-comment-card[data-comment-id="' + commentId + '"]');
      if (card) card.classList.remove('hovered');
    });
  }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wrInitOnLoad);
  } else {
    wrInitOnLoad();
  }
})();


/* ============================================================
   WRITE EDITOR — COMMENTS FEATURE
   Lightweight in-memory annotation system.
   ============================================================ */

var _wrComments = []; // { id, text, snippet, range serialization }
var _wrCommentId = 0;
var _wrPendingRange = null; // Holds the selection range while the popover is open
var _wrPopoverOpen = false; // Guard flag to track popover open state

/* ── Timestamp helper: returns "MMM D, YYYY HH:MM" format ── */
function _wrTimestamp() {
  var now = new Date();
  var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  var month = months[now.getMonth()];
  var day = now.getDate();
  var year = now.getFullYear();
  var hours = String(now.getHours()).padStart(2, '0');
  var minutes = String(now.getMinutes()).padStart(2, '0');
  return month + ' ' + day + ', ' + year + ' ' + hours + ':' + minutes;
}

/* ── Show/hide floating "Add Comment" button — REMOVED ── */
/* Comments are now triggered from the toolbar button only. */
function wrCheckSelection() {
  /* no-op: kept for compatibility with onmouseup handler */
}

/* ── Comment Popover: Show ── */
function wrShowCommentPopover(range) {
  var popover = document.getElementById('wr-comment-popover');
  var canvas = document.getElementById('wr-canvas');
  if (!popover || !canvas) return;

  // If popover is already open, close it first to reset state cleanly
  if (_wrPopoverOpen) {
    wrHideCommentPopover();
  }

  // Store the range for later use when submitting
  _wrPendingRange = range;
  _wrPopoverOpen = true;

  // Get the bounding rect of the selection range
  var rangeRect = range.getBoundingClientRect();
  var canvasRect = canvas.getBoundingClientRect();

  // Position the popover below the selection, relative to #wr-canvas
  var top = rangeRect.bottom - canvasRect.top + canvas.scrollTop + 8;
  var left = rangeRect.left - canvasRect.left;

  // Clamp left so popover doesn't overflow canvas
  var popoverWidth = 280;
  if (left + popoverWidth > canvas.clientWidth) {
    left = canvas.clientWidth - popoverWidth - 16;
  }
  if (left < 8) left = 8;

  // Clamp top so popover doesn't overflow below the visible canvas viewport
  var popoverHeight = 160; // approximate rendered height of popover
  var canvasVisibleBottom = canvas.scrollTop + canvas.clientHeight;
  if (top + popoverHeight > canvasVisibleBottom) {
    // Try placing above the selection instead
    var topAbove = rangeRect.top - canvasRect.top + canvas.scrollTop - popoverHeight - 8;
    if (topAbove >= canvas.scrollTop) {
      top = topAbove;
    } else {
      // Clamp to bottom of visible area as last resort
      top = canvasVisibleBottom - popoverHeight - 8;
    }
  }
  if (top < canvas.scrollTop + 8) top = canvas.scrollTop + 8;

  popover.style.top = top + 'px';
  popover.style.left = left + 'px';
  popover.style.display = 'block';

  // Focus the textarea after a microtask to ensure focus is not stolen by bubbling events
  var textarea = document.getElementById('wr-comment-popover-input');
  if (textarea) {
    textarea.value = '';
    setTimeout(function() { textarea.focus(); }, 0);
  }
}

/* ── Comment Popover: Hide ── */
function wrHideCommentPopover() {
  var popover = document.getElementById('wr-comment-popover');
  if (popover) {
    popover.style.display = 'none';
  }

  // Clear the textarea
  var textarea = document.getElementById('wr-comment-popover-input');
  if (textarea) {
    textarea.value = '';
  }

  // Clear the stored range and guard flag
  _wrPendingRange = null;
  _wrPopoverOpen = false;
}

/* ── Comment Popover: Submit ── */
function wrSubmitCommentFromPopover() {
  var textarea = document.getElementById('wr-comment-popover-input');
  if (!textarea) return;

  var text = textarea.value;

  // Prevent submission of empty/whitespace-only text (keep popover open)
  if (!text || !text.trim()) {
    textarea.focus();
    return;
  }

  // Guard: if no pending range, log and abort
  if (!_wrPendingRange) {
    console.warn('[Comments] Submit failed: _wrPendingRange is null. Popover will close.');
    wrHideCommentPopover();
    return;
  }

  var range = _wrPendingRange;
  var page = document.getElementById('wr-page');

  // Validate the range is still valid and within the editor
  try {
    var rangeText = range.toString();
    var snippet = rangeText.trim();
    if (!snippet) {
      console.warn('[Comments] Submit failed: range text is empty (selection may have been lost).');
      wrHideCommentPopover();
      return;
    }
    if (!page || !page.contains(range.startContainer) || !page.contains(range.endContainer)) {
      console.warn('[Comments] Submit failed: range is no longer within the editor.');
      wrHideCommentPopover();
      return;
    }
  } catch (e) {
    console.warn('[Comments] Submit failed: range validation threw:', e.message);
    wrHideCommentPopover();
    return;
  }

  _wrCommentId++;
  var id = 'wrc-' + _wrCommentId;

  // Restore selection from stored range
  var sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(range);

  // Wrap selected text in a highlight span
  var mark = document.createElement('span');
  mark.className = 'wr-comment-highlight';
  mark.setAttribute('data-comment-id', id);
  mark.title = text.trim();
  try {
    range.surroundContents(mark);
  } catch (e) {
    // surroundContents fails if selection crosses element boundaries (Req 1.7)
    console.warn('[Comments] Creation failed: surroundContents threw:', e.message);
    alert('Cannot add comment: the selection spans multiple paragraphs or elements. Please select text within a single block.');
    // Rollback the ID increment
    _wrCommentId--;
    wrHideCommentPopover();
    return;
  }

  // Normalize parent to merge adjacent text nodes created by surroundContents
  if (mark.parentNode) {
    mark.parentNode.normalize();
  }

  // Store comment
  var snippet = range.toString().trim() || mark.textContent.trim();
  _wrComments.push({
    id: id,
    text: text.trim(),
    snippet: snippet.slice(0, 60),
    time: _wrTimestamp(),
    replies: []
  });

  console.log('[Comments] Created comment:', id, '| snippet:', snippet.slice(0, 30));

  // Clear selection
  window.getSelection().removeAllRanges();

  // Render comments panel
  wrRenderComments();
  wrUpdate();
  wrSaveComments();

  wrHideCommentPopover();
}

/* ── Comment Popover: Keyboard shortcuts on textarea ── */
(function() {
  function setupCommentPopover() {
    var textarea = document.getElementById('wr-comment-popover-input');
    var submitBtn = document.getElementById('wr-popover-submit');
    var cancelBtn = document.getElementById('wr-popover-cancel');

    if (textarea) {
      textarea.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
          // Enter without Shift → submit
          e.preventDefault();
          wrSubmitCommentFromPopover();
        } else if (e.key === 'Escape') {
          // Escape → cancel and hide
          e.preventDefault();
          wrHideCommentPopover();
        }
        // Shift+Enter → default behavior (newline)
      });
    }

    // Wire up Add button
    if (submitBtn) {
      submitBtn.addEventListener('click', function(e) {
        e.preventDefault();
        wrSubmitCommentFromPopover();
      });
    }

    // Wire up Cancel button
    if (cancelBtn) {
      cancelBtn.addEventListener('click', function(e) {
        e.preventDefault();
        wrHideCommentPopover();
      });
    }

    // Click-outside-to-dismiss behavior
    document.addEventListener('mousedown', function(e) {
      var popover = document.getElementById('wr-comment-popover');
      if (!popover || popover.style.display === 'none') return;

      // Check if click is outside the popover
      if (!popover.contains(e.target)) {
        // Don't dismiss if clicking the Comment toolbar button (it will handle open/close itself)
        var commentBtn = document.getElementById('wr-comment-btn');
        if (commentBtn && (commentBtn === e.target || commentBtn.contains(e.target))) {
          return;
        }
        wrHideCommentPopover();
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupCommentPopover);
  } else {
    setupCommentPopover();
  }
})();

/* ── Reply Input: Delegated keyboard shortcuts on #wr-comments-list ── */
(function() {
  function setupReplyInput() {
    var commentsList = document.getElementById('wr-comments-list');
    if (!commentsList) return;

    commentsList.addEventListener('keydown', function(e) {
      // Only handle events from reply input textareas
      if (!e.target || !e.target.classList.contains('wr-reply-input')) return;

      if (e.key === 'Enter' && !e.shiftKey) {
        // Enter without Shift → submit reply
        e.preventDefault();
        var area = e.target.closest('.wr-reply-input-area');
        if (area && area.id) {
          var commentId = area.id.replace('reply-input-', '');
          wrSubmitReply(commentId);
        }
      } else if (e.key === 'Escape') {
        // Escape → cancel reply
        e.preventDefault();
        var area = e.target.closest('.wr-reply-input-area');
        if (area && area.id) {
          var commentId = area.id.replace('reply-input-', '');
          wrHideReplyInput(commentId);
        }
      }
      // Shift+Enter → default behavior (newline)
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupReplyInput);
  } else {
    setupReplyInput();
  }
})();

/* ── Add a comment (triggered from toolbar) ── */
function wrAddComment() {
  var sel = window.getSelection();
  var page = document.getElementById('wr-page');

  // Check selection exists and is within editor (Req 1.3)
  if (!sel || sel.isCollapsed || !sel.rangeCount) {
    alert('Select text in the editor before adding a comment.');
    return;
  }
  var anchorNode = sel.anchorNode;
  if (!anchorNode || !page.contains(anchorNode)) {
    alert('Select text in the editor before adding a comment.');
    return;
  }

  var range = sel.getRangeAt(0).cloneRange();
  var snippet = sel.toString().trim();

  // Validate selection is non-whitespace (Req 1.4)
  if (!snippet) {
    alert('Select text in the editor before adding a comment.');
    return;
  }

  // Check for cross-element selection that cannot be wrapped (Req 1.7)
  // Non-DOM-mutating validation: check if the range's common ancestor allows wrapping.
  // surroundContents requires that the range does not partially select a non-text node.
  var startContainer = range.startContainer;
  var endContainer = range.endContainer;
  var commonAncestor = range.commonAncestorContainer;

  // If start and end are in different block-level elements, wrapping will fail
  if (startContainer !== endContainer) {
    // Check if the common ancestor is a text node (impossible for cross-element)
    // or if the range partially selects element children
    var startBlock = _wrGetBlockParent(startContainer, page);
    var endBlock = _wrGetBlockParent(endContainer, page);
    if (startBlock !== endBlock) {
      console.warn('[Comments] Validation failed: selection crosses block boundaries.');
      alert('Cannot add comment: the selection spans multiple paragraphs or elements. Please select text within a single block.');
      return;
    }

    // Additional check: if commonAncestor is an element and range partially selects children
    if (commonAncestor.nodeType === Node.ELEMENT_NODE) {
      var startIdx = _wrNodeIndex(range.startContainer, commonAncestor);
      var endIdx = _wrNodeIndex(range.endContainer, commonAncestor);
      // Check that no element nodes are partially selected between start and end
      for (var ci = startIdx; ci <= endIdx; ci++) {
        var child = commonAncestor.childNodes[ci];
        if (child && child.nodeType === Node.ELEMENT_NODE) {
          // If an element child is partially (not fully) within the range, surroundContents will fail
          if (ci === startIdx && range.startOffset > 0 && range.startContainer === child) {
            console.warn('[Comments] Validation failed: partial element selection detected.');
            alert('Cannot add comment: the selection spans multiple paragraphs or elements. Please select text within a single block.');
            return;
          }
        }
      }
    }
  }

  // Show the inline comment popover (Req 1.1, 7.1)
  wrShowCommentPopover(range);
}

/* ── Helper: find the nearest block-level parent of a node within a boundary ── */
function _wrGetBlockParent(node, boundary) {
  var blockTags = /^(P|H[1-6]|LI|DIV|BLOCKQUOTE|PRE|TABLE|TR|TD|TH|UL|OL|SECTION|ARTICLE)$/i;
  var current = node;
  while (current && current !== boundary) {
    if (current.nodeType === Node.ELEMENT_NODE && blockTags.test(current.tagName)) {
      return current;
    }
    current = current.parentNode;
  }
  return boundary;
}

/* ── Helper: get the index of a node relative to an ancestor ── */
function _wrNodeIndex(node, ancestor) {
  var current = node;
  while (current.parentNode && current.parentNode !== ancestor) {
    current = current.parentNode;
  }
  var children = ancestor.childNodes;
  for (var i = 0; i < children.length; i++) {
    if (children[i] === current) return i;
  }
  return 0;
}

/* ── Render comments list ── */
function wrRenderComments() {
  var listEl = document.getElementById('wr-comments-list');
  var countEl = document.getElementById('wr-comments-count');
  var emptyEl = document.getElementById('wr-comments-empty');
  var panelEl = document.getElementById('wr-comments-panel');
  if (!listEl) {
    console.warn('[Comments] Render failed: #wr-comments-list not found.');
    return;
  }

  countEl.textContent = _wrComments.length;

  // Manage panel visibility: show when comments exist, hide when empty (Req 2.6)
  if (_wrComments.length > 0) {
    panelEl.classList.add('has-comments');
  } else {
    panelEl.classList.remove('has-comments');
  }

  if (_wrComments.length === 0) {
    // Recreate the empty message element if it was destroyed by a previous innerHTML assignment
    if (!emptyEl) {
      emptyEl = document.createElement('div');
      emptyEl.className = 'wr-comments-empty';
      emptyEl.id = 'wr-comments-empty';
      emptyEl.textContent = 'No comments yet. Select text and click "Add Comment" to start.';
    }
    listEl.innerHTML = '';
    listEl.appendChild(emptyEl);
    emptyEl.style.display = 'block';
    return;
  }

  // Hide the empty element if it still exists in the DOM (before innerHTML replaces children)
  if (emptyEl) {
    emptyEl.style.display = 'none';
  }

  var html = '';
  for (var i = 0; i < _wrComments.length; i++) {
    var c = _wrComments[i];
    var replies = c.replies || [];
    var orphanedClass = c.orphaned ? ' orphaned' : '';
    var snippetExtra = c.orphaned ? ' <span class="wr-orphaned-indicator">(text not found)</span>' : '';
    html += '<div class="wr-comment-card' + orphanedClass + '" data-comment-id="' + c.id + '" onclick="wrNavigateToComment(\'' + c.id + '\')">' +
      '<div class="wr-comment-snippet">"' + hEsc(c.snippet) + '"' + snippetExtra + '</div>' +
      '<div class="wr-comment-text">' + hEsc(c.text) + '</div>' +
      '<div class="wr-comment-footer">' +
        '<span class="wr-comment-time">' + c.time + '</span>' +
        '<button class="wr-comment-reply-btn" onclick="wrShowReplyInput(\'' + c.id + '\');event.stopPropagation();">Reply</button>' +
        '<button class="wr-comment-delete" onclick="wrDeleteComment(\'' + c.id + '\');event.stopPropagation();">Remove</button>' +
      '</div>' +
      '<div class="wr-comment-replies">';
    for (var j = 0; j < replies.length; j++) {
      var r = replies[j];
      html += '<div class="wr-reply-item">' +
        '<div class="wr-reply-text">' + hEsc(r.text) + '</div>' +
        '<div class="wr-reply-footer">' +
          '<span class="wr-reply-time">' + r.time + '</span>' +
          '<button class="wr-reply-delete" data-reply-id="' + r.id + '" onclick="wrDeleteReply(\'' + c.id + '\',\'' + r.id + '\');event.stopPropagation();">\u2715</button>' +
        '</div>' +
      '</div>';
    }
    html += '</div>' +
      '<div class="wr-reply-input-area" id="reply-input-' + c.id + '" style="display:none;" onclick="event.stopPropagation()">' +
        '<textarea class="wr-reply-input" maxlength="500" placeholder="Reply\u2026" onclick="event.stopPropagation()" onmousedown="event.stopPropagation()"></textarea>' +
        '<div class="wr-reply-input-actions">' +
          '<button class="btn-sm btn-green wr-reply-submit" onclick="wrSubmitReply(\'' + c.id + '\');event.stopPropagation();">Reply</button>' +
          '<button class="btn-sm btn-grey wr-reply-cancel" onclick="wrHideReplyInput(\'' + c.id + '\');event.stopPropagation();">Cancel</button>' +
        '</div>' +
      '</div>' +
    '</div>';
  }
  listEl.innerHTML = html;
}

/* ── Navigate to a comment highlight (card → highlight) ── */
function wrNavigateToComment(id) {
  // Target the highlight span specifically (not the card)
  var highlight = document.querySelector('.wr-comment-highlight[data-comment-id="' + id + '"]');
  if (!highlight) return;

  // Scroll the editor to the highlight with smooth behavior, centered in view
  highlight.scrollIntoView({ behavior: 'smooth', block: 'center' });

  // Apply focus state to both highlight and card
  if (typeof wrSetCommentFocus === 'function') {
    wrSetCommentFocus(id);
  } else {
    // Fallback: apply focused class directly to highlight and card
    highlight.classList.add('focused');
    var panel = document.getElementById('wr-comments-list');
    var card = panel ? panel.querySelector('.wr-comment-card[data-comment-id="' + id + '"]') : null;
    if (card) card.classList.add('focused');
  }

  // Clear focus after 1500ms visual indicator
  setTimeout(function() {
    if (typeof wrClearCommentFocus === 'function') {
      wrClearCommentFocus();
    } else {
      highlight.classList.remove('focused');
      var panel = document.getElementById('wr-comments-list');
      var card = panel ? panel.querySelector('.wr-comment-card[data-comment-id="' + id + '"]') : null;
      if (card) card.classList.remove('focused');
    }
  }, 1500);
}

/* ── Delete a comment ── */
function wrDeleteComment(id) {
  if (!confirm('Delete this comment and all its replies?')) return;

  // Remove highlight from editor
  var el = document.querySelector('[data-comment-id="' + id + '"]');
  if (el) {
    var parent = el.parentNode;
    while (el.firstChild) {
      parent.insertBefore(el.firstChild, el);
    }
    parent.removeChild(el);
    parent.normalize();
    console.log('[Comments] Removed highlight for:', id);
  } else {
    console.warn('[Comments] No highlight element found for:', id, '(may be orphaned).');
  }

  // Remove from array
  _wrComments = _wrComments.filter(function(c) { return c.id !== id; });

  wrRenderComments();
  wrUpdate();
  wrSaveComments();
}

/* ── Add a reply to a comment ── */
function wrAddReply(commentId, replyText) {
  if (!replyText || !replyText.trim()) return;

  var comment = null;
  for (var i = 0; i < _wrComments.length; i++) {
    if (_wrComments[i].id === commentId) {
      comment = _wrComments[i];
      break;
    }
  }
  if (!comment) return;

  // Ensure replies array exists (for comments created before this feature)
  if (!comment.replies) { comment.replies = []; }

  // Extract parent number from comment id (e.g. "wrc-3" → "3")
  var parentNum = commentId.replace('wrc-', '');
  var replyNum = comment.replies.length + 1;
  var replyId = 'wcr-' + parentNum + '-' + replyNum;

  comment.replies.push({
    id: replyId,
    text: replyText.trim(),
    time: _wrTimestamp()
  });

  wrRenderComments();
  wrSaveComments();
}

/* ── Delete a reply from a comment ── */
function wrDeleteReply(commentId, replyId) {
  var comment = null;
  for (var i = 0; i < _wrComments.length; i++) {
    if (_wrComments[i].id === commentId) {
      comment = _wrComments[i];
      break;
    }
  }
  if (!comment || !comment.replies) return;

  comment.replies = comment.replies.filter(function(r) { return r.id !== replyId; });

  wrRenderComments();
  wrSaveComments();
}

/* ── Reply input UI (stubs — full implementation in task 2.3) ── */
function wrShowReplyInput(commentId) {
  var area = document.getElementById('reply-input-' + commentId);
  if (area) {
    area.style.display = 'block';
    var textarea = area.querySelector('.wr-reply-input');
    if (textarea) {
      // Deferred focus to prevent event-cycle focus theft
      setTimeout(function() { textarea.focus(); }, 0);
    }
  }
}

function wrHideReplyInput(commentId) {
  var area = document.getElementById('reply-input-' + commentId);
  if (area) {
    area.style.display = 'none';
    var textarea = area.querySelector('.wr-reply-input');
    if (textarea) textarea.value = '';
  }
}

function wrSubmitReply(commentId) {
  var area = document.getElementById('reply-input-' + commentId);
  if (!area) return;
  var textarea = area.querySelector('.wr-reply-input');
  if (!textarea) return;
  var text = textarea.value;
  if (!text || !text.trim()) {
    textarea.focus();
    return;
  }
  wrAddReply(commentId, text);
  wrHideReplyInput(commentId);
}

/* ── Focus state management ── */
function wrSetCommentFocus(id) {
  // Clear any existing focus first (ensures only one comment focused at a time)
  wrClearCommentFocus();

  // Apply focused class to the highlight span in the editor
  var highlight = document.querySelector('.wr-comment-highlight[data-comment-id="' + id + '"]');
  if (highlight) highlight.classList.add('focused');

  // Apply focused class to the comment card in the panel
  var panel = document.getElementById('wr-comments-list');
  var card = panel ? panel.querySelector('.wr-comment-card[data-comment-id="' + id + '"]') : null;
  if (card) card.classList.add('focused');
}

function wrClearCommentFocus() {
  // Remove focused class from all highlight spans
  var focusedHighlights = document.querySelectorAll('.wr-comment-highlight.focused');
  for (var i = 0; i < focusedHighlights.length; i++) {
    focusedHighlights[i].classList.remove('focused');
  }

  // Remove focused class from all comment cards
  var focusedCards = document.querySelectorAll('.wr-comment-card.focused');
  for (var j = 0; j < focusedCards.length; j++) {
    focusedCards[j].classList.remove('focused');
  }
}

/* ── Highlight-to-card navigation ── */
function wrHighlightClicked(id) {
  var panel = document.getElementById('wr-comments-list');
  var card = panel ? panel.querySelector('.wr-comment-card[data-comment-id="' + id + '"]') : null;
  if (!card || !panel) return;

  // Set focus on both highlight and card
  wrSetCommentFocus(id);

  // Scroll the comments panel list to bring the card into view
  card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/* ── Delegated click handler for highlight spans ── */
(function() {
  document.addEventListener('DOMContentLoaded', function() {
    var page = document.getElementById('wr-page');
    if (!page) return;
    page.addEventListener('click', function(e) {
      var highlight = e.target.closest('.wr-comment-highlight');
      if (!highlight) {
        // Clicked non-highlighted content in the editor — clear focus
        wrClearCommentFocus();
        return;
      }
      var id = highlight.getAttribute('data-comment-id');
      if (id) wrHighlightClicked(id);
    });
  });
})();

/* ── Clear focus when clicking outside highlights and comments panel ── */
(function() {
  document.addEventListener('DOMContentLoaded', function() {
    document.addEventListener('click', function(e) {
      // If click is inside the editor (wr-page), the page handler above manages focus
      var page = document.getElementById('wr-page');
      if (page && page.contains(e.target)) return;

      // If click is inside the comments panel, don't clear focus
      var panel = document.querySelector('.wr-comments-panel');
      if (panel && panel.contains(e.target)) return;

      // Click is outside both — clear focus
      wrClearCommentFocus();
    });
  });
})();

/* ── Persistence: Offset calculation helpers ── */

/**
 * Calculate the character offset of a highlight element within #wr-page text content.
 * Walks text nodes in document order, counting characters until reaching the highlight.
 * Returns -1 if the highlight is not found or the editor is empty.
 */
function wrGetHighlightOffset(highlightEl) {
  var page = document.getElementById('wr-page');
  if (!page || !highlightEl) return -1;

  var offset = 0;
  var found = false;

  // TreeWalker to iterate all text nodes in document order
  var walker = document.createTreeWalker(page, NodeFilter.SHOW_TEXT, null, false);
  var node;

  while ((node = walker.nextNode())) {
    // Check if this text node is inside the highlight element
    if (highlightEl.contains(node)) {
      found = true;
      break;
    }
    offset += node.textContent.length;
  }

  return found ? offset : -1;
}

/**
 * Re-apply a highlight span at a given character offset in #wr-page.
 * Verifies that the text at the offset matches the saved snippet.
 * Returns true if highlight was successfully restored, false otherwise.
 */
function wrRestoreHighlight(commentObj) {
  var page = document.getElementById('wr-page');
  if (!page) return false;

  var targetOffset = commentObj.offset;
  var snippet = commentObj.snippet;

  // Edge case: empty editor
  if (!page.textContent || page.textContent.length === 0) return false;

  // Edge case: offset beyond content length
  if (targetOffset < 0 || targetOffset >= page.textContent.length) return false;

  // Verify text at offset matches the snippet
  var textAtOffset = page.textContent.substr(targetOffset, snippet.length);
  if (textAtOffset !== snippet) return false;

  // Walk text nodes to find the node and position at the target offset
  var walker = document.createTreeWalker(page, NodeFilter.SHOW_TEXT, null, false);
  var node;
  var currentOffset = 0;
  var startNode = null;
  var startPos = 0;

  while ((node = walker.nextNode())) {
    var nodeLen = node.textContent.length;
    if (currentOffset + nodeLen > targetOffset) {
      startNode = node;
      startPos = targetOffset - currentOffset;
      break;
    }
    currentOffset += nodeLen;
  }

  if (!startNode) return false;

  // Find the end position (may span multiple text nodes)
  var endNode = startNode;
  var endPos = startPos + snippet.length;
  var remainingInStart = startNode.textContent.length - startPos;

  if (snippet.length <= remainingInStart) {
    // Entire snippet fits within the start node
    endNode = startNode;
    endPos = startPos + snippet.length;
  } else {
    // Snippet spans multiple text nodes — find the end
    var remaining = snippet.length - remainingInStart;
    var searchNode = startNode;
    while (remaining > 0) {
      searchNode = walker.nextNode();
      if (!searchNode) return false;
      if (searchNode.textContent.length >= remaining) {
        endNode = searchNode;
        endPos = remaining;
        remaining = 0;
      } else {
        remaining -= searchNode.textContent.length;
      }
    }
  }

  // Create a range and wrap in highlight span
  try {
    var range = document.createRange();
    range.setStart(startNode, startPos);
    range.setEnd(endNode, endPos);

    var mark = document.createElement('span');
    mark.className = 'wr-comment-highlight';
    mark.setAttribute('data-comment-id', commentObj.id);
    mark.title = commentObj.text;
    range.surroundContents(mark);
    return true;
  } catch (e) {
    // surroundContents can fail if range crosses element boundaries
    return false;
  }
}

/* ── Persistence: Save comments to localStorage ── */

/**
 * Serializes _wrComments array to localStorage key "wr-comments-data".
 * Includes schema version, comment ID counter, and full comment objects with offsets.
 * Handles storage quota exceeded by showing notification and retaining in-memory.
 */
function wrSaveComments() {
  // Build comments array with calculated offsets
  var commentsData = [];
  for (var i = 0; i < _wrComments.length; i++) {
    var comment = _wrComments[i];

    // Calculate offset from the highlight span in the DOM
    var highlightEl = document.querySelector('.wr-comment-highlight[data-comment-id="' + comment.id + '"]');
    var offset = highlightEl ? wrGetHighlightOffset(highlightEl) : -1;

    commentsData.push({
      id: comment.id,
      text: comment.text,
      snippet: comment.snippet,
      time: comment.time,
      offset: offset,
      replies: comment.replies || []
    });
  }

  var data = {
    version: 1,
    commentIdCounter: _wrCommentId,
    comments: commentsData
  };

  try {
    localStorage.setItem('wr-comments-data', JSON.stringify(data));
  } catch (e) {
    // Handle storage quota exceeded (or other localStorage errors)
    if (e.name === 'QuotaExceededError' || e.code === 22 || e.code === 1014) {
      alert('Comments could not be saved: storage quota exceeded. Your comments are retained in memory for this session.');
    } else {
      alert('Comments could not be saved: ' + e.message + '. Your comments are retained in memory for this session.');
    }
  }
}

/* ── Persistence: Load comments from localStorage ── */

/**
 * Reads saved comments from localStorage and restores state.
 * Re-applies highlight spans by matching saved character offset and verifying snippet text.
 * If text at offset doesn't match snippet, marks comment as orphaned (no highlight applied).
 * Restores comment ID counter to avoid collisions.
 * Should be called on DOMContentLoaded.
 */
function wrLoadComments() {
  var raw = localStorage.getItem('wr-comments-data');
  if (!raw) return;

  var data;
  try {
    data = JSON.parse(raw);
  } catch (e) {
    console.warn('[Comments] Load failed: invalid JSON in localStorage.');
    return; // Invalid JSON, skip restoration
  }

  // Validate schema version
  if (!data || data.version !== 1) return;

  // Restore comment ID counter to avoid collisions
  if (typeof data.commentIdCounter === 'number' && data.commentIdCounter > _wrCommentId) {
    _wrCommentId = data.commentIdCounter;
  }

  var page = document.getElementById('wr-page');
  var editorEmpty = !page || !page.textContent || page.textContent.trim().length === 0;

  // If editor is empty, discard all saved comments (they are all orphaned)
  if (editorEmpty) {
    console.log('[Comments] Editor is empty on load — discarding saved comments.');
    try {
      localStorage.removeItem('wr-comments-data');
    } catch (e) { /* ignore */ }
    _wrCommentId = 0;
    return;
  }

  // Restore each comment
  var comments = data.comments || [];
  var restoredCount = 0;
  var orphanedCount = 0;
  for (var i = 0; i < comments.length; i++) {
    var comment = comments[i];

    // Ensure replies array exists
    if (!comment.replies) comment.replies = [];

    // Attempt to re-apply highlight span
    var restored = wrRestoreHighlight(comment);

    // If restoration fails, mark as orphaned
    if (!restored) {
      comment.orphaned = true;
      orphanedCount++;
    } else {
      restoredCount++;
    }

    _wrComments.push(comment);
  }

  console.log('[Comments] Loaded:', restoredCount, 'restored,', orphanedCount, 'orphaned.');

  // Render all comments (including orphaned ones)
  wrRenderComments();
}

/* ── Hide comment button — no-op (floating button removed) ── */


/* ============================================================
   MARKITDOWN — File/URL to Markdown Converter
   [FRONTEND: UI] — File handling, IPC calls, result display
   ============================================================ */

var _mdSelectedFile = null;
var _mdMarkdownContent = '';
var _mdOutputFilename = '';

const MD_SUPPORTED_EXTENSIONS = [
  '.pdf','.docx','.pptx','.xlsx','.html','.htm',
  '.png','.jpg','.jpeg','.gif','.bmp','.tiff',
  '.mp3','.wav','.epub','.msg','.ipynb','.zip',
  '.csv','.json','.xml','.txt','.md','.rst'
];
const MD_MAX_FILE_SIZE = 50 * 1024 * 1024; // 50 MB

/* ── Initialization ── */
(function mdInit() {
  function setup() {
    var dropArea = document.getElementById('md-drop-area');
    var fileInput = document.getElementById('md-file-input');
    var urlInput = document.getElementById('md-url-input');

    if (!dropArea) return; // Tab not present

    // Drag & drop
    dropArea.addEventListener('dragover', function(e) {
      e.preventDefault();
      dropArea.classList.add('dragover');
    });
    dropArea.addEventListener('dragleave', function() {
      dropArea.classList.remove('dragover');
    });
    dropArea.addEventListener('drop', function(e) {
      e.preventDefault();
      dropArea.classList.remove('dragover');
      if (e.dataTransfer.files.length > 0) {
        mdHandleFile(e.dataTransfer.files[0]);
      }
    });

    // File input change
    fileInput.addEventListener('change', function() {
      if (fileInput.files.length > 0) {
        mdHandleFile(fileInput.files[0]);
      }
    });

    // URL input — enable/disable convert button
    urlInput.addEventListener('input', function() {
      mdUpdateConvertBtn();
    });
  }

  // Run setup immediately if DOM is ready, otherwise wait
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setup);
  } else {
    setup();
  }
})();

function mdHandleFile(file) {
  mdHideAlert();

  // Validate extension
  var ext = '.' + file.name.split('.').pop().toLowerCase();
  if (MD_SUPPORTED_EXTENSIONS.indexOf(ext) === -1) {
    mdShowAlert('Unsupported file type. Supported: ' + MD_SUPPORTED_EXTENSIONS.join(', '), 'error');
    return;
  }

  // Validate size
  if (file.size > MD_MAX_FILE_SIZE) {
    mdShowAlert('File size exceeds the 50 MB limit.', 'error');
    return;
  }

  _mdSelectedFile = file;
  document.getElementById('md-file-name').textContent = file.name;
  document.getElementById('md-file-size').textContent = mdFormatSize(file.size);
  document.getElementById('md-file-info').style.display = 'block';
  mdUpdateConvertBtn();
}

function mdClearFile() {
  _mdSelectedFile = null;
  document.getElementById('md-file-input').value = '';
  document.getElementById('md-file-info').style.display = 'none';
  mdUpdateConvertBtn();
}

function mdUpdateConvertBtn() {
  var urlInput = document.getElementById('md-url-input');
  var btn = document.getElementById('md-convert-btn');
  btn.disabled = !(_mdSelectedFile || (urlInput && urlInput.value.trim()));
}

function mdFormatSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

/* ── Convert ── */
async function mdConvert() {
  mdHideAlert();
  var urlInput = document.getElementById('md-url-input');

  if (!_mdSelectedFile && !urlInput.value.trim()) return;

  // Check if API is available
  if (!window.api || !window.api.markitdownConvert) {
    mdShowAlert('Error: Backend API not available. Ensure the app is running in Electron.', 'error');
    return;
  }

  // Show loading
  document.getElementById('md-loading').style.display = 'block';
  document.getElementById('md-convert-btn').disabled = true;
  document.getElementById('md-output').style.display = 'none';

  try {
    var response;

    if (_mdSelectedFile) {
      // File conversion — read file as base64, send via IPC
      var fileData;
      try {
        fileData = await mdFileToBase64(_mdSelectedFile);
      } catch (readErr) {
        throw new Error('Failed to read file: ' + (readErr.message || 'file may have been moved or deleted'));
      }

      if (!fileData) {
        throw new Error('File appears to be empty or could not be read.');
      }

      response = await window.api.markitdownConvert({
        mode: 'file',
        filename: _mdSelectedFile.name,
        fileData: fileData
      });
    } else {
      // URL conversion
      var url = urlInput.value.trim();
      if (!/^https?:\/\//i.test(url)) {
        url = 'https://' + url;
      }
      response = await window.api.markitdownConvert({
        mode: 'url',
        url: url
      });
    }

    // Hide loading
    document.getElementById('md-loading').style.display = 'none';
    mdUpdateConvertBtn();

    // Validate response structure
    if (!response) {
      mdShowAlert('Error: No response received from backend. The conversion may have timed out.', 'error');
      return;
    }

    if (response.success) {
      var data = response.data || {};
      _mdMarkdownContent = data.markdown || '';
      _mdOutputFilename = data.filename || 'output.md';

      if (!_mdMarkdownContent.trim()) {
        mdShowAlert('No content was extracted from the source. The file may be empty, password-protected, or in an unsupported format variation.', 'error');
        document.getElementById('md-output').style.display = 'none';
        return;
      }

      document.getElementById('md-raw-view').value = _mdMarkdownContent;
      document.getElementById('md-output').style.display = 'block';
      mdShowRaw();
      mdShowAlert('Conversion successful! (' + mdFormatSize(_mdMarkdownContent.length) + ' of Markdown)', 'success');
    } else {
      var errMsg = (response.error && response.error.message) ? response.error.message : 'Conversion failed. Please try a different file or check the format.';
      mdShowAlert(errMsg, 'error');
    }

  } catch (err) {
    document.getElementById('md-loading').style.display = 'none';
    mdUpdateConvertBtn();
    var msg = err.message || 'Unknown error';
    if (msg.indexOf('timed out') !== -1) {
      mdShowAlert('Conversion timed out. The file may be too large or complex. Try a smaller file.', 'error');
    } else if (msg.indexOf('Backend not available') !== -1 || msg.indexOf('not available') !== -1) {
      mdShowAlert('Backend is not available. Please restart the application.', 'error');
    } else {
      mdShowAlert('Error: ' + msg, 'error');
    }
  }
}

function mdFileToBase64(file) {
  return new Promise(function(resolve, reject) {
    var reader = new FileReader();
    reader.onload = function() {
      // result is "data:<type>;base64,<data>" — strip prefix
      var b64 = reader.result.split(',')[1];
      resolve(b64);
    };
    reader.onerror = function() { reject(new Error('Failed to read file')); };
    reader.readAsDataURL(file);
  });
}

/* ── View Toggle ── */
function mdShowRaw() {
  document.getElementById('md-raw-view').style.display = 'block';
  document.getElementById('md-rendered-view').style.display = 'none';
  document.getElementById('md-btn-raw').style.background = '#495057';
  document.getElementById('md-btn-raw').style.color = '#fff';
  document.getElementById('md-btn-rendered').style.background = '';
  document.getElementById('md-btn-rendered').style.color = '';
  document.getElementById('md-btn-rendered').className = 'btn-sm btn-grey';
}

function mdShowRendered() {
  document.getElementById('md-raw-view').style.display = 'none';
  document.getElementById('md-rendered-view').style.display = 'block';
  document.getElementById('md-btn-rendered').style.background = '#495057';
  document.getElementById('md-btn-rendered').style.color = '#fff';
  document.getElementById('md-btn-raw').style.background = '';
  document.getElementById('md-btn-raw').style.color = '';
  document.getElementById('md-btn-raw').className = 'btn-sm btn-grey';

  // Render Markdown to HTML (basic rendering without external libs)
  var html = mdRenderMarkdown(_mdMarkdownContent);
  document.getElementById('md-rendered-view').innerHTML = html;
}

function mdRenderMarkdown(text) {
  // Basic Markdown rendering without external dependencies
  // Handles: headings, bold, italic, code blocks, inline code, links, lists, blockquotes, hr, tables
  var html = text;

  // Escape HTML
  html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  // Code blocks (fenced)
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, function(m, lang, code) {
    return '<pre><code>' + code.trim() + '</code></pre>';
  });

  // Inline code
  html = html.replace(/`([^`\n]+)`/g, '<code>$1</code>');

  // Headings
  html = html.replace(/^#{6}\s+(.+)$/gm, '<h6>$1</h6>');
  html = html.replace(/^#{5}\s+(.+)$/gm, '<h5>$1</h5>');
  html = html.replace(/^#{4}\s+(.+)$/gm, '<h4>$1</h4>');
  html = html.replace(/^#{3}\s+(.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^#{2}\s+(.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^#{1}\s+(.+)$/gm, '<h1>$1</h1>');

  // Horizontal rule
  html = html.replace(/^---+$/gm, '<hr>');

  // Bold & italic
  html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

  // Links
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

  // Images — show as alt text
  html = html.replace(/!\[([^\]]*)\]\([^)]+\)/g, '<span style="color:#888;">[Image: $1]</span>');

  // Blockquotes
  html = html.replace(/^&gt;\s?(.+)$/gm, '<blockquote>$1</blockquote>');

  // Unordered lists
  html = html.replace(/^[\*\-]\s+(.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>');
  // Collapse adjacent ul tags
  html = html.replace(/<\/ul>\s*<ul>/g, '');

  // Line breaks → paragraphs
  html = html.replace(/\n\n/g, '</p><p>');
  html = '<p>' + html + '</p>';
  html = html.replace(/<p>\s*<\/p>/g, '');
  html = html.replace(/<p>\s*(<h[1-6]>)/g, '$1');
  html = html.replace(/(<\/h[1-6]>)\s*<\/p>/g, '$1');
  html = html.replace(/<p>\s*(<pre>)/g, '$1');
  html = html.replace(/(<\/pre>)\s*<\/p>/g, '$1');
  html = html.replace(/<p>\s*(<ul>)/g, '$1');
  html = html.replace(/(<\/ul>)\s*<\/p>/g, '$1');
  html = html.replace(/<p>\s*(<blockquote>)/g, '$1');
  html = html.replace(/(<\/blockquote>)\s*<\/p>/g, '$1');
  html = html.replace(/<p>\s*(<hr>)/g, '$1');
  html = html.replace(/(<hr>)\s*<\/p>/g, '$1');

  return html;
}

/* ── Download ── */
function mdDownload() {
  if (!_mdMarkdownContent) return;
  var blob = new Blob([_mdMarkdownContent], { type: 'text/markdown;charset=utf-8' });
  saveAs(blob, _mdOutputFilename);
}

/* ── Copy ── */
function mdCopy() {
  if (!_mdMarkdownContent) return;
  var copyBtn = document.getElementById('md-copy-btn');
  navigator.clipboard.writeText(_mdMarkdownContent).then(function() {
    var originalText = copyBtn.textContent;
    copyBtn.textContent = '✓ Copied!';
    setTimeout(function() { copyBtn.textContent = originalText; }, 3000);
  }).catch(function() {
    mdShowAlert('Copy to clipboard failed. Select and copy manually.', 'error');
  });
}

/* ── Clear ── */
function mdClear() {
  mdClearFile();
  document.getElementById('md-url-input').value = '';
  document.getElementById('md-output').style.display = 'none';
  document.getElementById('md-loading').style.display = 'none';
  _mdMarkdownContent = '';
  _mdOutputFilename = '';
  mdHideAlert();
  mdUpdateConvertBtn();
}

/* ── Alert display ── */
function mdShowAlert(message, type) {
  var el = document.getElementById('md-alert');
  el.textContent = message;
  el.style.display = 'block';
  if (type === 'success') {
    el.style.background = '#d4edda';
    el.style.border = '1px solid #c3e6cb';
    el.style.color = '#155724';
    setTimeout(mdHideAlert, 3000);
  } else {
    el.style.background = '#f8d7da';
    el.style.border = '1px solid #f5c6cb';
    el.style.color = '#721c24';
  }
}

function mdHideAlert() {
  document.getElementById('md-alert').style.display = 'none';
}
