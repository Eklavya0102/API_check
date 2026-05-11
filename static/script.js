/* ─────────────────────────────────────────────
   KeyProbe — Frontend Script
   Handles: provider/model selection, key input,
   API test submission, result rendering, toasts
───────────────────────────────────────────── */

/* ── State ── */
const state = {
  providers: [],       // fetched from backend
  selectedProvider: null,
  selectedModel: null,
  lastResult: null,
};

/* ── Element references ── */
const providerSearch  = document.getElementById('provider-search');
const providerList    = document.getElementById('provider-list');
const providerWrapper = document.getElementById('provider-wrapper');
const stepModel       = document.getElementById('step-model');
const modelSelect     = document.getElementById('model-select');
const stepKey         = document.getElementById('step-key');
const apiKeyInput     = document.getElementById('api-key-input');
const toggleVisBtn    = document.getElementById('toggle-visibility');
const eyeOpen         = document.getElementById('eye-open');
const eyeClosed       = document.getElementById('eye-closed');
const pasteBtn        = document.getElementById('paste-btn');
const clearKeyBtn     = document.getElementById('clear-key-btn');
const testBtn         = document.getElementById('test-btn');
const btnText         = testBtn.querySelector('.btn-text');
const btnSpinner      = testBtn.querySelector('.btn-spinner');
const resetBtn        = document.getElementById('reset-btn');
const resultCard      = document.getElementById('result-card');
const resultIcon      = document.getElementById('result-icon');
const resultTitle     = document.getElementById('result-title');
const resultMsg       = document.getElementById('result-msg');
const resultDetails   = document.getElementById('result-details');
const copyResultBtn   = document.getElementById('copy-result-btn');
const toastContainer  = document.getElementById('toast-container');

/* ── Helpers ── */

// Show/hide step with slide-in animation
function showStep(el) {
  el.classList.remove('hidden');
  el.classList.remove('slide-in');
  void el.offsetWidth; // reflow
  el.classList.add('slide-in');
}

function hideStep(el) {
  el.classList.add('hidden');
}

// Provider icon abbreviation
function providerAbbr(name) {
  return name.substring(0, 2).toUpperCase();
}

