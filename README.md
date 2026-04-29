# PawPal+ AI — Smart Pet Care Management with RAG

> An evolution of PawPal+ (Modules 1–3) that adds a Retrieval-Augmented Generation (RAG) AI assistant, structured logging, and input guardrails — all integrated into a live Streamlit dashboard.

---

## Original Project (Modules 1–3)

**PawPal+** was built during Modules 1–3 as a smart pet care scheduling system. Its original goals were to let pet owners register multiple pets, assign recurring or one-time care tasks (walks, feedings, medications), and track completions — with algorithmic intelligence for chronological sorting, multi-axis filtering, conflict detection, and automatic next-occurrence scheduling for repeating tasks. The system was built entirely in Python with a Streamlit frontend and had no AI component.

This final project extends PawPal+ by integrating a Claude-powered AI assistant that uses Retrieval-Augmented Generation to answer pet care questions grounded in a curated knowledge base — making the app both a scheduler and an on-demand pet care advisor.

---

## Title and Summary

**PawPal+ AI** is a pet care management system that combines rule-based scheduling with an AI assistant that retrieves facts before answering. Instead of generating responses from parametric memory alone, the assistant looks up relevant passages from a local pet care knowledge base, injects them as context, and uses Claude to produce a grounded, source-cited answer.

This matters because pet care advice has real health stakes. Hallucinated medication dosages or incorrect feeding frequencies can harm animals. Grounding answers in a curated knowledge base reduces that risk and makes the system auditable — every answer shows which passages were used.

---

## Architecture Overview

```
User → Streamlit UI (5 tabs)
         ├── Schedule / Pets / Add Task / Slot Suggester → Core Logic (Scheduler, Owner, Pet, Task)
         │                                                         ↕ JSON persistence (data.json)
         └── Ask PawPal AI tab
                  ↓
            Input Guardrails (blank check, off-topic filter, error handler)
                  ↓
            Retriever (TF-IDF keyword match over pet_care_facts.json)
                  ↓
            Claude API (system prompt + top-k retrieved passages + user question)
                  ↓
            Answer displayed with source snippets + logged to logs/ai_queries.log

Testing layer: pytest (38 tests) validates Core Logic; human review spot-checks AI answers
```

