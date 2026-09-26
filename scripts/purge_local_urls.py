import asyncio
import sys
from sqlalchemy import delete
from luna_shared.database import Database
from luna_shared.repositories import DocumentRepository

async def purge_local_urls():
    db = Database()
    db.connect()

    try:
        async with db.session() as session:
            docs_repo = DocumentRepository(session)

            # 1. Identify invalid documents
            # We look for URLs that don't start with http/https or contain common local path patterns
            all_docs = await docs_repo.get_many([]) # Get all documents

            invalid_ids = []
            for doc_id, doc in all_docs.items():
                url = doc.url
                if not url:
                    invalid_ids.append(doc_id)
                    continue

                # Check for local paths
                if (
                    url.startswith('/') or
                    url.startswith('file://') or
                    '/var/folders/' in url or
                    '/tmp/' in url or
                    not url.startswith('http')
                ):
                    invalid_ids.append(doc_id)

            if not invalid_ids:
                print("✅ No invalid URLs found in the database. Index is clean!")
                return

            print(f"⚠️ Found {len(invalid_ids)} invalid entries (local paths/trash).")

            # 2. Purge invalid documents
            # Because of ON DELETE CASCADE in the schema, inverted_index entries will be removed automatically.
            await session.execute(
                delete(DocumentRepository.__table__).where(DocumentRepository.__table__.c.id.in_(invalid_ids))
            )
            await session.commit()
            print(f"🚀 Successfully purged {len(invalid_ids)} invalid entries from the index.")

    except Exception as e:
        print(f"❌ Error during purge: {e}")
        sys.exit(1)
    finally:
        await db.disconnect()

if __name__ == "__main__":
    sys.exit(asyncio.run(purge_local_urls()))
