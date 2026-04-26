# Dynu Tools

## Installation

Follow these steps to get the app installed on your system:

1. In Home Assistant, go to **Settings** > **Apps** > **Install app**.
2. Find the "Dynu Tools" app and click it.
3. Click on the "INSTALL" button.

## How to use

Navigate in your Home Assistant frontend to the apps overview page at
**Settings** > **Apps**, and pick the **Dynu Tools** app. On the top,
pick the **Configuration** page.

- **MQTT Settings**
  - **Core** If this is enabled, the app will use the Default Mosquitto Broker app.
  - **Host** This is the hostname/ip address of the MQTT server. If you enabled **Core**, this can be left blank.
  - **Port** Set this to the port for you MQTT server. If you enabled **Core**, this can be left blank.
  - **User** This is the username for the MQTT server. If you enabled **Core**, this can be left blank.
  - **Password** This is the password for the MQTT server. If you enabled **Core**, this can be left blank.
  - **TLS** If enabled, MQTT will connect using a secured connection.
  - **Validate Server Certificate** If enabled, the app will verify the MQTT server certificate is valid for the **Host**.
  - **Private Key File**, **Certificate File**, and **CA File** may be required for the TLS connection, depending on how the MQTT server has been configured. These are not required if the MQTT server is using a SSL certificate provided by this app.

Once the **Dynu Tools** app is running, click **Open Web UI** and enter the **API Key**, **IP Update Password**, **Email Address**, and then click **Save Settings**.
The Dynu API will then load all of the domains from the account. Each hostname has 3 checkboxes. **Update IPv4**, **Update IPv6** and **Certificate**.
If **Update IPv4** is checked, the IPv4 address for this hostname will be updated.
If **Update IPv46** is checked, the IPv6 address for this hostname will be updated. If either the host doesn't support IPv6 or, IPv6 is not enabled for the domain, this will be disabled.
If **Certificate** is checked, this hostname will be included in the certificate request.

Custom hostnames can be added for the certificate request, including wildcards. Hostnames which would be covered by a wildcard, are automatically ignored (Checkbox check removed and disabled). If you specify \*.yourdomain.com and sub.yourdomain.com, then sub.yourdomain.com is not added to the certificate. Duplicate hostnames are also ignored.

The IP Updater service will check and update the IP address of all hostnames with a check in **Update IPv4** or **Update IPv6**.

Current IP adrresses are resolved using external calls. Dynu is used as the primary external source, with Icanhazip as a backup. If no IP addresses can be resolved, the update process will automatically try again in 1 minute. If either an IPv4 or IPv6 address is resolved and found to have changed since the last update, an update request will be performed.
If an IPv4 address is resolved, but not an IPv6 address, only IPv4 hosts will be updated. If an IPv6 address is resolved, but not an IPv4 address, only IPv6 hosts will be updated. If both IPv4 and IPv6 addresses are resolved, all hosts are updated.

The Certificate Manager will create a SSL certificate for all the hostnames with a check in **Certificate**.
Up to 100 hostnames can be added to the certificate.

If an MQTT connection is established, various sensors and controls are created in the MQTT integration under the dynu_tools device. The sensors are self-explanatory. The controls enable forcing an IP update and forcing the renewal of a certificate.
**Force IP Update** can only be ran once every minute. **Force Certificate Update** can only be ran once every hour. Other attempts to run will generate a warning in the app logs.

## Events
The app will publish events on the Home Assistant Event Bus. All events are published to 'dynu_tools'. The following lists the possible events:
```JSON
{"event_type": "dynu_tools.ip_update", "data": {"status": "updated", "ipv4": "--New IPv4 Address--", "ipv6": "--New IPv6 Address--"}}
{"event_type": "dynu_tools.ip_update", "data": {"status": "no_change", "ipv4": "--Current IPv4 Address--", "ipv6": "--Current IPv6 Address--"}}
{"event_type": "dynu_tools.ip_update", "data": {"status": "fail"}}

{"event_type": "dynu_tools.certificate_update", "data": {"status": "updated", "created": "--New Certificate Creation Date--", "expires": "--New Certificate Expiry Date--"}}
{"event_type": "dynu_tools.certificate_update", "data": {"status": "no_change", "created": "--Current Certificate Creation Date--", "expires": "--Current Certificate Expiry Date--"}}
{"event_type": "dynu_tools.certificate_update", "data": {"status": "fail"}}
```
All dates are published in ISO Format

## Example YAML Configuration
```yaml
mqtt:
  core: false
  host: my-mqtt-server
  port: 1883
  username: USERNAME
  password: PASSWORD
  ssl: false
  server_cert: false
log_level: info
```