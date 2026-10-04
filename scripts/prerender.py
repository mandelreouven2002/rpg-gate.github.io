#!/usr/bin/env python3
"""
Prerender the data-driven parts of index.html from data.json.

Search engines and link previews read the HTML as it is served. The home page
used to build its lists in the browser, so crawlers saw empty containers. This
script writes the same markup the page's JavaScript produces straight into
index.html, between <!-- prerender:NAME --> markers, and embeds data.json so the
page can render instantly without waiting for a fetch.

Run it after every change to data.json:
    python3 scripts/prerender.py
The GitHub Action in .github/workflows/prerender.yml runs it automatically.
"""
import datetime, html, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
INDEX, DATA, SITEMAP = ROOT / "index.html", ROOT / "data.json", ROOT / "sitemap.xml"
SITE = "https://gate.roleplay.top/"

MONTHS = ["ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני", "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"]
TYPE = {"organization": "ארגון/עמותה", "event": "אירוע/כנס", "group": "קהילה/קבוצה", "store": "חנות/ציוד",
        "venue": "מתחם משחקים", "activities": "סדנאות והפעלות", "kids": "חוגי ילדים"}
PIN = '<svg viewBox="0 0 14 14" aria-hidden="true"><path d="M7 13s4.5-4.2 4.5-7.3a4.5 4.5 0 0 0-9 0C2.5 8.8 7 13 7 13z" fill="none" stroke="currentColor" stroke-width="1.4"/><circle cx="7" cy="5.8" r="1.5" fill="currentColor"/></svg>'
CAL = '<svg viewBox="0 0 14 14" aria-hidden="true"><rect x="1.5" y="2.5" width="11" height="10" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M1.5 5.5h11M4.5 1v3M9.5 1v3" stroke="currentColor" stroke-width="1.4"/></svg>'
FLASK = "M10 5H18V18.7A12 12 0 1 1 10 18.7Z"
TAPER = '<svg class="taper" viewBox="0 0 400 5" preserveAspectRatio="none" aria-hidden="true"><polygon points="0,2.5 400,0 400,5"/></svg>'


def esc(v):
    return html.escape(str(v if v is not None else ""), quote=True)


def types_of(item):
    t = item.get("type")
    return t if isinstance(t, list) else [t] if t else []


# ---------- directory entries (mirrors entryHTML in index.html) ----------
def entry(it):
    meta = [f"<span>{esc(', '.join(TYPE.get(t, 'כללי') for t in types_of(it)))}</span>"]
    if it.get("location"):
        meta.append(f"<span>{PIN}{esc(it['location'])}</span>")
    m = it.get("month") or 0
    if 1 <= m <= 12:
        meta.append(f"<span>{CAL}מתקיים ב{MONTHS[m - 1]}</span>")
    return (f'<li><a class="entry" href="{esc(it.get("link"))}" target="_blank" rel="noopener noreferrer">'
            f'<span class="entry-name">{esc(it.get("name"))}</span><span class="entry-meta">{"".join(meta)}</span>'
            f'<p class="entry-desc">{esc(it.get("description"))}</p></a></li>')


# ---------- systems: tabs + stat-block panels ----------
POTION_SHAPES = {
    "round": ("M10 5H18V18.7A12 12 0 1 1 10 18.7Z", "M8.4 4H19.6", "M6 28a8 8 0 0 1 4-7"),
    "tall":  ("M11 5H17V12C21 13 23 16 23 20V39C23 41 21 42 19 42H9C7 42 5 41 5 39V20C5 16 7 13 11 12Z", "M9.4 4H18.6", "M8.5 22V34"),
    "cone":  ("M11 5H17V16L25 38C26 40.5 25 42 22 42H6C3 42 2 40.5 3 38L11 16Z", "M9.4 4H18.6", "M8 31L11 24"),
    "jar":   ("M9 7H19V10C24 12 26 17 26 25C26 35 21 42 14 42C7 42 2 35 2 25C2 17 4 12 9 10Z", "M7.5 6H20.5", "M6 27a8 8 0 0 1 3-8"),
}
# every system gets its own potion: a shape and a brew colour (no difficulty meaning)
POTIONS = {"dnd": ("round", "#D02B45"), "sw": ("tall", "#E9B44C"), "spf": ("cone", "#6FD3BE"), "pbta": ("jar", "#9DB7FF")}


