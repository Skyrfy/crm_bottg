// Инициализация Telegram WebApp SDK.
// Объект Telegram.WebApp подключается через <script src="https://telegram.org/js/telegram-web-app.js">

const tg = window.Telegram?.WebApp;

export function initTelegram() {
    if (!tg) {
        console.warn('Telegram WebApp SDK не найден — открыто вне Telegram?');
        return null;
    }
    tg.ready();      // сообщаем Telegram, что мы готовы
    tg.expand();     // разворачиваем на весь экран
    return tg;
}

export function getInitData() {
    return tg?.initData || '';
}

export function getUser() {
    return tg?.initDataUnsafe?.user || null;
}

export function showAlert(message) {
    if (tg?.showAlert) {
        tg.showAlert(message);
    } else {
        alert(message);
    }
}

export function closeApp() {
    tg?.close();
}