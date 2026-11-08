$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
python -m vega.runtime
if ($LASTEXITCODE -ne 0) { throw 'Vega dependencies are incomplete. Run powershell -File setup.ps1 and retry.' }
python server.py
