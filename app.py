# Step 2: The web server. Start it with:
#   uvicorn app:app --reload
# then open http://127.0.0.1:8000 in your browser.

import re
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import ai

HERE = Path(__file__).parent
DB_FILE = HERE / "quran.db"

app = FastAPI(title="Quran & Dua Search")
# Serve files like fonts from the "static" folder at /static/...
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")


def get_db():
    if not DB_FILE.exists():
        raise HTTPException(500, "Database not found. Run: python build_database.py")
    db = sqlite3.connect(DB_FILE)
    db.row_factory = sqlite3.Row  # lets us read columns by name
    return db


def make_safe_query(words):
    """Turn a list of words into a safe search query.

    We keep only letters/numbers, then wrap each word in quotes, so symbols
    like * or " can't break the search.
    Words are joined with OR, so "worry grief" finds text with either word
    (text with both words still ranks higher).
    """
    cleaned = "".join(c if c.isalnum() else " " for c in " ".join(words)).split()
    return " OR ".join(f'"{w}"' for w in cleaned)


# The citation is always built here from the database, never typed by hand.
def verse_to_dict(r):
    return {
        "citation": f"{r['surah_name']} {r['surah']}:{r['ayah']}",
        "arabic": r["arabic"],
        "translation": r["translation"],
    }


def dua_to_dict(r):
    return {
        "citation": f"Hisn al-Muslim {r['number']}",
        "topic": r["topic"],
        "arabic": r["arabic"],
        "transliteration": r["transliteration"],
        "translation": r["translation"],
        "source": r["source"],
    }


def search_verses(db, query, limit):
    rows = db.execute(
        """
        SELECT v.* FROM verses_search
        JOIN verses v ON v.id = verses_search.rowid
        WHERE verses_search MATCH ?
        ORDER BY rank          -- best matches first
        LIMIT ?
        """,
        (query, limit),
    ).fetchall()
    return [verse_to_dict(r) for r in rows]


def search_duas(db, query, limit):
    # Words that match the dua's topic count 3x more than words in its text.
    rows = db.execute(
        """
        SELECT d.* FROM duas_search
        JOIN duas d ON d.id = duas_search.rowid
        WHERE duas_search MATCH ?
        ORDER BY bm25(duas_search, 1.0, 3.0)
        LIMIT ?
        """,
        (query, limit),
    ).fetchall()
    return [dua_to_dict(r) for r in rows]


@app.get("/")
def home_page():
    return FileResponse(HERE / "static" / "index.html")


@app.get("/api/search")
def search(q: str, limit: int = 10):
    query = make_safe_query([q])
    if not query:
        return {"query": q, "quran": [], "duas": []}
    limit = min(limit, 50)

    db = get_db()
    result = {"query": q, "quran": search_verses(db, query, limit), "duas": search_duas(db, query, limit)}
    db.close()
    return result


@app.get("/api/topics")
def list_topics():
    """All dua topics, in the order they appear in Hisn al-Muslim."""
    db = get_db()
    rows = db.execute("SELECT topic FROM duas GROUP BY topic ORDER BY MIN(id)").fetchall()
    db.close()
    return [r["topic"] for r in rows]


@app.get("/api/duas")
def duas_for_topic(topic: str):
    db = get_db()
    rows = db.execute("SELECT * FROM duas WHERE topic = ? ORDER BY id", (topic,)).fetchall()
    db.close()
    return [dua_to_dict(r) for r in rows]


# ---- Step 3: the AI chat ----

class Question(BaseModel):
    question: str


def check_citations(answer, passages):
    """Keep only citations that match a passage we actually sent to the AI.

    Returns the cleaned answer, the labels it cites (in order), and any
    labels the AI made up (these are removed from the answer).
    """
    cited, invented = [], []
    for label in re.findall(r"\[([QD]\d+)\]", answer):
        if label in passages:
            if label not in cited:
                cited.append(label)
        elif label not in invented:
            invented.append(label)
    for label in invented:
        answer = answer.replace(f"[{label}]", "")
    return answer.strip(), cited, invented


@app.post("/api/ask")
def ask(body: Question):
    question = body.question.strip()[:500]
    if not question:
        raise HTTPException(400, "Please type a question.")

    try:
        # 1. Let the AI pick search words, then search OUR database with them.
        words = ai.find_search_words(question)
        query = make_safe_query(words)
        db = get_db()
        verses = search_verses(db, query, 8) if query else []
        duas = search_duas(db, query, 6) if query else []
        db.close()

        passages = {f"Q{i}": v for i, v in enumerate(verses, 1)}
        passages.update({f"D{i}": d for i, d in enumerate(duas, 1)})
        if not passages:
            return {
                "answer": "I couldn't find any verse or dua about this. "
                          "Please try different words, or ask a qualified scholar.",
                "citations": [], "search_words": words,
            }

        # 2. Let the AI write an answer using only those passages.
        answer = ai.write_answer(question, passages)
    except ai.AIError as e:
        raise HTTPException(503, str(e))

    # 3. Check every citation in code, and attach the exact database text.
    answer, cited, invented = check_citations(answer, passages)
    if invented:
        print(f"Removed citations the AI made up: {invented}")
    return {
        "answer": answer,
        "citations": [
            {"label": label, "kind": "quran" if label.startswith("Q") else "dua", **passages[label]}
            for label in cited
        ],
        "search_words": words,
    }
