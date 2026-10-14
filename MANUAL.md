# Makuraba hub: user manual

*Everything you need to run, edit, publish and update the site. October 2026.*

## 1. What you have

Two pages, one tool, and a visual editor.

| File or folder | What it is | Yours to edit? |
|---|---|---|
| `hub.json` | The single source of truth: the left-hand directory and every index list | Yes (the editor writes it) |
| `pages/` | One `.html` and one `.json` per page, made by the tool | Edit with the editor, not by hand |
| `media/` | Pictures you upload in the editor | Yes |
| `examples/` | Your own HTML, 3D or canvas demos, one folder each with an `index.html` | Yes |
| `index.html` | The hub page: directory, index lists, living background | Style it; keep the marked regions |
| `template.html` | The one template every other page is made from | Style it; keep the marked regions |
| `hub.py` | The tool: builds everything and serves the editor | No (replace it to update) |
| `tools/editor.html` | The visual editor | No (replace it to update) |
| `core/` | Look and behaviour: theme, scripts, artwork | Colours in `theme.css`; otherwise no |

The sample pages in this package exist to show what is possible. Section 12 shows how to clear them in one command.

## 2. Quick start

You need Python 3.8 or newer. On Termux (Android): `pkg install python git`.

1. Open a terminal in the hub folder.
2. Run: `python3 hub.py serve`
3. Open `http://localhost:8000` to see the site and `http://localhost:8000/edit` for the editor.

Leave it running while you work; stop it with Ctrl+C. Always open the site this way rather than double-clicking `index.html`, because the animated background needs a web server. If port 8000 is busy, use `python3 hub.py serve --port 8001`.

## 3. The editor

On a phone it has three tabs; on a wide screen all three show at once.

- **Structure**: your directory. `＋` adds a group, page or link inside an item. `↑` `↓` reorder. `⇄` moves an item to another group. `✕` removes it (page files stay on disk). **＋ Menu item** adds a new section to the left-hand menu.
- **Page**: the title, summary and status shown in the hub lists, then the page content as blocks.
- **Preview**: the real page, from the real template. It refreshes after every save.

Changes save by themselves about a second after you stop typing. The status at the top right says *Saved* when done. Any problem, such as a link that points nowhere, is shown there too.

## 4. Everyday tasks

**Add a page.** Structure, `＋` on a menu item or group, Page, give it a title. It opens ready for blocks.

**Add a topic with sub-topics.** `＋`, Group, name it. Then `＋` on the group to add pages or more groups inside it. Groups can nest as deep as you like.

**Add a link to another website.** `＋`, Link, give a title and a web address. It appears in that list and opens in a new tab.

**Put a picture on a page.** Add a **Picture** or **Text + picture** block (**Text + picture** is under **More blocks**), then choose a file. It is uploaded to `media/<page>/` and shown framed.

**Link one page to another.** In any text, type `[[page-name]]`. See section 6.

**Show a 3D or HTML demo.** Put a folder in `examples/` with an `index.html`, then add an **Embed** block pointing at `examples/your-folder/index.html`. Section 7 has the details.

**Bring in a page you already made.** See section 8.

**Reorder or move.** Use `↑` `↓` and `⇄` in Structure. Order in the lists is exactly the order you set.

**Rename.** Change the title in the Page tab. The page's file name and id stay the same, so links keep working.

**Mark progress.** The Status field (for example `draft`, `live`, `planned`) shows as a tag in the hub lists. Leave it empty for no tag.

**Remove.** `✕` in Structure. The page's files remain in `pages/` and `media/` until you delete them yourself.

## 5. Blocks

| Block | Fields | Result |
|---|---|---|
| Heading | text, section or small | A gold-ruled section title |
| Subtitle | text | The small tracked line under a title |
| Text | text, drop cap | Paragraphs, lists, bold, italic, code, links (Markdown) |
| Picture | file, alt text, caption | A framed picture |
| Text + picture | text, drop cap, file, alt, caption, picture first | Text beside a picture; stacked on a phone |
| Quote | text, source | The dark pull-quote panel |
| Medallion list | name, colour (0 to 360), description, repeated | A list with a glowing medallion per entry |
| Link card | goes to, title, note | A clickable card to a page, group or web address |
| Embed | address, short title | Another page shown in a frame |
| Divider | none | A thin gold line |
| Raw HTML | html | Exactly what you type, for anything the blocks do not cover |

