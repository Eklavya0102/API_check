/* ─────────────────────────────────────────────
   KeyProbe — Frontend Script
   - Provider: searchable dropdown
   - Model: searchable + custom entry
   - Result: modal popup overlay
───────────────────────────────────────────── */

const state = {
  providers: [],
  selectedProvider: null,
  selectedModel: null,
  lastResult: null,
};

/* ── Element refs ── */
const providerSearch  = document.getElementById('provider-search');
const providerList    = document.getElementById('provider-list');
const providerWrapper = document.getElementById('provider-wrapper');
const stepModel       = document.getElementById('step-model');
const modelSearch     = document.getElementById('model-search');
const modelList       = document.getElementById('model-list');
const modelWrapper    = document.getElementById('model-wrapper');
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
const toastContainer  = document.getElementById('toast-container');

/* Modal refs */
const modalOverlay    = document.getElementById('modal-overlay');
const modalBox        = document.getElementById('modal-box');
const modalClose      = document.getElementById('modal-close');
const modalIcon       = document.getElementById('modal-icon');
const modalTitle      = document.getElementById('modal-title');
const modalMsg        = document.getElementById('modal-msg');
const modalDetails    = document.getElementById('modal-details');
const modalExtra      = document.getElementById('modal-extra');
const modalCopyBtn    = document.getElementById('modal-copy-btn');
const modalTestAgain  = document.getElementById('modal-test-again');

/* ── Utilities ── */
const showStep = el => { el.classList.remove('hidden','slide-in'); void el.offsetWidth; el.classList.add('slide-in'); };
const hideStep = el => el.classList.add('hidden');
const escHtml  = s  => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const providerAbbr = name => name.substring(0,2).toUpperCase();

/* ── Toast ── */
function showToast(message, type = 'info', duration = 3200) {
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.innerHTML = `<span class="toast-dot"></span><span>${escHtml(message)}</span>`;
  toastContainer.appendChild(t);
  setTimeout(() => { t.classList.add('toast-exit'); setTimeout(() => t.remove(), 280); }, duration);
}

/* ─────────────────────────────────────────────
   GENERIC DROPDOWN FACTORY
───────────────────────────────────────────── */
function makeDropdown(searchEl, listEl, wrapperEl) {
  let idx = -1;
  const open  = () => {
    listEl.classList.add('open');
    wrapperEl.classList.add('open');
    searchEl.setAttribute('aria-expanded','true');
    idx = -1;
    // Boost the parent field-group above siblings so the dropdown
    // isn't hidden behind elements that appear later in the DOM
    const fg = wrapperEl.closest('.field-group');
    if (fg) fg.classList.add('fg-open');
  };
  const close = () => {
    listEl.classList.remove('open');
    wrapperEl.classList.remove('open');
    searchEl.setAttribute('aria-expanded','false');
    const fg = wrapperEl.closest('.field-group');
    if (fg) fg.classList.remove('fg-open');
  };
  const items = () => [...listEl.querySelectorAll('.dropdown-item')];
  const highlight = list => list.forEach((el,i) => { el.classList.toggle('highlighted', i===idx); if(i===idx) el.scrollIntoView({block:'nearest'}); });

  searchEl.addEventListener('keydown', e => {
    const list = items();
    if (e.key === 'ArrowDown') { e.preventDefault(); idx = Math.min(idx+1, list.length-1); highlight(list); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); idx = Math.max(idx-1, 0); highlight(list); }
    else if (e.key === 'Escape') { close(); searchEl.blur(); }
  });

  return { open, close, items, getIdx: () => idx };
}

/* ─────────────────────────────────────────────
   PROVIDER DROPDOWN
───────────────────────────────────────────── */
const providerDD = makeDropdown(providerSearch, providerList, providerWrapper);

function renderProviderList(providers) {
  providerList.innerHTML = '';
  if (!providers.length) { providerList.innerHTML = `<li class="dropdown-empty">No providers found</li>`; return; }
  providers.forEach(p => {
    const li = document.createElement('li');
    li.className = 'dropdown-item' + (state.selectedProvider?.id === p.id ? ' selected' : '');
    li.setAttribute('role','option');
    li.dataset.id = p.id;
    li.innerHTML = `<span class="provider-icon">${providerAbbr(p.name)}</span><span>${escHtml(p.name)}</span>`;
    li.addEventListener('click', () => selectProvider(p));
    providerList.appendChild(li);
  });
}

