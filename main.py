import asyncio
import os
import re
import requests
from datetime import datetime, date
from playwright.async_api import async_playwright

DATASYSTEM_BASE = "https://lepoa11672.useserver.com.br/RETAGUARDA"
DATASYSTEM_URL  = f"{DATASYSTEM_BASE}/Inteligencia/Tendencia"
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

        # Passo 1: vai para a raiz do sistema para pegar o formulário de login
        print("Abrindo tela de login...", flush=True)
        await page.goto(DATASYSTEM_BASE + "/", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        print(f"URL: {page.url}", flush=True)

        # Debug: mostra todos os inputs
        inputs = await page.query_selector_all("input")
        print(f"Inputs na pagina: {len(inputs)}", flush=True)
        for inp in inputs:
            t = await inp.get_attribute("type") or "text"
            n = await inp.get_attribute("name") or ""
            i = await inp.get_attribute("id") or ""
            print(f"  input type={t} name={n} id={i}", flush=True)

        # Passo 2: preenche login
        try:
            # Usuario
            user_input = await page.query_selector("input[type='text'], input[name*='user'], input[name*='User'], input[id*='user'], input[id*='User'], input:not([type='password']):not([type='hidden'])")
            if user_input:
                await user_input.fill(DATASYSTEM_USER)
                print(f"Usuario preenchido", flush=True)

            # Senha
            pass_input = await page.query_selector("input[type='password']")
            if pass_input:
                await pass_input.fill(DATASYSTEM_PASS)
                print(f"Senha preenchida", flush=True)

            # Loja (dropdown)
            select = await page.query_selector("select")
            if select:
                options = await select.query_selector_all("option")
                for opt in options:
                    txt = await opt.inner_text()
                    val = await opt.get_attribute("value") or ""
                    print(f"  opcao loja: '{txt}' val='{val}'", flush=True)
                # Seleciona a opção que contém MATRIZ
                for opt in options:
                    txt = await opt.inner_text()
                    if "MATRIZ" in txt.upper() or "01" in txt:
                        val = await opt.get_attribute("value")
                        await select.select_option(value=val)
                        print(f"Loja selecionada: {txt}", flush=True)
                        break

            # Botão entrar
            btn = await page.query_selector("button, input[type='submit']")
            if btn:
                txt = await btn.inner_text() if await btn.get_attribute("type") != "submit" else "submit"
                print(f"Clicando botao: {txt}", flush=True)
                await btn.click()
            else:
                await page.keyboard.press("Enter")

            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(3000)
            print(f"Pos-login URL: {page.url}", flush=True)

        except Exception as e:
            print(f"Erro no login: {e}", flush=True)

        # Passo 3: navega para o relatório
        print("Navegando para relatorio...", flush=True)
        await page.goto(DATASYSTEM_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        print(f"URL relatorio: {page.url}", flush=True)

        body_text = await page.inner_text("body")
        print(f"Body preview: {body_text[:200]}", flush=True)

        # Passo 4: clica em Confirmar
        try:
            await page.locator("text=Confirmar").click(timeout=15000)
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(5000)
            print("Confirmado!", flush=True)
        except Exception as e:
            print(f"Erro confirmar: {e}", flush=True)
            body_text = await page.inner_text("body")
            print(f"Body apos erro: {body_text[:300]}", flush=True)
            await browser.close()
            return None

        # Passo 5: clica no botão de impressão
        print("Clicando impressora...", flush=True)
        try:
            # Tenta achar o botão de impressão por onclick ou imagem
            els = await page.query_selector_all("[onclick], button, img, a")
            for el in els:
                onclick = await el.get_attribute("onclick") or ""
                src     = await el.get_attribute("src") or ""
                title   = await el.get_attribute("title") or ""
                cls     = await el.get_attribute("class") or ""
                if any(x in (onclick+src+title+cls).lower() for x in ["print","imprim","xls","export"]):
                    print(f"  candidato: onclick={onclick[:60]} src={src} title={title}", flush=True)

            # Clica no primeiro que parecer ser impressão
            await page.locator("[onclick*='print'], [onclick*='Print'], [onclick*='imprimir'], [onclick*='Imprimir']").first.click(timeout=5000)
            await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"Impressora: {e}", flush=True)

        # Passo 6: seleciona XLS + Detalhado e faz download
        try:
            await page.locator("text=.XLS").click(timeout=3000)
            await page.locator("text=Detalhado").click(timeout=3000)
            print("XLS + Detalhado selecionados", flush=True)
        except Exception as e:
            print(f"Selecao: {e}", flush=True)

        try:
            async with page.expect_download(timeout=15000) as dl:
                await page.locator("text=Download").click(timeout=5000)
            download = await dl.value
            xls_path = "/tmp/relatorio.xls"
            await download.save_as(xls_path)
            print("XLS baixado!", flush=True)
            await browser.close()
            return xls_path
        except Exception as e:
            print(f"Erro download: {e}", flush=True)
            await browser.close()
            return None


def parse_xls(xls_path):
    if not xls_path:
        return {}

    hoje = date.today().strftime("%d/%m/%Y")
    print(f"Buscando: {hoje}", flush=True)

    indicadores = {
        "Valor Vendido": "-", "Quantidade de Vendas": "-",
        "Quantidade de Itens": "-", "PA": "-",
        "Ticket Medio": "-", "Vendas Acumuladas": "-",
        "Projecao": "-", "Meta Corrigida": "-",
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
                print(f"Linha encontrada: {cols}", flush=True)
                indicadores["Quantidade de Vendas"] = cols[COL_QTD_VENDAS]
                indicadores["Quantidade de Itens"]  = cols[COL_QTD_ITENS]
                indicadores["PA"]                   = cols[COL_PA]
                indicadores["Ticket Medio"]         = cols[COL_TICKET]
                indicadores["Valor Vendido"]        = cols[COL_VALOR]
                indicadores["Vendas Acumuladas"]    = cols[COL_ACUMULADO]
                break
    except Exception as e:
        print(f"Erro parse: {e}", flush=True)

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
        print("Enviado!", flush=True)
    else:
        print(f"Erro envio: {resp.status_code} - {resp.text}", flush=True)


async def executar():
    print(f"=== {datetime.now().strftime('%d/%m/%Y %H:%M')} ===", flush=True)
    xls_path = await baixar_xls()
    indicadores = parse_xls(xls_path)
    mensagem = montar_mensagem(indicadores)
    print("Mensagem:\n", mensagem, flush=True)
    enviar_whatsapp(mensagem)


if __name__ == "__main__":
    asyncio.run(executar())
