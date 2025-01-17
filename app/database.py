import asyncpg
from typing import Optional
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)
load_dotenv()

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.DATABASE_URL = os.getenv("DATABASE_URL")

    async def connect(self):
        if not self.pool:
            try:
                self.pool = await asyncpg.create_pool(
                    self.DATABASE_URL,
                    min_size=1,
                    max_size=10,
                    command_timeout=60
                )
                logging.info("Connected to database")
            except Exception as e:
                print(f"Error connecting to database: {e}")
                raise

    async def disconnect(self):
        if self.pool:
            await self.pool.close()

    async def fetch_one(self, query: str, *args):
        async with self.pool.acquire() as connection:
            return await connection.fetchrow(query, *args)

    async def fetch_all(self, query: str, *args):
        async with self.pool.acquire() as connection:
            return await connection.fetch(query, *args)

    async def execute(self, query: str, *args):
        async with self.pool.acquire() as connection:
            return await connection.execute(query, *args)

    async def execute_many(self, query: str, args):
        async with self.pool.acquire() as connection:
            return await connection.executemany(query, args)