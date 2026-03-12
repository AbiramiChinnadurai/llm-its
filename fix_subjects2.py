"""
fix_subjects2.py
───────────────────────────────────────────────────────────────
Run this from your project root:
    python fix_subjects2.py

This will:
1. Delete ALL rows for 'Dsa' (which has wrong DBMS topics mixed in)
2. Keep 'Dbms' with its correct 9 topics
3. Leave 'Machine Learning' untouched
4. After running, re-upload your DSA PDF in Manage Subjects
───────────────────────────────────────────────────────────────
"""

import os
import psycopg2
import psycopg2.extras

def get_db_url():
    secrets_path = os.path.join(".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        with open(secrets_path) as f:
            for line in f:
                if "DATABASE_URL" in line:
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    raise RuntimeError("DATABASE_URL not found")

conn = psycopg2.connect(get_db_url(), cursor_factory=psycopg2.extras.RealDictCursor, sslmode="require")
c = conn.cursor()

print("\n=== BEFORE ===")
c.execute("SELECT subject, COUNT(*) as cnt FROM subject_topics GROUP BY subject ORDER BY subject")
for r in c.fetchall():
    print(f"  '{r['subject']}' → {r['cnt']} topics")

# Step 1: Wipe 'Dsa' completely (it has wrong DBMS topics)
c.execute("DELETE FROM subject_topics WHERE subject='Dsa'")
print(f"\n✓ Deleted all 'Dsa' rows (had wrong DBMS topics mixed in)")

# Step 2: Rename 'Dbms' → 'DBMS' for clean casing
c.execute("UPDATE subject_topics SET subject='DBMS' WHERE subject='Dbms'")
print(f"✓ Renamed 'Dbms' → 'DBMS'")

conn.commit()

print("\n=== AFTER ===")
c.execute("SELECT subject, COUNT(*) as cnt FROM subject_topics GROUP BY subject ORDER BY subject")
for r in c.fetchall():
    print(f"  '{r['subject']}' → {r['cnt']} topics")

conn.close()
print("\n✅ Done!")
print("→ Now go to Manage Subjects → Upload Syllabus")
print("→ Select 'DSA' and re-upload your DSA PDF to restore its topics")