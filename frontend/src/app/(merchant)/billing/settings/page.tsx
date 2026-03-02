'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import CommissionSlider from '@/components/shared/CommissionSlider';

export default function BillingSettingsPage() {
  const [settings, setSettings] = useState({
    commission_rate: 5,
    auto_optimize_commission: false,
    daily_budget_cap: 100,
    billing_model: 'cpa',
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    async function fetch() {
      try {
        const res = await api.get('/merchants/profile/');
        setSettings({
          commission_rate: parseFloat(res.data.commission_rate),
          auto_optimize_commission: res.data.auto_optimize_commission,
          daily_budget_cap: parseFloat(res.data.daily_budget_cap),
          billing_model: res.data.billing_model,
        });
      } catch (err) {
        console.error('Failed to fetch settings:', err);
      } finally {
        setLoading(false);
      }
    }
    fetch();
  }, []);

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    try {
      await api.put('/merchants/billing-settings/', settings);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error('Failed to save settings:', err);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="animate-pulse">Loading settings...</div>;

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Billing Settings</h1>

      <Card className="mb-6">
        <CardHeader><CardTitle>Commission Rate</CardTitle></CardHeader>
        <CommissionSlider
          value={settings.commission_rate}
          onChange={(v) => setSettings({ ...settings, commission_rate: v })}
          autoOptimize={settings.auto_optimize_commission}
          onAutoOptimizeChange={(v) => setSettings({ ...settings, auto_optimize_commission: v })}
        />
      </Card>

      <Card className="mb-6">
        <CardHeader><CardTitle>Daily Budget Cap</CardTitle></CardHeader>
        <Input
          id="daily_budget_cap"
          type="number"
          value={settings.daily_budget_cap}
          onChange={(e) => setSettings({ ...settings, daily_budget_cap: parseFloat(e.target.value) || 0 })}
          label="Maximum daily spend (INR)"
        />
      </Card>

      <Card className="mb-6">
        <CardHeader><CardTitle>Billing Model</CardTitle></CardHeader>
        <div className="flex gap-4">
          {(['cpa', 'cpc'] as const).map((model) => (
            <label key={model} className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="billing_model"
                value={model}
                checked={settings.billing_model === model}
                onChange={() => setSettings({ ...settings, billing_model: model })}
                className="text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm font-medium uppercase">{model}</span>
              <span className="text-xs text-gray-500">
                {model === 'cpa' ? '(Cost per Acquisition)' : '(Cost per Click)'}
              </span>
            </label>
          ))}
        </div>
      </Card>

      <div className="flex items-center gap-4">
        <Button onClick={handleSave} loading={saving}>Save Settings</Button>
        {saved && (
          <span className="text-green-600 text-sm font-medium">Settings saved!</span>
        )}
      </div>
    </div>
  );
}
