document.addEventListener('DOMContentLoaded', () => {
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();

    const fromCurrencySelect = document.getElementById('from-currency');
    const toCurrencySelect = document.getElementById('to-currency');
    const swapCurrenciesBtn = document.getElementById('swap-currencies');
    const maxBtn = document.getElementById('max-btn');
    const continueSwapBtn = document.getElementById('continue-swap');
    const fromAmountInput = document.getElementById('from-amount');
    const toAmountDisplay = document.getElementById('to-amount');
    const fromBalanceDisplay = document.getElementById('from-balance-display');
    const fromCoinIcon = document.getElementById('from-coin-icon');
    const toCoinIcon = document.getElementById('to-coin-icon');

    const swapErrors = document.getElementById('swap-errors');
    const swapErrorsReceive = document.getElementById('swap-errors-receive');
    const refreshIcon = document.querySelector('.refresh-icon');

    const swapCoinModal = document.getElementById('swap-coin-modal');
    const swapCoinCloseBtn = document.getElementById('swap-coin-close');
    const swapCoinSearchInput = document.getElementById('swap-coin-search');
    const swapCoinList = document.getElementById('swap-coin-list');

    let currentPickingFor = 'from';
    let selectedFromCoin = { symbol: 'TON', name: 'Toncoin', icon: '/static/images/coins/ton.webp', balance: 0 };
    let selectedToCoin = { symbol: 'USDT', name: 'Tether', icon: '/static/images/coins/usdt.webp', balance: 0 };

    const API_BASE = '';
    let allCryptoCoins = [];

    if (window.TranslationManager) {
      window.TranslationManager.initLanguage();
    }

    async function fetchCryptoData() {
        try {
            const [balancesResp, pricesResp] = await Promise.all([
                fetch(`${API_BASE}/api/balances`),
                fetch(`${API_BASE}/api/crypto/prices`)
            ]);

            if (!balancesResp.ok) throw new Error('Failed to fetch balances');
            if (!pricesResp.ok) throw new Error('Failed to fetch crypto prices');

            const balancesData = await balancesResp.json();
            const pricesData = await pricesResp.json();

            const balances = balancesData.balances || {};
            const prices = pricesData.prices_usd || {};

            allCryptoCoins = Object.keys(prices).map(symbol => ({
                symbol: symbol,
                name: symbol,
                icon: `/static/images/coins/${symbol.toLowerCase()}.webp`,
                balance: balances[symbol] || 0,
                priceUSD: prices[symbol]
            }));

            allCryptoCoins = allCryptoCoins.filter(coin => coin.symbol !== 'GRAM');

            const initialFrom = allCryptoCoins.find(c => c.symbol === selectedFromCoin.symbol);
            const initialTo = allCryptoCoins.find(c => c.symbol === selectedToCoin.symbol);

            if (initialFrom) selectedFromCoin = initialFrom;
            else selectedFromCoin = allCryptoCoins[0] || { symbol: '', name: '', icon: '', balance: 0, priceUSD: 0 };

            if (initialTo) selectedToCoin = initialTo;
            else selectedToCoin = allCryptoCoins[1] || allCryptoCoins[0] || { symbol: '', name: '', icon: '', balance: 0, priceUSD: 0 };
            if (selectedFromCoin.symbol === selectedToCoin.symbol && allCryptoCoins.length > 1) {
                selectedToCoin = allCryptoCoins.find(c => c.symbol !== selectedFromCoin.symbol) || selectedToCoin;
            }

            updateSwapUI();
        } catch (error) {
            console.error('Error fetching crypto data for swap:', error);
            Telegram.WebApp.showAlert(`Error loading crypto data: ${error.message}`);
        }
    }

    function updateSwapUI() {

        fromCoinIcon.src = selectedFromCoin.icon;
        document.querySelector('#from-currency .currency-name').textContent = selectedFromCoin.symbol;
        document.querySelector('#from-currency ~ .balance-section .balance-text').textContent = `${selectedFromCoin.balance.toFixed(2)} ${selectedFromCoin.symbol}`;

        toCoinIcon.src = selectedToCoin.icon;
        document.querySelector('#to-currency .currency-name').textContent = selectedToCoin.symbol;

        fromAmountInput.value = '';
        toAmountDisplay.textContent = '0';
        swapErrors.textContent = '';
        swapErrorsReceive.textContent = '';
        continueSwapBtn.disabled = true;
    }

    function openSwapCoinPicker(forWhich) {
        currentPickingFor = forWhich;
        swapCoinModal.setAttribute('aria-hidden', 'false');
        document.body.classList.add('modal-open');
        filterCoins('');
        Telegram.WebApp.BackButton.show();
        Telegram.WebApp.BackButton.onClick(closeSwapCoinPicker);
    }

    function closeSwapCoinPicker() {
        swapCoinModal.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('modal-open');
        Telegram.WebApp.BackButton.hide();
        Telegram.WebApp.BackButton.offClick(closeSwapCoinPicker);
    }

    function filterCoins(searchTerm) {

        const filteredCoins = allCryptoCoins.filter(coin =>
            coin.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
            (coin.name && coin.name.toLowerCase().includes(searchTerm.toLowerCase()))
        );
        displayCoins(filteredCoins);
    }

    function displayCoins(coins) {
        swapCoinList.innerHTML = '';
        coins.forEach(coin => {
            const li = document.createElement('li');
            li.className = 'row';
            li.dataset.symbol = coin.symbol;
            li.dataset.name = coin.name;
            li.innerHTML = `
                <div class="left">
                    <img src="${coin.icon}" class="coin-icon">
                    <div class="labels">
                        <div class="sym">${coin.symbol}</div>
                        <div class="sub">${coin.name}</div>
                    </div>
                </div>
                <div class="right-mini">
                    <div class="amount-mini">${coin.balance.toFixed(2)}</div>
                    <div class="fiat-mini">$${(coin.balance * (coin.priceUSD || 0)).toFixed(2)}</div>
                </div>
            `;
            li.addEventListener('click', () => {
                if (currentPickingFor === 'from') {
                    if (coin.symbol === selectedToCoin.symbol) {
                        [selectedFromCoin, selectedToCoin] = [selectedToCoin, coin];
                    } else {
                        selectedFromCoin = coin;
                    }
                } else {
                    if (coin.symbol === selectedFromCoin.symbol) {
                        [selectedToCoin, selectedFromCoin] = [selectedFromCoin, coin];
                    } else {
                        selectedToCoin = coin;
                    }
                }
                updateSwapUI();
                closeSwapCoinPicker();
            });
            swapCoinList.appendChild(li);
        });
    }

    fromCurrencySelect.addEventListener('click', () => openSwapCoinPicker('from'));
    toCurrencySelect.addEventListener('click', () => openSwapCoinPicker('to'));

    swapCurrenciesBtn.addEventListener('click', () => {
        [selectedFromCoin, selectedToCoin] = [selectedToCoin, selectedFromCoin];
        updateSwapUI();
    });

    maxBtn.addEventListener('click', () => {
        fromAmountInput.value = selectedFromCoin.balance.toFixed(2);
        fromAmountInput.dispatchEvent(new Event('input'));
    });

    fromAmountInput.addEventListener('input', async () => {
        const amount = parseFloat(fromAmountInput.value);
        if (isNaN(amount) || amount <= 0) {
            toAmountDisplay.textContent = '0';
            swapErrors.textContent = '';
            continueSwapBtn.disabled = true;
            return;
        }

        if (amount > selectedFromCoin.balance) {
            swapErrors.textContent = translationManager.getTranslation('insufficient_funds');
            continueSwapBtn.disabled = true;
            toAmountDisplay.textContent = '0';
            return;
        } else {
            swapErrors.textContent = '';
        }

        let currentExchangeRate = 0;
        try {
            const responseRate = await fetch(`${API_BASE}/api/swap_rate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    from_symbol: selectedFromCoin.symbol,
                    to_symbol: selectedToCoin.symbol,
                })
            });
            if (responseRate.ok) {
                const rateData = await responseRate.json();
                currentExchangeRate = rateData.rate;
            } else {
                throw new Error('Failed to fetch live exchange rate');
            }
        } catch (error) {
            console.error('Error fetching live exchange rate for input:', error);
            swapErrors.textContent = translationManager.getTranslation('rate_unavailable');
            toAmountDisplay.textContent = '0';
            continueSwapBtn.disabled = true;
            return;
        }

        if (currentExchangeRate === 0) {
            swapErrors.textContent = translationManager.getTranslation('rate_unavailable');
            continueSwapBtn.disabled = true;
            toAmountDisplay.textContent = '0';
            return;
        }

        toAmountDisplay.textContent = (amount * currentExchangeRate).toFixed(4);
        continueSwapBtn.disabled = false;
    });

    continueSwapBtn.addEventListener('click', async () => {
        const amount = parseFloat(fromAmountInput.value);
        if (isNaN(amount) || amount <= 0 || amount > selectedFromCoin.balance) {
            Telegram.WebApp.showAlert(translationManager.getTranslation('swap_validation_error'));
            return;
        }

        let actualExchangeRate = 0;
        try {
            const responseRate = await fetch(`${API_BASE}/api/swap_rate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    from_symbol: selectedFromCoin.symbol,
                    to_symbol: selectedToCoin.symbol,
                })
            });
            if (responseRate.ok) {
                const rateData = await responseRate.json();
                actualExchangeRate = rateData.rate;
            } else {
                throw new Error('Failed to fetch live exchange rate');
            }
        } catch (error) {
            console.error('Error fetching live exchange rate:', error);
            Telegram.WebApp.showAlert(translationManager.getTranslation('rate_unavailable'));
            return;
        }

        if (actualExchangeRate === 0) {
            Telegram.WebApp.showAlert(translationManager.getTranslation('rate_unavailable'));
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/api/swap`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    from_symbol: selectedFromCoin.symbol,
                    to_symbol: selectedToCoin.symbol,
                    from_amount: amount
                })
            });

            const data = await response.json();

            if (response.ok) {
                Telegram.WebApp.showAlert(translationManager.getTranslation('swap_success_message')
                    .replace('{amount}', amount.toFixed(4))
                    .replace('{from}', selectedFromCoin.symbol)
                    .replace('{to}', data.to_amount_received.toFixed(4) + ' ' + selectedToCoin.symbol));
                window.location.reload();
            } else {
                Telegram.WebApp.showAlert(`Ошибка обмена: ${data.error || 'Неизвестная ошибка'}`);
            }
        } catch (error) {
            console.error('Error during swap:', error);
            Telegram.WebApp.showAlert(`Произошла ошибка при попытке обмена: ${error.message}`);
        }
    });

    swapCoinCloseBtn.addEventListener('click', closeSwapCoinPicker);

    swapCoinSearchInput.addEventListener('input', (event) => {
        filterCoins(event.target.value);
    });

    refreshIcon.addEventListener('click', async () => {

        refreshIcon.style.transform = 'rotate(360deg)';
        refreshIcon.style.transition = 'transform 0.5s ease';

        try {
            await fetchCryptoData();

            if (fromAmountInput.value && parseFloat(fromAmountInput.value) > 0) {
                fromAmountInput.dispatchEvent(new Event('input'));
            }
        } catch (error) {
            console.error('Error refreshing data:', error);
        } finally {

            setTimeout(() => {
                refreshIcon.style.transform = 'rotate(0deg)';
            }, 500);
        }
    });

    fetchCryptoData();

    Telegram.WebApp.BackButton.show();
    Telegram.WebApp.BackButton.onClick(() => {
        if (swapCoinModal.getAttribute('aria-hidden') === 'false') {
            closeSwapCoinPicker();
        } else {
            window.navigateBack();
        }
    });
});
