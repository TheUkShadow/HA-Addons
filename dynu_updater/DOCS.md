# Dynu Domain Update Tool

## Installation

Follow these steps to get the app installed on your system:

1. In Home Assistant, go to **Settings** > **Apps** > **Install app**.
2. Find the "Dynu Domain Update Tool" app and click it.
3. Click on the "INSTALL" button.

## How to use

The app can be configured via the interface.
The configuration via YAML is also possible, see the example below.

Navigate in your Home Assistant frontend to the apps overview page at
**Settings** > **Apps**, and pick the **Dynu Domain Update Tool** app. On the top,
pick the **Configuration** page.

At least one of **Update IP Addresses** or **Generate Certificate** options must be enabled.

- **Dynu Hostname** (required) is the primary domain registerd at dynu.com. eg yourdomain.com.
- **Dynu API Key** (required) is generated in the Dynu Control Panel under API Credentials.
- **Events** If enabled, the app will generate Events on the Home Assistant Event Bus.

- **IP Updater Options**
  - **Update IP Addresses** If enabled, the app will update the IP addresses for any hosts listed in **IP Update Hostnames**.
  - **Update Interval** This is the number of minutes to wait between each IP address check. If an IP address check or update fails, it will retry after 1 minute.
  - **Disable IPv6** If enabled, this will prevent the app from trying to resolve the server IPv6 address and updating any AAAA records in the Dynu account.
  - **Dynu Update Passwrod** (required) is either the Dynu account password, or the IP Update Password - if one has been created for the account.
  - **IP Update Hostnames** This is a list of hostnames to update IP addresses for. eg yourdomain.com, mx.yourdomain.com. These must match domain records created in the account. You can use *.yourdomain.com to update all hostnames for the account.

- **Certificate Options**
  - **Generate Certificate** If enabled, the app will generate a SSL certificate for all hosts listed in **Certificate Hostnames**
  - **Certificate Email Address** is the email address used by Certbot when generating the certificate. eg admin@yourdomain.com.
  - **Certificate Hostnames** This is a list of hostnames to add to the certificate. eg yourdomain.com, mx.yourdomain.com. Any valid hostname for the account can be added. Wildcards are supported.
  - **Renew Days** This is the number of days before a certificate is due to expire, to generate the new Certificate. If a certificate check or renewal fails, it will retry after 10 minutes.
  - **Private Key File** and **Certificate File** can be changed as required. These files are copied to the ssl directory for use by other addons/integrations.
  - **Force Renew** If enabled, this will cause the Certificate Manager to try and renew the current certificate on the first check.
  - **Test Run** If enabled, this will prevent the Certificate Manager from generating/renewing certificats on the first run.
	
- **MQTT Options**
  - **Enabled** This enables MQTT and the app will create a Device with Entities in the MQTT integration.
  - **Core** If this is enabled, the app will use the username and password supplied by the Default Mosquitto Broker app.
  - **Host** (required) This is the hostname/ip address of the MQTT server. Set this to core-mosquitto if you have the Default Mosquitto Broker app installed.
  - **Port** (required) Set this to the port for you MQTT server. This is usually 1883 for standard connections, or 8883 if using TLS.
  - **User** This is the username for the MQTT server. If you enabled **Core**, this can be left blank.
  - **Password** This is the password for the MQTT server. If you enabled **Core**, this can be left blank.
  - **TLS** If enabled, MQTT will connect using a secured connection. Ensure you change the **Port** accordingly.
  - **Validate Server Certificate** If enabled, the app will verify the MQTT server certificate is valid for the **Host**.
  - **Private Key File**, **Certificate File**, and **CA File** may be required for the TLS connection, depending on how the MQTT server has been configured. These are not required if the MQTT server is using a SSL certificate provided by this app.

All options are checked before the main services run. If any options are found to be invalid, an error message is logged and the app stopped. Do not enable the Watchdog option, until the app has successfully run once.

By default, the IP Updater service will check and update the IP address of all hostnames in **IP Update Hostnames**. If IPv6 is enabled in the Dynu control panel and AAAA records exist in the domain, then the service will update both IPv4 and IPv6 addresses.
IPv6 can be disabled manually in the Configuration using **Disable IPv6**.
If you want to update the IP address for every A/AAAA record in the Dynu domain, add a single hostname to **IP Update Hostnames** with \*.yourdomain.com.

The Certificate Manager will create an SSL certificate for all the hostnames in **Certificate Hostnames**. These must be valid for your Dynu domain or an error is raised.
Wildcards are supported (\*.yourdomain.com or \*.sub.yourdomain.com). The primary domain (yourdomain.com) is not automatically included and must be added to the list of hostnames, if required.
Up to 100 hostnames can be added to the certificate.
Hostnames which would be covered by a wildcard, are automatically ignored. If you specify \*.yourdomain.com and sub.yourdomain.com, then sub.yourdomain.com is not added to the certificate. Duplicate hostnames are also ignored.

## Events
If **Events** are enabled, the app will publish events on the Home Assistant Event Bus. All events are published to 'dynu_updater'. The following JSON lists the possible events:
```JSON
{"event_type": "dynu_updater", "data": {"action": "ip_update", "status": "updated", "info": {"ipv4": "--New IPv4 Address--", "ipv6": "--New IPv6 Address--"}}}
{"event_type": "dynu_updater", "data": {"action": "ip_update", "status": "no_change", "info": {"ipv4": "--Current IPv4 Address--", "ipv6": "--Current IPv6 Address--"}}}
{"event_type": "dynu_updater", "data": {"action": "ip_update", "status": "fail"}}

{"event_type": "dynu_updater", "data": {"action": "certificate_update", "status": "updated", "info": {"created": "--Certificate Creation Date--", "expires": "--Certificate Expiry Date--"}}}
{"event_type": "dynu_updater", "data": {"action": "certificate_update", "status": "no_change", "info": {"created": "--Certificate Creation Date--", "expires": "--Certificate Expiry Date--"}}}
{"event_type": "dynu_updater", "data": {"action": "certificate_update", "status": "fail"}}
```
All dates are published in ISO Format

## Example YAML Configuration
```yaml
dns:
  update_ip: true
  update_interval: 1
  disable_ipv6: false
  dynu_update_password: DYNU_PASSWORD
  domains:
    - "*.yourdomain.com"
cert:
  update_cert: true
  keyfile: privkey.pem
  certfile: fullchain.pem
  update_cert_days: 5
  force_renew: false
  dry_run: false
  email: admin@yourdomain.com
  domains:
    - yourdomain.com
    - homeassistant.yourdomain.com
    - mx.yourdomain.com
	- "*.api.yourdomain.com"
mqtt:
  enabled: true
  core: true
  host: core-mosquitto
  port: 1883
  tls: false
  server_cert: false
events: true
log_level: info
dynu_hostname: yourdomain.com
dynu_api_key: DYNU_API_KEY
```