import os
import sqlite3
import asyncio
import aiosqlite
from typing import Dict, Optional, List
from decimal import Decimal

class SimpleBotDatabase:
    def __init__(self, db_path: str = None):
        if db_path is None:
            possible_paths = [
                "BOT/cryptobot.db",
                "BOT/app/cryptobot.db",
                "cryptobot.db"
            ]

            for path in possible_paths:
                if os.path.exists(path):
                    self.db_path = path
                    break
            else:
                self.db_path = "BOT/cryptobot.db"
        else:
            self.db_path = db_path

    def get_database_info(self) -> Dict:
        info = {
            "db_path": self.db_path,
            "exists": os.path.exists(self.db_path),
            "size": 0
        }

        if info["exists"]:
            try:
                info["size"] = os.path.getsize(self.db_path)
            except:
                pass

        return info

    async def get_user_balances(self, user_id: int) -> Dict[str, float]:
        if not os.path.exists(self.db_path):
            print(f"Database file not found: {self.db_path}")
            return {}

    async def get_internal_user_id_by_telegram(self, telegram_id: int) -> Optional[int]:
        if not os.path.exists(self.db_path):
            return None
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT id FROM users WHERE telegram_id = ?",
                    (int(telegram_id),)
                )
                row = await cursor.fetchone()
                return int(row[0]) if row else None
        except Exception as e:
            print(f"Error mapping telegram_id to internal user id: {e}")
            return None

        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT currency, balance, frozen_balance
                    FROM wallets
                    WHERE user_id = ? AND status = 'ACTIVE'
                """, (user_id,))

                rows = await cursor.fetchall()

                balances = {}
                for currency, balance, frozen_balance in rows:
                    try:
                        total_balance = float(balance)
                        frozen = float(frozen_balance) if frozen_balance else 0.0
                        available_balance = total_balance - frozen

                        if currency in balances:
                            balances[currency] += available_balance
                        else:
                            balances[currency] = available_balance

                    except (ValueError, TypeError) as e:
                        print(f"Error processing balance for {currency}: {e}")
                        if currency not in balances:
                            balances[currency] = 0.0

                print(f"Retrieved balances for user {user_id}: {balances}")
                return balances

        except Exception as e:
            print(f"Error getting user balances: {e}")
            return {}

    async def get_all_users_with_balances(self) -> List[int]:
        if not os.path.exists(self.db_path):
            return []

        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT DISTINCT user_id
                    FROM wallets
                    WHERE status = 'ACTIVE'
                """)

                rows = await cursor.fetchall()
                user_ids = [row[0] for row in rows]

                print(f"Found {len(user_ids)} users with wallets")
                return user_ids

        except Exception as e:
            print(f"Error getting users: {e}")
            return []

    async def check_connection(self) -> bool:
        if not os.path.exists(self.db_path):
            return False

        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT 1")
                await cursor.fetchone()
                return True
        except Exception as e:
            print(f"Database connection check failed: {e}")
            return False

    def get_table_info(self) -> Dict:
        if not os.path.exists(self.db_path):
            return {"error": "Database not found"}

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]

            wallet_info = {}
            if 'wallets' in tables:
                cursor.execute("PRAGMA table_info(wallets);")
                columns = cursor.fetchall()
                wallet_info = {
                    "columns": [{"name": col[1], "type": col[2]} for col in columns],
                    "count": 0
                }

                cursor.execute("SELECT COUNT(*) FROM wallets;")
                wallet_info["count"] = cursor.fetchone()[0]

            conn.close()

            return {
                "tables": tables,
                "wallets_info": wallet_info
            }

        except Exception as e:
            return {"error": str(e)}

simple_bot_db = SimpleBotDatabase()

async def get_user_balances_from_bot_db(user_id: int) -> Dict[str, float]:
    return await simple_bot_db.get_user_balances(user_id)

async def check_bot_db_connection() -> bool:
    return await simple_bot_db.check_connection()

async def get_all_users_with_balances() -> List[int]:
    return await simple_bot_db.get_all_users_with_balances()

async def map_telegram_to_internal_user_id(telegram_id: int) -> Optional[int]:
    return await simple_bot_db.get_internal_user_id_by_telegram(telegram_id)

def get_database_info() -> Dict:
    return simple_bot_db.get_database_info()
