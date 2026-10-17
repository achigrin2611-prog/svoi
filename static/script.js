// ============ ID ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ ============
const messagesEl = document.getElementById('messages');
window.currentUserId = messagesEl ? parseInt(messagesEl.dataset.currentUser) : null;
window.currentGroupId = messagesEl ? parseInt(messagesEl.dataset.groupId) : null;

// ============ ПЕРЕМЕННАЯ ДЛЯ ОТВЕТА ============
let replyingTo = null;

// ============ SOCKET IO ============
const socket = io();
const formEl = document.getElementById('message-form');
const inputEl = document.getElementById('message-input');

// ============ ВОЙТИ В КОМНАТУ ГРУППЫ ============
if (window.currentGroupId) {
    socket.emit('join', { group_id: window.currentGroupId });
}

// ============ ОТПРАВКА СООБЩЕНИЯ ============
if (formEl) {
    formEl.addEventListener('submit', (e) => {
        e.preventDefault();
        const text = inputEl.value.trim();
        if (!text) return;

        const data = { text: text, group_id: window.currentGroupId };
        if (replyingTo) {
            data.reply_to_id = replyingTo.id;
        }

        socket.emit('send_message', data);
        inputEl.value = '';
        inputEl.focus();
        cancelReply();
    });
}

// ============ ПОЛУЧЕНИЕ СООБЩЕНИЯ ============
socket.on('new_message', (data) => {
    if (!messagesEl) return;

    const msg = document.createElement('div');
    msg.className = 'message';
    msg.dataset.messageId = data.id;
    msg.dataset.userId = data.user_id;
    msg.setAttribute('oncontextmenu', `showMessageMenu(event, ${data.id}, ${data.user_id}); return false;`);

    let replyHTML = '';
    if (data.reply_to_id) {
        replyHTML = `
            <div class="reply-quote" onclick="scrollToMessage(${data.reply_to_id})">
                <span class="reply-user">${escapeHtml(data.reply_to_user || '')}</span>
                <span class="reply-text">${escapeHtml(data.reply_to_text || '')}</span>
            </div>
        `;
    }

    msg.innerHTML = `
        ${replyHTML}
        <span class="msg-user">${escapeHtml(data.username)}</span>
        <span class="msg-text" id="text-${data.id}">${escapeHtml(data.text)}</span>
        <span class="msg-time">
            ${data.timestamp}
            <span class="edited-mark" id="edited-${data.id}"></span>
        </span>
        <div class="reactions" id="reactions-${data.id}"></div>
        <button class="react-btn" onclick="showEmojiPicker(${data.id}, event)">+</button>
    `;
    messagesEl.appendChild(msg);
    messagesEl.scrollTop = messagesEl.scrollHeight;

    attachLongPress(msg);
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

// ============ НЕ ПЕРЕЗАГРУЖАТЬ ПРИ ENTER ============
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

document.addEventListener('click', (e) => {
    const picker = document.getElementById('emoji-picker');
    if (picker && !picker.contains(e.target) && !e.target.classList.contains('react-btn')) {
        picker.style.display = 'none';
    }
});

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

// ============ МЕНЮ СООБЩЕНИЯ ============
let menuMessageId = null;

function showMessageMenu(event, messageId, userId) {
    event.preventDefault();

    menuMessageId = messageId;
    const menu = document.getElementById('message-menu');
    if (!menu) return;
    menu.style.display = 'block';
    menu.style.position = 'fixed';

    const x = event.clientX || event.touches?.[0]?.clientX || 100;
    const y = event.clientY || event.touches?.[0]?.clientY || 100;

    menu.style.top = y + 'px';
    menu.style.left = x + 'px';

    const editBtn = document.getElementById('edit-menu-item');
    if (editBtn) {
        if (parseInt(userId) === window.currentUserId) {
            editBtn.style.display = 'block';
        } else {
            editBtn.style.display = 'none';
        }
    }
}

function deleteMessage() {
    if (!menuMessageId) return;

    if (confirm('Удалить сообщение?')) {
        socket.emit('delete_message', { message_id: menuMessageId });
    }

    document.getElementById('message-menu').style.display = 'none';
    menuMessageId = null;
}

document.addEventListener('click', (e) => {
    const menu = document.getElementById('message-menu');
    if (menu && !menu.contains(e.target)) {
        menu.style.display = 'none';
    }
});

socket.on('message_deleted', (data) => {
    const msg = document.querySelector(`.message[data-message-id="${data.message_id}"]`);
    if (msg) {
        msg.style.transition = 'opacity 0.3s, transform 0.3s';
        msg.style.opacity = '0';
        msg.style.transform = 'scale(0.9)';
        setTimeout(() => msg.remove(), 300);
    }
});

// ============ РЕДАКТИРОВАНИЕ СООБЩЕНИЙ ============
function editMessage() {
    if (!menuMessageId) return;

    const msg = document.querySelector(`.message[data-message-id="${menuMessageId}"]`);
    if (!msg) return;

    const textEl = msg.querySelector('.msg-text');
    const oldText = textEl.textContent;

    const input = document.createElement('input');
    input.type = 'text';
    input.value = oldText;
    input.className = 'edit-input';
    input.dataset.messageId = menuMessageId;

    textEl.replaceWith(input);
    input.focus();
    input.select();

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            saveEdit(input, oldText);
        } else if (e.key === 'Escape') {
            cancelEdit(input, oldText);
        }
    });

    input.addEventListener('blur', () => {
        setTimeout(() => {
            if (document.contains(input)) {
                saveEdit(input, oldText);
            }
        }, 150);
    });

    document.getElementById('message-menu').style.display = 'none';
    menuMessageId = null;
}

