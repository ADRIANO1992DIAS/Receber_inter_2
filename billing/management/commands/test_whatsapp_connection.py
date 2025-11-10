import json

from django.core.management.base import BaseCommand, CommandError

from billing.services.whatsapp_service import (
    EVOLUTION_API_KEY,
    EVOLUTION_BASE_URL,
    EVOLUTION_INSTANCE_ID,
    send_whatsapp_message,
)


class Command(BaseCommand):
    help = (
        "Envia uma mensagem de teste usando a Evolution API para confirmar a conexao "
        "(equivalente ao exemplo evolution_api.py do projeto whatsapp_ai_bot)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "numero",
            help=(
                "Numero de destino. Pode ser informado apenas com digitos (5599999999999) "
                "ou no formato completo 5599999999999@s.whatsapp.net."
            ),
        )
        parser.add_argument(
            "--mensagem",
            dest="mensagem",
            default="Mensagem de teste do Contas a Receber.",
            help="Texto que sera enviado na mensagem de teste.",
        )

    def handle(self, *args, **options):
        numero = options["numero"]
        mensagem = options["mensagem"]

        missing_bits = []
        if not EVOLUTION_INSTANCE_ID:
            missing_bits.append("EVOLUTION_INSTANCE_ID ou EVOLUTION_INSTANCE_NAME")
        if not EVOLUTION_API_KEY:
            missing_bits.append("EVOLUTION_API_KEY ou AUTHENTICATION_API_KEY")
        if missing_bits:
            raise CommandError(
                "Variaveis de ambiente ausentes: " + ", ".join(missing_bits)
            )

        self.stdout.write(
            f"Testando envio via Evolution API (instancia='{EVOLUTION_INSTANCE_ID}' base='{EVOLUTION_BASE_URL}')."
        )

        resultado = send_whatsapp_message(numero, mensagem)
        payload = resultado.get("payload")
        status_code = resultado.get("status_code")
        if resultado.get("ok"):
            if isinstance(payload, (dict, list)):
                payload_text = json.dumps(payload, ensure_ascii=False)
            else:
                payload_text = str(payload)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Mensagem enviada com sucesso (status={status_code}). Resposta: {payload_text}"
                )
            )
            return

        detalhe = resultado.get("error") or payload or "Resposta vazia"
        raise CommandError(
            f"Falha ao enviar mensagem de teste (status={status_code}): {detalhe}"
        )
