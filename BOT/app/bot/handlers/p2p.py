from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from typing import List, Dict
import json
import os

from app.database import get_async_db
from app.bot.keyboards.p2p import (
    get_p2p_menu_keyboard,
    get_order_type_keyboard,
    get_currency_keyboard,
    get_payment_methods_keyboard,
    get_back_keyboard
)
from app.bot.keyboards.inline import get_main_menu_keyboard
from app.models.user import User
from app.services.exchange_rate import exchange_rate_service
from app.services.p2p import p2p_service
from app.services.user import UserService
from app.database import AsyncSessionLocal

logger = structlog.get_logger(__name__)
router = Router()

def load_payment_mapping():
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'payment_mapping.json')
    logger.info(f"DEBUG: Trying to load payment mapping from: {json_path}")
    logger.info(f"DEBUG: File exists: {os.path.exists(json_path)}")
    logger.info(f"DEBUG: Current directory: {os.path.dirname(__file__)}")
    logger.info(f"DEBUG: Files in directory: {os.listdir(os.path.dirname(__file__))}")

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"DEBUG: Successfully loaded payment mapping with {len(data.get('banks_mapping', {}))} banks")
            logger.info(f"DEBUG: First 3 banks: {list(data.get('banks_mapping', {}).keys())[:3]}")
            return data
    except FileNotFoundError:
        logger.warning(f"Payment mapping file not found at {json_path}")
        return {"payment_methods_mapping": {}, "banks_mapping": {}}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing payment mapping JSON: {e}")
        return {"payment_methods_mapping": {}, "banks_mapping": {}}

_payment_mapping_cache = None

def get_payment_mapping():
    global _payment_mapping_cache
    if _payment_mapping_cache is None:
        _payment_mapping_cache = load_payment_mapping()
        logger.info(f"DEBUG: Loaded payment mapping with structure: {list(_payment_mapping_cache.keys())}")
    return _payment_mapping_cache

class CreateOfferStates(StatesGroup):
    type = State()
    crypto = State()
    fiat = State()
    rate_type = State()
    rate_value = State()
    amount = State()
    limits = State()
    payments = State()
    pay_time = State()
    confirm = State()

PAYMENT_CATALOG: Dict[str, List[str]] = {
    "RUB": ["Тинькофф","Сбербанк","Альфа-Банк","ВТБ","Райффайзен","Росбанк","Газпромбанк","Открытие","Почта Банк","Совкомбанк","Промсвязьбанк","МТС Банк","ЮMoney","QIWI","СБП - Система быстрых платежей","WebMoney","Хоум Кредит","Ренессанс","Ак Барс","Уралсиб","Точка","Модульбанк","Банк Санкт-Петербург","МКБ","БКС Банк","Росгосстрах Банк","ЮниКредит Банк","Синара Банк"],
    "USD": ["SWIFT","ACH","Wire Transfer","Zelle","Cash App","Venmo","PayPal","Skrill","Neteller","Wise","Revolut","Advcash","Perfect Money","Western Union","MoneyGram","Paysend","Bank of America","Chase","Wells Fargo","Citi","Capital One","US Bank","PNC","TD Bank","HSBC US","Santander US","Fifth Third","Regions Bank","Ally Bank"],
    "EUR": ["SEPA","SWIFT","Wise","Revolut","PayPal","Skrill","Neteller","Advcash","Perfect Money","Paysend","N26","Bunq","Monese","Raiffeisen","Deutsche Bank","Commerzbank","ING","UniCredit","Santander","BNP Paribas","Societe Generale","Credit Agricole","ABN AMRO","KBC","CaixaBank","La Banque Postale","Intesa Sanpaolo","UBS Europe","Erste"],
    "GBP": ["Faster Payments","SWIFT","Wise","Revolut","Monzo","Starling","Barclays","HSBC","Lloyds","NatWest","Santander UK","TSB","Halifax","Virgin Money","Nationwide","Metro Bank","PayPal"],
    "CNY": ["Alipay","WeChat Pay","UnionPay","Bank Transfer","ICBC","ABC","CCB","Bank of China","China Merchants Bank","Bank of Communications","Ping An Bank","SPD Bank","China CITIC Bank"],
    "KZT": ["Kaspi","Halyk","Jusan","Forte","Eurasian","CenterCredit","Altyn","Sber KZ","Bank RBK","Freedom Finance","Home Credit KZ","ATF Bank","Tengri","VTB KZ","CapitalBank Kazakhstan"],
    "UZS": ["Click","Payme","Apelsin","Kapitalbank UZ","TBC Bank UZ","Ipak Yo'li","Hamkorbank","Uzcard","Humo","Trastbank","Asaka Bank","Mikrokreditbank","Anorbank"],
    "GEL": ["TBC Bank","Bank of Georgia","Liberty Bank","Terabank","Credo Bank","BasisBank","SEPA","Wise","Revolut","Cartu Bank","ProCredit Bank GE"],
    "TRY": ["FAST","Ziraat Bankası","İş Bankası","Garanti BBVA","Akbank","Yapı Kredi","QNB Finansbank","Halkbank","VakıfBank","Enpara","Papara","Paycell","Wise","Revolut","DenizBank","TEB","ING Türkiye"],
    "AMD": ["Ameriabank","ACBA","Inecobank","Ardshinbank","AraratBank","IDBank","EvocaBank","VTB Armenia","Unibank AM","Byblos Bank Armenia"],
    "THB": ["PromptPay","Bangkok Bank","Kasikorn","SCB","Krungthai","Krungsri","TMBThanachart","TrueMoney","LINE Pay","Kiatnakin","UOB Thailand"],
    "INR": ["UPI","IMPS","NEFT","RTGS","HDFC","ICICI","SBI","Axis Bank","Kotak","Paytm","PhonePe","Google Pay","Yes Bank","IDFC FIRST","Punjab National Bank"],
    "BRL": ["PIX","TED","DOC","Banco do Brasil","Bradesco","Itaú","Santander BR","Nubank","Inter","Caixa","Sicredi","Sicoob","BTG Pactual","PicPay","MercadoPago"],
    "IDR": ["BCA","Mandiri","BRI","BNI","CIMB Niaga","Permata","Danamon","Jenius","OVO","GoPay","DANA","LinkAja","SeaBank","Bank Mega"],
    "AZN": ["Kapital Bank","PASHA Bank","ABB","Bank Respublika","UniBank","XalqBank","Leobank","Milliön","Portmanat","Yapi Kredi AZ","TuranBank"],
    "AED": ["Emirates NBD","ADCB","FAB","Mashreq","RAKBANK","ADIB","Noon Pay","STC Pay","SWIFT","Wise","Revolut","Emirates Islamic"],
    "PLN": ["mBank","PKO Bank Polski","Santander Polska","ING Polska","Pekao","Millennium","Alior","BNP Paribas Polska","BLIK","Revolut","Wise","VeloBank","BOŚ Bank"],
    "ILS": ["Bank Hapoalim","Bank Leumi","Discount Bank","Mizrahi Tefahot","Pepper","Bit","PayBox","Bank Transfer","SWIFT","Post Bank Israel","First International Bank"],
    "KGS": ["Optima Bank","KICB","DemirBank","Ayil Bank","Doscredobank","BAKAI Bank","Keremet Bank","MBank","Элкарт","РСК Банк"],
    "TJS": ["Amonatbank","Orienbank","Eskhata Bank","Alif Bank","Spitamen Bank","Humo","Корти Миллӣ","International Bank of Tajikistan"],
    "BYN": ["Беларусбанк","Белагропромбанк","Приорбанк","БПС-Сбербанк","БелВЭБ","МТБанк","Альфа-Банк BY","РРБ-Банк","Технобанк","Банк Дабрабыт","Сбер Банк BY"],
    "UAH": ["Monobank","ПриватБанк","Ощадбанк","ПУМБ","А-Банк","Укргазбанк","Райффайзен","УкрСиббанк","Кредобанк","Идея Банк","ОТП Банк","Південний","МТБ Банк","Банк Восток","Sense Bank"],
}

