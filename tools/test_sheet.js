/* Checks assets/sheet.js against real match sheets.
 *   node tools/test_sheet.js <folder-with-pdfs> <local.json>
 * local.json stays on your computer (tools/local/ is git-ignored): it holds her surname and licence and the figures
 * you checked by hand, so none of that is ever committed:
 *   {"surname":"...","licence":"...","ours":"ΑΠΟΠ","sheets":[{"file":"a.pdf","date":"2026-10-10","points":2,"fouls":1}]}
 * Needs the same PDF reader version the website ships, as a node package:  npm i pdfjs-dist@3.11.174  (run it in any folder,
 * then NODE_PATH=<that folder>/node_modules node tools/test_sheet.js ...). */
const fs = require("fs"), path = require("path");
const pdfjs = require("pdfjs-dist/legacy/build/pdf.js");
const P = require(path.join(__dirname, "..", "assets", "sheet.js"));
const [dir, cfgFile] = process.argv.slice(2);
if (!dir || !cfgFile) { console.error("usage: node tools/test_sheet.js <pdf-folder> <local.json>"); process.exit(2); }
const cfg = JSON.parse(fs.readFileSync(cfgFile, "utf8"));
(async () => {
  let bad = 0; const tot = {};
  for (const s of cfg.sheets) {
    const doc = await pdfjs.getDocument({ data: new Uint8Array(fs.readFileSync(path.join(dir, s.file))), isEvalSupported: false, useSystemFonts: true }).promise;
    const tc = await (await doc.getPage(1)).getTextContent();
    const r = P.parse([tc.items.map(i => ({ str: i.str, x: i.transform[4], y: i.transform[5], w: i.width }))], cfg, cfg.ours || "ΑΠΟΠ");
    const ok = r.ok && r.game.date === s.date && r.player.points === s.points && r.player.fouls === s.fouls;
    if (!ok) bad++;
    const lg = r.game ? r.game.league : "?";
    tot[lg] = tot[lg] || { g: 0, p: 0, f: 0 };
    if (r.ok) { tot[lg].g++; tot[lg].p += r.player.points; tot[lg].f += r.player.fouls; }
    console.log((ok ? "ok   " : "FAIL ") + s.file + "  " + (r.game ? r.game.date + " " + lg : "") + "  points " + (r.player && r.player.points) + "  fouls " + (r.player && r.player.fouls) + (r.flags.length ? "  flags: " + r.flags.join("; ") : ""));
  }
  console.log("totals", JSON.stringify(tot));
  if (cfg.totals && JSON.stringify(cfg.totals) !== JSON.stringify(tot)) { console.log("FAIL totals, expected " + JSON.stringify(cfg.totals)); bad++; }
  process.exit(bad ? 1 : 0);
})();