The editor shows the five you use most (Heading, Text, Picture, Link card, Divider) as buttons; the rest are under **More blocks**. Use the arrows on a block to reorder it, `✕` to delete it. The **Block reference** page shows each one in use.

## 6. Linking pages

Write these in any Text block, or as the target of a Link card:

- `[[page-name]]` links a page (its file name, or its id if no other page shares it)
- `[[page-name|your words]]` links a page with your own wording
- `[[projects/makuraba]]` opens a whole group in the hub, as one reference
- `[[library]]` opens a menu section
- `[words](https://example.com)` is an ordinary web link and opens in a new tab

Text inside code (backticks or a fenced block) is left exactly as typed. If a link cannot be resolved, the editor reports it when you save and the words stay as plain text.

## 7. Examples and embeds

An example is any folder inside `examples/` that has an `index.html`. It can use its own CSS, JavaScript, canvas or WebGL, and include its own pictures. Two are included: `examples/cube/` (a CSS 3D cube) and `examples/spiral/` (a canvas animation).

Show one inside a page with an Embed block (`examples/cube/index.html`). That keeps your directory and header around it. Opening an example's address directly shows it alone, without the menu, so prefer embedding. Embeds also take web addresses, provided the other site allows being framed.

## 8. Adding a page you already have

You can bring in a page you made somewhere else. Pick the way that fits.

**A. Paste it into the editor (easiest).** Make a new page (section 4), add a **Raw HTML** block (under **More blocks**), paste your HTML into it. Use this for content that is already a piece of a page: headings, paragraphs, pictures, tables.

**B. It is a whole standalone page** (it has its own `<html>`, styles and scripts, such as a game or an animation). Make a folder `examples/your-page/`, save it there as `index.html` (with any pictures or scripts next to it), make a new page, and add an **Embed** block pointing at `examples/your-page/index.html`. If you reset the site, create the `examples/` folder again first. Your page stays exactly as it is, with the site's menu and header around it.

**C. Put the HTML straight into the file.** Make a new page, open `pages/<name>.html`, and paste your HTML between `<!-- page:content:start -->` and `<!-- page:content:end -->`. Keep those two lines. It is kept exactly as written, and the editor shows it as one Raw HTML block.

After any of these, run `python3 hub.py build` (or just leave `serve` running), look at the page, then publish (section 9).

Pictures that belong to a pasted page go in `media/` (use the **Picture** block to upload them), or next to the page in `examples/`.

## 9. Publishing to GitHub

**First time (once).**

1. Make a free account at github.com. Turn on two-factor sign-in.
2. Make a new empty **public** repository named `YOUR-NAME.github.io` (your user name, then `.github.io`).
3. On your device: `pkg install python git gh` (Termux; elsewhere install Python and Git). Run `gh auth login` and follow the prompts.
4. Set your name once: `git config --global user.name "Your Name"` and `git config --global user.email "you@example.com"`.
5. Clone the empty repository and unzip the hub into it: `git clone https://github.com/YOUR-NAME/YOUR-NAME.github.io`, then `cd` into it and run `unzip -o makuraba-hub.zip`.
6. If you want a clean start, run `python3 hub.py reset --yes` (section 12).
7. On GitHub open the repository, **Settings**, **Pages**, choose to deploy from the `main` branch, folder `/ (root)`.
8. Run `python3 hub.py publish "first version"`. After about a minute your site is at `https://YOUR-NAME.github.io`.

**Every time after that.** Edit in the editor, then run:

`python3 hub.py publish "what changed"`

It rebuilds, commits everything, and pushes. The site updates about a minute later. `python3 hub.py build` only rebuilds, without pushing.

What gets committed: everything except `backup-*` folders. `pages/`, `media/` and `examples/` must be committed too, because the published site needs them.

**Who can change your site.** Only people who can push to your repository. The published site is plain files and has no editor running, so visitors cannot change anything. (`tools/editor.html` is published with the rest, but it does nothing without the program on your own device.) Do not add collaborators unless you want them to edit, and keep two-factor sign-in on.

