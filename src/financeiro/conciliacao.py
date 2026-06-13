"""Módulo de conciliação bancária automática.

Cruza extrato bancário vs. lançamentos internos e aponta divergências.
"""

from datetime import timedelta
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz
from rich.console import Console
from rich.panel import Panel
from rich.progress import track

from .utils import (
    carregar_config,
    exibir_tabela,
    ler_excel,
    padronizar_data,
    padronizar_moeda,
    salvar_excel,
)

console = Console()


def conciliar(
    arquivo_banco: str,
    arquivo_interno: str,
    saida: str = "saida/conciliacao.xlsx",
    config_path: str = "config.yaml",
) -> dict:
    """Executa conciliação bancária entre extrato e controle interno.

    Args:
        arquivo_banco: Caminho do extrato bancário (.xlsx).
        arquivo_interno: Caminho do controle interno (.xlsx).
        saida: Caminho do arquivo de resultado.
        config_path: Caminho do arquivo de configuração.

    Returns:
        Dicionário com estatísticas da conciliação.
    """
    config = carregar_config(config_path).get("conciliacao", {})
    tolerancia_dias = config.get("tolerancia_dias", 1)
    tolerancia_valor = config.get("tolerancia_valor", 0.01)

    console.print(Panel("🏦 Conciliação Bancária", style="bold cyan"))
    console.print(f"  Extrato: [green]{arquivo_banco}[/green]")
    console.print(f"  Interno: [green]{arquivo_interno}[/green]")
    console.print(f"  Tolerância: ±{tolerancia_dias} dia(s), ±R$ {tolerancia_valor:.2f}\n")

    # Carregar dados
    df_banco = ler_excel(arquivo_banco)
    df_interno = ler_excel(arquivo_interno)

    # Detectar e padronizar colunas
    df_banco = _preparar_dataframe(df_banco, config.get("colunas_banco", {}))
    df_interno = _preparar_dataframe(df_interno, config.get("colunas_interno", {}))

    # Realizar conciliação
    conciliados = []
    somente_banco = []
    somente_interno = []
    divergencias = []

    interno_usado = set()

    for idx_b, row_b in track(
        df_banco.iterrows(), total=len(df_banco), description="Conciliando..."
    ):
        melhor_match = None
        melhor_score = 0

        for idx_i, row_i in df_interno.iterrows():
            if idx_i in interno_usado:
                continue

            # Verificar valor
            diff_valor = abs(row_b["_valor"] - row_i["_valor"])
            if diff_valor > tolerancia_valor:
                continue

            # Verificar data
            if pd.notna(row_b["_data"]) and pd.notna(row_i["_data"]):
                diff_dias = abs((row_b["_data"] - row_i["_data"]).days)
                if diff_dias > tolerancia_dias:
                    continue

            # Score por similaridade da descrição
            score = fuzz.token_sort_ratio(
                str(row_b.get("_descricao", "")),
                str(row_i.get("_descricao", "")),
            )

            # Bonus por data exata
            if pd.notna(row_b["_data"]) and pd.notna(row_i["_data"]):
                if row_b["_data"] == row_i["_data"]:
                    score += 20

            if score > melhor_score:
                melhor_score = score
                melhor_match = idx_i

        if melhor_match is not None and melhor_score >= 30:
            interno_usado.add(melhor_match)
            row_i = df_interno.loc[melhor_match]
            diff = row_b["_valor"] - row_i["_valor"]

            if abs(diff) <= tolerancia_valor:
                conciliados.append({
                    "Data Banco": row_b.get("_data", ""),
                    "Descrição Banco": row_b.get("_descricao", ""),
                    "Valor Banco": row_b["_valor"],
                    "Data Interno": row_i.get("_data", ""),
                    "Descrição Interno": row_i.get("_descricao", ""),
                    "Valor Interno": row_i["_valor"],
                    "Score": melhor_score,
                })
            else:
                divergencias.append({
                    "Data Banco": row_b.get("_data", ""),
                    "Descrição Banco": row_b.get("_descricao", ""),
                    "Valor Banco": row_b["_valor"],
                    "Data Interno": row_i.get("_data", ""),
                    "Descrição Interno": row_i.get("_descricao", ""),
                    "Valor Interno": row_i["_valor"],
                    "Diferença": diff,
                })
        else:
            somente_banco.append({
                "Data": row_b.get("_data", ""),
                "Descrição": row_b.get("_descricao", ""),
                "Valor": row_b["_valor"],
            })

    # Itens do interno sem match
    for idx_i, row_i in df_interno.iterrows():
        if idx_i not in interno_usado:
            somente_interno.append({
                "Data": row_i.get("_data", ""),
                "Descrição": row_i.get("_descricao", ""),
                "Valor": row_i["_valor"],
            })

    # Salvar resultado
    _salvar_resultado(conciliados, somente_banco, somente_interno, divergencias, saida)

    # Exibir resumo
    stats = {
        "conciliados": len(conciliados),
        "somente_banco": len(somente_banco),
        "somente_interno": len(somente_interno),
        "divergencias": len(divergencias),
    }

    console.print()
    exibir_tabela(
        "📊 Resumo da Conciliação",
        ["Status", "Quantidade"],
        [
            ["✅ Conciliados", str(stats["conciliados"])],
            ["🔴 Só no banco (não lançado)", str(stats["somente_banco"])],
            ["🟡 Só no interno (não apareceu)", str(stats["somente_interno"])],
            ["⚠️  Divergência de valor", str(stats["divergencias"])],
        ],
    )
    console.print(f"\n  Resultado salvo em: [green]{saida}[/green]\n")

    return stats


