if (typeof tgUserMenu === 'undefined') {
    var tgUserMenu = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
}

if (tgUserMenu) {
    tgUserMenu.ready();
    if (typeof tgUserMenu.expand === 'function') {
        tgUserMenu.expand();
    }
    try {
        document.body.style.background = tgUserMenu.backgroundColor;

        const container = document.querySelector('.user-menu-container');
        if (container) {
            container.style.background = tgUserMenu.backgroundColor;
            container.style.color = tgUserMenu.textColor;
        }
    } catch (_) {}
}

const pageMapping = {
    'settings': '/settings',
    'address_book': '/address_book',
    'security': '/security',
    'p2p_merchant': '/p2p_merchant',
    'p2c_merchant': '/p2c_merchant',
    'verification': '/verification',
    'privacy_policy': '/privacy_policy',
    'aml_policy': '/aml_policy',
    'crypto_bot_help': 'https://t.me/crypto_bot_help',
    'crypto_bot_features': 'https://t.me/crypto_bot_features',
    'support': 'https://t.me/crypto_bot_support'
};

console.log('Available menu routes:', pageMapping);

function navigateToPage(url) {
    console.log('=== navigateToPage вызвана ===');
    console.log('URL:', url);

    let loadPageFunction = null;
    let targetWindow = null;

    if (window.loadPage && typeof window.loadPage === 'function') {
        loadPageFunction = window.loadPage;
        targetWindow = window;
        console.log('Found loadPage in current window');
    }

    else if (window.parent && window.parent.loadPage && typeof window.parent.loadPage === 'function') {
        loadPageFunction = window.parent.loadPage;
        targetWindow = window.parent;
        console.log('Found loadPage in parent window');
    }

    else if (window.top && window.top.loadPage && typeof window.top.loadPage === 'function') {
        loadPageFunction = window.top.loadPage;
        targetWindow = window.top;
        console.log('Found loadPage in top window');
    }

    if (loadPageFunction && targetWindow) {
        try {
            console.log('Using dynamic loading with loadPage');
            loadPageFunction.call(targetWindow, url);
            return;
        } catch (error) {
            console.error('Dynamic loading failed:', error);
        }
    }

    console.log('Using fallback direct navigation');
    window.location.href = url;
}

function navigateToPageDirect(url) {
    console.log('=== navigateToPageDirect вызвана ===');
    console.log('URL:', url);

    if (url.startsWith('/')) {
        window.location.href = url;
    } else {

        window.open(url, '_blank');
    }
}

function navigateToMenuItem(pageKey) {
    console.log('=== navigateToMenuItem вызвана ===');
    console.log('Page key:', pageKey);

    const route = pageMapping[pageKey];
    console.log('Route for', pageKey, ':', route);

    if (!route) {
        console.error('Route not found for page key:', pageKey);
        return;
    }

    if (route.startsWith('http')) {

        console.log('Opening external link:', route);
        openExternalLink(route);
    } else {

        console.log('Navigating to internal page:', route);

        let loadPageFunction = null;
        let targetWindow = null;

        if (window.loadPage && typeof window.loadPage === 'function') {
            loadPageFunction = window.loadPage;
            targetWindow = window;
            console.log('Found loadPage in current window');
        }

        else if (window.parent && window.parent.loadPage && typeof window.parent.loadPage === 'function') {
            loadPageFunction = window.parent.loadPage;
            targetWindow = window.parent;
            console.log('Found loadPage in parent window');
        }

        else if (window.top && window.top.loadPage && typeof window.top.loadPage === 'function') {
            loadPageFunction = window.top.loadPage;
            targetWindow = window.top;
            console.log('Found loadPage in top window');
        }

        if (loadPageFunction && targetWindow) {
            try {
                console.log('Using dynamic loading with loadPage');
                loadPageFunction.call(targetWindow, route);
                return;
            } catch (error) {
                console.error('Dynamic loading failed:', error);
            }
        }

        console.log('Using fallback direct navigation');
        try {
            window.location.href = route;
        } catch (error) {
            console.error('Direct navigation failed:', error);

            if (window.parent && window.parent !== window) {
                try {
                    window.parent.location.href = route;
                } catch (parentError) {
                    console.error('Parent navigation also failed:', parentError);
                }
            }
        }
    }
}

function openExternalLink(url) {
    console.log('Открытие внешней ссылки:', url);

    if (tgUserMenu && typeof tgUserMenu.openLink === 'function') {
        tgUserMenu.openLink(url);
    } else {
        window.open(url, '_blank');
    }
}

