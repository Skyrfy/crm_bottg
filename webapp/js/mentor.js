import { initTelegram, showAlert } from './tg.js';
import { api } from './api.js';

const tg = initTelegram();

const greeting = document.getElementById('greeting');
const content = document.getElementById('content');
const newBtn = document.getElementById('new-deadline-btn');

async function load() {
    try {
        const [me, deadlines] = await Promise.all([
            api.me(),
            api.deadlines(),
        ]);

        if (me.role !== 'mentor') {
            showAlert('Этот раздел доступен только ментору');
            window.location.replace('/student/');
            return;
        }

        greeting.textContent = `Здравствуйте, ${me.full_name}!`;
        renderDeadlines(deadlines);
        newBtn.disabled = false;
    } catch (err) {
        content.innerHTML = `<div class="error">${err.message}</div>`;
    }
}

function renderDeadlines(deadlines) {
    if (!deadlines.length) {
        content.innerHTML = `
            <div class="card muted">Дедлайнов пока нет. Создайте первый!</div>
        `;
        return;
    }

    content.innerHTML = `<h2>Дедлайны (${deadlines.length})</h2>` + deadlines.map(d => `
        <div class="card">
            <strong>${escapeHtml(d.topic)}</strong><br>
            <span class="hint">До ${formatDate(d.due_at)} · назначено: ${d.assignments_count}</span>
        </div>
    `).join('');
}

function formatDate(iso) {
    const d = new Date(iso);
    return d.toLocaleString('ru-RU', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
    });
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
}

newBtn.addEventListener('click', () => {
    showAlert('Создание дедлайна — в следующем этапе');
});

load();