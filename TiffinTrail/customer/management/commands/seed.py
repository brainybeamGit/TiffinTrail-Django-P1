"""
Django Management Command: python manage.py seed
Executes the original user data seeder located in docs/seeds.py.
"""

from django.core.management.base import BaseCommand
import importlib.util
import os
import sys
from django.conf import settings


class Command(BaseCommand):
    help = "Seeds database with the original TiffinTrail user & business records from docs/seeds.py."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Initializing TiffinTrail original data seeder..."))

        docs_seeds_path = os.path.join(settings.BASE_DIR, "docs", "seeds.py")
        if not os.path.exists(docs_seeds_path):
            self.stderr.write(self.style.ERROR(f"Seeds file not found at: {docs_seeds_path}"))
            return

        spec = importlib.util.spec_from_file_location("docs_seeds", docs_seeds_path)
        seeds_module = importlib.util.module_from_spec(spec)
        sys.modules["docs_seeds"] = seeds_module
        spec.loader.exec_module(seeds_module)

        if hasattr(seeds_module, "run_seed"):
            seeds_module.run_seed()
            self.stdout.write(self.style.SUCCESS("Database seeding from docs/seeds.py finished successfully."))
        else:
            self.stderr.write(self.style.ERROR("Function 'run_seed' not found in docs/seeds.py."))

