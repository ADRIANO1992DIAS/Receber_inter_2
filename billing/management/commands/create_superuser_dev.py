import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()


class Command(BaseCommand):
    help = "Cria um superusuario apenas em ambiente de desenvolvimento (DEBUG=True)."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Este comando so pode ser executado com DEBUG=True.")
        username = os.getenv("DJANGO_SUPERUSER_USERNAME")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")
        if not all([username, password]):
            raise CommandError("Defina DJANGO_SUPERUSER_USERNAME e DJANGO_SUPERUSER_PASSWORD para usar este comando.")
        if User.objects.filter(username=username).exists():
            self.stdout.write("Superusuario ja existe; nenhuma acao tomada.")
            return
        User.objects.create_superuser(username=username, email=email or "", password=password)
        self.stdout.write(f"Superusuario '{username}' criado com sucesso (DEBUG).");
