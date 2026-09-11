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
| Inter | `https://inter.co/pix` | **Opens the app, screen unverified.** `inter.co` claims `*` on iOS (`br.com.intermedium`) and delegates the whole domain on Android (`br.com.intermedium`), so it cannot fall through to a browser. Added 2026-09-11. |
| Bradesco | `https://banco.bradesco/deeplink/pix` | **Opens the app, screen unverified.** `/deeplink/*` is claimed by the consumer app on iOS (`br.com.bradescora.app`) and the domain is delegated to `com.bradesco` on Android. Added 2026-09-11. |

**How Santander got in, after looking closed.** Every manifest route was a
dead end: `santander.com.br` 404s both app-link paths from a real phone
browser, and no attribution link exists — `santander.onelink.me` serves
AppsFlyer's empty catch-all (`{"applinks":{"apps":[],"details":[]}}`), unlike
`nubank.onelink.me`, whose manifest names the app *and* carries the `/g4UH/*`
template we ship. Branch, Adjust and the other OneLink subdomains do not
resolve at all.

What worked came from the other direction: a link found and tapped on a phone,
on `pf.santandernet.com.br` — a domain whose manifest Akamai will not serve to
a laptop either. Which is the whole lesson. **A blocked manifest never
disqualified a bank; it only meant the laptop could not do the check.** The
device test is the higher standard, not the fallback, and it is how both Itaú
and Santander got their buttons. Do not close a bank on a fetch failure again.