providerSearch.addEventListener('focus', () => { providerSearch.value = ''; providerDD.open(); renderProviderList(state.providers); });
providerSearch.addEventListener('input', () => {
  const q = providerSearch.value.toLowerCase();
  providerDD.open();
  renderProviderList(state.providers.filter(p => p.name.toLowerCase().includes(q) || p.id.includes(q)));
});
providerSearch.addEventListener('keydown', e => {
  if (e.key === 'Enter') {
    const list = providerDD.items(); const i = providerDD.getIdx();
    if (i >= 0 && list[i]) { const p = state.providers.find(x => x.id === list[i].dataset.id); if (p) selectProvider(p); }
  }
});

function selectProvider(p) {
  state.selectedProvider = p;
  providerSearch.value = p.name;
  providerDD.close();
  populateModelDropdown(p.models, p.default_model);
  showStep(stepModel);
  showStep(stepKey);
  validateForm();
}

document.addEventListener('click', e => {
  if (!providerWrapper.contains(e.target)) providerDD.close();
  if (!modelWrapper.contains(e.target)) modelDD.close();
});

/* ─────────────────────────────────────────────
   MODEL DROPDOWN — fully searchable + custom
───────────────────────────────────────────── */
const modelDD = makeDropdown(modelSearch, modelList, modelWrapper);
let currentModels = [];

function populateModelDropdown(models, defaultModel) {
  currentModels = models;
  if (models[0] === 'N/A') {
    modelSearch.value = 'N/A — not required';
    modelSearch.disabled = true;
    state.selectedModel = 'N/A';
    modelList.innerHTML = `<li class="dropdown-empty">No model selection needed for this provider</li>`;
    return;
  }
  modelSearch.disabled = false;
  state.selectedModel = defaultModel;
  modelSearch.value = defaultModel;
  renderModelList('');
  validateForm();
}

function renderModelList(query) {
  modelList.innerHTML = '';
  const q = query.trim().toLowerCase();
  const filtered = currentModels.filter(m => m !== 'N/A' && (q === '' || m.toLowerCase().includes(q)));

  filtered.forEach(m => {
    const li = document.createElement('li');
    li.className = 'dropdown-item' + (state.selectedModel === m ? ' selected' : '');
    li.setAttribute('role','option');
    li.dataset.model = m;
    li.innerHTML = `
      <span class="model-icon">
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="2" y="2" width="5" height="5" rx="1"/><rect x="9" y="2" width="5" height="5" rx="1"/>
          <rect x="2" y="9" width="5" height="5" rx="1"/><rect x="9" y="9" width="5" height="5" rx="1"/>
        </svg>
      </span>
      <span>${escHtml(m)}</span>`;
    li.addEventListener('click', () => selectModel(m));
    modelList.appendChild(li);
  });

  const typed = query.trim();
  const exactMatch = currentModels.some(m => m.toLowerCase() === q);
  if (typed && !exactMatch) {
    const li = document.createElement('li');
    li.className = 'dropdown-item dropdown-item-custom';
    li.setAttribute('role','option');
    li.dataset.model = typed;
    li.innerHTML = `
      <span class="model-icon custom-icon">
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8">
          <line x1="8" y1="2" x2="8" y2="14"/><line x1="2" y1="8" x2="14" y2="8"/>
        </svg>
      </span>
      <span>Use <strong>&ldquo;${escHtml(typed)}&rdquo;</strong></span>
      <span class="custom-badge">custom</span>`;
    li.addEventListener('click', () => selectModel(typed));
    modelList.appendChild(li);
  }

  if (!filtered.length && !typed) {
    modelList.innerHTML = `<li class="dropdown-empty">No models available</li>`;
  }
}

