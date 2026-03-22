import serial
import time
import json
import threading
from flask import Flask, request, jsonify, send_from_directory
import requests
import os
import logging
import signal

DEVICES_FILE = "/config/devices.json"
CONFIG_FILE = "/data/options.json"

with open(CONFIG_FILE) as f:
    addon_config = json.load(f)

SERIAL_PORT = addon_config.get("serial_port")
BAUD_RATE = addon_config.get("baud_rate")
LOG_LEVEL = addon_config.get("log_level", "info").upper()

HA_TOKEN = os.getenv("SUPERVISOR_TOKEN")
HA_URL = "http://supervisor/core/api"

TYPES = [{"id": "aa", "name": "Alarm Arm Away"},
        {"id": "ah", "name": "Alarm Arm Home"},
        {"id": "ad", "name": "Alarm Disarm"},
        {"id": "at", "name": "Alarm Trigger"},
        {"id": "db", "name": "Doorbell"},
        {"id": "dc", "name": "Door Closed"},
        {"id": "do", "name": "Door Opened"},
        {"id": "ls", "name": "Light Switch"},
        {"id": "md", "name": "Motion Detector"},
        {"id": "pa", "name": "Panic Alarm"},
        {"id": "sd", "name": "Smoke Detector"}]

last_events = {}
last_event = {}
stop_event = threading.Event()
serial_error = False
ser = None

# Enable detailed logging

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s"
)

app = Flask(__name__, static_folder="www") 

def load_devices():
    logging.debug("Starting load_devices")
    try:
        with open(DEVICES_FILE, "r") as f:
            return json.load(f)
            
    except FileNotFoundError:
        logging.info("devices.json not found, starting with empty device list")
        return {}

    except json.JSONDecodeError as e:
        logging.error(f"devices.json is corrupted: {e}")
        return {}

    except PermissionError as e:
        logging.error(f"No permission to read devices.json: {e}")
        return {}

    except Exception as e:
        logging.error(f"Unexpected error loading devices.json: {e}")
        return {}

def save_devices(devices):
    logging.debug("Starting save_devices")
    try:
        with open(DEVICES_FILE, "w") as f:
            json.dump(devices, f, indent=2)
            
    except PermissionError as e:
        logging.error(f"No permission to write devices.json: {e}")

    except IsADirectoryError as e:
        logging.error(f"Path points to a directory, not a file: {e}")

    except OSError as e:
        logging.error(f"OS error while writing devices.json: {e}")

    except Exception as e:
        logging.error(f"Unexpected error saving devices.json: {e}")

def handle_sigterm(*args):
    logging.debug(f"SIGTERM received args = {args}")
    stop_event.set()
    save_devices(devices)

def get_type(type_id):
    logging.debug(f"Starting get_type type_id = {type_id}")
    for t in TYPES:
        if t["id"] == type_id:
            return t
    return None
    
@app.route("/api/clear_events", methods=["POST"])
def api_clear_events():
    logging.debug("Starting api_clear_events")
    global last_events
    last_events = {}
    return jsonify({"status": "cleared"})
    
@app.route("/api/events", methods=["GET"])
def api_events():
    logging.debug("Starting api_events")
    return jsonify({
        "serial_ready": ser is not None and not serial_error,
        "events": last_events
    })
    
@app.route("/api/latest_event", methods=["GET"])
def api_latest_event():
    logging.debug("Starting api_latest_event")
    global last_event
    if last_event:
        return jsonify(last_event)

    return jsonify({})

@app.route("/api/ack_event", methods=["POST"])
def api_ack_event():
    logging.debug("Starting api_ack_event")
    global last_event
    last_event = {}
    return jsonify({"status": "ok"})
    
@app.route("/api/types", methods=["GET"])
def api_get_types():
    logging.debug("Starting api_get_types")
    return jsonify(TYPES)
    
@app.route("/api/devices", methods=["GET"])
def api_get_devices():
    logging.debug("Starting api_get_devices")
    return jsonify(devices)

@app.route("/api/add_device", methods=["POST"])
def api_add_device():
    logging.debug("Starting api_add_device")
    data = request.json
    logging.debug(f"api_add_device data = {data}")
    code = str(data["code"])
       
    devices[code] = {
        "name": data["name"],
        "type": data["type"],
        "timestamp": time.time()
    }

    global last_events
    if code in last_events:
        last_events.pop(code, None)
    
    save_devices(devices)

    return jsonify({"status": "ok"})

