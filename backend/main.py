from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
import os
import fitz  # PyMuPDF

app = FastAPI(title="Portfolio Q&A API")

# Allow Streamlit frontend (and any origin) to call this API.
# You can lock this down to your Streamlit URL in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini once at startup using the env var you set in Render.
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

# ---------------------------------------------------------------------------
# Document loading
# ---------------------------------------------------------------------------
DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")
document_context: str = ""


def load_pdf(path: str) -> str:
    """Extract plain text from every page of a PDF using PyMuPDF."""
    doc = fitz.open(path)
    return "\n".join(page.get_text() for page in doc)


def load_documents() -> None:
    """
    Walk the docs/ directory at startup and build a single string that
    concatenates every supported document.  Each file is labelled so
    Gemini can tell your resume from your research paper.
    """
    global document_context
    texts: list[str] = []

    if not os.path.exists(DOCS_DIR):
        print(f"[WARNING] docs/ directory not found at {DOCS_DIR}")
        return

    for filename in sorted(os.listdir(DOCS_DIR)):
        filepath = os.path.join(DOCS_DIR, filename)
        if filename.endswith(".pdf"):
            content = load_pdf(filepath)
            texts.append(f"=== {filename} ===\n{content}")
            print(f"[INFO] Loaded PDF: {filename} ({len(content)} chars)")
        elif filename.endswith(".txt"):
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
            texts.append(f"=== {filename} ===\n{content}")
            print(f"[INFO] Loaded TXT: {filename} ({len(content)} chars)")

    document_context = "\n\n".join(texts)
    print(f"[INFO] Total context size: {len(document_context)} characters")


# Run once when Render (or uvicorn) starts the process.
load_documents()

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class Question(BaseModel):
    question: str


class Answer(BaseModel):
    answer: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    """
    Render uses this to confirm the service is alive.
    Also handy for debugging — tells you whether documents were loaded.
    """
    return {
        "status": "ok",
        "docs_loaded": bool(document_context),
        "context_chars": len(document_context),
    }


@app.post("/ask", response_model=Answer)
def ask(payload: Question) -> Answer:
    """
    Core endpoint.  Receives a question, injects the full document context
    into a Gemini prompt, and returns the model's answer.
    """
    if not document_context:
        raise HTTPException(
            status_code=503,
            detail="No documents loaded. Add PDFs or TXT files to backend/docs/ and redeploy.",
        )

    prompt = f"""You are an AI assistant for a personal portfolio website.
Your job is to answer questions about the portfolio owner based ONLY on the
documents provided below. Be concise, friendly, and professional.
If the answer cannot be found in the documents, say so clearly —
do NOT invent or assume information.

--- DOCUMENTS START ---
{document_context}
--- DOCUMENTS END ---

QUESTION: {payload.question}

ANSWER:"""

    response = model.generate_content(prompt)
    return Answer(answer=response.text)