def vial(sid, vid, bubbles=False):
    shape, brew = POTIONS.get(sid, ("round", "#D02B45"))
    body, lip, shine = POTION_SHAPES[shape]
    h = 24
    b = ('<circle class="bubble" cx="11" cy="38" r="1.6"/><circle class="bubble" cx="16" cy="39" r="1.1"/>'
         '<circle class="bubble" cx="14" cy="37" r="1.3"/>') if bubbles else ""
    return (f'<svg class="vial" viewBox="0 0 28 44" aria-hidden="true" style="--brew:{brew}"><defs><clipPath id="vc-{vid}"><path d="{body}"/></clipPath></defs>'
            f'<g clip-path="url(#vc-{vid})"><rect class="liquid" x="0" y="{42.4 - h:.2f}" width="28" height="{h + 1:.2f}"/>{b}</g>'
            f'<path class="glass" d="{body}"/><path class="lip" d="{lip}"/><path class="shine" d="{shine}"/></svg>')


def sys_name(s):
    latin = s.get("latin")
    return esc(s["name"]) + (f' <span style="white-space:nowrap">(<bdi dir="ltr">{esc(latin)}</bdi>)</span>' if latin else "")


def systems(data):
    items = data.get("systemsData") or []
    tabs, panels = [], []
    for i, s in enumerate(items):
        sid, n, first = s["id"], int(s.get("complexity", 0)), i == 0
        tabs.append(
            f'<li role="presentation"><button class="sys-tab" type="button" role="tab" id="tab-{sid}" aria-controls="panel-{sid}" '
            f'aria-selected="{"true" if first else "false"}" tabindex="{0 if first else -1}"><span class="sys-name">{sys_name(s)}</span>'
            f'<span class="sys-badge">{esc(s.get("badge"))}</span><span class="gauge">{vial(sid, "tab-" + sid)}</span></button></li>')
        rows = "".join(
            f'<div><dt>{esc(st["label"])}</dt><dd>'
            + ('<span class="est" title="נתון משוער" aria-hidden="true">≈</span>' if st.get("est") else "")
            + f'<span>{esc(st["value"])}' + ('<span class="sr-only"> (משוער)</span>' if st.get("est") else "") + "</span></dd></div>"
            for st in s.get("stats", []))
        guide = f'<a class="guide-link" href="{esc(s["guide"])}">המדריך המלא על השיטה</a>' if s.get("guide") else ""
        panels.append(
            f'<div class="sys-panel" role="tabpanel" id="panel-{sid}" aria-labelledby="tab-{sid}"{"" if first else " hidden"} tabindex="0">'
            f'<div class="statblock"><div class="sb-head"><div><span class="sys-badge-lg">{esc(s.get("badge"))}</span>'
            f'<span class="sys-logo" data-art="logo-{sid}" role="img" aria-label="הלוגו של {esc(s["name"])}" hidden></span>'
            f'<h3 class="display">{sys_name(s)}</h3><p class="sb-type">{esc(s.get("type"))}</p></div>{vial(sid, "panel-" + sid, True)}</div>'
            f'{TAPER}<dl class="sb-stats">{rows}</dl>{TAPER}</div>'
            f'<div class="sys-side"><div class="why"><strong>למה זה טוב למתחילים?</strong><p>{esc(s.get("why"))}</p></div>'
            f'<div class="actions"><a class="btn btn-solid" href="{esc(s.get("link"))}" target="_blank" rel="noopener noreferrer">למעבר לאתר המשחק</a>{guide}</div></div></div>')
    return (f'<ul class="sys-list" role="tablist" aria-label="שיטות משחק" id="sys-list">{"".join(tabs)}</ul>'
            f'<div id="sys-panels">{"".join(panels)}</div>')


# ---------- phoenix-mail sample updates ----------
def updates(data):
    out = []
    for u in data.get("updatesData", []):
        body = "".join(f"<p>{esc(p)}</p>" for p in u.get("body", []))
        link = (f'<p><a class="update-url" href="{esc(u["link"])}" target="_blank" rel="noopener noreferrer">{esc(u["link"])}</a></p>'
                if u.get("link") else "")
        out.append(f'<li class="update"><p class="update-title">{esc(u.get("title"))}</p>{body}{link}</li>')
    return "".join(out)


