
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import subprocess
import threading
import time
import webbrowser

from collections import deque, Counter
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


# ============================================================
# CONFIGURATION - WINDOWS
# ============================================================

ROOT = Path(r"D:\cod\RAMP")

DOCKER = (
    r"C:\Users\Dr. System\AppData\Local\Programs"
    r"\DockerDesktop\resources\bin\docker.exe"
)

HOST = "127.0.0.1"
PORT = 8765

ROUTER_CONTAINER = "docker-netem-router-1"

REFRESH_SECONDS = 2
MAX_PACKETS = 500

TCPDUMP = "tcpdump"

CONTAINERS = {
    "client": "docker-ramp-client-1",
    "bridge": "docker-ramp-bridge-1",
    "router": "docker-netem-router-1",
    "destination": "docker-destination-1",
}


# ============================================================
# HELPERS
# ============================================================

def now():
    return datetime.now().astimezone().isoformat(
        timespec="milliseconds"
    )


def format_error(value):
    return str(value).strip() if value else "Unknown error"


# ============================================================
# RAMP MONITOR
# ============================================================

class Monitor:

    def __init__(self):

        self.lock = threading.RLock()

        self.packets = deque(maxlen=MAX_PACKETS)

        self.capture_process = None
        self.capture_thread = None
        self.stderr_thread = None

        self.running = False

        self.started_at = None
        self.stopped_at = None

        self.error = None
        self.docker_error = None
        self.tcpdump_error = None

        self.total_packets = 0
        self.total_bytes = 0

        self.last_packet_at = None

    # --------------------------------------------------------
    # Docker command
    # --------------------------------------------------------

    def docker_command(self, args, timeout=20):

        if not Path(DOCKER).is_file():
            raise RuntimeError(
                "Docker Desktop executable not found: " + DOCKER
            )

        result = subprocess.run(
            [DOCKER] + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=getattr(
                subprocess,
                "CREATE_NO_WINDOW",
                0
            )
        )

        if result.returncode != 0:
            raise RuntimeError(
                format_error(result.stderr)
            )

        return result.stdout.strip()

    # --------------------------------------------------------
    # Docker verification
    # --------------------------------------------------------

    def verify_docker(self):

        output = self.docker_command(["version", "--format", "{{.Server.Version}}"])

        if not output:
            raise RuntimeError("Docker Engine is not responding.")

        return output

    def get_container_status(self):

        output = self.docker_command([
            "ps",
            "-a",
            "--format",
            "{{.Names}}|{{.Status}}"
        ])

        statuses = {}

        for line in output.splitlines():

            parts = line.split("|", 1)

            if len(parts) != 2:
                continue

            name, status = parts

            for key, container_name in CONTAINERS.items():

                if name == container_name:
                    statuses[key] = {
                        "name": name,
                        "status": status,
                        "running": status.startswith("Up")
                    }

        return statuses

    def verify_router(self):

        output = self.docker_command([
            "inspect",
            "--format",
            "{{.State.Running}}",
            ROUTER_CONTAINER
        ])

        if output.lower() != "true":
            raise RuntimeError(
                "RAMP Router container is not running."
            )

        return True

    def verify_tcpdump(self):

        output = self.docker_command([
            "exec",
            ROUTER_CONTAINER,
            "tcpdump",
            "--version"
        ])

        return output.splitlines()[0] if output else "Available"

    # --------------------------------------------------------
    # Packet parsing
    # --------------------------------------------------------

    def parse_packet(self, line):

        line = line.strip()

        if not line:
            return None

        timestamp = now()

        timestamp_match = re.match(
            r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)",
            line
        )

        if timestamp_match:
            timestamp = timestamp_match.group(1)

        length_match = re.search(
            r"\blength\s+(\d+)",
            line
        )

        length = (
            int(length_match.group(1))
            if length_match else 0
        )

        flags_match = re.search(
            r"Flags\s+\[([^\]]+)\]",
            line
        )

        flags = (
            flags_match.group(1)
            if flags_match else "-"
        )

        if re.search(r"\bIP6\s", line):
            network_protocol = "IPv6"

        elif re.search(r"\bIP\s", line):
            network_protocol = "IPv4"

        else:
            network_protocol = "OTHER"

        if re.search(r"\bFlags\s+\[", line):
            protocol = "TCP"

        elif re.search(r"\bUDP\b", line):
            protocol = "UDP"

        elif re.search(r"\bICMP6?\b", line):
            protocol = "ICMP"

        elif network_protocol in ("IPv4", "IPv6"):
            protocol = network_protocol

        else:
            protocol = "OTHER"

        endpoint_match = re.search(
            r"\bIP6?\s+(.+?)\s+>\s+(.+?):",
            line
        )

        source = "Unknown"
        destination = "Unknown"

        if endpoint_match:
            source = endpoint_match.group(1).strip()
            destination = endpoint_match.group(2).strip()

        return {
            "id": 0,
            "timestamp": timestamp,
            "protocol": protocol,
            "network_protocol": network_protocol,
            "source": source,
            "destination": destination,
            "length": length,
            "flags": flags,
            "interface": "any",
            "raw": line
        }

    # --------------------------------------------------------
    # Capture stderr reader
    # --------------------------------------------------------

    def read_stderr(self, process):

        try:

            for line in process.stderr:

                line = line.strip()

                if not line:
                    continue

                with self.lock:
                    self.tcpdump_error = line

        except Exception as exc:

            with self.lock:
                self.tcpdump_error = str(exc)

    # --------------------------------------------------------
    # Capture reader
    # --------------------------------------------------------

    def capture_reader(self, process):

        try:

            for line in process.stdout:

                packet = self.parse_packet(line)

                if packet is None:
                    continue

                with self.lock:

                    self.total_packets += 1

                    self.total_bytes += packet["length"]

                    packet["id"] = self.total_packets

                    self.last_packet_at = now()

                    self.packets.append(packet)

        except Exception as exc:

            with self.lock:
                self.error = str(exc)

        finally:

            return_code = process.poll()

            with self.lock:

                self.running = False

                if return_code not in (None, 0):
                    self.error = (
                        self.error
                        or f"Capture process exited: {return_code}"
                    )

                self.stopped_at = now()

    # --------------------------------------------------------
    # Start capture
    # --------------------------------------------------------

    def start(self):

        with self.lock:

            if self.running:
                return {
                    "ok": True,
                    "message": "Capture is already running."
                }

            self.error = None
            self.tcpdump_error = None

        try:

            self.verify_router()
            self.verify_tcpdump()

            command = [
                DOCKER,
                "exec",
                "-i",
                ROUTER_CONTAINER,
                TCPDUMP,
                "-i",
                "any",
                "-nn",
                "-tttt",
                "-l",
                "-vvv"
            ]

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=getattr(
                    subprocess,
                    "CREATE_NO_WINDOW",
                    0
                )
            )

            time.sleep(0.7)

            if process.poll() is not None:

                error_output = process.stderr.read()

                raise RuntimeError(
                    error_output.strip()
                    or "tcpdump could not start."
                )

            with self.lock:

                self.capture_process = process
                self.running = True
                self.started_at = now()
                self.stopped_at = None

            self.stderr_thread = threading.Thread(
                target=self.read_stderr,
                args=(process,),
                daemon=True
            )

            self.capture_thread = threading.Thread(
                target=self.capture_reader,
                args=(process,),
                daemon=True
            )

            self.stderr_thread.start()
            self.capture_thread.start()

            return {
                "ok": True,
                "message": "Real packet capture started."
            }

        except Exception as exc:

            with self.lock:

                self.running = False
                self.error = str(exc)

            return {
                "ok": False,
                "message": str(exc)
            }

    # --------------------------------------------------------
    # Stop capture
    # --------------------------------------------------------

    def stop(self):

        with self.lock:
            process = self.capture_process

        if process is None or process.poll() is not None:

            with self.lock:
                self.running = False

            return {
                "ok": True,
                "message": "Capture is already stopped."
            }

        try:

            process.terminate()

            try:
                process.wait(timeout=5)

            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)

            with self.lock:
                self.running = False
                self.stopped_at = now()

            return {
                "ok": True,
                "message": "Capture stopped."
            }

        except Exception as exc:

            with self.lock:
                self.error = str(exc)

            return {
                "ok": False,
                "message": str(exc)
            }

    # --------------------------------------------------------
    # Snapshot
    # --------------------------------------------------------

    def snapshot(self):

        try:
            containers = self.get_container_status()
            docker_version = self.verify_docker()
            docker_error = None

        except Exception as exc:

            containers = {}
            docker_version = None
            docker_error = str(exc)

        with self.lock:

            packets = list(self.packets)

            protocol_counts = dict(
                Counter(
                    packet["protocol"]
                    for packet in packets
                )
            )

            return {

                "project": "RAMP",

                "timestamp": now(),

                "docker": {
                    "version": docker_version,
                    "error": docker_error
                },

                "capture": {
                    "running": self.running,
                    "started_at": self.started_at,
                    "stopped_at": self.stopped_at,
                    "last_packet_at": self.last_packet_at,
                    "error": self.error,
                    "tcpdump_error": self.tcpdump_error
                },

                "router": {
                    "container": ROUTER_CONTAINER,
                    "running": containers.get(
                        "router", {}
                    ).get("running", False)
                },

                "containers": containers,

                "statistics": {
                    "total_packets": self.total_packets,
                    "total_bytes": self.total_bytes,
                    "visible_packets": len(packets),
                    "protocols": protocol_counts
                },

                "packets": packets

            }


