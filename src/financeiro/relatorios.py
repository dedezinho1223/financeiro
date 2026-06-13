"""Módulo gerador de relatórios financeiros.

Gera DRE simplificado, fluxo de caixa e fechamento mensal
a partir de dados brutos de lançamentos.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd
from rich.console import Console
from rich.panel import Panel

from .utils import (
    carregar_config,
    exibir_tabela,
    ler_excel,
    padronizar_data,
    padronizar_moeda,
)

console = Console()

# Palavras-chave para classificação automática de categorias
CLASSIFICACAO_AUTO = {
    "Vendas": ["venda", "receita", "faturamento", "nf saída"],
    "Serviços": ["serviço", "consultoria", "honorário", "prestação"],
    "Receita Financeira": ["juros recebido", "rendimento", "aplicação", "resgate"],
    "Pessoal": ["salário", "folha", "fgts", "inss", "vale", "benefício"],
    "Aluguel": ["aluguel", "locação", "condomínio", "iptu"],
    "Fornecedores": ["fornecedor", "compra", "mercadoria", "material", "estoque"],
    "Impostos": ["imposto", "tributo", "das", "simples", "icms", "iss", "pis", "cofins"],
    "Despesas Financeiras": ["tarifa", "taxa", "juros pago", "iof", "multa"],
    "Outros": [],
}


def gerar_relatorio(
    arquivo: str,
    tipo: str = "dre",
    saida: str = "saida/relatorio.xlsx",
    config_path: str = "config.yaml",
) -> dict:
    """Gera relatório financeiro a partir de lançamentos.

    Args:
        arquivo: Caminho do arquivo de lançamentos (.xlsx).
        tipo: Tipo do relatório ('dre', 'fluxo', 'fechamento').
        saida: Caminho do arquivo de saída.
        config_path: Caminho do arquivo de configuração.

    Returns:
        Dicionário com os totais do relatório.
    """
    config = carregar_config(config_path).get("relatorios", {})

    console.print(Panel(f"📈 Gerador de Relatórios — {tipo.upper()}", style="bold cyan"))

    df = ler_excel(arquivo)
    df = _preparar_lancamentos(df, config)

    if tipo == "dre":
        return _gerar_dre(df, saida)
    elif tipo == "fluxo":
        return _gerar_fluxo_caixa(df, saida, config.get("periodo", "mensal"))
    elif tipo == "fechamento":
        return _gerar_fechamento(df, saida)
    else:
        console.print(f"[red]❌ Tipo de relatório inválido: {tipo}[/red]")
        console.print("  Opções: dre, fluxo, fechamento")
        return {}


def _preparar_lancamentos(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Padroniza colunas de lançamentos e classifica categorias."""
    df = df.copy()

    # Detectar colunas
    col_map = {}
    for col in df.columns:
        cl = str(col).lower().strip()
        if any(t in cl for t in ["data", "dt", "date"]):
            col_map["data"] = col
        elif any(t in cl for t in ["valor", "vlr", "total", "montante"]):
            col_map["valor"] = col
        elif any(t in cl for t in ["descri", "histori", "memo", "obs"]):
            col_map["descricao"] = col
        elif any(t in cl for t in ["categ", "classif", "tipo", "conta"]):
            col_map["categoria"] = col

    # Renomear
    rename = {v: k for k, v in col_map.items()}
    df = df.rename(columns=rename)

    # Padronizar data e valor
    if "data" in df.columns:
        df["data"] = df["data"].apply(padronizar_data)

    if "valor" in df.columns:
        df["valor"] = df["valor"].apply(padronizar_moeda)
        df = df.dropna(subset=["valor"])

    # Classificar categorias vazias
    if "categoria" not in df.columns:
        df["categoria"] = ""

    df["categoria"] = df.apply(
        lambda row: _classificar(row) if pd.isna(row["categoria"]) or str(row["categoria"]).strip() == "" else row["categoria"],
        axis=1,
    )

    # Determinar tipo (receita/despesa) pelo sinal do valor
    df["tipo"] = df["valor"].apply(lambda v: "receita" if v >= 0 else "despesa")

    return df


def _classificar(row) -> str:
    """Classifica lançamento por palavras-chave na descrição."""
    descricao = str(row.get("descricao", "")).lower()

    for categoria, termos in CLASSIFICACAO_AUTO.items():
        for termo in termos:
            if termo in descricao:
                return categoria

    return "Outros"