# ---------- conventions (mirrors renderCons in index.html) ----------
def events_of(data):
    return [e for e in data.get("communityData", []) if "event" in types_of(e) and 1 <= (e.get("month") or 0) <= 12]


def con(data, today):
    ev = events_of(data)
    m, y = today.month, today.year
    key = lambda e: (y + 1 if e["month"] < m else y, e["month"])
    ev_sorted = sorted(ev, key=key)
    if not ev_sorted:
        return '<div id="con-main"><p class="con-when">אין כנסים קרובים זמינים כרגע.</p></div><div class="con-side" id="con-side"></div>'
    nxt = ev_sorted[0]
    same = [e for e in ev_sorted if e is not nxt and e["month"] == nxt["month"]]
    when = "מתקיים בדרך כלל החודש" if nxt["month"] == m else "מתקיים בדרך כלל ב" + MONTHS[nxt["month"] - 1]
    loc = f' מיקום: {esc(nxt["location"])}.' if nxt.get("location") else ""
    same_html = ('<p class="muted">באותו חודש: ' + ", ".join(f'<a class="con-pick" href="{esc(e["link"])}" data-k="{ev_sorted.index(e)}" aria-pressed="false">{esc(e["name"])}</a>' for e in same) + ".</p>") if same else ""
    return (f'<div id="con-main"><p class="con-when muted">{when}</p><p class="con-name"><a href="{esc(nxt["link"])}" target="_blank" rel="noopener noreferrer">{esc(nxt["name"])}</a></p></div>'
            f'<div class="con-side" id="con-side"><p>{esc(nxt.get("description"))}{loc}</p>{same_html}'
            f'<div class="actions"><a class="btn btn-solid" href="{esc(nxt["link"])}" target="_blank" rel="noopener noreferrer">לפרטים באתר הרשמי</a></div></div>')


def year(data, today):
    ev, m = events_of(data), today.month
    order = sorted(ev, key=lambda e: (today.year + 1 if e["month"] < m else today.year, e["month"]))
    nxt = order[0] if order else None
    out = []
    for i in range(12):
        mo = (m - 1 + i) % 12 + 1
        links = "".join(
            f'<a class="con-pick{" sel" if e is nxt else ""}" href="{esc(e["link"])}" data-k="{order.index(e)}" aria-pressed="{"true" if e is nxt else "false"}">{esc(e["name"])}</a>'
            for e in ev if e["month"] == mo)
        now = mo == m
        cls = ' class="now" aria-current="date"' if now else ''
        out.append(f'<li{cls}><span class="m">{MONTHS[mo - 1]}</span>{links}</li>')
    return "".join(out)


# ---------- structured data for the lists ----------
def ld(data, date):
    def lst(lid, name, items):
        return {"@type": "ItemList", "@id": SITE + "#" + lid, "name": name, "numberOfItems": len(items),
                "itemListElement": [{"@type": "ListItem", "position": i + 1, "item": it} for i, it in enumerate(items)]}

    games = []
    for s in data.get("systemsData", []):
        g = {"@type": "Game", "name": s["name"], "url": s.get("link"), "description": s.get("description"), "genre": s.get("type")}
        if s.get("latin"):
            g["alternateName"] = s["latin"]
        if s.get("players"):
            g["numberOfPlayers"] = {"@type": "QuantitativeValue", "minValue": s["players"][0], "maxValue": s["players"][1]}
        if s.get("age"):
            g["typicalAgeRange"] = s["age"]
        games.append(g)

    def org(it):
        t = types_of(it)
        kind = "EventSeries" if "event" in t else "Organization"
        o = {"@type": kind, "name": it.get("name"), "url": it.get("link"), "description": it.get("description")}
        if kind == "EventSeries" and it.get("location"):
            o["location"] = {"@type": "Place", "name": it["location"]}
        return o

    def biz(it):
        t = types_of(it)
        kind = "Store" if "store" in t else "EntertainmentBusiness" if "venue" in t else "LocalBusiness"
        b = {"@type": kind, "name": it.get("name"), "url": it.get("link"), "description": it.get("description")}
        if it.get("location"):
            b["areaServed"] = {"@type": "Place", "name": it["location"]}
        return b

    graph = [
        {"@type": "WebPage", "@id": SITE + "#webpage", "dateModified": date},
        lst("systems", "שיטות משחק תפקידים מומלצות למתחילים", games),
        lst("community", "ארגונים, כנסים וקהילות משחקי תפקידים בישראל", [org(i) for i in data.get("communityData", [])]),
        lst("resources", "חנויות, מתחמי משחק וחוגי משחקי תפקידים בישראל", [biz(i) for i in data.get("resourcesData", [])]),
    ]
    body = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, indent=1)
    return '<script type="application/ld+json">\n' + body.replace("</", "<\\/") + "\n</script>"


