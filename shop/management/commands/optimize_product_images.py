from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from shop.image_optimization import optimize_product_image
from shop.models import ProductImage


class Command(BaseCommand):
    help = "Convert existing catalogue images to resized WebP files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many images would be optimized without changing files.",
        )
        parser.add_argument(
            "--delete-orphans",
            action="store_true",
            help="Delete unreferenced files from media/products after optimization.",
        )

    def handle(self, *args, **options):
        images = ProductImage.objects.exclude(image="")
        eligible = [item for item in images if not item.image.name.lower().endswith((".webp", ".avif"))]

        if options["dry_run"]:
            self.stdout.write(f"{len(eligible)} image(s) would be optimized.")
            if options["delete_orphans"]:
                self.stdout.write(f"{len(self._orphan_files())} orphan file(s) would be deleted.")
            return

        optimized = 0
        skipped = 0
        for product_image in eligible:
            if optimize_product_image(product_image.image):
                ProductImage.objects.filter(pk=product_image.pk).update(image=product_image.image.name)
                optimized += 1
            else:
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Optimization complete: {optimized} optimized, {skipped} skipped."
            )
        )

        if options["delete_orphans"]:
            orphan_files = self._orphan_files()
            reclaimed_bytes = sum(path.stat().st_size for path in orphan_files)
            for path in orphan_files:
                path.unlink()
            self._remove_empty_directories()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Deleted {len(orphan_files)} orphan file(s), reclaiming "
                    f"{reclaimed_bytes / 1024 / 1024:.1f} MB."
                )
            )

    def _orphan_files(self):
        products_root = Path(settings.MEDIA_ROOT) / "products"
        if not products_root.exists():
            return []

        referenced = set(ProductImage.objects.exclude(image="").values_list("image", flat=True))
        return [
            path
            for path in products_root.rglob("*")
            if path.is_file()
            and path.relative_to(Path(settings.MEDIA_ROOT)).as_posix() not in referenced
        ]

    def _remove_empty_directories(self):
        products_root = Path(settings.MEDIA_ROOT) / "products"
        for directory in sorted(
            (path for path in products_root.rglob("*") if path.is_dir()),
            key=lambda path: len(path.parts),
            reverse=True,
        ):
            try:
                directory.rmdir()
            except OSError:
                pass
