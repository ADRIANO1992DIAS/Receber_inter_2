import base64
import mimetypes
import os
import re
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple

import requests
from django.utils import timezone

from billing.constants import DEFAULT_WHATSAPP_SAUDACAO_TEMPLATE
from billing.models import Boleto, WhatsappConfig
from billing.services.inter_service import InterService


def _get_env_value(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value not in (None, ""):
            return value
    return default


def _load_whatsapp_settings() -> Dict[str, str]:
    cfg = WhatsappConfig.get_solo()
    return {
        "base_url": cfg.evolution_base_url or _get_env_value("EVOLUTION_BASE_URL", "EVOLUTION_API_URL", default="http://localhost:8080"),
        "instance_id": cfg.evolution_instance_id or _get_env_value("EVOLUTION_INSTANCE_ID", "EVOLUTION_INSTANCE_NAME", default=""),
        "api_key": cfg.evolution_api_key or _get_env_value("EVOLUTION_API_KEY", "EVOLUTION_AUTHENTICATION_API_KEY", "AUTHENTICATION_API_KEY", default=""),
        "pix_key": cfg.whatsapp_pix_key or _get_env_value("WHATSAPP_PIX_KEY", default="47.303.364/0001-04"),
    }


def _normalize_phone_digits(cliente) -> str:
    raw = f"{cliente.ddd or ''}{cliente.telefone or ''}"
    digits = re.sub(r"\D", "", raw)
    if not digits and cliente.telefone:
        digits = re.sub(r"\D", "", cliente.telefone)
    if not digits:
        return ""

    if digits.startswith("55") and len(digits) in (12, 13):
        return digits

    if len(digits) in (10, 11):
        return f"55{digits}"

    if len(digits) == 9 and cliente.ddd:
        ddd_digits = re.sub(r"\D", "", cliente.ddd)[:3]
        return f"55{ddd_digits}{digits}"

    return ""


def format_whatsapp_phone(cliente) -> Optional[str]:
    digits = _normalize_phone_digits(cliente)
    if not digits:
        return None
    if digits.endswith("@s.whatsapp.net"):
        return digits
    return f"{digits}@s.whatsapp.net"


def _evolution_number(phone: str) -> Optional[str]:
    if not phone:
        return None
    if "@s.whatsapp.net" in phone:
        return phone.split("@", 1)[0]
    return re.sub(r"\D", "", phone)


def _evo_headers(api_key: str, as_json: bool) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    if api_key:
        headers["apikey"] = api_key
    if as_json:
        headers["Content-Type"] = "application/json"
    return headers


def _evo_post(cfg: Dict[str, str], endpoint: str, *, payload: Optional[Dict[str, Any]] = None, files: Optional[Dict[str, Any]] = None, as_json: bool = True) -> Dict[str, Any]:
    base = (cfg.get("base_url") or "").rstrip("/")
    instance_id = cfg.get("instance_id") or ""
    api_key = cfg.get("api_key") or ""
    if not base or not instance_id:
        return {
            "ok": False,
            "error": "Configuracao da Evolution API ausente (base_url/instance_id)",
            "status_code": None,
            "payload": None,
        }

    endpoint = endpoint.lstrip("/")
    url = f"{base}/{endpoint}/{instance_id}"

    try:
        request_kwargs: Dict[str, Any] = {"timeout": 20, "headers": _evo_headers(api_key, as_json and not files)}
        if files:
            request_kwargs["files"] = files
            request_kwargs["data"] = payload or {}
        elif as_json:
            request_kwargs["json"] = payload or {}
        else:
            request_kwargs["data"] = payload or {}

        response = requests.post(url, **request_kwargs)
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc), "status_code": None, "payload": None}

    try:
        parsed = response.json()
    except ValueError:
        parsed = {"raw": response.text}

    ok = response.status_code in (200, 201) and isinstance(parsed, dict) and not parsed.get("error")
    return {
        "ok": ok,
        "status_code": response.status_code,
        "payload": parsed,
        "error": None if ok else parsed.get("error") if isinstance(parsed, dict) else "Resposta invalida",
    }


