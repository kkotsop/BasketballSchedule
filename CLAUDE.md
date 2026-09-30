# ΑΠΟΠ U14 · Γ΄ Όμιλος schedule website

A mobile-first, read-only schedule page for the ΑΠΟΠ Paphos girls' U14 basketball team (Cyprus Basketball
Federation, group Γ΄), meant to be shared with parents and players who are **not** on Claude. It should update
itself from the federation site with no manual pasting.

Moved here from a claude.ai chat. That chat first built the page as a Claude artifact, then turned it into this
standalone site. The artifact is kept in `legacy/claude-artifact-v5.html` for reference only.

## Status (read this first)
- Site (`index.html`) is built and tested in a phone-sized headless Chromium, light and dark.
- `scraper/scrape.py` is tested only against `tools/mock_cbf.py` (a stand-in for the federation form).
  **It has never run against the live site.** The chat's sandbox could not reach cbfweb.org.
- Nothing is deployed yet. No git repo, no GitHub Pages.
- `fixtures.json` holds 6 ΑΠΟΠ games seeded from an earlier import. Only the 3 Oct game has a tip-off time.

## Next steps
1. `git init`, create a **public** GitHub repo, push, Settings → Pages → Source: GitHub Actions, then run the
   workflow `Update fixtures and publish` (`.github/workflows/update.yml`).
2. Read the first real run's log. If the scraper fails, download the `scraper-debug` artifact (raw HTML of each
   step), save it as a test fixture, and fix `scraper/scrape.py` against the real markup. Also check that GitHub's
   runner IPs are not blocked by cbfweb.org.
3. Confirm the two uncertain venue pins (see Venues) and fill tip-off times through `overrides.json` until the
   federation publishes them.
4. Optional cleanup: `index.html` still contains the legacy editing UI (paste importer, game editor, quotes
   editor, `buildDoc`/`commit`). It is unreachable because `canWrite = false`; remove it if you want a smaller file.

## The federation page
`https://cbfweb.org/eCBF/pubgames.aspx` is ASP.NET WebForms (ViewState, UpdatePanel). A plain GET returns only three
drop-downs. The games appear after posting them back:
- season: `20262027` (texts like `20252026`; the season switches in August)
- competition ("Επιλογή Διοργάνωσης"): `Γυναικών U14 - Γ' Ομιλος` (ASCII apostrophe, no accent on Ομιλος)
- phase: `Κανονική Περίοδος` (others: Playoffs, PlayOut)
The scraper selects by visible text, re-posts hidden fields, parses rows by innermost `<tr>` with a date (with a
div/li fallback), keeps only ΑΠΟΠ games, and **exits 1 without touching `fixtures.json`** when nothing is found.
Group teams: ΑΠΟΠ, ΑΤΛΑΝΤΑΣ Πάφου, ΑΧΙΛΛΕΑΣ Αγρού, ΑΝΟΡΘΩΣΗ Αμμοχώστου, ΑΡΗΣ Λεμεσού, Α.Ε.Λ., ΑΠΟΛΛΩΝ Λεμεσού.

## Data model (`fixtures.json`)
`{team, league, group, source, updated, logo, places, games[]}`; a game is
`{id, date:"YYYY-MM-DD", time:"HH:MM" or "", home, away, venue, hs, as}` (scores as strings, home then away).
Empty `time` renders as "Time TBC" and exports as an all-day calendar event.
`places` maps a venue string to a Google place id; links use
`https://www.google.com/maps/search/?api=1&query=<venue>&query_place_id=<id>`; unknown venues fall back to a search.
`overrides.json` (`[{"date","opponent","time","venue"}]`) is applied by the scraper after parsing.

## Venues
- Αίθ. Α' Λυκείου Ακης Κλεάνθους (Paphos, home): pinned to "APOP Basketball court", about 150 m from the Α' Λύκειο.
  Not confirmed to be the hall itself.
- Λύκ. Αγ. Φύλας: mapped to Λύκειο Αγίας Φυλάξεως, Limassol, the only Google match. Verify it is the right school.
- Λύκ. Αγ. Σπυρίδωνα and Αίθ. Νίκος Σολομωνίδης (AEL arena): good matches.

## Design decisions (keep unless the user asks)
- Fintech "frosted glass" look: translucent surfaces, backdrop blur, 1px light edge, layered shadows. Tokens are
  CSS variables at the top of the `<style>` block, mapped to Tailwind values. Inter font.
- Palette: slate neutrals, orange accent (the ball, next game, calls to action), club blue `#2563EB` for Home.
  Green/red only for win/loss. The user disliked the first cream + royal-blue look.
- One continuous timeline, past above and upcoming below, scrolled so the **next game is centred**. Results are a
  separate widget (Record, Last 5, To play), not a tab.
- Home = solid blue badge with a house icon and "vs"; Away = outlined badge with an arrow and "at".
- Background: a real-looking basketball image (`assets/ball.webp`, rendered by `tools/render_ball.py`) fixed in place
  while the list scrolls. **No animation** (the user tried one and disliked it).
- Theme switch is top right; ⋯ menu beside it. Emblem in the header (`assets/logo.png`, supplied by the user).
- Each upcoming game has an "Add to calendar" button (.ics via Blob download); the menu has "Export all games".
- No player name anywhere on the page, so it can be shared with the whole team.
- Bottom bar: a random attributed quote on every visit, and a new one on each tap. Keep quotes short (under 15 words)
  and attributed. The four Pat Summitt lines were checked against published sources; the others are widely cited
  and worth spot-checking. Do not copy lists from other sites such as shootaway.com.
- Tagline in small glass pill at the end of the list: "One Club. One Dream."

## Commands
- Preview: `python3 -m http.server 8000`, then open http://localhost:8000
- Scraper: `pip install requests beautifulsoup4 && python scraper/scrape.py` (`CBF_URL=...` overrides the address).
  It **writes `fixtures.json`**, so test in a scratch copy of the repo.
- Mock test: `python tools/mock_cbf.py 8765` (`VARIANT=table|combined|cards`, `MOCK_EMPTY=1`), then
  `CBF_URL=http://127.0.0.1:8765/eCBF/pubgames.aspx python scraper/scrape.py`.
- Regenerate images: `pip install numpy pillow`, then `python tools/render_ball.py` and `python tools/make_icons.py`.
- The chat verified the UI with `puppeteer-core` + `@sparticuz/chromium` screenshots at 390×800 (scale 2).

## Conventions
- Single-file site: HTML, CSS and JS in `index.html`; images only from `assets/`. Keep it dependency-free.
- Greek text must render correctly; keep `lang`/UTF-8 and test with real team names.
- Accessibility: 44px tap targets in the header, visible focus rings, `prefers-reduced-motion` respected, contrast
  checked in both themes.
- Dates are rendered in the viewer's local time; tip-off times are local Cyprus time without a timezone.
