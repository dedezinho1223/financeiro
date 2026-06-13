"""Módulo consolidador de planilhas.

Junta múltiplas planilhas em uma base única padronizada,
tratando formatos diferentes de data, moeda e nomes de coluna.
"""

from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz
from rich.console import Console
from rich.panel import Panel
from rich.progress import track

from .utils import (
    carregar_config,
    exibir_tabela,
    padronizar_data,
    padronizar_moeda,
    salvar_excel,
)

console = Console()

# Mapeamento de nomes comuns de colunas financeiras
MAPA_COLUNAS = {
    "data": ["data", "dt", "date", "data_pgto", "dt_pagamento", "data pagamento", "vencimento"],
    "valor": ["valor", "vlr", "value", "montante", "total", "quantia"],
    "descricao": ["descricao", "descrição", "historico", "histórico", "memo", "obs", "observacao"],
    "categoria": ["categoria", "cat", "tipo", "classificacao", "classificação", "conta"],
    "documento": ["documento", "doc", "nf", "nota", "nota_fiscal", "numero"],
    "fornecedor": ["fornecedor", "cliente", "favorecido", "pagador", "recebedor", "nome"],
}


def consolidar(
    pasta: str = "dados",
    saida: str = "saida/consolidado.xlsx",
    config_path: str = "config.yaml",
) -> dict:
    """Consolida múltiplas planilhas em uma base única.

    Args:
        pasta: Pasta contendo os arquivos .xlsx para consolidar.
        saida: Caminho do arquivo consolidado de saída.
        config_path: Caminho do arquivo de configuração.

    Returns:
        Dicionário com estatísticas da consolidação.
    """
    config = carregar_config(config_path).get("consolidador", {})
    pasta_path = Path(pasta)

    console.print(Panel("📂 Consolidador de Planilhas", style="bold cyan"))
    console.print(f"  Pasta: [green]{pasta_path.absolute()}[/green]\n")

    # Encontrar arquivos Excel
    arquivos = list(pasta_path.glob("*.xlsx")) + list(pasta_path.glob("*.xls"))
    arquivos = [a for a in arquivos if not a.name.startswith("~$")]

    if not arquivos:
        console.print("[red]❌ Nenhum arquivo .xlsx encontrado na pasta.[/red]")
        return {"arquivos": 0, "linhas": 0, "duplicatas": 0}

    console.print(f"  Encontrados: [cyan]{len(arquivos)}[/cyan] arquivo(s)\n")

    # Processar cada arquivo
    dfs = []
    log_transformacoes = []

    for arquivo in track(arquivos, description="Processando..."):
        try:
            df = pd.read_excel(arquivo, engine="openpyxl")
            if df.empty:
                log_transformacoes.append(f"⚠️  {arquivo.name}: vazio, ignorado")
                continue

            # Renomear colunas para padrão
            df, mapeamento = _mapear_colunas(df)
            if mapeamento:
                log_transformacoes.append(
                    f"📝 {arquivo.name}: {', '.join(f'{k}→{v}' for k, v in mapeamento.items())}"
                )

            # Padronizar valores
            if "data" in df.columns:
                df["data"] = df["data"].apply(padronizar_data)

            if "valor" in df.columns:
                df["valor"] = df["valor"].apply(padronizar_moeda)

            # Adicionar origem
            df["_origem"] = arquivo.name

            dfs.append(df)

        except Exception as e:
            log_transformacoes.append(f"❌ {arquivo.name}: erro - {e}")

    if not dfs:
        console.print("[red]❌ Nenhum arquivo pôde ser processado.[/red]")
        return {"arquivos": 0, "linhas": 0, "duplicatas": 0}

    # Unir tudo
    df_final = pd.concat(dfs, ignore_index=True, sort=False)
    total_bruto = len(df_final)

    # Remover duplicatas exatas (ignorando coluna de origem)
    colunas_comparacao = [c for c in df_final.columns if c != "_origem"]
    df_final = df_final.drop_duplicates(subset=colunas_comparacao, keep="first")
    duplicatas = total_bruto - len(df_final)

    if duplicatas > 0:
        log_transformacoes.append(f"🔄 Removidas {duplicatas} duplicata(s)")

    # Salvar
    salvar_excel(df_final, saida, nome_aba="Consolidado")

    # Estatísticas
    stats = {
        "arquivos": len(arquivos),
        "linhas": len(df_final),
        "duplicatas": duplicatas,
        "colunas": len(df_final.columns),
    }

    # Exibir resumo
    console.print()
    exibir_tabela(
        "📊 Resumo da Consolidação",
        ["Métrica", "Valor"],
        [
            ["Arquivos processados", str(stats["arquivos"])],
            ["Linhas consolidadas", str(stats["linhas"])],
            ["Duplicatas removidas", str(stats["duplicatas"])],
            ["Colunas no resultado", str(stats["colunas"])],
        ],
    )

    if log_transformacoes:
        console.print("\n[bold]Transformações aplicadas:[/bold]")
        for log in log_transformacoes:
            console.print(f"  {log}")

    console.print(f"\n  Resultado salvo em: [green]{saida}[/green]\n")

    return stats


def _mapear_colunas(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Mapeia colunas do DataFrame para nomes padronizados usando fuzzy match.

    Returns:
        Tupla (DataFrame com colunas renomeadas, dicionário de mapeamentos feitos).
    """
    mapeamento = {}
    colunas_usadas = set()

    for padrao, variantes in MAPA_COLUNAS.items():
        melhor_col = None
        melhor_score = 0

        for col in df.columns:
            if col in colunas_usadas:
                continue

            col_lower = str(col).lower().strip()

            # Match exato primeiro
            if col_lower in variantes:
                melhor_col = col
                melhor_score = 100
                break

            # Fuzzy match
            for variante in variantes:
                score = fuzz.ratio(col_lower, variante)
                if score > melhor_score and score >= 75:
                    melhor_score = score
                    melhor_col = col

        if melhor_col and melhor_score >= 75:
            if str(melhor_col).lower().strip() != padrao:
                mapeamento[str(melhor_col)] = padrao
            colunas_usadas.add(melhor_col)

    if mapeamento:
        df = df.rename(columns={k: v for k, v in mapeamento.items() if k in df.columns})

    return df, mapeamento