def embed(data):
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'<script type="application/json" id="gate-data">{body}</script>'


def fill(doc, name, content):
    pat = re.compile(r"(<!-- prerender:%s -->).*?(<!-- /prerender:%s -->)" % (re.escape(name), re.escape(name)), re.S)
    if not pat.search(doc):
        sys.exit(f"marker not found in index.html: {name}")
    return pat.sub(lambda m: m.group(1) + content + m.group(2), doc, count=1)


def now_strip(data, today):
    """'What is happening now' under the gate: the next convention, the latest update, the size of the map."""
    ev = events_of(data)
    m, y = today.month, today.year
    nxt = sorted(ev, key=lambda e: (y + 1 if e["month"] < m else y, e["month"]))[:1]
    if nxt:
        e = nxt[0]
        when = "מתקיים בדרך כלל החודש" if e["month"] == m else "בדרך כלל ב" + MONTHS[e["month"] - 1]
        con = f'<li><a href="#next-con"><span class="now-k">הכנס הקרוב</span><span class="now-v" id="now-con">{esc(e["name"])}</span><span class="now-s" id="now-con-when">{when}</span></a></li>'
    else:
        con = '<li><a href="#next-con"><span class="now-k">הכנס הקרוב</span><span class="now-v" id="now-con">לוח הכנסים</span><span class="now-s" id="now-con-when"></span></a></li>'
    n = len(data.get("communityData", [])) + len(data.get("resourcesData", []))
    regions = len(data.get("regions", []))
    mp = (f'<li><a href="#community"><span class="now-k">על המפה</span><span class="now-v">{n} קהילות, חנויות וחוגים</span>'
          f'<span class="now-s">ב-{regions} אזורים בכל הארץ</span></a></li>')
    f = ROOT / "catalog" / "catalog.json"
    cat = len(json.loads(f.read_text(encoding="utf-8"))["items"]) if f.exists() else 0
    ct = (f'<li><a href="catalog/"><span class="now-k">בקטלוג</span><span class="now-v">{cat} משחקים בעברית</span>'
          f'<span class="now-s">עם מחירים וקישור לחנות</span></a></li>') if cat else ""
    return con + mp + ct


def render(doc, data, today, date):
    doc = fill(doc, "systems", systems(data))
    doc = fill(doc, "now", now_strip(data, today))
    doc = fill(doc, "guideCount", str(len(guide_files())))
    doc = fill(doc, "allData", "".join(entry(i) for i in data.get("communityData", []) + data.get("resourcesData", [])))
    doc = fill(doc, "updates", updates(data))
    doc = fill(doc, "con", con(data, today))
    doc = fill(doc, "year", year(data, today))
    doc = fill(doc, "data", embed(data))
    doc = fill(doc, "ld", ld(data, date))
    return doc


def render_search(doc, data, today, date):
    items = data.get("communityData", []) + data.get("resourcesData", [])
    doc = fill(doc, "allData", "".join(entry(i) for i in items))
    doc = fill(doc, "data", embed(data))
    return doc


SYSTEM_FILES = ["dungeons_and_dragons", "swords-wizardry", "Savage-Pathfinder", "Apocalypse-World", "pathfinder2", "Savage-Worlds",
                "Blades-in-the-Dark", "call-of-cthulhu", "dungeon-world", "exalted", "tiny-wizards", "malastra", "masks",
                "lasers-feelings", "shadowrun", "warhammer"]