function saveEdit(input, oldText) {
    const newText = input.value.trim();
    const messageId = input.dataset.messageId;

    if (newText && newText !== oldText) {
        socket.emit('edit_message', {
            message_id: parseInt(messageId),
            text: newText
        });
    } else {
        cancelEdit(input, oldText);
    }
}

function cancelEdit(input, oldText) {
    const span = document.createElement('span');
    span.className = 'msg-text';
    span.id = 'text-' + input.dataset.messageId;
    span.textContent = oldText;
    input.replaceWith(span);
}

socket.on('message_edited', (data) => {
    const textEl = document.getElementById('text-' + data.message_id);
    if (textEl) {
        textEl.textContent = data.text;
    }

    const editedMark = document.getElementById('edited-' + data.message_id);
    if (editedMark) {
        editedMark.textContent = '(изменено)';
    }
});

// ============ ОТВЕТЫ НА СООБЩЕНИЯ ============
function replyToMessage() {
    if (!menuMessageId) return;

    const msg = document.querySelector(`.message[data-message-id="${menuMessageId}"]`);
    if (!msg) return;

    const textEl = msg.querySelector('.msg-text');
    const userEl = msg.querySelector('.msg-user');
    const text = textEl ? textEl.textContent : '';
    const user = userEl ? userEl.textContent : '';

    replyingTo = {
        id: menuMessageId,
        user: user,
        text: text
    };

    const preview = document.getElementById('reply-preview');
    document.getElementById('reply-preview-user').textContent = user + ':';
    document.getElementById('reply-preview-text').textContent = text.slice(0, 60) + (text.length > 60 ? '...' : '');
    preview.style.display = 'flex';

    inputEl.focus();

    document.getElementById('message-menu').style.display = 'none';
    menuMessageId = null;
}

function cancelReply() {
    replyingTo = null;
    const preview = document.getElementById('reply-preview');
    if (preview) preview.style.display = 'none';
}

function scrollToMessage(messageId) {
    const msg = document.querySelector(`.message[data-message-id="${messageId}"]`);
    if (msg) {
        msg.scrollIntoView({ behavior: 'smooth', block: 'center' });
        msg.style.transition = 'background 0.5s';
        msg.style.background = 'rgba(124, 92, 255, 0.3)';
        setTimeout(() => {
            msg.style.background = '';
        }, 1000);
    }
}

// ============ КОПИРОВАТЬ КОД ПРИГЛАШЕНИЯ ============
function copyInviteCode(code) {
    navigator.clipboard.writeText(code).then(() => {
        const toast = document.createElement('div');
        toast.textContent = '✅ Код скопирован: ' + code;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: var(--accent);
            color: white;
            padding: 12px 24px;
            border-radius: 12px;
            font-size: 14px;
            z-index: 10000;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        `;
        document.body.appendChild(toast);

        setTimeout(() => toast.remove(), 2500);
    }).catch(err => {
        alert('Код: ' + code);
    });
}

// ============ ДОЛГИЙ ТАП ДЛЯ МОБИЛЬНЫХ ============
function attachLongPress(msg) {
    let touchTimer = null;
    msg.addEventListener('touchstart', (e) => {
        touchTimer = setTimeout(() => {
            const messageId = msg.dataset.messageId;
            const userId = msg.dataset.userId;
            showMessageMenu(e, messageId, userId);
        }, 600);
    });

    msg.addEventListener('touchend', () => clearTimeout(touchTimer));
    msg.addEventListener('touchmove', () => clearTimeout(touchTimer));
}

document.querySelectorAll('.message').forEach(attachLongPress);

// ============ PWA: РЕГИСТРАЦИЯ SERVICE WORKER ============
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
            .then((reg) => console.log('✅ Service Worker зарегистрирован:', reg.scope))
            .catch((err) => console.error('❌ SW ошибка:', err));
    });
}