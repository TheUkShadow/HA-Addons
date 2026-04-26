import json
import re
import os
import time
import copy
import shutil
import requests
import logging
import signal
import socket
import requests.packages.urllib3.util.connection as urllib3_cn
import threading
import subprocess
import paho.mqtt.client as mqtt
from pathlib import Path
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder="www") 

with open("/data/options.json", "r") as f:
    ADDON_CONFIG = json.load(f)
        
SETTINGS_FILE = "/data/settings.json"
DOMAINS_FILE = "/data/domains.json"
IP_STATUS_FILE = "/data/ip_status.json"

FORCE_IP = {"force": False, "last": 0}
FORCE_CERT = {"force": False, "last": 0}
FORCE_RENEW = False
DRY_RUN = False
IPV6_OK = False

MQTT_CLIENT = mqtt.Client(client_id = os.getenv("HOSTNAME"))

LOG_LEVEL = ADDON_CONFIG.get("log_level", "info")

STOP_EVENT = threading.Event()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s"
)

MQTT_ENTITIES={
    "force_ip_update": {
        "name": "Perform IP Update",
        "command_topic": "dynu_tools/service/force_ip_update",
        "component": "button",
        "icon": "mdi:play-network",
        "service": "dns"
    },
    "last_ip_check": {
        "name": "Last IP Check",
        "device_class": "timestamp",
        "state_topic": "dynu_tools/last_ip_check",
        "component": "sensor",
        "icon": "mdi:clock-check",
        "service": "dns"
    },
    "next_ip_check": {
        "name": "Next IP Check",
        "device_class": "timestamp",
        "state_topic": "dynu_tools/next_ip_check",
        "component": "sensor",
        "icon": "mdi:calendar-clock-outline",
        "service": "dns"
    },
    "last_ip_update": {
        "name": "Last IP Update",
        "device_class": "timestamp",
        "state_topic": "dynu_tools/last_ip_update",
        "component": "sensor",
        "icon": "mdi:update",
        "service": "dns"
    },
    "current_ipv4": {
        "name": "Current IPv4",
        "state_topic": "dynu_tools/current_ipv4",
        "component": "sensor",
        "icon": "mdi:ip-network",
        "service": "dns"
    },
    "current_ipv6": {
        "name": "Current IPv6",
        "state_topic": "dynu_tools/current_ipv6",
        "component": "sensor",
        "icon": "mdi:ip-network-outline",
        "service": "dns"
    },
    "ip_update_status": {
        "name": "IP Update Status",
        "device_class": "problem",
        "state_topic": "dynu_tools/ip_update_status",
        "component": "binary_sensor",
        "payload_on": "false",
        "payload_off": "true",
        "icon": "mdi:sticker-check",
        "service": "dns"
    },
    "force_cert_update": {
        "name": "Perform Certificate Update",
        "command_topic": "dynu_tools/service/force_cert_update",
        "component": "button",
        "icon": "mdi:archive-check-outline",
        "service": "cert"
    },
    "next_cert_check": {
        "name": "Next Certificate Check",
        "device_class": "timestamp",
        "state_topic": "dynu_tools/next_cert_check",
        "component": "sensor",
        "icon": "mdi:calendar-clock",
        "service": "cert"
    },
    "last_cert_check": {
        "name": "Last Certificate Check",
        "device_class": "timestamp",
        "state_topic": "dynu_tools/last_cert_check",
        "component": "sensor",
        "icon": "mdi:certificate-outline",
        "service": "cert"
    },
    "cert_valid": {
        "name": "Certificate Valid",
        "device_class": "problem",
        "state_topic": "dynu_tools/cert_valid",
        "component": "binary_sensor",
        "payload_on": "false",
        "payload_off": "true",
        "icon": "mdi:shield-check",
        "service": "cert"
    },
    "cert_update_status": {
        "name": "Certificate Update Status",
        "device_class": "problem",
        "state_topic": "dynu_tools/cert_update_status",
        "component": "binary_sensor",
        "payload_on": "false",
        "payload_off": "true",
        "icon": "mdi:shield-alert",
        "service": "cert"
    },
    "cert_expires": {
        "name": "Certificate Expires",
        "device_class": "timestamp",
        "state_topic": "dynu_tools/cert_expires",
        "component": "sensor",
        "icon": "mdi:calendar-alert",
        "service": "cert"
    },
    "cert_created": {
        "name": "Certificate Created",
        "device_class": "timestamp",
        "state_topic": "dynu_tools/cert_created",
        "component": "sensor",
        "icon": "mdi:certificate",
        "service": "cert"
    }
}

