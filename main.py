import asyncio
import os
import re
import requests
from datetime import datetime, date
from playwright.async_api import async_playwright

DATASYSTEM_URL = "https://lepoa11672.useserver.com.br/RETAGUARDA/Inteligencia/Tendencia"
DATASYSTEM_USER = os.environ.get("DS_USER", "")
DATASYSTEM_PASS = os.environ.get("DS_PASS", "")

ZAPI_INSTANCE = os.environ.get("ZAPI_INSTANCE", "3EFAD2909069028ADC8E6237BF5854B6")
ZAPI_TOKEN    = os.environ.get("ZAPI_TOKEN",    "3543270E8FE1C9AEA4383932")
ZAPI_CLIENT   = os.environ.get("ZAPI_CLIENT",   "F26521e4d25334eb0846c707873e47080S")
ZAPI_GROUP_ID = os.environ.get("ZAPI_GROUP_ID", "")

LOJA_NOME = "Le Poa Loja 01 - Matriz"

# Colunas do XLS: Loja | Data | QtdeVendas | QtdeItens | PA | PU | TicketMedio | Meta | ValorVendido | VendasAcumuladas | ...
COL_DATA       = 1
COL_QTD_VENDAS = 2
COL_QTD_ITENS  = 3
COL_PA         = 4
COL_TICKET     = 6
COL_VALOR      = 8
COL_ACUMULADO  = 9


async def baixar_xls():
    """Faz login no DataSystem, gera e baixa o XLS do relatório."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print("Login...")
        await page.goto("https://lepoa11672.useserver.com.br/RETAGUARDA/", wait_until="networkidle", timeout=30000)

        try:
            await page.wait_for_selector("input[type='text']", timeout=8000)
            await page.fill("input[type='text']", DATASYSTEM_USER)
            await page.fill("input[type='password']", DATASYSTEM_PASS)
            select = await page.query_selector("select")
            if select:
                await page.select_option("select", label="LE POA LOJA 01 MATRIZ")
            await page.click("text=Entrar")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)
            print("Login OK!")
        except Exception as e:
            print(f"Login erro: {e}")

        print("Abrindo relatorio...")
        await page.goto(DATASYSTEM_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)

        # Clica em Confirmar
        await page.click("text=Confirmar")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(4000)

        # Clica no botão de impressão (ícone de impressora)
        print("Abrindo dialogo de exportacao...")
        try:
            await page.click("button.btn-print, .btn-imprimir, input[title*='print'], button[title*='print'], .fa-print, [onclick*='print'], [onclick*='Print']")
        except:
            # Tenta pelo ícone de impressora na tabela
            await page.click("img[src*='print'], .glyphicon-print, button:has-text('Imprimir')")
        await page.wait_for_timeout(2000)

        # Seleciona XLS e Detalhado
        try:
            await page.click("input[value='.XLS'], label:has-text('XLS'), text=.XLS")
            await page.click("input[value='Detalhado'], label:has-text('Detalhado'), text=Detalhado")
        except Exception as e:
            print(f"Selecao opcoes: {e}")

        # Faz download interceptando a resposta
        print("Baixando XLS...")
        async with page.expect_download() as download_info:
            try:
                await page.click("text=Download")
            except:
                await page.click("button:has-text('Download'), a:has-text('Download')")

        download = await download_info.value
        xls_path = "/tmp/relatorio.xls"
        await download.save_as(xls_path)
        print(f"XLS salvo em {xls_path}")

        await browser.close()
        return xls_path


def parse_xls(xls_path):
    """Lê o XLS (HTML disfarçado) e extrai os dados de hoje."""
    hoje = date.today().strftime("%d/%m/%Y")
    print(f"Buscando dados de: {hoje}")

    indicadores = {
        "Valor Vendido": "-",
        "Quantidade de Vendas": "-",
        "Quantidade de Itens": "-",
        "PA": "-",
        "Ticket Medio": "-",
        "Vendas Acumuladas": "-",
        "Projecao": "-",
        "Meta Corrigida": "-",
    }

    try:
        content = open(xls_path, 'rb').read()
        text = content.decode('utf-16-le', errors='ignore')
        trs = re.findall(r'<tr[^>]*>(.*?)</tr>', text, re.DOTALL)

        for tr in trs:
            tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.DOTALL)
            if not tds:
                continue
            cols = [re.sub(r'<[^>]+>', '', td).strip() for td in tds]

            # Linha de hoje
            if len(cols) > COL_ACUMULADO and cols[COL_DATA] == hoje:
                print(f"Linha encontrada: {cols}")
                indicadores["Quantidade de Vendas"] = cols[COL_QTD_VENDAS]
                indicadores["Quantidade de Itens"]  = cols[COL_QTD_ITENS]
                indicadores["PA"]                   = cols[COL_PA]
                indicadores["Ticket Medio"]         = cols[COL_TICKET]
                indicadores["Valor Vendido"]        = cols[COL_VALOR]
                indicadores["Vendas Acumuladas"]    = cols[COL_ACUMULADO]
                break

    except Exception as e:
        print(f"Erro parse: {e}")

    return indicadores


def montar_mensagem(ind):
    agora = datetime.now().strftime("%d/%m/%Y as %H:%M")
    def v(k): return ind.get(k) or "-"
    return (
        f"*Resumo de Vendas - {LOJA_NOME}*\n"
        f"{agora}\n\n"
        f"Valor Vendido: R$ {v('Valor Vendido')}\n"
        f"Qtd. Vendas: {v('Quantidade de Vendas')}\n"
        f"Qtd. Itens: {v('Quantidade de Itens')}\n"
        f"PA: {v('PA')}\n"
        f"Ticket Medio: R$ {v('Ticket Medio')}\n"
        f"Vendas Acumuladas: R$ {v('Vendas Acumuladas')}\n"
        f"Projecao: {v('Projecao')}\n"
        f"Meta Corrigida: {v('Meta Corrigida')}\n\n"
        f"Enviado automaticamente pelo sistema Le Poa"
    )


def enviar_whatsapp(mensagem):
    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}/send-text"
    headers = {"Content-Type": "application/json", "client-token": ZAPI_CLIENT}
    payload = {"phone": ZAPI_GROUP_ID, "message": mensagem}
    resp = requests.post(url, json=payload, headers=headers)
    if resp.status_code == 200:
        print("Enviado!")
    else:
        print(f"Erro envio: {resp.status_code} - {resp.text}")


async def executar():
    print(f"=== {datetime.now().strftime('%d/%m/%Y %H:%M')} ===")
    xls_path = await baixar_xls()
    indicadores = parse_xls(xls_path)
    mensagem = montar_mensagem(indicadores)
    print("Mensagem:\n", mensagem)
    enviar_whatsapp(mensagem)


if __name__ == "__main__":
    asyncio.run(executar())
