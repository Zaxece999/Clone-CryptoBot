import secrets
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.models.invoice import Invoice, InvoiceStatus
from app.models.user import User

class InvoiceService:
    @staticmethod
    def generate_invoice_code() -> str:
        return f"IV{secrets.token_hex(4).upper()}"

    @staticmethod
    async def create_invoice(
        session: AsyncSession,
        user_id: int,
        amount: float,
        currencies: List[str],
        invoice_type: str = "single",
        description: Optional[str] = None
    ) -> Invoice:

        invoice_code = InvoiceService.generate_invoice_code()

        invoice = Invoice(
            invoice_code=invoice_code,
            user_id=user_id,
            creator_id=user_id,
            invoice_type=invoice_type,
            amount=amount,
            currency=", ".join(currencies),
            description=description or "",
            status="active"
        )

        session.add(invoice)
        await session.commit()
        await session.refresh(invoice)

        return invoice

    @staticmethod
    async def get_user_invoices(
        session: AsyncSession,
        user_id: int,
        status: Optional[str] = None
    ) -> List[Invoice]:

        query = select(Invoice).where(Invoice.user_id == user_id)

        if status:
            query = query.where(Invoice.status == status)

        result = await session.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_unpaid_invoices(
        session: AsyncSession,
        user_id: int
    ) -> List[Invoice]:

        query = select(Invoice).where(
            and_(
                Invoice.user_id == user_id,
                Invoice.status == "active"
            )
        )

        result = await session.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_invoice_by_code(
        session: AsyncSession,
        invoice_code: str
    ) -> Optional[Invoice]:

        query = select(Invoice).where(Invoice.invoice_code == invoice_code)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_invoice(
        session: AsyncSession,
        invoice_code: str,
        user_id: int
    ) -> bool:

        invoice = await InvoiceService.get_invoice_by_code(session, invoice_code)

        if invoice and invoice.user_id == user_id:
            await session.delete(invoice)
            await session.commit()
            return True

        return False

    @staticmethod
    async def update_invoice_settings(
        session: AsyncSession,
        invoice_code: str,
        user_id: int,
        allow_comments: bool = True,
        allow_anonymous: bool = True,
        hidden_message: bool = False
    ) -> bool:

        invoice = await InvoiceService.get_invoice_by_code(session, invoice_code)

        if invoice and invoice.user_id == user_id:
            await session.commit()
            return True

        return False
