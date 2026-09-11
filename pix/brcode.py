"""BR Code ("Pix Copia e Cola") generation.

There is no way to open a bank app on a prefilled payment screen from outside —
no Brazilian bank publishes that entry point, and deliberately so: an
externally-supplied payment intent is a phishing primitive, and clipboard
hijacking that swaps Pix keys mid-paste is an active attack right now.

What every bank app *does* read is the BR Code — the BACEN/EMV TLV string
behind a Pix QR. Generating it locally turns "type her CPF and the amount" into
tap-copy-paste-confirm. Deterministic, no API, no dependency.

Spec: EMV QRCPS-MPM as profiled by BACEN's BR Code manual.
"""

from __future__ import annotations

import re
import unicodedata


def _ascii(s: str, limit: int, allow: str = "") -> str:
    """BR Code fields are plain uppercase ASCII — accents break parsers.

    `allow` widens the set for free-text fields. The description is read by a
    person, and "08/26 - 6160" stripped to "0826 6160" is a different reference
    than the one the payee is expecting.
    """
    out = "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )
    out = re.sub(rf"[^A-Za-z0-9 {re.escape(allow)}]+", "", out).strip().upper()
    return out[:limit]


def _tlv(tag: str, value: str) -> str:
    return f"{tag}{len(value):02d}{value}"


def crc16(payload: str) -> str:
    """CRC-16/CCITT-FALSE — poly 0x1021, init 0xFFFF, no reflection, xorout 0.

    Validated against the standard check vector: "123456789" -> 29B1.
    """
    crc = 0xFFFF
    for byte in payload.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def br_code(
    key: str,
    amount: float | None = None,
    receiver_name: str = "",
    city: str = "BRASIL",
    txid: str = "***",
    info: str = "",
) -> str:
    """Static BR Code payload.

    `receiver_name` (tag 59) is **whoever gets paid**, not the payer — the
    field is "merchant name" in EMV terms, and putting the payer's name there
    makes the bank show the wrong person on the confirmation screen, which is
    precisely the check the user should be relying on. This bot never knows the
    receiver, so it stays "NAO INFORMADO" and the paying bank fills the real
    holder in from DICT, which is the only trustworthy source for it anyway.

    `amount` is optional (tag 54); omitting it lets the payer type the value.

    `info` is the description (tag 26-02, *infoAdicional*) — what the payer's
    app shows in the message field. Truncated to whatever is left of tag 26's
    99-character budget after the GUI and the key, which is why a long e-mail
    key leaves less room than a CNPJ. Whether the field is displayed is up to
    the paying bank; the payment itself is unaffected either way.
    """
    gui, k = "BR.GOV.BCB.PIX", key.strip()
    acct = _tlv("00", gui) + _tlv("01", k)
    if info:
        budget = 99 - len(acct) - 4      # 4 = this subfield's own tag+length
        if budget > 0:
            acct += _tlv("02", _ascii(info, budget, allow="/-.,:#"))
    payload = _tlv("00", "01")
    payload += _tlv("26", acct)
    payload += _tlv("52", "0000")          # merchant category: unspecified
    payload += _tlv("53", "986")           # BRL
    if amount is not None:
        payload += _tlv("54", f"{amount:.2f}")
    payload += _tlv("58", "BR")
    payload += _tlv("59", _ascii(receiver_name, 25) or "NAO INFORMADO")
    payload += _tlv("60", _ascii(city, 15) or "BRASIL")
    payload += _tlv("62", _tlv("05", txid))
    # The CRC covers everything before it *including* the "6304" tag+length.
    payload += "6304"
    return payload + crc16(payload)
