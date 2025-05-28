#!/usr/bin/env python3
"""
Send N simultaneous, non-conflicting, non-fraud orders to the orchestrator
and print a latency histogram.

• Uses a thread pool – easy to understand, no extra deps.
• Assumes orchestrator is reachable at http://localhost:8081.
"""

import uuid, json, time, statistics, random
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


ORCH_URL = "http://localhost:8081/checkout"
# BOOKS     = [f"Book {c}" for c in "AB"]          # Book A … Book J
CARD_OK   = "4111111111111111"                                # non-fraud visa
# USERS     = [f"user{i}" for i in range(2)]
THREADS   = 10                                        # one per order
BOOKS   = [f"Book {chr(65+i)}" for i in range(THREADS)]
USERS   = [f"user{i}" for i in range(THREADS)]




def make_payload(i: int) -> dict:
    """Build a complete, non-conflicting, non-fraud order."""
    title = BOOKS[i]
    return {
        "order_id": str(uuid.uuid4()),
        "user_id": f"user{i}",
        "amount": 30 + i,
        "payment_method": "credit_card",

        # --- every field below is required by transaction_verification ---
        "user": {
            "name": f"User {i}",
            "contact": f"user{i}@example.com"
        },
        "creditCard": {
            "number": CARD_OK,
            "expirationDate": "12/25",
            "cvv": "123"
        },
        "items": [
            { "name": title, "quantity": 1 }
        ],
        "billingAddress": {
            "street": "100 Main St",
            "city": "Tartu",
            "state": "Tartu County",
            "zip": "50090",
            "country": "Estonia"
        },
        "shippingMethod": "Standard",
        "userComment": "load-test",
        "giftWrapping": False,
        "termsAccepted": True
    }

def send(i: int):
    payload = make_payload(i)
    t0 = time.perf_counter()
    r  = requests.post(ORCH_URL, json=payload, timeout=10)
    dt = (time.perf_counter() - t0) * 1000                    # ms
    return i, r.status_code, dt, r.text[:80]                  # truncate body


def main():
    print(f"⏩ firing {THREADS} orders in parallel …")
    latencies, failures = [], []
    with ThreadPoolExecutor(max_workers=THREADS) as pool:
        tasks = [pool.submit(send, i) for i in range(THREADS)]
        for fut in as_completed(tasks):
            i, code, dt, body = fut.result()
            if code == 200:
                latencies.append(dt)
                print(f"✓ order {i:<2}  {BOOKS[i]:<6}  {dt:6.1f} ms  (HTTP 200)")
            else:
                failures.append((i, code, body))
                print(f"✗ order {i:<2}  HTTP {code}  body: {body}")

    print("\nRESULTS")
    if failures:
        for i, code, body in failures:
            print(f"  order {i} failed → HTTP {code}   excerpt: {body}")
    else:
        p50 = statistics.median(latencies)
        p95 = statistics.quantiles(latencies, n=20)[18]       # rough p95
        print(f"  all {THREADS} succeeded")
        print(f"  p50 latency = {p50:5.1f} ms")
        print(f"  p95 latency = {p95:5.1f} ms")
        print(f"  max latency = {max(latencies):5.1f} ms")


if __name__ == "__main__":
    main()
