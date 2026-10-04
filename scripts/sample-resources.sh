#!/bin/bash

while true
do
    echo "===== $(date -u +%FT%TZ) ====="

    kubectl -n "$NS" top pod
    kubectl -n "$NS" get pod -o wide

    sleep 5
done