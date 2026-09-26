import sqlite3
import re
import sys

DB_PATH = 'nexus.db'

def is_valid_web_url(url):
    """
    Checks if a URL is a valid web address (http/https).
    Returns False if it looks like a local system path.
    """
    if not url:
        return False

    # Local paths typically start with /, file://, or contain common temp paths
    if url.startswith('/') or url.startswith('file://'):
        return False

    if '/var/folders/' in url or '/tmp/' in url:
        return False

    # Basic regex for http/https
    web_pattern = re.compile(r'^https?://', re.IGNORECASE)
    return bool(web_pattern.match(url))

def clean_index():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        print("🔍 Scanning index for invalid URLs...")

        # Fetch all documents to analyze
        cursor.execute("SELECT id, url FROM documents")
        all_docs = cursor.fetchall()

        invalid_ids = []
        for doc_id, url in all_docs:
            if not is_valid_web_url(url):
                invalid_ids.append(doc_id)

        if not invalid_ids:
            print("✅ No invalid URLs found. Index is clean!")
            return

        print(f"⚠️ Found {len(invalid_ids)} invalid entries (local paths/trash).")

        # Delete invalid documents
        # Note: inverted_index entries are deleted automatically due to FOREIGN KEY ... ON DELETE CASCADE
        cursor.executemany("DELETE FROM documents WHERE id = ?", [(doc_id,) for doc_id in invalid_ids])

        conn.commit()
        print(f"🚀 Successfully purged {len(invalid_ids)} invalid entries from the index.")

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    clean_index()
