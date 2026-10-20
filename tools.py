"""Everyday graphic-designer tools. Pillow, rembg, vtracer, qrcode and reportlab run locally; copywriting uses a local Ollama model."""
import asyncio, datetime, io, os, tempfile, zipfile
from xml.sax.saxutils import escape
import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from PIL import Image, ImageColor, ImageOps

E = os.environ.get
LLM_URL, LLM_MODEL = E("LLM_URL", "http://127.0.0.1:11434"), E("LLM_MODEL", "llama3.2")
AGENCY, CONTACT, CUR = E("AGENCY_NAME", "Foster Creative Agency"), E("AGENCY_CONTACT", ""), E("CURRENCY", "Rs.")
MAX_PX, MAX_FILES = 8000, 30
# rembg's default model changed to a large one with a non-commercial licence; use a small permissive model unless you choose otherwise.
REMBG_MODEL, _SESSION = E("REMBG_MODEL", "isnet-general-use"), None
PRESETS = {
    "instagram-post": (1080, 1080), "instagram-portrait": (1080, 1350), "story-reel": (1080, 1920),
    "facebook-cover": (820, 312), "linkedin-banner": (1584, 396), "youtube-thumbnail": (1280, 720),
    "whatsapp-dp": (640, 640), "a4-300dpi": (2480, 3508), "visiting-card-90x54mm-300dpi": (1063, 638),
}
MIME = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
TASKS = {
    "caption": "Write 3 short, engaging social media captions for the post described below. Add a call to action.",
    "hashtags": "Suggest 15 relevant hashtags (mix of broad and niche) for the post described below. Output only the hashtags.",
    "brief": "Turn the rough notes below into a clear design brief: goal, audience, deliverables with sizes, tone/style, must-include text, open questions to ask the client.",
    "client_reply": "Write a polite, concise reply to the client message below. If it asks for changes, restate them as a short list and give a clear next step.",
    "rewrite": "Rewrite the text below to be clearer and more professional without changing its meaning.",
    "tagline": "Suggest 10 short tagline options for the business described below.",
}

def load(data: bytes) -> Image.Image:
    try:
        im = Image.open(io.BytesIO(data)); im.load()
        return ImageOps.exif_transpose(im)
    except Exception:
        raise HTTPException(400, "That file is not a valid image")

def png(im: Image.Image) -> Response:
    b = io.BytesIO(); im.save(b, "PNG"); return Response(b.getvalue(), media_type="image/png")

def flatten(im: Image.Image) -> Image.Image:
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA"); bg = Image.new("RGB", im.size, (255, 255, 255)); bg.paste(im, mask=im.split()[3]); return bg
    return im.convert("RGB")

def color(c: str):
    try: return ImageColor.getrgb(c)
    except ValueError: raise HTTPException(400, f"Bad colour: {c}")

def lum(rgb):
    c = [(v / 255) / 12.92 if v / 255 <= 0.03928 else ((v / 255 + 0.055) / 1.055) ** 2.4 for v in rgb]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

def ratio(a, b):
    hi, lo = sorted((lum(a), lum(b)), reverse=True); return (hi + 0.05) / (lo + 0.05)

class Item(BaseModel):
    desc: str; qty: float = 1; rate: float

class QuoteReq(BaseModel):
    client: str; items: list[Item]; gst_percent: float = 0; quote_no: str = ""; valid_days: int = 15; notes: str = ""

class WriteReq(BaseModel):
    task: str; text: str; tone: str = "friendly and professional"; language: str = "English"

def palette_of(im, n=6):
    n = max(2, min(n, 12))
    rgba = im.convert("RGBA"); q = None
    if rgba.getchannel("A").getextrema()[0] < 250:  # transparent logo: only count the visible pixels, not the empty background
        rgba.thumbnail((200, 200)); d = rgba.tobytes(); vis = [d[i:i + 3] for i in range(0, len(d), 4) if d[i + 3] > 128]
        if vis: q = Image.frombytes("RGB", (len(vis), 1), b"".join(vis)).quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    if q is None: q = flatten(im).resize((160, 160)).quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette(); cols = sorted(q.getcolors(), reverse=True); total = sum(c for c, _ in cols); kept = []
    for c, i in cols:  # merge near-identical colours so the palette shows distinct swatches
        rgb = tuple(pal[i * 3:i * 3 + 3])
        for k in kept:
            if sum((a - b) ** 2 for a, b in zip(rgb, k[0])) < 30 ** 2: k[1] += c; break
        else: kept.append([rgb, c])
    out = []
    for rgb, c in sorted(kept, key=lambda k: -k[1]):
        w, k = ratio(rgb, (255, 255, 255)), ratio(rgb, (0, 0, 0))
        out.append({"hex": "#%02x%02x%02x" % rgb, "percent": round(100 * c / total, 1),
                    "text_on": "#ffffff" if w >= k else "#000000", "contrast": round(max(w, k), 2)})
    return out

