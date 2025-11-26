## inter_api

Pasta opcional para scripts de integracao direta com a API do Banco Inter. Util se voce quiser rodar emissao/baixa de boletos fora do Django (CLI ou automacoes externas) sem depender do servico interno.

### Como funciona
- O app Django usa as credenciais salvas na tela `/config/inter/` e nao le mais o `.env` para producao.
- Estes scripts CLI continuam lendo `config/inter/.env` para facilitar testes locais. Preencha `CLIENT_ID`, `CLIENT_SECRET`, `CONTA_CORRENTE`, `CERT_PATH`, `KEY_PATH` e coloque os arquivos `.crt/.key` na mesma pasta.

### Assinaturas esperadas
Caso voce crie suas proprias versoes:

```
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

Se os modulos nao existirem, o sistema Django simula a emissao e nao tenta baixar PDFs reais.

### Dicas de uso via CLI
- Copie `config/inter/.env.example` para `config/inter/.env` e preencha com suas credenciais reais.
- Coloque `Inter_API_Certificado.crt` e `Inter_API_Chave.key` em `config/inter/` (ou aponte caminhos absolutos).
- Rode, por exemplo, `python inter_api/emitir_boletos.py` para testar chamadas diretas.

### Seguranca
Nao faca commit dos arquivos `.env`, `.crt` e `.key`. Eles estao no `.gitignore` por padrao. Mantenha as credenciais apenas localmente ou em cofres seguros.
