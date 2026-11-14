/* Reads one FIBA digital match sheet (the NBN23 PDF) and returns the game header plus ONE player's line.
 *
 * Input:  pages = [[{str, x, y, w}, ...], ...]  (the text items of each PDF page, as pdf.js gives them)
 *         who   = {surname, licence}             (kept only on the device, never in this file)
 *         ours  = "ΑΠΟΠ"                          (our club's name as it is printed on the sheet)
 * Output: {ok, flags[], game:{date,time,league,competition,home,away,hs,as,side}, player:{jersey,points,fouls,entries[]}}
 *
 * Only the chosen player's roster row and the running score are used. Other players' rows are looked at only to find
 * the right one and are never returned. Nothing is guessed: whatever does not add up is listed in `flags`.
 * Points come from the running score: each scoring entry carries the scorer's jersey next to the team's new total, and
 * the entry is worth (new total - previous total) points. That avoids reading the slash / dot / circle marks.
 */
(function (root) {
  "use strict";

  function norm(s) {
    return String(s == null ? "" : s).normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/\s+/g, " ").trim().toUpperCase();
  }

  function rowsOf(items, tol) {                       // group text items into lines (top to bottom), each sorted left to right
    var sorted = items.slice().sort(function (a, b) { return b.y - a.y || a.x - b.x; });
    var out = [];
    sorted.forEach(function (it) {
      var last = out[out.length - 1];
      if (last && Math.abs(last.y - it.y) <= (tol || 1.5)) last.items.push(it); else out.push({ y: it.y, items: [it] });
    });
    out.forEach(function (r) { r.items.sort(function (a, b) { return a.x - b.x; }); r.text = r.items.map(function (i) { return i.str; }).join(" ").replace(/\s+/g, " ").trim(); });
    return out;
  }

  function tidy(s) { return String(s).replace(/\s+([.,])/g, "$1").replace(/\s+/g, " ").trim(); }   // "Α . Ε . Λ ." -> "Α. Ε. Λ."

  function isInt(s) { return /^\d{1,3}$/.test(String(s).trim()); }

  /* the running-score grid: 4 blocks of (A total, B total) columns, rows 12pt apart */
  function runningScore(items) {
    var nums = items.filter(function (i) { return isInt(i.str); }).map(function (i) {
      return { v: Number(i.str.trim()), x: i.x, w: i.w || 0, y: i.y, cx: i.x + (i.w || 0) / 2 };
    });
    var cols = [];                                     // columns of consecutive totals
    nums.forEach(function (n) {
      for (var k = 0; k < cols.length; k++) if (Math.abs(cols[k].cx - n.cx) <= 2.2) { cols[k].items.push(n); return; }
      cols.push({ cx: n.cx, items: [n] });
    });
    var numberCols = [];
    cols.forEach(function (c) {
      c.items.sort(function (a, b) { return b.y - a.y; });
      var best = [], run = [];
      c.items.forEach(function (n) {
        var p = run[run.length - 1];
        if (p && n.v === p.v + 1 && p.y - n.y > 9 && p.y - n.y < 15) run.push(n); else run = [n];
        if (run.length > best.length) best = run.slice();
      });
      if (best.length >= 30) numberCols.push({ cx: c.cx, rows: best });
    });
    numberCols.sort(function (a, b) { return a.cx - b.cx; });
    if (numberCols.length !== 8) return null;
    var side = { A: [], B: [] }, last = { A: 0, B: 0 };
    for (var b = 0; b < 4; b++) {
      ["A", "B"].forEach(function (s, k) {
        var col = numberCols[b * 2 + k];
        col.rows.forEach(function (n) {
          var half = (n.w || 0) / 2;
          var marks = nums.filter(function (m) {
            if (Math.abs(m.y - n.y) > 2.5 || m.v > 99) return false;
            if (s === "A") return m.x + m.w <= n.cx - half - 1.5 && m.x + m.w >= n.cx - half - 20;   // right edge just left of the total
            return m.x >= n.cx + half + 1.5 && m.x <= n.cx + half + 20;                                // left edge just right of the total
          });
          if (marks.length === 1) side[s].push({ total: n.v, jersey: marks[0].v });
          else if (marks.length > 1) side[s].push({ total: n.v, jersey: null, many: true });
        });
      });
    }
    ["A", "B"].forEach(function (s) {
      side[s].sort(function (a, b) { return a.total - b.total; });
      var prev = 0;
      side[s].forEach(function (e) { e.pts = e.total - prev; prev = e.total; last[s] = e.total; });
    });
    return { A: side.A, B: side.B, last: last };
  }

  function parse(pages, who, ours) {
    var flags = [], res = { ok: false, flags: flags, game: null, player: null };
    var page = (pages && pages[0]) || [];
    var rows = rowsOf(page);
    var text = rows.map(function (r) { return r.text; });

    // ---- header
    var teams = null, comp = null, fin = { A: null, B: null };
    rows.forEach(function (r) {
      var m = !teams && /^Team A\s+(.+?)\s+Team B\s+(.+)$/.exec(r.text);
      if (m) teams = { A: tidy(m[1]), B: tidy(m[2]) };
      var c = !comp && /Competition\s+(.+?)\s+Date\s+(\d{1,2})\/(\d{1,2})\/(\d{4})(?:\s+Time\s+(\d{1,2}):(\d{2}))?/.exec(r.text);
      if (c) comp = { name: c[1].trim(), date: c[4] + "-" + ("0" + c[3]).slice(-2) + "-" + ("0" + c[2]).slice(-2), time: c[5] ? ("0" + c[5]).slice(-2) + ":" + c[6] : "" };
    });
    var fi = -1;
    rows.forEach(function (r, i) { if (fi < 0 && /Final Score/.test(r.text)) fi = i; });
    if (fi >= 0) for (var i = fi + 1; i < Math.min(rows.length, fi + 8); i++) {
      var m = /^([AB])\s+(\d{1,3})$/.exec(rows[i].text);
      if (m && fin[m[1]] === null) fin[m[1]] = Number(m[2]);
    }
    if (!teams) flags.push("team names not found");
    if (!comp) flags.push("competition / date not found");
    if (fin.A === null || fin.B === null) flags.push("final score not found");
    if (!teams || !comp) return res;
    var lg = /U\s*(14|16)/.exec(comp.name);
    var ourSide = norm(teams.A).indexOf(norm(ours)) > -1 ? "A" : (norm(teams.B).indexOf(norm(ours)) > -1 ? "B" : null);
    if (!ourSide) flags.push("our team is not on this sheet");

    // ---- her row in the roster (left part of the page)
    var left = rows.map(function (r) {
      var it = r.items.filter(function (i) { return i.x < 256; });
      return { y: r.y, items: it, text: it.map(function (i) { return i.str; }).join(" ").replace(/\s+/g, " ").trim() };
    }).filter(function (r) { return r.items.length; });
    var headB = null;
    left.forEach(function (r) { if (/^Team B\s+\S/.test(r.text) && (headB === null || r.y < headB)) headB = r.y; });
    var sn = norm(who && who.surname), lic = String((who && who.licence) || "").replace(/\D/g, "");
    var hits = left.filter(function (r) { return sn && norm(r.text).indexOf(sn) > -1 && /\(\d+\)/.test(r.text); });
    var licHits = lic ? hits.filter(function (r) { return r.text.indexOf("(" + lic + ")") > -1; }) : hits;
    var player = null, rowSide = null;
    if (hits.length === 0) flags.push("player not found on this sheet");
    else if (licHits.length === 0) flags.push("surname found but the licence number differs");
    else if (licHits.length > 1) flags.push("more than one roster line matches");
    else {
      var row = licHits[0];
      rowSide = headB !== null && row.y < headB ? "B" : "A";
      var rest = row.text.slice(norm(row.text).indexOf(sn) + sn.length);     // norm() keeps the length for Greek capitals
      var toks = rest.replace(/^[\s,]+/, "").split(/\s+/);
      var k = 0;
      while (k < toks.length && !/^\d{1,2}$/.test(toks[k])) k++;
      if (k >= toks.length) flags.push("jersey number not readable");
      else {
        var after = toks.slice(k + 1);
        var fouls = after.filter(function (t) { return /^(P|T|U|D)[0-9]?$/.test(t); }).length;
        player = { jersey: Number(toks[k]), fouls: fouls, licence: lic || null };
      }
    }
    if (ourSide && rowSide && ourSide !== rowSide) flags.push("roster side and team name disagree");
    var side = ourSide || rowSide;

    // ---- running score
    var rs = runningScore(page);
    if (!rs) flags.push("running score not readable");
    var entries = [];
    if (rs && side && player) {
      rs[side].forEach(function (e) {
        if (e.many || e.jersey === null) { flags.push("unreadable entry at " + e.total); return; }
        if (e.pts < 1 || e.pts > 3) flags.push("entry at " + e.total + " is worth " + e.pts + " points");
        if (e.jersey === player.jersey) entries.push({ total: e.total, pts: e.pts });
      });
      ["A", "B"].forEach(function (s) {
        if (fin[s] !== null && rs.last[s] !== fin[s]) flags.push("running score ends at " + rs.last[s] + " but the final score for " + s + " is " + fin[s]);
      });
      player.entries = entries;
      player.points = entries.reduce(function (t, e) { return t + e.pts; }, 0);
    }
    res.game = {
      date: comp.date, time: comp.time, competition: comp.name, league: lg ? "U" + lg[1] : "",
      home: teams.A, away: teams.B, hs: fin.A, as: fin.B, side: side
    };
    res.player = player;
    res.ok = !!(player && player.points !== undefined && flags.length === 0 && lg && fin.A !== null && fin.B !== null);
    return res;
  }

  var api = { parse: parse, norm: norm, rowsOf: rowsOf };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.SheetParser = api;
})(typeof self !== "undefined" ? self : this);
