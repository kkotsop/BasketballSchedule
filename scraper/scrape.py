#!/usr/bin/env python3
"""
Reads the ΑΠΟΠ fixtures from https://cbfweb.org/eCBF/pubgames.aspx and writes ../fixtures.json.

The federation page is an ASP.NET WebForms page: you pick Season, Competition and Phase in three
drop-downs and the games appear after the page posts itself back. This script does the same thing
a browser does: it opens the page, picks the three values (by their visible text, so internal ids
don't matter), posts the form back, and reads the game rows.

If anything looks wrong it stops WITHOUT touching fixtures.json, and saves what it saw in
scraper/debug/ so the problem can be diagnosed.
"""
import datetime as dt
import hashlib
import json
import os
import re
import sys
import unicodedata

import requests
from bs4 import BeautifulSoup

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIXTURES = os.path.join(ROOT, "fixtures.json")
OVERRIDES = os.path.join(ROOT, "overrides.json")
DEBUG = os.path.join(HERE, "debug")
URL = os.environ.get("CBF_URL", "https://cbfweb.org/eCBF/pubgames.aspx")

CONFIG = {
    # "Επιλογή Διοργάνωσης" for each age group we follow; label is shown on the website
    "competitions": [
        {"label": "U14", "competition": "Γυναικών U14 - Γ' Ομιλος"},
        {"label": "U16", "competition": "Γυναικών U16 - Γ' Ομιλος"},
    ],
    "phase": "Κανονική Περίοδος",
    "season": None,          # None = current season (e.g. 20262027). Or set it, e.g. "20262027"
    "team": "ΑΠΟΠ",          # only games of this team are kept
    # every team in the group, used to tell team cells from venue cells
    "teams": ["ΑΠΟΠ", "ΑΤΛΑΝΤΑΣ Πάφου", "ΑΧΙΛΛΕΑΣ Αγρού", "ΑΝΟΡΘΩΣΗ Αμμοχώστου",
              "ΑΡΗΣ Λεμεσού", "Α.Ε.Λ.", "ΑΠΟΛΛΩΝ Λεμεσού"],
}

UA = ("Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Mobile Safari/537.36")
DATE_RE = re.compile(r"(?<!\d)(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{4}|\d{2})(?!\d)")
TIME_RE = re.compile(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?!\d)")
SCORE_RE = re.compile(r"^\s*(\d{1,3})\s*[-–:]\s*(\d{1,3})\s*$")
DAY_RE = re.compile(r"^(ΔΕΥ|ΤΡΙ|ΤΕΤ|ΠΕΜ|ΠΑΡ|ΣΑΒ|ΚΥΡ|MON|TUE|WED|THU|FRI|SAT|SUN)[A-ZΑ-Ω]*\.?,?$")


LAST_TABLE = []                      # league table of the group that was read last
TEAMS = list(CONFIG["teams"])        # replaced by the real list of each group while reading it


def log(*a):
    print(*a, flush=True)


