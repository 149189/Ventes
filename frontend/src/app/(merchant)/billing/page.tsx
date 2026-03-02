'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { formatCurrency, formatDate } from '@/lib/utils';
import StatusBadge from '@/components/shared/StatusBadge';
import type { Invoice } from '@/types/billing';

export default function BillingPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetch() {
      try {
        const res = await api.get('/billing/invoices/');
        setInvoices(res.data.results || res.data);
      } catch (err) {
        console.error('Failed to fetch invoices:', err);
      } finally {
        setLoading(false);
      }
    }
    fetch();
  }, []);

  if (loading) return <div className="animate-pulse">Loading invoices...</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Billing</h1>

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Invoice #</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Period</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600">Clicks</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600">Conversions</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600">Total</th>
              <th className="text-center px-4 py-3 font-medium text-gray-600">Status</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Due Date</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {invoices.map((inv) => (
              <tr key={inv.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs font-medium">{inv.invoice_number}</td>
                <td className="px-4 py-3 text-gray-600">
                  {formatDate(inv.period_start)} — {formatDate(inv.period_end)}
                </td>
                <td className="px-4 py-3 text-right">{inv.total_clicks}</td>
                <td className="px-4 py-3 text-right">{inv.total_conversions}</td>
                <td className="px-4 py-3 text-right font-semibold">{formatCurrency(inv.total)}</td>
                <td className="px-4 py-3 text-center"><StatusBadge status={inv.status} /></td>
                <td className="px-4 py-3 text-gray-600">{formatDate(inv.due_date)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {invoices.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            No invoices yet. Invoices are generated weekly.
          </div>
        )}
      </div>
    </div>
  );
}
