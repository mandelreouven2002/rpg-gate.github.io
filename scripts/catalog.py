"""
The catalog (catalog/): a landing shop for role-playing games in Hebrew.
Nothing is sold here: every product sends the visitor to the original store.

Builds, from catalog/catalog.json:
  catalog/index.html          every product, with search, filters and sorting
  catalog/item/<id>.html      one page per product: price, details, where to buy, similar products
"""
import json
from urllib.parse import quote
from shell import shell, esc, url_path, SHARED_CSS, SEARCH_ICON, SITE

FORMATS = {"pdf": "PDF", "print": "מודפס", "subscription": "מנוי"}
CATEGORY_ORDER = ["הרפתקאות", "ספרי חוקים", "הרחבות ועולמות", "עזרי משחק", "עוד"]
SYMBOL = {"ILS": "₪", "USD": "$"}


AFFILIATE_ID = "3500804"


def store_url(url):
    """DriveThruRPG links always carry the affiliate id (and drop the /en/ locale segment)."""
    if not url or "drivethrurpg.com" not in url:
        return url
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
    u = urlsplit(url)
    path = u.path[3:] if u.path.startswith("/en/") else u.path
    q = [(k, v) for k, v in parse_qsl(u.query) if k != "affiliate_id"] + [("affiliate_id", AFFILIATE_ID)]
    return urlunsplit((u.scheme or "https", u.netloc, path, urlencode(q), ""))


def is_affiliate(url):
    return bool(url) and "drivethrurpg.com" in url


def rel(url):
    return "sponsored noopener noreferrer" if is_affiliate(url) else "noopener noreferrer"


def load(root):
    f = root / "catalog" / "catalog.json"
    if not f.exists():
        return None, None
    data = json.loads(f.read_text(encoding="utf-8"))
    return data["items"], data


def money(v, cur):
    s = SYMBOL.get(cur, "")
    n = f"{v:,.2f}".rstrip("0").rstrip(".") if isinstance(v, float) else f"{v:,}"
    return f"{s}{n}"


def price_label(it):
    if it.get("price_text"):
        return it["price_text"]
    p = it.get("price")
    if not p:
        return "המחיר בחנות"
    if p.get("free"):
        return "חינם"
    lo, hi, cur = p.get("min"), p.get("max"), p.get("currency")
    if hi is None or hi == lo:
        return money(lo, cur)
    return f"{money(lo, cur)}–{money(hi, cur).lstrip(SYMBOL.get(cur, ''))}"


def price_html(label):
    """a bare price ('₪99–199', '$5') is isolated left-to-right, so the range never flips inside Hebrew text"""
    return f'<bdi dir="ltr">{esc(label)}</bdi>' if label[:1] in SYMBOL.values() else esc(label)


def sort_price(it):
    p = it.get("price")
    if not p:
        return None
    return 0 if p.get("free") else p.get("min")


def date_he(d):
    if not d:
        return ""
    y, m, dd = d.split("-")
    return f"{int(dd)}.{int(m)}.{y}"


CAT_CSS = """<style>
.price{font-weight:700;color:var(--red-deep);font-size:1rem;margin-top:.15rem}
.price.free{color:#2E7D4F}
.price.soft{color:var(--ink-2);font-weight:600;font-size:.92rem}
.pre{display:inline-block;font-size:.75rem;font-weight:700;padding:.08rem .5rem;border-radius:999px;background:var(--gold-bright);color:var(--ink);margin-inline-start:.3rem;vertical-align:middle}
.sheet .cat-note{font-size:.92rem;color:var(--ink-2);margin:-.4rem 0 1rem}
.buy{margin:1.2rem 0 1.4rem;padding:1.1rem 1.2rem;border:1px solid var(--line);border-radius:12px;background:#FBF6EE}
.buy .big{font-family:var(--display);font-weight:700;font-size:clamp(2.2rem,5vw,3rem);line-height:1;color:var(--red-deep)}
.buy .big.free{color:#2E7D4F}
.sheet .buy p{font-size:.95rem;margin:.35rem 0 0;max-width:none}
.buy .actions{margin-top:.9rem}
.formats{display:flex;flex-wrap:wrap;gap:.35rem;margin-top:.6rem}
.formats span{font-size:.82rem;font-weight:700;padding:.15rem .6rem;border-radius:6px;border:1px solid rgba(42,26,16,.3);color:var(--ink)}
.also{margin:.8rem 0 0;padding:0;list-style:none;max-width:none}
.sheet .also li{font-size:.95rem;margin:.2rem 0}
.sheet .fine{font-size:.85rem;color:var(--ink-2)}
.item-cover img{background:#EFE5D1}
</style>"""


