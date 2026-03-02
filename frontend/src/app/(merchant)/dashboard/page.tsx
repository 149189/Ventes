'use client';

import { useState, useEffect } from 'react';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import api from '@/lib/api';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { formatCurrency, formatPercent } from '@/lib/utils';
import type { MerchantDashboard, TrendDataPoint } from '@/types/analytics';

function shortDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export default function MerchantDashboardPage() {
  const [data, setData] = useState<MerchantDashboard | null>(null);
  const [trends, setTrends] = useState<TrendDataPoint[]>([]);
  const [period, setPeriod] = useState('7d');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchDashboard() {
      try {
        const [dashRes, trendRes] = await Promise.all([
          api.get('/analytics/merchant/dashboard/'),
          api.get(`/analytics/merchant/trends/?period=${period}`),
        ]);
        setData(dashRes.data);
        setTrends(trendRes.data);
      } catch (error) {
        console.error('Failed to fetch dashboard:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchDashboard();
    const interval = setInterval(fetchDashboard, 30000);
    return () => clearInterval(interval);
  }, [period]);

  if (loading) {
    return <div className="animate-pulse">Loading dashboard...</div>;
  }

  if (!data) {
    return <div>Failed to load dashboard data.</div>;
  }

  const stats = [
    { label: 'Conversations Today', value: data.conversations_today },
    { label: 'Clicks Today', value: data.clicks_today },
    { label: 'Conversions Today', value: data.conversions_today },
    { label: 'Click-Through Rate', value: formatPercent(data.ctr) },
    { label: 'Spent Today', value: formatCurrency(data.spend_today) },
    { label: 'Budget Remaining', value: formatCurrency(data.budget_remaining) },
  ];

  const budgetPercent = data.daily_budget_cap > 0
    ? (data.spend_today / data.daily_budget_cap) * 100
    : 0;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <div className="flex gap-2">
          {['7d', '14d', '30d'].map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                period === p
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {p === '7d' ? '7 Days' : p === '14d' ? '14 Days' : '30 Days'}
            </button>
          ))}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <p className="text-sm text-gray-500">{stat.label}</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{stat.value}</p>
          </Card>
        ))}
      </div>

      {/* Budget Bar */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Budget Usage</CardTitle>
        </CardHeader>
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">
              {formatCurrency(data.spend_today)} of {formatCurrency(data.daily_budget_cap)}
            </span>
            <span className="font-medium">{formatPercent(budgetPercent)}</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className={`h-3 rounded-full transition-all ${
                budgetPercent > 80 ? 'bg-red-500' : budgetPercent > 50 ? 'bg-yellow-500' : 'bg-green-500'
              }`}
              style={{ width: `${Math.min(budgetPercent, 100)}%` }}
            />
          </div>
        </div>
      </Card>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <Card>
          <CardHeader><CardTitle>Spending Trend</CardTitle></CardHeader>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={trends}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tickFormatter={shortDate} fontSize={12} />
              <YAxis fontSize={12} />
              <Tooltip
                labelFormatter={shortDate}
                formatter={(v: number) => [formatCurrency(v), 'Spend']}
              />
              <Area
                type="monotone"
                dataKey="spend"
                stroke="#f59e0b"
                fill="#fef3c7"
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

      {/* Conversations Chart */}
      <Card>
        <CardHeader><CardTitle>Conversations Started</CardTitle></CardHeader>
        <ResponsiveContainer width="100%" height={250}>
          <AreaChart data={trends}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tickFormatter={shortDate} fontSize={12} />
            <YAxis fontSize={12} />
            <Tooltip labelFormatter={shortDate} />
            <Area
              type="monotone"
              dataKey="conversations"
              stroke="#3b82f6"
              fill="#dbeafe"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </Card>
    </div>
  );
}
