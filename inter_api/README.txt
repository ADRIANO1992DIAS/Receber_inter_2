# Scripts CLI Banco Inter (opcional)

Os scripts em `inter_api/` permitem testar emissao/baixa fora do Django. Eles usam `config/inter/.env` para ler:

```
CLIENT_ID=
CLIENT_SECRET=
CONTA_CORRENTE=
CERT_PATH=Inter_API_Certificado.crt
KEY_PATH=Inter_API_Chave.key
```

Use apenas para testes locais; em producao o app web usa credenciais criptografadas via `/config/inter/`.