## 10. Updating

**Updating your content.** Use the editor, then publish. Nothing else is needed.

**Updating the tool.** When you receive a newer package, copy only these from it into your folder, replacing the old ones: `hub.py`, `tools/` and `core/`. Never replace `hub.json`, `pages/`, `media/` or `examples/`. If you have not restyled `index.html` or `template.html`, you may replace those too; if you have, keep yours. Then run `python3 hub.py build` and look at the site. If the editor was open, reload it.

**Changing the look of every page.** Edit `template.html` (layout) or `core/theme.css` (colours and type; the values at the top are the tokens). Run `python3 hub.py build` and every page is rebuilt from the template. In `template.html`, keep the `hub:nav` and `page:content` markers and the tokens `{{title}}`, `{{summary}}`, `{{root}}` and `{{crumb}}`.

**Changing the menu.** In the editor use **＋ Menu item**. From the command line: `python3 hub.py menu-add "Archive"`.

**The agreement.** The tool writes only between marked comments: `hub:nav` (the directory, in every page), `hub:data` (the lists, in `index.html`) and `page:content` (the body). Everything else is yours. Never delete a marker.

## 11. Command reference

| Command | Does |
|---|---|
| `python3 hub.py serve [--port N]` | Builds, then serves the site and the editor |
| `python3 hub.py build` | Rebuilds the hub and every page |
| `python3 hub.py publish "message"` | Builds, commits, pushes |
| `python3 hub.py list` | Prints the directory and every list |
| `python3 hub.py group "Title" --to projects` | Adds a group (paths look like `projects/makuraba`) |
| `python3 hub.py page "Title" --to projects/makuraba` | Adds a page |
| `python3 hub.py link "Title" URL --to library` | Adds a link |
| `python3 hub.py rename PATH "New title"` | Changes a title |
| `python3 hub.py set PATH --summary "..." --status draft` | Changes summary, status, colour or URL (use `none` to clear) |
| `python3 hub.py move PATH --to PATH [--pos N]` | Moves an item |
| `python3 hub.py remove PATH [--yes] [--delete-files]` | Removes an item |
| `python3 hub.py menu-add / menu-rename / menu-move / menu-remove` | Manages the left-hand menu |
| `python3 hub.py reset --yes` | Starts fresh (section 12) |

`python3 hub.py -h` and `python3 hub.py COMMAND -h` list every option. You can also edit `hub.json` directly and run `build`.

## 12. Starting fresh (clearing the demos)

`python3 hub.py reset --yes`

This restores the five empty menu items and moves `hub.json`, `pages/`, `media/` and `examples/` into a new `backup-DATE/` folder. Nothing is deleted; delete the backup folder yourself when you are sure. It is ignored by Git, so it is never published.

## 13. Troubleshooting

| What you see | Why, and what to do |
|---|---|
| The background is a still image or plain | The site was opened as a file. Run `python3 hub.py serve` and use the localhost address |
| The editor says *forbidden* | Open it at `localhost` or `127.0.0.1`, not at a network address |
| *port 8000 is busy* | Use `python3 hub.py serve --port 8001` |
| *missing ... markers* | A marker comment was deleted. Restore `<!-- hub:nav:start -->` and its `:end` partner (and `hub:data`, `page:content`) from the original files |
| *no page, group or URL called [[x]]* | Check the spelling, or use the page's file name or full group path |
| *two pages use the file name ...* | Give one page a different title or use `--file` when adding it |
| A page is not in the menu | It is not in `hub.json`. Add it in Structure, or run `python3 hub.py list` to check |
| Published site shows old content | Run `publish` again, check that Pages deploys from `main`, wait a minute, and hard-refresh |
| A picture does not show | Use jpg, png, gif, webp, svg or avif. Check it appears under `media/` |
| Termux cannot see your Downloads | Run `termux-setup-storage` once, then look in `~/storage/downloads` |

## 14. Safety notes

The editor and its save commands only answer requests from your own device and refuse anything else. Keep your work in Git: every `publish` is a restore point. Before large changes, run `python3 hub.py publish "before changes"`.
