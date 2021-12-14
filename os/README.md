# os

This folder contains the base stuff needed to flash a drive and bring up an OS. We start with the bare minmum config required to start cloud-init, get ansible installed, check out the ansible config and run the first boot. 

Network stuff encrupted with sops/age

``` $ sops --age age1evdn7cpxtushtz0rpdg6dnau3hgk4kcpwvjk2s4fnh0pat0n9pgsl0r48k vars.yaml > vars.enc.yaml ```