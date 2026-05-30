const DEFAULTS = {
  BASE_URL: 'http://localhost:8000',
};

function getBaseUrl() {
  return localStorage.getItem('vaultai_base_url') || DEFAULTS.BASE_URL;
}

function getToken() {
  return localStorage.getItem('vaultai_token');
}

function headers(extra = {}) {
  const h = { 'Content-Type': 'application/json', ...extra };
  const token = getToken();
  if (token) h['Authorization'] = `Bearer ${token}`;
  return h;
}

async function api(method, path, body = null) {
  const url = `${getBaseUrl()}${path}`;
  const opts = { method, headers: headers() };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `Request failed: ${res.status}`);
  return data;
}

export async function register(email, password) {
  return api('POST', '/auth/register', { email, password });
}

export async function login(email, password) {
  const data = await api('POST', '/auth/login', { email, password });
  localStorage.setItem('vaultai_token', data.access_token);
  try { await chrome.storage?.local?.set({ vaultai_token: data.access_token }); } catch (_) {}
  return data;
}

export function logout() {
  localStorage.removeItem('vaultai_token');
  try { chrome.storage?.local?.remove('vaultai_token'); } catch (_) {}
}

export function isLoggedIn() {
  return !!getToken();
}

export async function uploadAudio(file) {
  const url = `${getBaseUrl()}/upload/audio`;
  const formData = new FormData();
  formData.append('file', file);
  const token = getToken();
  const res = await fetch(url, {
    method: 'POST',
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
    body: formData,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `Upload failed: ${res.status}`);
  return data;
}

export async function submitUrl(url) {
  return api('POST', '/upload/url', { url });
}

export async function getJobs(skip = 0, limit = 50) {
  return api('GET', `/ingest/jobs?skip=${skip}&limit=${limit}`);
}

export async function getJobStatus(jobId) {
  return api('GET', `/ingest/jobs/${jobId}`);
}

export async function getVaults(skip = 0, limit = 50) {
  return api('GET', `/vaults?skip=${skip}&limit=${limit}`);
}

export async function getVaultDetail(podcastId) {
  return api('GET', `/vaults/${podcastId}`);
}

export async function getVaultTranscript(podcastId) {
  return api('GET', `/vaults/${podcastId}/transcript`);
}

export async function getVaultSummary(podcastId) {
  return api('GET', `/vaults/${podcastId}/summary`);
}

export async function getVaultSentiment(podcastId) {
  return api('GET', `/vaults/${podcastId}/sentiment`);
}

export async function getVaultShowNotes(podcastId) {
  return api('GET', `/vaults/${podcastId}/show-notes`);
}

export async function getVaultClips(podcastId) {
  return api('GET', `/vaults/${podcastId}/clips`);
}

export async function askQuestion(podcastId, question) {
  return api('POST', '/query/ask', { podcast_id: podcastId, question });
}

export function getExportUrl(podcastId, format) {
  return `${getBaseUrl()}/vaults/${podcastId}/export/${format}`;
}

export function wsTranscribe(podcastId) {
  const baseUrl = getBaseUrl().replace(/^http/, 'ws');
  const token = getToken();
  return new WebSocket(`${baseUrl}/ws/transcribe/${podcastId}?token=${token}`);
}
