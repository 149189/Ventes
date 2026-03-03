"""RAG (Retrieval Augmented Generation) module using Pinecone + Gemini embeddings."""
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
    """Embed text using Google Gemini embeddings."""
    from google import genai

    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    result = client.models.embed_content(
        model=settings.GEMINI_EMBEDDING_MODEL,
        contents=text,
    )
    return result.embeddings[0].values


def _format_price(amount) -> str:
    """Format a price in Indian Rupees."""
    try:
        val = int(float(amount))
        if val >= 1000:
            return f"Rs.{val:,}"
        return f"Rs.{val}"
    except (ValueError, TypeError):
        return f"Rs.{amount}"


def retrieve_relevant_products(query: str, merchant_id: int, top_k: int = 3) -> tuple[str, list[int]]:
    """Retrieve relevant products from Pinecone and format as compact context.

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

            name = meta.get('name', 'Product')
            desc = meta.get('description', '')
            category = meta.get('category', '')
            price = _format_price(meta.get('original_price', '?'))
            line = f"{name} ({category}) - {desc} - {price}"

            disc = meta.get('discounted_price')
            if disc:
                line += f" NOW {_format_price(disc)}"

            stock = meta.get('stock_quantity', 999)
            if 0 < stock < 10:
                line += f" (Only {stock} left!)"

            context_parts.append(line)

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
    ).order_by('-updated_at')[:3]

    if not skus:
        return "No products available at the moment.", []

    parts = []
    sku_ids = []
    for sku in skus:
        sku_ids.append(sku.id)
        line = f"{sku.name} ({sku.category}) - {sku.description[:150]} - {_format_price(sku.original_price)}"
        if sku.discounted_price:
            line += f" NOW {_format_price(sku.discounted_price)}"
        if 0 < sku.stock_quantity < 10:
            line += f" (Only {sku.stock_quantity} left!)"
        parts.append(line)

    return "\n".join(parts), sku_ids


def upsert_sku(sku) -> None:
    """Embed and upsert a single SKU to Pinecone."""
    index = get_pinecone_index()
    if not index:
        logger.warning("Pinecone not available, skipping upsert")
        return

    text = f"{sku.name} - {sku.description} - Category: {sku.category} - Rs.{sku.original_price}"
    if sku.discounted_price:
        text += f" (Now Rs.{sku.discounted_price})"

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
