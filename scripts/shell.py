"""
Shared pieces for the catalog pages that scripts/prerender.py builds
(a searchable shelf and one page per item): the page shell, escaping, image sizes and the shared look.
"""
import html, json, re, pathlib
from urllib.parse import quote

SITE = "https://gate.roleplay.top/"


def esc(v):
    return html.escape(str(v if v is not None else ""), quote=True)


def url_path(p):
    return quote(p, safe="/")


def image_size(root, url):
    """width, height and type of a site image (png or webp), read from the file header; no extra libraries."""
    import struct
    from urllib.parse import unquote
    if not url.startswith(SITE):
        return None, None, None
    f = root / unquote(url[len(SITE):])
    try:
        b = f.read_bytes()[:40]
    except OSError:
        return None, None, None
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", b[16:24])
        return w, h, "image/png"
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        kind = b[12:16]
        if kind == b"VP8X":
            return 1 + int.from_bytes(b[24:27], "little"), 1 + int.from_bytes(b[27:30], "little"), "image/webp"
        if kind == b"VP8L":
            v = int.from_bytes(b[21:25], "little")
            return (v & 0x3FFF) + 1, ((v >> 14) & 0x3FFF) + 1, "image/webp"
        if kind == b"VP8 ":
            w, h = struct.unpack("<HH", b[26:30])
            return w & 0x3FFF, h & 0x3FFF, "image/webp"
    return None, None, None


def shell(root, depth, *, title, desc, url, body, head="", scripts="", robots="index, follow, max-snippet:-1, max-image-preview:large",
          img=SITE + "static/og-image.png", img_alt="שער להרפתקה", og_type="website", card="summary_large_image", body_attr="", current="cat"):
    tpl = (root / "scripts" / "shell.template.html").read_text(encoding="utf-8")
    canon = (f'<link rel="canonical" href="{url}">\n<link rel="alternate" hreflang="he" href="{url}">\n'
             f'<link rel="alternate" hreflang="x-default" href="{url}">\n') if "noindex" not in robots else ""
    w, h, typ = image_size(root, img)
    imgmeta = (f'<meta property="og:image:type" content="{typ}">\n<meta property="og:image:width" content="{w}">\n'
               f'<meta property="og:image:height" content="{h}">\n') if w else ""
    rep = {"{{P}}": "../" * depth, "{{TITLE}}": esc(title), "{{DESC}}": esc(desc), "{{URL}}": url, "{{ROBOTS}}": robots,
           "{{CANON}}": canon, "{{IMGMETA}}": imgmeta, "{{OGTYPE}}": og_type, "{{IMG}}": img, "{{IMGALT}}": esc(img_alt), "{{TWCARD}}": card,
           "{{CUR_CAT}}": ' aria-current="page"' if current == "cat" else "", "{{HEAD}}": head, "{{SCRIPTS}}": scripts, "{{BODYATTR}}": body_attr}
    out = tpl
    for k, v in rep.items():
        out = out.replace(k, v)
    return out.replace("{{BODY}}", body)


