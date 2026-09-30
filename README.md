# ΑΠΟΠ U14 & U16 · Γ΄ Όμιλος schedule

A small website that shows the ΑΠΟΠ fixtures, and keeps itself up to date.
Every 3 hours a GitHub server opens the federation page, picks
*Γυναικών U14 - Γ' Ομιλος* and *Γυναικών U16 - Γ' Ομιλος*, reads the games and republishes the site.
Nobody has to paste or edit anything.

## Put it online (about 10 minutes, free)

1. Create a free account at github.com, then **New repository**. Name it `apop-u14`, choose **Public**, click Create.
2. On the empty repository page click **uploading an existing file** and drag in everything from this folder
   (`index.html`, `fixtures.json`, `overrides.json`, `manifest.webmanifest`, `README.md`, and the `assets`, `scraper`
   and `.github` folders). Click **Commit changes**.
   * Mac tip: the `.github` folder is hidden in Finder (press Cmd+Shift+. to show it). If it won't upload, use
     **Add file → Create new file**, type `.github/workflows/update.yml` as the name and paste in the contents of
     `workflow-copy.yml`.
3. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
4. **Actions** tab → *Update fixtures and publish* → **Run workflow**. After about a minute the run shows the
   address of your site: `https://<your-username>.github.io/apop-u14/`.
5. Send that link to anyone. On a phone: Share → **Add to Home Screen** and it opens like an app.

## With git (Claude Code or a terminal)

`git init && git add -A && git commit -m "First version"`, create the public repository on GitHub, then
`git remote add origin <url> && git push -u origin main`. Continue from step 3 above.

## Good to know

* If the federation site changes and the scraper can't read it, GitHub emails you, the website keeps showing the
  last saved games, and the run has a `scraper-debug` download that shows what it saw.
* The federation may not publish tip-off times early. Add them in `overrides.json` (edit the file on GitHub),
  for example: `[{"date": "2026-10-10", "opponent": "ΑΠΟΛΛΩΝ", "time": "17:30"}]`. Once the federation publishes a
  time, remove the line.
* Venue map links come from `fixtures.json` → `places`. A venue that isn't listed there still gets a Google Maps
  search link.
* GitHub pauses scheduled runs after 60 days with no activity. If that happens, press **Run workflow** once.
* Use a custom address such as `apop-u14.com`: **Settings → Pages → Custom domain**.
