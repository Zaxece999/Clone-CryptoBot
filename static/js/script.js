window.API_BASE = ''
const API_BASE = window.API_BASE
var currentBaseCurrency = 'USD';
var exchangeRates = {}
var fiatCurrencySymbols = {}
var userBalances = {
	USDT: 0,
	TON: 0,
	SOL: 0,
	TRX: 0,
	BTC: 0,
	ETH: 0,
	DOGE: 0,
	LTC: 0,
	BNB: 0,
	USDC: 0,
	NOT: 0,
	TRUMP: 0,
	MELANIA: 0,
	WIF: 0,
	BONK: 0,
}
let allCurrenciesList = []
let cryptoPrices = {}
let priceChanges = {}
let refreshTimerId = null

const depositBtn = document.getElementById('deposit-btn')
const eyeToggle = document.getElementById('eye-toggle')
const withdrawBtn = document.getElementById('withdraw-btn')
const swapBtn = document.getElementById('swap-btn')

const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null
if (tg && typeof tg.expand === 'function') {
	tg.expand()
	try { document.body.style.background = tg.backgroundColor } catch (_) {}
}

const appContent = document.querySelector('.app')
const dynamicContentContainer = document.getElementById(
	'dynamic-content-container'
)
let currentDynamicPage = null
let currentScript = null
let currentStyle = null

window.pageHistory = []

window.loadPage = async function(path) {
	if (currentDynamicPage === path) return

	try {
		console.log(`Attempting to fetch page: ${path}`)
		const response = await fetch(path)
		if (!response.ok) {
			throw new Error(
				`Failed to load ${path}. Status: ${response.status} ${response.statusText}`
			)
		}
		const html = await response.text()

		dynamicContentContainer.innerHTML = ''
		if (currentScript) {
			currentScript.remove()
			currentScript = null
		}
		if (currentStyle) {
			currentStyle.remove()
			currentStyle = null
		}

		dynamicContentContainer.innerHTML = html

		appContent.style.display = 'none'
		dynamicContentContainer.style.display = 'block'

		const scripts = dynamicContentContainer.querySelectorAll('script')
		scripts.forEach((script) => {
			const newScript = document.createElement('script')
			if (script.src) {
				newScript.src = script.src
			} else {
				newScript.textContent = script.textContent
			}
			document.body.appendChild(newScript)
		})

		currentDynamicPage = path
		if (tg && tg.BackButton && typeof tg.BackButton.show === 'function') {
			tg.BackButton.show()
		}
		window.pageHistory.push(path)
		console.log('pageHistory after push:', window.pageHistory)

		const pageName = path.split('/').pop()
		if (pageName && pageName !== '') {
			const cssPath = `/static/css/${pageName}.css`
			console.log(`Attempting to load CSS: ${cssPath}`)

			const existingCSS = document.querySelector(`link[href="${cssPath}"]`)
			if (!existingCSS) {
				const link = document.createElement('link')
				link.rel = 'stylesheet'
				link.href = cssPath
				document.head.appendChild(link)
				currentStyle = link
			} else {
				console.log(`CSS ${cssPath} already loaded, skipping`)
			}
		}

		if (pageName && pageName !== '') {
			const jsPath = `/static/js/${pageName}.js`
			console.log(`Attempting to load JS: ${jsPath}`)

			const existingScript = document.querySelector(`script[src="${jsPath}"]`)
			if (!existingScript) {
				const script = document.createElement('script')
				script.src = jsPath
				script.defer = true
				document.body.appendChild(script)
				currentScript = script
			} else {
				console.log(`Script ${jsPath} already loaded, skipping`)
			}
		}

		if (window.TranslationManager) {
			window.TranslationManager.initLanguage()
		}

		console.log(`Successfully loaded page: ${path}`)
	} catch (error) {
		console.error('Error loading page:', error)
		const pageName = path.split('/').pop()
		const cssPath = pageName ? `/static/css/${pageName}.css` : 'N/A'
		const jsPath = pageName ? `/static/js/${pageName}.js` : 'N/A'

		if (tg && typeof tg.showAlert === 'function') {
			tg.showAlert(
				`Error loading page: ${path}\nDetails: ${error.message}\nCSS path attempted: ${cssPath}\nJS path attempted: ${jsPath}`
			)
		} else {
			alert(`Error loading page: ${path}\nDetails: ${error.message}`)
		}

		showMainPage()
	}
}

