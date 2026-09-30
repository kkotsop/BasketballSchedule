"""Tell people who turned on notifications when the schedule changes (Web Push, no app needed).

Usage: python tools/notify.py BEFORE.json AFTER.json [--dry-run]

Needs (from the workflow): env VAPID_PRIVATE_KEY and PUSH_ADMIN_TOKEN, and AFTER.json -> "push" -> {"api", "publicKey"}.
Subscriptions are kept by the small Cloudflare Worker in worker/push-worker.js; this script downloads the list,
sends one notification per person (only for the age groups they chose) and asks the Worker to forget dead ones.
Changes reported: a new game, a tip-off time set or changed, a venue change, a game moved, a result.
Nothing is sent when nothing changed or when push is not set up; a failure here never fails the site update.
"""
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request

TEAM = "ΑΠΟΠ"
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MAX_LINES = 4


def key(g):
    return (g.get("league") or "U14", g["home"], g["away"])


def when(g):
    y, m, d = (int(x) for x in g["date"].split("-"))
    day = "%s %d %s" % (DAYS[dt.date(y, m, d).weekday()], d, MONTHS[m - 1])
    return day + (" " + g["time"] if g.get("time") else "")


def played(g):
    try:
        return (int(g.get("hs")), int(g.get("as"))) != (0, 0)
    except (TypeError, ValueError):
        return False


def label(g):
    home = TEAM in g["home"]
    return "%s %s" % ("vs" if home else "at", g["away"] if home else g["home"])


def diff(before, after):
    """List of (league, text)."""
    old = {key(g): g for g in before}
    out = []
    for g in after:
        o = old.get(key(g))
        lg = g.get("league") or "U14"
        if o is None:
            out.append((lg, "New game %s, %s" % (label(g), when(g))))
            continue
        if o["date"] != g["date"]:
            out.append((lg, "Game moved %s: %s → %s" % (label(g), when(o), when(g))))
        elif (o.get("time") or "") != (g.get("time") or ""):
            if not o.get("time"):
                out.append((lg, "Tip-off set %s, %s" % (label(g), when(g))))
            elif not g.get("time"):
                out.append((lg, "Tip-off time removed %s, %s" % (label(g), when(g))))
            else:
                out.append((lg, "Time changed %s: %s → %s" % (label(g), o["time"], g["time"])))
        if (o.get("venue") or "") != (g.get("venue") or "") and g.get("venue"):
            out.append((lg, "Venue %s: %s" % (label(g), g["venue"])))
        if played(g) and not played(o):
            home = TEAM in g["home"]
            mine, theirs = (int(g["hs"]), int(g["as"])) if home else (int(g["as"]), int(g["hs"]))
            out.append((lg, "Result %s: %d-%d (%s)" % (label(g), mine, theirs, "win" if mine > theirs else "loss" if mine < theirs else "draw")))
    return out


def contact(site):
    """VAPID contact: the site's origin (no path), e.g. https://kkotsop.github.io"""
    u = urllib.parse.urlparse(site or "")
    return "%s://%s" % (u.scheme, u.netloc) if u.scheme == "https" and u.netloc else "https://example.com"


def api(base, path, token, body=None):
    req = urllib.request.Request(base.rstrip("/") + path, method="POST" if body is not None else "GET",
                                 data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode() or "null")


def payload_for(sub, changes, site):
    lines = [f"{lg} · {t}" if len(sub.get("lg") or []) != 1 else t for lg, t in changes if not sub.get("lg") or lg in sub["lg"]]
    if not lines:
        return None
    body = "\n".join(lines[:MAX_LINES]) + ("\n+%d more" % (len(lines) - MAX_LINES) if len(lines) > MAX_LINES else "")
    return {"title": "ΑΠΟΠ schedule update", "body": body, "url": site or "./", "tag": "apop-update"}


def main():
    before = json.load(open(sys.argv[1], encoding="utf-8")).get("games") or []
    after = json.load(open(sys.argv[2], encoding="utf-8"))
    changes = diff(before, after.get("games") or [])
    if not changes:
        print("no schedule changes")
        return 0
    for lg, t in changes:
        print("%s · %s" % (lg, t))
    push = after.get("push") or {}
    token, private = os.environ.get("PUSH_ADMIN_TOKEN"), os.environ.get("VAPID_PRIVATE_KEY")
    if "--dry-run" in sys.argv or not (push.get("api") and token and private):
        print("(not sent: %s)" % ("dry run" if "--dry-run" in sys.argv else "push notifications are not set up yet"))
        return 0
    try:
        from pywebpush import WebPushException, webpush
        subs = api(push["api"], "/subs", token) or []
        sent, gone = 0, []
        for sub in subs:
            data = payload_for(sub, changes, after.get("site"))
            if not data:
                continue
            try:
                webpush(subscription_info={"endpoint": sub["endpoint"], "keys": sub["keys"]}, data=json.dumps(data, ensure_ascii=False),
                        vapid_private_key=private, vapid_claims={"sub": contact(after.get("site"))}, ttl=86400, timeout=15)
                sent += 1
            except WebPushException as e:
                status = getattr(e.response, "status_code", None)
                if status in (404, 410):
                    gone.append(sub["endpoint"])
                print("push failed (%s): %s" % (status, str(e)[:120]))
            except Exception as e:
                print("push failed:", str(e)[:120])
        if gone:
            api(push["api"], "/prune", token, {"endpoints": gone})
        print("notifications sent: %d, removed dead subscriptions: %d" % (sent, len(gone)))
    except Exception as e:                                # never fail the site update because of a notification
        print("could not send notifications:", str(e)[:200])
    return 0


if __name__ == "__main__":
    sys.exit(main())