IP_REGEX = {}
IP_REGEX[socket.AF_INET] = re.compile(r'^([0-9]{1,3}\.){3}[0-9]{1,3}$')
IP_REGEX[socket.AF_INET6] = re.compile(
    r'^((([0-9A-Fa-f]{1,4}:){7}[0-9A-Fa-f]{1,4})|'
    r'(([0-9A-Fa-f]{1,4}:){1,7}:)|'
    r'(([0-9A-Fa-f]{1,4}:){1,6}:[0-9A-Fa-f]{1,4})|'
    r'(([0-9A-Fa-f]{1,4}:){1,5}(:[0-9A-Fa-f]{1,4}){1,2})|'
    r'(([0-9A-Fa-f]{1,4}:){1,4}(:[0-9A-Fa-f]{1,4}){1,3})|'
    r'(([0-9A-Fa-f]{1,4}:){1,3}(:[0-9A-Fa-f]{1,4}){1,4})|'
    r'(([0-9A-Fa-f]{1,4}:){1,2}(:[0-9A-Fa-f]{1,4}){1,5})|'
    r'([0-9A-Fa-f]{1,4}(:([0-9A-Fa-f]{1,4}:){1,6}))|'
    r'(:((:[0-9A-Fa-f]{1,4}){1,7}|:))|'
    r'(([0-9A-Fa-f]{1,4}:){1,4}'
    r'((25[0-5]|2[0-4][0-9]|[01]?[0-9]?[0-9])\.){3}'
    r'(25[0-5]|2[0-4][0-9]|[01]?[0-9]?[0-9])))$'
)

# -----------------------------
# Helpers
# -----------------------------

def load_json(path, default):
    logging.debug(f"Dynu Tools - Loading JSON. path = {path}, default = {default}")
    if not os.path.exists(path):
        return default
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    logging.debug(f"Dynu Tools - Saving JSON. path = {path}, data = {data}")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def load_settings():
    logging.debug("Dynu Tools - Loading Settings")
    return load_json(SETTINGS_FILE, {
        "api_key": "",
        "email": "",
        "password": ""
    })

def save_settings(data):
    logging.debug("Dynu Tools - Saving Settings")
    save_json(SETTINGS_FILE, data)

def load_domains():
    logging.debug("Dynu Tools - Loading Domains")
    return load_json(DOMAINS_FILE, {"domains": {}})

def save_domains(data):
    logging.debug("Dynu Tools - Saving Domains")
    save_json(DOMAINS_FILE, data)

def load_ip_status():
    logging.debug("Dynu Tools - Loading IP Status")
    return load_json(IP_STATUS_FILE, {"ipv4": None, "ipv6": None, "last": 0})
    
def save_ip_status(data):
    logging.debug("Dynu Tools - Saving IP Status")
    save_json(IP_STATUS_FILE, data)

