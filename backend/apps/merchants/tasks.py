from celery import shared_task


@shared_task
def sync_pinecone_vectors(merchant_id):
    """Re-embed and upsert all SKU data to Pinecone when SKUs change."""
    from .models import SKU
    from apps.conversations.bot.rag import upsert_sku

    skus = SKU.objects.filter(merchant_id=merchant_id, is_active=True)
    for sku in skus:
        upsert_sku(sku)