Santander's query string is its own routing, and `fc=transferenciasgerenciar
minhaschaves` is the Pix keys area — so it lands inside Pix rather than on the
app's front door. Whether a different `fc` reaches "pagar com copia e cola"
directly is untested; the parameter is clearly a catalog and worth one more tap
to explore.

**Still to verify on a device:** whether Inter and Bradesco land on their Pix
screens or on their home screens. Both are safe either way — the worst case is
the app's home screen, which is still better than hunting for the icon — but if
one lands somewhere useless, a different path may do better: Bradesco also
claims `/app_redirect/*`, and Inter claims everything so any path is fair game.

Banks go in rows of three, below the copy button. Five across truncate their
own labels on a phone; the copy button stays alone, wide and green on top,
because it is the actual payment and the banks only save hunting for an icon.
Past six, the shape to reach for is an "outro banco" button that expands, not a
third permanent row.

### Candidates, ranked by how many people they reach

Ranking by customer base: Nubank is the largest financial institution in the
country at 100M+ Brazilian customers, and Itaú, Bradesco, Banco do Brasil,
Caixa and Santander together hold roughly 80% of banking assets. Inter, C6,
PicPay, PagBank, Mercado Pago and Neon are the next tier. Pix itself reaches
~170M people, about 80% of the population.

| Bank | What its `apple-app-site-association` says | Next step |
|---|---|---|
| ~~Inter~~, ~~Bradesco~~ | — | **Added 2026-09-11**, see the table above. |
| **Mercado Pago** | `mercadopago.com.br` has no Pix-send path; the nearest is `/money-transfer*` | Low value — `/money-transfer*` is the transfer hub, not Pix. |
| **Nubank** | Re-checked 2026-09-11: still only `/payment/*` (*Link de Pagamento* — a receivable with a server-issued id, pointed the wrong way for us), plus e-mail/sim/account-linking paths | Nothing to improve without a Link de Pagamento API. Keep the OneLink. |
| Santander | `santanderpf://deeplink?tela=pix` via `docs/santander.html` | **Opens the app on the Pix area. Confirmed on device 2026-09-11.** A scheme cannot be a Telegram button, so the button points at our static page and the page opens the scheme. |
| Banco do Brasil, Caixa, C6, PicPay, PagBank, Neon | Manifests are behind Akamai/Cloudflare WAFs and refuse a plain fetch — **not absent, just unreadable from a laptop** | Fetch from a phone browser, or `curl` from a residential connection, then read the `paths` / `components` array the same way. |

### Why a half-working button is worse than none

Santander is the case that makes the rule. Even if its Android `assetlinks.json`
turned out to exist, iOS is confirmed absent — so the button would open the app
for Android users and drop every iPhone user in Safari on a 404. A button that
fails for half the people who press it reads as a broken bot, and there is no
way for the message to know which half is pressing.

So the bar for adding a bank is: **a manifest on both platforms, or a link
already verified on a device.** Itaú is in the bot on the second ground — its
manifest is unreadable from a laptop too, but someone tapped the link on a
phone on 2026-08-07 and watched it land on the Pix screen. The WAF never
mattered; the device check is what produced a working button.

### Nubank: what is settled and what is not (2026-09-11)

**Settled, by evidence:**

- Scheme is `nu-mmp://` — from `CFBundleURLTypes` of `com.nu.iphone`. The
  guesses `nubank://`, `nuapp://`, `nu://`, `nuconta://` do not exist.
- The app is Flutter (`CFBundleExecutable: Runner`, `DART_DEFINES`).
- `deep_link_value` is the right parameter. Proven on device: bare `nu-mmp://`
  opens with **no** Face ID, while `nu-mmp://?deep_link_value=<anything>`
  **always** prompts for Face ID — including a deliberately invalid value. The
  app parses the parameter, authenticates, fails to resolve the value, falls
  back to home.
- Therefore **Face ID is not a per-value signal.** It confirms the parameter,
  not the vocabulary. The only scoreboard is the screen you land on.
- `nuapp.nubank.com.br` claims `*` in `associated-domains` — every path opens
  the app. Rejected for this bot anyway: universal links hand off to the app
  and fall back to the web, which is the behaviour we are trying to avoid.

**Not settled:** the accepted `deep_link_value` vocabulary. It is not on the
web — all three OneLink templates (`g4UH`, `jTeG`, `gHLl`) 301 to the App Store
for any non-device client, so nothing leaks from there. The values live as
strings in the Dart snapshot inside `App.framework`.

**The one remaining move:** get the bundle and read it.
`strings App.framework/App | grep -i pix` prints a Flutter route table outright.
Two ways, both on your own machine and through Apple:

1. Mac App Store → *iPhone & iPad Apps* on an Apple Silicon Mac, if Nubank
   permits Mac installation. The bundle lands in `/Applications` and is readable
   directly. One search to find out.
2. Apple Configurator → download the `.ipa` → unzip → same grep.

Until then, tapping candidate values is a flat search of an unknown vocabulary
where every miss looks identical. Not worth more taps.

### Reading a scheme off an installed app — no jailbreak, no APK download

The device's install daemon answers over USB, and this is where `santanderpf`,
`nu-mmp` and Itaú's schemes actually came from — not from guessing:

```bash
brew install libimobiledevice ideviceinstaller
ideviceinstaller list | grep -i <banco>            # bundle id
ideviceinstaller list -b <bundleid> -a CFBundleURLTypes --xml
ideviceinstaller list -b <bundleid> -a UIApplicationShortcutItems --xml
```

`CFBundleURLTypes` is the exhaustive list of schemes the app registers.
`UIApplicationShortcutItems` is the sleeper: Santander's quick actions declare
`…minhacontapf.pixepagar3d` titled "Pix e pagar", which is the app's own naming
convention leaking out — lowercase concatenated Portuguese. Free evidence about
how their route names are spelled.

What the device will **not** give you is the route table. `tela=` values live in
compiled code. Same for Nubank: `CFBundleExecutable: Runner` plus `DART_DEFINES`
says the app is Flutter, and `NSAdvertisingAttributionReportEndpoint:
appsflyer-skadnetwork.com` plus the name `nu-mmp` (MMP = Mobile Measurement
Partner) says that scheme belongs to AppsFlyer — so its argument is
`deep_link_value`, not a path.

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

## 3. ~~Port the CPF/telefone fix back to Claudia~~ — done 2026-09-11

Ported on the `worktree-pix-cpf-telefone` branch of the finances repo, waiting
on a merge to main. `app/checking/pix.py` there now carries the same `Key`,
`is_cpf`, `is_mobile` and `readings`, and `/pix` takes the same trailing
`cpf` / `telefone`. Claudia has no inline mode, so the ambiguous case shows the
CPF reading with the note instead of two cards.

The two copies are deliberate duplication, not a shared package — one is a
public bot with no database and the other lives inside a private app. If they
drift, `pix/keys.py` here is the canonical one.
