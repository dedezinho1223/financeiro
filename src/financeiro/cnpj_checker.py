"""Checker de CNPJ online — consulta situação cadastral na Receita Federal.

Usa a BrasilAPI (gratuita, sem autenticação) para verificar se CNPJs
de uma planilha estão ativos ou com situação irregular.
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .utils import carregar_config, exibir_tabela, ler_excel, validar_cnpj

console = Console()

APIS = {
    "brasilapi": "https://brasilapi.com.br/api/cnpj/v1/{}",
    "receitaws": "https://receitaws.com.br/v1/cnpj/{}",
}


def checar_cnpjs(
    arquivo: str,
    saida: str = "saida/cnpj_check.xlsx",
    config_path: str = "config.yaml",
) -> dict:
    """Consulta CNPJs de uma planilha na API da Receita Federal.

    Args:
        arquivo: Planilha com coluna de CNPJ.
        saida: Caminho do relatório de saída.
        config_path: Configuração.

    Returns:
        Dict com contagem: total, ativas, irregulares, erro_api.
    """

    config_geral = carregar_config(config_path)
    config = config_geral.get("cnpj_checker", {})

    api_nome = config.get("api", "brasilapi")
    intervalo = config.get("intervalo_requests", 1.5)
    timeout = config.get("timeout", 10)
    cache_dir = config.get("cache_dir", ".cache")
    cache_dias = config.get("cache_dias", 30)

    console.print(Panel("🌐 Checker de CNPJ — Receita Federal", style="bold cyan"))
    console.print(f"  Arquivo: [green]{arquivo}[/green]")
    console.print(f"  API: [cyan]{api_nome}[/cyan]\n")

    df = ler_excel(arquivo)

    # Encontrar coluna de CNPJ
    col_cnpj = None
    for col in df.columns:
        if any(t in str(col).lower() for t in ["cnpj", "documento", "doc"]):
            col_cnpj = col
            break

    if col_cnpj is None:
        console.print("[red]Nenhuma coluna de CNPJ encontrada na planilha.[/red]")
        console.print("[dim]Procurei por: cnpj, documento, doc[/dim]\n")
        return {"total": 0, "ativas": 0, "irregulares": 0, "erro_api": 0}

    # Extrair CNPJs únicos e válidos
    cnpjs_unicos = set()
    for valor in df[col_cnpj].dropna():
        numeros = "".join(c for c in str(valor) if c.isdigit())
        if len(numeros) == 14 and validar_cnpj(numeros):
            cnpjs_unicos.add(numeros)

    if not cnpjs_unicos:
        console.print("[yellow]Nenhum CNPJ válido encontrado na planilha.[/yellow]\n")
        return {"total": 0, "ativas": 0, "irregulares": 0, "erro_api": 0}

    console.print(f"  CNPJs únicos para consultar: [cyan]{len(cnpjs_unicos)}[/cyan]\n")

    # Carregar cache
    cache = _carregar_cache(Path(cache_dir) / "cnpj_cache.json", cache_dias)

    # Consultar API
    resultados = []
    stats = {"total": len(cnpjs_unicos), "ativas": 0, "irregulares": 0, "erro_api": 0}

    api_url = APIS.get(api_nome, APIS["brasilapi"])

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Consultando CNPJs...", total=len(cnpjs_unicos))

        for cnpj in sorted(cnpjs_unicos):
            # Verificar cache
            if cnpj in cache:
                dados = cache[cnpj]
            else:
                dados = _consultar_cnpj_api(cnpj, api_url, timeout)
                if dados:
                    dados["consultado_em"] = datetime.now().isoformat()
                    cache[cnpj] = dados
                time.sleep(intervalo)

            if dados:
                situacao = dados.get("situacao_cadastral", dados.get("status", "DESCONHECIDO"))
                if isinstance(situacao, int):
                    # BrasilAPI retorna código numérico
                    situacao = _codigo_para_situacao(situacao)

                razao = dados.get("razao_social", dados.get("nome", ""))
                abertura = dados.get("data_inicio_atividade", dados.get("abertura", ""))

                status = "OK" if situacao.upper() == "ATIVA" else "IRREGULAR"
                if status == "OK":
                    stats["ativas"] += 1
                else:
                    stats["irregulares"] += 1

                resultados.append({
                    "CNPJ": _formatar_cnpj(cnpj),
                    "Razao Social": razao,
                    "Situacao": situacao,
                    "Data Abertura": abertura,
                    "Status": status,
                })
            else:
                stats["erro_api"] += 1
                resultados.append({
                    "CNPJ": _formatar_cnpj(cnpj),
                    "Razao Social": "",
                    "Situacao": "ERRO API",
                    "Data Abertura": "",
                    "Status": "ERRO",
                })

            progress.advance(task)

    # Salvar cache
    _salvar_cache(cache, Path(cache_dir) / "cnpj_cache.json")

    # Salvar relatório Excel
    _salvar_relatorio_cnpj(resultados, stats, saida)

    # Exibir resumo
    console.print()
    linhas = [
        ["ATIVA", str(stats["ativas"])],
        ["IRREGULAR", str(stats["irregulares"])],
        ["Erro API", str(stats["erro_api"])],
    ]
    exibir_tabela("📋 Resumo CNPJ", ["Situação", "Quantidade"], linhas)
    console.print(f"\n  Relatório salvo em: [green]{saida}[/green]\n")

    return stats


def _consultar_cnpj_api(cnpj: str, api_url: str, timeout: int = 10) -> dict | None:
    """Consulta um CNPJ individual na API pública."""
    url = api_url.format(cnpj)
    tentativas = 0
    espera = 2

    while tentativas < 3:
        try:
            resp = requests.get(url, timeout=timeout)

            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                # Rate limit — esperar e tentar novamente
                tentativas += 1
                console.print(f"[yellow]Rate limit — aguardando {espera}s...[/yellow]")
                time.sleep(espera)
                espera *= 2
            elif resp.status_code == 404:
                return {"situacao_cadastral": "NAO ENCONTRADO", "razao_social": ""}
            else:
                return None

        except requests.ConnectionError:
            console.print("[yellow]Sem conexão com a internet.[/yellow]")
            return None
        except requests.Timeout:
            tentativas += 1
            if tentativas >= 3:
                return None
            time.sleep(1)
        except Exception:
            return None

    return None


def _checar_cnpjs_no_validador(df: pd.DataFrame, config: dict) -> list[dict]:
    """Versão integrada ao validador — retorna erros no formato padrão."""
    config_checker = config if "api" in config else {}
    api_nome = config_checker.get("api", "brasilapi")
    intervalo = config_checker.get("intervalo_requests", 1.5)
    timeout = config_checker.get("timeout", 10)
    cache_dir = config_checker.get("cache_dir", ".cache")
    cache_dias = config_checker.get("cache_dias", 30)

    api_url = APIS.get(api_nome, APIS["brasilapi"])
    cache = _carregar_cache(Path(cache_dir) / "cnpj_cache.json", cache_dias)

    erros = []

    # Encontrar coluna CNPJ
    col_cnpj = None
    for col in df.columns:
        if any(t in str(col).lower() for t in ["cnpj", "documento"]):
            col_cnpj = col
            break

    if not col_cnpj:
        return erros

    # Coletar CNPJs únicos
    cnpj_map = {}  # cnpj -> lista de índices
    for idx, valor in df[col_cnpj].items():
        if pd.isna(valor):
            continue
        numeros = "".join(c for c in str(valor) if c.isdigit())
        if len(numeros) == 14 and validar_cnpj(numeros):
            cnpj_map.setdefault(numeros, []).append(idx)

    # Consultar cada CNPJ único
    for cnpj, indices in cnpj_map.items():
        if cnpj in cache:
            dados = cache[cnpj]
        else:
            dados = _consultar_cnpj_api(cnpj, api_url, timeout)
            if dados:
                dados["consultado_em"] = datetime.now().isoformat()
                cache[cnpj] = dados
            time.sleep(intervalo)

        if dados:
            situacao = dados.get("situacao_cadastral", dados.get("status", ""))
            if isinstance(situacao, int):
                situacao = _codigo_para_situacao(situacao)

            if situacao.upper() != "ATIVA":
                for idx in indices:
                    erros.append({
                        "Linha": idx + 2,
                        "Coluna": col_cnpj,
                        "Valor": _formatar_cnpj(cnpj),
                        "Tipo Erro": "CNPJ inativo",
                        "Sugestão": f"Situação na Receita: {situacao} — verifique fornecedor",
                    })

    _salvar_cache(cache, Path(cache_dir) / "cnpj_cache.json")
    return erros


def _carregar_cache(caminho: Path, cache_dias: int = 30) -> dict:
    """Carrega cache de CNPJs já consultados."""
    if not caminho.exists():
        return {}
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        # Filtrar entradas expiradas
        limite = datetime.now() - timedelta(days=cache_dias)
        cache_valido = {}
        for cnpj, info in dados.items():
            consultado = info.get("consultado_em", "")
            if consultado:
                try:
                    dt = datetime.fromisoformat(consultado)
                    if dt >= limite:
                        cache_valido[cnpj] = info
                except (ValueError, TypeError):
                    pass
        return cache_valido
    except (json.JSONDecodeError, OSError):
        return {}


def _salvar_cache(cache: dict, caminho: Path) -> None:
    """Salva cache atualizado."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _formatar_cnpj(cnpj: str) -> str:
    """Formata CNPJ: 12.345.678/0001-90."""
    cnpj = cnpj.zfill(14)
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"


