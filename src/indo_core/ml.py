"""Local ML: detect what a post is about and pull facts out of the event material.

Everything runs offline in pure Python:
- classify(): multinomial Naive Bayes over word unigrams and bigrams, trained on
  training_data.py when first used.
- extract_facts(): rules for event name, rank, prize, organiser, team and tech.
- key_sentences(): extractive summary scored by graph message passing over a
  sentence-entity graph (sentences are copied, never invented).
- voice_profile(): style statistics from the user's past posts.
"""

import math
import re
from collections import Counter
from functools import lru_cache

from .training_data import EXAMPLES, LABELS

MIN_CONFIDENCE = 0.35

STOPWORDS = set("""
a an and are as at be been but by for from has have i in is it its me my of on or our so that the
their them this to was we were with you your will just very am about into over after before
""".split())

EVENT_WORDS = (r"hackathon|hack|ideathon|buildathon|summit|conference|conf|workshop|bootcamp|meetup|"
               r"fest|expo|symposium|webinar|challenge|community day|day|days|i/o|summer school|program|programme")
EVENT_RE = re.compile(
    r"((?:(?:[A-Z][\w&'.:-]*|[A-Z0-9]{2,}|\d{4})[ \t]+){1,5})((?i:" + EVENT_WORDS + r"))\b(?:[ \t]+(\d{4}))?")
RANK_RE = re.compile(
    r"\b((?:first|second|third|1st|2nd|3rd|\d+th)\s+(?:place|prize|position|runner[- ]up)|runners?[- ]up|"
    r"winners?|finalists?|top\s+\d+)\b", re.I)
PRIZE_RE = re.compile(r"(?:[₹$€£]\s?|\b(?:rs\.?|inr|usd)\s?)\d[\d,]*(?:\.\d+)?(?:\s?(?:k|lakhs?|crore|l)\b)?", re.I)
ORGANISER_RE = re.compile(
    r"\b(?:organi[sz]ed|hosted|conducted|run|powered)\s+by\s+((?:[A-Z][\w&'.-]*|of|the|and)(?:[ \t]+(?:[A-Z][\w&'.-]*|of|and)){0,7})")
TEAM_RE = re.compile(r"\b[Tt]eam[ \t]+[\"“']?([A-Z][\w-]*(?:[ \t]+[A-Z][\w-]*){0,2})")
TECH = ["AWS", "Lambda", "DynamoDB", "S3", "Azure", "GCP", "Google Cloud", "Python", "Java", "JavaScript",
        "TypeScript", "React", "Node.js", "Rust", "Docker", "Kubernetes", "Terraform", "Serverless",
        "GenAI", "Generative AI", "Machine Learning", "Deep Learning", "AI", "LLM", "Data Science",
        "Cybersecurity", "Security", "DevOps", "Flutter", "Android", "Linux", "Open Source", "Blockchain"]
TECH_ALIASES = {"Generative AI": "GenAI"}
_TECH_RES = [(t, re.compile(r"(?<![\w.])" + re.escape(t) + r"(?![\w])", re.I if len(t) > 3 else 0)) for t in TECH]
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
BOILERPLATE = re.compile(r"https?://|www\.|cookie|privacy|register now|sign up|log ?in|copyright|©|all rights", re.I)
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


def tokens(text):
    words = [w for w in re.findall(r"[a-z0-9+#]+", text.lower()) if w not in STOPWORDS]
    return words + [f"{a}_{b}" for a, b in zip(words, words[1:])]


class NaiveBayes:
    """Multinomial Naive Bayes with Laplace smoothing."""

    def __init__(self, examples):
        self.counts = {label: Counter(t for text in texts for t in tokens(text)) for label, texts in examples.items()}
        self.totals = {label: sum(c.values()) for label, c in self.counts.items()}
        self.vocab = set().union(*self.counts.values())
        n = sum(len(texts) for texts in examples.values())
        self.prior = {label: math.log(len(texts) / n) for label, texts in examples.items()}

    def predict_proba(self, text):
        toks = [t for t in tokens(text) if t in self.vocab]
        v = len(self.vocab)
        scores = {}
        for label, counts in self.counts.items():
            denom = math.log(self.totals[label] + v)
            scores[label] = self.prior[label] + sum(math.log(counts[t] + 1) - denom for t in toks)
        top = max(scores.values())
        exp = {label: math.exp(s - top) for label, s in scores.items()}
        total = sum(exp.values())
        return {label: e / total for label, e in sorted(exp.items(), key=lambda kv: -kv[1])}