def setup_mqtt():
    logging.debug("Dynu Tools - Starting MQTT Setup")
    
    if ADDON_CONFIG.get("mqtt", {}).get("core", False):
        core_mqtt = False
        try:
            r = requests.get("http://supervisor/services", headers={"Authorization": f"Bearer {os.getenv("SUPERVISOR_TOKEN")}"}, timeout=5)
            r.raise_for_status()
            
            services = r.json().get("data", {}).get("services", {})
            
            for svc in services:
                if svc.get("slug") == "mqtt" and svc.get("available") and "core_mosquitto" in svc.get("providers"):
                    core_mqtt = True
                    break
                    
        except Exception as e:
            logging.error(f"Dynu Tools - Unable to query Supervisor API for services: {e}")
            core_mqtt = False
                
        if core_mqtt:
            try:
                r = requests.get("http://supervisor/services/mqtt", headers={"Authorization": f"Bearer {os.getenv("SUPERVISOR_TOKEN")}"}, timeout=5)
                r.raise_for_status()
                
                MQTT_CONFIG = r.json().get("data", {})

            except Exception as e:
                logging.error(f"Dynu Tools - Unable to query Supervisor API for core_mosquitto: {e}")
                MQTT_CONFIG = ADDON_CONFIG.get("mqtt", {})
            
    else:
        MQTT_CONFIG = ADDON_CONFIG.get("mqtt", {})

    logging.debug(f"Dynu Tools - MQTT Config: {MQTT_CONFIG}")
    
    if MQTT_CONFIG.get("host", "") and MQTT_CONFIG.get("port", ""):        
        
        def register_entities():
            logging.info("Dynu Tools - Registering MQTT Entities")
            device_id=f"dynu_tools_{os.getenv("HOSTNAME")}"
            device_name="Dynu Tools"
            manufacturer="TheUkShadow"
            model="Dynu Tools"
            sw_version=os.getenv("ADDON_VERSION")
            avail_topic="dynu_tools/availability"
            
            copy_entities = copy.deepcopy(MQTT_ENTITIES)
            
            for entity_id, entity_data in copy_entities.items():
                logging.debug(f"Dynu Tools - Registering entity {entity_id}")
                
                entity_avail_topic=f"dynu_tools/{entity_id}/availability"
                
                entity_data["unique_id"] = f"{device_id}_{entity_id}"
                entity_data["availability"] = [
                    { "topic": avail_topic },
                    { "topic": entity_avail_topic }
                ]
                entity_data["payload_available"] = "online"
                entity_data["payload_not_available"] = "offline"
                entity_data["device"] = {
                    "identifiers": [device_id],
                    "name": device_name,
                    "manufacturer": manufacturer,
                    "model": model,
                    "sw_version": sw_version
                }
                
                entity_data.pop("service", None)
                
                component = entity_data.get("component")
                entity_data.pop("component", None)
                
                publish_mqtt(f"homeassistant/{component}/{entity_id}/config", json.dumps(entity_data))
                
            publish_mqtt("dynu_tools/availability", "online")
        
        def on_connect(MQTT_CLIENT, userdata, flags, rc):
            match rc:
                case 0:
                    logging.info(f"Dynu Tools - MQTT connected to {MQTT_CONFIG.get("host", "")}")
                    MQTT_CLIENT.subscribe("dynu_tools/service/#")
                case 1:
                    logging.error("Dynu Tools - MQTT connection failed: incorrect protocol version")
                case 2:
                    logging.error("Dynu Tools - MQTT connection failed: invalid client identifier")
                case 3:
                    logging.error("Dynu Tools - MQTT connection failed: server unavailable")
                case 4:
                    logging.error("Dynu Tools - MQTT connection failed: bad username or password")
                case 5:
                    logging.error("Dynu Tools - MQTT connection failed: not authorised")
                case _:
                    logging.error("Dynu Tools - MQTT connection failed: unknown error")

        def on_message(MQTT_CLIENT, userdata, msg):
            global FORCE_IP
            global FORCE_CERT
            payload = msg.payload.decode()
            logging.debug(f"Dynu Tools - MQTT Message received: {msg.topic} → {payload}")
            if msg.topic == "dynu_tools/service/force_ip_update" and payload == "PRESS" and not FORCE_IP["force"] and time.time() - FORCE_IP["last"] > 60:
                FORCE_IP = {"force": True, "last": time.time()}
            elif msg.topic == "dynu_tools/service/force_ip_update" and payload == "PRESS" and not FORCE_IP["force"] and time.time() - FORCE_IP["last"] <= 60:
                logging.warning("Dynu Tools - Request for IP Update ignored")
            elif msg.topic == "dynu_tools/service/force_cert_update" and payload == "PRESS" and not FORCE_CERT["force"] and time.time() - FORCE_CERT["last"] > 3600:
                FORCE_CERT = {"force": True, "last": time.time()}
            elif msg.topic == "dynu_tools/service/force_cert_update" and payload == "PRESS" and not FORCE_CERT["force"] and time.time() - FORCE_CERT["last"] <= 3600:
                logging.warning("Dynu Tools - Request for Certificate Update ignored")
            
            
        if MQTT_CONFIG.get("ssl", False):
            MQTT_CLIENT.tls_set(
                ca_certs=ADDON_CONFIG.get("mqtt", {}).get("cafile", None),
                certfile=ADDON_CONFIG.get("mqtt", {}).get("certfile", None),
                keyfile=ADDON_CONFIG.get("mqtt", {}).get("keyfile", None)
            )
            MQTT_CLIENT.tls_insecure_set(ADDON_CONFIG.get("mqtt", {}).get("server_certificate", False) == False)
            
        try:
            logging.info("Dynu Tools - Starting MQTT Connection")
            MQTT_CLIENT.username_pw_set(
                username = MQTT_CONFIG.get("username", None),
                password = MQTT_CONFIG.get("password", None)
            )
            MQTT_CLIENT.on_connect = on_connect
            MQTT_CLIENT.on_message = on_message
            MQTT_CLIENT.connect(MQTT_CONFIG.get("host"), MQTT_CONFIG.get("port"))
            MQTT_CLIENT.loop_start()
        except Exception as e:
            logging.error(f"Dynu Tools - Unable to start MQTT connection: {e}")
        
        count = 0
        while not MQTT_CLIENT.is_connected() and count < 10:
            time.sleep(1)
            count += 1
        
        if MQTT_CLIENT.is_connected():        
            register_entities()
        else:
            logging.error("Dynu Tools - MQTT Connection timed out")
        
    else:
        logging.warning("Dynu Tools - Unable to create MQTT connection. No Config")

def publish_mqtt(topic, payload):
    if MQTT_CLIENT.is_connected():
        logging.debug(f"Dynu Tools - Publishing MQTT. topic = {topic}, payload = {payload}")
        MQTT_CLIENT.publish(topic=topic, payload=payload, qos=0, retain=True)
    else:
        logging.debug(f"Dynu Tools - Not Publishing MQTT. topic = {topic}, payload = {payload}. Not connected")
    
def publish_event(type, event):
    logging.debug(f"Dynu Tools - Publishing Event. type = {type}, event = {event}")
    requests.post(
        f"http://supervisor/core/api/events/dynu_tools.{type}",
        headers={"Authorization": f"Bearer {os.getenv("SUPERVISOR_TOKEN")}"},
        json=event
    )

