"""Thin HTTP wrapper around k2-fsa/OmniVoice (Apache-2.0): TTS, and cloning from a short reference clip."""
import io, os, tempfile
import torch, soundfile as sf
from fastapi import FastAPI, Form, File, UploadFile
from fastapi.responses import Response
from omnivoice import OmniVoice

DEVICE = os.environ.get("DEVICE", "cuda:0")  # "mps" on Apple Silicon, "cpu" works but is slow
model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map=DEVICE, dtype=torch.float16 if DEVICE != "cpu" else torch.float32)
app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/tts")
async def tts(text: str = Form(...), ref_text: str = Form(""), ref_audio: UploadFile | None = File(None)):
    kw = {}
    if ref_audio:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(await ref_audio.read())
        kw = dict(ref_audio=f.name, ref_text=ref_text)
    audio = model.generate(text=text, **kw)[0]  # numpy array, 24 kHz
    buf = io.BytesIO()
    sf.write(buf, audio, 24000, format="WAV")
    return Response(buf.getvalue(), media_type="audio/wav")
