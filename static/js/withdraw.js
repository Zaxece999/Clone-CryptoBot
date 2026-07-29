document.addEventListener('DOMContentLoaded', () => {
  if (window.Telegram && window.Telegram.WebApp) {
    window.Telegram.WebApp.ready();
    window.Telegram.WebApp.expand();

    window.Telegram.WebApp.BackButton.show();
    window.Telegram.WebApp.BackButton.onClick(() => {

      const withdrawNetworks = document.getElementById('withdraw-networks');
      const withdrawInsufficient = document.getElementById('withdraw-insufficient');
      const withdrawCoinList = document.getElementById('withdraw-coin-list');

      if (!withdrawNetworks.hidden) {
        withdrawNetworks.hidden = true;
        withdrawCoinList.hidden = false;
      } else if (!withdrawInsufficient.hidden) {
        withdrawInsufficient.hidden = true;
        withdrawCoinList.hidden = false;
      } else {
        window.navigateBack();
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

  const withdrawSearchInput = document.getElementById('withdraw-search');
  const withdrawCoinList = document.getElementById('withdraw-coin-list');
  const withdrawNetworks = document.getElementById('withdraw-networks');
  const withdrawInsufficient = document.getElementById('withdraw-insufficient');
  const insuffIcon = document.getElementById('insuff-icon');
  const insuffTitle = document.getElementById('insuff-title');
  const insuffBalanceEl = document.getElementById('insuff-balance');
  const insuffMin = document.getElementById('insuff-min');
  const insuffFee = document.getElementById('insuff-fee');
  const insuffCoin = document.getElementById('insuff-coin');
  const withdrawBackBtn = document.getElementById('insuff-back-btn');
  const withdrawConfirmBtn = document.getElementById('withdraw-confirm-btn');

  let userBalances = {};
  let selectedWithdrawCoin = null;
  let cryptoPrices = {};
  let exchangeRates = {};
  let allCurrenciesList = [];
  let currentBaseCurrency = 'USD';
  let availableWithdrawCoins = [];

  const CRYPTO_NETWORKS = {
    'USDT': [
      { name: 'Tron', code: 'TRC20', image: 'TRX.webp' },
      { name: 'Ethereum', code: 'ERC20', image: 'ETH.webp' },
      { name: 'BNB Smart Chain', code: 'BEP20', image: 'BNB.webp' },
    ],
    'TON': [
      { name: 'The Open Network', code: 'TON', image: 'TON.webp' },
    ],
    'SOL': [
      { name: 'Solana', code: 'SPL', image: 'SOL.webp' },
    ],
    'TRX': [
      { name: 'Tron', code: 'TRC20', image: 'TRX.webp' },
    ],

    'BTC': [
      { name: 'Bitcoin', code: 'BTC', image: 'BTC.webp' },
      { name: 'BNB Smart Chain', code: 'BEP20', image: 'BNB.webp' },
    ],
    'ETH': [
      { name: 'Ethereum', code: 'ERC20', image: 'ETH.webp' },
      { name: 'BNB Smart Chain', code: 'BEP20', image: 'BNB.webp' },
    ],
    'DOGE': [
      { name: 'Dogecoin', code: 'DOGE', image: 'DOGE.webp' },
    ],
    'LTC': [
      { name: 'Litecoin', code: 'LTC', image: 'LTC.webp' },
    ],
    'NOT': [
      { name: 'The Open Network', code: 'TON', image: 'TON.webp' },
    ],
    'TRUMP': [
      { name: 'Ethereum', code: 'ERC20', image: 'ETH.webp' },
    ],
    'MELANIA': [
      { name: 'Ethereum', code: 'ERC20', image: 'ETH.webp' },
    ],
    'WIF': [
      { name: 'Solana', code: 'SPL', image: 'SOL.webp' },
    ],
    'BONK': [
      { name: 'Solana', code: 'SPL', image: 'SOL.webp' },
    ],
    'USDC': [
      { name: 'Ethereum', code: 'ERC20', image: 'ETH.webp' },
      { name: 'Tron', code: 'TRC20', image: 'TRX.webp' },
      { name: 'BNB Smart Chain', code: 'BEP20', image: 'BNB.webp' },
    ],

  };

  const API_BASE = '';

  async function fetchAndDisplayBalances() {
    try {
      const response = await fetch(`${API_BASE}/api/balances`);
      if (!response.ok) throw new Error('Failed to fetch balances');
      const data = await response.json();
      userBalances = data.balances || {};

      cryptoPrices = window.cryptoPrices && Object.keys(window.cryptoPrices).length > 0
        ? window.cryptoPrices
        : (await window.fetchCryptoPrices());
      exchangeRates = window.exchangeRates && Object.keys(window.exchangeRates).length > 0
        ? window.exchangeRates
        : (await window.fetchExchangeRates());
      allCurrenciesList = window.allCurrenciesList && window.allCurrenciesList.length > 0
        ? window.allCurrenciesList
        : (await window.fetchAllCurrenciesData());
      currentBaseCurrency = window.currentBaseCurrency || 'USD';

      console.log('Withdrawal Menu Data:');
      console.log('  userBalances:', userBalances);
      console.log('  cryptoPrices:', cryptoPrices);
      console.log('  exchangeRates:', exchangeRates);
      console.log('  allCurrenciesList:', allCurrenciesList);
      console.log('  currentBaseCurrency:', currentBaseCurrency);

      availableWithdrawCoins = [];
      for (const symbol in userBalances) {
        if (userBalances.hasOwnProperty(symbol)) {
          const balance = userBalances[symbol];
          if (balance > 0) {
            const cryptoPriceUSD = cryptoPrices[symbol] || 0;
            let convertedValue = 0;

            if (currentBaseCurrency === 'USD') {
                convertedValue = balance * cryptoPriceUSD;
            } else {
                const baseInfo = allCurrenciesList.find(c => c.code === currentBaseCurrency);
                if (baseInfo && baseInfo.type === 'fiat') {
                    const usdToBase = exchangeRates[currentBaseCurrency] || 1;
                    convertedValue = balance * cryptoPriceUSD * usdToBase;
                } else if (baseInfo && baseInfo.type === 'crypto') {
                    const baseCryptoUsd = cryptoPrices[currentBaseCurrency] || 0;
                    convertedValue = baseCryptoUsd > 0 ? (balance * cryptoPriceUSD) / baseCryptoUsd : 0;
                } else {
                    convertedValue = balance * cryptoPriceUSD;
                }
            }
            availableWithdrawCoins.push({
              symbol: symbol,
              name: symbol,
              icon: `/static/images/coins/${symbol.toUpperCase()}.webp`,
              balance: balance,
              convertedValue: convertedValue
            });
          }
        }
      }
      populateCoinList(availableWithdrawCoins);
    } catch (error) {
      console.error('Error fetching balances:', error);
      Telegram.WebApp.showAlert(`Error loading balances: ${error.message}`);
    }
  }

  function populateCoinList(coinsToDisplay) {
    console.log('populateCoinList called with coinsToDisplay:', coinsToDisplay);
    withdrawCoinList.innerHTML = '';
    coinsToDisplay.forEach(coin => {
        const li = document.createElement('li');
        li.className = 'row';
        li.dataset.symbol = coin.symbol;
        li.dataset.name = coin.name;
        li.innerHTML = `
          <div class="left">
            <img src="${coin.icon}" class="coin-icon" alt="${coin.symbol}">
            <div class="labels"><div class="sym">${coin.symbol}</div><div class="sub">${coin.name}</div></div>
          </div>
          <div class="right">
            <div class="amount sensitive">${coin.balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8 })}</div>
            <div class="fiat muted sensitive">${window.formatWithSymbol(currentBaseCurrency, coin.convertedValue)}</div>
          </div>
        `;
        withdrawCoinList.appendChild(li);
        console.log(`Coin ${coin.symbol} added to list. Element:`, li);
    });
  }

  function filterCoins(searchTerm) {
    const lowerCaseSearchTerm = searchTerm.toLowerCase();
    const filteredCoins = availableWithdrawCoins.filter(coin =>
      coin.symbol.toLowerCase().includes(lowerCaseSearchTerm) ||
      coin.name.toLowerCase().includes(lowerCaseSearchTerm)
    );
    populateCoinList(filteredCoins);
  }

  function showWithdrawForm(symbol) {
    selectedWithdrawCoin = symbol;
    withdrawCoinList.hidden = true;
    withdrawNetworks.hidden = false;

    const networkList = document.querySelector('#withdraw-networks .network-list');
    networkList.innerHTML = '';

    const networks = CRYPTO_NETWORKS[symbol] || [];
    if (networks.length === 0) {
      Telegram.WebApp.showAlert(`Нет доступных сетей для ${symbol}.`);

      withdrawNetworks.hidden = true;
      withdrawCoinList.hidden = false;
      return;
    }

    networks.forEach(network => {
      const li = document.createElement('li');
      li.className = 'row';
      li.dataset.network = network.code;
      li.innerHTML = `
        <div class="left">
          <img src="/static/images/coins/${network.image}" class="coin-icon" alt="${network.code}">
          <div class="labels">
            <div class="name">${network.name}</div>
            <div class="sub">${network.code}</div>
          </div>
        </div>
        <div class="chev">›</div>
      `;
      networkList.appendChild(li);
    });

    if (networks.length > 0) {
      networkList.querySelector('.row')?.classList.add('selected');
    }

    document.getElementById('withdraw-amount').value = '';
    document.getElementById('withdraw-address').value = '';
    document.getElementById('withdraw-tag').value = '';
    updateWithdrawRateInfo();
  }

  function showInsufficientFunds(symbol, balance, minAmount, fee) {
    withdrawCoinList.hidden = true;
    withdrawNetworks.hidden = true;
    withdrawInsufficient.hidden = false;

    insuffIcon.querySelector('svg').hidden = true;
    insuffIcon.style.backgroundImage = `url(/static/images/coins/${symbol.toUpperCase()}.webp)`;
    insuffIcon.style.backgroundSize = 'cover';
    insuffIcon.style.backgroundPosition = 'center';
    insuffIcon.style.borderRadius = '50%';

    insuffTitle.textContent = `Недостаточно ${symbol} для вывода`;
    insuffBalanceEl.textContent = `${balance.toFixed(2)} ${symbol}`;
    insuffMin.textContent = `${minAmount.toFixed(4)} ${symbol}`;
    insuffFee.textContent = `${fee.toFixed(4)} ${symbol}`;
    insuffCoin.textContent = symbol;
  }

  function updateWithdrawRateInfo() {
    const withdrawAmountInput = document.getElementById('withdraw-amount');
    const amount = parseFloat(withdrawAmountInput.value);
    const rateInfoEl = document.getElementById('withdraw-rate-info');
    const fee = 0.5;

    if (isNaN(amount) || amount <= 0) {
      rateInfoEl.textContent = `Комиссия: ${fee} ${selectedWithdrawCoin}`;
      withdrawConfirmBtn.disabled = true;
      return;
    }

    const totalAmount = amount + fee;
    rateInfoEl.textContent = `Комиссия: ${fee} ${selectedWithdrawCoin}. Всего: ${totalAmount.toFixed(2)} ${selectedWithdrawCoin}`;
    withdrawConfirmBtn.disabled = false;
  }

  withdrawSearchInput?.addEventListener('input', (e) => {
    const searchTerm = e.target.value.toLowerCase();
    filterCoins(searchTerm);
  });

  withdrawCoinList?.addEventListener('click', (e) => {
    const targetRow = e.target.closest('.row');
    if (targetRow) {
      const symbol = targetRow.dataset.symbol;
      console.log('Clicked coin symbol:', symbol);
      showWithdrawForm(symbol);
    }
  });

  document.getElementById('withdraw-amount')?.addEventListener('input', updateWithdrawRateInfo);

  withdrawConfirmBtn?.addEventListener('click', async () => {
    const amount = parseFloat(document.getElementById('withdraw-amount').value);
    const address = document.getElementById('withdraw-address').value;
    const tag = document.getElementById('withdraw-tag').value;
    const network = document.querySelector('.network-row.selected')?.dataset.network || 'N/A';

    if (!selectedWithdrawCoin || isNaN(amount) || amount <= 0 || !address) {
      Telegram.WebApp.showAlert('Пожалуйста, введите корректные данные для вывода.');
      return;
    }

    const balance = userBalances[selectedWithdrawCoin] || 0;
    const fee = 0.5;
    const totalAmountNeeded = amount + fee;
    const minWithdrawal = 0.0005;

    if (amount < minWithdrawal) {
      showInsufficientFunds(selectedWithdrawCoin, balance, minWithdrawal, fee);
      insuffTitle.textContent = `Минимальная сумма вывода ${minWithdrawal} ${selectedWithdrawCoin}`;
      return;
    }

    if (balance < totalAmountNeeded) {
      showInsufficientFunds(selectedWithdrawCoin, balance, minWithdrawal, fee);
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/withdraw`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: selectedWithdrawCoin, amount: amount, address: address, network: network, tag: tag })
      });

      const data = await response.json();

      if (response.ok) {
        Telegram.WebApp.showAlert(`Успешно выведено ${amount} ${selectedWithdrawCoin} на адрес ${address}`);
        window.location.reload();
      } else {
        Telegram.WebApp.showAlert(`Ошибка вывода: ${data.error || 'Неизвестная ошибка'}`);
      }
    } catch (error) {
      console.error('Error during withdrawal:', error);
      Telegram.WebApp.showAlert(`Произошла ошибка при попытке вывода: ${error.message}`);
    }
  });

  document.querySelector('#withdraw-networks .network-list').addEventListener('click', (e) => {
    const target = e.target.closest('.network-row');
    if (target) {
      document.querySelectorAll('.network-row').forEach(row => row.classList.remove('selected'));
      target.classList.add('selected');
    }
  });

  withdrawBackBtn?.addEventListener('click', () => {
    if (!withdrawNetworks.hidden) {
      withdrawNetworks.hidden = true;
      withdrawCoinList.hidden = false;
    } else if (!withdrawInsufficient.hidden) {
    withdrawInsufficient.hidden = true;
      withdrawNetworks.hidden = false;
    }
  });

  fetchAndDisplayBalances();
  withdrawCoinList.hidden = false;
  withdrawNetworks.hidden = true;
  withdrawInsufficient.hidden = true;
});
