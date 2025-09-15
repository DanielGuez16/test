# report_generator.py
import asyncio
from weasyprint import HTML, CSS
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
import tempfile
import os
import json
import base64
import io

class ReportGenerator:
    def __init__(self, analysis_results, last_ai_response=None):
        self.analysis_results = analysis_results
        self.last_ai_response = last_ai_response
        self.timestamp = datetime.now()
        self.chart_images = {}  # Stockage des images de graphiques
    
    def generate_static_charts(self):
        """Génère les graphiques statiques avec matplotlib"""
        cons = self.analysis_results.get("consumption", {})
        significant_groups = cons.get("significant_groups", [])
        metier_details = cons.get("metier_details", {})
        
        if not significant_groups or not metier_details:
            return {}
        
        chart_images = {}
        
        for groupe in significant_groups:
            try:
                # Préparer les données comme dans main.js
                chart_data = self.prepare_chart_data(groupe, metier_details)
                if not chart_data:
                    continue
                
                # Créer le graphique matplotlib
                fig, ax = plt.subplots(figsize=(10, 6))
                
                labels = chart_data['labels']
                variations = chart_data['data']
                
                # Couleurs selon votre logique
                colors = []
                for i, (label, var) in enumerate(zip(labels, variations)):
                    if label == 'TOTAL GROUP':
                        colors.append('#6B218D')
                    else:
                        colors.append('#51A0A2' if var >= 0 else '#805bed')
                
                bars = ax.bar(labels, variations, color=colors, alpha=0.8, edgecolor='black', linewidth=1)
                
                ax.set_title(f'LCR variations detailed for - {groupe}', 
                        fontweight='bold', fontsize=14, color='#76279b')
                ax.set_ylabel('LCR Impact (Bn €)', fontweight='bold')
                ax.grid(axis='y', alpha=0.3)
                
                if len(labels) > 5:
                    plt.xticks(rotation=45, ha='right')
                
                # Valeurs sur les barres
                for bar, value in zip(bars, variations):
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{value:+.3f}', ha='center', va='bottom' if height >= 0 else 'top',
                        fontweight='bold', fontsize=9)
                
                plt.tight_layout()
                
                # Convertir en base64
                buffer = io.BytesIO()
                plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', 
                        facecolor='white', edgecolor='none')
                buffer.seek(0)
                chart_images[groupe] = base64.b64encode(buffer.getvalue()).decode()
                plt.close()
                
            except Exception as e:
                print(f"Erreur génération graphique {groupe}: {e}")
        
        return chart_images


    def prepare_chart_data(self, groupe, metier_details):
        """Reproduit la logique de prepareMetierChartData de main.js"""
        try:
            data_j = metier_details.get('j', [])
            data_j1 = metier_details.get('jMinus1', [])
            
            j_filtered = [item for item in data_j if item.get('LCR_ECO_GROUPE_METIERS') == groupe]
            j1_filtered = [item for item in data_j1 if item.get('LCR_ECO_GROUPE_METIERS') == groupe]
            
            if not j_filtered and not j1_filtered:
                return None
            
            metiers = {}
            
            for item in j1_filtered:
                metier = item.get('Métier', 'Unknown')
                metiers[metier] = {'j_minus_1': item.get('LCR_ECO_IMPACT_LCR_Bn', 0), 'j': 0}
            
            for item in j_filtered:
                metier = item.get('Métier', 'Unknown')
                if metier in metiers:
                    metiers[metier]['j'] = item.get('LCR_ECO_IMPACT_LCR_Bn', 0)
                else:
                    metiers[metier] = {'j_minus_1': 0, 'j': item.get('LCR_ECO_IMPACT_LCR_Bn', 0)}
            
            # Calculer variations et trier
            variations = [(metier, values['j'] - values['j_minus_1']) for metier, values in metiers.items()]
            variations.sort(key=lambda x: x[1], reverse=True)
            
            total_var = sum([var for _, var in variations])
            
            # Même logique que main.js pour positionner TOTAL
            if total_var >= 0:
                labels = ['TOTAL GROUP'] + [metier for metier, _ in variations]
                data = [total_var] + [var for _, var in variations]
            else:
                labels = [metier for metier, _ in variations] + ['TOTAL GROUP']
                data = [var for _, var in variations] + [total_var]
            
            return {'labels': labels, 'data': data}
            
        except Exception as e:
            print(f"Erreur préparation données {groupe}: {e}")
            return None
    
    def generate_export_html(self):
        """Génère le HTML pour export avec CSS inline"""
        css = self._get_inline_css()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>LCR Analysis Report - {self.timestamp.strftime('%Y-%m-%d')}</title>
            <style>{css}</style>
        </head>
        <body>
            <div class="report-container">
                {self._generate_header()}
                {self._generate_balance_sheet_section()}
                {self._generate_consumption_section()}
                {self._generate_ai_analysis_section()}
                {self._generate_footer()}
            </div>
        </body>
        </html>
        """
        return html
    
    def _generate_header(self):
        return f"""
        <div class="report-header">
            <h1>Daily LCR Analysis Report</h1>
            <div class="report-meta">
                <p>Generated on: {self.timestamp.strftime('%B %d, %Y at %H:%M')}</p>
                <p>Analysis Period: D vs D-1 Comparison</p>
            </div>
        </div>
        """
    
    def _generate_balance_sheet_section(self):
        """Génère la section Balance Sheet pour l'export"""
        if not self.analysis_results.get("balance_sheet"):
            return ""
        
        bs = self.analysis_results["balance_sheet"]
        
        html = f"""
        <div class="section">
            <h2>1. Balance Sheet Analysis</h2>
            <div class="table-container">
                {bs.get('pivot_table_html', '')}
            </div>
        """
        
        # Ajouter les métriques de variations
        if bs.get("variations"):
            html += self._generate_variations_cards(bs["variations"])

        # Ajouter le résumé si disponible
        if bs.get("summary"):
            html += f"""
            <div class="summary-box">
                <p>{bs['summary']}</p>
            </div>
            """
        
        html += "</div>"
        return html
    
    def _generate_consumption_section(self):
        """Génère la section Consumption pour l'export"""
        if not self.analysis_results.get("consumption"):
            return ""
        
        cons = self.analysis_results["consumption"]
        
        html = f"""
        <div class="section">
            <h2>2. LCR Consumption Analysis</h2>
            <div class="table-container">
                {cons.get('consumption_table_html', '')}
            </div>
        """
        
        
        if cons.get("variations", {}).get("global"):
            global_var = cons["variations"]["global"]
            is_positive = global_var["variation"] >= 0
            
            html += f"""
            <div class="consumption-metric-card">
                <div class="card-header-pdf">
                    <h6>CONSUMPTION</h6>
                    <span class="badge-pdf {'badge-success' if is_positive else 'badge-danger'}">
                        {'📈 Increase' if is_positive else '📉 Decrease'}
                    </span>
                </div>
                <div class="metrics-row">
                    <div class="metric-col">
                        <small>D-1</small>
                        <h4>{global_var['j_minus_1']} Bn</h4>
                    </div>
                    <div class="metric-col">
                        <small>D</small>
                        <h4>{global_var['j']} Bn</h4>
                    </div>
                    <div class="metric-col">
                        <small>Variation</small>
                        <h4 class="{'positive' if is_positive else 'negative'}">
                            {'+' if is_positive else ''}{global_var['variation']} Bn
                        </h4>
                    </div>
                </div>
            </div>
            """

        # Analyses textuelles
        if cons.get("analysis_text"):
            html += f"""
            <div class="summary-box">
                <p>{cons['analysis_text']}</p>
            </div>
            """

        if hasattr(self, 'chart_images') and self.chart_images:
            html += '<h3>Details by Group</h3>'
            html += '<div class="charts-grid">'
            
            for groupe, image_base64 in self.chart_images.items():
                html += f"""
                <div class="chart-item">
                    <div class="chart-container-pdf-small">
                        <img src="data:image/png;base64,{image_base64}" 
                            style="max-width: 100%; height: auto;" 
                            alt="Chart for {groupe}">
                    </div>
                </div>
                """

        if cons.get("metier_detailed_analysis"):
            html += f"""
            <div class="summary-box">
                <h3>Detailed Analysis</h3>
                <p>{cons['metier_detailed_analysis']}</p>
            </div>
            """
        
        html += "</div>"
        return html
    
    def _generate_ai_analysis_section(self):
        """Génère la section avec la dernière réponse IA"""
        if not self.last_ai_response:
            return ""
        
        # Convertir le markdown en HTML simple
        ai_html = self._markdown_to_simple_html(self.last_ai_response)
        
        return f"""
        <div class="section">
            <h2>3. AI Analysis & Insights</h2>
            <div class="ai-response-box">
                {ai_html}
            </div>
        </div>
        """
    
    def _generate_variations_cards(self, variations):
        """Génère les cartes de variations Balance Sheet comme dans l'interface"""
        html = '<div class="balance-variations-container">'
        
        for category, data in variations.items():
            variation = data["variation"]
            is_positive = variation >= 0
            
            if category == "ACTIF":
                category_name = "ASSET"
            elif category == "PASSIF": 
                category_name = "LIABILITY"
            else:
                category_name = category  # fallback
            
            html += f"""
            <div class="balance-variation-card">
                <div class="balance-card-header">
                    <h6>{category_name}</h6>
                    <span class="balance-badge {'balance-badge-success' if is_positive else 'balance-badge-danger'}">
                        {'📈 Increase' if is_positive else '📉 Decrease'}
                    </span>
                </div>
                <div class="balance-metrics-row">
                    <div class="balance-metric-col">
                        <small>D-1</small>
                        <h4>{data['j_minus_1']} Bn €</h4>
                    </div>
                    <div class="balance-metric-col">
                        <small>D</small>
                        <h4>{data['j']} Bn €</h4>
                    </div>
                </div>
                <hr class="balance-separator">
                <div class="balance-variation-display">
                    <small>Variation</small>
                    <h3 class="{'balance-positive' if is_positive else 'balance-negative'}">
                        {'+' if is_positive else ''}{variation} Bn €
                    </h3>
                </div>
            </div>
            """
        
        html += '</div>'
        return html

    def _markdown_to_simple_html(self, text):
        """Conversion markdown simple vers HTML pour PDF"""
        import re
        
        # Remplacements basiques
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
        text = re.sub(r'\n\n', '</p><p>', text)
        text = f'<p>{text}</p>'
        
        return text
    
    def _generate_footer(self):
        return f"""
        <div class="report-footer">
            <p>Generated by Steering ALM Metrics Tool</p>
            <p>Report ID: {self.timestamp.strftime('%Y%m%d_%H%M%S')}</p>
        </div>
        """
    
    def _get_inline_css(self):
        """CSS optimisé pour l'impression PDF avec support des graphiques"""
        return """
        body { 
            font-family: 'Segoe UI', Arial, sans-serif; 
            margin: 0; 
            padding: 20px; 
            color: #333;
            font-size: 12px;
        }
        
        .report-container { 
            max-width: 100%; 
            margin: 0 auto; 
        }
        
        .report-header { 
            text-align: center; 
            border-bottom: 3px solid #76279b; 
            padding-bottom: 20px; 
            margin-bottom: 30px; 
        }
        
        .report-header h1 { 
            color: #76279b; 
            font-size: 24px; 
            margin-bottom: 10px; 
        }
        
        .report-meta { 
            color: #666; 
            font-size: 11px; 
        }
        
        .section { 
            margin-bottom: 40px; 
            page-break-inside: avoid; 
        }
        
        .section h2 { 
            color: #76279b; 
            border-bottom: 2px solid #ab54d4; 
            padding-bottom: 5px; 
            font-size: 18px;
        }

        .section h3 {
            color: #76279b;
            font-size: 16px;
            margin-top: 25px;
            margin-bottom: 15px;
        }
        
        /* Styles pour les graphiques */
        .chart-section {
            margin: 30px 0;
            page-break-inside: avoid;
        }
        
        .chart-container-pdf {
            background: white;
            border: 1px solid #e0e6ed;
            border-radius: 8px;
            padding: 20px;
            margin: 15px 0;
            text-align: center;
        }
        
        .chart-container-pdf img {
            max-width: 100%;
            height: auto;
            border-radius: 4px;
        }
        
        .table-container { 
            margin: 20px 0; 
            overflow: visible; 
        }
        
        table { 
            width: 100%; 
            border-collapse: collapse; 
            font-size: 10px; 
        }
        
        th { 
            background: #bf7cde !important; 
            color: white; 
            padding: 8px 4px; 
            text-align: center; 
            font-weight: bold; 
        }
        
        td { 
            padding: 6px 4px; 
            border: 1px solid #ddd; 
            text-align: right; 
        }
        
        .total-row { 
            background: #f3dffc; 
            font-weight: bold; 
        }
        
        .variation-positive { color: #28a745; font-weight: bold; }
        .variation-negative { color: #dc3545; font-weight: bold; }
        
        .summary-box { 
            background: #f8f9fa; 
            border-left: 4px solid #ab54d4; 
            padding: 15px; 
            margin: 20px 0; 
        }
        
        .ai-response-box { 
            background: #f0f8ff; 
            border: 1px solid #ab54d4; 
            border-radius: 8px; 
            padding: 20px; 
        }
        
        .consumption-metric-card { 
            background: #f3dffc; 
            border-radius: 15px; 
            padding: 20px; 
            margin: 20px auto; 
            width: 80%;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }

        .card-header-pdf {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }

        .card-header-pdf h6 {
            margin: 0;
            color: #333;
            font-weight: bold;
        }

        .badge-pdf {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 10px;
            color: white;
        }

        .badge-success { background: #28a745; }
        .badge-danger { background: #dc3545; }

        .metrics-row {
            display: flex;
            text-align: center;
            gap: 20px;
        }

        .metric-col {
            flex: 1;
        }

        .metric-col small {
            display: block;
            color: #666;
            margin-bottom: 5px;
        }

        .metric-col h4 {
            margin: 0;
            font-size: 18px;
        }

        .metric-col h4.positive { color: #28a745; }
        .metric-col h4.negative { color: #dc3545; }

        .balance-variations-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            max-width: 600px;
            margin: 20px auto;
        }

        .balance-variation-card {
            background: #f3dffc;
            color: black;
            border-radius: 15px;
            padding: 16px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
            text-align: center;
        }

        .balance-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }

        .balance-card-header h6 {
            margin: 0;
            font-weight: bold;
            color: black;
        }

        .balance-badge {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
            color: white;
        }

        .balance-badge-success { background-color: #28a745; }
        .balance-badge-danger { background-color: #dc3545; }

        .balance-metrics-row {
            display: flex;
            text-align: center;
            margin-bottom: 15px;
        }

        .balance-metric-col {
            flex: 1;
            padding: 0 10px;
        }

        .balance-metric-col small {
            display: block;
            opacity: 0.75;
            color: #666;
            margin-bottom: 5px;
        }

        .balance-metric-col h4 {
            margin: 0;
            font-size: 16px;
            font-weight: bold;
        }

        .balance-separator {
            margin: 15px 0;
            opacity: 0.5;
            border: none;
            height: 1px;
            background: #666;
        }

        .balance-variation-display {
            text-align: center;
        }

        .balance-variation-display small {
            display: block;
            opacity: 0.75;
            color: #666;
            margin-bottom: 5px;
        }

        .balance-variation-display h3 {
            margin: 0;
            font-size: 18px;
            font-weight: 300;
        }

        .balance-variation-display h3.balance-positive {
            color: #28a745;
        }

        .balance-variation-display h3.balance-negative {
            color: #dc3545;
        }
        
        .report-footer { 
            text-align: center; 
            margin-top: 50px; 
            padding-top: 20px; 
            border-top: 1px solid #ddd; 
            font-size: 10px; 
            color: #666; 
        }

        /* Styles pour grille de graphiques */
        .charts-grid {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 15px;
            margin: 20px 0;
        }

        .chart-item {
            flex: 0 0 45%;
            max-width: 45%;
            margin-bottom: 20px;
        }

        .chart-item h4 {
            color: #76279b;
            font-size: 14px;
            margin-bottom: 10px;
            text-align: center;
        }

        .chart-container-pdf-small {
            background: white;
            border: 1px solid #e0e6ed;
            border-radius: 6px;
            padding: 10px;
            text-align: center;
        }

        .chart-container-pdf-small img {
            max-width: 100%;
            height: auto;
            border-radius: 4px;
        }

        /* Si un seul graphique, le centrer */
        .charts-grid:has(.chart-item:only-child) .chart-item {
            flex: 0 0 60%;
            max-width: 60%;
        }

        """

