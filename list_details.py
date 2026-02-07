#!/usr/bin/env python3
"""
Script to extract and display all details from election list PDF files.
This script reads both FinalList_Ward_2.pdf and FinalList_Ward_3.pdf
and displays their contents.
"""

import PyPDF2
import os
import sys


def extract_pdf_content(pdf_path):
    """
    Extract text content from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text content as a string
    """
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            content = []
            
            # Extract text from each page
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                content.append(f"\n{'='*80}\nPage {page_num + 1}\n{'='*80}\n{text}")
            
            return '\n'.join(content)
    except FileNotFoundError:
        return f"Error: File '{pdf_path}' not found."
    except Exception as e:
        return f"Error reading '{pdf_path}': {str(e)}"


def main():
    """Main function to list details from both election list PDF files."""
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define the PDF files
    pdf_files = [
        'FinalList_Ward_2.pdf',
        'FinalList_Ward_3.pdf'
    ]
    
    print("="*80)
    print("ELECTION LIST - DETAILED INFORMATION")
    print("="*80)
    print("\nExtracting details from both ward files...\n")
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(script_dir, pdf_file)
        
        print(f"\n{'#'*80}")
        print(f"# FILE: {pdf_file}")
        print(f"{'#'*80}\n")
        
        if os.path.exists(pdf_path):
            content = extract_pdf_content(pdf_path)
            print(content)
        else:
            print(f"Error: {pdf_file} not found in {script_dir}")
    
    print("\n" + "="*80)
    print("END OF ELECTION LIST DETAILS")
    print("="*80)


if __name__ == "__main__":
    main()
