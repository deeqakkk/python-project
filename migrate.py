import asyncio
import asyncpg
from dotenv import load_dotenv
import os

load_dotenv()

async def create_tables():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    
    # Read SQL file
    with open('database/init.sql', 'r') as file:
        sql = file.read()
    
    # Execute SQL commands
    await conn.execute(sql)
    
    # Close connection
    await conn.close()

if __name__ == "__main__":
    asyncio.run(create_tables())