def send_whatsapp_message(cfg: Dict[str, str], phone: str, message: str) -> Dict[str, Any]:
    number = _evolution_number(phone)
    if not number:
        return {"ok": False, "error": "Numero invalido", "status_code": None, "payload": None}
    return _evo_post(
        cfg,
        "message/sendText",
        payload={"number": number, "text": message},
        as_json=True,
    )


def _media_metadata(file_path: Path) -> Tuple[str, str]:
    mimetype, _ = mimetypes.guess_type(str(file_path))
    if not mimetype:
        mimetype = "application/octet-stream"
    if mimetype.startswith("image/"):
        media_type = "image"
    elif mimetype.startswith("video/"):
        media_type = "video"
    else:
        media_type = "document"
    return media_type, mimetype


def send_whatsapp_file(cfg: Dict[str, str], phone: str, file_path: Path) -> Dict[str, Any]:
    number = _evolution_number(phone)
    if not number:
        return {"ok": False, "error": "Numero invalido", "status_code": None, "payload": None}
    if not file_path.exists():
        return {"ok": False, "error": f"Arquivo nao encontrado: {file_path}", "status_code": None, "payload": None}
    try:
        media_base64 = base64.b64encode(file_path.read_bytes()).decode("ascii")
    except OSError as exc:
        return {"ok": False, "error": f"Falha ao ler arquivo: {exc}", "status_code": None, "payload": None}

    media_type, mimetype = _media_metadata(file_path)
    caption = Path(file_path).stem[:500] or "Boleto"

    payload = {
        "number": number,
        "mediatype": media_type,
        "mimetype": mimetype,
        "caption": caption,
        "media": media_base64,
        "fileName": file_path.name,
    }

    return _evo_post(cfg, "message/sendMedia", payload=payload)


def _format_valor(valor) -> str:
    try:
        return f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    except Exception:
        return str(valor)


def _refrescar_codigos_boleto(boleto: Boleto) -> str:
    """
    Busca detalhes no Inter quando o boleto ainda nao possui linha digitavel/codigo de barras.
    """
    identificadores = [
        (boleto.nosso_numero, "nosso_numero"),
        (boleto.codigo_solicitacao, "codigo_solicitacao"),
        (boleto.tx_id, "tx_id"),
    ]
    try:
        inter = InterService()
    except Exception:
        return ""

    for identificador, campo in identificadores:
        if not identificador:
            continue
        try:
            detalhe = inter.recuperar_cobranca_detalhada(identificador, campo=campo)
        except Exception:
            detalhe = None
        if not detalhe:
            continue

        update_fields: List[str] = []
        codigo_barras = detalhe.get("codigoBarras") or ""
        linha_digitavel = detalhe.get("linhaDigitavel") or ""
        nosso_numero = detalhe.get("nossoNumero") or ""
        codigo_solicitacao = detalhe.get("codigoSolicitacao") or ""
        tx_id = detalhe.get("txId") or detalhe.get("txid") or ""

        if codigo_barras and codigo_barras != boleto.codigo_barras:
            boleto.codigo_barras = codigo_barras
            update_fields.append("codigo_barras")
        if linha_digitavel and linha_digitavel != boleto.linha_digitavel:
            boleto.linha_digitavel = linha_digitavel
            update_fields.append("linha_digitavel")
        if nosso_numero and nosso_numero != boleto.nosso_numero:
            boleto.nosso_numero = nosso_numero
            update_fields.append("nosso_numero")
        if codigo_solicitacao and codigo_solicitacao != boleto.codigo_solicitacao:
            boleto.codigo_solicitacao = codigo_solicitacao
            update_fields.append("codigo_solicitacao")
        if tx_id and tx_id != boleto.tx_id:
            boleto.tx_id = tx_id
            update_fields.append("tx_id")

        if update_fields:
            boleto.save(update_fields=update_fields)

        return boleto.codigo_barras or boleto.linha_digitavel or ""

    return ""


