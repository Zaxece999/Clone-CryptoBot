const demoTransactions = [
	{
		id: 0,
		date: '2 СЕНТЯБРЯ',
		transactions: [
			{
				id: 'tx_usdt_send',
				type: 'send',
				description: 'Отправка USDT',
				time: '2 сен. 00:21',
				cryptoAmount: -20000,
				cryptoCurrency: 'USDT',
				fiatAmount: '10,765,149.12',
				fiatCurrency: 'KZT',
				transactionId: 'B79817482',
				address: '0x7...f12',
				sender: {
					name: 'scowy',
					deals: 2914,
					rating: 99.2,
					volume: '112,346',
					avatarUrl: '/static/images/avatar.jpg',
				},
				comment: 'люблю кошек! 🐱',
			},
		],
	},
	{
		id: 1,
		date: '1 СЕНТЯБРЯ',
		transactions: [
			{
				id: 'tx_009',
				type: 'check',
				description: 'Чек',
				time: '1 сен. 12:40',
				cryptoAmount: 30000,
				cryptoCurrency: 'TON',
				fiatAmount: '7,548,936.98',
				fiatCurrency: 'P',
				checkId: 'IV94817591',
				sender: {
					name: 'sender_name',
					deals: 3815,
					rating: 99.4,
					volume: '854,185.41',
					avatarUrl: '/static/images/euphoria.jpg',
				},
				comment: 'test_comment',
			},
		],
	},
	{
		id: 2,
		date: '22 АВГУСТА',
		transactions: [
			{
				id: 'tx_001',
				type: 'check',
				description: 'Чек',
				time: '22 авг. 15:51',
				cryptoAmount: -0.027879,
				cryptoCurrency: 'USDT',
				fiatAmount: 2.23,
				fiatCurrency: 'P',
			},
			{
				id: 'tx_002',
				type: 'crystalpay',
				description: 'CrystalPAY',
				time: '22 авг. 11:43',
				cryptoAmount: -1.781291,
				cryptoCurrency: 'USDT',
				fiatAmount: 143.1,
				fiatCurrency: 'P',
			},
			{
				id: 'tx_008',
				type: 'withdrawal',
				description: 'Вывод на карту',
				time: '22 авг. 09:15',
				cryptoAmount: -5.0,
				cryptoCurrency: 'USDT',
				fiatAmount: 400.0,
				fiatCurrency: 'P',
			},
		],
	},
];