def render_articles(doc, data, today, date):
    """System cards on /articles, read from the markdown guides so they are real links in the HTML."""
    folder = ROOT / "static" / "articles" / "files"
    names = SYSTEM_FILES + sorted(p.stem for p in folder.glob("*.md") if p.stem not in SYSTEM_FILES)
    cards = []
    for name in names:
        f = folder / (name + ".md")
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8")
        m = re.search(r"^#\s+(.+)$", text, re.M)
        title = m.group(1).strip() if m else name.replace("-", " ").replace("_", " ")
        ex = re.search(r"##\s*על השיטה בקצרה\s*\n([\s\S]*?)(?=\n#|$)", text)
        excerpt = re.sub(r"[#*`_\[\]>]", "", ex.group(1)).strip() if ex else ""
        excerpt = " ".join(excerpt.split())
        if len(excerpt) > 220:
            excerpt = excerpt[:220].rsplit(" ", 1)[0] + "…"
        cards.append(f'<li><a class="card" href="systems/{esc(name)}"><span class="tag">שיטת משחק</span>'
                     f'<span class="card-title">{esc(title)}</span><p class="card-text">{esc(excerpt)}</p>'
                     f'<span class="card-more">לעמוד השיטה</span></a></li>')
    return fill(doc, "systemCards", "".join(cards))


def render_nextcon(doc, data, today, date):
    doc = fill(doc, "con", con(data, today))
    return fill(doc, "year", year(data, today))


def render_guides(doc, data, today, date):
    """Every system guide, embedded in articles/system.html so it opens even without a server."""
    guides = {}
    for folder in (ROOT / "static" / "articles" / "files", ROOT / "articles" / "files"):
        for f in sorted(folder.glob("*.md")) if folder.exists() else []:
            guides.setdefault(f.stem, f.read_text(encoding="utf-8"))
    body = json.dumps(guides, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return fill(doc, "guides", f'<script type="application/json" id="guides">{body}</script>')


def render_quiz(doc, data, today, date):
    body = json.dumps(data.get("quizData", {}), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return fill(doc, "quiz", f'<script type="application/json" id="quiz-data">{body}</script>')


# page file, public URL, renderer
PAGES = [
    (INDEX, SITE, render),
    (ROOT / "search.html", SITE + "search", render_search),
    (ROOT / "articles" / "index.html", SITE + "articles/", render_articles),
    (ROOT / "next-con.html", SITE + "next-con", render_nextcon),
    (ROOT / "quiz.html", SITE + "quiz", render_quiz),
]


def touch_sitemap(url, day):
    if not SITEMAP.exists():
        return
    sm = SITEMAP.read_text(encoding="utf-8")
    if "<loc>" + url + "</loc>" in sm:
        sm = re.sub(r"(<loc>%s</loc>)(\s*<lastmod>[^<]*</lastmod>)?" % re.escape(url),
                    lambda m: m.group(1) + "\n    <lastmod>" + day + "</lastmod>", sm, count=1)
        SITEMAP.write_text(sm, encoding="utf-8")


# ---------- static pages for every system guide: real URLs that search and AI engines can read ----------
def guide_files():
    out = {}
    for folder in (ROOT / "static" / "articles" / "files", ROOT / "articles" / "files"):
        if folder.exists():
            for f in sorted(folder.glob("*.md")):
                out.setdefault(f.stem, f)
    names = [n for n in SYSTEM_FILES if n in out] + sorted(n for n in out if n not in SYSTEM_FILES)
    return [(n, out[n]) for n in names]


def md_parts(text, name):
    m = re.search(r"^#\s+(.+)$", text, re.M)
    title = m.group(1).strip() if m else name.replace("-", " ").replace("_", " ")
    body = text.replace(m.group(0), "", 1).strip() if m else text
    ex = re.search(r"##\s*על השיטה בקצרה\s*\n([\s\S]*?)(?=\n#|$)", text)
    plain = " ".join(re.sub(r"[#*`_\[\]>]", "", ex.group(1) if ex else body).split())
    desc = plain if len(plain) <= 155 else plain[:155].rsplit(" ", 1)[0] + "…"
    return title, body, desc, plain


def build_system_pages(today):
    try:
        import markdown
    except ImportError:
        print("system pages skipped: pip install markdown")
        return []
    tpl_path = ROOT / "scripts" / "system-page.template.html"
    if not tpl_path.exists():
        return []
    tpl = tpl_path.read_text(encoding="utf-8")
    outdir = ROOT / "articles" / "systems"
    outdir.mkdir(exist_ok=True)
    guides = guide_files()
    parsed = [(n, *md_parts(f.read_text(encoding="utf-8"), n)) for n, f in guides]
    urls = []
    for name, title, body, desc, plain in parsed:
        url = SITE + "articles/systems/" + name
        html_body = markdown.markdown(body, extensions=["tables", "sane_lists"])
        html_body = re.sub(r"(<table>.*?</table>)", r'<div class="table-wrap">\1</div>', html_body, flags=re.S)
        html_body = html_body.replace('<a href="http', '<a target="_blank" rel="noopener noreferrer" href="http')
        short = title.split(" (")[0].split(":")[0].strip()
        more = "".join(f'<li><a href="{esc(n)}">{esc(t)}</a></li>' for n, t, _, _, _ in parsed if n != name)
        ld = {"@context": "https://schema.org", "@graph": [
            {"@type": "Article", "@id": url + "#article", "headline": title, "description": desc, "inLanguage": "he-IL",
             "url": url, "mainEntityOfPage": url, "image": SITE + "static/og-image.png",
             "about": {"@type": "Game", "name": title}, "isPartOf": {"@id": SITE + "#website"},
             "author": {"@id": SITE + "#organization"}, "publisher": {"@id": SITE + "#organization"}},
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "בית", "item": SITE},
                {"@type": "ListItem", "position": 2, "name": "מאמרים", "item": SITE + "articles/"},
                {"@type": "ListItem", "position": 3, "name": short, "item": url}]}]}
        name_only = title.split(":")[0].strip()
        if len(name_only) > 48:
            name_only = name_only.split(" (")[0].strip()
        page_title = f"{name_only}: מדריך לשיטה | שער להרפתקה"
        if len(page_title) > 65:
            page_title = f"{name_only} | שער להרפתקה"
        page = (tpl.replace("{{PAGETITLE}}", esc(page_title)).replace("{{TITLE}}", esc(title)).replace("{{DESC}}", esc(desc)).replace("{{URL}}", url)
                   .replace("{{NAME}}", esc(name)).replace("{{SHORT}}", esc(short)).replace("{{MORE}}", more)
                   .replace("{{LD}}", json.dumps(ld, ensure_ascii=False, indent=1).replace("</", "<\\/"))
                   .replace("{{BODY}}", html_body))
        target = outdir / (name + ".html")
        if not target.exists() or target.read_text(encoding="utf-8") != page:
            target.write_text(page, encoding="utf-8")
            print("articles/systems/" + name + ".html written")
        urls.append(url)
    return urls


