document.addEventListener('DOMContentLoaded', () => {
  console.log('Settings page loaded');

  if (window.Telegram && window.Telegram.WebApp) {
    window.Telegram.WebApp.ready();
    window.Telegram.WebApp.expand();
  }

  const openTimezonesBtn = document.getElementById('open-timezones');
  const openLanguageBtn = document.getElementById('open-language');
  const openCurrencyBtn = document.getElementById('open-currency');
  const soundsToggle = document.getElementById('sounds-toggle');

  console.log('Settings elements found:', {
    openTimezonesBtn: !!openTimezonesBtn,
    openLanguageBtn: !!openLanguageBtn,
    openCurrencyBtn: !!openCurrencyBtn,
    soundsToggle: !!soundsToggle
  });

  const tzCurrent = document.getElementById('tz-current');
  const langCurrent = document.getElementById('lang-current');
  const baseCurrCurrent = document.getElementById('base-curr-current');

  if (window.TranslationManager) {
    window.TranslationManager.initLanguage();
  }

  const userId = window.userManager.getUserId();

  const timezoneDropdown = createTimezoneDropdown();
  document.body.appendChild(timezoneDropdown);
  console.log('Timezone dropdown created and added to DOM');

  const languageDropdown = createLanguageDropdown();
  document.body.appendChild(languageDropdown);
  console.log('Language dropdown created and added to DOM');

  function createTimezoneDropdown() {
    const dropdown = document.createElement('div');
    dropdown.className = 'custom-dropdown timezone-dropdown';
    dropdown.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      z-index: 1000;
      display: none;
      align-items: center;
      justify-content: center;
    `;

    const content = document.createElement('div');
    content.style.cssText = `
      background: var(--color-surface);
      border-radius: 20px;
      padding: 20px;
      max-height: 80vh;
      width: 90%;
      max-width: 400px;
      overflow-y: auto;
    `;

    const title = document.createElement('h3');
    title.textContent = 'Выберите часовой пояс';
    title.style.cssText = `
      color: white;
      margin: 0 0 20px 0;
      text-align: center;
      font-size: 18px;
    `;

    const searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.placeholder = 'Поиск часового пояса...';
    searchInput.style.cssText = `
      width: 100%;
      padding: 12px;
      border: 1px solid var(--color-border);
      border-radius: 10px;
      background: var(--color-background);
      color: white;
      margin-bottom: 15px;
      font-size: 14px;
    `;

    const timezoneList = document.createElement('div');
    timezoneList.className = 'timezone-list';

    const timezones = [
      'UTC', 'Europe/Moscow', 'Europe/London', 'America/New_York', 'America/Los_Angeles',
      'Asia/Tokyo', 'Asia/Shanghai', 'Asia/Dubai', 'Europe/Paris', 'Europe/Berlin',
      'America/Chicago', 'America/Denver', 'America/Toronto', 'Australia/Sydney',
      'Asia/Kolkata', 'Asia/Seoul', 'Asia/Bangkok', 'Europe/Rome', 'Europe/Madrid',
      'America/Sao_Paulo', 'Africa/Cairo', 'Asia/Jakarta', 'Europe/Amsterdam',
      'America/Mexico_City', 'Asia/Kuala_Lumpur', 'Europe/Stockholm', 'Asia/Manila',
      'America/Buenos_Aires', 'Europe/Vienna', 'Asia/Singapore', 'Europe/Zurich'
    ];

    function renderTimezones(filter = '') {
      timezoneList.innerHTML = '';
      const filtered = timezones.filter(tz =>
        tz.toLowerCase().includes(filter.toLowerCase())
      );

      filtered.forEach(timezone => {
        const item = document.createElement('div');
        item.className = 'timezone-item';
        item.textContent = timezone;
        item.style.cssText = `
          padding: 12px;
          color: white;
          cursor: pointer;
          border-radius: 8px;
          margin-bottom: 5px;
          transition: background 0.2s;
        `;

        item.addEventListener('click', () => {
          selectTimezone(timezone);
          dropdown.style.display = 'none';
        });

        item.addEventListener('mouseenter', () => {
          item.style.background = 'var(--color-primary)';
        });

        item.addEventListener('mouseleave', () => {
          item.style.background = 'transparent';
        });

        timezoneList.appendChild(item);
      });
    }

    searchInput.addEventListener('input', (e) => {
      renderTimezones(e.target.value);
    });

    content.appendChild(title);
    content.appendChild(searchInput);
    content.appendChild(timezoneList);
    dropdown.appendChild(content);

    dropdown.addEventListener('click', (e) => {
      if (e.target === dropdown) {
        dropdown.style.display = 'none';
      }
    });

    return dropdown;
  }

  function createLanguageDropdown() {
    const dropdown = document.createElement('div');
    dropdown.className = 'custom-dropdown language-dropdown';
    dropdown.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      z-index: 1000;
      display: none;
      align-items: center;
      justify-content: center;
    `;

    const content = document.createElement('div');
    content.style.cssText = `
      background: var(--color-surface);
      border-radius: 20px;
      padding: 20px;
      max-height: 80vh;
      width: 90%;
      max-width: 400px;
      overflow-y: auto;
    `;

    const title = document.createElement('h3');
    title.textContent = 'Выберите язык';
    title.style.cssText = `
      color: white;
      margin: 0 0 20px 0;
      text-align: center;
      font-size: 18px;
    `;

    const languageList = document.createElement('div');
    languageList.className = 'language-list';

    const languages = [
      { code: 'ru', name: 'Русский' },
      { code: 'en', name: 'English' }
    ];

    languages.forEach(lang => {
      const item = document.createElement('div');
      item.className = 'language-item';
      item.textContent = lang.name;
      item.dataset.code = lang.code;
      item.style.cssText = `
        padding: 12px;
        color: white;
        cursor: pointer;
        border-radius: 8px;
        margin-bottom: 5px;
        transition: background 0.2s;
      `;

      item.addEventListener('click', () => {
        selectLanguage(lang.code, lang.name);
        dropdown.style.display = 'none';
      });

      item.addEventListener('mouseenter', () => {
        item.style.background = 'var(--color-primary)';
      });

      item.addEventListener('mouseleave', () => {
        item.style.background = 'transparent';
      });

      languageList.appendChild(item);
    });

    content.appendChild(title);
    content.appendChild(languageList);
    dropdown.appendChild(content);

    dropdown.addEventListener('click', (e) => {
      if (e.target === dropdown) {
        dropdown.style.display = 'none';
      }
    });

    return dropdown;
  }

  function selectTimezone(timezone) {
    tzCurrent.textContent = timezone;

    window.userManager.makeApiCall('/api/settings/timezone', {
      timezone: timezone
    }).then(data => {
      if (data.success) {
        localStorage.setItem('timezone', timezone);
        showToast('Часовой пояс обновлен', 'success');
      } else {
        showToast('Ошибка обновления часового пояса', 'error');
      }
    }).catch(error => {
      console.error('Error updating timezone:', error);
      showToast('Ошибка обновления часового пояса', 'error');
    });
  }

  function selectLanguage(langCode, langName) {
    langCurrent.textContent = langName;

    window.userManager.makeApiCall('/api/settings/language', {
      language: langCode
    }).then(data => {
      if (data.success) {
        localStorage.setItem('language', langCode);
        showToast('Язык обновлен', 'success');

        setTimeout(() => {
          window.location.reload();
        }, 1000);
      } else {
        showToast('Ошибка обновления языка', 'error');
      }
    }).catch(error => {
      console.error('Error updating language:', error);
      showToast('Ошибка обновления языка', 'error');
    });
  }

  function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container') || createToastContainer();
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
      background: ${type === 'success' ? 'var(--color-good)' :
                   type === 'error' ? 'var(--color-bad)' : 'var(--color-primary)'};
      color: white;
      padding: 12px 16px;
      border-radius: 10px;
      margin-bottom: 10px;
      font-size: 14px;
      opacity: 0;
      transform: translateY(-20px);
      transition: all 0.3s ease;
    `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '1';
      toast.style.transform = 'translateY(0)';
    }, 100);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(-20px)';
      setTimeout(() => {
        if (toast.parentNode) {
          toast.parentNode.removeChild(toast);
        }
      }, 300);
    }, 3000);
  }

  function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.style.cssText = `
      position: fixed;
      top: 20px;
      left: 50%;
      transform: translateX(-50%);
      z-index: 10000;
      pointer-events: none;
    `;
    document.body.appendChild(container);
    return container;
  }

  function updateSettingsUI() {

    const savedTimezone = localStorage.getItem('timezone') || 'UTC';
    const savedLanguage = localStorage.getItem('language') || 'ru';
    const savedCurrency = localStorage.getItem('currency') || 'USD';
    const savedSounds = localStorage.getItem('sounds') === 'true';

    tzCurrent.textContent = savedTimezone;

    const langName = savedLanguage === 'ru' ? 'Русский' : 'English';
    langCurrent.textContent = langName;
    baseCurrCurrent.textContent = savedCurrency;
    soundsToggle.checked = savedSounds;
  }

  if (openTimezonesBtn) {
    openTimezonesBtn.addEventListener('click', () => {
      console.log('Timezone button clicked, showing dropdown');
      if (timezoneDropdown) {
        timezoneDropdown.style.display = 'flex';
        console.log('Timezone dropdown should be visible now');
      } else {
        console.error('Timezone dropdown not found');
      }
    });
  } else {
    console.error('Timezone button not found');
  }

  if (openLanguageBtn) {
    openLanguageBtn.addEventListener('click', () => {
      console.log('Language button clicked, showing dropdown');
      if (languageDropdown) {
        languageDropdown.style.display = 'flex';
        console.log('Language dropdown should be visible now');
      } else {
        console.error('Language dropdown not found');
      }
    });
  } else {
    console.error('Language button not found');
  }

  openCurrencyBtn.addEventListener('click', () => {
    window.loadPage('/currency_selection');
  });

  soundsToggle.addEventListener('change', (event) => {
    const enabled = event.target.checked;
    localStorage.setItem('sounds', enabled);

    window.userManager.makeApiCall('/api/settings/sounds', {
      sounds_enabled: enabled
    }).then(data => {
      if (data.success) {
        showToast(enabled ? 'Звуки включены' : 'Звуки выключены', 'success');
      } else {
        showToast('Ошибка обновления настроек звука', 'error');
      }
    }).catch(error => {
      console.error('Error updating sounds:', error);
      showToast('Ошибка обновления настроек звука', 'error');
    });
  });

  const tzChevNodes = openTimezonesBtn ? Array.from(openTimezonesBtn.querySelectorAll('.chev')) : [];
  const tzCurrentChevs = [tzCurrent, ...tzChevNodes].filter(Boolean);
  tzCurrentChevs.forEach(el => {
    if (el) {
      el.style.cursor = 'pointer';
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        if (timezoneDropdown) timezoneDropdown.style.display = 'flex';
      });
    }
  });

  const langChevNodes = openLanguageBtn ? Array.from(openLanguageBtn.querySelectorAll('.chev')) : [];
  const langCurrentChevs = [langCurrent, ...langChevNodes].filter(Boolean);
  langCurrentChevs.forEach(el => {
    if (el) {
      el.style.cursor = 'pointer';
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        if (languageDropdown) languageDropdown.style.display = 'flex';
      });
    }
  });

  const currChevNodes = openCurrencyBtn ? Array.from(openCurrencyBtn.querySelectorAll('.chev')) : [];
  const baseCurrChevs = [baseCurrCurrent, ...currChevNodes].filter(Boolean);
  baseCurrChevs.forEach(el => {
    if (el) {
      el.style.cursor = 'pointer';
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        window.loadPage('/currency_selection');
      });
    }
  });

  updateSettingsUI();

  updateSettingsUI();

  try {
    if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.BackButton) {
      window.Telegram.WebApp.BackButton.show();
      window.Telegram.WebApp.BackButton.onClick(() => {
        if (typeof window.navigateBack === 'function') {
          window.navigateBack();
        } else if (window.parent && typeof window.parent.navigateBack === 'function') {
          window.parent.navigateBack();
        } else if (window.history && typeof window.history.back === 'function') {
          window.history.back();
        } else {
          window.location.href = '/';
        }
      });
    }
  } catch (error) {
    console.warn('BackButton not available:', error);
  }

  window.addEventListener('popstate', () => {
    if (typeof window.navigateBack === 'function') {
      window.navigateBack();
    }
  });
});
