from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from billing.fields import EncryptedTextField

UF_CHOICES = [
    ('AC','AC'),('AL','AL'),('AP','AP'),('AM','AM'),('BA','BA'),('CE','CE'),
    ('DF','DF'),('ES','ES'),('GO','GO'),('MA','MA'),('MT','MT'),('MS','MS'),
    ('MG','MG'),('PA','PA'),('PB','PB'),('PR','PR'),('PE','PE'),('PI','PI'),
    ('RJ','RJ'),('RN','RN'),('RS','RS'),('RO','RO'),('RR','RR'),('SC','SC'),
    ('SP','SP'),('SE','SE'),('TO','TO'),
]


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Cliente",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("valorNominal", models.DecimalField(decimal_places=2, max_digits=12, verbose_name="Valor nominal")),
                ("dataVencimento", models.PositiveSmallIntegerField(verbose_name="Dia do vencimento (1..31)")),
                ("nome", models.CharField(max_length=200, verbose_name="Nome")),
                ("cpfCnpj", models.CharField(max_length=18, verbose_name="CPF/CNPJ")),
                ("ativo", models.BooleanField(default=True, verbose_name="Ativo")),
                ("email", models.EmailField(blank=True, max_length=254, verbose_name="E-mail")),
                ("ddd", models.CharField(blank=True, max_length=3, verbose_name="DDD")),
                ("telefone", models.CharField(blank=True, max_length=20, verbose_name="Telefone")),
                ("endereco", models.CharField(blank=True, max_length=200, verbose_name="Endereco")),
                ("numero", models.CharField(blank=True, max_length=20, verbose_name="Numero")),
                ("complemento", models.CharField(blank=True, max_length=100, verbose_name="Complemento")),
                ("bairro", models.CharField(blank=True, max_length=100, verbose_name="Bairro")),
                ("cidade", models.CharField(blank=True, max_length=100, verbose_name="Cidade")),
                ("uf", models.CharField(blank=True, choices=UF_CHOICES, max_length=2, verbose_name="UF")),
                ("cep", models.CharField(blank=True, max_length=9, verbose_name="CEP")),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="clientes", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ("nome",),
                "unique_together": {("owner", "cpfCnpj")},
            },
        ),
        migrations.CreateModel(
            name="InterConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("client_id", EncryptedTextField(blank=True, verbose_name="Client ID")),
                ("client_secret", EncryptedTextField(blank=True, verbose_name="Client Secret")),
                ("conta_corrente", EncryptedTextField(blank=True, verbose_name="Conta corrente")),
                ("cert_file_name", models.CharField(blank=True, max_length=255)),
                ("key_file_name", models.CharField(blank=True, max_length=255)),
                ("cert_file_encrypted", models.BinaryField(blank=True, null=True)),
                ("key_file_encrypted", models.BinaryField(blank=True, null=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Configuracao do Inter",
                "verbose_name_plural": "Configuracoes do Inter",
            },
        ),
        migrations.CreateModel(
            name="WhatsappConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("saudacao_template", models.TextField(default="{saudacao} {cliente}, segue o boleto com vencimento em {vencimento} no valor de R$ {valor}.")),
                ("evolution_base_url", EncryptedTextField(blank=True, verbose_name="Evolution Base URL")),
                ("evolution_instance_id", EncryptedTextField(blank=True, verbose_name="Evolution Instance ID")),
                ("evolution_api_key", EncryptedTextField(blank=True, verbose_name="Evolution API Key")),
                ("whatsapp_pix_key", EncryptedTextField(blank=True, verbose_name="Chave PIX WhatsApp")),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Configuracao de WhatsApp",
                "verbose_name_plural": "Configuracoes de WhatsApp",
            },
        ),
        migrations.CreateModel(
            name="Boleto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("competencia_ano", models.PositiveSmallIntegerField()),
                ("competencia_mes", models.PositiveSmallIntegerField()),
                ("data_vencimento", models.DateField()),
                ("valor", models.DecimalField(decimal_places=2, max_digits=12)),
                ("nosso_numero", models.CharField(blank=True, max_length=64)),
                ("linha_digitavel", models.CharField(blank=True, max_length=100)),
                ("codigo_barras", models.CharField(blank=True, max_length=100)),
                ("tx_id", models.CharField(blank=True, max_length=100)),
                ("codigo_solicitacao", models.CharField(blank=True, max_length=100)),
                ("status", models.CharField(choices=[("novo", "Novo"), ("emitido", "Emitido"), ("pago", "Pago"), ("cancelado", "Cancelado"), ("erro", "Erro"), ("atrasado", "Atrasado")], default="novo", max_length=10)),
                ("erro_msg", models.TextField(blank=True)),
                ("pdf", models.FileField(blank=True, null=True, upload_to="boletos/")),
                ("data_pagamento", models.DateField(blank=True, null=True)),
                ("forma_pagamento", models.CharField(blank=True, choices=[("", "Nao informado"), ("pix", "PIX"), ("dinheiro", "Dinheiro")], default="", max_length=20)),
                ("whatsapp_status", models.CharField(blank=True, choices=[("pendente", "A enviar"), ("enviado", "Enviado"), ("erro", "Erro")], default="pendente", max_length=20)),
                ("whatsapp_status_detail", models.TextField(blank=True)),
                ("whatsapp_status_updated_at", models.DateTimeField(blank=True, null=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("cliente", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="boletos", to="billing.cliente")),
            ],
            options={
                "unique_together": {("cliente", "competencia_ano", "competencia_mes")},
            },
        ),
        migrations.CreateModel(
            name="ConciliacaoAlias",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("descricao_chave", models.CharField(max_length=255, unique=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("cliente", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="conciliacao_aliases", to="billing.cliente")),
            ],
            options={
                "ordering": ("descricao_chave",),
            },
        ),
        migrations.CreateModel(
            name="ConciliacaoLancamento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("hash_identificador", models.CharField(max_length=128, unique=True)),
                ("data", models.DateField()),
                ("descricao", models.CharField(max_length=255)),
                ("descricao_chave", models.CharField(blank=True, db_index=True, max_length=255)),
                ("valor", models.DecimalField(decimal_places=2, max_digits=12)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("boleto", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="conciliacoes", to="billing.boleto")),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="conciliacao_lancamentos", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ("-data", "-id"),
            },
        ),
    ]
