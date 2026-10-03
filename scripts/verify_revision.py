"""Archive/wheel/site association and actual historical suite/probe execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
from sanitize_evidence import portable_json

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def run(args, cwd):
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    env.pop("PYTHONPATH", None)
    process = subprocess.run([str(x) for x in args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    return {"command": [str(x) for x in args], "returncode": process.returncode, "stdout": process.stdout, "stderr": process.stderr}


def verify(revision, probe=None):
    sha = subprocess.check_output(["git", "rev-parse", revision], cwd=ROOT, text=True).strip()
    with tempfile.TemporaryDirectory(prefix="accessdelta-audit-") as folder:
        folder = Path(folder)
        archive, source, wheels, env = folder / "source.zip", folder / "source", folder / "wheels", folder / "env"
        source.mkdir()
        subprocess.check_call(["git", "archive", "--format=zip", f"--output={archive}", sha], cwd=ROOT)
        with zipfile.ZipFile(archive) as data:
            data.extractall(source)
        build = run([sys.executable, "-m", "pip", "wheel", source, "--no-deps", "-w", wheels], folder)
        if build["returncode"]:
            raise RuntimeError(build)
        subprocess.check_call([sys.executable, "-m", "venv", env], cwd=folder)
        python = env / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        wheel = next(wheels.glob("accessdelta-*.whl"))
        install = run([python, "-m", "pip", "install", wheel], folder)
        if install["returncode"]:
            raise RuntimeError(install)
        location = run([python, "-c", "import accessdelta,pathlib,sysconfig,json;print(json.dumps({'package':str(pathlib.Path(accessdelta.__file__).parent),'scripts':sysconfig.get_path('scripts')}))"], folder)
        locations = json.loads(location["stdout"])
        site = Path(locations["package"])
        cli = Path(locations["scripts"]) / ("accessdelta.exe" if sys.platform == "win32" else "accessdelta")
        if not site.is_relative_to(env) or not cli.is_file() or not cli.is_relative_to(env):
            raise RuntimeError("package/registered CLI not associated with fresh environment")
        hashes = {}
        with zipfile.ZipFile(wheel) as contents:
            for module in sorted((source / "src/accessdelta").glob("*.py")):
                relative = module.relative_to(source).as_posix()
                git = subprocess.check_output(["git", "show", f"{sha}:{relative}"], cwd=ROOT)
                values = [digest(git), digest(module.read_bytes()), digest(contents.read(f"accessdelta/{module.name}")), digest((site / module.name).read_bytes())]
                if len(set(values)) != 1:
                    raise RuntimeError(f"Git/archive/wheel/site byte mismatch: {relative}")
                hashes[relative] = values[0]
        report = {"revision": sha, "python": sys.version, "archive_sha256": digest(archive.read_bytes()), "wheel_sha256": digest(wheel.read_bytes()), "module_hashes": hashes, "installed_module": str(site), "build": build, "install": install, "suite": run([python, "-m", "unittest", "discover", "-s", "tests", "-v"], source), "demo": run([python, "scripts/demo.py"], source), "contrast": run([python, "scripts/contrast.py"], source)}
        report.update(source_import_injection=False, installed_package_associated_with_fresh_venv=True, registered_cli_in_sysconfig_scripts=True)
        if (source / "scripts/run_probes.py").exists():
            report["frozen_probes"] = run([python, "scripts/run_probes.py"], source)
        if probe:
            probe = Path(probe).resolve()
            name = probe.relative_to(ROOT).as_posix() if probe.is_relative_to(ROOT) else probe.name
            report["probe"] = {"file": name, "sha256": digest(probe.read_bytes()), "result": run([python, probe], source)}
        return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("revision")
    parser.add_argument("--probe")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = verify(args.revision, args.probe)
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(portable_json(json.dumps(report, indent=2, ensure_ascii=False) + "\n"), encoding="utf-8", newline="\n")
    print(json.dumps({"revision": report["revision"], "suite_rc": report["suite"]["returncode"], "demo_rc": report["demo"]["returncode"], "contrast_rc": report["contrast"]["returncode"], "probe_rc": report.get("probe", {}).get("result", {}).get("returncode"), "output": str(output)}))


if __name__ == "__main__":
    main()
