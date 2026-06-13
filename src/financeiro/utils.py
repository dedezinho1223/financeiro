"""Funções utilitárias compartilhadas entre os módulos."""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import yaml
from rich.console import Console
from rich.table import Table

console = Console()


def carregar_config(caminho: str = "config.yaml") -> dict:
    """Carrega arquivo de configuração YAML.

    Args:
        caminho: Caminho para o arquivo de configuração.

    Returns:
        Dicionário com as configurações.
    """
    path = Path(caminho)
    if not path.exists():
        console.print("[yellow]⚠ Arquivo config.yaml não encontrado, usando padrões.[/yellow]")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def ler_excel(caminho: str) -> pd.DataFrame:
    """Lê arquivo Excel com tratamento de erros.

    Args:
        caminho: Caminho para o arquivo .xlsx.

    Returns:
        DataFrame com os dados do arquivo.

    Raises:
        FileNotFoundError: Se o arquivo não existe.
        ValueError: Se o arquivo está vazio ou corrompido.
    """
    path = Path(caminho)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
    if path.suffix.lower() not in (".xlsx", ".xls"):
        raise ValueError(f"Formato não suportado: {path.suffix}. Use .xlsx ou .xls")

    df = pd.read_excel(caminho, engine="openpyxl")
    if df.empty:
        raise ValueError(f"Arquivo vazio: {caminho}")
    return df


def padronizar_moeda(valor) -> Optional[float]:
    """Converte valor monetário brasileiro para float.

    Exemplos:
        'R$ 1.234,56' → 1234.56
        '1234.56' → 1234.56
        '-R$ 100,00' → -100.0

    Args:
        valor: Valor em string ou numérico.

    Returns:
        Float ou None se não conseguir converter.
    """
    if pd.isna(valor):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip()
    negativo = texto.startswith("-") or texto.startswith("(")

    # Remove R$, espaços, parênteses
    texto = re.sub(r"[R$\s()]+", "", texto)

    # Detecta formato brasileiro (1.234,56) vs americano (1,234.56)
    if re.search(r"\d\.\d{3},\d{2}$", texto):
        # Formato BR: remove pontos de milhar, troca vírgula por ponto
        texto = texto.replace(".", "").replace(",", ".")
    elif re.search(r"\d,\d{3}\.\d{2}$", texto):
        # Formato US: remove vírgulas de milhar
        texto = texto.replace(",", "")
    elif "," in texto and "." not in texto:
        # Só vírgula decimal: 1234,56
        texto = texto.replace(",", ".")
    # Se só tem ponto, assume decimal

    try:
        resultado = float(texto)
        return -abs(resultado) if negativo else resultado
    except ValueError:
        return None


def padronizar_data(valor) -> Optional[datetime]:
    """Converte data em diversos formatos para datetime.

    Suporta: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, DD.MM.YYYY, etc.

    Args:
        valor: Data em string ou datetime.

    Returns:
        Datetime ou None se não conseguir converter.
    """
    if pd.isna(valor):
        return None
    if isinstance(valor, datetime):
        return valor
    if isinstance(valor, pd.Timestamp):
        return valor.to_pydatetime()

    texto = str(valor).strip()

    formatos = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d/%m/%y",
        "%d-%m-%y",
        "%Y/%m/%d",
        "%d %b %Y",
        "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ]

    for fmt in formatos:
        try:
            return datetime.strptime(texto, fmt)
        except ValueError:
            continue

    return None


def validar_cnpj(cnpj: str) -> bool:
    """Valida CNPJ pelos dígitos verificadores.

    Args:
        cnpj: String com o CNPJ (com ou sem formatação).

    Returns:
        True se válido, False caso contrário.
    """
    cnpj = re.sub(r"[^0-9]", "", str(cnpj))

    if len(cnpj) != 14:
        return False
    if len(set(cnpj)) == 1:
        return False

    # Primeiro dígito verificador
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto

    if int(cnpj[12]) != digito1:
        return False

    # Segundo dígito verificador
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto

    return int(cnpj[13]) == digito2


def validar_cpf(cpf: str) -> bool:
    """Valida CPF pelos dígitos verificadores.

    Args:
        cpf: String com o CPF (com ou sem formatação).

    Returns:
        True se válido, False caso contrário.
    """
    cpf = re.sub(r"[^0-9]", "", str(cpf))

    if len(cpf) != 11:
        return False
    if len(set(cpf)) == 1:
        return False

    # Primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto

    if int(cpf[9]) != digito1:
        return False

    # Segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto

    return int(cpf[10]) == digito2


def salvar_excel(df: pd.DataFrame, caminho: str, nome_aba: str = "Dados") -> Path:
    """Salva DataFrame como Excel formatado.

    Args:
        df: DataFrame para salvar.
        caminho: Caminho de destino.
        nome_aba: Nome da aba na planilha.

    Returns:
        Path do arquivo salvo.
    """
    path = Path(caminho)
    path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=nome_aba, index=False)

    return path


def exibir_tabela(titulo: str, colunas: list[str], linhas: list[list], cor: str = "cyan"):
    """Exibe tabela formatada no terminal com rich.

    Args:
        titulo: Título da tabela.
        colunas: Lista de nomes das colunas.
        linhas: Lista de listas com os valores.
        cor: Cor do cabeçalho.
    """
    tabela = Table(title=titulo, show_lines=True)
    for col in colunas:
        tabela.add_column(col, style=cor)
    for linha in linhas:
        tabela.add_row(*[str(v) for v in linha])
    console.print(tabela)
