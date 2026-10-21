#!/usr/bin/env python3
"""hub.py - the one tool that manages this site (Python 3.8+, no dependencies).

Source of truth: hub.json (the left-hand menu and every index list).
Two pages: index.html (the hub) and template.html (every other page is made from it).
The tool only ever writes inside these marked regions; everything else in your files is yours:
  <!-- hub:nav:start -->  ...  <!-- hub:nav:end -->            left-hand menu (index.html and every page)
  <!-- hub:data:start --> ...  <!-- hub:data:end -->           index lists (index.html only)
  <!-- page:content:start --> ... <!-- page:content:end -->    page content: composed from pages/<name>.json (the editor writes it),
                                                                or, if there is no .json, your hand-written HTML, kept exactly as is
Easiest way to use it:  python3 hub.py   (no words after it). It opens the editor; press PUBLISH when done.
Run  python3 hub.py -h  for every command.
"""
import argparse, base64, datetime, functools, html, http.server, io, json, os, pathlib, re, shutil, subprocess, sys, threading, time, urllib.parse, urllib.request, webbrowser, zipfile

ROOT = pathlib.Path(__file__).resolve().parent
CFG, INDEX, TEMPLATE, PAGES = ROOT / "hub.json", ROOT / "index.html", ROOT / "template.html", ROOT / "pages"
HUES = [355, 222, 275, 150, 32, 190]
ICONS = {
    "home": "M3 11l9-8 9 8M5 10v10h5v-6h4v6h5V10",
    "projects": "M6 3h9l4 4v14H6zM9 12h7M9 16h7M9 8h3",
    "systems": "M12 2l9 5v10l-9 5-9-5V7zM12 12l9-5M12 12v10M12 12L3 7",
    "library": "M3 5c3-1 6-1 9 1 3-2 6-2 9-1v14c-3-1-6-1-9 1-3-2-6-2-9-1zM12 6v14",
    "about": "M12 3a9 9 0 100 18 9 9 0 000-18zM12 11v6M12 7.5v.5",
    "triangle": "M12 3l9 16H3z",
}
DEFAULT = {"title": "Makuraba", "menu": [
    {"id": "home", "label": "Home", "type": "home", "icon": "home"},
    {"id": "projects", "label": "Projects", "type": "index", "icon": "projects", "items": []},
    {"id": "systems", "label": "Systems", "type": "index", "icon": "systems", "items": []},
    {"id": "library", "label": "Library", "type": "index", "icon": "library", "items": []},
    {"id": "about", "label": "About", "type": "index", "icon": "about", "items": []}]}

def die(m): sys.exit("error: " + m)
def slug(s): return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-") or "untitled"
def esc(s, quote=False): return html.escape(s, quote=quote)
def kind(n): return "group" if "items" in n else "link" if "url" in n else "page"

# ---------- config
def save(cfg): CFG.write_text(json.dumps(cfg, indent=1, ensure_ascii=False) + "\n", "utf-8")

def load():
    if not CFG.exists(): save(DEFAULT); print("created hub.json")
    try: cfg = json.loads(CFG.read_text("utf-8"))
    except json.JSONDecodeError as e: die(f"hub.json is not valid JSON: {e}")
    if not isinstance(cfg.get("menu"), list): die('hub.json needs a "menu" list')
    normalize(cfg); return cfg

def normalize(cfg):
    seen = set()
    for m in cfg["menu"]:
        if not m.get("label"): die("every menu item needs a label")
        m.setdefault("id", slug(m["label"]))
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", str(m["id"])): die(f'menu id "{m["id"]}" may only use a-z, 0-9 and dashes')
        if m["id"] in seen: die(f'duplicate menu id "{m["id"]}"')
        seen.add(m["id"]); m.setdefault("type", "home" if m["id"] == "home" else "index")
        m.setdefault("icon", m["id"] if m["id"] in ICONS else "triangle")
        if m["type"] == "index": m.setdefault("items", []); check_nodes(m["items"], m["id"])
    if not any(m["type"] == "home" for m in cfg["menu"]): die('the menu needs a "home" item')

def check_nodes(items, where):
    ids = set()
    for n in items:
        if not n.get("title"): die(f"an item in {where} has no title")
        n.setdefault("id", slug(n["title"]))
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", str(n["id"])): die(f'id "{n["id"]}" may only use a-z, 0-9 and dashes')
        if n["id"] in ids: die(f'duplicate id "{n["id"]}" in {where}')
        ids.add(n["id"])
        if kind(n) == "page":
            n.setdefault("slug", n["id"])
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", str(n["slug"])): die(f'page file name "{n["slug"]}" may only use a-z, 0-9 and dashes')
        if kind(n) == "link" and re.match(r"\s*javascript:", str(n["url"]), re.I): die("javascript: links are not allowed")
        if "items" in n: check_nodes(n["items"], where + "/" + n["id"])

def walk(items, trail=()):
    for n in items:
        yield n, trail
        if "items" in n: yield from walk(n["items"], trail + (n,))

def page_map(cfg):
    pm = {}
    for m in cfg["menu"]:
        for n, trail in walk(m.get("items", [])):
            if kind(n) == "page":
                if n["slug"] in pm: die(f'two pages use the file name "{n["slug"]}"')
                pm[n["slug"]] = (m, trail, n)
    return pm

# ---------- marked regions
def region(text, name, new):
    pat = re.compile(r"(<!-- %s:start -->).*?(<!-- %s:end -->)" % (name, name), re.S)
    if not pat.search(text): die(f"missing <!-- {name}:start --> / <!-- {name}:end --> markers")
    return pat.sub(lambda m: m.group(1) + "\n" + new + "\n" + m.group(2), text, count=1)

