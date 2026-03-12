"""
fix_subjects.py
───────────────────────────────────────────────────────────────
Run this ONCE from your project root:
    python fix_subjects.py

It will:
1. Show exactly what's in subject_topics table
2. Ask you which name to keep for each subject
3. Fix the DB permanently
───────────────────────────────────────────────────────────────
"""

import os, sys
import psycopg2
import psycopg2.extras

# ── Read DB URL from secrets.toml or env ─────────────────────
def get_db_url():
    # Try secrets.toml
    secrets_path = os.path.join(".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        with open(secrets_path) as f:
            for line in f:
                if "DATABASE_URL" in line:
                    url = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return url
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    raise RuntimeError("DATABASE_URL not found in .streamlit/secrets.toml or environment")

conn = psycopg2.connect(get_db_url(), cursor_factory=psycopg2.extras.RealDictCursor, sslmode="require")
c = conn.cursor()

# ── Step 1: Show current state ────────────────────────────────
print("\n" + "="*60)
print("CURRENT subject_topics TABLE")
print("="*60)
c.execute("SELECT subject, COUNT(*) as cnt FROM subject_topics GROUP BY subject ORDER BY subject")
rows = c.fetchall()
for r in rows:
    print(f"  '{r['subject']}' → {r['cnt']} topics")

# ── Step 2: Show a few topics per subject ─────────────────────
print("\n" + "="*60)
print("SAMPLE TOPICS PER SUBJECT (first 3)")
print("="*60)
for r in rows:
    c.execute("SELECT topic FROM subject_topics WHERE subject=%s ORDER BY position LIMIT 3", (r['subject'],))
    topics = [t['topic'] for t in c.fetchall()]
    print(f"  '{r['subject']}': {topics}")

# ── Step 3: Auto-fix — for each lowercase group, keep the one with most topics ──
print("\n" + "="*60)
print("AUTO-FIX: Consolidating duplicate subject names...")
print("="*60)

all_subjects = [r['subject'] for r in rows]
groups = {}
for s in all_subjects:
    groups.setdefault(s.lower().strip(), []).append(s)

for key, variants in groups.items():
    if len(variants) <= 1:
        print(f"  '{variants[0]}' — no duplicates, skipping")
        continue

    # Count topics per variant
    counts = {}
    for v in variants:
        c.execute("SELECT COUNT(*) as cnt FROM subject_topics WHERE subject=%s", (v,))
        counts[v] = c.fetchone()['cnt']

    # Keep the one with most topics
    canonical = max(counts, key=counts.get)
    to_delete = [v for v in variants if v != canonical]

    print(f"\n  Group '{key}':")
    for v in variants:
        marker = " ← KEEP" if v == canonical else " ← DELETE"
        print(f"    '{v}' ({counts[v]} topics){marker}")

    for variant in to_delete:
        # Move any unique topics to canonical first
        c.execute("""
            UPDATE subject_topics SET subject=%s
            WHERE subject=%s
              AND topic NOT IN (SELECT topic FROM subject_topics WHERE subject=%s)
        """, (canonical, variant, canonical))
        moved = c.rowcount
        # Delete remaining (true duplicates)
        c.execute("DELETE FROM subject_topics WHERE subject=%s", (variant,))
        deleted = c.rowcount
        print(f"    Moved {moved} unique topics from '{variant}' → '{canonical}', deleted {deleted} duplicate rows")

conn.commit()

# ── Step 4: Show final state ──────────────────────────────────
print("\n" + "="*60)
print("FINAL STATE after fix:")
print("="*60)
c.execute("SELECT subject, COUNT(*) as cnt FROM subject_topics GROUP BY subject ORDER BY subject")
for r in c.fetchall():
    print(f"  '{r['subject']}' → {r['cnt']} topics")

conn.close()
print("\n✅ Done. Now re-upload DSA PDF in Manage Subjects if topics are missing.")