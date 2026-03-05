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

HEADERS_BROWSER = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def fazer_login_http():
    """Tenta fazer login via requests HTTP e retorna a sessão autenticada."""
    session = requests.Session()
    session.headers.update(HEADERS_BROWSER)

    # Testa varias URLs possiveis de login
    urls_teste = [
        DATASYSTEM_BASE + "/",
        DATASYSTEM_BASE + "/Login",
        DATASYSTEM_BASE + "/Account/Login",
        DATASYSTEM_BASE + "/Home/Login",
        DATASYSTEM_BASE + "/Usuario/Login",
        "https://lepoa11672.useserver.com.br/",
    ]

    print("=== TESTE DE URLs ===", flush=True)
    for url in urls_teste:
        try:
            r = session.get(url, timeout=10, allow_redirects=True)
            print(f"  GET {url} -> {r.status_code} ({len(r.text)} chars)", flush=True)
            if r.status_code == 200 and len(r.text) > 100:
                print(f"  Conteudo: {r.text[:200]}", flush=True)
                break
        except Exception as e:
            print(f"  GET {url} -> ERRO: {e}", flush=True)

    # Tenta POST de login em varios endpoints
    print("=== TESTE DE LOGIN POST ===", flush=True)
    login_urls = [
        DATASYSTEM_BASE + "/Login",
        DATASYSTEM_BASE + "/Account/Login",
        DATASYSTEM_BASE + "/Usuario/Autenticar",
        DATASYSTEM_BASE + "/Home/Autenticar",
        DATASYSTEM_BASE + "/api/login",
        DATASYSTEM_BASE + "/api/auth",
    ]

    payloads = [
        {"usuario": DATASYSTEM_USER, "senha": DATASYSTEM_PASS},
        {"user": DATASYSTEM_USER, "password": DATASYSTEM_PASS},
        {"login": DATASYSTEM_USER, "senha": DATASYSTEM_PASS},
        {"Username": DATASYSTEM_USER, "Password": DATASYSTEM_PASS},
        {"usuario": DATASYSTEM_USER, "senha": DATASYSTEM_PASS, "loja": "1"},
    ]

    for url in login_urls:
        for payload in payloads[:2]:
            try:
                r = session.post(url, json=payload, timeout=10)
                print(f"  POST {url} json={list(payload.keys())} -> {r.status_code}", flush=True)
                if r.status_code in [200, 201, 302]:
                    print(f"  Resposta: {r.text[:200]}", flush=True)
            except Exception as e:
                pass

            try:
                r = session.post(url, data=payload, timeout=10)
                print(f"  POST {url} form={list(payload.keys())} -> {r.status_code}", flush=True)
                if r.status_code in [200, 201, 302]:
                    print(f"  Resposta: {r.text[:200]}", flush=True)
            except Exception as e:
                pass

    return None


async def baixar_xls():
    # Primeiro tenta descobrir o endpoint de login
    fazer_login_http()
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
    # Nao envia ainda, so debug
    # enviar_whatsapp(msg)

if __name__ == "__main__":
    asyncio.run(executar())
