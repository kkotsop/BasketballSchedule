"""Send one push notification (through ntfy.sh) when the schedule changes.

Usage: python tools/notify.py BEFORE.json AFTER.json [--dry-run]
The topic is read from AFTER.json -> "ntfy". Anyone who knows the topic can subscribe (that is how parents join),
so it is long and random; it is not a secret. Nothing is sent when there are no changes or no topic.
Changes reported: a new game, a tip-off time set or changed, a venue change, a game moved to another day, a result.
"""
import datetime as dt
import json
import sys
import urllib.request

TEAM = "ΑΠΟΠ"
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MAX_LINES = 8


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
    return "%s %s %s" % (TEAM, "vs" if home else "at", g["away"] if home else g["home"])


def diff(before, after):
    old = {key(g): g for g in before}
    lines = []
    for g in after:
        o = old.get(key(g))
        tag = "%s · " % (g.get("league") or "")
        if o is None:
            lines.append("%sNew game: %s, %s" % (tag, label(g), when(g)))
            continue
        if o["date"] != g["date"]:
            lines.append("%sGame moved: %s, %s -> %s" % (tag, label(g), when(o), when(g)))
        elif (o.get("time") or "") != (g.get("time") or ""):
            if not o.get("time"):
                lines.append("%sTip-off set: %s, %s" % (tag, label(g), when(g)))
            elif not g.get("time"):
                lines.append("%sTip-off time removed: %s, %s" % (tag, label(g), when(g)))
            else:
                lines.append("%sTime changed: %s, %s -> %s" % (tag, label(g), o["time"], g["time"]))
        if (o.get("venue") or "") != (g.get("venue") or "") and g.get("venue"):
            lines.append("%sVenue: %s, %s" % (tag, label(g), g["venue"]))
        if played(g) and not played(o):
            home = TEAM in g["home"]
            mine, theirs = (int(g["hs"]), int(g["as"])) if home else (int(g["as"]), int(g["hs"]))
            lines.append("%sResult: %s %d-%d (%s)" % (tag, label(g), mine, theirs, "win" if mine > theirs else "loss" if mine < theirs else "draw"))
    return lines


def send(topic, lines, site):
    body = "\n".join(lines[:MAX_LINES]) + ("\n+%d more" % (len(lines) - MAX_LINES) if len(lines) > MAX_LINES else "")
    req = urllib.request.Request("https://ntfy.sh/" + topic, data=body.encode("utf-8"), method="POST")
    req.add_header("Title", "APOP schedule update")     # header values must be ASCII
    req.add_header("Tags", "basketball")
    if site:
        req.add_header("Click", site)
    urllib.request.urlopen(req, timeout=20).read()


def main():
    before = json.load(open(sys.argv[1], encoding="utf-8")).get("games") or []
    after_data = json.load(open(sys.argv[2], encoding="utf-8"))
    lines = diff(before, after_data.get("games") or [])
    if not lines:
        print("no schedule changes")
        return 0
    print("\n".join(lines))
    topic = after_data.get("ntfy")
    if "--dry-run" in sys.argv or not topic:
        print("(not sent: %s)" % ("dry run" if "--dry-run" in sys.argv else "no ntfy topic set"))
        return 0
    try:
        send(topic, lines, after_data.get("site"))
        print("notification sent")
    except Exception as e:                                # never fail the site update because of a notification
        print("could not send notification:", e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
