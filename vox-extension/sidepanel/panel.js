import * as api from '../shared/api.js';

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

let ws = null;

function showView(id) {
  $$('.view').forEach(v => v.classList.add('hidden'));
  $(`#${id}`).classList.remove('hidden');
}

$('#login-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    await api.login($('#login-email').value, $('#login-password').value);
    showView('connect-view');
  } catch (err) {
    alert('Login failed: ' + err.message);
  }
});

$('#connect-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const podcastId = $('#podcast-id').value.trim();
  if (!podcastId) return;
  connect(podcastId);
});

$('#disconnect-btn').addEventListener('click', disconnect);

function connect(podcastId) {
  disconnect();
  showView('transcript-view');
  $('#podcast-title').textContent = `Podcast: ${podcastId}`;
  $('#transcript-log').innerHTML = '';
  $('#summary-section').classList.add('hidden');
  $('#chapters-section').classList.add('hidden');
  $('#moments-section').classList.add('hidden');
  $('#status-bar').innerHTML = '<span class="status-dot live"></span> Connecting...';

  ws = api.wsTranscribe(podcastId);

  ws.onopen = () => {
    $('#status-bar').innerHTML = '<span class="status-dot live"></span> Connected';
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    switch (data.type) {
      case 'transcript':
        appendTranscriptSegment(data);
        break;
      case 'summary':
        showSummary(data.content);
        break;
      case 'chapters':
        showChapters(data.chapters);
        break;
      case 'key_moments':
        showKeyMoments(data.moments);
        break;
      case 'sentiment':
        showSentiment(data.data);
        break;
      case 'complete':
        $('#status-bar').innerHTML = '<span class="status-dot done"></span> Complete';
        break;
      case 'error':
        $('#status-bar').innerHTML = `<span class="status-dot error"></span> ${data.message}`;
        break;
    }
  };

  ws.onclose = () => {
    $('#status-bar').innerHTML = '<span class="status-dot error"></span> Disconnected';
    ws = null;
  };

  ws.onerror = () => {
    $('#status-bar').innerHTML = '<span class="status-dot error"></span> Connection error';
  };
}

function disconnect() {
  if (ws) {
    ws.close();
    ws = null;
  }
}

function appendTranscriptSegment(seg) {
  const log = $('#transcript-log');
  const el = document.createElement('div');
  el.className = 'segment';

  const speaker = seg.speaker || 'UNKNOWN';
  const text = seg.labeled_text || seg.text || '';
  const start = formatTime(seg.start);
  const end = formatTime(seg.end);

  el.innerHTML = `
    <span class="timestamp">${start} - ${end}</span>
    <span class="speaker">${escapeHtml(speaker)}:</span>
    <span class="text">${escapeHtml(text)}</span>
  `;
  log.appendChild(el);
  const container = $('#transcript-container');
  container.scrollTop = container.scrollHeight;
}

function showSummary(content) {
  $('#summary-content').textContent = content || 'No summary available';
  $('#summary-section').classList.remove('hidden');
}

function showChapters(chapters) {
  if (!chapters || !chapters.length) return;
  const list = $('#chapters-list');
  list.innerHTML = chapters.map((ch, i) => `
    <li><strong>${escapeHtml(ch.title || `Chapter ${i + 1}`)}</strong>
    ${ch.start_time ? `<span class="timestamp">${formatTime(ch.start_time)}</span>` : ''}
    ${ch.summary ? `<p class="small">${escapeHtml(ch.summary)}</p>` : ''}</li>
  `).join('');
  $('#chapters-section').classList.remove('hidden');
}

function showKeyMoments(moments) {
  if (!moments || !moments.length) return;
  const list = $('#moments-list');
  list.innerHTML = moments.map((m, i) => `
    <li>
      <strong>${escapeHtml(m.title || `Moment ${i + 1}`)}</strong>
      ${m.start ? `<span class="timestamp">${formatTime(m.start)}</span>` : ''}
      <p class="small">${escapeHtml(m.description || m.text || '')}</p>
    </li>
  `).join('');
  $('#moments-section').classList.remove('hidden');
}

function showSentiment(data) {
  if (!data) return;
}

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

if (api.isLoggedIn()) {
  showView('connect-view');
} else {
  showView('login-view');
}
