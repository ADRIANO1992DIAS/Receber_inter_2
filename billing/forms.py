import mimetypes
import os
import shutil
import subprocess
import tempfile

import magic
from django import forms
from django.db.models import QuerySet
from django.utils import timezone

from billing.utils.crypto import encrypt_bytes
from .models import Cliente, Boleto, ConciliacaoLancamento, WhatsappConfig, InterConfig

MAX_UPLOAD_SIZE = 5 * 1024 * 1024
ALLOWED_MIME_PDF = {"application/pdf"}
ALLOWED_MIME_CSV = {"text/csv", "text/plain", "application/vnd.ms-excel"}
ALLOWED_MIME_XLSX = {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
ALLOWED_MIME_CERT = {
    "application/x-x509-ca-cert",
    "application/pkix-cert",
    "application/pkcs12",
    "application/pkcs8",
    "application/x-pkcs12",
    "application/x-pem-file",
    "application/x-ssh-key",
    "application/octet-stream",
    "text/plain",
    "text/x-ssh-private-key",
}


def _magic_mime(uploaded_file) -> str:
    try:
        head = uploaded_file.read(4096)
        uploaded_file.seek(0)
        if not head:
            return ""
        return magic.from_buffer(head, mime=True) or ""
    except Exception:
        uploaded_file.seek(0)
        guessed, _ = mimetypes.guess_type(uploaded_file.name or "")
        return guessed or ""


def _clamd_scan(uploaded_file):
    scanner = shutil.which("clamdscan")
    if not scanner:
        return
    handle, temp_path = tempfile.mkstemp()
    try:
        with os.fdopen(handle, "wb") as tmp:
            for chunk in uploaded_file.chunks() if hasattr(uploaded_file, "chunks") else [uploaded_file.read()]:
                tmp.write(chunk)
        uploaded_file.seek(0)
        result = subprocess.run([scanner, "--no-summary", temp_path], capture_output=True, text=True)
        if result.returncode not in (0, 1):
            raise forms.ValidationError("Falha ao executar antivirus.")
        if result.returncode == 1:
            raise forms.ValidationError("Arquivo rejeitado pelo antivirus (clamdscan).")
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass
        uploaded_file.seek(0)


def _validate_upload(uploaded_file, *, allowed_mimes, field_label: str):
    if not uploaded_file:
        return uploaded_file
    size = getattr(uploaded_file, "size", 0) or 0
    if size > MAX_UPLOAD_SIZE:
        raise forms.ValidationError(f"{field_label}: tamanho acima do limite de 5MB.")

    mime_type = _magic_mime(uploaded_file).lower()
    if mime_type and mime_type not in {m.lower() for m in allowed_mimes}:
        raise forms.ValidationError(f"{field_label}: tipo de arquivo nao permitido ({mime_type}).")

    _clamd_scan(uploaded_file)
    uploaded_file.seek(0)
    return uploaded_file


def _coerce_int_or_none(value):
    if value in (None, "", "None"):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class SelecionarClientesForm(forms.Form):
    ano = forms.IntegerField(
        min_value=2000,
        max_value=2100,
        initial=2025,
        label="Ano",
        widget=forms.NumberInput(
            attrs={"min": 2000, "max": 2100, "style": "appearance:auto;"}
        ),
    )
    mes = forms.IntegerField(
        min_value=1,
        max_value=12,
        initial=9,
        label="Mes",
        widget=forms.NumberInput(
            attrs={"min": 1, "max": 12, "style": "appearance:auto;"}
        ),
    )
    dia = forms.TypedChoiceField(
        required=False,
        coerce=_coerce_int_or_none,
        choices=[],
        label="Filtrar por dia do vencimento",
    )
    nome = forms.CharField(
        required=False,
        label="Filtrar por nome",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Buscar por nome",
                "class": "w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700 shadow-sm placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200",
            }
        ),
    )
    clientes = forms.ModelMultipleChoiceField(
        queryset=Cliente.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label="Selecione os clientes para gerar boletos",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)

        if not self.is_bound:
            hoje = timezone.localdate()
            if hoje:
                self.initial.setdefault("ano", hoje.year)
                self.initial.setdefault("mes", hoje.month)
            self.fields["ano"].initial = self.initial.get("ano", self.fields["ano"].initial)
            self.fields["mes"].initial = self.initial.get("mes", self.fields["mes"].initial)

        clientes_qs = Cliente.objects.filter(ativo=True)
        if self.owner:
            clientes_qs = clientes_qs.filter(owner=self.owner)

        nome_raw = ""
        if self.is_bound:
            nome_raw = (self.data.get(self.add_prefix("nome")) or "").strip()
        else:
            nome_raw = (self.initial.get("nome") or "").strip()
        if nome_raw:
            clientes_qs = clientes_qs.filter(nome__icontains=nome_raw)
            self.initial["nome"] = nome_raw
        self.fields["nome"].initial = nome_raw

        dias_disponiveis = (
            clientes_qs.order_by("dataVencimento")
            .values_list("dataVencimento", flat=True)
            .distinct()
        )
        choices = [("", "Todos os vencimentos")]
        choices.extend((str(dia), f"Dia {dia:02d}") for dia in dias_disponiveis)
        self.fields["dia"].choices = choices

        dia_raw = (
            self.data.get(self.add_prefix("dia"))
            if self.is_bound
            else self.initial.get("dia")
        )
        dia_filtrado = _coerce_int_or_none(dia_raw)

        if dia_filtrado:
            clientes_qs = clientes_qs.filter(dataVencimento=dia_filtrado)
            self.initial["dia"] = dia_filtrado
            self.fields["dia"].initial = str(dia_filtrado)
        elif not self.is_bound and "dia" not in self.initial:
            self.fields["dia"].initial = ""

        self.filtered_clientes = clientes_qs.order_by("nome")
        self.fields["clientes"].queryset = self.filtered_clientes
        self.fields["clientes"].label_from_instance = self._formatar_label

        selected_ids = set()
        if self.is_bound:
            data = getattr(self.data, "getlist", None)
            if callable(data):
                selected_ids = {str(val) for val in self.data.getlist(self.add_prefix("clientes"))}
            else:
                raw = self.data.get(self.add_prefix("clientes"))
                if raw:
                    if isinstance(raw, (list, tuple, set)):
                        selected_ids = {str(val) for val in raw}
                    else:
                        selected_ids = {str(raw)}
        else:
            initial = self.initial.get("clientes")
            if initial:
                if isinstance(initial, (list, tuple, set, QuerySet)):
                    selected_ids = {str(getattr(val, "pk", val)) for val in initial}
                else:
                    selected_ids = {str(getattr(initial, "pk", initial))}
        self.selected_cliente_ids = selected_ids

    @staticmethod
    def _formatar_label(cliente: Cliente) -> str:
        return (
            f"{cliente.nome} - CNPJ: {cliente.cpfCnpj} - "
            f"Vencimento dia {cliente.dataVencimento:02d}"
        )


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            "nome",
            "cpfCnpj",
            "ativo",
            "valorNominal",
            "dataVencimento",
            "email",
            "ddd",
            "telefone",
            "endereco",
            "numero",
            "complemento",
            "bairro",
            "cidade",
            "uf",
            "cep",
        ]
        widgets = {
            "dataVencimento": forms.NumberInput(attrs={"min": 1, "max": 31}),
            "valorNominal": forms.NumberInput(attrs={"step": "0.01"}),
            "ativo": forms.CheckboxInput(
                attrs={
                    "class": "h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500",
                }
            ),
        }