monitor = Monitor()


# ============================================================
# DASHBOARD HTML
# ============================================================

HTML = r"""
<!DOCTYPE html>
<html lang="fa" dir="rtl">

<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>RAMP Network Monitor</title>

<style>

:root {
    color-scheme: dark;
    --bg: #0b1020;
    --panel: #121a2d;
    --panel2: #18233a;
    --border: #293650;
    --text: #e6edf8;
    --muted: #8b9bb5;
    --blue: #60a5fa;
    --green: #34d399;
    --red: #fb7185;
    --yellow: #fbbf24;
}

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: Tahoma, Arial, sans-serif;
}

header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px 28px;
    border-bottom: 1px solid var(--border);
    background: #0e1628;
    flex-wrap: wrap;
    gap: 15px;
}

.logo {
    font-size: 25px;
    font-weight: bold;
    color: var(--blue);
    letter-spacing: 2px;
}

.subtitle {
    color: var(--muted);
    font-size: 12px;
    margin-top: 7px;
}

.actions {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    align-items: center;
}

button {
    border: 1px solid var(--border);
    border-radius: 9px;
    padding: 10px 17px;
    cursor: pointer;
    color: white;
    background: var(--panel2);
    font-family: inherit;
}

button:disabled {
    opacity: .5;
    cursor: wait;
}

.start {
    background: #065f46;
}

.stop {
    background: #881337;
}

main {
    padding: 24px;
    max-width: 1800px;
    margin: auto;
}

.grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 15px;
}

.card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 13px;
    padding: 19px;
    min-width: 0;
}

.card-label {
    color: var(--muted);
    font-size: 13px;
}

.metric {
    font-size: 29px;
    font-weight: bold;
    margin-top: 13px;
    direction: ltr;
    text-align: right;
}

.metric-small {
    font-size: 12px;
    margin-top: 10px;
    color: var(--muted);
}

.section {
    margin-top: 22px;
}

.section-title {
    font-size: 17px;
    margin-bottom: 13px;
}

.panel {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 13px;
    padding: 18px;
}

.topology {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
}

.node {
    padding: 20px 10px;
    border-radius: 10px;
    text-align: center;
    background: var(--panel2);
    border: 1px solid var(--border);
}

.node-name {
    font-weight: bold;
    margin-bottom: 10px;
}

.node-status {
    font-size: 12px;
    color: var(--muted);
    direction: ltr;
    overflow-wrap: anywhere;
}

.online {
    color: var(--green);
}

.offline {
    color: var(--red);
}

.table-wrap {
    overflow-x: auto;
}

table {
    width: 100%;
    border-collapse: collapse;
    min-width: 950px;
}

th, td {
    padding: 12px 10px;
    border-bottom: 1px solid var(--border);
    text-align: right;
    font-size: 12px;
}

th {
    color: var(--muted);
    font-weight: normal;
}

td {
    direction: ltr;
    text-align: left;
    font-family: Consolas, monospace;
}

tr {
    cursor: pointer;
}

tr:hover {
    background: var(--panel2);
}

.protocol {
    display: inline-block;
    padding: 4px 8px;
    border-radius: 5px;
    background: #1e3a5f;
    color: #93c5fd;
}

.detail {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
}

.detail-item {
    padding: 12px;
    background: var(--panel2);
    border-radius: 8px;
    min-width: 0;
}

.detail-label {
    color: var(--muted);
    font-size: 11px;
    margin-bottom: 8px;
}

.detail-value {
    direction: ltr;
    text-align: left;
    font-family: Consolas, monospace;
    overflow-wrap: anywhere;
    font-size: 12px;
}

pre {
    white-space: pre-wrap;
    word-break: break-word;
    direction: ltr;
    text-align: left;
    color: #a7f3d0;
    background: #080e19;
    padding: 14px;
    border-radius: 9px;
    overflow: auto;
}

.status {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    color: var(--muted);
    font-size: 12px;
}

.dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: var(--red);
}

.dot.active {
    background: var(--green);
    box-shadow: 0 0 10px var(--green);
}

#error {
    color: var(--red);
    font-size: 12px;
    margin-top: 12px;
    white-space: pre-wrap;
    direction: ltr;
    text-align: left;
}

#last-update {
    color: var(--muted);
    font-size: 11px;
    margin-top: 12px;
}

footer {
    color: var(--muted);
    font-size: 11px;
    text-align: center;
    padding: 25px;
}

@media(max-width: 950px) {
    .grid {
        grid-template-columns: repeat(2, 1fr);
    }

    .topology {
        grid-template-columns: repeat(2, 1fr);
    }
}

@media(max-width: 550px) {
    main {
        padding: 12px;
    }

    .grid,
    .topology,
    .detail {
        grid-template-columns: 1fr;
    }
}

</style>
</head>

<body>

<header>

    <div>
        <div class="logo">RAMP MONITOR</div>
        <div class="subtitle">
            Real-time Network Laboratory Monitoring
        </div>
    </div>

    <div class="actions">

        <span class="status">
            <span id="capture-dot" class="dot"></span>
            <span id="capture-status">در حال بررسی...</span>
        </span>

        <button class="start" id="start-button" onclick="startCapture()">
            شروع Capture
        </button>

        <button class="stop" id="stop-button" onclick="stopCapture()">
            توقف Capture
        </button>

        <button onclick="downloadReport()">
            دریافت JSON
        </button>

    </div>

</header>

<main>

    <div class="grid">

        <div class="card">
            <div class="card-label">کل بسته‌های دریافت‌شده</div>
            <div class="metric" id="total-packets">0</div>
            <div class="metric-small">از ابتدای اجرای Capture</div>
        </div>

        <div class="card">
            <div class="card-label">مجموع طول بسته‌ها</div>
            <div class="metric" id="total-bytes">0 B</div>
            <div class="metric-small">مجموع طول گزارش‌شده توسط tcpdump</div>
        </div>

        <div class="card">
            <div class="card-label">بسته‌های ذخیره‌شده</div>
            <div class="metric" id="visible-packets">0</div>
            <div class="metric-small">حداکثر 500 بسته اخیر</div>
        </div>

        <div class="card">
            <div class="card-label">پروتکل‌های مشاهده‌شده</div>
            <div class="metric" id="protocol-count">0</div>
            <div class="metric-small" id="protocol-summary">بدون داده</div>
        </div>

    </div>

    <div class="section">

        <div class="section-title">
            توپولوژی آزمایشگاه RAMP
        </div>

        <div class="panel">

            <div class="topology">

                <div class="node">
                    <div class="node-name">RAMP Client</div>
                    <div class="node-status" id="client-status">Unknown</div>
                </div>

                <div class="node">
                    <div class="node-name">RAMP Bridge</div>
                    <div class="node-status" id="bridge-status">Unknown</div>
                </div>

                <div class="node">
                    <div class="node-name">NetEm Router</div>
                    <div class="node-status" id="router-status">Unknown</div>
                </div>

                <div class="node">
                    <div class="node-name">Destination</div>
                    <div class="node-status" id="destination-status">Unknown</div>
                </div>

            </div>

            <div id="docker-info" class="metric-small">
                Docker status: checking...
            </div>

        </div>

    </div>

    <div class="section">

        <div class="section-title">
            جریان زنده بسته‌های شبکه
        </div>

        <div class="panel">

            <div class="table-wrap">

                <table>

                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>زمان</th>
                            <th>پروتکل</th>
                            <th>نسخه IP</th>
                            <th>مبدأ</th>
                            <th>مقصد</th>
                            <th>اندازه</th>
                            <th>Flags</th>
                        </tr>
                    </thead>

                    <tbody id="packet-table">
                        <tr>
                            <td colspan="8">
                                هنوز بسته‌ای دریافت نشده است.
                            </td>
                        </tr>
                    </tbody>

                </table>

            </div>

        </div>

    </div>

    <div class="section">

        <div class="section-title">
            جزئیات بسته انتخاب‌شده
        </div>

        <div class="panel">

            <div class="detail" id="packet-detail">

                <div class="detail-item">
                    <div class="detail-label">وضعیت</div>
                    <div class="detail-value">
                        یک بسته را انتخاب کنید
                    </div>
                </div>

            </div>

            <div style="margin-top:15px">
                <div class="card-label">Raw Packet Information</div>
                <pre id="raw-packet">No packet selected.</pre>
            </div>

        </div>

    </div>

    <div id="error"></div>
    <div id="last-update"></div>

</main>

<footer>
    RAMP Network Laboratory · Live Docker Capture
</footer>

<script>

let selectedPacket = null;
let refreshBusy = false;

function formatBytes(bytes) {

    if (bytes < 1024) return bytes + " B";

    if (bytes < 1024 * 1024)
        return (bytes / 1024).toFixed(2) + " KB";

    return (bytes / 1024 / 1024).toFixed(2) + " MB";
}

function escapeHtml(value) {

    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    })[char]);
}

function updateContainer(id, container) {

    const element = document.getElementById(id);

    if (!container) {

        element.textContent = "Not found";
        element.className = "node-status offline";

        return;
    }

    element.textContent = container.status;

    element.className =
        "node-status " +
        (container.running ? "online" : "offline");
}

function selectPacket(packet) {

    selectedPacket = packet;

    const fields = [
        ["Packet ID", packet.id],
        ["Timestamp", packet.timestamp],
        ["Protocol", packet.protocol],
        ["Network Protocol", packet.network_protocol],
        ["Source", packet.source],
        ["Destination", packet.destination],
        ["Length", packet.length + " bytes"],
        ["TCP Flags", packet.flags],
        ["Interface", packet.interface]
    ];

    document.getElementById("packet-detail").innerHTML =
        fields.map(item => `
            <div class="detail-item">
                <div class="detail-label">${escapeHtml(item[0])}</div>
                <div class="detail-value">${escapeHtml(item[1])}</div>
            </div>
        `).join("");

    document.getElementById("raw-packet").textContent =
        packet.raw || "";
}

function renderPackets(packets) {

    const table = document.getElementById("packet-table");

    if (!packets.length) {

        table.innerHTML = `
            <tr>
                <td colspan="8">
                    هنوز بسته‌ای دریافت نشده است.
                </td>
            </tr>
        `;

        return;
    }

    table.innerHTML = packets.slice().reverse().map(packet => {

        const time = packet.timestamp.split("T").pop();

        return `
            <tr data-id="${packet.id}">
                <td>${packet.id}</td>
                <td>${escapeHtml(time)}</td>
                <td>
                    <span class="protocol">
                        ${escapeHtml(packet.protocol)}
                    </span>
                </td>
                <td>${escapeHtml(packet.network_protocol)}</td>
                <td>${escapeHtml(packet.source)}</td>
                <td>${escapeHtml(packet.destination)}</td>
                <td>${packet.length} B</td>
                <td>${escapeHtml(packet.flags)}</td>
            </tr>
        `;

    }).join("");

    table.querySelectorAll("tr[data-id]").forEach(row => {

        row.addEventListener("click", () => {

            const packet = packets.find(
                item => item.id === Number(row.dataset.id)
            );

            if (packet) selectPacket(packet);

        });

    });

    if (selectedPacket) {

        const updated = packets.find(
            item => item.id === selectedPacket.id
        );

        if (updated) selectPacket(updated);
    }
}

async function refresh() {

    if (refreshBusy) return;

    refreshBusy = true;

    try {

        const response = await fetch("/api/status", {
            cache: "no-store"
        });

        if (!response.ok)
            throw new Error("HTTP " + response.status);

        const data = await response.json();

        const stats = data.statistics;

        document.getElementById("total-packets").textContent =
            stats.total_packets.toLocaleString();

        document.getElementById("total-bytes").textContent =
            formatBytes(stats.total_bytes);

        document.getElementById("visible-packets").textContent =
            stats.visible_packets;

        const protocols = Object.keys(stats.protocols);

        document.getElementById("protocol-count").textContent =
            protocols.length;

        document.getElementById("protocol-summary").textContent =
            protocols.length
                ? protocols.map(p =>
                    p + ": " + stats.protocols[p]
                ).join(" | ")
                : "بدون داده";

        const running = data.capture.running;

        document.getElementById("capture-dot").className =
            "dot " + (running ? "active" : "");

        document.getElementById("capture-status").textContent =
            running ? "Capture فعال" : "Capture متوقف";

        updateContainer("client-status", data.containers.client);
        updateContainer("bridge-status", data.containers.bridge);
        updateContainer("router-status", data.containers.router);
        updateContainer("destination-status", data.containers.destination);

        document.getElementById("docker-info").textContent =
            data.docker.version
                ? "Docker Engine: " + data.docker.version
                : "Docker error: " + (data.docker.error || "Unknown");

        renderPackets(data.packets);

        const errors = [
            data.capture.error,
            data.capture.tcpdump_error,
            data.docker.error
        ].filter(Boolean);

        document.getElementById("error").textContent =
            errors.join("\n");

        document.getElementById("last-update").textContent =
            "آخرین به‌روزرسانی: " + data.timestamp;

    } catch (error) {

        document.getElementById("error").textContent =
            "Dashboard error: " + error.message;

    } finally {

        refreshBusy = false;
    }
}

async function captureAction(endpoint, buttonId) {

    const button = document.getElementById(buttonId);

    button.disabled = true;

    try {

        const response = await fetch(endpoint, {
            method: "POST"
        });

        const result = await response.json();

        alert(result.message);

    } catch (error) {

        alert("Request failed: " + error.message);

    } finally {

        button.disabled = false;
        refresh();
    }
}

function startCapture() {
    captureAction("/api/start", "start-button");
}

function stopCapture() {
    captureAction("/api/stop", "stop-button");
}

async function downloadReport() {

    try {

        const response = await fetch("/api/status");

        const data = await response.json();

        const blob = new Blob(
            [JSON.stringify(data, null, 2)],
            {type: "application/json"}
        );

        const url = URL.createObjectURL(blob);

        const link = document.createElement("a");

        link.href = url;
        link.download = "ramp-network-report.json";

        link.click();

        URL.revokeObjectURL(url);

    } catch (error) {

        alert("Report failed: " + error.message);
    }
}

refresh();

setInterval(refresh, 2000);

</script>

</body>
</html>
"""