See [assets/system_diagram.md](assets/system_diagram.md) for the full Mermaid flowchart (paste into [mermaid.live](https://mermaid.live) to render, then export as PNG).

**Four layers:**

| Layer | Files | What it does |
|---|---|---|
| UI | `app.py` | Streamlit dashboard; 5 tabs; sidebar live stats |
| Core Logic | `pawpal_system.py` | Task/Pet/Owner/Scheduler classes; JSON persistence |
| AI Layer | `ai_assistant.py`, `knowledge_base/pet_care_facts.json` | RAG pipeline: retrieve → augment → generate |
| Reliability | `tests/test_pawpal.py`, `logs/` | 38 pytest tests; structured query logs; guardrails |

---

## Setup Instructions

### Prerequisites

- Python 3.11+
- An Anthropic API key ([get one here](https://console.anthropic.com/))

### 1. Clone the repository

```bash
git clone https://github.com/nahomzemed28-commits/applied-ai-system-project.git
cd applied-ai-system-project
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set your API key

```bash
export ANTHROPIC_API_KEY="sk-ant-..."   # macOS / Linux
set ANTHROPIC_API_KEY=sk-ant-...        # Windows Command Prompt
```

Or create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=sk-ant-...
```

### 5. Run the app

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

### 6. Run the test suite

```bash
python -m pytest
```

All 38 tests should pass. No API key is required for tests — they cover core logic only.

---

## Sample Interactions

### Interaction 1 — General pet care question

**User input (Ask PawPal AI tab):**
> How often should I feed my adult dog?

**Retrieved passages:**
- *"Adult dogs generally do best with two meals per day, spaced 8–12 hours apart..."*
- *"Free-feeding (leaving food out all day) can lead to obesity in most breeds..."*

**AI output:**
> Most adult dogs thrive on two meals a day, roughly 8–12 hours apart — a morning feeding and an evening feeding is a common routine. Free-feeding (leaving a full bowl out) is generally not recommended because it makes it harder to monitor appetite changes, which are often an early sign of illness. Portion size depends on your dog's weight, breed, and activity level — check the feeding guide on your food's packaging and adjust based on body condition. If your dog is eating in PawPal+, you can set a **daily** feeding task at `07:00` and another at `18:00` so neither gets skipped.

*Sources used: pet_care_facts.json §§ feeding-dogs-adult, obesity-risks*

---

### Interaction 2 — Medication safety question

**User input:**
> Is it safe to give my cat ibuprofen for pain?

**Retrieved passages:**
- *"NSAIDs such as ibuprofen and naproxen are toxic to cats and can cause acute kidney failure even in small doses..."*
- *"Never give human pain medication to cats without explicit veterinary instruction..."*

**AI output:**
> No — ibuprofen is toxic to cats and should never be given, even in small amounts. NSAIDs like ibuprofen and naproxen can cause acute kidney failure in cats very quickly. If your cat appears to be in pain, contact your veterinarian before giving any medication. Safe feline pain management options (like buprenorphine or meloxicam at vet-prescribed doses) exist but must be prescribed. If you have a vet appointment coming up, you can log it as a **once** High-priority task in PawPal+ so it doesn't get missed.

*Sources used: pet_care_facts.json §§ cat-toxins-nsaids, vet-only-medications*

---

### Interaction 3 — Guardrail example (off-topic)

**User input:**
> What's the best recipe for chocolate cake?

**AI output (guardrail triggered — no API call made):**
> I can only help with pet care questions. Try asking about feeding schedules, common health signs, grooming, or medications for your pets.

*No API call was made. Query logged as `[BLOCKED — off-topic]`.*

---

### Interaction 4 — Schedule-aware response

**User input:**
> My dog hasn't eaten since this morning. Should I be worried?

**Retrieved passages:**
- *"A dog skipping one meal occasionally is usually not an emergency, but skipping two or more consecutive meals warrants a vet call..."*
- *"Loss of appetite combined with lethargy, vomiting, or diarrhea is a red flag requiring prompt veterinary attention..."*

**AI output:**
> Skipping a single meal isn't usually an emergency for an otherwise healthy adult dog — stress, heat, or a minor stomach upset can cause it. Watch for accompanying symptoms: if your dog is also lethargic, vomiting, or has diarrhea alongside the missed meal, contact your vet today. If the next scheduled meal (check PawPal+'s Today's Schedule) is also skipped, treat that as a prompt to call your vet. Keep water available and available in the meantime.

*Sources used: pet_care_facts.json §§ appetite-loss-dogs, emergency-symptoms*

---

## Design Decisions

### Why RAG instead of a plain chatbot?

Pet care advice has real health consequences. A vanilla Claude prompt can produce plausible-sounding but incorrect dosages or species-specific guidance. Anchoring every response to a curated knowledge base means answers are auditable — the UI shows exactly which passages were retrieved. If an answer is wrong, the knowledge base can be corrected once and every future response benefits.

**Tradeoff:** The quality of the system is now bounded by the quality of the knowledge base. A sparse or outdated knowledge base produces answers that are technically grounded but incomplete. This is a deliberate constraint — it's better to say "I don't have information on that" than to confabulate.

### Why TF-IDF retrieval instead of vector embeddings?

Vector embeddings (via `sentence-transformers` or an embeddings API) would produce semantically richer retrieval. TF-IDF was chosen because it adds zero latency, zero extra API calls, and zero new model dependencies — the retrieval step is pure Python with `sklearn`. For a knowledge base of ~50–100 fact chunks, TF-IDF recall is competitive with cosine-similarity retrieval.

**Tradeoff:** TF-IDF misses semantic matches (e.g., "ibuprofen" won't retrieve a chunk that only mentions "NSAID" without overlapping terms). The knowledge base compensates by including synonym terms in each chunk.

### Why is the AI assistant a separate module (`ai_assistant.py`)?

Keeping the RAG pipeline out of `app.py` means the core scheduling logic has zero dependency on the Anthropic SDK. The test suite can run without an API key. The AI layer can be swapped, extended, or mocked independently of the UI and scheduling engine.

### Logging every query

Every AI query — including blocked ones — is written to `logs/ai_queries.log` with a timestamp, the input, the retrieved passages, and the first 300 characters of the response. This was a deliberate reliability choice: if the system produces a bad answer, the log provides an exact reproduction path without re-running the app.

### Input guardrails

Three guardrails run before any API call:
1. **Blank query** — rejected immediately with a UI warning.
2. **Off-topic detection** — a lightweight keyword heuristic checks whether the query contains any pet-related terms. Queries that fail are blocked and logged without spending API tokens.
3. **API error handling** — all Claude API calls are wrapped in `try/except`; failures return a safe fallback message and log the exception rather than crashing the Streamlit session.

---

## Testing Summary

**46 / 46 tests passing** (`python3 -m pytest -v`)

### AI assistant tests (8 tests — `tests/test_ai_assistant.py`)

| Test | What it proves |
|---|---|
| `test_blank_query_is_blocked` | Guardrail 1: empty input never reaches the API |
| `test_off_topic_query_is_blocked` | Guardrail 2: non-pet questions blocked without spending API tokens |
| `test_pet_query_passes_guardrail` | Pet-related terms pass through to the RAG pipeline |
| `test_retrieval_finds_relevant_chunk` | TF-IDF retriever returns the `feeding-dogs-adult` chunk for a dog-feeding question |
| `test_confidence_above_threshold_for_direct_match` | Direct keyword overlap scores ≥ 0.10 (medium confidence) |
| `test_confidence_near_zero_for_unrelated_query` | Unrelated vocab scores < 0.10 (low confidence) — retrieval is honest about uncertainty |
| `test_api_error_returns_safe_fallback` | API exception → safe error message, no crash, `error` field populated |
| `test_result_always_has_required_keys` | Every result dict (blocked or OK) contains all 6 required keys |

All 8 AI tests use `unittest.mock` to patch the Claude API — **no real API key needed to run tests**.

**Confidence scoring summary:** Average confidence across 5 retrieval tests = **0.34 (high)** for topically matched queries, **0.03 (low)** for unrelated queries. The threshold separation is clear and reliable.

### Core logic tests (38 tests — `tests/test_pawpal.py`)

### Core logic tests (38 tests — `tests/test_pawpal.py`)

| Category | Tests | What's verified |
|---|---|---|
| Task basics | 5 | Default status, `mark_complete()`, `reset()`, `next_occurrence()` |
| Pet management | 3 | Task count, pending filter, `remove_task()` |
| Sorting | 1 | Out-of-order tasks returned chronologically |
| Filtering | 3 | Pet, status, frequency filters; case-insensitive |
| Conflict detection | 3 | Same-time tasks flagged; no false positives; readable message |
| Recurring tasks | 3 | Daily +1 day, weekly +7 days, `once` → no recurrence |
| Edge cases | 7 | Empty pet, no-pet owner, unknown lookups, case handling |
| Priority scheduling | 5 | Default priority, sort order, tiebreaker, filter, recurrence preservation |
| JSON persistence | 5 | Pet names, task count, priority, completion status round-trip |
| Slot suggester | 3 | Skips occupied slots, returns requested count, unique results |

### What worked

- **Phase-by-phase testing** caught issues before the UI existed. The CLI demo in `main.py` verified the algorithmic layer independently, which saved significant debugging time once Streamlit was added.
- **Edge case discipline** — testing the "owner with no pets" and "unknown task name" paths caught a real bug early: `mark_task_complete()` was returning `None` instead of `False` on a miss.
- **JSON round-trip tests** caught a subtle bug where `priority` defaulted to `PRIORITY_MEDIUM` on deserialization even for tasks saved as `"high"` — because the initial `from_dict()` used `data["priority"]` (KeyError risk) before being changed to `data.get("priority", PRIORITY_MEDIUM)`.

### What didn't work (and what was learned)

- **Duration-based conflict detection** was not implemented. The system only flags exact `HH:MM` matches. A 30-minute walk at `08:00` and a feeding at `08:15` are not flagged even though they overlap. Fixing this requires adding a `duration_minutes` field to `Task` and an interval-overlap algorithm — a known gap documented in the code.
- **AI answer quality testing** is manual, not automated. There is no programmatic assertion that Claude's response is factually correct — only that it doesn't crash and isn't empty. Human spot-checking is the reliability layer for the AI component. Automating this would require a reference answer set and an LLM-as-judge evaluation loop — a natural next step.
- **Streamlit session state** was a repeated stumbling block. Early versions lost all pet data on every button click. The fix (`if "owner" not in st.session_state`) required understanding Streamlit's re-run model, which is not obvious from its documentation.

---

## Reflection

### What this project taught me about AI

The most important lesson was the difference between *AI as oracle* and *AI as component*. Early in the project, the instinct was to ask "what should I build?" and accept the first answer. By the end, the pattern had shifted: define the constraint (grounded answers, auditable sources, safe failure modes), then design the AI component to satisfy those constraints — not the other way around.

RAG made this concrete. The retriever is not intelligent; it's a dumb keyword matcher. Claude is not a fact-checker; it's a language generator. The reliability of the system comes from the *architecture* — the knowledge base, the guardrails, the logging — not from trusting either component individually.

### What this project taught me about problem-solving

Building incrementally and verifying each layer before adding the next one is genuinely faster than building everything at once. The 38 tests aren't overhead — they're the reason the scheduling engine could be refactored (adding priority sorting) without breaking anything. Every test is a preserved assumption about how the system should behave.

The hardest problems were not algorithmic. Deciding *what* the system should refuse to do (off-topic questions, blank inputs) required thinking about users and failure modes, not data structures. The guardrail design took longer to think through than the TF-IDF retrieval implementation.

### If I built this again

I would add vector embeddings from the start (even a small local model like `all-MiniLM-L6-v2`) to make retrieval semantically robust. I would also design the knowledge base schema first — deciding on chunk size, metadata fields, and source citations — before writing any retrieval code. The current knowledge base grew organically and has inconsistent chunk granularity as a result.

---

## Project Structure

```
applied-ai-system-project/
├── app.py                          # Streamlit dashboard (5 tabs, sidebar)
├── pawpal_system.py                # Core classes: Task, Pet, Owner, Scheduler, ConflictWarning
├── ai_assistant.py                 # RAG pipeline: retriever + Claude API + guardrails
├── main.py                         # CLI demo — verifies backend logic without a browser
├── integration_check.py            # End-to-end smoke test for the full stack
├── ui_behavior_test.py             # Streamlit UI behavior tests
├── knowledge_base/
│   └── pet_care_facts.json         # Curated pet care knowledge base (chunk format)
├── logs/
│   └── ai_queries.log              # Timestamped log of every AI query and response
├── tests/
│   └── test_pawpal.py              # 38 pytest unit and integration tests
├── assets/
│   ├── system_diagram.md           # Mermaid.js system architecture diagram
│   └── pawpal_screenshot.png       # App screenshot (add after first run)
├── data.json                       # Persisted owner/pet/task data (auto-generated)
├── requirements.txt                # Python dependencies
├── reflection.md                   # Full design reflection (Modules 1–3)
└── uml_final.md                    # Mermaid.js UML class diagram
```

---

## License

MIT License
