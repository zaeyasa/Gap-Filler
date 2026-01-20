"""
Report Generation Service
Creates PDF reports for gap analysis results
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT


class ReportService:
    """Generates PDF reports for gap analysis results"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
        # Colors matching the app theme
        self.colors = {
            'primary': HexColor('#58a6ff'),
            'success': HexColor('#3fb950'),
            'warning': HexColor('#d29922'),
            'danger': HexColor('#f85149'),
            'text': HexColor('#1f2328'),
            'muted': HexColor('#57606a'),
            'bg': HexColor('#f6f8fa'),
        }
    
    def _setup_custom_styles(self):
        """Set up custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='Title_Custom',
            parent=self.styles['Title'],
            fontSize=18,
            spaceAfter=12,
            textColor=HexColor('#1f2328')
        ))
        
        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=HexColor('#57606a'),
            spaceAfter=20,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            spaceBefore=15,
            spaceAfter=8,
            textColor=HexColor('#1f2328')
        ))
        
        self.styles.add(ParagraphStyle(
            name='GeneItem',
            parent=self.styles['Normal'],
            fontSize=9,
            leftIndent=10,
            spaceAfter=2
        ))
    
    def generate_gap_report(self, query: str, source_species: str, 
                           target_species: list, gaps: list, 
                           genes: list = None, summaries: list = None) -> bytes:
        """
        Generate a 1-page PDF summary report
        
        Args:
            query: The search query used
            source_species: Source species name
            target_species: List of target species names
            gaps: Gap analysis results
            genes: Optional list of genes identified
            summaries: Optional list of gene summaries
            
        Returns:
            PDF bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
            topMargin=1.5*cm,
            bottomMargin=1.5*cm
        )
        
        story = []
        
        # Title
        story.append(Paragraph("🧬 GAP Filler Analysis Report", self.styles['Title_Custom']))
        
        # Subtitle with date
        date_str = datetime.now().strftime("%B %d, %Y at %H:%M")
        story.append(Paragraph(f"Generated on {date_str}", self.styles['Subtitle']))
        
        # Query Info
        story.append(Paragraph("📋 Search Parameters", self.styles['SectionHeader']))
        
        info_data = [
            ['Query:', query],
            ['Source Species:', source_species],
            ['Target Species:', ', '.join(target_species[:3]) + ('...' if len(target_species) > 3 else '')],
            ['Targets Analyzed:', str(len(target_species))],
        ]
        
        info_table = Table(info_data, colWidths=[2.5*cm, 14*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 0), (0, -1), self.colors['muted']),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 10))
        
        # Summary Statistics
        story.append(Paragraph("📊 Summary Statistics", self.styles['SectionHeader']))
        
        total_gaps = sum(g.get('gap_count', 0) for g in gaps)
        complete_gaps = sum(g.get('complete_gaps', 0) for g in gaps)
        severe_gaps = sum(g.get('severe_gaps', 0) for g in gaps)
        
        stats_data = [
            ['Total Research Gaps:', str(total_gaps)],
            ['Complete Gaps (No Publications):', f"🔴 {complete_gaps}"],
            ['Severe Gaps (1-3 Publications):', f"🟠 {severe_gaps}"],
            ['Species with Gaps:', str(len([g for g in gaps if g.get('gap_count', 0) > 0]))],
        ]
        
        stats_table = Table(stats_data, colWidths=[5*cm, 11.5*cm])
        stats_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 10))
        
        # Top Gaps by Species
        story.append(Paragraph("🔬 Research Gaps by Species", self.styles['SectionHeader']))
        
        # Create gaps table
        gap_table_data = [['Species', 'Gaps', 'Top Genes']]
        
        for gap in sorted(gaps, key=lambda x: x.get('gap_count', 0), reverse=True)[:6]:
            species_name = gap.get('species', 'Unknown')
            gap_count = gap.get('gap_count', 0)
            
            # Get top 3 genes
            top_genes = gap.get('missing_genes', [])[:3]
            genes_str = ', '.join([g.get('gene', '') for g in top_genes])
            if len(gap.get('missing_genes', [])) > 3:
                genes_str += '...'
            
            gap_table_data.append([species_name, str(gap_count), genes_str])
        
        if len(gap_table_data) > 1:
            gap_table = Table(gap_table_data, colWidths=[4.5*cm, 1.5*cm, 10.5*cm])
            gap_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 0), (-1, 0), self.colors['bg']),
                ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#d0d7de')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ]))
            story.append(gap_table)
        else:
            story.append(Paragraph("No gaps found.", self.styles['Normal']))
        
        story.append(Spacer(1, 10))
        
        # Key Genes (if available)
        if genes and len(genes) > 0:
            story.append(Paragraph("🧬 Key Genes Identified", self.styles['SectionHeader']))
            
            gene_names = [g.get('name', g.get('gene', '')) for g in genes[:10]]
            genes_text = ', '.join(gene_names)
            if len(genes) > 10:
                genes_text += f' (+{len(genes) - 10} more)'
            
            story.append(Paragraph(genes_text, self.styles['Normal']))
            story.append(Spacer(1, 10))
        
        # Footer
        story.append(Spacer(1, 20))
        footer_style = ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=HexColor('#8c959f'),
            alignment=TA_CENTER
        )
        story.append(Paragraph(
            "Generated by GAP Filler • Plant Genomics Literature Gap Finder",
            footer_style
        ))
        story.append(Paragraph(
            "Data sources: PubMed, OrthoDB | Powered by Local LLM",
            footer_style
        ))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes


# Create singleton instance
report_service = ReportService()
