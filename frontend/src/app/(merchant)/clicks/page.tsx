'use client';

import { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import api from '@/lib/api';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import StatusBadge from '@/components/shared/StatusBadge';
import { formatDate } from '@/lib/utils';

interface ClickEvent {
  id: number;
  token: string;
  sku_name: string;
  campaign_name: string | null;
  destination_url: string;
  is_fraudulent: boolean;
  fraud_score: number;
  clicked_at: string;
  ip_address: string;
  merchant_name: string;
  fraud_flags: string[];
}

interface ClickSummary {
  total_clicks: number;
  today_clicks: number;
  valid_clicks: number;
  fraudulent_clicks: number;
  fraud_rate: number;
  weekly_breakdown: { day: string; total: number; fraud: number }[];
  top_skus: { name: string; clicks: number }[];
}

function shortDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export default function MerchantClicksPage() {
  const [clicks, setClicks] = useState<ClickEvent[]>([]);
  const [summary, setSummary] = useState<ClickSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [clicksRes, summaryRes] = await Promise.all([
          api.get('/tracking/merchant/clicks/'),
          api.get('/tracking/merchant/clicks/summary/'),
        ]);
        setClicks(clicksRes.data.results || clicksRes.data);
        setSummary(summaryRes.data);
      } catch (error) {
        console.error('Failed to fetch click data:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) {
    return <div className="animate-pulse p-6">Loading click data...</div>;
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Click Tracking</h1>
        <p className="text-sm text-gray-500 mt-1">
          Monitor product link clicks from your WhatsApp campaigns
        </p>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <Card>
            <p className="text-sm text-gray-500">Total Clicks</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{summary.total_clicks}</p>
          </Card>
          <Card>
            <p className="text-sm text-gray-500">Today</p>
            <p className="text-2xl font-bold text-blue-600 mt-1">{summary.today_clicks}</p>
          </Card>
          <Card>
            <p className="text-sm text-gray-500">Valid Clicks</p>
            <p className="text-2xl font-bold text-green-600 mt-1">{summary.valid_clicks}</p>
          </Card>
          <Card>
            <p className="text-sm text-gray-500">Fraud Rate</p>
            <p className={`text-2xl font-bold mt-1 ${summary.fraud_rate > 10 ? 'text-red-600' : 'text-green-600'}`}>
              {summary.fraud_rate}%
            </p>
          </Card>
        </div>
      )}

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {summary && summary.weekly_breakdown.length > 0 && (
          <Card>
            <CardHeader><CardTitle>Weekly Click Activity</CardTitle></CardHeader>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={summary.weekly_breakdown}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" tickFormatter={shortDate} fontSize={12} />
                <YAxis fontSize={12} />
                <Tooltip labelFormatter={shortDate} />
                <Legend />
                <Bar dataKey="total" fill="#3b82f6" name="Total" radius={[4, 4, 0, 0]} />
                <Bar dataKey="fraud" fill="#ef4444" name="Fraudulent" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        )}

        {summary && summary.top_skus.length > 0 && (
          <Card>
            <CardHeader><CardTitle>Top Products by Clicks</CardTitle></CardHeader>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={summary.top_skus} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" fontSize={12} />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={120}
                  fontSize={12}
                  tick={{ fill: '#374151' }}
                />
                <Tooltip />
                <Bar dataKey="clicks" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        )}
      </div>

      {/* Click Log Table */}
      <Card>
        <div className="px-4 py-3 border-b border-gray-200">
          <CardTitle>Recent Clicks</CardTitle>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 font-medium text-gray-500">Token</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Product</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Campaign</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Fraud Score</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Status</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Time</th>
              </tr>
            </thead>
            <tbody>
              {clicks.map((click) => (
                <tr key={click.id} className={`border-b border-gray-100 ${click.is_fraudulent ? 'bg-red-50' : 'hover:bg-gray-50'}`}>
                  <td className="py-3 px-4 font-mono text-xs">{click.token.substring(0, 8)}...</td>
                  <td className="py-3 px-4">{click.sku_name}</td>
                  <td className="py-3 px-4 text-gray-600">{click.campaign_name || '\u2014'}</td>
                  <td className="py-3 px-4">
                    <span className={`font-medium ${
                      click.fraud_score >= 0.7 ? 'text-red-600' :
                      click.fraud_score >= 0.4 ? 'text-amber-600' :
                      'text-green-600'
                    }`}>
                      {(click.fraud_score * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    {click.is_fraudulent ? (
                      <StatusBadge status="rejected" />
                    ) : (
                      <StatusBadge status="approved" />
                    )}
                  </td>
                  <td className="py-3 px-4 text-gray-500 whitespace-nowrap">{formatDate(click.clicked_at)}</td>
                </tr>
              ))}
              {clicks.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-gray-500">
                    No clicks recorded yet. Clicks will appear here once customers interact with your product links.
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
