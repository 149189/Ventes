'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';

interface PlatformSettings {
  default_commission_rate: number;
  min_commission_rate: number;
  max_commission_rate: number;
  default_daily_budget_cap: number;
  dispute_window_days: number;
  fraud_score_threshold: number;
  max_daily_messages_per_campaign: number;
  redirect_token_expiry_hours: number;
  followup_delay_hours: number;
  auto_optimize_enabled: boolean;
}

export default function AdminSettingsPage() {
  const [settings, setSettings] = useState<PlatformSettings>({
    default_commission_rate: 7.0,
    min_commission_rate: 4.0,
    max_commission_rate: 10.0,
    default_daily_budget_cap: 5000,
    dispute_window_days: 14,
    fraud_score_threshold: 0.7,
    max_daily_messages_per_campaign: 1000,
    redirect_token_expiry_hours: 72,
    followup_delay_hours: 24,
    auto_optimize_enabled: true,
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    async function fetchSettings() {
      try {
        const response = await api.get('/settings/platform/');
        setSettings(response.data);
      } catch {
        // Use defaults if endpoint not available yet
      }
    }
    fetchSettings();
  }, []);

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    try {
      await api.put('/settings/platform/', settings);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (error) {
      console.error('Failed to save settings:', error);
    } finally {
      setSaving(false);
    }
  }

  function updateSetting<K extends keyof PlatformSettings>(key: K, value: PlatformSettings[K]) {
    setSettings((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Platform Settings</h1>
        <div className="flex items-center gap-3">
          {saved && <span className="text-sm text-green-600">Settings saved.</span>}
          <Button onClick={handleSave} loading={saving}>
            Save Settings
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Commission Defaults</CardTitle>
          </CardHeader>
          <div className="space-y-4">
            <Input
              label="Default Commission Rate (%)"
              type="number"
              min={0}
              max={100}
              step={0.5}
              value={settings.default_commission_rate}
              onChange={(e) => updateSetting('default_commission_rate', parseFloat(e.target.value))}
            />
            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Min Rate (%)"
                type="number"
                min={0}
                max={100}
                step={0.5}
                value={settings.min_commission_rate}
                onChange={(e) => updateSetting('min_commission_rate', parseFloat(e.target.value))}
              />
              <Input
                label="Max Rate (%)"
                type="number"
                min={0}
                max={100}
                step={0.5}
                value={settings.max_commission_rate}
                onChange={(e) => updateSetting('max_commission_rate', parseFloat(e.target.value))}
              />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={settings.auto_optimize_enabled}
                onChange={(e) => updateSetting('auto_optimize_enabled', e.target.checked)}
                className="rounded border-gray-300"
              />
              Enable auto-optimize commission globally
            </label>
          </div>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Budget & Billing</CardTitle>
          </CardHeader>
          <div className="space-y-4">
            <Input
              label="Default Daily Budget Cap"
              type="number"
              min={0}
              step={100}
              value={settings.default_daily_budget_cap}
              onChange={(e) => updateSetting('default_daily_budget_cap', parseFloat(e.target.value))}
            />
            <Input
              label="Dispute Window (days)"
              type="number"
              min={1}
              max={90}
              value={settings.dispute_window_days}
              onChange={(e) => updateSetting('dispute_window_days', parseInt(e.target.value))}
            />
          </div>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Fraud Detection</CardTitle>
          </CardHeader>
          <div className="space-y-4">
            <div>
              <label className="label">Fraud Score Threshold</label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={settings.fraud_score_threshold}
                  onChange={(e) => updateSetting('fraud_score_threshold', parseFloat(e.target.value))}
                  className="flex-1"
                />
                <span className="text-sm font-medium w-12 text-right">
                  {(settings.fraud_score_threshold * 100).toFixed(0)}%
                </span>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Clicks scoring above this threshold are flagged as fraudulent.
              </p>
            </div>
            <Input
              label="Redirect Token Expiry (hours)"
              type="number"
              min={1}
              max={720}
              value={settings.redirect_token_expiry_hours}
              onChange={(e) => updateSetting('redirect_token_expiry_hours', parseInt(e.target.value))}
            />
          </div>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Conversations</CardTitle>
          </CardHeader>
          <div className="space-y-4">
            <Input
              label="Max Daily Messages per Campaign"
              type="number"
              min={1}
              value={settings.max_daily_messages_per_campaign}
              onChange={(e) => updateSetting('max_daily_messages_per_campaign', parseInt(e.target.value))}
            />
            <Input
              label="Follow-up Delay (hours)"
              type="number"
              min={1}
              max={168}
              value={settings.followup_delay_hours}
              onChange={(e) => updateSetting('followup_delay_hours', parseInt(e.target.value))}
            />
          </div>
        </Card>
      </div>
    </div>
  );
}