def ipv6_capable():
    if not urllib3_cn.HAS_IPV6:
        logging.info("Dynu Tools - IPv6 Not available (urllib3)")
        return False

    try:
        socket.getaddrinfo("ipv6.google.com", 80, socket.AF_INET6)
    except socket.gaierror:
        logging.info("Dynu Tools - IPv6 Not available (DNS Error)")
        return False

    try:
        socket.create_connection(("ipv6.google.com", 80), timeout=2)
        logging.info("Dynu Tools - IPv6 available")
        return True
    except OSError:
        logging.info("Dynu Tools - IPv6 Not available (OS error)")
        return False

def fetch_domains_from_dynu(api_key):
    """Fetch domains + DNS records from Dynu API, including primary domain."""
    logging.debug(f"Dynu Tools - Fetching Domains from Dynu API. api_key = {api_key}")
    if not api_key:
        return {}
        
    try:
        root_resp = requests.get(
            "https://api.dynu.com/v2/dns",
            headers={"API-Key": api_key, "Content-Type": "application/json"}
        )
        root_resp.raise_for_status()
    except Exception as e:
        logging.error(f"Dynu Tools - Error while querying Dynu API: {e}")
        return {"error": e}

    domains = root_resp.json().get("domains", [])
    result = {}
    domain_sort = []

    existing = load_domains()

    for d in domains:
        domain_id = d["id"]
        domain_name = d["name"]
        
        domain_sort.append(domain_name)
        
        logging.debug(f"Dynu Tools - Dynu Domain API: {d}");

        # Primary domain IPv4/IPv6 come from the domain object
        primary_ipv4 = d.get("ipv4Address", "")
        primary_ipv6 = d.get("ipv6Address", "")
        primary_updated = d.get("updatedOn", "")
        ipv6_enabled = d.get("ipv6", False)
        ipv4_wildcard = d.get("ipv4WildcardAlias", False)
        ipv6_wildcard = d.get("ipv6WildcardAlias", False)

        # Initialize domain entry
        result[domain_name] = {
            "ipv6_enabled": ipv6_enabled,
            "ipv6_connection": IPV6_OK,
            "wildcards" : {"ipv4": ipv4_wildcard, "ipv6": ipv6_wildcard and ipv6_enabled},
            "records": {}
        }

        # Insert primary domain as a record
        result[domain_name]["records"][domain_name] = {
            "custom" : False,
            "wildcard" : False,
            "alias": "",
            "ipv4": primary_ipv4,
            "ipv6": primary_ipv6,
            "update_ipv4": existing.get("domains", {}).get(domain_name, {}).get("records", {}).get(domain_name, {}).get("update_ipv4", False),
            "update_ipv6": ipv6_enabled and IPV6_OK and existing.get("domains", {}).get(domain_name, {}).get("records", {}).get(domain_name, {}).get("update_ipv6", False),
            "certificate": existing.get("domains", {}).get(domain_name, {}).get("records", {}).get(domain_name, {}).get("certificate", False)
        }
        
        order = []
        order.append(domain_name)
        
        # Fetch DNS records
        try:
            rec_resp = requests.get(
                f"https://api.dynu.com/v2/dns/{domain_id}/record",
                headers={"API-Key": api_key, "Content-Type": "application/json"}
            )
            rec_resp.raise_for_status()
        except Exception as e:
            logging.error(f"Dynu Tools - Error while querying Dynu API: {e}")
            return {"error": e}

        records = rec_resp.json().get("dnsRecords", [])
        
        for r in records:
            
            logging.debug(f"Dynu Tools - Dynu Record API: {r}");
            
            fqdn = r.get("hostname", "")

            # Avoid overwriting primary domain record
            if not fqdn or fqdn == domain_name or r.get("recordType", "") not in ["A", "AAAA"]:
                continue
            
            if fqdn not in result[domain_name]["records"]:
                result[domain_name]["records"][fqdn] = {
                    "custom": False,
                    "wildcard": False,
                    "alias": r.get("nodeName", ""),
                    "ipv4": "",
                    "ipv6": "",
                    "update_ipv4": existing.get("domains", {}).get(domain_name, {}).get("records", {}).get(fqdn, {}).get("update_ipv4", False),
                    "update_ipv6": ipv6_enabled and IPV6_OK and existing.get("domains", {}).get(domain_name, {}).get("records", {}).get(fqdn, {}).get("update_ipv6", False),
                    "certificate": existing.get("domains", {}).get(domain_name, {}).get("records", {}).get(fqdn, {}).get("certificate", False)
                }
                order.append(fqdn)
            
            if r.get("recordType", "") == "A":
                result[domain_name]["records"][fqdn]["ipv4"] = r.get("ipv4Address", "")
            
            if r.get("recordType", "") == "AAAA":
                result[domain_name]["records"][fqdn]["ipv6"] = r.get("ipv6Address", "")
        
        for custom in existing.get("domains", {}).get(domain_name, {}).get("records", {}):
            if not existing.get("domains", {}).get(domain_name, {}).get("records", {}).get(custom, {}).get("custom", False):
                continue
            
            if custom not in result[domain_name]["records"]:
                result[domain_name]["records"][custom] = {
                    "custom": True,
                    "alias": "",
                    "ipv4": "",
                    "ipv6": "",
                    "update_ipv4": False,
                    "update_ipv6": False,
                    "certificate": existing.get("domains", {}).get(domain_name, {}).get("records", {}).get(custom, {}).get("certificate", False)
                }
                order.append(custom)

        result[domain_name]["sort_order"] = order
    
    return {"sort_order": domain_sort, "domains": result}

