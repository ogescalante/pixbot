# Backlog

## 1. QR code image alongside the copia-e-cola

Higher value than any remaining bank button. The BR Code this bot already
generates *is* the QR payload — rendering it as an image means the person in
the chat can scan it from a second device, which is the one flow a copy button
cannot serve. Inline mode makes it especially worth it: `InlineQueryResultPhoto`
puts a scannable code straight into the conversation.

Cost: one dependency (`qrcode` + `Pillow`, or a pure-Python PNG writer to keep
the image alone), and a decision about where to host the image bytes for inline
results — Telegram wants a URL, so this likely means uploading to a channel
once and reusing the `file_id`.

## 2. More bank buttons

### The ceiling, first

No button can prefill a payment. Every one of these opens the app, at best on
its Pix screen, and the code still has to be pasted. So this is a convenience
row, not a feature — worth expanding cheaply, not worth engineering around.

### What is live today

| Bank | Link | Status |
|---|---|---|
| Itaú PF | `https://www.itau.com.br/mobilepf/transferencia/pix` | Lands on the Pix screen. Verified on device 2026-08-07. |
| Nubank | `https://nubank.onelink.me/g4UH/pix` | Opens the app on its home screen. AppsFlyer OneLink; it ignores `deep_link_value`. |

### Candidates, ranked by how many people they reach

Ranking by customer base: Nubank is the largest financial institution in the
country at 100M+ Brazilian customers, and Itaú, Bradesco, Banco do Brasil,
Caixa and Santander together hold roughly 80% of banking assets. Inter, C6,
PicPay, PagBank, Mercado Pago and Neon are the next tier. Pix itself reaches
~170M people, about 80% of the population.

| Bank | What its `apple-app-site-association` says | Next step |
|---|---|---|
| **Inter** | `inter.co` claims **`*`** — every path on the domain opens `br.com.intermedium` (checked 2026-09-11) | Strongest candidate. Try `https://inter.co/pix` on a device; a wrong path degrades to the app's home screen rather than to Safari, so there is no bad outcome. |
| **Bradesco** | `banco.bradesco` claims `/deeplink/*` and `/app_redirect/*` for `br.com.bradescora.app` (checked 2026-09-11) | Try `https://banco.bradesco/deeplink/pix` on a device and see which screen it lands on. |
| **Mercado Pago** | `mercadopago.com.br` has no Pix-send path; the nearest is `/money-transfer*` | Low value — `/money-transfer*` is the transfer hub, not Pix. |
| **Nubank** | Re-checked 2026-09-11: still only `/payment/*` (*Link de Pagamento* — a receivable with a server-issued id, pointed the wrong way for us), plus e-mail/sim/account-linking paths | Nothing to improve without a Link de Pagamento API. Keep the OneLink. |
| Banco do Brasil, Caixa, Santander, C6, PicPay, PagBank, Neon | Manifests are behind Akamai/Cloudflare WAFs and refuse a plain fetch — **not absent, just unreadable from a laptop** | Fetch from a phone browser, or `curl` from a residential connection, then read the `paths` / `components` array the same way. |

### How to check one

```bash
curl -sL -A 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) ...' \
  https://<domain>/.well-known/apple-app-site-association | python3 -m json.tool
```

The `applinks.details[].paths` (or `components[]./`) array is the exhaustive
list of paths that open the app. A path outside it opens Safari, which is the
failure mode worth avoiding — it looks like the button is broken.

Android's equivalent is `/.well-known/assetlinks.json`, and the two do not
always agree; a link that works on iPhone can fall through to the browser on
Android. Worth checking both before adding a button.

### Keep the row short

Six bank buttons under every payment is worse than two. If this grows past
three or four, the shape to reach for is a "outro banco" button that expands,
not a longer permanent row.

## 3. Port the CPF/telefone fix back to Claudia

`api/app/checking/pix_bot.py` in the finances repo still reads eleven bare
digits as a CPF and warns when `key[2] == "9"`. The math in `pix/keys.py` here
replaces both the reading and the warning. Same fix, one file.
