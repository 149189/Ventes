import Badge from '@/components/ui/Badge';

const statusVariants: Record<string, 'default' | 'success' | 'warning' | 'danger' | 'info'> = {
  // Merchant statuses
  pending: 'warning',
  approved: 'success',
  rejected: 'danger',
  suspended: 'danger',
  // Campaign statuses
  draft: 'default',
  active: 'success',
  paused: 'warning',
  ended: 'default',
  // Invoice statuses
  sent: 'info',
  paid: 'success',
  overdue: 'danger',
  disputed: 'warning',
  // Conversation stages
  greeting: 'info',
  qualifying: 'info',
  narrowing: 'info',
  pitching: 'warning',
  closing: 'success',
  handed_off: 'danger',
  // Dispute statuses
  open: 'warning',
  under_review: 'info',
  upheld: 'success',
};

export default function StatusBadge({ status }: { status: string }) {
  return (
    <Badge variant={statusVariants[status] || 'default'}>
      {status.replace(/_/g, ' ')}
    </Badge>
  );
}
