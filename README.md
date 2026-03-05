# 🤖 Le Poá — Bot de Resumo de Vendas

Envia automaticamente o resumo de vendas do DataSystem para o WhatsApp todo dia às 19h.

## ⚙️ Variáveis de Ambiente (configurar no Railway)

| Variável | Descrição | Exemplo |
|---|---|---|
| `DS_USER` | Seu login do DataSystem | `lais` |
| `DS_PASS` | Sua senha do DataSystem | `suasenha` |
| `ZAPI_INSTANCE` | ID da instância Z-API | `3EFAD29...` |
| `ZAPI_TOKEN` | Token da instância Z-API | `3543270...` |
| `ZAPI_CLIENT` | Client-Token Z-API | `F26521e...` |
| `ZAPI_GROUP_ID` | ID do grupo WhatsApp | `120363XXX@g.us` |

## 🚀 Deploy no Railway

1. Crie um novo repositório no GitHub e suba esses arquivos
2. No Railway, clique em **"Novo Projeto" → "Repositório GitHub"**
3. Selecione o repositório
4. Vá em **"Variáveis"** e configure todas as variáveis acima
5. O Railway vai fazer o build e iniciar automaticamente

## 🧪 Testar manualmente

Para testar sem esperar as 19h, rode no Railway:
```
python main.py
```
