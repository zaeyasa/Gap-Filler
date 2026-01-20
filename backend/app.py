"""
GAP Filler API Server
Flask REST API for the plant genomics gap analysis application
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from services.gap_analyzer import gap_analyzer
from services.llm_service import llm_service
from services.pubmed_service import pubmed_service
from services.orthodb_service import orthodb_service

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend


# ============================================================================
# Health & Status Endpoints
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Check API health status"""
    return jsonify({
        "status": "healthy",
        "service": "GAP Filler API",
        "version": "1.0.0"
    })


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get overall system status including Ollama connection"""
    llm_status = llm_service.test_connection()
    
    return jsonify({
        "api": "running",
        "ollama": llm_status,
        "services": {
            "pubmed": "available",
            "orthodb": "available",
            "llm": llm_status.get("status", "unknown")
        }
    })


# ============================================================================
# Species Endpoints
# ============================================================================

@app.route('/api/species', methods=['GET'])
def get_species():
    """Get list of available plant species"""
    species = gap_analyzer.get_species_list()
    return jsonify({
        "species": species,
        "count": len(species)
    })


# ============================================================================
# LLM Model Endpoints
# ============================================================================

@app.route('/api/models', methods=['GET'])
def get_models():
    """Get available Ollama models"""
    models = llm_service.get_available_models()
    current = llm_service.get_current_model()
    
    return jsonify({
        "models": models,
        "current_model": current
    })


@app.route('/api/models/set', methods=['POST'])
def set_model():
    """Set the active LLM model"""
    data = request.get_json()
    model_name = data.get('model')
    
    if not model_name:
        return jsonify({"error": "Model name required"}), 400
    
    llm_service.set_model(model_name)
    
    return jsonify({
        "success": True,
        "current_model": llm_service.get_current_model()
    })


# ============================================================================
# Search Endpoints
# ============================================================================

@app.route('/api/search', methods=['POST'])
def search_articles():
    """Search PubMed for genome-wide analysis articles"""
    data = request.get_json()
    query = data.get('query', '')
    max_results = data.get('max_results', 20)
    
    if not query:
        return jsonify({"error": "Search query required"}), 400
    
    articles = pubmed_service.search_and_fetch(query, max_results)
    
    return jsonify({
        "query": query,
        "articles": articles,
        "count": len(articles)
    })


# ============================================================================
# Analysis Endpoints
# ============================================================================

@app.route('/api/analyze', methods=['POST'])
def analyze_gaps():
    """
    Full gap analysis pipeline.
    Searches articles, extracts genes, and finds gaps.
    """
    data = request.get_json()
    
    query = data.get('query', '')
    source_species = data.get('source_species', 'Arabidopsis thaliana')
    target_species = data.get('target_species', [])
    max_articles = data.get('max_articles', 20)
    model = data.get('model')  # Optional model override
    
    if not query:
        return jsonify({"error": "Search query required"}), 400
    
    if not target_species:
        # Default to common crop species if not specified
        target_species = [
            "Triticum aestivum",
            "Oryza sativa",
            "Zea mays",
            "Glycine max",
            "Solanum lycopersicum"
        ]
    
    result = gap_analyzer.analyze_query(
        search_query=query,
        source_species=source_species,
        target_species=target_species,
        max_articles=max_articles,
        llm_model=model
    )
    
    # Add statistics
    result["statistics"] = gap_analyzer.get_gap_statistics(result.get("gaps", []))
    
    return jsonify(result)


@app.route('/api/analyze/quick', methods=['POST'])
def quick_gap_check():
    """
    Quick gap check for a single gene.
    Doesn't use LLM, just queries OrthoDB.
    """
    data = request.get_json()
    
    gene_name = data.get('gene')
    source_species = data.get('source_species', 'Arabidopsis thaliana')
    target_species = data.get('target_species', [])
    
    if not gene_name:
        return jsonify({"error": "Gene name required"}), 400
    
    if not target_species:
        target_species = list(orthodb_service.plant_species.keys())
    
    result = gap_analyzer.quick_gap_check(gene_name, source_species, target_species)
    
    return jsonify(result)


# ============================================================================
# Extract Endpoints
# ============================================================================

@app.route('/api/extract', methods=['POST'])
def extract_from_text():
    """Extract genes and organisms from provided text using LLM"""
    data = request.get_json()
    
    text = data.get('text', '')
    model = data.get('model')
    
    if not text:
        return jsonify({"error": "Text required"}), 400
    
    result = llm_service.extract_genes_and_organisms(text, model)
    
    return jsonify(result)


@app.route('/api/summarize', methods=['POST'])
def summarize_gene():
    """Summarize gene function based on context"""
    data = request.get_json()
    
    gene_name = data.get('gene')
    context = data.get('context', '')
    model = data.get('model')
    
    if not gene_name:
        return jsonify({"error": "Gene name required"}), 400
    
    summary = llm_service.summarize_gene_function(gene_name, context, model)
    
    return jsonify({
        "gene": gene_name,
        "summary": summary
    })


# ============================================================================
# Publications Endpoints (NEW)
# ============================================================================

@app.route('/api/publications', methods=['POST'])
def get_publications():
    """
    Get publications for a gene+species combination with links.
    Used for on-demand loading in the gene detail panel.
    """
    data = request.get_json()
    
    gene_name = data.get('gene')
    species = data.get('species')
    max_results = data.get('max_results', 5)
    
    if not gene_name:
        return jsonify({"error": "Gene name required"}), 400
    
    if not species:
        return jsonify({"error": "Species name required"}), 400
    
    result = pubmed_service.get_gene_species_publications(
        gene_name, species, max_results
    )
    
    return jsonify(result)


# ============================================================================
# GO Terms Endpoints (NEW)
# ============================================================================

@app.route('/api/go-terms', methods=['POST'])
def get_go_terms():
    """
    Get Gene Ontology terms and pathway information for a gene.
    Uses UniProt and QuickGO APIs.
    """
    from services.go_terms_service import go_terms_service
    
    data = request.get_json()
    
    gene_name = data.get('gene')
    species = data.get('species')
    
    if not gene_name:
        return jsonify({"error": "Gene name required"}), 400
    
    result = go_terms_service.get_gene_go_terms(gene_name, species)
    
    return jsonify(result)


# ============================================================================
# v3.0 Funding Endpoint
# ============================================================================

@app.route('/api/funding', methods=['POST'])
def search_funding():
    """
    Search for NIH grants related to a gene.
    """
    from services.funding_service import funding_service
    
    data = request.get_json()
    gene = data.get('gene')
    
    if not gene:
        return jsonify({"error": "Gene name required"}), 400
    
    result = funding_service.search_plant_genomics_grants(gene)
    
    return jsonify(result)


# ============================================================================
# v3.0 Ortholog Confidence & Sequence Comparison Endpoint (Phase D & E)
# ============================================================================

@app.route('/api/ortholog', methods=['POST'])
def get_ortholog():
    """
    Get ortholog information including confidence and sequence identity.
    Uses Ensembl Plants REST API.
    """
    from services.ortholog_service import ortholog_service
    
    data = request.get_json()
    
    gene = data.get('gene')
    source_species = data.get('source_species')
    target_species = data.get('target_species')
    
    if not gene:
        return jsonify({"error": "Gene name required"}), 400
    
    if not source_species or not target_species:
        return jsonify({"error": "Source and target species required"}), 400
    
    result = ortholog_service.get_ortholog_info(gene, source_species, target_species)
    
    return jsonify(result)


# ============================================================================
# v3.0 Proposal Generation Endpoint
# ============================================================================

@app.route('/api/proposal/generate', methods=['POST'])
def generate_proposal():
    """
    Generate a research proposal using local LLM.
    On-demand only - triggered by user.
    """
    from services.proposal_service import proposal_service
    from services.go_terms_service import go_terms_service
    
    data = request.get_json()
    
    gene = data.get('gene')
    source_species = data.get('source_species')
    target_species = data.get('target_species')
    length = data.get('length', 'medium')  # short, medium, full
    
    if not gene:
        return jsonify({"error": "Gene name required"}), 400
    
    # Try to get GO terms for context
    go_terms = None
    if source_species:
        go_terms = go_terms_service.get_gene_go_terms(gene, source_species)
    
    # Use the model selected by the user in llm_service (from settings panel)
    user_selected_model = llm_service.get_current_model()
    
    result = proposal_service.generate_proposal(
        gene=gene,
        source_species=source_species or "model organism",
        target_species=target_species or "target species",
        length=length,
        go_terms=go_terms,
        model=user_selected_model  # Pass user-selected model
    )
    
    return jsonify(result)


# ============================================================================
# PDF Export Endpoint
# ============================================================================

@app.route('/api/export/pdf', methods=['POST'])
def export_pdf():
    """Generate PDF report from gap analysis results"""
    from services.report_service import report_service
    from flask import send_file
    
    data = request.get_json()
    
    query = data.get('query', 'Unknown query')
    source_species = data.get('source_species', 'Unknown')
    target_species = data.get('target_species', [])
    gaps = data.get('gaps', [])
    genes = data.get('genes', [])
    summaries = data.get('summaries', [])
    
    try:
        pdf_bytes = report_service.generate_gap_report(
            query=query,
            source_species=source_species,
            target_species=target_species,
            gaps=gaps,
            genes=genes,
            summaries=summaries
        )
        
        # Create filename
        safe_query = ''.join(c for c in query if c.isalnum() or c in ' -_')[:30]
        filename = f"gap_report_{safe_query}_{__import__('datetime').datetime.now().strftime('%Y%m%d')}.pdf"
        
        return send_file(
            __import__('io').BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate PDF: {str(e)}"}), 500


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error", "details": str(e)}), 500


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == '__main__':
    print("""
    ============================================================
                          GAP FILLER API                        
               Plant Genomics Literature Gap Finder             
    ============================================================
    """)
    print(f"  [*] Starting server on http://{Config.HOST}:{Config.PORT}")
    print(f"  [*] LLM Model: {Config.OLLAMA_MODEL}")
    print(f"  [*] PubMed & OrthoDB integration ready")
    print("-" * 60)
    
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )
