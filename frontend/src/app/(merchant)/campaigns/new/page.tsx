'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import Button from '@/components/ui/Button';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';

interface SKUOption {
  id: number;
  sku_code: string;
  name: string;
}

interface PromoOption {
  id: number;
  name: string;
  promo_type: string;
}

export default function NewCampaignPage() {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [skus, setSkus] = useState<SKUOption[]>([]);
  const [promos, setPromos] = useState<PromoOption[]>([]);

  const [form, setForm] = useState({
    name: '',
    description: '',
    start_date: new Date().toISOString().slice(0, 16),
    end_date: '',
    daily_message_limit: 1000,
    target_skus: [] as number[],
    promo_rule: '' as string | number,
  });

  useEffect(() => {
    Promise.all([
      api.get('/merchants/skus/').catch(() => ({ data: { results: [] } })),
      api.get('/merchants/promo-rules/').catch(() => ({ data: { results: [] } })),
    ]).then(([skuRes, promoRes]) => {
      setSkus(skuRes.data.results || skuRes.data || []);
      setPromos(promoRes.data.results || promoRes.data || []);
    });
  }, []);

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  function toggleSKU(id: number) {
    setForm((prev) => ({
      ...prev,
      target_skus: prev.target_skus.includes(id)
        ? prev.target_skus.filter((s) => s !== id)
        : [...prev.target_skus, id],
    }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      const payload: Record<string, unknown> = {
        name: form.name,
        description: form.description,
        start_date: new Date(form.start_date).toISOString(),
        daily_message_limit: form.daily_message_limit,
        target_skus: form.target_skus,
      };
      if (form.end_date) {
        payload.end_date = new Date(form.end_date).toISOString();
      }
      if (form.promo_rule) {
        payload.promo_rule = Number(form.promo_rule);
      }
      await api.post('/campaigns/', payload);
      router.push('/campaigns');
    } catch (err: any) {
      const detail = err?.response?.data;
      if (typeof detail === 'object') {
        const messages = Object.entries(detail)
          .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
          .join('; ');
        setError(messages);
      } else {
        setError('Failed to create campaign.');
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Create Campaign</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 text-sm">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <Card className="mb-6">
          <CardHeader><CardTitle>Campaign Details</CardTitle></CardHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Campaign Name *
              </label>
              <input
                type="text"
                name="name"
                value={form.name}
                onChange={handleChange}
                required
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                placeholder="e.g. Summer Sale 2024"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                name="description"
                value={form.description}
                onChange={handleChange}
                rows={3}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                placeholder="Brief description of this campaign..."
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Start Date *
                </label>
                <input
                  type="datetime-local"
                  name="start_date"
                  value={form.start_date}
                  onChange={handleChange}
                  required
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  End Date
                </label>
                <input
                  type="datetime-local"
                  name="end_date"
                  value={form.end_date}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Daily Message Limit
              </label>
              <input
                type="number"
                name="daily_message_limit"
                value={form.daily_message_limit}
                onChange={handleChange}
                min={1}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
          </div>
        </Card>

        {skus.length > 0 && (
          <Card className="mb-6">
            <CardHeader><CardTitle>Target Products</CardTitle></CardHeader>
            <p className="text-xs text-gray-500 mb-3">Select which products this campaign promotes.</p>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {skus.map((sku) => (
                <label key={sku.id} className="flex items-center gap-3 p-2 rounded hover:bg-gray-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.target_skus.includes(sku.id)}
                    onChange={() => toggleSKU(sku.id)}
                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-gray-700">
                    <span className="font-medium">{sku.name}</span>
                    <span className="text-gray-400 ml-2">({sku.sku_code})</span>
                  </span>
                </label>
              ))}
            </div>
          </Card>
        )}

        {promos.length > 0 && (
          <Card className="mb-6">
            <CardHeader><CardTitle>Promo Rule (Optional)</CardTitle></CardHeader>
            <select
              name="promo_rule"
              value={form.promo_rule}
              onChange={handleChange}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="">No promo rule</option>
              {promos.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.promo_type})
                </option>
              ))}
            </select>
          </Card>
        )}

        <div className="flex items-center justify-end gap-3">
          <Button
            type="button"
            variant="secondary"
            onClick={() => router.push('/campaigns')}
          >
            Cancel
          </Button>
          <Button type="submit" loading={saving}>
            Create Campaign
          </Button>
        </div>
      </form>
    </div>
  );
}
