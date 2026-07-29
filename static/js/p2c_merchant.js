const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;

if (tg && typeof tg.expand === 'function') {
    tg.expand();
    try {
        document.body.style.background = tg.backgroundColor;
    } catch (_) {}
}

function handleActivateClick() {
    const button = document.getElementById('activate-btn');
    if (!button) return;

    button.textContent = 'Активация...';
    button.disabled = true;

    setTimeout(() => {
        button.textContent = 'Активировано';
        button.style.background = '#28a745';

        const statusEl = document.querySelector('.info-content h3');
        if (statusEl) {
            statusEl.textContent = 'Статус: Активен';
        }

        const subtitleEl = document.querySelector('.info-content p');
        if (subtitleEl) {
            subtitleEl.textContent = 'P2C Мерчант успешно активирован';
        }
    }, 2000);
}

function initializePage() {
    const activateBtn = document.getElementById('activate-btn');
    if (activateBtn) {
        activateBtn.addEventListener('click', handleActivateClick);
    }
}

function setupBackButton() {
    if (tg && tg.BackButton) {
        tg.BackButton.show();
        tg.BackButton.onClick(() => {
            if (window.showMainPage && typeof window.showMainPage === 'function') {
                window.showMainPage();
            } else {
                window.history.back();
            }
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    console.log('P2C Merchant page loaded');

    initializePage();
    setupBackButton();

    if (window.TranslationManager) {
        window.TranslationManager.initLanguage();
    }
});

window.p2cMerchant = {
    handleActivateClick,
    initializePage
};
