# pixbot

Telegram bot: a Pix key in, a copia-e-cola out, inline in any chat.

## Shape

- `pix/` — framework-free. No aiogram, no network, no database. `keys.py`
  decides what a typed key is, `brcode.py` builds the EMV payload, `render.py`
  turns a command into a message, `banks.py` holds the deep links.
- `main.py` — the only Telegram. Handlers only; no logic worth testing lives
  here.
- `tests/` — pytest, no token needed. `uv run --with pytest pytest -q`.

## Rules

- Eleven bare digits are decided by **arithmetic**, never by length. The CPF
  check digits and the mobile shape (real DDD, then 9) are both computed; see
  the table in `README.md`. Do not reintroduce a length-only reading.
- Keys go into the BR Code in DICT's canonical form — bare digits, E.164,
  lowercase. Punctuation is display only (`format_key`).
- Tag 59 stays `NAO INFORMADO`. The paying bank resolves the real holder from
  DICT, and that confirmation screen is the user's only defence against a
  mistyped key.
- Nothing is persisted. If a change needs storage, that is a design decision to
  raise, not an implementation detail.
