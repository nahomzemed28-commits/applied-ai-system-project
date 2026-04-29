# Model Card — PawPal AI

> Follows the model card format established by Mitchell et al. (2019), adapted for a course project.

---

## Model / System Description

**System name:** PawPal AI  
**Base project:** PawPal+ (Modules 1–3) — a rule-based pet care scheduling system built in Python and Streamlit  
**AI technique:** Retrieval-Augmented Generation (RAG)  
**Language model:** Claude Haiku (`claude-haiku-4-5-20251001`) via the Anthropic API  
**Retrieval method:** TF-IDF cosine similarity (`scikit-learn`) over a local JSON knowledge base (18 fact chunks)  
**Version:** Final project submission — April 2026

PawPal AI extends the original PawPal+ scheduler by adding an AI assistant that answers pet care questions. Before generating any response, the system retrieves the most relevant passages from a curated knowledge base and injects them as context into the Claude prompt. Answers are grounded in those passages; the model is instructed not to invent facts outside them.

---

## Intended Use

**Primary users:** Pet owners using the PawPal+ Streamlit app  
**Primary use cases:**
- General pet care questions (feeding schedules, grooming frequency, exercise needs)
- Medication safety questions (what is toxic to cats/dogs)
- Health monitoring guidance (when to call a vet vs. wait)

**This system is NOT intended for:**
- Emergency triage or diagnosis — always call a vet or poison control in an emergency
- Replacing professional veterinary advice
- Species outside the knowledge base (exotic pets, livestock, wildlife)
- Questions requiring knowledge of an individual animal's health history

---

## AI Features

| Feature | Implementation |
|---|---|
| Retrieval-Augmented Generation | TF-IDF retriever selects top-3 relevant KB chunks before every API call |
| Confidence scoring | Cosine similarity of top retrieved chunk → high / medium / low label |
| Input guardrails | Blank-query check + pet-term keyword filter block off-topic and empty inputs |
| Structured logging | Every query, confidence score, source IDs, and response preview written to `logs/ai_queries.log` |
| Error handling | All API calls wrapped in try/except; failures return a safe fallback message |

---

## Training Data and Knowledge Base

The language model (Claude Haiku) was trained by Anthropic on a large corpus of internet text and is not fine-tuned for this project. No custom training was performed.

The **knowledge base** (`knowledge_base/pet_care_facts.json`) consists of 18 manually written fact chunks covering:

| Topic | Chunks |
|---|---|
| Feeding (dogs and cats) | 4 |
| Medications and toxins | 3 |
| Health symptoms and emergencies | 4 |
| Exercise | 2 |
| Grooming | 2 |
| Dental care and hydration | 2 |
| Vaccines | 2 |

**Knowledge base bias:** All chunks reflect general North American veterinary guidelines as of 2026. Regional variation, breed-specific differences, and individual animal health factors are not represented. The knowledge base was written by one person during a 2-week project — it has not been peer-reviewed by a licensed veterinarian.

---

## Evaluation and Testing Results

### Automated tests — 46 / 46 passing (`python3 -m pytest -v`)

**AI-specific tests (8):**

| Test | Result | What it proves |
|---|---|---|
| Blank query blocked | PASS | Guardrail 1 fires before any API call |
| Off-topic query blocked | PASS | Guardrail 2 filters non-pet questions |
| Pet query passes guardrail | PASS | Legitimate questions reach the RAG pipeline |
| Retrieval finds relevant chunk | PASS | TF-IDF returns the correct chunk for a feeding question |
| Confidence ≥ 0.10 for direct match | PASS | Score: 0.34 for "ibuprofen toxic cats kidney" |
| Confidence < 0.10 for unrelated query | PASS | Score: 0.03 for "quantum entanglement photon spin" |
| API error returns safe fallback | PASS | No crash on connection timeout; error field populated |
| Result always has required keys | PASS | All 6 keys present in both blocked and OK results |

**Confidence score distribution (observed during manual testing):**

| Query type | Avg. confidence | Label |
|---|---|---|
| Direct keyword match (e.g., "ibuprofen cats") | 0.34–0.48 | High |
| Topical match (e.g., "how often feed dog") | 0.12–0.28 | Medium |
| Paraphrase with no shared terms | 0.02–0.07 | Low |
| Off-topic (blocked before retrieval) | 0.00 | n/a |

**Summary:** 8 / 8 AI tests passed. Confidence scores reliably distinguish high-relevance from low-relevance retrievals. The main unverified dimension is factual accuracy of Claude's generated answers — this is evaluated by human review only.

