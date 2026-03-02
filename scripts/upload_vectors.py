"""Upload all active SKU data to Pinecone vector database."""
import os
import sys
import django

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'salescount.settings.dev')
django.setup()

from apps.merchants.models import SKU
from apps.conversations.bot.rag import upsert_sku


def upload():
    skus = SKU.objects.filter(is_active=True)
    total = skus.count()
    print(f"Uploading {total} SKUs to Pinecone...")

    for i, sku in enumerate(skus, 1):
        try:
            upsert_sku(sku)
            print(f"  [{i}/{total}] Uploaded: {sku.name}")
        except Exception as e:
            print(f"  [{i}/{total}] FAILED: {sku.name} - {e}")

    print(f"\nDone! Uploaded {total} SKUs.")


if __name__ == '__main__':
    upload()
