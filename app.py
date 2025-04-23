from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import os

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
    if filename.endswith('.csv'):
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        try:
            # Lê o CSV usando ponto e vírgula
            df = pd.read_csv(filepath, sep=';', encoding='latin1')
            # Normaliza nomes de colunas (minusculas, sem espaços)
            df.columns = [col.strip().lower() for col in df.columns]
            if 'valor' not in df.columns:
                return redirect(url_for('index', error='CSV inválido: coluna "valor" não encontrada.'))
            # Salva transacoes.csv com separador padrão
            df.to_csv('transacoes.csv', index=False, sep=';', encoding='latin1')
        except Exception as e:
            return redirect(url_for('index', error='Erro ao processar CSV: ' + str(e)))
        return redirect(url_for('transacoes'))
    else:
        # Formato não suportado
        return redirect(url_for('index', error='Formato não suportado. Envie apenas arquivos CSV.'))

@app.route('/transacoes')
def transacoes():
    if not os.path.exists('transacoes.csv'):
        return redirect(url_for('index', error='Antes de ver transações, faça upload de um CSV válido.'))
    try:
        # Lê o CSV com ponto e vírgula
        df = pd.read_csv('transacoes.csv', sep=';', encoding='latin1')
        # Normaliza colunas
        df.columns = [col.strip().lower() for col in df.columns]
    except Exception as e:
        return redirect(url_for('index', error='Erro ao ler transações: ' + str(e)))
    if 'valor' not in df.columns:
        return redirect(url_for('index', error='CSV inválido: coluna "valor" não encontrada.'))
    # Converte coluna valor para numérico (troca vírgula e pontos)
    df['valor'] = df['valor'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0.0)
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
