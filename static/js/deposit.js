document.addEventListener('DOMContentLoaded', () => {
  if (window.Telegram && window.Telegram.WebApp) {
    window.Telegram.WebApp.ready();
    window.Telegram.WebApp.expand();

    window.Telegram.WebApp.BackButton.show();
    window.Telegram.WebApp.BackButton.onClick(() => {
      window.navigateBack();
    });
  }

  if (window.TranslationManager) {
    window.TranslationManager.initLanguage();
    const savedLang = localStorage.getItem('lang') || 'ru';
    if (window.TranslationManager.getCurrentLanguage() !== savedLang) {
      window.TranslationManager.changeLanguage(savedLang);
    }
  }

  const coinSearchInput = document.getElementById('coin-search');
  const coinList = document.getElementById('coin-list');
  let allCoinsData = [];

  function extractCoinsData() {
    const coins = coinList.querySelectorAll('.row');
    coins.forEach(coin => {
      allCoinsData.push({
        symbol: coin.dataset.symbol,
        name: coin.dataset.name,
        element: coin
      });
    });
  }

  function filterCoins(searchTerm) {
    const lowerCaseSearchTerm = searchTerm.toLowerCase();
    allCoinsData.forEach(coin => {
      const symbol = coin.symbol.toLowerCase();
      const name = coin.name.toLowerCase();
      const isVisible = symbol.includes(lowerCaseSearchTerm) || name.includes(lowerCaseSearchTerm);
      coin.element.style.display = isVisible ? 'flex' : 'none';
    });
  }

  coinSearchInput?.addEventListener('input', (e) => {
    const searchTerm = e.target.value;
    filterCoins(searchTerm);
  });

  coinList?.addEventListener('click', async (e) => {
    const targetRow = e.target.closest('.row');
    if (targetRow) {
      const symbol = targetRow.dataset.symbol;

      const API_BASE = '';

      try {
        const mockAmount = 100;
        const response = await fetch(`${API_BASE}/api/deposit`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ symbol: symbol, amount: mockAmount })
        });

        const data = await response.json();

        if (response.ok) {
          Telegram.WebApp.showAlert(`Успешно пополнено ${mockAmount} ${symbol}!`);

          window.location.reload();
        } else {
          Telegram.WebApp.showAlert(`Ошибка пополнения: ${data.error || 'Неизвестная ошибка'}`);
        }
      } catch (error) {
        console.error('Error during deposit:', error);
        Telegram.WebApp.showAlert(`Произошла ошибка при попытке пополнения: ${error.message}`);
      }

    }
  });

  extractCoinsData();
});