def get_region(text, name):
    m = re.search(r"<!-- %s:start -->(.*?)<!-- %s:end -->" % (name, name), text, re.S)
    if not m: return None
    s = m.group(1)
    if s.startswith("\n"): s = s[1:]
    if s.endswith("\n"): s = s[:-1]
    return s

def write(p, text):
    if p.exists() and p.read_text("utf-8") == text: return False
    p.write_text(text, "utf-8"); return True

# ---------- optional Markdown for pages/<name>.md
def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", r'<img src="\2" alt="\1">', s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    return re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", s)

def md2html(src):
    src = re.sub(r"^---\s*\n.*?\n---\s*\n", "", src, count=1, flags=re.S)
    out, para, lst, i, lines = [], [], None, 0, src.splitlines()
    def flush():
        nonlocal para
        if para: out.append("<p>" + inline(" ".join(para)) + "</p>"); para = []
    def endlist():
        nonlocal lst
        if lst: out.append("</%s>" % lst); lst = None
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            flush(); endlist(); buf = []; i += 1
            while i < len(lines) and not lines[i].startswith("```"): buf.append(lines[i]); i += 1
            out.append("<pre><code>" + html.escape("\n".join(buf)) + "</code></pre>")
        elif re.match(r"^#{2,4} ", ln):
            flush(); endlist(); n = len(ln.split(" ")[0]); out.append("<h%d>%s</h%d>" % (n, inline(ln[n + 1:]), n))
        elif re.match(r"^\s*([-*]|\d+\.) ", ln):
            flush(); k = "ol" if re.match(r"^\s*\d+\.", ln) else "ul"
            if lst != k: endlist(); out.append("<%s>" % k); lst = k
            out.append("<li>" + inline(re.sub(r"^\s*([-*]|\d+\.) ", "", ln)) + "</li>")
        elif ln.startswith("> "): flush(); endlist(); out.append("<blockquote>" + inline(ln[2:]) + "</blockquote>")
        elif re.match(r"^---+$", ln.strip()): flush(); endlist(); out.append("<hr>")
        elif ln.lstrip().startswith("<"): flush(); endlist(); out.append(ln)
        elif not ln.strip(): flush(); endlist()
        else: endlist(); para.append(ln.strip())
        i += 1
    flush(); endlist(); return "\n".join(out)

# ---------- composer: blocks -> page HTML
BLOCK_TYPES = ("heading", "sub", "text", "image", "split", "quote", "keys", "link", "embed", "divider", "html")
def attr(s): return html.escape(str(s if s is not None else ""), quote=True)

def make_links(cfg, pm):
    """Resolve [[target]]: a page file name or unique page id, a group path (projects/makuraba), a menu id, or a URL."""
    byid = {}
    for s, (_, _, n) in pm.items(): byid.setdefault(n["id"], []).append(s)
    paths = {}
    for m in cfg["menu"]:
        paths[m["id"]] = m["label"]
        for n, trail in walk(m.get("items", [])):
            if "items" in n: paths["/".join([m["id"]] + [x["id"] for x in trail] + [n["id"]])] = n["title"]
    def link(target):
        t = str(target or "").strip()
        if re.match(r"javascript:", t, re.I): return None, None
        if re.match(r"(https?:)?//|mailto:", t): return t, t
        k = t.strip("/")
        if re.match(r"(examples|media)/", t) and (ROOT / re.split(r"[?#]", t)[0]).is_file(): return "../" + t, t  # a demo or file inside this site
        if k in pm: return k + ".html", pm[k][2]["title"]
        if len(byid.get(k, [])) == 1: s = byid[k][0]; return s + ".html", pm[s][2]["title"]
        if k in paths: return "../index.html#" + k, paths[k]
        return None, None
    return link

