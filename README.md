# JDN-Chunk Document Processor

A document processing system that extracts text content from various file formats and generates embeddings for further analysis.

## Overview

This project provides a robust document processing system that:

1. Recursively scans a directory for documents (PDF, DOCX) and images
2. Extracts text content using MarkItDown
3. Generates embeddings using Ollama
4. Saves results as markdown and embedding files
5. Implements a restart mechanism to continue processing where it left off

The system is designed following SOLID principles, making it easy to extend and maintain.

## Features

- **Document Extraction**: Extract text from PDFs, DOCX files, and images
- **Embeddings Generation**: Create embeddings using Ollama's models
- **Restart Capability**: Resume processing from where it left off
- **Extensible Architecture**: Easily add support for new file types or processing methods
- **Error Handling**: Gracefully handles processing errors and saves error information

## Installation

### Prerequisites

- Python 3.11
- MarkItDown library
- Ollama (optional, for embeddings generation)

### Setup

1. Clone the repository:
   ```
   git clone <repository-url>
   cd jdn-chunk
   ```

2. Install the required dependencies:
   ```
   uv add 'markitdown[all]' ollama
   ```

## Usage

### Basic Usage

Process all documents in the `docs` directory:

```bash
python main.py
```

### Advanced Options

```bash
python main.py --input-dir docs --output-dir output --enable-plugins --embedding-model "nomic-embed-text"
```

Options:
- `--input-dir`: Directory containing documents to process (default: "docs")
- `--output-dir`: Directory to save output files (default: "output")
- `--enable-plugins`: Enable MarkItDown plugins
- `--embedding-model`: Ollama model to use for embeddings (default: "nomic-embed-text")

## Architecture

The project follows SOLID principles with a clean, modular architecture:

### Interfaces and Implementations

- **FileFinder**: Interface for finding files
  - **ExtensionBasedFileFinder**: Implementation that finds files based on extensions

- **DocumentProcessor**: Interface for processing documents
  - **MarkItDownProcessor**: Implementation using MarkItDown

- **EmbeddingGenerator**: Interface for generating embeddings
  - **OllamaEmbeddingGenerator**: Implementation using Ollama
  - **NullEmbeddingGenerator**: Null implementation when embeddings aren't needed

- **DocumentProcessingService**: Service that orchestrates the process

### File Formats

- **Markdown (.md)**: Contains the extracted text content
- **JSON (.json)**: Human-readable version of embeddings with metadata
- **Progress (.json)**: Tracks processing progress for restart capability

## Development

### Adding New File Types

Extend the `ExtensionBasedFileFinder` by adding new extensions to the set:

```python
extensions = {
    "pdf", "docx",  # Documents
    "png", "jpg", "jpeg",  # Images
    "new_extension"  # Your new extension
}
```

### Implementing New Processing Methods

1. Create a new implementation of the `DocumentProcessor` interface
2. Pass it to the `DocumentProcessingService`

### Adding New Embedding Models

1. Modify the `OllamaEmbeddingGenerator` to use different models
2. Or create a new implementation of the `EmbeddingGenerator` interface