def norm(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.upper()
    for ch in "΄’´`‘":
        s = s.replace(ch, "'")
    s = s.replace(".", "").replace("\u00a0", " ")
    return re.sub(r"\s+", " ", s).strip()


def clean(s):
    return re.sub(r"\s+", " ", str(s or "").replace("\u00a0", " ")).strip(" \t-–—|")


DUMP_PREFIX = ""


def dump(name, text):
    os.makedirs(DEBUG, exist_ok=True)
    with open(os.path.join(DEBUG, DUMP_PREFIX + name), "w", encoding="utf-8") as f:
        f.write(text)


# ------------------------------------------------------------------ WebForms helpers

def form_fields(soup):
    form = soup.find("form")
    if form is None:
        raise RuntimeError("no <form> on the page")
    data = {}
    for inp in form.find_all("input"):
        name = inp.get("name")
        if not name:
            continue
        typ = (inp.get("type") or "text").lower()
        if typ in ("submit", "button", "image", "file", "reset"):
            continue
        if typ in ("checkbox", "radio"):
            if inp.has_attr("checked"):
                data[name] = inp.get("value", "on")
            continue
        data[name] = inp.get("value", "")
    for ta in form.find_all("textarea"):
        if ta.get("name"):
            data[ta["name"]] = ta.text
    for sel in form.find_all("select"):
        name = sel.get("name")
        if not name:
            continue
        opts = sel.find_all("option")
        chosen = [o for o in opts if o.has_attr("selected")] or opts[:1]
        if chosen:
            data[name] = chosen[0].get("value", chosen[0].get_text(strip=True))
    return data


def selects(soup):
    """[(name, [(value, text), ...]), ...] for every drop-down."""
    out = []
    for sel in soup.find_all("select"):
        opts = [(o.get("value", o.get_text(strip=True)), o.get_text(" ", strip=True)) for o in sel.find_all("option")]
        if sel.get("name"):
            out.append((sel["name"], opts))
    return out


def find_select(soup, kind):
    for name, opts in selects(soup):
        texts = [norm(t) for _, t in opts]
        if kind == "season" and sum(bool(re.fullmatch(r"\d{8}|\d{4}\s*[-/]\s*\d{4}", t)) for t in texts) >= 2:
            return name, opts
        if kind == "competition" and any("ΟΜΙΛΟΣ" in t for t in texts):
            return name, opts
        if kind == "phase" and any("ΚΑΝΟΝΙΚΗ ΠΕΡΙΟΔΟΣ" in t for t in texts):
            return name, opts
    return None, []


def pick(opts, wanted, kind):
    w = norm(wanted)
    for value, text in opts:
        if norm(text) == w:
            return value, text
    if kind == "competition":                        # tolerate small spelling differences
        tokens = [t for t in re.split(r"[\s\-]+", w) if t]
        for value, text in opts:
            n = norm(text)
            if all(t in n for t in tokens) and "ΑΝΔΡΩΝ" not in n:
                return value, text
    raise RuntimeError("option %r not found in the %s drop-down (found: %s)" %
                       (wanted, kind, ", ".join(t for _, t in opts[:40])))


def current_season():
    today = dt.date.today()
    y = today.year if today.month >= 8 else today.year - 1
    return "%d%d" % (y, y + 1)


def post(session, soup, changes, target, extra=None):
    data = form_fields(soup)
    data.update(changes)
    data["__EVENTTARGET"] = target
    data["__EVENTARGUMENT"] = ""
    if extra:
        data.update(extra)
    r = session.post(URL, data=data, headers={"Referer": URL}, timeout=60)
    r.raise_for_status()
    return r.text


# ------------------------------------------------------------------ reading the game rows

def match_team(cell):
    n = norm(cell)
    if not n:
        return None
    for t in TEAMS:
        nt = norm(t)
        if n == nt or (len(nt) >= 4 and nt in n and len(n) <= len(nt) + 14):
            return t
    return None


def candidate_rows(soup):
    """Cells of every innermost table row that contains a date."""
    rows = []
    for tr in soup.find_all("tr"):
        if tr.find("tr"):
            continue
        cells = [clean(c.get_text(" ", strip=True)) for c in tr.find_all(["td", "th"])]
        if any(DATE_RE.search(c) for c in cells) and len([c for c in cells if c]) >= 3:
            rows.append(cells)
    if rows:
        return rows
    # fallback: card/list layouts made of <div>/<li>
    seen = set()
    for node in soup.find_all(string=DATE_RE):
        block = node.parent
        for _ in range(4):
            parts = [clean(x) for x in block.stripped_strings]
            if 4 <= len(parts) <= 14:
                break
            block = block.parent if block.parent else block
        parts = [clean(x) for x in block.stripped_strings]
        key = tuple(parts)
        if 3 <= len(parts) <= 16 and key not in seen:
            seen.add(key)
            rows.append(parts)
    return rows


def parse_row(cells):
    date = time = None
    score = None
    rest = []
    for cell in cells:
        c = cell
        m = DATE_RE.search(c)
        if m and not date:
            y = int(m.group(3))
            y += 2000 if y < 100 else 0
            try:
                date = dt.date(y, int(m.group(2)), int(m.group(1))).isoformat()
            except ValueError:
                return None
            c = clean(c[:m.start()] + " " + c[m.end():])
        m = TIME_RE.search(c)
        if m and not time:
            time = "%02d:%s" % (int(m.group(1)), m.group(2))
            c = clean(c[:m.start()] + " " + c[m.end():])
        c = " ".join(w for w in c.split() if not DAY_RE.match(norm(w)))
        if SCORE_RE.match(c):
            if score is None:
                score = tuple(int(x) for x in SCORE_RE.match(c).groups())
            continue
        c = clean(c)
        if len(c) > 1 and not re.fullmatch(r"\d{1,3}[ΗηΑα'΄]?\.?", c):
            rest.append(c)
    if not date:
        return None

    team_idx = [i for i, c in enumerate(rest) if match_team(c)]
    if len(team_idx) >= 2:
        hi, ai = team_idx[0], team_idx[1]
    else:                                              # unknown opponent name: use the neighbour of ours
        ours = [i for i, c in enumerate(rest) if norm(CONFIG["team"]) in norm(c)]
        if not ours:
            return None
        i = ours[0]
        nb = [j for j in (i + 1, i - 1) if 0 <= j < len(rest)]
        if not nb:
            return None
        j = nb[0]
        hi, ai = (i, j) if i < j else (j, i)
    venue = clean(" ".join(c for k, c in enumerate(rest) if k not in (hi, ai) and not re.fullmatch(r"[\d\W]+", c)))
    # the federation puts the game code, the score and a "|" in the same cell as the venue
    m = re.search(r"(?<![\d-])(\d{1,3})\s*-\s*(\d{1,3})(?![\d-])", venue)
    if m and score is None:
        score = (int(m.group(1)), int(m.group(2)))
    venue = re.sub(r"\b[A-Z]{1,4}\d*[A-Z]?-\d+-\d+\b", " ", venue)
    venue = re.sub(r"(?<![\d-])\d{1,3}\s*-\s*\d{1,3}(?![\d-])", " ", venue).replace("|", " ")
    venue = clean(venue)
    return {
        "date": date, "time": time or "", "home": rest[hi], "away": rest[ai], "venue": venue,
        "hs": "" if score is None else str(score[0]), "as": "" if score is None else str(score[1]),
    }


def games_from(soup):
    out = []
    for cells in candidate_rows(soup):
        g = parse_row(cells)
        if g and (norm(CONFIG["team"]) in norm(g["home"]) or norm(CONFIG["team"]) in norm(g["away"])):
            out.append(g)
    seen, uniq = set(), []
    for g in out:
        k = (g["date"], norm(g["home"]), norm(g["away"]))
        if k not in seen:
            seen.add(k)
            uniq.append(g)
    return uniq


# ------------------------------------------------------------------ main flow

def group_teams(soup):
    """Team names from the standings table (the table with the ΟΜΑΔΑ / ΒΑΘΜΟΙ header)."""
    for t in soup.find_all("table"):
        if t.find("table"):
            continue
        txt = t.get_text(" ", strip=True)
        if "ΟΜΑΔΑ" in txt and "ΒΑΘΜΟΙ" in txt:
            names = []
            for tr in t.find_all("tr")[1:]:
                cells = [clean(c.get_text(" ", strip=True)) for c in tr.find_all(["td", "th"])]
                cells = [c for c in cells if c and not re.fullmatch(r"[\d\W]+", c)]
                if cells and cells[0] not in names:
                    names.append(cells[0])
            if len(names) >= 3:
                return names
    return []


def standings_from(html):
    """League table. The federation writes its cells without closing tags, so read the raw HTML.
    Row layout: rank, logo, team, then 12 numbers: played, wins, losses, forfeits, points, for, against, diff,
    wins home, wins away, losses home, losses away. Blank (before the first game) counts as 0."""
    i = html.find("acTBLTopLine")
    if i < 0:
        return []
    end = html.find("</table>", i)
    chunk = html[i:end if end > i else len(html)]
    rows = []
    for tr in chunk.split("<tr")[2:]:                      # [0] table tag, [1] header row
        cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip() for c in re.split(r"<td[^>]*>", tr)[1:]]
        name_i = next((k for k, c in enumerate(cells) if c and not re.fullmatch(r"[\d\W]+", c)), None)
        if name_i is None or len(cells) < name_i + 13:
            continue
        nums = []
        for c in cells[name_i + 1:name_i + 13]:
            m = re.search(r"-?\d+", c)
            nums.append(int(m.group()) if m else 0)
        rows.append({"team": cells[name_i], "p": nums[0], "w": nums[1], "l": nums[2], "pts": nums[4],
                     "pf": nums[5], "pa": nums[6], "diff": nums[7]})
    return rows


