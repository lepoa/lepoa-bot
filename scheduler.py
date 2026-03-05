import schedule
import time
import asyncio
from main import executar

def job():
    asyncio.run(executar())

# Agenda todo dia às 19:00 (horário de Brasília = UTC-3, então 22:00 UTC)
schedule.every().day.at("22:00").do(job)

print("⏰ Agendador iniciado! Enviará o resumo todo dia às 19:00 (horário de Brasília).")
print("   Aguardando próximo horário agendado...")

while True:
    schedule.run_pending()
    time.sleep(30)