async def export_to_pdf(self, output_path):
    """Génère le PDF avec WeasyPrint (sans Chromium)"""
    try:
        # Générer les graphiques statiques
        self.chart_images = self.generate_static_charts()
        
        # Générer le HTML
        html_content = self.generate_export_html()
        
        # CSS optimisé pour WeasyPrint
        css_content = """
        @page { size: A4; margin: 1.5cm 1cm; }
        body { font-family: Arial, sans-serif; font-size: 11px; line-height: 1.4; }
        .section { page-break-inside: avoid; margin-bottom: 25px; }
        .section h2 { color: #76279b; font-size: 16px; border-bottom: 2px solid #ab54d4; }
        table { width: 100%; border-collapse: collapse; font-size: 9px; }
        th { background: #bf7cde !important; color: white; padding: 6px; text-align: center; }
        td { padding: 4px; border: 1px solid #ddd; text-align: right; }
        .total-row { background: #f3dffc; font-weight: bold; }
        .variation-positive { color: #28a745; font-weight: bold; }
        .variation-negative { color: #dc3545; font-weight: bold; }
        .chart-container-pdf img { max-width: 100%; height: auto; page-break-inside: avoid; }
        .summary-box { background: #f8f9fa; border-left: 4px solid #ab54d4; padding: 12px; }
        """
        
        # Créer le PDF
        html_doc = HTML(string=html_content)
        css_doc = CSS(string=css_content)
        html_doc.write_pdf(output_path, stylesheets=[css_doc])
        
        return output_path
        
    except ImportError:
        raise ImportError("WeasyPrint non installé. Exécutez: pip install weasyprint")
    except Exception as e:
        raise Exception(f"Erreur génération PDF: {str(e)}")