def _codigo_para_situacao(codigo: int) -> str:
    """Converte código numérico da BrasilAPI para texto."""
    mapa = {
        1: "NULA",
        2: "ATIVA",
        3: "SUSPENSA",
        4: "INAPTA",
        8: "BAIXADA",
    }
    return mapa.get(codigo, f"CODIGO {codigo}")


def _salvar_relatorio_cnpj(resultados: list[dict], stats: dict, caminho: str):
    """Salva relatório de CNPJ em Excel."""
    path = Path(caminho)
    path.parent.mkdir(parents=True, exist_ok=True)

    df_resultados = pd.DataFrame(resultados) if resultados else pd.DataFrame(
        columns=["CNPJ", "Razao Social", "Situacao", "Data Abertura", "Status"]
    )

    df_resumo = pd.DataFrame([
        {"Situação": "ATIVA", "Quantidade": stats["ativas"]},
        {"Situação": "IRREGULAR", "Quantidade": stats["irregulares"]},
        {"Situação": "Erro API", "Quantidade": stats["erro_api"]},
        {"Situação": "TOTAL", "Quantidade": stats["total"]},
    ])

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df_resultados.to_excel(writer, sheet_name="Resultados", index=False)
        df_resumo.to_excel(writer, sheet_name="Resumo", index=False)
