// webapp/js/student.js
import { initTelegram } from './tg.js';
import { api } from './api.js';

initTelegram();

const greeting = document.getElementById('greeting');
const content = document.getElementById('content');

async function load() {
    try {
        const [me, deadlines] = await Promise.all([
            api.me(),
            api.deadlines(),
        ]);

        const groupNote = me.group_label ? `группа «${me.group_label}»` : 'группа не определена';
        greeting.textContent = `${me.full_name} · ${groupNote}`;

        renderDeadlines(deadlines);
    } catch (err) {
        content.innerHTML = `<div class="error">${err.message}</div>`;
    }
}

function renderDeadlines(deadlines) {
    if (!deadlines.length) {
        content.innerHTML = `<div class="card muted">У вас пока нет активных дедлайнов.</div>`;
        return;
    }

    content.innerHTML = deadlines.map(d => `
        <div class="card">
            <strong>${escapeHtml(d.topic)}</strong><br>
            <span class="hint">До ${formatDate(d.due_at)}</span>
        </div>
    `).join('');
}

function formatDate(iso) {
    return new Date(iso).toLocaleString('ru-RU', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
    });
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
}

load();