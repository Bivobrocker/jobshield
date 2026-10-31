
import re
from html import unescape
from html.parser import HTMLParser


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def get_text(self):
        return " ".join(self.parts)


STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "to", "of",
    "in", "on", "for", "with", "at", "by", "from",
    "is", "are", "was", "were", "be", "as", "this",
    "that", "we", "you", "our", "your", "will", "can",
    "have", "has", "their", "they", "it", "job"
}


def normalize_text(text):
    text = unescape(text or "")

    parser = HTMLTextExtractor()
    parser.feed(text)

    text = " ".join(parser.parts).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def get_keywords(text):
    return {
        word for word in text.split()
        if len(word) > 2 and word not in STOP_WORDS
    }


def compare_job_descriptions(
    submitted_description,
    official_description
):
    if not submitted_description or not official_description:
        return {
            "status": "UNABLE_TO_COMPARE",
            "similarity": None,
            "finding": "One or both job descriptions are unavailable."
        }

    submitted = normalize_text(submitted_description)
    official = normalize_text(official_description)

    submitted_words = get_keywords(submitted)
    official_words = get_keywords(official)

    # Avoid unreliable comparisons with short messages
    if len(submitted_words) < 20 or len(official_words) < 20:
        return {
            "status": "INSUFFICIENT_DATA",
            "similarity": None,
            "finding": (
                "Not enough meaningful description text "
                "to perform a reliable comparison."
            )
        }

    common_words = submitted_words.intersection(official_words)

    # Measures how much of the submitted description
    # is covered by the official listing.
    similarity = len(common_words) / len(submitted_words)

    similarity_percent = round(similarity * 100, 2)

    if similarity >= 0.70:
        status = "STRONG_MATCH"
        finding = (
            "Most submitted job-description keywords "
            "are present in the official listing."
        )

    elif similarity >= 0.40:
        status = "PARTIAL_MATCH"
        finding = (
            "Some submitted job-description keywords "
            "match the official listing."
        )

    else:
        status = "LOW_MATCH"
        finding = (
            "Submitted job-description keywords differ "
            "significantly from the official listing."
        )

    return {
        "status": status,
        "similarity": similarity_percent,
        "finding": finding
    }
