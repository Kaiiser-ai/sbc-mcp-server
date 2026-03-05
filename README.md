# Saudi Building Code AI Assistant — Agentic Hybrid RAG with MCP

An end-to-end pipeline that lets you query the Saudi Building Code (SBC 201-CC-2024) using natural language and get grounded, section-referenced answers — powered by Agentic Hybrid RAG served via MCP in a multi-agent architecture.

## What It Does

Ask a question like *"What is the minimum tread depth?"* and get:

> **275 mm** (Section 1011.5.2, pages 1106–1107)

No hallucinations. Just the actual code, with section references.

## Architecture

```
Colab (processing + embeddings)
    → Supabase (vector DB + keyword search)
        → n8n (AI Agent #1: Agentic Hybrid RAG)
            → MCP (protocol layer)
                → Claude (AI Agent #2: conversational interface)
```

### Why "Agentic Hybrid RAG with MCP"?

- **Hybrid RAG** — Two retrieval methods: vector search (semantic similarity) + keyword search (exact term matching). One knowledge base.
- **Agentic** — The n8n AI Agent autonomously decides how to query both retrieval tools, combines results, and generates grounded answers. It reasons over what it finds — not just retrieve-and-paste.
- **MCP** — The workflow is exposed as an MCP server, so Claude can connect to it as a second AI Agent. Two agents, two roles, one pipeline.
- **Multi-Agent** — Claude handles conversation and user interaction via MCP. The n8n AI Agent handles retrieval and code-grounded reasoning.

## Stack

| Layer | Tool | Role |
|-------|------|------|
| Data Processing | Google Colab | PDF extraction, chunking, embedding generation |
| Embeddings | OpenAI (text-embedding-ada-002) | Vector embeddings for semantic search |
| Knowledge Store | Supabase | Vector database (`match_sbc_documents`) + keyword search (`keyword_search_sbc`) |
| AI Agent / Orchestration | n8n | AI Agent with dual retrieval tools + direct chat interface |
| LLM | GPT-4.1-mini | Reasoning and answer generation |
| Protocol | MCP | Exposes the n8n workflow to external AI clients |
| Interface | Claude.ai | Conversational front-end via MCP connection |

## Repository Contents

```
├── README.md
├── SBC_RAG_Pipeline.ipynb          # Colab notebook: PDF processing, chunking, embedding, upload
├── SBC_MCP_Query.json              # n8n workflow: AI Agent with dual retrieval + MCP
└── screenshots/                    # Architecture diagram and demo screenshots (optional)
```

## Setup Guide

### 1. Supabase

Create a Supabase project and set up the following:

**Vector table** — `sbc_documents`:
- `id` (int8, primary key)
- `content` (text)
- `metadata` (jsonb)
- `embedding` (vector(1536))

**Functions:**
- `match_sbc_documents` — vector similarity search using pgvector
- `keyword_search_sbc` — full-text keyword search on content

### 2. Colab Notebook

Open `SBC_RAG_Pipeline.ipynb` in Google Colab:

1. Upload the SBC 201-CC-2024 PDF
2. Set your environment variables:
   - `OPENAI_API_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
3. Run all cells — this will:
   - Extract text from the PDF
   - Chunk it into meaningful sections
   - Generate OpenAI embeddings
   - Upload everything to Supabase

### 3. n8n Workflow

Import `SBC_MCP_Query.json` into your n8n instance:

1. Go to n8n → Import Workflow → paste the JSON
2. Configure credentials:
   - **OpenAI** — your API key
   - **Supabase** — your project URL and API key
3. Update the HTTP Request node with your Supabase URL and key
4. Activate the workflow
5. Enable **"Available in MCP"** in workflow settings

### 4. Claude.ai (MCP Connection)

1. In Claude.ai settings, add your n8n MCP server URL
2. Start a new conversation and ask any SBC question

## Demo Questions

These queries consistently return strong, grounded answers:

- "What is the minimum tread depth?"
- "What is the maximum riser height?"
- "What is the minimum stair width?"

## Key Decisions

- **Dual retrieval** — Vector search alone misses exact terms; keyword search alone misses context. Using both gives the most reliable results.
- **topK=12** — Retrieves 12 chunks per vector query for sufficient coverage of complex code sections.
- **GPT-4.1-mini** — Fast and cost-effective for the RAG reasoning layer. Claude handles the conversational interface.
- **Session memory** — The n8n agent maintains conversation context within a session for follow-up questions.

## Limitations

- Some SBC sections (e.g., fire rating for exit stairway enclosures) are not reliably retrieved — a known chunking/embedding gap that could be improved with better chunking strategies or contextual enrichment.
- The system works best with specific, measurable code queries (dimensions, heights, widths) rather than broad conceptual questions.

## License

This project is for educational and research purposes. The Saudi Building Code (SBC 201-CC-2024) content is not included in this repository due to copyright.

## Author

Built as part of the MSc in AI for Architecture, Engineering, Construction & Operations (MAICEN) program at Zigurat Institute of Technology.

---

*This is one approach to grounded AI for AEC professionals — building codes that answer back.*
