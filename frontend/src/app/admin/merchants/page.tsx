'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import api from '@/lib/api';
import { Card } from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import StatusBadge from '@/components/shared/StatusBadge';
import { formatCurrency, formatDate } from '@/lib/utils';
import type { MerchantProfile, MerchantIndustry } from '@/types/merchant';
import { INDUSTRY_LABELS } from '@/types/merchant';

const INDUSTRY_EMOJI: Record<MerchantIndustry, string> = {
  tech: '💻',
  fashion: '👗',
  home: '🏠',
  health: '💊',
  food: '🍕',
  beauty: '💄',
  sports: '🏋️',
  other: '📦',
};

export default function AdminMerchantsPage() {
  const [merchants, setMerchants] = useState<MerchantProfile[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [industryFilter, setIndustryFilter] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'category' | 'list'>('category');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchMerchants() {
      try {
        const params = statusFilter !== 'all' ? `?status=${statusFilter}` : '';
        const response = await api.get(`/merchants/admin/list/${params}`);
        setMerchants(response.data.results || response.data);
      } catch (error) {
        console.error('Failed to fetch merchants:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchMerchants();
  }, [statusFilter]);

  async function handleAction(merchantId: number, action: 'approve' | 'reject' | 'suspend') {
    try {
      await api.put(`/merchants/admin/${merchantId}/${action}/`);
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

  const grouped = useMemo(() => {
    const groups: Record<string, MerchantProfile[]> = {};
    const filtered = industryFilter === 'all'
      ? merchants
      : merchants.filter((m) => m.industry === industryFilter);

    for (const m of filtered) {
      const key = m.industry || 'other';
      if (!groups[key]) groups[key] = [];
      groups[key].push(m);
    }
    return groups;
  }, [merchants, industryFilter]);

  const industries = useMemo(() => {
    const set = new Set(merchants.map((m) => m.industry || 'other'));
    return Array.from(set).sort();
  }, [merchants]);

  const statusFilters = ['all', 'pending', 'approved', 'suspended', 'rejected'];
  const pendingCount = merchants.filter((m) => m.status === 'pending').length;
  const totalCount = merchants.length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading merchants...</div>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Merchants</h1>
          <p className="text-sm text-gray-500 mt-1">
            {totalCount} total merchants
            {pendingCount > 0 && (
              <span className="text-amber-600 ml-2">({pendingCount} pending approval)</span>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setViewMode('category')}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              viewMode === 'category'
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            By Category
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              viewMode === 'list'
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            List View
          </button>
        </div>
      </div>

      {/* Status Filters */}
      <div className="flex gap-2 mb-4">
        {statusFilters.map((f) => (
          <button
            key={f}
            onClick={() => setStatusFilter(f)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors capitalize ${
              statusFilter === f
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Industry Filters */}
      <div className="flex gap-2 mb-6 flex-wrap">
        <button
          onClick={() => setIndustryFilter('all')}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
            industryFilter === 'all'
              ? 'bg-gray-900 text-white'
              : 'bg-gray-50 text-gray-600 hover:bg-gray-100 border border-gray-200'
          }`}
        >
          All Industries
        </button>
        {industries.map((ind) => (
          <button
            key={ind}
            onClick={() => setIndustryFilter(ind)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              industryFilter === ind
                ? 'bg-gray-900 text-white'
                : 'bg-gray-50 text-gray-600 hover:bg-gray-100 border border-gray-200'
            }`}
          >
            {INDUSTRY_EMOJI[ind as MerchantIndustry] || '📦'}{' '}
            {INDUSTRY_LABELS[ind as MerchantIndustry] || ind}
          </button>
        ))}
      </div>

      {/* Category View */}
      {viewMode === 'category' ? (
        <div className="space-y-8">
          {Object.entries(grouped)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([industry, members]) => (
              <div key={industry}>
                <div className="flex items-center gap-2 mb-4">
                  <span className="text-2xl">{INDUSTRY_EMOJI[industry as MerchantIndustry] || '📦'}</span>
                  <h2 className="text-lg font-semibold text-gray-800">
                    {INDUSTRY_LABELS[industry as MerchantIndustry] || industry}
                  </h2>
                  <span className="text-sm text-gray-400 ml-1">({members.length})</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {members.map((merchant) => (
                    <Card key={merchant.id} className="p-4 hover:shadow-md transition-shadow">
                      <div className="flex items-start justify-between mb-3">
                        <Link
                          href={`/admin/merchants/${merchant.id}`}
                          className="text-base font-semibold text-primary-600 hover:underline"
                        >
                          {merchant.company_name}
                        </Link>
                        <StatusBadge status={merchant.status} />
                      </div>
                      <div className="space-y-1.5 text-sm text-gray-500">
                        <p>{merchant.contact_email}</p>
                        <p>{merchant.contact_phone}</p>
                        <div className="flex items-center gap-3 pt-1">
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700 capitalize">
                            {merchant.tier}
                          </span>
                          <span>{merchant.commission_rate}% commission</span>
                        </div>
                        <p className="text-xs text-gray-400">Joined {formatDate(merchant.created_at)}</p>
                      </div>
                      <div className="flex gap-1 mt-3 pt-3 border-t border-gray-100">
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
                        <Link href={`/admin/merchants/${merchant.id}`}>
                          <Button size="sm" variant="secondary">View</Button>
                        </Link>
                      </div>
                    </Card>
                  ))}
                </div>
              </div>
            ))}
          {Object.keys(grouped).length === 0 && (
            <div className="text-center py-12 text-gray-500">
              No merchants found.
            </div>
          )}
        </div>
      ) : (
        /* List View */
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Company</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Industry</th>
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
                {Object.entries(grouped)
                  .sort(([a], [b]) => a.localeCompare(b))
                  .flatMap(([, members]) => members)
                  .map((merchant) => (
                    <tr key={merchant.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4">
                        <Link href={`/admin/merchants/${merchant.id}`} className="text-primary-600 hover:underline font-medium">
                          {merchant.company_name}
                        </Link>
                      </td>
                      <td className="py-3 px-4">
                        <span className="inline-flex items-center gap-1">
                          {INDUSTRY_EMOJI[merchant.industry] || '📦'}
                          <span className="text-gray-600 text-xs">
                            {INDUSTRY_LABELS[merchant.industry] || merchant.industry}
                          </span>
                        </span>
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
                {Object.keys(grouped).length === 0 && (
                  <tr>
                    <td colSpan={9} className="py-8 text-center text-gray-500">
                      No merchants found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
