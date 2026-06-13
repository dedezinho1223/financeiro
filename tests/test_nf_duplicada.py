"""Testes para detecção de NF duplicada (pagamento em dobro)."""

from datetime import datetime, timedelta

import pandas as pd
import pytest

from financeiro.validador import _detectar_nf_duplicadas


def _criar_df(dados: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(dados)


class TestRegra1_MesmoNfMesmoFornecedor:
    """Regra 1: Mesmo NF + mesmo fornecedor = duplicata certa."""

    def test_detecta_nf_duplicada_mesmo_fornecedor(self):
        df = _criar_df([
            {"nf": "001", "fornecedor": "Empresa ABC", "valor": "1000", "data": "01/01/2025"},
            {"nf": "002", "fornecedor": "Empresa XYZ", "valor": "2000", "data": "02/01/2025"},
            {"nf": "001", "fornecedor": "Empresa ABC", "valor": "1000", "data": "05/01/2025"},
        ])
        erros = _detectar_nf_duplicadas(df)
        tipos = [e["Tipo Erro"] for e in erros]
        assert "NF duplicada (mesmo fornecedor)" in tipos

    def test_nao_flagra_nf_diferente(self):
        df = _criar_df([
            {"nf": "001", "fornecedor": "Empresa ABC", "valor": "1000", "data": "01/01/2025"},
            {"nf": "002", "fornecedor": "Empresa ABC", "valor": "1000", "data": "02/01/2025"},
        ])
        erros = _detectar_nf_duplicadas(df)
        tipos_r1 = [e for e in erros if e["Tipo Erro"] == "NF duplicada (mesmo fornecedor)"]
        assert len(tipos_r1) == 0

    def test_nao_flagra_mesmo_nf_fornecedor_diferente(self):
        df = _criar_df([
            {"nf": "001", "fornecedor": "Empresa ABC", "valor": "1000", "data": "01/01/2025"},
            {"nf": "001", "fornecedor": "Empresa XYZ", "valor": "1000", "data": "02/01/2025"},
        ])
        erros = _detectar_nf_duplicadas(df)
        tipos_r1 = [e for e in erros if e["Tipo Erro"] == "NF duplicada (mesmo fornecedor)"]
        assert len(tipos_r1) == 0


class TestRegra2_MesmoNfMesmoValorDatasDiferentes:
    """Regra 2: Mesmo NF + mesmo valor + datas diferentes = mesma NF paga 2x."""

    def test_detecta_mesma_nf_valor_igual_data_diferente(self):
        df = _criar_df([
            {"nf": "100", "fornecedor": "Forn A", "valor": "R$ 5.000,00", "data": "10/03/2025"},
            {"nf": "100", "fornecedor": "Forn B", "valor": "R$ 5.000,00", "data": "15/03/2025"},
        ])
        erros = _detectar_nf_duplicadas(df)
        tipos = [e["Tipo Erro"] for e in erros]
        assert "NF duplicada (mesmo valor, data diferente)" in tipos

    def test_nao_flagra_mesma_nf_valores_diferentes(self):
        df = _criar_df([
            {"nf": "100", "fornecedor": "Forn A", "valor": "R$ 5.000,00", "data": "10/03/2025"},
            {"nf": "100", "fornecedor": "Forn A", "valor": "R$ 3.000,00", "data": "15/03/2025"},
        ])
        erros = _detectar_nf_duplicadas(df)
        tipos_r2 = [e for e in erros if e["Tipo Erro"] == "NF duplicada (mesmo valor, data diferente)"]
        assert len(tipos_r2) == 0


class TestRegra3_FornecedorValorJanelaDias:
    """Regra 3: Mesmo fornecedor + mesmo valor dentro da janela = suspeito."""

    def test_detecta_pagamento_suspeito_dentro_janela(self):
        df = _criar_df([
            {"nf": "200", "fornecedor": "Forn X", "valor": "R$ 1.200,00", "data": "01/06/2025"},
            {"nf": "201", "fornecedor": "Forn X", "valor": "R$ 1.200,00", "data": "04/06/2025"},
        ])
        erros = _detectar_nf_duplicadas(df, janela_dias=5)
        tipos = [e["Tipo Erro"] for e in erros]
        assert "Pagamento suspeito (fornecedor + valor similar)" in tipos

    def test_nao_flagra_fora_da_janela(self):
        df = _criar_df([
            {"nf": "200", "fornecedor": "Forn X", "valor": "R$ 1.200,00", "data": "01/06/2025"},
            {"nf": "201", "fornecedor": "Forn X", "valor": "R$ 1.200,00", "data": "20/06/2025"},
        ])
        erros = _detectar_nf_duplicadas(df, janela_dias=5)
        tipos_r3 = [e for e in erros if e["Tipo Erro"] == "Pagamento suspeito (fornecedor + valor similar)"]
        assert len(tipos_r3) == 0

    def test_nao_flagra_valores_diferentes_mesmo_fornecedor(self):
        df = _criar_df([
            {"nf": "200", "fornecedor": "Forn X", "valor": "R$ 1.200,00", "data": "01/06/2025"},
            {"nf": "201", "fornecedor": "Forn X", "valor": "R$ 800,00", "data": "03/06/2025"},
        ])
        erros = _detectar_nf_duplicadas(df, janela_dias=5)
        tipos_r3 = [e for e in erros if e["Tipo Erro"] == "Pagamento suspeito (fornecedor + valor similar)"]
        assert len(tipos_r3) == 0


class TestCasosEspeciais:
    """Casos limites e sem colunas necessárias."""

    def test_sem_coluna_nf_retorna_vazio(self):
        df = _criar_df([
            {"descricao": "Algo", "valor": "100", "data": "01/01/2025"},
        ])
        erros = _detectar_nf_duplicadas(df)
        assert erros == []

    def test_dataframe_vazio(self):
        df = pd.DataFrame(columns=["nf", "fornecedor", "valor", "data"])
        erros = _detectar_nf_duplicadas(df)
        assert erros == []

    def test_uma_linha_so(self):
        df = _criar_df([
            {"nf": "001", "fornecedor": "ABC", "valor": "1000", "data": "01/01/2025"},
        ])
        erros = _detectar_nf_duplicadas(df)
        assert erros == []

    def test_nf_nan_ignorada(self):
        df = _criar_df([
            {"nf": None, "fornecedor": "ABC", "valor": "1000", "data": "01/01/2025"},
            {"nf": None, "fornecedor": "ABC", "valor": "1000", "data": "02/01/2025"},
        ])
        erros = _detectar_nf_duplicadas(df)
        tipos_r1 = [e for e in erros if "NF duplicada" in e["Tipo Erro"]]
        assert len(tipos_r1) == 0