def compose(blocks, link, where, root="../"):
    out, warns = [], []
    def media(p):
        p = str(p or "").strip()
        return "" if not p else p if re.match(r"(https?:)?//|data:", p) else root + p.lstrip("/")
    def rich(text, dropcap=False):
        def sub(m):
            href, label = link(m.group(1))
            if not href: warns.append(f"{where}: no page, group or URL called [[{m.group(1)}]]"); return m.group(2) or m.group(1)
            return f"[{m.group(2) or label}]({href})"
        parts = re.split(r"(```.*?```|`[^`\n]*`)", str(text or ""), flags=re.S)
        parts[::2] = [re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", sub, x) for x in parts[::2]]
        h = md2html("".join(parts))
        return h.replace("<p>", '<p class="dropcap">', 1) if dropcap else h
    def fig(b):
        src = media(b.get("file"))
        if not src: return ""
        cap = f"<figcaption>{esc(str(b.get('caption', '')))}</figcaption>" if b.get("caption") else ""
        return f'<figure class="fig"><img src="{attr(src)}" alt="{attr(b.get("alt"))}" loading="lazy">{cap}</figure>'
    for b in blocks:
        t = b.get("type")
        if t == "heading":
            lv = 3 if str(b.get("level")) == "3" else 2; out.append(f"<h{lv}>{inline(str(b.get('text', '')))}</h{lv}>")
        elif t == "sub": out.append(f'<div class="sub">{esc(str(b.get("text", "")))}</div>')
        elif t == "text": out.append(rich(b.get("text"), b.get("dropcap")))
        elif t == "image": out.append(fig(b))
        elif t == "split":
            side, text = fig(b), "<div>" + rich(b.get("text"), b.get("dropcap")) + "</div>"
            out.append('<div class="two">' + (side + text if b.get("flip") else text + side) + "</div>")
        elif t == "quote":
            cite = f"<cite>{inline(str(b['cite']))}</cite>" if b.get("cite") else ""
            out.append(f"<blockquote>{inline(' '.join(str(b.get('text', '')).split()))}{cite}</blockquote>")
        elif t == "keys":
            li = []
            for k in b.get("items", []):
                try: hue = max(0, min(360, int(k.get("hue", 40))))
                except (TypeError, ValueError): hue = 40
                li.append(f'<li style="--h:{hue}"><span class="med"></span><div><h3>{esc(str(k.get("title", "")))}</h3><p>{inline(str(k.get("text", "")))}</p></div></li>')
            out.append('<ul class="keys">' + "".join(li) + "</ul>")
        elif t == "link":
            href, label = link(b.get("target"))
            if not href: warns.append(f"{where}: link card target \"{b.get('target', '')}\" not found"); continue
            note = f"<span>{esc(str(b['note']))}</span>" if b.get("note") else ""
            out.append(f'<a class="card" href="{attr(href)}"><strong>{esc(str(b.get("label") or label))}</strong>{note}</a>')
        elif t == "embed":
            src = media(b.get("url"))
            if src: out.append(f'<iframe src="{attr(src)}" title="{attr(b.get("title") or "Embedded page")}" loading="lazy"></iframe>')
        elif t == "divider": out.append("<hr>")
        elif t == "html": out.append(str(b.get("html", "")))
    return re.sub(r'<a (class="card" )?href="(https?://|\.\./examples/)', r'<a \1target="_blank" rel="noopener" href="\2', "\n".join(x for x in out if x)), warns

# ---------- build
def nav_html(cfg, root, current=None):
    rows = []
    for m in cfg["menu"]:
        cur = ' aria-current="true"' if m["id"] == current else ""
        rows.append(f'<a href="{root}index.html#{m["id"]}" data-id="{m["id"]}"{cur}><svg viewBox="0 0 24 24"><path d="{ICONS.get(m["icon"], ICONS["triangle"])}"/></svg><span>{esc(m["label"])}</span></a>')
    return "\n".join(rows)

def export(items):
    out = []
    for n in items:
        e = {"id": n["id"], "title": n["title"]}
        for k in ("summary", "status", "hue"):
            if n.get(k) not in (None, ""): e[k] = n[k]
        if "items" in n: e["items"] = export(n["items"])
        elif "url" in n: e["href"] = n["url"]; e["external"] = bool(re.match(r"(https?:)?//", n["url"]))
        else: e["href"] = "pages/" + n["slug"] + ".html"
        out.append(e)
    return out

def build(cfg=None):
    cfg = cfg or load(); pm = page_map(cfg); warns = []
    for p in (INDEX, TEMPLATE):
        if not p.exists(): die(f"{p.name} is missing")
    data = {"title": cfg.get("title", ""), "menu": [{"id": m["id"], "label": m["label"], "type": m["type"], "items": export(m.get("items", []))} for m in cfg["menu"]]}
    js = "<script>window.HUB=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + ";</script>"
    idx = region(region(INDEX.read_text("utf-8"), "hub:nav", nav_html(cfg, "")), "hub:data", js)
    if cfg.get("title"): idx = re.sub(r"<title>.*?</title>", lambda m: "<title>" + esc(cfg["title"]) + "</title>", idx, count=1)
    changed = write(INDEX, idx)
    template = TEMPLATE.read_text("utf-8"); PAGES.mkdir(exist_ok=True); made = upd = 0; link = make_links(cfg, pm)
    for s, (sec, trail, n) in pm.items():
        f, jf = PAGES / f"{s}.html", PAGES / f"{s}.json"
        if jf.exists():
            try: blocks = json.loads(jf.read_text("utf-8")).get("blocks", [])
            except (ValueError, AttributeError) as e: warns.append(f"pages/{s}.json is not valid ({e}); left alone"); continue
            content, w = compose(blocks, link, f"pages/{s}.json"); warns += w
        elif f.exists():
            content = get_region(f.read_text("utf-8"), "page:content")
            if content is None: warns.append(f"pages/{s}.html has no page:content markers; left alone"); continue
        else: content = ""
        label, where = (trail[-1]["title"], [sec["id"]] + [t["id"] for t in trail]) if trail else (sec["label"], [sec["id"]])
        crumb = f'<a class="crumb" href="../index.html#{"/".join(where)}">\u2039 {esc(label)}</a>'
        page = template.replace("{{title}}", esc(n["title"])).replace("{{summary}}", esc(n.get("summary", ""), True)).replace("{{root}}", "../").replace("{{crumb}}", crumb)
        page = region(region(page, "hub:nav", nav_html(cfg, "../", sec["id"])), "page:content", content)
        existed = f.exists()
        if write(f, page): upd, made = (upd + 1, made) if existed else (upd, made + 1)
    unused = [f.name for f in sorted(PAGES.glob("*.html")) if f.stem not in pm]
    if unused: print(f"note: {len(unused)} file(s) in pages/ are not in the menu, so they are not linked anywhere (harmless): {', '.join(unused[:4])}{'...' if len(unused) > 4 else ''}")
    print(f"built: hub {'updated' if changed else 'unchanged'}, {len(pm)} pages ({made} new, {upd} updated)")
    for w in warns: print("warning:", w, file=sys.stderr)
    return warns

# ---------- editing commands
def parts(path): return [slug(p) for p in path.strip("/").split("/") if p]

def find_list(cfg, path):
    ps = parts(path)
    if not ps: die("give a path such as projects/makuraba")
    sec = next((m for m in cfg["menu"] if m["id"] == ps[0]), None)
    if not sec: die(f'no menu item "{ps[0]}". Menu: {", ".join(m["id"] for m in cfg["menu"])}')
    if sec["type"] != "index": die(f'"{sec["id"]}" has no index list')
    lst, where = sec["items"], sec["id"]
    for p in ps[1:]:
        n = next((x for x in lst if x["id"] == p), None)
        if not n: die(f'"{p}" not found in {where}. Here: {", ".join(x["id"] for x in lst) or "(empty)"}')
        if "items" not in n: die(f'"{p}" is a {kind(n)}, not a group')
        lst, where = n["items"], where + "/" + p
    return lst

def find_node(cfg, path):
    ps = parts(path)
    if len(ps) < 2: die("give the path of an item, such as projects/makuraba")
    lst = find_list(cfg, "/".join(ps[:-1])); n = next((x for x in lst if x["id"] == ps[-1]), None)
    if not n: die(f'"{ps[-1]}" not found in {"/".join(ps[:-1])}. Here: {", ".join(x["id"] for x in lst) or "(empty)"}')
    return lst, n

def place(lst, n, pos):
    lst.insert(max(0, min(len(lst), pos - 1)), n) if pos else lst.append(n)

def make(lst, title, a):
    i = slug(title)
    if any(x["id"] == i for x in lst): die(f'"{i}" already exists there')
    n = {"id": i, "title": title}
    for k in ("summary", "status", "hue"):
        if getattr(a, k, None) not in (None, ""): n[k] = getattr(a, k)
    return n

def done(cfg): save(cfg); build(cfg)

def cmd_group(a):
    cfg = load(); lst = find_list(cfg, a.to); n = make(lst, a.title, a); n["items"] = []; place(lst, n, a.pos); done(cfg)

def cmd_page(a):
    cfg = load(); lst = find_list(cfg, a.to); n = make(lst, a.title, a); s = a.file or n["id"]
    if s in page_map(cfg): die(f'a page file named "{s}" exists; use --file to pick another name')
    n["slug"] = s; place(lst, n, a.pos); done(cfg); print(f"open the editor (python3 hub.py serve, then /edit) to write it, or paste ready-made HTML into pages/{s}.html between the page:content markers")

def cmd_link(a):
    cfg = load(); lst = find_list(cfg, a.to); n = make(lst, a.title, a); n["url"] = a.url; place(lst, n, a.pos); done(cfg)

def cmd_rename(a):
    cfg = load(); _, n = find_node(cfg, a.path); n["title"] = a.title; done(cfg); print("title changed; its id and file name stay the same, so links keep working")

def cmd_set(a):
    cfg = load(); _, n = find_node(cfg, a.path)
    for k in ("summary", "status", "hue", "url"):
        v = getattr(a, k)
        if v is not None:
            if v == "" or v == "none": n.pop(k, None)
            else: n[k] = v
    done(cfg)

def cmd_move(a):
    cfg = load(); src, n = find_node(cfg, a.path); dest = find_list(cfg, a.to)
    if "items" in n and any(dest is g["items"] for g, _ in walk([n])): die("cannot move a group into itself")
    if any(x["id"] == n["id"] for x in dest if x is not n): die(f'"{n["id"]}" already exists at the destination')
    src.remove(n); place(dest, n, a.pos); done(cfg)

def cmd_remove(a):
    cfg = load(); lst, n = find_node(cfg, a.path)
    pages = [x["slug"] for x, _ in walk([n]) if kind(x) == "page"]
    if "items" in n and n["items"] and not a.yes: die(f'"{n["id"]}" contains {len(n["items"])} items; add --yes to remove it and everything inside')
    lst.remove(n); save(cfg)
    if a.delete_files:
        for s in pages:
            for ext in (".html", ".md"): (PAGES / (s + ext)).unlink(missing_ok=True)
    build(cfg)
    if pages and not a.delete_files: print("the page files were kept; add --delete-files to remove them")

def cmd_menu_add(a):
    cfg = load(); i = slug(a.label)
    if any(m["id"] == i for m in cfg["menu"]): die(f'menu item "{i}" exists')
    m = {"id": i, "label": a.label, "type": "index", "icon": a.icon if a.icon in ICONS else "triangle", "items": []}
    place(cfg["menu"], m, a.pos); done(cfg)

def menu_item(cfg, i):
    m = next((x for x in cfg["menu"] if x["id"] == slug(i)), None)
    if not m: die(f'no menu item "{i}". Menu: {", ".join(x["id"] for x in cfg["menu"])}')
    return m

def cmd_menu_rename(a): cfg = load(); menu_item(cfg, a.id)["label"] = a.label; done(cfg)

def cmd_menu_move(a):
    cfg = load(); m = menu_item(cfg, a.id); cfg["menu"].remove(m); place(cfg["menu"], m, a.pos); done(cfg)

def cmd_menu_remove(a):
    cfg = load(); m = menu_item(cfg, a.id)
    if m["type"] == "home": die("Home cannot be removed")
    if m.get("items") and not a.yes: die(f'"{m["id"]}" contains {len(m["items"])} items; add --yes to remove it and everything inside')
    cfg["menu"].remove(m); done(cfg)

def cmd_list(a):
    cfg = load()
    def show(items, path, depth):
        for n, in [(x,) for x in items]:
            p = path + "/" + n["id"]; k = kind(n)
            extra = f'pages/{n["slug"]}.html' if k == "page" else n.get("url", "")
            print("  " * depth + f'{n["title"]}  [{k}]  {p}  {extra}'.rstrip())
            if k == "group": show(n["items"], p, depth + 1)
    for m in cfg["menu"]:
        print(f'{m["label"]}  ({m["id"]})'); show(m.get("items", []), m["id"], 1)

def cmd_build(a): build()

def cmd_reset(a):
    if not a.yes: die("this moves every page, picture and example into a backup folder and empties the menu; add --yes to confirm")
    bk = ROOT / ("backup-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")); moved = []
    for name in ("hub.json", "pages", "media", "examples"):
        src = ROOT / name
        if src.exists(): bk.mkdir(exist_ok=True); shutil.move(str(src), str(bk / name)); moved.append(name)
    build(); print(f"started fresh. Moved {', '.join(moved) or 'nothing'} into {bk.name}/ (delete it when you no longer need it)")

