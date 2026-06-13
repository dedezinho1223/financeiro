"""Gerador de fixtures (planilhas de exemplo) para testes."""

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


def gerar_extrato_bancario(caminho: str = "tests/fixtures/extrato_banco.xlsx"):
    """Gera extrato bancário fictício para testes."""
    dados = [
        {"Data": "01/06/2024", "Descrição": "TED RECEBIDA - CLIENTE ABC LTDA", "Valor": 5000.00},
        {"Data": "03/06/2024", "Descrição": "PAGAMENTO BOLETO - ALUGUEL", "Valor": -2500.00},
        {"Data": "05/06/2024", "Descrição": "PIX RECEBIDO - VENDA 1234", "Valor": 1800.00},
        {"Data": "07/06/2024", "Descrição": "TARIFA BANCARIA", "Valor": -35.90},
        {"Data": "10/06/2024", "Descrição": "TED RECEBIDA - FORNECEDOR XYZ", "Valor": 3200.00},
        {"Data": "12/06/2024", "Descrição": "PAGAMENTO FORNECEDOR - NF 456", "Valor": -4100.00},
        {"Data": "15/06/2024", "Descrição": "PIX RECEBIDO - SERVICO CONSULTORIA", "Valor": 7500.00},
        {"Data": "18/06/2024", "Descrição": "FOLHA PAGAMENTO JUNHO", "Valor": -12000.00},
        {"Data": "20/06/2024", "Descrição": "DAS SIMPLES NACIONAL", "Valor": -890.00},
        {"Data": "22/06/2024", "Descrição": "PIX RECEBIDO - CLIENTE MARIA", "Valor": 950.00},
        {"Data": "25/06/2024", "Descrição": "PAGAMENTO INTERNET", "Valor": -149.90},
        {"Data": "28/06/2024", "Descrição": "RENDIMENTO APLICACAO", "Valor": 125.30},
    ]

    df = pd.DataFrame(dados)
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(caminho, index=False, engine="openpyxl")
    return caminho


def gerar_controle_interno(caminho: str = "tests/fixtures/controle_interno.xlsx"):
    """Gera controle interno fictício (com algumas divergências propositais)."""
    dados = [
        {"Data": "01/06/2024", "Histórico": "Recebimento Cliente ABC", "Valor": 5000.00, "Categoria": "Vendas"},
        {"Data": "03/06/2024", "Histórico": "Aluguel escritório", "Valor": -2500.00, "Categoria": "Aluguel"},
        {"Data": "05/06/2024", "Histórico": "Venda 1234 - PIX", "Valor": 1800.00, "Categoria": "Vendas"},
        {"Data": "07/06/2024", "Histórico": "Tarifa bancária mensal", "Valor": -35.90, "Categoria": "Despesas Financeiras"},
        {"Data": "10/06/2024", "Histórico": "Recebimento Fornecedor XYZ", "Valor": 3200.00, "Categoria": "Vendas"},
        {"Data": "12/06/2024", "Histórico": "Pagto NF 456 fornecedor", "Valor": -4100.00, "Categoria": "Fornecedores"},
        {"Data": "15/06/2024", "Histórico": "Consultoria prestada", "Valor": 7500.00, "Categoria": "Serviços"},
        {"Data": "18/06/2024", "Histórico": "Folha de pagamento", "Valor": -12000.00, "Categoria": "Pessoal"},
        {"Data": "20/06/2024", "Histórico": "DAS - Simples Nacional", "Valor": -890.00, "Categoria": "Impostos"},
        # Item que existe no interno mas NÃO no banco (divergência proposital)
        {"Data": "21/06/2024", "Histórico": "Recebimento pendente - cheque", "Valor": 2000.00, "Categoria": "Vendas"},
        # Valor divergente proposital (149.90 vs 149.90 ok, mas cliente Maria não está aqui)
        {"Data": "25/06/2024", "Histórico": "Internet escritório", "Valor": -149.90, "Categoria": "Outros"},
    ]

    df = pd.DataFrame(dados)
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(caminho, index=False, engine="openpyxl")
    return caminho


