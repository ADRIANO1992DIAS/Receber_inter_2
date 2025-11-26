# Contas a Receber + Boletos (Banco Inter) - Django

Aplicacao web para controlar clientes recorrentes, gerar boletos mensais e integrar com a API do Banco Inter. O projeto nasce minimalista (templates simples + Django admin) e prioriza clareza de codigo para iterarmos rapido.

## Recursos principais
- Cadastro de clientes com dados completos do sacado e dia de vencimento padrao.
- Geracao mensal de boletos com status acompanhados em `/boletos`, incluindo reprocessamento em massa e baixa manual.
- Download individual ou em lote (ZIP) dos PDFs armazenados em `./media/boletos/`.
- Cancelamento direto via API Inter (usa `codigo_solicitacao` e cai para `nosso_numero` se preciso).
- Hooks para conectar scripts proprios em `inter_api/` quando quiser substituir a simulacao.

## Stack e decisoes
- Python 3.12 + Django 5.0 (ver `requirements.txt`).
- SQLite persistido em `./data/db.sqlite3`; montamos como volume no Docker para manter historico.
- Credenciais do Inter agora ficam no banco (tela `/config/inter/`), com arquivos armazenados em `media/inter_credentials/`.
- `requests` faz as chamadas HTTP; `python-dotenv` segue disponivel para utilitarios CLI em `inter_api/`.
- `entrypoint.sh` aplica migracoes, coleta estaticos e cria o superusuario definido nas variaveis antes de subir o `runserver`.

## Credenciais do Banco Inter (app web)
1) Acesse `/config/inter/` logado e preencha `Client ID`, `Client Secret`, `Conta corrente`.
2) Anexe o certificado (.crt/.pem) e a chave (.key/.pem). Os arquivos ficam em `media/inter_credentials/` e nao sao versionados.
3) O `InterService` usa apenas o que estiver salvo nessa tela (nao depende mais de variaveis no `.env`).

## Credenciais para scripts CLI (opcional)
Os scripts em `inter_api/` permitem testar emissao/baixa fora do Django. Para eles, use `config/inter/.env`:

```env
CLIENT_ID=
CLIENT_SECRET=
CONTA_CORRENTE=
CERT_PATH=Inter_API_Certificado.crt   # caminho relativo a config/inter/ ou absoluto
KEY_PATH=Inter_API_Chave.key          # caminho relativo a config/inter/ ou absoluto

DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=
DJANGO_SUPERUSER_PASSWORD=
```

Coloque os arquivos `.crt` e `.key` em `config/inter/` ou informe caminhos absolutos.

## Executando com Docker Desktop
```bash
docker compose up --build -d
# App:   http://localhost:8000
# Admin: http://localhost:8000/admin/
```
No primeiro start o `entrypoint` cria o superusuario definido no `.env`. Os volumes `./data`, `./media`, `./static` e `./staticfiles` permanecem sincronizados com o host para facilitar backup e inspecao. Depois de logar, acesse `/config/inter/` para cadastrar as credenciais do Banco Inter.

## Executando localmente (sem Docker)
```bash
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.env\Scriptsctivate            # ou source .venv/bin/activate no Linux/macOS
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser  # opcional se ja estiver configurado no .env
python manage.py runserver
```
Preencha as credenciais do Inter em `/config/inter/` apos acessar o app.

## Fluxo sugerido
1. Acesse `/admin` e cadastre clientes ou utilize a tela simplificada em `/clientes`.
2. Em `/gerar`, selecione ano/mes, escolha os clientes e gere os boletos; o sistema respeita o dia de vencimento individual.
3. Acompanhe em `/boletos`: baixe PDFs, marque como pagos, reenvie ou cancele conforme necessario.

## Integracao com scripts proprios
Se deseja usar implementacoes customizadas (por exemplo, wrappers legados da API do Inter), adicione os modulos abaixo ao lado do `manage.py`:
- `inter_api/emitir_boletos.py`
- `inter_api/baixar_boletos_pdf.py`

Assinaturas esperadas:

```python
# emitir_boletos.py
def emitir_boleto_unico(cliente: dict, data_vencimento, client_id, client_secret,
                        conta_corrente, cert_path, key_path) -> dict:
    return {
        "nossoNumero": "...",
        "linhaDigitavel": "...",
        "codigoBarras": "...",
        "txId": "...",
        "pdfBytes": b"...",  # opcional
    }

# baixar_boletos_pdf.py
def baixar_pdf_por_nosso_numero(nosso_numero: str, client_id, client_secret,
                                conta_corrente, cert_path, key_path) -> bytes:
    return b"%PDF..."  # conteudo completo do PDF
```

Caso esses modulos nao existam, o sistema simula a emissao (gera `nossoNumero` fake) e nao tenta baixar PDFs externos.

## Estrutura principal
- `billing/`: models, forms, views e servicos que falam com o Banco Inter.
- `config/`: settings, urls e arquivos ASGI/WSGI do projeto.
- `templates/`: HTML simples utilizado pelas views customizadas.
- `data/`, `media/`, `static/`, `staticfiles/`: montados como volumes no Docker.
- `inter_api/`: ponto opcional para scripts externos (ignorado quando vazio).

## Observacoes
- A base SQLite e os PDFs ficam fora da imagem para preservar historico entre deploys.
- A pagina de boletos permite selecionar varios registros e baixar um unico `.zip`.
- O cancelamento utiliza `InterService.cancelar_boleto` e faz fallback para outro endpoint quando necessario.
- A interface esta propositalmente simples; o plano e evoluir com Tailwind ou outro framework quando as regras estiverem maduras.

## WhatsApp (Evolution API)
Para enviar boletos automaticamente pelo WhatsApp, configure as seguintes variaveis no `config/inter/.env`:

- `EVOLUTION_BASE_URL` (ou `EVOLUTION_API_URL` do projeto whatsapp_ai_bot)
- `EVOLUTION_INSTANCE_ID` (ou `EVOLUTION_INSTANCE_NAME`)
- `EVOLUTION_API_KEY`, `EVOLUTION_AUTHENTICATION_API_KEY` ou `AUTHENTICATION_API_KEY`
- `WHATSAPP_PIX_KEY` (opcional, cai no CNPJ padrao caso nao seja informado)

Quando estiver rodando o stack Docker deste projeto, mantenha o `EVOLUTION_BASE_URL` apontando para `http://evolution-api:8080`, que e o hostname interno exposto pelo container evolution-api.

Essas variaveis tambem sao usadas pelo stack Docker incluso neste repositorio. O arquivo `evolution/.env.example` foi copiado do projeto pycodebr/whatsapp_ai_bot; basta duplica-lo para `evolution/.env`, ajustar `EVOLUTION_INSTANCE_NAME` e `AUTHENTICATION_API_KEY`, e entao executar `docker compose up --build -d` para subir a API (`evolution-api`), Postgres e Redis no Docker Desktop.
### Testando a conexao com a Evolution API
O comando abaixo replica o helper `evolution_api.py` do projeto [whatsapp_ai_bot](https://github.com/pycodebr/whatsapp_ai_bot) e envia uma mensagem simples para validar a autenticacao/configuracao:

```bash
python manage.py test_whatsapp_connection 5599999999999 --mensagem "Teste de conexao"
```

Use um numero proprio para o teste (o comando apenas dispara a mensagem e imprime a resposta da API). Em caso de erro, verifique se as variaveis acima estao preenchidas.
