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
    error = request.args.get('error')
    return render_template('index.html', error=error)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    if not file:
        return redirect(url_for('index', error='Nenhum arquivo enviado.'))
    filename = file.filename.lower()

    # --- Processar CSV ---
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

    # --- Processar PDF ---
    elif filename.endswith('.pdf'):
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        try:
            records = []
            current_date = None
            # Extrair texto e processar linha a linha
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if not text:
                        continue
                    for line in text.splitlines():
                        line = line.strip()
                        # Detectar linha de data (e.g., 23/04/2025), sem valor
                        m_date = re.search(r"(\d{2}/\d{2}/\d{4})", line)
                        if m_date and 'R$' not in line:
                            try:
                                current_date = datetime.strptime(m_date.group(1), '%d/%m/%Y')
                            except:
                                current_date = None
                            continue
                        # Detectar valor R$ e extrair transação
                        m_val = re.search(r"R\$\s*([\d\.,]+)", line)
                        if m_val and current_date:
                            val_str = m_val.group(1)
                            num = val_str.replace('.', '').replace(',', '.')
                            try:
                                valor = float(num)
                            except:
                                continue
                            desc = line[:m_val.start()].strip()
                            desc = re.sub(r"^[^A-Za-z0-9]+", '', desc)
                            tipo = 'Entrada' if valor > 0 else 'Saída'
                            records.append({
                                'data': current_date.strftime('%d/%m/%Y'),
                                'descricao': desc,
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
        df.columns = [col.strip().lower() for col in df.columns]
        if 'valor' not in df.columns:
            return redirect(url_for('index', error='CSV interno inválido: coluna "valor" não encontrada.'))
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