def card(it, href, thumb):
    pl = price_label(it)
    cls = "price free" if pl == "חינם" else ("price soft" if pl == "המחיר בחנות" else "price")
    pre = '<span class="pre">מכירה מוקדמת</span>' if it.get("preorder") else ""
    img = (f'<img src="{thumb}{esc(url_path(it["image"]))}" alt="" width="240" height="336" loading="lazy" decoding="async">'
           if it.get("image") else "")
    return (f'<li data-id="{esc(it["id"])}"><a class="book" href="{href}{esc(it["id"])}">'
            f'<span class="book-cover">{img}</span><span class="book-type">{esc(it.get("type"))}</span>'
            f'<span class="book-name">{esc(it["title"])}</span><span class="book-meta">{esc(it.get("system"))}</span>'
            f'<span class="{cls}">{price_html(pl)}{pre}</span></a></li>')


def similar(it, items):
    """the same system (the 'meta tag') with shared tags first, then the same system, then shared tags."""
    mine = set(it.get("tags") or [])
    tiers = ([], [], [])
    for o in items:
        if o["id"] == it["id"]:
            continue
        shared = len(mine & set(o.get("tags") or []))
        same = o.get("system") == it.get("system")
        score = shared * 3 + (o.get("type") == it.get("type")) * 2 + (o.get("publisher") == it.get("publisher"))
        if same and shared:
            tiers[0].append((score, o))
        elif same:
            tiers[1].append((score, o))
        elif shared:
            tiers[2].append((score, o))
    out = []
    for t in tiers:
        out += [o for _, o in sorted(t, key=lambda x: (-x[0], x[1]["title"]))]
    return out