def make_router(auth):
    r = APIRouter(prefix="/api/tools", dependencies=[Depends(auth)])

    @r.post("/resize")
    async def resize(files: list[UploadFile] = File(...), preset: str = Form(""), width: int = Form(0), height: int = Form(0),
                     mode: str = Form("fill"), fmt: str = Form("jpg"), quality: int = Form(88)):
        w, h = PRESETS.get(preset, (width, height)); fmt = fmt.lower()
        if not (0 < w <= MAX_PX and 0 < h <= MAX_PX): raise HTTPException(400, f"Pick a preset or give width and height (max {MAX_PX})")
        if fmt not in MIME: raise HTTPException(400, "Format must be jpg, png or webp")
        if len(files) > MAX_FILES: raise HTTPException(400, f"Max {MAX_FILES} files at a time")
        out = []
        for f in files:
            im = load(await f.read())
            im = flatten(im) if fmt == "jpg" else im.convert("RGBA")
            im = ImageOps.fit(im, (w, h), Image.LANCZOS) if mode == "fill" else ImageOps.contain(im, (w, h), Image.LANCZOS)
            b = io.BytesIO()
            im.save(b, {"jpg": "JPEG", "png": "PNG", "webp": "WEBP"}[fmt], **({"quality": max(1, min(quality, 100))} if fmt != "png" else {}), optimize=True)
            stem = os.path.splitext(os.path.basename(f.filename or "image"))[0]
            out.append((f"{stem}-{w}x{h}.{fmt}", b.getvalue()))
        if len(out) == 1: return Response(out[0][1], media_type=MIME[fmt])
        z = io.BytesIO()
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            for n, d in out: zf.writestr(n, d)
        return Response(z.getvalue(), media_type="application/zip")

    @r.post("/cutout")
    async def cutout(file: UploadFile = File(...)):
        try: from rembg import new_session, remove
        except ImportError: raise HTTPException(501, "rembg is not installed")
        global _SESSION
        if _SESSION is None: _SESSION = await asyncio.to_thread(new_session, REMBG_MODEL)
        im = load(await file.read())
        im.thumbnail((3000, 3000))
        return png(await asyncio.to_thread(remove, im, session=_SESSION))

    @r.post("/palette")
    async def palette(file: UploadFile = File(...), n: int = Form(6)):
        return {"colors": palette_of(load(await file.read()), n)}

    @r.post("/vectorize")
    async def vectorize(file: UploadFile = File(...), mode: str = Form("color")):
        import vtracer
        im = flatten(load(await file.read())); im.thumbnail((2000, 2000))
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, "in.png"), os.path.join(d, "out.svg"); im.save(a)
            await asyncio.to_thread(vtracer.convert_image_to_svg_py, a, b, colormode="binary" if mode == "binary" else "color")
            return Response(open(b, "rb").read(), media_type="image/svg+xml")

    @r.post("/watermark")
    async def watermark(file: UploadFile = File(...), logo: UploadFile = File(...), position: str = Form("br"),
                        scale: float = Form(0.2), opacity: float = Form(0.7), margin: float = Form(3)):
        base, lg = load(await file.read()).convert("RGBA"), load(await logo.read()).convert("RGBA")
        lw = max(1, int(base.width * max(0.02, min(scale, 1)))); lg = lg.resize((lw, max(1, int(lg.height * lw / lg.width))), Image.LANCZOS)
        lg.putalpha(lg.split()[3].point(lambda p: int(p * max(0, min(opacity, 1)))))
        m = int(base.width * max(0, min(margin, 20)) / 100)
        x = {"l": m, "r": base.width - lg.width - m}.get(position[-1], (base.width - lg.width) // 2)
        y = {"t": m, "b": base.height - lg.height - m}.get(position[0], (base.height - lg.height) // 2)
        base.alpha_composite(lg, (max(0, x), max(0, y)))
        return png(base)

    @r.post("/qr")
    async def qr(text: str = Form(...), fg: str = Form("#000000"), bg: str = Form("#ffffff"), size: int = Form(1024)):
        import qrcode
        if not text or len(text) > 2000: raise HTTPException(400, "Text must be 1-2000 characters")
        q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, border=2, box_size=10); q.add_data(text); q.make(fit=True)
        im = q.make_image(fill_color=color(fg), back_color=color(bg)).convert("RGB")
        s = max(128, min(size, 4000)); return png(im.resize((s, s), Image.NEAREST))

    @r.post("/to-pdf")
    async def to_pdf(files: list[UploadFile] = File(...)):
        if len(files) > 40: raise HTTPException(400, "Max 40 images")
        pages = [flatten(load(await f.read())) for f in files]; b = io.BytesIO()
        pages[0].save(b, "PDF", save_all=True, append_images=pages[1:], resolution=150)
        return Response(b.getvalue(), media_type="application/pdf")

    @r.post("/write")
    async def write(q: WriteReq):
        if q.task not in TASKS: raise HTTPException(400, f"task must be one of {list(TASKS)}")
        prompt = (f"You are a copywriter at {AGENCY}, a graphic design agency. {TASKS[q.task]}\n"
                  f"Tone: {q.tone[:80]}. Write in: {q.language[:40]}.\n\nInput:\n{q.text[:4000]}")
        try:
            async with httpx.AsyncClient(timeout=300) as c:
                res = await c.post(f"{LLM_URL}/api/generate", json={"model": LLM_MODEL, "prompt": prompt, "stream": False})
            return {"text": res.json()["response"].strip()}
        except Exception:
            raise HTTPException(502, f"Local LLM not reachable. Install Ollama and run: ollama pull {LLM_MODEL}")

    @r.post("/quote")
    async def quote(q: QuoteReq):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        if not q.items or len(q.items) > 50: raise HTTPException(400, "Give 1-50 line items")
        st, today = getSampleStyleSheet(), datetime.date.today()
        P = lambda t, s="Normal": Paragraph(escape(t[:300]), st[s])
        sub = sum(i.qty * i.rate for i in q.items); gst = sub * q.gst_percent / 100
        m = lambda v: f"{CUR} {v:,.2f}"
        rows = [["Description", "Qty", "Rate", "Amount"]] + [[P(i.desc), f"{i.qty:g}", m(i.rate), m(i.qty * i.rate)] for i in q.items]
        rows.append(["", "", "Subtotal", m(sub)])
        if gst: rows.append(["", "", f"GST ({q.gst_percent:g}%)", m(gst)])
        rows.append(["", "", "Total", m(sub + gst)])
        t = Table(rows, colWidths=[78 * mm, 18 * mm, 30 * mm, 33 * mm], repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f26b21")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                               ("ALIGN", (1, 0), (-1, -1), "RIGHT"), ("GRID", (0, 0), (-1, len(q.items)), 0.4, colors.grey),
                               ("FONTNAME", (2, -1), (-1, -1), "Helvetica-Bold"), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story = [P(AGENCY, "Title"), P(CONTACT), Spacer(1, 6 * mm), P("QUOTATION", "Heading2"),
                 P(f"Quote no: {q.quote_no or '-'}  |  Date: {today:%d %b %Y}  |  Valid until: {today + datetime.timedelta(days=q.valid_days):%d %b %Y}"),
                 P(f"For: {q.client}"), Spacer(1, 6 * mm), t]
        if q.notes: story += [Spacer(1, 6 * mm), P("Notes / terms", "Heading4"), P(q.notes)]
        b = io.BytesIO(); SimpleDocTemplate(b, pagesize=A4, title=f"Quotation {q.quote_no}").build(story)
        return Response(b.getvalue(), media_type="application/pdf")

    @r.post("/mockup")
    async def mockup(file: UploadFile = File(...), back: UploadFile | None = File(None), kind: str = Form("business-card"),
                     mode: str = Form("art"), bg: str = Form(""), brand: str = Form("")):
        """kind: one mockup, or 'all' for a ZIP of the set that suits the design. mode 'logo' = logo on transparent PNG, 'art' = full artwork."""
        import mockups
        if kind != "all" and kind not in mockups.KINDS: raise HTTPException(400, f"kind must be one of {mockups.KINDS + ['all']}")
        if mode not in ("art", "logo"): raise HTTPException(400, "mode must be art or logo")
        for c in (bg, brand):
            if c: color(c)
        d = load(await file.read()); b = load(await back.read()) if back is not None and back.filename else None
        if kind != "all":
            return png(await asyncio.to_thread(mockups.render, kind, d, b, bg, brand, mode))
        z = io.BytesIO()
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            for k in mockups.ALL[mode]:
                o = io.BytesIO(); (await asyncio.to_thread(mockups.render, k, d, b, bg, brand, mode)).save(o, "PNG"); zf.writestr(f"{k}.png", o.getvalue())
        return Response(z.getvalue(), media_type="application/zip")
    return r
