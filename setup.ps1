param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program failed with exit code $LASTEXITCODE" }
}
if ($CheckOnly) {
    Invoke-Checked 'python' @('-m', 'vega.runtime')
    exit
}
Invoke-Checked 'python' @('-m', 'pip', 'install', '--target', '.tools/python', '-r', 'requirements-runtime.txt')
$dotnet = Join-Path $PSScriptRoot '.tools/dotnet/dotnet.exe'
if (-not (Test-Path -LiteralPath $dotnet)) {
    & (Join-Path $PSScriptRoot 'integrations/dotnet-install.ps1') -Channel '9.0' -InstallDir (Join-Path $PSScriptRoot '.tools/dotnet')
    if (-not (Test-Path -LiteralPath $dotnet)) { throw '.NET installation did not produce dotnet.exe' }
}
Invoke-Checked 'git' @('submodule', 'update', '--init', '--recursive')
Invoke-Checked $dotnet @('build', 'integrations/Vega.Native.csproj', '-c', 'Release')
Invoke-Checked 'python' @('-m', 'vega.runtime')
