"""What kind of Pix key someone just typed — and, for eleven bare digits, the
one decision this bot exists to get right.

A CPF and a Brazilian mobile number are both eleven digits. Length alone cannot
tell them apart, so reading "eleven digits" as "CPF" pays a stranger every time
someone types a phone number without the +55. `45999999999` is a real example:
DDD 45, mobile, and it was being turned into a CPF payment.

The tie-break is arithmetic. A CPF carries two check digits computed from the
first nine, so a mistaken CPF is detectable — a number that fails the check is
not a CPF that DICT would ever resolve. A mobile number carries no checksum,
only a shape: a real DDD followed by the mandatory 9. Run both and the readings
separate:

    check digits ok, not mobile-shaped  ->  CPF, no doubt
    check digits ok, mobile-shaped      ->  CPF, and this is the *only* case
                                            that says anything out loud (~1%
                                            of mobiles pass the CPF checksum)
    check digits fail, mobile-shaped    ->  telefone, silently  <- the case
                                            above
    neither                             ->  not a key we recognise

An explicit `cpf` / `telefone` at the end of the command settles it regardless;
that is the escape hatch for the ~1% the math genuinely cannot decide.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# Every DDD ANATEL has actually assigned. The gaps are real — there is no 20,
# 23, 25, 26, 29, 36, 39, 52, 56, 57, 58, 59, 60, 70, 72, 76, 78, 80 or 90 —
# and they are what make "is this shaped like a phone?" a question worth
# asking instead of a formality that passes everything.
DDDS = frozenset({
    11, 12, 13, 14, 15, 16, 17, 18, 19,
    21, 22, 24, 27, 28,
    31, 32, 33, 34, 35, 37, 38,
    41, 42, 43, 44, 45, 46, 47, 48, 49,
    51, 53, 54, 55,
    61, 62, 63, 64, 65, 66, 67, 68, 69,
    71, 73, 74, 75, 77, 79,
    81, 82, 83, 84, 85, 86, 87, 88, 89,
    91, 92, 93, 94, 95, 96, 97, 98, 99,
})

CPF = "CPF"
CNPJ = "CNPJ"
PHONE = "telefone"
EMAIL = "e-mail"
EVP = "chave aleatória"

# What the user may type as the last word to force a reading.
HINTS = {
    "cpf": CPF,
    "cnpj": CNPJ,
    "telefone": PHONE, "tel": PHONE, "celular": PHONE, "cel": PHONE,
    "fone": PHONE, "phone": PHONE, "mobile": PHONE, "whatsapp": PHONE,
    "zap": PHONE,
}

_RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_RE_EVP = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)


@dataclass(frozen=True)
class Key:
    """A canonical key plus why we read it that way.

    `value` is what goes into the BR Code verbatim, so it is DICT's own form —
    bare digits for CPF/CNPJ, E.164 for phones, lowercase for e-mail and EVP.
    Canonicalising is not cosmetic: a bank looking up "123.456.789-01" against
    a CPF that DICT holds as bare digits answers "chave não encontrada".

    `note` is empty whenever the reading is obvious. It is only populated when
    the user deserves to know that a judgement call was made on his behalf.
    """

    value: str
    kind: str
    note: str = ""


def cpf_check_digits(nine: str) -> str:
    """The two check digits BACEN's CPF algorithm derives from the first nine."""
    out = ""
    for start in (10, 11):
        base = nine + out
        total = sum(int(c) * w for c, w in zip(base, range(start, 1, -1)))
        rest = total % 11
        out += "0" if rest < 2 else str(11 - rest)
    return out


def is_cpf(digits: str) -> bool:
    """Eleven digits that a CPF registry would actually accept.

    The repeated-digit family (`00000000000`, `11111111111`, …) satisfies the
    arithmetic — the weights sum to a multiple that lands on the same digit —
    and is rejected everywhere as invalid anyway. Leaving it in would hand
    `11111111111` to the CPF branch, where it is neither a CPF nor the phone
    it is not shaped like either.
    """
    if len(digits) != 11 or not digits.isdigit() or digits == digits[0] * 11:
        return False
    return digits[9:] == cpf_check_digits(digits[:9])


