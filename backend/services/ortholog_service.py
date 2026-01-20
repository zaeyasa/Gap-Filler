"""
Ortholog Service - Phase D & E
Provides ortholog confidence and sequence identity using Ensembl REST API
"""
import requests
from typing import Dict, Optional
from functools import lru_cache


class OrthologService:
    """Service for fetching ortholog information from Ensembl"""
    
    def __init__(self):
        self.ensembl_url = "https://rest.ensembl.org"
        self.plants_url = "https://rest.ensembl.plants.org"  # For plant species
        
        # Map common species names to Ensembl species names
        self.species_map = {
            "Arabidopsis thaliana": "arabidopsis_thaliana",
            "Oryza sativa": "oryza_sativa",
            "Zea mays": "zea_mays",
            "Triticum aestivum": "triticum_aestivum",
            "Glycine max": "glycine_max",
            "Solanum lycopersicum": "solanum_lycopersicum",
            "Solanum tuberosum": "solanum_tuberosum",
            "Brassica napus": "brassica_napus",
            "Vitis vinifera": "vitis_vinifera",
            "Medicago truncatula": "medicago_truncatula",
            "Sorghum bicolor": "sorghum_bicolor",
            "Hordeum vulgare": "hordeum_vulgare",
            "Brachypodium distachyon": "brachypodium_distachyon",
            "Physcomitrella patens": "physcomitrella_patens",
            "Populus trichocarpa": "populus_trichocarpa",
            "Setaria italica": "setaria_italica",
            "Beta vulgaris": "beta_vulgaris",
            "Cucumis sativus": "cucumis_sativus",
            "Gossypium raimondii": "gossypium_raimondii",
            "Nicotiana tabacum": "nicotiana_tabacum",
        }
    
    def _get_ensembl_species(self, species_name: str) -> str:
        """Convert common species name to Ensembl format"""
        if species_name in self.species_map:
            return self.species_map[species_name]
        # Try to convert directly (lowercase, replace spaces with underscores)
        return species_name.lower().replace(" ", "_")
    
    def get_ortholog_info(self, gene: str, source_species: str, 
                          target_species: str) -> Dict:
        """
        Get ortholog information between source and target species.
        
        Args:
            gene: Gene name/symbol
            source_species: Source species (e.g., "Arabidopsis thaliana")
            target_species: Target species to check for orthologs
            
        Returns:
            Dictionary with ortholog info including confidence and sequence identity
        """
        source = self._get_ensembl_species(source_species)
        target = self._get_ensembl_species(target_species)
        
        try:
            # Try Ensembl Plants API first (for plant species)
            result = self._query_ensembl_homology(gene, source, target, use_plants=True)
            
            if not result.get("success"):
                # Fallback to main Ensembl API
                result = self._query_ensembl_homology(gene, source, target, use_plants=False)
            
            return result
            
        except Exception as e:
            print(f"Ortholog service error: {e}")
            return {
                "success": False,
                "gene": gene,
                "source_species": source_species,
                "target_species": target_species,
                "error": str(e)
            }
    
    def _query_ensembl_homology(self, gene: str, source: str, target: str,
                                 use_plants: bool = True) -> Dict:
        """Query Ensembl homology endpoint"""
        
        base_url = self.plants_url if use_plants else self.ensembl_url
        
        # First, try to get gene ID from symbol
        gene_id = self._get_gene_id(gene, source, use_plants)
        
        if not gene_id:
            return {
                "success": False,
                "error": f"Gene '{gene}' not found in {source}"
            }
        
        # Query homology endpoint
        url = f"{base_url}/homology/id/{gene_id}"
        params = {
            "target_species": target,
            "content-type": "application/json"
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Ensembl API returned {response.status_code}"
                }
            
            data = response.json()
            return self._parse_homology_response(data, gene, source, target)
            
        except requests.RequestException as e:
            return {
                "success": False,
                "error": f"API request failed: {str(e)}"
            }
    
    def _get_gene_id(self, gene: str, species: str, use_plants: bool = True) -> Optional[str]:
        """Get Ensembl gene ID from gene symbol"""
        
        base_url = self.plants_url if use_plants else self.ensembl_url
        url = f"{base_url}/xrefs/symbol/{species}/{gene}"
        params = {"content-type": "application/json"}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                # Find the gene entry
                for entry in data:
                    if entry.get("type") == "gene":
                        return entry.get("id")
                # If no gene type found, return first ID
                if data:
                    return data[0].get("id")
            
            return None
            
        except Exception as e:
            print(f"Gene ID lookup error: {e}")
            return None
    
    def _parse_homology_response(self, data: Dict, gene: str, 
                                  source: str, target: str) -> Dict:
        """Parse Ensembl homology response"""
        
        homologies = data.get("data", [])
        
        if not homologies:
            return {
                "success": True,
                "gene": gene,
                "source_species": source,
                "target_species": target,
                "ortholog_found": False,
                "message": "No ortholog data available"
            }
        
        # Get homology entries
        all_homologies = []
        for entry in homologies:
            for homology in entry.get("homologies", []):
                all_homologies.append(homology)
        
        if not all_homologies:
            return {
                "success": True,
                "gene": gene,
                "source_species": source,
                "target_species": target,
                "ortholog_found": False,
                "message": "No orthologs found in target species"
            }
        
        # Parse the best ortholog (prioritize one2one)
        best_ortholog = None
        for h in all_homologies:
            orth_type = h.get("type", "")
            if "ortholog_one2one" in orth_type:
                best_ortholog = h
                break
            elif "ortholog" in orth_type and not best_ortholog:
                best_ortholog = h
        
        if not best_ortholog:
            best_ortholog = all_homologies[0]
        
        # Extract target info
        target_info = best_ortholog.get("target", {})
        
        # Calculate confidence based on identity and type
        identity = target_info.get("perc_id", 0)
        orth_type = best_ortholog.get("type", "unknown")
        confidence = self._calculate_confidence(identity, orth_type)
        
        return {
            "success": True,
            "gene": gene,
            "source_species": source,
            "target_species": target,
            "ortholog_found": True,
            "ortholog": {
                "target_gene": target_info.get("id", ""),
                "target_symbol": target_info.get("protein_id", target_info.get("id", "")),
                "sequence_identity": round(identity, 1),
                "query_coverage": round(target_info.get("perc_pos", identity), 1),
                "ortholog_type": self._format_ortholog_type(orth_type),
                "confidence": confidence,
                "confidence_score": self._confidence_to_score(confidence),
                "ensembl_url": f"https://plants.ensembl.org/{target}/Gene/Summary?g={target_info.get('id', '')}"
            },
            "total_orthologs": len(all_homologies)
        }
    
    def _calculate_confidence(self, identity: float, orth_type: str) -> str:
        """Calculate confidence level based on identity and ortholog type"""
        
        # Weight: one2one is best, then one2many, then many2many
        type_bonus = 0
        if "one2one" in orth_type:
            type_bonus = 15
        elif "one2many" in orth_type:
            type_bonus = 5
        
        score = identity + type_bonus
        
        if score >= 80:
            return "high"
        elif score >= 50:
            return "medium"
        else:
            return "low"
    
    def _confidence_to_score(self, confidence: str) -> int:
        """Convert confidence level to numeric score"""
        return {"high": 95, "medium": 70, "low": 40}.get(confidence, 50)
    
    def _format_ortholog_type(self, orth_type: str) -> str:
        """Format ortholog type for display"""
        type_map = {
            "ortholog_one2one": "1:1",
            "ortholog_one2many": "1:many",
            "ortholog_many2many": "many:many",
            "within_species_paralog": "paralog",
        }
        
        for key, val in type_map.items():
            if key in orth_type:
                return val
        
        return orth_type.replace("_", " ").title()


# Singleton instance
ortholog_service = OrthologService()
