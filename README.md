# ΑΠΟΠ U14 & U16 · Γ΄ Όμιλος schedule

A small, free website that shows the ΑΠΟΠ Paphos girls' basketball fixtures (Cyprus Basketball Federation,
Γυναικών U14 and U16, group Γ΄). It keeps itself up to date: every 3 hours a GitHub server reads the federation
page, saves the games and republishes the site. Nobody has to paste or edit anything.

Live site: `https://kkotsop.github.io/BasketballSchedule/` (on a phone: Share → **Add to Home Screen**).

## What it does
- Timeline of past and upcoming games; the **next game** is highlighted with a countdown and the page opens on it.
- **Both / U14 / U16** filter (remembered on the device).
- Season box: record, last 5 (green win, red loss, only for games with a real result) and games to play.
- Every game shows its score (0–0 until played); tip-off times appear when the federation publishes them.
- Venue links open Google Maps. **Add to calendar** offers Google Calendar or an `.ics` file (times are converted
  from Cyprus time, so they are right wherever the phone is).
- Dark (default) and light theme, each with its own photo background; soft scroll animations (switched off when
  the phone has *Reduce Motion* on); the quote and the "last check" footnote stay pinned at the bottom.
- **League table** (Table button next to the filter): standings from the federation for each group, with ΑΠΟΠ
  highlighted (logo, bold, red edge).
- **Share** (bottom bar): WhatsApp with a ready message that includes the next game, the system share sheet, or copy link.
- **Get updates** (bell, bottom bar): subscribe to a **calendar feed** and turn on **notifications** (see below).
- Refresh button next to the footnote.

## Calendar feed and notifications
- **Calendar feed**: the workflow writes `calendar/apop.ics`, `apop-u14.ics` and `apop-u16.ics` into the published
  site (`tools/make_ics.py`). Every game keeps the same id, so when a tip-off time is published or a game moves,
  subscribed calendars update the existing event. Apple/Outlook refresh within about an hour, Google Calendar
  every few hours to a day (Google's own limit).
- **Notifications inside the page (Web Push)**: tap the bell → *Turn on notifications*. After every scrape
  `tools/notify.py` compares the games with the previous run and sends one push to each subscriber (only for the age
  groups they chose) when a time is set or changed, a game moves, a venue changes, a game is added or a result is
  posted. No app to install. On **iPhone** the page must first be added to the Home Screen (Apple's rule); Android
  and desktop browsers work directly. Setup of the small free storage piece is in [worker/README.md](worker/README.md);
  until `push.api` in `fixtures.json` is filled in, the notification option stays hidden.
- **Haptic feedback**: taps give a light vibration on Android and a native tap on iPhone (Safari 17.4+).
- `fixtures.json` also holds `site` (the public address), `push` (`api` = the Worker address, `publicKey`) and
  `standings` (the league tables).

## How it works
| Part | File |
|---|---|
| The whole site (HTML, CSS, JS in one file) | `index.html` |
| Games, venue map links, last check time | `fixtures.json` |
| Manual fixes (tip-off time, venue) | `overrides.json` |
| Reads the federation site (games and league tables) | `scraper/scrape.py` |
| Calendar feeds / notifications | `tools/make_ics.py`, `tools/notify.py`, `sw.js`, `worker/push-worker.js` |
| Runs the scraper every 3 hours and publishes | `.github/workflows/update.yml` |
| Images | `assets/` (logo, icons, two background photos) |

The federation page (`cbfweb.org/eCBF/pubgames.aspx`) is an ASP.NET form. The scraper chooses season
`20262027`, then each competition (`Γυναικών U14 - Γ' Ομιλος`, `Γυναικών U16 - Γ' Ομιλος`), reads the games of ΑΠΟΠ
and writes `fixtures.json`. If one group cannot be read, its previous games are kept and the run is marked failed
(you get an email from GitHub); the site keeps showing the last saved games. On a failure the pages the scraper saw
are published to a `debug-output` branch for diagnosis.

## Put it online / set it up again
1. Repository **Settings → Pages → Build and deployment → Source: GitHub Actions**. (Free accounts need a
   **public** repository for Pages.)
2. **Actions** tab → *Update fixtures and publish* → **Run workflow**. After about a minute the run shows the address.
3. Mac tip: the `.github` folder is hidden in Finder (Cmd+Shift+.). If it won't upload, create
   `.github/workflows/update.yml` in the GitHub web editor and paste in `workflow-copy.yml`.

## Everyday use
- **Tip-off times** not yet published: add them in `overrides.json`, e.g.
  `[{"date": "2026-10-10", "opponent": "ΑΠΟΛΛΩΝ", "time": "17:30"}]`. Remove the line once the federation publishes it.
- **Venue pins**: `fixtures.json` → `places` maps a venue name to a Google place id, or to a full `https://` link
  (used for the home hall). Unknown venues get a Google Maps search link.
- **New season**: the scraper uses the current season automatically (it switches in August). To follow another
  group, change `CONFIG["competitions"]` in `scraper/scrape.py`.
- **Notification test**: `python tools/notify.py OLD.json NEW.json --dry-run` prints what would be sent.
- **Phase**: only *Κανονική Περίοδος* (regular season) is read. Playoffs/PlayOut are not included yet.
- GitHub pauses scheduled runs after 60 days with no repository activity. The bot commits after every run, which
  counts as activity; if runs ever stop, press **Run workflow** once.

## Limits and costs
Free. Public repositories have unlimited Actions minutes; a run takes about a minute. The load on the
federation site is small: about 4 requests per group, 8 runs a day.

## Custom domain (optional)
Use a domain you own (about $10–15/year). At the registrar add four `A` records for the apex to
`185.199.108.153`, `.109.153`, `.110.153`, `.111.153` (DNS only, not proxied), then **Settings → Pages → Custom
domain** and tick **Enforce HTTPS**. Until the DNS works, do not set a custom domain: Pages then stops serving the
default address. Free `eu.org` names need a manual request and a DNS host first.

## Development
- Preview: `python3 -m http.server 8000`, open http://localhost:8000
- Scraper: `pip install requests beautifulsoup4 && python scraper/scrape.py` (`CBF_URL=...` overrides the address).
  It **writes `fixtures.json`**, so test in a scratch copy. Mock test: `python tools/mock_cbf.py 8765`
  (`VARIANT=table|combined|cards`), then `CBF_URL=http://127.0.0.1:8765/eCBF/pubgames.aspx python scraper/scrape.py`.
- Icons: `pip install pillow`, then `python tools/make_icons.py`.
- `?debug=1` on the address shows the screen measurements used to diagnose phone layout problems.
- The workflow runs `tools/embed_data.py` to copy `fixtures.json` into the page before publishing.

## Security and privacy
See [SECURITY.md](SECURITY.md). In short: no accounts, no secrets, no analytics, no third-party requests; data from
the federation is always escaped before it is shown.
