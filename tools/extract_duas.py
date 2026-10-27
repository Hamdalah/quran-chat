# How data/hisn_al_muslim.json was made. You do NOT need to run this:
# the JSON file is already included in the project.
#
# The source is the hadith database inside the "hadith" npm package
# (https://www.npmjs.com/package/hadith, version 1.3.0), which contains
# Hisn al-Muslim (Fortress of the Muslim) by Sa'id bin Wahf Al-Qahtani.
#
# Usage: python tools/extract_duas.py path/to/hadith.db

import json
import re
import sqlite3
import sys
from pathlib import Path

HISN_AL_MUSLIM = 300  # collection id in the source database
OUT_FILE = Path(__file__).parent.parent / "data" / "hisn_al_muslim.json"


def split_english(text):
    """Split the English entry into transliteration, translation and reference.

    Most entries look like:
        <transliteration>\n\n<translation>\n\nReference:\n\n<source>
    Text is kept exactly as written; we only decide which part is which.
    """
    # "Reference:" usually sits on its own line, but not always, so match it loosely.
    parts = re.split(r"\s*Reference:\s*", text, maxsplit=1)
    body = parts[0]
    reference = parts[1] if len(parts) == 2 else ""
    paragraphs = body.split("\n\n")
    translation = paragraphs[-1]
    transliteration = "\n\n".join(paragraphs[:-1])
    return transliteration.strip(), translation.strip(), reference.strip()


def main(db_path):
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    topics = {
        int(chapter_id): title
        for chapter_id, title in db.execute(
            "SELECT id, title_en FROM chapter WHERE collection_id = ?", (HISN_AL_MUSLIM,))
    }

    # hadith_content = Arabic, hadith_en_content = English; they share the same id (c0).
    rows = db.execute(
        """
        SELECT ar.c4 AS number, ar.c3 AS chapter_id, ar.c7 AS arabic, en.c4 AS english
        FROM hadith_content ar
        JOIN hadith_en_content en ON en.c0 = ar.c0
        WHERE ar.c1 = ?
        ORDER BY ar.c5  -- position in the book
        """,
        (HISN_AL_MUSLIM,),
    ).fetchall()

    duas = []
    for number, chapter_id, arabic, english in rows:
        transliteration, translation, reference = split_english(english)
        duas.append({
            "number": number,  # text, because some are like "75a"
            "topic": topics[int(chapter_id)],
            "arabic": arabic.strip(),
            "transliteration": transliteration,
            "translation": translation,
            # The book's reference for the dua, e.g. "Muslim 1/414.", sometimes
            # with the author's notes (like the reward for saying it).
            "source": reference,
        })

    OUT_FILE.write_text(json.dumps(duas, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Saved {len(duas)} duas to {OUT_FILE}")


if __name__ == "__main__":
    main(sys.argv[1])
