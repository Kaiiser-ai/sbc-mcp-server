"""
Saudi Building Code MCP Server
RAG-based building code assistant using MCP protocol
"""

import os
import json
from mcp.server.fastmcp import FastMCP
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import PyPDF2
from pathlib import Path

# Initialize MCP server
mcp = FastMCP("Saudi Building Code Assistant")

# Global variables
vectorstore = None
embedding_model = None
collection = None

def initialize_rag():
    """Initialize the RAG system with embeddings and vector store"""
    global vectorstore, embedding_model, collection
    
    print("🔄 Initializing RAG system...")
    
    # Load embedding model
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    print("✅ Embedding model loaded")
    
    # Initialize ChromaDB
    vectorstore = chromadb.Client(Settings(
        chroma_db_impl="duckdb+parquet",
        persist_directory="./chroma_db",
        anonymized_telemetry=False
    ))
    
    # Get or create collection
    collection = vectorstore.get_or_create_collection(
        name="saudi_building_code",
        metadata={"description": "Saudi Building Code - Staircase Requirements"}
    )
    print(f"✅ Vector store ready with {collection.count()} documents")
    
    # If empty, load the PDF
    if collection.count() == 0:
        load_pdf()

def load_pdf():
    """Load and chunk the Saudi Building Code PDF"""
    global collection, embedding_model
    
    pdf_path = Path("./data/sbc_staircase.pdf")
    
    if not pdf_path.exists():
        print("⚠️ PDF not found at ./data/sbc_staircase.pdf")
        return
    
    print(f"📄 Loading PDF: {pdf_path}")
    
    # Extract text from PDF
    text = ""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    
    # Chunk the text
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    print(f"📝 Created {len(chunks)} chunks")
    
    # Create embeddings and store
    for i, chunk in enumerate(chunks):
        embedding = embedding_model.encode(chunk).tolist()
        collection.add(
            ids=[f"chunk_{i}"],
            embeddings=[embedding],
            documents=[chunk],
            metadatas=[{"source": "SBC_Staircase", "chunk_id": i}]
        )
    
    print(f"✅ Loaded {len(chunks)} chunks into vector store")

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list:
    """Split text into overlapping chunks"""
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
    """Search for similar documents in the vector store"""
    global collection, embedding_model
    
    if collection is None or embedding_model is None:
        initialize_rag()
    
    # Create query embedding
    query_embedding = embedding_model.encode(query).tolist()
    
    # Search
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k
    )
    
    return results['documents'][0] if results['documents'] else []

@mcp.tool()
def query_building_code(question: str) -> str:
    """
    Query the Saudi Building Code for staircase requirements.
    
    Args:
        question: Your question about building code requirements (e.g., "What is the minimum stair width?")
    
    Returns:
        Relevant building code information with citations
    """
    # Search for relevant chunks
    relevant_docs = search_similar(question, k=3)
    
    if not relevant_docs:
        return "No relevant information found in the Saudi Building Code database."
    
    # Format response
    context = "\n\n---\n\n".join(relevant_docs)
    
    response = f"""## Saudi Building Code - Relevant Sections

Based on your question: "{question}"

### Retrieved Information:

{context}

---
*Source: Saudi Building Code (SBC) - Staircase Requirements*
"""
    
    return response

@mcp.tool()
def check_compliance(
    stair_width: float = None,
    riser_height: float = None,
    tread_depth: float = None,
    headroom: float = None
) -> str:
    """
    Check if staircase dimensions comply with Saudi Building Code.
    
    Args:
        stair_width: Width of staircase in mm (minimum usually 1100mm)
        riser_height: Height of each step in mm (typically 150-180mm)
        tread_depth: Depth of each step in mm (typically 280-300mm)
        headroom: Vertical clearance in mm (minimum usually 2100mm)
    
    Returns:
        Compliance status and recommendations
    """
    results = []
    all_compliant = True
    
    # SBC typical requirements (adjust based on actual code)
    if stair_width is not None:
        if stair_width >= 1100:
            results.append(f"✅ Stair width ({stair_width}mm): COMPLIANT (min 1100mm)")
        else:
            results.append(f"❌ Stair width ({stair_width}mm): NON-COMPLIANT (min 1100mm required)")
            all_compliant = False
    
    if riser_height is not None:
        if 150 <= riser_height <= 180:
            results.append(f"✅ Riser height ({riser_height}mm): COMPLIANT (150-180mm)")
        else:
            results.append(f"❌ Riser height ({riser_height}mm): NON-COMPLIANT (150-180mm required)")
            all_compliant = False
    
    if tread_depth is not None:
        if tread_depth >= 280:
            results.append(f"✅ Tread depth ({tread_depth}mm): COMPLIANT (min 280mm)")
        else:
            results.append(f"❌ Tread depth ({tread_depth}mm): NON-COMPLIANT (min 280mm required)")
            all_compliant = False
    
    if headroom is not None:
        if headroom >= 2100:
            results.append(f"✅ Headroom ({headroom}mm): COMPLIANT (min 2100mm)")
        else:
            results.append(f"❌ Headroom ({headroom}mm): NON-COMPLIANT (min 2100mm required)")
            all_compliant = False
    
    if not results:
        return "Please provide at least one dimension to check."
    
    status = "✅ ALL DIMENSIONS COMPLIANT" if all_compliant else "⚠️ SOME DIMENSIONS NON-COMPLIANT"
    
    return f"""## Compliance Check Results

{status}

### Details:
{chr(10).join(results)}

---
*Based on Saudi Building Code (SBC) requirements*
"""

@mcp.tool()
def list_requirements(category: str = "general") -> str:
    """
    List building code requirements by category.
    
    Args:
        category: Category of requirements - "general", "residential", "commercial", "emergency"
    
    Returns:
        List of requirements for the specified category
    """
    # Search for category-specific information
    query = f"{category} staircase requirements"
    relevant_docs = search_similar(query, k=5)
    
    if not relevant_docs:
        return f"No specific requirements found for category: {category}"
    
    context = "\n\n".join(relevant_docs)
    
    return f"""## Saudi Building Code - {category.title()} Requirements

{context}

---
*Source: Saudi Building Code (SBC)*
"""

# Initialize on startup
initialize_rag()

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment (Railway sets this)
    port = int(os.environ.get("PORT", 8000))
    
    print(f"🚀 Starting MCP Server on port {port}")
    
    # Run with SSE transport for n8n compatibility
    mcp.run(transport="sse")
