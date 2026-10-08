import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/ui/Card';
import Badge from '../../components/ui/Badge';
import EmptyState from '../../components/ui/EmptyState';
import { CheckCircle } from 'lucide-react';

export default function BusinessBookingsPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold text-white tracking-tight">Business Bookings</h1>
            <Badge status="BUSINESS">BUSINESS</Badge>
          </div>
          <p className="text-sm text-slate-400">
            Monitor confirmed appointments, trigger cancellations, and observe automated candidate recovery.
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Customer Appointments</CardTitle>
          <CardDescription>P7c Business Bookings placeholder route (/business/bookings)</CardDescription>
        </CardHeader>
        <CardContent>
          <EmptyState
            icon={CheckCircle}
            title="Business Bookings (P7c Placeholder)"
            description="The customer booking list and cancellation recovery triggers will be connected in Phase 7c."
          />
        </CardContent>
      </Card>
    </div>
  );
}
