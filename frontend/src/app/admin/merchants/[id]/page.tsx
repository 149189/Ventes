'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import api from '@/lib/api';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import StatusBadge from '@/components/shared/StatusBadge';
import { formatCurrency, formatDate, formatPercent } from '@/lib/utils';
import type { MerchantProfile, SKU } from '@/types/merchant';

export default function AdminMerchantDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [merchant, setMerchant] = useState<MerchantProfile | null>(null);
  const [skus, setSkus] = useState<SKU[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [merchantRes, skuRes] = await Promise.all([
          api.get(`/merchants/admin/merchants/${params.id}/`),
          api.get(`/merchants/admin/merchants/${params.id}/skus/`),
        ]);
        setMerchant(merchantRes.data);
        setSkus(skuRes.data.results || skuRes.data);
      } catch (error) {
        console.error('Failed to fetch merchant detail:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [params.id]);

  async function handleAction(action: 'approve' | 'reject' | 'suspend') {
    if (!merchant) return;
    try {
      await api.post(`/merchants/admin/merchants/${merchant.id}/action/`, { action });
      setMerchant({
        ...merchant,
        status: action === 'approve' ? 'approved' : action === 'reject' ? 'rejected' : 'suspended',
      });
    } catch (error) {
      console.error(`Failed to ${action} merchant:`, error);
    }
  }

  if (loading) {
    return <div className="animate-pulse">Loading merchant details...</div>;
  }

  if (!merchant) {
    return <div className="text-gray-500">Merchant not found.</div>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <button onClick={() => router.back()} className="text-sm text-gray-500 hover:text-gray-700 mb-2 block">
            &larr; Back to Merchants
          </button>
          <h1 className="text-2xl font-bold text-gray-900">{merchant.company_name}</h1>
        </div>
        <div className="flex gap-2">
          {merchant.status === 'pending' && (
            <>
              <Button onClick={() => handleAction('approve')}>Approve</Button>
              <Button variant="secondary" onClick={() => handleAction('reject')}>Reject</Button>
            </>
          )}
          {merchant.status === 'approved' && (
            <Button variant="secondary" onClick={() => handleAction('suspend')}>Suspend</Button>
          )}
          {merchant.status === 'suspended' && (
            <Button onClick={() => handleAction('approve')}>Reactivate</Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <Card>
          <CardHeader>
            <CardTitle>Company Info</CardTitle>
          </CardHeader>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-500">Status</dt>
              <dd><StatusBadge status={merchant.status} /></dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Tier</dt>
              <dd className="capitalize font-medium">{merchant.tier}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Website</dt>
              <dd className="text-primary-600 truncate max-w-[180px]">{merchant.company_website || '—'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Joined</dt>
              <dd>{formatDate(merchant.created_at)}</dd>
            </div>
            {merchant.approved_at && (
              <div className="flex justify-between">
                <dt className="text-gray-500">Approved</dt>
                <dd>{formatDate(merchant.approved_at)}</dd>
              </div>
            )}
          </dl>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Contact</CardTitle>
          </CardHeader>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-500">Email</dt>
              <dd>{merchant.contact_email}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Phone</dt>
              <dd>{merchant.contact_phone || '—'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">WhatsApp</dt>
              <dd>{merchant.whatsapp_number || '—'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Tax ID</dt>
              <dd>{merchant.tax_id || '—'}</dd>
            </div>
          </dl>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Billing Config</CardTitle>
          </CardHeader>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-500">Model</dt>
              <dd className="uppercase font-medium">{merchant.billing_model}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Commission</dt>
              <dd>{formatPercent(merchant.commission_rate / 100)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Auto-Optimize</dt>
              <dd>{merchant.auto_optimize_commission ? 'Yes' : 'No'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Daily Budget</dt>
              <dd>{formatCurrency(merchant.daily_budget_cap)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Dispute Window</dt>
              <dd>{merchant.dispute_window_days} days</dd>
            </div>
          </dl>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Products ({skus.length})</CardTitle>
        </CardHeader>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 font-medium text-gray-500">SKU Code</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Name</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Category</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Price</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Stock</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Active</th>
              </tr>
            </thead>
            <tbody>
              {skus.map((sku) => (
                <tr key={sku.id} className="border-b border-gray-100">
                  <td className="py-3 px-4 font-mono text-xs">{sku.sku_code}</td>
                  <td className="py-3 px-4">{sku.name}</td>
                  <td className="py-3 px-4 text-gray-500">{sku.category}</td>
                  <td className="py-3 px-4">
                    {sku.discounted_price ? (
                      <span>
                        <span className="line-through text-gray-400 mr-1">{formatCurrency(sku.original_price)}</span>
                        {formatCurrency(sku.discounted_price)}
                      </span>
                    ) : (
                      formatCurrency(sku.original_price)
                    )}
                  </td>
                  <td className="py-3 px-4">{sku.stock_quantity}</td>
                  <td className="py-3 px-4">
                    <StatusBadge status={sku.is_active ? 'active' : 'paused'} />
                  </td>
                </tr>
              ))}
              {skus.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-gray-500">No products yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
