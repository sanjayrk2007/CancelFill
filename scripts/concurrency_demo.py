#!/usr/bin/env python3
import argparse
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import httpx


PASSWORD = "password123"


def _register(client: httpx.Client, base_url: str, email: str, name: str, role: str) -> Dict[str, str]:
    response = client.post(
        f"{base_url}/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "name": name, "role": role},
    )
    if response.status_code not in (201, 400):
        response.raise_for_status()
    login = client.post(f"{base_url}/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    login.raise_for_status()
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Demonstrate concurrent hold acceptance safety against a running CancelFill server.")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Running server base URL")
    parser.add_argument("--n", type=int, default=10, help="Number of simultaneous accept requests")
    args = parser.parse_args()

    if args.n < 2:
        parser.error("--n must be at least 2")

    base_url = args.base_url.rstrip("/")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")

    with httpx.Client(timeout=20.0) as client:
        business_headers = _register(client, base_url, f"demo-biz-{run_id}@example.com", "Demo Business", "BUSINESS")
        customer_headers: List[Dict[str, str]] = [
            _register(client, base_url, f"demo-customer-{run_id}-{i}@example.com", f"Demo Customer {i}", "CUSTOMER")
            for i in range(args.n)
        ]

        now = datetime.now(timezone.utc)
        slot_response = client.post(
            f"{base_url}/api/v1/slots",
            json={
                "resource_id": f"concurrency-demo-{run_id}",
                "start_time": (now + timedelta(hours=1)).isoformat(),
                "end_time": (now + timedelta(hours=2)).isoformat(),
                "price": "50.00",
            },
            headers=business_headers,
        )
        slot_response.raise_for_status()
        slot_id = slot_response.json()["id"]

        booking_response = client.post(f"{base_url}/api/v1/bookings", json={"slot_id": slot_id}, headers=customer_headers[0])
        booking_response.raise_for_status()
        booking_id = booking_response.json()["id"]

        waitlist_response = client.post(f"{base_url}/api/v1/waitlist", json={"slot_id": slot_id}, headers=customer_headers[1])
        waitlist_response.raise_for_status()

        cancel_response = client.post(f"{base_url}/api/v1/bookings/{booking_id}/cancel", headers=customer_headers[0])
        cancel_response.raise_for_status()
        hold_id = cancel_response.json()["hold"]["id"]

        barrier = threading.Barrier(args.n)

        def accept_once() -> int:
            with httpx.Client(timeout=20.0) as thread_client:
                barrier.wait(timeout=10)
                response = thread_client.post(
                    f"{base_url}/api/v1/holds/{hold_id}/accept",
                    headers=customer_headers[1],
                )
                return response.status_code

        with ThreadPoolExecutor(max_workers=args.n) as executor:
            status_codes = list(executor.map(lambda _: accept_once(), range(args.n)))

    counts = Counter(status_codes)
    print("status_code | count")
    print("----------- | -----")
    for status_code, count in sorted(counts.items()):
        print(f"{status_code:11d} | {count}")

    successes = sum(count for status_code, count in counts.items() if 200 <= status_code < 300)
    conflicts = counts.get(409, 0)
    print(f"\nSuccesses: {successes}; conflicts: {conflicts}; total: {args.n}")
    if successes > 1:
        return 1
    if successes != 1 or conflicts != args.n - 1:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())