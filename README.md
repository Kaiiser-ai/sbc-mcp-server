# Saudi Building Code MCP Server

MCP (Model Context Protocol) server for querying Saudi Building Code staircase requirements.

## Features

- **RAG-based queries**: Ask questions about building code requirements
- **Compliance checking**: Verify if dimensions meet code requirements
- **Category listing**: Get requirements by category (residential, commercial, etc.)

## MCP Tools

1. `query_building_code(question)` - Ask any question about the building code
2. `check_compliance(stair_width, riser_height, tread_depth, headroom)` - Check dimension compliance
3. `list_requirements(category)` - List requirements by category

## Setup

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Add your PDF to data folder
cp your_sbc_file.pdf data/sbc_staircase.pdf

# Run server
python server.py
```

### Deploy to Railway

1. Push to GitHub
2. Connect Railway to your repo
3. Add your PDF via Railway volume or include in repo
4. Deploy!

## Usage with n8n

1. Add MCP Client node
2. Set Server Transport: HTTP Streamable
3. Set MCP Endpoint URL: `https://your-railway-url.railway.app/mcp`
4. Select tool and provide inputs

## Author

Mohamad Jaber - MAICEN Thesis Project
