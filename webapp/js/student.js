import { initTelegram, showAlert, getStartParam } from './tg.js';
import { api } from './api.js';

initTelegram();

const screenList = document.getElementById('screen-list');
const screenDetail = document.getElementById('screen-detail');

const greeting = document.getElementById('greeting');
const content = document.getElementById('content');

const backBtn = document.getElementById('back-btn');
const detailContent = document.getElementById('detail-content');
const submitForm = document.getElementById('submit-form');
const answerText = document.getElementById('answer-text');
const sendBtn = document.getElementById('send-answer-btn');
const submitError = document.getElementById('submit-error');

let currentDeadline = null;

async function loadList() {
    showScreen('list');
    try {
        const [me, deadlines] = await Promise.all([api.me(), api.deadlines()]);
        const groupNote = me.group_label ? `группа «${me.group_label}»` : 'группа не определена';
        greeting.textContent = `${me.full_name} · ${groupNote}`;
        renderDeadlines(deadlines);
    } catch (err) {
        content.innerHTML = `<div class="error">${escapeHtml(err.message)}</div>`;
    }
}

function renderDeadlines(deadlines) {
    if (!deadlines.length) {
        content.innerHTML = `<div class="card muted">У вас пока нет активных дедлайнов.</div>`;
        return;
    }
    content.innerHTML = deadlines.map(d => {
        const a = d.my_assignment;
        const statusBadge = a ? `<span class="status status-${a.status}">${escapeHtml(a.status_label)}</span>` : '';
        return `
            <div class="card deadline-card" data-id="${d.id}">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <strong>${escapeHtml(d.topic)}</strong>${statusBadge}
                </div>
                <span class="hint">До ${formatDate(d.due_at)}</span>
            </div>
        `;
    }).join('');

    document.querySelectorAll('.deadline-card').forEach(card => {
        card.addEventListener('click', () => openDetail(parseInt(card.dataset.id, 10)));
    });
}

async function openDetail(deadlineId) {
    showScreen('detail');
    detailContent.innerHTML = `<div class="card"><div class="spinner"></div> Загрузка...</div>`;
    submitForm.style.display = 'none';

    try {
        const d = await api.deadlineDetail(deadlineId);
        currentDeadline = d;

        const myAssignment = d.assignments[0]; // ученик видит только свой
        renderDetail(d, myAssignment);
    } catch (err) {
        detailContent.innerHTML = `<div class="error">${escapeHtml(err.message)}</div>`;
    }
}

function renderDetail(d, myAssignment) {
    const overdue = new Date(d.due_at) < new Date();
    const description = d.description
        ? `<div class="card"><strong>Описание</strong><br>${escapeHtml(d.description).replace(/\n/g, '<br>')}</div>`
        : '';

    detailContent.innerHTML = `
        <h1>${escapeHtml(d.topic)}</h1>
        <div class="hint" style="margin-bottom: 12px;">
            Срок: до ${formatDate(d.due_at)}
            ${overdue ? '<span class="status status-overdue">просрочен</span>' : ''}
            · <span class="status status-${myAssignment.status}">${escapeHtml(myAssignment.status_label)}</span>
        </div>
        ${description}

        <h2>Обсуждение</h2>
        <div class="thread">${renderThread(myAssignment.submissions)}</div>

        <button class="btn btn-secondary" id="refresh-btn" style="width: 100%;">🔄 Обновить</button>
    `;

    document.getElementById('refresh-btn').addEventListener('click', () => openDetail(d.id));

    // Форма ответа доступна, если работа не принята
    if (myAssignment.status !== 'approved') {
        submitForm.style.display = 'block';
        answerText.value = '';
        submitError.innerHTML = '';
        sendBtn.dataset.assignmentId = myAssignment.id;
    }
}

function renderThread(submissions) {
    if (!submissions.length) {
        return `<div class="thread-empty">Здесь будет ваше обсуждение с ментором.</div>`;
    }
    return submissions.map(s => {
        const cls = s.author === 'mentor' ? 'message-mentor' : 'message-student';
        return `
            <div class="message ${cls}">
                <div class="message-meta">${escapeHtml(s.author_name)} · ${formatDateShort(s.submitted_at)}</div>
                <div class="message-text">${escapeHtml(s.text)}</div>
            </div>
        `;
    }).join('');
}

async function sendAnswer() {
    const text = answerText.value.trim();
    submitError.innerHTML = '';

    if (!text) {
        submitError.innerHTML = `<div class="error">Напишите ответ.</div>`;
        return;
    }

    sendBtn.disabled = true;
    sendBtn.textContent = 'Отправка...';
    try {
        const assignmentId = parseInt(sendBtn.dataset.assignmentId, 10);
        await api.submit(assignmentId, { text });
        showAlert('Ответ отправлен ментору.');
        await openDetail(currentDeadline.id);
    } catch (err) {
        submitError.innerHTML = `<div class="error">${escapeHtml(err.message)}</div>`;
    } finally {
        sendBtn.disabled = false;
        sendBtn.textContent = 'Отправить ответ';
    }
}

function backToList() {
    showScreen('list');
    currentDeadline = null;
    loadList();
}

function showScreen(name) {
    screenList.style.display = name === 'list' ? 'block' : 'none';
    screenDetail.style.display = name === 'detail' ? 'block' : 'none';
}

function formatDate(iso) {
    return new Date(iso).toLocaleString('ru-RU', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
    });
}

function formatDateShort(iso) {
    return new Date(iso).toLocaleString('ru-RU', {
        day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
    });
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
}

backBtn.addEventListener('click', backToList);
sendBtn.addEventListener('click', sendAnswer);

// ---------- Старт + deep link ----------
async function init() {
    const startParam = getStartParam();
    if (startParam.startsWith('deadline_')) {
        const id = parseInt(startParam.replace('deadline_', ''), 10);
        if (!isNaN(id)) {
            // Сначала грузим список (для greeting), потом открываем карточку
            await loadList();
            await openDetail(id);
            return;
        }
    }
    await loadList();
}

init();