modelSearch.addEventListener('focus', () => { if (modelSearch.disabled) return; modelDD.open(); renderModelList(''); });
modelSearch.addEventListener('input', () => {
  if (modelSearch.disabled) return;
  modelDD.open(); renderModelList(modelSearch.value);
  if (!modelSearch.value.trim()) { state.selectedModel = null; validateForm(); }
});
modelSearch.addEventListener('keydown', e => {
  if (e.key === 'Enter') {
    const list = modelDD.items(); const i = modelDD.getIdx();
    if (i >= 0 && list[i]) selectModel(list[i].dataset.model);
    else if (modelSearch.value.trim()) selectModel(modelSearch.value.trim());
  }
});

function selectModel(model) {
  state.selectedModel = model;
  modelSearch.value = model;
  modelDD.close();
  validateForm();
}

/* ─────────────────────────────────────────────
   API KEY INPUT
───────────────────────────────────────────── */
apiKeyInput.addEventListener('input', () => {
  if (apiKeyInput.value !== apiKeyInput.value.trim()) apiKeyInput.value = apiKeyInput.value.trim();
  validateForm();
});
apiKeyInput.addEventListener('keydown', e => { if (e.key === 'Enter' && !testBtn.disabled) submitTest(); });

toggleVisBtn.addEventListener('click', () => {
  const isPwd = apiKeyInput.type === 'password';
  apiKeyInput.type = isPwd ? 'text' : 'password';
  eyeOpen.classList.toggle('hidden', isPwd);
  eyeClosed.classList.toggle('hidden', !isPwd);
});
pasteBtn.addEventListener('click', async () => {
  try { apiKeyInput.value = (await navigator.clipboard.readText()).trim(); validateForm(); showToast('Pasted from clipboard', 'success', 2000); }
  catch { showToast('Could not access clipboard', 'error', 2000); }
});
clearKeyBtn.addEventListener('click', () => { apiKeyInput.value = ''; validateForm(); apiKeyInput.focus(); });

function validateForm() {
  const hasProvider = !!state.selectedProvider;
  const isNaModel   = state.selectedProvider?.models?.[0] === 'N/A';
  const hasModel    = isNaModel || (!!state.selectedModel && state.selectedModel !== 'N/A');
  const hasKey      = apiKeyInput.value.trim().length > 4;
  testBtn.disabled  = !(hasProvider && hasModel && hasKey);
}

/* ─────────────────────────────────────────────
   SUBMIT
───────────────────────────────────────────── */
testBtn.addEventListener('click', submitTest);

async function submitTest() {
  const apiKey = apiKeyInput.value.trim();
  if (!apiKey || !state.selectedProvider) return;

  testBtn.disabled = true;
  btnText.textContent = 'Testing…';
  btnSpinner.classList.remove('hidden');

  const model = state.selectedModel || state.selectedProvider.default_model;

  try {
    const res = await fetch('/api/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider: state.selectedProvider.id, model, api_key: apiKey }),
    });
    const data = await res.json();
    state.lastResult = data;
    openModal(data);
  } catch {
    const fallback = {
      success: false, error_type: 'network_error',
      message: 'Could not reach the testing server. Make sure the Flask app is running.',
      provider: state.selectedProvider.name, model, latency_ms: 0, masked_key: '••••••',
    };
    state.lastResult = fallback;
    openModal(fallback);
  } finally {
    btnText.textContent = 'Test API Key';
    btnSpinner.classList.add('hidden');
    testBtn.disabled = false;
    resetBtn.classList.remove('hidden');
  }
}

/* ─────────────────────────────────────────────
   MODAL — open / close
───────────────────────────────────────────── */
function openModal(data) {
  renderModalContent(data);
  modalOverlay.classList.add('open');
  document.body.style.overflow = 'hidden';
  setTimeout(() => modalClose.focus(), 80);
}

function closeModal() {
  modalOverlay.classList.remove('open');
  document.body.style.overflow = '';
}

modalClose.addEventListener('click', closeModal);
modalTestAgain.addEventListener('click', closeModal);

// Click backdrop to close
modalOverlay.addEventListener('click', e => { if (e.target === modalOverlay) closeModal(); });

