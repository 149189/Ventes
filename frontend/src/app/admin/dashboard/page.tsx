'use client';

import { useState, useEffect } from 'react';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import api from '@/lib/api';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { formatCurrency, formatPercent } from '@/lib/utils';
import type { AdminDashboard, TrendDataPoint, FunnelStep, TopMerchant } from '@/types/analytics';

function shortDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export default function AdminDashboardPage() {
  const [data, setData] = useState<AdminDashboard | null>(null);
  const [trends, setTrends] = useState<TrendDataPoint[]>([]);
  const [funnel, setFunnel] = useState<FunnelStep[]>([]);
  const [topMerchants, setTopMerchants] = useState<TopMerchant[]>([]);
  const [period, setPeriod] = useState('7d');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchAll() {
      setLoading(true);
      try {
        const [dashRes, trendRes, funnelRes, topRes] = await Promise.all([
          api.get(`/analytics/admin/dashboard/?period=${period}`),
          api.get(`/analytics/admin/trends/?period=${period}`),
          api.get(`/analytics/admin/funnel/?period=${period}`),
          api.get(`/analytics/admin/top-merchants/?period=${period}`),
        ]);
        setData(dashRes.data);
        setTrends(trendRes.data);
        setFunnel(funnelRes.data.funnel);
        setTopMerchants(topRes.data);
      } catch (error) {
        console.error('Failed to fetch admin dashboard:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchAll();
  }, [period]);

  if (loading) {
    return <div className="animate-pulse">Loading dashboard...</div>;
  }

  if (!data) {
    return <div>Failed to load dashboard data.</div>;
  }

  const stats = [
    { label: 'Total Conversations', value: data.total_conversations, color: 'text-blue-600' },
    { label: 'Total Clicks', value: data.total_clicks, color: 'text-green-600' },
    { label: 'Flagged Clicks', value: data.flagged_clicks, color: 'text-red-600' },
    { label: 'Conversions', value: data.total_conversions, color: 'text-purple-600' },
    { label: 'Revenue', value: formatCurrency(data.total_revenue), color: 'text-green-600' },
    { label: 'Conversion Rate', value: formatPercent(data.conversion_rate), color: 'text-blue-600' },
    { label: 'Active Merchants', value: data.active_merchants, color: 'text-gray-900' },
  ];

  const funnelMax = Math.max(...funnel.map((f) => f.count), 1);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
        <div className="flex gap-2">
          {['today', '7d', '30d'].map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                period === p
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {p === 'today' ? 'Today' : p === '7d' ? '7 Days' : '30 Days'}
            </button>
          ))}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <p className="text-sm text-gray-500">{stat.label}</p>
            <p className={`text-2xl font-bold mt-1 ${stat.color}`}>{stat.value}</p>
          </Card>
        ))}
      </div>

      {/* Charts Row 1: Revenue + Clicks/Conversions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <Card>
          <CardHeader><CardTitle>Revenue Trend</CardTitle></CardHeader>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={trends}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tickFormatter={shortDate} fontSize={12} />
              <YAxis fontSize={12} />
              <Tooltip
                labelFormatter={shortDate}
                formatter={(v: number) => [formatCurrency(v), 'Revenue']}
              />
              <Area
                type="monotone"
                dataKey="revenue"
                stroke="#16a34a"
                fill="#bbf7d0"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        <Card>
          <CardHeader><CardTitle>Clicks & Conversions</CardTitle></CardHeader>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={trends}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tickFormatter={shortDate} fontSize={12} />
              <YAxis fontSize={12} />
              <Tooltip labelFormatter={shortDate} />
              <Legend />
              <Bar dataKey="clicks" fill="#3b82f6" name="Clicks" radius={[4, 4, 0, 0]} />
              <Bar dataKey="conversions" fill="#8b5cf6" name="Conversions" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Charts Row 2: Fraud + Funnel */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <Card>
          <CardHeader><CardTitle>Fraud Detection</CardTitle></CardHeader>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={trends}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tickFormatter={shortDate} fontSize={12} />
              <YAxis fontSize={12} />
              <Tooltip labelFormatter={shortDate} />
              <Legend />
              <Area
                type="monotone"
                dataKey="clicks"
                stroke="#3b82f6"
                fill="#dbeafe"
                strokeWidth={2}
                name="Total Clicks"
              />
              <Area
                type="monotone"
                dataKey="fraudulent"
                stroke="#ef4444"
                fill="#fecaca"
                strokeWidth={2}
                name="Fraudulent"
              />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        <Card>
          <CardHeader><CardTitle>Conversion Funnel</CardTitle></CardHeader>
          <div className="space-y-4 pt-2">
            {funnel.map((step, i) => {
              const pct = funnelMax > 0 ? (step.count / funnelMax) * 100 : 0;
              const colors = ['bg-blue-500', 'bg-green-500', 'bg-purple-500'];
              return (
                <div key={step.stage}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium text-gray-700">{step.stage}</span>
                    <span className="text-gray-500">
                      {step.count.toLocaleString()}
                      {i > 0 && funnel[i - 1].count > 0 && (
                        <span className="ml-1 text-xs text-gray-400">
                          ({formatPercent((step.count / funnel[i - 1].count) * 100)})
                        </span>
                      )}
                    </span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-6">
                    <div
                      className={`h-6 rounded-full ${colors[i]} transition-all`}
                      style={{ width: `${Math.max(pct, 2)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      {/* Top Merchants */}
      {topMerchants.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Top Merchants by Revenue</CardTitle></CardHeader>
          <ResponsiveContainer width="100%" height={Math.max(topMerchants.length * 40, 200)}>
            <BarChart data={topMerchants} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" fontSize={12} />
              <YAxis
                type="category"
                dataKey="merchant"
                width={150}
                fontSize={12}
                tick={{ fill: '#374151' }}
              />
              <Tooltip formatter={(v: number) => [formatCurrency(v), 'Revenue']} />
              <Bar dataKey="revenue" fill="#16a34a" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}
    </div>
  );
}
