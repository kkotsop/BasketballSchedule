# Security

This is a read-only public website with no login, no database, no analytics and no secrets.

## What is public
Everything in this repository: the page, the scraper, the schedule data and the workflow. The schedule data comes
from the public federation fixtures page. No player names or personal details are stored.

## Protections in place
- **No untrusted HTML**: every value from the federation (team names, venues, dates) is escaped before it is
  inserted into the page, and embedded data escapes `<`. Map links only accept `https://` addresses.
- **Content Security Policy** (meta tag): only this site's own scripts/styles/images, `connect-src 'self'`, no
  frames, no objects, no forms, no base tag. The page makes **no third-party requests** (system fonts; Google Maps and
  Google Calendar are only opened when a visitor taps a link, with `noopener noreferrer`, and `no-referrer` is set).
- **Third parties, only on request**: the ntfy subscribe links open ntfy.sh only when a visitor taps them. The
  workflow (not the page) sends change alerts to ntfy.sh; the message contains only public schedule information.
  The ntfy topic is public by design (long random name, not a secret).
- **Storage**: the browser stores only the theme, the filter and the last quote (localStorage).
- **Workflow least privilege**: default permission is read-only; only the build job may write to the repository
  and only the deploy job may publish Pages. It is not triggered by pull requests, so forks cannot run it.
  Only GitHub's own `actions/*` are used, kept current by Dependabot (`.github/dependabot.yml`).
- **Scraper**: fixed address, timeouts, never writes `fixtures.json` when nothing is found, never follows data into
  code.

## Known limits
- GitHub Pages cannot send security headers, so clickjacking protection (`frame-ancestors`) is not possible; the
  page has nothing to click that changes data, so the risk is low.
- The CSP allows inline scripts/styles because the site is a single file.
- Commit history is public and contains the owner's GitHub commit e-mail from the first commit. Enable
  *Settings → Emails → Keep my email addresses private* on GitHub for future commits.

## Reporting a problem
Use GitHub **Security → Report a vulnerability** on this repository (enable *Private vulnerability reporting* in
Settings → Code security), or open an issue for anything that is not sensitive.

## Owner checklist
- Two-factor authentication on the GitHub account.
- Settings → Code security: enable Dependabot alerts, secret scanning and push protection.
- Settings → Actions → General: allow only GitHub-owned actions.
