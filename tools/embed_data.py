"""Copy fixtures.json into the inline data block of index.html (run by the workflow before publishing)."""
import json, re, sys
src, dst = sys.argv[1], sys.argv[2]
data = json.dumps(json.load(open(src, encoding="utf-8")), ensure_ascii=False).replace("<", "\\u003c")
html = open(dst, encoding="utf-8").read()
html, n = re.subn(r'(<script id="data" type="application/json">).*?(</script>)', lambda m: m.group(1) + data + m.group(2), html, count=1, flags=re.S)
assert n == 1, "data block not found"
open(dst, "w", encoding="utf-8").write(html)
