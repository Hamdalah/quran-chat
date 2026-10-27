# Quran & Dua Guide (Version 3)

A website where you can **ask a question in plain English** ("What dua can I say
when I feel anxious?") and get a short answer that uses **only** Quran verses and
duas from *Hisn al-Muslim*, with every citation shown in full.

You can also search by keyword (like "anxiety" or "travel") and see:
- **Duas** from *Hisn al-Muslim* (Fortress of the Muslim), with Arabic,
  transliteration, translation, and the hadith reference (e.g. *Al-Bukhari 7/158*)
- **Quran verses** in Arabic and English, with their reference (e.g. *Al-Baqarah 2:153*)

You can also **browse duas by topic** (131 topics, like "When waking up" or "For anxiety and sorrow").

## How the AI answers stay grounded

1. The AI turns the question into search words (e.g. "anxious" becomes
   anxiety, worry, grief, distress).
2. The app searches **its own database** with those words and numbers what it finds
   (Q1, Q2, … for verses and D1, D2, … for duas).
3. The AI writes a short answer using **only** those passages, citing them like [D1].
4. The code checks every citation. Any label the AI made up is removed, and the
   Arabic, translation, and reference shown under the answer always come from the
   database, never from the AI.

The AI is told not to give religious rulings (fatwas) and to say so honestly when the
passages don't answer the question. The Search and Browse tabs don't use AI at all.

## What each file does

| File | What it does |
|---|---|
| `data/quran_en.json` | The Quran: Arabic text and the Saheeh International English translation |
| `data/hisn_al_muslim.json` | 268 duas from Hisn al-Muslim, with their references |
| `tools/extract_duas.py` | Shows how the dua file was made (you don't need to run it) |
| `build_database.py` | Turns the two JSON files into a searchable database (`quran.db`) |
| `app.py` | The web server. It runs searches, checks citations, and serves the web page |
| `ai.py` | The two AI steps: picking search words and writing the answer |
| `test_chat.py` | Tests the chat logic with a fake AI (free, no key needed) |
| `static/index.html` | The web page you see in your browser |
| `static/fonts/UthmanicHafs.otf` | The King Fahd Complex Quran font, so Arabic marks display correctly |

## How to run it on your computer

1. **Install Python** (version 3.10 or newer) from https://www.python.org/downloads/.
   On Windows, tick **"Add Python to PATH"** during install.
2. **Open a terminal** in this folder.
   - Windows: open the folder, click the address bar, type `cmd`, and press Enter.
   - Mac: right-click the folder and choose **New Terminal at Folder**.
3. **Install the libraries** this app needs:
   ```
   pip install -r requirements.txt
   ```
4. **Build the database** (you only need to do this once):
   ```
   python build_database.py
   ```
   You should see it save 6236 Quran verses and 267 duas.
5. **Give the app your Anthropic API key** (needed only for the "Ask a question" tab).
   Create a key at https://console.anthropic.com (under **API Keys**) and add credits
   under **Plans & Billing**. Then, in the same terminal:
   - Windows: `set ANTHROPIC_API_KEY=your-key-here`
   - Mac: `export ANTHROPIC_API_KEY=your-key-here`

   You need to do this each time you open a new terminal. **Never put your key in
   the code, and never share it.** If it leaks, delete it in the Console and make a new one.
6. **Start the website:**
   ```
   uvicorn app:app --reload
   ```
7. Open **http://127.0.0.1:8000** in your browser and ask a question.
   To stop the server, press `Ctrl + C` in the terminal.

(On Mac, you may need to type `python3` and `pip3` instead of `python` and `pip`.)

To check the chat logic without spending anything: `python test_chat.py`

**Cost:** each question makes two calls to Claude Opus 5.5. Expect a few cents
per question. Check the Usage page in the Console after trying it.
If Claude declines a question, Anthropic automatically retries it on a suitable
fallback model (the `fallbacks` setting in `ai.py`).

## Sources and licenses

- Quran text and translation: the [quran-json](https://github.com/risan/quran-json)
  project (CC BY-SA 4.0, see `data/QURAN_DATA_LICENSE.txt`). Its Arabic text comes from
  [QuranEnc](https://quranenc.com), and its English translation is Saheeh International via
  [Tanzil](https://tanzil.net/trans/en.sahih). Check Tanzil's terms for the
  translation before any commercial use.
- Duas: *Hisn al-Muslim* by Sa'id bin Wahf Al-Qahtani, taken from the
  [hadith](https://www.npmjs.com/package/hadith) npm package (v1.3.0), whose data matches
  sunnah.com. The English translation of Hisn al-Muslim is a published, copyrighted
  translation. Get permission before any public or commercial launch.
- Fonts: Amiri (Google Fonts) for duas, and KFGQPC Uthmanic Script HAFS for the Quran.
  The Quran font is by the King Fahd Glorious Quran Printing Complex. It is free to
  use and share, but it must not be modified or sold.

## About the duas: please read

- Only duas with a listed reference are included. One entry (#149) had no
  reference in our data, so it is left out.
- The "Reference & notes" line is the book's own footnote, copied word for word.
  It often includes the authenticity grading (e.g. "Al-Albani graded it authentic").
- A few entries are not supplications of the Prophet ﷺ. Some are sayings of
  Companions (e.g. #161, #168), and some are advice (e.g. #114). **Before launch,
  ask someone with Islamic knowledge to review the list** and mark which entries to keep.

## Ideas for later

- **Follow-up questions:** right now each question is answered on its own.
- **Better search:** "meaning" search with embeddings would find matches that share
  no words with the question.
- **Put it online** (e.g. Render or Railway), with a limit on questions per person
  so your API bill stays under control.
