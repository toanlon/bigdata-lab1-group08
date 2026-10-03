#!/bin/bash

set -e

echo "Warm-up..."
kubectl -n "$NS" exec ingestor -- python /opt/s3lab.py \
  probe get research-raw fixture.txt

for pair in \
  '1 r1-c1' \
  '4 r1-c4' \
  '4 r2-c4' \
  '1 r2-c1' \
  '1 r3-c1' \
  '4 r3-c4'
do
    set -- $pair

    concurrency="$1"
    trial="$2"

    echo "Running $trial with concurrency=$concurrency"

    kubectl -n "$NS" exec ingestor -- python /opt/s3lab.py \
      bench "$concurrency" "bench/$trial" \
      > "evidence/benchmark/$trial.jsonl"
done