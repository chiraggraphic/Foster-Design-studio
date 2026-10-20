# Foster AI Studio

Foster Creative Agency's own AI workspace: one dashboard and one API in front of open-source engines that run on **your** machine or server (no per-use fees, no usage caps beyond your hardware).

| Tool | Engine (open source) | Status in this repo |
|---|---|---|
| Image generation | [ComfyUI](https://github.com/Comfy-Org/ComfyUI) | Working adapter (`/api/image`) |
| Voice generation + cloning (600+ languages) | [OmniVoice](https://github.com/k2-fsa/OmniVoice) | Working service (`services/voice`) + adapter |
| Speech-to-text | [VoiceStudio](https://github.com/debpalash/VoiceStudio) backend (OpenAI-compatible) | Adapter (`/api/transcribe`) |
| WhatsApp reports to the boss | [OpenWA](https://github.com/rmyndharis/OpenWA) | Adapter (`/api/whatsapp/report`) |
| Talking-avatar / lip-sync video | [HeyGem](https://github.com/suifeng9203/HeyGem.ai) | Run separately, see `docs/ENGINES.md` (adapter is a later phase) |
| Lead finding | [OpenGTM](https://github.com/debpalash/OpenGTM) | Run separately |
| AI video production | [OpenMontage](https://github.com/calesthio/OpenMontage) | Run separately (agent-driven) |

Read **docs/ENGINES.md** before deploying: it has hardware needs and licence rules.

## Designer toolbox (daily work)

These run locally on the gateway, with no GPU needed (except where noted) and no per-use fees.

| Tab | What it does |
|---|---|
| Pitch deck (PPT) | Upload your designs, add the client, brief and prices, and get an editable PowerPoint with speaker notes: cover, about you, brief and objectives, design idea, colour palette (taken from the logo), each design, mockups, quotation, timeline, next steps. "Quick" mode makes just designs + mockups + next steps. Empty sections are left out. Opens in PowerPoint, Google Slides and Keynote. |
| Mockups | Business card (front and back), framed poster, phone / social post, website in a browser, shop signboard, and a logo presentation board (logo on white, black, brand colour, grey, gradient and at small sizes). Pick one or get a ZIP of the whole set. |
| Resize / export | Batch-resize to Instagram, Story/Reel, Facebook, LinkedIn, YouTube, WhatsApp DP, A4 and visiting-card sizes, or any custom size. Fill (crop) or fit. JPG, PNG or WebP. Many files come back as a ZIP. |
| Remove background | Transparent PNG cut-outs. |
| Image → SVG | Traces logos and sketches into vectors (colour or black and white). Always clean the result in CorelDRAW or Illustrator. |
| Colour palette | Main colours as HEX codes, with the readable text colour and contrast ratio for each. |
| Watermark | Puts your logo on designs at a chosen corner, size and opacity. |
| QR code | Branded QR codes in any colour, high error correction so a logo can sit on top. |
| Images → PDF | Combines proofs or a portfolio into one PDF. |
| Copywriter | Captions, hashtags, design briefs from rough notes, client replies, taglines. Uses a local Ollama model. |
| Quotation PDF | Branded quotation with line items, optional GST, validity date and terms. |
| Print size calc | Pixel size needed for a print size including bleed. |
| AI image / voice / Transcribe / WhatsApp report | The AI engines from the first version. |

Extra setup for the Copywriter: install [Ollama](https://ollama.com) and run `ollama pull llama3.2`. Set `AGENCY_NAME`, `AGENCY_CONTACT` and `CURRENCY` in `.env` for quotations. The first background removal downloads a small model (about 180 MB). The Docker image is large (a few GB) because of the background-removal libraries.

## Quick start

```bash
git clone <your-repo-url> && cd foster-ai-studio
cp .env.example .env          # set FOSTER_API_KEY and the engine URLs
docker compose up -d --build  # dashboard at http://localhost:8000
```

Without Docker: `cd gateway && pip install -r requirements.txt && set -a && . ../.env && uvicorn main:app --port 8000`.

### Start the engines you want

1. **Images:** install ComfyUI, put an SDXL (or any) checkpoint in `models/checkpoints/`, run `python main.py --listen`, and set `COMFY_CHECKPOINT` to that file name.
2. **Voice:** `cd services/voice`, install PyTorch for your GPU, `pip install -r requirements.txt`, then `uvicorn app:app --port 8100`. First start downloads the model.
3. **Transcribe:** install VoiceStudio and keep its backend on port 3900.
4. **WhatsApp:** run OpenWA, scan the QR code, then set `OPENWA_API_KEY`, `OPENWA_SESSION`, `BOSS_WHATSAPP`.

Open the dashboard, enter your `FOSTER_API_KEY`, and use **Status** to see which engines are up. The studio is owner-only: every API call needs that key. Put it behind HTTPS (e.g. Caddy) before exposing it to the internet.

## Layout

```
gateway/        FastAPI gateway + dashboard (static/index.html) + ComfyUI workflow
services/voice/ OmniVoice HTTP wrapper (GPU recommended)
docs/ENGINES.md Engine notes, hardware, licences, roadmap
```

## Roadmap

1. Per-user logins and a job history database (SQLite), plus a client folder so every tool saves into the right client's project.
2. More mockups (T-shirt, mug, packaging, letterhead) and print-ready PDF checks (bleed, CMYK).
3. HeyGem avatar adapter, after verifying its video endpoints against its docs.
4. Image-to-image, upscaling and background removal as extra ComfyUI workflows.
5. Dubbing and audiobook tools via VoiceStudio.
6. Connect Foster Tasks to `/api/whatsapp/report` for daily reports.