// Escape key
document.addEventListener('keydown', e => { if (e.key === 'Escape' && modalOverlay.classList.contains('open')) closeModal(); });

/* ─────────────────────────────────────────────
   MODAL CONTENT RENDERING
───────────────────────────────────────────── */
const ERROR_META = {
  invalid_key:      { icon: '🔑', label: 'Invalid API Key',              color: 'error', what: 'The provider rejected this key as unrecognised. It may have been deleted, rotated, or never existed.', tip: 'Double-check the key is copied fully with no missing characters. Most keys are 40–60 characters long.' },
  permission_error: { icon: '🚫', label: 'Permission Denied',            color: 'error', what: 'The key exists but lacks permission to make this type of request.', tip: 'Check that your key has the required scopes/permissions enabled in the provider dashboard.' },
  quota_exceeded:   { icon: '📊', label: 'Quota / Rate Limit Exceeded',  color: 'warn',  what: 'The key is recognised, but the account has exhausted its usage quota or is being rate-limited.', tip: 'Your key is valid but your account is out of credits or hit a rate limit. Upgrade your plan or wait for the limit to reset.' },
  billing_issue:    { icon: '💳', label: 'Billing Issue',                color: 'warn',  what: 'The account associated with this key has a billing problem — no active subscription or payment method.', tip: 'Add a payment method or top up credits in the provider billing dashboard.' },
  invalid_model:    { icon: '🤖', label: 'Invalid Model',                color: 'warn',  what: 'The API key is valid, but the requested model does not exist or you do not have access to it.', tip: 'Your key works, but the model name is wrong or unavailable on your plan. Try a different model.' },
  provider_error:   { icon: '🛠', label: 'Provider Server Error',        color: 'error', what: 'The provider API returned a 5xx server error, indicating a problem on their end.', tip: 'This is a provider-side issue, not your key. Try again in a few minutes or check the provider status page.' },
  timeout:          { icon: '⏱', label: 'Request Timed Out',            color: 'error', what: 'No response was received from the provider within the timeout window (15 seconds).', tip: 'Check your internet connection. The provider may also be experiencing slowness — try again shortly.' },
  network_error:    { icon: '🌐', label: 'Network Error',                color: 'error', what: 'The connection to the provider could not be established.', tip: 'Check your internet connection. A firewall or proxy may be blocking outbound requests.' },
  validation:       { icon: '⚠️', label: 'Validation Error',            color: 'error', what: 'The request was rejected before reaching the provider due to missing or invalid input.', tip: 'Make sure you selected the correct provider and entered a complete, valid key.' },
  unknown_error:    { icon: '❓', label: 'Unknown Error',                color: 'error', what: 'An unexpected error occurred that does not match a known failure pattern.', tip: 'Check the provider status page for ongoing incidents and try again.' },
};

