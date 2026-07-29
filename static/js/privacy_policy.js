const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;

if (tg && typeof tg.expand === 'function') {
    tg.expand();
    try {
        document.body.style.background = tg.backgroundColor;
    } catch (_) {}
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
    console.log('Privacy Policy page loaded');

    setupBackButton();

    if (window.TranslationManager) {
        window.TranslationManager.initLanguage();
    }
});

window.privacyPolicy = {
    setupBackButton
};