# ---------------------------------------------------------------- shared look
SHARED_CSS = """<style>
/* ---------- collection pages: a searchable shelf, and one page per item ---------- */
.coll-head{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:1rem 3rem;align-items:end;margin-bottom:1.4rem}
.coll-head h1{margin:0}
.coll-head .lede{margin:.6rem 0 0}
.coll-search{position:relative;display:block}
.coll-search svg{position:absolute;right:1rem;top:50%;width:22px;height:22px;transform:translateY(-50%);color:var(--red);pointer-events:none}
.coll-search input{width:100%;font:inherit;font-size:1.1rem;color:var(--ink);background:#FBF6EE;border:1.5px solid rgba(90,58,28,.35);border-radius:10px;padding:.85rem 3rem .85rem 1rem}
.coll-search input::placeholder{color:#8A735A;opacity:1}
.coll-search input:focus{outline:3px solid var(--red);outline-offset:2px;border-color:transparent}
.coll-controls{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:.8rem 1.2rem;margin-bottom:1rem}
.chips{display:flex;flex-wrap:wrap;gap:.45rem}
.chip{font:inherit;font-size:.93rem;font-weight:600;color:var(--ink);background:transparent;cursor:pointer;padding:.38rem .95rem;border-radius:999px;border:1px solid rgba(42,26,16,.35)}
.chip:hover{background:rgba(155,21,40,.07)}
.chip[aria-pressed="true"]{background:var(--red);border-color:var(--red);color:var(--bone)}
.chip small{font-weight:500;opacity:.75;margin-inline-start:.25rem}
.coll-select{font:inherit;font-size:.95rem;color:var(--ink);background:#FBF6EE;border:1.5px solid rgba(90,58,28,.35);border-radius:10px;padding:.45rem .8rem}
.sheet .coll-count{font-size:1rem;font-weight:600;color:var(--ink-2);margin:0 0 .9rem}
.sheet .coll-count strong{color:var(--red)}
.tag-filter{display:inline-flex;align-items:center;gap:.4rem;margin-inline-start:.6rem;font-weight:700;color:var(--ink)}
.tag-filter button{font:inherit;color:var(--red);background:none;border:0;cursor:pointer;text-decoration:underline;padding:0}
.shelf{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,168px),1fr));gap:1.4rem 1.1rem;max-width:none}
.shelf li{margin:0}
.book{display:flex;flex-direction:column;gap:.35rem;height:100%;color:var(--ink);text-decoration:none}
.book-cover{display:block;aspect-ratio:5/7;border-radius:6px;overflow:hidden;background:#EFE5D1;box-shadow:0 1px 2px rgba(60,35,10,.15),0 12px 22px -14px rgba(60,35,10,.55);transition:transform .25s cubic-bezier(.16,1,.3,1),box-shadow .25s}
.book-cover img{display:block;width:100%;height:100%;object-fit:contain}
.book:hover .book-cover,.book:focus-visible .book-cover{transform:translateY(-4px);box-shadow:0 1px 2px rgba(60,35,10,.15),0 18px 28px -14px rgba(60,35,10,.6)}
.book-type{font-size:.78rem;font-weight:700;color:var(--red-deep);margin-top:.2rem}
.book-name{font-weight:700;font-size:1rem;line-height:1.35}
.book:hover .book-name{color:var(--red);text-decoration:underline}
.book-meta{font-size:.84rem;color:var(--ink-2);line-height:1.4}
.coll-empty{padding:2rem 0;font-weight:600}
/* ---------- one item ---------- */
.item{display:grid;grid-template-columns:minmax(0,280px) minmax(0,1fr);gap:clamp(1.5rem,4vw,3rem);align-items:start}
.item-cover{position:sticky;top:calc(var(--topbar) + 1.5rem)}
.item-cover img{display:block;width:100%;height:auto;border-radius:8px;box-shadow:0 1px 2px rgba(60,35,10,.15),0 22px 40px -22px rgba(60,35,10,.65)}
.item-cover .btn{width:100%;margin-top:1rem}
.item h1{margin:.2rem 0 .3rem}
.orig{font-size:1rem;color:var(--ink-2);margin:0 0 1rem}
.facts{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,190px),1fr));gap:.7rem 1.4rem;margin:1.2rem 0 1.4rem;padding:1rem 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.facts div{min-width:0}
.facts dt{font-size:.82rem;font-weight:700;color:var(--ink-2)}
.facts dd{margin:0;font-weight:600}
.tags{display:flex;flex-wrap:wrap;gap:.4rem;margin:0 0 1.4rem;padding:0;list-style:none;max-width:none}
.tags li{margin:0}
.tags a{display:inline-block;font-size:.88rem;font-weight:600;padding:.25rem .75rem;border-radius:999px;background:rgba(155,21,40,.08);color:var(--red-deep);text-decoration:none}
.tags a:hover{background:rgba(155,21,40,.16)}
.sources{font-size:.92rem;color:var(--ink-2)}
.sources ul{padding-right:1.2rem;margin:.3rem 0 0}
.sources li{font-size:.92rem;margin-bottom:.25rem;overflow-wrap:anywhere}
.similar{margin-top:3rem}
.similar h2{margin-top:0}
.similar .shelf li.more-hidden{display:none}
.similar.open .shelf li.more-hidden{display:block}
@media (max-width:560px){.shelf{grid-template-columns:repeat(2,minmax(0,1fr));gap:1.1rem .8rem}.book-name{font-size:.94rem}}
@media (max-width:760px){
  .coll-head{grid-template-columns:1fr}
  .item{grid-template-columns:1fr}
  .item-cover{position:static;max-width:240px;margin-inline:auto}
}
</style>"""

SEARCH_ICON = ('<svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="8.5" cy="8.5" r="6" fill="none" stroke="currentColor" stroke-width="1.8"/>'
               '<path d="M13 13l5 5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>')
