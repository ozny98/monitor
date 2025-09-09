import apprise
import json
import argparse

import psutil
import socket
import subprocess
import builtins
import requests
import urllib3
import ssl
from datetime import datetime

global appr, buffer, notify_flag, debug
debug = False
buffer = []

notify_flag = False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def notify(message, ntype=apprise.NotifyType.INFO):
    import datetime
    import socket
    current_time = datetime.datetime.now()
    hostname = socket.gethostname()
    formatted_time = current_time.strftime("%a %b %d %H:%M:%S %Z %Y")
    global appr
    if appr:
        appr.notify(title=f'# {formatted_time} - [{hostname}]',
    body=message,
    notify_type=ntype
)
    else:
        print("not ok")


def check_ram(threshold=5,**kwargs):
    global notify_flag
    print("\n=== RAM ===")
    mem = psutil.virtual_memory()
    mem_total = mem.total / (1024 ** 2)
    if debug:
        print(" - ".join(mem._asdict().keys()))
        values = [str(f"{value / (1024**3):.2f}GB") for value in mem._asdict().values()]
        print(" - ".join(values))
    for label, attr in kwargs.items():
        if hasattr(mem, label):
            label_percentage = getattr(mem, label) / (1024 ** 2) * 100 / mem_total
            th = attr.get("threshold") if attr.get("threshold") else threshold
            if label_percentage < (th):
                print(f"[WARNING] - RAM ({label}) is under {th}% - current [{round(label_percentage,2)}%] ")
                notify_flag = True


def check_disks(threshold=80,**kwargs):
    global notify_flag
    print("\n=== Disks -  ===")
    lines = subprocess.check_output(["df", "-h"], text=True).splitlines()
    headers = lines[0].split()
    entries = []
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 6:
            entries.append(dict(zip(headers, parts)))
    for entry in entries:
        if debug:
            print(f"Disk {entry.get('Mounted')} - {entry.get('Use%')}")
        if entry.get("Use%") and int(entry.get("Use%").replace("%", "")) > threshold:
            notify_flag = True
            print(f"[WARNING] - Disk {entry.get('Mounted')} is over {threshold}% used")
    return entries


# TODO:
def check_cpu(threshold=4.0):
    return {
        "cpu_usage_percent": psutil.cpu_percent(interval=1)
    }



def is_port_open(host, port):
    try:
        if debug:
            print(f"Checking port {port} on {host}")
        s =  socket.socket()
        s.settimeout(1)
        s.connect((host, int(port)))
        s.close()
        return True
    except:
        return False

def check_services(services:list,**kwargs):
    print("\n=== Services ===")
    global notify_flag
    try:
        for svc in services:
            reachable = is_port_open( svc.get("host"),svc.get("port"))
            if debug:
                print(f"Service ({svc.get('description', 'net_service')}) {svc.get('host')}:{svc.get('port')} is {'reachable' if reachable else 'not reachable'}")
            if not reachable:
                notify_flag = True
                print(f"[WARNING] - Service ({svc.get('description', 'net_service')}) {svc.get('host')}:{svc.get('port')} is down")
    except Exception as e:
        print(f"Error checking services: {e}")
        notify_flag = True
        

def check_web(endpoints:list,**kwargs):
    print("\n=== WEB URL CHECK ===")
    global notify_flag
    for ep in endpoints:
        try:
            url = ep.get("url")
            method = ep.get("method", "GET").upper()
            timeout = ep.get("timeout", 5)
            verify = ep.get("verify", True)
            headers = ep.get("headers", {"User-Agent": "endpoint-healthcheck/1.0"})
            allow_redirects = ep.get("allow_redirects", True)
            expect = ep.get("expect")
            ok_min = ep.get("ok_min", 200)
            ok_max = ep.get("ok_max", 299)
            max_bytes = ep.get("max_bytes", 1024 * 1024)  # Default to 1MB
            insecure = ep.get("insecure", False)
            cert = (ep.get("cert",None), ep.get("key",None))

            if debug:
                print(f"Checking {url} with method {method} {f'Required Cert:{ cert}' if cert else ''}")

            response = requests.request(
                method,
                url,
                timeout=timeout,
                verify=verify,
                allow_redirects=allow_redirects,
                headers=headers,
                cert=cert,
            )

            if debug:
                print(f"\tResponse: {response.status_code} {response.reason}")

            if not (ok_min <= response.status_code <= ok_max):
                notify_flag = True
                print(f"[WARNING] - URL {url} returned status code {response.status_code}, expected between {ok_min} and {ok_max}")
            
            if expect and expect.lower() not in response.text.lower():
                notify_flag = True
                print(f"[WARNING] - URL {url} did not contain expected text '{expect}'")

        except requests.RequestException as e:
            notify_flag = True
            print(f"[ERROR] - Failed to check URL {url}: {e}")
    return None



def printbuff(*args, **kwargs):
    global buffer
    if not buffer:
        buffer = []
    message = " ".join(map(str, args))
    buffer.append(message)
    if kwargs.get("flush", False):
        builtins.print(*args, **kwargs)
    else:
        pass


parser = argparse.ArgumentParser(description="Monitoring script: in debug printa le statistiche , CPU monitor non funzionante")
parser.add_argument('--config', type=str, required=True, help='Path al file di configurazione JSON')
parser.add_argument('--debug', action="store_true", help='Print in console')

args = parser.parse_args()


with open(args.config, "r") as f:
    config = json.load(f)

apprise_conf = config["apprise_conf"]

appr = apprise.Apprise()
appr.add(f'gchat://{apprise_conf.get("workspace")}/{apprise_conf.get("key")}/{apprise_conf.get("token")}')

if not args.debug:
    builtins.print = printbuff
else:
    debug = True

if __name__ == "__main__":

    if config.get("ram"):
        ram = check_ram(**config["ram"])

    if config.get("disk"):
        check_disks(**config["disk"])

    if config.get("cpu"):
        cpu = check_cpu(**config["cpu"])

    if config.get("network_svc"):
        check_services(**config["network_svc"])

    if config.get("web_svc"):
        check_web(**config["web_svc"])

    if not args.debug and notify_flag:
        notify("\n".join(buffer), ntype=apprise.NotifyType.INFO)
