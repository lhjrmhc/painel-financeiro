from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import os
import re
import pdfplumber
from datetime import datetime

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    # Captura mensagem de erro (se enviada por query string)
    error = request.args.get('error')
    return render_template('index.html', error=error)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    if not file:
        return redirect(url_for('index', error='Nenhum arquivo enviado.'))
    filename = file.filename.lower()
    # Processar CSV
    if filename.endswith('.csv'):
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        try:
            df = pd.read_csv(filepath, sep=';', encoding='latin1')
            df.columns = [col.strip().lower() for col in df.columns]
            if 'valor' not in df.columns:
                return redirect(url_for('index', error='CSV inválido: coluna "valor" não encontrada.'))
            df.to_csv('transacoes.csv', index=False, sep=';', encoding='latin1')
        except Exception as e:
            return redirect(url_for('index', error='Erro ao processar CSV: ' + str(e)))
        return redirect(url_for('transacoes'))
    # Processar PDF
    elif filename.endswith('.pdf'):
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        try:
            # Extrair texto do PDF
            text = ''
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + '\n'
            # Regex para linhas de transação (data, descrição, valor)
            matches = re.findall(r"(\d{2}/\d{2}/\d{4})\s+(.*?)\s+R\$\s*([\d\.]+,\d{2})", text)
            records = []
            for date_str, desc, val_str in matches:
                # Converter data e valor
                try:
                    date = datetime.strptime(date_str, '%d/%m/%Y')
                except:
                    continue
                # Normalizar valor
                num = val_str.replace('.', '').replace(',', '.')
                valor = float(num)
                # Determinar tipo
                tipo = 'Entrada' if valor > 0 else 'Saída'
                records.append({
                    'data': date,
                    'descricao': desc.strip(),
                    'valor': valor,
                    'tipo': tipo
                })
            if not records:
                return redirect(url_for('index', error='PDF processado, mas nenhuma transação encontrada.'))
            df = pd.DataFrame(records)
            df.to_csv('transacoes.csv', index=False, sep=';', encoding='latin1')
        except Exception as e:
            return redirect(url_for('index', error='Erro ao processar PDF: ' + str(e)))
        return redirect(url_for('transacoes'))
    # Formato não suportado
    else:
        return redirect(url_for('index', error='Formato não suportado. Envie CSV ou PDF.'))

@app.route('/transacoes')
def transacoes():
    if not os.path.exists('transacoes.csv'):
        return redirect(url_for('index', error='Antes de ver transações, faça upload de um CSV/PDF válido.'))
    try:
        df = pd.read_csv('transacoes.csv', sep=';', encoding='latin1')
        # Normalizar e converter valor
        df.columns = [col.strip().lower() for col in df.columns]
        if 'valor' not in df.columns:
            return redirect(url_for('index', error='CSV interno inválido: coluna "valor" não encontrada.'))
        df['valor'] = df['valor'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0.0)
    except Exception as e:
        return redirect(url_for('index', error='Erro ao ler transações: ' + str(e)))
    total_receita = df[df['valor'] > 0]['valor'].sum()
    total_despesa = -df[df['valor'] < 0]['valor'].sum()
    lucro = total_receita - total_despesa
    tables = [df.to_html(classes='table table-striped', index=False)]
    return render_template('transacoes.html', tables=tables,
                           total_receita=total_receita,
                           total_despesa=total_despesa,
                           lucro=lucro)

if __name__ == '__main__':
    app.run(debug=True)
