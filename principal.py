from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict
from datetime import date, datetime
import matplotlib.pyplot as plt
import io
import base64
import sqlalchemy
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, Column, Integer, String, Numeric, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Configuração do Banco de Dados
DATABASE_URL = "postgresql://usuario:senha@localhost/cofipei"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modelo de Dados para Lançamentos
class Lancamento(Base):
    __tablename__ = "lancamentos"
    
    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String)
    valor = Column(Numeric(10, 2))
    categoria = Column(String)
    tipo = Column(String)
    data = Column(Date)

# Esquema de Requisição para Relatório Financeiro
class RelatorioFinanceiroRequest(BaseModel):
    data_inicial: date
    data_final: date

# Esquema de Resposta para Relatório Financeiro
class RelatorioFinanceiroResponse(BaseModel):
    periodo: Dict[str, date]
    total_despesas: float
    total_receitas: float
    imagem: str

# Função para gerar gráficos
def gerar_graficos(despesas_por_categoria: Dict[str, float], 
                   receitas_por_categoria: Dict[str, float]) -> str:
    # Criação de duas subplots lado a lado
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    fig.suptitle('Relatório Financeiro - COFIPEI', fontsize=16)
    
    # Gráfico de Pizza para Despesas
    ax1.pie(
        despesas_por_categoria.values(), 
        labels=despesas_por_categoria.keys(), 
        autopct='%1.1f%%',
        title='Distribuição de Despesas por Categoria'
    )
    
    # Gráfico de Barras para Receitas
    ax2.bar(
        receitas_por_categoria.keys(), 
        receitas_por_categoria.values()
    )
    ax2.set_title('Receitas por Categoria')
    ax2.set_xlabel('Categorias')
    ax2.set_ylabel('Valor (R$)')
    plt.xticks(rotation=45, ha='right')
    
    # Salvar gráfico em memória
    buffer = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    
    # Converter para base64
    imagem_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close()
    
    return imagem_base64

# Dependência para obter sessão do banco de dados
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Inicialização do FastAPI
app = FastAPI(title="COFIPEI - Controle Financeiro Pessoal Inteligente")

# Endpoint para Relatório Financeiro
@app.post("/relatorio-financeiro", response_model=RelatorioFinanceiroResponse)
def gerar_relatorio_financeiro(
    request: RelatorioFinanceiroRequest, 
    db: Session = Depends(get_db)
):
    # Consulta de lançamentos no período
    lancamentos = db.query(Lancamento).filter(
        Lancamento.data.between(request.data_inicial, request.data_final)
    ).all()
    
    # Processamento de despesas por categoria
    despesas_por_categoria = {}
    total_despesas = 0
    
    # Processamento de receitas por categoria
    receitas_por_categoria = {}
    total_receitas = 0
    
    for lancamento in lancamentos:
        if lancamento.tipo == 'Despesa':
            despesas_por_categoria[lancamento.categoria] = \
                despesas_por_categoria.get(lancamento.categoria, 0) + lancamento.valor
            total_despesas += lancamento.valor
        elif lancamento.tipo == 'Receita':
            receitas_por_categoria[lancamento.categoria] = \
                receitas_por_categoria.get(lancamento.categoria, 0) + lancamento.valor
            total_receitas += lancamento.valor
    
    # Gerar gráficos
    imagem = gerar_graficos(despesas_por_categoria, receitas_por_categoria)
    
    return {
        "periodo": {
            "data_inicial": request.data_inicial,
            "data_final": request.data_final
        },
        "total_despesas": float(total_despesas),
        "total_receitas": float(total_receitas),
        "imagem": imagem
    }
