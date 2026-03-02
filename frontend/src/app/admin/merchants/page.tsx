'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import api from '@/lib/api';
import { Card } from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import StatusBadge from '@/components/shared/StatusBadge';
import { formatCurrency, formatDate } from '@/lib/utils';
import type { MerchantProfile } from '@/types/merchant';

export default function AdminMerchantsPage() {
  const [merchants, setMerchants] = useState<MerchantProfile[]>([]);
  const [filter, setFilter] = useState<string>('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchMerchants() {
      try {
        const params = filter !== 'all' ? `?status=${filter}` : '';
        const response = await api.get(`/merchants/admin/merchants/${params}`);
        setMerchants(response.data.results || response.data);
      } catch (error) {
        console.error('Failed to fetch merchants:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchMerchants();
  }, [filter]);

  async function handleAction(merchantId: number, action: 'approve' | 'reject' | 'suspend') {
    try {
      await api.post(`/merchants/admin/merchants/${merchantId}/action/`, { action });
      setMerchants((prev) =>
        prev.map((m) =>
          m.id === merchantId
            ? { ...m, status: action === 'approve' ? 'approved' : action === 'reject' ? 'rejected' : 'suspended' }
            : m,
        ),
      );
    } catch (error) {
      console.error(`Failed to ${action} merchant:`, error);
    }
  }

  const filters = ['all', 'pending', 'approved', 'suspended', 'rejected'];
  const pendingCount = merchants.filter((m) => m.status === 'pending').length;

  if (loading) {
    return <div className="animate-pulse">Loading merchants...</div>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Merchants</h1>
          {pendingCount > 0 && (
            <p className="text-sm text-amber-600 mt-1">{pendingCount} pending approval</p>
          )}
        </div>
      </div>

      <div className="flex gap-2 mb-6">
        {filters.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors capitalize ${
              filter === f
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 font-medium text-gray-500">Company</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Contact</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Tier</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Commission</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Budget</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Status</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Joined</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody>
              {merchants.map((merchant) => (
                <tr key={merchant.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-3 px-4">
                    <Link href={`/admin/merchants/${merchant.id}`} className="text-primary-600 hover:underline font-medium">
                      {merchant.company_name}
                    </Link>
                  </td>
                  <td className="py-3 px-4 text-gray-600">{merchant.contact_email}</td>
                  <td className="py-3 px-4 capitalize">{merchant.tier}</td>
                  <td className="py-3 px-4">{merchant.commission_rate}%</td>
                  <td className="py-3 px-4">{formatCurrency(merchant.daily_budget_cap)}/day</td>
                  <td className="py-3 px-4">
                    <StatusBadge status={merchant.status} />
                  </td>
                  <td className="py-3 px-4 text-gray-500">{formatDate(merchant.created_at)}</td>
                  <td className="py-3 px-4">
                    <div className="flex gap-1">
                      {merchant.status === 'pending' && (
                        <>
                          <Button size="sm" onClick={() => handleAction(merchant.id, 'approve')}>
                            Approve
                          </Button>
                          <Button size="sm" variant="secondary" onClick={() => handleAction(merchant.id, 'reject')}>
                            Reject
                          </Button>
                        </>
                      )}
                      {merchant.status === 'approved' && (
                        <Button size="sm" variant="secondary" onClick={() => handleAction(merchant.id, 'suspend')}>
                          Suspend
                        </Button>
                      )}
                      {merchant.status === 'suspended' && (
                        <Button size="sm" onClick={() => handleAction(merchant.id, 'approve')}>
                          Reactivate
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {merchants.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-gray-500">
                    No merchants found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
