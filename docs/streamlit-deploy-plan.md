# Deploy to Streamlit (local + Cloud, Ollama vs Gemini)

## Goals

- Same codebase runs **locally** and on **Streamlit Community Cloud**.
- **Locally:** AI Assistant uses **Ollama (Llama3)**; DuckDB at `data/copper.duckdb` (user runs generator or uses existing DB).
- **On Streamlit:** AI Assistant uses **Google Gemini**; DuckDB created automatically on first run if missing (run generator once at startup).
- **Background Vanna warmup:** Load and train Vanna at app startup in a background thread so the first visit to the AI Assistant page is fast (no long block).
- No duplicate code paths beyond one "which LLM?" and "ensure DB exists?" layer.

## Detection strategy

- **LLM choice:** Use **Gemini** when a Gemini/Google API key is available (e.g. `st.secrets.get("GOOGLE_API_KEY")` or `os.environ.get("GOOGLE_API_KEY")`); otherwise use **Ollama**.
- **DB availability:** If `data/copper.duckdb` is missing, run the synthetic data generator once at startup (cached) so the DB exists.
- **Vanna warmup:** Start a background thread at app start that calls the same `setup_vanna()` used by the AI Assistant page, so the `@st.cache_resource` cache is warmed before the user opens that page.

---

## 1. Ensure database exists on first run (Cloud and optional local)

**Problem:** On Streamlit Cloud, `data/copper.duckdb` is not in the repo (gitignored). The app must create it or it will crash.

**Approach:**

- In **app.py**, before the page router, add a one-time check: if `not os.path.exists(DB_PATH)`, call the generator so the DB is created.
- Use `@st.cache_resource` on a small function that returns "ok" and inside it, if DB missing, call `generate_synthetic_data.main()` (or a thin wrapper). Call that function once at app top-level. Streamlit runs it only when the cache is cold.
- Ensure **utils/data_loader.py** and **generators/generate_synthetic_data.py** use the same `DB_PATH` (e.g. data_loader exports `DB_PATH`, generator imports it or keeps path consistent).
- **Local:** If the user already has `data/copper.duckdb`, the check does nothing.

**Files:** app.py, optionally a small helper in utils (e.g. `ensure_db()`) that calls the generator when DB is missing.

---

## 2. AI Assistant: dual backend (Ollama vs Gemini)

**Current state:** pages/04_ai_assistant.py uses Vanna with `vanna.legacy.ollama.Ollama` and `ChromaDB_VectorStore`, and connects to DuckDB at `DB_PATH`. Training is inline (DDL + example question–SQL pairs).

**Target state:**

- **When Gemini API key is present:** Use Vanna with a **Gemini** backend (e.g. `GoogleGeminiChat`) and the same ChromaDB vector store. Connect to DuckDB the same way. Use the **same** training data (DDL + example pairs).
- **When Gemini API key is absent:** Keep current Ollama + ChromaDB + DuckDB setup (local Llama3).

**Implementation outline:**

- **Config:** Read Gemini key from `st.secrets.get("GOOGLE_API_KEY")` or `os.environ.get("GOOGLE_API_KEY")`. If set and non-empty, `use_gemini = True`; else `use_gemini = False`.
- **Setup function:** Refactor `setup_vanna()` into two paths inside the same function: (1) Ollama path (existing), (2) Gemini path using Vanna’s Gemini chat class, same `connect_to_duckdb` and training loop.
- **Caption / sidebar:** Show "Using Ollama (local)" vs "Using Gemini (cloud)" based on `use_gemini`.
- **Error handling:** If `use_gemini` but key missing/invalid, show clear message. Keep Ollama-specific message for connection refused.
- **Dependencies:** Add Gemini-related dependency to requirements.txt (e.g. `vanna[gemini]`). Keep existing deps for local.

**Files:** pages/04_ai_assistant.py, requirements.txt.

---

## 3. Background Vanna warmup

**Goal:** Run Vanna setup (connect, train on DDL + examples) in a **background thread** when the app starts, so that by the time a user opens the AI Assistant page, `setup_vanna()` has already run and the result is in `@st.cache_resource`. First visit to AI Assistant then returns immediately from cache instead of blocking 30+ seconds.

