
###Links
RHEL Kickstart based automated installation 
https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/6/html/installation_guide/sn-automating-installation

Python flask documentation:
https://flask.palletsprojects.com/en/1.1.x/


###Steps to Create Image File
####Create Empty Image
```
dd if=/dev/zero of=ks.img bs=1M count=0 seek=10
```
####Create Partition using fdisk (bootable partition, partition types to e(W95 FAT16 (LBA))
```
fdisk ks.img
n t a 
```
####Create device map from partition
```
kpartx -av ks.img
```
####Format using mkfs.fat
```
sudo mkfs.fat  /dev/mapper/loop0p1
```
####Close Partition device map
```
kpartx -d ks.img
```
####Copy ks.cfg file to partition
```kpartx -av ks.img
mount /dev/mapper/loop0p1 /tmp/temp_ks/
cp ks.cfg /tmp/temp_ks/
umount /tmp/temp_ks
kpartx -d ks.img
```

###Steps to Modify Image File
####Copy modified ks.cfg file to existing image file
```
kpartx -av ks.img
mount /dev/mapper/loop0p1 /tmp/temp_ks/
cp ks.cfg /tmp/temp_ks/
umount /tmp/temp_ks
kpartx -d ks.img
```