def map_payment_to_enum(name: str) -> str:
    n = name.lower()
    mapping = get_payment_mapping()

    logger.info(f"DEBUG: Mapping payment '{name}' (lowercase: '{n}')")
    logger.info(f"DEBUG: Available payment methods: {list(mapping.get('payment_methods_mapping', {}).keys())}")
    logger.info(f"DEBUG: Available banks: {list(mapping.get('banks_mapping', {}).keys())}")

    for method_key, method_data in mapping.get("payment_methods_mapping", {}).items():
        keywords = method_data.get("keywords", [])
        logger.info(f"DEBUG: Checking payment method {method_key} with keywords: {keywords}")
        if any(keyword.lower() in n or n in keyword.lower() for keyword in keywords):
            display_name = method_data.get("display_name", method_key)
            logger.info(f"Mapped payment method '{name}' to '{method_data['enum_value']}' (recognized as: {display_name})")
            return method_data["enum_value"]

    for bank_category, bank_data in mapping.get("banks_mapping", {}).items():
        keywords = bank_data.get("keywords", [])
        logger.info(f"DEBUG: Checking bank {bank_category} with keywords: {keywords}")
        if any(keyword.lower() in n or n in keyword.lower() for keyword in keywords):
            display_name = bank_data.get("display_name", bank_category)
            logger.info(f"Mapped bank '{name}' to '{bank_data['enum_value']}' (recognized as: {display_name})")
            return bank_data["enum_value"]

    logger.info(f"Unknown payment method '{name}', defaulting to 'bank_transfer'")
    return "bank_transfer"


@router.message(Command("p2p"))
async def cmd_p2p(message: Message, language_code: str = "ru"):
    await show_p2p_menu(message, language_code)


@router.callback_query(F.data == "p2p_menu")
async def callback_p2p_menu(callback: CallbackQuery, language_code: str = "ru"):
    await show_p2p_menu(callback.message, language_code)
    await callback.answer()


@router.callback_query(F.data == "market-trade-buy")
async def callback_p2p_buy(callback: CallbackQuery, language_code: str = "ru"):
    from app.services.exchange_rates import exchange_rate_service
    from app.services.p2p import p2p_service
    from app.database import get_async_db

    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        from app.models.p2p import P2POrderType

        crypto_list = ["USDT", "TON", "SOL", "TRX", "GRAM", "BTC", "ETH", "DOGE", "LTC", "NOT", "TRUMP", "BNB"]
        rates = await exchange_rate_service.get_multiple_rates(crypto_list, "USD")

        seller_counts = {}
        for crypto in crypto_list:
            orders = await p2p_service.get_orders(
                db=db,
                order_type=P2POrderType.SELL,
                crypto_currency=crypto
            )
            seller_counts[crypto] = len(orders)

        text = "Выберите криптовалюту, которую вы хотите купить."

        builder = InlineKeyboardBuilder()

        crypto_buttons = [
            ("Tether (USDT)", "USDT"),
            ("Toncoin (TON)", "TON"),
            ("Solana (SOL)", "SOL"),
            ("TRON (TRX)", "TRX"),
            ("Gram (GRAM)", "GRAM"),
            ("Bitcoin (BTC)", "BTC"),
            ("Ethereum (ETH)", "ETH"),
            ("Dogecoin (DOGE)", "DOGE"),
            ("Litecoin (LTC)", "LTC"),
            ("Noicoin (NOT)", "NOT"),
            ("Official Trump (TRUMP)", "TRUMP"),
            ("Binance Coin (BNB)", "BNB")
        ]

        for display_name, crypto_code in crypto_buttons:
            rate = rates.get(crypto_code, 0)
            sellers = seller_counts.get(crypto_code, 0)

            button_text = f"{display_name} • ${rate:.2f} • {sellers}"
            builder.add(InlineKeyboardButton(text=button_text, callback_data=f"buy_crypto_{crypto_code}"))

        builder.adjust(1)
        builder.row(InlineKeyboardButton(text="◀️ Назад в P2P Маркет", callback_data="p2p_menu"))

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "market-trade-sell")
async def callback_p2p_sell(callback: CallbackQuery, language_code: str = "ru"):
    from app.services.exchange_rates import exchange_rate_service
    from app.services.p2p import p2p_service
    from app.database import AsyncSessionLocal
    from app.models.p2p import P2POrderType

    async with AsyncSessionLocal() as db:
        crypto_list = ["USDT", "TON", "SOL", "TRX", "GRAM", "BTC", "ETH", "DOGE", "LTC", "NOT", "TRUMP", "BNB"]
        rates = await exchange_rate_service.get_multiple_rates(crypto_list, "USD")

        buyer_counts = {}
        for crypto in crypto_list:
            orders = await p2p_service.get_orders(
                db=db,
                order_type=P2POrderType.BUY,
                crypto_currency=crypto
            )
            buyer_counts[crypto] = len(orders)

        text = "Выберите криптовалюту, которую вы хотите продать."

        builder = InlineKeyboardBuilder()

        crypto_buttons = [
            ("Tether (USDT)", "USDT"),
            ("Toncoin (TON)", "TON"),
            ("Solana (SOL)", "SOL"),
            ("TRON (TRX)", "TRX"),
            ("Gram (GRAM)", "GRAM"),
            ("Bitcoin (BTC)", "BTC"),
            ("Ethereum (ETH)", "ETH"),
            ("Dogecoin (DOGE)", "DOGE"),
            ("Litecoin (LTC)", "LTC"),
            ("Noicoin (NOT)", "NOT"),
            ("Official Trump (TRUMP)", "TRUMP"),
            ("Binance Coin (BNB)", "BNB")
        ]

        for display_name, crypto_code in crypto_buttons:
            rate = rates.get(crypto_code, 0)
            buyers = buyer_counts.get(crypto_code, 0)

            button_text = f"{display_name} • ${rate:.2f} • {buyers}"
            builder.add(InlineKeyboardButton(text=button_text, callback_data=f"sell_crypto_{crypto_code}"))

        builder.adjust(1)
        builder.row(InlineKeyboardButton(text="◀️ Назад в P2P Маркет", callback_data="p2p_menu"))

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "market-manage-orders")
async def callback_p2p_orders(callback: CallbackQuery, language_code: str = "ru"):
    await callback.message.edit_text(
        "📊 Здесь будут ваши сделки и ордера...",
        reply_markup=get_back_keyboard("p2p_menu")
    )
    await callback.answer()


@router.callback_query(F.data == "market-create-offer")
async def callback_p2p_create_offer(callback: CallbackQuery, language_code: str = "ru"):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📈 Хочу купить", callback_data="order_type_buy"),
        InlineKeyboardButton(text="📉 Хочу продать", callback_data="order_type_sell")
    )
    builder.row(InlineKeyboardButton(text="‹ Назад", callback_data="p2p_menu"))
    await callback.message.edit_text(
        "Вы хотите продать или купить криптовалюту?",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.in_(["order_type_buy", "order_type_sell"]))
async def fsm_offer_type(callback: CallbackQuery, state: FSMContext):
    offer_type = "buy" if callback.data == "order_type_buy" else "sell"
    await state.update_data(type=offer_type)
    await state.set_state(CreateOfferStates.crypto)
    b = InlineKeyboardBuilder()
    crypto_order = ["USDT","TON","ETH","USDC","SOL","DOGE","BTC","TRON","BNB","LTC"]
    row = []
    for sym in crypto_order:
        cb = f"crypto_{'TRX' if sym=='TRON' else sym}"
        row.append(InlineKeyboardButton(text=sym, callback_data=cb))
        if len(row) == 3:
            b.row(*row)
            row = []
    if row:
        b.row(*row)
    b.row(InlineKeyboardButton(text="‹ Изменить тип", callback_data="market-create-offer"))
    await callback.message.edit_text(
        "Выберите криптовалюту, которую хотите {}.".format("купить" if offer_type == "buy" else "продать"),
        reply_markup=b.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("crypto_"), CreateOfferStates.crypto)