def build_index(root, items, data):
    order = sorted(items, key=lambda i: (bool(i.get("secondary")),))
    cats = {}
    for it in items:
        cats[it["category"]] = cats.get(it["category"], 0) + 1
    free_n = sum(1 for i in items if (i.get("price") or {}).get("free"))
    chips = ('<button class="chip" type="button" data-cat="" aria-pressed="true">הכל</button>' +
             "".join(f'<button class="chip" type="button" data-cat="{esc(c)}" aria-pressed="false">{esc(c)}<small>{cats[c]}</small></button>'
                     for c in CATEGORY_ORDER if c in cats) +
             f'<button class="chip" type="button" data-cat="__free" aria-pressed="false">חינם<small>{free_n}</small></button>')
    systems = {}
    for it in items:
        systems[it["system"]] = systems.get(it["system"], 0) + 1
    sys_opts = '<option value="">כל השיטות</option>' + "".join(
        f'<option value="{esc(s)}">{esc(s)} ({n})</option>' for s, n in sorted(systems.items(), key=lambda x: -x[1]))
    shelf = "".join(card(it, "item/", "") for it in order)
    mini = [{"id": it["id"], "c": it["category"], "s": it["system"], "f": 1 if (it.get("price") or {}).get("free") else 0,
             "p": sort_price(it), "t": it["title"], "o": i,
             "x": " ".join(str(v) for v in [it["title"], it.get("subtitle"), it.get("system"), it.get("type"), it.get("publisher"),
                                            it.get("store"), it.get("year"), it.get("summary"), " ".join(it.get("tags") or []),
                                            " ".join(it.get("creators") or [])] if v),
             "g": it.get("tags") or []} for i, it in enumerate(order)]
    checked = date_he(data.get("updated"))
    body = f'''<div class="sheet wide">
  <nav class="crumbs" aria-label="מיקום באתר"><a href="../">בית</a><span aria-hidden="true">/</span><span aria-current="page">קטלוג</span></nav>
  <div class="coll-head">
    <div>
      <h1>קטלוג משחקי התפקידים בעברית</h1>
      <p class="lede">כל משחקי התפקידים שיוצאים בעברית, במקום אחד. בוחרים משחק, ועוברים לקנות אותו ישירות בחנות של ההוצאה.</p>
    </div>
    <form role="search" onsubmit="return false">
      <label class="coll-search"><span class="sr-only">חיפוש בקטלוג</span>{SEARCH_ICON}
        <input id="q" type="search" placeholder="שם, שיטה, הוצאה או נושא, למשל: דרקונים" autocomplete="off" enterkeyhint="search"></label>
    </form>
  </div>
  <div class="coll-controls">
    <div class="chips" role="group" aria-label="סינון לפי סוג">{chips}</div>
    <div style="display:flex;gap:.6rem;flex-wrap:wrap">
      <label><span class="sr-only">סינון לפי שיטה</span><select id="system" class="coll-select">{sys_opts}</select></label>
      <label><span class="sr-only">מיון</span><select id="sort" class="coll-select">
        <option value="">מיון: מומלץ</option><option value="lo">מחיר: מהנמוך לגבוה</option><option value="hi">מחיר: מהגבוה לנמוך</option><option value="az">לפי שם</option>
      </select></label>
    </div>
  </div>
  <p class="coll-count" aria-live="polite"><span id="count">{len(items)}</span> מוצרים<span class="tag-filter" id="tagf" hidden></span></p>
  <p class="cat-note">המחירים נבדקו ב-{checked} ועשויים להשתנות. הרכישה עצמה נעשית באתר החנות.</p>
  <ul class="shelf" id="shelf">{shelf}</ul>
  <p class="coll-empty" id="empty" hidden>לא נמצאו מוצרים. נסו מילה אחרת, או חזרו לסינון "הכל".</p>
</div>'''
    payload = json.dumps(mini, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    script = f'''<script type="application/json" id="cat-data">{payload}</script>
<script>
(() => {{
  const items = JSON.parse(document.getElementById('cat-data').textContent);
  const norm = s => String(s || '').toLowerCase().replace(/[\\u0591-\\u05C7]/g, '').replace(/[-–—־"'׳״.,:;!?()]/g, ' ').replace(/\\s+/g, ' ').trim();
  const shelf = document.getElementById('shelf');
  items.forEach(it => {{ it.n = norm(it.x); it.li = shelf.querySelector('li[data-id="' + it.id + '"]'); }});
  const q = document.getElementById('q'), sys = document.getElementById('system'), sort = document.getElementById('sort');
  const chips = [...document.querySelectorAll('.chip')], count = document.getElementById('count'), empty = document.getElementById('empty'), tagf = document.getElementById('tagf');
  const params = new URLSearchParams(location.search);
  let cat = params.get('cat') || '', tag = params.get('tag') || '';
  q.value = params.get('q') || ''; if (params.get('system')) sys.value = params.get('system'); if (params.get('sort')) sort.value = params.get('sort');
  const cmp = {{
    '': (a, b) => a.o - b.o,
    lo: (a, b) => (a.p ?? 1e9) - (b.p ?? 1e9) || a.o - b.o,
    hi: (a, b) => (b.p ?? -1) - (a.p ?? -1) || a.o - b.o,
    az: (a, b) => a.t.localeCompare(b.t, 'he')
  }};
  function render(){{
    const words = norm(q.value).split(' ').filter(Boolean);
    let n = 0;
    [...items].sort(cmp[sort.value] || cmp['']).forEach(it => {{
      const ok = (!cat || (cat === '__free' ? it.f : it.c === cat)) && (!sys.value || it.s === sys.value) && (!tag || it.g.includes(tag)) && words.every(w => it.n.includes(w));
      it.li.hidden = !ok; if (ok) n++;
      shelf.appendChild(it.li);
    }});
    count.textContent = n; empty.hidden = n > 0;
    chips.forEach(c => c.setAttribute('aria-pressed', c.dataset.cat === cat));
    tagf.hidden = !tag; if (tag) tagf.innerHTML = 'בנושא: ' + tag.replace(/[&<>]/g, '') + ' <button type="button">ניקוי</button>';
    const p = new URLSearchParams();
    if (q.value.trim()) p.set('q', q.value.trim()); if (cat) p.set('cat', cat); if (sys.value) p.set('system', sys.value); if (sort.value) p.set('sort', sort.value); if (tag) p.set('tag', tag);
    history.replaceState(null, '', location.pathname + (p.toString() ? '?' + p : ''));
  }}
  chips.forEach(c => c.addEventListener('click', () => {{ cat = c.dataset.cat; render(); }}));
  q.addEventListener('input', render); sys.addEventListener('change', render); sort.addEventListener('change', render);
  tagf.addEventListener('click', e => {{ if (e.target.tagName === 'BUTTON') {{ tag = ''; render(); }} }});
  render();
}})();
</script>'''
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "@id": SITE + "catalog/#page", "url": SITE + "catalog/", "name": "קטלוג משחקי התפקידים בעברית",
         "inLanguage": "he-IL", "isPartOf": {"@id": SITE + "#website"},
         "mainEntity": {"@type": "ItemList", "numberOfItems": len(items), "itemListElement": [
             {"@type": "ListItem", "position": i + 1, "url": SITE + "catalog/item/" + it["id"], "name": it["title"]} for i, it in enumerate(order)]}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "בית", "item": SITE},
            {"@type": "ListItem", "position": 2, "name": "קטלוג", "item": SITE + "catalog/"}]}]}
    head = SHARED_CSS + "\n" + CAT_CSS + '\n<script type="application/ld+json">\n' + json.dumps(ld, ensure_ascii=False, indent=1).replace("</", "<\\/") + "\n</script>"
    return shell(root, 1, title="קטלוג משחקי התפקידים בעברית | שער להרפתקה",
                 desc=f"{len(items)} משחקי תפקידים בעברית: ספרי חוקים, הרפתקאות, הרחבות ועזרי משחק של חרבות וכשפים, פאת'פיינדר, ואנור ועוד, עם מחירים וקישור לרכישה בחנות של ההוצאה.",
                 url=SITE + "catalog/", body=body, head=head, scripts=script, current="cat")