def ensure_sitemap(urls, day):
    if not SITEMAP.exists() or not urls:
        return
    sm = SITEMAP.read_text(encoding="utf-8")
    add = "".join(f"  <url>\n    <loc>{u}</loc>\n    <lastmod>{day}</lastmod>\n    <changefreq>monthly</changefreq>\n    <priority>0.60</priority>\n  </url>\n"
                  for u in urls if f"<loc>{u}</loc>" not in sm)
    if add:
        SITEMAP.write_text(sm.replace("</urlset>", add + "</urlset>"), encoding="utf-8")


# ---------- llms-full.txt: the whole site as plain text, for AI answer engines ----------
class _Text(__import__("html.parser").parser.HTMLParser):
    BLOCK = {"p", "li", "h1", "h2", "h3", "h4", "tr", "br", "div", "section", "blockquote"}
    def __init__(self):
        super().__init__(); self.out = []; self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "svg"): self.skip += 1
        if tag in ("h1", "h2", "h3"): self.out.append("\n" + "#" * int(tag[1]) + " ")
        elif tag == "li": self.out.append("\n- ")
        elif tag in self.BLOCK: self.out.append("\n")
    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "svg"): self.skip -= 1
        if tag in self.BLOCK: self.out.append("\n")
    def handle_data(self, d):
        if not self.skip: self.out.append(d)
    def text(self):
        return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", "".join(self.out))).strip()


