# 🌱 GAP Filler

**Plant Genomics Literature Gap Finder**

A desktop research tool that identifies knowledge gaps in plant genomics by analyzing genome-wide analysis (GWAS/GWA) articles and comparing gene characterization across plant species.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-API-green?logo=flask)
![Ollama](https://img.shields.io/badge/LLM-Ollama-purple?logo=ollama)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## ✨ Features

### Core Analysis
- 🔍 **PubMed Integration** - Search and analyze genome-wide analysis articles
- 🧬 **AI Gene Extraction** - Uses local LLM (Ollama) to extract gene names from abstracts
- 🌿 **Gap Detection** - Identifies genes studied in model organisms but missing in crop species
- 📊 **OrthoDB Integration** - Cross-references ortholog data for 20+ plant species

### Analysis Tools
- 🏷️ **GO Terms & Pathways** - Gene function annotations from UniProt/QuickGO
- 📈 **Priority Scoring** - Ranks gaps by research potential
- 📅 **Timeline View** - Publication trends over time
- 🔀 **Ortholog Confidence** - Sequence identity from Ensembl Plants

### Research Tools  
- 📝 **AI Proposal Generator** - Generate research proposal drafts using local LLM
- 💰 **Funding Search** - Direct link to NIH RePORTER with auto-copy
- 📄 **PDF Export** - Generate 1-page summary reports

### User Experience
- 🌙 **Dark/Light Theme** - Toggle between themes
- 📜 **Search History** - Save and restore previous searches
- 📝 **Personal Notes** - Add notes to any gene gap

---

## 🖼️ Screenshots

<details>
<summary>Click to view screenshots</summary>

*Add your screenshots here*

</details>

---

## 🚀 Quick Start

### Prerequisites

1. **Python 3.10+** - [Download](https://www.python.org/downloads/)
2. **Ollama** - [Download](https://ollama.com/download)
   - Pull a model: `ollama pull deepseek-r1:8b`

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/gap-filler.git
cd gap-filler

# Install dependencies
cd backend
pip install -r requirements.txt
```

### Configuration (Optional)

Create a `.env` file in the `backend` folder:

```env
OLLAMA_MODEL=deepseek-r1:8b
OLLAMA_HOST=http://localhost:11434
NCBI_EMAIL=your.email@example.com
NCBI_API_KEY=your_ncbi_api_key  # Optional, increases rate limits
```

### Running

```bash
# 1. Start Ollama (in a separate terminal)
ollama serve

# 2. Start the backend
cd backend
python app.py

# 3. Open the frontend
# Open frontend/index.html in your browser
# Or serve it with: python -m http.server 8080 (then go to localhost:8080)
```

---

## 📖 Usage

1. **Select Species** - Choose source (model organism) and target species
2. **Choose LLM Model** - Select from available Ollama models
3. **Enter Search Query** - e.g., "drought stress", "flowering time"
4. **Click "Analyze Gaps"** - Wait for analysis to complete
5. **Explore Results** - Expand genes to see publications, GO terms, and more

### Tips

- Click the 🎯 button on any gene to select it for Funding/Proposal tools
- Use the filter toggles to show only GWAS or Functional studies
- Export results as PDF for sharing

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | System status including Ollama |
| `/api/species` | GET | Available plant species |
| `/api/models` | GET | Available Ollama models |
| `/api/models/set` | POST | Set active LLM model |
| `/api/analyze` | POST | Full gap analysis |
| `/api/publications` | POST | Fetch publications for gene |
| `/api/go-terms` | POST | Get GO terms for gene |
| `/api/ortholog` | POST | Get ortholog confidence |
| `/api/proposal/generate` | POST | Generate research proposal |
| `/api/report` | POST | Generate PDF report |

---

## 📁 Project Structure

```
Gap Filler/
├── backend/
│   ├── app.py                 # Flask API server
│   ├── config.py              # Configuration
│   ├── requirements.txt       # Python dependencies
│   ├── services/
│   │   ├── pubmed_service.py      # PubMed integration
│   │   ├── orthodb_service.py     # OrthoDB integration
│   │   ├── llm_service.py         # Ollama LLM integration
│   │   ├── gap_analyzer.py        # Core gap analysis
│   │   ├── go_terms_service.py    # GO term annotations
│   │   ├── ortholog_service.py    # Ensembl ortholog data
│   │   ├── proposal_service.py    # AI proposal generation
│   │   ├── funding_service.py     # NIH grant search
│   │   └── report_service.py      # PDF generation
│   └── utils/
│       └── text_processor.py      # Text utilities
├── frontend/
│   ├── index.html             # Main page
│   ├── css/styles.css         # Dark/Light theme styles
│   └── js/app.js              # Frontend logic
└── README.md
```

---

## 🌐 Data Sources

| Source | Purpose | Auth Required |
|--------|---------|---------------|
| [PubMed](https://pubmed.ncbi.nlm.nih.gov/) | Literature search | No (API key optional) |
| [OrthoDB](https://www.orthodb.org/) | Ortholog relationships | No |
| [UniProt](https://www.uniprot.org/) | Protein annotations | No |
| [QuickGO](https://www.ebi.ac.uk/QuickGO/) | GO terms | No |
| [Ensembl Plants](https://plants.ensembl.org/) | Ortholog confidence | No |
| [NIH RePORTER](https://reporter.nih.gov/) | Funding opportunities | No |

---

## 🛠️ Technology Stack

- **Backend**: Python, Flask, Requests
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **LLM**: Ollama (local AI)
- **PDF**: ReportLab

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 🙏 Acknowledgments

- NCBI for PubMed E-utilities API
- OrthoDB for ortholog data
- EBI for UniProt and QuickGO APIs
- Ensembl for plant genomics data
- Ollama for local LLM infrastructure
