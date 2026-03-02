'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import api from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import type { SKU } from '@/types/merchant';

export default function ProductsPage() {
  const [skus, setSkus] = useState<SKU[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSkus();
  }, []);

  async function fetchSkus() {
    try {
      const res = await api.get('/merchants/skus/');
      setSkus(res.data.results || res.data);
    } catch (err) {
      console.error('Failed to fetch SKUs:', err);
    } finally {
      setLoading(false);
    }
  }

  async function toggleActive(sku: SKU) {
    try {
      await api.patch(`/merchants/skus/${sku.id}/`, { is_active: !sku.is_active });
      fetchSkus();
    } catch (err) {
      console.error('Failed to toggle SKU:', err);
    }
  }

  if (loading) return <div className="animate-pulse">Loading products...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Products</h1>
        <div className="flex gap-3">
          <Link href="/products/upload">
            <Button variant="secondary">CSV Upload</Button>
          </Link>
          <Button onClick={() => setShowAdd(true)}>Add Product</Button>
        </div>
      </div>

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600">SKU Code</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Name</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Category</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600">Price</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600">Sale Price</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600">Stock</th>
              <th className="text-center px-4 py-3 font-medium text-gray-600">Status</th>
              <th className="text-center px-4 py-3 font-medium text-gray-600">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {skus.map((sku) => (
              <tr key={sku.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs">{sku.sku_code}</td>
                <td className="px-4 py-3 font-medium">{sku.name}</td>
                <td className="px-4 py-3 text-gray-600">{sku.category}</td>
                <td className="px-4 py-3 text-right">{formatCurrency(sku.original_price)}</td>
                <td className="px-4 py-3 text-right text-green-600">
                  {sku.discounted_price ? formatCurrency(sku.discounted_price) : '—'}
                </td>
                <td className="px-4 py-3 text-right">
                  <span className={sku.stock_quantity < 10 ? 'text-red-600 font-semibold' : ''}>
                    {sku.stock_quantity}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <Badge variant={sku.is_active ? 'success' : 'default'}>
                    {sku.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                </td>
                <td className="px-4 py-3 text-center">
                  <button
                    onClick={() => toggleActive(sku)}
                    className="text-primary-600 hover:underline text-xs"
                  >
                    {sku.is_active ? 'Deactivate' : 'Activate'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {skus.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            No products yet.{' '}
            <Link href="/products/upload" className="text-primary-600 hover:underline">
              Upload your first CSV
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

// Placeholder — add modal will be built in next iteration
function setShowAdd(_: boolean) {}