function getTransactionSVGIcon(type) {
  const iconMap = {
    'buy': `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="18" height="18" rx="9" fill="black"/>
      <path d="M12 5V19M5 12H19" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,

    'sell': `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="18" height="18" rx="9" fill="black"/>
      <path d="M5 12H19" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,

    'send': `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="18" height="18" rx="9" fill="black"/>
      <path d="M22 2L11 13M22 2L15 22L11 13M22 2L2 9L11 13" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,

    'payment': `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="18" height="18" rx="9" fill="black"/>
      <path d="M20 4H4C2.89543 4 2 4.89543 2 6V18C2 19.1046 2.89543 20 4 20H20C21.1046 20 22 19.1046 22 18V6C22 4.89543 21.1046 4 20 4Z" stroke="white" stroke-width="1.5" fill="none"/>
      <path d="M2 10H22" stroke="white" stroke-width="1.5"/>
      <circle cx="6" cy="14" r="1" stroke="white" stroke-width="1.5" fill="none"/>
      <circle cx="10" cy="14" r="1" stroke="white" stroke-width="1.5" fill="none"/>
      <circle cx="14" cy="14" r="1" stroke="white" stroke-width="1.5" fill="none"/>
    </svg>`,

    'withdrawal': `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="18" height="18" rx="9" fill="black"/>
      <path d="M12 5V19M12 19L7 14M12 19L17 14" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,

    'check': `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="18" height="18" rx="9" fill="black"/>
      <path d="M20 6L9 17L4 12" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,

    'crystalpay': `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="18" height="18" rx="9" fill="black"/>
      <path d="M12 2L4 7L12 12L20 7L12 2Z" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M4 12L12 17L20 12" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M4 17L12 22L20 17" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="12" cy="12" r="2" stroke="white" stroke-width="1.5" fill="none"/>
    </svg>`,

    'umarket': `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="18" height="18" rx="9" fill="black"/>
      <path d="M3 3H21V21H3V3Z" stroke="white" stroke-width="1.5" fill="none"/>
      <path d="M3 9H21" stroke="white" stroke-width="1.5"/>
      <path d="M9 21V9" stroke="white" stroke-width="1.5"/>
      <circle cx="6" cy="6" r="1" stroke="white" stroke-width="1.5" fill="none"/>
      <circle cx="18" cy="6" r="1" stroke="white" stroke-width="1.5" fill="none"/>
      <circle cx="6" cy="18" r="1" stroke="white" stroke-width="1.5" fill="none"/>
      <circle cx="18" cy="18" r="1" stroke="white" stroke-width="1.5" fill="none"/>
    </svg>`,

    'default': `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="18" height="18" rx="9" fill="black"/>
      <circle cx="12" cy="12" r="10" stroke="white" stroke-width="1.5" fill="none"/>
      <path d="M12 6V12L16 14" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`
  };

  return iconMap[type] || iconMap.default;
}

function getDetailSVGIcon(type) {
  const iconMap = {
    'order': `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M14 2H6A2 2 0 0 0 4 4V20A2 2 0 0 0 6 22H18A2 2 0 0 0 20 20V8L14 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M14 2V8H20" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M16 13H8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M16 17H8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M10 9H8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,
    'payment-method': `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="2" y="5" width="20" height="14" rx="2" stroke="currentColor" stroke-width="2"/>
      <path d="M2 10H22" stroke="currentColor" stroke-width="2"/>
    </svg>`,
    'details': `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M14 2H6A2 2 0 0 0 4 4V20A2 2 0 0 0 6 22H18A2 2 0 0 0 20 20V8L14 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M14 2V8H20" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M16 13H8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M16 17H8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M10 9H8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,
    'transaction-id': `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M10 6H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2h-5m-4 0V4a2 2 0 114 0v2m-4 0a2 2 0 104 0m-5 8a2 2 0 100-4 2 2 0 000 4zm0 0c1.306 0 2.417.835 2.83 2M9 14a3.001 3.001 0 00-2.83 2M15 11h3m-3 4h2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,
    'address': `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6c0 1.1.9 2 2 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,
    'date': `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="3" y="4" width="18" height="18" rx="2" stroke="currentColor" stroke-width="2"/>
      <path d="M16 2V6M8 2V6M3 10H21" stroke="currentColor" stroke-width="2"/>
    </svg>`,
    'user': `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M20 21V19C20 17.9391 19.5786 16.9217 18.8284 16.1716C18.0783 15.4214 17.0609 15 16 15H8C6.93913 15 5.92172 15.4214 5.17157 16.1716C4.42143 16.9217 4 17.9391 4 19V21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="12" cy="7" r="4" stroke="currentColor" stroke-width="2"/>
    </svg>`,
    'comment': `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,
    'copy': `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="9" y="9" width="13" height="13" rx="2" stroke="currentColor" stroke-width="2"/>
      <path d="M5 15H4C3.46957 15 2.96086 14.7893 2.58579 14.4142C2.21071 14.0391 2 13.5304 2 13V4C2 3.46957 2.21071 2.96086 2.58579 2.58579C2.96086 2.21071 3.46957 2 4 2H13C13.5304 2 14.0391 2.21071 14.4142 2.58579C14.7893 2.96086 15 3.46957 15 4V5" stroke="currentColor" stroke-width="2"/>
    </svg>`,
    'check': `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M20 6L9 17L4 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`
  };

  return iconMap[type] || iconMap.default;
}

function formatCryptoAmount(amount, currency) {
  const sign = amount >= 0 ? '+' : '';
  return `${sign}${amount.toFixed(6)} ${currency}`;
}

function formatFiatAmount(amount, currency) {
  const symbolMap = {
    'P': '₽',
    'RUB': '₽',
    'T': '₸',
    'KZT': '₸',
    'USD': '$',
    'EUR': '€',
    'GBP': '£',
    'UAH': '₴',
    'TRY': '₺',
    'CNY': '¥',
    'JPY': '¥',
    'INR': '₹',
  };
  const symbol = symbolMap[currency] || currency;
  return `${amount} ${symbol}`;
}