def dispatch_boleto_via_whatsapp(
    boleto: Boleto,
    *,
    pix_key: Optional[str] = None,
    saudacao_template: Optional[str] = None,
) -> Dict[str, Any]:
    cfg = _load_whatsapp_settings()
    cliente = boleto.cliente
    phone = format_whatsapp_phone(cliente)
    if not phone:
        return {"boleto_id": boleto.id, "cliente": cliente.nome, "ok": False, "error": "Telefone invalido ou ausente"}

    if not boleto.pdf:
        return {"boleto_id": boleto.id, "cliente": cliente.nome, "ok": False, "error": "Boleto sem PDF anexado"}

    pdf_path = Path(boleto.pdf.path)
    if not pdf_path.exists():
        return {"boleto_id": boleto.id, "cliente": cliente.nome, "ok": False, "error": f"Arquivo nao encontrado: {pdf_path}"}

    vencimento = boleto.data_vencimento.strftime("%d/%m/%Y") if boleto.data_vencimento else "sem data"
    valor = _format_valor(boleto.valor)
    codigo = boleto.codigo_barras or boleto.linha_digitavel or ""
    pix = pix_key or cfg.get("pix_key") or ""

    steps: List[Dict[str, Any]] = []

    if not saudacao_template:
        try:
            saudacao_template = WhatsappConfig.get_solo().saudacao_template
        except Exception:
            saudacao_template = DEFAULT_WHATSAPP_SAUDACAO_TEMPLATE

    saudacao = _time_based_saudacao()
    template_context = {
        "vencimento": vencimento,
        "valor": valor,
        "cliente": cliente.nome,
        "ven": vencimento,
        "va": valor,
        "saudacao": saudacao,
    }
    try:
        mensagem_inicial = saudacao_template.format(**template_context)
    except KeyError as exc:
        return {
            "boleto_id": boleto.id,
            "cliente": cliente.nome,
            "ok": False,
            "error": f"Variavel ausente no template da mensagem: {exc}",
        }
    for texto in [mensagem_inicial, "Segue a chave pix cnpj", pix]:
        resultado = send_whatsapp_message(cfg, phone, texto)
        steps.append({"tipo": "mensagem", "conteudo": texto, **resultado})
        if not resultado.get("ok"):
            return {"boleto_id": boleto.id, "cliente": cliente.nome, "ok": False, "phone": phone, "steps": steps}

    arquivo_resultado = send_whatsapp_file(cfg, phone, pdf_path)
    steps.append({"tipo": "arquivo", "conteudo": str(pdf_path), **arquivo_resultado})
    if not arquivo_resultado.get("ok"):
        return {"boleto_id": boleto.id, "cliente": cliente.nome, "ok": False, "phone": phone, "steps": steps}

    if not codigo:
        codigo = _refrescar_codigos_boleto(boleto)
        steps.append(
            {
                "tipo": "atualizacao_codigo",
                "conteudo": "recuperar_detalhe_inter" if codigo else "nao_disponivel",
                "ok": bool(codigo),
            }
        )

    if codigo:
        codigo_resultado = send_whatsapp_message(cfg, phone, codigo)
        steps.append({"tipo": "mensagem", "conteudo": codigo, **codigo_resultado})
        if not codigo_resultado.get("ok"):
            return {"boleto_id": boleto.id, "cliente": cliente.nome, "ok": False, "phone": phone, "steps": steps}

    return {"boleto_id": boleto.id, "cliente": cliente.nome, "ok": True, "phone": phone, "steps": steps}


def _time_based_saudacao() -> str:
    agora = timezone.localtime()
    hora = agora.hour
    if 0 <= hora < 12:
        return "Bom dia!"
    if 12 <= hora < 18:
        return "Boa tarde!"
    return "Boa noite!"
