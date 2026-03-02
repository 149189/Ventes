'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import StatusBadge from '@/components/shared/StatusBadge';
import { formatDate } from '@/lib/utils';
import type { Campaign, CampaignCreative } from '@/types/campaign';

interface AdminCampaign extends Campaign {
  merchant_name: string;
}

export default function AdminCampaignsPage() {
  const [campaigns, setCampaigns] = useState<AdminCampaign[]>([]);
  const [creatives, setCreatives] = useState<CampaignCreative[]>([]);
  const [tab, setTab] = useState<'campaigns' | 'creatives'>('campaigns');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [campRes, creativeRes] = await Promise.all([
          api.get('/campaigns/admin/campaigns/'),
          api.get('/campaigns/admin/creatives/?pending=true'),
        ]);
        setCampaigns(campRes.data.results || campRes.data);
        setCreatives(creativeRes.data.results || creativeRes.data);
      } catch (error) {
        console.error('Failed to fetch campaign data:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  async function handleCreativeAction(creativeId: number, action: 'approve' | 'reject') {
    try {
      await api.post(`/campaigns/admin/creatives/${creativeId}/${action}/`);
      setCreatives((prev) =>
        prev.map((c) =>
          c.id === creativeId ? { ...c, is_approved: action === 'approve' } : c,
        ),
      );
    } catch (error) {
      console.error(`Failed to ${action} creative:`, error);
    }
  }

  if (loading) {
    return <div className="animate-pulse">Loading campaigns...</div>;
  }

  const pendingCreatives = creatives.filter((c) => !c.is_approved);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Campaigns</h1>
          {pendingCreatives.length > 0 && (
            <p className="text-sm text-amber-600 mt-1">{pendingCreatives.length} creatives pending approval</p>
          )}
        </div>
      </div>

      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setTab('campaigns')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            tab === 'campaigns' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          All Campaigns
        </button>
        <button
          onClick={() => setTab('creatives')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            tab === 'creatives' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Creative Approval {pendingCreatives.length > 0 && `(${pendingCreatives.length})`}
        </button>
      </div>

      {tab === 'campaigns' && (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Name</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Merchant</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Status</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Daily Limit</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Sent Today</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Start Date</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">End Date</th>
                </tr>
              </thead>
              <tbody>
                {campaigns.map((campaign) => (
                  <tr key={campaign.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4 font-medium">{campaign.name}</td>
                    <td className="py-3 px-4 text-gray-600">{campaign.merchant_name}</td>
                    <td className="py-3 px-4">
                      <StatusBadge status={campaign.status} />
                    </td>
                    <td className="py-3 px-4">{campaign.daily_message_limit}</td>
                    <td className="py-3 px-4">
                      <span className={campaign.messages_sent_today >= campaign.daily_message_limit ? 'text-red-600 font-medium' : ''}>
                        {campaign.messages_sent_today}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-500">{formatDate(campaign.start_date)}</td>
                    <td className="py-3 px-4 text-gray-500">{campaign.end_date ? formatDate(campaign.end_date) : '—'}</td>
                  </tr>
                ))}
                {campaigns.length === 0 && (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-gray-500">No campaigns found.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {tab === 'creatives' && (
        <div className="space-y-4">
          {creatives.map((creative) => (
            <Card key={creative.id}>
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="font-medium text-gray-900">{creative.name}</h3>
                  <p className="text-xs text-gray-500">Campaign #{creative.campaign} | Created {formatDate(creative.created_at)}</p>
                </div>
                <div className="flex gap-2">
                  {!creative.is_approved ? (
                    <>
                      <Button size="sm" onClick={() => handleCreativeAction(creative.id, 'approve')}>
                        Approve
                      </Button>
                      <Button size="sm" variant="secondary" onClick={() => handleCreativeAction(creative.id, 'reject')}>
                        Reject
                      </Button>
                    </>
                  ) : (
                    <StatusBadge status="approved" />
                  )}
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <p className="text-xs font-medium text-gray-500 mb-1">Greeting Template</p>
                  <div className="bg-gray-50 rounded p-3 text-sm whitespace-pre-wrap">{creative.greeting_template}</div>
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500 mb-1">Pitch Template</p>
                  <div className="bg-gray-50 rounded p-3 text-sm whitespace-pre-wrap">{creative.pitch_template}</div>
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500 mb-1">Close Template</p>
                  <div className="bg-gray-50 rounded p-3 text-sm whitespace-pre-wrap">{creative.close_template}</div>
                </div>
              </div>
            </Card>
          ))}
          {creatives.length === 0 && (
            <Card>
              <p className="text-center text-gray-500 py-8">No creatives pending approval.</p>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
