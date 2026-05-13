import json
import re
from typing import Any, Dict, Tuple
from rapidfuzz import fuzz, utils
from app.core.llm_clients import BaseLLMClient


class EvaluationException(Exception):
    pass


class EvaluationService:
    @staticmethod
    def evaluate_exact_match(expected: str, actual: str) -> Tuple[float, Dict[str, Any]]:
        """
        Dokładne dopasowanie tekstu.
        Zwraca 1.0 (100% zgodności) lub 0.0.
        """
        score = 1.0 if expected == actual else 0.0
        return score, {}

    @staticmethod
    def evaluate_json_compare(expected: str, actual: str) -> Tuple[float, Dict[str, Any]]:
        """
        Porównanie struktury i wartości JSON (od 0.0 do 1.0).
        Obsługuje zagnieżdżenia poprzez spłaszczenie (flattening) struktury.
        """
        try:
            expected_json = json.loads(expected)
            actual_json = json.loads(actual)
        except json.JSONDecodeError:
            raise EvaluationException("Failed to deserialize JSON!")

        def flatten_json(y: Any) -> Dict[str, Any]:
            out = {}

            def flatten(x, name=''):
                if isinstance(x, dict):
                    for a in x:
                        flatten(x[a], name + a + '.')
                elif isinstance(x, list):
                    for i, a in enumerate(x):
                        flatten(a, name + str(i) + '.')
                else:
                    out[name[:-1]] = x
            flatten(y)
            return out

        flat_expected = flatten_json(expected_json)
        flat_actual = flatten_json(actual_json)

        if not flat_expected and not flat_actual:
            return 1.0, {}
        if not flat_expected or not flat_actual:
            return 0.0, {}

        keys_expected = set(flat_expected.keys())
        keys_actual = set(flat_actual.keys())
        all_keys = keys_expected.union(keys_actual)

        match_score = 0.0

        for key in all_keys:
            if key in keys_expected and key in keys_actual:
                val_exp = flat_expected[key]
                val_act = flat_actual[key]
                if val_exp == val_act:
                    match_score += 1.0
                elif isinstance(val_exp, str) and isinstance(val_act, str):
                    similarity = fuzz.ratio(val_exp, val_act, processor=utils.default_process) / 100.0
                    match_score += similarity
        final_score = match_score / len(all_keys)
        return round(final_score, 4), {}

    @staticmethod
    def evaluate_ocr_match(expected: str, actual: str) -> Tuple[float, Dict[str, Any]]:
        """
        Zaawansowane dopasowanie OCR odporne na literówki i szum.
        Zwraca od 0.0 do 1.0. Używa algorytmu odległości Indel/Levenshteina.
        """
        score = fuzz.ratio(expected, actual, processor=utils.default_process) / 100.0
        return round(score, 4), {}

    @staticmethod
    async def evaluate_llm_eval(
        expected: str,
        actual: str,
        judge_client: BaseLLMClient | None = None,
        system_prompt: str | None = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Ocena przy pomocy LLM jako sędziego.
        Zwraca stopień zgodności (0.0 - 1.0) oraz uzasadnienie.
        """

        if not judge_client:
            raise ValueError("Błąd: judge_client musi być zdefiniowany i przekazany do metody!")

        if system_prompt and system_prompt.strip():
            judge_system_prompt = system_prompt
        else:
            judge_system_prompt = (
                "Jesteś surowym, ale sprawiedliwym sędzią oceniającym jakość odpowiedzi modelu. "
                "Porównaj odpowiedź 'Otrzymaną' z odpowiedzią 'Oczekiwaną'. "
                "Zawsze najpierw przedstaw krótkie uzasadnienie swojej decyzji. "
                "Na samym końcu swojej analizy, w nowej linii, podaj ostateczną ocenę używając tagów XML:\n"
                "<score>X.XX</score>\n"
                "gdzie X.XX to wartość punktowa od 0.0 do 1.0."
            )

        judge_prompt = f"Oczekiwana odpowiedź:\n{expected}\n" + "#"*30 + f"\nOtrzymana odpowiedź:\n{actual}"

        try:
            response = await judge_client.generate(prompt=judge_prompt, system_prompt=judge_system_prompt)
            response_text = response[0] if isinstance(response, (list, tuple)) else str(response)
            match = re.search(r"<score>\s*([0-1](?:\.\d+)?)\s*</score>", response_text, re.IGNORECASE)

            if match:
                score = float(match.group(1))
            else:
                match_fallback = re.search(r"\[?SCORE:?\s*([0-1](?:\.\d+)?)\]?", response_text, re.IGNORECASE)
                if match_fallback:
                    score = float(match_fallback.group(1))
                else:
                    numbers = re.findall(r"\b(0(?:\.\d+)?|1(?:\.0+)?)\b", response_text)
                    if numbers:
                        score = float(numbers[-1])
                    else:
                        return 0.0, {
                            "error": "BŁĄD PARSOWANIA WYNIKU SĘDZIEGO",
                            "reason": response_text.strip()
                        }

            score = max(0.0, min(1.0, score))

            return round(score, 4), {"reason": response_text.strip()}

        except Exception as e:
            error_type = type(e).__name__
            if error_type == "LLMAPIError":
                status_code = getattr(e, 'status_code', 'Brak kodu')
                response_body = getattr(e, 'response_body', 'Brak body')
                error_reason = f"Błąd API {status_code} od modelu sędziego: {response_body}"
            elif error_type == "LLMException":
                error_reason = f"Problem z komunikacją z modelem sędzią: {str(e)}"
            else:
                error_reason = f"Nieoczekiwany błąd systemu LLM: {str(e)}"
            return 0.0, {"error": error_reason}

    @classmethod
    async def evaluate(cls, verification_method: str, expected: str, actual: str, **kwargs) -> Tuple[float, Dict[str, Any]]:
        """Główna metoda wywołująca odpowiedni ewaluator na podstawie zadanego typu."""
        if verification_method == "EXACT_MATCH":
            return cls.evaluate_exact_match(expected, actual)
        elif verification_method == "JSON_COMPARE":
            return cls.evaluate_json_compare(expected, actual)
        elif verification_method == "OCR_MATCH":
            return cls.evaluate_ocr_match(expected, actual)
        elif verification_method == "LLM_EVAL":
            return await cls.evaluate_llm_eval(
                expected,
                actual,
                judge_client=kwargs.get("judge_client"),
                system_prompt=kwargs.get("system_prompt"),
            )
        else:
            raise ValueError(f"Nieobsługiwana metoda weryfikacji: {verification_method}")
