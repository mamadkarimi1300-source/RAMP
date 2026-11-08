#!/usr/bin/env python3
"""Repeatable direct-vs-RAMP workload runner; Python standard library only."""
from __future__ import annotations
import argparse, datetime as dt, json, math, os, platform, shutil, statistics, subprocess, sys, time, uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = ROOT / "deployments/docker/compose.yaml"
MATRIX_FILE = ROOT / "laboratory/scenarios/matrix.json"

def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def run_command(args, *, env=None, timeout=180, check=True):
    result = subprocess.run([str(x) for x in args], cwd=ROOT, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(map(str, args))}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    return result

def compose(*args, env=None, timeout=180, check=True):
    return run_command(["docker", "compose", "-f", str(COMPOSE_FILE), *args],
                       env=env, timeout=timeout, check=check)

def percentile(values, p):
    if not values: return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * p
    lo, hi = math.floor(position), math.ceil(position)
    return ordered[lo] if lo == hi else ordered[lo] * (hi-position) + ordered[hi] * (position-lo)

def summarize(samples):
    groups = {}
    for item in samples: groups.setdefault((item["scenario_id"], item["mode"]), []).append(item)
    rows = []
    for (scenario, mode), items in sorted(groups.items()):
        good = [x for x in items if x["success"]]
        rates = [x["goodput_mbps"] for x in good]
        durations = [x["transfer_duration_ms"] for x in good]
        rows.append({
            "scenario_id": scenario, "mode": mode, "runs": len(items),
            "successes": len(good), "failures": len(items)-len(good),
            "success_rate": len(good)/len(items) if items else 0,
            "goodput_mbps_mean": statistics.mean(rates) if rates else None,
            "goodput_mbps_median": statistics.median(rates) if rates else None,
            "goodput_mbps_p95": percentile(rates, .95),
            "goodput_mbps_stdev": statistics.stdev(rates) if len(rates)>1 else (0.0 if rates else None),
            "transfer_duration_ms_mean": statistics.mean(durations) if durations else None,
            "transfer_duration_ms_median": statistics.median(durations) if durations else None,
            "transfer_duration_ms_p95": percentile(durations, .95),
        })
    by_key = {(row["scenario_id"], row["mode"]): row for row in rows}
    for row in rows:
        if row["mode"] == "ramp-fixed":
            direct = by_key.get((row["scenario_id"], "direct"))
            if direct:
                base_goodput = direct["goodput_mbps_median"]
                ramp_goodput = row["goodput_mbps_median"]
                base_duration = direct["transfer_duration_ms_median"]
                ramp_duration = row["transfer_duration_ms_median"]
                row["goodput_change_vs_direct_percent"] = (
                    (ramp_goodput / base_goodput - 1) * 100
                    if base_goodput not in (None, 0) and ramp_goodput is not None else None
                )
                row["transfer_duration_change_vs_direct_percent"] = (
                    (ramp_duration / base_duration - 1) * 100
                    if base_duration not in (None, 0) and ramp_duration is not None else None
                )
    return rows

