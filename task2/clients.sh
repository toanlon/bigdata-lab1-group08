#!/bin/sh

set -eu

: "${NS:?}" "${CLIENT_IMAGE:?}"

for role in owner ingestor analyst blocked; do

  ACCESS=""

  CREDS=""

  if [ "$role" != blocked ]; then

    ACCESS="access: s3"

    CREDS="envFrom: [{secretRef: {name: s3-$role}}]"

  fi

  cat <<EOF | kubectl -n "$NS" apply -f -

apiVersion: v1

kind: Pod

metadata:

  name: $role

  labels: {role: $role, $ACCESS}

spec:

  automountServiceAccountToken: false

  securityContext: {runAsNonRoot: false}

  containers:

  - name: client

    image: $CLIENT_IMAGE

    command: [sleep, infinity]

    securityContext:

      allowPrivilegeEscalation: false

      capabilities: {drop: [ALL]}

      seccompProfile: {type: RuntimeDefault}

    resources:

      requests: {cpu: 100m, memory: 128Mi}

      limits: {cpu: 500m, memory: 512Mi}

    env:

    - {name: S3_ENDPOINT, value: 'http://objects:8333'}

    - {name: PRINCIPAL, value: '$role'}

    $CREDS

EOF

done

kubectl -n "$NS" wait --for=condition=Ready pod/owner pod/ingestor \

  pod/analyst pod/blocked --timeout=120s