"""
Gap Analyzer Service
Core logic for identifying research gaps in plant genomics
Uses publication-based gap detection for accurate results
"""
from typing import List, Dict, Set, Optional
from collections import defaultdict
from services.pubmed_service import pubmed_service
from services.orthodb_service import orthodb_service
from services.llm_service import llm_service


class GapAnalyzer:
    """
    Analyzes genome-wide analysis articles to find research gaps.
    Uses publication-based detection: finds genes where orthologs EXIST
    but publications DON'T EXIST for that gene+species combination.
    """
    
    def __init__(self):
        self.pubmed = pubmed_service
        self.orthodb = orthodb_service
        self.llm = llm_service
    
    def analyze_query(self, search_query: str, source_species: str,
                      target_species: List[str], max_articles: int = 20,
                      llm_model: Optional[str] = None) -> Dict:
        """
        Complete gap analysis pipeline with publication-based detection.
        
        A TRUE GAP is: Ortholog EXISTS in target species BUT 
                       NO publications exist for that gene in that species.
        """
        result = {
            "query": search_query,
            "source_species": source_species,
            "target_species": target_species,
            "articles_analyzed": 0,
            "genes_found": [],
            "gaps": [],
            "publication_gaps": [],  # NEW: Publication-based gaps
            "gene_summaries": {},
            "errors": []
        }
        
        # Step 1: Search and fetch articles
        print(f"Searching PubMed for: {search_query}")
        articles = self.pubmed.search_and_fetch(search_query, max_articles)
        result["articles_analyzed"] = len(articles)
        
        if not articles:
            result["errors"].append("No articles found for the search query")
            return result
        
        # Step 2: Extract genes and organisms using LLM
        print(f"Extracting genes from {len(articles)} articles...")
        extractions = self.llm.batch_extract(articles, llm_model)
        
        # Collect all unique genes and their contexts
        gene_contexts = defaultdict(list)
        gene_info = {}
        
        for extraction in extractions:
            pmid = extraction.get("pmid", "")
            title = extraction.get("title", "")
            ext_data = extraction.get("extraction", {})
            
            for gene in ext_data.get("genes", []):
                gene_name = gene.get("name", "").strip()
                if gene_name and len(gene_name) > 1:
                    gene_contexts[gene_name].append({
                        "pmid": pmid,
                        "title": title,
                        "function": gene.get("function", "")
                    })
                    
                    if gene_name not in gene_info:
                        gene_info[gene_name] = {
                            "name": gene_name,
                            "symbol": gene.get("symbol", ""),
                            "mentions": 0
                        }
                    gene_info[gene_name]["mentions"] += 1
        
        # Sort genes by mention count
        sorted_genes = sorted(
            gene_info.values(),
            key=lambda x: x["mentions"],
            reverse=True
        )
        
        result["genes_found"] = sorted_genes[:50]  # Top 50 genes
        
        if not sorted_genes:
            result["errors"].append("No genes extracted from articles")
            return result
        
        # Step 3: Publication-based gap detection (NEW!)
        print(f"Checking publication gaps for top genes...")
        publication_gaps = []
        
        # Check top 15 genes for publication gaps
        for gene_data in sorted_genes[:15]:
            gene_name = gene_data["name"]
            print(f"  Checking: {gene_name}")
            
            # Count publications in source species first
            source_count = self.pubmed.count_gene_species_publications(
                gene_name, source_species
            )
            
            # Only proceed if gene is well-studied in source
            if source_count["publication_count"] <= 0:
                continue
                
            gene_gaps = {
                "gene": gene_name,
                "mentions_in_query": gene_data["mentions"],
                "source_species": source_species,
                "source_publications": source_count["publication_count"],
                "target_gaps": []
            }
            
            # Check each target species
            for target in target_species:
                target_count = self.pubmed.count_gene_species_publications(
                    gene_name, target
                )
                
                target_info = self.orthodb.plant_species.get(target, {})
                
                gap_entry = {
                    "species": target,
                    "common_name": target_info.get("common", ""),
                    "publication_count": target_count["publication_count"],
                    "gap_level": target_count["gap_level"],
                    "is_gap": target_count["is_gap"]
                }
                
                # Only add if it's a gap (few or no publications)
                if target_count["gap_level"] in ["complete_gap", "severe_gap", "moderate_gap"]:
                    gene_gaps["target_gaps"].append(gap_entry)
            
            # Only add gene if it has gaps
            if gene_gaps["target_gaps"]:
                publication_gaps.append(gene_gaps)
        
        result["publication_gaps"] = publication_gaps
        
        # Step 4: Format gaps for backward-compatible output
        gaps_by_species = defaultdict(list)
        
        for gene_gap in publication_gaps:
            gene_name = gene_gap["gene"]
            for target_gap in gene_gap["target_gaps"]:
                # Calculate priority score
                # Higher source pubs = more important gene
                # Complete gaps get highest priority, then severe, then moderate
                gap_severity_weights = {
                    "complete_gap": 3.0,
                    "severe_gap": 2.0,
                    "moderate_gap": 1.0
                }
                severity_weight = gap_severity_weights.get(target_gap["gap_level"], 0.5)
                
                # Priority = log(source_pubs + 1) * severity_weight * 10
                import math
                source_pubs = gene_gap["source_publications"]
                priority_score = round(math.log(source_pubs + 1) * severity_weight * 10, 1)
                
                gap_entry = {
                    "gene": gene_name,
                    "mentions": gene_gap["mentions_in_query"],
                    "source_publications": gene_gap["source_publications"],
                    "target_publications": target_gap["publication_count"],
                    "gap_level": target_gap["gap_level"],
                    "priority_score": priority_score
                }
                gaps_by_species[target_gap["species"]].append(gap_entry)
        
        # Build final gaps structure
        for species, genes in gaps_by_species.items():
            species_info = self.orthodb.plant_species.get(species, {})
            
            # Sort genes by priority score (highest first)
            genes.sort(key=lambda g: g.get("priority_score", 0), reverse=True)
            
            # Count gaps by severity
            complete_gaps = sum(1 for g in genes if g["gap_level"] == "complete_gap")
            severe_gaps = sum(1 for g in genes if g["gap_level"] == "severe_gap")
            
            # Top priority score for this species
            top_priority = genes[0].get("priority_score", 0) if genes else 0
            
            result["gaps"].append({
                "species": species,
                "common_name": species_info.get("common", ""),
                "missing_genes": genes,
                "gap_count": len(genes),
                "complete_gaps": complete_gaps,
                "severe_gaps": severe_gaps,
                "top_priority": top_priority
            })
        
        # Sort by number of complete gaps first, then total
        result["gaps"].sort(
            key=lambda x: (x["complete_gaps"], x["gap_count"]), 
            reverse=True
        )
        
        # Step 5: Generate summaries for top gap genes
        print("Generating gene function summaries...")
        top_gap_genes = set()
        for gap in result["gaps"][:5]:
            for gene in gap["missing_genes"][:3]:
                top_gap_genes.add(gene["gene"])
        
        for gene_name in list(top_gap_genes)[:10]:
            contexts = gene_contexts.get(gene_name, [])
            if contexts:
                context_text = "\n".join([
                    f"- {c['title']}: {c['function']}"
                    for c in contexts[:3]
                ])
                
                summary = self.llm.summarize_gene_function(
                    gene_name,
                    context_text,
                    llm_model
                )
                result["gene_summaries"][gene_name] = summary
        
        return result
    
    def quick_publication_gap_check(self, gene_name: str, 
                                     target_species: List[str]) -> Dict:
        """
        Quick check for publication gaps for a single gene.
        Directly queries PubMed for publication counts.
        """
        result = {
            "gene": gene_name,
            "species_results": []
        }
        
        for species in target_species:
            pub_check = self.pubmed.count_gene_species_publications(gene_name, species)
            species_info = self.orthodb.plant_species.get(species, {})
            
            result["species_results"].append({
                "species": species,
                "common_name": species_info.get("common", ""),
                "publication_count": pub_check["publication_count"],
                "gap_level": pub_check["gap_level"],
                "is_gap": pub_check["is_gap"],
                "search_query": pub_check["query"]
            })
        
        return result
    
    def quick_gap_check(self, gene_name: str, source_species: str,
                        target_species: List[str]) -> Dict:
        """
        Quick check for a single gene across species.
        Now uses publication-based detection.
        """
        return self.quick_publication_gap_check(gene_name, target_species)
    
    def get_species_list(self) -> List[Dict]:
        """Get available plant species for analysis"""
        return self.orthodb.get_available_species()
    
    def get_gap_statistics(self, gaps: List[Dict]) -> Dict:
        """Calculate statistics from gap analysis results"""
        total_gaps = sum(g["gap_count"] for g in gaps)
        complete_gaps = sum(g.get("complete_gaps", 0) for g in gaps)
        species_with_gaps = len(gaps)
        
        all_genes = set()
        for gap in gaps:
            for gene in gap.get("missing_genes", []):
                all_genes.add(gene["gene"])
        
        return {
            "total_gaps": total_gaps,
            "complete_gaps": complete_gaps,
            "species_with_gaps": species_with_gaps,
            "unique_gap_genes": len(all_genes),
            "top_gap_species": gaps[0]["species"] if gaps else None
        }


# Singleton instance
gap_analyzer = GapAnalyzer()
