"""Testes para o módulo cnpj_checker (com mock HTTP)."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from financeiro.cnpj_checker import (
    _carregar_cache,
    _checar_cnpjs_no_validador,
    _codigo_para_situacao,
    _consultar_cnpj_api,
    _formatar_cnpj,
    _salvar_cache,
)


class TestConsultarCnpjApi:
    """Testes da função de consulta individual."""

    @patch("financeiro.cnpj_checker.requests.get")
    def test_retorno_sucesso(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "razao_social": "EMPRESA TESTE LTDA",
            "situacao_cadastral": 2,
        }
        mock_get.return_value = resp

        resultado = _consultar_cnpj_api("11222333000181", "https://api.test/{}", timeout=5)
        assert resultado is not None
        assert resultado["razao_social"] == "EMPRESA TESTE LTDA"

    @patch("financeiro.cnpj_checker.requests.get")
    def test_cnpj_nao_encontrado_404(self, mock_get):
        resp = MagicMock()
        resp.status_code = 404
        mock_get.return_value = resp

        resultado = _consultar_cnpj_api("00000000000000", "https://api.test/{}", timeout=5)
        assert resultado is not None
        assert "NAO ENCONTRADO" in resultado.get("situacao_cadastral", "")

    @patch("financeiro.cnpj_checker.requests.get")
    def test_sem_conexao(self, mock_get):
        import requests as real_requests
        mock_get.side_effect = real_requests.ConnectionError("Sem rede")

        resultado = _consultar_cnpj_api("11222333000181", "https://api.test/{}", timeout=5)
        assert resultado is None

    @patch("financeiro.cnpj_checker.time.sleep")
    @patch("financeiro.cnpj_checker.requests.get")
    def test_rate_limit_429_retry(self, mock_get, mock_sleep):
        resp_429 = MagicMock()
        resp_429.status_code = 429
        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = {"razao_social": "OK", "situacao_cadastral": 2}

        mock_get.side_effect = [resp_429, resp_200]

        resultado = _consultar_cnpj_api("11222333000181", "https://api.test/{}", timeout=5)
        assert resultado is not None
        assert resultado["razao_social"] == "OK"


class TestCache:
    """Testes de cache."""

    def test_carregar_cache_inexistente(self, tmp_path):
        caminho = tmp_path / "nao_existe.json"
        cache = _carregar_cache(caminho, cache_dias=30)
        assert cache == {}

    def test_salvar_e_carregar_cache(self, tmp_path):
        caminho = tmp_path / "cache.json"
        dados = {
            "11222333000181": {
                "razao_social": "TESTE",
                "situacao_cadastral": 2,
                "consultado_em": datetime.now().isoformat(),
            }
        }
        _salvar_cache(dados, caminho)
        cache = _carregar_cache(caminho, cache_dias=30)
        assert "11222333000181" in cache

    def test_cache_expirado_nao_carrega(self, tmp_path):
        caminho = tmp_path / "cache.json"
        dados = {
            "11222333000181": {
                "razao_social": "TESTE",
                "situacao_cadastral": 2,
                "consultado_em": "2020-01-01T00:00:00",
            }
        }
        _salvar_cache(dados, caminho)
        cache = _carregar_cache(caminho, cache_dias=30)
        assert "11222333000181" not in cache

    def test_cache_corrompido_retorna_vazio(self, tmp_path):
        caminho = tmp_path / "cache.json"
        caminho.write_text("isso nao e json {{{{", encoding="utf-8")
        cache = _carregar_cache(caminho, cache_dias=30)
        assert cache == {}


class TestIntegracaoValidador:
    """Teste da versão integrada ao validador."""

    @patch("financeiro.cnpj_checker._consultar_cnpj_api")
    @patch("financeiro.cnpj_checker._carregar_cache")
    @patch("financeiro.cnpj_checker._salvar_cache")
    def test_cnpj_inativo_gera_erro(self, mock_salvar, mock_cache, mock_api):
        mock_cache.return_value = {}
        mock_api.return_value = {
            "razao_social": "EMPRESA BAIXADA",
            "situacao_cadastral": 8,
            "consultado_em": datetime.now().isoformat(),
        }

        df = pd.DataFrame({"cnpj": ["11.222.333/0001-81"], "valor": ["1000"]})
        config = {"api": "brasilapi", "intervalo_requests": 0, "timeout": 5, "cache_dir": ".cache", "cache_dias": 30}

        erros = _checar_cnpjs_no_validador(df, config)
        assert len(erros) >= 1
        assert erros[0]["Tipo Erro"] == "CNPJ inativo"
        assert "BAIXADA" in erros[0]["Sugestão"]


class TestUtilitarios:
    """Testes de funções auxiliares."""

    def test_formatar_cnpj(self):
        assert _formatar_cnpj("11222333000181") == "11.222.333/0001-81"

    def test_codigo_para_situacao(self):
        assert _codigo_para_situacao(2) == "ATIVA"
        assert _codigo_para_situacao(8) == "BAIXADA"
        assert _codigo_para_situacao(3) == "SUSPENSA"
        assert _codigo_para_situacao(99) == "CODIGO 99"