class BoletoForm(forms.ModelForm):
    class Meta:
        model = Boleto
        fields = [
            "cliente",
            "competencia_ano",
            "competencia_mes",
            "data_vencimento",
            "valor",
            "status",
            "forma_pagamento",
            "nosso_numero",
            "linha_digitavel",
            "codigo_barras",
            "tx_id",
            "codigo_solicitacao",
            "data_pagamento",
            "pdf",
        ]
        widgets = {
            "competencia_ano": forms.NumberInput(attrs={"min": 2000, "max": 2100}),
            "competencia_mes": forms.NumberInput(attrs={"min": 1, "max": 12}),
            "data_vencimento": forms.DateInput(attrs={"type": "date"}),
            "data_pagamento": forms.DateInput(attrs={"type": "date"}),
            "valor": forms.NumberInput(attrs={"step": "0.01"}),
        }

    def clean_pdf(self):
        arquivo = self.cleaned_data.get("pdf")
        return _validate_upload(arquivo, allowed_mimes=ALLOWED_MIME_PDF, field_label="PDF do boleto")


class ClienteImportForm(forms.Form):
    arquivo = forms.FileField(label="Planilha Excel (.xlsx)")

    def clean_arquivo(self):
        arquivo = self.cleaned_data["arquivo"]
        nome = (arquivo.name or "").lower()
        if not nome.endswith(".xlsx"):
            raise forms.ValidationError("Envie um arquivo com extensao .xlsx.")
        _validate_upload(arquivo, allowed_mimes=ALLOWED_MIME_XLSX, field_label="Planilha")
        return arquivo


