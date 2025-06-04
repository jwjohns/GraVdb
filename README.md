# PDF-AI: Intelligent Technical Documentation Search System

## Overview
PDF-AI is a sophisticated document search and analysis system designed specifically for technical documentation. It combines sparse TF-IDF search with LLM-powered analysis to provide accurate and contextually relevant search results from PDF documents.

## Key Features
- **Sparse TF-IDF Search**: High-performance search system optimized for technical terminology
- **LLM Integration**: Advanced context understanding using the Qwen 3 30B model via Ollama
- **Performance Optimized**: Sub-100ms search response times
- **Technical Context Awareness**: Maintains relationships between technical components and signals
- **Scalable Architecture**: Designed to handle large technical documentation sets

## System Architecture
### Search Components
- Sparse TF-IDF vectorization for efficient document representation
- Threshold-based filtering (1e-6) for result relevance
- Relationship mapping between technical components
- LLM-powered context enhancement

### Performance Metrics
- Total Search Time: ~52ms
  - Similarity Computation: 44ms
  - Query Processing: 6ms
  - Filtering: 1.3ms
  - Result Building: 0.4ms

## Installation

### Prerequisites
- Python 3.8 or higher
- Virtual environment management tool (venv)
- Ollama (for LLM integration)

### Setup
1. Clone the repository:
```bash
git clone [repository-url]
cd pdf-ai
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Unix/macOS
# or
.\venv\Scripts\activate  # On Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Ensure Ollama is installed and the Qwen 3 30B model is available:
```bash
ollama pull qwen3:30b
```

## Usage

### Basic Search
```python
from search.sparse_search import perform_search

results = perform_search("query text")
```

### LLM-Enhanced Search
```python
from search.ollama_search import perform_llm_search

enhanced_results = perform_llm_search("technical query")
```

## Project Structure
```
pdf-ai/
├── search/
│   ├── sparse_search.py      # TF-IDF search implementation
│   └── ollama_search.py      # LLM integration
├── data/                     # Document storage (gitignored)
├── docs/
│   ├── search_evaluation_results.md
│   └── llm_integration_analysis.md
├── requirements.txt
└── README.md
```

## Performance Considerations
- The system uses sparse matrices for efficient memory usage
- Filtering threshold can be adjusted for performance/accuracy trade-off
- LLM processing is done asynchronously to maintain responsiveness

## Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License
[License Information]

## Contact
[Contact Information] 