from typing import Any, Dict

from fastapi import HTTPException

from utils.letter_generator import (
    GUIDANCE_TEMPLATE_KEYS,
    LETTER_SKELETONS,
    VISA_TEMPLATE_KEYS,
    build_visa_support_content,
    fill_template,
    generate_pdf,
)
from utils.translator import translate_document_text


def preview_letter_html(
    template_key: str,
    user_data: Dict[str, Any],
    medical_data: Dict[str, Any],
    package_data: Dict[str, Any],
    target_language: str | None,
) -> str:
    template = _get_template(template_key)
    content = _build_letter_content(template_key, template, user_data, medical_data, package_data)
    if target_language and target_language.lower() not in {"english", "en"}:
        content = translate_document_text(content, target_language)
    return content


def generate_letter_pdf(
    template_key: str,
    user_data: Dict[str, Any],
    medical_data: Dict[str, Any],
    package_data: Dict[str, Any],
    target_language: str | None,
) -> bytes:
    content = preview_letter_html(
        template_key=template_key,
        user_data=user_data,
        medical_data=medical_data,
        package_data=package_data,
        target_language=target_language,
    )
    return generate_pdf(content)


def _get_template(template_key: str) -> str:
    if template_key not in LETTER_SKELETONS:
        raise HTTPException(status_code=404, detail="Template not found")
    return LETTER_SKELETONS[template_key]


def _build_letter_content(
    template_key: str,
    template: str,
    user_data: Dict[str, Any],
    medical_data: Dict[str, Any],
    package_data: Dict[str, Any],
) -> str:
    if template_key in VISA_TEMPLATE_KEYS or template_key in GUIDANCE_TEMPLATE_KEYS:
        return build_visa_support_content(
            template_str=template_key,
            user_data=user_data,
            medical_data=medical_data,
            package_data=package_data,
        )

    from utils.letter_generator import enrich_user_data_with_package

    enrich_user_data_with_package(user_data, medical_data, package_data)
    return fill_template(template, user_data)
