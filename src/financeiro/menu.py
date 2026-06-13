"""Menu interativo do Sistema Financeiro.

Permite usar o sistema sem decorar comandos — basta rodar e seguir as perguntas.
"""

import os
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.table import Table

console = Console()


def listar_arquivos_xlsx(pasta: str = ".") -> list[Path]:
    """Lista arquivos .xlsx em uma pasta."""
    path = Path(pasta)
    if not path.exists():
        return []
    arquivos = list(path.glob("*.xlsx")) + list(path.glob("*.xls"))
    return [a for a in arquivos if not a.name.startswith("~$")]


def escolher_arquivo(mensagem: str = "Escolha o arquivo", pasta: str = ".") -> str:
    """Mostra lista de arquivos e deixa o usuário escolher por número."""
    arquivos = listar_arquivos_xlsx(pasta)

    if not arquivos:
        console.print(f"\n[yellow]Nenhum arquivo .xlsx encontrado em: {Path(pasta).absolute()}[/yellow]")
        console.print("[dim]Coloque seus arquivos Excel na pasta e tente novamente.[/dim]\n")
        caminho = Prompt.ask("Digite o caminho completo do arquivo (ou 'voltar')")
        if caminho.lower() == "voltar":
            return ""
        return caminho

    console.print(f"\n[bold cyan]{mensagem}:[/bold cyan]\n")
    for i, arq in enumerate(arquivos, 1):
        tamanho = arq.stat().st_size / 1024
        console.print(f"  [green]{i}[/green]) {arq.name} [dim]({tamanho:.0f} KB)[/dim]")

    console.print(f"  [green]{len(arquivos)+1}[/green]) Digitar caminho manualmente")
    console.print()

    escolha = IntPrompt.ask("Número", default=1)

    if escolha == len(arquivos) + 1:
        return Prompt.ask("Caminho do arquivo")
    elif 1 <= escolha <= len(arquivos):
        return str(arquivos[escolha - 1])
    else:
        console.print("[red]Opção inválida.[/red]")
        return ""


def menu_conciliar():
    """Menu interativo para conciliação bancária."""
    console.print(Panel("[bold]Conciliação Bancária[/bold]\n\nVou cruzar seu extrato com o controle interno.", style="cyan"))

    console.print("[bold]1. Extrato bancário[/bold] (arquivo baixado do banco)")
    banco = escolher_arquivo("Selecione o EXTRATO BANCÁRIO", "dados")
    if not banco:
        return

    console.print("\n[bold]2. Controle interno[/bold] (sua planilha de lançamentos)")
    interno = escolher_arquivo("Selecione o CONTROLE INTERNO", "dados")
    if not interno:
        return

    saida = "saida/conciliacao.xlsx"
    console.print(f"\n[dim]Resultado será salvo em: {saida}[/dim]\n")

    from financeiro.conciliacao import conciliar
    conciliar(banco, interno, saida=saida)


def menu_consolidar():
    """Menu interativo para consolidação de planilhas."""
    console.print(Panel("[bold]Consolidar Planilhas[/bold]\n\nVou juntar várias planilhas em uma só.", style="cyan"))

    pasta_padrao = "dados"
    console.print(f"\n  Pasta padrão: [green]{Path(pasta_padrao).absolute()}[/green]")
    console.print("  [dim]Coloque todos os arquivos que quer consolidar nessa pasta.[/dim]\n")

    arquivos = listar_arquivos_xlsx(pasta_padrao)
    if arquivos:
        console.print(f"  Encontrados: [cyan]{len(arquivos)}[/cyan] arquivo(s):")
        for arq in arquivos:
            console.print(f"    • {arq.name}")
        console.print()

    usar_padrao = Prompt.ask("Usar pasta 'dados/'?", choices=["s", "n"], default="s")

    if usar_padrao == "s":
        pasta = pasta_padrao
    else:
        pasta = Prompt.ask("Digite o caminho da pasta")

    saida = "saida/consolidado.xlsx"
    console.print(f"\n[dim]Resultado será salvo em: {saida}[/dim]\n")

    from financeiro.consolidador import consolidar
    consolidar(pasta, saida=saida)


def menu_relatorio():
    """Menu interativo para geração de relatórios."""
    console.print(Panel("[bold]Gerar Relatório[/bold]\n\nEscolha o tipo de relatório.", style="cyan"))

    console.print("\n  [green]1[/green]) DRE Simplificado (Receitas - Despesas = Lucro)")
    console.print("  [green]2[/green]) Fluxo de Caixa (Entradas vs Saídas por mês)")
    console.print("  [green]3[/green]) Fechamento Mensal (Saldo inicial → final)\n")

    tipo_num = IntPrompt.ask("Tipo", default=1)
    tipos = {1: "dre", 2: "fluxo", 3: "fechamento"}
    tipo = tipos.get(tipo_num, "dre")

    arquivo = escolher_arquivo("Selecione a planilha de LANÇAMENTOS", "dados")
    if not arquivo:
        return

    saida = f"saida/relatorio_{tipo}.xlsx"
    console.print(f"\n[dim]Resultado será salvo em: {saida}[/dim]\n")

    from financeiro.relatorios import gerar_relatorio
    gerar_relatorio(arquivo, tipo=tipo, saida=saida)


def menu_validar():
    """Menu interativo para validação de dados."""
    console.print(Panel("[bold]Validar Dados[/bold]\n\nVou verificar erros na sua planilha.", style="cyan"))

    arquivo = escolher_arquivo("Selecione o arquivo para VALIDAR", "dados")
    if not arquivo:
        return

    saida = "saida/validacao.xlsx"
    console.print(f"\n[dim]Relatório de erros será salvo em: {saida}[/dim]\n")

    from financeiro.validador import validar
    validar(arquivo, saida=saida)


def menu_principal():
    """Menu principal interativo."""
    # Garantir que as pastas existem
    Path("dados").mkdir(exist_ok=True)
    Path("saida").mkdir(exist_ok=True)

    while True:
        console.print()
        console.print(Panel(
            "[bold cyan]SISTEMA FINANCEIRO AUTOMATIZADO[/bold cyan]\n\n"
            "  [green]1[/green]) 🏦 Conciliação Bancária\n"
            "  [green]2[/green]) 📂 Consolidar Planilhas\n"
            "  [green]3[/green]) 📈 Gerar Relatório\n"
            "  [green]4[/green]) 🔍 Validar Dados\n\n"
            "  [red]0[/red]) Sair",
            title="💰 Menu Principal",
            border_style="cyan",
        ))

        opcao = IntPrompt.ask("\nEscolha", default=0)

        if opcao == 1:
            menu_conciliar()
        elif opcao == 2:
            menu_consolidar()
        elif opcao == 3:
            menu_relatorio()
        elif opcao == 4:
            menu_validar()
        elif opcao == 0:
            console.print("\n[cyan]Até logo! 👋[/cyan]\n")
            break
        else:
            console.print("[red]Opção inválida. Tente novamente.[/red]")

        # Pausa antes de voltar ao menu
        console.print()
        Prompt.ask("[dim]Pressione Enter para voltar ao menu[/dim]")


if __name__ == "__main__":
    menu_principal()
