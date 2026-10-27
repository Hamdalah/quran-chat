# Checks the chat logic WITHOUT calling the real AI (so it's free and needs no key).
# We replace the two AI functions with fake ones that return fixed text.
#
# Run it with:  python test_chat.py

from fastapi.testclient import TestClient

import ai
import app

client = TestClient(app.app)


def fake_search_words(question):
    return ["anxiety", "worry", "grief", "distress"]


def fake_answer(question, passages):
    # Cites one real passage, one that exists, and one the AI "made up" (Q99).
    return "Try this dua [D1]. Allah also says [Q1]. And see [Q99]."


def fake_ai_down(question):
    raise ai.AIError("The AI key is missing or invalid. Check ANTHROPIC_API_KEY.")


def test_citations_are_checked():
    ai.find_search_words = fake_search_words
    ai.write_answer = fake_answer

    response = client.post("/api/ask", json={"question": "I feel anxious, what can I say?"})
    assert response.status_code == 200, response.text
    data = response.json()

    # The made-up [Q99] must be removed; the real ones stay.
    assert "[Q99]" not in data["answer"]
    assert "[D1]" in data["answer"] and "[Q1]" in data["answer"]

    # Each citation carries the exact text from our database.
    labels = [c["label"] for c in data["citations"]]
    assert labels == ["D1", "Q1"], labels
    dua = data["citations"][0]
    assert dua["citation"].startswith("Hisn al-Muslim ")
    assert dua["arabic"] and dua["translation"] and dua["source"]
    print("OK  made-up citation removed; real ones kept:", [c["citation"] for c in data["citations"]])


def test_ai_errors_are_shown_politely():
    ai.find_search_words = fake_ai_down
    response = client.post("/api/ask", json={"question": "anything"})
    assert response.status_code == 503
    assert "ANTHROPIC_API_KEY" in response.json()["detail"]
    print("OK  AI problems give a clear message:", response.json()["detail"])


def test_empty_question():
    response = client.post("/api/ask", json={"question": "   "})
    assert response.status_code == 400
    print("OK  empty question rejected")


if __name__ == "__main__":
    test_citations_are_checked()
    test_ai_errors_are_shown_politely()
    test_empty_question()
    print("All tests passed.")
