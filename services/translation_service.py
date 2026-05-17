import json
import os
from typing import Dict

import requests

from utils.llm import call_gemini
from utils.translator import translate_text


def translate_batch_texts(texts: Dict[str, str], target_language: str) -> Dict[str, str]:
    if target_language.lower() in {"en", "english"}:
        return texts

    prompt = (
        f"Translate the following UI labels and button texts to {target_language}. "
        f"Keep the exact same keys. Return ONLY valid JSON.\n\n"
        f"{json.dumps(texts, ensure_ascii=False)}"
    )

    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    try:
        response = requests.post(
            f"{ollama_host}/api/generate",
            json={
                "model": "llama3.2:3b",
                "prompt": (
                    "You are a translator helping with administrative UI localization. "
                    "Return ONLY valid JSON.\n\n"
                    f"{prompt}"
                ),
                "stream": False,
            },
            timeout=120,
        )
        if response.status_code == 200:
            return _parse_translation_response(response.json().get("response", ""), texts)
    except Exception as exc:
        print(f"Ollama batch translation failed: {exc}")

    try:
        gemini_response = call_gemini(
            "You are a translator helping with administrative UI localization. Return ONLY valid JSON.",
            prompt,
            model_name="gemini-1.5-flash",
        )
        return _parse_translation_response(gemini_response.get("text", ""), texts)
    except Exception as exc:
        print(f"Batch translation error: {exc}")
        return {
            key: _safe_translate(value, target_language)
            for key, value in texts.items()
        }


def _parse_translation_response(response_text: str, original_texts: Dict[str, str]) -> Dict[str, str]:
    cleaned_response = response_text.strip()
    if "```json" in cleaned_response:
        cleaned_response = cleaned_response.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned_response:
        cleaned_response = cleaned_response.split("```", 1)[1].split("```", 1)[0].strip()

    translated_texts = json.loads(cleaned_response)
    for key, value in original_texts.items():
        translated_texts.setdefault(key, value)
    return translated_texts


def _safe_translate(text: str, target_language: str) -> str:
    try:
        return translate_text(text, target_language)
    except Exception:
        return text
