# -*- coding: utf-8 -*-
"""
Lightweight Chinese text patch rules for Microsoft Edge TTS.

This module is intentionally small and domain-focused. It is not a general
Chinese text normalizer. Instead, it only handles cases that are high-value
for Bashi Voice Factory's current TTS product direction:

- Classical chapter references:   古书 1:1 -> 古书第一章第一节
- Phone numbers:          138-1234-5678 -> 一三八 一二三四 五六七八
- File paths / URLs:      simplify to speakable forms
- Punctuation cleanup:    remove long ellipsis / em-dash patterns that read badly

It is repo-local on purpose so the Edge TTS path does not depend on the
separate CosyVoice_Local_TTS project at runtime.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class TtsPatchOptions:
    enable_classical_ref: bool = True
    enable_phone: bool = True
    enable_filepath: bool = True
    enable_punctuation_cleanup: bool = True


_CLASSICAL_REF_BOOK_ENDINGS = set("记音篇书传歌录言训诗")
_CLASSICAL_REF_EXCLUSIONS = {"游记", "日记", "笔记", "传记", "手记", "札记", "随笔录"}
_CLASSICAL_REF_KEYWORDS = {
    "章节", "篇", "节", "注释", "古籍", "古文", "篇目", "卷",
}
_PIAN_UNIT_NAMES = {"诗篇", "诗"}
_DIGIT_MAP = {
    "0": "零", "1": "一", "2": "二", "3": "三", "4": "四",
    "5": "五", "6": "六", "7": "七", "8": "八", "9": "九",
}

_RE_CLASSICAL_REF = re.compile(
    r"(\d{1,3})"
    r"[:：]"
    r"(\d{1,3})"
    r"(?:"
    r"[-–—~～]"
    r"(?:(\d{1,3})[:：])?"
    r"(\d{1,3})"
    r")?"
    r"(?:"
    r"[,，]"
    r"(\d{1,3})"
    r"(?:[-–—~～](\d{1,3}))?"
    r")?"
)

_RE_URL = re.compile(
    r"(?:https?://)"
    r"([\w.-]+)"
    r"(?:[/\w.?=&#%-]*)"
)
_RE_WIN_PATH = re.compile(
    r"[A-Za-z]:[\\]"
    r"[\w\\. -]+"
)
_RE_UNIX_PATH = re.compile(
    r"(?<![a-zA-Z0-9])"
    r"(/[\w.-]+){2,}"
)
_RE_ELLIPSIS = re.compile(r"[…]{1,}|\.{3,}")
_RE_DASH = re.compile(r"[—–]{2,}")

_RE_CN_MOBILE = re.compile(
    r"(?<!\d)"
    r"(1[3-9]\d)"
    r"[-–]?"
    r"(\d{4})"
    r"[-–]?"
    r"(\d{4})"
    r"(?!\d)"
)
_RE_CN_LANDLINE = re.compile(
    r"(?<!\d)"
    r"(0\d{2,3})"
    r"[-–]"
    r"(\d{7,8})"
    r"(?!\d)"
)
_RE_CN_LANDLINE_PAREN = re.compile(
    r"(?<!\d)"
    r"[（(]"
    r"(0\d{2,3})"
    r"[）)]"
    r"\s*"
    r"(\d{3,4})"
    r"[-–]"
    r"(\d{4})"
    r"(?!\d)"
)
_RE_INTL_PREFIX = re.compile(
    r"(\+\d{1,4})"
    r"[-–\s]?"
)
_RE_SHORT_NUMBER = re.compile(
    r"(?<!\d)"
    r"(1(?:10|19|20|22)|12315|12345|114|120|122|999|911|112)"
    r"(?!\d)"
)


def _num_to_chinese(n: int) -> str:
    """Convert 0-999 into natural Chinese reading."""
    if n < 0 or n > 999:
        return str(n)
    if n == 0:
        return "零"

    result = ""
    hundreds = n // 100
    tens = (n % 100) // 10
    ones = n % 10

    if hundreds > 0:
        result += _DIGIT_MAP[str(hundreds)] + "百"
        if tens == 0 and ones > 0:
            result += "零"

    if tens > 0:
        if tens == 1 and hundreds == 0:
            result += "十"
        else:
            result += _DIGIT_MAP[str(tens)] + "十"

    if ones > 0:
        result += _DIGIT_MAP[str(ones)]

    return result


def _digits_to_chinese(digits: str) -> str:
    return "".join(_DIGIT_MAP.get(d, d) for d in digits)


def _digits_grouped(digits: str, group_size: int = 4) -> str:
    cn = _digits_to_chinese(digits)
    groups = [cn[i:i + group_size] for i in range(0, len(cn), group_size)]
    return " ".join(groups)


def _has_classical_ref_context(text: str, match_start: int) -> bool:
    window_start = max(0, match_start - 20)
    before = text[window_start:match_start].rstrip()

    for excl in _CLASSICAL_REF_EXCLUSIONS:
        if before.endswith(excl):
            return False

    if before and before[-1] in _CLASSICAL_REF_BOOK_ENDINGS:
        return True

    return any(keyword in text for keyword in _CLASSICAL_REF_KEYWORDS)


def _uses_pian_unit(text: str, match_start: int) -> bool:
    before = text[max(0, match_start - 10):match_start]
    return any(name in before for name in _PIAN_UNIT_NAMES)


def _convert_classical_ref(match: re.Match, full_text: str) -> str:
    chapter = int(match.group(1))
    start_verse = int(match.group(2))
    cross_chapter = match.group(3)
    end_verse = match.group(4)
    cont_start = match.group(5)
    cont_end = match.group(6)

    unit = "篇" if _uses_pian_unit(full_text, match.start()) else "章"
    result = f"第{_num_to_chinese(chapter)}{unit}第{_num_to_chinese(start_verse)}节"

    if end_verse:
        end_v = int(end_verse)
        if cross_chapter:
            cross_ch = int(cross_chapter)
            result += f"至第{_num_to_chinese(cross_ch)}{unit}第{_num_to_chinese(end_v)}节"
        else:
            result += f"至第{_num_to_chinese(end_v)}节"

    if cont_start:
        cont_s = int(cont_start)
        result += f"、第{_num_to_chinese(cont_s)}节"
        if cont_end:
            cont_e = int(cont_end)
            result += f"至第{_num_to_chinese(cont_e)}节"

    return result


def convert_classical_references(text: str) -> str:
    def _replacer(match: re.Match) -> str:
        if _has_classical_ref_context(text, match.start()):
            return _convert_classical_ref(match, text)
        return match.group(0)

    return _RE_CLASSICAL_REF.sub(_replacer, text)


def convert_filepaths(text: str) -> str:
    def _replace_url(match: re.Match) -> str:
        domain = match.group(1)
        return domain[4:] if domain.startswith("www.") else domain

    def _replace_win_path(match: re.Match) -> str:
        path = match.group(0)
        parts = [p for p in path.split("\\") if p]
        return parts[-1] if parts else path

    def _replace_unix_path(match: re.Match) -> str:
        path = match.group(0)
        parts = [p for p in path.split("/") if p]
        return parts[-1] if parts else path

    text = _RE_URL.sub(_replace_url, text)
    text = _RE_WIN_PATH.sub(_replace_win_path, text)
    text = _RE_UNIX_PATH.sub(_replace_unix_path, text)
    return text


def convert_phone_numbers(text: str) -> str:
    def _replace_landline_paren(match: re.Match) -> str:
        area = _digits_to_chinese(match.group(1))
        first = _digits_to_chinese(match.group(2))
        second = _digits_to_chinese(match.group(3))
        return f"{area} {first} {second}"

    def _replace_intl(match: re.Match) -> str:
        digits = match.group(1)[1:]
        return f"加{_digits_to_chinese(digits)}"

    def _replace_mobile(match: re.Match) -> str:
        return (
            f"{_digits_to_chinese(match.group(1))} "
            f"{_digits_to_chinese(match.group(2))} "
            f"{_digits_to_chinese(match.group(3))}"
        )

    def _replace_landline(match: re.Match) -> str:
        area = _digits_to_chinese(match.group(1))
        number = _digits_grouped(match.group(2), 4)
        return f"{area} {number}"

    def _replace_short(match: re.Match) -> str:
        return _digits_to_chinese(match.group(1))

    text = _RE_CN_LANDLINE_PAREN.sub(_replace_landline_paren, text)
    text = _RE_INTL_PREFIX.sub(_replace_intl, text)
    text = _RE_CN_MOBILE.sub(_replace_mobile, text)
    text = _RE_CN_LANDLINE.sub(_replace_landline, text)
    text = _RE_SHORT_NUMBER.sub(_replace_short, text)
    return text


def cleanup_punctuation(text: str) -> str:
    text = _RE_ELLIPSIS.sub("，", text)
    text = _RE_DASH.sub("，", text)
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"[，,]{2,}", "，", text)
    return text.strip()


def normalize_chinese_tts_text(
    text: str,
    options: Optional[TtsPatchOptions] = None,
) -> str:
    """
    Apply a small patch-style normalization for Chinese Edge TTS inputs.

    This function intentionally avoids broad number/date normalization.
    We only patch cases that are high value and known to be unstable.
    """
    if not text:
        return text

    opts = options or TtsPatchOptions()
    result = text

    if opts.enable_classical_ref:
        result = convert_classical_references(result)
    if opts.enable_phone:
        result = convert_phone_numbers(result)
    if opts.enable_filepath:
        result = convert_filepaths(result)
    if opts.enable_punctuation_cleanup:
        result = cleanup_punctuation(result)

    return result
