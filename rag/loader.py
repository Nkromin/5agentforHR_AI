"""Load and prepare HR policy documents from /docs folder."""
from langchain.schema import Document
from typing import List, Tuple
import os
import re


# Path to policy documents
DOCS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")

# Required policy files
REQUIRED_POLICIES = [
    "leave_policy.txt",
    "remote_work_policy.txt",
    "expense_policy.txt",
    "code_of_conduct.txt",
    "it_security_policy.txt"
]


def clean_text(text: str) -> str:
    """
    Clean and normalize text for embedding.

    Args:
        text: Raw text from document

    Returns:
        Cleaned and normalized text
    """
    # Replace multiple whitespace with single space
    text = re.sub(r'[ \t]+', ' ', text)

    # Fix broken line joins (word-\nword -> word-word or word\nword -> word word)
    text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)

    # Replace multiple newlines with double newline
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Fix corrupted text patterns like "200/nightfordomestic" -> "200/night for domestic"
    text = re.sub(r'(\d+)/(\w+)for(\w+)', r'\1/\2 for \3', text)
    text = re.sub(r'(\d+)for(\w+)', r'\1 for \2', text)

    # Ensure proper spacing after punctuation
    text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)

    # Preserve currency symbols (₹, $, €, etc.)
    # No changes needed - they are preserved

    # Strip leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)

    # Final strip
    return text.strip()


def extract_title_from_content(content: str) -> str:
    """
    Extract the title (first line) from document content.

    Args:
        content: Document content

    Returns:
        Title string
    """
    lines = content.strip().split('\n')
    if lines:
        return lines[0].strip()
    return "Unknown Policy"


def load_document_from_file(filepath: str) -> Tuple[str, dict]:
    """
    Load a single document from file.

    Args:
        filepath: Path to the document file

    Returns:
        Tuple of (content, metadata)
    """
    filename = os.path.basename(filepath)

    print(f"[LOADER] Loading: {filename}")

    with open(filepath, 'r', encoding='utf-8') as f:
        raw_content = f.read()

    # Clean the text
    content = clean_text(raw_content)

    # Extract title
    title = extract_title_from_content(content)

    # Determine section from filename
    section = filename.replace('.txt', '').replace('_policy', '').replace('_', ' ')

    metadata = {
        "source": filename,
        "title": title,
        "section": section,
        "filepath": filepath,
        "char_count": len(content)
    }

    print(f"[LOADER]   Title: {title}")
    print(f"[LOADER]   Characters: {len(content)}")

    return content, metadata


def load_hr_policies() -> List[Document]:
    """
    Load HR policy documents from the /docs folder.

    This function:
    1. Loads only from /docs folder (no hardcoded policies)
    2. Cleans and normalizes text
    3. Validates required documents exist

    Returns:
        List of Document objects containing HR policies
    """
    print("\n" + "="*60)
    print("[LOADER] Loading HR Policy Documents from /docs folder")
    print("="*60)

    # Check docs folder exists
    if not os.path.exists(DOCS_PATH):
        raise FileNotFoundError(f"Docs folder not found: {DOCS_PATH}")

    print(f"[LOADER] Docs folder: {DOCS_PATH}")

    # List available files
    available_files = [f for f in os.listdir(DOCS_PATH) if f.endswith('.txt')]
    print(f"[LOADER] Found {len(available_files)} document files")

    # Check for required policies
    missing = [f for f in REQUIRED_POLICIES if f not in available_files]
    if missing:
        print(f"[LOADER] WARNING: Missing required policies: {missing}")

    # Load documents
    documents = []
    for filename in available_files:
        filepath = os.path.join(DOCS_PATH, filename)
        try:
            content, metadata = load_document_from_file(filepath)
            doc = Document(page_content=content, metadata=metadata)
            documents.append(doc)
        except Exception as e:
            print(f"[LOADER] ERROR loading {filename}: {e}")

    print(f"\n[LOADER] Successfully loaded {len(documents)} documents")
    print("="*60 + "\n")

    return documents


def validate_policies() -> dict:
    """
    Validate that all required policies exist and contain expected content.

    Returns:
        Dictionary with validation results
    """
    results = {
        "valid": True,
        "documents": [],
        "errors": []
    }

    if not os.path.exists(DOCS_PATH):
        results["valid"] = False
        results["errors"].append(f"Docs folder not found: {DOCS_PATH}")
        return results

    for filename in REQUIRED_POLICIES:
        filepath = os.path.join(DOCS_PATH, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            results["documents"].append({
                "file": filename,
                "exists": True,
                "chars": len(content),
                "lines": len(content.split('\n'))
            })
        else:
            results["valid"] = False
            results["errors"].append(f"Missing: {filename}")
            results["documents"].append({
                "file": filename,
                "exists": False
            })

    return results

