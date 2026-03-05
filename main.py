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

COL_DATA       = 1
COL_QTD_VENDAS = 2
COL_QTD_ITENS  = 3
COL_PA         = 4
COL_TICKET     = 6
COL_VALOR      = 8
COL_ACUMULADO  = 9


async def baixar_xls():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Vai direto para o relatório — se redirecionar para login, faz o login
        print("Acessando sistema...")
        await page.goto(DATASYSTEM_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)

        # Verifica se caiu na tela de login
        url_atual = page.url
        print(f"URL atual: {url_atual}")

        if "Login" in url_atual or "login" in url_atual or "RETAGUARDA/" == url_atual.split("useserver.com.br/")[-1]:
            print("Tela de login detectada, fazendo login...")
            try:
                inputs = await page.query_selector_all("input")
                print(f"Inputs encontrados: {len(inputs)}")
                for inp in inputs:
                    t = await inp.get_attribute("type")
                    print(f"  input type={t}")

                # Preenche todos os campos de texto/senha encontrados
                all_inputs = await page.query_selector_all("input[type='text'], input:not([type])")
                if all_inputs:
                    await all_inputs[0].fill(DATASYSTEM_USER)

                pass_inputs = await page.query_selector_all("input[type='password']")
                if pass_inputs:
                    await pass_inputs[0].fill(DATASYSTEM_PASS)

                # Seleciona loja no dropdown
                selects = await page.query_selector_all("select")
                if selects:
                    options = await selects[0].query_selector_all("option")
                    for opt in options:
                        val = await opt.inner_text()
                        print(f"  opcao: {val}")
                    # Seleciona a primeira opção que não seja vazia
                    await selects[0].select_option(index=0)

                # Clica no botão de entrar
                btns = await page.query_selector_all("button, input[type='submit'], input[type='button']")
                for btn in btns:
                    txt = await btn.inner_text() if await btn.get_attribute("type") != "submit" else ""
                    val = await btn.get_attribute("value") or ""
                    print(f"  botao: txt={txt} val={val}")

                await page.click("text=Entrar")
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(3000)
                print(f"Pos-login URL: {page.url}")

                # Vai para o relatório após login
                await page.goto(DATASYSTEM_URL, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(2000)
            except Exception as e:
                print(f"Erro login: {e}")

        # Agora deve estar na tela do relatório
        print(f"URL relatorio: {page.url}")

        # Tira screenshot para debug
        await page.screenshot(path="/tmp/debug.png")
        print("Screenshot salvo em /tmp/debug.png")

        # Clica em Confirmar
        print("Clicando Confirmar...")
        try:
            # Tenta vários seletores
            confirmar = await page.query_selector("text=Confirmar, button:has-text('Confirmar'), input[value='Confirmar']")
            if confirmar:
                await confirmar.click()
            else:
                # Lista todos os botões presentes
                btns = await page.query_selector_all("button, input[type='button'], input[type='submit'], a.btn")
                for btn in btns:
                    txt = await btn.inner_text()
                    print(f"  btn: {txt}")
                await page.locator("text=Confirmar").click(timeout=10000)

            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(5000)
            print("Relatorio gerado!")
        except Exception as e:
            print(f"Erro confirmar: {e}")
            # Pega o HTML para debug
            body = await page.inner_text("body")
            print(f"Body (500 chars): {body[:500]}")

        # Clica na impressora para exportar XLS
        print("Exportando XLS...")
        try:
            # Tenta clicar no icone de impressao
            await page.click(".fa-print, .glyphicon-print, [title*='print'], [title*='Print'], [title*='mprimir']", timeout=5000)
        except:
            try:
                await page.click("img[src*='print'], img[alt*='print'], img[alt*='Print']", timeout=5000)
            except Exception as e:
                print(f"Botao impressora: {e}")
                # Lista imagens e botoes para debug
                imgs = await page.query_selector_all("img, button")
                for el in imgs[:20]:
                    src = await el.get_attribute("src") or ""
                    title = await el.get_attribute("title") or ""
                    onclick = await el.get_attribute("onclick") or ""
                    if src or title or onclick:
                        print(f"  el: src={src} title={title} onclick={onclick[:50]}")

        await page.wait_for_timeout(2000)

        # Seleciona XLS e Detalhado
        try:
            await page.click("label:has-text('.XLS'), input[value='.XLS']", timeout=3000)
            await page.click("label:has-text('Detalhado'), input[value='Detalhado']", timeout=3000)
        except Exception as e:
            print(f"Selecao: {e}")

        # Download
        print("Baixando...")
        try:
            async with page.expect_download(timeout=15000) as dl:
                await page.click("text=Download", timeout=5000)
            download = await dl.value
            xls_path = "/tmp/relatorio.xls"
            await download.save_as(xls_path)
            print(f"XLS salvo!")
            await browser.close()
            return xls_path
        except Exception as e:
            print(f"Erro download: {e}")
            await browser.close()
            return None


def parse_xls(xls_path):
    if not xls_path:
        return {}

    hoje = date.today().strftime("%d/%m/%Y")
    print(f"Buscando: {hoje}")

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
