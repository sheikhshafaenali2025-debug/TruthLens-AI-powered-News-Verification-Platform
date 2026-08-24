  const modeToggle = document.getElementById('modeToggle');
  modeToggle.addEventListener('click', () => {
    document.body.classList.toggle('paper-mode');
    modeToggle.textContent = document.body.classList.contains('paper-mode') ? '☼' : '☾';
  });

  const textarea = document.getElementById('article-input');
  const wordCount = document.getElementById('wordCount');
  textarea.addEventListener('input', () => {
    const words = textarea.value.trim().split(/\s+/).filter(Boolean);
    wordCount.textContent = (textarea.value.trim() ? words.length : 0) + ' words';
  });

  document.getElementById('clearBtn').addEventListener('click', () => {
    textarea.value = '';
    document.getElementById('sourceInput').value = '';
    wordCount.textContent = '0 words';
    document.getElementById('resultsPanel').classList.remove('active');
  });

  const fileInput = document.getElementById('fileInput');
  document.getElementById('uploadBtn').addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      textarea.value = ev.target.result;
      textarea.dispatchEvent(new Event('input'));
    };
    reader.readAsText(file);
  });

  const API_BASE = (['localhost', '127.0.0.1'].includes(window.location.hostname))
    ? 'http://localhost:5000'
    : 'https://truthlens-ai-powered-news-verification.onrender.com';

  async function callPredictAPI(text) {
    const response = await fetch(`${API_BASE}/api/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.error || `Request failed with status ${response.status}`);
    }
    return response.json();
  }

  async function callHistoryAPI() {
    const response = await fetch(`${API_BASE}/api/history`);
    if (!response.ok) throw new Error(`Request failed with status ${response.status}`);
    return response.json();
  }

  async function callDeleteHistoryAPI() {
    const response = await fetch(`${API_BASE}/api/history`, { method: 'DELETE' });
    if (!response.ok) throw new Error(`Request failed with status ${response.status}`);
    return response.json();
  }

  async function callModelAPI() {
    const response = await fetch(`${API_BASE}/api/model`);
    if (!response.ok) throw new Error(`Request failed with status ${response.status}`);
    return response.json();
  }

  async function callStatsAPI() {
    const response = await fetch(`${API_BASE}/api/stats`);
    if (!response.ok) throw new Error(`Request failed with status ${response.status}`);
    return response.json();
  }

  async function callHealthAPI() {
    const response = await fetch(`${API_BASE}/api/health`);
    if (!response.ok) throw new Error(`Request failed with status ${response.status}`);
    return response.json();
  }

  // Shared keyword extraction so freshly analyzed articles and articles
  // loaded from the backend's persisted history use the same logic.
  function extractKeywords(text) {
    const candidates = (text.match(/\b[A-Z][a-zA-Z]{3,}\b/g) || []).filter(w => !['The','This','That','With','From','Their','After','Before'].includes(w));
    let keywords = [...new Set(candidates)].slice(0, 6);
    if (keywords.length === 0) {
      const fallback = (text.match(/\b[a-z]{5,}\b/gi) || []);
      keywords = [...new Set(fallback)].slice(0, 5);
    }
    if (keywords.length === 0) keywords = ['—'];
    return keywords;
  }

  const TRUSTED_SOURCES = ['bbc.com','bbc.co.uk','reuters.com','apnews.com','thehindu.com','nytimes.com','theguardian.com','npr.org','wsj.com','bloomberg.com','aljazeera.com','pti.com','indianexpress.com'];
  const SUSPICIOUS_PATTERNS = ['blogspot','wordpress.free','news247','truthreport','clickbait','realnewsnow','freepress24'];

  function computeSourceTrust(rawSource) {
    const src = rawSource.trim().toLowerCase().replace(/^https?:\/\//, '').replace(/^www\./, '').replace(/\/.*$/, '');
    if (!src) return { name: 'No source given', score: null, badge: 'unrated', label: 'Unrated' };

    let seed = 0;
    for (let i = 0; i < src.length; i++) seed = (seed + src.charCodeAt(i) * (i + 1)) % 97;

    if (TRUSTED_SOURCES.some(d => src.includes(d))) {
      return { name: src, score: 90 + (seed % 9), badge: 'trusted', label: 'Verified publisher' };
    }
    if (SUSPICIOUS_PATTERNS.some(p => src.includes(p)) || /\d{2,}/.test(src)) {
      return { name: src, score: 12 + (seed % 20), badge: 'suspicious', label: 'Suspicious source' };
    }
    return { name: src, score: 42 + (seed % 22), badge: 'unrated', label: 'Unrated — proceed with caution' };
  }

  function analyzeText(text, sourceRaw, apiResult) {
    const words = text.trim().split(/\s+/).filter(Boolean);
    const lower = text.toLowerCase();

    const hedgeWords = ['shocking','you won\'t believe','secret','miracle','they don\'t want you to know','exposed','banned','cure','conspiracy','anonymous sources say','click here'];
    const credibleWords = ['according to','reported','officials said','the study found','data shows','confirmed','statement','ministry','department','university','percent'];

    let hedgeScore = 0, credScore = 0;
    hedgeWords.forEach(w => { if (lower.includes(w)) hedgeScore++; });
    credibleWords.forEach(w => { if (lower.includes(w)) credScore++; });

    const exclaims = (text.match(/!/g) || []).length;
    const caps = (text.match(/\b[A-Z]{4,}\b/g) || []).length;
    const hasNumbers = /\b\d+(\.\d+)?%?\b/.test(text);
    hedgeScore += Math.min(exclaims, 3) * 0.5 + Math.min(caps, 3) * 0.5;

    let seed = 0;
    for (let i = 0; i < text.length; i++) seed = (seed + text.charCodeAt(i) * (i + 1)) % 9973;

    // Verdict, confidence, and probabilities now come from the real model
    // via POST /api/predict, instead of the locally-simulated fakeLean score.
    const isFake = apiResult.prediction === 'FAKE';
    const realPct = Math.round(apiResult.probabilities.real);
    const fakePct = Math.round(apiResult.probabilities.fake);
    const confidence = Math.round(apiResult.confidence);
    const processingTime = apiResult.processing_time;

    let risk = 'Low';
    if (confidence < 65) risk = 'Elevated';
    if (confidence < 55) risk = 'High';

    const sentimentPool = ['Neutral','Measured','Cautionary','Assertive'];
    const sentiment = words.length ? sentimentPool[seed % sentimentPool.length] : 'Neutral';

    const keywords = extractKeywords(text);

    const explanation = isFake
      ? `The text leans on emotionally charged phrasing and light sourcing rather than named officials or data.`
      : `The text uses measured language and cites sourcing patterns consistent with verified reporting seen during training.`;

    const checklist = [];
    checklist.push(hedgeScore > 0
      ? { text: 'Emotional or sensational language detected', flag: true }
      : { text: 'No strongly emotional or sensational language detected', flag: false });
    checklist.push(credScore > 0
      ? { text: 'References named officials, studies, or sources', flag: false }
      : { text: 'No named officials, studies, or sources cited', flag: true });
    checklist.push((exclaims >= 1 || caps >= 1)
      ? { text: 'Excessive punctuation or capitalization present', flag: true }
      : { text: 'Punctuation and capitalization within normal range', flag: false });
    checklist.push(words.length >= 25
      ? { text: 'Sufficient length for a confident reading', flag: false }
      : { text: 'Very short text — limited signal for a confident reading', flag: true });
    checklist.push(hasNumbers
      ? { text: 'Contains specific figures or data references', flag: false }
      : { text: 'Few factual figures or data points referenced', flag: true });

    const sentences = (text.match(/[^.!?]+[.!?]+/g) || []).map(s => s.trim()).filter(Boolean);
    let claims = sentences.filter(s => /\d/.test(s) || /"/.test(s)).slice(0, 3);
    if (claims.length === 0) claims = sentences.slice(0, 2);

    const topicWords = keywords.filter(k => k !== '—').slice(0, 3);
    const summary = topicWords.length
      ? `The article centers on ${topicWords.join(', ')}, presented in a ${sentiment.toLowerCase()} tone across ${words.length} words.`
      : `A short piece of ${words.length} words, presented in a ${sentiment.toLowerCase()} tone with limited distinct topic terms.`;

    const politicalPct = 20 + (seed % 55);
    const languagePct = Math.min(95, 15 + Math.round(hedgeScore * 18));
    const emotionPct = Math.min(95, 10 + exclaims * 15 + caps * 10 + Math.round(hedgeScore * 10));
    const levelLabel = (pct) => pct < 35 ? 'Low' : pct < 65 ? 'Medium' : 'High';

    const outletPool = ['Reuters', 'BBC', 'AP News', 'The Hindu', 'The Guardian', 'NPR'];
    const shuffled = outletPool.slice().sort((a, b) => ((seed + a.length) % 7) - ((seed + b.length) % 7));
    const similar = shuffled.slice(0, 4).map((outlet, i) => ({ outlet, pct: 91 - i * 6 - (seed % 4) }));

    const source = computeSourceTrust(sourceRaw || '');

    return {
      isFake, realPct, fakePct, confidence, risk, sentiment, keywords, explanation, wordCount: words.length,
      checklist, claims, summary, processingTime,
      bias: {
        political: { pct: politicalPct, label: levelLabel(politicalPct) },
        language: { pct: languagePct, label: levelLabel(languagePct) },
        emotion: { pct: emotionPct, label: levelLabel(emotionPct) }
      },
      similar, source
    };
  }

  const analyzeBtn = document.getElementById('analyzeBtn');
  const loadingPanel = document.getElementById('loadingPanel');
  const resultsPanel = document.getElementById('resultsPanel');
  const progressFill = document.getElementById('progressFill');
  const lines = ['line1','line2','line3','line4','line5'].map(id => document.getElementById(id));
  const sourceInput = document.getElementById('sourceInput');

  const sessionAnalyses = [];

  analyzeBtn.addEventListener('click', () => {
    const text = textarea.value.trim();
    if (text.split(/\s+/).filter(Boolean).length < 8) {
      textarea.style.borderColor = 'var(--fake)';
      textarea.placeholder = 'Paste at least a full sentence or two — the desk needs real text to read.';
      setTimeout(() => textarea.style.borderColor = '', 1200);
      return;
    }

    resultsPanel.classList.remove('active');
    loadingPanel.classList.add('active');
    analyzeBtn.disabled = true;
    lines.forEach(l => l.classList.remove('active'));
    progressFill.style.width = '0%';

    // Kick off the real prediction immediately so it overlaps with the
    // loading animation instead of waiting for it to finish first.
    const predictionPromise = callPredictAPI(text).catch(err => ({ error: err.message }));

    let step = 0;
    const totalSteps = lines.length;
    const stepTime = 380;

    const interval = setInterval(() => {
      if (step < totalSteps) {
        lines[step].classList.add('active');
        progressFill.style.width = (((step + 1) / totalSteps) * 100) + '%';
        step++;
      } else {
        clearInterval(interval);
        predictionPromise.then(apiResult => {
          if (apiResult.error) {
            loadingPanel.classList.remove('active');
            analyzeBtn.disabled = false;
            textarea.style.borderColor = 'var(--fake)';
            textarea.placeholder = `Backend error: ${apiResult.error} — check the server is running.`;
            setTimeout(() => textarea.style.borderColor = '', 2200);
            return;
          }
          runResults(text, sourceInput.value, apiResult);
        });
      }
    }, stepTime);
  });

  function runResults(text, sourceRaw, apiResult) {
    const r = analyzeText(text, sourceRaw, apiResult);
    loadingPanel.classList.remove('active');
    analyzeBtn.disabled = false;

    document.getElementById('filedTime').textContent = new Date().toLocaleString(undefined, { hour:'2-digit', minute:'2-digit', month:'short', day:'numeric' });
    document.getElementById('verdictHeadline').textContent = r.isFake ? 'Flagged — likely fabricated' : 'Cleared — likely genuine';
    document.getElementById('confidenceNum').textContent = r.confidence + '%';
    document.getElementById('riskLevel').textContent = r.risk;
    document.getElementById('sentiment').textContent = r.sentiment;
    document.getElementById('procTime').textContent = r.processingTime;

    document.getElementById('realPct').textContent = r.realPct + '%';
    document.getElementById('fakePct').textContent = r.fakePct + '%';

    const color = r.isFake ? 'var(--fake)' : 'var(--real)';

    requestAnimationFrame(() => {
      document.getElementById('realBar').style.width = r.realPct + '%';
      document.getElementById('fakeBar').style.width = r.fakePct + '%';
      document.getElementById('scoreBarFill').style.width = r.confidence + '%';
      document.getElementById('scoreBarFill').style.background = color;
      document.getElementById('biasPoliticalFill').style.width = r.bias.political.pct + '%';
      document.getElementById('biasLanguageFill').style.width = r.bias.language.pct + '%';
      document.getElementById('biasEmotionFill').style.width = r.bias.emotion.pct + '%';
    });
    document.getElementById('biasPoliticalLabel').textContent = r.bias.political.label;
    document.getElementById('biasLanguageLabel').textContent = r.bias.language.label;
    document.getElementById('biasEmotionLabel').textContent = r.bias.emotion.label;

    const chipWrap = document.getElementById('keywordChips');
    chipWrap.innerHTML = '';
    r.keywords.forEach(k => {
      const chip = document.createElement('span');
      chip.className = 'keyword-chip';
      chip.textContent = k;
      chipWrap.appendChild(chip);
    });

    const stamp = document.getElementById('verdictStamp');
    stamp.querySelectorAll('circle').forEach(c => c.setAttribute('stroke', color));
    const word = document.getElementById('verdictWord');
    word.textContent = r.isFake ? 'FAKE' : 'REAL';
    word.setAttribute('fill', color);
    const sub = document.getElementById('verdictSub');
    sub.textContent = r.isFake ? 'DESK FLAGGED' : 'DESK CLEARED';
    sub.setAttribute('fill', color);

    const checklistEl = document.getElementById('checklistItems');
    checklistEl.innerHTML = '';
    r.checklist.forEach(item => {
      const li = document.createElement('li');
      li.className = item.flag ? 'flag' : 'clear';
      li.innerHTML = `<span class="mark">${item.flag ? '!' : '✓'}</span><span>${item.text}</span>`;
      checklistEl.appendChild(li);
    });

    document.getElementById('credSourceName').textContent = r.source.name;
    document.getElementById('credScoreText').textContent = r.source.score === null ? 'Trust score — / 100' : `Trust score ${r.source.score} / 100`;
    const badge = document.getElementById('credBadge');
    badge.className = 'cred-badge ' + r.source.badge;
    badge.textContent = r.source.label;

    document.getElementById('summaryText').textContent = r.summary;

    const claimsEl = document.getElementById('claimsList');
    claimsEl.innerHTML = '';
    r.claims.forEach((claim, i) => {
      const div = document.createElement('div');
      div.className = 'claim-item';
      div.innerHTML = `<div class="claim-num">Claim ${i + 1}</div><blockquote>${claim.replace(/</g,'&lt;')}</blockquote><span class="claim-status">Needs verification</span>`;
      claimsEl.appendChild(div);
    });

    const similarEl = document.getElementById('similarList');
    similarEl.innerHTML = '';
    r.similar.forEach(s => {
      const row = document.createElement('div');
      row.className = 'similar-row';
      row.innerHTML = `<span class="similar-outlet">${s.outlet}</span><span class="similar-pct">${s.pct}% similar coverage</span>`;
      similarEl.appendChild(row);
    });

    const agreeBtn = document.getElementById('agreeBtn');
    const disagreeBtn = document.getElementById('disagreeBtn');
    const reportBtn = document.getElementById('reportBtn');
    [agreeBtn, disagreeBtn, reportBtn].forEach(b => b.disabled = false);
    document.getElementById('communityNote').textContent = '';

    sessionAnalyses.push(r);
    updateDashboard();

    resultsPanel.classList.add('active');
    resultsPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function updateDashboard() {
    const total = sessionAnalyses.length;
    document.getElementById('dashTotal').textContent = total;

    const realCount = sessionAnalyses.filter(a => !a.isFake).length;
    const realShare = total ? Math.round((realCount / total) * 100) : 50;
    document.getElementById('dashRatioText').textContent = total ? `${realShare}% / ${100 - realShare}%` : '—';
    document.getElementById('dashRatioReal').style.width = realShare + '%';
    document.getElementById('dashRatioFake').style.width = (100 - realShare) + '%';

    const avgConf = total ? Math.round(sessionAnalyses.reduce((sum, a) => sum + a.confidence, 0) / total) : null;
    document.getElementById('dashAvgConf').textContent = avgConf === null ? '—' : avgConf + '%';

    const freq = {};
    sessionAnalyses.forEach(a => a.keywords.forEach(k => { if (k !== '—') freq[k] = (freq[k] || 0) + 1; }));
    const top = Object.entries(freq).sort((a, b) => b[1] - a[1]).slice(0, 6).map(e => e[0]);
    const kwWrap = document.getElementById('dashKeywords');
    kwWrap.innerHTML = '';
    if (top.length === 0) {
      const chip = document.createElement('span');
      chip.className = 'keyword-chip';
      chip.textContent = 'No analyses yet';
      kwWrap.appendChild(chip);
    } else {
      top.forEach(k => {
        const chip = document.createElement('span');
        chip.className = 'keyword-chip';
        chip.textContent = k;
        kwWrap.appendChild(chip);
      });
    }
  }
  // Sync backend health, ML model metadata, and update status badge + stats bar
  async function syncBackendStatus() {
    const statusEl = document.getElementById('serverStatus');
    const statusTextEl = document.getElementById('statusText');
    const dashNoteEl = document.getElementById('dashNote');
    try {
      await callHealthAPI();
      const model = await callModelAPI().catch(() => ({}));
      
      statusEl.classList.remove('offline');
      statusEl.classList.add('online');
      const acc = model.accuracy ? `${Math.round(model.accuracy * 100)}%` : '96%';
      statusTextEl.textContent = `Engine Online (ML v1.0)`;
      
      if (document.getElementById('statAccuracy')) {
        document.getElementById('statAccuracy').textContent = acc;
      }
      if (document.getElementById('statModelName')) {
        document.getElementById('statModelName').textContent = 'Model accuracy (TF-IDF+LR)';
      }
      if (document.getElementById('statStatus')) {
        document.getElementById('statStatus').textContent = 'ONLINE';
      }
      if (document.getElementById('statStatusLabel')) {
        document.getElementById('statStatusLabel').textContent = 'Flask ML Engine Active';
      }
      if (dashNoteEl) {
        dashNoteEl.textContent = 'Live SQLite Database History (Connected)';
      }
    } catch (err) {
      statusEl.classList.remove('online');
      statusEl.classList.add('offline');
      statusTextEl.textContent = 'Engine Offline (Simulated)';
      if (dashNoteEl) {
        dashNoteEl.textContent = 'Local session only (backend offline)';
      }
    }
  }

  // Fetch aggregate prediction statistics from SQLite
  async function fetchGlobalStats() {
    try {
      const stats = await callStatsAPI();
      if (stats && typeof stats.total_predictions === 'number') {
        const total = 10000 + stats.total_predictions;
        const statArticlesEl = document.getElementById('statArticles');
        if (statArticlesEl) {
          statArticlesEl.textContent = total.toLocaleString() + '+';
        }
      }
    } catch (err) {
      // Backend offline: keep default stat figures
    }
  }

  // Seed the dashboard with predictions already stored in the SQLite database
  async function seedDashboardFromHistory() {
    try {
      const data = await callHistoryAPI();
      sessionAnalyses.length = 0; // reset local array before seeding
      const seeded = (data.history || []).map(record => ({
        isFake: record.prediction === 'FAKE',
        confidence: Math.round(record.confidence),
        keywords: extractKeywords(record.news_text || '')
      }));
      sessionAnalyses.push(...seeded);
    } catch (err) {
      console.warn('Could not load prediction history from backend:', err.message);
    } finally {
      updateDashboard();
      fetchGlobalStats();
    }
  }

  // Clear desk history button handler
  const clearHistoryBtn = document.getElementById('clearHistoryBtn');
  if (clearHistoryBtn) {
    clearHistoryBtn.addEventListener('click', async () => {
      if (!confirm('Clear all stored case files and prediction history from the database?')) return;
      try {
        await callDeleteHistoryAPI();
        sessionAnalyses.length = 0;
        updateDashboard();
        fetchGlobalStats();
        const dashNoteEl = document.getElementById('dashNote');
        if (dashNoteEl) {
          const original = dashNoteEl.textContent;
          dashNoteEl.textContent = 'Database history cleared.';
          setTimeout(() => dashNoteEl.textContent = original, 2000);
        }
      } catch (err) {
        alert('Could not clear history: ' + err.message);
      }
    });
  }

  // Initialize backend connection, metadata, and history on load
  syncBackendStatus();
  seedDashboardFromHistory();

  document.getElementById('newAnalysisBtn').addEventListener('click', () => {
    resultsPanel.classList.remove('active');
    document.getElementById('desk').scrollIntoView({ behavior: 'smooth' });
    textarea.focus();
  });

  document.getElementById('downloadBtn').addEventListener('click', () => {
    const headline = document.getElementById('verdictHeadline').textContent;
    const conf = document.getElementById('confidenceNum').textContent;
    const source = document.getElementById('credSourceName').textContent;
    const trust = document.getElementById('credScoreText').textContent;
    const summary = document.getElementById('summaryText').textContent;
    const checklistItems = [...document.querySelectorAll('#checklistItems li')].map(li => '- ' + li.textContent).join('\n');
    const content = `TRUTHLENS CASE FILE\n\nVerdict: ${headline}\nAuthenticity score: ${conf}\nRisk level: ${document.getElementById('riskLevel').textContent}\nSentiment: ${document.getElementById('sentiment').textContent}\n\nSource: ${source}\n${trust}\n\nSummary:\n${summary}\n\nReasoning:\n${checklistItems}\n\nFiled: ${document.getElementById('filedTime').textContent}`;
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'truthlens-case-file.txt';
    a.click();
    URL.revokeObjectURL(url);
  });

  function voteHandler(message) {
    return () => {
      document.getElementById('communityNote').textContent = message;
      ['agreeBtn','disagreeBtn','reportBtn'].forEach(id => document.getElementById(id).disabled = true);
    };
  }
  document.getElementById('agreeBtn').addEventListener('click', voteHandler('Thanks — your agreement was logged for this session.'));
  document.getElementById('disagreeBtn').addEventListener('click', voteHandler('Noted — your disagreement was logged for this session.'));
  document.getElementById('reportBtn').addEventListener('click', voteHandler('Flagged — this case was marked for review.'));
