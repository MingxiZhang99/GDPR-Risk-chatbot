from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
from pypdf import PdfReader
import io
import json

from vectorstore import ingest, search
from llm import chat, risk_analysis
from seed import load_seed_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        load_seed_data()
    except Exception as e:
        print(f"[seed] Skipped: {e}")
    yield


from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title="GDPR RAG System", lifespan=lifespan)


# --- Request Models ---

class TextInput(BaseModel):
    text: str
    source: str = "manual_input"
    metadata: dict | None = None


class ChatInput(BaseModel):
    question: str
    metadata_filter: dict | None = None
    history: list[dict] | None = None  # [{"role": "user", "content": "..."}, ...]
    language: str | None = None  # preferred response language


class RiskInput(BaseModel):
    project_description: str


@app.get("/")
def serve_ui():
    return FileResponse("static/index.html")


# --- Endpoints ---

@app.post("/text")
def upload_text(body: TextInput):
    result = ingest(body.text, source=body.source, metadata=body.metadata)
    return result


@app.post("/document")
async def upload_document(
    file: UploadFile = File(...),
    metadata: str = Form(default="{}"),
):
    content = await file.read()
    meta = json.loads(metadata)

    if file.filename.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        text = content.decode("utf-8")

    result = ingest(text, source=file.filename, metadata=meta)
    return result


@app.get("/search")
def semantic_search(q: str, top_k: int = 5, topic: str | None = None, type: str | None = None):
    metadata_filter = {}
    if topic:
        metadata_filter["topic"] = topic
    if type:
        metadata_filter["type"] = type
    results = search(q, top_k=top_k, metadata_filter=metadata_filter or None)
    return {"results": results}


@app.post("/chat")
def chat_endpoint(body: ChatInput):
    return chat(body.question, metadata_filter=body.metadata_filter, history=body.history, language=body.language)


@app.post("/risk")
def risk_endpoint(body: RiskInput):
    return risk_analysis(body.project_description)
