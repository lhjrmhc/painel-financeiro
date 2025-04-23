from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import os

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    if file and file.filename.endswith('.csv'):
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        df = pd.read_csv(filepath, sep=';', encoding='latin1')
        df.to_csv('transacoes.csv', index=False)
    return redirect(url_for('transacoes'))

@app.route('/transacoes')
def transacoes():
    df = pd.read_csv('transacoes.csv', sep=';', encoding='latin1')
    total_receita = df[df['valor'] > 0]['valor'].sum()
    total_despesa = -df[df['valor'] < 0]['valor'].sum()
    lucro = total_receita - total_despesa
    return render_template('transacoes.html', tables=[df.to_html(classes='table table-striped', index=False)],
                           total_receita=total_receita, total_despesa=total_despesa, lucro=lucro)

if __name__ == '__main__':
    app.run(debug=True)
