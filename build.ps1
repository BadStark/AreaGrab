# Build and release script for AreaGrab 1.1.
# Run from the repository root:  pwsh -File build.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "== Tests ==" -ForegroundColor Cyan
python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Tests failed" }

Write-Host "== PyInstaller (onedir) ==" -ForegroundColor Cyan
python -m PyInstaller --noconfirm --workpath build_v11 --distpath dist_final AreaGrab.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

$iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (Test-Path $iscc) {
    Write-Host "== Inno Setup ==" -ForegroundColor Cyan
    & $iscc "$root\areagrab_setup.iss"
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed" }
} else {
    Write-Warning "ISCC.exe not found; installer was not built."
}

Write-Host "== Portable ZIP ==" -ForegroundColor Cyan
$portableRoot = Join-Path $root "Output_v11\portable"
$portableStage = Join-Path $portableRoot "AreaGrab"
if (Test-Path $portableRoot) { Remove-Item $portableRoot -Recurse -Force }
New-Item -ItemType Directory -Force -Path $portableStage | Out-Null
Copy-Item (Join-Path $root "dist_final\AreaGrab\*") $portableStage -Recurse -Force
Copy-Item (Join-Path $root "portable.flag") (Join-Path $portableStage "portable.flag") -Force
Copy-Item (Join-Path $root "README-PORTABLE.txt") (Join-Path $portableStage "README-PORTABLE.txt") -Force
$zip = Join-Path $root "Output_v11\AreaGrab_1.1.0_portable.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path (Join-Path $portableStage "*") -DestinationPath $zip -CompressionLevel Optimal

Write-Host "== Checksums ==" -ForegroundColor Cyan
Get-ChildItem "dist_final\AreaGrab\AreaGrab.exe", "Output_v11\AreaGrab_Setup_1.1.0.exe", "Output_v11\AreaGrab_1.1.0_portable.zip" -ErrorAction SilentlyContinue |
    ForEach-Object {
        $hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
        Write-Host ("{0}  {1}  ({2:N1} MB)" -f $hash, $_.FullName, ($_.Length / 1MB))
    }
