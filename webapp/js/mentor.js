import { initTelegram, showAlert, getStartParam } from './tg.js';
import { api } from './api.js';

initTelegram();

const screenList = document.getElementById('screen-list');
const screenCreate = document.getElementById('screen-create');
const screenDetail = document.getElementById('screen-detail');

const greeting = document.getElementById('greeting');
const content = document.getElementById('content');

const newBtn = document.getElementById('new-deadline-btn');
const cancelBtn = document.getElementById('cancel-create');
const submitBtn = document.getElementById('submit-create');

const topicInput = document.getElementById('topic');
const descriptionInput = document.getElementById('description');
const dueAtInput = document.getElementById('due_at');
const studentsList = document.getElementById('students-list');
const createError = document.getElementById('create-error');

const detailContent = document.getElementById('detail-content');
const detailBackBtn = document.getElementById('detail-back-btn');

let students = [];
let currentDeadlineId = null;

async function loadList() {
    showScreen('list');
    try {
        const [me, deadlines] = await Promise.all([api.me(), api.deadlines()]);
        if (me.role !== 'mentor') {
            showAlert('Этот раздел доступен только ментору');
            window.location.replace('/student/');
            return;
        }
        greeting.textContent = `Здравствуйте, ${me.full_name}!`;
        renderDeadlines(deadlines);
    } catch (err) {
        content.innerHTML = `<div class="error">${escapeHtml(err.message)}</div>`;
    }
}

function renderDeadlines(deadlines) {
    if (!deadlines.length) {
        content.innerHTML = `<div class="card muted">Дедлайнов пока нет. Создайте первый!</div>`;
        return;
    }
    content.innerHTML = `<h2>Дедлайны (${deadlines.length})</h2>` + deadlines.map(d => `
        <div class="card deadline-card" data-id="${d.id}">
            <strong>${escapeHtml(d.topic)}</strong><br>
            <span class="hint">До ${formatDate(d.due_at)} · назначено: ${d.assignments_count}</span>
        </div>
    `).join('');

    document.querySelectorAll('.deadline-card').forEach(card => {
        card.addEventListener('click', () => openDetail(parseInt(card.dataset.id, 10)));
    });
}

// ---------- Создание ----------
async function openCreate() {
    showScreen('create');
    createError.innerHTML = '';

    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(18, 0, 0, 0);
    dueAtInput.value = toLocalInput(tomorrow);

    if (!students.length) {
        try {
            students = await api.students();
        } catch (err) {
            studentsList.innerHTML = `<div class="error">${escapeHtml(err.message)}</div>`;
            return;
        }
    }
    renderStudents();
}

function renderStudents() {
    if (!students.length) {
        studentsList.innerHTML = `<div class="muted">Учеников пока нет.</div>`;
        return;
    }
    const byGroup = {};
    for (const s of students) {
        const key = s.group_label || 'Без группы';
        (byGroup[key] = byGroup[key] || []).push(s);
    }
    let html = '';
    for (const [groupName, groupStudents] of Object.entries(byGroup)) {
        html += `<div class="hint" style="margin-top: 8px;">${escapeHtml(groupName)}</div>`;
        for (const s of groupStudents) {
            const username = s.username ? `@${escapeHtml(s.username)}` : '';
            html += `
                <div class="checkbox-row">
                    <input type="checkbox" id="student-${s.id}" value="${s.id}">
                    <label for="student-${s.id}">${escapeHtml(s.full_name)} <span class="hint">${username}</span></label>
                </div>
            `;
        }
    }
    studentsList.innerHTML = html;
}

async function submitCreate() {
    createError.innerHTML = '';
    const topic = topicInput.value.trim();
    const description = descriptionInput.value.trim();
    const dueAtRaw = dueAtInput.value;
    const checkedIds = Array.from(
        document.querySelectorAll('#students-list input[type=checkbox]:checked')
    ).map(cb => parseInt(cb.value, 10));

    if (!topic) return showCreateError('Укажите тему');
    if (!dueAtRaw) return showCreateError('Укажите срок сдачи');
    if (!checkedIds.length) return showCreateError('Выберите хотя бы одного ученика');
    const dueAt = new Date(dueAtRaw).toISOString();
    if (new Date(dueAt) < new Date()) return showCreateError('Срок сдачи должен быть в будущем');

    submitBtn.disabled = true;
    submitBtn.textContent = 'Создание...';
    try {
        await api.createDeadline({ topic, description, due_at: dueAt, student_ids: checkedIds });
        showAlert(`Дедлайн создан и отправлен ${checkedIds.length} ученикам`);
        topicInput.value = '';
        descriptionInput.value = '';
        document.querySelectorAll('#students-list input[type=checkbox]').forEach(cb => cb.checked = false);
        await loadList();
    } catch (err) {
        showCreateError(err.message);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Создать дедлайн';
    }
}

