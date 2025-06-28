# Enterprise Knowledge Graph Search: Context-Aware Data Intelligence

## Overview
This project presents an Enterprise Knowledge Graph Search system, an advanced data intelligence solution engineered for diverse enterprise data. It combines sparse TF-IDF search with graph-based relationship mapping and Large Language Model (LLM) integration to deliver high-performance, context-aware search capabilities. This architecture is specifically designed to minimize latency when LLMs query vast enterprise knowledge bases, encompassing structured data, unstructured documents, technical specifications, and operational records.

## Core Capabilities

### High-Performance Search Architecture
- **Sub-100ms Response Time**: Achieves exceptional query performance through optimized sparse matrix operations
- **Memory-Efficient Design**: Utilizes sparse TF-IDF representations to handle large-scale documentation sets
- **Intelligent Filtering**: Implements adaptive threshold filtering (1e-6) to ensure result relevance

### Technical Context Intelligence
- **Relationship Mapping**: Maintains bidirectional relationships between:
  - Technical Components
  - System Signals
  - ECO Tables
  - Section References
  - Technical Diagrams
- **Visual Content Integration**: Automatically indexes and associates technical flowcharts and diagrams
- **Context Preservation**: Maintains technical relationships while providing rapid access to relevant documentation

### Hybrid Search Innovation
- **Dual-Layer Architecture**:
  - Primary Layer: Optimized sparse TF-IDF for rapid technical term matching
  - Secondary Layer: Graph-based relationship traversal for context enrichment
- **LLM Enhancement**: Optional integration with Qwen 3 30B model via Ollama for natural language understanding
- **Adaptive Results**: Combines statistical relevance with technical context for comprehensive results

## Why This Architecture? Optimizing for LLM Performance
This system is specifically designed to act as a highly efficient Retrieval Augmented Generation (RAG) component for Large Language Models (LLMs). By precisely identifying and delivering only the most relevant, contextual data from vast enterprise knowledge bases, it significantly reduces the amount of information the LLM needs to process. This targeted retrieval enables:
- **Reduced Latency**: Faster LLM response times due to smaller, highly relevant input contexts.
- **Cost Efficiency**: Lower operational costs by minimizing the computational load on LLMs.
- **Internal Data Processing**: Facilitates the effective use of smaller, more efficient, and often internally deployable LLMs (e.g., Qwen 3 30B, 30A3B), enhancing data privacy and control.

## Performance Metrics

### Search Operation Breakdown
```
Total Response Time: ~52ms
├── Similarity Computation: 44ms
├── Query Processing: 6ms
├── Filtering: 1.3ms
└── Result Building: 0.4ms
```

### System Requirements
- Python 3.8+
- 16GB RAM recommended for optimal performance
- SSD storage for rapid index access

## Technical Architecture

### Core Components
```
pdf-ai/
├── main.py                 # PDF extraction to JSON
├── build_chunks.py         # Chunks extracted JSON into smaller, processable units
├── build_embeddings.py     # Generates TF-IDF embeddings from chunks
├── build_graph.py          # Constructs the knowledge graph from chunks and relationships
├── serve_hybrid.py         # Core hybrid search service (loads graph, vectorizer, embeddings)
├── ollama_search.py        # LLM integration layer for enhanced search
├── data/                     # Document storage (gitignored)
│   └── pdf_extracted/        # Extracted JSON and images from PDFs
└── persistence/              # Generated search artifacts (gitignored)
    ├── graph.pkl             # Relationship graph
    ├── vectorizer.pkl        # TF-IDF vectorizer
    ├── chunk_embeddings_sparse.npz # Sparse TF-IDF matrix
    └── chunk_ids.json        # Mapping of chunk IDs to embedding indices
```

### Data Flow
1. Document Ingestion → Chunk Extraction
2. TF-IDF Vectorization → Sparse Matrix Generation
3. Relationship Graph Construction
4. Query Processing → Hybrid Search Execution
5. Result Aggregation and Scoring

## Enterprise Benefits

### Operational Efficiency
- **Rapid Access**: Sub-100ms response times enable real-time technical documentation search
- **Resource Optimization**: Sparse matrix operations reduce memory footprint while maintaining performance
- **Scalability**: Designed to handle enterprise-scale technical documentation sets

### Technical Accuracy
- **Context Preservation**: Maintains technical relationships and component dependencies
- **Signal Tracing**: Enables tracking of system signals across documentation
- **Visual Integration**: Associates technical diagrams with relevant documentation

### Integration Ready
- **API-First Design**: Built for enterprise system integration
- **Extensible Architecture**: Supports custom plugins and enhancements
- **LLM Integration**: Ready for advanced natural language processing capabilities

## Detailed Use Cases
For more in-depth examples of how this system can be applied in various enterprise contexts, please refer to:
- [Supply Chain Benefits](supply_chain_benefits.md)
- [Auto Parts Supplier Use Cases](auto_parts_supplier_use_cases.md)
- [E-commerce & Auto Parts E-commerce Use Cases](ecommerce_auto_parts_use_cases.md)

## Getting Started