def gerar_lancamentos(caminho: str = "tests/fixtures/lancamentos.xlsx"):
    """Gera planilha de lançamentos para relatórios."""
    dados = [
        {"Data": "02/01/2024", "Descrição": "Venda produto A", "Valor": 3500.00, "Categoria": "Vendas"},
        {"Data": "05/01/2024", "Descrição": "Aluguel janeiro", "Valor": -2500.00, "Categoria": "Aluguel"},
        {"Data": "10/01/2024", "Descrição": "Salários janeiro", "Valor": -8000.00, "Categoria": "Pessoal"},
        {"Data": "15/01/2024", "Descrição": "Venda serviço B", "Valor": 6000.00, "Categoria": "Serviços"},
        {"Data": "20/01/2024", "Descrição": "Fornecedor materiais", "Valor": -1200.00, "Categoria": "Fornecedores"},
        {"Data": "25/01/2024", "Descrição": "DAS janeiro", "Valor": -450.00, "Categoria": "Impostos"},
        {"Data": "03/02/2024", "Descrição": "Venda produto C", "Valor": 4200.00, "Categoria": "Vendas"},
        {"Data": "05/02/2024", "Descrição": "Aluguel fevereiro", "Valor": -2500.00, "Categoria": "Aluguel"},
        {"Data": "10/02/2024", "Descrição": "Salários fevereiro", "Valor": -8500.00, "Categoria": "Pessoal"},
        {"Data": "12/02/2024", "Descrição": "Rendimento aplicação", "Valor": 180.00, "Categoria": "Receita Financeira"},
        {"Data": "18/02/2024", "Descrição": "Consultoria prestada", "Valor": 9000.00, "Categoria": "Serviços"},
        {"Data": "22/02/2024", "Descrição": "Impostos fevereiro", "Valor": -520.00, "Categoria": "Impostos"},
        {"Data": "28/02/2024", "Descrição": "Fornecedor equipamento", "Valor": -3000.00, "Categoria": "Fornecedores"},
        {"Data": "05/03/2024", "Descrição": "Venda grande cliente", "Valor": 15000.00, "Categoria": "Vendas"},
        {"Data": "10/03/2024", "Descrição": "Salários março", "Valor": -8500.00, "Categoria": "Pessoal"},
        {"Data": "15/03/2024", "Descrição": "Aluguel março", "Valor": -2500.00, "Categoria": "Aluguel"},
    ]

    df = pd.DataFrame(dados)
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(caminho, index=False, engine="openpyxl")
    return caminho


def gerar_dados_validacao(caminho: str = "tests/fixtures/dados_validacao.xlsx"):
    """Gera planilha com erros propositais para testar o validador."""
    dados = [
        {"Data": "01/06/2024", "CNPJ": "33.000.167/0001-01", "Valor": 5000.00, "NF": "1001", "Categoria": "Vendas"},
        {"Data": "03/06/2024", "CNPJ": "11.222.333/0001-99", "Valor": -2500.00, "NF": "1002", "Categoria": "Aluguel"},  # CNPJ inválido
        {"Data": "05/06/2024", "CNPJ": "33.000.167/0001-01", "Valor": 1800.00, "NF": "1003", "Categoria": ""},  # Categoria vazia
        {"Data": "32/13/2024", "CNPJ": "33.000.167/0001-01", "Valor": 900.00, "NF": "1004", "Categoria": "Vendas"},  # Data impossível
        {"Data": "07/06/2024", "CNPJ": "33.000.167/0001-01", "Valor": -35.90, "NF": "1005", "Categoria": "Taxas"},
        {"Data": "07/06/2024", "CNPJ": "33.000.167/0001-01", "Valor": -35.90, "NF": "1005", "Categoria": "Taxas"},  # Duplicado
        {"Data": "10/06/2024", "CNPJ": "33.000.167/0001-01", "Valor": 3200.00, "NF": "1006", "Categoria": "Vendas"},
        {"Data": "12/06/2024", "CNPJ": "11111111111111", "Valor": -4100.00, "NF": "1008", "Categoria": "Fornecedores"},  # CNPJ inválido + NF 1007 faltando
        {"Data": "15/06/2024", "CNPJ": "33.000.167/0001-01", "Valor": 750000.00, "NF": "1009", "Categoria": "Vendas"},  # Outlier
        {"Data": "18/06/2024", "CNPJ": "33.000.167/0001-01", "Valor": -1200.00, "NF": "1010", "Categoria": "Pessoal"},
    ]

    df = pd.DataFrame(dados)
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(caminho, index=False, engine="openpyxl")
    return caminho


if __name__ == "__main__":
    gerar_extrato_bancario()
    gerar_controle_interno()
    gerar_lancamentos()
    gerar_dados_validacao()
    print("✅ Fixtures geradas com sucesso!")
