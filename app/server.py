import logging
from fastapi import FastAPI, Request, Response
from app.config import load_config
from app.logging import setup_logging


app = FastAPI()


@app.on_event("startup")
def on_startup() -> None:
    cfg = load_config()
    setup_logging(cfg.log_dir)
    logging.getLogger(__name__).info("Server starting up")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request) -> Response:
    body = await request.body()
    logging.getLogger(__name__).info("Webhook received %s bytes", len(body))
    return Response(content="OK", media_type="text/plain")