---

## Limitations and Biases

### 1. Knowledge base is narrow and unreviewed
18 chunks written by one person, not peer-reviewed by a vet. Missing topics include exotic pets, senior animal care, breed-specific needs, and post-surgical recovery. The system will silently give generic answers for topics that fall outside the coverage.

### 2. TF-IDF cannot handle paraphrases
A user who asks "my cat won't eat" will not retrieve the `appetite-loss-cats` chunk because the keyword overlap is near zero. The retriever needs matching vocabulary, not matching intent. Vector-embedding-based retrieval (e.g., `sentence-transformers`) would fix this but adds latency and model dependencies.

### 3. Keyword guardrail causes false negatives
The off-topic filter blocks queries that contain no recognized pet terms. "Is Tylenol dangerous?" gets blocked even though the answer (yes, it is toxic to both cats and dogs) is in the knowledge base. Pet-adjacent questions that use medical vocabulary instead of pet vocabulary are silenced.

### 4. Claude ignores "no invention" instruction probabilistically
The system prompt tells Claude not to invent facts outside the provided passages. During manual testing, Claude once added a specific dosage claim not present in any retrieved chunk. LLMs follow soft constraints probabilistically — the instruction reduces hallucination but does not eliminate it. A post-generation fact-check against the knowledge base would be needed to close this gap.

### 5. No emergency intercept
The system lacks a hard-coded response for genuine emergencies (suspected poisoning, seizures, difficulty breathing). A user in a real emergency who types "my dog ate chocolate" should see the ASPCA poison control number (888-426-4435) instantly, not wait for retrieval and generation.

---

## Ethical Considerations

**Health stakes are real.** Pet care advice can affect animal health and welfare. Incorrect dosage information, missed emergency symptoms, or misidentified toxins could cause harm. This system mitigates — but does not eliminate — that risk through knowledge-base grounding and vet-referral prompts in every low-confidence response.

**The system should not be the last line of defense.** It is designed as a convenience tool for a pet owner who wants a quick answer at 11pm, not as a substitute for a licensed veterinarian. The README, the UI, and every low-confidence response communicate this explicitly.

**No personal data is stored.** Queries are logged to a local file (`logs/ai_queries.log`) and are never transmitted to any third party beyond the Anthropic API. The Anthropic API processes queries according to Anthropic's data use policies.

---

## AI Collaboration Notes

### One instance where AI gave a helpful suggestion

During the UI design phase, I described the confidence scoring system and asked whether to display the raw cosine similarity score or something else. The AI suggested converting the float into a labeled tier (high / medium / low) displayed alongside the number. Its reasoning: a raw decimal like "0.23" is not interpretable by a non-technical user without context. A labeled tier makes uncertainty legible at a glance without hiding the underlying number for users who want it.

This was genuinely useful — it addressed a real usability problem I hadn't thought about, and the suggestion mapped directly onto a clean implementation (`_confidence_label()` in `ai_assistant.py`). The labeled confidence badge in the Streamlit UI shipped exactly as suggested.

### One instance where AI gave a flawed or incorrect suggestion

When designing the off-topic guardrail, I asked for approaches to detect non-pet-related queries. The AI suggested using a second Claude API call — a classifier prompt like "Is this question related to pet care? Answer yes or no." — to gate each query before the main pipeline.

This is architecturally backwards. The entire purpose of a guardrail is to avoid unnecessary API calls. Using one API call to decide whether to make another API call doubles cost and latency, and adds a new failure mode (what happens if the classifier call fails?). The suggestion was technically valid — it would work — but it ignored the constraint that motivated the guardrail in the first place.

The correct solution (a keyword intersection check that runs in microseconds with no external dependency) requires understanding *why* you're adding the guardrail, not just *what* it needs to do. The AI optimized for "does it work" without reasoning about "what problem is it solving." I rejected the suggestion and built the keyword filter instead.

**Lesson:** AI suggestions are most dangerous when they are technically correct but solve the wrong problem. Evaluating a suggestion requires knowing the full set of constraints — cost, latency, failure modes, and design intent — not just whether the code would run.

---

## Citation

Mitchell, M., Wu, S., Zaldivar, A., Barnes, P., Vasserman, L., Hutchinson, B., Spitzer, E., Raji, I. D., & Gebru, T. (2019). Model cards for model reporting. *Proceedings of the conference on fairness, accountability, and transparency*, 220–229.
