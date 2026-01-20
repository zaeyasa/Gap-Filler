"""
OrthoDB Service
Fetches ortholog data for gene comparisons across plant species
OrthoDB has broader species coverage than Ensembl Plants
"""
import requests
import time
from typing import List, Dict, Optional, Set
from config import Config


class OrthoDBService:
    """Service for interacting with OrthoDB API for ortholog data"""
    
    def __init__(self):
        self.base_url = Config.ORTHODB_BASE_URL
        self.last_request_time = 0
        self.min_interval = 1.0 / Config.ORTHODB_REQUESTS_PER_SECOND
        
        # Plant taxon IDs in OrthoDB (Viridiplantae)
        self.plant_taxon_id = "33090"  # Viridiplantae (green plants)
        
        # Common plant species with their NCBI taxonomy IDs
        self.plant_species = {
            "Arabidopsis thaliana": {"taxid": "3702", "common": "Thale cress"},
            "Triticum aestivum": {"taxid": "4565", "common": "Bread wheat"},
            "Oryza sativa": {"taxid": "4530", "common": "Rice"},
            "Zea mays": {"taxid": "4577", "common": "Maize"},
            "Glycine max": {"taxid": "3847", "common": "Soybean"},
            "Solanum lycopersicum": {"taxid": "4081", "common": "Tomato"},
            "Solanum tuberosum": {"taxid": "4113", "common": "Potato"},
            "Vitis vinifera": {"taxid": "29760", "common": "Grape"},
            "Brassica napus": {"taxid": "3708", "common": "Rapeseed"},
            "Brassica rapa": {"taxid": "3711", "common": "Chinese cabbage"},
            "Medicago truncatula": {"taxid": "3880", "common": "Barrel medic"},
            "Populus trichocarpa": {"taxid": "3694", "common": "Black cottonwood"},
            "Sorghum bicolor": {"taxid": "4558", "common": "Sorghum"},
            "Hordeum vulgare": {"taxid": "4513", "common": "Barley"},
            "Nicotiana tabacum": {"taxid": "4097", "common": "Tobacco"},
            "Phaseolus vulgaris": {"taxid": "3885", "common": "Common bean"},
            "Cucumis sativus": {"taxid": "3659", "common": "Cucumber"},
            "Capsicum annuum": {"taxid": "4072", "common": "Pepper"},
            "Helianthus annuus": {"taxid": "4232", "common": "Sunflower"},
            "Beta vulgaris": {"taxid": "161934", "common": "Sugar beet"},
        }
    
    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()
    
    def get_available_species(self) -> List[Dict]:
        """Get list of available plant species"""
        return [
            {
                "scientific_name": name,
                "taxid": info["taxid"],
                "common_name": info["common"]
            }
            for name, info in self.plant_species.items()
        ]
    
    def search_gene(self, gene_name: str, species_taxid: Optional[str] = None) -> List[Dict]:
        """
        Search for a gene in OrthoDB.
        Returns list of matching ortholog groups.
        """
        self._rate_limit()
        
        params = {
            "query": gene_name,
            "level": self.plant_taxon_id,  # Search within plants
            "species": species_taxid if species_taxid else "",
            "universal": "0.5",  # Present in at least 50% of species
        }
        
        # Remove empty params
        params = {k: v for k, v in params.items() if v}
        
        try:
            response = requests.get(
                f"{self.base_url}/search",
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            else:
                print(f"OrthoDB search returned status {response.status_code}")
                return []
        
        except requests.RequestException as e:
            print(f"OrthoDB search error: {e}")
            return []
    
    def get_ortholog_group(self, group_id: str) -> Optional[Dict]:
        """
        Get detailed information about an ortholog group.
        """
        self._rate_limit()
        
        try:
            response = requests.get(
                f"{self.base_url}/group",
                params={"id": group_id},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("data", {})
            return None
        
        except requests.RequestException as e:
            print(f"OrthoDB group fetch error: {e}")
            return None
    
    def get_species_in_group(self, group_id: str) -> Set[str]:
        """
        Get set of species (taxids) that have genes in this ortholog group.
        """
        group_data = self.get_ortholog_group(group_id)
        
        if not group_data:
            return set()
        
        species_set = set()
        
        # Extract species from group members
        for gene in group_data.get("genes", []):
            taxid = gene.get("organism", {}).get("id")
            if taxid:
                species_set.add(str(taxid))
        
        return species_set
    
    def find_gaps(self, gene_name: str, source_species: str, target_species: List[str]) -> Dict:
        """
        Find gaps: genes present in source species but missing in target species.
        
        Args:
            gene_name: Gene name to search for
            source_species: Name of source species (e.g., "Arabidopsis thaliana")
            target_species: List of target species names to check
        
        Returns:
            Dictionary with gap analysis results
        """
        result = {
            "gene_name": gene_name,
            "source_species": source_species,
            "gaps": [],
            "present_in": [],
            "ortholog_groups": []
        }
        
        # Get source species taxid
        source_info = self.plant_species.get(source_species)
        if not source_info:
            result["error"] = f"Unknown species: {source_species}"
            return result
        
        # Search for the gene
        groups = self.search_gene(gene_name, source_info["taxid"])
        
        if not groups:
            result["error"] = f"Gene '{gene_name}' not found in OrthoDB"
            return result
        
        # Check each ortholog group
        for group in groups[:3]:  # Limit to top 3 groups
            group_id = group.get("id", "")
            if not group_id:
                continue
            
            result["ortholog_groups"].append({
                "id": group_id,
                "name": group.get("name", ""),
                "description": group.get("description", "")
            })
            
            # Get species in this group
            species_in_group = self.get_species_in_group(group_id)
            
            # Check each target species
            for target in target_species:
                target_info = self.plant_species.get(target)
                if not target_info:
                    continue
                
                target_taxid = target_info["taxid"]
                
                if target_taxid in species_in_group:
                    if target not in result["present_in"]:
                        result["present_in"].append(target)
                else:
                    if target not in [g["species"] for g in result["gaps"]]:
                        result["gaps"].append({
                            "species": target,
                            "common_name": target_info["common"],
                            "taxid": target_taxid,
                            "ortholog_group": group_id
                        })
        
        return result
    
    def batch_find_gaps(self, genes: List[str], source_species: str, 
                        target_species: List[str]) -> List[Dict]:
        """
        Find gaps for multiple genes.
        """
        results = []
        for gene in genes:
            gap_result = self.find_gaps(gene, source_species, target_species)
            results.append(gap_result)
        return results


# Singleton instance
orthodb_service = OrthoDBService()
