# Notification store (Cloudflare Worker)

Web Push needs a place that remembers who turned notifications on. This tiny Worker does that (free plan is plenty:
100,000 requests/day, 1,000 writes/day). It never sends notifications itself; the GitHub workflow downloads the list
and sends them (`tools/notify.py`).

## One-time setup (about 15 minutes, no coding)
1. Create a free account at dash.cloudflare.com.
2. **Storage & databases → KV → Create** a namespace called `apop-subs`.
3. **Workers & Pages → Create → Start with Hello World → name it `apop-push` → Deploy**, then **Edit code**, delete
   everything, paste the whole of `worker/push-worker.js`, and **Deploy**.
4. Worker → **Settings → Bindings → Add → KV namespace**: variable name **`SUBS`**, namespace `apop-subs`.
5. Worker → **Settings → Variables and Secrets → Add**:
   - Type **Text**, name `ALLOWED_ORIGIN`, value `https://kkotsop.github.io` (no slash, no path)
   - Type **Secret**, name `ADMIN_TOKEN`, value = a long random password (the same one goes into GitHub below)
6. Copy the Worker address (looks like `https://apop-push.<your-name>.workers.dev`).
7. GitHub repository → **Settings → Secrets and variables → Actions → New repository secret**, add two secrets:
   - `PUSH_ADMIN_TOKEN` = the same value as `ADMIN_TOKEN` above
   - `VAPID_PRIVATE_KEY` = the private key created with `tools/gen_vapid.py`
8. Put the Worker address in `fixtures.json` → `"push"` → `"api"` (the public key is already there). The page then shows
   "Turn on notifications" in the bell sheet.

## How it fits together
- The page asks the phone for permission, subscribes using the **public** key and sends the subscription to the Worker
  (`POST /subscribe`, only from `ALLOWED_ORIGIN`).
- After every scrape the workflow runs `tools/notify.py`: if games changed it downloads the list (`GET /subs`, admin
  token), sends one encrypted push per person for the age groups they chose, and tells the Worker to forget
  subscriptions the phone services report as gone (`POST /prune`).
- `sw.js` (the site's service worker) shows the notification and opens the page when it is tapped.

## Rotating keys
Run `python tools/gen_vapid.py`, update `push.publicKey` in `fixtures.json` and the `VAPID_PRIVATE_KEY` secret.
Everyone has to turn notifications on again. Change `ADMIN_TOKEN` in both places to rotate the admin password.

## iPhone note
Apple only allows web notifications for pages added to the Home Screen (iOS 16.4 or newer). The page tells iPhone
visitors to do that first; Android and desktop browsers work straight from the page.
