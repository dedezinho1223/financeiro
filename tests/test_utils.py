"""Testes unitários para funções utilitárias."""

import pytest

from financeiro.utils import (
    padronizar_data,
    padronizar_moeda,
    validar_cnpj,
    validar_cpf,
)


class TestPadronizarMoeda:
    """Testes para conversão de valores monetários brasileiros."""

    def test_formato_brasileiro(self):
        assert padronizar_moeda("R$ 1.234,56") == 1234.56

    def test_formato_brasileiro_sem_cifrao(self):
        assert padronizar_moeda("1.234,56") == 1234.56

    def test_virgula_decimal_simples(self):
        assert padronizar_moeda("100,50") == 100.50

    def test_valor_inteiro(self):
        assert padronizar_moeda("1000") == 1000.0

    def test_valor_float(self):
        assert padronizar_moeda(1234.56) == 1234.56

    def test_valor_negativo(self):
        assert padronizar_moeda("-R$ 100,00") == -100.0

    def test_valor_com_parenteses(self):
        assert padronizar_moeda("(1.000,00)") == -1000.0

    def test_valor_nulo(self):
        assert padronizar_moeda(None) is None

    def test_formato_americano(self):
        assert padronizar_moeda("1,234.56") == 1234.56

    def test_zero(self):
        assert padronizar_moeda("0,00") == 0.0

    def test_centavos(self):
        assert padronizar_moeda("0,99") == 0.99


class TestPadronizarData:
    """Testes para conversão de datas em vários formatos."""

    def test_formato_brasileiro(self):
        result = padronizar_data("25/12/2024")
        assert result.day == 25
        assert result.month == 12
        assert result.year == 2024

    def test_formato_iso(self):
        result = padronizar_data("2024-12-25")
        assert result.day == 25
        assert result.month == 12
        assert result.year == 2024

    def test_formato_com_traco(self):
        result = padronizar_data("25-12-2024")
        assert result.day == 25
        assert result.month == 12
        assert result.year == 2024

    def test_formato_com_ponto(self):
        result = padronizar_data("25.12.2024")
        assert result.day == 25
        assert result.month == 12
        assert result.year == 2024

    def test_formato_ano_curto(self):
        result = padronizar_data("25/12/24")
        assert result.day == 25
        assert result.month == 12

    def test_valor_nulo(self):
        assert padronizar_data(None) is None

    def test_formato_invalido(self):
        assert padronizar_data("abc") is None


class TestValidarCNPJ:
    """Testes para validação de CNPJ."""

    def test_cnpj_valido(self):
        # CNPJ da Petrobras
        assert validar_cnpj("33.000.167/0001-01") is True

    def test_cnpj_valido_sem_formatacao(self):
        assert validar_cnpj("33000167000101") is True

    def test_cnpj_invalido(self):
        assert validar_cnpj("11.222.333/0001-99") is False

    def test_cnpj_todos_iguais(self):
        assert validar_cnpj("11111111111111") is False

    def test_cnpj_curto(self):
        assert validar_cnpj("1234567") is False

    def test_cnpj_vazio(self):
        assert validar_cnpj("") is False


class TestValidarCPF:
    """Testes para validação de CPF."""

    def test_cpf_valido(self):
        assert validar_cpf("529.982.247-25") is True

    def test_cpf_valido_sem_formatacao(self):
        assert validar_cpf("52998224725") is True

    def test_cpf_invalido(self):
        assert validar_cpf("111.222.333-99") is False

    def test_cpf_todos_iguais(self):
        assert validar_cpf("11111111111") is False

    def test_cpf_curto(self):
        assert validar_cpf("12345") is False

    def test_cpf_vazio(self):
        assert validar_cpf("") is False
