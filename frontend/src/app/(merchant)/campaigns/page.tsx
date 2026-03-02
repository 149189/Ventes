'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { formatDate } from '@/lib/utils';
import Button from '@/components/ui/Button';
import StatusBadge from '@/components/shared/StatusBadge';
import type { Campaign } from '@/types/campaign';

export default function CampaignsPage() {
  const router = useRouter();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    fetchCampaigns();
  }, []);

  async function fetchCampaigns() {
    try {
      const res = await api.get('/campaigns/');
      setCampaigns(res.data.results || res.data);
    } catch (err) {
      console.error('Failed to fetch campaigns:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleAction(id: number, action: 'activate' | 'pause') {
    try {
      await api.post(`/campaigns/${id}/${action}/`);
      fetchCampaigns();
    } catch (err) {
      console.error(`Failed to ${action} campaign:`, err);
    }
  }

  const filtered = filter === 'all'
    ? campaigns
    : campaigns.filter((c) => c.status === filter);

  if (loading) return <div className="animate-pulse">Loading campaigns...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Campaigns</h1>
        <Button onClick={() => router.push('/campaigns/new')}>Create Campaign</Button>
      </div>

      <div className="flex gap-2 mb-4">
        {['all', 'draft', 'active', 'paused', 'ended'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium capitalize transition-colors ${
              filter === f
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      <div className="space-y-4">
        {filtered.map((campaign) => (
          <div key={campaign.id} className="card flex items-center justify-between">
            <div>
              <Link
                href={`/campaigns/${campaign.id}`}
                className="text-lg font-semibold text-gray-900 hover:text-primary-600"
              >
                {campaign.name}
              </Link>
              <p className="text-sm text-gray-500 mt-1">
                {campaign.description || 'No description'}
              </p>
              <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                <span>Start: {formatDate(campaign.start_date)}</span>
                {campaign.end_date && <span>End: {formatDate(campaign.end_date)}</span>}
                <span>Msgs today: {campaign.messages_sent_today}/{campaign.daily_message_limit}</span>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <StatusBadge status={campaign.status} />
              {campaign.status === 'draft' && (
                <Button size="sm" onClick={() => handleAction(campaign.id, 'activate')}>Activate</Button>
              )}
              {campaign.status === 'active' && (
                <Button size="sm" variant="secondary" onClick={() => handleAction(campaign.id, 'pause')}>Pause</Button>
              )}
              {campaign.status === 'paused' && (
                <Button size="sm" onClick={() => handleAction(campaign.id, 'activate')}>Resume</Button>
              )}
            </div>
          </div>
        ))}
        {filtered.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            No campaigns found.
          </div>
        )}
      </div>
    </div>
  );
}
