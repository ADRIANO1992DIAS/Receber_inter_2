from pathlib import Path
from django import forms
from django.db.models import QuerySet
from django.utils import timezone

from .models import Cliente, Boleto, ConciliacaoLancamento, WhatsappConfig


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
        super().__init__(*args, **kwargs)

        if not self.is_bound:
            hoje = timezone.localdate()
            if hoje:
                self.initial.setdefault("ano", hoje.year)
                self.initial.setdefault("mes", hoje.month)
            self.fields["ano"].initial = self.initial.get("ano", self.fields["ano"].initial)
            self.fields["mes"].initial = self.initial.get("mes", self.fields["mes"].initial)

        clientes_qs = Cliente.objects.filter(ativo=True)

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


class ClienteImportForm(forms.Form):
    arquivo = forms.FileField(label="Planilha Excel (.xlsx)")


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
        return arquivo


class ConciliacaoLinkForm(forms.Form):
    acao = forms.CharField(widget=forms.HiddenInput(), initial="vincular")
    lancamento_id = forms.IntegerField(widget=forms.HiddenInput())
    boleto_id = forms.IntegerField(required=True)

    def clean(self):
        cleaned = super().clean()
        lancamento_id = cleaned.get("lancamento_id")
        boleto_id = cleaned.get("boleto_id")
        if not lancamento_id or not boleto_id:
            raise forms.ValidationError("Informe o lancamento e o boleto a vincular.")
        try:
            lancamento = ConciliacaoLancamento.objects.get(pk=lancamento_id)
        except ConciliacaoLancamento.DoesNotExist as exc:
            raise forms.ValidationError("Lancamento de conciliacao nao foi encontrado.") from exc
        try:
            boleto = Boleto.objects.get(pk=boleto_id)
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


class InterConfigForm(forms.Form):
    DEFAULT_CERT_NAME = "Inter_API_Certificado.crt"
    DEFAULT_KEY_NAME = "Inter_API_Chave.key"

    client_id = forms.CharField(label="Client ID")
    client_secret = forms.CharField(
        label="Client Secret",
        widget=forms.PasswordInput(render_value=True),
    )
    conta_corrente = forms.CharField(label="Conta corrente")
    cert_path = forms.CharField(label="Nome do certificado (.crt)", required=False)
    cert_file = forms.FileField(label="Upload do certificado", required=False)
    key_path = forms.CharField(label="Nome da chave (.key)", required=False)
    key_file = forms.FileField(label="Upload da chave privada", required=False)

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
        for field_name in ("client_id", "client_secret", "conta_corrente", "cert_path", "key_path"):
            self.fields[field_name].widget.attrs.update({"class": text_class})
        for field_name in ("cert_file", "key_file"):
            self.fields[field_name].widget.attrs.update({"class": file_class, "accept": ".crt,.pem,.key"})

    def clean_cert_file(self):
        arquivo = self.cleaned_data.get("cert_file")
        if arquivo:
            nome = (arquivo.name or "").lower()
            if not nome.endswith((".crt", ".pem", ".cer")):
                raise forms.ValidationError("Envie um certificado com extensao .crt, .cer ou .pem.")
        return arquivo

    def clean_key_file(self):
        arquivo = self.cleaned_data.get("key_file")
        if arquivo:
            nome = (arquivo.name or "").lower()
            if not nome.endswith((".key", ".pem")):
                raise forms.ValidationError("Envie uma chave com extensao .key ou .pem.")
        return arquivo

    def clean_cert_path(self):
        valor = (self.cleaned_data.get("cert_path") or "").strip()
        if not valor:
            return self.DEFAULT_CERT_NAME
        caminho = Path(valor)
        if caminho.is_absolute():
            return str(caminho)
        return caminho.name or self.DEFAULT_CERT_NAME

    def clean_key_path(self):
        valor = (self.cleaned_data.get("key_path") or "").strip()
        if not valor:
            return self.DEFAULT_KEY_NAME
        caminho = Path(valor)
        if caminho.is_absolute():
            return str(caminho)
        return caminho.name or self.DEFAULT_KEY_NAME