function initializeUserProfile() {
    try {
        const avatarEl = document.getElementById('user-avatar');
        const nameEl = document.getElementById('user-name');
        const teleUser = tgUserMenu?.initDataUnsafe?.user;

        if (teleUser) {

            const displayName = teleUser.first_name || 'Пользователь';
            if (nameEl) {
                nameEl.textContent = displayName;
            }

            if (avatarEl && teleUser.photo_url) {
                avatarEl.src = teleUser.photo_url;
            } else if (avatarEl) {

                const firstLetter = displayName.charAt(0).toUpperCase();
                avatarEl.style.backgroundColor = '#007AFF';
                avatarEl.style.color = '#ffffff';
                avatarEl.style.display = 'flex';
                avatarEl.style.alignItems = 'center';
                avatarEl.style.justifyContent = 'center';
                avatarEl.style.fontSize = '18px';
                avatarEl.style.fontWeight = '600';
                avatarEl.textContent = firstLetter;
            }
        } else {

            if (nameEl) {
                nameEl.textContent = 'Пользователь';
            }
            if (avatarEl) {
                avatarEl.style.backgroundColor = '#007AFF';
                avatarEl.style.color = '#ffffff';
                avatarEl.style.display = 'flex';
                avatarEl.style.alignItems = 'center';
                avatarEl.style.justifyContent = 'center';
                avatarEl.style.fontSize = '18px';
                avatarEl.style.fontWeight = '600';
                avatarEl.textContent = 'П';
            }
        }
    } catch (e) {
        console.warn('Failed to initialize user profile:', e);
    }
}

function handleMenuItemClick(event) {

    console.log('Legacy click handler called - using onclick instead');
}

function initializeMenuItems() {
    const menuItems = document.querySelectorAll('.menu-item[data-page]');
    console.log('Found menu items:', menuItems.length);

    menuItems.forEach((item, index) => {
        const pageKey = item.getAttribute('data-page');
        console.log(`Menu item ${index}: data-page="${pageKey}"`);

        item.setAttribute('tabindex', '0');

        item.removeEventListener('click', handleMenuItemClick);

        const clickHandler = (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log(`=== Элемент меню нажат: ${pageKey} ===`);
            const route = pageMapping[pageKey];
            console.log(`Маршрут для ${pageKey}: ${route}`);

            if (route) {
                if (route.startsWith('http')) {

                    console.log('Открытие внешней ссылки:', route);
                    openExternalLink(route);
                } else {

                    console.log('Переход на внутреннюю страницу:', route);

                    navigateToPage(route);
                }
            } else {
                console.warn(`Маршрут не найден для ключа страницы: ${pageKey}`);
                console.warn('Доступные маршруты:', Object.keys(pageMapping));
            }
        };

        item.addEventListener('click', clickHandler);

        item.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                clickHandler(e);
            }
        });

        item.style.cursor = 'pointer';
        item.title = `Перейти к: ${pageKey}`;
    });

    console.log(`Инициализировано ${menuItems.length} элементов меню`);
    console.log('Доступные маршруты:', pageMapping);
}

function initializeTranslations() {
    if (window.TranslationManager) {
        window.TranslationManager.initLanguage();

        const savedLang = localStorage.getItem('language') || 'ru';
        if (window.TranslationManager.getCurrentLanguage() !== savedLang) {
            window.TranslationManager.changeLanguage(savedLang);
        }
    }
}

