"""RAG-based pet care AI assistant with confidence scoring, logging, and input guardrails."""

import json
import logging
import os
import re
from pathlib import Path

KNOWLEDGE_BASE_PATH = Path(__file__).parent / "knowledge_base" / "pet_care_facts.json"
LOG_DIR = Path(__file__).parent / "logs"

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    filename=LOG_DIR / "ai_queries.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_log = logging.getLogger(__name__)

# ── Confidence thresholds ─────────────────────────────────────────────────────
_HIGH_THRESHOLD = 0.25
_MED_THRESHOLD  = 0.10

# ── Off-topic guard ───────────────────────────────────────────────────────────
_PET_TERMS = {
    "dog", "dogs", "cat", "cats", "pet", "pets", "animal", "animals",
    "puppy", "puppies", "kitten", "kittens", "bird", "rabbit", "hamster", "fish", "reptile",
    "feed", "feeding", "food", "meal", "meals", "diet", "nutrition", "portion",
    "walk", "walks", "exercise", "play", "groom", "grooming", "brush", "brushing",
    "vet", "veterinarian", "medication", "medicine", "dose", "dosage", "drug",
    "vaccine", "vaccination", "flea", "tick", "parasite", "dental", "teeth", "tooth",
    "health", "sick", "illness", "symptom", "pain", "injury", "allergy",
    "fur", "coat", "nail", "nails", "ear", "ears", "eye", "eyes",
    "water", "hydration", "weight", "obesity", "breed", "ibuprofen", "toxic",
}


def _confidence_label(score: float) -> str:
    if score >= _HIGH_THRESHOLD:
        return "high"
    if score >= _MED_THRESHOLD:
        return "medium"
    return "low"


def _blocked(message: str) -> dict:
    return {
        "answer": message,
        "confidence": 0.0,
        "confidence_label": "n/a",
        "sources": [],
        "blocked": True,
        "error": None,
    }


class PetCareAssistant:
    """Retrieval-Augmented Generation assistant for pet care questions.

    Pipeline: query → guardrails → TF-IDF retrieval → Claude API → structured result.
    Every query (including blocked ones) is written to logs/ai_queries.log.
    """

    def __init__(
        self,
        kb_path: Path = KNOWLEDGE_BASE_PATH,
        model: str = "claude-haiku-4-5-20251001",
    ):
        self._model = model
        self._chunks = self._load_kb(kb_path)
        self._vectorizer, self._matrix = self._build_index()

    # ── Knowledge base ────────────────────────────────────────────────────────

    def _load_kb(self, path: Path) -> list[dict]:
        if not path.exists():
            _log.warning("KB_MISSING | path=%s", path)
            return []
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)

    def _build_index(self):
        if not self._chunks:
            return None, None
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            texts = [c["text"] for c in self._chunks]
            vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
            mat = vec.fit_transform(texts)
            return vec, mat
        except ImportError:
            _log.error("IMPORT_ERROR | sklearn not installed — retrieval disabled")
            return None, None

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def retrieve(self, query: str, top_k: int = 3) -> tuple[list[dict], float]:
        """Return (top_k matching chunks, best cosine-similarity confidence score)."""
        if self._vectorizer is None:
            return [], 0.0
        from sklearn.metrics.pairwise import cosine_similarity
        q_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(q_vec, self._matrix)[0]
        top_idx = scores.argsort()[-top_k:][::-1]
        best = float(scores[top_idx[0]])
        chunks = [
            {**self._chunks[i], "score": float(scores[i])}
            for i in top_idx
            if scores[i] > 0.0
        ]
        return chunks, best

    # ── Guardrails ────────────────────────────────────────────────────────────

    @staticmethod
    def _is_pet_related(query: str) -> bool:
        words = set(re.findall(r"\b\w+\b", query.lower()))
        return bool(words & _PET_TERMS)

    # ── Main entry point ──────────────────────────────────────────────────────

    def answer(self, query: str) -> dict:
        """Run the full RAG pipeline. Returns a dict with answer, confidence, sources, and metadata."""
        query = query.strip()

        # Guardrail 1 — blank query
        if not query:
            _log.info("BLOCKED | reason=blank_query")
            return _blocked("Please enter a question.")

        # Guardrail 2 — off-topic
        if not self._is_pet_related(query):
            _log.info("BLOCKED | reason=off_topic | query=%r", query)
            return _blocked(
                "I can only help with pet care questions — try asking about "
                "feeding schedules, health symptoms, medications, or grooming."
            )

        # Retrieval
        chunks, confidence = self.retrieve(query)
        conf_label = _confidence_label(confidence)

        context = (
            "\n\n".join(
                f"[Source {i+1} — {c.get('id', '?')}]\n{c['text']}"
                for i, c in enumerate(chunks)
            )
            if chunks
            else "No specific knowledge base entries matched this query."
        )
        source_ids = [c.get("id", f"chunk-{i}") for i, c in enumerate(chunks)]

        # Claude API call
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            response = client.messages.create(
                model=self._model,
                max_tokens=400,
                system=(
                    "You are PawPal AI, a helpful pet care assistant. "
                    "Answer ONLY using the provided knowledge base passages. "
                    "If the passages lack sufficient detail, say so and recommend consulting a vet. "
                    "Be practical and specific. Keep answers under 150 words. "
                    "Do not invent facts not present in the passages."
                ),
                messages=[{
                    "role": "user",
                    "content": f"Knowledge base passages:\n{context}\n\nQuestion: {query}",
                }],
            )
            answer_text = response.content[0].text
            _log.info(
                "OK | confidence=%.3f (%s) | sources=%s | query=%r | preview=%r",
                confidence, conf_label, source_ids, query, answer_text[:120],
            )
            return {
                "answer": answer_text,
                "confidence": round(confidence, 3),
                "confidence_label": conf_label,
                "sources": source_ids,
                "blocked": False,
                "error": None,
            }

        except Exception as exc:
            _log.error("API_ERROR | query=%r | error=%s", query, exc)
            return {
                "answer": "The AI service is temporarily unavailable. Please try again shortly.",
                "confidence": round(confidence, 3),
                "confidence_label": conf_label,
                "sources": source_ids,
                "blocked": False,
                "error": str(exc),
            }
