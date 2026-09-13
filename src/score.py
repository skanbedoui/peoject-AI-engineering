import re


def parse_answer(output: str) -> str | None:
    match = re.search(r"(?i)\b(yes|no)\b", output or "")
    return match.group(1).title() if match else None


def score(output: str, expected: str) -> tuple[bool, str | None]:
    parsed = parse_answer(output)
    return parsed == expected, parsed
