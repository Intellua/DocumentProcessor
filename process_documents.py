#!/usr/bin/env python3
import os
import argparse
from document_processor import (
    ExtensionBasedFileFinder,
    MarkItDownProcessor,
    OllamaEmbeddingGenerator,
    DocumentProcessingService
)


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Process documents and save as markdown files")
    parser.add_argument("--input-dir", default="docs", help="Directory containing documents to process")
    parser.add_argument("--output-dir", default="output", help="Directory to save markdown output")
    parser.add_argument("--enable-plugins", action="store_true", help="Enable MarkItDown plugins")
    args = parser.parse_args()
    
    # Define file types to process
    # PDF, DOCX, and common image formats
    extensions = {
        # Documents
        "pdf", "docx",
        # Images
        "png", "jpg", "jpeg", "gif", "bmp", "tiff", "webp"
    }
    
    # Create components following dependency injection pattern
    file_finder = ExtensionBasedFileFinder(extensions)
    document_processor = MarkItDownProcessor(enable_plugins=args.enable_plugins)
    embedding_generator = OllamaEmbeddingGenerator(model="nomic-embed-text")
    
    # Create the service by injecting dependencies
    processing_service = DocumentProcessingService(
        file_finder,
        document_processor,
        embedding_generator,
        output_dir=args.output_dir
    )
    
    # Process all documents in the input directory
    print(f"Processing documents in '{args.input_dir}' directory...")
    print(f"Saving markdown output to '{args.output_dir}' directory...")
    
    # Process documents and get results
    progress, errors = processing_service.process_directory(args.input_dir)
    
    # Display results
    if not progress:
        print(f"No documents found in '{args.input_dir}' directory.")
    else:
        # Count new vs. previously processed files
        # Determine which files are newly processed
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


if __name__ == "__main__":
    main()