import re
import json
from utils.llm import call_gemini
import os

def translate_medical_text(raw_text):
    """Translate medical text to clear English. NO JSON."""
    system_prompt = (
        "You are a professional translator assisting with administrative document processing. "
        "Translate the provided raw OCR text into clear, readable English for logistical and administrative purposes. "
        "This is not for clinical diagnosis or medical advice. Fix any obvious OCR typos. "
        "Return ONLY the translated English text, and nothing else. No introductions or apologies."
    )
    return _call_llm(system_prompt, raw_text)

def translate_template_text(template_str, target_language):
    """Translate a medical template to target language, keeping placeholders."""
    system_prompt = (
        f"Translate this administrative template to {target_language}. "
        "Keep {{placeholders}} exactly as they are. "
        "Return ONLY the translated string."
    )
    return _call_llm(system_prompt, template_str)

def translate_text(text, target_language):
    """Translate general display text to the chosen language."""
    system_prompt = (
        f"Translate the provided administrative text (such as an email template for booking an appointment) to {target_language}. "
        "This is purely logistical and is not medical advice or clinical interpretation. "
        "Preserve hospital names, charity names, codes, acronyms, and numbers. "
        "Return ONLY the translated text."
    )
    return _call_llm(system_prompt, text)

def translate_document_text(document_str, target_language):
    """
    Translate a formal document while preserving placeholder lines exactly.
    This keeps fill-in-the-blank PII scaffolding safe for later PDF generation.
    """
    protected_lines = []
    protected_text = document_str

    for index, line in enumerate(document_str.splitlines()):
        if "____" in line:
            token = f"[[PLACEHOLDER_{index}]]"
            protected_lines.append((token, line))
            protected_text = protected_text.replace(line, token, 1)

    system_prompt = (
        f"Translate the provided formal administrative travel document to {target_language}. "
        "This is not medical advice. Preserve placeholder tokens like [[PLACEHOLDER_0]] exactly as they are. "
        "Preserve hospital names, charity names, acronyms, reference codes, and numbers when appropriate. "
        "Return ONLY the translated document."
    )
    translated = _call_llm(system_prompt, protected_text)

    for token, original_line in protected_lines:
        translated = translated.replace(token, original_line)
    return translated

def generate_friendly_reasoning(item_type: str, item_data: dict, user_condition: str, target_language: str):
    """
    Generates a friendly, human-like explanation for why this option suits the user.
    Persona: Friendly talking to a person who lacks knowledge.
    """
    system_prompt = (
        f"You are a friendly customer service coordinator helping a patient plan travel logistics. "
        f"The user lacks technical knowledge, so explain things simply and warmly. "
        f"Generate the explanation directly in {target_language}. "
        f"Explain why this {item_type} is a great choice for them, highlighting specific details from the data like their specialty, location, or coverage to make it unique. "
        f"Make it sound personal and specific, not generic. Do NOT give medical advice. "
        f"Keep it short (2-3 sentences) and very encouraging. Return ONLY the explanation."
    )
    
    user_content = f"Item Details: {json.dumps(item_data, ensure_ascii=False)}"
    
    # Use Ollama for this as requested by user to bypass filters
    prompt = f"{system_prompt}\n\n{user_content}"
    response = _call_ollama(prompt)
    if response:
        return response
        
    # Fallback to Gemini
    res = call_gemini(system_prompt, user_content, model_name="gemini-1.5-flash")
    text = res.get("text", "").strip()
    return text or f"This {item_type} seems like a good fit for your logistics."

def _call_llm(system_prompt, user_content):
    prompt = f"{system_prompt}\n\nContent to translate:\n{user_content}"
    
    # Try Ollama first as requested by user
    ollama_response = _call_ollama(prompt)
    if ollama_response:
        return ollama_response
        
    # Fallback to Gemini
    res = call_gemini(system_prompt, user_content, model_name="gemini-1.5-flash")
    text = res.get("text", "").strip()
    return text or user_content

def _call_ollama(prompt):
    import requests
    try:
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        res = requests.post(
            f"{ollama_host}/api/generate",
            json={
                "model": "llama3.2:3b",
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )
        if res.status_code == 200:
            return res.json().get("response", "").strip()
    except Exception as e:
        print(f"Ollama failed or not running: {e}")
    return ""
