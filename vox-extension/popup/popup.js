import * as api from '../shared/api.js';

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

function showView(id) {
  $$('.view').forEach(v => v.classList.add('hidden'));
  $(`#${id}`).classList.remove('hidden');
}

async function refreshAuth() {
  if (api.isLoggedIn()) {
    showView('main-view');
  } else {
    showView('login-view');
  }
}

$('#show-register').addEventListener('click', (e) => { e.preventDefault(); showView('register-view'); });
$('#show-login').addEventListener('click', (e) => { e.preventDefault(); showView('login-view'); });

$('#login-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    await api.login($('#login-email').value, $('#login-password').value);
    refreshAuth();
  } catch (err) {
    alert('Login failed: ' + err.message);
  }
});

$('#register-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    await api.register($('#register-email').value, $('#register-password').value);
    await api.login($('#register-email').value, $('#register-password').value);
    refreshAuth();
  } catch (err) {
    alert('Registration failed: ' + err.message);
  }
});

$('#logout-btn').addEventListener('click', () => {
  api.logout();
  refreshAuth();
});

$('#open-dashboard').addEventListener('click', () => {
  chrome.tabs.create({ url: chrome.runtime.getURL('dashboard/dashboard.html') });
});

$('#open-sidepanel').addEventListener('click', async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab) chrome.sidePanel.open({ tabId: tab.id });
});

$$('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    $$('.tab').forEach(t => t.classList.remove('active'));
    $$('.tab-content').forEach(tc => tc.classList.remove('active'));
    tab.classList.add('active');
    $(`#tab-${tab.dataset.tab}`).classList.add('active');
    if (tab.dataset.tab === 'recent') loadRecent();
  });
});

const uploadZone = $('#upload-zone');
const fileInput = $('#file-input');

uploadZone.addEventListener('click', () => fileInput.click());
uploadZone.addEventListener('dragover', (e) => { e.preventDefault(); uploadZone.classList.add('drag-over'); });
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
uploadZone.addEventListener('drop', (e) => {
  e.preventDefault();
  uploadZone.classList.remove('drag-over');
  if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});

fileInput.addEventListener('change', () => {
  if (fileInput.files.length) handleFile(fileInput.files[0]);
});

async function handleFile(file) {
  const progress = $('#upload-progress');
  const fill = $('#progress-fill');
  const status = $('#upload-status');
  progress.classList.remove('hidden');
  fill.style.width = '0%';

  try {
    status.textContent = 'Uploading...';
    fill.style.width = '30%';
    const result = await api.uploadAudio(file);
    fill.style.width = '100%';
    status.textContent = `Processing started! Job: ${result.job_id}`;
    setTimeout(() => { progress.classList.add('hidden'); }, 3000);
  } catch (err) {
    status.textContent = 'Error: ' + err.message;
    fill.style.width = '0%';
  }
}

$('#url-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = e.target.querySelector('button');
  const result = $('#url-result');
  btn.disabled = true;
  btn.textContent = 'Submitting...';
  result.classList.remove('hidden');

  try {
    const data = await api.submitUrl($('#url-input').value);
    result.innerHTML = `<p class="success">✓ Processing started</p>
      <p class="small">Job: ${data.job_id} | Podcast: ${data.podcast_id}</p>`;
    $('#url-input').value = '';
  } catch (err) {
    result.innerHTML = `<p class="error">✗ ${err.message}</p>`;
  }

  btn.disabled = false;
  btn.textContent = 'Transcribe';
});

async function loadRecent() {
  const list = $('#recent-list');
  try {
    const data = await api.getVaults(0, 5);
    if (!data.vaults || data.vaults.length === 0) {
      list.innerHTML = '<p class="small muted">No vaults yet. Upload some audio!</p>';
      return;
    }
    list.innerHTML = data.vaults.map(v => `
      <div class="vault-item" data-id="${v.podcast_id}">
        <div class="vault-title">${escapeHtml(v.title)}</div>
        <div class="vault-meta">${v.duration_minutes}m | ${v.language || 'unknown'}</div>
      </div>
    `).join('');
    list.querySelectorAll('.vault-item').forEach(el => {
      el.addEventListener('click', () => {
        chrome.tabs.create({
          url: chrome.runtime.getURL(`dashboard/dashboard.html?vault=${el.dataset.id}`),
        });
      });
    });
  } catch (err) {
    list.innerHTML = `<p class="error">${err.message}</p>`;
  }
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

refreshAuth();
