import { getInitData } from './tg.js';

const API_BASE = '/api';

async function request(path, options = {}) {
    const initData = getInitData();
    const headers = {
        'Content-Type': 'application/json',
        'X-Telegram-Init-Data': initData,
        ...(options.headers || {}),
    };

    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
    });

    if (!response.ok) {
        const text = await response.text();
        let detail = text;
        try {
            const json = JSON.parse(text);
            detail = json.detail || json.error || text;
        } catch (_) {}
        throw new Error(`${response.status}: ${detail}`);
    }

    // Если ответ пустой (204 No Content)
    if (response.status === 204) return null;
    return await response.json();
}

export const api = {
    me: () => request('/me/'),
    students: () => request('/students/'),
    deadlines: () => request('/deadlines/'),
    deadlineDetail: (id) => request(`/deadlines/${id}/`),
    createDeadline: (data) => request('/deadlines/', {
        method: 'POST',
        body: JSON.stringify(data),
    }),
    submit: (assignmentId, data) => request(`/assignments/${assignmentId}/submit/`, {
        method: 'POST',
        body: JSON.stringify(data),
    }),
    approve: (assignmentId) => request(`/assignments/${assignmentId}/approve/`, {
        method: 'POST',
    }),
    reject: (assignmentId, comment) => request(`/assignments/${assignmentId}/reject/`, {
        method: 'POST',
        body: JSON.stringify({ comment }),
    }),
};