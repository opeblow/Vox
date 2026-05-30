chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'vaultai-upload-url',
    title: 'Send link to VaultAI',
    contexts: ['link'],
  });

  chrome.contextMenus.create({
    id: 'vaultai-upload-page',
    title: 'Transcribe this page URL with VaultAI',
    contexts: ['page', 'video', 'audio'],
  });

  chrome.contextMenus.create({
    id: 'vaultai-sidepanel',
    title: 'Open VaultAI Side Panel',
    contexts: ['action'],
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  chrome.storage.local.get('vaultai_token', (result) => {
    const token = result.vaultai_token;
    if (!token) {
      chrome.action.openPopup();
      return;
    }

    const baseUrl = 'http://localhost:8000';

    if (info.menuItemId === 'vaultai-upload-url' && info.linkUrl) {
      fetch(`${baseUrl}/upload/url`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ url: info.linkUrl }),
      }).catch(console.error);
    }

    if (info.menuItemId === 'vaultai-upload-page' && tab?.url) {
      fetch(`${baseUrl}/upload/url`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ url: tab.url }),
      }).catch(console.error);
    }
  });
});

chrome.action.onClicked.addListener((tab) => {
  chrome.sidePanel.open({ tabId: tab.id });
});
