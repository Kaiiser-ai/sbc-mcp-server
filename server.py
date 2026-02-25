"""
Saudi Building Code MCP Server
RAG-based building code assistant using MCP protocol
Uses OpenAI embeddings for faster deployment
"""

import os
from mcp.server.fastmcp import FastMCP
from openai import OpenAI
import chromadb
import PyPDF2
from pathlib import Path

# Initialize MCP server
mcp = FastMCP("Saudi Building Code Assistant")

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
    """Initialize the RAG system with vector store"""
    global collection
    
    print("🔄 Initializing RAG system...")
    
    # Initialize ChromaDB (in-memory for simplicity)
    chroma_client = chromadb.Client()
    
    # Get or create collection
    collection = chroma_client.get_or_create_collection(
        name="saudi_building_code",
        metadata={"description": "Saudi Building Code - Staircase Requirements"}
    )
    print(f"✅ Vector store ready with {collection.count()} documents")
    
    # If empty, load the PDF
    if collection.count() == 0:
        load_pdf()

def load_pdf():
    """Load and chunk the Saudi Building Code PDF"""
    global collection
    
    # Try multiple possible paths
    possible_paths = [
        Path("./Full SBC staircase.pdf"),
        Path("./data/sbc_staircase.pdf"),
        Path("/app/Full SBC staircase.pdf"),
        Path("/app/data/sbc_staircase.pdf")
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
    
    # Extract text from PDF
    text = ""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    
    # Chunk the text
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    print(f"📝 Created {len(chunks)} chunks")
    
    # Create embeddings and store
    for i, chunk in enumerate(chunks):
        try:
            embedding = get_embedding(chunk)
            collection.add(
                ids=[f"chunk_{i}"],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{"source": "SBC_Staircase", "chunk_id": i}]
            )
        except Exception as e:
            print(f"⚠️ Error embedding chunk {i}: {e}")
    
    print(f"✅ Loaded {collection.count()} chunks into vector store")

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
    global collection
    
    if collection is None:
        initialize_rag()
    
    if collection.count() == 0:
        return []
    
    # Create query embedding
    query_embedding = get_embedding(query)
    
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
        question: Your question about building code requirements
    
    Returns:
        Relevant building code information
    """
    # Ensure RAG is initialized
    if collection is None or collection.count() == 0:
        initialize_rag()
    
    # Search for relevant chunks
    relevant_docs = search_similar(question, k=3)
    
    if not relevant_docs:
        return "No relevant information found in the Saudi Building Code database."
    
    # Format response
    context = "\n\n---\n\n".join(relevant_docs)
    
    response = f"""## Saudi Building Code - Relevant Sections

**Question:** {question}

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
        stair_width: Width of staircase in mm
        riser_height: Height of each step in mm
        tread_depth: Depth of each step in mm
        headroom: Vertical clearance in mm
    
    Returns:
        Compliance status and recommendations
    """
    results = []
    all_compliant = True
    
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
    
    status = "✅ ALL COMPLIANT" if all_compliant else "⚠️ NON-COMPLIANT"
    
    return f"""## Compliance Check Results

**Status:** {status}

### Details:
{chr(10).join(results)}

---
*Based on Saudi Building Code (SBC)*
"""

@mcp.tool()
def list_requirements(category: str = "general") -> str:
    """
    List building code requirements by category.
    
    Args:
        category: Category - "general", "residential", "commercial", "emergency"
    
    Returns:
        List of requirements
    """
    if collection is None or collection.count() == 0:
        initialize_rag()
    
    query = f"{category} staircase requirements"
    relevant_docs = search_similar(query, k=5)
    
    if not relevant_docs:
        return f"No requirements found for category: {category}"
    
    context = "\n\n".join(relevant_docs)
    
    return f"""## Saudi Building Code - {category.title()} Requirements

{context}

---
*Source: Saudi Building Code (SBC)*
"""

# Initialize on startup
print("🚀 Starting Saudi Building Code MCP Server...")

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    print(f"🌐 Running on port {port}")
    
    # Set the port via environment variable for FastMCP
    os.environ["FASTMCP_PORT"] = str(port)
    
    mcp.run(transport="sse")
