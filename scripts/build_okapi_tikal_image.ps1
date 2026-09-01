# Build the LDW Okapi tikal Docker image (Java 17 + official okapi-apps zip).
param(
    [string]$Tag = "ldw-okapi-tikal:1.48",
    [string]$OkapiVersion = "1.48.0"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$DockerDir = Join-Path $Root "docker\okapi-tikal"
$ZipName = "okapi-apps_gtk2-linux-x86_64_$OkapiVersion.zip"
$ZipPath = Join-Path $DockerDir $ZipName
$Url = "https://okapiframework.org/binaries/main/$OkapiVersion/$ZipName"

if (-not (Test-Path $ZipPath)) {
    Write-Host "Downloading $Url ..."
    Invoke-WebRequest -Uri $Url -OutFile $ZipPath -UseBasicParsing
}

Write-Host "Building $Tag (Okapi $OkapiVersion, $ZipName)..."
docker build `
    --build-arg "OKAPI_VERSION=$OkapiVersion" `
    --build-arg "OKAPI_ZIP=$ZipName" `
    -t $Tag `
    $DockerDir

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Smoke: tikal -info"
docker run --rm $Tag tikal -info
exit $LASTEXITCODE
