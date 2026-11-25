"""Select a local Windows interface without probing the internet."""
from __future__ import annotations

import ipaddress
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

_QUERY = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$physical = @(Get-NetAdapter -Physical -ErrorAction SilentlyContinue |
    Where-Object Status -eq 'Up' | ForEach-Object ifIndex)
$profiles = @{}
Get-NetConnectionProfile -ErrorAction SilentlyContinue | ForEach-Object {
    $profiles[[int]$_.InterfaceIndex] = [string]$_.NetworkCategory
}
$interfaces = @{}
Get-NetIPInterface -AddressFamily IPv4 | Where-Object ConnectionState -eq 'Connected' |
    ForEach-Object { $interfaces[[int]$_.InterfaceIndex] = $_.InterfaceMetric }
$items = @(Get-NetIPAddress -AddressFamily IPv4 -AddressState Preferred | Where-Object {
    -not $_.SkipAsSource -and $interfaces.ContainsKey([int]$_.InterfaceIndex)
} | ForEach-Object {
    $index = [int]$_.InterfaceIndex
    @{address=$_.IPAddress; prefix=$_.PrefixLength; name=$_.InterfaceAlias;
      physical=($physical -contains $index); metric=$interfaces[$index]; category=$profiles[$index]}
})
ConvertTo-Json -InputObject $items -Compress
"""


@dataclass(frozen=True)
class Adapter:
    address: ipaddress.IPv4Interface
    name: str
    category: str = ""
    physical: bool = False
    metric: int = 0


def parse_adapters(payload: str) -> list[Adapter]:
    candidates: list[Adapter] = []
    for item in json.loads(payload):
        try:
            address = ipaddress.IPv4Interface(f"{item['address']}/{item['prefix']}")
            ip = address.ip
            if (ip.is_loopback or ip.is_link_local or ip.is_unspecified or ip.is_multicast
                    or ip.is_reserved or address.network.prefixlen < 1):
                continue
            candidates.append(Adapter(
                address, str(item["name"]), str(item.get("category") or ""),
                bool(item.get("physical")), int(item.get("metric") or 0),
            ))
        except (KeyError, TypeError, ValueError):
            continue
    candidates.sort(key=lambda item: (not item.physical, item.category == "Public", item.metric))
    # Windows can expose the same IP through more than one interface record.
    unique = {}
    for candidate in candidates:
        unique.setdefault(candidate.address.ip, candidate)
    return list(unique.values())


def find_adapters() -> list[Adapter]:
    executable = Path(os.environ.get("SystemRoot", r"C:\Windows")) / (
        "System32/WindowsPowerShell/v1.0/powershell.exe"
    )
    result = subprocess.run(
        [str(executable), "-NoProfile", "-NonInteractive", "-Command", _QUERY],
        capture_output=True, encoding="utf-8", timeout=10, check=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return parse_adapters(result.stdout)
