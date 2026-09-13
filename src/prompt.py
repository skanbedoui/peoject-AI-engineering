SYSTEM_PROMPT = """You classify one legal contract clause.
Answer whether the clause contains the named category.
Return exactly one word: Yes or No.
Do not explain. Do not use punctuation.
"""


def build_prompt(category: str, description: str, clause: str) -> str:
    return (
        f"Category: {category}\n"
        f"Category definition: {description}\n"
        f"Contract clause: {clause}\n\n"
        "Does this clause contain the category? Answer exactly Yes or No."
    )
