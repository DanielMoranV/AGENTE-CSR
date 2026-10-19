<#
.SYNOPSIS
    Aplica controles de aislamiento NTFS para AGENTE-CSR en Windows mediante icacls.
.DESCRIPTION
    Asegura el principio de privilegio mínimo:
    - src/, instrucciones/, conocimiento/: Solo Lectura y Ejecución para el usuario del agente.
    - workspace/: Lectura y Escritura.
    - logs/: Solo Escritura/Append.
    - .env: Acceso denegado a usuarios estándar (restringido a Administradores y Cuenta de Servicio).
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$UsuarioAgente = "$env:USERNAME",

    [Parameter(Mandatory=$false)]
    [string]$RutaBase = "C:\AGENTE-CSR"
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "AGENTE-CSR — Configuración de Permisos NTFS (Principio de Menor Privilegio)" -ForegroundColor Cyan
Write-Host "Usuario objetivo: $UsuarioAgente" -ForegroundColor Yellow
Write-Host "Ruta base:        $RutaBase" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Código, Instrucciones y Conocimiento: SOLO LECTURA
$carpetasSoloLectura = @(
    "$RutaBase\src",
    "$RutaBase\instrucciones",
    "$RutaBase\conocimiento"
)

foreach ($carpeta in $carpetasSoloLectura) {
    if (Test-Path $carpeta) {
        Write-Host "Restringiendo a Solo Lectura: $carpeta" -ForegroundColor Gray
        # Conceder lectura y ejecución (RX)
        icacls $carpeta /grant "${UsuarioAgente}:(OI)(CI)(RX)" /T /C | Out-Null
        # Denegar explícitamente modificación o eliminación
        icacls $carpeta /deny "${UsuarioAgente}:(WD,WEA,WA)" /T /C | Out-Null
    }
}

# 2. Workspace: LECTURA Y ESCRITURA CONTROLADA
$carpetaWorkspace = "$RutaBase\workspace"
if (Test-Path $carpetaWorkspace) {
    Write-Host "Habilitando Lectura/Escritura en: $carpetaWorkspace" -ForegroundColor Green
    icacls $carpetaWorkspace /grant "${UsuarioAgente}:(OI)(CI)(M)" /T /C | Out-Null
}

# 3. Logs: LECTURA Y ESCRITURA
$carpetaLogs = "$RutaBase\logs"
if (Test-Path $carpetaLogs) {
    Write-Host "Habilitando auditoría en: $carpetaLogs" -ForegroundColor Green
    icacls $carpetaLogs /grant "${UsuarioAgente}:(OI)(CI)(M)" /T /C | Out-Null
}

# 4. Archivo de configuración (.env): BLOQUEAR A USUARIOS NO ADMINISTRADORES
$archivoEnv = "$RutaBase\.env"
if (Test-Path $archivoEnv) {
    Write-Host "Protegiendo archivo de secretos: $archivoEnv" -ForegroundColor Yellow
    icacls $archivoEnv /inheritance:r /grant:r "SYSTEM:(F)" /grant:r "Administrators:(F)" /grant:r "${UsuarioAgente}:(R)" /C | Out-Null
}

Write-Host "`n[OK] Permisos NTFS configurados exitosamente." -ForegroundColor Green
