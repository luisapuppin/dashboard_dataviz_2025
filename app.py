from flask import Flask, render_template, request, redirect, flash, url_for
from pandas import DataFrame, to_numeric
from sqlalchemy import func
from flask_sqlalchemy import SQLAlchemy
from os.path import join, exists
from os import makedirs
import plotly.express as px


app = Flask(__name__)

app.config['SECRET_KEY'] = 'adf09dfam2034m128t3210dfniasa'

DATABASE_FILE = 'kickstarter.db'
DATABASE_INSTANCE = join(app.instance_path, DATABASE_FILE)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DATABASE_INSTANCE
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = 'dados'
if not exists(UPLOAD_FOLDER):
    makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)

class Projeto(db.Model):
    __tablename__ = 'projeto'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(12), nullable=False)
    subcategoria = db.Column(db.String(18), nullable=False)
    moeda = db.Column(db.String(3), nullable=False)
    data_fim = db.Column(db.Date, nullable=False)
    valor_meta = db.Column(db.Float, default=0.0)
    data_inicio = db.Column(db.Date, nullable=False)
    valor_recebido = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(10), nullable=False)
    qtd_apoiador = db.Column(db.Integer, nullable=False, default=0)
    pais = db.Column(db.String(15), nullable=False)
    valor_recebido_dolar = db.Column(db.Float, default=0.0)
    valor_meta_dolar = db.Column(db.Float, default=0.0)

    def __repr__(self):
        return f"<Projeto(id={self.id}')>"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    from funcoes import importar_dados_csv

    if 'file' not in request.files:
        flash(f'Nenhum arquivo selecionado', 'warning')
        return redirect(url_for('dataset'))
    file = request.files['file']
    if file.filename == '':
        flash(f'Nenhum arquivo selecionado', 'warning')
        return redirect(url_for('dataset'))
    if file:
        filename = "ks-projects-201801.csv"
        filepath = join(app.config['UPLOAD_FOLDER'], filename)
        try:
            file.save(filepath)
            importar_dados_csv(DATABASE_INSTANCE, db, app, Projeto)
            flash(f'Arquivo "{filename}" enviado com sucesso!', 'success')
            return redirect(url_for('dataset'))
        except Exception as e:
            return redirect(url_for('dataset'))
    else:
        return redirect(url_for('dataset'))

def gerar_pizza_status():
    dados_por_status = db.session.query(
        Projeto.status,
        func.count(Projeto.id).label('quantidade')
    ).group_by(Projeto.status).all()

    df_status = DataFrame(dados_por_status, columns=['status', 'quantidade'])
    
    fig = px.pie(
        df_status,
        names='status',
        values='quantidade',
        title='Quantidade de projetos por status',
        hover_data=['quantidade'],
        color_discrete_sequence=px.colors.qualitative.Pastel
    )

    fig.update_traces(textposition='inside', textinfo='percent')
    fig.update_layout(
        height=380,
        autosize=True,
        margin=dict(l=20, r=20, t=50, b=20),
    )

    pizza_html = fig.to_html(full_html=False)

    return pizza_html

def gerar_linha_evolucao():
    dados_anuais = db.session.query(
        func.strftime('%Y', Projeto.data_inicio).label('ano'),
        func.sum(Projeto.valor_recebido_dolar).label('valor_total_anual')
    ).group_by('ano').order_by('ano').all()

    df_anual = DataFrame(dados_anuais)
    df_anual['ano'] = to_numeric(df_anual['ano'])
    
    fig = px.line(
        df_anual,
        x='ano',
        y='valor_total_anual',
        title='Evolução anual do valor arrecadado pelos projetos',
        labels={
            'ano': 'Ano de Início do Projeto',
            'valor_total_anual': 'Valor Arrecadado (USD$)'
        }
    )

    fig.update_layout(
        height=380,
        autosize=True,
        margin=dict(l=100, r=50, t=50, b=50),
        xaxis=dict(
            tickmode='array',
            tickvals=df_anual['ano'],
            type='category'
        )
    )

    fig.update_traces(
        mode='lines+markers',
        hovertemplate='Ano: %{x}<br>Valor arrecadado: USD$%{y:,.2f}<br><extra></extra>'
    )
    
    grafico_evolucao = fig.to_html(full_html=False)

    return grafico_evolucao

