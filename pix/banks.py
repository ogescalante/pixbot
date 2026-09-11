"""The bank buttons under a code, and what they can and cannot do.

None of these prefill a payment. No Brazilian bank publishes an entry point
that accepts an externally-supplied payment intent, and that is a deliberate
security decision, not an oversight — see the note at the top of `brcode.py`.
The BR Code *is* the prefill; a bank button only saves hunting for the icon on
a crowded home screen.

Which app a payment should leave from is the payer's call, so both are always
offered rather than guessed at.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Button:
    """A keyboard button, framework-free so this package stays testable.

    Exactly one of `url` / `copy` is set: `copy` becomes Telegram's
    CopyTextButton, which puts the payload on the clipboard without ever
    posting it as a message.
    """

    label: str
    url: str | None = None
    copy: str | None = None


# Itaú's own domain, from its apple-app-site-association: the Personnalité app
# (FWR8CJ7249.com.itau.iphone.personnalite) claims `/mobilepf/*` as a wildcard,
# and `/mobilepf/transferencia/pix` lands on the Pix screen — verified on
# device 2026-08-07.
#
# Deliberately NOT the `7kwy.adj.st` route that also works: that is Adjust, a
# third-party attribution vendor. If Itaú changes vendors the domain stops
# resolving and the button dies silently. Their own domain has no such clock.
ITAU_PIX = "https://www.itau.com.br/mobilepf/transferencia/pix"

# Nubank: nubank.com.br claims only /payment/* (which is *Link de Pagamento* —
# a receivable with a server-issued id, pointed the wrong way for us) plus a
# few email/sim paths. Re-checked against the live manifest on 2026-09-11 and
# it still holds. Their AppsFlyer OneLink opens the app but ignores
# deep_link_value, so this lands on the home screen and no further. Still worth
# a button: it saves hunting for the icon.
NUBANK_APP = "https://nubank.onelink.me/g4UH/pix"


def buttons(code: str) -> list[list[Button]]:
    """Copy first — it is the whole product. The banks are a convenience row."""
    return [
        [Button("📋 Copiar código Pix", copy=code)],
        [Button("🟠 Abrir Itaú PF", url=ITAU_PIX),
         Button("🟣 Abrir Nubank", url=NUBANK_APP)],
    ]