# ---------- GitHub token (paste it once in the editor; it is remembered on this device only)
TOKEN_FILE = ROOT / ".hub-token"

def ensure_ignored():
    """The token file must never be committed. Make sure .gitignore always lists it."""
    gi = ROOT / ".gitignore"; cur = gi.read_text("utf-8") if gi.exists() else ""
    if ".hub-token" not in cur.split():
        gi.write_text(cur + ("" if cur.endswith("\n") or not cur else "\n") + ".hub-token\n", "utf-8")

def get_token():
    t = os.environ.get("GITHUB_TOKEN", "").strip()
    if t: return t
    try: return TOKEN_FILE.read_text("utf-8").strip()
    except OSError: return ""

def set_token(t):
    ensure_ignored()
    if not t: TOKEN_FILE.unlink(missing_ok=True); return
    TOKEN_FILE.write_text(t + "\n", "utf-8")
    try: os.chmod(TOKEN_FILE, 0o600)
    except OSError: pass

def origin_url():
    try: return git("remote", "get-url", "origin", timeout=10).stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired): return ""

def repo_parts(url=None):
    m = re.search(r"github\.com[:/]+([^/]+)/([^/]+?)(?:\.git)?/?$", url if url is not None else origin_url())
    return (m.group(1), m.group(2)) if m else (None, None)

