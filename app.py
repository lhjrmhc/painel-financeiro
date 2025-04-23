from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import os
import re
import pdfplumber
from datetime import datetime

# Categorias pré-estabelecidas
CATEGORIES = [
    "Receita: Crédito", "Receita: Débito", "Receita: Pix", "Receita: Dinheiro", "Receita: Convênio",
    "Custo Fixo: Pró-labore", "Custo Fixo: Salários", "Custo Fixo: Aluguel", "Custo Fixo: Energia elétrica", "Custo Fixo: Internet", "Custo Fixo: Celular", "Custo Fixo: Sabesp", "Custo Fixo: Contabilidade", "Custo Fixo: Vale transporte", "Custo Fixo: Sistema",
    "Custo Variável: Plantonista", "Custo Variável: Terceiros", "Custo Variável: Limpeza", "Custo Variável: Material Escritório", "Custo Variável: Material Limpeza", "Custo Variável: Impostos", "Custo Variável: Manutenção predial",
    "Investimentos/Aquisições: Equipamentos Internação", "Investimentos/Aquisições: Equipamentos Consultórios"
]

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
TRANSACTIONS_FILE = 'transacoes.csv'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# Inicializa arquivo de transações com colunas, se não existir
if not os.path.exists(TRANSACTIONS_FILE):
    pd.DataFrame(columns=['data','descricao','valor','tipo','categoria']) \
       .to_csv(TRANSACTIONS_FILE, index=False, sep=';', encoding='latin1')

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
    # Processar CSV
    if filename.endswith('.csv'):
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        try:
            df = pd.read_csv(filepath, sep=';', encoding='latin1')
            df.columns = [col.strip().lower() for col in df.columns]
            if 'valor' not in df.columns:
                return redirect(url_for('index', error='CSV inválido: coluna "valor" não encontrada.'))
            if 'categoria' not in df.columns:
                df['categoria'] = ''
            df.to_csv(TRANSACTIONS_FILE, index=False, sep=';', encoding='latin1')
        except Exception as e:
            return redirect(url_for('index', error='Erro ao processar CSV: ' + str(e)))
        return redirect(url_for('transacoes'))
    # Processar PDF
    elif filename.endswith('.pdf'):
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        try:
            records = []
            current_date = None
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ''
                    for line in text.splitlines():
                        line = line.strip()
                        # Detecta data isolada
                        if re.fullmatch(r"\d{2}/\d{2}/\d{4}", line):
                            try:
                                current_date = datetime.strptime(line, '%d/%m/%Y')
                            except:
                                current_date = None
                            continue
                        # Detecta valor e extrai
                        m_val = re.search(r"R\$\s*([\d\.,]+)", line)
                        if m_val and current_date:
                            num = m_val.group(1).replace('.', '').replace(',', '.')
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
                                'tipo': tipo,
                                'categoria': ''
                            })
            if not records:
                return redirect(url_for('index', error='PDF processado, mas nenhuma transação encontrada.'))
            df = pd.DataFrame(records)
            df.to_csv(TRANSACTIONS_FILE, index=False, sep=';', encoding='latin1')
        except Exception as e:
            return redirect(url_for('index', error='Erro ao processar PDF: ' + str(e)))
        return redirect(url_for('transacoes'))
    else:
        return redirect(url_for('index', error='Formato não suportado. Envie CSV ou PDF.'))

@app.route('/adicionar', methods=['GET', 'POST'])
def adicionar():
    if request.method == 'POST':
        vencimento = request.form.get('vencimento')
        descricao = request.form.get('descricao')
        valor = request.form.get('valor')
        categoria = request.form.get('categoria')
        try:
            dt = datetime.strptime(vencimento, '%Y-%m-%d')
            data_str = dt.strftime('%d/%m/%Y')
        except:
            data_str = vencimento
        try:
            valor_num = float(valor.replace(',', '.'))
        except:
            valor_num = 0.0
        df = pd.read_csv(TRANSACTIONS_FILE, sep=';', encoding='latin1')
        new_df = pd.concat([df, pd.DataFrame([{
            'data': data_str,
            'descricao': descricao,
            'valor': -abs(valor_num),
            'tipo': 'Saída',
            'categoria': categoria
        }])], ignore_index=True)
        new_df.to_csv(TRANSACTIONS_FILE, index=False, sep=';', encoding='latin1')
        return redirect(url_for('transacoes'))
    # Passa categorias para template
    return render_template('adicionar.html', categories=CATEGORIES)

@app.route('/transacoes')
def transacoes():
    if not os.path.exists(TRANSACTIONS_FILE):
        return redirect(url_for('index', error='Antes de ver transações, faça upload de um CSV/PDF válido.'))
    try:
        df = pd.read_csv(TRANSACTIONS_FILE, sep=';', encoding='latin1')
        df.columns = [col.strip().lower() for col in df.columns]
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
