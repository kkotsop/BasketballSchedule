# ΑΠΟΠ U14 & U16 · Γ΄ Όμιλος schedule website

Mobile-first, read-only schedule page for the ΑΠΟΠ Paphos girls' teams (Cyprus Basketball Federation, Γυναικών U14
and U16, group Γ΄), shared with parents and players. It updates itself from the federation site. Read README.md for
setup and everyday use and SECURITY.md for the security notes.

## Status
- Live on GitHub Pages: https://kkotsop.github.io/BasketballSchedule/ (public repo, deployed by the workflow).
- The scraper runs every 3 hours against the real site and reads both groups. Tested live on GitHub's runners
  (the development sandbox cannot reach cbfweb.org).
- Only the regular season is read; playoffs/PlayOut are not (next possible task).

## Files
- `index.html`: the entire site (HTML + CSS + JS). `fixtures.json`: data. `overrides.json`: manual tip-off/venue fixes.
- `scraper/scrape.py`: reads the federation form (ASP.NET WebForms) for each entry of `CONFIG["competitions"]`.
- `.github/workflows/update.yml` (copy in `workflow-copy.yml`): scrape, commit `fixtures.json`, embed data, publish Pages.
- `tools/`: `mock_cbf.py` (fake federation for tests), `make_icons.py`, `embed_data.py`, `make_ics.py` (calendar feeds),
  `notify.py` (web push sender), `gen_vapid.py`. `sw.js`: service worker (push display only). `worker/`: Cloudflare Worker that
  stores push subscriptions (see worker/README.md; tested with a fake KV in node). `assets/`: logo, icons, the
  two background photos (`bg-ball.webp` dark, `bg-wall.webp` light).

## The federation page
`https://cbfweb.org/eCBF/pubgames.aspx`. A GET returns three drop-downs; the games appear after posting them back.
Season `20262027`, competition text `Γυναικών U14 - Γ' Ομιλος` / `Γυναικών U16 - Γ' Ομιλος` (ASCII apostrophe, no accent on
Ομιλος), phase `Κανονική Περίοδος`. **The full game list is already on the page right after the competition is
chosen**; the phase step returns a page without games, so the scraper keeps the last non-empty result. Each row holds
`game code · home · score · date | time · venue · away`; the scraper strips the code, `0 - 0`, and the pipe from the
venue. Team names of each group come from the standings table (`group_teams`). A failed group keeps its previous
games and the run exits 1 (workflow shows red, site still deploys; debug pages go to branch `debug-output`).

## Data model (`fixtures.json`)
`{team, league, group, source, site, push:{api,publicKey}, updated, checked, logo, places, standings, games[]}`. `standings` is
`{"U14":[{team,p,w,l,pts,pf,pa,diff}], "U16":[...]}` read from the federation table (`standings_from` parses the raw
HTML because the site writes unclosed `<td>` tags; 12 numbers follow the team name: played, wins, losses, forfeits,
points, for, against, diff, home/away wins and losses). The table parser is verified only against pre-season (all
zero) HTML and a synthetic sample; check it against real numbers once games are played. A game is
`{id, league:"U14"|"U16", date:"YYYY-MM-DD", time:"HH:MM" or "", home, away, venue, hs, as}` (scores are strings, `"0"`
before the game). `updated` changes when games change; `checked` changes every successful run (shown in the
footnote). `places` maps a venue to a Google place id (`ChIJ…`), a plain search text, or a full `https://` link.
A game counts as **played only when the score is not 0–0**; unplayed games always look like upcoming ones.

## Page behaviour worth knowing
- The whole page scrolls (not an inner box) so phone browsers can hide their toolbars; header/filter/season box are
  sticky at the top, quote + footnote are fixed at the bottom. Do **not** go back to a fixed-height inner scroller or
  to measuring heights with `innerHeight`/`dvh`: that caused a black strip at the bottom on iPhones.
- On load and when returning after 30 s the list centres on the next game (`centerFocus`).
- Times are Cyprus local time; `cyprusUTC()` converts them (used for countdown, `.ics` and Google Calendar links).
- Theme: dark by default, stored in localStorage; each theme has its own photo. Filter and quote also remembered.
- Scroll animation: `IntersectionObserver` reveal + background parallax; disabled for *Reduce Motion*.
- `?debug=1` overlays the screen measurements; `?r=…` is used by the refresh button to bypass the cache.

## Design decisions (keep unless the user asks)
- Dark: black-and-white ball on a finger photo, graphite glass, white controls. Light: hoop-on-concrete photo, white
  glass, black controls. One red accent on the **next game** card (top line, glow under the card, timeline dot).
- Cards are intentionally very transparent (blurred glass); the next-game card is the brightest.
- Home badge is solid (inverse colour), Away is outlined; U14/U16 tag shown in the "Both" view.
- No player name anywhere on the page (it is shared with the whole team).
- Quote bar: short attributed quotes (under 15 words). Do not copy lists from other sites.
- System fonts only (no Google Fonts) for privacy and speed.

## Features added later
- Table view (`view` = games|table, button in the filter row). Bottom-bar icons: WhatsApp (`wa.me` link, `waUrl()`),
  copy link (`copyLink()`), bell (updates sheet), refresh; the bell shows a red dot until opened once
  (localStorage `apop-seen-updates`).
- Updates sheet: calendar subscription links (`webcal://`, Google `cid=`) and in-page **Web Push** (`pushOn/pushOff`,
  stored choice in localStorage `apop-push`). Hidden until `push.api` is set. iPhone needs the page on the Home Screen.
  Subscribing must start inside a tap (`Notification.requestPermission`). The sender is `tools/notify.py`
  (pywebpush; `sub` claim must be the site ORIGIN without a path, else py-vapid rejects it).
- Haptics: `haptic()` uses `navigator.vibrate` (Android) or a hidden `<input type=checkbox switch>` click (iPhone).
- Workflow order: remember old games, scrape, (debug on failure), save fixtures, send push notifications, build site
  (embed data + `calendar/*.ics`, copy `sw.js`), deploy. Secrets: `VAPID_PRIVATE_KEY`, `PUSH_ADMIN_TOKEN`.

## Conventions
- Single-file site: HTML, CSS, JS in `index.html`; images only from `assets/`; no dependencies.
- Everything from the federation must go through `esc()` before it is put in HTML.
- Greek text must render correctly; keep UTF-8 and test with real team names.
- Accessibility: 44 px tap targets in the header, visible focus, contrast checked in both themes.
- The styling has layers from several design rounds (later blocks override earlier ones). If a rewrite is needed,
  consolidate the `design v10` and `document scrolling` blocks into the base styles.
