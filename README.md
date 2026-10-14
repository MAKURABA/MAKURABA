# Makuraba hub

Two pages, one tool, one visual editor.

- `index.html` is the hub page. `template.html` is the one template every other page is made from.
- `hub.json` says what the left-hand directory and every index list contain.
- `hub.py` builds everything. `tools/editor.html` is the visual editor it serves.

There is no sample content. Everything starts empty except the five menu items.

## Run it

```
python3 hub.py serve
```

- Site: http://localhost:8000
- Editor: http://localhost:8000/edit

Leave it running while you work. In Termux: `pkg install python git`, run the same command, and open the addresses in your phone browser. Open the site this way, not by double-clicking `index.html`, because the background needs a web server.

## The editor

Three panes (tabs on a phone): **Structure**, **Page**, **Preview**. Changes save by themselves a moment after you stop typing, and the preview reloads from the real template.

- **Structure** is the left-hand directory. `＋` adds a group, page or link inside an item. ↑ ↓ reorder, ⇄ moves to another group, ✕ removes (page files stay on disk).
- **Page** edits the title, summary and status shown in the hub lists, then the page content as blocks:
  Heading, Subtitle, Text, Picture, Text + picture, Quote, Medallion list, Link card, Embed, Divider, Raw HTML.
- Pictures you add are uploaded to `media/<page>/`.

Saving writes `hub.json` and `pages/<name>.json`, then rebuilds `index.html` and the page, so the directory on every page and the index lists stay in step.

## Linking pages

In any Text block, or in a Link card:

- `[[page-name]]` or `[[page-name|your words]]` links a page (its file name, or its id if unique)
- `[[projects/makuraba]]` opens that group in the hub; `[[projects]]` opens a menu section
- `https://…` links open in a new tab

Anything that cannot be resolved is reported after saving, so there are no silent dead links.
An **Embed** block shows any page in a frame: another site, or a folder of your own with an `index.html` (for example `examples/cube/index.html`, a 3D or canvas demo). A **Link card** can point at one too.

## The agreement

1. `hub.json` is the single source of truth for the menu and every index list.
2. `hub.py` writes only inside marked regions: `hub:nav` (the directory, in every page), `hub:data` (index lists, in `index.html`) and `page:content` (the page body).
3. A page's body is composed from `pages/<name>.json`. If a page has no `.json`, its hand-written HTML between the markers is kept exactly as written, and the editor loads it as one Raw HTML block.
4. Everything outside the markers is yours. Never delete a marker.
5. Every page is `template.html` plus its body, so editing the template changes every page.

## Command line (optional)

```
python3 hub.py list
python3 hub.py group "Makuraba" --to projects
python3 hub.py page "Root design" --to projects/makuraba
python3 hub.py link "GitHub Pages docs" https://docs.github.com/pages --to library
python3 hub.py rename|set|move|remove ...
python3 hub.py menu-add|menu-rename|menu-move|menu-remove ...
python3 hub.py build
python3 hub.py publish "what changed"
```

Run `python3 hub.py -h` for all options. You can also edit `hub.json` by hand and run `build`.

## Publishing

`python3 hub.py publish "message"` builds, commits and pushes. In GitHub, Settings > Pages should deploy from the `main` branch, `/ (root)`. Commit `media/` and `pages/` with everything else. The editor file `tools/editor.html` is only used locally; it does nothing on the published site.

## Look

- `core/theme.css`: colours and sizes (edit `:root`); the page look is the block at the bottom
- `core/assets/`: wordmark, emblem, marble, parchment, background art
- `core/shell.js` drawer, `core/hub.js` index lists, `core/art.js` living background