async def fsm_offer_crypto(callback: CallbackQuery, state: FSMContext):
    crypto = callback.data.split("_")[1]
    await state.update_data(crypto=crypto)
    await state.set_state(CreateOfferStates.fiat)
    fiat_codes = [
        "RUB","USD","EUR","GBP","CNY","KZT","UZS","GEL","TRY","AMD",
        "THB","INR","BRL","IDR","AZN","AED","PLN","ILS","KGS","TJS"
    ]
    b = InlineKeyboardBuilder()
    for i in range(0, len(fiat_codes), 3):
        for code in fiat_codes[i:i+3]:
            b.add(InlineKeyboardButton(text=code, callback_data=f"fiat_{code}"))
        b.adjust(3)
    b.row(InlineKeyboardButton(text="‹ Изменить монету", callback_data="market-create-offer"))
    await callback.message.edit_text(
        f"За какую валюту вы хотите {('купить' if (await state.get_data()).get('type')=='buy' else 'продать')} {crypto}?",
        reply_markup=b.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("fiat_"), CreateOfferStates.fiat)
async def fsm_offer_fiat(callback: CallbackQuery, state: FSMContext):
    fiat = callback.data.split("_")[1]
    await state.update_data(fiat=fiat)
    await state.set_state(CreateOfferStates.rate_type)
    data = await state.get_data()
    crypto = data.get("crypto")
    market_rate = await exchange_rate_service.get_exchange_rate(crypto, fiat) or 0
    market_rate_fmt = f"{market_rate:.2f}"
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="Фиксированная", callback_data="rate_fixed"),
        InlineKeyboardButton(text="Плавающая", callback_data="rate_float")
    )
    b.row(InlineKeyboardButton(text="‹ Изменить валюту", callback_data="market-create-offer"))
    await callback.message.edit_text(
        (
            f"Пришлите процент от биржевого курса (например, +4% или -2.5%) для покупки {crypto}.\n\n"
            f"Биржевой курс: {market_rate_fmt} {fiat}\n"
            f"Источник курса: CoinGecko\n\n"
            f"Цена за {crypto} ≈ {market_rate_fmt} {fiat}\n"
            f"Процент от биржевого курса: 0%"
        ),
        reply_markup=b.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data == "next_rate", CreateOfferStates.rate_type)
async def fsm_offer_rate_next(callback: CallbackQuery, state: FSMContext):
    await state.update_data(rate_type=(await state.get_data()).get("rate_type","float"), rate_value=0)
    await state.set_state(CreateOfferStates.amount)
    data = await state.get_data()
    await callback.message.edit_text(
        f"Пришлите общий объём {data.get('crypto')}, который вы хотите {('купить' if data.get('type')=='buy' else 'продать')}.",
        reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="‹ Изменить цену", callback_data="rate_float")).as_markup()
    )
    await callback.answer()

@router.message(CreateOfferStates.amount)
async def fsm_offer_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace(",", "."))
        await state.update_data(amount=amount)
    except Exception:
        await message.answer("Некорректное значение. Пожалуйста, введите число.")
        return
    await state.set_state(CreateOfferStates.limits)
    data = await state.get_data()
    fiat = data.get('fiat')
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="100-10 700", callback_data="limits_example_100_10700"))
    b.row(InlineKeyboardButton(text="‹ Изменить валюту", callback_data="market-create-offer"))
    await message.answer(
        (
            f"Пришлите лимиты сделки в {fiat} (например, 100-10 700). Лимиты определяют минимальную и максимальную сумму одной сделки.\n\n"
            f"Минимум: 100 {fiat}\nМаксимум: 10 700 {fiat}"
        ),
        reply_markup=b.as_markup()
    )

@router.callback_query(F.data == "limits_example_100_10700", CreateOfferStates.limits)
async def fsm_offer_limits_example(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    crypto = data.get("crypto"); fiat = data.get("fiat")
    market = await exchange_rate_service.get_exchange_rate(crypto, fiat) or 0
    min_limit = int(round(market * 1))
    max_limit = int(round(market * 107))
    if fiat == "RUB":
        min_limit = max(min_limit, 100)
        max_limit = max(max_limit, 10700)
    if fiat == "KZT":
        min_limit = max(int(round(market * 6)), 600)
        max_limit = max(int(round(market * 642)), 64200)
    await state.update_data(limits=(min_limit, max_limit))
    await state.set_state(CreateOfferStates.payments)
    await show_payment_methods(callback, state)
    await callback.answer()

@router.callback_query(F.data.in_(["pm_tinkoff","pm_sber","pm_alfa","pm_vtb","pm_sbp"]), CreateOfferStates.payments)
async def fsm_offer_payments_short(callback: CallbackQuery, state: FSMContext):
    name_map = {"pm_tinkoff":"Тинькофф","pm_sber":"Сбербанк","pm_alfa":"Альфа-Банк","pm_vtb":"ВТБ","pm_sbp":"СБП"}
    cb_name = name_map.get(callback.data, "Банковский перевод")
    data = await state.get_data()
    payments_disp = data.get("payments_disp", [])
    payments_enum = data.get("payments_enum", [])
    if cb_name not in payments_disp:
        payments_disp.append(cb_name)
        payments_enum.append(map_payment_to_enum(cb_name))
    await state.update_data(payments_disp=payments_disp, payments_enum=payments_enum)
    await state.set_state(CreateOfferStates.pay_time)
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="• 15 мин •", callback_data="pt_15"),
        InlineKeyboardButton(text="30 мин", callback_data="pt_30"),
        InlineKeyboardButton(text="45 мин", callback_data="pt_45")
    )
    b.row(
        InlineKeyboardButton(text="1 ч", callback_data="pt_60"),
        InlineKeyboardButton(text="2 ч", callback_data="pt_120"),
        InlineKeyboardButton(text="3 ч", callback_data="pt_180")
    )
    b.row(InlineKeyboardButton(text="Далее ›", callback_data="pt_next"))
    b.row(InlineKeyboardButton(text="‹ Изменить лимиты", callback_data="back_limits"))
    await callback.message.edit_text(
        "Выберите период времени, в течение которого должна быть подтверждена отправка оплаты.",
        reply_markup=b.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("pmidx_"), CreateOfferStates.payments)
async def fsm_offer_payment_from_catalog(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[1])
    data = await state.get_data()
    fiat = data.get("fiat")
    methods = PAYMENT_CATALOG.get(fiat, [])
    if idx < 0 or idx >= len(methods):
        await callback.answer()
        return

    disp = methods[idx]
    payments_disp = data.get("payments_disp", [])
    payments_enum = data.get("payments_enum", [])

    if disp in payments_disp:
        payments_disp.remove(disp)
        enum_value = map_payment_to_enum(disp)
        if enum_value in payments_enum:
            payments_enum.remove(enum_value)
    else:
        if len(payments_disp) < 5:
            payments_disp.append(disp)
            payments_enum.append(map_payment_to_enum(disp))
        else:
            await callback.answer("Можно выбрать максимум 5 способов оплаты", show_alert=True)
            return

    await state.update_data(payments_disp=payments_disp, payments_enum=payments_enum)
    await show_payment_methods(callback, state)
    await callback.answer()

