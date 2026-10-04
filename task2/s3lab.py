"""Teaching client: real S3 probes; synthetic data; no grading assumptions."""
import concurrent.futures as cf
import hashlib
import json
import math
import os
import random
import socket
import sys
import time
from datetime import datetime, timezone
import boto3
from botocore import UNSIGNED
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

FIXTURE = b"research-landing-zone-v1\n"
MIB, N, SIZE = 1024 * 1024, 32, 4 * 1024 * 1024

def emit(row):
    row["utc"] = datetime.now(timezone.utc).isoformat()
    print(json.dumps(row, sort_keys=True), flush=True)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def client(anonymous=False):
    cfg = Config(connect_timeout=2, read_timeout=5,
                max_pool_connections=8,
                retries={"mode": "standard", "total_max_attempts": 1},
                s3={"addressing_style": "path"},
                signature_version=UNSIGNED if anonymous else "s3v4")
    return boto3.client("s3", endpoint_url=os.environ["S3_ENDPOINT"],
                        region_name="us-east-1", config=cfg)

def operation(s3, op, bucket, key="fixture.txt", body=FIXTURE, expected=None):
    start = time.perf_counter()
    row = {"op": op, "bucket": bucket, "key": key,
        "principal": os.environ.get("PRINCIPAL", "unspecified"),
        "ok": False, "bytes": 0, "http": None, "error": None}
    try:
        if op == "put":
            response = s3.put_object(Bucket=bucket, Key=key, Body=body)
            row["bytes"] = len(body)
        elif op == "get":
            response = s3.get_object(Bucket=bucket, Key=key)
            stream = response["Body"]
            try:
                data = stream.read()
            finally:
                stream.close()
            row["bytes"] = len(data)
        elif op == "list":
            response = s3.list_objects_v2(Bucket=bucket, Prefix=key)
            row["keys"] = [x["Key"] for x in response.get("Contents", [])]
        elif op == "delete":
            response = s3.delete_object(Bucket=bucket, Key=key)
        else:
            raise ValueError("unknown operation")
        row["ms"] = 1000 * (time.perf_counter() - start)
        meta = response["ResponseMetadata"]
        row.update(http=meta["HTTPStatusCode"], ok=True,
                   request_id=meta.get("RequestId"))
        if op == "get":
            row["sha256"] = digest(data)
            if expected is not None:
                row["hash_ok"] = row["sha256"] == expected
                row["ok"] = row["ok"] and row["hash_ok"]
    except ClientError as exc:
        row.update(http=exc.response["ResponseMetadata"]["HTTPStatusCode"],
            error=exc.response["Error"]["Code"],
            request_id=exc.response["ResponseMetadata"].get("RequestId"))
    except BotoCoreError as exc:
        row["error"] = type(exc).__name__
    row.setdefault("ms", 1000 * (time.perf_counter() - start))
    return row

def seed(s3):
    for bucket in ("research-raw", "research-release"):
        try:
            s3.head_bucket(Bucket=bucket)
        except ClientError as exc:
            if exc.response["ResponseMetadata"]["HTTPStatusCode"] != 404:
                raise
            s3.create_bucket(Bucket=bucket)
        for key in ("fixture.txt", "delete-probe.txt"):
            row = operation(s3, "put", bucket, key)
            emit(row)
            if not row["ok"]:
                raise RuntimeError("seeding failed")

def p95(values):
    if not values:
        return None
    return sorted(values)[math.ceil(0.95 * len(values)) - 1]

def payloads():
    return [random.Random(i).randbytes(SIZE) for i in range(N)]

def benchmark(s3, concurrency, prefix):
    if concurrency not in (1, 4):
        raise ValueError("use concurrency 1 or 4")
    data = payloads()  # Preparation is outside the measured phases.
    hashes = [digest(x) for x in data]
    for phase in ("put", "get"):
        def one(i):
            return operation(s3, phase, "research-raw",
                f"{prefix}/{i:03d}.bin", data[i], hashes[i])
        start = time.perf_counter()
        with cf.ThreadPoolExecutor(max_workers=concurrency) as pool:
            rows = list(pool.map(one, range(N)))
        elapsed = time.perf_counter() - start
        for row in rows:
            emit(dict(row, run=prefix, concurrency=concurrency))
        good = [r for r in rows if r["ok"]]
        emit({"kind": "summary", "run": prefix, "phase": phase,
            "concurrency": concurrency, "n": N, "successes": len(good),
            "success_ratio": len(good) / N, "wall_s": elapsed,
            "goodput_MiB_s": sum(r["bytes"] for r in good) / MIB / elapsed,
            "p95_success_ms": p95([r["ms"] for r in good])})

def verify(s3, prefix):
    for i, value in enumerate(payloads()):
        row = operation(s3, "get", "research-raw",
            f"{prefix}/{i:03d}.bin", expected=digest(value))
        emit(row)
        if not row["ok"]:
            raise RuntimeError("missing or changed object")
    emit({"kind": "verified", "objects": N, "prefix": prefix})

def watch(s3, seconds):
    start = time.perf_counter()
    while time.perf_counter() - start < seconds:
        offset = time.perf_counter() - start
        row = operation(s3, "get", "research-raw",
                        expected=digest(FIXTURE))
        emit(dict(row, start_s=offset,
                  end_s=time.perf_counter() - start))
        time.sleep(1)  # One-second pause, not a fixed sampling period.

def main():
    args = sys.argv[1:]
    if not args:
        raise SystemExit("seed | probe OP BUCKET KEY [anon] | "
            "bench C PREFIX | verify PREFIX | watch SECONDS | tcp HOST PORT")
    mode = args[0]
    if mode == "tcp":
        start = time.perf_counter()
        try:
            with socket.create_connection((args[1], int(args[2])), timeout=3):
                emit({"tcp_connected": True, "host": args[1],
                      "port": int(args[2])})
        except OSError as exc:
            emit({"tcp_connected": False, "host": args[1],
                "port": int(args[2]), "error": type(exc).__name__,
                "seconds": time.perf_counter() - start})
        return
    anon = mode == "probe" and args[-1] == "anon"
    s3 = client(anon)
    if mode == "seed":
        seed(s3)
    elif mode == "probe":
        row = operation(s3, args[1], args[2], args[3])
        if anon:
            row["principal"] = "anonymous"
        emit(row)
        raise SystemExit(0 if row["ok"] else 2)
    elif mode == "bench": benchmark(s3, int(args[1]), args[2])
    elif mode == "verify": verify(s3, args[1])
    elif mode == "watch": watch(s3, int(args[1]))
    else: raise SystemExit("unknown mode")

if __name__ == "__main__":
    main()