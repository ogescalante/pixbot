"""What the user reads, in chat and inline."""

from __future__ import annotations

import pytest

from pix.keys import CPF, PHONE
from pix.render import USAGE, parse, parse_amount, quotes, render


# --- parsing ---------------------------------------------------------------


def test_key_is_the_first_token_not_the_first_number():
    """The bug this guards: a CPF is digits, so hunting for "the number"
    anywhere in the text turns `/pix 123.456.789-01` into a payment of R$ 1,23
    to a truncated key."""
    assert parse("/pix 123.456.789-01 250") == ("123.456.789-01", 250.0, None)


def test_the_hint_is_the_last_word_and_leaves_the_amount_alone():
    assert parse("/pix 45999999999 120 telefone") == ("45999999999", 120.0, PHONE)
    assert parse("/pix 45999999999 cpf") == ("45999999999", None, CPF)
    assert parse("45926018153 1.000,50 cel") == ("45926018153", 1000.5, PHONE)


def test_a_lone_hint_word_is_a_key_not_a_hint():
    """`/pix cpf` has nothing to disambiguate, so it is just a bad key."""
    assert parse("/pix cpf") == ("cpf", None, None)


def test_amount_is_optional():
    assert parse("/pix maria@email.com") == ("maria@email.com", None, None)


def test_bare_command_asks_for_arguments():
    assert parse("/pix") == (None, None, None)
    assert render("/pix") == (USAGE, None)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("250", 250.0),
        ("250,50", 250.5),
        ("R$ 1.000", 1000.0),
        ("1.000,50", 1000.5),
        ("250.00", 250.0),      # phone keyboard / copied figure, not R$ 25.000
        ("", None),
        ("0", None),
    ],
)
def test_amount_notation(text, expected):
    assert parse_amount(text) == expected


# --- the message -----------------------------------------------------------


def test_a_phone_reading_is_visible_in_the_reply():
    text, rows = render("/pix 45999999999 250")
    assert "R$ 250,00" in text
    assert "+55 (45) 99999-9999" in text
    assert "(telefone)" in text
    assert "dígito verificador" in text
    assert "Confere o nome" in text
    assert rows[0][0].copy.startswith("000201")


def test_an_open_amount_says_so():
    text, _ = render("/pix maria@email.com")
    assert "valor em aberto" in text
    assert "você digita no app" in text


def test_an_unrecognised_key_is_quoted_back():
    text, rows = render("/pix 20999534351 250")
    assert "«20999534351»" in text
    assert rows is None


def test_the_buttons_are_copy_first_then_the_banks():
    _, rows = render("/pix 11144477735 10")
    assert [b.label for b in rows[0]] == ["📋 Copiar código Pix"]
    assert all(b.url for row in rows[1:] for b in row)


def test_the_bank_row_stops_at_four():
    """A fifth bank pushes the copy button — which is the actual payment —
    out of the first place the eye lands."""
    _, rows = render("/pix 11144477735 10")
    assert sum(len(row) for row in rows[1:]) <= 4


# --- inline ----------------------------------------------------------------


def test_an_ambiguous_key_offers_both_cards():
    """No warning to write: two cards, and whoever knows the person picks."""
    found, error = quotes("45926018153 120")
    assert error is None
    assert [q.key.kind for q in found] == [CPF, PHONE]
    assert found[0].title == "💸 Pix de R$ 120,00 · CPF"
    assert found[1].description.startswith("+55 (45) 92601-8153")
    assert found[0].code != found[1].code


def test_an_unambiguous_key_offers_exactly_one():
    found, _ = quotes("45999999999 120")
    assert len(found) == 1 and found[0].key.kind == PHONE


def test_inline_needs_no_slash():
    assert quotes("11144477735 10")[0][0].key.value == "11144477735"
