def clean_llm_response(response: str) -> str:
    """
    Cleans LLM response by:
    1. Removing everything up to and including </think> tag (if present)
    2. Removing triple backticks (e.g. ```json ... ```)
    """

    cleaned: str = response

    think_end_tag: str = "</think>"
    if think_end_tag in cleaned:
        cleaned = cleaned.split(think_end_tag, 1)[1]

    lines: list[str] = cleaned.splitlines()
    filtered_lines: list[str] = [
        line for line in lines if not line.strip().startswith("```")
    ]

    cleaned = "\n".join(filtered_lines)

    return cleaned.strip()
