"""Configuration settings for the HR Automation System."""
import os
from dotenv import load_dotenv

load_dotenv()

# Groq Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = "llama-3.1-8b-instant"

# Vector Store Configuration
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
VECTOR_STORE_PATH = "faiss_index"

# Agent Configuration
TEMPERATURE = 0.0
MAX_TOKENS = 512

