import re
from typing import Iterable


# Phrases that explicitly ask Hailey to search or look something up.
_EXPLICIT_SEARCH = (
    "zoek op internet", "zoek op het internet", "zoek online", "zoek op",
    "zoek even", "zoek voor me", "zoek voor mij", "kun je zoeken",
    "kan je zoeken", "zoek uit", "zoek dit op", "zoek informatie",
    "opzoeken", "internet", "online opzoeken", "look up", "search online",
    "search the web", "search for", "google", "find online",
)

# Signals that the answer depends on changing or current information.
_FRESHNESS = (
    "vandaag", "gisteren", "morgen", "deze week", "deze maand",
    "momenteel", "op dit moment", "nu", "actueel", "recent", "recente",
    "nieuwste", "laatste", "huidige", "huidig", "2026", "2025",
    "today", "yesterday", "tomorrow", "this week", "this month",
    "currently", "right now", "latest", "newest", "recent", "current",
    "this year", "2026", "2025",
)

# Topics where freshness/source verification is commonly useful.
_LOOKUP_TOPICS = (
    "prijs", "prijzen", "kosten", "kost het", "beschikbaar", "openingstijden",
    "openingstijd", "reviews", "review", "beoordelingen", "nieuws",
    "release", "uitgebracht", "uitgave", "update", "versie", "specificaties",
    "vergelijk", "vergelijken", "beste", "aanbieding", "voorraad",
    "weather", "price", "prices", "cost", "availability", "opening hours",
    "reviews", "news", "release", "released", "update", "version",
    "specifications", "compare", "comparison", "best", "deal",
)

_URL_RE = re.compile(r"https?://", re.IGNORECASE)


def should_search(message: str) -> bool:
    """Return True when a message likely needs live web information."""
    if not message or not message.strip():
        return False

    text = " ".join(message.lower().split())

    if _URL_RE.search(text):
        return True

    if any(phrase in text for phrase in _EXPLICIT_SEARCH):
        return True

    has_freshness = any(term in text for term in _FRESHNESS)
    has_lookup_topic = any(term in text for term in _LOOKUP_TOPICS)

    # Require a question or lookup topic to avoid searching casual mentions
    # of words such as "nu" or "best".
    looks_like_question = "?" in text or text.startswith(
        ("wat ", "wie ", "waar ", "wanneer ", "welke ", "hoe ", "is ", "zijn ",
         "what ", "who ", "where ", "when ", "which ", "how ", "is ", "are ")
    )

    return (has_freshness and (looks_like_question or has_lookup_topic)) or (
        has_lookup_topic and looks_like_question
    )


def explain_search_decision(message: str) -> str:
    """Small diagnostic helper useful while testing."""
    return "web search" if should_search(message) else "normal chat"
