"""RAG (Retrieval Augmented Generation) module using Pinecone."""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def get_pinecone_index():
    """Initialize and return Pinecone index."""
    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        return pc.Index(settings.PINECONE_INDEX_NAME)
    except Exception as e:
        logger.error(f"Failed to connect to Pinecone: {e}")
        return None


def embed_text(text: str) -> list[float]:
    """Embed text using OpenAI embeddings."""
    import openai
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding


def retrieve_relevant_products(query: str, merchant_id: int, top_k: int = 5) -> tuple[str, list[int]]:
    """Retrieve relevant products from Pinecone and format as context string.

    Returns:
        tuple of (context_string, list_of_sku_ids)
    """
    index = get_pinecone_index()
    if not index:
        return _fallback_db_retrieval(merchant_id, query)

    try:
        query_vector = embed_text(query)
        results = index.query(
            vector=query_vector,
            top_k=top_k,
            filter={"merchant_id": merchant_id},
            include_metadata=True,
        )

        if not results.matches:
            return _fallback_db_retrieval(merchant_id, query)

        context_parts = []
        sku_ids = []
        for match in results.matches:
            meta = match.metadata
            sku_id = meta.get('sku_id')
            if sku_id:
                sku_ids.append(sku_id)
            part = (
                f"- {meta.get('name', 'Product')}: {meta.get('description', '')}\n"
                f"  Category: {meta.get('category', 'N/A')} | "
                f"  Price: ${meta.get('original_price', '?')}"
            )
            if meta.get('discounted_price'):
                part += f" -> ${meta['discounted_price']} (SALE)"
            if meta.get('stock_quantity', 0) > 0 and meta.get('stock_quantity', 999) < 10:
                part += f" | Only {meta['stock_quantity']} left!"
            part += f"\n  Link: [product_link:{sku_id or ''}]"
            context_parts.append(part)

        return "\n".join(context_parts), sku_ids

    except Exception as e:
        logger.error(f"Pinecone query failed: {e}")
        return _fallback_db_retrieval(merchant_id, query)


def _fallback_db_retrieval(merchant_id: int, query: str) -> tuple[str, list[int]]:
    """Fallback: retrieve products from the database when Pinecone is unavailable."""
    from apps.merchants.models import SKU

    skus = SKU.objects.filter(
        merchant_id=merchant_id,
        is_active=True,
    ).order_by('-updated_at')[:5]

    if not skus:
        return "No products available at the moment.", []

    parts = []
    sku_ids = []
    for sku in skus:
        sku_ids.append(sku.id)
        part = (
            f"- {sku.name}: {sku.description[:100]}\n"
            f"  Category: {sku.category} | Price: ${sku.original_price}"
        )
        if sku.discounted_price:
            part += f" -> ${sku.discounted_price} (SALE)"
        if 0 < sku.stock_quantity < 10:
            part += f" | Only {sku.stock_quantity} left!"
        part += f"\n  Link: [product_link:{sku.id}]"
        parts.append(part)

    return "\n".join(parts), sku_ids


def upsert_sku(sku) -> None:
    """Embed and upsert a single SKU to Pinecone."""
    index = get_pinecone_index()
    if not index:
        logger.warning("Pinecone not available, skipping upsert")
        return

    text = f"{sku.name} - {sku.description} - Category: {sku.category} - Price: ${sku.original_price}"
    if sku.discounted_price:
        text += f" (Now ${sku.discounted_price})"

    try:
        vector = embed_text(text)
        index.upsert(vectors=[{
            "id": f"sku-{sku.id}",
            "values": vector,
            "metadata": {
                "merchant_id": sku.merchant_id,
                "sku_id": sku.id,
                "name": sku.name,
                "description": sku.description,
                "category": sku.category,
                "original_price": float(sku.original_price),
                "discounted_price": float(sku.discounted_price) if sku.discounted_price else None,
                "landing_url": sku.landing_url,
                "stock_quantity": sku.stock_quantity,
            },
        }])
        sku.pinecone_vector_id = f"sku-{sku.id}"
        sku.save(update_fields=['pinecone_vector_id'])
    except Exception as e:
        logger.error(f"Failed to upsert SKU {sku.id}: {e}")