def handle_sigterm(*args):
    logging.debug(f"Dynu Tools - SIGTERM received args = {args}")
    publish_mqtt("dynu_tools/availability", "offline")
    MQTT_CLIENT.loop_stop()
    STOP_EVENT.set()

def get_public_ip(hostname, family):
    logging.debug(f"IP Updater - Querying {hostname} for {socket.AddressFamily(family).name} IP Address")
    
    if not IPV6_OK and family == socket.AF_INET6:
        logging.debug(f"IP Updater - No IPv6 connectivity")
        return None
    
    def allow_ipv6():
        return socket.AF_INET6
        
    def allow_ipv4():
        return socket.AF_INET
        
    def allow_unspec():
        return socket.AF_UNSPEC

    if family == socket.AF_INET6:
        urllib3_cn.allowed_gai_family = allow_ipv6
    elif family == socket.AF_INET:
        urllib3_cn.allowed_gai_family = allow_ipv4
        
    url = f"https://{hostname}/"
    
    try:
        response = requests.get(
            url,
            headers={"Host": hostname},
            timeout=5
        )
        response.raise_for_status()
    except Exception as e:
        logging.error(f"IP Updater - Error during IP request. Hostname: {hostname}, error: {e}")
        response = None
        
    urllib3_cn.allowed_gai_family = allow_unspec

    if not response:
        return None
        
    raw = response.text.strip()
    
    # Split only on the FIRST colon
    # dynu returns Current IP Address: 81.156.180.253
    
    if raw.startswith("Current IP Address:"):
        ip_address = raw.split(":", 1)[1].strip()
    else:
        ip_address = raw
        
    if IP_REGEX[family].match(ip_address):
        return ip_address
    else:
        return None
        
def update_ip(params):
    url = "https://api.dynu.com/nic/update"

    try:
        response = requests.get(
            url,
            params=params,
            timeout=5
        )
        response.raise_for_status()
    except Exception as e:
        return e

    return response.text.strip()

def iso_timestamp(timestamp):
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()

