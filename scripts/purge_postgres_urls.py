import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import delete, select, text

# Use the connection string from docker-compose.yml
# Note: using asyncpg for async sqlalchemy
DATABASE_URL = "postgresql+asyncpg://luna:lunapass@localhost:5432/luna"

async def purge_local_urls():
    print("🚀 Connecting to PostgreSQL database...")
    engine = create_async_engine(DATABASE_URL)

    try:
        async with engine.begin() as conn:
            # 1. Identify invalid documents
            # We look for URLs that start with / or file:// or contain /var/folders/
            # This query finds them directly in SQL for efficiency
            result = await conn.execute(
                text("SELECT id, url FROM documents WHERE url LIKE '/%' OR url LIKE 'file://%' OR url LIKE '%/var/folders/%' OR url LIKE '%/tmp/%'")
            )
            invalid_docs = result.all()

            if not invalid_docs:
                print("✅ No invalid URLs found in the PostgreSQL database. Index is clean!")
                return

            invalid_ids = [row[0] for row in invalid_docs]
            print(f"⚠️ Found {len(invalid_ids)} invalid entries (local paths/trash).")

            # 2. Purge invalid documents
            # The schema has ON DELETE CASCADE for inverted_index, so we just delete from documents
            await conn.execute(
                text("DELETE FROM documents WHERE id = ANY(:ids)"),
                {"ids": invalid_ids}
            )

            print(f"🚀 Successfully purged {len(invalid_ids)} invalid entries from the index.")

    except Exception as e:
        print(f"❌ Error during purge: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    try:
        asyncio.run(purge_local_urls())
    except KeyboardInterrupt:
        pass
