#!/usr/bin/env python3
"""
Send a mixture of non-fraudulent and fraudulent orders in parallel and verify
that the orchestrator returns the correct status for each kind.

 • No third-party deps except `requests`
 • Works on Windows / macOS / Linux / WSL
"""

import uuid, time, statistics, random
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

# ─── CONFIG ──────────────────────────────────────────────────────────────────
ORCH_URL     = "http://localhost:8081/checkout"
THREADS_OK   = 5                         # non-fraud orders
THREADS_BAD  = 5                         # fraud orders
STATUS_OK    = 200                       # what your API returns on success
STATUS_FRAUD = 409                       # change to 400/422 if different

CARD_OK      = "4111111111111111"
CARD_FRAUD   = "4000000000000002"        # Visa test card that should fail

# one unique book per order so we never hit stock conflicts
BOOK_TITLES  = [f"Book {chr(65+i)}" for i in range(THREADS_OK + THREADS_BAD)]
# ─────────────────────────────────────────────────────────────────────────────


def make_payload(i: int, fraud: bool) -> dict:
    """Return a complete order body."""
    return {
        "order_id": str(uuid.uuid4()),
        "user_id": f"user{i}",
        "amount": 30 + i,
        "payment_method": "credit_card",
        "user": {
            "name": f"User {i}",
            "contact": f"user{i}@example.com"
        },
        "creditCard": {
            "number": CARD_FRAUD if fraud else CARD_OK,
            "expirationDate": "12/25",
            "cvv": "123"
        },
        "items": [
            { "name": BOOK_TITLES[i], "quantity": 1 }
        ],
        "billingAddress": {
            "street": "100 Main St",
            "city": "Tartu",
            "state": "Tartu County",
            "zip": "50090",
            "country": "Estonia"
        },
        "shippingMethod": "Standard",
        "userComment": "mixed-test",
        "giftWrapping": False,
        "termsAccepted": True
    }


def send(i: int, fraud: bool):
    payload = make_payload(i, fraud)
    t0 = time.perf_counter()
    resp = requests.post(ORCH_URL, json=payload, timeout=15)
    latency_ms = (time.perf_counter() - t0) * 1000
    expected   = STATUS_FRAUD if fraud else STATUS_OK
    ok         = resp.status_code == expected
    return {
        "i": i, "fraud": fraud, "status": resp.status_code,
        "latency": latency_ms, "ok": ok, "body": resp.text[:100]
    }


def main():
    total_threads = THREADS_OK + THREADS_BAD
    print(f"🚀 firing {total_threads} mixed orders "
          f"({THREADS_OK} ok, {THREADS_BAD} fraud) …")

    # build a shuffled work list: True == fraud order
    work = [False] * THREADS_OK + [True] * THREADS_BAD
    random.shuffle(work)

    results, lat_ok, lat_bad = [], [], []
    with ThreadPoolExecutor(max_workers=total_threads) as pool:
        futures = [pool.submit(send, idx, fraud) for idx, fraud in enumerate(work)]
        for fut in as_completed(futures):
            res = results.append(fut.result()) or fut.result()
            tag = "FRAUD" if res["fraud"] else "OK"
            check = "✓" if res["ok"] else "✗"
            print(f"{check} order {res['i']:<2} {tag:<5} "
                  f"{res['latency']:6.1f} ms  HTTP {res['status']}")
            if res["fraud"]: lat_bad.append(res["latency"])
            else:            lat_ok.append(res["latency"])

    # summary
    good = sum(r["ok"] for r in results)
    print("\nRESULTS")
    print(f"  passed {good}/{total_threads}")
    if good == total_threads:
        print(f"  OK  p50={statistics.median(lat_ok):.1f} ms  "
              f"p95={statistics.quantiles(lat_ok,n=20)[18]:.1f} ms")
        print(f"  FRAUD p50={statistics.median(lat_bad):.1f} ms  "
              f"p95={statistics.quantiles(lat_bad,n=20)[18]:.1f} ms")
    else:
        for r in results:
            if not r["ok"]:
                print(f"  order {r['i']} unexpected HTTP {r['status']} "
                      f"body: {r['body']}")


if __name__ == "__main__":
    main()
