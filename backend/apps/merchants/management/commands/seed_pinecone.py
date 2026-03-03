"""
Management command to create/populate the Pinecone index with SKU embeddings.

Uses Google Gemini gemini-embedding-001 (3072 dimensions).

Usage:
    python manage.py seed_pinecone            # Embed & upsert all active SKUs
    python manage.py seed_pinecone --clear    # Delete all vectors first, then re-seed
    python manage.py seed_pinecone --recreate # Delete & recreate the index, then seed
"""
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.merchants.models import SKU

# Gemini gemini-embedding-001 outputs 3072 dimensions
EMBEDDING_DIMENSION = 3072


class Command(BaseCommand):
    help = 'Embed all active SKUs and upsert them into the Pinecone index'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear', action='store_true',
            help='Delete all existing vectors before seeding',
        )
        parser.add_argument(
            '--recreate', action='store_true',
            help='Delete and recreate the entire index (use when changing embedding dimensions)',
        )

    def _embed_with_retry(self, client, text, max_retries=5):
        """Call Gemini embeddings with exponential backoff."""
        for attempt in range(max_retries):
            try:
                result = client.models.embed_content(
                    model=settings.GEMINI_EMBEDDING_MODEL,
                    contents=text,
                )
                return result.embeddings[0].values
            except Exception as e:
                err_msg = str(e).lower()
                if 'quota' in err_msg and 'billing' in err_msg:
                    raise  # billing issue, retries won't help
                wait = 2 ** attempt
                self.stdout.write(
                    self.style.WARNING(f'  Rate limited, retrying in {wait}s... ({e})')
                )
                time.sleep(wait)
        raise RuntimeError(f'Failed after {max_retries} retries')

    def handle(self, *args, **options):
        from pinecone import Pinecone, ServerlessSpec
        from google import genai

        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index_name = settings.PINECONE_INDEX_NAME

        # Recreate index if requested
        if options['recreate']:
            existing = [idx['name'] for idx in pc.list_indexes()]
            if index_name in existing:
                self.stdout.write(f'Deleting existing index "{index_name}"...')
                pc.delete_index(index_name)
                time.sleep(3)
                self.stdout.write('  Deleted')

        # Create index if it doesn't exist
        existing = [idx['name'] for idx in pc.list_indexes()]
        if index_name not in existing:
            self.stdout.write(f'Creating Pinecone index "{index_name}" (dim={EMBEDDING_DIMENSION})...')
            pc.create_index(
                name=index_name,
                dimension=EMBEDDING_DIMENSION,
                metric='cosine',
                spec=ServerlessSpec(cloud='aws', region='us-east-1'),
            )
            # Wait for index to be ready
            while not pc.describe_index(index_name)['status']['ready']:
                self.stdout.write('  Waiting for index to be ready...')
                time.sleep(2)
            self.stdout.write(self.style.SUCCESS(f'  Index "{index_name}" created'))
        else:
            self.stdout.write(f'Index "{index_name}" already exists')

        index = pc.Index(index_name)

        # Clear if requested
        if options['clear']:
            self.stdout.write('Clearing all vectors...')
            index.delete(delete_all=True)
            self.stdout.write('  Cleared')

        # Get all active SKUs
        skus = SKU.objects.filter(is_active=True).select_related('merchant')
        if not skus.exists():
            self.stdout.write(self.style.WARNING('No active SKUs found. Run seed_data first.'))
            return

        self.stdout.write(f'Embedding {skus.count()} SKUs using Gemini ({settings.GEMINI_EMBEDDING_MODEL})...')

        client = genai.Client(api_key=settings.GOOGLE_API_KEY)

        sku_list = list(skus)
        total_upserted = 0
        batch_vectors = []

        for i, sku in enumerate(sku_list):
            text = (
                f"{sku.name} - {sku.description} - "
                f"Category: {sku.category} - "
                f"Price: ${sku.original_price}"
            )
            if sku.discounted_price:
                text += f" (Now ${sku.discounted_price})"

            # Embed single SKU with retry
            vector = self._embed_with_retry(client, text)

            batch_vectors.append({
                'id': f'sku-{sku.id}',
                'values': vector,
                'metadata': {
                    'merchant_id': sku.merchant_id,
                    'sku_id': sku.id,
                    'name': sku.name,
                    'description': sku.description[:500],
                    'category': sku.category,
                    'original_price': float(sku.original_price),
                    'discounted_price': float(sku.discounted_price) if sku.discounted_price else None,
                    'landing_url': sku.landing_url,
                    'stock_quantity': sku.stock_quantity,
                },
            })

            SKU.objects.filter(pk=sku.pk).update(pinecone_vector_id=f'sku-{sku.id}')
            self.stdout.write(f'  [{i + 1}/{len(sku_list)}] Embedded: {sku.name}')

            # Upsert in batches of 50 or at the end
            if len(batch_vectors) >= 50 or i == len(sku_list) - 1:
                index.upsert(vectors=batch_vectors)
                total_upserted += len(batch_vectors)
                batch_vectors = []

            # Small delay to avoid rate limits
            time.sleep(0.2)

        # Verify
        time.sleep(2)
        stats = index.describe_index_stats()
        self.stdout.write(self.style.SUCCESS(
            f'\nPinecone seeding complete!'
            f'\n  Total vectors upserted: {total_upserted}'
            f'\n  Index vector count: {stats.get("total_vector_count", "unknown")}'
        ))
