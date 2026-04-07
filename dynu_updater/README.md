# Dynu Domain Update Tool

This app can update IP addresses and create a SSL certificate for a domain registered at dynu.com.

Uses Let's Encrypt to create and update the certificate, and Dynu's API to update dynamic DNS records.

By default, the IP updater checks the current IP address every minute. If a change is detected, all configured hostnames are updated. The time between checks is adjustable from 1 minute to 60 minutes.

The Certificate Manager will automatically renew the certiifcate before the old one expires.

![Supports aarch64 Architecture][aarch64-shield] ![Supports amd64 Architecture][amd64-shield]

The generated certificate can be used by other addons and integrations.

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
