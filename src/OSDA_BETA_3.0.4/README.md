# HPE OSDA
OSDA is being developed with goal to simplify OS deployment automation on multiple HPE server products (Synergy, DL, Apollo) using simple REST API interface as well as Web-UI interface. It simplifies OS deployment process by eliminating need for PXE networking and complex OS deployment plans. Utilizes HPE iLO Virtual Media feature for presenting OS installation media to the server and performs the OS installation in unattended mode.
Designed to support multiple operating systems for deployment. 
The REST API enables the tool to easily integrate with O&M tools such as Ansible, Puppet, Terraform etc. and becomes important building block for implementing end-to-end automation for large scale deployments of HPE servers.


## Key Features
* Can deploy multiple operating systems and Hypervisors (SLES 15, ESXi 6.x, ESXi 7.0, RHEL 7.x and CentOS 7.x) 
* Supports HPE Synergy Gen10 blades with HPE Synergy Composer 5.0 or later
* Supports multiple HPE hardware products with iLO 5 (DL Gen10 servers and Apollo Gen10 servers).
* Supports Proliant DL Gen9 servers for iLO 4 based deployment
* The tool can be used in three modes:
  * Grommet Web Client UI for interactive use
  * REST API for scripting the tool operations
  * Python module 
* Supports UEFI boot mode
* Installs OS to the logical RAID volume created with local drives
* Create logical RAID drive for OS volume for iLO based deployment of OS
* Modifies the boot-order to boot from the OS drive
* Supports Static IP assignment for the installed hosts.
* Interfaces with HPE OneView 5 and later for deployment on Synergy servers
* Interfaces with HPE iLO 5 for deployment on DL and Apollo servers.
* Interfaces with HPE iLO 4 (iLO version 2.30) for deployment on Gen9 DL.
* Examples included for Python scripts and Ansible playbooks based OS deployment.
* Supports user defined custom kickstart files for customized OS installation.
* SSH Keys for passwordless SSH access to deployed hosts.
* Dual NIC support for network configuration (with NIC bonding implemented in the custom kickstart)
* Supports configuring 2 networks on the host OS

**Note:** _SLES SP1 operating system installation ISO media should include Autoyast packages along with additional required packages. This requires generating of ISO with required packages included. Please refer to the User Guide document for steps for creating the SLES ISO file._

## Ecosystem Projects
* Ansible playbooks for VMWare VCF deployment automation ( https://github.hpe.com/GSE/osda-ansible-vcf ).
* Ansible playbooks for deploying WEKA.IO on Apollo and Proliant DL servers ( https://github.hpe.com/GSE/osda-ansible-weka ).

## Supported Hardware Products
HPE Synergy Gen10 servers
HPE Proliant DL Gen10 servers
HPE Apollo Gen10 servers
HPE Proliant DL Gen9 servers

## Supported Operating Systems and Hypervisors
* SUSE Linux Enterprise Server 15
* VMWare ESXi 6.5/6.7/7.0
* RHEL 7.6/7.7
* CentOS 7.6/7.7
* SLES

## Installation 

The software for HPE OSDA is available as installable package. 
After the installation it runs as Systemd serverice with service name **osda**.

### Pre-requisites

CentOS 7.x, RHEL 7.x, or SLES15 VM with 8 VCPUs and 8GB or more.

#### Pre-requisites packages for SLES15 host
- mkisofs
- xorriso
- kpartx 
- python3-setuptools
- apache2
- python3

**Software packages:**
* Python v3.6
* Pip 19.0.3
* Apache Webserver (httpd service) v2.4.6
* kpartx v0.4.9
* genisoimage v1.1.11
* openssl v1.0.2k-fips

#### Storage
50 GB or more. Storage requirement for OS image ISO files.

#### Ports to be allowed by Firewall
5000 – Incoming traffic on this port for HPEOSDA server side component
80 – Web-UI and HTTP File server


### Setup
The installation can be performed using the following steps:

1. Download/Extract the OSDA.tar or git clone the OSDA repository to the local directory in the CentOS/RHEL host. This will be install directory for the tool.

2. Initialize and install the python code by running the following command.

``` python setup.py install ```

Note: This module depends on Python3. If the default interpreter is not python3, perform the setup tasks using python3. If osda should be installed only for currently running user, use --user option.

``` python3 setup.py install ```

This command installs all the required pre-requisites from requirements.txt, creates the directory hierarchy and enables OSDA as a systemd service.

### Configuration

1. If the setup is successful, the following directories are created.

| Directory | Description |
| ---------:|:-----------:|
| /opt/hpe/osda      |  Default path for all OSDA related files
| /opt/hpe/osda/etc  |  Configuration files of OSDA
| /opt/hpe/osda/lib  |  All python libraries related to OSDA
| /opt/hpe/osda/bin  |  Binaries of OSDA
| /opt/hpe/osda/data |  All data files of OSDA – This would include all the kickstarts, osimages, etc.,
| /opt/hpe/osda/log  |  Logging files for OSDA
| \<Python site-packages\>/osda_server-\<release\>.egg  |  OSDA Python module

2. Edit the configuration in the following path `/opt/hpe/osda/etc/config.ini`

| Parameter | Default    |   Description  |
| ---------:|:----------:|:----------:|
| server    | **Mandatory**  | **IP address of the OSDA server (Mandatory)**
| port      |   5000     | Port to run the REST API server on the OSDA server
| log_path  | /opt/hpe/osda/log | Path for the OSDA log directory
| log_level | INFO       | Log level

### Service

**IMP: Ensure OSDA server IP address is updated in the configuration file `/opt/hpe/osda/etc/config.ini`. **
**This IP address setting is essential for OSDA functionality.**

1. Load the OSDA service by reloading the systemd

`systemctl daemon-reload`

2. Start the osda server using systemd service

`systemctl start osda.service`

The OSDA server backend will be started on server address and host specified in the config file

### Install OSDA Web Client

Run the below command to install and configure web server:

``` ./configureWeb.sh ```

**IMP: The above script can install the Web Client only on Apache HTTPD server running local to machine where OSDA service is running**

Now the tool should be ready. To access the Web-UI from browser, use the url http://<host-IP-address>/ where “host-IP address in the IP address of the host that is running the HPE OSDA tool.



## Limitations and known issues

| S.No| Limitation/Known issue                         | Remarks                             |
|--------|------------------------------------------------|-------------------------------------|
| 1   | Gen9 support is not available for Synergy blades	|  |
| 2   | With “secure boot” enabled in BIOS, SSH service will not be enabled by default for hosted deployed with ESXi| This is limitation by VMWare ESXi kickstart. Investigating a work-around.|
| 3   | Bulk deployment using JSON is disabled in the UI         | This feature is not enabled as enough testing not done|
| 4   | Legacy BIOS is not supported         | This support can be added on request |
| 5   | DHCP option not selectable | This feature will be enabled in next version|
| 6 | Web-UI doesn’t show error messages when any operation is failed on the server side. | Work in progress |
| 7 | Setup script shows error message “Could not find a version that satisfies the requirement Click==7.0” | Ignore this error.| 


