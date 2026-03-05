import asyncio
import os
import requests
from datetime import datetime
from playwright.async_api import async_playwright

# ─── CONFIGURAÇÕES ────────────────────────────────────────────
DATASYSTEM_URL = "https://lepoa11672.useserver.com.br/RETAGUARDA/Inteligencia/Tendencia"
DATASYSTEM_USER = os.environ.get("DS_USER", "")
DATASYSTEM_PASS = os.environ.get("DS_PASS", "")

ZAPI_INSTANCE = os.environ.get("ZAPI_INSTANCE", "3EFAD2909069028ADC8E6237BF5854B6")
ZAPI_TOKEN    = os.environ.get("ZAPI_TOKEN",    "3543270E8FE1C9AEA4383932")
ZAPI_CLIENT   = os.environ.get("ZAPI_CLIENT",   "F26521e4d25334eb0846c707873e47080S")
ZAPI_GROUP_ID = os.environ.get("ZAPI_GROUP_ID", "")   # será preenchido depois

LOJA_NOME = "Le Poá Loja 01 - Matriz"
# ──────────────────────────────────────────────────────────────


async def buscar_dados_datasystem():
    """Acessa o DataSystem e extrai os dados do relatório de tendência."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print("🔐 Acessando DataSystem...")
        await page.goto(DATASYSTEM_URL, wait_until="networkidle", timeout=30000)

        # Faz login se necessário
        try:
            await page.wait_for_selector("input[type='text'], input[name='login'], input[id*='user']", timeout=5000)
            await page.fill("input[type='text']", DATASYSTEM_USER)
            await page.fill("input[type='password']", DATASYSTEM_PASS)
            await page.keyboard.press("Enter")
            await page.wait_for_load_state("networkidle")
            print("✅ Login realizado!")
        except:
            print("ℹ️ Login não necessário ou já autenticado.")

        # Aguarda o relatório carregar
        await page.wait_for_timeout(4000)

        # Captura o texto da página toda
        conteudo = await page.inner_text("body")
        print("📄 Conteúdo capturado!")

        await browser.close()
        return conteudo


def extrair_indicadores(texto):
    """Extrai os indicadores do texto capturado da página."""
    import re

    indicadores = {
        "Valor Vendido": None,
        "Quantidade de Vendas": None,
        "Quantidade de Itens": None,
        "PA": None,
        "Ticket Médio": None,
        "Vendas Acumuladas": None,
        "Projeção": None,
        "Meta Corrigida": None,
    }

    linhas = texto.split("\n")
    for i, linha in enumerate(linhas):
        linha_lower = linha.lower()
        for chave in indicadores:
            if chave.lower() in linha_lower and indicadores[chave] is None:
                # Tenta pegar o valor na mesma linha ou na próxima
                valor = re.search(r"R?\$?\s?[\d.,]+", linha)
                if not valor and i + 1 < len(linhas):
                    valor = re.search(r"R?\$?\s?[\d.,]+", linhas[i + 1])
                if valor:
                    indicadores[chave] = valor.group().strip()

    return indicadores


def montar_mensagem(indicadores):
    """Monta a mensagem formatada para o WhatsApp."""
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")

    def val(k):
        return indicadores.get(k) or "–"

    msg = f"""📊 *Resumo de Vendas — {LOJA_NOME}*
🗓️ {agora}

💰 *Valor Vendido:* {val("Valor Vendido")}
🛒 *Qtd. Vendas:* {val("Quantidade de Vendas")}
📦 *Qtd. Itens:* {val("Quantidade de Itens")}
👟 *PA:* {val("PA")}
🎯 *Ticket Médio:* {val("Ticket Médio")}
📈 *Vendas Acumuladas:* {val("Vendas Acumuladas")}
🔮 *Projeção:* {val("Projeção")}
🏆 *Meta Corrigida:* {val("Meta Corrigida")}

_Enviado automaticamente pelo sistema Le Poá_ 🤖"""
    return msg


def enviar_whatsapp(mensagem):
    """Envia a mensagem para o grupo via Z-API."""
    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}/send-text"
    headers = {
        "Content-Type": "application/json",
        "client-token": ZAPI_CLIENT,
    }
    payload = {
        "phone": ZAPI_GROUP_ID,
        "message": mensagem,
    }
    resp = requests.post(url, json=payload, headers=headers)
    if resp.status_code == 200:
        print("✅ Mensagem enviada no WhatsApp!")
    else:
        print(f"❌ Erro ao enviar: {resp.status_code} — {resp.text}")


async def executar():
    print(f"\n🚀 Iniciando coleta — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    texto = await buscar_dados_datasystem()
    indicadores = extrair_indicadores(texto)
    mensagem = montar_mensagem(indicadores)
    print("\n📋 Mensagem gerada:\n", mensagem)
    enviar_whatsapp(mensagem)


if __name__ == "__main__":
    asyncio.run(executar())
