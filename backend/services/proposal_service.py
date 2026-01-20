"""
Research Proposal Generator Service
Uses local Ollama LLM to generate research proposals based on gap analysis
"""
import ollama
from typing import Dict, Optional
from config import Config


class ProposalService:
    """Service for generating AI-powered research proposals"""
    
    def __init__(self):
        self.default_model = Config.OLLAMA_MODEL
        # Create client with proper host configuration
        self._client = ollama.Client(host=Config.OLLAMA_HOST)
    
    def generate_proposal(self, gene: str, source_species: str, 
                          target_species: str, length: str = "medium",
                          go_terms: Dict = None, priority_score: float = None,
                          model: str = None) -> Dict:
        """
        Generate a research proposal for a gene gap.
        
        Args:
            gene: Gene name
            source_species: Species where gene is studied
            target_species: Target species with research gap
            length: "short", "medium", or "full"
            go_terms: Optional GO term annotations
            priority_score: Optional priority score
            model: Optional LLM model override
            
        Returns:
            Dictionary with generated proposal
        """
        
        # Build context for LLM
        context = self._build_context(gene, source_species, target_species, 
                                       go_terms, priority_score)
        
        # Get length-specific prompt
        prompt = self._get_prompt(gene, source_species, target_species, 
                                  context, length)
        
        # System prompt to prevent thinking output
        system_prompt = """You are a plant genomics research proposal writer.
Provide ONLY the final proposal text - no thinking, no reasoning, no explanations before the proposal.
Start directly with the proposal content. Be scientific, clear, and professional."""
        
        try:
            # Generate using configured Ollama client
            model_to_use = model or self.default_model
            print(f"Generating proposal for {gene} using model: {model_to_use} on host: {Config.OLLAMA_HOST}")
            
            response = self._client.generate(
                model=model_to_use,
                prompt=prompt,
                system=system_prompt
            )
            
            if response and response.get("response"):
                proposal_text = response["response"].strip()
                
                # Filter out any thinking tags (some models still include them)
                proposal_text = self._clean_thinking_output(proposal_text)
                
                return {
                    "success": True,
                    "gene": gene,
                    "source_species": source_species,
                    "target_species": target_species,
                    "length": length,
                    "proposal": proposal_text
                }
            else:
                return {
                    "success": False,
                    "error": "LLM returned empty response"
                }
                
        except Exception as e:
            print(f"Proposal generation error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _clean_thinking_output(self, text: str) -> str:
        """Remove thinking/reasoning tags from LLM output"""
        import re
        
        # Remove <think>...</think> blocks
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove <thinking>...</thinking> blocks  
        text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove any leftover opening/closing tags
        text = re.sub(r'</?think(ing)?>', '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    def _build_context(self, gene: str, source_species: str, 
                       target_species: str, go_terms: Dict = None,
                       priority_score: float = None) -> str:
        """Build context string from available data"""
        context_parts = []
        
        if go_terms and go_terms.get("success"):
            if go_terms.get("description"):
                context_parts.append(f"Gene description: {go_terms['description']}")
            
            if go_terms.get("biological_process"):
                processes = [g["name"] for g in go_terms["biological_process"][:3]]
                context_parts.append(f"Biological processes: {', '.join(processes)}")
            
            if go_terms.get("molecular_function"):
                functions = [g["name"] for g in go_terms["molecular_function"][:3]]
                context_parts.append(f"Molecular functions: {', '.join(functions)}")
        
        if priority_score:
            context_parts.append(f"Research priority score: {priority_score} (higher = more important)")
        
        return "\n".join(context_parts) if context_parts else "No additional context available."
    
    def _get_prompt(self, gene: str, source_species: str, 
                    target_species: str, context: str, length: str) -> str:
        """Get the prompt template based on length"""
        
        base_info = f"""You are a plant genomics researcher writing a research proposal.

Gene: {gene}
Well-studied in: {source_species}
Research gap in: {target_species}

Additional context:
{context}

This is a research gap - the gene has been studied in {source_species} but NOT YET in {target_species}.
"""
        
        if length == "short":
            return base_info + """
Write a SHORT 1-paragraph proposal (3-4 sentences) that briefly explains:
1. Why this gene is important
2. Why studying it in the target species matters
3. The key hypothesis

Be concise and scientific."""

        elif length == "medium":
            return base_info + """
Write a MEDIUM research proposal with these sections:
1. **Background** (2-3 sentences): What is known about this gene
2. **Research Gap** (1-2 sentences): Why it needs to be studied in the target species
3. **Hypothesis** (1 sentence): Your main hypothesis
4. **Objectives** (3 bullet points): Specific aims

Be scientific but accessible."""

        else:  # full
            return base_info + """
Write a FULL research proposal with these sections:
1. **Background and Significance** (1 paragraph): What is known, why it matters
2. **Research Gap** (1 paragraph): Current knowledge limitations in target species
3. **Hypothesis and Objectives** (bullet points): Main hypothesis and 3-4 specific aims
4. **Methods Overview** (bullet points): Key experimental approaches
5. **Expected Outcomes and Impact** (1 paragraph): What you expect to find and its significance

Be thorough, scientific, and compelling. This should read like a real grant proposal."""

# Singleton instance
proposal_service = ProposalService()