function setupBackButton() {
    console.log('Настройка кнопки "Назад"...');
    console.log('tgUserMenu доступен:', !!tgUserMenu);
    console.log('tgUserMenu.BackButton доступен:', !!(tgUserMenu && tgUserMenu.BackButton));

    if (tgUserMenu && tgUserMenu.BackButton && typeof tgUserMenu.BackButton.show === 'function') {
        console.log('Показ кнопки "Назад"');
        try {
            tgUserMenu.BackButton.show();
            tgUserMenu.BackButton.onClick(() => {
            console.log('Кнопка "Назад" нажата');

            if (window.parent && window.parent.navigateBack && typeof window.parent.navigateBack === 'function') {
                console.log('Используется window.parent.navigateBack');
                window.parent.navigateBack();
            } else if (window.top && window.top.navigateBack && typeof window.top.navigateBack === 'function') {
                console.log('Используется window.top.navigateBack');
                window.top.navigateBack();
            } else if (window.parent && window.parent.showMainPage && typeof window.parent.showMainPage === 'function') {
                console.log('Используется window.parent.showMainPage');
                window.parent.showMainPage();
            } else if (window.showMainPage && typeof window.showMainPage === 'function') {
                console.log('Используется window.showMainPage');
                window.showMainPage();
            } else {
                console.log('Используется window.history.back');
                window.history.back();
            }
        });
        } catch (error) {
            console.warn('BackButton not supported in this Telegram WebApp version:', error);
        }
    } else {
        console.log('Кнопка "Назад" недоступна');
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    console.log('=== Страница пользовательского меню загружена ===');
    console.log('window.loadPage доступен:', typeof window.loadPage);
    console.log('window.parent.loadPage доступен:', window.parent && typeof window.parent.loadPage);
    console.log('window.top.loadPage доступен:', window.top && typeof window.top.loadPage);
    console.log('window.showMainPage доступен:', typeof window.showMainPage);
    console.log('window.parent.showMainPage доступен:', window.parent && typeof window.parent.showMainPage);
    console.log('window.top.showMainPage доступен:', window.top && typeof window.top.showMainPage);
    console.log('window.navigateBack доступен:', typeof window.navigateBack);
    console.log('window.parent.navigateBack доступен:', window.parent && typeof window.parent.navigateBack);
    console.log('window.pageHistory доступен:', typeof window.pageHistory);
    console.log('window.parent.pageHistory доступен:', window.parent && typeof window.parent.pageHistory);
    console.log('window.location.href:', window.location.href);
    console.log('window.parent.location.href:', window.parent ? window.parent.location.href : 'N/A');

    initializeUserProfile();
    initializeMenuItems();
    initializeTranslations();
    setupBackButton();

    console.log('Маршруты определены в Flask приложении');

    console.log('Тестирование навигации...');
    if (typeof window.loadPage === 'function') {
        console.log('window.loadPage доступен');
    } else {
        console.log('window.loadPage НЕ доступен, будет использован резервный вариант');
    }

    const container = document.querySelector('.user-menu-container');
    if (container) {
        container.classList.add('loading');
        setTimeout(() => {
            container.classList.remove('loading');
        }, 300);
    }

    try {
        const teleUser = tgUserMenu?.initDataUnsafe?.user;
        if (teleUser) {
            fetch('/api/user/telegram_profile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user: teleUser }),
            }).catch(e => {
                console.warn('Не удалось синхронизировать профиль Telegram:', e);
            });
        }
    } catch (e) {
        console.warn('Не удалось синхронизировать профиль Telegram:', e);
    }
});

document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {

        initializeUserProfile();
    }
});

window.userMenu = {
    initializeUserProfile,
    handleMenuItemClick,
    initializeMenuItems,
    pageMapping,
    navigateToPage,
    navigateToPageDirect,
    navigateToMenuItem,
    openExternalLink
};

window.navigateToMenuItem = navigateToMenuItem;

window.showMainPage = function() {
    console.log('showMainPage вызвана из user_menu.js');

    if (window.parent && window.parent.showMainPage && typeof window.parent.showMainPage === 'function') {
        console.log('Используется window.parent.showMainPage');
        window.parent.showMainPage();
    } else if (window.top && window.top.showMainPage && typeof window.top.showMainPage === 'function') {
        console.log('Используется window.top.showMainPage');
        window.top.showMainPage();
    } else if (window.parent && window.parent.loadPage && typeof window.parent.loadPage === 'function') {
        console.log('Используется window.parent.loadPage для главной страницы');
        window.parent.loadPage('/');
    } else if (window.top && window.top.loadPage && typeof window.top.loadPage === 'function') {
        console.log('Используется window.top.loadPage для главной страницы');
        window.top.loadPage('/');
    } else {
        console.log('Используется резервная навигация - window.location.href');
        window.location.href = '/';
    }
};

window.navigateBack = function() {
    console.log('navigateBack вызвана из user_menu.js');

    if (window.parent && window.parent.navigateBack && typeof window.parent.navigateBack === 'function') {
        console.log('Используется window.parent.navigateBack');
        window.parent.navigateBack();
    } else if (window.top && window.top.navigateBack && typeof window.top.navigateBack === 'function') {
        console.log('Используется window.top.navigateBack');
        window.top.navigateBack();
    } else if (window.pageHistory && window.pageHistory.length > 1) {
        const previousPage = window.pageHistory.pop();
        console.log('Переход назад к:', previousPage);

        if (window.parent && window.parent.loadPage && typeof window.parent.loadPage === 'function') {
            window.parent.loadPage(previousPage);
        } else if (window.top && window.top.loadPage && typeof window.top.loadPage === 'function') {
            window.top.loadPage(previousPage);
        } else {
            window.history.back();
        }
    } else {

        window.showMainPage();
    }
};
