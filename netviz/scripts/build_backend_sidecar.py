from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def detect_default_target() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "windows":
        return "x86_64-pc-windows-msvc"

    if system == "darwin":
        return (
            "aarch64-apple-darwin"
            if machine in {"arm64", "aarch64"}
            else "x86_64-apple-darwin"
        )

    if system == "linux":
        return (
            "aarch64-unknown-linux-gnu"
            if machine in {"arm64", "aarch64"}
            else "x86_64-unknown-linux-gnu"
        )

    raise RuntimeError(f"Unsupported host platform: {platform.platform()}")


def executable_name(sidecar_name: str, target: str) -> str:
    return f"{sidecar_name}.exe" if "windows" in target else sidecar_name


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and stage the NetViz backend sidecar")
    parser.add_argument(
        "--target",
        default=None,
        help="Rust target triple used by Tauri (defaults to the current host triple)",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    backend_dir = project_root / "backend"
    output_dir = project_root / "src-tauri" / "binaries"
    target = args.target or detect_default_target()
    sidecar_name = f"netviz-backend-{target}"

    env = os.environ.copy()
    env["NETVIZ_SIDECAR_NAME"] = sidecar_name
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "netviz-backend.spec",
    ]
    subprocess.run(command, cwd=backend_dir, check=True, env=env)

    built_binary = backend_dir / "dist" / executable_name(sidecar_name, target)
    if not built_binary.exists():
        raise FileNotFoundError(f"Expected PyInstaller output was not found: {built_binary}")

    output_dir.mkdir(parents=True, exist_ok=True)
    staged_binary = output_dir / built_binary.name
    shutil.copy2(built_binary, staged_binary)

    print(f"Built backend sidecar for {target}: {staged_binary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
