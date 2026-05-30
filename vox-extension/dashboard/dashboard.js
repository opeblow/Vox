import * as api from '../shared/api.js';

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

let currentVaultId = null;

function checkAuth() {
  if (!api.isLoggedIn()) {
    window.location.href = chrome.runtime.getURL('popup/popup.html');
  }
}

$$('.nav-links a').forEach(link => {
  link.addEventListener('click', (e) => {
    e.preventDefault();
    $$('.nav-links a').forEach(l => l.classList.remove('active'));
    link.classList.add('active');
    showView(link.dataset.view);
  });
});

function showView(name) {
  $$('.view').forEach(v => v.classList.remove('active'));
  const el = $(`#view-${name}`);
  if (el) el.classList.add('active');

  switch (name) {
    case 'vaults': loadVaults(); break;
    case 'upload': break;
    case 'jobs': loadJobs(); break;
  }
}

$('#logout-btn').addEventListener('click', () => {
  api.logout();
  window.location.href = chrome.runtime.getURL('popup/popup.html');
});

$('#back-to-vaults').addEventListener('click', () => {
  currentVaultId = null;
  showView('vaults');
});

// Upload file
const uploadZone = $('#upload-zone');
const fileInput = $('#file-input');

uploadZone.addEventListener('click', () => fileInput.click());
uploadZone.addEventListener('dragover', (e) => { e.preventDefault(); uploadZone.classList.add('drag-over'); });
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
uploadZone.addEventListener('drop', (e) => {
  e.preventDefault();
  uploadZone.classList.remove('drag-over');
  if (e.dataTransfer.files.length) handleFileUpload(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', () => {
  if (fileInput.files.length) handleFileUpload(fileInput.files[0]);
});

async function handleFileUpload(file) {
  const progress = $('#upload-progress');
  const fill = $('#progress-fill');
  const status = $('#upload-status');
  progress.classList.remove('hidden');
  fill.style.width = '0%';
  status.textContent = 'Uploading...';

  try {
    fill.style.width = '30%';
    const result = await api.uploadAudio(file);
    fill.style.width = '100%';
    status.textContent = `✓ Processing started! Job: ${result.job_id}, Podcast: ${result.podcast_id}`;
  } catch (err) {
    status.textContent = `✗ ${err.message}`;
    fill.style.width = '0%';
  }
}

// URL upload
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
  btn.textContent = 'Transcribe URL';
});

// Vaults
async function loadVaults() {
  const grid = $('#vaults-grid');
  try {
    const data = await api.getVaults(0, 50);
    if (!data.vaults || data.vaults.length === 0) {
      grid.innerHTML = '<div class="empty-state"><h3>No vaults yet</h3><p class="muted">Upload some audio to get started!</p></div>';
      return;
    }
    grid.innerHTML = data.vaults.map(v => `
      <div class="vault-card" data-id="${v.podcast_id}">
        <div class="vault-card-header">
          <span class="vault-lang">${escapeHtml(v.language || '?')}</span>
          <span class="vault-duration">${v.duration_minutes}m</span>
        </div>
        <h3 class="vault-card-title">${escapeHtml(v.title)}</h3>
        <p class="vault-card-summary">${escapeHtml(v.summary?.slice(0, 150) || 'No summary')}</p>
        <div class="vault-card-meta">
          <span>${v.speaker_count || '?'} speakers</span>
          ${v.has_chapters ? '<span class="tag">chapters</span>' : ''}
          ${v.has_key_moments ? '<span class="tag">moments</span>' : ''}
          ${v.has_sentiment ? '<span class="tag">sentiment</span>' : ''}
        </div>
      </div>
    `).join('');
    grid.querySelectorAll('.vault-card').forEach(card => {
      card.addEventListener('click', () => openVaultDetail(card.dataset.id));
    });
  } catch (err) {
    grid.innerHTML = `<p class="error">Failed to load vaults: ${err.message}</p>`;
  }
}

