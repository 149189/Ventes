'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import StatusBadge from '@/components/shared/StatusBadge';
import { formatCurrency, formatDate } from '@/lib/utils';
import type { Invoice, DisputeRecord } from '@/types/billing';

interface AdminInvoice extends Invoice {
  merchant_name: string;
}

interface AdminDispute extends DisputeRecord {
  merchant_name: string;
}

export default function AdminBillingPage() {
  const [invoices, setInvoices] = useState<AdminInvoice[]>([]);
  const [disputes, setDisputes] = useState<AdminDispute[]>([]);
  const [tab, setTab] = useState<'invoices' | 'disputes' | 'revenue'>('revenue');
  const [revenueStats, setRevenueStats] = useState<{
    total_revenue: number;
    total_invoices: number;
    paid_invoices: number;
    overdue_invoices: number;
    total_disputes: number;
    open_disputes: number;
    total_credits: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [invoiceRes, disputeRes, statsRes] = await Promise.all([
          api.get('/billing/invoices/'),
          api.get('/billing/disputes/'),
          api.get('/billing/revenue-stats/'),
        ]);
        setInvoices(invoiceRes.data.results || invoiceRes.data);
        setDisputes(disputeRes.data.results || disputeRes.data);
        setRevenueStats(statsRes.data);
      } catch (error) {
        console.error('Failed to fetch billing data:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  async function handleDisputeAction(disputeId: number, action: 'upheld' | 'rejected') {
    try {
      await api.post(`/billing/disputes/${disputeId}/resolve/`, { status: action });
      setDisputes((prev) =>
        prev.map((d) => (d.id === disputeId ? { ...d, status: action } : d)),
      );
    } catch (error) {
      console.error(`Failed to ${action} dispute:`, error);
    }
  }

  if (loading) {
    return <div className="animate-pulse">Loading billing data...</div>;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Billing & Revenue</h1>

      <div className="flex gap-2 mb-6">
        {(['revenue', 'invoices', 'disputes'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors capitalize ${
              tab === t ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'revenue' && revenueStats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <p className="text-sm text-gray-500">Total Revenue</p>
            <p className="text-2xl font-bold text-green-600 mt-1">{formatCurrency(revenueStats.total_revenue)}</p>
          </Card>
          <Card>
            <p className="text-sm text-gray-500">Invoices</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{revenueStats.total_invoices}</p>
            <p className="text-xs text-gray-500 mt-1">
              {revenueStats.paid_invoices} paid, {revenueStats.overdue_invoices} overdue
            </p>
          </Card>
          <Card>
            <p className="text-sm text-gray-500">Disputes</p>
            <p className="text-2xl font-bold text-amber-600 mt-1">{revenueStats.total_disputes}</p>
            <p className="text-xs text-gray-500 mt-1">{revenueStats.open_disputes} open</p>
          </Card>
          <Card>
            <p className="text-sm text-gray-500">Credits Issued</p>
            <p className="text-2xl font-bold text-red-600 mt-1">{formatCurrency(revenueStats.total_credits)}</p>
          </Card>
        </div>
      )}

      {tab === 'invoices' && (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Invoice #</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Merchant</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Period</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Clicks</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Conversions</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Total</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Status</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Due</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((inv) => (
                  <tr key={inv.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4 font-mono text-xs">{inv.invoice_number}</td>
                    <td className="py-3 px-4">{inv.merchant_name}</td>
                    <td className="py-3 px-4 text-gray-500 text-xs">
                      {formatDate(inv.period_start)} - {formatDate(inv.period_end)}
                    </td>
                    <td className="py-3 px-4">{inv.total_clicks}</td>
                    <td className="py-3 px-4">{inv.total_conversions}</td>
                    <td className="py-3 px-4 font-medium">{formatCurrency(inv.total)}</td>
                    <td className="py-3 px-4">
                      <StatusBadge status={inv.status} />
                    </td>
                    <td className="py-3 px-4 text-gray-500">{formatDate(inv.due_date)}</td>
                  </tr>
                ))}
                {invoices.length === 0 && (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-gray-500">No invoices found.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {tab === 'disputes' && (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-medium text-gray-500">ID</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Merchant</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Reason</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Credit Amount</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Status</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Filed</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Actions</th>
                </tr>
              </thead>
              <tbody>
                {disputes.map((dispute) => (
                  <tr key={dispute.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4 font-mono text-xs">#{dispute.id}</td>
                    <td className="py-3 px-4">{dispute.merchant_name}</td>
                    <td className="py-3 px-4 text-gray-600 max-w-xs truncate">{dispute.reason}</td>
                    <td className="py-3 px-4">{formatCurrency(dispute.credit_amount)}</td>
                    <td className="py-3 px-4">
                      <StatusBadge status={dispute.status} />
                    </td>
                    <td className="py-3 px-4 text-gray-500">{formatDate(dispute.filed_at)}</td>
                    <td className="py-3 px-4">
                      {(dispute.status === 'open' || dispute.status === 'under_review') && (
                        <div className="flex gap-1">
                          <button
                            onClick={() => handleDisputeAction(dispute.id, 'upheld')}
                            className="text-xs text-green-600 hover:text-green-800 font-medium"
                          >
                            Uphold
                          </button>
                          <span className="text-gray-300">|</span>
                          <button
                            onClick={() => handleDisputeAction(dispute.id, 'rejected')}
                            className="text-xs text-red-600 hover:text-red-800 font-medium"
                          >
                            Reject
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
                {disputes.length === 0 && (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-gray-500">No disputes found.</td>
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
