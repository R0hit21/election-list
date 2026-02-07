# election-list

This repository contains election ward lists in PDF format and a Python script to extract and display all details from these files.

## Files

- `FinalList_Ward_2.pdf` - Election list for Ward 2 (32 pages)
- `FinalList_Ward_3.pdf` - Election list for Ward 3 (31 pages)
- `list_details.py` - Python script to extract and display all details from both PDF files

## Usage

To list all details from both election list files, run:

```bash
python3 list_details.py
```

### Requirements

The script requires Python 3 and the PyPDF2 library. Install the dependency with:

```bash
pip install PyPDF2
```

### Output

The script will display:
- Complete text content from all pages of both PDF files
- Clear section headers indicating which file is being displayed
- Page numbers for each page of content

You can save the output to a file:

```bash
python3 list_details.py > election_details.txt
```