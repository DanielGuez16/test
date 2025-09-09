import pandas as pd
import chardet
from pathlib import Path

def read_any_file(file_path, required_columns=None):
    """
    Lit n'importe quel fichier: Excel, CSV, TSV, etc.
    Retourne un DataFrame pandas
    """
    file_path = Path(file_path)
    extension = file_path.suffix.lower()
    
    try:
        # EXCEL (.xlsx, .xls, .xlsm, .xlsb)
        if extension in ['.xlsx', '.xls', '.xlsm', '.xlsb']:
            if extension == '.xls':
                df = pd.read_excel(file_path, engine='xlrd')
            else:
                df = pd.read_excel(file_path, engine='openpyxl')
        
        # CSV et texte (.csv, .tsv, .txt)
        elif extension in ['.csv', '.tsv', '.txt']:
            # Détecter l'encodage
            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)  # Lire les premiers 10KB
                encoding = chardet.detect(raw_data)['encoding'] or 'utf-8'
            
            # Détecter le délimiteur
            if extension == '.tsv':
                delimiter = '\t'
            else:
                # Tester les délimiteurs courants
                with open(file_path, 'r', encoding=encoding) as f:
                    first_line = f.readline()
                    if ';' in first_line:
                        delimiter = ';'
                    elif '\t' in first_line:
                        delimiter = '\t'
                    else:
                        delimiter = ','
            
            df = pd.read_csv(file_path, delimiter=delimiter, encoding=encoding)
        
        else:
            raise ValueError(f"Format non supporté: {extension}")
        
        # Nettoyer les noms de colonnes
        df.columns = df.columns.astype(str).str.strip()
        
        return df, {
            'format': extension,
            'rows': len(df),
            'columns': len(df.columns)
        }
        
    except Exception as e:
        raise ValueError(f"Erreur lecture fichier {extension}: {str(e)}")