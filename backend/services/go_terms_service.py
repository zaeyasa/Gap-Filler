"""
Gene Ontology (GO) Terms Service
Fetches GO annotations for genes using QuickGO and UniProt APIs
"""
import requests
from typing import List, Dict, Optional
from functools import lru_cache


class GOTermsService:
    """Service for fetching Gene Ontology terms and pathway information"""
    
    def __init__(self):
        self.quickgo_base = "https://www.ebi.ac.uk/QuickGO/services"
        self.uniprot_base = "https://rest.uniprot.org/uniprotkb"
        
    @lru_cache(maxsize=100)
    def get_gene_go_terms(self, gene_name: str, species: str = None) -> Dict:
        """
        Get GO terms for a gene.
        
        Args:
            gene_name: Gene name or symbol
            species: Optional species name to filter results
            
        Returns:
            Dictionary with GO terms organized by category
        """
        result = {
            "gene": gene_name,
            "molecular_function": [],
            "biological_process": [],
            "cellular_component": [],
            "pathways": [],
            "description": "",
            "success": False
        }
        
        try:
            # Try UniProt first for comprehensive data
            uniprot_data = self._fetch_uniprot_data(gene_name, species)
            
            if uniprot_data:
                result.update(uniprot_data)
                result["success"] = True
            else:
                # Fallback to QuickGO search
                quickgo_data = self._fetch_quickgo_annotations(gene_name)
                if quickgo_data:
                    result.update(quickgo_data)
                    result["success"] = True
                    
        except Exception as e:
            result["error"] = str(e)
            
        return result
    
    def _fetch_uniprot_data(self, gene_name: str, species: str = None) -> Optional[Dict]:
        """Fetch gene data from UniProt with multiple search strategies"""
        
        # Map common species to taxonomy
        species_tax = {
            "Arabidopsis thaliana": "3702",
            "Oryza sativa": "4530",
            "Triticum aestivum": "4565",
            "Zea mays": "4577",
            "Glycine max": "3847",
            "Solanum lycopersicum": "4081",
            "Hordeum vulgare": "4513",
            "Brassica napus": "3708"
        }
        
        tax_filter = ""
        if species:
            tax_id = species_tax.get(species)
            if tax_id:
                tax_filter = f' AND organism_id:{tax_id}'
        
        # Try multiple query formats
        query_formats = [
            f'gene:{gene_name}{tax_filter}',  # Exact gene name
            f'gene_exact:{gene_name}{tax_filter}',  # Exact match
            f'({gene_name}){tax_filter}',  # Full text search
            f'protein_name:{gene_name}{tax_filter}',  # Try protein name
        ]
        
        # For multi-word gene names, also try without species filter
        if ' ' in gene_name or '-' in gene_name:
            clean_name = gene_name.replace(' ', '').replace('-', '')
            query_formats.append(f'gene:{clean_name}')
            query_formats.append(f'({gene_name})')  # Full text without species
        
        for query in query_formats:
            try:
                response = requests.get(
                    f"{self.uniprot_base}/search",
                    params={
                        "query": query,
                        "format": "json",
                        "fields": "accession,gene_names,protein_name,go_f,go_p,go_c,cc_pathway",
                        "size": 1
                    },
                    timeout=10
                )
                
                if response.status_code != 200:
                    continue
                    
                data = response.json()
                
                if not data.get("results"):
                    continue
                    
                entry = data["results"][0]
                
                # Parse GO terms
                result = {
                    "uniprot_id": entry.get("primaryAccession", ""),
                    "description": "",
                    "molecular_function": [],
                    "biological_process": [],
                    "cellular_component": [],
                    "source": "UniProt"
                }
                
                # Get protein name
                protein_name = entry.get("proteinDescription", {})
                if protein_name.get("recommendedName"):
                    result["description"] = protein_name["recommendedName"].get("fullName", {}).get("value", "")
                elif protein_name.get("submittedName"):
                    # Try submitted name as fallback
                    names = protein_name.get("submittedName", [])
                    if names:
                        result["description"] = names[0].get("fullName", {}).get("value", "")
                
                # Parse GO annotations - using correct field names
                # GO terms come in different field formats
                go_fields = ['goTerms', 'go_f', 'go_p', 'go_c']
                
                for field in go_fields:
                    for go_entry in entry.get(field, []):
                        if isinstance(go_entry, dict):
                            go_term = {
                                "id": go_entry.get("id", go_entry.get("goId", "")),
                                "name": go_entry.get("term", go_entry.get("goName", ""))
                            }
                            aspect = go_entry.get("aspect", "").lower()
                            if not aspect:
                                # Determine from field name
                                if field == "go_f":
                                    aspect = "molecular_function"
                                elif field == "go_p":
                                    aspect = "biological_process"
                                elif field == "go_c":
                                    aspect = "cellular_component"
                            
                            if "molecular" in aspect or "function" in aspect:
                                if go_term not in result["molecular_function"]:
                                    result["molecular_function"].append(go_term)
                            elif "process" in aspect or "biological" in aspect:
                                if go_term not in result["biological_process"]:
                                    result["biological_process"].append(go_term)
                            elif "component" in aspect or "cellular" in aspect:
                                if go_term not in result["cellular_component"]:
                                    result["cellular_component"].append(go_term)
                
                # Parse pathways from comments
                pathways = []
                for comment in entry.get("comments", []):
                    if comment.get("commentType") == "PATHWAY":
                        for pathway in comment.get("texts", []):
                            pathways.append(pathway.get("value", ""))
                result["pathways"] = pathways
                
                # Only return if we found some useful data
                if result["description"] or result["molecular_function"] or result["biological_process"] or result["cellular_component"]:
                    print(f"Found GO data for {gene_name} using query: {query}")
                    return result
                    
            except Exception as e:
                print(f"UniProt query failed ({query}): {e}")
                continue
        
        print(f"No UniProt data found for {gene_name}")
        return None
    
    def _fetch_quickgo_annotations(self, gene_name: str) -> Optional[Dict]:
        """Fetch GO annotations from QuickGO as fallback"""
        try:
            response = requests.get(
                f"{self.quickgo_base}/annotation/search",
                params={
                    "geneProductId": gene_name,
                    "limit": 50
                },
                headers={"Accept": "application/json"},
                timeout=15
            )
            
            if response.status_code != 200:
                return None
                
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                return None
            
            result = {
                "molecular_function": [],
                "biological_process": [],
                "cellular_component": []
            }
            
            seen = set()
            for annotation in results:
                go_id = annotation.get("goId", "")
                go_name = annotation.get("goName", "")
                aspect = annotation.get("goAspect", "")
                
                if go_id in seen:
                    continue
                seen.add(go_id)
                
                go_term = {"id": go_id, "name": go_name}
                
                if aspect == "molecular_function":
                    result["molecular_function"].append(go_term)
                elif aspect == "biological_process":
                    result["biological_process"].append(go_term)
                elif aspect == "cellular_component":
                    result["cellular_component"].append(go_term)
            
            return result
            
        except Exception as e:
            print(f"QuickGO fetch error: {e}")
            return None
    
    def get_batch_go_terms(self, genes: List[str], species: str = None) -> Dict[str, Dict]:
        """
        Get GO terms for multiple genes.
        
        Args:
            genes: List of gene names
            species: Optional species to filter
            
        Returns:
            Dictionary mapping gene names to their GO terms
        """
        results = {}
        for gene in genes:
            results[gene] = self.get_gene_go_terms(gene, species)
        return results


# Singleton instance
go_terms_service = GOTermsService()
