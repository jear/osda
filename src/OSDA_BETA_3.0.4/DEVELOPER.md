## Setting up the development environment for OSDA:

### Pre-requisites for tool installation:
**Operating System:**
* Centos 7.6/7.7 or RHEL 7.6/7.7

**Software packages:**
* Python v3.6
* Pip 19.0.3
* Node JS v10.16.0
* NPM v6.9.0
* Apache Webserver (httpd service) v2.4.6
* kpartx v0.4.9
* genisoimage v1.1.11
* openssl v1.0.2k-fips


**Get the sources**

```
git clone https://github.hpe.com/govind-avireddi/OSDA.git
```

**Install Node modules for Web UI**
```
cd OSDA/walkman-ui
npm install
```
**Run OSDA Web UI in development mode**
```
cd OSDA/walkman-ui
npm run dev
```

ESXi 7 Kickstart documentation:
https://docs.vmware.com/en/VMware-vSphere/7.0/com.vmware.esxi.install.doc/GUID-61A14EBB-5CF3-43EE-87EF-DB8EC6D83698.html