async function openVaultDetail(podcastId) {
  currentVaultId = podcastId;
  showView('vault-detail');
  const content = $('#vault-detail-content');
  content.innerHTML = '<p class="muted">Loading vault details...</p>';

  try {
    const [detail, transcript, summary, sentiment, showNotes] = await Promise.all([
      api.getVaultDetail(podcastId),
      api.getVaultTranscript(podcastId),
      api.getVaultSummary(podcastId).catch(() => ({ summary: null })),
      api.getVaultSentiment(podcastId).catch(() => ({ sentiment: null })),
      api.getVaultShowNotes(podcastId).catch(() => ({ show_notes: null })),
    ]);

    const segments = detail.segments || [];
    const t = transcript;

    content.innerHTML = `
      <div class="detail-header">
        <h2>${escapeHtml(detail.summary?.name || podcastId)}</h2>
        <div class="detail-actions">
          <a href="${api.getExportUrl(podcastId, 'srt')}" target="_blank" class="btn secondary">SRT</a>
          <a href="${api.getExportUrl(podcastId, 'vtt')}" target="_blank" class="btn secondary">VTT</a>
          <a href="${api.getExportUrl(podcastId, 'markdown')}" target="_blank" class="btn secondary">MD</a>
          <button class="btn secondary" id="open-sidepanel-detail">Live View</button>
        </div>
      </div>

      <div class="detail-tabs">
        <button class="detail-tab active" data-tab="transcript">Transcript</button>
        <button class="detail-tab" data-tab="summary">Summary</button>
        <button class="detail-tab" data-tab="insights">Insights</button>
        <button class="detail-tab" data-tab="qa">Q&A</button>
      </div>

      <div id="detail-transcript" class="detail-tab-content active">
        <div class="transcript-text"><pre>${escapeHtml(t?.speaker_transcript || t?.full_text || 'No transcript available')}</pre></div>
      </div>

      <div id="detail-summary" class="detail-tab-content hidden">
        <div class="card"><p>${escapeHtml(summary?.summary || 'No summary available')}</p></div>
      </div>

      <div id="detail-insights" class="detail-tab-content hidden">
        ${sentiment?.sentiment ? `
          <div class="card">
            <h3>Sentiment</h3>
            <p>Overall: ${escapeHtml(sentiment.sentiment.overall_sentiment || 'N/A')}</p>
          </div>
        ` : ''}
        ${showNotes?.show_notes ? `
          <div class="card">
            <h3>Show Notes</h3>
            <p>${escapeHtml(showNotes.show_notes.notes || showNotes.show_notes.description || '')}</p>
            ${showNotes.show_notes.tags?.length ? `<p class="tags">${showNotes.show_notes.tags.map(t => `<span class="tag">${escapeHtml(t)}</span>`).join('')}</p>` : ''}
          </div>
        ` : ''}
        ${detail.chapters?.length ? `
          <div class="card">
            <h3>Chapters (${detail.chapters.length})</h3>
            <ul class="chapter-list">${detail.chapters.map(c => `<li><strong>${escapeHtml(c.title)}</strong> <span class="muted">${formatTime(c.start_time)}</span></li>`).join('')}</ul>
          </div>
        ` : ''}
        ${detail.key_moments?.length ? `
          <div class="card">
            <h3>Key Moments (${detail.key_moments.length})</h3>
            <ul class="moment-list">${detail.key_moments.map(m => `<li><strong>${escapeHtml(m.title || 'Moment')}</strong><p class="small">${escapeHtml(m.description || m.text || '')}</p></li>`).join('')}</ul>
          </div>
        ` : ''}
      </div>

      <div id="detail-qa" class="detail-tab-content hidden">
        <form id="qa-form">
          <input type="text" id="qa-input" placeholder="Ask a question about this podcast..." required>
          <button type="submit" class="btn primary">Ask</button>
        </form>
        <div id="qa-result" class="hidden"></div>
        <div id="qa-history"></div>
      </div>
    `;

    // Tab switching
    content.querySelectorAll('.detail-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        content.querySelectorAll('.detail-tab').forEach(t => t.classList.remove('active'));
        content.querySelectorAll('.detail-tab-content').forEach(tc => tc.classList.remove('active'));
        tab.classList.add('active');
        $(`#detail-${tab.dataset.tab}`).classList.add('active');
      });
    });

    // Q&A
    const qaForm = content.querySelector('#qa-form');
    if (qaForm) {
      qaForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const question = $('#qa-input').value.trim();
        if (!question) return;
        const result = $('#qa-result');
        const history = $('#qa-history');
        result.classList.remove('hidden');
        result.innerHTML = '<p class="muted">Thinking...</p>';

        try {
          const qaData = await api.askQuestion(podcastId, question);
          result.innerHTML = '';
          history.innerHTML = `
            <div class="qa-item"><strong>Q:</strong> ${escapeHtml(question)}</div>
            <div class="qa-item"><strong>A:</strong> ${escapeHtml(qaData.answer || 'No answer')}</div>
          ` + history.innerHTML;
          $('#qa-input').value = '';
        } catch (err) {
          result.innerHTML = `<p class="error">${escapeHtml(err.message)}</p>`;
        }
      });
    }

    // Open side panel
    $('#open-sidepanel-detail')?.addEventListener('click', async () => {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab) await chrome.sidePanel.open({ tabId: tab.id });
    });

  } catch (err) {
    content.innerHTML = `<p class="error">Failed to load vault: ${err.message}</p>`;
  }
}

// Jobs
async function loadJobs() {
  const list = $('#jobs-list');
  try {
    const data = await api.getJobs(0, 50);
    if (!data.jobs || data.jobs.length === 0) {
      list.innerHTML = '<div class="empty-state"><h3>No jobs</h3><p class="muted">Submit audio to see processing jobs here.</p></div>';
      return;
    }
    list.innerHTML = `<div class="jobs-grid">${data.jobs.map(j => `
      <div class="job-card ${j.status}">
        <div class="job-header">
          <span class="job-filename">${escapeHtml(j.original_filename || 'Unknown')}</span>
          <span class="job-status status-${j.status}">${j.status}</span>
        </div>
        <p class="small muted">Job: ${j.job_id} | Podcast: ${j.podcast_id || 'N/A'}</p>
        ${j.error ? `<p class="error small">${escapeHtml(j.error)}</p>` : ''}
        ${j.status === 'completed' && j.podcast_id ? `<button class="btn secondary small-btn view-vault-btn" data-id="${j.podcast_id}">View Vault</button>` : ''}
      </div>
    `).join('')}</div>`;
    list.querySelectorAll('.view-vault-btn').forEach(btn => {
      btn.addEventListener('click', () => openVaultDetail(btn.dataset.id));
    });
  } catch (err) {
    list.innerHTML = `<p class="error">Failed to load jobs: ${err.message}</p>`;
  }
}

// Vault search
$('#vault-search')?.addEventListener('input', (e) => {
  const q = e.target.value.toLowerCase();
  document.querySelectorAll('.vault-card').forEach(card => {
    const title = card.querySelector('.vault-card-title')?.textContent?.toLowerCase() || '';
    card.style.display = title.includes(q) ? '' : 'none';
  });
});

function formatTime(seconds) {
  if (!seconds && seconds !== 0) return '--:--';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

const params = new URLSearchParams(window.location.search);
const vaultParam = params.get('vault');

checkAuth();
$('#nav-email').textContent = 'VaultAI User';

if (vaultParam) {
  openVaultDetail(vaultParam);
} else {
  loadVaults();
}
