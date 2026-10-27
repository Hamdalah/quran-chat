# The AI part of the app. It is used in two small steps:
#
#   1. find_search_words(): turn the user's question into search words,
#      e.g. "I can't stop worrying" -> ["anxiety", "worry", "grief", "distress"]
#   2. write_answer(): write a short answer that may ONLY use the passages
#      our database search found, citing them like [Q1] or [D2].
#
# The AI never supplies verse or dua text itself. The app shows the exact
# text from the database for every citation, and app.py removes any
# citation that doesn't match a passage we actually sent.
#
# Needs an Anthropic API key in the ANTHROPIC_API_KEY environment variable.

import json

import anthropic

MODEL = "claude-opus-5-5"

# If the model declines a request, Anthropic automatically retries it on a
# suitable fallback model instead of returning a refusal.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AIError(Exception):
    """A problem talking to the AI, with a message that is safe to show users."""


def ask_claude(system, user_text, effort, max_tokens, json_schema=None):
    """Send one message to Claude and return the text of its reply."""
    extra = {}
    if json_schema:
        # Forces the reply to be JSON matching this shape.
        extra["output_config"] = {
            "effort": effort,
            "format": {"type": "json_schema", "schema": json_schema},
        }
    else:
        extra["output_config"] = {"effort": effort}

    try:
        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_text}],
            betas=[FALLBACK_BETA],
            fallbacks="default",
            **extra,
        )
    except anthropic.AuthenticationError:
        raise AIError("The AI key is missing or invalid. Check ANTHROPIC_API_KEY.")
    except anthropic.RateLimitError:
        raise AIError("Too many questions at once. Please wait a minute and try again.")
    except anthropic.APIConnectionError:
        raise AIError("Could not reach the AI service. Check your internet connection.")
    except anthropic.APIStatusError as e:
        raise AIError(f"The AI service returned an error: {e.message}")
    except anthropic.AnthropicError as e:  # e.g. no API key set at all
        raise AIError(f"The AI is not set up: {e}")

    if response.stop_reason == "refusal":
        raise AIError("The AI could not answer this question.")
    return "".join(block.text for block in response.content if block.type == "text")


SEARCH_WORDS_PROMPT = """You turn a question into English search words for a database \
of Quran verses (Saheeh International translation) and duas from Hisn al-Muslim.

Return 3 to 8 single English words likely to appear in relevant verses or dua \
translations or topic names. Include the key words from the question plus close \
synonyms (for example "anxious" -> anxiety, worry, grief, distress, sorrow)."""


def find_search_words(question):
    reply = ask_claude(
        SEARCH_WORDS_PROMPT,
        question,
        effort="low",
        max_tokens=4000,
        json_schema={
            "type": "object",
            "properties": {"words": {"type": "array", "items": {"type": "string"}}},
            "required": ["words"],
            "additionalProperties": False,
        },
    )
    return json.loads(reply)["words"]


ANSWER_PROMPT = """You help Muslims find guidance in the Quran and in authentic duas. \
You will get a question and a numbered list of passages that our database search \
found: Quran verses labelled Q1, Q2, ... and duas from Hisn al-Muslim labelled D1, D2, ...

Answer using only these passages:
- Cite each passage you rely on by its label in square brackets, like [Q2] or [D1]. \
Only use labels from the list.
- Do not quote the passages at length. The app shows the full Arabic and English text \
of every passage you cite right under your answer, so just explain briefly how each \
one relates to the question.
- Do not add anything from memory: no other verses, hadith, tafsir or scholars' views.
- If none of the passages really address the question, say so plainly, cite nothing, \
and suggest asking a qualified scholar or local imam.
- If the question asks for a religious ruling (is X halal or haram, how to perform an \
act of worship in detail, etc.), do not give a ruling. Share any relevant passages and \
recommend asking a qualified scholar.
- Write 2 to 5 sentences in plain, warm English. Cite the passages that help most \
(usually 1 to 4), not all of them."""


def write_answer(question, passages):
    """passages: a dict like {"Q1": {...}, "D1": {...}} from the database."""
    lines = []
    for label, p in passages.items():
        if label.startswith("Q"):
            lines.append(f'[{label}] Quran, {p["citation"]}: "{p["translation"]}"')
        else:
            lines.append(
                f'[{label}] Dua, {p["citation"]} (topic: {p["topic"]}): '
                f'"{p["translation"]}" Reference: {p["source"]}'
            )
    user_text = f"Question: {question}\n\nPassages:\n" + "\n".join(lines)
    return ask_claude(ANSWER_PROMPT, user_text, effort="medium", max_tokens=8000)
