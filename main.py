from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import logging

from verification_pipeline import verification

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="VeritasAI",
    description="AI-powered news fact-checking and trust analysis",
    version="1.1.0",
)

app.mount("/static", StaticFiles(directory="frontend"), name="static")

vc = verification()


class CheckInput(BaseModel):
    input: str


class VerifyInput(BaseModel):
    claims: list[str]


@app.get("/")
async def serve_frontend():
    return FileResponse("frontend/index.html")


@app.post("/api/check")
async def classify_input(body: CheckInput):
    return vc.input_handler(body.input)


@app.post("/api/verify")
async def verify_claims_batch(body: VerifyInput):
    return vc.verify_claims_batch(body.claims)