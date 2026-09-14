from collections.abc import Collection


def parse_answer(output: str, allowed: Collection[str]) -> str | None:
    if not isinstance(output, str):
        return None
    answer = output.strip()
    return answer if answer in allowed else None


def score(
    output: str, expected: str, allowed: Collection[str]
) -> tuple[bool, str | None]:
    parsed = parse_answer(output, allowed)
    return parsed is not None and parsed == expected, parsed
