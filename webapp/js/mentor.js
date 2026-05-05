import { initTelegram, showAlert } from './tg.js';
import { api } from './api.js';

initTelegram();

const screenList = document.getElementById('screen-list');
const screenCreate = document.getElementById('screen-create');

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

let students = [];

// ---------- Загрузка главного экрана ----------
async function loadList() {
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
        <div class="card">
            <strong>${escapeHtml(d.topic)}</strong><br>
            <span class="hint">До ${formatDate(d.due_at)} · назначено: ${d.assignments_count}</span>
        </div>
    `).join('');
}

// ---------- Экран создания ----------
async function openCreate() {
    screenList.style.display = 'none';
    screenCreate.style.display = 'block';
    createError.innerHTML = '';

    // Дефолтное значение срока: завтра 18:00 локального времени
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(18, 0, 0, 0);
    dueAtInput.value = toLocalInput(tomorrow);

    if (!students.length) {
        try {
            students = await api.students();
            renderStudents();
        } catch (err) {
            studentsList.innerHTML = `<div class="error">${escapeHtml(err.message)}</div>`;
        }
    }
}

function closeCreate() {
    screenCreate.style.display = 'none';
    screenList.style.display = 'block';
    topicInput.value = '';
    descriptionInput.value = '';
    createError.innerHTML = '';
    document.querySelectorAll('#students-list input[type=checkbox]').forEach(cb => cb.checked = false);
}

function renderStudents() {
    if (!students.length) {
        studentsList.innerHTML = `<div class="muted">Учеников пока нет. Они появятся, когда напишут боту /start.</div>`;
        return;
    }

    // Группа учеников по группе обучения
    const byGroup = {};
    for (const s of students) {
        const key = s.group_label || 'Без группы';
        if (!byGroup[key]) byGroup[key] = [];
        byGroup[key].push(s);
    }

    let html = '';
    for (const [groupName, groupStudents] of Object.entries(byGroup)) {
        html += `<div class="hint" style="margin-top: 8px;">${escapeHtml(groupName)}</div>`;
        for (const s of groupStudents) {
            const username = s.username ? `@${escapeHtml(s.username)}` : '';
            html += `
                <div class="checkbox-row">
                    <input type="checkbox" id="student-${s.id}" value="${s.id}">
                    <label for="student-${s.id}">
                        ${escapeHtml(s.full_name)}
                        <span class="hint">${username}</span>
                    </label>
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

    if (!topic) return showError('Укажите тему');
    if (!dueAtRaw) return showError('Укажите срок сдачи');
    if (!checkedIds.length) return showError('Выберите хотя бы одного ученика');

    // datetime-local даёт строку в локальном времени без TZ → конвертируем в ISO
    const dueAt = new Date(dueAtRaw).toISOString();

    if (new Date(dueAt) < new Date()) {
        return showError('Срок сдачи должен быть в будущем');
    }

    submitBtn.disabled = true;
    submitBtn.textContent = 'Создание...';
    try {
        await api.createDeadline({
            topic,
            description,
            due_at: dueAt,
            student_ids: checkedIds,
        });
        showAlert(`Дедлайн создан и отправлен ${checkedIds.length} ученикам`);
        closeCreate();
        await loadList();
    } catch (err) {
        showError(err.message);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Создать дедлайн';
    }
}

function showError(msg) {
    createError.innerHTML = `<div class="error">${escapeHtml(msg)}</div>`;
}

// ---------- Утилиты ----------
function formatDate(iso) {
    return new Date(iso).toLocaleString('ru-RU', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
    });
}

function toLocalInput(date) {
    // Конвертация Date → строка для <input type="datetime-local"> (без TZ)
    const pad = n => String(n).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
}

// ---------- Биндинги ----------
newBtn.addEventListener('click', openCreate);
cancelBtn.addEventListener('click', closeCreate);
submitBtn.addEventListener('click', submitCreate);

loadList();