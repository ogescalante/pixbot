# pixbot

A Telegram bot that turns a Pix key into a **copia-e-cola**, from inside any
conversation.

```
@seubot 45999999999 120
```

No bank app can be opened on a prefilled payment screen from outside — no
Brazilian bank publishes that entry point, and deliberately so: an
externally-supplied payment intent is a phishing primitive. What every bank app
*does* read is the BR Code, the BACEN/EMV string behind a Pix QR. Generating it
locally turns "type her CPF and the amount" into tap-copy-paste-confirm.

Nothing is stored. No key, no amount, no chat id, no database. The bot holds a
payment intent for exactly as long as it takes to answer.

## CPF or telefone?

A CPF and a Brazilian mobile are both eleven digits, so length cannot tell them
apart. Reading "eleven digits" as "CPF" pays a stranger every time someone
types a phone number without the +55 — `45999999999` is a real mobile that was
being turned into a CPF payment.

This bot does the arithmetic instead. A CPF carries two check digits derived
from the first nine; a mobile carries no checksum, only a shape (a real DDD,
then the mandatory 9). Run both:

| CPF check digits | mobile shape | reading |
|---|---|---|
| ok | no | **CPF**, silently |
| ok | yes | **CPF**, and this is the only case that warns (~1% of mobiles pass the CPF checksum) |
| fail | yes | **telefone** → `+55…`, silently |
| fail | no | refused, with what it accepts |

The collision is the only thing worth a `⚠️`. When the checksum settles it,
explaining the arithmetic on every payment is the same noise as warning on
every payment — read once, ignored after.

Measured over 200k samples: ~1.0% of real mobiles also pass the CPF checksum,
and ~6.7% of real CPFs look like a mobile. The second group is why a
length-only reading has to warn on every CPF payment; the checksum settles
them and the warning disappears.

For the ~1% the math genuinely cannot decide, put `cpf` or `telefone` at the
end:

```
/pix 45926018153 120 telefone
```

Inline mode does better than a warning: when both readings survive it offers
**two cards** and the person who knows whose key it is picks one.

## Keys it accepts

CPF, CNPJ, e-mail, telefone (with or without `+55`, mobile or landline) and
chave aleatória (the EVP UUID). Keys are canonicalised to DICT's own forms —
bare digits, E.164, lowercase — because a bank looking up `123.456.789-01`
against a CPF it holds as bare digits answers *chave não encontrada*.

## Amounts

`250`, `250,50`, `R$ 1.000`, `1.000,50` — and `250.00`, which Brazilian
notation would call twenty-five thousand. A phone keyboard and a copied figure
both produce `250.00`, and reading that as R$ 25.000 is a 100× error pointed at
a stranger's account, so a dot with exactly two digits after it and no comma
anywhere is treated as a decimal point.

Leave the amount out and the code goes out open — the payer types the value.

## Setup

1. `/newbot` with [BotFather](https://t.me/botfather), grab the token.
2. `/setinline` on the same bot — **inline mode is off by default** and the
   `@seubot …` flow does nothing until it is on. Placeholder suggestion:
   `chave e valor: 45999999999 120`.
3. `/setcommands` → `pix - gera o copia-e-cola de uma chave`
4. `cp token.env.example token.env` and fill in `TELEGRAM_TOKEN`.

## Run

```bash
docker compose up -d --build      # or:
uv run --with aiogram==3.28.2 python main.py
```

Long polling, no webhook, no inbound port.

## Tests

```bash
uv run --with pytest pytest -q
```

Everything under `pix/` is framework-free — it imports no aiogram and touches
no network, so the payment logic is tested without a bot token. `main.py` is
the only Telegram.

## Before you send

The name your bank shows on the confirmation screen comes from DICT, not from
anything this bot sent. It is the only check that catches a mistyped key, and
it costs one glance.