def _gerar_dre(df: pd.DataFrame, saida: str) -> dict:
    """Gera DRE simplificado."""
    receitas = df[df["valor"] >= 0].groupby("categoria")["valor"].sum()
    despesas = df[df["valor"] < 0].groupby("categoria")["valor"].sum()

    total_receita = receitas.sum()
    total_despesa = abs(despesas.sum())
    lucro = total_receita - total_despesa

    # Montar DRE
    linhas_dre = []
    linhas_dre.append({"Conta": "═══ RECEITAS ═══", "Valor": ""})
    for cat, val in receitas.items():
        linhas_dre.append({"Conta": f"  {cat}", "Valor": f"R$ {val:,.2f}"})
    linhas_dre.append({"Conta": "TOTAL RECEITAS", "Valor": f"R$ {total_receita:,.2f}"})
    linhas_dre.append({"Conta": "", "Valor": ""})
    linhas_dre.append({"Conta": "═══ DESPESAS ═══", "Valor": ""})
    for cat, val in despesas.items():
        linhas_dre.append({"Conta": f"  {cat}", "Valor": f"R$ {abs(val):,.2f}"})
    linhas_dre.append({"Conta": "TOTAL DESPESAS", "Valor": f"R$ {total_despesa:,.2f}"})
    linhas_dre.append({"Conta": "", "Valor": ""})
    linhas_dre.append({"Conta": "═══ RESULTADO ═══", "Valor": f"R$ {lucro:,.2f}"})

    df_dre = pd.DataFrame(linhas_dre)

    # Salvar
    path = Path(saida)
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df_dre.to_excel(writer, sheet_name="DRE", index=False)

    # Exibir no terminal
    console.print()
    exibir_tabela(
        "📊 DRE Simplificado",
        ["Conta", "Valor"],
        [[r["Conta"], r["Valor"]] for r in linhas_dre if r["Conta"]],
    )
    console.print(f"\n  Salvo em: [green]{saida}[/green]\n")

    return {"receitas": total_receita, "despesas": total_despesa, "lucro": lucro}


def _gerar_fluxo_caixa(df: pd.DataFrame, saida: str, periodo: str) -> dict:
    """Gera fluxo de caixa agrupado por período."""
    if "data" not in df.columns or df["data"].isna().all():
        console.print("[red]❌ Coluna de data não encontrada ou vazia.[/red]")
        return {}

    df = df.dropna(subset=["data"]).copy()

    # Agrupar por período
    if periodo == "diario":
        df["periodo"] = df["data"].dt.strftime("%d/%m/%Y")
    elif periodo == "semanal":
        df["periodo"] = df["data"].dt.to_period("W").apply(lambda r: r.start_time.strftime("%d/%m/%Y"))
    else:  # mensal
        df["periodo"] = df["data"].dt.strftime("%m/%Y")

    # Calcular entradas e saídas
    fluxo = df.groupby("periodo").apply(
        lambda g: pd.Series({
            "Entradas": g[g["valor"] >= 0]["valor"].sum(),
            "Saídas": abs(g[g["valor"] < 0]["valor"].sum()),
            "Saldo": g["valor"].sum(),
        })
    ).reset_index()

    fluxo["Saldo Acumulado"] = fluxo["Saldo"].cumsum()

    # Salvar
    path = Path(saida)
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        fluxo.to_excel(writer, sheet_name="Fluxo de Caixa", index=False)

    # Exibir
    console.print()
    linhas = []
    for _, row in fluxo.iterrows():
        linhas.append([
            str(row["periodo"]),
            f"R$ {row['Entradas']:,.2f}",
            f"R$ {row['Saídas']:,.2f}",
            f"R$ {row['Saldo']:,.2f}",
            f"R$ {row['Saldo Acumulado']:,.2f}",
        ])

    exibir_tabela(
        "💰 Fluxo de Caixa",
        ["Período", "Entradas", "Saídas", "Saldo", "Acumulado"],
        linhas,
    )
    console.print(f"\n  Salvo em: [green]{saida}[/green]\n")

    return {"periodos": len(fluxo), "total_entradas": fluxo["Entradas"].sum(), "total_saidas": fluxo["Saídas"].sum()}


def _gerar_fechamento(df: pd.DataFrame, saida: str) -> dict:
    """Gera fechamento mensal com saldo inicial, movimentações e saldo final."""
    if "data" not in df.columns or df["data"].isna().all():
        console.print("[red]❌ Coluna de data não encontrada ou vazia.[/red]")
        return {}

    df = df.dropna(subset=["data"]).sort_values("data").copy()
    df["mes"] = df["data"].dt.to_period("M")

    meses = df["mes"].unique()
    linhas_fechamento = []
    saldo_acumulado = 0.0

    for mes in sorted(meses):
        dados_mes = df[df["mes"] == mes]
        entradas = dados_mes[dados_mes["valor"] >= 0]["valor"].sum()
        saidas = abs(dados_mes[dados_mes["valor"] < 0]["valor"].sum())
        saldo_inicial = saldo_acumulado
        saldo_acumulado += entradas - saidas

        linhas_fechamento.append({
            "Mês": str(mes),
            "Saldo Inicial": saldo_inicial,
            "Entradas": entradas,
            "Saídas": saidas,
            "Saldo Final": saldo_acumulado,
        })

    df_fechamento = pd.DataFrame(linhas_fechamento)

    # Salvar
    path = Path(saida)
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df_fechamento.to_excel(writer, sheet_name="Fechamento", index=False)

    # Exibir
    console.print()
    linhas = []
    for _, row in df_fechamento.iterrows():
        linhas.append([
            row["Mês"],
            f"R$ {row['Saldo Inicial']:,.2f}",
            f"R$ {row['Entradas']:,.2f}",
            f"R$ {row['Saídas']:,.2f}",
            f"R$ {row['Saldo Final']:,.2f}",
        ])

    exibir_tabela(
        "📅 Fechamento Mensal",
        ["Mês", "Saldo Inicial", "Entradas", "Saídas", "Saldo Final"],
        linhas,
    )
    console.print(f"\n  Salvo em: [green]{saida}[/green]\n")

    return {"meses": len(linhas_fechamento), "saldo_final": saldo_acumulado}
