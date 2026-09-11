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

    Exactly one of `url` / `copy` is set — that is Telegram's own rule, not a
    simplification: "exactly one of the fields other than text,
    icon_custom_emoji_id and style must be used to specify the type of the
    button". So no button can both copy the code and open a bank; the trip is
    two taps and the most we can do is make the first one obvious.

    `copy` becomes Telegram's CopyTextButton, which puts the payload on the
    clipboard without ever posting it as a message. `style` is Bot API 10.0's
    button colour — `success` paints it green.
    """

    label: str
    url: str | None = None
    copy: str | None = None
    style: str | None = None


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

# Inter claims `*` on its own domain — every path opens br.com.intermedium,
# and Android delegates the whole domain to the same package. So this cannot
# fall through to a browser; the worst case is the app's home screen rather
# than its Pix screen. Which screen it actually lands on is unverified — no
# Inter account here to tap it with. Checked against both manifests 2026-09-11.
INTER_PIX = "https://inter.co/pix"

# Bradesco claims `/deeplink/*` for its consumer app (br.com.bradescora.app on
# iOS, com.bradesco on Android), so a path under /deeplink opens the app. Same
# caveat as Inter: the app opens, the screen it opens on is unverified.
BRADESCO_PIX = "https://banco.bradesco/deeplink/pix"

# Santander publishes no app-link manifest on santander.com.br — both the
# .well-known and legacy paths 404 from a real phone browser, and no AppsFlyer
# or Branch link exists either (santander.onelink.me serves the empty catch-all
# manifest, unlike nubank.onelink.me which names the app and the template).
#
# This one comes from the other direction, the way Itaú's did: a link verified
# on a device, on a domain whose manifest Akamai will not serve to a laptop.
# The query string is Santander's own routing — `fc=transferenciasgerenciar
# minhaschaves` is the Pix keys area — so it lands inside Pix rather than on
# the app's front door. Verified opening the bank 2026-09-11.
SANTANDER_PIX = (
    "https://pf.santandernet.com.br/LOGBBR_NS_ENS/BtoChannelDriver.ssobto"
    "?dse_operationName=LoginNMW&tplink=s&cp=transferenciasgerenciarm"
    "&fc=transferenciasgerenciarminhaschaves"
)


def buttons(code: str) -> list[list[Button]]:
    """Copy first — it is the whole product. The banks are a convenience row.

    Rows of three, never one long row: five buttons across truncate their own
    labels on a phone. The copy button stays alone, wide and green above them,
    which is what keeps it the thing the thumb goes to first.
    """
    return [
        # Green, alone, and in caps. A bank button cannot carry the code with
        # it, so the copy has to be the thing the thumb goes to first — and
        # the colour is not the only signal, because an older client that
        # ignores `style` still sees one wide shouting button over four narrow
        # quiet ones.
        [Button("📋 COPIAR O CÓDIGO PIX", copy=code, style="success")],
        [Button("🟠 Itaú", url=ITAU_PIX),
         Button("🟣 Nubank", url=NUBANK_APP),
         Button("🟧 Inter", url=INTER_PIX)],
        [Button("🔴 Bradesco", url=BRADESCO_PIX),
         Button("🟥 Santander", url=SANTANDER_PIX)],
    ]