@router.callback_query(F.data == "continue_to_pay_time", CreateOfferStates.payments)
async def fsm_continue_to_pay_time(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    payments_disp = data.get("payments_disp", [])

    if not payments_disp:
        await callback.answer("Выберите хотя бы один способ оплаты", show_alert=True)
        return

    await state.set_state(CreateOfferStates.pay_time)
    await show_pay_time_selection(callback, state)
    await callback.answer()

async def show_pay_time_selection(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_time = data.get('pay_time', 15)

    b = InlineKeyboardBuilder()
    time_options = [
        ("pt_15", "15 мин", 15),
        ("pt_30", "30 мин", 30),
        ("pt_45", "45 мин", 45),
        ("pt_60", "1 ч", 60),
        ("pt_120", "2 ч", 120),
        ("pt_180", "3 ч", 180)
    ]

    row1 = []
    for callback_data, display, value in time_options[:3]:
        text = f"• {display} •" if value == selected_time else display
        row1.append(InlineKeyboardButton(text=text, callback_data=callback_data))
    b.row(*row1)

    row2 = []
    for callback_data, display, value in time_options[3:]:
        text = f"• {display} •" if value == selected_time else display
        row2.append(InlineKeyboardButton(text=text, callback_data=callback_data))
    b.row(*row2)

    b.row(InlineKeyboardButton(text="Далее ›", callback_data="pt_next"))
    b.row(InlineKeyboardButton(text="‹ Изменить способы оплаты", callback_data="back_to_payments"))

    await callback.message.edit_text(
        "Выберите период времени, в течение которого должна быть подтверждена отправка оплаты.",
        reply_markup=b.as_markup()
    )

@router.callback_query(F.data.in_(["pt_15","pt_30","pt_45","pt_60","pt_120","pt_180"]), CreateOfferStates.pay_time)
async def fsm_offer_pay_time_short(callback: CallbackQuery, state: FSMContext):
    mapping = {"pt_15":15,"pt_30":30,"pt_45":45,"pt_60":60,"pt_120":120,"pt_180":180}
    await state.update_data(pay_time=mapping[callback.data])
    await show_pay_time_selection(callback, state)
    await callback.answer()

@router.callback_query(F.data == "pt_next", CreateOfferStates.pay_time)
async def fsm_offer_pay_time_next_short(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if 'pay_time' not in data:
        await state.update_data(pay_time=15)
    await _show_confirm(callback, state)

@router.callback_query(F.data == "back_to_pay_time_from_confirm", CreateOfferStates.confirm)
async def back_to_pay_time_from_confirm(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CreateOfferStates.pay_time)
    await show_pay_time_selection(callback, state)
    await callback.answer()

async def _show_confirm(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CreateOfferStates.confirm)
    logger.info("Set state to confirm", user_id=callback.from_user.id, state="confirm")
    data = await state.get_data()
    payments_display = ", ".join(data.get('payments_disp', [])) or "не указаны"
    text = (
        "Проверка и подтверждение\n\n"
        f"{('Покупка' if data.get('type')=='buy' else 'Продажа')} {data.get('crypto')} за {data.get('fiat')}.\n\n"
        f"Цена: {data.get('rate_value')} {data.get('fiat')}\n\n"
        f"Общий объём: {data.get('amount')} {data.get('crypto')}\n"
        f"Лимиты: {data.get('limits')[0]} {data.get('fiat')} ~ {data.get('limits')[1]} {data.get('fiat')}\n\n"
        f"Способы оплаты:\n1. {payments_display}\n\n"
        f"Срок оплаты: {data.get('pay_time', 15)} мин"
    )
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="Создать объявление", callback_data="offer_publish"))
    b.row(InlineKeyboardButton(text="‹ Изменить срок оплаты", callback_data="back_to_pay_time_from_confirm"))
    await callback.message.edit_text(text, reply_markup=b.as_markup())


@router.callback_query(F.data == "market-settings")
async def callback_p2p_settings(callback: CallbackQuery, language_code: str = "ru"):
    text = "Здесь вы можете выбрать валюту отображаемых объявлений или управлять своими способами оплаты."

    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(text="Валюта P2P Маркета: RUB", callback_data="select_p2p_currency"))
    builder.add(InlineKeyboardButton(text="Способы оплаты", callback_data="manage_payment_methods"))
    builder.adjust(1)

    builder.add(InlineKeyboardButton(text="Справка Crypto Bot", url="https://help.send.tg/ru/articles/9819562-как-купить-монеты"))
    builder.add(InlineKeyboardButton(text="Что умеет Crypto Bot", url="http://t.me/CryptoBotTips"))
    builder.adjust(1)

    builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data="p2p_menu"))
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "select_p2p_currency")
async def callback_select_p2p_currency(callback: CallbackQuery, language_code: str = "ru"):
    text = "Выберите локальную валюту для покупки и продажи монет в Р2Р Маркете."

    currencies = [
        ("🇷🇺 RUB", "RUB"),
        ("🇺🇸 USD", "USD"),
        ("🇪🇺 EUR", "EUR"),
        ("🇧🇾 BYN", "BYN"),
        ("🇺🇦 UAH", "UAH"),
        ("🇰🇿 KZT", "KZT"),
        ("🇺🇿 UZS", "UZS"),
        ("🇬🇪 GEL", "GEL"),
        ("🇹🇷 TRY", "TRY"),
        ("🇦🇲 AMD", "AMD"),
        ("🇹🇭 THB", "THB"),
        ("🇮🇳 INR", "INR"),
        ("🇧🇷 BRL", "BRL"),
        ("🇮🇩 IDR", "IDR"),
        ("🇦🇿 AZN", "AZN"),
        ("🇦🇪 AED", "AED"),
        ("🇵🇱 PLN", "PLN"),
        ("🇮🇱 ILS", "ILS"),
        ("🇰🇬 KGS", "KGS"),
        ("🇹🇯 TJS")
    ]

    builder = InlineKeyboardBuilder()

    for i in range(0, len(currencies), 4):
        row = currencies[i:i+4]
        for display_name, currency_code in row:
            builder.add(InlineKeyboardButton(text=display_name, callback_data=f"set_currency_{currency_code}"))

    builder.adjust(4)

    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="market-settings"))

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("set_currency_"))
async def callback_set_currency(callback: CallbackQuery, language_code: str = "ru"):
    currency = callback.data.split("_")[2]

    flag_map = {
        "RUB": "🇷🇺",
        "USD": "🇺🇸",
        "EUR": "🇪🇺",
        "BYN": "🇧🇾",
        "UAH": "🇺🇦",
        "KZT": "🇰🇿",
        "UZS": "🇺🇿",
        "GEL": "🇬🇪",
        "TRY": "🇹🇷",
        "AMD": "🇦🇲",
        "THB": "🇹🇭",
        "INR": "🇮🇳",
        "BRL": "🇧🇷",
        "IDR": "🇮🇩",
        "AZN": "🇦🇿",
        "AED": "🇦🇪",
        "PLN": "🇵🇱",
        "ILS": "🇮🇱",
        "KGS": "🇰🇬",
        "TJS": "🇹🇯"
    }

    flag = flag_map.get(currency, "")

    text = "Здесь вы можете выбрать валюту отображаемых объявлений или управлять своими способами оплаты."

    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(text=f"Валюта P2P Маркета: · {flag} {currency} ·", callback_data="select_p2p_currency"))
    builder.add(InlineKeyboardButton(text="Способы оплаты", callback_data="manage_payment_methods"))
    builder.adjust(1)

    builder.add(InlineKeyboardButton(text="Справка Crypto Bot", url="https://help.send.tg/ru/articles/9819562-как-купить-монеты"))
    builder.add(InlineKeyboardButton(text="Что умеет Crypto Bot", url="http://t.me/CryptoBotTips"))
    builder.adjust(1)

    builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data="p2p_menu"))
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "open-profile")
async def callback_p2p_profile(callback: CallbackQuery):
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        from app.services.user import UserService
        from app.services.p2p import p2p_service

        user_service = UserService()
        user = await user_service.get_user_by_telegram_id(session, callback.from_user.id)

        if not user:
            await callback.answer("Пользователь не найден")
            return

        await callback.answer()

        stats_30d = await p2p_service.get_user_stats(session, user_id=user.id, days=30)

        if stats_30d:
            total_volume = Decimal(stats_30d.buy_volume_usd) + Decimal(stats_30d.sell_volume_usd)
            stats_text = (
                f"🏆 {stats_30d.total_trades} сделок · {stats_30d.completion_rate:.1f}% выполнено · ${total_volume:.2f}\n\n"
                f"Срок отправки оплаты: ~{stats_30d.average_payment_time_minutes} мин\n"
                f"Срок перевода монет: ~{stats_30d.average_release_time_minutes} мин"
            )
            positive_feedback_percent = (stats_30d.average_rating / 5 * 100) if stats_30d.total_ratings > 0 else 0
            reviews_text = f"Мои отзывы · {stats_30d.total_ratings} · 👍 {positive_feedback_percent:.0f}%"
        else:
            stats_text = (
                "🏆 0 сделок · 0.0% выполнено · $0.00\n\n"
                "Срок отправки оплаты: ~5 мин\n"
                "Срок перевода монет: ~2 мин"
            )
            reviews_text = "Мои отзывы · 0 · 👍 0%"

        p2p_nickname = getattr(user, 'p2p_nickname', None)
        nickname_display = f"{p2p_nickname}" if p2p_nickname else ""
        text = (
            f"👤 {nickname_display}\n\n"
            f"Ваша статистика торговли за 30 дней:\n"
            f"{stats_text}"
        )

        builder = InlineKeyboardBuilder()

        builder.button(text="· За 30 дней ·", callback_data="change-user-stat-30d")
        builder.button(text="За всё время", callback_data="change-user-stat-all")

        builder.button(text="Мои объявления", callback_data="my_ads")

        builder.button(text="🔡 Установить имя пользователя", callback_data="set_username")

        builder.button(text="⛔️ Чёрный список", callback_data="blacklist")

        builder.button(text=reviews_text, callback_data="my_reviews")

        builder.button(text="‹ Назад в P2P Маркет", callback_data="p2p_menu")

        builder.adjust(2, 1, 1, 1, 1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("change-user-stat-"))
