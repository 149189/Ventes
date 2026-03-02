'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import Button from '@/components/ui/Button';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ created: number; errors: string[] } | null>(null);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await api.post('/merchants/skus/upload/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setResult(res.data);
    } catch (err: any) {
      setResult({ created: 0, errors: [err.response?.data?.error || 'Upload failed'] });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Upload Products (CSV)</h1>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>CSV Format</CardTitle>
        </CardHeader>
        <p className="text-sm text-gray-600 mb-3">
          Your CSV must include these columns:
        </p>
        <code className="block bg-gray-50 p-3 rounded text-xs font-mono text-gray-700">
          sku_code,name,description,category,original_price,discounted_price,landing_url,image_url,stock_quantity
        </code>
        <p className="text-xs text-gray-500 mt-2">
          <strong>Required:</strong> sku_code, name, original_price, landing_url.
          Other fields are optional.
        </p>
      </Card>

      <Card>
        <form onSubmit={handleUpload} className="space-y-4">
          <div>
            <label className="label">Select CSV File</label>
            <input
              type="file"
              accept=".csv"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4
                         file:rounded-lg file:border-0 file:text-sm file:font-medium
                         file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100"
            />
          </div>

          <Button type="submit" loading={loading} disabled={!file}>
            Upload Products
          </Button>
        </form>

        {result && (
          <div className="mt-4">
            {result.created > 0 && (
              <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg mb-2">
                Successfully imported {result.created} products.
              </div>
            )}
            {result.errors.length > 0 && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
                <p className="font-medium mb-1">Errors:</p>
                <ul className="list-disc list-inside text-sm">
                  {result.errors.map((err, i) => (
                    <li key={i}>{err}</li>
                  ))}
                </ul>
              </div>
            )}
            {result.created > 0 && (
              <Button variant="secondary" className="mt-3" onClick={() => router.push('/products')}>
                View Products
              </Button>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