function renderModalContent(data) {
  const meta      = data.success ? null : (ERROR_META[data.error_type] || ERROR_META.unknown_error);
  const colorClass = data.success ? 'success' : (meta?.color === 'warn' ? 'warn' : 'error');

  // Reset classes
  modalBox.className = `modal-box modal-${colorClass}`;

  /* Header */
  if (data.success) {
    modalIcon.textContent = '✅';
    modalTitle.textContent = 'API Key is Valid & Working';
    showToast(`${data.provider} key is working!`, 'success');
  } else {
    modalIcon.textContent = meta.icon;
    modalTitle.textContent = meta.label;
    showToast(meta.label, colorClass === 'warn' ? 'info' : 'error');
  }
  modalMsg.textContent = data.message || '—';

  /* Pills */
  const pills = [
    { label: 'Provider', val: data.provider || '—' },
    { label: 'Model',    val: (data.model && data.model !== 'N/A') ? data.model : 'N/A' },
    { label: 'Latency',  val: data.latency_ms ? `${data.latency_ms} ms` : '—' },
    { label: 'Key',      val: data.masked_key || '—' },
  ];
  if (!data.success && data.error_type) pills.push({ label: 'Error', val: data.error_type });
  if (data.success && data.meta?.login)    pills.push({ label: 'User', val: data.meta.login });
  if (data.success && data.meta?.username) pills.push({ label: 'Bot',  val: data.meta.username });

  modalDetails.innerHTML = pills.map(p =>
    `<div class="detail-pill">
      <span class="pill-label">${escHtml(p.label)}</span>
      <span class="pill-val">${escHtml(String(p.val))}</span>
    </div>`
  ).join('');

  /* Rich extra block */
  if (data.success) {
    modalExtra.innerHTML = `
      <div class="extra-block extra-success">
        <div class="extra-row">
          <svg class="extra-ico" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
          <div>
            <div class="extra-title">Key authenticated successfully</div>
            <div class="extra-desc">The provider accepted your API key and returned a valid response. You are good to go.</div>
          </div>
        </div>
        <div class="extra-stat-row">
          <div class="extra-stat">
            <span class="stat-val">${data.latency_ms} ms</span>
            <span class="stat-lbl">Response time</span>
          </div>
          <div class="extra-stat">
            <span class="stat-val">${escHtml(data.provider)}</span>
            <span class="stat-lbl">Provider</span>
          </div>
          ${(data.model && data.model !== 'N/A') ? `<div class="extra-stat"><span class="stat-val" style="font-size:0.72rem;max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escHtml(data.model)}</span><span class="stat-lbl">Model tested</span></div>` : ''}
        </div>
      </div>`;
  } else {
    const warnSvg = `<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>`;
    const errSvg  = `<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>`;
    modalExtra.innerHTML = `
      <div class="extra-block extra-${colorClass}">
        <div class="extra-row">
          <svg class="extra-ico" viewBox="0 0 20 20" fill="currentColor">${colorClass === 'warn' ? warnSvg : errSvg}</svg>
          <div>
            <div class="extra-title">What happened</div>
            <div class="extra-desc">${escHtml(meta.what)}</div>
          </div>
        </div>
        <div class="extra-tip-row">
          <svg class="tip-ico" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>
          <div><span class="tip-label">How to fix it: </span><span class="tip-text">${escHtml(meta.tip)}</span></div>
        </div>
      </div>`;
  }
}

/* ── Copy result ── */
modalCopyBtn.addEventListener('click', () => {
  if (!state.lastResult) return;
  const d    = state.lastResult;
  const meta = d.error_type ? (ERROR_META[d.error_type] || ERROR_META.unknown_error) : null;
  const lines = [
    `Status:   ${d.success ? '✅ WORKING' : '❌ FAILED'}`,
    `Provider: ${d.provider}`,
    `Model:    ${d.model || 'N/A'}`,
    `Key:      ${d.masked_key}`,
    `Latency:  ${d.latency_ms} ms`,
    `Message:  ${d.message}`,
    d.error_type    ? `Error:  ${d.error_type}` : '',
    meta?.what      ? `Detail: ${meta.what}`     : '',
    meta?.tip       ? `Fix:    ${meta.tip}`       : '',
  ].filter(Boolean).join('\n');

  navigator.clipboard.writeText(lines)
    .then(() => showToast('Result copied to clipboard', 'success', 2000))
    .catch(() => showToast('Could not copy', 'error', 2000));
});

/* ── Reset ── */
resetBtn.addEventListener('click', () => {
  state.selectedProvider = null;
  state.selectedModel    = null;
  state.lastResult       = null;
  currentModels          = [];

  providerSearch.value   = '';
  modelSearch.value      = '';
  modelSearch.disabled   = false;
  apiKeyInput.value      = '';
  apiKeyInput.type       = 'password';
  eyeOpen.classList.remove('hidden');
  eyeClosed.classList.add('hidden');

  hideStep(stepModel);
  hideStep(stepKey);
  resetBtn.classList.add('hidden');
  testBtn.disabled = true;

  renderProviderList(state.providers);
  providerSearch.focus();
});

/* ── Load providers ── */
async function loadProviders() {
  try {
    const res = await fetch('/api/providers');
    state.providers = await res.json();
    renderProviderList(state.providers);
  } catch {
    showToast('Failed to load providers — is the server running?', 'error');
  }
}

loadProviders();