async def change_user_stat_range(callback: CallbackQuery):
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        from app.services.user import UserService
        from app.services.p2p import p2p_service

        user_service = UserService()
        user = await user_service.get_user_by_telegram_id(session, callback.from_user.id)

        if not user:
            await callback.answer("Пользователь не найден")
            return

        await callback.answer()

        range_type = callback.data.split("-")[-1]

        if range_type == "30d":
            days = 30
            range_text_part1 = "· За 30 дней ·"
            range_text_part2 = "За всё время"
            range_text = "30 дней"
        else:
            days = None
            range_text_part1 = "За 30 дней"
            range_text_part2 = "· За всё время ·"
            range_text = "всё время"

        stats = await p2p_service.get_user_stats(session, user_id=user.id, days=days)

        if stats:
            total_volume = Decimal(stats.buy_volume_usd) + Decimal(stats.sell_volume_usd)
            stats_text = (
                f"🏆 {stats.total_trades} сделок · {stats.completion_rate:.1f}% выполнено · ${total_volume:.2f}\n\n"
                f"Срок отправки оплаты: ~{stats.average_payment_time_minutes} мин\n"
                f"Срок перевода монет: ~{stats.average_release_time_minutes} мин"
            )
            positive_feedback_percent = (stats.average_rating / 5 * 100) if stats.total_ratings > 0 else 0
            reviews_text = f"Мои отзывы · {stats.total_ratings} · 👍 {positive_feedback_percent:.0f}%"
        else:
            stats_text = (
                "🏆 0 сделок · 0.0% выполнено · $0.00\n\n"
                "Срок отправки оплаты: ~5 мин\n"
                "Срок перевода монет: ~2 мин"
            )
            reviews_text = "Мои отзывы · 0 · 👍 0%"

        p2p_nickname = getattr(user, 'p2p_nickname', None)
        nickname_display = f"{p2p_nickname}" if p2p_nickname else ""
        text = (
            f"👤 {nickname_display}\n\n"
            f"Ваша статистика торговли за {range_text}:\n"
            f"{stats_text}"
        )

        builder = InlineKeyboardBuilder()

        builder.button(text=range_text_part1, callback_data="change-user-stat-30d")
        builder.button(text=range_text_part2, callback_data="change-user-stat-all")

        builder.button(text="Мои объявления", callback_data="my_ads")

        builder.button(text="🔡 Установить имя пользователя", callback_data="set_username")

        builder.button(text="⛔️ Чёрный список", callback_data="blacklist")

        builder.button(text=reviews_text, callback_data="my_reviews")

        builder.button(text="‹ Назад в P2P Маркет", callback_data="p2p_menu")

        builder.adjust(2, 1, 1, 1, 1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "set_username")
async def set_username_check(callback: CallbackQuery, state: FSMContext):
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        from app.services.user import UserService
        from app.services.p2p import p2p_service

        user_service = UserService()
        user = await user_service.get_user_by_telegram_id(session, callback.from_user.id)

        if not user:
            await callback.answer("Пользователь не найден", show_alert=True)
            return

        stats = await p2p_service.get_user_stats(session, user.id, days=None)

        if stats and stats.total_trades >= 10 and stats.completion_rate >= 80:
            await callback.message.answer("Введите новый никнейм:")
            await state.set_state("set_p2p_nickname")
        else:
            await callback.answer(
                "Для того, чтобы установить имя пользователя у вас должно быть 10 сделок и 80% завершенных.",
                show_alert=True
            )

@router.message(F.state == "set_p2p_nickname")
async def set_p2p_nickname(message: Message, state: FSMContext):
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        from app.services.user import user_service

        user = await user_service.get_user_by_telegram_id(session, message.from_user.id)
        if user:
            user.p2p_nickname = message.text
            await session.commit()
            await message.answer(f"Ваш новый никнейм: {message.text}")
        else:
            await message.answer("Произошла ошибка, попробуйте еще раз.")

        await state.clear()


@router.callback_query(F.data == "blacklist")
async def show_blacklist(callback: CallbackQuery):
    await callback.answer()

    text = "Здесь вы можете управлять своими заблокированными пользователями."

    builder = InlineKeyboardBuilder()
    builder.button(text="< Назад", callback_data="open-profile")

    await callback.message.edit_text(text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "my_ads")
async def show_my_ads(callback: CallbackQuery):
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        from app.services.user import UserService
        from app.services.p2p import p2p_service
        from app.models.p2p import P2POrderType

        user_service = UserService()
        user = await user_service.get_user_by_telegram_id(session, callback.from_user.id)

        if not user:
            await callback.answer("Пользователь не найден")
            return

        await callback.answer()

        all_buy_orders = await p2p_service.get_orders(db=session, order_type=P2POrderType.BUY)
        all_sell_orders = await p2p_service.get_orders(db=session, order_type=P2POrderType.SELL)

        buy_orders = [order for order in all_buy_orders if order.creator_id == user.id]
        sell_orders = [order for order in all_sell_orders if order.creator_id == user.id]

        text = "Список ваших объявлений:\n\n"
        builder = InlineKeyboardBuilder()

        if not buy_orders and not sell_orders:
            text = "У вас пока нет активных объявлений."
        else:
            if buy_orders:
                text += "<b>Покупка:</b>\n"
                for order in buy_orders:
                    builder.button(
                        text=f"Купить {order.crypto_currency} за {order.fiat_currency} @ {order.price_per_unit}",
                        callback_data=f"show_ad_{order.id}"
                    )
            if sell_orders:
                text += "\n<b>Продажа:</b>\n"
                for order in sell_orders:
                    builder.button(
                        text=f"Продать {order.crypto_currency} за {order.fiat_currency} @ {order.price_per_unit}",
                        callback_data=f"show_ad_{order.id}"
                    )

        builder.adjust(1)
        builder.row(InlineKeyboardButton(text="< Назад", callback_data="open-profile"))

        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@router.callback_query(F.data == "my_reviews")
async def show_my_reviews(callback: CallbackQuery):
    await callback.answer()

    text = "Мои отзывы\n\nФункция в разработке..."

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="< Назад", callback_data="open-profile")

    await callback.message.edit_text(text, reply_markup=keyboard.as_markup())


@router.callback_query(F.data == "order_type_buy")
async def callback_order_type_buy(callback: CallbackQuery, state: FSMContext, language_code: str = "ru"):
    await state.update_data(type="buy")
    await state.set_state(CreateOfferStates.crypto)
    await callback.message.edit_text(
        "Выберите криптовалюту, которую хотите купить.",
        reply_markup=get_currency_keyboard("crypto")
    )
    await callback.answer()


@router.callback_query(F.data == "order_type_sell")
async def callback_order_type_sell(callback: CallbackQuery, state: FSMContext, language_code: str = "ru"):
    await state.update_data(type="sell")
    await state.set_state(CreateOfferStates.crypto)
    await callback.message.edit_text(
        "Выберите криптовалюту, которую хотите продать.",
        reply_markup=get_currency_keyboard("crypto")
    )
    await callback.answer()


@router.callback_query(F.data.in_(["order_type_buy", "order_type_sell"]))
async def fsm_offer_type(callback: CallbackQuery, state: FSMContext):
    offer_type = "buy" if callback.data == "order_type_buy" else "sell"
    await state.update_data(type=offer_type)
    await state.set_state(CreateOfferStates.crypto)
    await callback.message.edit_text(
        "Выберите криптовалюту, которую хотите {}.".format("купить" if offer_type == "buy" else "продать"),
        reply_markup=get_currency_keyboard("crypto")
    )
    await callback.answer()

