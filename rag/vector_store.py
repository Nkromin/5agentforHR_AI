"""Initialize and manage FAISS vector store with clean rebuild."""
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from rag.loader import load_hr_policies, validate_policies
from typing import List, Optional
import config
import os
import shutil


def clean_rebuild_index() -> None:
    """
    Force clean deletion of existing FAISS index.
    This ensures no contamination from old data.
    """
    if os.path.exists(config.VECTOR_STORE_PATH):
        print(f"[VECTOR STORE] Deleting existing index: {config.VECTOR_STORE_PATH}")
        shutil.rmtree(config.VECTOR_STORE_PATH)
        print("[VECTOR STORE] Existing index deleted successfully")
    else:
        print("[VECTOR STORE] No existing index found")


def create_chunks(documents: List[Document]) -> List[Document]:
    """
    Split documents into chunks with proper overlap and metadata.

    Args:
        documents: List of Document objects

    Returns:
        List of chunked Document objects with metadata
    """
    print("\n[CHUNKING] Creating document chunks...")

    # Use RecursiveCharacterTextSplitter as specified
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        length_function=len,
        separators=["\n\nSection", "\n\n", "\n", ". ", " "]
    )

    all_chunks = []

    for doc in documents:
        # Get document metadata
        source = doc.metadata.get("source", "unknown")
        title = doc.metadata.get("title", "Unknown Policy")

        # Split the document
        chunks = text_splitter.split_documents([doc])

        print(f"[CHUNKING] {source}: {len(chunks)} chunks")

        for i, chunk in enumerate(chunks):
            # Prepend policy name to each chunk for better retrieval
            if not chunk.page_content.startswith(title):
                chunk.page_content = f"[{title}]\n{chunk.page_content}"

            # Add chunk metadata
            chunk.metadata["chunk_index"] = i
            chunk.metadata["total_chunks"] = len(chunks)
            chunk.metadata["chunk_chars"] = len(chunk.page_content)

            all_chunks.append(chunk)

    print(f"[CHUNKING] Total chunks created: {len(all_chunks)}")
    return all_chunks


