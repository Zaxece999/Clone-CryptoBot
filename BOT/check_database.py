import asyncio
import sys
sys.path.append('.')

from sqlalchemy import text
from app.database import AsyncSessionLocal

async def check_db():
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(text('SELECT id, check_id, amount, currency, is_gift FROM checks ORDER BY created_at DESC LIMIT 10'))
            checks = result.fetchall()
            print('Recent checks with is_gift column:')
            for check in checks:
                print(f'  ID: {check[0]}, Check ID: {check[1]}, Amount: {check[2]} {check[3]}, Is Gift: {check[4]}')
        except Exception as e:
            print(f'Column is_gift might not exist: {e}')
            result = await db.execute(text('SELECT id, check_id, amount, currency FROM checks ORDER BY created_at DESC LIMIT 10'))
            checks = result.fetchall()
            print('Recent checks (without is_gift):')
            for check in checks:
                print(f'  ID: {check[0]}, Check ID: {check[1]}, Amount: {check[2]} {check[3]}')

        try:
            result = await db.execute(text("PRAGMA table_info(checks)"))
            columns = result.fetchall()
            print('\nTable structure:')
            for col in columns:
                print(f'  {col[1]} - {col[2]} (nullable: {col[3] == 0}, default: {col[4]})')
        except Exception as e:
            print(f'Error checking table structure: {e}')

if __name__ == "__main__":
    asyncio.run(check_db())
