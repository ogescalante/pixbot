"""Command text in, payable message out — the same one for chat and inline."""

from __future__ import annotations

import re
from dataclasses import dataclass

from pix.banks import Button, buttons
from pix.brcode import br_code
from pix.keys import CPF, HINTS, PHONE, Key, format_key, readings


USAGE = (
    "💸 Pix — gera o copia-e-cola de qualquer chave\n"
    "\n"
    "Manda assim:\n"
    "   /pix 123.456.789-01 250\n"
    "   /pix maria@email.com 89,90\n"
    "   /pix 45999999999 120 telefone\n"
    "\n"
    "Vale CPF, CNPJ, e-mail, telefone e chave aleatória.\n"
    "Sem valor, o código sai em aberto e você digita no app.\n"
    "\n"
    "CPF e celular têm os mesmos 11 dígitos. Eu conto o dígito verificador "
    "pra saber qual é — e quando os dois passam, você fecha a conta pondo "
    "`cpf` ou `telefone` no fim."
)

UNKNOWN = (
    "Não reconheci «{raw}» como chave Pix.\n"
    "\n"
    "Vale CPF (11 dígitos), CNPJ (14), e-mail, telefone com DDD ou chave "
    "aleatória.\n"
    "Se for telefone, confere o DDD; se for CPF, confere os dígitos."
)

# The receiver's name on the bank's confirmation screen is resolved from DICT,
# not from anything this bot sent. It is the only check that catches a mistyped
# key, and it costs one glance.
CONFIRM = "Confere o nome que o banco mostrar antes de confirmar."


def brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "~").replace(".", ",").replace("~", ".")


def parse(text: str) -> tuple[str | None, float | None, str | None]:
    """`<chave> [valor] [cpf|telefone]` -> (raw key, amount, hint).

    The key is the first token and the amount is whatever follows. Splitting
    the other way around — hunting for a number anywhere — misreads every
    numeric key there is: a CPF *is* digits, and `/pix 123.456.789-01` would
    pay one to itself.

    The hint is the last token, and only when something precedes it, so `/pix
    cpf` still reads as a nonsense key rather than as a hint with no number.
    """
    parts = text.strip().split()
    if parts and parts[0].startswith("/"):
        parts = parts[1:]
    if not parts:
        return None, None, None
    hint = None
    if len(parts) > 1 and parts[-1].lower() in HINTS:
        hint = HINTS[parts.pop().lower()]
    return parts[0], parse_amount(" ".join(parts[1:])), hint


def parse_amount(text: str) -> float | None:
    """`250`, `250,50`, `R$ 1.000`, and — unlike Brazilian notation — `250.00`.

    Here `.` is a thousands separator, so `1.000` is a thousand. But a phone
    keyboard and a copied figure both produce `250.00`, and reading that as
    R$ 25.000 is a 100× error pointed at a stranger's account. A dot with
    exactly two digits after it and no comma anywhere is a decimal point — no
    BR-formatted number looks like that.
    """
    raw = re.sub(r"[^\d.,]", "", text)
    if not raw:
        return None
    if "," not in raw and re.fullmatch(r"\d+\.\d{2}", raw):
        cleaned = raw
    else:
        cleaned = raw.replace(".", "").replace(",", ".")
    try:
        v = float(cleaned)
    except ValueError:
        return None
    return v if v > 0 else None


@dataclass(frozen=True)
class Quote:
    """One payable reading of one typed key."""

    key: Key
    amount: float | None

    @property
    def code(self) -> str:
        return br_code(self.key.value, self.amount)

    @property
    def headline(self) -> str:
        return (f"Pix de {brl(self.amount)}" if self.amount
                else "Pix — valor em aberto")

    @property
    def title(self) -> str:
        """Inline card title: amount first, because that is the risky part."""
        return f"💸 {self.headline} · {self.key.kind}"

    @property
    def description(self) -> str:
        """Inline card subtitle: the key as read, and any doubt about it."""
        line = format_key(self.key)
        return f"{line} — {self.key.note}" if self.key.note else line

    @property
    def message(self) -> str:
        lines = [f"💸 {self.headline}", "",
                 f"   Chave: {format_key(self.key)}  ({self.key.kind})"]
        if self.key.note:
            lines.append(f"   ⚠️ {self.key.note}")
        if self.amount is None:
            lines += ["", "O código não leva valor — você digita no app."]
        lines += ["", CONFIRM]
        return "\n".join(lines)

    @property
    def buttons(self) -> list[list[Button]]:
        return buttons(self.code)


def quotes(text: str) -> tuple[list[Quote], str | None]:
    """Every payable reading of a command, plus an error when there is none.

    Returns `([], USAGE)` for an empty command and `([], UNKNOWN…)` for a key
    that no reading fits — callers decide whether to say it out loud (chat) or
    to offer it as a hint above the results (inline).
    """
    raw, amount, hint = parse(text)
    if raw is None:
        return [], USAGE
    found = readings(raw, hint)
    if not found:
        return [], UNKNOWN.format(raw=raw)
    return [Quote(k, amount) for k in found], None


def render(text: str) -> tuple[str, list[list[Button]] | None]:
    """The chat reply: the best reading, with the alternative named in-line."""
    found, error = quotes(text)
    if error is not None:
        return error, None
    best = found[0]
    return best.message, best.buttons


__all__ = ["CPF", "PHONE", "Quote", "USAGE", "brl", "parse", "parse_amount",
           "quotes", "render"]
