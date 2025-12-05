import base64
from typing import Optional

from celery import shared_task
from django.core.files.base import ContentFile
from django.utils import timezone

from billing.models import Boleto
from billing.services.inter_service import InterService


def _pdf_filename(boleto: Boleto) -> str:
    base = f"boleto-{boleto.id}.pdf"
    return base


def _dados_pagador(boleto: Boleto) -> dict:
    cli = boleto.cliente
    return {
        "valorNominal": float(cli.valorNominal),
        "nome": cli.nome,
        "cpfCnpj": cli.cpfCnpj,
        "email": cli.email,
        "ddd": cli.ddd or "85",
        "telefone": cli.telefone or "985134478",
        "endereco": cli.endereco,
        "numero": cli.numero,
        "complemento": cli.complemento,
        "bairro": cli.bairro,
        "cidade": cli.cidade,
        "uf": cli.uf,
        "cep": cli.cep,
    }


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=10, retry_kwargs={"max_retries": 3})
def emitir_boleto_task(self, boleto_id: int) -> str:
    boleto: Optional[Boleto] = None
    try:
        boleto = Boleto.objects.select_related("cliente").get(id=boleto_id)
    except Boleto.DoesNotExist:
        return "boleto_nao_encontrado"

    if boleto.status == Boleto.STATUS_EMITIDO:
        return "ja_emitido"

    inter = InterService()
    cli_dict = _dados_pagador(boleto)
    resultado = inter.emitir_boleto(cli_dict, boleto.data_vencimento)

    pdf_base64 = resultado.get("pdfBytes")
    pdf_saved = False
    if pdf_base64:
        try:
            pdf_bytes = base64.b64decode(pdf_base64)
        except Exception:
            pdf_bytes = b""
        if pdf_bytes:
            boleto.pdf.save(_pdf_filename(boleto), ContentFile(pdf_bytes), save=False)
            pdf_saved = True

    boleto.nosso_numero = resultado.get("nossoNumero", "")
    boleto.linha_digitavel = resultado.get("linhaDigitavel", "")
    boleto.codigo_barras = resultado.get("codigoBarras", "")
    boleto.tx_id = resultado.get("txId", "")
    boleto.codigo_solicitacao = resultado.get("codigoSolicitacao", "")
    boleto.status = Boleto.STATUS_EMITIDO
    boleto.erro_msg = ""
    boleto.whatsapp_status_updated_at = timezone.now()
    boleto.save()

    return "emitido_com_pdf" if pdf_saved else "emitido"


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=10, retry_kwargs={"max_retries": 3})
def baixar_pdf_task(self, boleto_id: int) -> str:
    try:
        boleto = Boleto.objects.get(id=boleto_id)
    except Boleto.DoesNotExist:
        return "boleto_nao_encontrado"

    inter = InterService()
    ident = boleto.nosso_numero or boleto.codigo_solicitacao or boleto.tx_id
    if not ident:
        return "identificador_indisponivel"

    pdf_bytes = inter.baixar_pdf(ident, campo="nosso_numero" if boleto.nosso_numero else "codigo_solicitacao")
    if not pdf_bytes:
        return "pdf_indisponivel"

    boleto.pdf.save(_pdf_filename(boleto), ContentFile(pdf_bytes), save=False)
    boleto.save(update_fields=["pdf"])
    return "pdf_salvo"
