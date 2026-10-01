"""Generic quantity normalization for evidence checks, never eligibility rules."""

import re
from decimal import Decimal

SCALES = {
    "hundred": 100,
    "thousand": 1000,
    "lakh": 100000,
    "lakhs": 100000,
    "crore": 10000000,
    "crores": 10000000,
    "million": 1000000,
    "billion": 1000000000,
}
WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
}
TENS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}


def quantities(text):
    text = re.sub(r"https?://\S+", "", text.lower())
    text = re.sub(r"(?m)^\s*\d+[.)]\s+", "", text)
    text = re.sub(r"\bstep\s+\d+\b", "step", text)

    def tens(match):
        terms = re.split(r"[ -]", match.group())
        return str(TENS[terms[0]] + (WORDS[terms[1]] if len(terms) > 1 else 0))

    pattern = (
        r"\b(?:" + "|".join(TENS) + r")(?:[ -](?:one|two|three|four|five|six|seven|eight|nine))?\b"
    )
    text = re.sub(pattern, tens, text)
    text = re.sub(r"\b(?:" + "|".join(WORDS) + r")\b", lambda m: str(WORDS[m.group()]), text)
    scale_pattern = "|".join(sorted(SCALES, key=len, reverse=True))
    results = set()
    for match in re.finditer(
        r"(?<![\w])(?P<value>\d+(?:,\d+)*(?:\.\d+)?)(?P<scales>(?:\s*(?:"
        + scale_pattern
        + r")\b)*)",
        text,
    ):
        value = Decimal(match.group("value").replace(",", ""))
        for scale in re.findall(scale_pattern, match.group("scales")):
            value *= SCALES[scale]
        results.add(value)
    return results
