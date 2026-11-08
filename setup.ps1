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

# Keep the two OpenCASCADE distributions isolated, as required by the exporter.
Invoke-Checked 'python' @('-m', 'pip', 'install', '--upgrade', '--target', '.tools/python', '-r', 'requirements-runtime.txt')
Invoke-Checked 'python' @('integrations/install_meshing.py')
Invoke-Checked 'python' @('-m', 'pip', 'install', '--upgrade', '--target', '.tools/cadquery', 'cadquery==2.8.0')
Invoke-Checked 'python' @('-m', 'pip', 'install', '--upgrade', '--target', '.tools/build123d', 'build123d==0.13.0')

$dotnet = Join-Path $PSScriptRoot '.tools/dotnet/dotnet.exe'
if (-not (Test-Path -LiteralPath $dotnet)) {
    & (Join-Path $PSScriptRoot 'integrations/dotnet-install.ps1') -Channel '9.0' -InstallDir (Join-Path $PSScriptRoot '.tools/dotnet')
    if (-not (Test-Path -LiteralPath $dotnet)) { throw '.NET installation did not produce dotnet.exe' }
}
Invoke-Checked 'git' @('submodule', 'update', '--init', '--recursive')
foreach ($source in @('vendor/PicoGK/PicoGK.csproj', 'vendor/ShapeKernel/ShapeKernel')) {
    if (-not (Test-Path -LiteralPath $source)) { throw "Missing upstream source: $source. Restore the vendored sources before building." }
}
Invoke-Checked $dotnet @('build', 'integrations/Vega.Native.csproj', '-c', 'Release')
Invoke-Checked 'python' @('-m', 'vega.runtime')
