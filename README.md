# Contas a Receber + Boletos (Banco Inter) - Django

Aplicacao web para controlar clientes recorrentes, gerar boletos mensais e integrar com a API do Banco Inter. Agora inclui isolamento por usuario, armazenamento criptografado das credenciais do Inter/WhatsApp e painel para configurar ambos.

## Stack
- Python 3.12+ e Django 5.0.7
- Postgres (psycopg3 binario)
- Gunicorn em producao
- Credenciais criptografadas via Fernet (django-fernet-fields)

## Fluxo principal
- Cadastre clientes e gere boletos mensais; acompanhe status, download individual/lote e cancelamento via API Inter.
- Baixe PDFs e envie via WhatsApp (Evolution API) usando credenciais criptografadas em `/config/whatsapp/`.
- Conciliacao: importe CSV e vincule automaticamente a boletos.

## Instalacao local
```bash
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\activate  # ou source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
```

## Variaveis de ambiente (config/inter/.env)
Exemplo:
```env
FERNET_KEYS=CHAVE_FERNET_ATUAL
SECRET_KEY=... # gere via os.urandom
DEBUG=0
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://localhost,https://127.0.0.1
DJANGO_SETTINGS_MODULE=config.settings

DB_NAME=receber_inter
DB_USER=receber_user
DB_PASSWORD=receber_pass
DB_HOST=db
DB_PORT=5432

# Banco Inter
CLIENT_ID=...
CLIENT_SECRET=...
CONTA_CORRENTE=...
CERT_PATH=Inter_API_Certificado.crt
KEY_PATH=Inter_API_Chave.key

# Evolution / WhatsApp
EVOLUTION_BASE_URL=...
EVOLUTION_INSTANCE_ID=...
EVOLUTION_API_KEY=...
WHATSAPP_PIX_KEY=...

# Superuser dev (usar so em DEBUG)
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=ChangeMe!123
```

### Gerar chave Fernet
```bash
python -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```
`FERNET_KEYS` aceita varias chaves separadas por virgula para rotacao; a primeira criptografa, todas descriptografam.

## Comandos uteis
- Rodar server dev: `python manage.py runserver`
- Criar superuser em dev (so com DEBUG=1): `python manage.py create_superuser_dev`
- Limpar midias sensiveis: `python manage.py clearmedia`
- Envio WhatsApp: configure em `/config/whatsapp/` (staff) e use `/enviaboleto/`.

## Docker
```bash
docker compose up --build -d
```
- Web em `http://localhost:8000`
- Volumes montados: `media/`, `private/`, `backup/`, `data/`, `static`, `staticfiles`
- Gunicorn via entrypoint; migrations rodadas na subida

## Seguranca
- Credenciais do Inter e Evolution armazenadas criptografadas em banco
- Certificado/chave do Inter armazenados como blobs cifrados
- `FERNET_KEYS` e `SECRET_KEY` devem vir do ambiente/secret manager
- DEBUG desligado por padrao; cookies e HSTS configurados

## Rotas chave
- `/config/inter/` (staff): credenciais Inter + upload certificado/chave (criptografado)
- `/config/whatsapp/` (staff): Evolution API + chave PIX (criptografado)
- `/clientes`, `/boletos`, `/conciliacao`, `/enviaboleto`

## Observacoes
- Apagar banco existente se estiver migrando a partir de versao antiga; migrations foram squashed em `0001_initial`.
- Certifique-se de reenvio dos certificados/chaves e credenciais apos recriar o banco.
