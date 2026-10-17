<p align="left">
   <img src="https://i.imgur.com/4l9bHvG.png" alt="ansible logo" width="150" align="left" />
   <img src="https://i.imgur.com/EXNTJnA.png" alt="kubernetes home logo" width="150" align="left" />
</p>

### Operations for my home...
_...with Ansible, Kubernetes and flex :sailboat:
<br/><br/><br/><br/>

![lint](https://github.com/Diaoul/home-ops/workflows/lint/badge.svg)
![pre-commit](https://github.com/Diaoul/home-ops/workflows/pre-commit/badge.svg)

## :notebook: Todo

* Get the k8s cluster up. 
* Add some code to poke DHCP addresses into my router.
* Create an internal DNS server and share that. 
* 


-append 'autoinstall ds=nocloud-net;s=http://_gateway:3003/'

## :open_book: Overview
This repo contains everything I use to setup and manage my home network. 

* An internal DNS server
* k8s cluster that runs on all my machines. 
* Everything is deployed as a docker container usually using labels to get it in the right place
* All machines are ubuntu servers


### :robot: Automatic updates
All dependencies are autmatically updated by Renovatebot. https://docs.renovatebot.com/modules/manager/

Renovate bot is cool af. It runs, checks project dependencies and creates a PR if there are newer ones. 
I automerge mine, which then upgrades them, deploys them and bam! My network is all the most recent version. 

Since some of my tools are docker images I push to docker hub, it even deploys my own code as dependencies. 

### Instalation: 

* Add MAC to DHCP list so we get consistent address 
* Add DNS entry for IP so we have the right name
* Flash a base boot media, with basics as parameters.  
* Manually run ansible or ping the hook. 


### Bootstraping with the Base image

The base image consists of 
* andrewmccall user
    * Added to suoders
    * ssh pub key allowed to connect. 
* ansible user
    * Added to sudoers
    * ssh pub key allowed to connect. 
* Python to be able to run ansible

Once the base image is flashed to the install media (see /scripts) then the machine can be booted on the network. The DHCP server
will assign the correct IP. 

### Create the ansible configuration for the server

Once the ansible config is created the server can be started, on boot the server will try and download this repository and will execute the ansible config. This is usually pretty simple and mostly the same for most machines. 

* Install k3s. 
* Setup any hardware additional hardware that is required. 

## :gear: Hardware
Here is a list of what runs on my network. 

In the Rack!
1U DSL Modems x2 on custom printed 1U brackets. 
1U Unify USG and 12V meanwell PSU in custom bracket and enclosure. 
1U Patch Panel. 
1U TPLink Switch.
4U betelguese home server.   

Elsewhere on the network: 

| Host             | Device                  | Storage                  | Purpose                                      |
|------------------|-------------------------|--------------------------|----------------------------------------------|
| betelgeuse.local | Raspberrt Pi 4          | 64GB SD                  | k8s master, octoprint                        |
|                  | Raspberry Pi Zero 2     | 64GB SD                  | Smart mirror                                 |
|                  | Raspberry Pi Zero       | 16GB SDe                 | Gamer beds in boys rooms                     |

## Adding new harders

1) Flash the image.
2) Add entries to Ansible
3) Label any nodes

# Setting up. 

Hermes runs in [Agent Sandbox](cluster/apps/hermes/README.md) with a dedicated
OpenRouter key. See that guide for credential setup and the OpenClaw cutover.

Validate rendered cluster manifests with `python3 scripts/verify-cluster.py`.
This requires `kubectl`, PyYAML and jsonschema. CI runs the same check and rejects
`cluster.local` in rendered resources. This cluster's DNS domain is
`cluster.andrewmccall.com`; see [Flux domain configuration](cluster/README.md#cluster-dns-domain).

Check the live monitoring stack with `python3 scripts/verify-monitoring.py`: Grafana
datasources, plugins and dashboards, scrape targets, Loki logs from every namespace,
and Alertmanager delivery. It is read-only and needs `kubectl` access to the cluster.

System requirements - 
sops, age, yq, 

1. Install SOPS
2. Intall age. 
3. Get the age key.txt and put it in `~/Library/Application\ Support/sops/age/keys.txt`

# Credits
This repo is heavily based on: https://github.com/Diaoul/home-ops