def build_item(root, it, items, data):
    sims = similar(it, items)
    buy_url = store_url(it["url"])
    pl = price_label(it)
    free = pl == "חינם"
    img = (f'<img src="../{esc(url_path(it["image"]))}" alt="{esc(it.get("image_alt") or it["title"])}" width="480" height="672">'
           if it.get("image") else "")
    fmt = "".join(f"<span>{FORMATS.get(f, f)}</span>" for f in it.get("formats") or [])
    checked = date_he(it.get("price_checked"))
    price_line = (f'<p>המחיר נבדק ב-{checked} ועשוי להשתנות. המחיר הקובע הוא בחנות.</p>' if checked and it.get("price")
                  else '<p>המחיר מופיע בחנות, ויכול להשתנות לפי פורמט.</p>')
    also = ""
    if it.get("also"):
        also = '<ul class="also">' + "".join(
            f'<li>אפשר גם ב-<a href="{esc(store_url(a["url"]))}" target="_blank" rel="{rel(store_url(a["url"]))}">{esc(a["store"])}</a>{": " + esc(a["price_text"]) if a.get("price_text") else ""}</li>'
            for a in it["also"]) + "</ul>"
    pre = '<span class="pre">מכירה מוקדמת</span>' if it.get("preorder") else ""
    facts = [("הוצאה", it.get("publisher")), ("חנות", it.get("store")), ("שיטה", it.get("system")), ("סוג", it.get("type")),
             ("עמודים", it.get("pages")), ("שנת הוצאה", it.get("year")), ("גיל", f'{it["age_min"]}+' if it.get("age_min") else None),
             ("יוצרים", ", ".join(it.get("creators") or []) or None)]
    facts_html = "".join(f"<div><dt>{k}</dt><dd>{esc(v)}</dd></div>" for k, v in facts if v not in (None, ""))
    tags = "".join(f'<li><a href="../?tag={esc(quote(t))}">{esc(t)}</a></li>' for t in (it.get("tags") or []))
    note = f'<div class="note"><p>{esc(it["note"])}</p></div>' if it.get("note") else ""
    desc = it.get("description") or ""
    desc_html = f'<p>{esc(desc)}</p>' if desc else ""
    sub = f'<p class="orig"><bdi dir="auto">{esc(it["subtitle"])}</bdi></p>' if it.get("subtitle") else ""
    shown = 12
    sim_html = ""
    if sims:
        lis = "".join(card(o, "", "../").replace("<li ", f'<li class="more-hidden" ' if i >= shown else "<li ", 1) for i, o in enumerate(sims))
        more = (f'<p style="text-align:center;margin-top:1.4rem"><button class="btn btn-ghost" type="button" id="more-sim">הצגת עוד {len(sims) - shown} מוצרים דומים</button></p>'
                if len(sims) > shown else "")
        sim_html = f'<section class="similar" id="similar" aria-labelledby="sim-title"><h2 id="sim-title">מוצרים דומים</h2><ul class="shelf">{lis}</ul>{more}</section>'
    body = f'''<div class="sheet wide">
  <nav class="crumbs" aria-label="מיקום באתר"><a href="../../">בית</a><span aria-hidden="true">/</span><a href="../">קטלוג</a><span aria-hidden="true">/</span><span aria-current="page">{esc(it["title"])}</span></nav>
  <article class="item">
    <div class="item-cover">{img}</div>
    <div>
      <span class="tag">{esc(it.get("type"))}</span>{pre}
      <h1>{esc(it["title"])}</h1>
      {sub}
      <p class="lede">{esc(it.get("summary"))}</p>
      <div class="buy">
        <div class="big{' free' if free else ''}">{price_html(pl)}</div>
        <div class="formats">{fmt}</div>
        {price_line}
        {also}
        <div class="actions"><a class="btn btn-solid" href="{esc(buy_url)}" target="_blank" rel="{rel(buy_url)}">{"להורדה" if free else "לרכישה"} באתר החנות</a><span class="fine">החנות: {esc(it.get("store"))}</span></div>
      </div>
      {note}
      {desc_html}
      <dl class="facts">{facts_html}</dl>
      <ul class="tags" aria-label="נושאים">{tags}</ul>
      <p class="fine">שער להרפתקה לא מוכר את המוצר. הקישור מוביל לחנות המקור, והרכישה נעשית שם.{" ברכישה דרך הקישור ל-DriveThruRPG האתר מקבל עמלה קטנה, בלי עלות נוספת עבורכם." if is_affiliate(buy_url) else ""}</p>
    </div>
  </article>
  {sim_html}
</div>'''
    script = '''<script>
(() => { const more = document.getElementById('more-sim');
  if (more) more.addEventListener('click', () => { document.getElementById('similar').classList.add('open'); more.remove(); }); })();
</script>'''
    url = SITE + "catalog/item/" + it["id"]
    p = it.get("price")
    prod = {"@type": "Product", "@id": url + "#product", "name": it["title"], "url": url, "description": it.get("summary"),
            "category": it.get("type"), "brand": {"@type": "Brand", "name": it.get("publisher")}, "inLanguage": "he"}
    if it.get("image"):
        prod["image"] = SITE + "catalog/" + url_path(it["image"])
    if p:
        avail = "https://schema.org/PreOrder" if it.get("preorder") else "https://schema.org/InStock"
        seller = {"@type": "Organization", "name": it.get("store")}
        if p.get("free"):
            prod["offers"] = {"@type": "Offer", "price": 0, "priceCurrency": "ILS", "availability": avail, "url": buy_url, "seller": seller}
        elif p.get("max") not in (None, p.get("min")):
            prod["offers"] = {"@type": "AggregateOffer", "lowPrice": p["min"], "highPrice": p["max"], "priceCurrency": p.get("currency"),
                              "availability": avail, "url": buy_url, "seller": seller}
        else:
            prod["offers"] = {"@type": "Offer", "price": p["min"], "priceCurrency": p.get("currency"), "availability": avail, "url": buy_url, "seller": seller}
    ld = {"@context": "https://schema.org", "@graph": [prod, {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "בית", "item": SITE},
        {"@type": "ListItem", "position": 2, "name": "קטלוג", "item": SITE + "catalog/"},
        {"@type": "ListItem", "position": 3, "name": it["title"], "item": url}]}]}
    head = SHARED_CSS + "\n" + CAT_CSS + '\n<script type="application/ld+json">\n' + json.dumps(ld, ensure_ascii=False, indent=1).replace("</", "<\\/") + "\n</script>"
    title = f'{it["title"]} | קטלוג שער להרפתקה'
    if len(title) > 65:
        title = f'{it["title"]} | שער להרפתקה'
    desc_meta = it.get("summary") or it["title"]
    if len(desc_meta) < 110:
        price = price_label(it)
        price = "" if price == "המחיר בחנות" else (" חינם." if price == "חינם" else f" מחיר: {price}.")
        desc_meta = f"{desc_meta.rstrip('.')}. {it.get('type')} ל{it.get('system')}, בעברית, בהוצאת {it.get('publisher')}.{price}"
    if it["title"] not in desc_meta:
        desc_meta = f'{it["title"]}: {desc_meta}'
    if len(desc_meta) > 160:
        desc_meta = desc_meta[:157].rsplit(" ", 1)[0] + "…"
    return shell(root, 2, title=title, desc=desc_meta, url=url, body=body, head=head, scripts=script, og_type="product",
                 img=(SITE + "catalog/" + url_path(it["image"])) if it.get("image") else SITE + "static/og-image.png",
                 img_alt=it.get("image_alt") or it["title"], card="summary", current="cat")


def build(root, write):
    items, data = load(root)
    if not items:
        return []
    urls = [SITE + "catalog/"]
    write(root / "catalog" / "index.html", build_index(root, items, data))
    (root / "catalog" / "item").mkdir(exist_ok=True)
    for it in items:
        write(root / "catalog" / "item" / (it["id"] + ".html"), build_item(root, it, items, data))
        urls.append(SITE + "catalog/item/" + it["id"])
    return urls
