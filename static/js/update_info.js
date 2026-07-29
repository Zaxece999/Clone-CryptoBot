(function() {
  const continuePhoneBtn = document.getElementById('continue-phone');
  const personalDataForm = document.getElementById('personal-data-form');
  const submitFinalBtn = document.getElementById('submit-final');
  const firstNameInput = document.getElementById('first-name');
  const lastNameInput = document.getElementById('last-name');
  const birthDaySelect = document.getElementById('birth-day');
  const birthMonthSelect = document.getElementById('birth-month');
  const birthYearSelect = document.getElementById('birth-year');
  const countrySelect = document.getElementById('country');
  const agreeTermsCheckbox = document.getElementById('agree-terms');
  const backToPhoneBtn = document.querySelector('.update-step:not(.hidden) .back-btn');

  function initializeForm() {
    clearStickers();

    if (firstNameInput) firstNameInput.value = '';
    if (lastNameInput) lastNameInput.value = '';

    if (birthDaySelect) birthDaySelect.value = '';
    if (birthMonthSelect) birthMonthSelect.value = '';
    if (birthYearSelect) birthYearSelect.value = '';
    if (countrySelect) countrySelect.value = '';

    populateYears();
    populateMonths();
    populateDays();
    populateCountrySelect();
  }

  function populateYears() {
    if (!birthYearSelect) {
      return;
    }
    const startYear = 1900;
    const endYear = 2025;
    birthYearSelect.innerHTML = '<option value="">Год</option>';
    for (let year = endYear; year >= startYear; year--) {
      const option = document.createElement('option');
      option.value = year;
      option.textContent = year;
      birthYearSelect.appendChild(option);
    }
  }

  function populateMonths() {
    if (!birthMonthSelect) {
      return;
    }
    const months = window.TranslationManager?.t('months') || [
      'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
      'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
    ];
    birthMonthSelect.innerHTML = '<option value="">Месяц</option>';
    months.forEach((month, index) => {
      const option = document.createElement('option');
      option.value = index + 1;
      option.textContent = month;
      birthMonthSelect.appendChild(option);
    });
  }

  function populateDays() {
    if (!birthDaySelect || !birthMonthSelect || !birthYearSelect) {
      return;
    }

    const selectedMonth = parseInt(birthMonthSelect.value, 10);
    const selectedYear = parseInt(birthYearSelect.value, 10);

    if (!selectedMonth || !selectedYear) {
      birthDaySelect.innerHTML = '<option value="">День</option>';
      for (let day = 1; day <= 31; day++) {
        const option = document.createElement('option');
        option.value = day;
        option.textContent = day;
        birthDaySelect.appendChild(option);
      }
      return;
    }

    const daysInMonth = new Date(selectedYear, selectedMonth, 0).getDate();

    birthDaySelect.innerHTML = '<option value="">День</option>';
    for (let day = 1; day <= daysInMonth; day++) {
      const option = document.createElement('option');
      option.value = day;
      option.textContent = day;
      birthDaySelect.appendChild(option);
    }
  }

  const currencyCountryMap = {
    RUB: 'Россия',
    USD: 'United States',
    EUR: 'Eurozone',
    BYN: 'Беларусь',
    UAH: 'Украина',
    GBP: 'United Kingdom',
    CNY: 'Китай',
    KZT: 'Казахстан',
    UZS: 'Узбекистан',
    GEL: 'Грузия',
    TRY: 'Турция',
    AMD: 'Армения',
    THB: 'Таиланд',
    INR: 'Индия',
    BRL: 'Бразилия',
    IDR: 'Индонезия',
    AZN: 'Азербайджан',
    AED: 'United Arab Emirates',
    PLN: 'Польша',
    ILS: 'Израиль',
    KGS: 'Кыргызстан',
    TJS: 'Таджикистан',
  };

  function populateCountrySelect() {
    if (!countrySelect || !currencyCountryMap) {
      return;
    }
    countrySelect.innerHTML = '<option value="">Выберите страну</option>';

    const countries = [...new Set(Object.values(currencyCountryMap))].sort((a, b) => a.localeCompare(b));

    countries.forEach(countryName => {
      const option = document.createElement('option');
      option.value = countryName;
      option.textContent = countryName;
      countrySelect.appendChild(option);
    });
  }

  if (birthMonthSelect) {
    birthMonthSelect.addEventListener('change', populateDays);
  }

  if (birthYearSelect) {
    birthYearSelect.addEventListener('change', populateDays);
  }

  async function loadPhoneSticker() {
    const container = document.getElementById('phone-sticker');
    if (!container) return;

    container.innerHTML = '';

    try {
      const res = await fetch('/static/icons/stickers/phone.tgs');
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      const buffer = await res.arrayBuffer();
      const uint8 = new Uint8Array(buffer);
      const jsonString = pako.inflate(uint8, { to: 'string' });
      const animationData = JSON.parse(jsonString);

      lottie.loadAnimation({
        container,
        renderer: 'svg',
        loop: true,
        autoplay: true,
        animationData
      });
    } catch (e) {
      container.textContent = '📱';
    }
  }

  async function loadDocumentSticker() {
    const container = document.getElementById('document-sticker');
    if (!container) return;

    container.innerHTML = '';

    try {
      const res = await fetch('/static/icons/stickers/document.tgs');
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      const buffer = await res.arrayBuffer();
      const uint8 = new Uint8Array(buffer);
      const jsonString = pako.inflate(uint8, { to: 'string' });
      const animationData = JSON.parse(jsonString);

      lottie.loadAnimation({
        container,
        renderer: 'svg',
        loop: true,
        autoplay: true,
        animationData
      });
    } catch (e) {
      container.textContent = '📄';
    }
  }

  function showStep(stepId) {
    document.querySelectorAll('.update-step').forEach(step => {
      step.classList.add('hidden');
    });

    const targetStep = document.getElementById(stepId);
    if (targetStep) {
      targetStep.classList.remove('hidden');
    }

    if (stepId === 'step-phone') {
      setTimeout(() => loadPhoneSticker(), 0);
    } else if (stepId === 'step-form') {
      initializeForm();
    } else if (stepId === 'step-document') {
      setTimeout(() => loadDocumentSticker(), 0);
    }
  }

  function clearStickers() {
    const phoneSticker = document.getElementById('phone-sticker');
    const documentSticker = document.getElementById('document-sticker');

    if (phoneSticker) phoneSticker.innerHTML = '';
    if (documentSticker) documentSticker.innerHTML = '';
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (window.Telegram && window.Telegram.WebApp) {
      window.Telegram.WebApp.ready();
      window.Telegram.WebApp.expand();

      window.Telegram.WebApp.BackButton.show();
      window.Telegram.WebApp.BackButton.onClick(() => {
        const currentStep = document.querySelector('.update-step:not(.hidden)');
        if (currentStep && currentStep.id === 'step-document') {
          showStep('step-form');
        } else if (currentStep && currentStep.id === 'step-form') {
          showStep('step-phone');
        } else {
          if (window.navigateBack) {
            window.navigateBack();
          }
        }
      });
    }

    if (window.TranslationManager) {
      window.TranslationManager.initLanguage();
      const savedLang = localStorage.getItem('lang') || 'ru';
      if (window.TranslationManager.getCurrentLanguage() !== savedLang) {
        window.TranslationManager.changeLanguage(savedLang);
      }
    }

    initializeForm();
    showStep('step-phone');
  });

  continuePhoneBtn?.addEventListener('click', () => {
    if (window.Telegram && window.Telegram.WebApp) {
      window.Telegram.WebApp.requestContact();

      setTimeout(() => {
        showStep('step-form');
      }, 2500);
    } else {
      showStep('step-form');
    }
  });

  personalDataForm?.addEventListener('submit', (e) => {
    e.preventDefault();

    const firstName = firstNameInput.value.trim();
    const lastName = lastNameInput.value.trim();
    const birthDay = birthDaySelect?.value || '';
    const birthMonth = birthMonthSelect?.value || '';
    const birthYear = birthYearSelect?.value || '';
    const countryCode = countrySelect?.value || '';

    const namePattern = /^[A-Za-zА-Яа-яЁё]+$/;

    if (!namePattern.test(firstName)) {
      alert(window.TranslationManager?.t('name_validation_error') || 'Имя может содержать только русские и английские буквы');
      firstNameInput.focus();
      return;
    }

    if (!namePattern.test(lastName)) {
      alert(window.TranslationManager?.t('lastname_validation_error') || 'Фамилия может содержать только русские и английские буквы');
      lastNameInput.focus();
      return;
    }

    if (!birthDay || !birthMonth || !birthYear) {
      alert(window.TranslationManager?.t('birth_date_validation_error') || 'Пожалуйста, укажите полную дату рождения');
      return;
    }

    const birthDate = new Date(birthYear, parseInt(birthMonth, 10) - 1, parseInt(birthDay, 10));
    const today = new Date();
    let age = today.getFullYear() - birthDate.getFullYear();
    const m = today.getMonth() - birthDate.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) {
      age--;
    }

    if (age < 16) {
      alert(window.TranslationManager?.t('age_validation_error') || 'Вам должно быть не менее 16 лет');
      return;
    }

    if (firstName && lastName && birthDay && birthMonth && birthYear && countryCode) {
      showStep('step-document');
    } else {
      alert(window.TranslationManager?.t('fill_all_fields') || 'Пожалуйста, заполните все поля');
    }
  });

  submitFinalBtn?.addEventListener('click', () => {
    if (agreeTermsCheckbox.checked) {
      alert(window.TranslationManager?.t('success_message') || 'Информация успешно обновлена!');
      if (window.navigateBack) {
        window.navigateBack();
      } else {
        showStep('step-phone');
      }
    } else {
      alert(window.TranslationManager?.t('agree_terms') || 'Необходимо согласиться с условиями');
    }
  });

  const formBackBtn = document.querySelector('.form-buttons .back-btn');
  formBackBtn?.addEventListener('click', () => {
    showStep('step-phone');
  });
})();
