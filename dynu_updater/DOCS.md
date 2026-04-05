# Dynu Domain Update Tool

## Installation

Follow these steps to get the app installed on your system:

1. In Home Assistant, go to **Settings** > **Apps** > **Install app**.
2. Find the "Dynu Domain Update Tool" app and click it.
3. Click on the "INSTALL" button.

## How to use

The app can be configured via the interface.
The configuration via YAML is also possible, see the examples below.

Navigate in your Home Assistant frontend to the apps overview page at
**Settings** > **Apps**, and pick the **Dynu Domain Update Tool** app. On the top,
pick the **Configuration** page.

**Dynu Hostname** (required) is the primary domain registerd at dynu.com. eg yourdomain.com.

**Dynu Update Passwrod** (required) is either the Dynu account password, or the IP Update Password - if one has been created for the account.

**Dynu API Key** (required) is generated in the Dynu Control Panel and is required by Certbot to generate the certificate.

**Domain Email** is the email address used by Certbot when generating the certificate eg admin@yourdomain.com.

**DNS Update Hostnames** This is a list of hostnames to update IP addresses for. eg yourdomain.com, mx.yourdomain.com.

**Certificate Hostnames** This is a list of hostnames to add to the certificate. eg yourdomain.com, mx.yourdomain.com, *.yourdomain.com.

The file names for **Private Key File** and **Certificate File** can be changed if required.