def ip_updater():
    first_run = True
    last_run = 0
    last_ip_state = load_ip_status()
    domainData = {}
    domain_count = 0
    last_update = True
    password = None
    
    logging.info("IP Updater - Thread started")
    
    for entity_id, entity_data in MQTT_ENTITIES.items():
        if entity_data.get("service", "") == "dns":
            publish_mqtt(f"dynu_tools/{entity_id}/availability", "offline")
    
    while not STOP_EVENT.is_set():
        if STOP_EVENT.wait(1):
            break
            
        if time.time() - last_run < 60 and not FORCE_IP["force"]:        
            continue
            
        last_run = time.time()
        forced = False
        
        if not last_update:
            forced = True
        
        if FORCE_IP["force"]:
            logging.info("IP Updater - Update Requested")
            forced = True
        
        if FORCE_IP["force"] or first_run:
            FORCE_IP["force"] = False
            first_run = False
        
            password = load_settings().get("password", None)
                
            if not password:
                continue

            domainData = load_domains()
            
            domain_count = 0
            for domain_name, domain_data in domainData.get("domains", {}).items():
                for record, record_data in domain_data.get("records", {}).items():
                    if record_data.get("update_ipv4", False) or record_data.get("update_ipv6", False):
                        domain_count += 1
                        
            if domain_count:
                for entity_id, entity_data in MQTT_ENTITIES.items():
                    if entity_data.get("service", "") == "dns":
                        publish_mqtt(f"dynu_tools/{entity_id}/availability", "online")
            
        if not domain_count or not password:
            continue
        
        ipv4_hosts = ["checkip.dynu.com", "icanhazip.com"]
        ipv6_hosts = ["checkipv6.dynu.com", "icanhazip.com"]
        
        ipv4 = None
        ipv6 = None
        
        for ipv4_host in ipv4_hosts:
            ipv4 = get_public_ip(ipv4_host, socket.AF_INET)
            if ipv4:
                break
            else:
                ipv4 = None
        
        if ipv4:
            logging.debug(f"IP Updater - Retrieved IPv4 address: {ipv4}")
        else:
            logging.error("IP Updater - Unable to retrive IPv4 address")
        
        for ipv6_host in ipv6_hosts:
            ipv6 = get_public_ip(ipv6_host, socket.AF_INET6)
            if ipv6:
                break
            else:
                ipv6 = None
                
        if ipv6:
            logging.debug(f"IP Updater - Retrieved IPv6 address: {ipv6}")
        else:
            logging.error("IP Updater - Unable to retrive IPv6 address")
        
        if ipv4 or ipv6:
            publish_mqtt("dynu_tools/last_ip_check", iso_timestamp(time.time()))
            
        if (ipv4 and (forced or ipv4 != last_ip_state.get("ipv4", None))) or (ipv6 and (forced or ipv6 != last_ip_state.get("ipv6", None))):
            all_update = True
            for domain_name, domain_data in domainData.get("domains", {}).items():
                for record, record_data in domain_data.get("records", {}).items():
                    if record_data.get("update_ipv4", False) or record_data.get("update_ipv6", False):
                        params = {
                            "hostname": domain_name,
                            "password": password
                        }
                        if record_data.get("alias", ""):
                            params["alias"] = record_data.get("alias")
                        if record_data.get("update_ipv4", False) and ipv4:
                            params["ipv4"] = ipv4
                        else:
                            params["ipv4"] = "no"
                        if record_data.get("update_ipv6", False) and ipv6:
                            params["ipv6"] = ipv6
                        else:
                            params["ipv6"] = "no"
                            
                        logging.info(f"IP Updater - Updating {record}")
                        
                        try:
                            update_status = update_ip(params)
                            
                            match update_status.split()[0]:   # look only at the first word
                                case "good":
                                    logging.info(f"IP Updater - Status = {update_status}")
                                case "nochg":
                                    logging.info(f"IP Updater - Status = {update_status}")
                                case "badauth":
                                    logging.error("IP Updater - Failed to authenticate")
                                    all_update = False
                                case "nohost":
                                    logging.error(f"IP Updater - Invalid hostname: {domain_name}")
                                    all_update = False
                                case "911":
                                    logging.error("IP Updater - Server Error")
                                    all_update = False
                                case _:
                                    logging.error(f"IP Updater - Unknown server response: {update_status}")
                                    all_update = False
                        except Exception as e:
                            logging.error(f"IP Updater - Error during update process: {e}")
                            all_update = False
                    
            if all_update:            
                last_ip_state={"ipv4": ipv4, "ipv6": ipv6, "last": time.time()}
                save_ip_status(last_ip_state)
                publish_event("ip_update", {"status": "updated", "ipv4": ipv4, "ipv6": ipv6})
                publish_mqtt("dynu_tools/ip_update_status", "true")
                publish_mqtt("dynu_tools/current_ipv4", ipv4)
                publish_mqtt("dynu_tools/current_ipv6", ipv6)
                publish_mqtt("dynu_tools/last_ip_update", iso_timestamp(time.time()))
                last_update = True
            else:
                publish_event("ip_update", {"status": "fail"})
                publish_mqtt("dynu_tools/ip_update_status", "false")
                last_update = False
                
        elif ipv4 or ipv6:
            logging.debug("IP Updater - IP not changed")
            publish_event("ip_update", {"status": "no_change", "ipv4": ipv4, "ipv6": ipv6})
        else:
            logging.error("IP Updater - Unable to retrieve IP Addresses")
        
        publish_mqtt("dynu_tools/next_ip_check", iso_timestamp(last_run + 60))
        logging.debug(f"IP Updater - Next IP check: {iso_timestamp(last_run + 60)}")
    
    logging.info("IP Updater - Thread stopped")
        