@lru_cache(maxsize=1)
def model():
    return NaiveBayes(EXAMPLES)


def classify(text):
    """Return (label, confidence). Low-confidence guesses fall back to 'general'."""
    proba = model().predict_proba(text)
    label, conf = next(iter(proba.items()))
    if conf < MIN_CONFIDENCE:
        return "general", proba.get("general", 0.0)
    return label, conf


def label_name(label):
    return LABELS[label]


def _event_name(text):
    for m in EVENT_RE.finditer(text):
        words = m.group(1).split()
        while words and words[0].lower() in ("the", "a", "an", "at", "in", "of", "our", "my", "i", "we"):
            words.pop(0)
        if words:
            return " ".join(words + [m.group(2)] + ([m.group(3)] if m.group(3) else []))
    return None


def extract_facts(topic, event_text):
    """Facts found in the user's own words first, then in the event material."""
    material = event_text or ""
    both = f"{topic}\n{material}"
    rank = RANK_RE.search(topic) or RANK_RE.search(material)
    prize = PRIZE_RE.search(topic) or PRIZE_RE.search(material)
    organiser = ORGANISER_RE.search(both)
    team = TEAM_RE.search(both)
    tech = list(dict.fromkeys(TECH_ALIASES.get(t, t) for t, rx in _TECH_RES if rx.search(both)))
    # Keep the most specific term: drop "AI" when "GenAI" or "Generative AI" was found.
    tech = [t for t in tech if not any(t != o and t.lower() in o.lower() for o in tech)]
    return {
        "event": _event_name(topic) or _event_name(material),
        "rank": rank.group(1) if rank else None,
        "prize": prize.group(0).strip() if prize else None,
        "organiser": organiser.group(1).strip().rstrip(".,") if organiser else None,
        "team": team.group(1) if team else None,
        "tech": tech[:6],
    }


# Graph scoring. Node features: [topic relevance, position prior, length quality, entity density].
# These weights are fixed by hand, not learned: this is GCN-style message passing
# (normalised adjacency, ReLU, a fixed linear map per round), not a trained network.
GRAPH_ROUNDS = 3
GRAPH_W = [[0.9, 0.0, 0.0, 0.3],
           [0.0, 0.8, 0.0, 0.0],
           [0.0, 0.0, 0.6, 0.0],
           [0.3, 0.0, 0.0, 0.9]]
GRAPH_READOUT = [1.0, 0.4, 0.3, 0.6]
MAX_GRAPH_SENTENCES = 120


def _content_words(text):
    return {w for w in tokens(text) if "_" not in w}


def _normalised_adjacency(weights):
    """D^-1/2 (A + I) D^-1/2, the propagation rule of a graph convolutional network."""
    n = len(weights)
    a = [[weights[i][j] + (1.0 if i == j else 0.0) for j in range(n)] for i in range(n)]
    inv_sqrt = [1 / math.sqrt(sum(row)) for row in a]
    return [[a[i][j] * inv_sqrt[i] * inv_sqrt[j] for j in range(n)] for i in range(n)]


def propagate(adjacency, features, weights=GRAPH_W, rounds=GRAPH_ROUNDS):
    """Run `rounds` of H <- ReLU(A_hat H W). Returns the final node features."""
    h = features
    dim = len(weights[0])
    for _ in range(rounds):
        mixed = [[sum(a_ij * h[j][k] for j, a_ij in enumerate(row) if a_ij) for k in range(len(h[0]))] for row in adjacency]
        h = [[max(0.0, sum(x[k] * weights[k][c] for k in range(len(x)))) for c in range(dim)] for x in mixed]
    return h


