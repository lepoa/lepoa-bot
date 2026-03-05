import schedule
import time
import asyncio
import sys

print("=== SCHEDULER INICIADO ===", flush=True)
sys.stdout.flush()

from main import executar

print("=== MAIN IMPORTADO ===", flush=True)

def job():
    print("=== JOB INICIADO ===", flush=True)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(executar())
    finally:
        loop.close()
    print("=== JOB FINALIZADO ===", flush=True)

# Agenda 22:00 UTC = 19:00 BRT
schedule.every().day.at("22:00").do(job)

print("Agendado para 22:00 UTC (19:00 BRT)", flush=True)
print("Rodando teste imediato...", flush=True)

# Roda imediatamente
job()

print("Teste concluido. Aguardando 19h...", flush=True)

while True:
    schedule.run_pending()
    time.sleep(30)
