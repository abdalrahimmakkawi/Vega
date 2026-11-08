param([switch]$InstallAnsysClients)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
python integrations/install_meshing.py
if ($LASTEXITCODE -ne 0) { throw 'Gmsh installation failed' }
# Uses the existing Ubuntu distribution. Does not install WSL or reboot Windows.
wsl -d Ubuntu-22.04 -u root -- bash -lc 'export DEBIAN_FRONTEND=noninteractive; apt-get update && apt-get install -y --no-install-recommends openfoam calculix-ccx'
if ($LASTEXITCODE -ne 0) { throw 'WSL solver installation failed' }
if ($InstallAnsysClients) {
    python -m pip install --upgrade --target .tools/ansys -r requirements-ansys.txt
    if ($LASTEXITCODE -ne 0) { throw 'Ansys connector installation failed' }
}
python -m vega.meshing.solvers --probe
