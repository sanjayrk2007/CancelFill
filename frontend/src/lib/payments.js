import client from '../api/client';
import { formatCurrency } from './formatters';

let razorpayPromise = null;

function loadRazorpay() {
  if (window.Razorpay) return Promise.resolve();
  if (!razorpayPromise) {
    razorpayPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://checkout.razorpay.com/v1/checkout.js';
      script.onload = resolve;
      script.onerror = () => {
        razorpayPromise = null;
        reject(new Error('Could not load the payment form. Check your connection and try again.'));
      };
      document.body.appendChild(script);
    });
  }
  return razorpayPromise;
}

function cancelled() {
  return Object.assign(new Error('Payment cancelled.'), { cancelled: true });
}

async function openRazorpay(checkout, user) {
  await loadRazorpay();
  return new Promise((resolve, reject) => {
    const rzp = new window.Razorpay({
      key: checkout.key_id,
      amount: checkout.amount_minor,
      currency: checkout.currency,
      order_id: checkout.provider_order_id,
      name: 'CancelFill',
      description: 'Appointment booking',
      prefill: { name: user?.name, email: user?.email, contact: user?.phone || undefined },
      theme: { color: '#2563eb' },
      handler: (resp) =>
        resolve({
          provider_order_id: resp.razorpay_order_id,
          provider_payment_id: resp.razorpay_payment_id,
          signature: resp.razorpay_signature,
        }),
      modal: { ondismiss: () => reject(cancelled()) },
    });
    // A single failed attempt keeps the Razorpay form open so the customer can retry; the payment
    // only counts as failed once they give up (dismiss), which rejects above.
    rzp.on('payment.failed', () => {});
    rzp.open();
  });
}

/**
 * Pay for a free slot (slotId) or for an accepted waitlist offer (holdId).
 * Resolves with the confirmed booking. Rejects with `error.cancelled === true` if the customer
 * did not complete payment; the slot or offer is released (a failed payment == a declined offer).
 */
export async function checkoutAndPay({ slotId, holdId, user }) {
  const { data: checkout } = await client.post('/api/v1/payments/checkout', {
    slot_id: slotId,
    hold_id: holdId,
  });

  let credentials;
  try {
    if (checkout.provider === 'mock') {
      const ok = window.confirm(
        `Test payment: pay ${formatCurrency(checkout.amount)}? (mock gateway, no real money)`,
      );
      if (!ok) throw cancelled();
      credentials = (await client.post(`/api/v1/payments/${checkout.payment_id}/mock-pay`)).data;
    } else {
      credentials = await openRazorpay(checkout, user);
    }
  } catch (err) {
    // SRS 3.12: a payment that does not succeed is treated as a declined offer. The hold is released
    // now and the next waitlisted customer is offered the slot, instead of waiting for the timer.
    await client.post(`/api/v1/holds/${checkout.hold_id}/decline`).catch(() => {});
    throw err;
  }

  const { data: booking } = await client.post('/api/v1/payments/confirm', {
    payment_id: checkout.payment_id,
    ...credentials,
  });
  return booking;
}