function createTransactionItem(transaction) {
  const item = document.createElement('div');
  item.className = 'transaction-item';
  item.dataset.transactionId = transaction.id;

  const iconClass = transaction.type || 'default';
  const svgIcon = getTransactionSVGIcon(transaction.type);

  item.innerHTML = `
    <div class="transaction-icon ${iconClass}">
      ${svgIcon}
    </div>
    <div class="transaction-details">
      <div class="transaction-description">${transaction.description}</div>
      <div class="transaction-time">${transaction.time}</div>
    </div>
    <div class="transaction-amounts">
      <div class="transaction-crypto ${transaction.cryptoAmount >= 0 ? 'positive' : 'negative'}">
        ${formatCryptoAmount(transaction.cryptoAmount, transaction.cryptoCurrency)}
      </div>
      <div class="transaction-fiat">
        ${formatFiatAmount(transaction.fiatAmount, transaction.fiatCurrency)}
      </div>
    </div>
  `;

  item.addEventListener('click', () => {
    openTransactionModal(transaction);
  });

  return item;
}

function createTransactionGroup(group) {
  const groupElement = document.createElement('div');
  groupElement.className = 'transaction-group';

  const dateHeader = document.createElement('div');
  dateHeader.className = 'transaction-date';
  dateHeader.textContent = group.date;

  groupElement.appendChild(dateHeader);

  group.transactions.forEach((transaction, index) => {
    const transactionElement = createTransactionItem(transaction);
    transactionElement.style.animationDelay = `${(index + 1) * 0.1}s`;
    groupElement.appendChild(transactionElement);
  });

  return groupElement;
}

function displayTransactions() {
  const transactionList = document.getElementById('transaction-list');

  if (!transactionList) {
    console.error('Элемент transaction-list не найден!');
    return;
  }

  transactionList.classList.add('loading');

  setTimeout(() => {
    transactionList.innerHTML = '';
    transactionList.classList.remove('loading');

    demoTransactions.forEach((group, index) => {
      const groupElement = createTransactionGroup(group);
      transactionList.appendChild(groupElement);
    });
  }, 300);
}

function createSendTransactionModal(transaction) {
  const cryptoCurrency = transaction.cryptoCurrency || 'USDT';
  let fiatCurrency = transaction.fiatCurrency || 'USD';

  const currencyMapping = {
    'T': 'KZT',
    'P': 'RUB',
    'KZT': 'KZT',
    'RUB': 'RUB',
    'USD': 'USD'
  };

  fiatCurrency = currencyMapping[fiatCurrency] || fiatCurrency;

  return `
    <div class="transaction-summary">
      <div class="transaction-icons-overlay">
        <div class="icons-wrapper">
          <div class="icon-back">
            <img src="/static/images/coins/${cryptoCurrency}.webp" alt="${cryptoCurrency}" class="icon-img">
          </div>
          <div class="icon-front">
            <img src="/static/images/currency/${fiatCurrency}.webp" alt="${fiatCurrency}" class="icon-img">
          </div>
        </div>
      </div>
      <div class="transaction-type">${transaction.description}</div>
      <div class="transaction-amount-large negative">${formatCryptoAmount(transaction.cryptoAmount, transaction.cryptoCurrency)}</div>
      <div class="transaction-spent">${formatFiatAmount(transaction.fiatAmount, transaction.fiatCurrency)}</div>
    </div>

    <div class="transaction-details-list">
      <div class="detail-item">
        <div class="detail-icon">
          ${getDetailSVGIcon('transaction-id')}
        </div>
        <div class="detail-label">ID Транзакции</div>
        <div class="detail-value">${transaction.transactionId}</div>
        <button class="copy-btn" data-copy="${transaction.transactionId}" title="Копировать">
          <span class="copy-icon">${getDetailSVGIcon('copy')}</span>
          <span class="check-icon">${getDetailSVGIcon('check')}</span>
        </button>
      </div>

      <div class="detail-item">
        <div class="detail-icon">
          ${getDetailSVGIcon('address')}
        </div>
        <div class="detail-label">Адрес</div>
        <div class="detail-value">${transaction.address}</div>
        <button class="copy-btn" data-copy="${transaction.address}" title="Копировать">
          <span class="copy-icon">${getDetailSVGIcon('copy')}</span>
          <span class="check-icon">${getDetailSVGIcon('check')}</span>
        </button>
      </div>

      <div class="detail-item">
        <div class="detail-icon">
          ${getDetailSVGIcon('date')}
        </div>
        <div class="detail-label">Дата</div>
        <div class="detail-value">${transaction.time}</div>
      </div>

      <div class="detail-item">
        <div class="detail-icon">
          <img class="counterparty-avatar-img" src="${transaction.sender.avatarUrl || '/static/images/avatar.jpg'}" alt="${transaction.sender.name}">
        </div>
        <div class="detail-label">Отправитель</div>
        <div class="detail-value">
          <div class="counterparty-info">
            <div class="counterparty-details">
              <div class="counterparty-name">${transaction.sender.name}</div>
              <div class="counterparty-stats">${transaction.sender.deals} сделок, ${transaction.sender.rating}%, ${transaction.sender.volume}$</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    ${transaction.comment ? `
    <div class="transaction-conditions">
      <div class="conditions-label">Комментарий</div>
      <div class="conditions-text">
        <div class="highlight">${transaction.comment}</div>
      </div>
    </div>
    ` : ''}

    <button class="back-btn">Назад</button>
  `;
}

