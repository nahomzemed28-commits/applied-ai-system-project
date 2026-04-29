# Ethics & Responsibility Reflection — PawPal AI

## Limitations and Biases

**The knowledge base reflects one perspective.**
The 18 fact chunks in `pet_care_facts.json` were written by hand during this project. They represent general North American veterinary guidelines, but pet care recommendations vary by region, breed, individual animal health history, and evolving research. A dog owner in a country with different vaccination laws or dietary norms would get advice that doesn't apply to them. The system has no way to signal this.

**TF-IDF retrieval fails on paraphrases.**
The retriever matches keywords, not meaning. A user who asks "my cat won't touch her bowl" won't retrieve the `appetite-loss-cats` chunk because none of those exact words appear in it. The system will either retrieve a weakly-related chunk and produce a low-confidence answer, or retrieve nothing and tell Claude there are no matches — leaving the user without the relevant information even though it exists in the knowledge base. This is a structural gap, not an edge case.

**The guardrail keyword list is coarse.**
The off-topic filter blocks any query with no pet-related words. This means a question like "Is Tylenol dangerous?" gets blocked even though the answer (yes, to both cats and dogs) is in the knowledge base and highly relevant to a pet owner. The filter is too blunt — it optimizes for blocking clearly off-topic questions but sacrifices borderline-useful ones.

**Claude's language can sound more certain than the retrieval confidence warrants.**
Even when the confidence score is "low" (< 0.10), Claude generates fluent, confident-sounding prose. A user who doesn't notice the small confidence badge in the UI may treat a poorly-grounded answer the same as a well-grounded one. The system tries to address this with a warning banner for low-confidence responses, but the mismatch between retrieval uncertainty and output fluency is a fundamental limitation of any RAG system using large language models.

---

## Could This AI Be Misused?

**The most realistic misuse is substituting this tool for a vet in an emergency.**
A user whose dog ate chocolate might ask PawPal AI instead of calling poison control or an emergency vet. The knowledge base does contain the `dog-toxins-common` chunk and the `emergency-symptoms-pets` chunk, so the system would likely return an answer that mentions calling a vet — but there is no guarantee the system will always respond fast enough, retrieve the right chunk, or phrase the urgency clearly enough.

**Prevention measures built into the current system:**
- Every low-confidence response displays: *"Consult your vet for authoritative advice."*
- The system prompt instructs Claude to recommend consulting a vet when passages are insufficient.
- The knowledge base is presented as context, not diagnosis — Claude is told not to invent facts outside the passages.

**What is not yet built but should be:**
A hard-coded emergency intercept: if the query contains words like "ate," "poison," "not breathing," "seizure," or "collapsed," the system should skip the RAG pipeline entirely and display the ASPCA poison control number (888-426-4435) and a prompt to go to an emergency vet immediately. Retrieval-based answers are too slow and too uncertain for true emergencies.

---

## What Surprised Me During Testing

**The confidence scores separated cleanly — almost too cleanly.**
I expected TF-IDF confidence to be noisy, but queries that directly used vocabulary from the knowledge base (e.g., "ibuprofen toxic cats kidney") scored 0.34–0.48, while genuinely unrelated queries scored 0.00–0.03. There was almost no middle ground in the test cases. This made me realize the threshold values I chose (0.10 and 0.25) may have been validated by the test cases I designed rather than by truly challenging edge-case queries.

**The off-topic filter blocked a medically relevant question.**
During manual testing, I typed: "Is it safe to give Tylenol to my pet?" The word "Tylenol" is not in `_PET_TERMS`, and "safe" and "give" aren't either — so the guardrail blocked the query before retrieval even ran. The knowledge base has the answer (`vet-only-medications` chunk explicitly covers acetaminophen toxicity). The filter created a false negative where a safety-critical question was silenced. I added "toxic" and "medication" to the keyword list as a partial fix, but the deeper lesson is that a keyword blocklist is the wrong tool for semantic intent detection.

**Claude ignored the "don't invent facts" instruction in one case.**
When the retrieved context was thin (one weakly-matched chunk), Claude once added a specific claim about "giving no more than one small dental chew per day" — a detail that does not appear anywhere in `pet_care_facts.json`. The system prompt says *"Do not invent facts not present in the passages,"* but the model did anyway. This is a known property of instruction-tuned LLMs: they follow soft constraints probabilistically, not absolutely. The only reliable fix is post-generation fact-checking against the knowledge base, which is not currently implemented.

---

## AI Collaboration During This Project

### One helpful suggestion

When designing the confidence scoring system, I initially planned to expose the raw cosine similarity score directly (e.g., "confidence: 0.23"). Claude suggested converting the raw float into a labeled tier — high / medium / low — and displaying that alongside the number. The reasoning it gave was that a raw decimal is difficult for a non-technical user to interpret: does 0.23 mean the answer is good or bad? A labeled tier makes the uncertainty legible at a glance, while the raw number is still available for anyone who wants it. This was a genuinely good UX insight that I hadn't considered, and it's the design that shipped.

### One flawed suggestion

During the guardrail design phase, I asked Claude how to detect off-topic queries efficiently. It suggested using another Claude API call with a classifier prompt — something like: *"Is the following question related to pet care? Answer yes or no."* — and blocking the query if the answer was "no."

This is architecturally backward. The entire purpose of the guardrail is to prevent unnecessary API calls; using an API call to decide whether to make an API call defeats that purpose entirely. It also adds latency, cost, and a new failure mode (what if the classifier call fails?). I rejected this suggestion and kept the keyword-intersection approach, which runs in microseconds with no external dependency. The flaw wasn't that Claude's suggestion was technically wrong — a classifier prompt would work — it was that Claude didn't reason about the constraint (cost/latency) that made the keyword approach the right tradeoff for this specific problem. Knowing *why* you're making a design choice matters as much as knowing *what* the options are.
