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

COL_DATA=1; COL_QTD_VENDAS=2; COL_QTD_ITENS=3; COL_PA=4
COL_TICKET=6; COL_VALOR=8; COL_ACUMULADO=9


async def baixar_xls():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print("Abrindo login...", flush=True)
        await page.goto(DATASYSTEM_BASE + "/", timeout=30000)

        # Espera o JS renderizar o formulário (até 15 segundos)
        print("Aguardando formulario JS carregar...", flush=True)
        try:
            await page.wait_for_selector("input", timeout=15000)
            print("Formulario encontrado!", flush=True)
        except:
            # Mostra o HTML bruto para debug
            html = await page.content()
            print(f"HTML (300 chars): {html[:300]}", flush=True)

        await page.wait_for_timeout(2000)

        # Lista todos os inputs
        inputs = await page.query_selector_all("input")
        print(f"Total inputs: {len(inputs)}", flush=True)
        for inp in inputs:
            t = await inp.get_attribute("type") or "text"
            n = await inp.get_attribute("name") or ""
            i = await inp.get_attribute("id") or ""
            ph = await inp.get_attribute("placeholder") or ""
            print(f"  input: type={t} name={n} id={i} placeholder={ph}", flush=True)

        # Preenche usuario (primeiro input não-hidden)
        try:
            user_input = await page.query_selector("input:not([type='hidden']):not([type='password'])")
            if user_input:
                await user_input.fill(DATASYSTEM_USER)
                print("Usuario preenchido", flush=True)
            else:
                print("AVISO: input usuario nao encontrado!", flush=True)
        except Exception as e:
            print(f"Erro usuario: {e}", flush=True)

        # Preenche senha
        try:
            pass_input = await page.query_selector("input[type='password']")
            if pass_input:
                await pass_input.fill(DATASYSTEM_PASS)
                print("Senha preenchida", flush=True)
            else:
                print("AVISO: input senha nao encontrado!", flush=True)
        except Exception as e:
            print(f"Erro senha: {e}", flush=True)

        # Seleciona loja
        try:
            select = await page.query_selector("select")
            if select:
                options = await select.query_selector_all("option")
                print(f"Opcoes de loja: {len(options)}", flush=True)
                for opt in options:
                    txt = await opt.inner_text()
                    val = await opt.get_attribute("value") or ""
                    print(f"  '{txt}' = '{val}'", flush=True)
                    if "MATRIZ" in txt.upper() or "01" in txt:
                        await select.select_option(value=val)
                        print(f"Loja selecionada: {txt}", flush=True)
                        break
        except Exception as e:
            print(f"Erro loja: {e}", flush=True)

        # Clica em Entrar
        try:
            await page.click("text=Entrar", timeout=5000)
            print("Clicou Entrar", flush=True)
        except:
            try:
                await page.click("button, input[type='submit']", timeout=5000)
                print("Clicou botao submit", flush=True)
            except Exception as e:
                print(f"Erro botao entrar: {e}", flush=True)

        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(3000)
        print(f"Pos-login: {page.url}", flush=True)

        # Navega para o relatorio
        print("Indo para relatorio...", flush=True)
        await page.goto(DATASYSTEM_URL, timeout=30000)
        await page.wait_for_timeout(3000)

        body = await page.inner_text("body")
        print(f"Relatorio body: {body[:300]}", flush=True)

        if "401" in body or "Unauthorized" in body:
            print("ERRO: Ainda sem autorizacao. Login falhou.", flush=True)
            await browser.close()
            return None

        # Clica Confirmar
        try:
            await page.locator("text=Confirmar").click(timeout=15000)
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(5000)
            print("Confirmado!", flush=True)
        except Exception as e:
            print(f"Erro confirmar: {e}", flush=True)
            await browser.close()
            return None

        # Acha botao de impressao
        print("Procurando botao impressora...", flush=True)
        els = await page.query_selector_all("[onclick]")
        for el in els:
            onclick = await el.get_attribute("onclick") or ""
            tag = await el.evaluate("el => el.tagName")
            print(f"  [{tag}] onclick={onclick[:80]}", flush=True)

        try:
            await page.locator("[onclick*='print'], [onclick*='Print'], [onclick*='imprimir']").first.click(timeout=5000)
            await page.wait_for_timeout(2000)
            print("Impressora clicada!", flush=True)
        except Exception as e:
            print(f"Impressora: {e}", flush=True)

        # XLS + Detalhado
        try:
            await page.locator("text=.XLS").click(timeout=3000)
            await page.locator("text=Detalhado").click(timeout=3000)
            print("XLS+Detalhado OK", flush=True)
        except Exception as e:
            print(f"Selecao: {e}", flush=True)

        # Download
        try:
            async with page.expect_download(timeout=20000) as dl:
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
                print(f"Linha hoje: {cols}", flush=True)
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
        f"*Resumo de Vendas - {LOJA_NOME}*\n{agora}\n\n"
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
        print(f"Erro: {resp.status_code} {resp.text}", flush=True)


async def executar():
    print(f"=== {datetime.now().strftime('%d/%m/%Y %H:%M')} ===", flush=True)
    xls_path = await baixar_xls()
    ind = parse_xls(xls_path)
    msg = montar_mensagem(ind)
    print(msg, flush=True)
    enviar_whatsapp(msg)

if __name__ == "__main__":
    asyncio.run(executar())
