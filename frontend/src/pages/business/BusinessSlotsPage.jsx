import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/ui/Card';
import Badge from '../../components/ui/Badge';
import EmptyState from '../../components/ui/EmptyState';
import { Layers } from 'lucide-react';

export default function BusinessSlotsPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold text-white tracking-tight">Business Slot Management</h1>
            <Badge status="BUSINESS">BUSINESS</Badge>
          </div>
          <p className="text-sm text-slate-400">
            Publish resource slots, set pricing, and monitor real-time availability states.
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Resource Slots</CardTitle>
          <CardDescription>P7c Business Slots placeholder route (/business/slots)</CardDescription>
        </CardHeader>
        <CardContent>
          <EmptyState
            icon={Layers}
            title="Business Slots Management (P7c Placeholder)"
            description="The slot creation form, capacity controls, and live status monitors will be connected in Phase 7c."
          />
        </CardContent>
      </Card>
    </div>
  );
}