**Approach:**

1. **Shared setup module**
   - Move `setup_vanna()` (and its training data: DDL list, documentation strings, example_pairs) into a **shared module** used by both the warmup and the AI Assistant page (e.g. **utils/vanna_setup.py**). The function must be decorated with `@st.cache_resource` in that module so there is a single cache key for "Vanna instance."
   - The AI Assistant page imports and calls this same `setup_vanna()` (no duplicate training logic).

2. **Start warmup from app.py**
   - In **app.py**, after imports and before the page router (or right after `ensure_db()`), start a **daemon thread** that calls `setup_vanna()`. Use a **process-wide or module-level guard** (e.g. a global flag or `threading.Lock`) so that the thread is started only **once per process**, not on every Streamlit rerun. Streamlit re-executes the script on each interaction, so without a guard you would spawn a new thread every rerun.
   - Implementation detail: e.g. in the shared module, maintain `_warmup_started = False`; in app.py, if not `_warmup_started`, set it True and start `threading.Thread(target=setup_vanna, daemon=True).start()`. The thread will run `setup_vanna()`; when it returns, the cache is populated.

3. **AI Assistant page: "still loading" handling**
   - When the user opens the AI Assistant page before the background thread has finished, the page will call `setup_vanna()`. That call will **block** until the cached result is available (because the background thread and this call share the same cache—whoever runs first wins; the second call waits and then gets the cached value). So no extra logic is strictly required: the page may block once if the user is very fast. Alternatively, to avoid blocking: the page can check "is Vanna ready?" (e.g. try to get the cached instance or check a "setup done" flag set by the background thread). If not ready, show a message like "Preparing AI… (runs once at app start)" and `st.rerun()` after a short `time.sleep(2)` until the cache is populated. This keeps the UI responsive at the cost of a couple of reruns.
   - **Recommendation:** Implement the optional "still loading" + rerun so the first visitor never sits on a frozen page; document that the very first load after deploy may take one short "Preparing…" cycle.

**Files:** New utils/vanna_setup.py (shared `setup_vanna()` + training data), app.py (start daemon thread with guard), pages/04_ai_assistant.py (import from utils/vanna_setup, optionally add "Preparing AI…" branch).

---

## 4. Requirements and Streamlit config

- **requirements.txt:** Add Gemini-related dependency for Vanna (e.g. `vanna[gemini]` or `google-generativeai`). Keep existing deps (duckdb, streamlit, vanna[chromadb], ollama, etc.) for local.
- **Streamlit Cloud:** User sets in app Secrets: `GOOGLE_API_KEY = "your-gemini-api-key"`. App reads via `st.secrets["GOOGLE_API_KEY"]` or env.
- **.streamlit/config.toml:** No change required.

**Files:** requirements.txt.

---

## 5. Deployment steps (for the user)

1. Push the repo to GitHub.
2. Streamlit Community Cloud: New app → connect repo, Main file path `app.py`, Python 3.10 (or similar).
3. Advanced settings → Secrets: `GOOGLE_API_KEY = "your-google-gemini-api-key"`.
4. Deploy. First run creates DB (if missing) and starts Vanna warmup in background; first visit to AI Assistant may show "Preparing AI…" briefly, then load from cache.

---

## 6. Summary of code changes

| Area | Action |
|------|--------|
| **DB on first run** | app.py (or utils): call generator when DB_PATH missing, guarded by cache; ensure data/ exists. |
| **AI Assistant** | 04_ai_assistant.py: branch on Gemini API key; if set use Gemini backend + same training/DuckDB; else Ollama. Update sidebar caption and errors. |
| **Background Vanna warmup** | New utils/vanna_setup.py with shared setup_vanna() and training data. app.py: start daemon thread (with one-time guard) that calls setup_vanna(). 04_ai_assistant.py: import setup_vanna from utils/vanna_setup; optionally show "Preparing AI…" and rerun until cache ready. |
| **Requirements** | Add Gemini-related dependency; keep existing deps. |
| **Secrets** | Document GOOGLE_API_KEY in Streamlit Cloud Secrets for Gemini. |

No refactor to Portfolio, Customer Intel, or Architecture beyond current behavior; they work on Cloud once the DB exists.