@router.callback_query(F.data.startswith("crypto_"), CreateOfferStates.crypto)
async def fsm_offer_crypto(callback: CallbackQuery, state: FSMContext):
    crypto = callback.data.split("_")[1]
    await state.update_data(crypto=crypto)
    await state.set_state(CreateOfferStates.fiat)
    await callback.message.edit_text(
        "За какую валюту вы хотите {} {}?".format(
            "купить" if (await state.get_data())["type"] == "buy" else "продать", crypto
        ),
        reply_markup=get_currency_keyboard("fiat")
    )
    await callback.answer()

@router.callback_query(F.data.startswith("fiat_"), CreateOfferStates.fiat)
async def fsm_offer_fiat(callback: CallbackQuery, state: FSMContext):
    fiat = callback.data.split("_")[1]
    await state.update_data(fiat=fiat)
    await state.set_state(CreateOfferStates.rate_type)
    data = await state.get_data()
    crypto = data.get("crypto")
    market_rate = await exchange_rate_service.get_exchange_rate(crypto, fiat) or 0
    market_rate_fmt = f"{market_rate:.2f}"
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="Фиксированная", callback_data="rate_fixed"),
        InlineKeyboardButton(text="Плавающая", callback_data="rate_float")
    )
    b.row(InlineKeyboardButton(text="‹ Изменить валюту", callback_data="back_to_fiat"))
    await callback.message.edit_text(
        (
            f"Пришлите процент от биржевого курса (например, +4% или -2.5%) для покупки {crypto}.\n\n"
            f"Биржевой курс: {market_rate_fmt} {fiat}\n"
            f"Источник курса: CoinGecko\n\n"
            f"Цена за {crypto} ≈ {market_rate_fmt} {fiat}\n"
            f"Процент от биржевого курса: 0%"
        ),
        reply_markup=b.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.in_(["rate_fixed", "rate_float"]), CreateOfferStates.rate_type)
async def fsm_offer_rate_type(callback: CallbackQuery, state: FSMContext):
    rate_type = "fixed" if callback.data == "rate_fixed" else "float"
    await state.update_data(rate_type=rate_type)
    await state.set_state(CreateOfferStates.rate_value)
    data = await state.get_data()
    crypto = data.get("crypto")
    fiat = data.get("fiat")
    market_rate = await exchange_rate_service.get_exchange_rate(crypto, fiat)
    if not market_rate:
        market_rate = 0
    market_rate_fmt = f"{market_rate:.2f}"
    if rate_type == "fixed":
        text = (
            f"Пришлите цену за 1 {crypto} в {fiat} (например, {market_rate_fmt}).\n\n"
            f"Биржевой курс: {market_rate_fmt} {fiat}"
        )
    else:
        text = (
            f"Пришлите процент от биржевого курса (например, +4% или -2.5%) для покупки {crypto}.\n\n"
            f"Биржевой курс: {market_rate_fmt} {fiat}\nИсточник курса: CoinGecko\nЦена за {crypto} ≈ {market_rate_fmt} {fiat}\nПроцент от биржевого курса: 0%"
        )
    builder = InlineKeyboardBuilder()
    if rate_type == "fixed":
        builder.row(
            InlineKeyboardButton(text="• Фиксированная •", callback_data="rate_fixed"),
            InlineKeyboardButton(text="Плавающая", callback_data="rate_float")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="Фиксированная", callback_data="rate_fixed"),
            InlineKeyboardButton(text="• Плавающая •", callback_data="rate_float")
        )
    builder.row(InlineKeyboardButton(text="‹ Изменить валюту", callback_data="back_to_fiat"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.message(CreateOfferStates.rate_value)
async def fsm_offer_rate_value(message: Message, state: FSMContext):
    value = message.text.strip().replace(",", ".")
    data = await state.get_data()
    rate_type = data.get("rate_type")
    try:
        if rate_type == "fixed":
            price = float(value)
            await state.update_data(rate_value=price)
        else:
            percent = float(value.replace("%", ""))
            await state.update_data(rate_value=percent)
    except Exception:
        await message.answer("Некорректное значение. Пожалуйста, введите число.")
        return
    await state.set_state(CreateOfferStates.amount)
    await message.answer(
        f"Пришлите общий объём {data.get('crypto')}, который вы хотите {('купить' if data.get('type') == 'buy' else 'продать')}.",
        reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="‹ Изменить цену", callback_data="back_to_rate_type")).as_markup()
    )

@router.message(CreateOfferStates.amount)
async def fsm_offer_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace(",", "."))
        await state.update_data(amount=amount)
    except Exception:
        await message.answer("Некорректное значение. Пожалуйста, введите число.")
        return
    await state.set_state(CreateOfferStates.limits)
    await message.answer(
        "Пришлите лимиты сделки в {} (например, 100-10700). Лимиты определяют минимальную и максимальную сумму одной сделки.".format((await state.get_data()).get('fiat')),
        reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="‹ Изменить цену", callback_data="back_to_rate_type")).as_markup()
    )

@router.message(CreateOfferStates.limits)
async def fsm_offer_limits(message: Message, state: FSMContext):
    limits = message.text.strip().replace(" ", "")
    if "-" not in limits:
        await message.answer("Некорректный формат. Введите лимиты через дефис, например: 100-10700")
        return
    min_limit, max_limit = limits.split("-")
    try:
        min_limit = float(min_limit)
        max_limit = float(max_limit)
        if min_limit > max_limit:
            raise ValueError
        await state.update_data(limits=(min_limit, max_limit))
    except Exception:
        await message.answer("Некорректные лимиты. Проверьте значения.")
        return
    await state.set_state(CreateOfferStates.payments)
    await show_payment_methods(message, state)

@router.callback_query(F.data.startswith("paymethod_"), CreateOfferStates.payments)
async def fsm_offer_payments(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    payments = data.get("payments", [])
    method = callback.data.split("_")[1]
    if method not in payments:
        payments.append(method)
    await state.update_data(payments=payments)
    if len(payments) >= 5:
        await state.set_state(CreateOfferStates.pay_time)
        await callback.message.edit_text(
            "Выберите период времени, в течение которого должна быть подтверждена отправка оплаты.",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="15 мин", callback_data="paytime_15"),
                InlineKeyboardButton(text="30 мин", callback_data="paytime_30"),
                InlineKeyboardButton(text="45 мин", callback_data="paytime_45"),
                InlineKeyboardButton(text="1 ч", callback_data="paytime_60"),
                InlineKeyboardButton(text="2 ч", callback_data="paytime_120"),
                InlineKeyboardButton(text="3 ч", callback_data="paytime_180")
            ).as_markup()
        )
    else:
        await callback.answer("Добавлено. Можно выбрать ещё.")

@router.callback_query(F.data.startswith("paytime_"), CreateOfferStates.pay_time)
async def fsm_offer_pay_time(callback: CallbackQuery, state: FSMContext):
    pay_time = int(callback.data.split("_")[1])
    await state.update_data(pay_time=pay_time)
    await state.set_state(CreateOfferStates.confirm)
    data = await state.get_data()
    text = (
        f"Проверка и подтверждение\n\n"
        f"Покупка {data.get('crypto')} за {data.get('fiat')}\n"
        f"Цена: {data.get('rate_value')} {data.get('fiat')}\n"
        f"Общий объём: {data.get('amount')} {data.get('crypto')}\n"
        f"Лимиты: {data.get('limits')[0]} {data.get('fiat')} ~ {data.get('limits')[1]} {data.get('fiat')}\n"
        f"Способы оплаты: {', '.join(data.get('payments_disp', []))}\n"
        f"Срок оплаты: {pay_time} мин"
    )
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="Создать объявление", callback_data="offer_publish"))
    b.row(InlineKeyboardButton(text="‹ Изменить срок оплаты", callback_data="back_to_pay_time"))
    await callback.message.edit_text(text, reply_markup=b.as_markup())
    await callback.answer()

