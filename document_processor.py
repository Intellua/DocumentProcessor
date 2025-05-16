from abc import ABC, abstractmethod
import os
from pathlib import Path
from typing import List, Set, Dict, Tuple, Any
import json
import numpy as np
from markitdown import MarkItDown

# Import ollama for embeddings
try:
    from ollama import Client
except ImportError:
    print("Warning: ollama package not found. Embeddings functionality will be disabled.")
    ollama = None


class FileFinder(ABC):
    """Interface for file finding strategies"""
    @abstractmethod
    def find_files(self, directory: str) -> List[str]:
        """Find files in the specified directory"""
        pass


class DocumentProcessor(ABC):
    """Interface for document processing strategies"""
    @abstractmethod
    def process_document(self, file_path: str) -> str:
        """Process a document and return the text content"""
        pass


class EmbeddingGenerator(ABC):
    """Interface for generating embeddings from text"""
    
    @abstractmethod
    def generate_embeddings(self, text: str) -> Any:
        """
        Generate embeddings from text
        
        Args:
            text: Text to generate embeddings for
            
        Returns:
            Embeddings representation (implementation-specific)
        """
        pass
    
    @abstractmethod
    def save_embeddings(self, embeddings: Any, file_path: str) -> None:
        """
        Save embeddings to a file
        
        Args:
            embeddings: Embeddings to save
            file_path: Path to save embeddings to
        """
        pass


class OllamaEmbeddingGenerator(EmbeddingGenerator):
    """Implementation of EmbeddingGenerator using Ollama"""
    
    def __init__(self, model: str = "nomic-embed-text", base_url: str = "http://localhost:11434", api_key: str = None):
        """
        Initialize with Ollama model configuration
        
        Args:
            model: Ollama model to use for embeddings
        """
        self.model = model
    
        headers = None
        if api_key is not None:
            headers = {'Authorization': f'Bearer {api_key}'}

        self.client = Client(host=base_url, headers=headers)
        
    def generate_embeddings(self, text: str) -> Any:
        """
        Generate embeddings using Ollama
        
        Args:
            text: Text to generate embeddings for
            
        Returns:
            Embeddings from Ollama or None if unavailable
        """
            
        try:
            response = self.client.embeddings(model=self.model, prompt=text)
            return response.get('embedding')
        except Exception as e:
            print(f"Error generating embeddings: {str(e)}")
            return None
            
    def save_embeddings(self, embeddings: Any, file_path: str) -> None:
        """
        Save embeddings to a file
        
        Args:
            embeddings: Embeddings to save
            file_path: Path to save embeddings to
        """
        if embeddings is None:
            return
            
        try:
            # Also save a JSON version for human readability/debugging
            with open(file_path, 'w') as f:
                json.dump({
                    'model': self.model,
                    'dimensions': len(embeddings),
                    'embedding': embeddings
                }, f, indent=2)
                
        except Exception as e:
            print(f"Error saving embeddings: {str(e)}")


class NullEmbeddingGenerator(EmbeddingGenerator):
    """Null implementation of EmbeddingGenerator for when embeddings are not needed"""
    
    def generate_embeddings(self, text: str) -> None:
        """No-op implementation"""
        return None
        
    def save_embeddings(self, embeddings: Any, file_path: str) -> None:
        """No-op implementation"""
        pass


class ExtensionBasedFileFinder(FileFinder):
    """Implementation of FileFinder that finds files based on extensions"""
    
    def __init__(self, extensions: Set[str]):
        """
        Initialize with a set of file extensions to find
        
        Args:
            extensions: Set of file extensions (without the dot)
        """
        self.extensions = extensions
    
    def find_files(self, directory: str) -> List[str]:
        """
        Find all files with the specified extensions in the directory
        
        Args:
            directory: Path to the directory to search
            
        Returns:
            List of file paths matching the extensions
        """
        result = []
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.lower().endswith(f".{ext}") for ext in self.extensions):
                    result.append(os.path.join(root, file))
        return result


