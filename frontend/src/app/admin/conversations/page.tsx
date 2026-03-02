'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card } from '@/components/ui/Card';
import StatusBadge from '@/components/shared/StatusBadge';
import { formatDate } from '@/lib/utils';

interface Conversation {
  id: number;
  customer_phone: string;
  merchant_name: string;
  campaign_name: string;
  stage: string;
  is_opted_out: boolean;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export default function AdminConversationsPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [stageFilter, setStageFilter] = useState('all');
  const [loading, setLoading] = useState(true);

  const stages = ['all', 'greeting', 'qualifying', 'narrowing', 'pitching', 'closing', 'handed_off', 'ended'];

  useEffect(() => {
    async function fetchConversations() {
      try {
        const params = stageFilter !== 'all' ? `?stage=${stageFilter}` : '';
        const response = await api.get(`/conversations/admin/conversations/${params}`);
        setConversations(response.data.results || response.data);
      } catch (error) {
        console.error('Failed to fetch conversations:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchConversations();
  }, [stageFilter]);

  async function handleHandoff(conversationId: number) {
    try {
      await api.post(`/conversations/${conversationId}/handoff/`);
      setConversations((prev) =>
        prev.map((c) => (c.id === conversationId ? { ...c, stage: 'handed_off' } : c)),
      );
    } catch (error) {
      console.error('Failed to hand off conversation:', error);
    }
  }

  if (loading) {
    return <div className="animate-pulse">Loading conversations...</div>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Conversations Monitor</h1>
        <p className="text-sm text-gray-500">{conversations.length} conversations</p>
      </div>

      <div className="flex gap-2 mb-6 flex-wrap">
        {stages.map((s) => (
          <button
            key={s}
            onClick={() => setStageFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors capitalize ${
              stageFilter === s
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {s.replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 font-medium text-gray-500">ID</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Customer</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Merchant</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Campaign</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Stage</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Messages</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Last Activity</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody>
              {conversations.map((conv) => (
                <tr key={conv.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-3 px-4 font-mono text-xs">#{conv.id}</td>
                  <td className="py-3 px-4">
                    {conv.customer_phone}
                    {conv.is_opted_out && (
                      <span className="ml-2 text-xs text-red-500">(opted out)</span>
                    )}
                  </td>
                  <td className="py-3 px-4">{conv.merchant_name}</td>
                  <td className="py-3 px-4 text-gray-600">{conv.campaign_name}</td>
                  <td className="py-3 px-4">
                    <StatusBadge status={conv.stage} />
                  </td>
                  <td className="py-3 px-4">{conv.message_count}</td>
                  <td className="py-3 px-4 text-gray-500">{formatDate(conv.updated_at)}</td>
                  <td className="py-3 px-4">
                    {conv.stage !== 'ended' && conv.stage !== 'handed_off' && (
                      <button
                        onClick={() => handleHandoff(conv.id)}
                        className="text-xs text-amber-600 hover:text-amber-800 font-medium"
                      >
                        Hand Off
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {conversations.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-gray-500">
                    No conversations found.
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
