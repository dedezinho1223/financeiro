"""CLI principal do Sistema Financeiro Automatizado.

Uso:
    financeiro conciliar BANCO INTERNO [--saida ARQUIVO]
    financeiro consolidar [PASTA] [--saida ARQUIVO]
    financeiro relatorio ARQUIVO [--tipo dre|fluxo|fechamento] [--saida ARQUIVO]
    financeiro validar ARQUIVO [--saida ARQUIVO]
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(
    name="financeiro",
    help="Sistema Financeiro Automatizado — Conciliação, Consolidação, Relatórios e Validação.",
    invoke_without_command=True,
)
console = Console()


@app.command()
def conciliar(
    banco: str = typer.Argument(..., help="Arquivo do extrato bancário (.xlsx)"),
    interno: str = typer.Argument(..., help="Arquivo do controle interno (.xlsx)"),
    saida: str = typer.Option("saida/conciliacao.xlsx", "--saida", "-s", help="Arquivo de saída"),
    config: str = typer.Option("config.yaml", "--config", "-c", help="Arquivo de configuração"),
):
    """Conciliação bancária: cruza extrato vs. controle interno."""
    from .conciliacao import conciliar as _conciliar

    _conciliar(banco, interno, saida=saida, config_path=config)


@app.command()
def consolidar(
    pasta: str = typer.Argument("dados", help="Pasta com planilhas para consolidar"),
    saida: str = typer.Option("saida/consolidado.xlsx", "--saida", "-s", help="Arquivo de saída"),
    config: str = typer.Option("config.yaml", "--config", "-c", help="Arquivo de configuração"),
):
    """Consolida múltiplas planilhas em uma base única padronizada."""
    from .consolidador import consolidar as _consolidar

    _consolidar(pasta, saida=saida, config_path=config)


@app.command()
def relatorio(
    arquivo: str = typer.Argument(..., help="Arquivo de lançamentos (.xlsx)"),
    tipo: str = typer.Option("dre", "--tipo", "-t", help="Tipo: dre, fluxo, fechamento"),
    saida: str = typer.Option("saida/relatorio.xlsx", "--saida", "-s", help="Arquivo de saída"),
    config: str = typer.Option("config.yaml", "--config", "-c", help="Arquivo de configuração"),
):
    """Gera relatórios financeiros (DRE, fluxo de caixa, fechamento mensal)."""
    from .relatorios import gerar_relatorio

    gerar_relatorio(arquivo, tipo=tipo, saida=saida, config_path=config)


@app.command()
def validar(
    arquivo: str = typer.Argument(..., help="Arquivo para validar (.xlsx)"),
    saida: str = typer.Option("saida/validacao.xlsx", "--saida", "-s", help="Relatório de erros"),
    config: str = typer.Option("config.yaml", "--config", "-c", help="Arquivo de configuração"),
):
    """Valida dados: CNPJ/CPF, duplicatas, datas, outliers, sequências."""
    from .validador import validar as _validar

    _validar(arquivo, saida=saida, config_path=config)


@app.command()
def menu():
    """Abre o menu interativo (modo fácil — sem decorar comandos)."""
    from .menu import menu_principal

    menu_principal()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Sistema Financeiro Automatizado."""
    if ctx.invoked_subcommand is None:
        # Sem subcomando: abre o menu interativo direto
        from .menu import menu_principal

        menu_principal()


if __name__ == "__main__":
    app()