class ConciliacaoUploadForm(forms.Form):
    arquivo = forms.FileField(label="Extrato em CSV")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["arquivo"].widget.attrs.update(
            {
                "class": "mt-1 block w-full rounded-full border border-slate-300 bg-white px-4 py-2 text-sm text-slate-700 shadow-sm focus:border-brand-300 focus:outline-none focus:ring-2 focus:ring-brand-200",
            }
        )

    def clean_arquivo(self):
        arquivo = self.cleaned_data["arquivo"]
        nome = (arquivo.name or "").lower()
        if not nome.endswith(".csv"):
            raise forms.ValidationError("Envie um arquivo com extensao .csv.")
        return _validate_upload(arquivo, allowed_mimes=ALLOWED_MIME_CSV, field_label="Extrato CSV")


class ConciliacaoLinkForm(forms.Form):
    acao = forms.CharField(widget=forms.HiddenInput(), initial="vincular")
    lancamento_id = forms.IntegerField(widget=forms.HiddenInput())
    boleto_id = forms.IntegerField(required=True)

    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        lancamento_id = cleaned.get("lancamento_id")
        boleto_id = cleaned.get("boleto_id")
        if not lancamento_id or not boleto_id:
            raise forms.ValidationError("Informe o lancamento e o boleto a vincular.")
        lanc_qs = ConciliacaoLancamento.objects
        if self.owner:
            lanc_qs = lanc_qs.filter(owner=self.owner)
        try:
            lancamento = lanc_qs.get(pk=lancamento_id)
        except ConciliacaoLancamento.DoesNotExist as exc:
            raise forms.ValidationError("Lancamento de conciliacao nao foi encontrado.") from exc
        boleto_qs = Boleto.objects.select_related("cliente")
        if self.owner:
            boleto_qs = boleto_qs.filter(cliente__owner=self.owner)
        try:
            boleto = boleto_qs.get(pk=boleto_id)
        except Boleto.DoesNotExist as exc:
            raise forms.ValidationError("Boleto selecionado nao existe mais.") from exc
        if boleto.status not in ("emitido", "atrasado"):
            raise forms.ValidationError("Somente boletos emitidos ou atrasados podem ser conciliados.")
        cleaned["lancamento"] = lancamento
        cleaned["boleto"] = boleto
        return cleaned


class WhatsappMensagemForm(forms.ModelForm):
    class Meta:
        model = WhatsappConfig
        fields = ["saudacao_template"]
        labels = {"saudacao_template": "Mensagem inicial"}
        widgets = {
            "saudacao_template": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": (
                        "mt-1 block w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 "
                        "text-sm text-slate-700 shadow-sm focus:border-emerald-300 "
                        "focus:outline-none focus:ring-2 focus:ring-emerald-200"
                    ),
                }
            )
        }