def _preparar_dataframe(df: pd.DataFrame, config_colunas: dict) -> pd.DataFrame:
    """Detecta e padroniza colunas de data, valor e descrição."""
    df = df.copy()

    # Mapear colunas pelo config ou detectar automaticamente
    col_data = config_colunas.get("data") or _detectar_coluna(df, ["data", "dt", "date", "vencimento"])
    col_valor = config_colunas.get("valor") or _detectar_coluna(df, ["valor", "vlr", "value", "montante", "total"])
    col_desc = config_colunas.get("descricao") or _detectar_coluna(
        df, ["descricao", "descrição", "historico", "histórico", "memo", "obs"]
    )

    # Padronizar
    df["_data"] = df[col_data].apply(padronizar_data) if col_data else None
    df["_valor"] = df[col_valor].apply(padronizar_moeda) if col_valor else 0.0
    df["_descricao"] = df[col_desc].astype(str) if col_desc else ""

    # Remover linhas sem valor
    df = df.dropna(subset=["_valor"])
    df["_valor"] = df["_valor"].astype(float)

    return df


def _detectar_coluna(df: pd.DataFrame, termos: list[str]) -> str | None:
    """Detecta coluna pelo nome usando correspondência parcial."""
    for col in df.columns:
        col_lower = str(col).lower().strip()
        for termo in termos:
            if termo in col_lower:
                return col
    return None


def _salvar_resultado(
    conciliados: list,
    somente_banco: list,
    somente_interno: list,
    divergencias: list,
    caminho: str,
):
    """Salva resultado da conciliação em Excel com múltiplas abas."""
    path = Path(caminho)
    path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        if conciliados:
            pd.DataFrame(conciliados).to_excel(writer, sheet_name="Conciliados", index=False)
        if somente_banco:
            pd.DataFrame(somente_banco).to_excel(writer, sheet_name="Só no Banco", index=False)
        if somente_interno:
            pd.DataFrame(somente_interno).to_excel(writer, sheet_name="Só no Interno", index=False)
        if divergencias:
            pd.DataFrame(divergencias).to_excel(writer, sheet_name="Divergências", index=False)

        # Aba de resumo
        resumo = pd.DataFrame([
            {"Status": "Conciliados", "Quantidade": len(conciliados)},
            {"Status": "Só no Banco", "Quantidade": len(somente_banco)},
            {"Status": "Só no Interno", "Quantidade": len(somente_interno)},
            {"Status": "Divergências", "Quantidade": len(divergencias)},
        ])
        resumo.to_excel(writer, sheet_name="Resumo", index=False)