### Prerequisites
```bash
python -m venv venv
source venv/bin/activate  # Unix/macOS
# or
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Quickest Start

For the fastest way to get started, use the provided shell script:

```bash
./poc.sh
```

This script will automatically perform the data preparation steps and start the hybrid search service. Ensure the script has execute permissions (`chmod +x poc.sh`).

### Detailed Quick Start

If you prefer to run each step manually or understand the process in detail, follow these steps:

1.  **Prepare your PDF data:**
    Place your PDF files (e.g., `Funktionsrahmen-Simos-18.1.pdf`) into the `data/` directory. This directory is designed to hold your raw PDF documents.

2.  **Extract text and images from PDFs:**
    ```bash
    python main.py
    ```
    This script processes the PDF files found in `data/`. It extracts text content and any embedded images, then saves them as structured JSON files and image files within the `data/pdf_extracted/` directory. Each page of a PDF will typically result in a separate JSON file and associated images.

3.  **Build chunks from extracted data:**
    ```bash
    python build_chunks.py
    ```
    After extraction, this script reads the JSON files from `data/pdf_extracted/` and breaks down the content into smaller, manageable "chunks." These chunks are designed to be semantically coherent units suitable for indexing and search. The output is a single `all_chunks.json` file in the project root, containing all processed chunks.

4.  **Build embeddings and the knowledge graph:**
    ```bash
    python build_embeddings.py
    python build_graph.py
    ```
    These two scripts are crucial for preparing the search infrastructure:
    - `build_embeddings.py`: Generates TF-IDF (Term Frequency-Inverse Document Frequency) embeddings from the `all_chunks.json`. These embeddings are sparse numerical representations of your text data, enabling efficient similarity calculations. It produces `vectorizer.pkl` (the TF-IDF model) and `chunk_embeddings_sparse.npz` (the sparse matrix of embeddings).
    - `build_graph.py`: Constructs a knowledge graph based on the relationships identified within your chunks (e.g., connections between technical components, signals, or sections). This graph enhances search by providing context-aware traversal. It generates `graph.pkl`.
    All these generated files (`vectorizer.pkl`, `chunk_embeddings_sparse.npz`, `chunk_ids.json`, and `graph.pkl`) are stored in the `persistence/` directory. This directory acts as a cache for your search artifacts, allowing the search service to load them quickly without re-processing the entire dataset each time.

5.  **Run the hybrid search service (CLI):**
    ```bash
    python serve_hybrid.py
    ```
    This command starts the core hybrid search service. It loads the pre-built graph, vectorizer, and embeddings from the `persistence/` directory. Once loaded, it provides a simple command-line interface where you can enter queries. The service will then perform a hybrid search (combining TF-IDF and graph traversal) and display relevant results directly in your terminal.

6.  **Run the LLM-integrated search (requires Ollama):**
    ```bash
    python ollama_search.py
    ```
    For an enhanced, conversational search experience, you can use this script. It integrates with a local Large Language Model (LLM) via Ollama (e.g., using the `qwen3:4b` model). Ensure Ollama is running and the desired model is pulled. This script provides a conversational interface that leverages the LLM to better understand your natural language queries and generate more comprehensive responses based on the search results.

### Using the POC Shell Script
For convenience, you can use the `poc.sh` script to run the data preparation and start the hybrid search service in sequence:

```bash
./poc.sh
```

Ensure the script has execute permissions (`chmod +x poc.sh`).

### Example Usage (within Python scripts)

You can integrate the search functionality into your own Python applications. The `hybrid_search` function is designed to query across various data types once they are processed and integrated into the knowledge graph.

```python
from serve_hybrid import hybrid_search

# Example 1: Searching technical documentation
# This assumes technical manuals/documents have been processed.
results_tech = hybrid_search("coolant temperature monitoring system specifications")

print("--- Technical Documentation Search Results ---")
for r in results_tech:
    print(f"Chunk ID: {r['chunk_id']}, Score: {r['score']:.3f}")
    print(f"Text: {r['text']}")
    print(f"Section: {r['section_id']}")
    print(f"Related Signals: {r['signal_ids']}")
    print(f"Related ECO Tables: {r['eco_ids']}")
    print(f"Image Paths: {r['image_paths']}")
    print("-" * 20)

# Example 2: Searching supply chain data
# This assumes structured or unstructured supply chain data (e.g., invoices, shipping logs, supplier agreements)
# has been ingested, chunked, and linked within the knowledge graph.
results_supply_chain = hybrid_search("find all shipments delayed by more than 3 days in Q1 2025")

print("\n--- Supply Chain Data Search Results ---")
for r in results_supply_chain:
    print(f"Chunk ID: {r['chunk_id']}, Score: {r['score']:.3f}")
    print(f"Text: {r['text']}")
    # Example of potential supply chain specific metadata fields (adjust based on your data model)
    print(f"Order ID: {r.get('order_id', 'N/A')}")
    print(f"Supplier Name: {r.get('supplier_name', 'N/A')}")
    print(f"Expected Delivery: {r.get('expected_delivery_date', 'N/A')}")
    print(f"Actual Delivery: {r.get('actual_delivery_date', 'N/A')}")
    print("-" * 20)

# Example 3: Conceptual search for customer support interactions
# If customer support transcripts or tickets are processed and integrated:
# results_customer_support = hybrid_search("common issues with product 'X' reported in last month")
#
# print("\n--- Customer Support Data Search Results (Conceptual) ---")
# for r in results_customer_support:
#     print(f"Chunk ID: {r['chunk_id']}, Score: {r['score']:.3f}")
#     print(f"Text: {r['text']}")
#     # Add relevant metadata fields for customer support data
#     # print(f"Ticket ID: {r['ticket_id']}")
#     # print(f"Issue Type: {r['issue_type']}")
#     # print(f"Resolution: {r['resolution']}")
#     print("-" * 20)
```

## Performance Optimization

### Memory Management
- Sparse matrix operations optimize memory usage
- Adaptive threshold filtering reduces result set size
- Efficient graph traversal for relationship queries

### Response Time
- Sub-100ms total response time
- Optimized similarity computation
- Efficient result building and formatting

## Future Roadmap
- Dense embedding layer for enhanced semantic understanding
- User feedback integration for result optimization
- Expanded graph relationship learning
- Advanced query complexity support

## License
This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## Support
For any questions or support, please open an issue on the GitHub repository. 