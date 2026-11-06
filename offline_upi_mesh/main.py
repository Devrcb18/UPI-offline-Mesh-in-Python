from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import hashlib
import json
import uvicorn

from crypto_utils import load_keys, encrypt_payment, decrypt_packet
from database import init_db, get_accounts, settle_payment

app = FastAPI(title="Offline UPI Mesh - Simple Demo")
templates = Jinja2Templates(directory="templates")

private_key, public_key = load_keys()

@app.on_event("startup")
async def startup():
    await init_db()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    accounts = await get_accounts()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "accounts": accounts
    })

@app.post("/create")
async def create_payment(sender: str = Form(...), receiver: str = Form(...), amount: float = Form(...)):
    packet = encrypt_payment(public_key, sender, receiver, amount)
    return JSONResponse({
        "status": "created",
        "packet": packet,
        "packet_json": json.dumps(packet, indent=2)
    })

@app.post("/upload")
async def upload_packet(request: Request):
    body = await request.json()
    packet = body.get("packet")
    if not packet:
        return JSONResponse({"status": "error", "message": "No packet"}, status_code=400)

    packet_str = json.dumps(packet, sort_keys=True)
    packet_hash = hashlib.sha256(packet_str.encode()).hexdigest()

    try:
        payment = decrypt_packet(private_key, packet)
    except Exception as e:
        return JSONResponse({"status": "INVALID", "message": f"Decryption failed / Tampered: {str(e)}"})

    result = await settle_payment(
        packet_hash,
        payment["sender"],
        payment["receiver"],
        payment["amount"]
    )
    return JSONResponse(result)

@app.get("/accounts")
async def accounts():
    return await get_accounts()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)