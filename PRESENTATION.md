# PawPal AI — Engineer's Pitch
### Presentation Script

> Run `python3 demo_setup.py` then `streamlit run app.py` before you present.
> Keep the browser open on the **Ask PawPal AI** tab.

---

## 1. THE PROBLEM
*~60 seconds | No demo yet — just talk*

---

**Opening line (say this exactly):**

> "It's 11pm. Your dog hasn't eaten all day. You don't know if that's normal or an emergency. Do you wake up your vet? Google it and get 40 contradicting articles? Or do you have something that actually knows your pet's routine and can give you a grounded answer?"

**Then say:**

PawPal+ started as a scheduling app — you register your pets, assign tasks like walks and feedings, and track what's been done. That was Modules 1 through 3. It worked, but it was dumb. It had no opinion. It couldn't answer a question.

The final project adds a layer on top of that: an AI assistant that doesn't just guess — it looks things up first. That's the problem I set out to solve. Not "build a chatbot." Build something that gives **trustworthy** answers when the stakes are real.

---

## 2. THE LOGIC
*~90 seconds | Show the app — Schedule tab first, then AI tab*

---

**Show the Today's Schedule tab and say:**

This is the original system. Two pets — Luna the dog, Mochi the cat. Tasks sorted by priority, conflict detection, auto-recurrence when you mark something done. All rule-based Python. No AI.

**Click to the Ask PawPal AI tab and say:**

This tab is the new layer. When you ask a question, three things happen before Claude ever sees it.

**Walk through the pipeline on your fingers:**

> "One — guardrails. If the query is blank or has nothing to do with pets, it gets blocked right here. No API call is made, no money is spent, no hallucination risk.
>
> Two — retrieval. The system searches a knowledge base of 18 pet care fact chunks using TF-IDF — keyword overlap scored by cosine similarity. It pulls the top three most relevant passages.
>
> Three — generation. Those passages get injected into Claude's prompt as the only source it's allowed to use. The model is told explicitly: do not invent facts outside these passages.
>
> That's RAG — Retrieval Augmented Generation. The retriever is dumb and fast. The generator is smart but constrained. Together they're more reliable than either one alone."

**Type the first prompt and hit Ask:**

> `How often should I feed my adult dog?`

**While it loads, say:**
Watch the confidence badge when it comes back. That's the cosine similarity score from the retriever — not Claude's self-rating, an actual math score based on how well the knowledge base matched the question.

**After it responds, point out:**
High confidence. Source cited. Answer is under 150 words. That's not a coincidence — I capped it in the system prompt.

---

**Type the second prompt:**

> `Is it safe to give my cat ibuprofen for pain?`

**Say:**
This is where it matters. Ibuprofen is toxic to cats. Watch what happens.

**After it responds, say:**
The knowledge base has the `cat-toxins-nsaids` chunk. Retrieval found it. Claude answered correctly and recommended calling a vet. If I had just asked a plain chatbot with no knowledge base, it might have given a hedged answer, or worse, suggested a small dose was okay. Grounding the answer in a curated source is what makes this different.

---

**Type the third prompt:**

> `What is the best recipe for chocolate cake?`

**Say:**
Guardrail. No API call was made. Zero tokens spent. This is why the off-topic filter exists — it's not just a UX decision, it's a cost and safety decision.

---

## 3. THE RELIABILITY
*~75 seconds | Switch to terminal*

---

**Open terminal, navigate to the project folder, and run:**

```
python3 -m pytest tests/test_ai_assistant.py -v
```

**While it runs, say:**
I have 46 automated tests total — 38 for the core scheduling logic, 8 for the AI layer. None of the AI tests make a real API call. They use mocks. That means anyone can clone this repo and run the full test suite without an API key.

**After it finishes (8 passed), say:**

> "8 out of 8. Let me walk through what's actually being verified."

Point at the results one by one:

- `test_blank_query_is_blocked` — guardrail 1 fires, confidence is zero, no API call
- `test_off_topic_query_is_blocked` — guardrail 2 fires on the cake question
- `test_retrieval_finds_relevant_chunk` — the feeding chunk comes back when you ask about dog meals
- `test_confidence_above_threshold_for_direct_match` — 0.34 score for a direct keyword match
- `test_confidence_near_zero_for_unrelated_query` — 0.03 for quantum physics
- `test_api_error_returns_safe_fallback` — connection timeout returns a safe message, not a crash
- `test_result_always_has_required_keys` — blocked results and successful results both have the same structure

**Then say:**
The one thing I cannot automate is whether Claude's answer is *factually correct*. That's evaluated by human review. That gap is documented in the model card.

---

**Flip back to the app and expand the Recent Query Log:**

The log file records every query — timestamp, confidence score, which knowledge base chunks were retrieved, and the first 120 characters of the response. If an answer is ever wrong, I have an exact reproduction path.

---

## 4. THE REFLECTION
*~60 seconds | Just talk — no demo needed*

---

**Say:**

Three things surprised me.

**First:** the confidence scores separated almost too cleanly. Direct keyword matches scored 0.34 to 0.48. Unrelated queries scored 0.02 to 0.03. I expected it to be messier. When I looked more carefully, I realized my test queries were all things I'd written the knowledge base to answer. The thresholds I picked weren't validated — they were circular. That's a bias I built into my own evaluation.

**Second:** the guardrail silenced a medically important question. During manual testing I typed *"Is Tylenol dangerous?"* — no pet words, blocked immediately. The answer is in the knowledge base. The filter optimized for blocking irrelevant content and accidentally blocked a safety-critical one. A keyword list is the wrong tool for intent detection.

**Third:** Claude ignored a direct instruction. The system prompt says *"do not invent facts outside the passages."* Once, when the retrieved context was thin, Claude added a specific dosage claim that wasn't in any chunk. LLMs follow soft constraints probabilistically. The only reliable fix is post-generation fact-checking — which isn't built yet, and that's documented in the model card as a known gap.

**Closing line:**

> "The lesson isn't that AI is unreliable. It's that reliability has to be designed — in the architecture, in the tests, in the guardrails, and in what you're honest about not having solved yet. That's what this project is."

---

## Demo Prompts — Quick Reference

| # | Prompt to type | Expected result |
|---|---|---|
| 1 | `How often should I feed my adult dog?` | HIGH confidence, feeding chunk cited |
| 2 | `Is it safe to give my cat ibuprofen for pain?` | HIGH confidence, toxicity warning |
| 3 | `What is the best recipe for chocolate cake?` | BLOCKED — off-topic guardrail |
| 4 | `My dog hasn't eaten since this morning. Should I be worried?` | MEDIUM confidence, vet referral |

---

## Timing Guide

| Section | Time |
|---|---|
| The Problem | ~60 sec |
| The Logic (demo) | ~90 sec |
| The Reliability (tests) | ~75 sec |
| The Reflection | ~60 sec |
| **Total** | **~5 min** |
