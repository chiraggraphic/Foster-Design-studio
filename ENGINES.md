# Engines, hardware and licences

Research date: 19 Oct 2026, from each project's README and LICENSE file. Re-check before commercial use; projects change.

| Engine | Licence | What it means for Foster |
|---|---|---|
| ComfyUI | GPL-3.0 | Fine to run and use for client work. Run it as a separate service (as here). If you ship a modified copy, you must share your changes under GPL. |
| OmniVoice | Apache-2.0 | Permissive. Keep the licence notice if you redistribute. |
| VoiceStudio | AGPL-3.0 | Run unmodified as a separate service. If you modify it and let others use it over a network, you must publish your changes. |
| OpenGTM | AGPL-3.0 | Same as above. Needs Docker and about 4 GB RAM. |
| OpenMontage | AGPL-3.0 | Same as above. Agent-driven: you use it from Claude Code or similar. |
| OpenWA | MIT | Permissive. **Unofficial WhatsApp client: the number can be restricted or banned.** Use a dedicated number, message only people who expect it (like the boss's report), never bulk-message strangers. |
| Handy | MIT | Offline desktop dictation app. Not an API, so it is not wired in; use VoiceStudio's backend for server use. |
| HeyGem | Custom community licence | Requires a "Built with Silicon Intelligence" credit and a licence notice. **If your product has more than 1,000 monthly active users you must request a licence.** Fine for the agency's own use. Needs a GPU (about 8 GB VRAM) and about 100 GB disk. |
| onetake | PolyForm Noncommercial | **Not allowed for paid client work** without the author's commercial version. Not used in this repo. |

Skills I deliberately did not build into the studio: the penetration-testing agent (needs written authorization for every target and is unrelated to the agency's tools), and the app/website cloning skills (copying someone else's site or code can infringe their copyright; use them for learning and build original work).

## Hardware guide

- Images (SDXL): NVIDIA GPU with 8 GB VRAM or more is comfortable. CPU-only is too slow to be useful.
- Voice (OmniVoice): GPU recommended; CPU works but slowly.
- Transcription: runs on CPU, faster on GPU.
- No GPU at home? Rent one by the hour from a cloud GPU provider and point the `*_URL` values at it, keeping the same gateway.

## Voice cloning rules for Foster

Only clone a voice with the speaker's written consent, and say so to clients when audio is synthetic. Do not use cloned voices to imitate public figures or to make people appear to say things they did not.

## Adding the HeyGem avatar adapter

HeyGem exposes local services after `docker-compose up -d` in its `deploy/` folder. Its README documents voice training and synthesis on port 18180 (`/v1/preprocess_and_tran`, `/v1/invoke`); the video-synthesis endpoint is implemented in its `src/main/service/video.js`. Read that file, copy the request format, and add a `/api/avatar` route in `gateway/main.py` following the pattern of `/api/voice`.

## Designer-toolbox libraries

| Library | Licence | Note |
|---|---|---|
| Pillow, qrcode, reportlab | HPND / BSD / BSD | Fine for client work. |
| vtracer | MIT | Auto-tracing is a starting point; clean up by hand. |
| rembg | MIT | The library is MIT, but each **model** has its own licence. The newest rembg default (BRIA RMBG-2.0, about 1 GB) is, as far as I know, non-commercial, so this repo uses `isnet-general-use` instead. Check a model's licence before you set `REMBG_MODEL` to something else. |
| Ollama + llama3.2 | Ollama MIT; Llama licence | Meta's Llama licence allows commercial use with conditions. Read it, or choose another model. Always proofread generated copy. |

Reminder: a QR code, quotation or watermark made here is a normal file you own. Check any client logo or font you process for its own usage rights.
| python-pptx | MIT | Builds the pitch decks. The decks use Cambria and Calibri, which ship with Office. |

## Mockups and pitch decks: what to know

- Mockups are drawn by the app itself (no stock photos or templates), so there are no licence problems and the files are yours. They are clean and stylised, not photo-real. For a photo-real product shot, use the AI image engine or a mockup PSD you have the licence for.
- Logo mode works best with a logo on a transparent PNG. A logo on plain white is cut out automatically, but fine edges can look slightly rough.
- The pitch deck is a starting point to edit in PowerPoint. Text that is too long for a slide is trimmed with "…", so keep each field short.
- If you switch on the AI writer for objectives and rationale, read and correct the text before it goes to a client. A small local model can get facts wrong.
- Mockup slides are labelled as illustrative previews in the speaker notes. Say so to the client.
