from markitdown import MarkItDown
import os
import argparse
from document_processor import (
    ExtensionBasedFileFinder,
    MarkItDownProcessor,
    OllamaEmbeddingGenerator,
    ApiFileUploader,
    DocumentProcessingService
)
import time

def main():
    print("Hello from jdn-chunk!")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Process documents and save as markdown files")
    parser.add_argument("--input-dir", default="docs", help="Directory containing documents to process")
    parser.add_argument("--output-dir", default="output", help="Directory to save markdown output")
    parser.add_argument("--enable-plugins", action="store_true", help="Enable MarkItDown plugins")
    parser.add_argument("--embedding-model", default="nomic-embed-text", help="Ollama model to use for embeddings")
    parser.add_argument("--api-url", default="http://localhost:3000", help="API URL for uploading files")
    parser.add_argument("--api-token", default="sk-1be9497213bc416cb05b6d64959df11f", help="API token for authentication")
    parser.add_argument("--skip-upload", action="store_true", help="Skip uploading files to API")
    parser.add_argument("--batch-size", type=int, default=10, help="Number of files to process in parallel")
    parser.add_argument("--max-workers", type=int, default=None, help="Maximum number of worker threads")
    args = parser.parse_args()
    
    # Define file types to process (PDF, DOCX, and images)
    extensions = {
        # Documents
        "pdf", "docx", "txt",
        # Images
        "png", "jpg", "jpeg", "gif", "bmp", "tiff", "webp"
    }
    
    # Create components
    file_finder = ExtensionBasedFileFinder(extensions)
    document_processor = MarkItDownProcessor(enable_plugins=args.enable_plugins)
    embedding_generator = OllamaEmbeddingGenerator(model=args.embedding_model, base_url="http://localhost:11434", api_key=None)
    
    # Create file uploader if not skipped
    file_uploader = None
    if not args.skip_upload:
        if not args.api_token:
            print("Warning: API token not provided. File upload will be skipped.")
        else:
            file_uploader = ApiFileUploader(api_url=args.api_url, token=args.api_token)
    
    processing_service = DocumentProcessingService(
        file_finder,
        document_processor,
        embedding_generator,
        file_uploader,
        output_dir=args.output_dir
    )
    
    # Process all documents in the input directory
    print(f"\nProcessing documents in '{args.input_dir}' directory...")
    print(f"Saving markdown output to '{args.output_dir}' directory...")
    
    # Process documents and get results
    progress, errors, upload_results = processing_service.process_directory(
        args.input_dir,
        batch_size=args.batch_size,
        max_workers=args.max_workers
    )
    
    # Display results
    if not progress:
        print(f"No documents found in '{args.input_dir}' directory.")
    else:
        # Count new vs. previously processed files
        new_files = [
            f for f in progress
            if (
                os.path.exists(processing_service.progress_file) and
                os.path.getmtime(progress[f]) >= os.path.getmtime(processing_service.progress_file)
            ) or not os.path.exists(processing_service.progress_file)
        ]
        
        print(f"\nProcessed {len(new_files)} new documents out of {len(progress)} total:")
        
        # Show information about processed files
        for file_path in new_files:
            md_path = progress[file_path]
            status = "Error" if file_path in errors else "Success"
            print(f"- {file_path} → {md_path} ({status})")
        
        # If there are errors, provide more details
        if errors:
            print("\nErrors encountered:")
            for file_path, error in errors.items():
                print(f"- {file_path}: {error}")
        
        print(f"\nAll results saved to: {args.output_dir}")
        print(f"Progress file saved to: {processing_service.progress_file}")
        print(f"Embeddings were generated using the '{args.embedding_model}' model")
        
        print("Sleeping 10s before uploading")
        time.sleep(10)

        ids = [upload_results[x]['id'] for x in upload_results]
        processing_service.add_files_to_knowledge(ids, api_url=args.api_url, token=args.api_token)
        
        # Show upload results if any
        if upload_results:
            print(f"\nUploaded {len(upload_results)} files:")
            for md_path, result in upload_results.items():
                status = "Success" if not result.get("error") else f"Error: {result.get('error')}"
                print(f"- {md_path}: {status}")
        
        # Show upload results file location
        if file_uploader:
            print(f"Upload results saved to: {processing_service.upload_results_file}")


if __name__ == "__main__":
    main()
