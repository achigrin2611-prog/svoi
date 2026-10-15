// ============ SOCKET IO ============
const socket = io();

const messagesEl = document.getElementById('messages');
const formEl = document.getElementById('message-form');
const inputEl = document.getElementById('message-input');

// ============ ОТПРАВКА СООБЩЕНИЯ ============
if (formEl) {
    formEl.addEventListener('submit', (e) => {
        e.preventDefault();
        const text = inputEl.value.trim();
        if (!text) return;

        socket.emit('send_message', { text: text });
        inputEl.value = '';
        inputEl.focus();
    });
}

// ============ ПОЛУЧЕНИЕ СООБЩЕНИЯ ============
socket.on('new_message', (data) => {
    if (!messagesEl) return;

    const msg = document.createElement('div');
    msg.className = 'message';
    msg.innerHTML = `
        <span class="msg-user">${escapeHtml(data.username)}</span>
        <span class="msg-text">${escapeHtml(data.text)}</span>
        <span class="msg-time">${data.timestamp}</span>
    `;
    messagesEl.appendChild(msg);
    messagesEl.scrollTop = messagesEl.scrollHeight;
});

// ============ ЗАЩИТА ОТ XSS ============
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============ АВТОСКРОЛЛ ВНИЗ ============
if (messagesEl) {
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

// ============ НЕ ПЕРЕЗАГРУЖАТЬ СТРАНИЦУ ПРИ ENTER ============
document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && document.activeElement === inputEl) {
        e.preventDefault();
        formEl.dispatchEvent(new Event('submit'));
    }
});