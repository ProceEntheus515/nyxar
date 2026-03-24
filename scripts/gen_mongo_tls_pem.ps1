# Genera data/ssl/nyxar-mongo.pem (clave + certificado autofirmado) para mongo-security.conf / docker-compose.prod.yml.
# Requiere openssl en PATH (incluido en Git for Windows: C:\Program Files\Git\usr\bin).

#Requires -Version 5.1
param(
    [int] $DaysValid = 365,
    [string] $CommonName = "nyxar-mongodb",
    # Sobrescribe nyxar-mongo.pem sin preguntar (util en CI o scripts).
    [switch] $Force
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$sslDir = Join-Path $repoRoot "data\ssl"
$pemPath = Join-Path $sslDir "nyxar-mongo.pem"
$keyPath = Join-Path $sslDir "nyxar-mongo-temp.key"
$crtPath = Join-Path $sslDir "nyxar-mongo-temp.crt"

$openssl = Get-Command openssl -ErrorAction SilentlyContinue
if (-not $openssl) {
    Write-Error "No se encontro openssl en PATH. Instala OpenSSL o Git for Windows y reabre la terminal."
}

New-Item -ItemType Directory -Force -Path $sslDir | Out-Null

if ((Test-Path $pemPath) -and -not $Force) {
    Write-Host "Ya existe $pemPath"
    $r = Read-Host "Sobrescribir? (s/N)"
    if ($r -ne "s" -and $r -ne "S") {
        exit 0
    }
}

# -nodes: clave sin passphrase (mongod lee el PEM sin prompt; en prod usar cert firmado por CA y rotacion).
$subj = "/CN=$CommonName/O=NYXAR/C=AR"
& openssl req -x509 -newkey rsa:4096 -days $DaysValid -nodes `
    -keyout $keyPath -out $crtPath -subj $subj

if ($LASTEXITCODE -ne 0) {
    Remove-Item $keyPath, $crtPath -ErrorAction SilentlyContinue
    Write-Error "openssl fallo con codigo $LASTEXITCODE"
}

try {
    $key = Get-Content -Raw $keyPath
    $crt = Get-Content -Raw $crtPath
    $combined = $key.TrimEnd() + "`n" + $crt.TrimEnd() + "`n"
    Set-Content -Path $pemPath -Value $combined -Encoding ascii
}
finally {
    Remove-Item $keyPath, $crtPath -ErrorAction SilentlyContinue
}

Write-Host "Listo: $pemPath"
Write-Host "Siguiente: docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d"
Write-Host "Ajusta MONGODB_URL con tls=true (ver comentarios en .env.example)."