def make_report(manifest, rows):
    lines = [
        "# RAMP Laboratory Experiment Report", "",
        f"- Experiment: {manifest['experiment_id']}",
        f"- Started UTC: {manifest['started_at_utc']}",
        f"- Finished UTC: {manifest.get('finished_at_utc', 'incomplete')}",
        f"- Git revision: {manifest['git_commit']}",
        f"- Payload bytes: {manifest['workload']['payload_bytes']}",
        f"- Repetitions: {manifest['repetitions']}", "",
        "> Results describe this Docker testbed and host only; they are not public-network performance claims.", "",
        "| Scenario | Mode | Runs | Success | Goodput median Mbps | Goodput p95 Mbps | Transfer median ms | Transfer p95 ms | Goodput vs direct % | Duration vs direct % |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in rows:
        f = lambda x: "n/a" if x is None else f"{x:.3f}"
        lines.append(f"| {r['scenario_id']} | {r['mode']} | {r['runs']} | {r['successes']}/{r['runs']} | {f(r['goodput_mbps_median'])} | {f(r['goodput_mbps_p95'])} | {f(r['transfer_duration_ms_median'])} | {f(r['transfer_duration_ms_p95'])} | {f(r.get('goodput_change_vs_direct_percent'))} | {f(r.get('transfer_duration_change_vs_direct_percent'))} |")
    lines += ["", "## Measurement definitions", "",
        "- Goodput = downloaded application bytes * 8 / curl transfer duration.",
        "- curl_time_connect_ms is the peer connection time reported by curl. In RAMP mode, the peer is the local SOCKS5 listener; it is not the RAMP TLS handshake duration.",
        "- NetEm shaping is applied on both router egress interfaces. The configured delay is not the total RTT.",
        "- Failed runs are retained in raw samples and included in the success-rate denominator.", ""]
    return "\n".join(lines)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scenario", action="append", help="scenario ID; repeat to select multiple (default: all)")
    p.add_argument("--repetitions", type=int)
    p.add_argument("--payload-bytes", type=int)
    p.add_argument("--warmup", type=int)
    p.add_argument("--mode", choices=("both", "direct", "ramp-fixed"), default="both")
    p.add_argument("--keep-running", action="store_true")
    p.add_argument("--output-dir", default="laboratory/results")
    a = p.parse_args()
    if shutil.which("docker") is None: p.error("docker CLI is required")
    matrix = json.loads(MATRIX_FILE.read_text(encoding="utf-8"))
    defaults = matrix["defaults"]
    reps = a.repetitions if a.repetitions is not None else defaults["repetitions"]
    warmups = a.warmup if a.warmup is not None else defaults["warmup_repetitions"]
    payload = a.payload_bytes if a.payload_bytes is not None else defaults["payload_bytes"]
    if reps < 1 or warmups < 0 or not 1 <= payload <= 104857600: p.error("invalid repetitions, warmup or payload size")
    by_id = {s["id"]: s for s in matrix["scenarios"]}
    selected = a.scenario or list(by_id)
    unknown = [x for x in selected if x not in by_id]
    if unknown: p.error("unknown scenario(s): " + ", ".join(unknown))

    exp_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    out = ROOT / a.output_dir / dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d") / exp_id
    rawdir = out / "raw"
    rawdir.mkdir(parents=True, exist_ok=False)
    token = os.environ.get("RAMP_TOKEN") or uuid.uuid4().hex + uuid.uuid4().hex
    base_env = os.environ.copy()
    base_env["RAMP_TOKEN"] = token
    certs = ROOT / "deployments/docker/certs"
    if not (certs / "ca.crt").is_file() or not (certs / "server.key").is_file():
        run_command(["sh", "deployments/docker/generate-certs.sh"], env=base_env)

    git = run_command(["git", "rev-parse", "HEAD"], check=False)
    dv = run_command(["docker", "version", "--format", "{{.Server.Version}}"], env=base_env, check=False)
    cv = run_command(["docker", "compose", "version", "--short"], env=base_env, check=False)
    memory_total = None
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                memory_total = int(line.split()[1]) * 1024
                break
    except (OSError, ValueError, IndexError):
        pass
    modes = ["direct", "ramp-fixed"] if a.mode == "both" else [a.mode]
    manifest = {
        "experiment_id": exp_id, "scenario_ids": selected,
        "git_commit": git.stdout.strip() if git.returncode == 0 else "unknown",
        "started_at_utc": utc_now(),
        "host_environment": {"os": platform.platform(), "kernel": platform.release(),
            "processor": platform.processor(), "cpu_count": os.cpu_count(),
            "memory_total_bytes": memory_total, "python": platform.python_version(),
            "docker_server": dv.stdout.strip() if dv.returncode == 0 else "unavailable",
            "docker_compose": cv.stdout.strip() if cv.returncode == 0 else "unavailable"},
        "topology_revision": "docker-lab-v2", "mode": a.mode,
        "repetitions": reps, "warmup_repetitions": warmups,
        "workload": {"destination": "lab-destination:8080", "protocol": "HTTP/1.1", "payload_bytes": payload},
        "network_profiles": [by_id[x] for x in selected],
        "metric_definitions": {"goodput_mbps": "downloaded application bytes * 8 / curl time_total / 1e6",
            "curl_time_connect_ms": "curl connection time to direct destination or local SOCKS5 peer; not TLS handshake"},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    samples = []
    try:
        compose("config", "--quiet", env=base_env)
        print("[1/4] Build and start Docker laboratory", flush=True)
        compose("up", "--build", "-d", env=base_env, timeout=900)
        print("[2/4] Wait for destination and SOCKS5 readiness", flush=True)
        ready = False
        for _ in range(60):
            h = compose("exec", "-T", "destination", "python", "-c",
                "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2)",
                env=base_env, check=False, timeout=10)
            if h.returncode == 0: ready = True; break
            time.sleep(2)
        if not ready: raise RuntimeError("destination health check timed out")
        proxy_ok = False
        for _ in range(30):
            h = compose("exec", "-T", "ramp-client", "curl", "--silent", "--show-error", "--max-time", "4",
                "--socks5-hostname", "127.0.0.1:1080", "http://lab-destination:8080/health",
                env=base_env, check=False, timeout=10)
            if h.returncode == 0 and "ramp-lab-destination-ok" in h.stdout: proxy_ok = True; break
            time.sleep(2)
        if not proxy_ok: raise RuntimeError("RAMP SOCKS5 health request failed")

        total = len(selected)*len(modes)*(warmups+reps)
        n = 0
        with (rawdir / "samples.jsonl").open("w", encoding="utf-8") as raw:
            for sid in selected:
                sc = by_id[sid]
                profile = base_env.copy()
                print(f"[3/4] Apply scenario {sid}", flush=True)
                addr = compose("exec", "-T", "netem-router", "ip", "-o", "-4", "addr", "show", env=profile)
                interfaces = []
                for line in addr.stdout.splitlines():
                    fields = line.split()
                    if len(fields) > 3 and (fields[3].startswith("172.28.10.2/") or fields[3].startswith("172.28.20.2/")):
                        interfaces.append(fields[1].split("@", 1)[0])
                if len(set(interfaces)) != 2:
                    raise RuntimeError(f"expected two router interfaces, found: {interfaces}")
                for iface in sorted(set(interfaces)):
                    compose("exec", "-T", "netem-router", "tc", "qdisc", "del", "dev", iface, "root",
                            env=profile, check=False)
                    tc = ["exec", "-T", "netem-router", "tc", "qdisc", "replace", "dev", iface, "root", "netem"]
                    if sc["delay_ms"] > 0:
                        tc += ["delay", f"{sc['delay_ms']}ms"]
                        if sc["jitter_ms"] > 0:
                            tc += [f"{sc['jitter_ms']}ms"]
                    if sc["loss_percent"] > 0:
                        tc += ["loss", f"{sc['loss_percent']}%"]
                    if sc["rate_mbit"] is not None:
                        tc += ["rate", f"{sc['rate_mbit']}mbit"]
                    if len(tc) > 10:
                        compose(*tc, env=profile)
                q = compose("exec", "-T", "netem-router", "tc", "-s", "qdisc", "show", env=profile, check=False)
                with (rawdir / "qdisc.txt").open("a", encoding="utf-8") as qf:
                    qf.write(f"\n### {sid}\n{q.stdout}\n{q.stderr}\n")
                if q.returncode: raise RuntimeError("tc qdisc inspection failed for " + sid)

                for rep in range(warmups+reps):
                    ordered = modes if rep % 2 == 0 else list(reversed(modes))
                    for mode in ordered:
                        n += 1
                        warmup = rep < warmups
                        url = (f"http://172.28.20.11:8080/payload?bytes={payload}" if mode == "direct"
                               else f"http://lab-destination:8080/payload?bytes={payload}")
                        cmd = ["exec", "-T", "ramp-client", "curl", "--silent", "--show-error",
                            "--output", "/dev/null", "--max-time", str(defaults["max_time_seconds"]),
                            "--write-out", '{"http_code":%{http_code},"time_total":%{time_total},"time_connect":%{time_connect},"time_starttransfer":%{time_starttransfer},"size_download":%{size_download},"speed_download":%{speed_download}}']
                        if mode == "ramp-fixed": cmd += ["--socks5-hostname", "127.0.0.1:1080"]
                        cmd.append(url)
                        start = utc_now()
                        tick = time.perf_counter()
                        res = compose(*cmd, env=profile, check=False, timeout=defaults["max_time_seconds"]+30)
                        runner_ms = (time.perf_counter()-tick)*1000
                        values = {}
                        if res.returncode == 0:
                            try: values = json.loads(res.stdout)
                            except json.JSONDecodeError: values = {}
                        ok = res.returncode == 0 and values.get("http_code") == 200
                        got = int(float(values.get("size_download", 0) or 0))
                        secs = float(values.get("time_total", 0) or 0)
                        sample = {"experiment_id": exp_id, "scenario_id": sid, "mode": mode,
                            "repetition": rep+1, "warmup": warmup, "started_at_utc": start,
                            "finished_at_utc": utc_now(), "success": ok, "exit_code": res.returncode,
                            "http_code": values.get("http_code"), "payload_bytes_expected": payload,
                            "bytes_downloaded": got, "transfer_duration_ms": secs*1000 if secs else None,
                            "runner_elapsed_ms": runner_ms,
                            "curl_time_connect_ms": float(values.get("time_connect",0) or 0)*1000 if values else None,
                            "time_to_first_byte_ms": float(values.get("time_starttransfer",0) or 0)*1000 if values else None,
                            "curl_speed_bytes_per_second": float(values.get("speed_download",0) or 0) if values else None,
                            "goodput_mbps": got*8/secs/1e6 if ok and secs>0 else None,
                            "error": res.stderr.strip() if not ok else None}
                        if not warmup:
                            samples.append(sample)
                            raw.write(json.dumps(sample, ensure_ascii=False)+"\n")
                            raw.flush()
                        print(f"  [{n}/{total}] {mode} rep={rep+1} success={ok} goodput_mbps={sample['goodput_mbps']}", flush=True)

                q_after = compose("exec", "-T", "netem-router", "tc", "-s", "qdisc", "show",
                                  env=profile, check=False)
                with (rawdir / "qdisc.txt").open("a", encoding="utf-8") as qf:
                    qf.write(f"\n### {sid} after workload\n{q_after.stdout}\n{q_after.stderr}\n")
                if q_after.returncode:
                    raise RuntimeError("post-workload qdisc inspection failed for " + sid)

                ps = compose("ps", "-q", "ramp-client", "ramp-bridge", "netem-router", "destination",
                             env=profile, check=False)
                ids = [x.strip() for x in ps.stdout.splitlines() if x.strip()]
                if ids:
                    st = run_command(["docker", "stats", "--no-stream", "--format",
                        "{{.Name}} {{.CPUPerc}} {{.MemUsage}}", *ids], env=profile, check=False)
                    with (rawdir / "container-stats.txt").open("a", encoding="utf-8") as sf:
                        sf.write(f"\n### {sid}\n{st.stdout}\n{st.stderr}\n")

        summaries = summarize(samples)
        manifest["finished_at_utc"] = utc_now()
        manifest["valid_measurement_samples"] = len(samples)
        manifest["successful_measurement_samples"] = sum(1 for x in samples if x["success"])
        manifest["failed_measurement_samples"] = len(samples)-manifest["successful_measurement_samples"]
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
        (out / "summary.json").write_text(json.dumps(summaries, indent=2)+"\n", encoding="utf-8")
        (out / "report.md").write_text(make_report(manifest, summaries), encoding="utf-8")
        print(f"[4/4] Results: {out.relative_to(ROOT)}", flush=True)
        print(f"Successful: {manifest['successful_measurement_samples']}/{len(samples)}", flush=True)
        return 2 if manifest["failed_measurement_samples"] else 0
    finally:
        if not a.keep_running:
            compose("down", "--remove-orphans", env=base_env, check=False, timeout=120)

if __name__ == "__main__":
    try: sys.exit(main())
    except Exception as exc:
        print(f"experiment runner error: {exc}", file=sys.stderr)
        sys.exit(1)
