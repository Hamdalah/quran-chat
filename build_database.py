# Step 1: Run this ONCE to turn the Quran JSON file into a searchable database.
#   python build_database.py
#
# It reads data/quran_en.json and data/hisn_al_muslim.json
# and creates quran.db (an SQLite database file).

import json
import sqlite3
from pathlib import Path

HERE = Path(__file__).parent
JSON_FILE = HERE / "data" / "quran_en.json"
DUAS_FILE = HERE / "data" / "hisn_al_muslim.json"
DB_FILE = HERE / "quran.db"


def main():
    # Start fresh every time so re-running is safe.
    if DB_FILE.exists():
        DB_FILE.unlink()

    surahs = json.loads(JSON_FILE.read_text(encoding="utf-8"))
    db = sqlite3.connect(DB_FILE)

    # A normal table that holds every verse exactly as it appears in the source.
    db.execute("""
        CREATE TABLE verses (
            id           INTEGER PRIMARY KEY,  -- 1 to 6236
            surah        INTEGER NOT NULL,     -- chapter number, 1 to 114
            ayah         INTEGER NOT NULL,     -- verse number inside the chapter
            surah_name   TEXT NOT NULL,        -- e.g. "Al-Baqarah"
            arabic       TEXT NOT NULL,
            translation  TEXT NOT NULL
        )
    """)

    # A special "full-text search" index on the English translation.
    # "porter" means a search for "pray" also finds "prayer" and "praying".
    db.execute("""
        CREATE VIRTUAL TABLE verses_search USING fts5(
            translation,
            content='verses', content_rowid='id',
            tokenize='porter'
        )
    """)

    verse_id = 0
    for surah in surahs:
        for verse in surah["verses"]:
            verse_id += 1
            db.execute(
                "INSERT INTO verses VALUES (?, ?, ?, ?, ?, ?)",
                (verse_id, surah["id"], verse["id"], surah["transliteration"],
                 verse["text"], verse["translation"]),
            )

    # Fill the search index from the verses table.
    db.execute("INSERT INTO verses_search(verses_search) VALUES ('rebuild')")

    # Sanity check: the Quran has exactly 6236 verses.
    count = db.execute("SELECT COUNT(*) FROM verses").fetchone()[0]
    assert count == 6236, f"Expected 6236 verses, got {count}"
    print(f"Saved {count} Quran verses")

    add_duas(db)
    db.commit()
    print(f"Done! Database saved to {DB_FILE.name}")


def add_duas(db):
    """Add the duas from Hisn al-Muslim (Fortress of the Muslim)."""
    duas = json.loads(DUAS_FILE.read_text(encoding="utf-8"))

    db.execute("""
        CREATE TABLE duas (
            id               INTEGER PRIMARY KEY,
            number           TEXT NOT NULL,  -- number in Hisn al-Muslim, e.g. "137"
            topic            TEXT NOT NULL,  -- e.g. "When waking up"
            arabic           TEXT NOT NULL,
            transliteration  TEXT NOT NULL,
            translation      TEXT NOT NULL,
            source           TEXT NOT NULL   -- reference & notes, e.g. "Al-Bukhari 7/158."
        )
    """)
    # Search both the translation and the topic, so "debt" finds the duas
    # in the "Settling a debt" chapter.
    db.execute("""
        CREATE VIRTUAL TABLE duas_search USING fts5(
            translation, topic,
            content='duas', content_rowid='id',
            tokenize='porter'
        )
    """)

    skipped = []
    for dua in duas:
        # Our rule: only show duas whose hadith source is listed.
        if not dua["source"]:
            skipped.append(dua["number"])
            continue
        db.execute(
            "INSERT INTO duas (number, topic, arabic, transliteration, translation, source)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (dua["number"], dua["topic"], dua["arabic"], dua["transliteration"],
             dua["translation"], dua["source"]),
        )
    db.execute("INSERT INTO duas_search(duas_search) VALUES ('rebuild')")

    count = db.execute("SELECT COUNT(*) FROM duas").fetchone()[0]
    print(f"Saved {count} duas (skipped {len(skipped)} with no source listed: {skipped})")


if __name__ == "__main__":
    main()
