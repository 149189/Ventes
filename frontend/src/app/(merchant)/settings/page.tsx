'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import StatusBadge from '@/components/shared/StatusBadge';

export default function MerchantSettingsPage() {
  const [profile, setProfile] = useState({
    company_name: '',
    company_website: '',
    contact_email: '',
    contact_phone: '',
    billing_address: '',
    tax_id: '',
    whatsapp_number: '',
    status: 'pending',
    tier: 'bronze',
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    async function fetch() {
      try {
        const res = await api.get('/merchants/profile/');
        setProfile(res.data);
      } catch (err) {
        console.error('Failed to fetch profile:', err);
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
      await api.put('/merchants/profile/', profile);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error('Failed to save profile:', err);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="animate-pulse">Loading profile...</div>;

  return (
    <div className="max-w-2xl">
      <div className="flex items-center gap-4 mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <StatusBadge status={profile.status} />
        <StatusBadge status={profile.tier} />
      </div>

      <Card className="mb-6">
        <CardHeader><CardTitle>Company Information</CardTitle></CardHeader>
        <div className="space-y-4">
          <Input
            id="company_name" label="Company Name"
            value={profile.company_name}
            onChange={(e) => setProfile({ ...profile, company_name: e.target.value })}
          />
          <Input
            id="company_website" label="Website"
            type="url"
            value={profile.company_website}
            onChange={(e) => setProfile({ ...profile, company_website: e.target.value })}
          />
          <Input
            id="tax_id" label="Tax ID / GST Number"
            value={profile.tax_id}
            onChange={(e) => setProfile({ ...profile, tax_id: e.target.value })}
          />
        </div>
      </Card>

      <Card className="mb-6">
        <CardHeader><CardTitle>Contact Details</CardTitle></CardHeader>
        <div className="space-y-4">
          <Input
            id="contact_email" label="Contact Email"
            type="email"
            value={profile.contact_email}
            onChange={(e) => setProfile({ ...profile, contact_email: e.target.value })}
          />
          <Input
            id="contact_phone" label="Contact Phone"
            type="tel"
            value={profile.contact_phone}
            onChange={(e) => setProfile({ ...profile, contact_phone: e.target.value })}
          />
          <Input
            id="whatsapp_number" label="WhatsApp Business Number"
            value={profile.whatsapp_number}
            onChange={(e) => setProfile({ ...profile, whatsapp_number: e.target.value })}
          />
          <div>
            <label className="label" htmlFor="billing_address">Billing Address</label>
            <textarea
              id="billing_address"
              className="input-field"
              rows={3}
              value={profile.billing_address}
              onChange={(e) => setProfile({ ...profile, billing_address: e.target.value })}
            />
          </div>
        </div>
      </Card>

      <div className="flex items-center gap-4">
        <Button onClick={handleSave} loading={saving}>Save Changes</Button>
        {saved && <span className="text-green-600 text-sm font-medium">Profile saved!</span>}
      </div>
    </div>
  );
}
