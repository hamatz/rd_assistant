let sessionId = null;
let isDarkMode = true;
let isLoading = false;
let customImages = { userAvatar: null, botAvatar: null };

function loadSettings() {
  const imgs = localStorage.getItem('chatCustomImages');
  if (imgs) customImages = JSON.parse(imgs);
  const theme = localStorage.getItem('chatTheme');
  if (theme) {
    isDarkMode = theme === 'dark';
    document.body.className = isDarkMode ? 'dark' : 'light';
  }
  updateAvatarPreview('user');
  updateAvatarPreview('bot');
}

function saveSettings() {
  localStorage.setItem('chatCustomImages', JSON.stringify(customImages));
  localStorage.setItem('chatTheme', isDarkMode ? 'dark' : 'light');
}

async function initSession() {
  const res = await fetch('/sessions', { method: 'POST' });
  const data = await res.json();
  sessionId = data.session_id;
  await loadVisualization();
  addInitialMessage();
}

function addInitialMessage() {
  addMessage('👋 Hello! Ask me anything.', 'bot');
}

async function sendMessageToServer(text) {
  const res = await fetch(`/sessions/${sessionId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: text })
  });
  return await res.json();
}

async function loadVisualization() {
  const res = await fetch(`/sessions/${sessionId}/visualization`);
  const data = await res.json();
  const diagramEl = document.getElementById('diagram');
  diagramEl.textContent = data.diagram;
  mermaid.run({ nodes: [diagramEl] });
}

function onSend() {
  const input = document.getElementById('message-input');
  const text = input.value.trim();
  if (!text || isLoading) return;
  addMessage(text, 'user');
  input.value = '';
  input.style.height = 'auto';
  startLoading();
  sendMessageToServer(text).then(resp => {
    stopLoading();
    if (resp.result && resp.result.response) {
      addMessage(resp.result.response.message, 'bot');
    } else {
      addMessage(JSON.stringify(resp), 'bot');
    }
    loadVisualization();
  });
}

function addMessage(content, type) {
  const messagesArea = document.getElementById('messagesArea');
  const div = document.createElement('div');
  div.className = `message ${type}`;
  div.innerHTML = `
    <div class="avatar ${type}">
      <div class="avatar-inner">
        ${type === 'user' ? getUserAvatarSVG() : getBotAvatarSVG()}
      </div>
    </div>
    <div class="message-bubble">
      <div>${renderMarkdown(content)}</div>
      <div class="message-time">${new Date().toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit'})}</div>
    </div>`;
  messagesArea.appendChild(div);
  messagesArea.scrollTop = messagesArea.scrollHeight;
}

function startLoading() {
  isLoading = true;
  const messagesArea = document.getElementById('messagesArea');
  const loadingDiv = document.createElement('div');
  loadingDiv.className = 'message bot';
  loadingDiv.id = 'loadingMessage';
  loadingDiv.innerHTML = `
    <div class="avatar bot">
      <div class="avatar-inner">
        ${getBotAvatarSVG(true)}
      </div>
    </div>
    <div class="message-bubble">
      <div class="loading-message">
        <div class="loading-dots">
          <div class="loading-dot"></div>
          <div class="loading-dot"></div>
          <div class="loading-dot"></div>
        </div>
        <span>Thinking...</span>
      </div>
    </div>`;
  messagesArea.appendChild(loadingDiv);
  messagesArea.scrollTop = messagesArea.scrollHeight;
  document.getElementById('sendButton').disabled = true;
}

function stopLoading() {
  isLoading = false;
  const loadingMessage = document.getElementById('loadingMessage');
  if (loadingMessage) loadingMessage.remove();
  document.getElementById('sendButton').disabled = false;
  document.getElementById('message-input').focus();
}

function renderMarkdown(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code style="background-color: rgba(156,163,175,0.2); padding: 0.125rem 0.25rem; border-radius: 0.25rem; font-size: 0.875rem;">$1</code>')
    .replace(/\n/g, '<br>');
}

function getUserAvatarSVG() {
  if (customImages.userAvatar) {
    return `<img src="${customImages.userAvatar}" alt="user avatar" class="avatar-custom">`;
  }
  return `<svg viewBox="0 0 100 100"><circle cx="50" cy="45" r="35" fill="#fbbf24" stroke="#f59e0b" stroke-width="2"/><circle cx="42" cy="38" r="3" fill="#1f2937"/><circle cx="58" cy="38" r="3" fill="#1f2937"/><circle cx="43" cy="37" r="1" fill="white"/><circle cx="59" cy="37" r="1" fill="white"/><path d="M50,42 Q52,45 50,48" stroke="#f59e0b" stroke-width="1.5" fill="none"/><path d="M45,52 Q50,57 55,52" stroke="#dc2626" stroke-width="2" fill="none"/><path d="M20,35 Q25,15 50,20 Q75,15 80,35 Q75,25 50,25 Q25,25 20,35" fill="#7c2d12"/></svg>`;
}

function getBotAvatarSVG(anim=false) {
  if (customImages.botAvatar) {
    return `<img src="${customImages.botAvatar}" alt="bot avatar" class="avatar-custom">`;
  }
  const eye = anim ? '#10b981' : '#3b82f6';
  const antenna = anim ? '#10b981' : '#ef4444';
  return `<svg viewBox="0 0 100 100"><rect x="25" y="20" width="50" height="45" rx="25" fill="#e5e7eb" stroke="#9ca3af" stroke-width="2"/><circle cx="38" cy="35" r="4" fill="${eye}"/><circle cx="62" cy="35" r="4" fill="${eye}"/><ellipse cx="50" cy="50" rx="${anim?'8':'6'}" ry="${anim?'4':'2'}" fill="#1f2937"/><rect x="48" y="15" width="4" height="8" fill="#9ca3af"/><circle cx="50" cy="12" r="3" fill="${antenna}"/><rect x="30" y="42" width="6" height="2" rx="1" fill="#6b7280"/><rect x="64" y="42" width="6" height="2" rx="1" fill="#6b7280"/></svg>`;
}

function openSettings() {
  document.getElementById('settingsOverlay').style.display = 'flex';
}

function closeSettings() {
  document.getElementById('settingsOverlay').style.display = 'none';
}

document.getElementById('settingsOverlay').addEventListener('click', e => {
  if (e.target === e.currentTarget) closeSettings();
});

function selectUserAvatar() { document.getElementById('userAvatarInput').click(); }
function selectBotAvatar() { document.getElementById('botAvatarInput').click(); }

function readFileAsDataURL(file) { return new Promise((res, rej) => { const r = new FileReader(); r.onload = e => res(e.target.result); r.onerror = rej; r.readAsDataURL(file); }); }

async function handleUserAvatarUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  if (file.size > 2 * 1024 * 1024) { alert('File too big'); return; }
  const dataURL = await readFileAsDataURL(file);
  customImages.userAvatar = dataURL;
  updateAvatarPreview('user');
  saveSettings();
}

async function handleBotAvatarUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  if (file.size > 2 * 1024 * 1024) { alert('File too big'); return; }
  const dataURL = await readFileAsDataURL(file);
  customImages.botAvatar = dataURL;
  updateAvatarPreview('bot');
  saveSettings();
}

function updateAvatarPreview(type) {
  const previewId = type === 'user' ? 'userAvatarPreview' : 'botAvatarPreview';
  const areaId = type === 'user' ? 'userAvatarArea' : 'botAvatarArea';
  const img = type === 'user' ? customImages.userAvatar : customImages.botAvatar;
  const preview = document.getElementById(previewId);
  const area = document.getElementById(areaId);
  if (img) {
    preview.innerHTML = `<img src="${img}" class="image-preview" style="border-radius:50%;"><div class="upload-text">Change</div>`;
    area.classList.add('has-image');
  } else {
    preview.innerHTML = `<div class="upload-icon"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1"><path d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/></svg></div><div class="upload-text">Upload Image</div><div class="upload-hint">Click to choose</div>`;
    area.classList.remove('has-image');
  }
}

function resetUserAvatar() { customImages.userAvatar = null; updateAvatarPreview('user'); saveSettings(); }
function resetBotAvatar() { customImages.botAvatar = null; updateAvatarPreview('bot'); saveSettings(); }

function toggleTheme() {
  isDarkMode = !isDarkMode;
  document.body.className = isDarkMode ? 'dark' : 'light';
  saveSettings();
  const toggleButton = document.getElementById('themeToggle');
  toggleButton.innerHTML = isDarkMode ?
    `<svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>` :
    `<svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/></svg>`;
}

document.getElementById('message-input').addEventListener('keypress', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSend(); }
});

document.getElementById('message-input').addEventListener('input', e => {
  e.target.style.height = 'auto';
  e.target.style.height = e.target.scrollHeight + 'px';
});

document.addEventListener('DOMContentLoaded', () => {
  loadSettings();
  initSession();
});
