import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/ui/Card';
import Badge from '../../components/ui/Badge';
import EmptyState from '../../components/ui/EmptyState';
import { Users } from 'lucide-react';

export default function BusinessWaitlistPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold text-white tracking-tight">Active Waitlists</h1>
            <Badge status="BUSINESS">BUSINESS</Badge>
          </div>
          <p className="text-sm text-slate-400">
            View ordered waitlists per slot and candidate queue positions.
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Waitlist Queues</CardTitle>
          <CardDescription>P7c Business Waitlist placeholder route (/business/waitlist)</CardDescription>
        </CardHeader>
        <CardContent>
          <EmptyState
            icon={Users}
            title="Business Waitlists (P7c Placeholder)"
            description="The priority waitlist queue visualizer per resource slot will be connected in Phase 7c."
          />
        </CardContent>
      </Card>
    </div>
  );
}
