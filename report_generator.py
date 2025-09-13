# report_generator.py
import asyncio
from pyppeteer import launch
from pathlib import Path
from datetime import datetime
import tempfile
import os
import json
import base64

class ReportGenerator:
    def __init__(self, analysis_results, last_ai_response=None):
        self.analysis_results = analysis_results
        self.last_ai_response = last_ai_response
        self.timestamp = datetime.now()
        self.chart_images = {}  # Stockage des images de graphiques
    
    async def capture_charts_with_puppeteer(self, browser):
        """Capture les graphiques depuis une page HTML temporaire avec Chart.js"""
        cons = self.analysis_results.get("consumption", {})
        significant_groups = cons.get("significant_groups", [])
        metier_details = cons.get("metier_details", {})
        
        if not significant_groups or not metier_details:
            return {}
        
        # Créer le HTML temporaire avec Chart.js et les mêmes données que l'interface
        chart_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
            <style>
                body {{ margin: 0; padding: 20px; background: white; }}
                .chart-container {{ 
                    width: 600px; 
                    height: 300px; 
                    margin: 15px auto; 
                    background: white; 
                    padding: 20px;
                    border: 1px solid #e0e6ed;
                    border-radius: 8px;
                }}
                canvas {{ background: white !important; }}
                h3 {{ 
                    color: #76279b; 
                    text-align: center; 
                    margin-bottom: 20px; 
                    font-family: 'Segoe UI', Arial, sans-serif;
                }}
            </style>
        </head>
        <body>
            <div id="charts-container"></div>
            <script>
                const significantGroups = {json.dumps(significant_groups)};
                const metierDetails = {json.dumps(metier_details)};
                
                // Copie exacte de la fonction prepareMetierChartData de main.js
                function prepareMetierChartData(groupe, metierDetails) {{
                    try {{
                        const dataJ = metierDetails.j ? metierDetails.j.filter(item => item.LCR_ECO_GROUPE_METIERS === groupe) : [];
                        const dataJ1 = metierDetails.jMinus1 ? metierDetails.jMinus1.filter(item => item.LCR_ECO_GROUPE_METIERS === groupe) : [];
                        
                        if (dataJ.length === 0 && dataJ1.length === 0) {{
                            return null;
                        }}
                        
                        const metiersMap = new Map();
                        
                        // Ajouter les données J-1
                        dataJ1.forEach(item => {{
                            metiersMap.set(item.Métier, {{
                                metier: item.Métier,
                                j_minus_1: item.LCR_ECO_IMPACT_LCR_Bn,
                                j: 0
                            }});
                        }});
                        
                        // Ajouter/mettre à jour avec les données J
                        dataJ.forEach(item => {{
                            if (metiersMap.has(item.Métier)) {{
                                metiersMap.get(item.Métier).j = item.LCR_ECO_IMPACT_LCR_Bn;
                            }} else {{
                                metiersMap.set(item.Métier, {{
                                    metier: item.Métier,
                                    j_minus_1: 0,
                                    j: item.LCR_ECO_IMPACT_LCR_Bn
                                }});
                            }}
                        }});
                        
                        // Calculer les variations et trier
                        const metierVariations = Array.from(metiersMap.entries()).map(([metier, data]) => ({{
                            metier: metier,
                            variation: data.j - data.j_minus_1,
                            j: data.j,
                            j_minus_1: data.j_minus_1
                        }}));
                        
                        metierVariations.sort((a, b) => b.variation - a.variation);
                        
                        const totalVariation = metierVariations.reduce((sum, item) => sum + item.variation, 0);
                        
                        let labels = [];
                        let variations = [];
                        
                        if (totalVariation >= 0) {{
                            labels.push('TOTAL GROUP');
                            variations.push(totalVariation);
                            
                            metierVariations.forEach(item => {{
                                labels.push(item.metier);
                                variations.push(item.variation);
                            }});
                        }} else {{
                            metierVariations.forEach(item => {{
                                labels.push(item.metier);
                                variations.push(item.variation);
                            }});
                            
                            labels.push('TOTAL GROUP');
                            variations.push(totalVariation);
                        }}
                        
                        return {{
                            labels: labels,
                            datasets: [{{
                                label: 'Variation (D - D-1)',
                                data: variations,
                                backgroundColor: variations.map((v, index) => {{
                                    const isTotalBar = labels[index] === 'TOTAL GROUP';
                                    
                                    if (isTotalBar) {{
                                        return '#6B218D';
                                    }}
                                    return v >= 0 ? '#51A0A2' : '#805bed';
                                }}),
                                borderColor: variations.map((v, index) => {{
                                    const isTotalBar = labels[index] === 'TOTAL GROUP';
                                    
                                    if (isTotalBar) {{
                                        return '#6B218D';
                                    }}
                                    return v >= 0 ? '#51A0A2' : '#805bed';
                                }}),
                                borderWidth: variations.map((v, index) => {{
                                    const isTotalBar = labels[index] === 'TOTAL GROUP';
                                    return isTotalBar ? 3 : 2;
                                }})
                            }}]
                        }};
                        
                    }} catch (error) {{
                        console.error('Erreur préparation données pour', groupe, ':', error);
                        return null;
                    }}
                }}
                
                // Créer les graphiques
                const container = document.getElementById('charts-container');
                let chartsCreated = 0;
                
                significantGroups.forEach((groupe, index) => {{
                    const chartData = prepareMetierChartData(groupe, metierDetails);
                    
                    if (!chartData) {{
                        chartsCreated++;
                        return;
                    }}
                    
                    const chartDiv = document.createElement('div');
                    chartDiv.className = 'chart-container';
                    chartDiv.innerHTML = `
                        <h3>${{groupe}}</h3>
                        <canvas id="metierChart_${{index}}" width="200" height="100"></canvas>
                    `;
                    container.appendChild(chartDiv);
                    
                    const canvas = document.getElementById(`metierChart_${{index}}`);
                    
                    new Chart(canvas.getContext('2d'), {{
                        type: 'bar',
                        data: chartData,
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                title: {{
                                    display: true,
                                    text: `LCR variations detailed for - ${{groupe}}`,
                                    font: {{ size: 14, weight: 'bold' }}
                                }},
                                legend: {{
                                    display: true,
                                    position: 'top'
                                }}
                            }},
                            scales: {{
                                y: {{
                                    beginAtZero: false,
                                    title: {{
                                        display: true,
                                        text: 'LCR Impact (Bn €)'
                                    }},
                                    grid: {{
                                        color: 'rgba(0,0,0,0.1)'
                                    }}
                                }},
                                x: {{
                                    title: {{
                                        display: true,
                                        text: ''
                                    }},
                                    ticks: {{
                                        maxRotation: 45,
                                        minRotation: 0
                                    }}
                                }}
                            }},
                            elements: {{
                                bar: {{
                                    borderWidth: 1
                                }}
                            }}
                        }}
                    }});
                    
                    chartsCreated++;
                }});
                
                // Marquer comme prêt quand tous les graphiques sont créés
                setTimeout(() => {{
                    document.body.classList.add('charts-ready');
                    console.log('Charts ready, total created:', chartsCreated);
                }}, 2000);
            </script>
        </body>
        </html>
        """
        
        # Écrire le fichier temporaire
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
        temp_file.write(chart_html)
        temp_file.close()
        
        # Créer une nouvelle page pour la capture
        page = await browser.newPage()
        await page.setViewport({'width': 1200, 'height': 800})
        
        try:
            # Naviguer vers le fichier temporaire
            await page.goto(f'file://{temp_file.name}')
            
            # Attendre que Chart.js soit chargé et que les graphiques soient rendus
            await page.waitForSelector('.charts-ready', {'timeout': 15000})
            await page.waitFor(1000)  # Attendre 1s supplémentaire pour l'animation
            
            # Capturer chaque graphique individuellement
            chart_images = {}
            for i, groupe in enumerate(significant_groups):
                try:
                    element = await page.querySelector(f'#metierChart_{i}')
                    if element:
                        screenshot = await element.screenshot({'type': 'png'})
                        chart_images[groupe] = base64.b64encode(screenshot).decode()
                except Exception as e:
                    print(f"Erreur capture graphique {groupe}: {e}")
            
            await page.close()
            
        finally:
            # Nettoyer le fichier temporaire
            try:
                os.unlink(temp_file.name)
            except:
                pass
        
        return chart_images
    
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
        """Génère le PDF avec capture des graphiques via Puppeteer"""
        browser = await launch({
            'headless': True,
            'args': ['--no-sandbox', '--disable-setuid-sandbox']
        })
        
        try:
            # NOUVEAU : Capturer les graphiques d'abord
            self.chart_images = await self.capture_charts_with_puppeteer(browser)
            
            # Ensuite générer le HTML avec les images intégrées
            html_content = self.generate_export_html()
            
            # Créer une nouvelle page pour le PDF
            page = await browser.newPage()
            await page.setContent(html_content)
            await page.pdf({
                'path': output_path,
                'format': 'A4',
                'margin': {
                    'top': '1cm',
                    'right': '1cm',
                    'bottom': '1cm',
                    'left': '1cm'
                },
                'printBackground': True
            })
            
        finally:
            await browser.close()
        
        return output_path