window.navigateBack = function() {
	if (window.pageHistory && window.pageHistory.length > 1) {
		window.pageHistory.pop();
		window.loadPage(window.pageHistory[window.pageHistory.length - 1]);
	} else {
		window.showMainPage();
	}
}

window.showMainPage = function() {
	console.log('Showing main page. Clearing dynamic content.')
	dynamicContentContainer.innerHTML = ''
	dynamicContentContainer.style.display = 'none'
	appContent.style.display = 'block'
	currentDynamicPage = null
	if (currentScript) {
		currentScript.remove()
		currentScript = null
	}
	if (currentStyle) {
		currentStyle.remove()
		currentStyle = null
	}
	if (tg && tg.BackButton && typeof tg.BackButton.hide === 'function') {
		tg.BackButton.hide()
	}
	window.pageHistory.splice(0)
	console.log('pageHistory after clear:', window.pageHistory)
}

if (tg && tg.BackButton) {
	tg.BackButton.onClick(() => {
		window.navigateBack()
	})
}

if (window.TranslationManager) {
	window.TranslationManager.initLanguage()

	const savedLang = localStorage.getItem('language') || 'ru'
	if (window.TranslationManager.getCurrentLanguage() !== savedLang) {
		window.TranslationManager.changeLanguage(savedLang)
	}
}

document.addEventListener('currencyChanged', async event => {
	const newCurrencyCode = event.detail.code
	await applyCurrencySymbol(newCurrencyCode)
})

;(async function loadWaveSticker() {
	const container = document.getElementById('wave-sticker')
	if (!container) return
	try {
		const res = await fetch('/static/icons/stickers/wave.tgs')
		const buffer = await res.arrayBuffer()
		const uint8 = new Uint8Array(buffer)
		const jsonString = pako.inflate(uint8, { to: 'string' })
		const animationData = JSON.parse(jsonString)
		lottie.loadAnimation({
			container,
			renderer: 'svg',
			loop: true,
			autoplay: true,
			animationData,
		})
	} catch (e) {

		container.textContent = '👋'
	}
})()

document.getElementById('update-info-banner').addEventListener('click', () => {
	loadPage('/update_info')
})

document.getElementById('user-btn').addEventListener('click', () => {
	loadPage('/user_menu')
})

const currencyBtn = document.getElementById('currency-btn')
if (currencyBtn) {
	currencyBtn.addEventListener('click', e => {
		e.stopPropagation()
		loadPage('/currency_selection')
	})
}

depositBtn.addEventListener('click', () => {
	loadPage('/deposit')
})

withdrawBtn.addEventListener('click', () => {
	loadPage('/withdraw')
})

swapBtn.addEventListener('click', () => {
	loadPage('/swap')
})

const toggleHidden = () => {
	document.body.classList.toggle('hidden-values')
}
eyeToggle?.addEventListener('click', toggleHidden)

const soundsToggle = document.getElementById('sounds-toggle')
if (soundsToggle) {
	const saved = localStorage.getItem('sounds') === 'on'
	soundsToggle.checked = saved
	soundsToggle.addEventListener('change', () => {
		localStorage.setItem('sounds', soundsToggle.checked ? 'on' : 'off')
	})
}

;(() => {
	const tz = localStorage.getItem('timezone')
	if (tz) {

	}

	const savedLang = localStorage.getItem('language') || 'ru'
	if (
		window.TranslationManager &&
		window.TranslationManager.getCurrentLanguage() !== savedLang
	) {
		window.TranslationManager.changeLanguage(savedLang)
	}
})()

function getCurrencySymbol(code) {
	const currency = allCurrenciesList.find(c => c.code === code)
	if (currency && currency.symbol) {
		return currency.symbol
	} else if (currency && currency.type === 'crypto') {
		return code
	}
	return code
}

