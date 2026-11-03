import os
from pathlib import Path
from pypdf import PdfReader, PdfWriter

# =================================================================
# 1. CONFIGURATION: CHANGE THESE THREE VARIABLES
# =================================================================

# The folder where your original PDF files are located.
# Use an 'r' prefix for raw string to handle Windows paths easily.
SOURCE_FOLDER = r"C:\Users\Acer\Desktop\AFE\PDFs\Source_PDF_for exporting\WRC ENERGY_PDF_Download"

# The folder where the new, extracted PDF files will be saved.
DESTINATION_FOLDER = r"C:\Users\Acer\Desktop\AFE\PDFs\Export_PDF"

# The page range to extract (1-based page numbers)
START_PAGE = 10   # For example, start at the 3rd page
END_PAGE = 11    # End at the 8th page (extracts pages 3, 4, 5, 6, 7, 8)

# =================================================================

def extract_pages_bulk():
    # Ensure the source folder exists
    source_path = Path(SOURCE_FOLDER)
    if not source_path.is_dir():
        print(f"Error: Source folder not found at {SOURCE_FOLDER}")
        return

    # Create the destination folder if it doesn't exist
    destination_path = Path(DESTINATION_FOLDER)
    destination_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Searching for PDFs in: {SOURCE_FOLDER}")
    
    processed_count = 0
    
    # Loop through every file in the source folder
    for input_pdf_path in source_path.glob("*.pdf"):
        
        # Determine the name for the new output file
        # It appends '_extracted' before the .pdf extension
        output_filename = f"{input_pdf_path.stem}.pdf"
        output_pdf_path = destination_path / output_filename
        
        print(f"\nProcessing: {input_pdf_path.name}")
        
        try:
            reader = PdfReader(input_pdf_path)
            writer = PdfWriter()

            # Iterate through the desired pages (Remember: Python is 0-indexed)
            # The range needs (START_PAGE - 1) up to END_PAGE
            for i in range(START_PAGE - 1, END_PAGE):
                if i < len(reader.pages):
                    writer.add_page(reader.pages[i])
                else:
                    # Handle cases where a file is too short
                    print(f"Warning: PDF is too short to reach page {i + 1}.")
                    break

            # Write the collected pages to the new PDF file
            with open(output_pdf_path, "wb") as output_file:
                writer.write(output_file)
            
            print(f"SUCCESS: Extracted pages {START_PAGE}-{i+1} saved to {output_pdf_path.name}")
            processed_count += 1
            
        except Exception as e:
            print(f"ERROR processing {input_pdf_path.name}: {e}")

    print(f"\n--- DONE ---")
    print(f"Total PDFs processed: {processed_count}")

# Execute the main function
if __name__ == "__main__":
    extract_pages_bulk()