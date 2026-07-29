(function() {
  Telegram.WebApp.ready();
  Telegram.WebApp.expand();

  const currencyList = document.querySelector('.currency-list');

  const CURRENCY_ORDER = [
    'RUB', 'USD', 'EUR', 'BYN', 'UAH', 'GBP', 'CNY', 'KZT', 'UZS', 'GEL', 'TRY', 'AMD', 'THB', 'INR', 'BRL', 'IDR', 'AZN', 'AED', 'PLN', 'ILS', 'KGS', 'TJS'
  ];

  const CURRENCY_FULL_NAMES = {
    'RUB': 'Russian ruble',
    'USD': 'United States Dollar',
    'EUR': 'Euro',
    'BYN': 'Belarusian ruble',
    'UAH': 'Ukrainian hryvnia',
    'GBP': 'Pound sterling',
    'CNY': 'Chinese yuan renminbi',
    'KZT': 'Kazakhstani tenge',
    'UZS': 'Uzbekistani som',
    'GEL': 'Georgian lari',
    'TRY': 'Turkish lira',
    'AMD': 'Armenian dram',
    'THB': 'Thai baht',
    'INR': 'Indian rupee',
    'BRL': 'Brazilian real',
    'IDR': 'Indonesian rupiah',
    'AZN': 'Azerbaijani manat',
    'AED': 'United Arab Emirates dirham',
    'PLN': 'Polish zloty',
    'ILS': 'Israeli new shekel',
    'KGS': 'Kyrgystani som',
    'TJS': 'Tajikistani somoni',
  };

  window.CURRENCY_DISPLAY_SYMBOLS = {
    'USD': '$',
    'EUR': '€',
    'RUB': '₽',
    'BYN': 'Br',
    'UAH': '₴',
    'GBP': '£',
    'CNY': '¥',
    'KZT': '₸',
    'UZS': "сум",
    'GEL': '₾',
    'TRY': '₺',
    'AMD': '֏',
    'THB': '฿',
    'INR': '₹',
    'BRL': 'R$',
    'IDR': 'Rp',
    'AZN': '₼',
    'AED': 'د.إ',
    'PLN': 'zł',
    'ILS': '₪',
    'KGS': 'сом',
    'TJS': 'ЅМ'
  };

  let allFiatCurrencies = [];

  async function fetchAndRenderCurrencies() {
    try {

      let userSettingsData = {};
      try {
        const userSettingsResp = await fetch(`/api/settings`);
        if (userSettingsResp.ok) {
          userSettingsData = await userSettingsResp.json();
        }
      } catch (_) {  }

      allFiatCurrencies = CURRENCY_ORDER.map(code => ({
        code,
        name: CURRENCY_FULL_NAMES[code] || code,
        symbol: (typeof CURRENCY_DISPLAY_SYMBOLS !== 'undefined' ? CURRENCY_DISPLAY_SYMBOLS[code] : code) || code
      }));

          currentBaseCurrency = userSettingsData.base_currency || 'USD';
          renderCurrencyList();
    } catch (error) {
      console.error('Error preparing currencies:', error);
      renderCurrencyList();
      }
  }

  function renderCurrencyList() {
      currencyList.innerHTML = '';
      allFiatCurrencies.forEach(currency => {
          const li = document.createElement('li');
          li.className = 'row';
          li.dataset.code = currency.code;
          li.innerHTML = `
              <div class="left">
                  <img src="/static/images/currency/${currency.code}.webp" class="coin-icon" alt="${currency.code}">
                  <div class="labels">
                      <div class="sym">${currency.code}</div>
                      <div class="sub">${currency.name}</div>
                  </div>
              </div>
              <div class="checkmark-indicator"></div>
          `;

          if (currency.code === currentBaseCurrency) {
              li.querySelector('.checkmark-indicator')?.classList.add('selected');
          }

          li.addEventListener('click', () => {

              currencyList.querySelectorAll('.checkmark-indicator').forEach(indicator => {
                  indicator.classList.remove('selected');
              });

              li.querySelector('.checkmark-indicator')?.classList.add('selected');
              applyCurrencySelection(currency.code);
          });
          currencyList.appendChild(li);
      });
  }

  async function applyCurrencySelection(code) {

      window.currentBaseCurrency = code;

    try {
      await fetch(`/api/settings/currency`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ code: code })
      });

          const event = new CustomEvent('currencyChanged', { detail: { code: code } });
    document.dispatchEvent(event);
          window.navigateBack();

      } catch (e) {
          console.error("Failed to persist currency to backend:", e);
          Telegram.WebApp.showAlert(`Error setting currency: ${e.message}`);
      }
  }

  fetchAndRenderCurrencies();

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
})();
