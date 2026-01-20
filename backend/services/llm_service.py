"""
LLM Service using Ollama
Extracts gene names, organism mentions, and summarizes gene functions
Model is configurable via settings
"""
import ollama
import json
import re
import requests
from typing import List, Dict, Optional
from config import Config


class LLMService:
    """Service for interacting with local Ollama LLM for text extraction and summarization"""
    
    def __init__(self):
        self.host = Config.OLLAMA_HOST
        self.default_model = Config.OLLAMA_MODEL
        self._client = None
    
    @property
    def client(self):
        """Lazy initialization of Ollama client"""
        if self._client is None:
            # Re-read config to ensure latest values
            host = Config.OLLAMA_HOST
            self._client = ollama.Client(host=host)
        return self._client
    
    def get_available_models(self) -> List[str]:
        """Get list of available models from Ollama"""
        # Try direct requests first (more reliable)
        try:
            response = requests.get(f"{Config.OLLAMA_HOST}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                return [m.get('model') or m.get('name', '') for m in models if m]
        except Exception as e:
            print(f"Requests fallback error: {e}")
        
        # Fallback to ollama library
        try:
            response = self.client.list()
            
            if hasattr(response, 'models'):
                models = response.models
            elif isinstance(response, dict):
                models = response.get('models', [])
            else:
                return []
            
            if not models:
                return []
            
            model_names = []
            for m in models:
                if hasattr(m, 'model'):
                    model_names.append(m.model)
                elif hasattr(m, 'name'):
                    model_names.append(m.name)
                elif isinstance(m, dict):
                    model_names.append(m.get('model') or m.get('name', str(m)))
                else:
                    model_names.append(str(m))
            
            return model_names
        except Exception as e:
            print(f"Error getting models: {e}")
            return []
    
    def set_model(self, model_name: str):
        """Change the active model"""
        self.default_model = model_name
    
    def get_current_model(self) -> str:
        """Get the currently active model"""
        return self.default_model
    
    def extract_genes_and_organisms(self, text: str, model: Optional[str] = None) -> Dict:
        """
        Extract gene names and organism mentions from scientific text.
        Uses structured JSON output for reliable parsing.
        
        Args:
            text: Scientific text (abstract, article content)
            model: Optional model override
        
        Returns:
            Dictionary with extracted genes and organisms
        """
        use_model = model or self.default_model
        
        prompt = f"""Analyze this scientific text and extract:
1. Gene names (including gene symbols like AT1G01010, gene names like FLOWERING LOCUS T)
2. Organism/species names (scientific names like Arabidopsis thaliana, Triticum aestivum)
3. Any gene functions or roles mentioned

Return ONLY a valid JSON object in this exact format (no other text):
{{
    "genes": [
        {{"name": "gene_name", "symbol": "gene_symbol_if_any", "function": "brief_function_if_mentioned"}}
    ],
    "organisms": [
        {{"scientific_name": "full_name", "common_name": "common_name_if_known"}}
    ]
}}

Scientific text to analyze:
{text}

JSON output:"""

        try:
            response = self.client.generate(
                model=use_model,
                prompt=prompt,
                options={
                    "temperature": 0.1,  # Low temperature for more deterministic output
                    "num_predict": 2000,
                }
            )
            
            response_text = response.get('response', '{}')
            
            # Parse JSON from response
            return self._parse_json_response(response_text)
        
        except Exception as e:
            print(f"LLM extraction error: {e}")
            return {"genes": [], "organisms": [], "error": str(e)}
    
    def summarize_gene_function(self, gene_name: str, context: str, 
                                 model: Optional[str] = None) -> str:
        """
        Summarize the function/role of a gene based on context.
        Useful for genetic engineering applications.
        
        Args:
            gene_name: Name of the gene
            context: Text context mentioning the gene
            model: Optional model override
        
        Returns:
            Brief summary of gene function
        """
        use_model = model or self.default_model
        
        prompt = f"""Based on this scientific context, provide a brief (2-3 sentences) summary of the gene "{gene_name}" and its potential role/function. Focus on aspects useful for genetic engineering applications.

Context:
{context}

Brief summary of {gene_name}:"""

        try:
            response = self.client.generate(
                model=use_model,
                prompt=prompt,
                options={
                    "temperature": 0.3,
                    "num_predict": 500,
                }
            )
            
            return response.get('response', '').strip()
        
        except Exception as e:
            print(f"LLM summarization error: {e}")
            return f"Error summarizing gene function: {e}"
    
    def batch_extract(self, articles: List[Dict], model: Optional[str] = None) -> List[Dict]:
        """
        Extract genes and organisms from multiple articles.
        
        Args:
            articles: List of article dicts with 'abstract' field
            model: Optional model override
        
        Returns:
            List of extraction results
        """
        results = []
        
        for article in articles:
            abstract = article.get('abstract', '')
            title = article.get('title', '')
            
            if abstract or title:
                text = f"Title: {title}\n\nAbstract: {abstract}"
                extraction = self.extract_genes_and_organisms(text, model)
                
                results.append({
                    "pmid": article.get('pmid', ''),
                    "title": title,
                    "extraction": extraction
                })
        
        return results
    
    def _parse_json_response(self, text: str) -> Dict:
        """Parse JSON from LLM response, handling potential formatting issues"""
        # Try to find JSON in the response
        text = text.strip()
        
        # Handle thinking models that output reasoning first
        # Look for JSON block after </think> tag or similar
        if '</think>' in text.lower():
            text = text.split('</think>')[-1].strip()
        
        # Try to find JSON object in the text
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Return empty structure if parsing fails
        return {"genes": [], "organisms": [], "raw_response": text}
    
    def test_connection(self) -> Dict:
        """Test connection to Ollama and return status"""
        try:
            models = self.get_available_models()
            return {
                "status": "connected",
                "available_models": models,
                "current_model": self.default_model,
                "model_available": self.default_model in models
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "current_model": self.default_model
            }


# Singleton instance
llm_service = LLMService()