def live_url():
    o, r = repo_parts()
    if not o: return ""
    return f"https://{o.lower()}.github.io/" + ("" if r.lower() == o.lower() + ".github.io" else r + "/")

def check_token(t):
    """Ask GitHub whether this token can write to this repo. Returns (True/False/None, plain sentence). None = could not tell."""
    o, r = repo_parts()
    if not o: return None, "Saved. (This folder has no GitHub address to check it against.)"
    req = urllib.request.Request(f"https://api.github.com/repos/{o}/{r}", headers={"Authorization": "Bearer " + t, "Accept": "application/vnd.github+json", "User-Agent": "makuraba-hub"})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp: d = json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403): return False, "GitHub did not accept that token. Check you copied all of it, and that it has not expired."
        if e.code == 404: return False, f"That token cannot see the repository {o}/{r}. When making the token, select that repository."
        return None, "Saved, but GitHub gave an unexpected answer so it could not be checked."
    except Exception: return None, "Saved, but could not reach GitHub to check it. Press PUBLISH to find out."
    if d.get("permissions", {}).get("push") is False: return False, "That token can only read this repository. Create one with Contents: Read and write."
    return True, "Connected. You can press PUBLISH now."

# ---------- git helpers (used by the PUBLISH button and the publish command)
def git(*c, timeout=90):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")  # fail with a message instead of hanging on a password prompt
    t = get_token()
    if t:  # hand the token to git through the environment, so it is never written into .git/config or the remote address
        auth = base64.b64encode(("x-access-token:" + t).encode()).decode()
        env.update(GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="http.https://github.com/.extraheader", GIT_CONFIG_VALUE_0="Authorization: Basic " + auth)
    return subprocess.run(["git", *c], cwd=ROOT, capture_output=True, text=True, timeout=timeout, env=env)

def git_words(r):
    """Turn a failed git result into one plain sentence."""
    t = ((r.stderr or "") + (r.stdout or "")).strip(); low = t.lower()
    if any(k in low for k in ("authentication failed", "could not read username", "permission denied", "403", "invalid username or token", "terminal prompts disabled", "write access to repository not granted")):
        return "GitHub did not accept your login. Press the 🔑 button in the editor and paste your token (or in a terminal run:  gh auth login ), then press PUBLISH again."
    if any(k in low for k in ("could not resolve host", "unable to access", "network is unreachable", "timed out")):
        return "Could not reach GitHub. Check your internet connection, then press PUBLISH again. Your changes are safe."
    if "no configured push destination" in low or "does not appear to be a git repository" in low:
        return "This folder is not connected to a GitHub repository yet (no remote)."
    return "Git said: " + (" ".join(t.splitlines()[-3:]) or "something went wrong")

