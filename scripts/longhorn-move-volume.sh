#!/bin/bash
# Move a single-replica Longhorn volume to the disks tagged hdd, live: add a replica there,
# wait for it to rebuild, drop the old one. Usage: longhorn-move-volume.sh <longhorn volume name>
# (the PV name, pvc-...). See cluster/core/longhorn/README.md.
set -euo pipefail
V=$1; NS=longhorn; NODE=${NODE:-vecna}
reps() { kubectl get replicas.longhorn.io -n $NS -l longhornvolume=$V -o jsonpath='{range .items[*]}{.metadata.name} {.spec.diskID} {.status.currentState}{"\n"}{end}'; }
restore() { kubectl patch settings.longhorn.io -n $NS replica-soft-anti-affinity --type merge -p '{"value":"false"}' >/dev/null; }
trap restore EXIT
bulk=$(kubectl get nodes.longhorn.io -n $NS $NODE -o jsonpath='{.status.diskStatus.bulk0.diskUUID}')
kubectl patch settings.longhorn.io -n $NS replica-soft-anti-affinity --type merge -p '{"value":"true"}' >/dev/null
kubectl patch volumes.longhorn.io -n $NS $V --type merge -p '{"spec":{"diskSelector":["hdd"],"numberOfReplicas":2}}' >/dev/null
for i in $(seq 1 720); do
  n=$(reps | awk -v b=$bulk '$2==b && $3=="running"' | wc -l)
  rw=$(kubectl get engines.longhorn.io -n $NS -l longhornvolume=$V -o jsonpath='{.items[0].status.replicaModeMap}' | grep -o '"RW"' | wc -l)
  [ "$n" -ge 1 ] && [ "$rw" -ge 2 ] && break
  sleep 10
done
[ "$n" -ge 1 ] && [ "$rw" -ge 2 ] || { echo "rebuild did not finish; volume left with 2 replicas"; reps; exit 1; }
old=$(reps | awk -v b=$bulk '$2!=b {print $1}')
kubectl patch volumes.longhorn.io -n $NS $V --type merge -p '{"spec":{"numberOfReplicas":1}}' >/dev/null
kubectl delete replicas.longhorn.io -n $NS $old
echo "moved $V to bulk0 after ~$((i*10))s"