# ============================================================
# HTTP SERVER
# ============================================================

class DashboardHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        return

    def send_json(self, data, status=200):

        payload = json.dumps(
            data,
            ensure_ascii=False
        ).encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )

        self.send_header(
            "Content-Length",
            str(len(payload))
        )

        self.send_header(
            "Cache-Control",
            "no-store"
        )

        self.end_headers()

        self.wfile.write(payload)

    def do_GET(self):

        path = urlparse(self.path).path

        if path == "/":

            payload = HTML.encode("utf-8")

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8"
            )

            self.send_header(
                "Content-Length",
                str(len(payload))
            )

            self.end_headers()

            self.wfile.write(payload)

            return

        if path == "/api/status":

            self.send_json(monitor.snapshot())
            return

        if path == "/api/health":

            self.send_json({
                "ok": True,
                "service": "RAMP Monitor"
            })

            return

        self.send_json({
            "error": "Not found"
        }, 404)

    def do_POST(self):

        path = urlparse(self.path).path

        if path == "/api/start":

            result = monitor.start()

            self.send_json(
                result,
                200 if result["ok"] else 500
            )

            return

        if path == "/api/stop":

            result = monitor.stop()

            self.send_json(
                result,
                200 if result["ok"] else 500
            )

            return

        self.send_json({
            "error": "Not found"
        }, 404)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("RAMP NETWORK MONITOR")
    print("=" * 60)

    print("Project:", ROOT)
    print("Docker:", DOCKER)
    print("Router:", ROUTER_CONTAINER)
    print("Address:", f"http://127.0.0.1:{PORT}")
    print("Refresh:", REFRESH_SECONDS, "seconds")

    print("=" * 60)

    if not ROOT.is_dir():

        raise SystemExit(
            "RAMP project directory not found: " + str(ROOT)
        )

    if not Path(DOCKER).is_file():

        raise SystemExit(
            "Docker Desktop CLI not found: " + DOCKER
        )

    try:

        version = monitor.verify_docker()

        print("[OK] Docker Engine:", version)

        monitor.verify_router()

        print("[OK] Router container is running")

        tcpdump_version = monitor.verify_tcpdump()

        print("[OK] tcpdump:", tcpdump_version)

    except Exception as exc:

        raise SystemExit(
            "Startup verification failed: " + str(exc)
        )

    try:

        server = ThreadingHTTPServer(
            (HOST, PORT),
            DashboardHandler
        )

    except OSError as exc:

        raise SystemExit(
            f"Could not bind dashboard port {PORT}: {exc}"
        )

    print("[OK] Dashboard server started")
    print("[INFO] Capture is initially stopped")
    print("[INFO] Open http://127.0.0.1:8765")

    threading.Timer(
        1.0,
        lambda: webbrowser.open(
            f"http://127.0.0.1:{PORT}"
        )
    ).start()

    try:

        server.serve_forever()

    except KeyboardInterrupt:

        print("\nStopping RAMP Monitor...")

    finally:

        monitor.stop()
        server.server_close()

        print("[OK] Dashboard stopped")


if __name__ == "__main__":
    main()
