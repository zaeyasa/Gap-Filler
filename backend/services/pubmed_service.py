"""
PubMed E-utilities Service
Fetches genome-wide analysis articles from NCBI PubMed
"""
import requests
import xml.etree.ElementTree as ET
import time
from typing import List, Dict, Optional
from config import Config


class PubMedService:
    """Service for interacting with NCBI PubMed E-utilities API"""
    
    def __init__(self):
        self.base_url = Config.PUBMED_BASE_URL
        self.email = Config.NCBI_EMAIL
        self.api_key = Config.NCBI_API_KEY
        self.last_request_time = 0
        self.min_interval = 1.0 / Config.PUBMED_REQUESTS_PER_SECOND
    
    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()
    
    def _build_params(self, params: dict) -> dict:
        """Add common parameters to request"""
        if self.email:
            params["email"] = self.email
        if self.api_key:
            params["api_key"] = self.api_key
        return params
    
    def search_articles(self, query: str, max_results: int = 50) -> List[str]:
        """
        Search PubMed for articles matching the query.
        Returns list of PubMed IDs (PMIDs).
        """
        self._rate_limit()
        
        # Build search query for genome-wide analysis articles
        full_query = f'({query}) AND ("genome-wide" OR "GWAS" OR "genome wide association")'
        
        params = self._build_params({
            "db": "pubmed",
            "term": full_query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance"
        })
        
        try:
            response = requests.get(
                f"{self.base_url}/esearch.fcgi",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            return data.get("esearchresult", {}).get("idlist", [])
        
        except requests.RequestException as e:
            print(f"PubMed search error: {e}")
            return []
    
    def fetch_articles(self, pmids: List[str]) -> List[Dict]:
        """
        Fetch article details for given PubMed IDs.
        Returns list of article dictionaries with title, abstract, etc.
        """
        if not pmids:
            return []
        
        self._rate_limit()
        
        params = self._build_params({
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "rettype": "abstract"
        })
        
        try:
            response = requests.get(
                f"{self.base_url}/efetch.fcgi",
                params=params,
                timeout=60
            )
            response.raise_for_status()
            
            return self._parse_articles_xml(response.text)
        
        except requests.RequestException as e:
            print(f"PubMed fetch error: {e}")
            return []
    
    def _parse_articles_xml(self, xml_text: str) -> List[Dict]:
        """Parse PubMed XML response into article dictionaries"""
        articles = []
        
        try:
            root = ET.fromstring(xml_text)
            
            for article_elem in root.findall(".//PubmedArticle"):
                article = self._extract_article_data(article_elem)
                if article:
                    articles.append(article)
        
        except ET.ParseError as e:
            print(f"XML parse error: {e}")
        
        return articles
    
    def _extract_article_data(self, elem) -> Optional[Dict]:
        """Extract article data from XML element"""
        try:
            # Get PMID
            pmid_elem = elem.find(".//PMID")
            pmid = pmid_elem.text if pmid_elem is not None else ""
            
            # Get title
            title_elem = elem.find(".//ArticleTitle")
            title = title_elem.text if title_elem is not None else ""
            
            # Get abstract
            abstract_parts = []
            for abstract_elem in elem.findall(".//AbstractText"):
                label = abstract_elem.get("Label", "")
                text = abstract_elem.text or ""
                if label:
                    abstract_parts.append(f"{label}: {text}")
                else:
                    abstract_parts.append(text)
            abstract = " ".join(abstract_parts)
            
            # Get authors
            authors = []
            for author_elem in elem.findall(".//Author"):
                last_name = author_elem.find("LastName")
                first_name = author_elem.find("ForeName")
                if last_name is not None:
                    name = last_name.text
                    if first_name is not None:
                        name = f"{first_name.text} {name}"
                    authors.append(name)
            
            # Get journal and year
            journal_elem = elem.find(".//Journal/Title")
            journal = journal_elem.text if journal_elem is not None else ""
            
            year_elem = elem.find(".//PubDate/Year")
            year = year_elem.text if year_elem is not None else ""
            
            # Get keywords
            keywords = []
            for kw_elem in elem.findall(".//Keyword"):
                if kw_elem.text:
                    keywords.append(kw_elem.text)
            
            return {
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "journal": journal,
                "year": year,
                "keywords": keywords,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            }
        
        except Exception as e:
            print(f"Error extracting article data: {e}")
            return None
    
    def search_and_fetch(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        Convenience method to search and fetch articles in one call.
        """
        pmids = self.search_articles(query, max_results)
        return self.fetch_articles(pmids)
    
    def count_publications(self, query: str) -> int:
        """
        Count total publications matching a query.
        Uses ESearch with rettype=count for efficiency.
        """
        self._rate_limit()
        
        params = self._build_params({
            "db": "pubmed",
            "term": query,
            "rettype": "count",
            "retmode": "json"
        })
        
        try:
            response = requests.get(
                f"{self.base_url}/esearch.fcgi",
                params=params,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            count = data.get("esearchresult", {}).get("count", "0")
            return int(count)
        
        except requests.RequestException as e:
            print(f"PubMed count error: {e}")
            return -1  # Return -1 to indicate error
    
    def count_gene_species_publications(self, gene_name: str, species_name: str) -> Dict:
        """
        Count publications for a specific gene in a specific species.
        This is the core method for publication-based gap detection.
        
        Args:
            gene_name: Gene name or symbol (e.g., "FT", "FLOWERING LOCUS T")
            species_name: Species scientific name (e.g., "Triticum aestivum")
        
        Returns:
            Dictionary with count and query details
        """
        # Build query: gene name AND species name
        # Use quotes for exact species match
        query = f'"{gene_name}" AND "{species_name}"'
        
        count = self.count_publications(query)
        
        return {
            "gene": gene_name,
            "species": species_name,
            "publication_count": count,
            "query": query,
            "is_gap": count == 0,  # TRUE gap if no publications
            "gap_level": self._classify_gap_level(count)
        }
    
    def _classify_gap_level(self, count: int) -> str:
        """Classify the gap level based on publication count"""
        if count < 0:
            return "unknown"  # Error occurred
        elif count == 0:
            return "complete_gap"  # No publications at all
        elif count <= 3:
            return "severe_gap"  # Very few publications
        elif count <= 10:
            return "moderate_gap"  # Some publications but limited
        else:
            return "studied"  # Well studied
    
    def batch_count_gene_species(self, gene_name: str, 
                                  species_list: List[str]) -> List[Dict]:
        """
        Count publications for a gene across multiple species.
        
        Args:
            gene_name: Gene name to check
            species_list: List of species to check
        
        Returns:
            List of publication count results per species
        """
        results = []
        for species in species_list:
            result = self.count_gene_species_publications(gene_name, species)
            results.append(result)
        return results
    
    def get_gene_species_publications(self, gene_name: str, species_name: str, 
                                       max_results: int = 10) -> Dict:
        """
        Get actual publications for a gene+species combination with details and links.
        Includes GWAS/genome-wide detection and tagging.
        
        Args:
            gene_name: Gene name or symbol
            species_name: Species scientific name
            max_results: Maximum number of publications to return
        
        Returns:
            Dictionary with publications including titles, links, years, and is_gwas flag
        """
        query = f'"{gene_name}" AND "{species_name}"'
        
        # Search for PMIDs
        pmids = self.search_publications_simple(query, max_results)
        
        if not pmids:
            return {
                "gene": gene_name,
                "species": species_name,
                "query": query,
                "publications": [],
                "total_count": 0,
                "gwas_count": 0,
                "functional_count": 0
            }
        
        # Fetch article details
        articles = self.fetch_articles(pmids)
        
        # Keywords that indicate genome-wide study
        gwas_keywords = [
            'genome-wide', 'genome wide', 'gwas', 'gwa study',
            'genome-wide association', 'whole-genome', 'whole genome',
            'transcriptome-wide', 'transcriptome wide', 'rna-seq',
            'chip-seq', 'atac-seq', 'genome analysis', 'pan-genome'
        ]
        
        # Format for frontend display with GWAS detection
        publications = []
        gwas_count = 0
        
        for article in articles:
            title = article.get("title", "").lower()
            abstract = article.get("abstract", "").lower()
            keywords = " ".join(article.get("keywords", [])).lower()
            
            # Check if this is a GWAS/genome-wide study
            combined_text = f"{title} {abstract} {keywords}"
            is_gwas = any(kw in combined_text for kw in gwas_keywords)
            
            if is_gwas:
                gwas_count += 1
            
            publications.append({
                "pmid": article.get("pmid", ""),
                "title": article.get("title", ""),
                "authors": ", ".join(article.get("authors", [])[:3]) + ("..." if len(article.get("authors", [])) > 3 else ""),
                "journal": article.get("journal", ""),
                "year": article.get("year", ""),
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{article.get('pmid', '')}/",
                "is_gwas": is_gwas,
                "study_type": "gwas" if is_gwas else "functional"
            })
        
        # Sort: GWAS studies first, then by year (descending)
        publications.sort(key=lambda x: (not x["is_gwas"], -(int(x["year"]) if x["year"].isdigit() else 0)))
        
        # Get total count
        total_count = self.count_publications(query)
        
        # Calculate year statistics for timeline
        years = [int(p["year"]) for p in publications if p["year"].isdigit()]
        year_range = None
        trend = "stable"
        
        if years:
            earliest = min(years)
            latest = max(years)
            year_range = {"earliest": earliest, "latest": latest}
            
            # Calculate trend: compare last 3 years vs earlier
            current_year = 2026  # Could use datetime.now().year
            recent = sum(1 for y in years if y >= current_year - 3)
            older = sum(1 for y in years if y < current_year - 3)
            
            if len(years) >= 3:
                if recent > older:
                    trend = "increasing"  # 📈
                elif recent < older * 0.5:
                    trend = "decreasing"  # 📉
                else:
                    trend = "stable"  # ➡️
        
        return {
            "gene": gene_name,
            "species": species_name,
            "query": query,
            "publications": publications,
            "total_count": total_count,
            "gwas_count": gwas_count,
            "functional_count": len(publications) - gwas_count,
            "year_range": year_range,
            "trend": trend
        }
    
    def search_publications_simple(self, query: str, max_results: int = 10) -> List[str]:
        """
        Simple search that returns only PMIDs (no genome-wide filter).
        """
        self._rate_limit()
        
        params = self._build_params({
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance"
        })
        
        try:
            response = requests.get(
                f"{self.base_url}/esearch.fcgi",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            return data.get("esearchresult", {}).get("idlist", [])
        
        except requests.RequestException as e:
            print(f"PubMed search error: {e}")
            return []


# Singleton instance
pubmed_service = PubMedService()