def update_llms_index():
    f = ROOT / "llms.txt"
    if not f.exists():
        return
    lines = []
    for name, md in guide_files():
        title, _, desc, _ = md_parts(md.read_text(encoding="utf-8"), name)
        lines.append(f"- [{title}]({SITE}articles/systems/{name}): {desc}")
    s = f.read_text(encoding="utf-8")
    new = re.sub(r"<!-- systems -->.*?<!-- /systems -->", lambda m: "<!-- systems -->\n" + "\n".join(lines) + "\n<!-- /systems -->", s, flags=re.S)
    if new != s:
        f.write_text(new, encoding="utf-8")
        print("llms.txt updated")


def build_llms_full(data):
    parts = ["# שער להרפתקה: הטקסט המלא של האתר", "",
             "> הבית של משחקי התפקידים בישראל: הקהילה, הכנסים, החנויות והחוגים, מדריכי שיטות ומאמרים, ופינת מתחילים. " + SITE, ""]
    for f in sorted((ROOT / "articles").glob("*.html")):
        if f.stem in ("index", "system"):
            continue
        doc = f.read_text(encoding="utf-8")
        m = re.search(r'<article class="sheet">(.*?)</article>', doc, re.S)
        if not m:
            continue
        p = _Text(); p.feed(m.group(1))
        parts += [f"---", f"מקור: {SITE}articles/{f.stem}", "", p.text(), ""]
    for name, f in guide_files():
        parts += ["---", f"מקור: {SITE}articles/systems/{name}", "", f.read_text(encoding="utf-8").strip(), ""]
    parts += ["---", "# מאגר הקהילה", ""]
    TYPES = {"organization": "ארגון", "event": "כנס/אירוע", "group": "קהילה", "store": "חנות", "venue": "מתחם משחק", "activities": "סדנאות והפעלות", "kids": "חוגי ילדים"}
    for it in data.get("communityData", []) + data.get("resourcesData", []):
        kind = ", ".join(TYPES.get(t, t) for t in types_of(it))
        where = f" | מיקום: {it['location']}" if it.get("location") else ""
        when = f" | בדרך כלל ב{MONTHS[it['month'] - 1]}" if 1 <= (it.get("month") or 0) <= 12 else ""
        parts.append(f"- {it.get('name')} ({kind}){where}{when}: {it.get('description', '')} {it.get('link', '')}")
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import catalog as _cat
        items, cdata = _cat.load(ROOT)
    except Exception:
        items, cdata = None, None
    if items:
        parts += ["---", "# קטלוג משחקי התפקידים בעברית (מחירים נבדקו ב-" + _cat.date_he(cdata.get("updated")) + ")", ""]
        for it in items:
            parts.append(f"- {it['title']} ({it.get('type')}, {it.get('system')}, {it.get('publisher')}): {_cat.price_label(it)}. "
                         f"{it.get('summary', '')} {SITE}catalog/item/{it['id']}")
    out = "\n".join(parts) + "\n"
    target = ROOT / "llms-full.txt"
    if not target.exists() or target.read_text(encoding="utf-8") != out:
        target.write_text(out, encoding="utf-8")
        print("llms-full.txt written")


def build_catalog():
    """The catalog (catalog/). See scripts/catalog.py."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import catalog
    def write(path, text):
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")
            print(str(path.relative_to(ROOT)), "written")
            return True
        return False
    return catalog.build(ROOT, write)


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    today = datetime.date.today()
    for path, url, fn in PAGES:
        if not path.exists():
            continue
        doc = path.read_text(encoding="utf-8")
        old = re.search(r'"dateModified": "([0-9-]+)"', doc)
        old_date = old.group(1) if old else today.isoformat()
        # Keep the old date if nothing else changed, so the script is idempotent.
        if fn(doc, data, today, old_date) == doc:
            print(path.name, "is up to date")
            continue
        path.write_text(fn(doc, data, today, today.isoformat()), encoding="utf-8")
        if url:
            touch_sitemap(url, today.isoformat())
        print(path.name, "prerendered", today.isoformat())
    ensure_sitemap(build_system_pages(today), today.isoformat())
    ensure_sitemap(build_catalog(), today.isoformat())
    update_llms_index()
    build_llms_full(data)


if __name__ == "__main__":
    main()
