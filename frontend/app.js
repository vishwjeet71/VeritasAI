/**
 * VeritasAI — Frontend Application
 * Handles: /api/check → /api/verify flow, all UI states, loading sequences
 */

/* DOM References */
const $input         = document.getElementById('main-input');
const $charCounter   = document.getElementById('char-counter');
const $clearBtn      = document.getElementById('clear-btn');
const $submitBtn     = document.getElementById('submit-btn');

const $loadingSection = document.getElementById('loading-section');
const $loadingMsg     = document.getElementById('loading-message');
const $loadingSteps   = document.getElementById('loading-steps');

const $claimsSection  = document.getElementById('claims-section');
const $claimsList     = document.getElementById('claims-list');
const $selectAllBtn   = document.getElementById('select-all-btn');
const $deselectAllBtn = document.getElementById('deselect-all-btn');
const $selectionCount = document.getElementById('selection-count');
const $verifyBtn      = document.getElementById('verify-btn');

const $resultsSection = document.getElementById('results-section');
const $resultsMeta    = document.getElementById('results-meta');
const $resultsSummary = document.getElementById('results-summary');
const $resultsGrid    = document.getElementById('results-grid');
const $newCheckBtn    = document.getElementById('new-check-btn');

const $errorSection   = document.getElementById('error-section');
const $errorTitle     = document.getElementById('error-title');
const $errorMessage   = document.getElementById('error-message');
const $errorRetryBtn  = document.getElementById('error-retry-btn');

/* State */
const state = {
  currentInput: '',
  extractedClaims: [],
  selectedClaims: new Set(),
  verificationResults: [],
  isLoading: false,
};

/* Loading Messages */
const LOADING_SEQUENCES = {
  check: [
    { msg: 'Analyzing input...', step: 'Detecting input type' },
    { msg: 'Extracting claims...', step: 'Parsing text & identifying assertions' },
    { msg: 'Fetching article content...', step: 'Scraping article via trafilatura' },
    { msg: 'Processing article...', step: 'Extracting key claims from article' },
  ],
  verify: [
    { msg: 'Searching credible sources...', step: 'Querying fact-check databases' },
    { msg: 'Retrieving evidence...', step: 'Fetching relevant web sources' },
    { msg: 'Building semantic context...', step: 'Embedding & chunking evidence' },
    { msg: 'Generating verdict...', step: 'LLM reasoning over collected evidence' },
  ],
};

/* Helpers */
const show = el  => el.classList.remove('hidden');
const hide = el  => el.classList.add('hidden');
const isHidden   = el => el.classList.contains('hidden');

