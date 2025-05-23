from abc import ABC, abstractmethod
import os
from pathlib import Path
from typing import List, Set, Dict, Tuple, Any, Optional
import json
import numpy as np
from markitdown import MarkItDown
import requests
import concurrent.futures
import threading
from functools import partial
from pathlib import Path

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


class FileUploader(ABC):
    """Interface for uploading files to external services"""
    
    @abstractmethod
    def upload_file(self, file_path: str) -> Dict[str, Any]:
        """
        Upload a file to an external service
        
        Args:
            file_path: Path to the file to upload
            
        Returns:
            Response data from the upload service
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
        return None    
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


class ApiFileUploader(FileUploader):
    """Implementation of FileUploader using API requests"""
    
    def __init__(self, api_url: str, token: str):
        """
        Initialize with API URL and authentication token
        
        Args:
            api_url: Base URL of the API
            token: Authentication token
        """
        self.api_url = api_url.rstrip('/')
        self.token = token
        
    def upload_file(self, file_path: str) -> Dict[str, Any]:
        """
        Upload a file to the API
        
        Args:
            file_path: Path to the file to upload
            
        Returns:
            Response data from the API
        """
        url = f'{self.api_url}/api/v1/files/'
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/json'
        }
        
        try:
            with open(file_path, 'rb') as f:
                filename = Path(file_path).name
                files = {'file': (filename, f, 'text/markdown')}
                response = requests.post(url, headers=headers, files=files)
                response.raise_for_status()  # Raise exception for 4XX/5XX responses
                result = response.json()
                return result

        except Exception as e:
            print(f"Error uploading file {file_path}: {str(e)}")
            return {"error": str(e), "file_path": file_path}


class NullFileUploader(FileUploader):
    """Null implementation of FileUploader for when file uploading is not needed"""
    
    def upload_file(self, file_path: str) -> Dict[str, Any]:
        """No-op implementation"""
        return {"status": "skipped", "file_path": file_path}


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
                 file_uploader: FileUploader = None,
                 output_dir: str = "output"):
        """
        Initialize with strategies for finding and processing files
        
        Args:
            file_finder: Strategy for finding files
            document_processor: Strategy for processing documents
            embedding_generator: Strategy for generating embeddings (optional)
            file_uploader: Strategy for uploading files (optional)
            output_dir: Directory to save markdown output files
        """
        self.file_finder = file_finder
        self.document_processor = document_processor
        self.embedding_generator = embedding_generator or NullEmbeddingGenerator()
        self.file_uploader = file_uploader or NullFileUploader()
        self.output_dir = output_dir
        self.progress_file = os.path.join(output_dir, "processing_progress.json")
        self.upload_results_file = os.path.join(output_dir, "upload_results.json")
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Add locks for thread safety
        self.progress_lock = threading.Lock()
        self.upload_results_lock = threading.Lock()
    
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
        with self.progress_lock:
            with open(self.progress_file, 'w') as f:
                json.dump(progress, f, indent=2)
    
    def _load_upload_results(self) -> Dict[str, Dict[str, Any]]:
        """
        Load file upload results from JSON file
        
        Returns:
            Dictionary mapping markdown file paths to upload results
        """
        if os.path.exists(self.upload_results_file):
            try:
                with open(self.upload_results_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def _save_upload_results(self, results: Dict[str, Dict[str, Any]]) -> None:
        """
        Save file upload results to JSON file
        
        Args:
            results: Dictionary mapping markdown file paths to upload results
        """
        with self.upload_results_lock:
            with open(self.upload_results_file, 'w') as f:
                json.dump(results, f, indent=2)
    
    def _process_file(self, file_path: str, progress: Dict[str, str], errors: Dict[str, str]) -> Tuple[str, bool]:
        """
        Process a single file
        
        Args:
            file_path: Path to the file to process
            progress: Shared progress dictionary
            errors: Shared errors dictionary
            
        Returns:
            Tuple containing:
            - Output markdown path
            - Whether processing was successful
        """
        # Skip already processed files
        with self.progress_lock:
            if file_path in progress and os.path.exists(progress[file_path]):
                return progress[file_path], True
                
        # Generate output filenames
        md_filename = self._get_markdown_filename(file_path)
        embeddings_filename = self._get_embeddings_filename(file_path)
        
        try:
            # Process the document
            content = self.document_processor.process_document(file_path)

            # Skip empty content
            if content == '':
                return md_filename, False
            
            # Save content to markdown file
            with open(md_filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Generate and save embeddings
            embeddings = self.embedding_generator.generate_embeddings(content)
            if embeddings is not None:
                self.embedding_generator.save_embeddings(embeddings, embeddings_filename)
            
            # Update progress
            with self.progress_lock:
                progress[file_path] = md_filename
                
            return md_filename, True
                
        except Exception as e:
            # Record error
            error_message = f"Error processing file: {str(e)}"
            
            with self.progress_lock:
                errors[file_path] = error_message
            
            # Create error markdown file
            with open(md_filename, 'w', encoding='utf-8') as f:
                f.write(f"# Error processing {os.path.basename(file_path)}\n\n")
                f.write(f"```\n{error_message}\n```\n")
            
            # Update progress even for errors
            with self.progress_lock:
                progress[file_path] = md_filename
                
            return md_filename, False
    
    def _upload_file(self, file_info: Tuple[str, str], upload_results: Dict[str, Dict[str, Any]], new_upload_results: Dict[str, Dict[str, Any]]) -> None:
        """
        Upload a file to the external service
        
        Args:
            file_info: Tuple containing (file_path, md_path)
            upload_results: Shared upload results dictionary
            new_upload_results: Shared new upload results dictionary
        """
        file_path, md_path = file_info
        
        # Skip already uploaded files
        with self.upload_results_lock:
            if md_path in upload_results and upload_results[md_path].get("status") != "error":
                return
        
        # Upload the markdown file
        result = self.file_uploader.upload_file(md_path)
        
        with self.upload_results_lock:
            upload_results[md_path] = result
            new_upload_results[md_path] = result
    
    def process_directory(self, directory: str, batch_size: int = 10, max_workers: int = None) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, Dict[str, Any]]]:
        """
        Process all matching documents in the directory in parallel batches, save as markdown, and upload
        
        Args:
            directory: Path to the directory to process
            batch_size: Number of files to process in parallel
            max_workers: Maximum number of worker threads (defaults to min(32, os.cpu_count() + 4))
            
        Returns:
            Tuple containing:
            - Dictionary mapping file paths to their output markdown paths
            - Dictionary mapping file paths to errors (if any)
            - Dictionary mapping markdown file paths to upload results
        """
        # Load existing progress and upload results
        progress = self._load_progress()
        upload_results = self._load_upload_results()
        errors = {}
        new_upload_results = {}
        
        # Find all files to process
        files = self.file_finder.find_files(directory)
        
        # Skip already processed files
        files_to_process = []
        for file_path in files:
            if file_path not in progress or not os.path.exists(progress[file_path]):
                files_to_process.append(file_path)
        
        # Process files in parallel batches
        if files_to_process:
            print(f"Processing {len(files_to_process)} files in batches of {batch_size}...")
            
            # Process files in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Create a partial function with shared dictionaries
                process_file_func = partial(self._process_file, progress=progress, errors=errors)
                
                # Process files in batches
                for i in range(0, len(files_to_process), batch_size):
                    batch = files_to_process[i:i+batch_size]
                    print(f"Processing batch {i//batch_size + 1}/{(len(files_to_process) + batch_size - 1)//batch_size} ({len(batch)} files)...")
                    
                    # Submit batch for processing
                    futures = [executor.submit(process_file_func, file_path) for file_path in batch]
                    concurrent.futures.wait(futures)
                
                # Save progress after each batch
                self._save_progress(progress)
        
        # Upload markdown files in parallel
        if progress:
            print(f"Uploading {len(progress)} markdown files in batches of {batch_size}...")
            
            # Create list of (file_path, md_path) tuples for uploading
            upload_items = [(file_path, md_path) for file_path, md_path in progress.items()]
            
            # Upload files in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Create a partial function with shared dictionaries
                upload_file_func = partial(
                    self._upload_file,
                    upload_results=upload_results,
                    new_upload_results=new_upload_results
                )
                
                # Upload files in batches
                for i in range(0, len(upload_items), batch_size):
                    batch = upload_items[i:i+batch_size]
                    print(f"Uploading batch {i//batch_size + 1}/{(len(upload_items) + batch_size - 1)//batch_size} ({len(batch)} files)...")
                    
                    # Submit batch for uploading
                    futures = [executor.submit(upload_file_func, item) for item in batch]
                    concurrent.futures.wait(futures)
                
                # Save upload results after each batch
                self._save_upload_results(upload_results)
        
        return progress, errors, new_upload_results
    
    def add_files_to_knowledge(self, ids, api_url: str, token: str):
        knowledge_url = f'{api_url}/api/v1/knowledge/a6470419-7149-41de-8de1-e8b44404c7c8/file/add'
        knowledge_headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
        }

        for id in ids:
            data = {'file_id': id}
            try:
                response = requests.post(knowledge_url, headers=knowledge_headers, json=data)

                response.raise_for_status()
            except Exception as e:
                print(e)
                print(response.json())