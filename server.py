"""
Saudi Building Code MCP Server
Using FastAPI for HTTP transport
"""

import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
from openai import OpenAI
import chromadb
import PyPDF2
from pathlib import Path

# Initialize FastAPI
app = FastAPI(title="Saudi Building Code MCP Server")

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Global variables
collection = None

def get_embedding(text: str) -> list:
    """Get embedding from OpenAI"""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def initialize_rag():
    """Initialize the RAG system"""
    global collection
    
    print("🔄 Initializing RAG system...")
    
    chroma_client = chromadb.Client()
    collection = chroma_client.get_or_create_collection(
        name="saudi_building_code"
    )
    print(f"✅ Vector store ready with {collection.count()} documents")
    
    if collection.count() == 0:
        load_pdf()

def load_pdf():
    """Load and chunk the PDF"""
    global collection
    
    possible_paths = [
        Path("./Full SBC staircase.pdf"),
        Path("/app/Full SBC staircase.pdf"),
    ]
    
    pdf_path = None
    for path in possible_paths:
        if path.exists():
            pdf_path = path
            break
    
    if pdf_path is None:
        print("⚠️ PDF not found!")
        return
    
    print(f"📄 Loading PDF: {pdf_path}")
    
    text = ""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    print(f"📝 Created {len(chunks)} chunks")
    
    for i, chunk in enumerate(chunks):
        try:
            embedding = get_embedding(chunk)
            collection.add(
                ids=[f"chunk_{i}"],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{"source": "SBC", "chunk_id": i}]
            )
        except Exception as e:
            print(f"⚠️ Error embedding chunk {i}: {e}")
    
    print(f"✅ Loaded {collection.count()} chunks")

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap
    return chunks

def search_similar(query: str, k: int = 3) -> list:
    global collection
    
    if collection is None or collection.count() == 0:
        initialize_rag()
    
    if collection.count() == 0:
        return []
    
    query_embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k
    )
    
    return results['documents'][0] if results['documents'] else []

# MCP-style endpoints
@app.get("/")
async def root():
    return {"status": "ok", "service": "Saudi Building Code MCP Server"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/mcp")
async def mcp_info():
    return {
        "name": "Saudi Building Code Assistant",
        "version": "1.0.0",
        "tools": [
            {
                "name": "query_building_code",
                "description": "Query the Saudi Building Code for staircase requirements",
                "parameters": {
                    "question": {"type": "string", "description": "Your question"}
                }
            },
            {
                "name": "check_compliance",
                "description": "Check if dimensions comply with code",
                "parameters": {
                    "stair_width": {"type": "number"},
                    "riser_height": {"type": "number"},
                    "tread_depth": {"type": "number"},
                    "headroom": {"type": "number"}
                }
            }
        ]
    }

@app.post("/mcp/tools/query_building_code")
async def query_building_code(request: Request):
    data = await request.json()
    question = data.get("question", "")
    
    relevant_docs = search_similar(question, k=3)
    
    if not relevant_docs:
        return {"result": "No relevant information found."}
    
    context = "\n\n---\n\n".join(relevant_docs)
    
    return {
        "result": f"## Saudi Building Code\n\n**Question:** {question}\n\n### Retrieved:\n\n{context}"
    }

@app.post("/mcp/tools/check_compliance")
async def check_compliance(request: Request):
    data = await request.json()
    
    results = []
    all_compliant = True
    
    stair_width = data.get("stair_width")
    riser_height = data.get("riser_height")
    tread_depth = data.get("tread_depth")
    headroom = data.get("headroom")
    
    if stair_width is not None:
        if stair_width >= 1100:
            results.append(f"✅ Stair width ({stair_width}mm): COMPLIANT")
        else:
            results.append(f"❌ Stair width ({stair_width}mm): NON-COMPLIANT (min 1100mm)")
            all_compliant = False
    
    if riser_height is not None:
        if 150 <= riser_height <= 180:
            results.append(f"✅ Riser height ({riser_height}mm): COMPLIANT")
        else:
            results.append(f"❌ Riser height ({riser_height}mm): NON-COMPLIANT (150-180mm)")
            all_compliant = False
    
    if tread_depth is not None:
        if tread_depth >= 280:
            results.append(f"✅ Tread depth ({tread_depth}mm): COMPLIANT")
        else:
            results.append(f"❌ Tread depth ({tread_depth}mm): NON-COMPLIANT (min 280mm)")
            all_compliant = False
    
    if headroom is not None:
        if headroom >= 2100:
            results.append(f"✅ Headroom ({headroom}mm): COMPLIANT")
        else:
            results.append(f"❌ Headroom ({headroom}mm): NON-COMPLIANT (min 2100mm)")
            all_compliant = False
    
    status = "✅ ALL COMPLIANT" if all_compliant else "⚠️ NON-COMPLIANT"
    
    return {"result": f"## Compliance Check\n\n**Status:** {status}\n\n" + "\n".join(results)}

# Initialize on startup
@app.on_event("startup")
async def startup_event():
    print("🚀 Starting Saudi Building Code Server...")
    initialize_rag()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🌐 Running on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
```

---

## Also update `requirements.txt`:
```
fastapi>=0.104.0
uvicorn>=0.24.0
openai>=1.0.0
chromadb>=0.4.0
PyPDF2>=3.0.0
python-dotenv>=1.0.0
