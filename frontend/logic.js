(() => {
  const state = { userId: null, selectedClaims: new Set() };

  const $ = id => document.getElementById(id);
  const show = el => el.classList.remove('hidden');
  const hide = el => el.classList.add('hidden');

  //  SECTIONS 
  const hero          = document.querySelector('.hero');
  const processingEl  = $('processingSection');
  const claimSel      = $('claimSelectionSection');
  const resultsEl     = $('resultsSection');

  function showOnly(section) {
    [processingEl, claimSel, resultsEl].forEach(s => s !== section && hide(s));
    if (section) show(section);
  }

  //  TOAST 
  function toast(msg, type = 'info') {
    const icons = { info: 'ℹ', success: '✓', error: '✕' };
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.innerHTML = `<span class="toast-icon">${icons[type]}</span><span class="toast-msg">${msg}</span>`;
    $('toastContainer').appendChild(t);
    setTimeout(() => { t.classList.add('removing'); setTimeout(() => t.remove(), 300); }, 4000);
  }

  //  STEP PROGRESS 
  const steps = ['step-classify', 'step-extract', 'step-search', 'step-evidence', 'step-verdict'];
  const stepMeta = [
    ['Analysing input…',       'Classifying your input and preparing the pipeline'],
    ['Extracting claims…',     'Identifying verifiable factual statements'],
    ['Searching sources…',     'Querying fact-check databases and news sources'],
    ['Extracting evidence…',   'Embedding and ranking relevant passages'],
    ['Generating verdict…',    'LLM reasoning over evidence chunks'],
  ];
  let _stepTimer = null;

  function setStep(idx) {
    steps.forEach((id, i) => {
      $(id).className = 'step-item' + (i < idx ? ' done' : i === idx ? ' active' : '');
    });
    const [stage, detail] = stepMeta[Math.min(idx, stepMeta.length - 1)];
    $('processingStage').textContent = stage;
    $('processingDetail').textContent = detail;
  }

  function startStepTimer() {
    let idx = 0;
    setStep(idx);
    _stepTimer = setInterval(() => {
      idx = Math.min(idx + 1, steps.length - 1);
      setStep(idx);
      if (idx === steps.length - 1) clearInterval(_stepTimer);
    }, 3000);
  }

  function stopStepTimer() {
    clearInterval(_stepTimer);
    _stepTimer = null;
  }

  function setProcessingText(stage, detail) {
    $('processingStage').textContent = stage;
    $('processingDetail').textContent = detail;
  }

  //  SESSION SETUP 
  async function setup() {
    const uid = crypto.randomUUID();
    try {
      const r = await fetch('/api/setup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userid: uid })
      });
      if (!r.ok) throw new Error();
      state.userId = uid;
    } catch {
      toast('Failed to initialise session. Refresh to retry.', 'error');
    }
  }

  //  CHECK 
  async function runCheck() {
    const input = $('mainInput').value.trim();
    if (!input) { toast('Enter a claim or URL first.', 'error'); return; }
    if (!state.userId) { toast('Session not ready. Refresh.', 'error'); return; }

    resetUI();
    showOnly(processingEl);
    startStepTimer();

    try {
      const r = await fetch('/api/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userid: state.userId, input })
      });
      stopStepTimer();
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();

      if (Array.isArray(data)) {
        showClaimSelection(data);
      } else {
        showResults([data]);
      }
    } catch (e) {
      stopStepTimer();
      showOnly(null);
      toast(`Check failed: ${e.message}`, 'error');
    }
  }

  //  CLAIM SELECTION 
  function showClaimSelection(claims) {
    state.selectedClaims.clear();
    const grid = $('claimsGrid');
    grid.innerHTML = '';
    claims.forEach(claim => {
      const card = document.createElement('button');
      card.className = 'claim-card';
      card.innerHTML = `
        <div class="claim-checkbox">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
        </div>
        <span class="claim-text">${escHtml(claim)}</span>`;
      card.addEventListener('click', () => toggleClaim(card, claim));
      grid.appendChild(card);
    });
    updateSelectionCount();
    showOnly(claimSel);
  }

  function toggleClaim(card, claim) {
    if (state.selectedClaims.has(claim)) {
      state.selectedClaims.delete(claim);
      card.classList.remove('selected');
    } else {
      state.selectedClaims.add(claim);
      card.classList.add('selected');
    }
    updateSelectionCount();
  }

  function updateSelectionCount() {
    const n = state.selectedClaims.size;
    $('selectionCount').textContent = `${n} selected`;
    const btn = $('verifyBtn');
    btn.disabled = n === 0;
    btn.setAttribute('aria-disabled', n === 0);
  }

  //  VERIFY 
  async function runVerify() {
    const claims = [...state.selectedClaims];
    if (!claims.length) return;

    showOnly(processingEl);
    startStepTimer();

    try {
      const r = await fetch('/api/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userid: state.userId, claims })
      });
      stopStepTimer();
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      showResults(data);
    } catch (e) {
      stopStepTimer();
      showOnly(null);
      toast(`Verify failed: ${e.message}`, 'error');
    }
  }

  //  RESULTS 
  function showResults(results) {
    const counts = {};
    results.forEach(r => {
      const v = (r.verdict || 'error').toLowerCase();
      counts[v] = (counts[v] || 0) + 1;
    });

    $('resultsMeta').textContent = `${results.length} claim${results.length !== 1 ? 's' : ''} verified`;

    const summary = $('resultsSummary');
    summary.innerHTML = Object.entries(counts).map(([v, n]) =>
      `<div class="summary-pill ${v}"><span class="summary-dot"></span>${n} ${cap(v)}</div>`
    ).join('');

    const list = $('resultsList');
    list.innerHTML = results.map(r => buildResultCard(r)).join('');

    showOnly(resultsEl);
  }

  function buildResultCard(r) {
    const verdict = (r.verdict || 'error').toLowerCase();
    const sources = (r.sources_used || []).map(url =>
      `<a class="source-link" href="${escAttr(url)}" target="_blank" rel="noopener noreferrer">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
        ${escHtml(hostname(url))}
      </a>`
    ).join('');

    return `
      <div class="result-card verdict-${verdict}" role="listitem">
        <div class="result-header">
          <div class="result-claim-wrap">
            <div class="result-claim-label">Claim</div>
            <div class="result-claim-text">${escHtml(r.claim || '')}</div>
          </div>
          <div class="verdict-badge ${verdict}">
            <span class="verdict-icon"></span>
            ${escHtml(cap(r.verdict || 'Error'))}
          </div>
        </div>
        <div class="result-body">
          <div class="result-explanation-label">Explanation</div>
          <div class="result-explanation">${escHtml(r.explanation || '')}</div>
          ${sources ? `<div class="result-sources-inline"><span class="result-sources-label">Sources</span>${sources}</div>` : ''}
        </div>
        <div class="result-footer">
          <span class="result-method">
            <svg class="result-method-icon" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
            ${escHtml(r.method || '')}
          </span>
        </div>
      </div>`;
  }

  //  RESET 
  function resetUI() {
    state.selectedClaims.clear();
    $('claimsGrid').innerHTML = '';
    $('resultsList').innerHTML = '';
    $('resultsSummary').innerHTML = '';
    steps.forEach(id => { $(id).className = 'step-item'; });
  }

  function fullReset() {
    resetUI();
    $('mainInput').value = '';
    showOnly(null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  //  SETTINGS PANEL 
  function openSettings() {
    $('settingsPanel').classList.add('open');
    $('settingsBackdrop').classList.add('visible');
    $('toggleSettings').setAttribute('aria-expanded', 'true');
    $('settingsPanel').setAttribute('aria-hidden', 'false');
  }
  function closeSettings() {
    $('settingsPanel').classList.remove('open');
    $('settingsBackdrop').classList.remove('visible');
    $('toggleSettings').setAttribute('aria-expanded', 'false');
    $('settingsPanel').setAttribute('aria-hidden', 'true');
  }

  async function saveApiKeys() {
    if (!state.userId) return;
    const groq = $('groqApiInput').value.trim() || null;
    const serper = $('serperApiInput').value.trim() || null;
    try {
      const r = await fetch('/api/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userid: state.userId, usergroq: groq, user_SerperDev: serper })
      });
      const ok = r.ok;
      setSettingsStatus(ok ? 'Keys saved.' : 'Failed to save.', ok ? 'success' : 'error');
    } catch {
      setSettingsStatus('Network error.', 'error');
    }
  }

  async function clearApiKeys() {
    if (!state.userId) return;
    $('groqApiInput').value = '';
    $('serperApiInput').value = '';
    try {
      await fetch('/api/clear-Api', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userid: state.userId })
      });
      setSettingsStatus('Keys cleared.', 'success');
    } catch {
      setSettingsStatus('Network error.', 'error');
    }
  }

  function setSettingsStatus(msg, type) {
    const el = $('settingsStatus');
    el.textContent = msg;
    el.className = `settings-status ${type}`;
    setTimeout(() => { el.textContent = ''; el.className = 'settings-status'; }, 3000);
  }

  //  HELPERS 
  function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function escAttr(s) { return escHtml(s); }
  function cap(s) { return s.charAt(0).toUpperCase() + s.slice(1); }
  function hostname(url) {
    try { return new URL(url).hostname.replace('www.', ''); } catch { return url; }
  }

  //  VISIBILITY TOGGLES 
  document.querySelectorAll('.field-toggle-vis').forEach(btn => {
    btn.addEventListener('click', () => {
      const inp = $(btn.dataset.target);
      inp.type = inp.type === 'password' ? 'text' : 'password';
    });
  });

  //  EXAMPLE CHIPS 
  document.querySelectorAll('.example-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      $('mainInput').value = chip.dataset.claim;
      $('mainInput').focus();
    });
  });

  //  WIRE EVENTS 
  $('checkBtn').addEventListener('click', runCheck);
  $('mainInput').addEventListener('keydown', e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) runCheck(); });
  $('verifyBtn').addEventListener('click', runVerify);
  $('newCheckBtn').addEventListener('click', fullReset);
  $('toggleSettings').addEventListener('click', openSettings);
  $('closeSettings').addEventListener('click', closeSettings);
  $('settingsBackdrop').addEventListener('click', closeSettings);
  $('saveApiKeys').addEventListener('click', saveApiKeys);
  $('clearApiKeys').addEventListener('click', clearApiKeys);

  //  EXIT CLEANUP 
  window.addEventListener('beforeunload', () => {
    if (!state.userId) return;
    const data = JSON.stringify({ userid: state.userId });
    navigator.sendBeacon('/api/delete-user', data);
  });

  //  INIT 
  setup();
})();