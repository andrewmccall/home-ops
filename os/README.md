# os

This folder contains the base stuff needed to flash a drive and bring up an OS. We start with the bare minmum config required to start cloud-init, get ansible installed, check out the ansible config and run the first boot. 

Network stuff encrupted with sops/age

``` $ sops --age age16rj2w4scur86mjvs6eutq03cwlpygu3pywcedvl0rkh68vzv0dlqagqenq vars.yaml > vars.enc.yaml ```


# Booting servers

Run the script 
add this to grub: 
'''autoinstall quiet ds=nocloud-net;s=http://IP:3003/'''