def cert_updater():
    next_check = 0
    first_run = True
    creds_path = "/run/dns-multi.ini"
    cert_file = "/data/letsencrypt/live/dynu_tools_certificate/cert.pem"
    acme_arguments = []
    key_arguments = []
    additional_args = []
    email = None
    apikey = None
    cert_domains = []
    
    logging.info("Certificate Manager - Thread started")
    
    for entity_id, entity_data in MQTT_ENTITIES.items():
        if entity_data.get("service", "") == "cert":
            publish_mqtt(f"dynu_tools/{entity_id}/availability", "offline")
    
    while not STOP_EVENT.is_set():
        if STOP_EVENT.wait(1):
            break
        
        if time.time() < next_check and not FORCE_CERT["force"]:        
            continue
            
        if FORCE_CERT["force"]:
            logging.info("Certificate Manager - Update requested")
           
        if FORCE_CERT["force"] or first_run:
            FORCE_CERT["force"] = False
            first_run = False
            
            settings = load_settings()
            
            email = settings.get("email", None)
            apikey = settings.get("api_key", None)
        
            if not email or not apikey:
                next_check = time.time() + 60
                continue
        
            domainData = load_domains()
            
            cert_domains = []

            for domain_name, domain_data in domainData.get("domains", {}).items():
                for record, record_data in domain_data.get("records", {}).items():
                    if record_data.get("certificate", False):
                        cert_domains.append(record)
                        
            if not len(cert_domains):
                next_check = time.time() + 60
                continue
                        
            os.makedirs("/data/workdir", exist_ok=True)
            os.makedirs("/data/letsencrypt", exist_ok=True)

            # Create file (touch) and set permissions 0600
            Path(creds_path).touch(mode=0o600, exist_ok=True)
            os.chmod(Path(creds_path), 0o600)

            # Write the credentials file
            try:
                with Path(creds_path).open("w") as f:
                    f.write("# generated by letsencrypt app startup script\n")
                    f.write("dns_multi_provider = dynu\n")
                    f.write(f"DYNU_API_KEY={apikey}\n")
                    f.write(f"DYNU_PROPAGATION_TIMEOUT=300\n")
            except Exception as e:
                logging.error(f"Certificate Manager - Error creating {creds_path}: {e}")
                next_check = time.time() + 60
                continue
                
            
            acme_arguments = []
            key_arguments = []
            additional_args = []

            acme_arguments += [
                "--authenticator", "dns-multi",
                "--dns-multi-credentials", creds_path,
                "--dns-multi-propagation-seconds", "300",
                "--preferred-chain", "ISRG Root X2"
            ]
            
            key_arguments += [
                "--key-type", "ecdsa",
                "--elliptic-curve", "secp256r1"
            ]
            
            additional_args = []
            
            if FORCE_RENEW:
                additional_args += ["--force-renewal"]
                
            if DRY_RUN:
                additional_args += ["--dry-run"]
                
            if LOG_LEVEL == "debug":
                additional_args += ["-vvv"]  
                
            for entity_id, entity_data in MQTT_ENTITIES.items():
                if entity_data.get("service", "") == "cert":
                    publish_mqtt(f"dynu_tools/{entity_id}/availability", "online")
        
        if not email or not apikey or not len(cert_domains):
            next_check = time.time() + 60
            continue

        cmd = [
            "certbot", "certonly",
            "--non-interactive",
            "--keep-until-expiring",
            "--expand",
            "--email", email,
            "--agree-tos",
            "--cert-name", "dynu_tools_certificate",
            "--config-dir", "/data/letsencrypt",
            "--work-dir", "/data/workdir",
            "--preferred-challenges", "dns",
        ]

        cmd.extend(key_arguments)
        cmd.extend(additional_args)
        cmd.extend(acme_arguments)

        for d in cert_domains:
            cmd.extend(["-d", d])

        cert_update_status = "fail"
        
        try:
            logging.info(f"Certificate Manager - Running certbot. This can take up to 5 minutes when creating a new certificate")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            output_lines = []

            for line in process.stdout:
                line = line.rstrip()
                output_lines.append(line)
                logging.debug(line)   # live streaming

            process.wait()
            certbot_exit = process.returncode
            certbot_output = "\n".join(output_lines)
            
            if certbot_exit == 0:
                if "Successfully received certificate" in certbot_output:
                    logging.info("Certificate Manager - New certificate received.")
                    shutil.copy("/data/letsencrypt/live/dynu_tools_certificate/privkey.pem", "/ssl/privkey.pem")
                    shutil.copy("/data/letsencrypt/live/dynu_tools_certificate/chain.pem", "/ssl/chain.pem")
                    shutil.copy("/data/letsencrypt/live/dynu_tools_certificate/fullchain.pem", "/ssl/fullchain.pem")
                    cert_update_status = "updated"
                elif "Certificate not yet due for renewal" in certbot_output:
                    logging.info("Certificate Manager - Certificate not yet due for renewal.")
                    shutil.copy("/data/letsencrypt/live/dynu_tools_certificate/privkey.pem", "/ssl/privkey.pem")
                    shutil.copy("/data/letsencrypt/live/dynu_tools_certificate/chain.pem", "/ssl/chain.pem")
                    shutil.copy("/data/letsencrypt/live/dynu_tools_certificate/fullchain.pem", "/ssl/fullchain.pem")
                    cert_update_status = "no_change"
                elif "The dry run was successful" in certbot_output:
                    logging.info("Certificate Manager - The test-run was successful.")
                    cert_update_status = "no_change"
                else:
                    logging.error("Certificate Manager - Unexpected Certbot output")
            else:
                logging.error(f"Certificate Manager - Certbot failed with code {certbot_exit}.")
        
        except Exception as e:
            logging.error(f"Certificate Manager - Certbot failed with error: {e}.")
            cert_update_status = "fail"
            
        CREATED_RAW = None
        VALID_FROM_RAW = None
        EXPIRY_RAW = None
        CREATED_ISO = None
        VALID_FROM_ISO = None
        EXPIRY_ISO = None
        
        if os.path.exists(cert_file):
            try:
                result = subprocess.run([                
                        "stat", "-c",
                        "%Y", cert_file
                    ],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if result.returncode != 0:
                    CREATED_RAW = None
                    logging.error("Certificate Manager - Unable to parse certificate creation date")
                else:
                    CREATED_RAW = result.stdout.strip()
            except Exception as e:
                CREATED_RAW = None
                logging.error(f"Certificate Manager - Unable to parse certificate creation date: {e}")
                
            try:
                result = subprocess.run([                
                        "openssl", "x509",
                        "-in", cert_file,
                        "-noout",
                        "-startdate"
                    ],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if result.returncode != 0:
                    VALID_FROM_RAW = None
                    logging.error("Certificate Manager - Unable to parse certificate valid from date")
                else:
                    VALID_FROM_RAW = result.stdout.strip().split("=", 1)[1]
            except Exception as e:
                VALID_FROM_RAW = None
                logging.error(f"Certificate Manager - Unable to parse certificate valid from date: {e}")
            
            try:
                result = subprocess.run([                
                        "openssl", "x509",
                        "-in", cert_file,
                        "-noout",
                        "-enddate"
                    ],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if result.returncode != 0:
                    EXPIRY_RAW = None
                    logging.error("Certificate Manager - Unable to parse certificate expiry date")
                else:
                    EXPIRY_RAW = result.stdout.strip().split("=", 1)[1]
            except Exception as e:
                EXPIRY_RAW = None
                logging.error(f"Certificate Manager - Unable to parse certificate expiry date: {e}")
        
        if EXPIRY_RAW and CREATED_RAW and VALID_FROM_RAW:
            logging.debug(f"Certificate Manager - Created raw: {CREATED_RAW}")
            logging.debug(f"Certificate Manager - Valid from raw: {VALID_FROM_RAW}")
            logging.debug(f"Certificate Manager - Expiry raw: {EXPIRY_RAW}")
            
            CREATED_TS = int(CREATED_RAW)
            VALID_FROM_TS = int(datetime.strptime(VALID_FROM_RAW, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc).timestamp())
            EXPIRY_TS = int(datetime.strptime(EXPIRY_RAW, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc).timestamp())
            
            CREATED_ISO = iso_timestamp(CREATED_TS)
            VALID_FROM_ISO = iso_timestamp(VALID_FROM_TS)
            EXPIRY_ISO = iso_timestamp(EXPIRY_TS)
            
            logging.info(f"Certificate Manager - Certificate Created {CREATED_ISO}")
            logging.info(f"Certificate Manager - Certificate Valid From {VALID_FROM_ISO}")
            logging.info(f"Certificate Manager - Certificate Expires {EXPIRY_ISO}")
            
            if time.time() >= EXPIRY_TS:
                logging.info("Certificate Manager - Current Certificate has expired!")
                publish_mqtt("dynu_tools/cert_valid", "false")
                next_check = time.time() + 600
            elif time.time() >= EXPIRY_TS - 432060:
                logging.info("Certificate Manager - Current Certificate will expire in the next 5 days")
                publish_mqtt("dynu_tools/cert_valid", "true")
                next_check = time.time() + 600
            else:
                logging.info("Certificate Manager - Current Certificate is valid")
                publish_mqtt("dynu_tools/cert_valid", "true")
                next_check = EXPIRY_TS - 431940
            
            publish_mqtt("dynu_tools/cert_expires", EXPIRY_ISO)
            publish_mqtt("dynu_tools/cert_created", CREATED_ISO)
            publish_mqtt("dynu_tools/last_cert_check", iso_timestamp(time.time()))
           
        else:
            publish_mqtt("dynu_tools/cert_valid", "unknown")
            cert_update_status = "fail"
            
        if cert_update_status == "fail":
            publish_mqtt("dynu_tools/cert_update_status", "false")
            publish_event("certificate_update", {"status": "fail"})
            next_check = time.time() + 600
        else:
            publish_mqtt("dynu_tools/cert_update_status", "true")
            publish_event("certificate_update", {"status": cert_update_status, "created": CREATED_ISO, "expires": EXPIRY_ISO})
            
        publish_mqtt("dynu_tools/next_cert_check", iso_timestamp(next_check))
        
    logging.info("Certificate Manager - Thread stopped")
  
# -----------------------------
# API Endpoints
# -----------------------------

@app.route("/")
def index():
    return send_from_directory("www", "index.html")

@app.route("/<path:path>")
def www_files(path):
    return send_from_directory("www", path)

@app.get("/api/settings")
def api_get_settings():
    return jsonify(load_settings())

@app.post("/api/settings")
def api_set_settings():
    save_settings(request.json)
    FORCE_IP["force"] = True
    FORCE_CERT["force"] = True
    return jsonify({"status": "ok"})

@app.get("/api/domains")
def api_get_domains():
    return jsonify(fetch_domains_from_dynu(load_settings().get("api_key", "")))

@app.post("/api/domains")
def api_save_domains():
    save_domains(request.json)
    FORCE_IP["force"] = True
    FORCE_CERT["force"] = True
    return jsonify({"status": "ok"})
    
signal.signal(signal.SIGTERM, handle_sigterm)
IPV6_OK = ipv6_capable()
setup_mqtt()
threading.Thread(target=ip_updater, daemon=True).start()
threading.Thread(target=cert_updater, daemon=True).start()
