'use client';

import { useState } from 'react';

interface CommissionSliderProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  autoOptimize?: boolean;
  onAutoOptimizeChange?: (value: boolean) => void;
}

export default function CommissionSlider({
  value,
  onChange,
  min = 4,
  max = 10,
  autoOptimize = false,
  onAutoOptimizeChange,
}: CommissionSliderProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="label">Commission Rate</label>
        <span className="text-lg font-semibold text-primary-600">{value}%</span>
      </div>

      <input
        type="range"
        min={min}
        max={max}
        step={0.5}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        disabled={autoOptimize}
        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary-600 disabled:opacity-50"
      />

      <div className="flex justify-between text-xs text-gray-500">
        <span>{min}%</span>
        <span>{max}%</span>
      </div>

      {onAutoOptimizeChange && (
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={autoOptimize}
            onChange={(e) => onAutoOptimizeChange(e.target.checked)}
            className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
          />
          Auto-optimize commission rate
        </label>
      )}
    </div>
  );
}
