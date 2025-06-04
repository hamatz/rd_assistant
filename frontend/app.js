let sessionId = null;

async function initSession() {
  const res = await fetch('/sessions', { method: 'POST' });
  const data = await res.json();
  sessionId = data.session_id;
  await loadVisualization();
}

async function sendMessage(text) {
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

document.addEventListener('DOMContentLoaded', () => {
  initSession();
  const form = document.getElementById('chat-form');
  const input = document.getElementById('message-input');
  const chat = document.getElementById('chat');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    appendMessage('user', text);
    input.value = '';
    const resp = await sendMessage(text);
    if (resp.result && resp.result.response) {
      appendMessage('ai', resp.result.response.message);
    } else {
      appendMessage('ai', JSON.stringify(resp));
    }
    await loadVisualization();
  });
});

function appendMessage(role, text) {
  const div = document.createElement('div');
  div.className = role;
  div.textContent = text;
  const chat = document.getElementById('chat');
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}
