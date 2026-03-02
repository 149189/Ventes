'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import StatusBadge from '@/components/shared/StatusBadge';
import { formatDate } from '@/lib/utils';

interface ClickEvent {
  id: number;
  token: string;
  sku_name: string;
  merchant_name: string;
  campaign_name: string | null;
  ip_address: string;
  user_agent: string;
  referer: string;
  country_code: string;
  destination_url: string;
  is_fraudulent: boolean;
  fraud_score: number;
  fraud_reasons: { type: string; details: Record<string, unknown> }[];
  fraud_flags: string[];
  clicked_at: string;
}

interface FraudFlag {
  id: number;
  click_event: number;
  click_event_id: number;
  flag_type: 'rate_limit' | 'token_reuse' | 'ip_cluster' | 'bot_ua' | 'low_dwell';
  details: Record<string, unknown>;
  reviewed: boolean;
  reviewed_by: number | null;
  reviewed_at: string | null;
  created_at: string;
}

const FLAG_LABELS: Record<string, string> = {
  rate_limit: 'Rate Limit',
  token_reuse: 'Token Reuse',
  ip_cluster: 'IP Cluster',
  bot_ua: 'Bot UA',
  low_dwell: 'Low Dwell',
};

export default function AdminClicksPage() {
  const [clicks, setClicks] = useState<ClickEvent[]>([]);
  const [flags, setFlags] = useState<FraudFlag[]>([]);
  const [tab, setTab] = useState<'clicks' | 'flags'>('clicks');
  const [fraudOnly, setFraudOnly] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [clicksRes, flagsRes] = await Promise.all([
          api.get(`/tracking/clicks/${fraudOnly ? '?fraud_only=true' : ''}`),
          api.get('/tracking/fraud-flags/'),
        ]);
        setClicks(clicksRes.data.results || clicksRes.data);
        setFlags(flagsRes.data.results || flagsRes.data);
      } catch (error) {
        console.error('Failed to fetch click data:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [fraudOnly]);

  async function handleReviewFlag(flagId: number, verdict: 'legitimate' | 'fraudulent') {
    try {
      await api.post(`/tracking/fraud-flags/${flagId}/review/`, { verdict });
      setFlags((prev) =>
        prev.map((f) => (f.id === flagId ? { ...f, reviewed: true } : f)),
      );
    } catch (error) {
      console.error('Failed to review flag:', error);
    }
  }

  if (loading) {
    return <div className="animate-pulse p-6">Loading click data...</div>;
  }

  const unreviewedCount = flags.filter((f) => !f.reviewed).length;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Clicks & Fraud Detection</h1>
          <p className="text-sm text-gray-500 mt-1">
            {clicks.length} total clicks
            {unreviewedCount > 0 && (
              <span className="text-red-600 ml-2">{unreviewedCount} unreviewed fraud flags</span>
            )}
          </p>
        </div>
      </div>

      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setTab('clicks')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            tab === 'clicks' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Click Log
        </button>
        <button
          onClick={() => setTab('flags')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            tab === 'flags' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Fraud Flags {unreviewedCount > 0 && `(${unreviewedCount})`}
        </button>
      </div>

      {tab === 'clicks' && (
        <Card>
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
            <CardTitle>Click Events</CardTitle>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={fraudOnly}
                onChange={(e) => setFraudOnly(e.target.checked)}
                className="rounded border-gray-300"
              />
              Flagged only
            </label>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Token</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Merchant</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Campaign</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">IP</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Fraud Score</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Flags</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Status</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Time</th>
                </tr>
              </thead>
              <tbody>
                {clicks.map((click) => (
                  <tr key={click.id} className={`border-b border-gray-100 ${click.is_fraudulent ? 'bg-red-50' : 'hover:bg-gray-50'}`}>
                    <td className="py-3 px-4 font-mono text-xs">{click.token.substring(0, 8)}...</td>
                    <td className="py-3 px-4">{click.merchant_name}</td>
                    <td className="py-3 px-4 text-gray-600">{click.campaign_name || '\u2014'}</td>
                    <td className="py-3 px-4 font-mono text-xs">{click.ip_address}</td>
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
                      <div className="flex flex-wrap gap-1">
                        {click.fraud_flags.map((flag) => (
                          <span key={flag} className="inline-block px-1.5 py-0.5 rounded bg-red-100 text-red-700 text-xs">
                            {FLAG_LABELS[flag] || flag}
                          </span>
                        ))}
                        {click.fraud_flags.length === 0 && <span className="text-gray-400 text-xs">Clean</span>}
                      </div>
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
                    <td colSpan={8} className="py-8 text-center text-gray-500">No click events found.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {tab === 'flags' && (
        <Card>
          <CardHeader>
            <CardTitle>Fraud Flags</CardTitle>
          </CardHeader>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Click ID</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Flag Type</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Details</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Status</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Time</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Actions</th>
                </tr>
              </thead>
              <tbody>
                {flags.map((flag) => (
                  <tr key={flag.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4 font-mono text-xs">#{flag.click_event_id}</td>
                    <td className="py-3 px-4">
                      <span className="inline-block px-2 py-1 rounded bg-red-100 text-red-700 text-xs font-medium">
                        {FLAG_LABELS[flag.flag_type] || flag.flag_type.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-600 max-w-xs truncate font-mono text-xs">
                      {JSON.stringify(flag.details)}
                    </td>
                    <td className="py-3 px-4">
                      {flag.reviewed ? (
                        <span className="text-green-600 text-xs font-medium">Reviewed</span>
                      ) : (
                        <span className="text-amber-600 text-xs font-medium">Pending</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-gray-500 whitespace-nowrap">{formatDate(flag.created_at)}</td>
                    <td className="py-3 px-4">
                      {!flag.reviewed && (
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleReviewFlag(flag.id, 'legitimate')}
                            className="text-xs text-green-600 hover:text-green-800 font-medium px-2 py-1 rounded hover:bg-green-50"
                          >
                            Legit
                          </button>
                          <button
                            onClick={() => handleReviewFlag(flag.id, 'fraudulent')}
                            className="text-xs text-red-600 hover:text-red-800 font-medium px-2 py-1 rounded hover:bg-red-50"
                          >
                            Fraud
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
                {flags.length === 0 && (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-gray-500">No fraud flags found.</td>
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