function showCreateError(msg) {
    createError.innerHTML = `<div class="error">${escapeHtml(msg)}</div>`;
}

// ---------- Детали ----------
async function openDetail(deadlineId) {
    currentDeadlineId = deadlineId;
    showScreen('detail');
    detailContent.innerHTML = `<div class="card"><div class="spinner"></div> Загрузка...</div>`;

    try {
        const d = await api.deadlineDetail(deadlineId);
        renderDetail(d);
    } catch (err) {
        detailContent.innerHTML = `<div class="error">${escapeHtml(err.message)}</div>`;
    }
}

function renderDetail(d) {
    const description = d.description
        ? `<div class="card"><strong>Описание</strong><br>${escapeHtml(d.description).replace(/\n/g, '<br>')}</div>`
        : '';

    const assignmentsHtml = d.assignments.map(a => `
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <strong>${escapeHtml(a.student.full_name)}</strong>
                <span class="status status-${a.status}">${escapeHtml(a.status_label)}</span>
            </div>

            <div class="thread">${renderThread(a.submissions)}</div>

            <div class="compose">
                <textarea id="comment-${a.id}" placeholder="Написать сообщение ученику..."></textarea>
                <div class="compose-actions">
                    <button class="btn comment-btn" data-id="${a.id}">💬 Отправить</button>
                </div>
            </div>

            ${a.status === 'submitted' || a.status === 'rejected' ? `
                <div class="review-actions">
                    <button class="btn approve-btn" data-id="${a.id}">✅ Принять</button>
                    <button class="btn btn-secondary reject-btn" data-id="${a.id}">❌ Отклонить</button>
                </div>
            ` : ''}
        </div>
    `).join('');

    detailContent.innerHTML = `
        <h1>${escapeHtml(d.topic)}</h1>
        <div class="hint" style="margin-bottom: 12px;">До ${formatDate(d.due_at)}</div>
        ${description}
        <h2>Ответы учеников (${d.assignments.length})</h2>
        ${assignmentsHtml}
        <button class="btn btn-secondary" id="refresh-btn" style="width: 100%; margin-top: 12px;">🔄 Обновить</button>
    `;

    document.getElementById('refresh-btn').addEventListener('click', () => openDetail(d.id));
    document.querySelectorAll('.comment-btn').forEach(btn => {
        btn.addEventListener('click', () => sendComment(parseInt(btn.dataset.id, 10)));
    });
    document.querySelectorAll('.approve-btn').forEach(btn => {
        btn.addEventListener('click', () => approveAssignment(parseInt(btn.dataset.id, 10)));
    });
    document.querySelectorAll('.reject-btn').forEach(btn => {
        btn.addEventListener('click', () => rejectAssignment(parseInt(btn.dataset.id, 10)));
    });
}

function renderThread(submissions) {
    if (!submissions.length) {
        return `<div class="thread-empty">Ученик ещё не отправил ответ.</div>`;
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

async function sendComment(assignmentId) {
    const ta = document.getElementById(`comment-${assignmentId}`);
    const text = ta.value.trim();
    if (!text) {
        showAlert('Напишите сообщение.');
        return;
    }
    try {
        await api.comment(assignmentId, text);
        ta.value = '';
        await openDetail(currentDeadlineId);
    } catch (err) {
        showAlert('Ошибка: ' + err.message);
    }
}

async function approveAssignment(assignmentId) {
    if (!confirm('Принять работу ученика?')) return;
    try {
        await api.approve(assignmentId);
        showAlert('Работа принята.');
        await openDetail(currentDeadlineId);
    } catch (err) {
        showAlert('Ошибка: ' + err.message);
    }
}

async function rejectAssignment(assignmentId) {
    const comment = prompt('Что нужно доработать?');
    if (comment === null) return;
    try {
        await api.reject(assignmentId, comment);
        showAlert('Работа отклонена.');
        await openDetail(currentDeadlineId);
    } catch (err) {
        showAlert('Ошибка: ' + err.message);
    }
}

function showScreen(name) {
    screenList.style.display = name === 'list' ? 'block' : 'none';
    screenCreate.style.display = name === 'create' ? 'block' : 'none';
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

function toLocalInput(date) {
    const pad = n => String(n).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
}

newBtn.addEventListener('click', openCreate);
cancelBtn.addEventListener('click', () => { topicInput.value = ''; descriptionInput.value = ''; loadList(); });
submitBtn.addEventListener('click', submitCreate);
detailBackBtn.addEventListener('click', loadList);

async function init() {
    const startParam = getStartParam();
    if (startParam.startsWith('deadline_')) {
        const id = parseInt(startParam.replace('deadline_', ''), 10);
        if (!isNaN(id)) {
            await loadList();
            await openDetail(id);
            return;
        }
    }
    await loadList();
}

init();