## :construction: Installation

Create namespace
```bash
kubectl create namespace flux-system
```

Add SOPS private key
```bash

kubectl -n flux-system create secret generic sops-age \
  --from-file=age.agekey=sops-key.txt
```

Genrate a key
```
flux create secret git flux-cluster \
    --url=ssh://git@github.com/andrewmccall/home-ops \
  ```

put the key as a deploy key in github

Install Flux
```bash
kubectl apply --kustomize=./cluster/bootstrap
kubectl apply --kustomize=./cluster/base/flux-system
```

Enable k3s upgrades (if not already done by ansible)
```bash
kubectl label node --all k3s-upgrade=true
```