function openTransactionModal(transaction) {
  const modal = document.getElementById('transaction-modal');
  const modalBody = document.getElementById('modal-body');

  if (!modal || !modalBody) return;

  let modalContent = '';

  if (transaction.type === 'buy') {
    modalContent = createBuyTransactionModal(transaction);
  } else if (transaction.type === 'check') {
    modalContent = createCheckTransactionModal(transaction);
  } else if (transaction.type === 'send') {
    modalContent = createSendTransactionModal(transaction);
  } else {
    modalContent = createSimpleTransactionModal(transaction);
  }

  modalBody.innerHTML = modalContent;
  modal.classList.add('active');
  document.body.classList.add('modal-open');

  const backBtn = modal.querySelector('.back-btn');
  if (backBtn) {
    backBtn.addEventListener('click', closeTransactionModal);
  }

  const copyBtns = modal.querySelectorAll('.copy-btn');
  copyBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      const textToCopy = e.target.dataset.copy;
      if (textToCopy) {
        btn.classList.add('copied', 'success');

        navigator.clipboard.writeText(textToCopy).then(() => {
          showCopyNotification();
          setTimeout(() => {
            btn.classList.remove('copied', 'success');
          }, 2000);
        }).catch(err => {
          console.error('Ошибка копирования:', err);
          fallbackCopyTextToClipboard(textToCopy);
          setTimeout(() => {
            btn.classList.remove('copied', 'success');
          }, 2000);
        });
      }
    });
  });
}

function closeTransactionModal() {
  const modal = document.getElementById('transaction-modal');
  if (modal) {
    modal.classList.remove('active');
    document.body.classList.remove('modal-open');
  }
}

function fallbackCopyTextToClipboard(text) {
  const textArea = document.createElement('textarea');
  textArea.value = text;
  textArea.style.top = '0';
  textArea.style.left = '0';
  textArea.style.position = 'fixed';
  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();

  try {
    const successful = document.execCommand('copy');
    if (successful) {
      showCopyNotification();
    }
  } catch (err) {
    console.error('Fallback: Ошибка копирования', err);
  }

  document.body.removeChild(textArea);
}

