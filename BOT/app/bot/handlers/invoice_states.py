from aiogram.fsm.state import StatesGroup, State


class InvoiceStates(StatesGroup):
    selecting_type = State()

    selecting_currencies = State()

    entering_amount = State()

    confirming_creation = State()

    managing_invoice = State()

    managing_permissions = State()

    deleting_invoice = State()
