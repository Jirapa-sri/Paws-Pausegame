# Getting Started in Cursor — Paws & Pause

A quick reference for picking this project back up in Cursor.

---

## 1. Open the project

```bash
open -a Cursor "/Users/jirapasriprakrobporn/Desktop/AI Generate /HW2"
```
Or launch Cursor → `File → Open Folder…` → select this `HW2` folder.

This folder is the git repo already pushed to **[github.com/Jirapa-sri/Paws-Pausegame](https://github.com/Jirapa-sri/Paws-Pausegame)** — Cursor's Source Control panel will pick that up automatically.

---

## 2. What's in this folder

| File / folder | What it is |
|---|---|
| **`game_demo.html`** | The whole playable game. One self-contained HTML file — canvas rendering, all game logic, all CSS, all inline. No build step, no dependencies. |
| `breed-cartoons/` | Source puppy artwork. **Not tracked in git** (it's in `.gitignore`) — local only, used to generate the small embedded thumbnails already baked into `game_demo.html`. |
| `slides.html` | The pitch deck (18 slides), also self-contained HTML. |
| `Paws_and_Pause_Proposal.docx`, `..._Narration_Script.docx`, `..._Video_Reel_Plan.docx` | Written deliverables. |
| `reel_agent.py`, `reel_pipeline/` | A **separate** tool — a PydanticAI agent that auto-generates a pitch video from `project_proposal.md`. Different from the game; see §5 if you want to run it. |
| `project_proposal.md`, `ai_grading/` | Inputs/outputs for `reel_agent.py`. |

---

## 3. Run the game (no build step)

It's a static HTML file, so there's nothing to install or compile:

- **Fastest**: Finder → double-click `game_demo.html` → opens in your default browser.
- **From Cursor**: right-click `game_demo.html` in the file explorer → "Reveal in Finder," or use the integrated terminal:
  ```bash
  open game_demo.html
  ```
- **Live-reload while editing** (optional): install the "Live Server" extension in Cursor, then right-click `game_demo.html` → "Open with Live Server." It'll auto-refresh the browser every time you save.

After any edit, just save the file and refresh the browser tab — that's the whole loop.

---

## 4. Finding your way around `game_demo.html`

It's a big single file (2,600+ lines), organized with `/* ---------- Section ---------- */` comments. Search (`Cmd+F` in the file, or `Cmd+Shift+F` project-wide) for these to jump around:

- `Catalogs` — colors, hairstyles, clothing, decor items
- `State` — save data shape, `defaultState()`, load/save
- `Sound Effects` — the Web Audio synth functions
- `Canvas / world` — camera, movement, world constants (`WORLD_W`, `ZONES`, `PATH_NODES`, etc.)
- `Fishing`, `Café: cooking job`, `Go-Kart Stadium`, `Arcade` — each minigame is self-contained in its own section
- `Save controls` / `Init` — bottom of the file, where everything wires together

If you ask Cursor's AI chat (`Cmd+L`) for help, mention the section name or a line number — it makes a big difference in a file this size (e.g. "in the Fishing section of game_demo.html, add...").

---

## 5. (Optional) Running the reel agent

Only needed if you want to regenerate `reel.mp4` from `project_proposal.md`:

```bash
source .venv/bin/activate
python reel_agent.py
```

Requires `OPENAI_API_KEY` set in `.env` (already there locally — never commit it). If you edit `project_proposal.md` or `ai_grading/slide_plan.json`, re-run this to regenerate the slides/audio/video.

---

## 6. Git workflow

Everything here already tracks `origin/main` on GitHub. From Cursor's Source Control tab (or the terminal):

```bash
git add -A
git commit -m "your message"
git push
```

Reminder: `breed-cartoons/`, `.env`, `.venv/`, `reel.mp4`, `audio/`, `renders/`, and `output/` are all gitignored on purpose — don't force-add them.
