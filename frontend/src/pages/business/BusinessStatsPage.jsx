import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/ui/Card';
import Badge from '../../components/ui/Badge';
import EmptyState from '../../components/ui/EmptyState';
import { BarChart3 } from 'lucide-react';

export default function BusinessStatsPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold text-white tracking-tight">Recovery & Revenue Stats</h1>
            <Badge status="BUSINESS">BUSINESS</Badge>
          </div>
          <p className="text-sm text-slate-400">
            Track recovered bookings, conversion rate, and revenue saved by CancelFill.
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Business Analytics</CardTitle>
          <CardDescription>P7c Business Stats placeholder route (/business/stats)</CardDescription>
        </CardHeader>
        <CardContent>
          <EmptyState
            icon={BarChart3}
            title="Business Analytics (P7c Placeholder)"
            description="The recovery metrics, conversion rates, and revenue impact reports will be connected in Phase 7c."
          />
        </CardContent>
      </Card>
    </div>
  );
}
