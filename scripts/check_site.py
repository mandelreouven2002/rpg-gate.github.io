"""
Checks run on every pull request (and locally: python3 scripts/check_site.py).
  1. The data files are valid JSON.
  2. The site builds (scripts/prerender.py runs without errors).
  3. No internal link or image points to a file that does not exist.
Exits with an error when something is wrong, so the pull request is marked red.
"""
import json, os, re, subprocess, sys, pathlib
from urllib.parse import unquote

ROOT = pathlib.Path(__file__).resolve().parent.parent
errors = []

# 1. data
for f in ["data.json", "catalog/catalog.json"]:
    p = ROOT / f
    if not p.exists():
        continue
    try:
        json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        errors.append(f"{f}: JSON לא תקין: {e}")

# 2. build
if not errors:
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "prerender.py")], capture_output=True, text=True)
    if r.returncode != 0:
        errors.append("הבנייה נכשלה:\n" + r.stderr[-2000:])

# 3. links
def exists(target):
    t = pathlib.Path(os.path.normpath(target))
    return t.is_file() or t.with_suffix(t.suffix + ".html").is_file() or (t / "index.html").is_file() or pathlib.Path(str(t) + ".html").is_file()

for page in ROOT.rglob("*.html"):
    rel = page.relative_to(ROOT)
    if rel.parts[0] in ("scripts", ".github", "node_modules"):
        continue
    html = page.read_text(encoding="utf-8")
    html = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S)   # links built in JavaScript are checked by eye
    for attr, url in re.findall(r'\b(href|src)="([^"]+)"', html):
        if re.match(r"^([a-z]+:|//|#|\$\{)", url, re.I) or "{{" in url:
            continue
        path = unquote(url.split("#")[0].split("?")[0])
        if not path:
            continue
        if rel.name == "404.html":          # 404 resolves from the site root
            target = ROOT / path.lstrip("/")
        else:
            target = page.parent / path
        if not exists(target):
            errors.append(f"{rel}: קישור שבור: {url}")

if errors:
    print("\n".join(errors))
    print(f"\n{len(errors)} בעיות.")
    sys.exit(1)
print("הכל תקין: הנתונים, הבנייה והקישורים.")