def sentence_graph(topic, sentences, entities):
    """Nodes: one topic node, the sentences, then the entities.

    Sentence-sentence edges are weighted by token overlap (Jaccard); sentence-topic
    edges by overlap with the topic; sentence-entity edges link a sentence to each
    entity it mentions, so sentences that share entities are two hops apart.
    """
    topic_words = _content_words(topic)
    words = [_content_words(s) for s in sentences]
    ents = [e for e in dict.fromkeys(entities) if e and any(e.lower() in s.lower() for s in sentences)]
    n_s = len(sentences)
    n = 1 + n_s + len(ents)
    w = [[0.0] * n for _ in range(n)]
    mentions = [[e for e in ents if e.lower() in s.lower()] for s in sentences]
    peak_mentions = max((len(m) for m in mentions), default=0) or 1
    features = [[1.0, 0.0, 0.0, 0.0]]
    for i, s in enumerate(sentences):
        rel = len(words[i] & topic_words) / (len(topic_words) or 1)
        length_quality = 1.0 - abs(len(s.split()) - 22) / 40
        features.append([rel, 1 / (1 + 0.05 * i), max(0.0, length_quality), len(mentions[i]) / peak_mentions])
        w[0][1 + i] = w[1 + i][0] = rel
        for j in range(i + 1, n_s):
            union = words[i] | words[j]
            overlap = len(words[i] & words[j]) / len(union) if union else 0.0
            w[1 + i][1 + j] = w[1 + j][1 + i] = overlap
        for e in mentions[i]:
            k = 1 + n_s + ents.index(e)
            w[1 + i][k] = w[k][1 + i] = 1.0
    features += [[0.5, 0.0, 0.0, 1.0] for _ in ents]
    return _normalised_adjacency(w), features


def key_sentences(topic, event_text, limit=3, entities=()):
    """Pick the most informative sentences of the event material, in original order."""
    if not event_text:
        return []
    sentences = [" ".join(s.split()) for s in SENTENCE_SPLIT.split(event_text)]
    topic_norm = topic.lower()
    candidates = [s for s in sentences
                  if 40 <= len(s) <= 260 and len(s.split()) >= 6 and not BOILERPLATE.search(s)
                  and sum(c.isupper() for c in s) < len(s) / 2 and s.lower() not in topic_norm]
    candidates = list(dict.fromkeys(candidates))[:MAX_GRAPH_SENTENCES]
    if not candidates:
        return []
    adjacency, features = sentence_graph(topic, candidates, entities)
    final = propagate(adjacency, features)
    scores = [sum(r * x for r, x in zip(GRAPH_READOUT, final[1 + i])) + sum(r * x for r, x in zip(GRAPH_READOUT, features[1 + i]))
              for i in range(len(candidates))]
    # Greedy pick by score, skipping sentences that only restate the topic and
    # extracted facts, or repeat a sentence already picked.
    known = _content_words(" ".join([topic, *entities]))
    best = []
    for i in sorted(range(len(candidates)), key=lambda i: (-scores[i], i)):
        words = _content_words(candidates[i])
        if words and len(words - known) / len(words) < 0.3:
            continue
        if any(len(words & _content_words(candidates[j])) / len(words | _content_words(candidates[j])) > 0.5 for j in best):
            continue
        best.append(i)
        if len(best) == limit:
            break
    return [candidates[i] if candidates[i][-1] in ".!?" else candidates[i] + "." for i in sorted(best)]


def voice_profile(samples):
    """Style statistics from past posts. Neutral defaults when there are none."""
    if not samples:
        return {"emoji": False, "hashtags": 3, "length": 0, "exclaim": True}
    words = [len(s.split()) for s in samples]
    hashtags = [len(re.findall(r"(?<!\w)#\w+", s)) for s in samples]
    exclaims = sum(s.count("!") for s in samples)
    avg_words = sum(words) / len(words)
    return {
        "emoji": sum(bool(EMOJI_RE.search(s)) for s in samples) * 2 >= len(samples),
        "hashtags": max(0, min(4, round(sum(hashtags) / len(hashtags)))),
        "length": -1 if avg_words < 60 else (1 if avg_words > 180 else 0),
        "exclaim": exclaims > 0,
    }


def analyse(topic, event_text, post_text=None):
    """Everything the writer needs, as plain JSON-safe data."""
    text = post_text if post_text else f"{topic} {topic} {topic} {(event_text or '')[:2000]}"
    label, conf = classify(text)
    facts = extract_facts(topic, event_text)
    entities = [facts[k] for k in ("event", "organiser", "team", "rank") if facts[k]] + facts["tech"]
    return {
        "category": label,
        "confidence": round(conf, 2),
        "facts": facts,
        "highlights": key_sentences(topic, event_text, entities=entities),
    }