def gerar_grafico_dispersao():
    projetos_para_scatter = db.session.query(
        Projeto.categoria,
        Projeto.valor_meta_dolar,
        Projeto.valor_recebido_dolar,
        Projeto.qtd_apoiador
    ).all()

    df_scatter = DataFrame(projetos_para_scatter,
        columns=['categoria', 'valor_meta_dolar', 'valor_recebido_dolar', 'qtd_apoiador'])

    df_agrupado = df_scatter.groupby('categoria').agg(
        total_valor_meta=('valor_meta_dolar', 'sum'),
        total_valor_recebido=('valor_recebido_dolar', 'sum'),
        total_apoiadores=('qtd_apoiador', 'sum')
    ).reset_index()

    fig = px.scatter(
        df_agrupado,
        x='total_valor_meta',
        y='total_valor_recebido',
        size='total_apoiadores',
        color='categoria',
        hover_name='categoria',
        custom_data=['total_apoiadores'],
        title='Valor recebido vs. solicitado por categoria (Tamanho = Total de apoiadores)',
        labels={
            'total_valor_meta': 'Total Solicitado (R$)',
            'total_valor_recebido': 'Total Recebido (R$)',
            'total_apoiadores': 'Total de Apoiadores',
            'categoria': 'Categoria'
        },
        size_max=60
    )

    fig.update_layout(
        height=600,
        autosize=True,
        margin=dict(l=100, r=50, t=50, b=50),
        xaxis_title='Total Solicitado (USD$)',
        yaxis_title='Total Recebido (USD$)'
    )

    fig.update_traces(
        hovertemplate=(
            "<b>Categoria:</b> %{hovertext}<br>" +
            "<b>Total Solicitado:</b> R$ %{x:,.2f}<br>" +
            "<b>Total Recebido:</b> R$ %{y:,.2f}<br>" +
            "<b>Total de Apoiadores:</b> %{customdata[0]:,}<br>" +
            "<extra></extra>"
        )
    )

    scatter_categoria = fig.to_html(full_html=False)

    return scatter_categoria

def gerar_grafico_categoria():
    projetos_por_categoria = db.session.query(
        Projeto.categoria
    ).all()

    df_categoria = DataFrame(projetos_por_categoria, columns=['categoria'])

    fig = px.histogram(
        df_categoria,
        x='categoria',
        title='Número de projetos por categoria',
        labels={
            'categoria': 'Categoria do projeto',
            'count': 'Número de projetos'
        },
        color='categoria',
        color_discrete_sequence=px.colors.qualitative.Alphabet
    )

    fig.update_layout(
        height=500,
        autosize=True,
        margin=dict(l=100, r=50, t=50, b=50),
        xaxis={'categoryorder':'total descending'},
        yaxis_title='Número de projetos'
    )
    
    fig.update_traces(
        hovertemplate=(
            "<b>Categoria:</b> %{x}<br>" +
            "<b>Número de Projetos:</b> %{y:,}<br>" +
            "<extra></extra>"
        )
    )

    grafico_categoria = fig.to_html(full_html=False)

    return grafico_categoria

def gerar_mapa_pais():
    projetos_por_pais = db.session.query(
        Projeto.pais
    ).all()

    df_pais = DataFrame(projetos_por_pais, columns=['pais'])
    
    cont_pais = df_pais['pais'].value_counts().reset_index()
    cont_pais.columns = ['pais', 'num_projetos']

    fig = px.choropleth(
        cont_pais,
        locations="pais",
        color="num_projetos",
        hover_name="pais",
        color_continuous_scale="Viridis",
        projection="natural earth",
        title="Número de Projetos por País",
        labels={'num_projetos': 'Número de Projetos'},
        locationmode='country names'
    )

    fig.update_layout(
        height=500,
        autosize=True,
        margin=dict(l=100, r=50, t=50, b=50),
    )

    mapa_html = fig.to_html(full_html=False)

    return mapa_html

