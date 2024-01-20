#!/bin/sh
#
# Helper script used to flash boot media. This script is for SD cards in raspbery Pis and works on my mac. I haven't 
# tested is elsewhere.

# USAGE: ./flash.sh <HOSTNAME> <DEVICE> [ARCH] [VERSION]
# Where, hostname isn't the fqdn and device is just the last part - eg: 
# $  ./flash.sh betelguese disks2 arm64 21.10

set -e


TEMP=$(/usr/local/opt/gnu-getopt/bin/getopt -o 'f,d:,h:,v:' -l 'full,skipFlash,host:,device:,version:' \
              -n 'test.sh' -- "$@")


if [ $? != 0 ] ; then echo "Terminating..." >&2 ; exit 1 ; fi

# Note the quotes around '$TEMP': they are essential!
eval set -- "$TEMP"

version=
skipFlash=
hostname=
device=
full=

while true; do
  case "$1" in
    -v | --version ) version="$2"; shift 2 ;;
    -h | --host ) hostname="$2"; shift 2 ;;
    -d | --device ) device="$2"; shift 2 ;;
    --skipFlash ) skipFlash=true; shift ;;
    -f | --full ) full=true; shift ;;
    * ) break ;;
  esac
done


if [ -z $device ] || [ -z $hostname ]; then
    echo "Usage: ./flash.sh --host <HOSTNAME> --device <DEVICE> [--version <VERSION>] [--skipFlash]"
    exit 1;
fi;

if [ ! -e $device ]; then
    echo "No such device found: $device"
    exit 1;
fi;

if [ -z $version ]; then
    version='2023-12-11'
fi;


workdir=/tmp/homeops

mkdir -p $workdir/{images,mnt}/

if [ ! "$skipFlash" = true ]; then

    #Donwload image
    url="https://downloads.raspberrypi.com/raspios_lite_arm64/images/raspios_lite_arm64-$version/$version-raspios-bookworm-arm64-lite.img.xz"
    image="/tmp/homeops/images/raspios_arm64-lite.img"
    if [ "$full" = true  ]; then
        url="https://downloads.raspberrypi.com/raspios_arm64/images/raspios_arm64-$version/$version-raspios-bookworm-arm64.img.xz"
        image="/tmp/homeops/images/raspios_arm64.img"
    fi;
    
    if [ ! -f $image ]; then
        echo "Fetching image $url"
        curl $url --output $image.xz
    fi;

    echo "Decompressing image..."
    xz -d $image.xz
    
    # do the flashinng.
    echo "Flashing disk $device, with $image this may take a few minutes"

    /Applications/Raspberry\ Pi\ Imager.app/Contents/MacOS/rpi-imager --cli  $image $device

    echo "SSD flashed."
    sleep 10;

    echo "Please remove and re-insert SSD."
    while [ ! -e $device ]; do
        sleep 1;
    done
fi; 

# mount the disk
echo "Remounting disk $device to $workdir/mnt"
diskutil unmountDisk $device
diskutil mount -mountPoint $workdir/mnt ${device}s1 

# copy the configs and set the hostname
echo "Applying config"

cp ./config/* ${workdir}/mnt/
sed -i '' "s/NEW_HOSTNAME/${hostname}/g" $workdir/mnt/firstrun.sh

dec=$(sops -d ../vars.enc.yaml)
network_ssid=$(printf '%s' "$dec" | yq e ".network.ssid" -)
network_password=$(printf '%s' "$dec" | yq e ".network.psk" -)
user_password=$(printf '%s' "$dec" | yq e ".user-pass" -)


sed -i '' "s/NETWORK_SSID/${network_ssid}/g" $workdir/mnt/firstrun.sh
sed -i '' "s/NETWORK_PSK/${network_password}/g" $workdir/mnt/firstrun.sh
sed -i '' "s/USER_PASSWORD/${user_password}/g" $workdir/mnt/firstrun.sh

# unmount the disk, so we can boot a pi. 
diskutil unmountDisk $device
echo "Disk imaged, you can remove the card."