def fetch_games(competition):
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "el,en;q=0.8"})
    r = s.get(URL, timeout=60)
    r.raise_for_status()
    html = r.text
    dump("step0-initial.html", html)
    soup = BeautifulSoup(html, "html.parser")
    games = games_from(soup)                          # in case the page already lists something
    steps = [("season", CONFIG["season"] or current_season()),
             ("competition", competition),
             ("phase", CONFIG["phase"])]
    chosen = {}
    table = []
    for n, (kind, wanted) in enumerate(steps, 1):
        name, opts = find_select(soup, kind)
        if not name:
            log("  (no %s drop-down found, skipping)" % kind)
            continue
        value, text = pick(opts, wanted, kind)
        log("  %s -> %r (value %r)" % (kind, text, value))
        chosen[name] = value
        html = post(s, soup, dict(chosen), name)
        dump("step%d-after-%s.html" % (n, kind), html)
        soup = BeautifulSoup(html, "html.parser")
        # pages remember earlier choices; keep sending them in case they were reset
        if kind == "competition":
            table = standings_from(html) or table
            global TEAMS
            TEAMS = [r["team"] for r in table] or group_teams(soup) or list(CONFIG["teams"])
            log("  teams: %s" % ", ".join(TEAMS))
        found = games_from(soup)
        if found:                                     # the list can appear before the last drop-down is set;
            games = found                             # never let a later, empty page throw it away
            log("  %d game(s) for %s after %s" % (len(found), CONFIG["team"], kind))
            if kind != "season":
                break
    if not games:                                     # maybe the page needs a Search button
        buttons = [b for b in soup.find_all(["input", "button"])
                   if (b.get("type") or "").lower() in ("submit", "button") and b.get("name")]
        for b in buttons:
            log("  trying button %r" % (b.get("value") or b.get_text(strip=True)))
            html = post(s, soup, dict(chosen), "", {b["name"]: b.get("value", "")})
            dump("step9-after-button.html", html)
            soup2 = BeautifulSoup(html, "html.parser")
            games = games_from(soup2)
            if games:
                break
    global LAST_TABLE
    LAST_TABLE = table
    return games