@router.callback_query(F.data == "offer_publish", CreateOfferStates.confirm)
async def fsm_offer_publish(callback: CallbackQuery, state: FSMContext):
    logger.info("offer_publish callback triggered", user_id=callback.from_user.id)
    current_state = await state.get_state()
    logger.info("Current FSM state", state=current_state)

    try:
        data = await state.get_data()
        user_service = UserService()

        async with AsyncSessionLocal() as db:
            user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
            if not user:
                await callback.message.edit_text("Ошибка: пользователь не найден.")
                await state.clear()
                return

            await db.refresh(user)

            from app.models.p2p import P2POrderType
            order_type = P2POrderType.BUY if data.get("type") == "buy" else P2POrderType.SELL

            market_rate = await exchange_rate_service.get_exchange_rate(data.get("crypto"), data.get("fiat")) or 0
            price_per_unit = float(data.get("rate_value", 0))
            if data.get("rate_type") == "float":
                price_per_unit = round(float(market_rate) * (1 + (price_per_unit / 100.0)), 2)
            else:
                price_per_unit = round(price_per_unit, 2)

            payment_methods = data.get("payments_enum", [])
            payments_disp = data.get("payments_disp", [])

            if not payment_methods:
                payment_methods = [map_payment_to_enum("Bank Transfer")]

            await p2p_service.create_order(
                db=db,
                creator=user,
                order_type=order_type,
                crypto_currency=data.get("crypto"),
                crypto_amount=str(data.get("amount")),
                fiat_currency=data.get("fiat"),
                price_per_unit=str(price_per_unit),
                payment_methods=payment_methods,
                min_amount=str(data.get("limits")[0]),
                max_amount=str(data.get("limits")[1]),
                payment_timeout_minutes=int(data.get("pay_time", 15)),
                )

        await state.clear()
        await callback.message.edit_text(
            "🎉 Объявление успешно создано! Теперь вы можете активировать объявление, чтобы начать принимать сделки.\n\n"
            "⚠️ Активируя объявление, вы соглашаетесь с правилами использования Маркета.",
            reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="Активировать", callback_data="offer_activate")).as_markup()
        )
    except Exception as e:
        logger.error("Error creating P2P offer", error=str(e), user_id=callback.from_user.id)
        await callback.message.edit_text(
            "❌ Произошла ошибка при создании объявления. Попробуйте еще раз.",
            reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="‹ Назад", callback_data="p2p_menu")).as_markup()
        )
    finally:
        await callback.answer()


@router.callback_query(F.data == "offer_activate")
async def handle_offer_activate(callback: CallbackQuery, state: FSMContext):
    try:
        user_service = UserService()

        async with AsyncSessionLocal() as db:
            user = await user_service.get_user_by_telegram_id(db, callback.from_user.id)
            if not user:
                await callback.message.edit_text("Ошибка: пользователь не найден.")
                await callback.answer()
                return

            await db.refresh(user)


            logger.info(
                "P2P offer activation requested",
                user_id=callback.from_user.id,
                username=user.username
            )

            await callback.message.edit_text(
                "✅ Объявление успешно активировано!\n\n"
                "Ваше объявление теперь доступно другим пользователям в P2P Маркете. "
                "Вы будете получать уведомления о новых сделках.\n\n"
                "Чтобы управлять объявлениями, используйте раздел 'Мои объявления'.",
                reply_markup=InlineKeyboardBuilder().row(
                    InlineKeyboardButton(text="📋 Мои объявления", callback_data="market-manage-orders"),
                    InlineKeyboardButton(text="‹ В меню", callback_data="p2p_menu")
                ).as_markup()
            )

    except Exception as e:
        logger.error("Error activating P2P offer", error=str(e), user_id=callback.from_user.id)
        await callback.message.edit_text(
            "❌ Произошла ошибка при активации объявления. Попробуйте еще раз.",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="‹ Назад", callback_data="p2p_menu")
            ).as_markup()
        )
    finally:
        await callback.answer()


@router.callback_query(F.data.startswith("crypto_"))
async def callback_crypto_selection(callback: CallbackQuery, state: FSMContext, language_code: str = "ru"):
    current = await state.get_state()
    if current == CreateOfferStates.crypto.state:
        crypto = callback.data.split("_")[1]
        await state.update_data(crypto=crypto)
        await state.set_state(CreateOfferStates.fiat)
        await callback.message.edit_text(
            f"За какую валюту вы хотите {('купить' if (await state.get_data()).get('type') == 'buy' else 'продать')} {crypto}?",
            reply_markup=get_currency_keyboard("fiat")
        )
    else:
        await callback.answer()


@router.callback_query(F.data.startswith("fiat_"))
async def callback_fiat_selection(callback: CallbackQuery, state: FSMContext, language_code: str = "ru"):
    current = await state.get_state()
    if current == CreateOfferStates.fiat.state:
        fiat = callback.data.split("_")[1]
        await state.update_data(fiat=fiat)
        await state.set_state(CreateOfferStates.rate_type)
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="Фиксированная", callback_data="rate_fixed"),
            InlineKeyboardButton(text="Плавающая", callback_data="rate_float")
        )
        builder.row(InlineKeyboardButton(text="‹ Изменить валюту", callback_data="back_to_crypto"))
        await callback.message.edit_text(
            "Выберите тип цены: фиксированная или плавающая.",
            reply_markup=builder.as_markup()
        )
    else:
        await callback.answer()


@router.callback_query(F.data.startswith("buy_crypto_"))
async def callback_buy_crypto_selection(callback: CallbackQuery, language_code: str = "ru"):
    crypto = callback.data.split("_")[2]
    await callback.message.edit_text(
        f"💰 Покупка {crypto}\n\n"
        "Выберите способ оплаты:",
        reply_markup=get_payment_methods_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("payment_"))
async def callback_payment_method(callback: CallbackQuery, language_code: str = "ru"):
    method = callback.data.split("_")[1]
    await callback.message.edit_text(
        f"Вы выбрали способ оплаты: {method}\n\n"
        "Функция в разработке...",
        reply_markup=get_back_keyboard("p2p_menu")
    )
    await callback.answer()


@router.callback_query(F.data == "p2p_main")
async def callback_p2p_main(callback: CallbackQuery, language_code: str = "ru"):
    await show_p2p_menu(callback.message, language_code)
    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, language_code: str = "ru"):
    from app.bot.keyboards.inline import get_main_menu_keyboard
    from app.bot.utils.texts import get_text

    main_menu_text = get_text("main_menu", language_code)
    keyboard = get_main_menu_keyboard(language_code)

    await callback.message.edit_text(main_menu_text, reply_markup=keyboard)
    await callback.answer()


async def show_p2p_menu(message: Message, language_code: str = "ru"):
    text = (
        "💠 Здесь вы можете <a href=\"https://help.send.tg/ru/articles/9819562-%D0%BA%D0%B0%D0%BA-%D0%BA%D1%83%D0%BF%D0%B8%D1%82%D1%8C-%D0%BC%D0%BE%D0%BD%D0%B5%D1%82%D1%8B\">купить</a> "
        "или <a href=\"https://help.send.tg/ru/articles/9819582-%D0%BA%D0%B0%D0%BA-%D0%BF%D1%80%D0%BE%D0%B4%D0%B0%D1%82%D1%8C-%D0%BC%D0%BE%D0%BD%D0%B5%D1%82%D1%8B\">продать</a> "
        "криптовалюту переводом на карту или электронный кошелёк. "
        "Смотреть <a href=\"https://youtu.be/PuD59ai_VNg\">видеоинструкцию</a> ›"
    )

    keyboard = get_p2p_menu_keyboard()

    if hasattr(message, 'edit_text'):
        await message.edit_text(text, reply_markup=keyboard, disable_web_page_preview=True)
    else:
        await message.answer(text, reply_markup=keyboard, disable_web_page_preview=True)

async def show_payment_methods(message_or_callback, state: FSMContext):
    data = await state.get_data()
    fiat = data.get("fiat")
    methods = PAYMENT_CATALOG.get(fiat, [])
    selected_payments = data.get("payments_disp", [])

    b = InlineKeyboardBuilder()
    for idx, disp in enumerate(methods[:12]):
        prefix = "✅ " if disp in selected_payments else ""
        b.row(InlineKeyboardButton(text=f"{prefix}{disp}", callback_data=f"pmidx_{idx}"))

    if selected_payments:
        b.row(InlineKeyboardButton(text="➡️ Продолжить", callback_data="continue_to_pay_time"))
    b.row(InlineKeyboardButton(text="‹ Изменить лимиты", callback_data="back_limits"))

    selected_count = len(selected_payments)
    text = f"Выберите до 5 способов оплаты ({selected_count}/5):\n"
    if selected_payments:
        text += "\nВыбранные способы:\n" + "\n".join(f"• {method}" for method in selected_payments)

    markup = b.as_markup()

    if hasattr(message_or_callback, 'message'):
        await message_or_callback.message.edit_text(text, reply_markup=markup)
    else:
        await message_or_callback.answer(text, reply_markup=markup)

