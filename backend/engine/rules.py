import re
from datetime import datetime, timezone


def detect_text_red_flags(job_text: str):
    text = (job_text or "").lower()
    evidence = []
    recommendations = []

    # Split into sentences and contrast clauses so that a denial in one
    # sentence does not hide a suspicious request in another.
    sentences = [
        part.strip()
        for part in re.split(
            r"[.!?;\n]+|\b(?:but|however|although|nevertheless)\b",
            text,
            flags=re.IGNORECASE,
        )
        if part.strip()
    ]

    rules = [
        {
            "category": "UPFRONT_PAYMENT",
            "patterns": [
                # "pay a refundable registration and security deposit"
                r"\b(?:pay|transfer|send|deposit|submit|make)\b.{0,100}\b"
                r"(?:registration|processing|interview|security|training|application|recruitment)"
                r"\b.{0,45}\b(?:fee|fees|deposit|payment|charge)\b",

                # "refundable security deposit of ₹1,500"
                r"\b(?:refundable|non-refundable)\b.{0,45}\b"
                r"(?:registration|processing|interview|security|training|application|recruitment)"
                r"\b.{0,35}\b(?:fee|fees|deposit|payment|charge)\b",

                # "registration fee is mandatory / required"
                r"\b(?:registration|processing|interview|security|training|application|recruitment)"
                r"\s+(?:fee|fees|deposit|payment|charge)\b.{0,60}\b"
                r"(?:required|mandatory|pay|transfer|deposit|send|charged)\b",

                # "pay ₹1,500 to secure your position"
                r"\b(?:pay|transfer|send)\b.{0,50}\b"
                r"(?:₹|inr|rs\.?)?\s*\d[\d,]*(?:\.\d{1,2})?\b.{0,60}\b"
                r"(?:to secure|to confirm|to get|for securing)\b.{0,35}\b"
                r"(?:job|position|offer|interview)\b",

                # "pay to get the job / secure the offer"
                r"\bpay\b.{0,40}\b(?:to get|for securing|to confirm)\b.{0,30}\b"
                r"(?:job|interview|offer|position)\b",

                # Payment request without the word "fee"
                r"\b(?:security|registration|processing|application)\s+deposit\b",
            ],
            "severity": "HIGH",
            "finding": "The message appears to request an upfront recruitment-related payment.",
            "recommendation": "Do not pay recruitment, registration or interview fees or deposits. Verify the employer independently.",
        },
        {
            "category": "OTP_REQUEST",
            "patterns": [
                r"\b(?:share|send|provide|forward|tell|reveal|submit)\b.{0,40}\b(?:otp|one.time password)\b",
                r"\b(?:otp|one.time password)\b.{0,40}\b(?:share|send|provide|forward|tell|reveal)\b",
            ],
            "severity": "HIGH",
            "finding": "The message appears to ask the applicant to disclose an OTP.",
            "recommendation": "Never share an OTP with a recruiter or anyone claiming to offer a job.",
        },
        {
            "category": "PASSWORD_REQUEST",
            "patterns": [
                r"\b(?:share|send|provide|reveal|tell)\b.{0,40}\b(?:password|login credentials)\b",
                r"\b(?:password|login credentials)\b.{0,40}\b(?:share|send|provide|reveal|required)\b",
            ],
            "severity": "HIGH",
            "finding": "The message appears to request sensitive login credentials.",
            "recommendation": "Never share passwords or login credentials during recruitment.",
        },
        {
            "category": "BANKING_INFORMATION",
            "patterns": [
                r"\b(?:share|send|provide|submit|enter)\b.{0,50}\b(?:bank account details|bank details|card number|cvv|upi pin|banking credentials)\b",
                r"\b(?:bank account details|bank details|card number|cvv|upi pin|banking credentials)\b.{0,50}\b(?:share|send|provide|submit|required)\b",
            ],
            "severity": "HIGH",
            "finding": "The message appears to request sensitive banking information.",
            "recommendation": "Never share your CVV, UPI PIN, card details or banking credentials.",
        },
    ]

    def is_negated(sentence: str, category: str) -> bool:
        if category == "UPFRONT_PAYMENT":
            payment_denials = [
                r"\bno\s+(?:(?:registration|processing|interview|security|training|application|recruitment)\s+)?fees?\b",
                r"\bno\s+(?:registration|security|processing|application)\s+fee\s+(?:or\s+payment\s+)?(?:is\s+)?(?:required|needed|charged)\b",
                r"\b(?:free of charge|no fees charged|without any fees)\b",
                r"\b(?:we|our company|the recruiter)\b.{0,40}\b(?:never|do not|don't|will not|won't)\s+(?:ask for|charge|require)\b",
            ]
            if any(re.search(pattern, sentence) for pattern in payment_denials):
                return True

        general_denials = [
            r"\b(?:never|don't|do not|will not|won't)\b.{0,50}\b(?:pay|share|send|provide|reveal|submit|disclose)\b",
            r"\b(?:never|do not|don't|will not|won't)\b.{0,50}\b(?:ask|request|require)\b",
            r"\bno\s+(?:otp|password|bank details|bank account details|upi pin|cvv)\s+(?:is\s+)?(?:required|needed)\b",
        ]
        return any(re.search(pattern, sentence) for pattern in general_denials)

    for rule in rules:
        matched = any(
            any(re.search(pattern, sentence) for pattern in rule["patterns"])
            and not is_negated(sentence, rule["category"])
            for sentence in sentences
        )

        if matched:
            evidence.append({
                "category": rule["category"],
                "status": "DETECTED",
                "severity": rule["severity"],
                "finding": rule["finding"],
                "source_url": None,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            })
            recommendations.append(rule["recommendation"])

    return evidence, recommendations