@app.route("/api/remove_device", methods=["POST"])
def api_remove_device():
    logging.debug("Starting api_remove_device")
    data = request.json
    logging.debug(f"api_remove_device data = {data}")
    code = str(data["code"])
    if code in devices:
        del devices[code]
        save_devices(devices)
    return jsonify({"status": "ok"})

@app.route("/api/test_device", methods=["POST"])
def api_test_device():
    logging.debug("Starting api_test_device")
    data = request.json
    logging.debug(f"api_test_device data = {data}")
    code = str(data["code"])
    type = get_type(str(data["type"]))['name']
    name = str(data["name"])
    
    logging.info(f"Triggering test event for {code}")
    
    event_payload = {
        "code": code,
        "name": name,
        "type": type,
    }
    requests.post(
        f"{HA_URL}/events/rf433_bridge",
        headers={"Authorization": f"Bearer {HA_TOKEN}"},
        json=event_payload
    )
    return jsonify({"status": "ok"})
    
@app.route("/api/send", methods=["POST"])
def api_send():
    logging.debug("Starting api_send")
    if ser is None:
        return jsonify({"error": "Serial port not ready"}), 503
    data = request.json
    logging.debug(f"api_send data = {data}")
    code = str(data["code"])
    msg = f"TX:{code}\n"
    logging.info(f"Sending TX message: {msg.strip()}")
    ser.write(msg.encode())
    return jsonify({"status": "sent"})

@app.route("/")
def index():
    logging.debug("Starting index")
    return send_from_directory("www", "index.html")

@app.route("/<path:path>")
def www_files(path):
    logging.debug(f"Starting www_files path = {path}")
    return send_from_directory("www", path)
    
def serial_reader():
    logging.info(f"Serial reader thread started")
    
    global serial_error
    
    while not stop_event.is_set():
        if stop_event.wait(1 if serial_error else 0.01):
            break
        
        try:
            raw = ser.readline()
            serial_error = False
        except (serial.SerialException, OSError) as e:
            if not serial_error:
                logging.error(f"Serial port error: {e}")
            serial_error = True
            continue
    
        if not raw:
            continue
            
        logging.debug(f"Serial Data received = {raw}")
        
        try:
            line = raw.decode("utf-8").strip()
        except UnicodeDecodeError:
            logging.warning(f"DECODE ERROR: {raw}")
            continue

        clean = ''.join(c for c in line if 32 <= ord(c) <= 126)

        if not clean.startswith("RX:"):
            continue

        try:
            _, id, bits, protocol = clean.split(":")
        except ValueError:
            logging.warning(f"PARSE ERROR: {clean}")
            continue
            
        code = f"{id}:{bits}:{protocol}"
        
        logging.debug(f"Code received = {code}")
        
        # If device is known, fire event with metadata
        if code in devices:
            device = devices[code]
            device_type = get_type(device['type'])
            
            global last_event
            last_event = {"code": code, "timestamp": time.time()};
            
            logging.info(f"Triggering event for {code}")
            event_payload = {
                "code": code,
                "name": device["name"],
                "type": device_type['name'],
            }
            requests.post(
                f"{HA_URL}/events/rf433_bridge",
                headers={"Authorization": f"Bearer {HA_TOKEN}"},
                json=event_payload
            )
            device['timestamp'] = time.time()
            
        else:
            logging.debug(f"Adding code {code} to last_events")
            global last_events
            last_events[code] = {
                "timestamp": time.time()
            }
            if len(last_events) > 50:
                logging.debug("Stripping last_events")
                # keep only the last 20 keys
                for key in list(last_events.keys())[:-50]:
                    del last_events[key]

    logging.info(f"Serial reader thread stopped")
    try:
        ser.close()
        logging.info("Serial Port closed")
    except:
        logging.error("Error trying to close Serial Port")
        pass

def startup():
    global ser
    
    load_error = False

    while not stop_event.is_set():
        if stop_event.wait(1 if load_error else 0.01):
            break

        if os.path.exists(SERIAL_PORT):
            try:
                logging.debug(f"Opening serial port {SERIAL_PORT} at {BAUD_RATE} baud")
                ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
                logging.info(f"Opened serial port {SERIAL_PORT} at {BAUD_RATE} baud")
                if ser:
                    threading.Thread(target=serial_reader, daemon=True).start()
                break
            except (serial.SerialException, Exception) as e:
                if not load_error:
                    logging.error(f"Failed to open serial port {SERIAL_PORT}: {e}")
                load_error = True
        else:
            if not load_error:
                logging.error("Serial Port not found")
            load_error = True

signal.signal(signal.SIGTERM, handle_sigterm)  
devices = load_devices()
threading.Thread(target=startup, daemon=True).start()

