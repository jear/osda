#!/bin/bash

installRHEL () {
echo Install on RHEL or Centos
cp -rf web-files/dist/* /var/www/html

cp /etc/httpd/conf/httpd.conf /etc/httpd/conf/httpd.conf_org
cp web-files/httpd.conf /etc/httpd/conf/
firewall-cmd --zone=public --permanent --add-port=5000/tcp
firewall-cmd --zone=public --permanent --add-port=80/tcp
firewall-cmd --reload
systemctl restart firewalld
systemctl restart httpd.service
}

installSLES () {
echo Install on SLES
cp -rf web-files/dist/* /srv/www/htdocs
cp web-files/osda_sles.conf /etc/apache2/vhosts.d
firewall-cmd --zone=public --permanent --add-port=5000/tcp
firewall-cmd --zone=public --permanent --add-port=80/tcp
firewall-cmd --reload
systemctl restart firewalld
systemctl enable apache2
systemctl restart apache2
}

r=$(cat /etc/*release)
releaseInfo=($(echo $r | tr "\" " "\n"))  

#for i in "${releaseInfo[@]}"; do
#    v="${i##*=}"
    #echo $v
if [[ $r == *"sles"* ]]; then
    installSLES
elif [[ $r == *"centos"* ]] || [[ $r == *"Centos"* ]] || [[ $r == *"rhel"* ]]; then	
    installRHEL
fi
#done