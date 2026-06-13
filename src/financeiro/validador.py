"""Módulo validador de dados financeiros.

Detecta erros comuns antes que virem problema:
CNPJs/CPFs inválidos, duplicatas, datas impossíveis, outliers, etc.
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
    validar_cnpj,
    validar_cpf,
)

console = Console()


def validar(
    arquivo: str,
    saida: str = "saida/validacao.xlsx",
    config_path: str = "config.yaml",
) -> dict:
    """Valida dados de uma planilha financeira e aponta erros.

    Args:
        arquivo: Caminho do arquivo a validar (.xlsx).
        saida: Caminho do relatório de erros.
        config_path: Caminho do arquivo de configuração.

    Returns:
        Dicionário com contagem de erros por tipo.
    """
    config = carregar_config(config_path).get("validador", {})

    console.print(Panel("🔍 Validador de Dados", style="bold cyan"))
    console.print(f"  Arquivo: [green]{arquivo}[/green]\n")

    df = ler_excel(arquivo)
    erros = []

    # 1. Validar CNPJ/CPF
    if config.get("validar_cnpj", True):
        erros.extend(_validar_documentos(df))

    # 2. Detectar duplicados
    if config.get("detectar_duplicados", True):
        erros.extend(_detectar_duplicados(df))

    # 3. Detectar datas impossíveis
    if config.get("detectar_datas_futuras", True):
        erros.extend(_validar_datas(df))

    # 4. Campos obrigatórios vazios
    erros.extend(_validar_campos_vazios(df))

    # 5. Detectar outliers
    if config.get("detectar_outliers", True):
        fator = config.get("fator_outlier", 3.0)
        erros.extend(_detectar_outliers(df, fator))

    # 6. Sequência quebrada
    erros.extend(_validar_sequencia(df))

    # 7. NF duplicada (pagamento em dobro)
    if config.get("detectar_nf_duplicada", True):
        janela = config.get("janela_nf_dias", 5)
        erros.extend(_detectar_nf_duplicadas(df, janela_dias=janela))

    # 8. Checar CNPJ online (opcional — desabilitado por padrão)
    if config.get("checar_cnpj_online", False):
        try:
            from .cnpj_checker import _checar_cnpjs_no_validador

            erros.extend(_checar_cnpjs_no_validador(df, config))
        except ImportError:
            console.print("[yellow]⚠ requests não instalado — checagem online ignorada.[/yellow]")

    # Salvar relatório
    _salvar_relatorio(erros, saida)

    # Exibir resumo
    stats = _contar_por_tipo(erros)

    console.print()
    linhas = [[tipo, str(qtd)] for tipo, qtd in stats.items()]
    if linhas:
        exibir_tabela("🚨 Erros Encontrados", ["Tipo", "Quantidade"], linhas)
    else:
        console.print("[green]✅ Nenhum erro encontrado! Dados válidos.[/green]")

    console.print(f"\n  Total de erros: [{'red' if erros else 'green'}]{len(erros)}[/{'red' if erros else 'green'}]")
    console.print(f"  Relatório salvo em: [green]{saida}[/green]\n")

    return stats


def _validar_documentos(df: pd.DataFrame) -> list[dict]:
    """Valida colunas que parecem conter CNPJ ou CPF."""
    erros = []
    colunas_doc = _encontrar_colunas(df, ["cnpj", "cpf", "documento", "doc"])

    for col in colunas_doc:
        for idx, valor in df[col].items():
            if pd.isna(valor) or str(valor).strip() == "":
                continue

            texto = str(valor).strip()
            numeros = "".join(c for c in texto if c.isdigit())

            if len(numeros) == 14:
                if not validar_cnpj(numeros):
                    erros.append({
                        "Linha": idx + 2,
                        "Coluna": col,
                        "Valor": texto,
                        "Tipo Erro": "CNPJ inválido",
                        "Sugestão": "Verifique os dígitos do CNPJ",
                    })
            elif len(numeros) == 11:
                if not validar_cpf(numeros):
                    erros.append({
                        "Linha": idx + 2,
                        "Coluna": col,
                        "Valor": texto,
                        "Tipo Erro": "CPF inválido",
                        "Sugestão": "Verifique os dígitos do CPF",
                    })

    return erros


def _detectar_duplicados(df: pd.DataFrame) -> list[dict]:
    """Detecta linhas duplicadas (mesma data + valor + descrição)."""
    erros = []
    colunas_chave = []

    for col in df.columns:
        cl = str(col).lower()
        if any(t in cl for t in ["data", "valor", "descri", "histori"]):
            colunas_chave.append(col)

    if len(colunas_chave) < 2:
        return erros

    duplicados = df[df.duplicated(subset=colunas_chave, keep=False)]

    # Agrupar e marcar a partir da segunda ocorrência
    vistos = set()
    for idx, row in duplicados.iterrows():
        chave = tuple(str(row[c]) for c in colunas_chave)
        if chave in vistos:
            erros.append({
                "Linha": idx + 2,
                "Coluna": ", ".join(colunas_chave),
                "Valor": " | ".join(str(row[c]) for c in colunas_chave[:3]),
                "Tipo Erro": "Duplicado",
                "Sugestão": "Lançamento possivelmente duplicado — verifique",
            })
        else:
            vistos.add(chave)

    return erros


def _validar_datas(df: pd.DataFrame) -> list[dict]:
    """Detecta datas impossíveis: futuras, muito antigas, ou inválidas."""
    erros = []
    hoje = datetime.now()
    colunas_data = _encontrar_colunas(df, ["data", "dt", "date", "vencimento"])

    for col in colunas_data:
        for idx, valor in df[col].items():
            if pd.isna(valor):
                continue

            data = padronizar_data(valor)

            if data is None:
                erros.append({
                    "Linha": idx + 2,
                    "Coluna": col,
                    "Valor": str(valor),
                    "Tipo Erro": "Data inválida",
                    "Sugestão": "Formato não reconhecido — use DD/MM/AAAA",
                })
            elif data > hoje:
                erros.append({
                    "Linha": idx + 2,
                    "Coluna": col,
                    "Valor": str(valor),
                    "Tipo Erro": "Data futura",
                    "Sugestão": f"Data posterior a hoje ({hoje.strftime('%d/%m/%Y')})",
                })
            elif data.year < 2000:
                erros.append({
                    "Linha": idx + 2,
                    "Coluna": col,
                    "Valor": str(valor),
                    "Tipo Erro": "Data suspeita",
                    "Sugestão": "Ano anterior a 2000 — possível erro de digitação",
                })

    return erros


def _validar_campos_vazios(df: pd.DataFrame) -> list[dict]:
    """Detecta campos obrigatórios em branco (categoria, descrição)."""
    erros = []
    colunas_obrigatorias = _encontrar_colunas(df, ["categoria", "classif", "tipo"])

    for col in colunas_obrigatorias:
        for idx, valor in df[col].items():
            if pd.isna(valor) or str(valor).strip() == "":
                erros.append({
                    "Linha": idx + 2,
                    "Coluna": col,
                    "Valor": "(vazio)",
                    "Tipo Erro": "Campo vazio",
                    "Sugestão": "Preencha a categoria/classificação",
                })

    return erros


def _detectar_outliers(df: pd.DataFrame, fator: float = 3.0) -> list[dict]:
    """Detecta valores muito acima da média (possível erro de digitação)."""
    erros = []
    colunas_valor = _encontrar_colunas(df, ["valor", "vlr", "total", "montante"])

    for col in colunas_valor:
        valores = df[col].apply(padronizar_moeda).dropna()
        if len(valores) < 5:
            continue

        media = valores.mean()
        desvio = valores.std()

        if desvio == 0:
            continue

        limite = abs(media) + (fator * desvio)

        for idx in valores.index:
            val = valores[idx]
            if abs(val) > limite:
                erros.append({
                    "Linha": idx + 2,
                    "Coluna": col,
                    "Valor": f"R$ {val:,.2f}",
                    "Tipo Erro": "Valor outlier",
                    "Sugestão": f"Valor muito acima da média (R$ {media:,.2f}) — verifique digitação",
                })

    return erros


def _validar_sequencia(df: pd.DataFrame) -> list[dict]:
    """Detecta quebras na sequência numérica (notas fiscais, documentos)."""
    erros = []
    colunas_seq = _encontrar_colunas(df, ["nf", "nota", "numero", "num", "doc"])

    for col in colunas_seq:
        # Extrair apenas valores numéricos
        numeros = []
        for idx, valor in df[col].items():
            if pd.isna(valor):
                continue
            texto = "".join(c for c in str(valor) if c.isdigit())
            if texto and len(texto) <= 10:
                numeros.append((idx, int(texto)))

        if len(numeros) < 3:
            continue

        # Ordenar e verificar gaps
        numeros.sort(key=lambda x: x[1])
        for i in range(1, len(numeros)):
            diff = numeros[i][1] - numeros[i - 1][1]
            if diff > 1 and diff <= 10:
                faltando = [str(numeros[i - 1][1] + j) for j in range(1, diff)]
                erros.append({
                    "Linha": numeros[i][0] + 2,
                    "Coluna": col,
                    "Valor": f"{numeros[i-1][1]} → {numeros[i][1]}",
                    "Tipo Erro": "Sequência quebrada",
                    "Sugestão": f"Faltando: {', '.join(faltando[:5])}",
                })

    return erros


def _detectar_nf_duplicadas(df: pd.DataFrame, janela_dias: int = 5) -> list[dict]:
    """Detecta notas fiscais duplicadas que podem causar pagamento em dobro.

    Regras:
        1. Mesmo NF + mesmo fornecedor = duplicata certa
        2. Mesmo NF + mesmo valor + datas diferentes = mesma NF paga 2x
        3. Mesmo fornecedor + mesmo valor dentro de N dias = suspeito
    """
    erros = []

    colunas_nf = _encontrar_colunas(df, ["nf", "nota_fiscal", "nota", "numero_nf"])
    colunas_forn = _encontrar_colunas(df, ["fornecedor", "razao", "cnpj_fornec", "supplier", "parceiro"])
    colunas_valor = _encontrar_colunas(df, ["valor", "vlr", "total", "montante"])
    colunas_data = _encontrar_colunas(df, ["data", "dt", "date", "vencimento"])

    col_nf = colunas_nf[0] if colunas_nf else None
    col_forn = colunas_forn[0] if colunas_forn else None
    col_valor = colunas_valor[0] if colunas_valor else None
    col_data = colunas_data[0] if colunas_data else None

    if not col_nf and not (col_forn and col_valor):
        return erros

    # Preparar colunas numéricas/data
    if col_valor:
        valores = df[col_valor].apply(padronizar_moeda)
    if col_data:
        datas = df[col_data].apply(padronizar_data)

    # Regra 1: Mesmo NF + mesmo fornecedor
    if col_nf and col_forn:
        vistos = {}
        for idx, row in df.iterrows():
            nf = str(row[col_nf]).strip().lower()
            forn = str(row[col_forn]).strip().lower()
            if pd.isna(row[col_nf]) or nf in ("", "nan"):
                continue
            chave = (nf, forn)
            if chave in vistos:
                erros.append({
                    "Linha": idx + 2,
                    "Coluna": col_nf,
                    "Valor": f"NF {row[col_nf]} / {row[col_forn]}",
                    "Tipo Erro": "NF duplicada (mesmo fornecedor)",
                    "Sugestão": f"Mesma NF já aparece na linha {vistos[chave] + 2} — possível pagamento em dobro",
                })
            else:
                vistos[chave] = idx

    # Regra 2: Mesmo NF + mesmo valor + datas diferentes
    if col_nf and col_valor and col_data:
        grupos_nf = {}
        for idx, row in df.iterrows():
            nf = str(row[col_nf]).strip().lower()
            if pd.isna(row[col_nf]) or nf in ("", "nan"):
                continue
            val = valores.iloc[idx] if idx < len(valores) else None
            dt = datas.iloc[idx] if idx < len(datas) else None
            if val is not None and dt is not None:
                grupos_nf.setdefault(nf, []).append((idx, val, dt))

        for nf, itens in grupos_nf.items():
            if len(itens) < 2:
                continue
            for i in range(1, len(itens)):
                idx_a, val_a, dt_a = itens[0]
                idx_b, val_b, dt_b = itens[i]
                if val_a == val_b and dt_a != dt_b and dt_a is not None and dt_b is not None:
                    erros.append({
                        "Linha": idx_b + 2,
                        "Coluna": col_nf,
                        "Valor": f"NF {nf} / R$ {val_b:,.2f}",
                        "Tipo Erro": "NF duplicada (mesmo valor, data diferente)",
                        "Sugestão": f"Mesma NF e valor, mas data difere da linha {idx_a + 2} — mesma NF paga 2x?",
                    })

    # Regra 3: Mesmo fornecedor + mesmo valor dentro da janela de dias
    if col_forn and col_valor and col_data:
        from datetime import timedelta

        grupos_forn = {}
        for idx, row in df.iterrows():
            forn = str(row[col_forn]).strip().lower()
            if pd.isna(row[col_forn]) or forn in ("", "nan"):
                continue
            val = valores.iloc[idx] if idx < len(valores) else None
            dt = datas.iloc[idx] if idx < len(datas) else None
            if val is not None and dt is not None and val != 0:
                grupos_forn.setdefault((forn, val), []).append((idx, dt))

        for (forn, val), itens in grupos_forn.items():
            if len(itens) < 2:
                continue
            itens.sort(key=lambda x: x[1] if x[1] else datetime.min)
            for i in range(1, len(itens)):
                idx_ant, dt_ant = itens[i - 1]
                idx_cur, dt_cur = itens[i]
                if dt_ant and dt_cur:
                    diff = abs((dt_cur - dt_ant).days)
                    if diff <= janela_dias and diff > 0:
                        erros.append({
                            "Linha": idx_cur + 2,
                            "Coluna": col_forn,
                            "Valor": f"{forn[:30]} / R$ {val:,.2f} / {diff}d",
                            "Tipo Erro": "Pagamento suspeito (fornecedor + valor similar)",
                            "Sugestão": f"Mesmo fornecedor e valor a {diff} dia(s) da linha {idx_ant + 2} — conferir se não é duplicado",
                        })

    return erros


def _encontrar_colunas(df: pd.DataFrame, termos: list[str]) -> list[str]:
    """Encontra colunas cujo nome contém algum dos termos."""
    resultado = []
    for col in df.columns:
        cl = str(col).lower().strip()
        if any(t in cl for t in termos):
            resultado.append(col)
    return resultado


def _contar_por_tipo(erros: list[dict]) -> dict:
    """Conta erros agrupados por tipo."""
    contagem = {}
    for erro in erros:
        tipo = erro["Tipo Erro"]
        contagem[tipo] = contagem.get(tipo, 0) + 1
    return contagem


def _salvar_relatorio(erros: list[dict], caminho: str):
    """Salva relatório de erros em Excel."""
    path = Path(caminho)
    path.parent.mkdir(parents=True, exist_ok=True)

    if erros:
        df_erros = pd.DataFrame(erros)
    else:
        df_erros = pd.DataFrame(columns=["Linha", "Coluna", "Valor", "Tipo Erro", "Sugestão"])

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df_erros.to_excel(writer, sheet_name="Erros", index=False)

        # Aba de resumo
        contagem = _contar_por_tipo(erros)
        resumo = pd.DataFrame([
            {"Tipo": tipo, "Quantidade": qtd} for tipo, qtd in contagem.items()
        ]) if contagem else pd.DataFrame(columns=["Tipo", "Quantidade"])
        resumo.to_excel(writer, sheet_name="Resumo", index=False)
