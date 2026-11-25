import base64
import hashlib
from contextlib import asynccontextmanager
from io import BytesIO

import qrcode
import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from crypto_utils import decrypt_packet, encrypt_payment, extract_packet, load_keys
from database import get_accounts, init_db, settle_payment


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Offline UPI Mesh", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

private_key, public_key = load_keys()


def make_qr_png_data_url(data: str) -> str:
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    buf = BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/sender", response_class=HTMLResponse)
async def sender_page(request: Request):
    accounts = await get_accounts()
    return templates.TemplateResponse(request, "sender.html", {"accounts": accounts})


@app.post("/create")
async def create_payment(sender: str = Form(...), receiver: str = Form(...), amount: float = Form(...)):
    packet = encrypt_payment(public_key, sender, receiver, amount)
    return JSONResponse({
        "status": "created",
        "packet": packet,
        "packet_json": packet,
        "qr_data": packet,
        "qr_png": make_qr_png_data_url(packet),
    })


@app.post("/upload")
async def upload_packet(request: Request):
    body = await request.json()
    raw = body.get("packet")
    if isinstance(raw, dict):           # tolerate {"packet": {"packet": "UM1:..."}}
        raw = raw.get("packet")
    if not raw or not isinstance(raw, str):
        return JSONResponse({"status": "INVALID", "message": "No packet received"}, status_code=400)

    try:
        packet = extract_packet(raw)
        payment = decrypt_packet(private_key, packet)
    except Exception as e:
        return JSONResponse({"status": "INVALID", "message": f"Could not read packet: {e}"})

    packet_hash = hashlib.sha256(packet.encode()).hexdigest()
    result = await settle_payment(packet_hash, payment["sender"], payment["receiver"], payment["amount"])
    return JSONResponse(result)


@app.get("/accounts")
async def accounts():
    return await get_accounts()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
