#!/usr/bin/env python3
"""
Race 10 orders against ONE remaining copy of 'Conflicted Book'.

Success criteria
  • exactly one order gets HTTP 200
  • the rest get 409 (or whatever code your service emits on out-of-stock)
"""

import uuid, time, statistics, random
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

ORCH_URL  = "http://localhost:8081/checkout"
THREADS   = 10
GOOD_CODE = 200       # change if your "ok" status is different
FAIL_CODE = 409       # change to 422/400/... if needed

def make_payload(i: int):
    return {
        "order_id": str(uuid.uuid4()),
        "user_id": f"user{i}",
        "amount": 10,
        "payment_method": "credit_card",
        "user": {"name": f"User {i}", "contact": f"user{i}@x.com"},
        "creditCard": {
            "number": "4111111111111111", "expirationDate": "12/25", "cvv": "123"
        },
        "items": [ { "name": "Conflicted Book", "quantity": 1 } ],
        "billingAddress": {
            "street":"Load 1","city":"Tartu","state":"TC","zip":"50090","country":"EE"
        },
        "shippingMethod":"Standard","termsAccepted":True
    }

def send(i:int):
    t0 = time.perf_counter()
    r  = requests.post(ORCH_URL, json=make_payload(i), timeout=15)
    return i, r.status_code, (time.perf_counter()-t0)*1000, r.text[:120]

def main():
    print(f"⚔️  racing {THREADS} identical orders …")
    successes, rejects, lat = [], [], []
    with ThreadPoolExecutor(max_workers=THREADS) as pool:
        futs = [pool.submit(send,i) for i in range(THREADS)]
        for f in as_completed(futs):
            i, code, ms, body = f.result()
            lat.append(ms)
            if code == GOOD_CODE:
                successes.append((i,ms))
                tag = "WIN"
            elif code == FAIL_CODE:
                rejects.append((i,ms))
                tag = "expected-reject"
            else:
                tag = f"UNEXPECTED {code}"
            print(f"{tag:<15} order {i:<2}  {ms:6.1f} ms  HTTP {code}")

    print("\nSUMMARY")
    print(f"  wins         : {len(successes)}")
    print(f"  expected rej.: {len(rejects)}")
    if len(successes)==1 and len(rejects)==THREADS-1:
        print("Concurrency control PASS")
    else:
        print("Concurrency control FAIL")
    if lat:
        print(f"  latency p50 = {statistics.median(lat):.1f} ms   "
              f"max = {max(lat):.1f} ms")

if __name__ == "__main__":
    main()
