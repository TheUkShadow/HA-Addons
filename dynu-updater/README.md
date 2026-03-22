# Dynu Domain Update Tool

This tool allows Dynamic DNS updates and SSL certificates to be generated for domians registered with dynu.com.

Uses Let's Encrypt to create and update certificates and Dynu's API to update dynamic DNS records.

The certificate generation/renewal check runs each day at 00:00. The DNS update check runs every 60 seconds.

![Supports aarch64 Architecture][aarch64-shield] ![Supports amd64 Architecture][amd64-shield]

The generated certificate can be used within others addons. By default the path and file for the certificates within other addons will refer to the files generated within this addon.

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