@router.callback_query(F.data == "pt_15")
async def handle_pt_15_no_state(callback: CallbackQuery, state: FSMContext):
    logger.info("pt_15 callback without FSM state, redirecting to P2P menu", user_id=callback.from_user.id)

    await callback.answer(
        "⚠️ Сессия истекла. Начните создание объявления заново.",
        show_alert=True
    )

    await state.clear()
    from app.bot.keyboards.p2p import get_p2p_menu_keyboard
    await callback.message.edit_text(
        "💠 P2P Маркетплейс\n\nВыберите действие:",
        reply_markup=get_p2p_menu_keyboard()
    )

@router.callback_query(F.data == "offer_publish")
async def handle_offer_publish_no_state(callback: CallbackQuery, state: FSMContext):
    logger.info("offer_publish callback without FSM state, redirecting to P2P menu", user_id=callback.from_user.id)

    await callback.answer(
        "⚠️ Сессия истекла. Начните создание объявления заново.",
        show_alert=True
    )

    await state.clear()
    from app.bot.keyboards.p2p import get_p2p_menu_keyboard
    await callback.message.edit_text(
        "💠 P2P Маркетплейс\n\nВыберите действие:",
        reply_markup=get_p2p_menu_keyboard()
    )

@router.callback_query()
async def handle_unknown_callbacks(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()

    logger.warning(
        "Unknown P2P callback",
        callback_data=callback.data,
        current_state=current_state,
        user_id=callback.from_user.id
    )

    specific_callbacks = ["offer_activate", "offer_publish"]
    p2p_callbacks = ["crypto_", "fiat_", "rate_", "pmidx_", "pt_", "offer_", "back_"]

    if callback.data not in specific_callbacks and any(callback.data.startswith(prefix) for prefix in p2p_callbacks):
        await callback.answer(
            "⚠️ Действие недоступно. Возвращаю в P2P меню.",
            show_alert=True
        )
        await state.clear()
        from app.bot.keyboards.p2p import get_p2p_menu_keyboard
        await callback.message.edit_text(
            "💠 P2P Маркетплейс\n\nВыберите действие:",
            reply_markup=get_p2p_menu_keyboard()
        )
    else:
        return

@router.callback_query(F.data == "back_to_payments")
async def back_to_payments(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CreateOfferStates.payments)
    await show_payment_methods(callback, state)
    await callback.answer()

@router.callback_query(F.data == "back_to_pay_time_from_confirm", CreateOfferStates.confirm)
async def back_to_pay_time_from_confirm(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CreateOfferStates.pay_time)
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="• 15 мин •", callback_data="pt_15"),
        InlineKeyboardButton(text="30 мин", callback_data="pt_30"),
        InlineKeyboardButton(text="45 мин", callback_data="pt_45")
    )
    b.row(
        InlineKeyboardButton(text="1 ч", callback_data="pt_60"),
        InlineKeyboardButton(text="2 ч", callback_data="pt_120"),
        InlineKeyboardButton(text="3 ч", callback_data="pt_180")
    )
    b.row(InlineKeyboardButton(text="Далее ›", callback_data="pt_next"))
    b.row(InlineKeyboardButton(text="‹ Изменить способы оплаты", callback_data="back_to_payments"))
    await callback.message.edit_text(
        "Выберите период времени, в течение которого должна быть подтверждена отправка оплаты.",
        reply_markup=b.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_pay_time")
async def back_to_pay_time(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CreateOfferStates.pay_time)
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="• 15 мин •", callback_data="pt_15"),
        InlineKeyboardButton(text="30 мин", callback_data="pt_30"),
        InlineKeyboardButton(text="45 мин", callback_data="pt_45")
    )
    b.row(
        InlineKeyboardButton(text="1 ч", callback_data="pt_60"),
        InlineKeyboardButton(text="2 ч", callback_data="pt_120"),
        InlineKeyboardButton(text="3 ч", callback_data="pt_180")
    )
    b.row(InlineKeyboardButton(text="Далее ›", callback_data="pt_next"))
    b.row(InlineKeyboardButton(text="‹ Изменить способы оплаты", callback_data="back_to_payments"))
    await callback.message.edit_text(
        "Выберите период времени, в течение которого должна быть подтверждена отправка оплаты.",
        reply_markup=b.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_crypto")
async def back_to_crypto(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CreateOfferStates.crypto)
    b = InlineKeyboardBuilder()
    crypto_order = ["USDT","TON","ETH","USDC","SOL","DOGE","BTC","TRON","BNB","LTC"]
    row = []
    for sym in crypto_order:
        cb = f"crypto_{'TRX' if sym=='TRON' else sym}"
        row.append(InlineKeyboardButton(text=sym, callback_data=cb))
        if len(row) == 3:
            b.row(*row)
            row = []
    if row:
        b.row(*row)
    b.row(InlineKeyboardButton(text="‹ Изменить тип", callback_data="market-create-offer"))
    await callback.message.edit_text("Выберите криптовалюту, которую хотите купить/продать.", reply_markup=b.as_markup())
    await callback.answer()

@router.callback_query(F.data == "back_to_fiat")
async def back_to_fiat(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CreateOfferStates.fiat)
    data = await state.get_data()
    crypto = data.get("crypto")
    fiat_codes = [
        "RUB","USD","EUR","GBP","CNY","KZT","UZS","GEL","TRY","AMD",
        "THB","INR","BRL","IDR","AZN","AED","PLN","ILS","KGS","TJS"
    ]
    b = InlineKeyboardBuilder()
    for i in range(0, len(fiat_codes), 3):
        for code in fiat_codes[i:i+3]:
            b.add(InlineKeyboardButton(text=code, callback_data=f"fiat_{code}"))
        b.adjust(3)
    b.row(InlineKeyboardButton(text="‹ Изменить монету", callback_data="back_to_crypto"))
    await callback.message.edit_text(
        f"За какую валюту вы хотите {('купить' if data.get('type')=='buy' else 'продать')} {crypto}?",
        reply_markup=b.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_rate_type")
async def back_to_rate_type(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CreateOfferStates.rate_type)
    data = await state.get_data()
    crypto = data.get("crypto"); fiat = data.get("fiat")
    market = await exchange_rate_service.get_exchange_rate(crypto, fiat) or 0
    market_rate_fmt = f"{market:.2f}"
    selected = data.get("rate_type", "float")
    builder = InlineKeyboardBuilder()
    if selected == "fixed":
        builder.row(
            InlineKeyboardButton(text="• Фиксированная •", callback_data="rate_fixed"),
            InlineKeyboardButton(text="Плавающая", callback_data="rate_float")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="Фиксированная", callback_data="rate_fixed"),
            InlineKeyboardButton(text="• Плавающая •", callback_data="rate_float")
        )
    builder.row(InlineKeyboardButton(text="‹ Изменить валюту", callback_data="back_to_fiat"))
    text = (
        f"Пришлите процент от биржевого курса (например, +4% или -2.5%) для покупки {crypto}.\n\n"
        f"Биржевой курс: {market_rate_fmt} {fiat}\nИсточник курса: CoinGecko\nЦена за {crypto} ≈ {market_rate_fmt} {fiat}\nПроцент от биржевого курса: 0%"
    )
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "back_limits")
async def back_limits(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CreateOfferStates.limits)
    data = await state.get_data()
    fiat = data.get("fiat")
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="100-10 700", callback_data="limits_example_100_10700"))
    b.row(InlineKeyboardButton(text="‹ Изменить цену", callback_data="back_to_rate_type"))
    await callback.message.edit_text(
        (
            f"Пришлите лимиты сделки в {fiat} (например, 100-10 700). Лимиты определяют минимальную и максимальную сумму одной сделки.\n\n"
            f"Минимум: 100 {fiat}\nМаксимум: 10 700 {fiat}"
        ),
        reply_markup=b.as_markup()
    )
    await callback.answer()