def publish_now(message=""):
    """Build, commit, push. Returns (ok, one plain sentence). Never raises."""
    try: build()
    except SystemExit as e: return False, f"The site could not be built: {e}"
    try:
        if git("rev-parse", "--is-inside-work-tree").returncode: return False, "This folder is not a git repository, so there is nothing to publish to."
        ensure_ignored(); git("add", "-A")
        if ".hub-token" in git("diff", "--cached", "--name-only").stdout.split():  # belt and braces: the token must never be published
            git("rm", "--cached", "-q", ".hub-token"); return False, "Safety stop: the token file was about to be published. It has been removed from the list; press PUBLISH again."
        ident =[] if git("config", "user.name").stdout.strip() and git("config", "user.email").stdout.strip() else ["-c", "user.name=Makuraba Editor", "-c", "user.email=editor@makuraba.local"]
        if git("diff", "--cached", "--quiet").returncode != 0:
            r = git(*ident, "commit", "-m", (message or "").strip() or "Update site " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
            if r.returncode: return False, git_words(r)
        elif not git_unpushed(): return True, "Nothing new to publish. The site is already up to date."
        p = git("push")
        if p.returncode:  # GitHub may hold newer changes (edited elsewhere): fold them in, then try once more
            pl = git(*ident, "pull", "--rebase", "--autostash")
            if pl.returncode:
                clash = "conflict" in ((pl.stdout or "") + (pl.stderr or "")).lower()
                if clash: git("rebase", "--abort")
                return False, ("GitHub has newer changes that overlap with yours, so nothing was sent. Your work is safe in this folder; ask Claude to help merge them." if clash else git_words(pl) + " Your work is safe in this folder.")
            p = git("push")
        if p.returncode: return False, git_words(p)
        return True, "Published! Your site updates in about a minute."
    except FileNotFoundError: return False, "git is not installed. In Termux run:  pkg install git"
    except subprocess.TimeoutExpired: return False, "That took too long and was stopped. Check your internet connection and press PUBLISH again."

def git_unpushed():
    r = git("rev-list", "--count", "@{u}..HEAD")
    return int(r.stdout.strip() or 0) if r.returncode == 0 else 0

def publish_status():
    try:
        r = git("status", "--porcelain")
        if r.returncode: return {"git": False, "changes": 0, "token": bool(get_token())}
        n = len([l for l in r.stdout.splitlines() if l.strip() and ".hub-token" not in l])
        return {"git": True, "changes": n, "unpushed": git_unpushed(), "dirty": n > 0 or git_unpushed() > 0, "token": bool(get_token()), "live": live_url()}
    except (FileNotFoundError, subprocess.TimeoutExpired): return {"git": False, "changes": 0, "token": bool(get_token())}

def cmd_publish(a):
    ok, msg = publish_now(a.message)
    print(msg)
    if not ok: sys.exit(1)

class ApiError(Exception):
    def __init__(self, msg, code=400): super().__init__(msg); self.code = code

LOCK, STATE = threading.RLock(), {"sig": ()}
def sig(): return tuple((str(f), f.stat().st_mtime) for f in [CFG, TEMPLATE] + list(PAGES.glob("*.json")) if f.exists())
def write_atomic(p, text): tmp = p.with_name(p.name + ".tmp"); tmp.write_text(text, "utf-8"); tmp.replace(p)

# ---------- demos: drop a file, folder or zip; it lands in examples/<name>/ and gets a page
DEMO_EXT = {".html", ".htm", ".css", ".js", ".mjs", ".json", ".txt", ".md", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".avif", ".ico", ".mp3", ".wav", ".ogg", ".mp4", ".webm", ".woff", ".woff2", ".ttf", ".otf", ".wasm", ".glb", ".gltf", ".bin", ".obj", ".mtl", ".map"}

def safe_rel(name):
    """A relative path made only of harmless pieces: no '..', no leading dots, no odd characters."""
    segs = []
    for s in str(name).replace("\\", "/").split("/"):
        s = re.sub(r"[^A-Za-z0-9._-]", "-", s).lstrip(".-")
        if s: segs.append(s[-100:])
    return "/".join(segs)

def demo_write(d, rel, data):
    rel = safe_rel(rel)
    if not rel or pathlib.PurePosixPath(rel).suffix.lower() not in DEMO_EXT: return False
    p = (d / rel).resolve()
    if d.resolve() not in p.parents: return False
    p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data); return True

def demo_zip(d, data):
    z = zipfile.ZipFile(io.BytesIO(data))
    infos = [i for i in z.infolist() if not i.is_dir() and not i.filename.startswith("__MACOSX/")]
    if len(infos) > 3000 or sum(i.file_size for i in infos) > 300_000_000: raise ApiError("that zip is too big (limit 3000 files, 300 MB unpacked)")
    names = [i.filename.replace("\\", "/") for i in infos]
    strip = len({n.split("/")[0] for n in names}) == 1 and all("/" in n for n in names)  # a zip that wraps everything in one folder
    return sum(demo_write(d, n.split("/", 1)[1] if strip else n, z.read(i)) for i, n in zip(infos, names))

def demo_entry(d):
    if (d / "index.html").exists(): return "index.html"
    hs = sorted((p.relative_to(d).as_posix() for p in d.rglob("*") if p.suffix.lower() in (".html", ".htm")), key=lambda s: (s.count("/"), s))
    return hs[0] if hs else ""