def is_mobile(digits: str) -> bool:
    """Eleven digits shaped like a Brazilian mobile: real DDD, then the 9."""
    return (
        len(digits) == 11
        and digits.isdigit()
        and int(digits[:2]) in DDDS
        and digits[2] == "9"
    )


def is_ten_digit_phone(digits: str) -> bool:
    """Ten digits with a real DDD — landline, or a mobile written the old way.

    No CPF is ten digits, so there is no tie to break here and no reason to be
    strict about what follows the DDD. Insisting on a landline prefix (2–5)
    would refuse `4599998888`, which is how a mobile was written before the
    ninth digit arrived and is still how plenty of people type one.
    """
    return len(digits) == 10 and digits.isdigit() and int(digits[:2]) in DDDS


def readings(raw: str, hint: str | None = None) -> list[Key]:
    """Every defensible reading of what was typed, best first.

    Usually one. Eleven ambiguous digits produce two, which is exactly what
    inline mode wants: instead of warning about a coin flip, it offers both
    cards and lets the person who knows whose key it is pick.
    """
    s = raw.strip()
    if not s:
        return []
    if "@" in s:
        return [Key(s.lower(), EMAIL)] if _RE_EMAIL.match(s) else []
    if _RE_EVP.match(s):
        return [Key(s.lower(), EVP)]

    digits = re.sub(r"\D", "", s)
    if not digits:
        return []

    # A typed +55 or a (45) is the person telling us it is a phone; believe it
    # over any checksum. International keys go through here too — DICT accepts
    # a foreign number as a key and no CPF reading competes for those.
    if s.startswith("+"):
        return [Key("+" + digits, PHONE)] if 12 <= len(digits) <= 15 else []
    if "(" in s and len(digits) in (10, 11):
        return [Key("+55" + digits, PHONE)]

    if len(digits) == 14:
        return [Key(digits, CNPJ)]
    if len(digits) == 13 and digits.startswith("55"):
        # 5545999999999 — a phone that lost only its plus sign.
        return [Key("+" + digits, PHONE)]
    if len(digits) == 10:
        return [Key("+55" + digits, PHONE)] if is_ten_digit_phone(digits) else []
    if len(digits) != 11:
        return []

    cpf_ok, mobile_ok = is_cpf(digits), is_mobile(digits)
    as_cpf = Key(digits, CPF)
    as_phone = Key("+55" + digits, PHONE)

    if hint == CPF:
        return [as_cpf if cpf_ok else Key(
            digits, CPF, "o dígito verificador não bate — confere se digitou certo"
        )]
    if hint == PHONE:
        return [as_phone if mobile_ok else Key(
            "+55" + digits, PHONE, "não parece um celular válido — confere o DDD"
        )]

    if cpf_ok and mobile_ok:
        # Both readings survive. CPF leads because the checksum is evidence and
        # the mobile shape is only a pattern, but the alternative rides along.
        return [
            Key(digits, CPF, "também pode ser telefone — manda `telefone` no fim "
                             "se for"),
            Key("+55" + digits, PHONE, "leitura alternativa"),
        ]
    if cpf_ok:
        return [as_cpf]
    if mobile_ok:
        # No note. The checksum settled it, and a line explaining the
        # arithmetic on every single phone payment is the same noise the old
        # "Li como CPF" warning was — read once, ignored after.
        return [Key("+55" + digits, PHONE)]
    return []


def normalize_key(raw: str, hint: str | None = None) -> Key | None:
    """The single best reading, or None when nothing fits."""
    found = readings(raw, hint)
    return found[0] if found else None


def format_key(key: Key | str) -> str:
    """Canonical key -> readable. Display only; never feed this to the BR Code.

    Punctuating the phone is not decoration — `+55 (45) 99999-9999` is the one
    place the user can see at a glance that his sister-in-law's number was read
    as a number and not as somebody's CPF.
    """
    value = key.value if isinstance(key, Key) else key
    if value.startswith("+55") and len(value) in (13, 14):
        d = value[3:]
        return f"+55 ({d[:2]}) {d[2:-4]}-{d[-4:]}"
    if len(value) == 11 and value.isdigit():
        return f"{value[:3]}.{value[3:6]}.{value[6:9]}-{value[9:]}"
    if len(value) == 14 and value.isdigit():
        return f"{value[:2]}.{value[2:5]}.{value[5:8]}/{value[8:12]}-{value[12:]}"
    return value