def apply_overrides(games):
    try:
        with open(OVERRIDES, encoding="utf-8") as f:
            rules = json.load(f)
    except (OSError, ValueError):
        return games
    for rule in rules if isinstance(rules, list) else []:
        for g in games:
            if rule.get("date") != g["date"]:
                continue
            opp = rule.get("opponent")
            if opp and norm(opp) not in norm(g["home"] + " " + g["away"]):
                continue
            for k in ("time", "venue"):
                if rule.get(k):
                    g[k] = rule[k]
    return games


def main():
    try:
        with open(FIXTURES, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {"team": CONFIG["team"], "league": "Γυναικών", "group": "Γ΄ Όμιλος", "places": {}}
    old_games = data.get("games") or []
    all_games, failed = [], []
    standings = dict(data.get("standings") or {})      # keep the old table of a group that could not be read
    for comp in CONFIG["competitions"]:
        label = comp["label"]
        global DUMP_PREFIX
        DUMP_PREFIX = label + "-"
        log("Reading", URL, "for", comp["competition"])
        try:
            games = fetch_games(comp["competition"])
        except Exception as e:                        # network, layout change, missing option...
            log("FAILED (%s):" % label, e)
            dump("error-%s.txt" % label, repr(e))
            games = []
        if not games:
            log("FAILED (%s): no games for %s were found." % (label, CONFIG["team"]))
            failed.append(label)
            all_games += [g for g in old_games if (g.get("league") or "U14") == label]   # keep what we had
            continue
        games = apply_overrides(games)
        for g in games:
            g["league"] = label
            g["id"] = hashlib.sha1(("%s|%s|%s|%s" % (label, g["date"], norm(g["home"]), norm(g["away"]))).encode()).hexdigest()[:8]
        all_games += games
        if LAST_TABLE:
            standings[label] = LAST_TABLE
        log("OK (%s): %d games for %s, %d teams in the table" % (label, len(games), CONFIG["team"], len(LAST_TABLE)))
    if len(failed) == len(CONFIG["competitions"]):
        return 1
    all_games.sort(key=lambda g: (g["date"], g["time"] or "99:99"))
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    old = json.dumps(old_games, ensure_ascii=False, sort_keys=True)
    data["games"] = all_games
    if old != json.dumps(all_games, ensure_ascii=False, sort_keys=True) or not data.get("updated"):
        data["updated"] = now
    data["checked"] = now
    data["standings"] = standings
    data["league"] = "Γυναικών"
    data["source"] = URL
    with open(FIXTURES, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")
    for g in all_games:
        log("  %s %s %-5s %s - %s | %s | %s-%s" % (g.get("league"), g["date"], g["time"], g["home"], g["away"], g["venue"], g["hs"], g["as"]))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