def route(method, name, q, body):
    if (method, name) == ("GET", "config"): return {"config": load()}
    if (method, name) == ("PUT", "config"):
        cfg = json.loads(body)
        if not isinstance(cfg, dict) or not isinstance(cfg.get("menu"), list): raise ApiError("bad config")
        normalize(cfg); page_map(cfg); save(cfg); w = build(cfg); STATE["sig"] = sig(); return {"config": cfg, "warnings": w}
    if (method, name) == ("POST", "demo"):
        f = slug((q.get("folder") or [""])[0] or "demo"); d = ROOT / "examples" / f; fn = (q.get("name") or ["file"])[0]; d.mkdir(parents=True, exist_ok=True)
        try: n = demo_zip(d, body) if fn.lower().endswith(".zip") else int(demo_write(d, fn, body))
        except zipfile.BadZipFile: raise ApiError("that zip file could not be opened")
        return {"folder": f, "saved": n, "entry": demo_entry(d)}
    if (method, name) == ("POST", "demo-page"):
        b = json.loads(body or b"{}"); title = str(b.get("title") or "").strip() or "New demo"; sec = slug(b.get("section") or "games"); cfg = load()
        m = next((x for x in cfg["menu"] if x["id"] == sec and x["type"] == "index"), None)
        if not m: raise ApiError("pick a menu section that has a list, such as Games & Demos")
        url = str(b.get("url") or "").strip()
        if url:
            if not re.match(r"https?://", url, re.I): raise ApiError("a link must start with https://")
            target = url
        else:
            f = slug(b.get("folder") or ""); d = ROOT / "examples" / f; ent = demo_entry(d) if d.is_dir() else ""
            if not ent: raise ApiError("no HTML file was found in what you dropped, so there is nothing to show")
            target = f"examples/{f}/{ent}"
        pm = page_map(cfg); base = slug(title); s = base; i = 2
        while s in pm or any(x["id"] == s for x in m["items"]): s = f"{base}-{i}"; i += 1
        m["items"].append({"id": s, "title": title, "slug": s, "summary": "Interactive demo"})
        blocks = [{"type": "embed", "url": target, "title": title}, {"type": "link", "target": target, "label": "Open full screen", "note": "Opens the demo on its own, in a new tab."}]
        PAGES.mkdir(exist_ok=True); write_atomic(PAGES / f"{s}.json", json.dumps({"blocks": blocks}, indent=1, ensure_ascii=False) + "\n")
        save(cfg); w = build(cfg); STATE["sig"] = sig(); return {"config": cfg, "section": sec, "id": s, "warnings": w}
    if (method, name) == ("GET", "status"): return publish_status()
    if (method, name) == ("POST", "token"):  # the token itself is never sent back, only whether one is saved
        try: t = str(json.loads(body or b"{}").get("token", "")).strip()
        except ValueError: t = ""
        if not t: set_token(""); return {"ok": True, "message": "Token forgotten. Paste a new one anytime.", **publish_status()}
        if re.search(r"\s", t) or len(t) < 20: return {"ok": False, "message": "That does not look like a full token (no spaces, and it is long). Try copying it again.", **publish_status()}
        good, words = check_token(t)
        if good is False: return {"ok": False, "message": words, **publish_status()}
        set_token(t); return {"ok": True, "message": words, **publish_status()}
    if (method, name) == ("POST", "publish"):
        try: msg = str(json.loads(body or b"{}").get("message", ""))
        except ValueError: msg = ""
        ok, words = publish_now(msg); return {"ok": ok, "message": words, **publish_status()}
    s = (q.get("slug") or [""])[0]
    if name in ("page", "upload"):
        cfg = load()
        if s not in page_map(cfg): raise ApiError("no such page", 404)
    if (method, name) == ("GET", "page"):
        jf, f = PAGES / f"{s}.json", PAGES / f"{s}.html"
        if jf.exists(): return {"source": "blocks", "blocks": json.loads(jf.read_text("utf-8")).get("blocks", [])}
        c = (get_region(f.read_text("utf-8"), "page:content") or "") if f.exists() else ""
        return {"source": "html" if c.strip() else "new", "blocks": [{"type": "html", "html": c}] if c.strip() else []}
    if (method, name) == ("PUT", "page"):
        bl = json.loads(body).get("blocks")
        if not isinstance(bl, list) or any(not isinstance(x, dict) or x.get("type") not in BLOCK_TYPES for x in bl): raise ApiError("bad blocks")
        PAGES.mkdir(exist_ok=True); write_atomic(PAGES / f"{s}.json", json.dumps({"blocks": bl}, indent=1, ensure_ascii=False) + "\n")
        w = build(cfg); STATE["sig"] = sig(); return {"ok": True, "warnings": w}
    if (method, name) == ("POST", "upload"):
        fn = re.sub(r"[^A-Za-z0-9._-]", "-", (q.get("name") or ["image"])[0])[-80:].lstrip(".-") or "image"
        if not re.search(r"\.(jpe?g|png|gif|webp|svg|avif)$", fn, re.I): raise ApiError("images only: jpg, png, gif, webp, svg, avif")
        d = ROOT / "media" / s; d.mkdir(parents=True, exist_ok=True); (d / fn).write_bytes(body)
        return {"path": f"media/{s}/{fn}"}
    raise ApiError("not found", 404)

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *x): pass
    def end_headers(self): self.send_header("Cache-Control", "no-store"); super().end_headers()
    def send_json(self, code, obj):
        b = json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def api(self, method):
        if self.headers.get("Host", "").split(":")[0] not in ("localhost", "127.0.0.1") or self.headers.get("X-Hub") != "1": return self.send_json(403, {"error": "forbidden"})
        u = urllib.parse.urlparse(self.path); n = int(self.headers.get("Content-Length") or 0)
        if n > 40_000_000: return self.send_json(413, {"error": "file too large (limit 40 MB)"})
        body = self.rfile.read(n) if n else b""
        try:
            with LOCK: res = route(method, u.path[len("/_api/"):], urllib.parse.parse_qs(u.query), body)
            self.send_json(200, res)
        except ApiError as e: self.send_json(e.code, {"error": str(e)})
        except (SystemExit, ValueError) as e: self.send_json(400, {"error": str(e)})
        except Exception as e: self.send_json(500, {"error": f"{type(e).__name__}: {e}"})
    def do_GET(self):
        p = urllib.parse.urlparse(self.path).path
        if p.startswith("/_api/"): return self.api("GET")
        if p in ("/edit", "/edit/"):
            ed = ROOT / "tools" / "editor.html"
            if not ed.exists(): return self.send_json(404, {"error": "tools/editor.html is missing"})
            b = ed.read_bytes(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(b))); self.end_headers(); return self.wfile.write(b)
        super().do_GET()
    def do_PUT(self): self.api("PUT") if self.path.startswith("/_api/") else self.send_json(404, {})
    def do_POST(self): self.api("POST") if self.path.startswith("/_api/") else self.send_json(404, {})

def watch():
    STATE["sig"] = sig()
    while True:
        time.sleep(1); cur = sig()
        if cur != STATE["sig"]:
            with LOCK:
                STATE["sig"] = cur
                try: build()
                except SystemExit as e: print(e)
                except Exception as e: print("build failed:", e)

