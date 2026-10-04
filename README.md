# Big Data Lab — Group 08

## Task 5: Storage Pod Recovery Verification

### Objective

This task evaluates whether the object-storage service can recover from the deletion of its storage Pod while retaining access to previously stored benchmark objects. The experiment verifies Kubernetes workload recovery, persistent-volume continuity, object integrity, and selected access-control behaviors after recovery.

### Environment and design

The experiment was conducted in the Google Kubernetes Engine cluster using namespace `bd-g08`. The storage workload is managed by the Kubernetes Deployment `objects`, and clients access the `objects` Service on TCP port 8333. The Service uses a ClusterIP, so it is not directly exposed through a public Service IP. Persistent data is associated with the `object-data` PersistentVolumeClaim.

The namespace has a ResourceQuota limiting CPU, memory, Pod count, PVC count, and requested storage. During recovery, quota constraints caused Pod-creation failures before the replacement Pod became available. This demonstrates that resource quotas are operational constraints that must be considered during recovery.

### Recovery procedure and results

The experiment recorded the Deployment, Pod, PVC, events, and relevant storage logs before and after recovery. The storage Pod was deleted to test whether the Deployment would recreate it. The replacement Pod reached the Running state and reported one ready replica.

The `object-data` PVC remained Bound. Its UID and backing volume identity were unchanged across Pod replacement. A post-recovery verification checked 32 objects under the `bench/r1-c1` prefix. All 32 requests returned HTTP 200, and all recorded object hashes matched the expected hashes.

Three security checks were repeated after recovery. S06 confirmed that the analyst could retrieve the permitted research fixture. S08 confirmed that an analyst PUT to the protected research-release location was denied with HTTP 403. S10 confirmed that an analyst GET from the restricted research-raw location was denied with HTTP 403. These outcomes matched the expected access-control behavior.

### Limitations and follow-up

This experiment tested storage-Pod replacement only. It did not test node failure, cluster failure, backup restoration, disaster recovery, crash consistency, or power-loss durability. Exact recovery time and service downtime were not measured. The storage logs also reported a security warning concerning the gRPC administrative endpoint and its lack of mutual TLS; this requires a separate security review.

The evidence files in `evidence/recovery/` record the observed state and verification results. Before submission, the team should review the evidence, complete governance fields using confirmed team decisions, and ensure that no real credentials are included in the submitted repository or Git history.
