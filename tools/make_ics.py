"""Build subscribable calendar feeds from fixtures.json.

Usage: python tools/make_ics.py fixtures.json OUT_DIR
Writes OUT_DIR/apop.ics (all games), apop-u14.ics and apop-u16.ics. Every game keeps the same UID forever, so when a
tip-off time is published or a game moves, calendars that subscribed update the existing event instead of adding a new one.
Tip-off times are Cyprus local time and are written as UTC, so they are right wherever the phone is.
"""
import datetime as dt
import json
import os
import sys
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Nicosia")
TEAM = "ΑΠΟΠ"


def esc(t):
    return str(t or "").replace("\\", "\\\\").replace(";", "\;").replace(",", "\\,").replace("\r", "").replace("\n", "\\n")


def fold(line):
    """RFC 5545: lines longer than 75 octets are folded."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    out, cur = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        limit = 75 if not out else 74
        if len(cur) + len(b) > limit:
            out.append(cur.decode("utf-8"))
            cur = b
        else:
            cur += b
    out.append(cur.decode("utf-8"))
    return "\r\n ".join(out)


def utc(d):
    return d.astimezone(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def maps_url(game, places):
    venue = (game.get("venue") or "").strip()
    if not venue:
        return ""
    key = "".join(ch for ch in venue.lower() if ch.isalnum())
    pid = next((v for k, v in (places or {}).items() if "".join(c for c in k.lower() if c.isalnum()) == key), "")
    if pid.startswith("https://"):
        return pid
    from urllib.parse import quote
    if pid and not pid.startswith("ChIJ"):
        return "https://www.google.com/maps/search/?api=1&query=" + quote(pid)
    url = "https://www.google.com/maps/search/?api=1&query=" + quote(venue if pid else venue + " Cyprus")
    return url + ("&query_place_id=" + quote(pid) if pid else "")


def title(game):
    home = TEAM in (game.get("home") or "")
    opp = game["away"] if home else game["home"]
    t = "%s %s %s (%s)" % (TEAM, "vs" if home else "at", opp, game.get("league") or "")
    hs, as_ = game.get("hs"), game.get("as")
    if hs not in (None, "") and as_ not in (None, "") and (int(hs), int(as_)) != (0, 0):
        mine, theirs = (int(hs), int(as_)) if home else (int(as_), int(hs))
        t += " %d-%d" % (mine, theirs)
    if not game.get("time"):
        t += " [time TBC]"
    return t


def event(game, data, stamp):
    y, m, d = (int(x) for x in game["date"].split("-"))
    lines = ["BEGIN:VEVENT", "UID:%s@apop-schedule" % game["id"], "DTSTAMP:" + stamp, "LAST-MODIFIED:" + stamp]
    if game.get("time"):
        hh, mm = (int(x) for x in game["time"].split(":"))
        start = dt.datetime(y, m, d, hh, mm, tzinfo=TZ)
        lines += ["DTSTART:" + utc(start), "DTEND:" + utc(start + dt.timedelta(minutes=90))]
    else:
        day = dt.date(y, m, d)
        lines += ["DTSTART;VALUE=DATE:" + day.strftime("%Y%m%d"), "DTEND;VALUE=DATE:" + (day + dt.timedelta(days=1)).strftime("%Y%m%d")]
    lines.append("SUMMARY:" + esc(title(game)))
    if game.get("venue"):
        lines.append("LOCATION:" + esc(game["venue"]))
    desc = "%s · %s" % (game.get("league") or "", data.get("group") or "")
    url = maps_url(game, data.get("places"))
    if url:
        desc += "\nDirections: " + url
    if data.get("site"):
        desc += "\nSchedule: " + data["site"]
    lines.append("DESCRIPTION:" + esc(desc))
    lines += ["STATUS:CONFIRMED", "TRANSP:OPAQUE"]
    if game.get("time"):
        lines += ["BEGIN:VALARM", "TRIGGER:-PT90M", "ACTION:DISPLAY", "DESCRIPTION:Tip-off in 90 minutes", "END:VALARM"]
    lines.append("END:VEVENT")
    return lines


def calendar(games, data, name):
    stamp = (data.get("updated") or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")).replace("-", "").replace(":", "")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//APOP schedule//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
             "X-WR-CALNAME:" + esc(name), "X-WR-TIMEZONE:Asia/Nicosia",
             "REFRESH-INTERVAL;VALUE=DURATION:PT6H", "X-PUBLISHED-TTL:PT6H"]
    for g in sorted(games, key=lambda g: (g["date"], g.get("time") or "99:99")):
        lines += event(g, data, stamp)
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(l) for l in lines) + "\r\n"


def main():
    src, out = sys.argv[1], sys.argv[2]
    data = json.load(open(src, encoding="utf-8"))
    games = data.get("games") or []
    os.makedirs(out, exist_ok=True)
    feeds = {"apop.ics": ("ΑΠΟΠ U14 & U16", games),
             "apop-u14.ics": ("ΑΠΟΠ U14", [g for g in games if (g.get("league") or "U14") == "U14"]),
             "apop-u16.ics": ("ΑΠΟΠ U16", [g for g in games if g.get("league") == "U16"])}
    for fn, (name, gs) in feeds.items():
        with open(os.path.join(out, fn), "w", encoding="utf-8", newline="") as f:
            f.write(calendar(gs, data, name))
        print("wrote %s (%d games)" % (fn, len(gs)))


if __name__ == "__main__":
    main()
