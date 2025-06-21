'''
Módulo com funções a serem utilizadas no app.py
'''

def formatar_moeda(valor, moeda="USD"):
    if valor is None:
        return moeda+"$ 0,00"
    valor_formatado = f"{valor:,.2f}"
    return moeda+"$ " + valor_formatado.replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_inteiro(valor):
    if valor is None:
        return "0"
    valor_formatado = format(valor, ",")
    return valor_formatado.replace(",", ".")

def formatar_porcentagem(valor):
    if valor is None:
        return "0,0%"
    valor_formatado = f"{valor:.1f}"
    return valor_formatado.replace(",", ".")

def importar_dados_csv(db_instance, db, app, Projeto):
    from pandas import read_csv, to_datetime, notna
    from os import remove
    from os.path import exists

    if exists (db_instance):
        remove(db_instance)

    dicionario_paises = {
        'GB': 'United Kingdom', 'US': 'United States', 'CA': 'Canada',
        'AU': 'Australia', 'NO': 'Norway', 'IT': 'Italy', 'DE': 'Germany',
        'IE': 'Ireland', 'MX': 'Mexico', 'ES': 'Spain', 'SE': 'Sweden',
        'FR': 'France', 'NL': 'Netherlands', 'NZ': 'New Zealand',
        'CH': 'Switzerland', 'AT': 'Austria', 'DK': 'Denmark',
        'BE': 'Belgium', 'HK': 'Hong Kong', 'LU': 'Luxembourg',
        'SG': 'Singapore', 'JP': 'Japan'
        }
    
    with app.app_context():
        
        db.create_all()

        try:
            csv_file_path = './dados/ks-projects-201801.csv'
            df = read_csv(csv_file_path, low_memory=False)
            df = df.rename(columns={
                'name': 'nome',
                'main_category': 'categoria',
                'deadline': 'data_fim',
                'launched': 'data_inicio',
                'goal': 'valor_meta',
                'pledged': 'valor_recebido',
                'state': 'status',
                'backers': 'qtd_apoiador',
                'usd_pledged_real': 'valor_recebido_dolar',
                'usd_goal_real': 'valor_meta_dolar',
                'category': 'subcategoria',
                'currency': 'moeda',
                'country': 'pais'
            })
            df = df.dropna(subset=['ID'])
            df = df.drop(columns="usd pledged")
            df = df.drop(df[df['pais'] == 'N,0"'].index)

            df['data_inicio'] = to_datetime(df['data_inicio'], format='%Y-%m-%d %H:%M:%S')
            df['data_fim'] = to_datetime(df['data_fim'], format='%Y-%m-%d')

            df = df[(df['data_inicio'].dt.year >= 2009) & (df['data_inicio'].dt.year <= 2017)]

            df['pais'] = df['pais'].map(dicionario_paises)

            print("Iniciando a inserção de dados...")
            for index, row in df.iterrows():
                data_inicio_date = row['data_inicio'].date()
                data_fim_date = row['data_fim'].date()

                projeto = Projeto(
                    id=row['ID'],
                    nome=str(row['nome']) if notna(row['nome']) else 'N/A',
                    categoria=str(row['categoria']),
                    subcategoria=str(row['subcategoria']),
                    moeda=str(row['moeda']),
                    data_fim=data_fim_date,
                    valor_meta=row['valor_meta'],
                    data_inicio=data_inicio_date,
                    valor_recebido=row['valor_recebido'],
                    status=str(row['status']),
                    qtd_apoiador=row['qtd_apoiador'],
                    pais=str(row['pais']) if notna(row['pais']) else 'N/A',
                    valor_recebido_dolar=row['valor_recebido_dolar'],
                    valor_meta_dolar=row['valor_meta_dolar']
                )
                db.session.add(projeto)

                if index % 30000 == 0:
                    db.session.commit()
                    print(f"Inseridos {index + 1} registros...")

            db.session.commit()
            print("Dados inseridos com sucesso!")

        except Exception as e:
            db.session.rollback()
            print(f"Ocorreu um erro: {e}")
        finally:
            db.session.close()

            with app.app_context():
                try:
                    print("\nVerificando alguns dados inseridos:")
                    first_10_projects = Projeto.query.limit(10).all()
                    for p in first_10_projects:
                        print(p)
                except Exception as e:
                    print(f"Erro ao verificar dados: {e}")