function showCopyNotification() {
  const notification = document.createElement('div');
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: var(--green);
    color: white;
    padding: 12px 20px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    z-index: 1001;
    animation: slideIn 0.3s ease;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  `;
  notification.textContent = 'Скопировано!';

  const style = document.createElement('style');
  style.textContent = `
    @keyframes slideIn {
      from { transform: translateX(100%); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    }
  `;
  document.head.appendChild(style);

  document.body.appendChild(notification);

  setTimeout(() => {
    notification.remove();
    style.remove();
  }, 2000);
}

document.addEventListener('click', (e) => {
  const modal = document.getElementById('transaction-modal');
  if (modal && e.target === modal) {
    closeTransactionModal();
  }
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    const modal = document.getElementById('transaction-modal');
    if (modal && modal.classList.contains('active')) {
      closeTransactionModal();
    }
  }
});

document.addEventListener('DOMContentLoaded', () => {
  console.log('DOM загружен, начинаем отображение транзакций');
  console.log('Количество групп транзакций:', demoTransactions.length);

  setTimeout(() => {
    displayTransactions();
  }, 100);
});

function createSimpleTransactionModal(transaction) {
  const cryptoCurrency = transaction.cryptoCurrency || 'USDT';
  let fiatCurrency = transaction.fiatCurrency || 'P';

  const currencyMapping = {
    'T': 'KZT',
    'P': 'RUB',
    'KZT': 'KZT',
    'RUB': 'RUB'
  };

  fiatCurrency = currencyMapping[fiatCurrency] || fiatCurrency;

  return `
    <div class="transaction-summary">
      <div class="transaction-icons-overlay">
        <div class="icons-wrapper">
          <div class="icon-back">
            <img src="/static/images/coins/${cryptoCurrency}.webp" alt="${cryptoCurrency}" class="icon-img">
          </div>
          <div class="icon-front">
            <img src="/static/images/currency/${fiatCurrency}.webp" alt="${fiatCurrency}" class="icon-img">
          </div>
        </div>
      </div>
      <div class="transaction-type">${transaction.description}</div>
      <div class="transaction-amount-large ${transaction.cryptoAmount >= 0 ? 'positive' : 'negative'}">
        ${formatCryptoAmount(transaction.cryptoAmount, transaction.cryptoCurrency)}
      </div>
      <div class="transaction-spent">${transaction.cryptoAmount >= 0 ? '+' : ''}${formatFiatAmount(transaction.fiatAmount, transaction.fiatCurrency)}</div>
    </div>

    <div class="transaction-details-list">
      <div class="detail-item">
        <div class="detail-icon">
          ${getDetailSVGIcon('date')}
        </div>
        <div class="detail-label">Дата</div>
        <div class="detail-value">${transaction.time}</div>
      </div>
    </div>

    <button class="back-btn">Назад</button>
  `;
}

function createBuyTransactionModal(transaction) {
  const cryptoCurrency = transaction.cryptoCurrency || 'USDT';
  let fiatCurrency = transaction.fiatCurrency || 'T';

  const currencyMapping = {
    'T': 'KZT',
    'P': 'RUB',
    'KZT': 'KZT',
    'RUB': 'RUB'
  };

  fiatCurrency = currencyMapping[fiatCurrency] || fiatCurrency;

  return `
    <div class="transaction-summary">
      <div class="transaction-icons-overlay">
        <div class="icons-wrapper">
          <div class="icon-back">
            <img src="/static/images/coins/${cryptoCurrency}.webp" alt="${cryptoCurrency}" class="icon-img">
          </div>
          <div class="icon-front">
            <img src="/static/images/currency/${fiatCurrency}.webp" alt="${fiatCurrency}" class="icon-img">
          </div>
        </div>
      </div>
      <div class="transaction-type">${transaction.description}</div>
      <div class="transaction-amount-large positive">${formatCryptoAmount(
				transaction.cryptoAmount,
				transaction.cryptoCurrency
			)}</div>
      <div class="transaction-spent">-${formatFiatAmount(
				transaction.fiatAmount,
				transaction.fiatCurrency
			)}</div>
    </div>

    <div class="transaction-details-list">
      <div class="detail-item">
        <div class="detail-icon">
          ${getDetailSVGIcon('order')}
        </div>
        <div class="detail-label">Ордер ID</div>
        <div class="detail-value">${transaction.orderId}</div>
        <button class="copy-btn" data-copy="${
					transaction.orderId
				}" title="Копировать">
          <span class="copy-icon">${getDetailSVGIcon('copy')}</span>
          <span class="check-icon">${getDetailSVGIcon('check')}</span>
        </button>
      </div>

      <div class="detail-item">
        <div class="detail-icon">
          ${getDetailSVGIcon('date')}
        </div>
        <div class="detail-label">Дата</div>
        <div class="detail-value">${transaction.time}</div>
      </div>

      <div class="detail-item">
        <div class="detail-icon">
          <img class="counterparty-avatar-img" src="${
						transaction.counterparty.avatarUrl || '/static/images/avatar.jpg'
					}" alt="${transaction.counterparty.name}">
        </div>
        <div class="detail-label">Контрагент</div>
        <div class="detail-value">
          <div class="counterparty-info">
            <div class="counterparty-details">
              <div class="counterparty-name">${
								transaction.counterparty.name
							}</div>
              <div class="counterparty-stats">${
								transaction.counterparty.deals
							} сделок, ${transaction.counterparty.successRate}, ${
		transaction.counterparty.volume
	}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="detail-item">
        <div class="detail-icon">
          ${getDetailSVGIcon('payment-method')}
        </div>
        <div class="detail-label">Способ оплаты</div>
        <div class="detail-value">${transaction.paymentMethod}</div>
      </div>

      <div class="detail-item">
        <div class="detail-icon">
          ${getDetailSVGIcon('details')}
        </div>
        <div class="detail-label">Реквизиты</div>
        <div class="detail-value">${transaction.accountDetails}</div>
        <button class="copy-btn" data-copy="${
					transaction.accountDetails
				}" title="Копировать">
          <span class="copy-icon">${getDetailSVGIcon('copy')}</span>
          <span class="check-icon">${getDetailSVGIcon('check')}</span>
        </button>
      </div>
    </div>

    ${
			transaction.conditions
				? `
    <div class="transaction-conditions">
      <div class="conditions-label">Условия</div>
      <div class="conditions-text">
        ${transaction.conditions
					.map(condition => `<div class="highlight">${condition}</div>`)
					.join('')}
      </div>
    </div>
    `
				: ''
		}

  <button class="back-btn">Назад</button>
  `;
}

function createCheckTransactionModal(transaction) {
  const cryptoCurrency = transaction.cryptoCurrency || 'TON';
  let fiatCurrency = transaction.fiatCurrency || 'T';

  const currencyMapping = {
    'T': 'KZT',
    'P': 'RUB',
    'KZT': 'KZT',
    'RUB': 'RUB'
  };

  fiatCurrency = currencyMapping[fiatCurrency] || fiatCurrency;

  return `
    <div class="transaction-summary">
      <div class="transaction-icons-overlay">
        <div class="icons-wrapper">
          <div class="icon-back">
            <img src="/static/images/coins/${cryptoCurrency}.webp" alt="${cryptoCurrency}" class="icon-img">
          </div>
          <div class="icon-front">
            <img src="/static/images/currency/${fiatCurrency}.webp" alt="${fiatCurrency}" class="icon-img">
          </div>
        </div>
      </div>
      <div class="transaction-type">${transaction.description}</div>
      <div class="transaction-amount-large positive">${formatCryptoAmount(transaction.cryptoAmount, transaction.cryptoCurrency)}</div>
      <div class="transaction-spent">${formatFiatAmount(transaction.fiatAmount, transaction.fiatCurrency)}</div>
    </div>

    <div class="transaction-details-list">
      <div class="detail-item">
        <div class="detail-icon">
          ${getDetailSVGIcon('order')}
        </div>
        <div class="detail-label">ID Чека</div>
        <div class="detail-value">${transaction.checkId}</div>
        <button class="copy-btn" data-copy="${transaction.checkId}" title="Копировать">
          <span class="copy-icon">${getDetailSVGIcon('copy')}</span>
          <span class="check-icon">${getDetailSVGIcon('check')}</span>
        </button>
      </div>

      <div class="detail-item">
        <div class="detail-icon">
          ${getDetailSVGIcon('date')}
        </div>
        <div class="detail-label">Дата</div>
        <div class="detail-value">${transaction.time}</div>
      </div>

      <div class="detail-item">
        <div class="detail-icon">
          <img class="counterparty-avatar-img" src="${transaction.sender.avatarUrl || '/static/images/avatar.jpg'}" alt="${transaction.sender.name}">
        </div>
        <div class="detail-label">Отправитель</div>
        <div class="detail-value">
          <div class="counterparty-info">
            <div class="counterparty-details">
              <div class="counterparty-name">${transaction.sender.name}</div>
              <div class="counterparty-stats">${transaction.sender.deals} сделок, ${transaction.sender.rating}%, ${transaction.sender.volume}$</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    ${transaction.comment ? `
    <div class="transaction-conditions">
      <div class="conditions-label">Комментарий</div>
      <div class="conditions-text">
        <div class="highlight">${transaction.comment}</div>
      </div>
    </div>
    ` : ''}

    <button class="back-btn">Назад</button>
  `;
}