/* ── Toast system ── */
function showToast(message, type = 'info', duration = 3000) {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span class="toast-dot"></span><span>${message}</span>`;
  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.classList.add('toast-exit');
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

/* ── Load providers from backend ── */
async function loadProviders() {
  try {
    const res = await fetch('/api/providers');
    state.providers = await res.json();
    renderDropdown(state.providers);
  } catch {
    showToast('Failed to load providers — is the server running?', 'error');
  }
}

/* ── Render dropdown list ── */
function renderDropdown(providers) {
  providerList.innerHTML = '';
  if (!providers.length) {
    providerList.innerHTML = `<li class="dropdown-empty">No providers found</li>`;
    return;
  }
  providers.forEach(p => {
    const li = document.createElement('li');
    li.className = 'dropdown-item';
    if (state.selectedProvider?.id === p.id) li.classList.add('selected');
    li.setAttribute('role', 'option');
    li.dataset.id = p.id;
    li.innerHTML = `
      <span class="provider-icon">${providerAbbr(p.name)}</span>
      <span>${p.name}</span>
    `;
    li.addEventListener('click', () => selectProvider(p));
    providerList.appendChild(li);
  });
}

/* ── Open / close dropdown ── */
function openDropdown() {
  providerList.classList.add('open');
  providerWrapper.classList.add('open');
  providerSearch.setAttribute('aria-expanded', 'true');
  highlightedIndex = -1;
}

function closeDropdown() {
  providerList.classList.remove('open');
  providerWrapper.classList.remove('open');
  providerSearch.setAttribute('aria-expanded', 'false');
}

providerSearch.addEventListener('focus', () => {
  providerSearch.value = '';
  openDropdown();
  renderDropdown(state.providers);
});

providerSearch.addEventListener('input', () => {
  const q = providerSearch.value.toLowerCase();
  const filtered = state.providers.filter(p =>
    p.name.toLowerCase().includes(q) || p.id.toLowerCase().includes(q)
  );
  openDropdown();
  renderDropdown(filtered);
  highlightedIndex = -1;
});

// Close on outside click
document.addEventListener('click', e => {
  if (!providerWrapper.contains(e.target)) closeDropdown();
});

/* ── Keyboard nav for dropdown ── */
let highlightedIndex = -1;
providerSearch.addEventListener('keydown', e => {
  const items = [...providerList.querySelectorAll('.dropdown-item')];
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    highlightedIndex = Math.min(highlightedIndex + 1, items.length - 1);
    updateHighlight(items);
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    highlightedIndex = Math.max(highlightedIndex - 1, 0);
    updateHighlight(items);
  } else if (e.key === 'Enter') {
    if (highlightedIndex >= 0 && items[highlightedIndex]) {
      const id = items[highlightedIndex].dataset.id;
      const p = state.providers.find(x => x.id === id);
      if (p) selectProvider(p);
    }
  } else if (e.key === 'Escape') {
    closeDropdown();
    providerSearch.blur();
  }
});

function updateHighlight(items) {
  items.forEach((el, i) => {
    el.classList.toggle('highlighted', i === highlightedIndex);
    if (i === highlightedIndex) el.scrollIntoView({ block: 'nearest' });
  });
}

/* ── Select a provider ── */
function selectProvider(p) {
  state.selectedProvider = p;
  providerSearch.value = p.name;
  closeDropdown();

  // Populate model dropdown
  modelSelect.innerHTML = '';
  p.models.forEach(m => {
    const opt = document.createElement('option');
    opt.value = m;
    opt.textContent = m;
    modelSelect.appendChild(opt);
  });
  state.selectedModel = p.default_model;

  showStep(stepModel);
  showStep(stepKey);
  validateForm();
}

/* ── Model change ── */
modelSelect.addEventListener('change', () => {
  state.selectedModel = modelSelect.value;
  validateForm();
});

/* ── Key input ── */
apiKeyInput.addEventListener('input', () => {
  // Auto-trim leading/trailing spaces
  const trimmed = apiKeyInput.value.trim();
  if (trimmed !== apiKeyInput.value) apiKeyInput.value = trimmed;
  validateForm();
});

apiKeyInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !testBtn.disabled) submitTest();
});

/* ── Toggle visibility ── */
toggleVisBtn.addEventListener('click', () => {
  const isPassword = apiKeyInput.type === 'password';
  apiKeyInput.type = isPassword ? 'text' : 'password';
  eyeOpen.classList.toggle('hidden', isPassword);
  eyeClosed.classList.toggle('hidden', !isPassword);
});

/* ── Paste ── */
pasteBtn.addEventListener('click', async () => {
  try {
    const text = await navigator.clipboard.readText();
    apiKeyInput.value = text.trim();
    validateForm();
    showToast('Key pasted from clipboard', 'success', 2000);
  } catch {
    showToast('Could not access clipboard', 'error', 2000);
  }
});

/* ── Clear key ── */
clearKeyBtn.addEventListener('click', () => {
  apiKeyInput.value = '';
  validateForm();
  apiKeyInput.focus();
});

/* ── Validate form ── */
function validateForm() {
  const hasProvider = !!state.selectedProvider;
  const hasKey = apiKeyInput.value.trim().length > 5;
  testBtn.disabled = !(hasProvider && hasKey);
}

/* ── Submit test ── */
testBtn.addEventListener('click', submitTest);

async function submitTest() {
  const apiKey = apiKeyInput.value.trim();
  if (!apiKey || !state.selectedProvider) return;

  // Loading state
  testBtn.disabled = true;
  btnText.textContent = 'Testing…';
  btnSpinner.classList.remove('hidden');
  resultCard.classList.add('hidden');

  const payload = {
    provider: state.selectedProvider.id,
    model: modelSelect.value || state.selectedProvider.default_model,
    api_key: apiKey,
  };

  try {
    const res = await fetch('/api/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    state.lastResult = data;
    renderResult(data);
  } catch {
    renderResult({
      success: false,
      error_type: 'network_error',
      message: 'Could not reach the testing server. Is the Flask app running?',
      provider: state.selectedProvider.name,
      model: payload.model,
      latency_ms: 0,
      masked_key: '••••••',
    });
  } finally {
    btnText.textContent = 'Test API Key';
    btnSpinner.classList.add('hidden');
    testBtn.disabled = false;
    resetBtn.classList.remove('hidden');
  }
}

/* ── Render result ── */
const ERROR_ICONS = {
  invalid_key:    '🔑',
  permission_error: '🚫',
  quota_exceeded: '📊',
  billing_issue:  '💳',
  invalid_model:  '🤖',
  provider_error: '🛠',
  timeout:        '⏱',
  network_error:  '🌐',
  validation:     '⚠️',
  unknown_error:  '❓',
};

function renderResult(data) {
  resultCard.classList.remove('hidden', 'success', 'error');
  resultCard.classList.add(data.success ? 'success' : 'error');

  if (data.success) {
    resultIcon.textContent = '✅';
    resultTitle.textContent = 'API Key is Working Perfectly';
    showToast(`${data.provider} key validated!`, 'success');
  } else {
    const icon = ERROR_ICONS[data.error_type] || '❌';
    resultIcon.textContent = icon;
    resultTitle.textContent = errorTypeLabel(data.error_type);
    showToast(errorTypeLabel(data.error_type), 'error');
  }

  resultMsg.textContent = data.message || '—';

  // Detail pills
  const pills = [
    { label: 'Provider', val: data.provider || '—' },
    { label: 'Model', val: data.model || '—' },
    { label: 'Latency', val: data.latency_ms ? `${data.latency_ms}ms` : '—' },
    { label: 'Key', val: data.masked_key || '—' },
  ];
  if (data.success && data.meta) {
    if (data.meta.login)    pills.push({ label: 'User', val: data.meta.login });
    if (data.meta.username) pills.push({ label: 'Bot', val: data.meta.username });
  }
  if (!data.success && data.error_type) {
    pills.push({ label: 'Error Code', val: data.error_type });
  }

  resultDetails.innerHTML = pills.map(p => `
    <div class="detail-pill">
      <span class="pill-label">${p.label}</span>
      <span class="pill-val">${escHtml(String(p.val))}</span>
    </div>
  `).join('');

  // Scroll to result
  resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function errorTypeLabel(type) {
  const map = {
    invalid_key:     'Invalid API Key',
    permission_error:'Permission Denied',
    quota_exceeded:  'Quota / Rate Limit Exceeded',
    billing_issue:   'Billing Issue',
    invalid_model:   'Invalid Model',
    provider_error:  'Provider Server Error',
    timeout:         'Request Timed Out',
    network_error:   'Network Error',
    validation:      'Validation Error',
    unknown_error:   'Unknown Error',
  };
  return map[type] || 'Error';
}

function escHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

/* ── Copy result ── */
copyResultBtn.addEventListener('click', () => {
  if (!state.lastResult) return;
  const d = state.lastResult;
  const text = [
    `Status:   ${d.success ? 'SUCCESS' : 'FAILED'}`,
    `Provider: ${d.provider}`,
    `Model:    ${d.model}`,
    `Message:  ${d.message}`,
    `Latency:  ${d.latency_ms}ms`,
    `Key:      ${d.masked_key}`,
    d.error_type ? `Error:    ${d.error_type}` : '',
  ].filter(Boolean).join('\n');

  navigator.clipboard.writeText(text)
    .then(() => showToast('Result copied to clipboard', 'success', 2000))
    .catch(() => showToast('Could not copy to clipboard', 'error', 2000));
});

/* ── Reset ── */
resetBtn.addEventListener('click', () => {
  state.selectedProvider = null;
  state.selectedModel = null;
  state.lastResult = null;

  providerSearch.value = '';
  apiKeyInput.value = '';
  apiKeyInput.type = 'password';
  eyeOpen.classList.remove('hidden');
  eyeClosed.classList.add('hidden');

  hideStep(stepModel);
  hideStep(stepKey);
  resultCard.classList.add('hidden');
  resetBtn.classList.add('hidden');

  testBtn.disabled = true;
  renderDropdown(state.providers);

  providerSearch.focus();
});

/* ── Init ── */
loadProviders();