@app.route('/dashboard')
def dashboard():
    from funcoes import formatar_inteiro, formatar_moeda, formatar_porcentagem

    # KPIs
    contProjetos = Projeto.query.count()
    dtMin = db.session.scalar(db.select(func.min(Projeto.data_inicio)))
    dtMax = db.session.scalar(db.select(func.max(Projeto.data_inicio)))
    totalApoiador = db.session.scalar(db.select(func.sum(Projeto.qtd_apoiador)))
    totalRecebido = db.session.scalar(db.select(func.sum(Projeto.valor_recebido_dolar)))
    totalSolicitado = db.session.scalar(db.select(func.sum(Projeto.valor_meta_dolar)))
    maxSolicitado = db.session.scalar(db.select(func.max(Projeto.valor_meta_dolar)))
    maxApoiador = db.session.scalar(db.select(func.max(Projeto.qtd_apoiador)))
    projMaxMeta = Projeto.query.filter(Projeto.status == 'successful').order_by(Projeto.valor_meta_dolar.desc()).first()
    projMaxMetaPercentual = (projMaxMeta.valor_recebido_dolar) / projMaxMeta.valor_meta_dolar
    projMaxMetaF = Projeto.query.filter(Projeto.status == 'failed').order_by(Projeto.valor_meta_dolar.desc()).first()
    projMaxMetaPercentualF = (projMaxMetaF.valor_recebido_dolar) / projMaxMetaF.valor_meta_dolar
    numCategorias = db.session.scalar(db.select(func.count(Projeto.categoria.distinct())))
    numSubcategorias = db.session.scalar(db.select(func.count(Projeto.subcategoria.distinct())))
    numPaises = db.session.scalar(db.select(func.count(Projeto.pais.distinct())))
    
    # Gráficos
    pizzaStatus = gerar_pizza_status()
    linhaEvolucao = gerar_linha_evolucao()
    scatterCategoria = gerar_grafico_dispersao()
    barraCategoria = gerar_grafico_categoria()
    mapaPais = gerar_mapa_pais()

    return render_template(
        'dashboard.html',
        contProjetos = formatar_inteiro(contProjetos),
        dtMin = dtMin,
        dtMax = dtMax,
        totalSolicitado = formatar_moeda(totalSolicitado),
        totalRecebido = formatar_moeda(totalRecebido),
        totalApoiador = formatar_inteiro(totalApoiador),
        mediaApoiador = formatar_moeda(totalRecebido / totalApoiador),
        maxSolicitado = formatar_moeda(maxSolicitado),
        maxApoiador = formatar_inteiro(maxApoiador),
        maxMetaSucesso = formatar_moeda(projMaxMeta.valor_meta_dolar),
        maxMetaSucessoPercent = formatar_porcentagem(projMaxMetaPercentual * 100),
        maxMetaFracasso = formatar_moeda(projMaxMetaF.valor_meta_dolar),
        maxMetaFracassoPercent = formatar_porcentagem(projMaxMetaPercentualF * 100),
        numCategorias = numCategorias,
        numSubcategorias = numSubcategorias,
        numPaises = numPaises,
        pizzaStatus = pizzaStatus,
        linhaEvolucao = linhaEvolucao,
        scatterCategoria = scatterCategoria,
        barraCategoria = barraCategoria,
        mapaPais = mapaPais
        )

@app.route('/kickstater')
def kickstater():
    return render_template('sobre-kickstater.html')

@app.route('/dataset')
def dataset():
    return render_template('sobre-dataset.html')

if __name__ == '__main__':
    app.run(debug=True)
