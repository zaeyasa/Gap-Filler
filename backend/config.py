"""
GAP Filler Backend Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

def _get_ollama_host():
    """Get Ollama host, ensuring proper URL format"""
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    
    # Handle edge cases
    if not host.startswith("http"):
        # If just an IP (e.g., "0.0.0.0"), treat as localhost for client connections
        if host in ("0.0.0.0", "127.0.0.1"):
            host = "http://localhost:11434"
        else:
            host = f"http://{host}:11434"
    
    # Convert 0.0.0.0 in URL to localhost (0.0.0.0 is for binding, not connecting)
    if "0.0.0.0" in host:
        host = host.replace("0.0.0.0", "localhost")
    
    return host

class Config:
    """Application configuration"""
    
    # Flask settings
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", 5000))
    
    # Ollama settings
    OLLAMA_HOST = _get_ollama_host()
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "Qwen3-30B-A3B-Thinking-2507-Deepseek-v3.1-Distill:4b")
    
    # NCBI PubMed settings
    NCBI_EMAIL = os.getenv("NCBI_EMAIL", "")  # Optional but recommended
    NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")  # Optional for higher rate limits
    PUBMED_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    # OrthoDB settings (broader species coverage)
    ORTHODB_BASE_URL = "https://data.orthodb.org/v12"
    
    # Rate limiting
    PUBMED_REQUESTS_PER_SECOND = 3  # Without API key
    ORTHODB_REQUESTS_PER_SECOND = 5
