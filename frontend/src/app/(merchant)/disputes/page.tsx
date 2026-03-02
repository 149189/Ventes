'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { formatCurrency, formatDate } from '@/lib/utils';
import StatusBadge from '@/components/shared/StatusBadge';
import Button from '@/components/ui/Button';
import type { DisputeRecord } from '@/types/billing';

export default function DisputesPage() {
  const [disputes, setDisputes] = useState<DisputeRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetch() {
      try {
        const res = await api.get('/billing/disputes/');
        setDisputes(res.data.results || res.data);
      } catch (err) {
        console.error('Failed to fetch disputes:', err);
      } finally {
        setLoading(false);
      }
    }
    fetch();
  }, []);

  if (loading) return <div className="animate-pulse">Loading disputes...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Disputes</h1>
        <p className="text-sm text-gray-500">14-day window to file disputes on conversions</p>
      </div>

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600">ID</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Reason</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600">Credit</th>
              <th className="text-center px-4 py-3 font-medium text-gray-600">Status</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Filed</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Resolved</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {disputes.map((d) => (
              <tr key={d.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs">#{d.id}</td>
                <td className="px-4 py-3">{d.reason.slice(0, 80)}{d.reason.length > 80 ? '...' : ''}</td>
                <td className="px-4 py-3 text-right font-semibold">
                  {d.credit_amount > 0 ? formatCurrency(d.credit_amount) : '—'}
                </td>
                <td className="px-4 py-3 text-center"><StatusBadge status={d.status} /></td>
                <td className="px-4 py-3 text-gray-600">{formatDate(d.filed_at)}</td>
                <td className="px-4 py-3 text-gray-600">
                  {d.resolved_at ? formatDate(d.resolved_at) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {disputes.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            No disputes filed.
          </div>
        )}
      </div>
    </div>
  );
}