def initialize_vector_store(force_rebuild: bool = True):
    """
    Initialize FAISS vector store with clean rebuild.

    This function:
    1. ALWAYS deletes existing index when force_rebuild=True
    2. Loads documents ONLY from /docs folder
    3. Applies proper text cleaning
    4. Creates chunks with metadata
    5. Builds fresh FAISS index

    Args:
        force_rebuild: If True (default), delete and rebuild index

    Returns:
        FAISS vector store instance
    """
    print("\n" + "="*70)
    print("[VECTOR STORE] INITIALIZING FAISS INDEX")
    print("="*70)

    # Step 1: Validate policy documents exist
    print("\n[VECTOR STORE] Step 1: Validating policy documents...")
    validation = validate_policies()
    if not validation["valid"]:
        print(f"[VECTOR STORE] ERROR: {validation['errors']}")
        raise FileNotFoundError(f"Missing required policy documents: {validation['errors']}")

    for doc_info in validation["documents"]:
        status = "✅" if doc_info["exists"] else "❌"
        print(f"[VECTOR STORE]   {status} {doc_info['file']}")

    # Step 2: Force clean rebuild
    print("\n[VECTOR STORE] Step 2: Cleaning existing index...")
    if force_rebuild:
        clean_rebuild_index()
    elif os.path.exists(config.VECTOR_STORE_PATH):
        print("[VECTOR STORE] Loading existing index (force_rebuild=False)...")
        try:
            embeddings = HuggingFaceEmbeddings(
                model_name=config.EMBEDDING_MODEL,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            vector_store = FAISS.load_local(
                config.VECTOR_STORE_PATH,
                embeddings,
                allow_dangerous_deserialization=True
            )
            print("[VECTOR STORE] Loaded existing index successfully")
            return vector_store
        except Exception as e:
            print(f"[VECTOR STORE] Error loading index: {e}")
            print("[VECTOR STORE] Will rebuild...")
            clean_rebuild_index()

    # Step 3: Load documents from /docs folder
    print("\n[VECTOR STORE] Step 3: Loading documents from /docs folder...")
    documents = load_hr_policies()

    if not documents:
        raise ValueError("No documents loaded from /docs folder")

    print(f"[VECTOR STORE] Loaded {len(documents)} documents:")
    for doc in documents:
        print(f"[VECTOR STORE]   - {doc.metadata.get('source')}: {doc.metadata.get('char_count', len(doc.page_content))} chars")

    # Step 4: Create chunks
    print("\n[VECTOR STORE] Step 4: Creating chunks...")
    chunks = create_chunks(documents)

    # Step 5: Initialize embeddings
    print("\n[VECTOR STORE] Step 5: Initializing embeddings...")
    embeddings = HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL,
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    print(f"[VECTOR STORE] Using model: {config.EMBEDDING_MODEL}")

    # Step 6: Create FAISS index
    print("\n[VECTOR STORE] Step 6: Creating FAISS index...")
    vector_store = FAISS.from_documents(chunks, embeddings)

    # Step 7: Save index
    print("\n[VECTOR STORE] Step 7: Saving index...")
    vector_store.save_local(config.VECTOR_STORE_PATH)
    print(f"[VECTOR STORE] Index saved to: {config.VECTOR_STORE_PATH}")

    print("\n" + "="*70)
    print("[VECTOR STORE] INITIALIZATION COMPLETE")
    print(f"[VECTOR STORE] Documents: {len(documents)}")
    print(f"[VECTOR STORE] Chunks: {len(chunks)}")
    print("="*70 + "\n")

    return vector_store


def search_with_debug(vector_store, query: str, k: int = 5) -> List[Document]:
    """
    Search vector store with debug logging.

    Args:
        vector_store: FAISS vector store
        query: Search query
        k: Number of results to return

    Returns:
        List of retrieved documents
    """
    print(f"\n[RETRIEVAL DEBUG] Query: {query}")
    print(f"[RETRIEVAL DEBUG] Retrieving top {k} chunks...")

    docs = vector_store.similarity_search(query, k=k)

    print(f"[RETRIEVAL DEBUG] Retrieved {len(docs)} chunks:")
    for i, doc in enumerate(docs):
        source = doc.metadata.get("source", "unknown")
        chunk_idx = doc.metadata.get("chunk_index", "?")
        snippet = doc.page_content[:200].replace('\n', ' ')
        print(f"[RETRIEVAL DEBUG]   {i+1}. {source} (chunk {chunk_idx})")
        print(f"[RETRIEVAL DEBUG]      \"{snippet}...\"")

    return docs


def test_retrieval():
    """
    Test retrieval with specific queries to validate index accuracy.
    """
    print("\n" + "="*70)
    print("[TEST] RETRIEVAL VALIDATION")
    print("="*70)

    # Initialize vector store
    vector_store = initialize_vector_store(force_rebuild=True)

    # Test queries
    test_queries = [
        ("Maternity leave duration", "26 weeks"),
        ("Sick leave entitlement", "12 sick leave days"),
        ("International meal allowance", "₹2500"),
        ("Public WiFi rule", "Do not use public WiFi"),
        ("Remote work eligibility", "6 months probation"),
        ("Disciplinary action", "First offense"),
        ("Password length", "14 characters"),
        ("Hotel reimbursement domestic", "₹8000"),
    ]

    results = []

    for query, expected in test_queries:
        print(f"\n--- Testing: {query} ---")
        print(f"Expected to find: '{expected}'")

        docs = search_with_debug(vector_store, query, k=3)

        # Check if expected content is in retrieved docs
        found = False
        for doc in docs:
            if expected.lower() in doc.page_content.lower():
                found = True
                break

        status = "✅ PASS" if found else "❌ FAIL"
        print(f"Result: {status}")
        results.append((query, expected, found))

    # Summary
    print("\n" + "="*70)
    print("[TEST] SUMMARY")
    print("="*70)
    passed = sum(1 for _, _, found in results if found)
    print(f"Passed: {passed}/{len(results)}")
    for query, expected, found in results:
        status = "✅" if found else "❌"
        print(f"  {status} {query}")

    return results


if __name__ == "__main__":
    # Run test when executed directly
    test_retrieval()


