from pathlib import Path
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Remove arquivos sensiveis (PDFs, certificados) das pastas de media privadas." \
        " Use apenas em ambientes controlados."

    def handle(self, *args, **options):
        targets = [
            Path(settings.MEDIA_ROOT) / "boletos",
            Path(settings.MEDIA_ROOT) / "inter_credentials",
            Path(getattr(settings, "PRIVATE_STORAGE_ROOT", Path(settings.BASE_DIR) / "private")),
        ]
        removidos = 0
        for target in targets:
            if not target.exists():
                continue
            for caminho in target.rglob("*"):
                if caminho.is_file():
                    try:
                        caminho.unlink()
                        removidos += 1
                    except OSError:
                        self.stderr.write(f"Nao foi possivel remover {caminho}")
        self.stdout.write(f"Arquivos removidos: {removidos}")
