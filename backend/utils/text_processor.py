"""
Text Processing Utilities
"""
import re
from typing import List


def clean_text(text: str) -> str:
    """Clean and normalize text"""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove HTML tags if any
    text = re.sub(r'<[^>]+>', '', text)
    
    return text.strip()


def truncate_text(text: str, max_length: int = 5000) -> str:
    """Truncate text to maximum length while preserving word boundaries"""
    if len(text) <= max_length:
        return text
    
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    
    if last_space > max_length * 0.8:
        truncated = truncated[:last_space]
    
    return truncated + "..."


def extract_gene_patterns(text: str) -> List[str]:
    """
    Extract potential gene names/symbols using patterns.
    Useful as a fallback when LLM is not available.
    """
    patterns = [
        # Arabidopsis gene IDs (e.g., AT1G01010)
        r'\bAT[1-5MC]G\d{5}\b',
        # Gene symbols in uppercase (e.g., FLC, TFL1)
        r'\b[A-Z]{2,}[0-9]*\b',
        # Gene names with numbers (e.g., WRKY12)
        r'\b[A-Z][A-Za-z]+\d+[A-Za-z]*\b',
    ]
    
    genes = set()
    for pattern in patterns:
        matches = re.findall(pattern, text)
        genes.update(matches)
    
    # Filter out common false positives
    false_positives = {'DNA', 'RNA', 'PCR', 'GWAS', 'SNP', 'QTL', 'USA', 'THE', 'AND', 'FOR'}
    genes = genes - false_positives
    
    return list(genes)


def normalize_species_name(name: str) -> str:
    """Normalize species name to standard format"""
    name = name.strip()
    
    # Capitalize first letter of genus, lowercase rest
    parts = name.split()
    if len(parts) >= 2:
        genus = parts[0].capitalize()
        species = parts[1].lower()
        subspecies = ' '.join(parts[2:]).lower() if len(parts) > 2 else ''
        
        normalized = f"{genus} {species}"
        if subspecies:
            normalized += f" {subspecies}"
        return normalized
    
    return name.capitalize()
