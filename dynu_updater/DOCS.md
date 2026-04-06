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

**Dynu API Key** (required) is generated in the Dynu Control Panel.

**IP Update**
	**Dynu Update Passwrod** (required) is either the Dynu account password, or the IP Update Password - if one has been created for the account.

	**IP Update Hostnames** This is a list of hostnames to update IP addresses for. eg yourdomain.com, mx.yourdomain.com. These must match domain records created in the account. You can use *.yourdomain.com to update all domains for the account.

**Certificate**
	**Certificate Email Address** is the email address used by Certbot when generating the certificate. eg admin@yourdomain.com.

	**Certificate Hostnames** This is a list of hostnames to add to the certificate. eg yourdomain.com, mx.yourdomain.com. Any valid hostname for the account can be added. Wildcards are supported eg *.yourdomain.com, *.api.yourdomain.com. Wildcards do not add the base domain, this must be added separately.

	**Renew Days** This is the number of days before a certificate is due to expire, to generate the new Certificate.

	The file names for **Private Key File** and **Certificate File** can be changed as required. These files are copied to the ssl directory for use by other addons/integrations.