async function getUsdToBaseRate(baseCurrency) {
	if (!baseCurrency || baseCurrency === 'USD') return 1

	try {
		const response = await fetch(`${API_BASE}/api/convert`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				from_currency: 'USD',
				to_currency: baseCurrency,
				amount: 1,
			}),
		})
		if (!response.ok) throw new Error('Conversion API call failed')
		const data = await response.json()
		return data.rate
	} catch (error) {
		console.error(`Error fetching USD to ${baseCurrency} rate:`, error)

		return 1
	}
}

async function fetchAllCurrenciesData() {
	try {
		const response = await fetch(`${API_BASE}/api/currencies`)
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`)
		}
		allCurrenciesList = await response.json()
		console.log('All currencies loaded:', allCurrenciesList)
	} catch (error) {
		console.error('Error fetching all currencies:', error)

		allCurrenciesList = [
			{ code: 'USD', name: 'United States Dollar', type: 'fiat', symbol: '$' },
			{ code: 'EUR', name: 'Euro', type: 'fiat', symbol: '€' },
			{ code: 'BTC', name: 'Bitcoin', type: 'crypto' },
			{ code: 'ETH', name: 'Ethereum', type: 'crypto' },
		]
	}
}

async function fetchCryptoPrices() {
	try {
		const resp = await fetch(`${API_BASE}/api/crypto/prices`)
		if (!resp.ok) throw new Error('prices api')
		const data = await resp.json()
		const prices = data.prices_usd || {}
		const changes = data.changes_24h_pct || {}

		Object.keys(prices).forEach(sym => {
			const ch = changes[sym]
			if (typeof ch === 'number') {
				priceChanges[sym] = parseFloat(Number(ch).toFixed(2))
			} else {
				const newPrice = prices[sym]
				const oldPrice = cryptoPrices[sym]
				let changePct = 0
				if (oldPrice && oldPrice > 0) changePct = ((newPrice - oldPrice) / oldPrice) * 100
				const prev = priceChanges[sym] ?? 0
				if (Math.abs(changePct) < 0.01 && prev !== 0) changePct = prev
				priceChanges[sym] = parseFloat(Number(changePct).toFixed(2))
			}
		})
		cryptoPrices = prices
		return prices
	} catch (e) {
		console.error('Error fetching crypto prices (frontend):', e)
		return null
	}
}

async function fetchExchangeRates() {

	console.log(
		'fetchExchangeRates called, but rates primarily fetched via /api/convert.'
	)
	if (currentBaseCurrency !== 'USD') {
		exchangeRates[currentBaseCurrency] = await getUsdToBaseRate(
			currentBaseCurrency
		)
		exchangeRates['USD'] = 1
	} else {
		exchangeRates['USD'] = 1
	}
}

async function fetchBalances() {
	try {

		const urlUserId = new URLSearchParams(location.search).get('user_id')

		const userId = (urlUserId ? Number(urlUserId) : null) || tg?.initDataUnsafe?.user?.id || null
		if (!userId) {

			userBalances = {
				USDT: 0,
				TON: 0,
				SOL: 0,
				TRX: 0,
				BTC: 0,
				ETH: 0,
				DOGE: 0,
				LTC: 0,
				BNB: 0,
				USDC: 0,
				NOT: 0,
				TRUMP: 0,
				MELANIA: 0,
				WIF: 0,
				BONK: 0,
			}
			return { balances: userBalances, source: 'no_telegram_user' }
		}

		let response

		if (tg || urlUserId) {
			response = await fetch(`${API_BASE}/api/balances/by-telegram/${userId}`)
		} else {
			response = await fetch(`${API_BASE}/api/balances/user/${userId}`)
		}
		if (!response.ok) throw new Error('balances api')
		const data = await response.json()

		const incoming = data.balances || {}
		userBalances = {
			USDT: Number(incoming.USDT || 0),
			TON: Number(incoming.TON || 0),
			SOL: Number(incoming.SOL || 0),
			TRX: Number(incoming.TRX || 0),
			BTC: Number(incoming.BTC || 0),
			ETH: Number(incoming.ETH || 0),
			DOGE: Number(incoming.DOGE || 0),
			LTC: Number(incoming.LTC || 0),
			BNB: Number(incoming.BNB || 0),
			USDC: Number(incoming.USDC || 0),
			NOT: Number(incoming.NOT || 0),
			TRUMP: Number(incoming.TRUMP || 0),
			MELANIA: Number(incoming.MELANIA || 0),
			WIF: Number(incoming.WIF || 0),
			BONK: Number(incoming.BONK || 0),
		}

		console.log('Balances loaded:', userBalances);
		await updateBalanceDisplay(currentBaseCurrency);
		await updateCryptoFiatValues(currentBaseCurrency);

		return data
	} catch (error) {
		console.error('Error fetching balances (backend):', error)

		userBalances = {
			USDT: 0,
			TON: 0,
			SOL: 0,
			TRX: 0,
			BTC: 0,
			ETH: 0,
			DOGE: 0,
			LTC: 0,
			BNB: 0,
			USDC: 0,
			NOT: 0,
			TRUMP: 0,
			MELANIA: 0,
			WIF: 0,
			BONK: 0,
		}
		return { balances: userBalances }
	}
}

function calculateTotalBalance(baseCurrency) {
	let totalUSD = 0

	Object.keys(userBalances).forEach(crypto => {
		const price = cryptoPrices[crypto] || 0
		totalUSD += userBalances[crypto] * price
	})

	if (baseCurrency === 'USD') {
		return totalUSD
	}

	const baseCurrencyInfo = allCurrenciesList.find(c => c.code === baseCurrency)
	if (baseCurrencyInfo && baseCurrencyInfo.type === 'fiat') {
		const usdToBaseRate = exchangeRates[baseCurrency] || 1
		return totalUSD * usdToBaseRate
	} else if (baseCurrencyInfo && baseCurrencyInfo.type === 'crypto') {
		const baseCryptoPriceInUSD = cryptoPrices[baseCurrency] || 1
		if (baseCryptoPriceInUSD === 0) return 0
		return totalUSD / baseCryptoPriceInUSD
	}

	return totalUSD
}

function formatWithSymbol(code, amount) {
	const symbol = getCurrencySymbol(code)
	const formattedAmount = parseFloat(amount).toLocaleString('en-US', {
		minimumFractionDigits: 2,
		maximumFractionDigits: 2,
	})
	return `<span class=\"currency-symbol\">${symbol}</span><span class=\"balance-digits sensitive\">${formattedAmount}</span>`
}

function formatPrice(code, price) {
	const symbol = getCurrencySymbol(code)
	if (price >= 1) {
		return `${symbol}${price.toLocaleString('en-US', {
			minimumFractionDigits: 2,
			maximumFractionDigits: 2,
		})}`
	} else {
		return `${symbol}${price.toLocaleString('en-US', {
			minimumFractionDigits: 2,
			maximumFractionDigits: 8,
		})}`
	}
}

async function updateBalanceDisplay(baseCurrency) {
	const totalBalance = calculateTotalBalance(baseCurrency)
	const balanceEl = document.querySelector('.amount-balance')

	if (baseCurrency !== 'USD' && !exchangeRates[baseCurrency]) {
		await fetchExchangeRates()
	}

	if (balanceEl) {
		balanceEl.innerHTML = formatWithSymbol(baseCurrency, totalBalance)
	}
}

async function updateCryptoFiatValues(baseCurrency) {

	await fetchCryptoPrices()

	const cryptoRows = document.querySelectorAll('.coin')
	for (const row of cryptoRows) {
		const cryptoIcon = row.querySelector('.coin-icon')
		const cryptoCode = cryptoIcon?.alt

		if (cryptoCode) {
			const cryptoAmount = userBalances[cryptoCode] || 0
			const cryptoPriceUSD = cryptoPrices[cryptoCode] || 0
			let convertedValue = 0
			let displaySymbol = getCurrencySymbol(baseCurrency)

			if (baseCurrency === 'USD') {
				convertedValue = cryptoAmount * cryptoPriceUSD
			} else {
				const baseInfo = allCurrenciesList.find(c => c.code === baseCurrency)
				if (baseInfo && baseInfo.type === 'fiat') {
					const usdToBase = exchangeRates[baseCurrency] || 1
					convertedValue = cryptoAmount * cryptoPriceUSD * usdToBase
				} else if (baseInfo && baseInfo.type === 'crypto') {
					const baseCryptoUsd = cryptoPrices[baseCurrency] || 0
					convertedValue = baseCryptoUsd > 0 ? (cryptoAmount * cryptoPriceUSD) / baseCryptoUsd : 0
				} else {
					convertedValue = cryptoAmount * cryptoPriceUSD
				}
			}

			const amountEl = row.querySelector('.amount')
			if (amountEl) {
				amountEl.textContent = `${cryptoAmount.toLocaleString('en-US', {
					minimumFractionDigits: 2,
					maximumFractionDigits: 2,
				})} ${cryptoCode}`
			}

			const fiatEl = row.querySelector('.fiat')
			if (fiatEl) {
				fiatEl.innerHTML = formatWithSymbol(baseCurrency, convertedValue)
			}

			const priceEl = row.querySelector('.price')
			if (priceEl) {
				const priceChange = priceChanges[cryptoCode] || 0
				const changeClass =
					priceChange > 0 ? 'up' : priceChange < 0 ? 'down' : 'neutral'
				const changeText =
					priceChange > 0 ? `+${priceChange}%` : `${priceChange}%`

				priceEl.innerHTML = `${formatPrice(
					'USD',
					cryptoPriceUSD
				)} <span class=\"${changeClass}\">${changeText}</span>`
			}
		}
	}
}

async function applyCurrencySymbol(code) {
	currentBaseCurrency = code

	const currencyBtn = document.getElementById('currency-btn')
	if (currencyBtn) {
		currencyBtn.textContent = code
	}

	await fetchExchangeRates()
	await fetchCryptoPrices()

	updateBalanceDisplay(code)
	updateCryptoFiatValues(code)
}

async function initializeCurrencySystem() {
	try {
		await fetchAllCurrenciesData()

		const settings = await fetch(`${API_BASE}/api/settings`).then(res =>
			res.json()
		)
		const baseCurrency = settings.base_currency || 'USD'

		await fetchBalances()

		await applyCurrencySymbol(baseCurrency)

		if (refreshTimerId) {
			clearInterval(refreshTimerId)
		}
		refreshTimerId = setInterval(async () => {
			try {
				await fetchCryptoPrices()
				await fetchBalances()
				await updateBalanceDisplay(currentBaseCurrency)
				await updateCryptoFiatValues(currentBaseCurrency)
			} catch (e) {
				console.warn('Auto-refresh failed:', e)
			}
		}, 30000)
	} catch (error) {
		console.error('Error in initializeCurrencySystem:', error)
		if (tg && typeof tg.showAlert === 'function') {
			tg.showAlert('Failed to load initial data. Displaying approximate values.')
		} else if (window.Telegram && window.Telegram.WebApp && typeof window.Telegram.WebApp.showAlert === 'function') {
			window.Telegram.WebApp.showAlert('Failed to load initial data. Displaying approximate values.')
		} else if (typeof window.alert === 'function') {
			alert('Failed to load initial data. Displaying approximate values.')
		}
		const balanceEl = document.querySelector('.amount-balance')
		if (balanceEl) {
			balanceEl.innerHTML = '<span class="currency-symbol">$</span>Loading...'
		}
	} finally {

		showMainPage()
	}
}

document.addEventListener('DOMContentLoaded', async () => {

	try {
		const teleUser = tg?.initDataUnsafe?.user
		if (teleUser) {
			await fetch(`${API_BASE}/api/user/telegram_profile`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ user: teleUser }),
			})
		}
	} catch (e) {
		console.warn('Failed to sync Telegram profile:', e)
	}

	try {
		const avatarEl = document.querySelector('.user .avatar')
		const usernameEl = document.querySelector('.user .username')
		const teleUser = tg?.initDataUnsafe?.user
		if (teleUser && usernameEl) {

			const displayName = teleUser.first_name || 'User'
			usernameEl.textContent = displayName
		}
		if (teleUser && avatarEl) {
			if (teleUser.photo_url) {
				avatarEl.src = teleUser.photo_url
			}
		}
	} catch (e) {
		console.warn('Failed to apply Telegram profile to UI:', e)
	}

	setTimeout(async () => {
		await initializeCurrencySystem()
	}, 100)
})
