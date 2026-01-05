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
    --url=ssh://git@github.com/andrewmccall/home-ops
  ```

put the key as a deploy key in github

Install Flux
```bash

flux bootstrap git \
  --url=ssh://git@github.com/andrewmccall/home-ops.git \
  --branch=main \
  --private-key-file=../key \
  --path=cluster/flux-system/ \
  --cluster-domain=cluster.andrewmccall.com
```

Enable k3s upgrades (if not already done by ansible)
`
kubectl label node --all k3s-upgrade=true
```

Make sure we've got the cloudnative postgres installed.

````bash

kubectl apply --server-side -f \
  https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.26/releases/cnpg-1.26.0.yaml
  ````