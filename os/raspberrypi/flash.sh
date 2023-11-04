#!/bin/sh
#
# Helper script used to flash boot media. This script is for SD cards in raspbery Pis and works on my mac. I haven't 
# tested is elsewhere.

# USAGE: ./flash.sh <HOSTNAME> <DEVICE> [ARCH] [VERSION]
# Where, hostname isn't the fqdn and device is just the last part - eg: 
# $  ./flash.sh betelguese disks2 arm64 21.10

set -e

#hostname and device are required.
hostname=$1
device=$2

if [ -z $device ] || [ -z $hostname ]; then
    echo "Usage: ./flash.sh <HOSTNAME> <DEVICE> [ARCH] [VERSION] "
    exit 1;
fi;

if [ ! -e /dev/$device ]; then
    echo "No such device found: /dev/$device"
    exit 1;
fi;

# Arch and version are optional.
arch=$3
version=$4

if [ -z $arch ]; then
    arch='arm64'
fi;

if [ ! -d $arch ]; then
    echo "No such arch found: $arch"
    exit 1;
fi;

if [ -z $version ]; then
    version='22.04.3'
fi;


workdir=/tmp/homeops

mkdir -p $workdir/{images,mnt}/

#Donwload image
image="/tmp/homeops/images/ubuntu-server-$version-$arch.img"
if [ ! -f $image ]; then
    url="https://cdimage.ubuntu.com/releases/22.04/release/ubuntu-$version-preinstalled-server-arm64+raspi.img.xz"
    echo "Fetching image $url"
    curl $url --output $image
fi;

filesize=$(xz -l /tmp/homeops/images/ubuntu-server-$version-$arch.img | tail -n -1 | awk '{print $5}' | sed 's/,//g' | sed 's/\.*//g')

filesize=$((filesize * 1024 * 1024 / 10))

# do the flashinng.
echo "Unmounting and flashing disk /dev/$device, this may take a few minutes"
diskutil unmountDisk /dev/$device
xzcat $image | pv -s ${filesize} | dd of=/dev/$device bs=4m && sync

echo "SSD flashed."
sleep 10;

echo "Please remove and re-insert SSD."
while [ ! -e /dev/$device ]; do
    sleep 1;
done

# mount the disk
echo "Remounting disk /dev/$device to $workdir/mnt"
diskutil unmountDisk /dev/$device
diskutil mount -mountPoint $workdir/mnt /dev/${device}s1 

# copy the configs and set the hostname
echo "Applying config"

cp ./${arch}/* ${workdir}/mnt/
sed -i '' "s/HOSTNAME/${hostname}/g" $workdir/mnt/user-data

dec=$(sops -d ../vars.enc.yaml)
network_ssid=$(printf '%s' "$dec" | yq e ".network.ssid" -)
network_password=$(printf '%s' "$dec" | yq e ".network.password" -)

sed -i '' "s/network_ssid/${network_ssid}/g" $workdir/mnt/network-config
sed -i '' "s/network_password/${network_password}/g" $workdir/mnt/network-config

# unmount the disk, so we can boot a pi. 
diskutil unmountDisk /dev/$device
echo "Disk imaged, you can remove the card."