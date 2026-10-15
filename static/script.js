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
    msg.dataset.messageId = data.id;
    msg.innerHTML = `
        <span class="msg-user">${escapeHtml(data.username)}</span>
        <span class="msg-text">${escapeHtml(data.text)}</span>
        <span class="msg-time">${data.timestamp}</span>
        <div class="reactions" id="reactions-${data.id}"></div>
        <button class="react-btn" onclick="showEmojiPicker(${data.id}, event)">+</button>
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

// ============ РЕАКЦИИ ============
let currentMessageId = null;

function showEmojiPicker(messageId, event) {
    currentMessageId = messageId;
    const picker = document.getElementById('emoji-picker');
    picker.style.display = 'flex';

    const rect = event.target.getBoundingClientRect();
    picker.style.position = 'fixed';
    picker.style.top = (rect.top - 60) + 'px';
    picker.style.left = rect.left + 'px';
}

function toggleReaction(emoji) {
    if (!currentMessageId) return;

    socket.emit('toggle_reaction', {
        message_id: currentMessageId,
        emoji: emoji
    });

    document.getElementById('emoji-picker').style.display = 'none';
    currentMessageId = null;
}

function quickReact(messageId, emoji) {
    socket.emit('toggle_reaction', {
        message_id: messageId,
        emoji: emoji
    });
}

// Скрывать при клике вне меню
document.addEventListener('click', (e) => {
    const picker = document.getElementById('emoji-picker');
    if (picker && !picker.contains(e.target) && !e.target.classList.contains('react-btn')) {
        picker.style.display = 'none';
    }
});

// Обновление реакций
socket.on('reaction_updated', (data) => {
    const container = document.getElementById('reactions-' + data.message_id);
    if (!container) return;

    container.innerHTML = '';

    for (const [emoji, count] of Object.entries(data.counts)) {
        const span = document.createElement('span');
        span.className = 'reaction';
        span.textContent = emoji + ' ' + count;
        span.onclick = () => {
            socket.emit('toggle_reaction', {
                message_id: data.message_id,
                emoji: emoji
            });
        };
        container.appendChild(span);
    }
});

// ============ PWA: РЕГИСТРАЦИЯ SERVICE WORKER ============
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
            .then((reg) => console.log('✅ Service Worker зарегистрирован:', reg.scope))
            .catch((err) => console.error('❌ SW ошибка:', err));
    });
}