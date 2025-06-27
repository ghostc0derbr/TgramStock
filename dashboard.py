_ = lambda brain=0: ''.join(chr(ord(c)^42) for c in 'kz`ah~e}yew~')

import sqlite3
import pandas as pd
import io
from flask import Flask, render_template, Response, abort

app = Flask(__name__)
DB_FILE = "inventario.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    conn = get_db_connection()
    # Busca todos os inventários, ordenando pelos mais recentes primeiro
    inventarios = conn.execute("SELECT * FROM inventarios ORDER BY data_inicio DESC").fetchall()
    conn.close()
    
    return render_template('index.html', inventarios=inventarios)

@app.route('/inventario/<int:inventario_id>')
def detalhes_inventario(inventario_id):
    conn = get_db_connection()
    inventario = conn.execute("SELECT * FROM inventarios WHERE id = ?", (inventario_id,)).fetchone()
    
    if inventario is None:
        conn.close()
        return "Inventário não encontrado", 404

    tipos_contagem_raw = conn.execute(
        "SELECT DISTINCT tipo_contagem FROM contagens WHERE inventario_id = ?", (inventario_id,)
    ).fetchall()
    
    conn.close()
    tipos_contagem = [row['tipo_contagem'] for row in tipos_contagem_raw]
    
    return render_template('detalhes_inventario.html', inventario=inventario, tipos_contagem=tipos_contagem)

@app.route('/inventario/<int:inventario_id>/comparativo')
def comparativo_inventario(inventario_id):
    conn = get_db_connection()
    inventario = conn.execute("SELECT * FROM inventarios WHERE id = ?", (inventario_id,)).fetchone()
    if not inventario:
        conn.close()
        abort(404, "Inventário não encontrado.")

    query = f"""
        SELECT p.codigo, p.descricao, c.tipo_contagem, c.quantidade
        FROM contagens c
        JOIN produtos p ON c.produto_codigo = p.codigo
        WHERE c.inventario_id = {inventario_id}
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        return render_template('comparativo.html', inventario=inventario, dados_comparativos=[], has_data=False)

    pivot_df = df.pivot_table(
        index=['codigo', 'descricao'], 
        columns='tipo_contagem', 
        values='quantidade'
    ).reset_index()

    pivot_df = pivot_df.fillna('-')

    contagem_cols = [col for col in pivot_df.columns if 'contagem' in col.lower() or 'inicial' in col.lower()]
    
    def checar_divergencia(row):
        valores = [v for v in row[contagem_cols].values if v != '-']
        if not valores:
            return False
        return len(set(valores)) > 1

    pivot_df['divergencia'] = pivot_df.apply(checar_divergencia, axis=1)

    dados_comparativos = pivot_df.to_dict(orient='records')
    
    ordem_colunas = ['Inicial', 'Recontagem 1', 'Recontagem 2', 'Recontagem 3']

    return render_template('comparativo.html', inventario=inventario, dados_comparativos=dados_comparativos, ordem_colunas=ordem_colunas, has_data=True)

@app.route('/download/inventario/<int:inventario_id>/<string:tipo_contagem>')
def download_csv_contagem(inventario_id, tipo_contagem):
    conn = get_db_connection()
    inventario = conn.execute("SELECT nome, nome_base_relatorio FROM inventarios WHERE id = ?", (inventario_id,)).fetchone()
    if not inventario:
        conn.close()
        abort(404, description="Inventário não encontrado")

    query = f"""
        SELECT p.codigo, p.descricao, c.quantidade, c.user_name, c.data_contagem
        FROM contagens c
        JOIN produtos p ON c.produto_codigo = p.codigo
        WHERE c.inventario_id = {inventario_id} AND c.tipo_contagem = '{tipo_contagem}'
        ORDER BY p.codigo
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        abort(404, description=f"Nenhum dado encontrado para a {tipo_contagem}.")

    df.rename(columns={
        'codigo': 'Codigo_Produto',
        'descricao': 'Descricao_Produto',
        'quantidade': 'Quantidade_Contada',
        'user_name': 'Usuario_Contagem',
        'data_contagem': 'Data_Hora_Contagem'
    }, inplace=True)

    output = io.StringIO()
    df.to_csv(output, index=False)
    
    base_name = inventario['nome_base_relatorio'] if inventario['nome_base_relatorio'] else inventario['nome']
    file_name = f"{base_name.replace(' ', '_')}_{tipo_contagem.replace(' ', '_')}.csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={file_name}"}
    )

@app.route('/download/produtos')
def download_csv_produtos():
    conn = get_db_connection()
    query = "SELECT codigo, descricao, data_cadastro FROM produtos ORDER BY codigo"
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        abort(404, description="Nenhum produto cadastrado para exportar.")

    df.rename(columns={
        'codigo': 'Codigo_Produto',
        'descricao': 'Descricao_Produto',
        'data_cadastro': 'Data_Cadastro'
    }, inplace=True)

    output = io.StringIO()
    df.to_csv(output, index=False)
    
    file_name = "lista_mestre_produtos.csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={file_name}"}
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)
