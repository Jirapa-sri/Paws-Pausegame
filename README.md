# Paws & Pause Reel Agent

Generate a **30–60 second** pitch reel for *Paws & Pause* from the project proposal and slide plan.

## Repository layout

```
README.md
requirements.txt
.gitignore
.env.example
project_proposal.md
reel_agent.py
reel_pipeline/              # modular asyncio / PydanticAI pipeline
slides/                     # one HTML file per slide
ai_grading/
  slide_plan.json
  critique_feedback.json
  agent_flow.png
reel.mp4                    # generated locally (gitignored — upload separately)
```

## Pipeline

1. Read `project_proposal.md`
2. Read `ai_grading/slide_plan.json`
3. Generate HTML slides (**parallel**)
4. Critique each slide (**parallel**)
5. Revise each slide (**parallel**)
6. Generate narration with OpenAI TTS `tts-1-hd` (**parallel**)
7. Render HTML → PNG at **1920×1080** via Playwright (**parallel**)
8. Compose `reel.mp4` with FFmpeg
9. Export grading artifacts (`critique_feedback.json`, `agent_flow.png`)

Models:

- LLM: **`gpt-5.6-luna`** (PydanticAI with tools + schemas)
- TTS: **`tts-1-hd`**

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

Install FFmpeg if needed:

```bash
brew install ffmpeg
```

Configure secrets:

```bash
cp .env.example .env
# edit .env → set OPENAI_API_KEY
```

A valid OpenAI key is required for LLM critique/polish and `tts-1-hd`.

## Run

```bash
python reel_agent.py
```

Verbose logs:

```bash
python reel_agent.py -v
```

## Notes

- `reel.mp4` is gitignored — upload it separately for submission.
- Slides use HTML/CSS/inline SVG only (no stock photos / AI images).
- Slide 2 includes a custom town + shelter illustration built entirely with SVG.
- Do not commit `.env` or API keys.