def cmd_serve(a):
    build(); threading.Thread(target=watch, daemon=True).start()
    try: srv = http.server.ThreadingHTTPServer(("127.0.0.1", a.port), functools.partial(Handler, directory=str(ROOT)))
    except OSError: die(f"port {a.port} is busy; try --port {a.port + 1}")
    print(f"site:   http://localhost:{a.port}\neditor: http://localhost:{a.port}/edit\n(Ctrl+C stops. Editing hub.json or template.html also rebuilds.)")
    try: srv.serve_forever()
    except KeyboardInterrupt: print("\nstopped")

def open_browser(url):
    """Open the editor for you. Termux first (its own opener), then the normal way. Never fails loudly."""
    try:
        if shutil.which("termux-open-url"): subprocess.Popen(["termux-open-url", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else: webbrowser.open(url)
    except Exception: pass

def cmd_go(a):
    """The one command: get the latest from GitHub, build, start, open the editor."""
    print("\n  MAKURABA - starting...\n"); ensure_ignored()
    try:  # start from whatever is newest on GitHub (quietly; skipped if offline or not set up)
        if git("rev-parse", "--is-inside-work-tree", timeout=10).returncode == 0 and git("remote", timeout=10).stdout.strip():
            r = git("pull", "--rebase", "--autostash", timeout=25)
            print("  synced with GitHub" if r.returncode == 0 else "  (could not sync with GitHub right now; continuing with what is on this device)")
    except (FileNotFoundError, subprocess.TimeoutExpired): pass
    build(); threading.Thread(target=watch, daemon=True).start()
    srv = port = None
    for port in range(a.port, a.port + 11):
        try: srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Handler, directory=str(ROOT))); break
        except OSError: continue
    if not srv: die("could not find a free port (8000-8010). Close other programs using them and try again.")
    url = f"http://localhost:{port}/edit"
    print(f"""
  ============================================================
   READY. The editor should open by itself. If it does not,
   open this address in your browser:

       {url}

   1. Pick something on the left and type your changes.
      (They save by themselves.)
   2. Press the big gold PUBLISH button.
   3. That is all. Close this window or press Ctrl+C to stop.
  ============================================================
""")
    threading.Timer(0.8, open_browser, [url]).start()
    try: srv.serve_forever()
    except KeyboardInterrupt: print("\n  stopped. Bye!")

def main():
    ap = argparse.ArgumentParser(prog="hub.py", description=__doc__.split("\n")[0] + ". With no command it runs `go`: opens the editor."); sub = ap.add_subparsers(dest="cmd", required=False, metavar="command")
    def sp(name, fn, help, *pos, to=False, opts=()):
        p = sub.add_parser(name, help=help)
        for x in pos: p.add_argument(x)
        if to: p.add_argument("--to", required=True, help="where it goes, e.g. projects/makuraba")
        for o in opts: p.add_argument(*o[0], **o[1])
        p.set_defaults(fn=fn); return p
    P = ("--pos", dict(type=int, help="position, starting at 1 (default: end)")); S = ("--summary", dict()); T = ("--status", dict()); Hh = ("--hue", dict(type=int))
    sp("go", cmd_go, "THE EASY WAY: sync, build, start, and open the editor (this is what plain `python3 hub.py` does)", opts=[(["--port"], dict(type=int, default=8000))])
    sp("list", cmd_list, "show the menu and every index list"); sp("build", cmd_build, "rebuild index.html and all pages from hub.json")
    sp("serve", cmd_serve, "build, then serve the site and the visual editor (/edit) at http://localhost:8000", opts=[(["--port"], dict(type=int, default=8000))])
    sp("publish", cmd_publish, "build, git commit, git push", "message")
    sp("reset", cmd_reset, "start fresh: move all pages, pictures and examples into a backup folder and restore the empty menu", opts=[(["--yes"], dict(action="store_true"))])
    sp("group", cmd_group, "add a topic/subtopic (a group that holds more items)", "title", to=True, opts=[(["--summary"], {}), (["--hue"], dict(type=int)), (list(P[:1]), P[1])])
    sp("page", cmd_page, "add a page (creates pages/<name>.html)", "title", to=True, opts=[(["--summary"], {}), (["--status"], {}), (["--file"], dict(help="file name without .html")), (list(P[:1]), P[1])])
    sp("link", cmd_link, "add a link to a URL or another file", "title", "url", to=True, opts=[(["--summary"], {}), (["--status"], {}), (list(P[:1]), P[1])])
    sp("rename", cmd_rename, "change an item's title", "path", "title")
    sp("set", cmd_set, "change summary/status/hue/url of an item (use none to clear)", "path", opts=[(["--summary"], dict(default=None)), (["--status"], dict(default=None)), (["--hue"], dict(default=None, type=int)), (["--url"], dict(default=None))])
    sp("move", cmd_move, "move an item somewhere else", "path", to=True, opts=[(list(P[:1]), P[1])])
    sp("remove", cmd_remove, "remove an item from the lists", "path", opts=[(["--yes"], dict(action="store_true")), (["--delete-files"], dict(action="store_true"))])
    sp("menu-add", cmd_menu_add, "add a left-hand menu item", "label", opts=[(["--icon"], dict(default="triangle", help=", ".join(ICONS))), (list(P[:1]), P[1])])
    sp("menu-rename", cmd_menu_rename, "change a menu item's label", "id", "label")
    sp("menu-move", cmd_menu_move, "reorder the menu", "id", "pos").set_defaults()
    sp("menu-remove", cmd_menu_remove, "remove a menu item", "id", opts=[(["--yes"], dict(action="store_true"))])
    a = ap.parse_args()
    if not a.cmd: a = ap.parse_args(["go"])
    if a.cmd == "menu-move": a.pos = int(a.pos)
    a.fn(a)

if __name__ == "__main__": main()