class MarkItDownProcessor(DocumentProcessor):
    """Implementation of DocumentProcessor using MarkItDown"""
    
    def __init__(self, enable_plugins: bool = False):
        """
        Initialize with MarkItDown configuration
        
        Args:
            enable_plugins: Whether to enable plugins in MarkItDown
        """
        self.md = MarkItDown(enable_plugins=enable_plugins)
    
    def process_document(self, file_path: str) -> str:
        """
        Process a document using MarkItDown
        
        Args:
            file_path: Path to the document to process
            
        Returns:
            Extracted text content
        """
        result = self.md.convert(file_path)
        return result.text_content


class DocumentProcessingService:
    """Service that finds and processes documents"""
    
    def __init__(self,
                 file_finder: FileFinder,
                 document_processor: DocumentProcessor,
                 embedding_generator: EmbeddingGenerator = None,
                 output_dir: str = "output"):
        """
        Initialize with strategies for finding and processing files
        
        Args:
            file_finder: Strategy for finding files
            document_processor: Strategy for processing documents
            embedding_generator: Strategy for generating embeddings (optional)
            output_dir: Directory to save markdown output files
        """
        self.file_finder = file_finder
        self.document_processor = document_processor
        self.embedding_generator = embedding_generator or NullEmbeddingGenerator()
        self.output_dir = output_dir
        self.progress_file = os.path.join(output_dir, "processing_progress.json")
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    def _get_markdown_filename(self, file_path: str) -> str:
        """
        Generate a markdown filename for the output file
        
        Args:
            file_path: Original file path
            
        Returns:
            Path to the markdown output file
        """
        base_name = os.path.basename(file_path)
        name_without_ext = os.path.splitext(base_name)[0]
        return os.path.join(self.output_dir, f"{name_without_ext}.md")
    
    def _get_embeddings_filename(self, file_path: str) -> str:
        """
        Generate a embeddings filename for the output file
        
        Args:
            file_path: Original file path
            
        Returns:
            Path to the embeddings output file
        """
        base_name = os.path.basename(file_path)
        name_without_ext = os.path.splitext(base_name)[0]
        return os.path.join(self.output_dir, f"{name_without_ext}.embeddings")
    
    def _load_progress(self) -> Dict[str, str]:
        """
        Load processing progress from JSON file
        
        Returns:
            Dictionary mapping file paths to output markdown paths
        """
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def _save_progress(self, progress: Dict[str, str]) -> None:
        """
        Save processing progress to JSON file
        
        Args:
            progress: Dictionary mapping file paths to output markdown paths
        """
        with open(self.progress_file, 'w') as f:
            json.dump(progress, f, indent=2)
    
    def process_directory(self, directory: str) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        Process all matching documents in the directory and save as markdown
        
        Args:
            directory: Path to the directory to process
            
        Returns:
            Tuple containing:
            - Dictionary mapping file paths to their output markdown paths
            - Dictionary mapping file paths to errors (if any)
        """
        # Load existing progress
        progress = self._load_progress()
        errors = {}
        
        # Find all files to process
        files = self.file_finder.find_files(directory)
        
        # Process each file
        for file_path in files:
            # Skip already processed files
            if file_path in progress and os.path.exists(progress[file_path]):
                continue
                
            # Generate output markdown filename
            md_filename = self._get_markdown_filename(file_path)

            # Generate output embeddings filename
            embeddings_filename = self._get_embeddings_filename(file_path)
            
            try:
                # Process the document
                content = self.document_processor.process_document(file_path)
                
                # Save content to markdown file
                with open(md_filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Generate and save embeddings
                embeddings = self.embedding_generator.generate_embeddings(content)
                if embeddings is not None:
                    self.embedding_generator.save_embeddings(embeddings, embeddings_filename)
                else:
                    print("Embeddings are none")
                
                # Update progress
                progress[file_path] = md_filename
                
            except Exception as e:
                # Record error
                error_message = f"Error processing file: {str(e)}"
                errors[file_path] = error_message
                
                # Create error markdown file
                with open(md_filename, 'w', encoding='utf-8') as f:
                    f.write(f"# Error processing {os.path.basename(file_path)}\n\n")
                    f.write(f"```\n{error_message}\n```\n")
                
                # Update progress even for errors
                progress[file_path] = md_filename
        
        # Save progress
        self._save_progress(progress)
        
        return progress, errors