class WhatsappConfigSecurityForm(forms.ModelForm):
    class Meta:
        model = WhatsappConfig
        fields = ["evolution_base_url", "evolution_instance_id", "evolution_api_key", "whatsapp_pix_key"]
        labels = {
            "evolution_base_url": "Evolution Base URL",
            "evolution_instance_id": "Evolution Instance ID",
            "evolution_api_key": "Evolution API Key",
            "whatsapp_pix_key": "Chave PIX",
        }
        widgets = {
            "evolution_base_url": forms.URLInput(),
            "evolution_instance_id": forms.TextInput(),
            "evolution_api_key": forms.TextInput(),
            "whatsapp_pix_key": forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        text_class = (
            "mt-1 block w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm "
            "text-slate-700 shadow-sm focus:border-brand-300 focus:outline-none focus:ring-2 focus:ring-brand-200"
        )
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({"class": text_class})
        self.fields["evolution_api_key"].widget = forms.PasswordInput(render_value=True, attrs={"class": text_class})

    def clean_evolution_base_url(self):
        url = (self.cleaned_data.get("evolution_base_url") or "").strip()
        if url and not url.startswith(("http://", "https://")):
            raise forms.ValidationError("Informe uma URL valida (http/https).")
        return url


class InterConfigForm(forms.ModelForm):
    cert_file = forms.FileField(required=False, label="Certificado (.crt/.pem)")
    key_file = forms.FileField(required=False, label="Chave privada (.key/.pem)")

    class Meta:
        model = InterConfig
        fields = ["client_id", "client_secret", "conta_corrente"]
        labels = {
            "client_id": "Client ID",
            "client_secret": "Client Secret",
            "conta_corrente": "Conta corrente",
        }
        widgets = {
            "client_id": forms.TextInput(),
            "client_secret": forms.PasswordInput(render_value=True),
            "conta_corrente": forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        text_class = (
            "mt-1 block w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm "
            "text-slate-700 shadow-sm focus:border-brand-300 focus:outline-none focus:ring-2 focus:ring-brand-200"
        )
        file_class = (
            "mt-1 block w-full rounded-full border border-slate-300 bg-white px-4 py-2 text-sm "
            "text-slate-700 shadow-sm file:mr-4 file:rounded-full file:border-0 file:bg-brand-600 "
            "file:px-4 file:py-2 file:text-sm file:font-semibold file:text-slate-900 hover:file:brightness-110"
        )
        for field_name in ("client_id", "client_secret", "conta_corrente"):
            self.fields[field_name].widget.attrs.update({"class": text_class})
        for field_name in ("cert_file", "key_file"):
            self.fields[field_name].widget.attrs.update({"class": file_class, "accept": ".crt,.pem,.key,.cer,.pfx,.p12"})

    def clean_cert_file(self):
        arquivo = self.cleaned_data.get("cert_file")
        if arquivo:
            _validate_upload(arquivo, allowed_mimes=ALLOWED_MIME_CERT, field_label="Certificado")
        return arquivo

    def clean_key_file(self):
        arquivo = self.cleaned_data.get("key_file")
        if arquivo:
            _validate_upload(arquivo, allowed_mimes=ALLOWED_MIME_CERT, field_label="Chave privada")
        return arquivo

    def save(self, commit=True):
        instance = super().save(commit=False)
        cert_upload = self.cleaned_data.get("cert_file")
        key_upload = self.cleaned_data.get("key_file")
        if cert_upload:
            instance.cert_file_encrypted = encrypt_bytes(cert_upload.read())
            instance.cert_file_name = cert_upload.name
        if key_upload:
            instance.key_file_encrypted = encrypt_bytes(key_upload.read())
            instance.key_file_name = key_upload.name
        if commit:
            instance.save()
        return instance
