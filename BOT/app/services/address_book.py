import structlog
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.models.user import User
from app.models.address_book import AddressBookEntry

logger = structlog.get_logger(__name__)


class AddressBookService:
    async def create_entry(
        self,
        db: AsyncSession,
        user: User,
        name: str,
        address: str,
        network: str,
        currency: str,
        description: Optional[str] = None
    ) -> AddressBookEntry:

        existing_entry = await self.get_entry_by_address(db, user.id, address, network)
        if existing_entry:
            raise ValueError(f"Address {address} already exists in address book")

        try:
            entry = AddressBookEntry(
                user_id=user.id,
                name=name,
                address=address,
                network=network.upper(),
                currency=currency.upper(),
                description=description
            )

            db.add(entry)
            await db.commit()

            logger.info(
                "Address book entry created",
                user_id=user.id,
                entry_id=entry.id,
                name=name,
                network=network,
                address=address[:10] + "..."
            )

            return entry

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to create address book entry",
                user_id=user.id,
                name=name,
                network=network,
                error=str(e)
            )
            raise

    async def get_user_entries(
        self,
        db: AsyncSession,
        user_id: int,
        network: Optional[str] = None,
        currency: Optional[str] = None
    ) -> List[AddressBookEntry]:

        query = select(AddressBookEntry).where(AddressBookEntry.user_id == user_id)

        if network:
            query = query.where(AddressBookEntry.network == network.upper())

        if currency:
            query = query.where(AddressBookEntry.currency == currency.upper())

        query = query.order_by(desc(AddressBookEntry.last_used_at), desc(AddressBookEntry.created_at))

        result = await db.execute(query)
        return result.scalars().all()

    async def get_entries_by_network(
        self,
        db: AsyncSession,
        user_id: int,
        network: str
    ) -> List[AddressBookEntry]:

        return await self.get_user_entries(db, user_id, network=network)

    async def get_entry_by_id(
        self,
        db: AsyncSession,
        user_id: int,
        entry_id: str
    ) -> Optional[AddressBookEntry]:

        result = await db.execute(
            select(AddressBookEntry).where(
                and_(
                    AddressBookEntry.id == entry_id,
                    AddressBookEntry.user_id == user_id
                )
            )
        )

        return result.scalars().first()

    async def get_entry_by_address(
        self,
        db: AsyncSession,
        user_id: int,
        address: str,
        network: str
    ) -> Optional[AddressBookEntry]:

        result = await db.execute(
            select(AddressBookEntry).where(
                and_(
                    AddressBookEntry.user_id == user_id,
                    AddressBookEntry.address == address,
                    AddressBookEntry.network == network.upper()
                )
            )
        )

        return result.scalars().first()

    async def update_entry(
        self,
        db: AsyncSession,
        user_id: int,
        entry_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[AddressBookEntry]:

        entry = await self.get_entry_by_id(db, user_id, entry_id)
        if not entry:
            return None

        try:
            if name is not None:
                entry.name = name
            if description is not None:
                entry.description = description

            await db.commit()

            logger.info(
                "Address book entry updated",
                user_id=user_id,
                entry_id=entry_id,
                name=entry.name
            )

            return entry

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to update address book entry",
                user_id=user_id,
                entry_id=entry_id,
                error=str(e)
            )
            raise

    async def delete_entry(
        self,
        db: AsyncSession,
        user_id: int,
        entry_id: str
    ) -> bool:

        entry = await self.get_entry_by_id(db, user_id, entry_id)
        if not entry:
            return False

        try:
            await db.delete(entry)
            await db.commit()

            logger.info(
                "Address book entry deleted",
                user_id=user_id,
                entry_id=entry_id,
                name=entry.name
            )

            return True

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to delete address book entry",
                user_id=user_id,
                entry_id=entry_id,
                error=str(e)
            )
            raise

    async def mark_as_used(
        self,
        db: AsyncSession,
        user_id: int,
        entry_id: str
    ) -> Optional[AddressBookEntry]:

        entry = await self.get_entry_by_id(db, user_id, entry_id)
        if not entry:
            return None

        try:
            entry.update_last_used()
            await db.commit()

            logger.info(
                "Address book entry marked as used",
                user_id=user_id,
                entry_id=entry_id,
                name=entry.name
            )

            return entry

        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to mark address book entry as used",
                user_id=user_id,
                entry_id=entry_id,
                error=str(e)
            )
            raise

    async def search_entries(
        self,
        db: AsyncSession,
        user_id: int,
        query: str,
        network: Optional[str] = None
    ) -> List[AddressBookEntry]:

        search_query = select(AddressBookEntry).where(
            and_(
                AddressBookEntry.user_id == user_id,
                or_(
                    AddressBookEntry.name.ilike(f"%{query}%"),
                    AddressBookEntry.address.ilike(f"%{query}%"),
                    AddressBookEntry.description.ilike(f"%{query}%")
                )
            )
        )

        if network:
            search_query = search_query.where(AddressBookEntry.network == network.upper())

        search_query = search_query.order_by(desc(AddressBookEntry.last_used_at), desc(AddressBookEntry.created_at))

        result = await db.execute(search_query)
        return result.scalars().all()

    async def get_address_counts_by_network(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Dict[str, int]:

        entries = await self.get_user_entries(db, user_id)

        counts = {}
        for entry in entries:
            network = entry.network
            counts[network] = counts.get(network, 0) + 1

        return counts


address_book_service = AddressBookService()
