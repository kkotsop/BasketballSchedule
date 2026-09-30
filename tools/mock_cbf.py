# A stand-in for the federation page: ASP.NET-style form, three drop-downs that post back, session cookie,
# event validation, and the games table only after the right three choices are posted.
import base64, html, json, os, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

VARIANT = os.environ.get("VARIANT", "table")
EMPTY = os.environ.get("MOCK_EMPTY") == "1"
SEASONS = [("0", "--- Επιλογή ---"), ("11", "20262027"), ("10", "20252026"), ("9", "20242025")]
COMPS = [("0", "--- Επιλογή Διοργάνωσης ---"), ("201", "Ανδρών U14 - Γ' Ομιλος"), ("305", "Γυναικών U14 - Α' Ομιλος"),
         ("306", "Γυναικών U14 - Β' Ομιλος"), ("307", "Γυναικών U14 - Γ' Ομιλος"), ("308", "Γυναικών U16 - Α' Ομιλος")]
PHASES = [("0", "--- Φάση ---"), ("1", "Κανονική Περίοδος"), ("2", "Playoffs"), ("3", "PlayOut")]
G = [
 ("26/09/2026", "17:00", "ΑΠΟΠ", "Α.Ε.Λ.", "Αίθ. Α' Λυκείου Ακης Κλεάνθους", "52 - 44"),
 ("03/10/2026", "12:30", "ΑΝΟΡΘΩΣΗ Αμμοχώστου", "ΑΠΟΠ", "Λύκ. Αγ. Φύλας", ""),
 ("03/10/2026", "", "ΑΠΟΛΛΩΝ Λεμεσού", "ΑΡΗΣ Λεμεσού", "Λύκ. Αγ. Σπυρίδωνα", ""),
 ("10/10/2026", "", "ΑΠΟΠ", "ΑΠΟΛΛΩΝ Λεμεσού", "Αίθ. Α' Λυκείου Ακης Κλεάνθους", ""),
 ("17/10/2026", "", "ΑΡΗΣ Λεμεσού", "ΑΠΟΠ", "Λύκ. Αγ. Σπυρίδωνα", ""),
 ("31/10/2026", "", "ΑΠΟΠ", "ΑΧΙΛΛΕΑΣ Αγρού", "Αίθ. Α' Λυκείου Ακης Κλεάνθους", ""),
 ("07/11/2026", "", "Α.Ε.Λ.", "ΑΠΟΠ", "Αίθ. Νίκος Σολομωνίδης", ""),
 ("14/11/2026", "", "ΑΠΟΠ", "ΑΤΛΑΝΤΑΣ Πάφου", "Αίθ. Α' Λυκείου Ακης Κλεάνθους", ""),
]
DAYS = ["Δευ", "Τρι", "Τετ", "Πεμ", "Παρ", "Σαβ", "Κυρ"]
VALID = "EVAL-7f3a"

def opts(lst, sel):
    return "".join('<option %svalue="%s">%s</option>' % ('selected="selected" ' if v == sel else "", v, html.escape(t)) for v, t in lst)

def results(form):
    ok = form.get("ctl00$ContentPlaceHolder1$ddlSeason") == "11" and form.get("ctl00$ContentPlaceHolder1$ddlComp") == "307" \
         and form.get("ctl00$ContentPlaceHolder1$ddlPhase") == "1"
    if not ok or EMPTY:
        return '<div id="ctl00_ContentPlaceHolder1_pnl"></div>'
    import datetime
    if VARIANT == "table":
        rows = "".join("<tr><td>%d</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" %
                       (i + 1, d, t, h, a, v, s) for i, (d, t, h, a, v, s) in enumerate(G))
        return ('<table class="gv" id="grid"><tr><th>Αγ.</th><th>Ημερομηνία</th><th>Ώρα</th><th>Γηπεδούχος</th><th>Φιλοξενούμενος</th>'
                '<th>Γήπεδο</th><th>Αποτέλεσμα</th></tr>' + rows + '</table>')
    if VARIANT == "combined":
        def dd(d):
            dtm = datetime.datetime.strptime(d, "%d/%m/%Y"); return DAYS[dtm.weekday()] + " " + d
        rows = "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" %
                       ((dd(d) + " " + t).strip(), h, a, v, s or "-") for (d, t, h, a, v, s) in G)
        return '<table id="grid"><tr><th>Ημ/νία</th><th>Γηπεδούχος</th><th>Φιλοξενούμενος</th><th>Γήπεδο</th><th>Σκορ</th></tr>' + rows + '</table>'
    cards = "".join('<div class="card"><span>%s %s</span><b>%s</b><b>%s</b><i>%s</i><em>%s</em></div>' % (d, t, h, a, v, s) for (d, t, h, a, v, s) in G)
    return '<div id="list">' + cards + '</div>'

def page(form):
    s, c, p = (form.get("ctl00$ContentPlaceHolder1$ddlSeason", "0"), form.get("ctl00$ContentPlaceHolder1$ddlComp", "0"),
               form.get("ctl00$ContentPlaceHolder1$ddlPhase", "0"))
    vs = base64.b64encode(json.dumps([s, c, p]).encode()).decode()
    return f"""<!DOCTYPE html><html><head><title>eCBF</title></head><body>
<form method="post" action="./pubgames.aspx" id="aspnetForm">
<div class="aspNetHidden"><input type="hidden" name="__EVENTTARGET" id="__EVENTTARGET" value="" />
<input type="hidden" name="__EVENTARGUMENT" id="__EVENTARGUMENT" value="" />
<input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE" value="{vs}" />
<input type="hidden" name="__VIEWSTATEGENERATOR" id="__VIEWSTATEGENERATOR" value="ABC123" />
<input type="hidden" name="__EVENTVALIDATION" id="__EVENTVALIDATION" value="{VALID}" /></div>
<img src="images/ajax-loader.gif">
<select name="ctl00$ContentPlaceHolder1$ddlSeason" onchange="javascript:setTimeout('__doPostBack(\\'ctl00$ContentPlaceHolder1$ddlSeason\\',\\'\\')', 0)" id="s">{opts(SEASONS, s)}</select>
<select name="ctl00$ContentPlaceHolder1$ddlComp" onchange="javascript:setTimeout('__doPostBack(\\'ctl00$ContentPlaceHolder1$ddlComp\\',\\'\\')', 0)" id="c">{opts(COMPS, c)}</select>
<select name="ctl00$ContentPlaceHolder1$ddlPhase" onchange="javascript:setTimeout('__doPostBack(\\'ctl00$ContentPlaceHolder1$ddlPhase\\',\\'\\')', 0)" id="p">{opts(PHASES, p)}</select>
<input type="text" name="ctl00$search" value="" />
{results(form)}
</form></body></html>"""

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, body, code=200, cookie=False):
        b = body.encode(); self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(b)))
        if cookie: self.send_header("Set-Cookie", "ASP.NET_SessionId=abc123; path=/; HttpOnly")
        self.end_headers(); self.wfile.write(b)
    def do_GET(self): self._send(page({}), cookie=True)
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0)); form = {k: v[0] for k, v in parse_qs(self.rfile.read(n).decode()).items()}
        if "ASP.NET_SessionId=abc123" not in (self.headers.get("Cookie") or ""): return self._send("no session", 500)
        if form.get("__EVENTVALIDATION") != VALID or not form.get("__VIEWSTATE"): return self._send("bad validation", 500)
        if not form.get("__EVENTTARGET"): return self._send(page(form))
        self._send(page(form))

HTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
