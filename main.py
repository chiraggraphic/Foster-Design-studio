"""Foster AI Studio gateway: one API + dashboard in front of local open-source AI engines."""
import os, json, random, asyncio, pathlib
import httpx
from fastapi import FastAPI, Depends, HTTPException, Header, UploadFile, File, Form
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

E = os.environ.get
COMFY, VOICE, STT = E("COMFYUI_URL", "http://127.0.0.1:8188"), E("VOICE_URL", "http://127.0.0.1:8100"), E("STT_URL", "http://127.0.0.1:3900")
WA, WA_KEY, WA_SESSION, BOSS = E("OPENWA_URL", "http://127.0.0.1:2785"), E("OPENWA_API_KEY", ""), E("OPENWA_SESSION", ""), E("BOSS_WHATSAPP", "")
CKPT, API_KEY = E("COMFY_CHECKPOINT", "sd_xl_base_1.0.safetensors"), E("FOSTER_API_KEY", "")
HERE = pathlib.Path(__file__).parent
if not API_KEY:
    raise SystemExit("Set FOSTER_API_KEY in .env (the studio is owner-only).")

def auth(authorization: str = Header(default="")):
    if authorization != f"Bearer {API_KEY}":
        raise HTTPException(401, "Invalid or missing key")

app = FastAPI(title="Foster AI Studio")
from tools import make_router
app.include_router(make_router(auth))
from pitch import make_router as pitch_router
app.include_router(pitch_router(auth))
http = httpx.AsyncClient(timeout=600)

class ImageReq(BaseModel):
    prompt: str
    negative: str = "blurry, low quality, watermark, text artifacts"
    width: int = 1024
    height: int = 1024
    steps: int = 25

@app.post("/api/image", dependencies=[Depends(auth)])
async def image(r: ImageReq):
    wf = json.loads((HERE / "workflows/txt2img.json").read_text())
    wf["3"]["inputs"].update(seed=random.randint(0, 2**32), steps=r.steps)
    wf["4"]["inputs"]["ckpt_name"] = CKPT
    wf["5"]["inputs"].update(width=r.width, height=r.height)
    wf["6"]["inputs"]["text"], wf["7"]["inputs"]["text"] = r.prompt, r.negative
    try:
        pid = (await http.post(f"{COMFY}/prompt", json={"prompt": wf})).json()["prompt_id"]
    except Exception as e:
        raise HTTPException(502, f"ComfyUI not reachable or rejected workflow: {e}")
    for _ in range(300):  # up to ~10 min
        hist = (await http.get(f"{COMFY}/history/{pid}")).json()
        if pid in hist and hist[pid].get("outputs"):
            img = hist[pid]["outputs"]["9"]["images"][0]
            png = await http.get(f"{COMFY}/view", params=img)
            return Response(png.content, media_type="image/png")
        await asyncio.sleep(2)
    raise HTTPException(504, "Image generation timed out")

@app.post("/api/voice", dependencies=[Depends(auth)])
async def voice(text: str = Form(...), ref_text: str = Form(""), ref_audio: UploadFile | None = File(None)):
    """Text to speech. With ref_audio (+ ref_text) it clones that voice. Only clone voices you have consent for."""
    files = {"ref_audio": (ref_audio.filename, await ref_audio.read())} if ref_audio else None
    r = await http.post(f"{VOICE}/tts", data={"text": text, "ref_text": ref_text}, files=files)
    if r.status_code != 200:
        raise HTTPException(502, r.text)
    return Response(r.content, media_type="audio/wav")

@app.post("/api/transcribe", dependencies=[Depends(auth)])
async def transcribe(file: UploadFile = File(...)):
    r = await http.post(f"{STT}/v1/audio/transcriptions", files={"file": (file.filename, await file.read())})
    return r.json()

class Report(BaseModel):
    text: str

@app.post("/api/whatsapp/report", dependencies=[Depends(auth)])
async def whatsapp_report(r: Report):
    """Send a text report to the boss over OpenWA (opted-in recipient only, never bulk/cold messages)."""
    if not (WA_SESSION and BOSS):
        raise HTTPException(400, "Set OPENWA_SESSION and BOSS_WHATSAPP in .env")
    chat = BOSS if "@" in BOSS else f"{BOSS}@c.us"
    res = await http.post(f"{WA}/api/sessions/{WA_SESSION}/messages/send-text",
                          headers={"X-API-Key": WA_KEY}, json={"chatId": chat, "text": r.text})
    return {"status": res.status_code, "body": res.text[:300]}

@app.get("/api/status", dependencies=[Depends(auth)])
async def status():
    async def ping(name, url):
        try:
            await http.get(url, timeout=3); return name, "up"
        except Exception:
            return name, "down"
    res = await asyncio.gather(ping("image (ComfyUI)", COMFY + "/system_stats"), ping("voice", VOICE + "/health"),
                               ping("speech-to-text", STT + "/.well-known/voicestudio-speech"), ping("whatsapp (OpenWA)", WA))
    return dict(res)

@app.get("/")
async def index():
    return FileResponse(HERE / "static/index.html")
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
