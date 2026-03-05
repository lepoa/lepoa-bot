import asyncio
import os
import requests
from datetime import datetime, date
from playwright.async_api import async_playwright

# ─── CONFIGURAÇÕES ────────────────────────────────────────────
DATASYSTEM_URL = "https://lepoa11672.useserver.com.br/RETAGUARDA/Inteligencia/Tendencia"
DATASYSTEM_USER = os.environ.get("DS_USER", "")
DATASYSTEM_PASS = os.environ.get("DS_PASS", "")

ZAPI_INSTANCE = os.environ.get("ZAPI_INSTANCE", "3EFAD2909069028ADC8E6237BF5854B6")
ZAPI_TOKEN    = os.environ.get("ZAPI_TOKEN",    "3543270E8FE1C9AEA4383932")
ZAPI_CLIENT   = os.environ.get("ZAPI_CLIENT",   "F26521e4d25334eb0846c707873e47080S")
ZAPI_GROUP_ID = os.environ.get("ZAPI_GROUP_ID", "")

LOJA_NOME = "Le Poá Loja 01 - Matriz"
# ──────────────────────────────────────────────────────────────


async def buscar_dados_datasystem():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print("Acessando DataSystem...")
        await page.goto("https://lepoa11672.useserver.com.br/RETAGUARDA/", wait_until="networkidle", timeout=30000)

        try:
            await page.wait_for_selector("input[type='text']", timeout=8000)
            await page.fill("input[type='text']", DATASYSTEM_USER)
            await page.fill("input[type='password']", DATASYSTEM_PASS)
            await page.keyboard.press("Enter")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)
            print("Login realizado!")
        except Exception as e:
            print(f"Login: {e}")

        print("Acessando relatorio de Tendencia...")
        await page.goto(DATASYSTEM_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)

        try:
            await page.click("text=Confirmar")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(4000)
            print("Relatorio gerado!")
        except Exception as e:
            print(f"Confirmar: {e}")

        hoje = date.today().strftime("%d/%m/%Y")
        print(f"Buscando dados de hoje: {hoje}")

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
            rows = await page.query_selector_all("tr")
            for row in rows:
                cells = await row.query_selector_all("td")
                if not cells:
                    continue
                texts = [await c.inner_text() for c in cells]

                if texts and hoje in texts[0]:
                    print(f"Linha de hoje: {texts}")
                    if len(texts) >= 9:
                        indicadores["Quantidade de Vendas"] = texts[1].strip()
                        indicadores["Quantidade de Itens"]  = texts[2].strip()
                        indicadores["PA"]                   = texts[3].strip()
                        indicadores["Ticket Medio"]         = texts[5].strip()
                        indicadores["Valor Vendido"]        = texts[7].strip()
                        indicadores["Vendas Acumuladas"]    = texts[8].strip()

                if texts and texts[0].strip() == "TOTAL" and len(texts) >= 14:
                    t = texts[11].strip()
                    m = texts[13].strip()
                    indicadores["Projecao"]      = t if t not in ["0,00","0","","–"] else "-"
                    indicadores["Meta Corrigida"] = m if m not in ["0,00","0","","–"] else "-"

        except Exception as e:
            print(f"Erro tabela: {e}")

        await browser.close()
        return indicadores


def montar_mensagem(ind):
    agora = datetime.now().strftime("%d/%m/%Y as %H:%M")
    def v(k): return ind.get(k) or "-"
    msg = (
        f"Resumo de Vendas - {LOJA_NOME}\n"
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
    return msg


def enviar_whatsapp(mensagem):
    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}/send-text"
    headers = {"Content-Type": "application/json", "client-token": ZAPI_CLIENT}
    payload = {"phone": ZAPI_GROUP_ID, "message": mensagem}
    resp = requests.post(url, json=payload, headers=headers)
    if resp.status_code == 200:
        print("Mensagem enviada!")
    else:
        print(f"Erro: {resp.status_code} - {resp.text}")


async def executar():
    print(f"Iniciando - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    indicadores = await buscar_dados_datasystem()
    mensagem = montar_mensagem(indicadores)
    print("Mensagem:\n", mensagem)
    enviar_whatsapp(mensagem)


if __name__ == "__main__":
    asyncio.run(executar())
