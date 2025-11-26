
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0008_cliente_ativo_alter_whatsappconfig_saudacao_template"),
    ]

    operations = [
        migrations.CreateModel(
            name="InterConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("client_id", models.CharField("Client ID", max_length=200, blank=True)),
                ("client_secret", models.CharField("Client Secret", max_length=300, blank=True)),
                ("conta_corrente", models.CharField("Conta corrente", max_length=50, blank=True)),
                ("cert_file", models.FileField(upload_to="inter_credentials/", blank=True, null=True)),
                ("key_file", models.FileField(upload_to="inter_credentials/", blank=True, null=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Configuracao do Inter",
                "verbose_name_plural": "Configuracoes do Inter",
            },
        ),
    ]
