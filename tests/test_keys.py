"""Which key is which — and above all, CPF vs. celular.

Run: uv run --with pytest pytest -q
"""

from __future__ import annotations

import pytest

from pix.keys import (
    CNPJ, CPF, EMAIL, EVP, PHONE,
    cpf_check_digits, format_key, is_cpf, is_mobile, normalize_key, readings,
)


# --- the bug this bot exists to fix ----------------------------------------


def test_a_mobile_typed_without_plus55_is_not_a_cpf():
    """45999999999 is a real mobile (DDD 45) that was being paid as a CPF.

    Its check digits would have to be 13, not 51 — so no CPF registry would
    ever resolve it, and reading it as one sends money to whoever does own
    that number's CPF-shaped neighbour.
    """
    assert cpf_check_digits("459999999") == "13"
    assert not is_cpf("45999999999")

    key = normalize_key("45999999999")
    assert key.kind == PHONE
    assert key.value == "+5545999999999"
    assert key.note == ""       # the checksum settled it; nothing to explain


def test_a_real_cpf_that_looks_like_a_mobile_is_still_a_cpf():
    """~6.7% of valid CPFs carry a valid DDD and a 9 in third place.

    The old length-only reading warned on every one of them. The checksum is
    evidence and the mobile shape is only a pattern, so the CPF leads — but
    the alternative reading rides along instead of being thrown away.
    """
    both = "45926018153"
    assert is_cpf(both) and is_mobile(both)

    first, second = readings(both)
    assert (first.kind, first.value) == (CPF, both)
    assert (second.kind, second.value) == (PHONE, "+55" + both)
    assert "telefone" in first.note


def test_an_unambiguous_cpf_says_nothing_at_all():
    key = normalize_key("111.444.777-35")
    assert (key.kind, key.value, key.note) == (CPF, "11144477735", "")


def test_eleven_digits_that_are_neither_are_refused():
    """Bad checksum and no DDD 20 — this is a typo, not a key."""
    assert readings("20999534351") == []


def test_the_repeated_digit_family_is_not_a_cpf():
    """It satisfies the arithmetic and every registry rejects it anyway."""
    assert cpf_check_digits("111111111") == "11"
    assert not is_cpf("11111111111")
    assert readings("11111111111") == []


# --- the escape hatch ------------------------------------------------------


def test_an_explicit_hint_overrules_the_math():
    ambiguous = "45926018153"
    assert normalize_key(ambiguous, hint=PHONE).value == "+55" + ambiguous
    assert normalize_key(ambiguous, hint=CPF).value == ambiguous


def test_a_hint_that_contradicts_the_math_still_warns():
    """He asked for it, so he gets it — with the reason it looked wrong."""
    key = normalize_key("45999999999", hint=CPF)
    assert key.kind == CPF
    assert "não bate" in key.note


# --- everything else -------------------------------------------------------


@pytest.mark.parametrize(
    "raw,value,kind",
    [
        ("maria@email.com", "maria@email.com", EMAIL),
        ("Maria@Email.com", "maria@email.com", EMAIL),
        ("12.345.678/0001-95", "12345678000195", CNPJ),
        ("+5545999999999", "+5545999999999", PHONE),
        ("5545999999999", "+5545999999999", PHONE),       # lost only the plus
        ("(45) 99999-9999", "+5545999999999", PHONE),     # said so out loud
        ("4532101234", "+554532101234", PHONE),           # landline, no CPF is 10
        ("4599998888", "+554599998888", PHONE),           # mobile, written the old way
        ("123E4567-E89B-12D3-A456-426614174000",
         "123e4567-e89b-12d3-a456-426614174000", EVP),
    ],
)
def test_canonical_forms(raw, value, kind):
    """DICT's own forms: bare digits, E.164, lowercase. A key it holds as bare
    digits is "chave não encontrada" when sent punctuated."""
    key = normalize_key(raw)
    assert (key.value, key.kind) == (value, kind)


@pytest.mark.parametrize("raw", ["", "   ", "maria@", "@email.com", "12345",
                                 "2099953435", "não sei"])
def test_nothing_recognisable(raw):
    assert normalize_key(raw) is None


@pytest.mark.parametrize(
    "raw,shown",
    [
        ("45999999999", "+55 (45) 99999-9999"),
        ("11144477735", "111.444.777-35"),
        ("12345678000195", "12.345.678/0001-95"),
        ("maria@email.com", "maria@email.com"),
    ],
)
def test_display_punctuation_shows_the_reading(raw, shown):
    """Punctuating the phone is the one place he can see, at a glance, that
    his sister-in-law's number was read as a number."""
    assert format_key(normalize_key(raw)) == shown
