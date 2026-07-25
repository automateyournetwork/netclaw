#!/usr/bin/env python3
# NetClaw Convergence — Ookla speedtest runner (T072 full stack)
# Pure-stdlib. Mirrors k3s-observability-stack/k8s/observability/speedtest.yml
# runner logic, adapted to loop on an interval instead of a K8s CronJob since
# Docker Compose has no native cron primitive.
import io, json, os, platform, subprocess, tarfile, time, urllib.request, urllib.parse

OOKLA_VERSION = os.environ.get("OOKLA_VERSION", "1.2.0")
PUSHGW = os.environ.get("PUSHGATEWAY_URL", "http://pushgateway:9091")
SITE = os.environ.get("SITE_LABEL", "home")
INTERVAL_SECONDS = int(os.environ.get("SPEEDTEST_INTERVAL_SECONDS", str(60 * 60)))  # default hourly
SERVER_ID = os.environ.get("SPEEDTEST_SERVER_ID", "")  # empty = Ookla auto-nearest


def arch():
    m = platform.machine().lower()
    return {"x86_64": "x86_64", "amd64": "x86_64", "aarch64": "aarch64", "arm64": "aarch64"}.get(m, m)


def ensure_cli():
    dst = "/tmp/speedtest"
    if os.path.exists(dst):
        return dst
    url = f"https://install.speedtest.net/app/cli/ookla-speedtest-{OOKLA_VERSION}-linux-{arch()}.tgz"
    print("downloading Ookla CLI:", url, flush=True)
    data = urllib.request.urlopen(url, timeout=90).read()
    tf = tarfile.open(fileobj=io.BytesIO(data))
    open(dst, "wb").write(tf.extractfile("speedtest").read())
    os.chmod(dst, 0o755)
    return dst


def esc(v):
    return str(v).replace("\\", "\\\\").replace('"', '\\"')


def push(metrics):
    lbl = f'site="{esc(SITE)}",server_id="{esc(SERVER_ID)}"'
    body = "\n".join(f"{n}{{{lbl}}} {v}" for n, v in metrics) + "\n"
    url = f"{PUSHGW}/metrics/job/speedtest/instance/{urllib.parse.quote(SITE)}"
    req = urllib.request.Request(url, data=body.encode(), method="PUT", headers={"Content-Type": "text/plain"})
    urllib.request.urlopen(req, timeout=30)


def run_once(cli):
    cmd = [cli, "-f", "json", "--accept-license", "--accept-gdpr"]
    if SERVER_ID:
        cmd += ["-s", SERVER_ID]
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=240, text=True)
        if out.returncode != 0:
            return None, (out.stderr or out.stdout).strip()[:200]
        return json.loads(out.stdout), None
    except Exception as e:
        return None, str(e)[:200]


def main():
    cli = ensure_cli()
    while True:
        res, err = run_once(cli)
        if res is None:
            print(f"speedtest FAILED: {err}", flush=True)
            try:
                push([("speedtest_up", 0)])
            except Exception as pe:
                print("pushgateway push failed:", pe, flush=True)
        else:
            dl = res["download"]["bandwidth"] * 8
            ul = res["upload"]["bandwidth"] * 8
            ping = res["ping"]["latency"]
            metrics = [
                ("speedtest_up", 1),
                ("speedtest_download_bits_per_second", dl),
                ("speedtest_upload_bits_per_second", ul),
                ("speedtest_ping_latency_ms", ping),
                ("speedtest_ping_jitter_ms", res["ping"].get("jitter", 0)),
                ("speedtest_packet_loss_pct", res.get("packetLoss", 0)),
                ("speedtest_data_used_bytes", res["download"].get("bytes", 0) + res["upload"].get("bytes", 0)),
                ("speedtest_result_timestamp", int(time.time())),
            ]
            print(f"speedtest OK down={dl/1e6:.1f}Mbps up={ul/1e6:.1f}Mbps ping={ping}ms", flush=True)
            try:
                push(metrics)
            except Exception as pe:
                print("pushgateway push failed:", pe, flush=True)
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
