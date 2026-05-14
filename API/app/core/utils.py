import json_repair


def clean_llm_response(response: str, verification_method: str | None = None) -> str:
    """
    Cleans LLM response by:
    1. Removing everything up to and including </think> tag (if present)
    2. Removing triple backticks (e.g. ```json ... ```)
    3. Repairing JSON formatting if verification_method is "JSON_COMPARE"
    """

    cleaned: str = response

    think_end_tag: str = "</think>"
    if think_end_tag in cleaned:
        cleaned = cleaned.split(think_end_tag, 1)[1]

    lines: list[str] = cleaned.splitlines()
    filtered_lines: list[str] = [
        line for line in lines if not line.strip().startswith("```")
    ]

    cleaned = "\n".join(filtered_lines).strip()

    if verification_method == "JSON_COMPARE":
        cleaned = json_repair.repair_json(cleaned, ensure_ascii=False)

    return cleaned