function isURL(str) {
  try {
    const url = new URL(str.trim());
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch {
    return false;
  }
}

function normalizeVerdict(raw) {
  if (!raw) return 'unverifiable';
  const v = raw.toLowerCase().trim();
  if (v.includes('support'))      return 'supported';
  if (v.includes('contradict'))   return 'contradicted';
  if (v.includes('inconclu'))     return 'inconclusive';
  if (v.includes('unverif'))      return 'unverifiable';
  if (v.includes('error'))        return 'error';
  return 'unverifiable';
}

function verdictIcon(verdict) {
  const icons = {
    supported:    `<svg width="11" height="11" viewBox="0 0 11 11" fill="none"><path d="M2 5.5l2.5 2.5L9 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    contradicted: `<svg width="11" height="11" viewBox="0 0 11 11" fill="none"><path d="M2 2l7 7M9 2L2 9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
    inconclusive: `<svg width="11" height="11" viewBox="0 0 11 11" fill="none"><path d="M5.5 3v2.5l1.5 1.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="5.5" cy="5.5" r="4" stroke="currentColor" stroke-width="1.3"/></svg>`,
    unverifiable: `<svg width="11" height="11" viewBox="0 0 11 11" fill="none"><circle cx="5.5" cy="5.5" r="4" stroke="currentColor" stroke-width="1.3"/><path d="M5.5 5V3.5M5.5 7v.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
    error:        `<svg width="11" height="11" viewBox="0 0 11 11" fill="none"><circle cx="5.5" cy="5.5" r="4" stroke="currentColor" stroke-width="1.3"/><path d="M5.5 3.5v2M5.5 7v.3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  };
  return icons[verdict] || icons.unverifiable;
}

/* Loading Orchestration */
let loadingIntervalId = null;
let loadingStepIndex  = 0;
let completedSteps    = [];

function startLoading(type) {
  state.isLoading = true;
  $submitBtn.disabled = true;

  hideAllSections();
  show($loadingSection);

  const sequence = LOADING_SEQUENCES[type] || LOADING_SEQUENCES.check;
  loadingStepIndex = 0;
  completedSteps   = [];
  $loadingSteps.innerHTML = '';
  $loadingMsg.textContent = sequence[0].msg;

  // Render initial step indicators
  sequence.forEach((item, i) => {
    const el = document.createElement('div');
    el.className = 'loading-step';
    el.id = `loading-step-${i}`;
    el.style.animationDelay = `${i * 60}ms`;
    el.innerHTML = `
      <span class="step-icon" id="step-icon-${i}">·</span>
      <span>${item.step}</span>
    `;
    $loadingSteps.appendChild(el);
  });

  // Activate first step
  updateLoadingStep(0, sequence);

  loadingIntervalId = setInterval(() => {
    loadingStepIndex++;
    if (loadingStepIndex < sequence.length) {
      updateLoadingStep(loadingStepIndex, sequence);
    }
  }, 2200);
}

function updateLoadingStep(index, sequence) {
  const item = sequence[index];
  if (!item) return;

  // Update message with fade effect
  $loadingMsg.style.animation = 'none';
  void $loadingMsg.offsetWidth;
  $loadingMsg.style.animation = 'loading-text-fade 0.4s ease';
  $loadingMsg.textContent = item.msg;

  // Mark previous step as done
  if (index > 0) {
    const prev = document.getElementById(`loading-step-${index - 1}`);
    if (prev) {
      prev.classList.remove('active');
      prev.classList.add('done');
      const icon = document.getElementById(`step-icon-${index - 1}`);
      if (icon) icon.innerHTML = `<svg width="11" height="11" viewBox="0 0 11 11" fill="none"><path d="M2 5.5l2.5 2.5L9 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
    }
  }

  // Activate current step
  const curr = document.getElementById(`loading-step-${index}`);
  if (curr) {
    curr.classList.add('active');
    const icon = document.getElementById(`step-icon-${index}`);
    if (icon) icon.innerHTML = `<div style="width:10px;height:10px;border-radius:50%;border:1.5px solid currentColor;border-top-color:transparent;animation:scan-rotate 0.8s linear infinite;"></div>`;
  }
}

function stopLoading() {
  state.isLoading = false;
  $submitBtn.disabled = false;
  if (loadingIntervalId) {
    clearInterval(loadingIntervalId);
    loadingIntervalId = null;
  }
  hide($loadingSection);
}

/* Section Visibility */
function hideAllSections() {
  hide($loadingSection);
  hide($claimsSection);
  hide($resultsSection);
  hide($errorSection);
}

/* API: /api/check */
async function apiCheck(input) {
  const res = await fetch('/api/check', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ input: input.trim() }),
  });

  if (!res.ok) {
    const errBody = await res.text();
    throw new Error(`Server error ${res.status}: ${errBody || res.statusText}`);
  }

  return res.json();
}

/* API: /api/verify */
async function apiVerify(claims) {
  const res = await fetch('/api/verify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ claims }),
  });

  if (!res.ok) {
    const errBody = await res.text();
    throw new Error(`Server error ${res.status}: ${errBody || res.statusText}`);
  }

  return res.json();
}

/* Response Routing */
function handleCheckResponse(data) {
  // Array of strings → claim selection UI
  if (Array.isArray(data) && data.length > 0 && typeof data[0] === 'string') {
    state.extractedClaims = data;
    renderClaimsSection(data);
    return;
  }

  // Array of result objects → already verified
  if (Array.isArray(data) && data.length > 0 && typeof data[0] === 'object') {
    renderResults(data);
    return;
  }

  // Single result object
  if (data && typeof data === 'object' && data.verdict) {
    renderResults([data]);
    return;
  }

  // Empty array — no claims found
  if (Array.isArray(data) && data.length === 0) {
    showError('No Claims Found', 'VeritasAI could not extract any verifiable claims from this input. Try rephrasing or providing a different article.');
    return;
  }

  showError('Unexpected Response', 'The server returned an unrecognized response format. Please try again.');
}

/* Claims Section Rendering */
function renderClaimsSection(claims) {
  state.selectedClaims.clear();
  $claimsList.innerHTML = '';

  claims.forEach((claim, i) => {
    const item = document.createElement('div');
    item.className = 'claim-item';
    item.dataset.index = i;
    item.style.animationDelay = `${i * 55}ms`;
    item.setAttribute('role', 'checkbox');
    item.setAttribute('aria-checked', 'false');
    item.setAttribute('tabindex', '0');

    item.innerHTML = `
      <div class="claim-checkbox-box" aria-hidden="true"></div>
      <span class="claim-index">${String(i + 1).padStart(2, '0')}</span>
      <span class="claim-text">${escapeHTML(claim)}</span>
    `;

    item.addEventListener('click', () => toggleClaim(i, claim, item));
    item.addEventListener('keydown', (e) => {
      if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        toggleClaim(i, claim, item);
      }
    });

    $claimsList.appendChild(item);
  });

  updateSelectionCount();
  hide($loadingSection);
  show($claimsSection);
  $claimsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function toggleClaim(index, claim, el) {
  if (state.selectedClaims.has(index)) {
    state.selectedClaims.delete(index);
    el.classList.remove('selected');
    el.setAttribute('aria-checked', 'false');
  } else {
    state.selectedClaims.add(index);
    el.classList.add('selected');
    el.setAttribute('aria-checked', 'true');
  }
  updateSelectionCount();
}

function updateSelectionCount() {
  const count = state.selectedClaims.size;
  $selectionCount.textContent = `${count} selected`;
  $verifyBtn.disabled = count === 0;
}

/* Results Rendering */
function renderResults(results) {
  state.verificationResults = results;
  $resultsGrid.innerHTML = '';
  $resultsSummary.innerHTML = '';

  const ts = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  $resultsMeta.textContent = `${results.length} claim${results.length !== 1 ? 's' : ''} · ${ts}`;

  // Summary pills
  const counts = {};
  results.forEach(r => {
    const v = normalizeVerdict(r.verdict);
    counts[v] = (counts[v] || 0) + 1;
  });

  Object.entries(counts).forEach(([verdict, count]) => {
    const pill = document.createElement('span');
    pill.className = `summary-pill ${verdict}`;
    pill.style.cssText = getSummaryPillStyle(verdict);
    pill.innerHTML = `${verdictIcon(verdict)} ${count} ${capitalizeFirst(verdict)}`;
    $resultsSummary.appendChild(pill);
  });

  // Result cards
  results.forEach((result, i) => {
    const card = buildResultCard(result, i);
    $resultsGrid.appendChild(card);
  });

  hide($claimsSection);
  hide($loadingSection);
  show($resultsSection);
  $resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function getSummaryPillStyle(verdict) {
  const styles = {
    supported:    'color:var(--v-supported);background:var(--v-supported-bg);border-color:var(--v-supported-border);',
    contradicted: 'color:var(--v-contradicted);background:var(--v-contradicted-bg);border-color:var(--v-contradicted-border);',
    inconclusive: 'color:var(--v-inconclusive);background:var(--v-inconclusive-bg);border-color:var(--v-inconclusive-border);',
    unverifiable: 'color:var(--v-unverifiable);background:var(--v-unverifiable-bg);border-color:var(--v-unverifiable-border);',
    error:        'color:var(--v-error);background:var(--v-error-bg);border-color:var(--v-error-border);',
  };
  return styles[verdict] || styles.unverifiable;
}

function buildResultCard(result, delayIndex) {
  const verdict    = normalizeVerdict(result.verdict);
  const claim      = result.claim       || 'Unknown claim';
  const explanation = result.explanation || 'No explanation provided.';
  const method     = result.method      || 'unknown';
  const sources    = Array.isArray(result.sources_used) ? result.sources_used : [];

  const card = document.createElement('div');
  card.className = 'result-card';
  card.dataset.verdict = verdict;
  card.style.animationDelay = `${delayIndex * 80}ms`;

  const sourcesHTML = sources.length > 0
    ? sources.map((url, i) => `
        <a href="${escapeAttr(url)}" target="_blank" rel="noopener noreferrer" class="source-link">
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
            <path d="M5 2H2.5A1.5 1.5 0 0 0 1 3.5v7A1.5 1.5 0 0 0 2.5 12h7A1.5 1.5 0 0 0 11 10.5V8M7 1h5v5M7.5 5.5L12 1" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          ${escapeHTML(truncateURL(url, 72))}
        </a>
      `).join('')
    : `<span class="no-sources">No sources available for this claim.</span>`;

  card.innerHTML = `
    <div class="result-card-header">
      <p class="result-claim-text">${escapeHTML(claim)}</p>
      <span class="verdict-badge ${verdict}" aria-label="Verdict: ${capitalizeFirst(verdict)}">
        ${verdictIcon(verdict)}
        ${capitalizeFirst(verdict)}
      </span>
    </div>
    <div class="result-card-body">
      <div class="result-row">
        <span class="result-row-label">
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
            <path d="M1.5 6.5h10M7 2l4.5 4.5L7 11" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          Analysis
        </span>
        <p class="result-explanation">${escapeHTML(explanation)}</p>
      </div>
      <div class="result-row">
        <span class="result-row-label">
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
            <rect x="1" y="1" width="11" height="11" rx="2" stroke="currentColor" stroke-width="1.2" fill="none"/>
            <path d="M4 6.5h5M4 4.5h5M4 8.5h3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
          </svg>
          Method
        </span>
        <span class="method-tag">
          <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
            <circle cx="5.5" cy="5.5" r="4" stroke="currentColor" stroke-width="1.2"/>
            <path d="M5.5 3.5v2l1.3 1.3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
          </svg>
          ${escapeHTML(method)}
        </span>
      </div>
      ${sources.length > 0 || true ? `
      <div class="result-row">
        <span class="result-row-label">
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
            <path d="M5 2H2.5A1.5 1.5 0 0 0 1 3.5v7A1.5 1.5 0 0 0 2.5 12h7A1.5 1.5 0 0 0 11 10.5V8M7 1h5v5M7.5 5.5L12 1" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          Sources (${sources.length})
        </span>
        <div class="sources-list">${sourcesHTML}</div>
      </div>` : ''}
    </div>
  `;

  return card;
}

/* Error Handling */
function showError(title, message) {
  stopLoading();
  $errorTitle.textContent   = title   || 'Something went wrong';
  $errorMessage.textContent = message || 'Please try again.';
  hideAllSections();
  show($errorSection);
  $errorSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

/* Main Submit Handler */
async function handleSubmit() {
  const raw = $input.value.trim();

  if (!raw) {
    $input.focus();
    $input.style.borderColor = 'rgba(248, 113, 113, 0.4)';
    setTimeout(() => { $input.style.borderColor = ''; }, 1200);
    return;
  }

  state.currentInput = raw;
  const isUrl = isURL(raw);

  startLoading(isUrl ? 'check' : 'check');

  try {
    const data = await apiCheck(raw);
    stopLoading();
    handleCheckResponse(data);
  } catch (err) {
    console.error('[VeritasAI] /api/check error:', err);
    const isNetworkErr = err.message.includes('Failed to fetch') || err.message.includes('NetworkError');
    showError(
      isNetworkErr ? 'Connection Failed' : 'Request Failed',
      isNetworkErr
        ? 'Could not reach the VeritasAI server. Make sure the backend is running and accessible.'
        : err.message || 'An unexpected error occurred. Please try again.'
    );
  }
}

/* Verify Button Handler */
async function handleVerify() {
  if (state.selectedClaims.size === 0) return;

  const selectedClaims = [...state.selectedClaims].map(i => state.extractedClaims[i]);

  startLoading('verify');

  try {
    const results = await apiVerify(selectedClaims);
    stopLoading();

    if (!Array.isArray(results)) {
      // Might be a single result object
      if (results && typeof results === 'object' && results.verdict) {
        renderResults([results]);
      } else {
        showError('Unexpected Response', 'The verification endpoint returned an unrecognized format.');
      }
      return;
    }

    if (results.length === 0) {
      showError('No Results', 'Verification returned no results. This may be a backend issue — please try again.');
      return;
    }

    renderResults(results);
  } catch (err) {
    console.error('[VeritasAI] /api/verify error:', err);
    const isNetworkErr = err.message.includes('Failed to fetch') || err.message.includes('NetworkError');
    showError(
      isNetworkErr ? 'Connection Failed' : 'Verification Failed',
      isNetworkErr
        ? 'Could not reach the VeritasAI server. Make sure the backend is running.'
        : err.message || 'An unexpected error during verification. Please try again.'
    );
  }
}

/* Reset */
function resetApp() {
  state.currentInput        = '';
  state.extractedClaims     = [];
  state.verificationResults = [];
  state.selectedClaims.clear();

  hideAllSections();
  $input.value = '';
  $charCounter.textContent = '0 characters';
  $claimsList.innerHTML    = '';
  $resultsGrid.innerHTML   = '';
  $resultsSummary.innerHTML = '';
  $loadingSteps.innerHTML  = '';

  $input.focus();
  document.getElementById('hero').scrollIntoView({ behavior: 'smooth' });
}

/* Select All / Deselect All */
function selectAll() {
  const items = $claimsList.querySelectorAll('.claim-item');
  items.forEach((item, i) => {
    if (!state.selectedClaims.has(i)) {
      state.selectedClaims.add(i);
      item.classList.add('selected');
      item.setAttribute('aria-checked', 'true');
    }
  });
  updateSelectionCount();
}

function deselectAll() {
  const items = $claimsList.querySelectorAll('.claim-item');
  items.forEach((item, i) => {
    state.selectedClaims.delete(i);
    item.classList.remove('selected');
    item.setAttribute('aria-checked', 'false');
  });
  updateSelectionCount();
}

/* Utility Functions */
function escapeHTML(str) {
  if (typeof str !== 'string') return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function escapeAttr(str) {
  if (typeof str !== 'string') return '#';
  return str.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function capitalizeFirst(str) {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function truncateURL(url, maxLen) {
  if (!url) return '';
  if (url.length <= maxLen) return url;
  const half = Math.floor(maxLen / 2) - 2;
  return url.slice(0, half) + '...' + url.slice(-half);
}

/* Char Counter */
$input.addEventListener('input', () => {
  const len = $input.value.length;
  $charCounter.textContent = `${len} character${len !== 1 ? 's' : ''}`;
});

/* Enter key shortcut (Ctrl+Enter or Cmd+Enter) */
$input.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault();
    if (!state.isLoading) handleSubmit();
  }
});

/* Event Listeners */
$submitBtn.addEventListener('click', () => {
  if (!state.isLoading) handleSubmit();
});

$clearBtn.addEventListener('click', () => {
  $input.value = '';
  $charCounter.textContent = '0 characters';
  $input.focus();
});

$selectAllBtn.addEventListener('click', selectAll);
$deselectAllBtn.addEventListener('click', deselectAll);

$verifyBtn.addEventListener('click', () => {
  if (!state.isLoading) handleVerify();
});

$newCheckBtn.addEventListener('click', resetApp);
$errorRetryBtn.addEventListener('click', () => {
  hide($errorSection);
  $input.focus();
});

/* Init */
(function init() {
  hideAllSections();
  $input.focus();

  // Add subtle submit hint to textarea placeholder
  if (window.navigator.platform.includes('Mac')) {
    $input.setAttribute('placeholder',
      'e.g. "Scientists discovered water on Mars in 2024"\nor paste a news article URL...\n\n⌘+Enter to submit'
    );
  } else {
    $input.setAttribute('placeholder',
      'e.g. "Scientists discovered water on Mars in 2024"\nor paste a news article URL...\n\nCtrl+Enter to submit'
    );
  }
})();