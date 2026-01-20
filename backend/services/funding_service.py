"""
Funding Opportunity Matcher Service
Searches for active grants related to genes using NIH RePORTER API
"""
import requests
from typing import Dict, List, Optional


class FundingService:
    """Service for finding funding opportunities related to gene research"""
    
    def __init__(self):
        # NIH RePORTER API (free, no auth required)
        self.reporter_url = "https://api.reporter.nih.gov/v2/projects/search"
    
    def search_grants(self, gene: str, keywords: List[str] = None, 
                      max_results: int = 10) -> Dict:
        """
        Search for NIH grants related to a gene.
        
        Args:
            gene: Gene name to search
            keywords: Optional additional keywords
            max_results: Maximum number of grants to return
            
        Returns:
            Dictionary with matching grants
        """
        try:
            # Build search terms
            search_terms = [gene]
            if keywords:
                search_terms.extend(keywords)
            
            # Query NIH RePORTER
            payload = {
                "criteria": {
                    "advanced_text_search": {
                        "operator": "or",
                        "search_field": "all",
                        "search_text": " OR ".join(search_terms)
                    },
                    "is_active": True  # Only active grants
                },
                "include_fields": [
                    "project_title", "contact_pi_name", "organization",
                    "award_amount", "project_start_date", "project_end_date",
                    "abstract_text", "terms", "project_num"
                ],
                "offset": 0,
                "limit": max_results,
                "sort_field": "award_amount",
                "sort_order": "desc"
            }
            
            response = requests.post(
                self.reporter_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "gene": gene,
                    "error": f"NIH API returned status {response.status_code}",
                    "grants": []
                }
            
            data = response.json()
            results = data.get("results", [])
            
            # Parse results
            grants = []
            for project in results:
                # NIH API uses various field names - try multiple
                project_num = (project.get("project_num") or 
                               project.get("projectNum") or 
                               project.get("core_project_num") or "")
                
                title = (project.get("project_title") or 
                         project.get("projectTitle") or 
                         project.get("title") or "Untitled")
                
                pi_name = (project.get("contact_pi_name") or 
                           project.get("contactPiName") or
                           project.get("pi_name") or "Unknown PI")
                
                # Handle organization structure
                org_data = project.get("organization") or project.get("org") or {}
                org_str = self._format_org(org_data)
                
                amount = (project.get("award_amount") or 
                          project.get("awardAmount") or 
                          project.get("total_cost") or None)
                
                grant = {
                    "title": title,
                    "pi": pi_name,
                    "org": org_str,
                    "amount": amount,
                    "start": project.get("project_start_date", "")[:10] if project.get("project_start_date") else "",
                    "end": project.get("project_end_date", "")[:10] if project.get("project_end_date") else "",
                    "project_num": project_num,
                    "link": f"https://reporter.nih.gov/project-details/{project_num}" if project_num else None
                }
                grants.append(grant)
                
            print(f"Funding search for '{gene}' found {len(grants)} grants")
            
            return {
                "success": True,
                "gene": gene,
                "total_found": data.get("meta", {}).get("total", len(grants)),
                "grants": grants
            }
            
        except requests.RequestException as e:
            return {
                "success": False,
                "gene": gene,
                "error": str(e),
                "grants": []
            }
        except Exception as e:
            return {
                "success": False,
                "gene": gene,
                "error": f"Unexpected error: {str(e)}",
                "grants": []
            }
    
    def _format_org(self, org: Dict) -> str:
        """Format organization info"""
        if not org:
            return "Unknown Organization"
        
        name = org.get("org_name", "")
        city = org.get("org_city", "")
        state = org.get("org_state", "")
        
        if city and state:
            return f"{name} ({city}, {state})"
        return name or "Unknown Organization"
    
    def search_plant_genomics_grants(self, gene: str) -> Dict:
        """
        Search for plant genomics specific grants.
        Adds relevant plant biology keywords.
        """
        plant_keywords = [
            "plant", "Arabidopsis", "crop", "agriculture",
            "genomics", "genome", "transcriptome"
        ]
        
        return self.search_grants(gene, keywords=plant_keywords)


# Singleton instance
funding_service = FundingService()
