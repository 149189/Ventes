'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import api from '@/lib/api';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import StatusBadge from '@/components/shared/StatusBadge';
import { formatDate, formatPercent } from '@/lib/utils';
import type { Campaign, CampaignCreative, ABTestVariant } from '@/types/campaign';

export default function CampaignDetailPage() {
  const { id } = useParams();
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [creatives, setCreatives] = useState<CampaignCreative[]>([]);
  const [variants, setVariants] = useState<ABTestVariant[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get(`/campaigns/${id}/`),
      api.get(`/campaigns/${id}/creatives/`).catch(() => ({ data: [] })),
      api.get(`/campaigns/${id}/ab-variants/`).catch(() => ({ data: [] })),
    ]).then(([campRes, creativeRes, variantRes]) => {
      setCampaign(campRes.data);
      setCreatives(creativeRes.data.results || creativeRes.data);
      setVariants(variantRes.data.results || variantRes.data);
    }).finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="animate-pulse">Loading campaign...</div>;
  if (!campaign) return <div>Campaign not found.</div>;

  return (
    <div>
      <div className="flex items-center gap-4 mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{campaign.name}</h1>
        <StatusBadge status={campaign.status} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader><CardTitle>Campaign Details</CardTitle></CardHeader>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-500">Start Date</dt>
              <dd className="font-medium">{formatDate(campaign.start_date)}</dd>
            </div>
            {campaign.end_date && (
              <div className="flex justify-between">
                <dt className="text-gray-500">End Date</dt>
                <dd className="font-medium">{formatDate(campaign.end_date)}</dd>
              </div>
            )}
            <div className="flex justify-between">
              <dt className="text-gray-500">Daily Message Limit</dt>
              <dd className="font-medium">{campaign.daily_message_limit}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Messages Sent Today</dt>
              <dd className="font-medium">{campaign.messages_sent_today}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Target SKUs</dt>
              <dd className="font-medium">{campaign.target_skus.length} products</dd>
            </div>
          </dl>
        </Card>

        <Card>
          <CardHeader><CardTitle>A/B Test Variants</CardTitle></CardHeader>
          {variants.length === 0 ? (
            <p className="text-sm text-gray-500">No A/B variants configured.</p>
          ) : (
            <div className="space-y-3">
              {variants.map((v) => (
                <div key={v.id} className="flex items-center justify-between border-b pb-2 last:border-0">
                  <div>
                    <p className="font-medium text-sm">{v.name}</p>
                    <p className="text-xs text-gray-500">
                      Weight: {(v.traffic_weight * 100).toFixed(0)}% | Type: {v.variant_type}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold">{formatPercent(v.conversion_rate)}</p>
                    <p className="text-xs text-gray-500">
                      {v.conversions}/{v.impressions} converted
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader><CardTitle>Creatives</CardTitle></CardHeader>
        {creatives.length === 0 ? (
          <p className="text-sm text-gray-500">No creatives yet.</p>
        ) : (
          <div className="space-y-4">
            {creatives.map((c) => (
              <div key={c.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium">{c.name}</h4>
                  <StatusBadge status={c.is_approved ? 'approved' : 'pending'} />
                </div>
                <div className="grid grid-cols-3 gap-4 text-xs">
                  <div>
                    <p className="font-medium text-gray-500 mb-1">Greeting</p>
                    <p className="text-gray-700 bg-gray-50 p-2 rounded">{c.greeting_template}</p>
                  </div>
                  <div>
                    <p className="font-medium text-gray-500 mb-1">Pitch</p>
                    <p className="text-gray-700 bg-gray-50 p-2 rounded">{c.pitch_template}</p>
                  </div>
                  <div>
                    <p className="font-medium text-gray-500 mb-1">Close</p>
                    <p className="text-gray-700 bg-gray-50 p-2 rounded">{c.close_template}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
