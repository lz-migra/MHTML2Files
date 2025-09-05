# ===================================================================
# 1. VERIFICACIoN E INSTALACIoN DE PYTHON
# ===================================================================
Add-Type -AssemblyName System.Windows.Forms
Write-Host "Verificando instalacion real de Python..."

# Variable para rastrear si Python esta realmente instalado
$isPythonInstalled = $false

# Busca cualquier comando 'python' disponible en el sistema
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue

if ($pythonCommand) {
    # Si encuentra un comando, verifica su ruta de origen.
    # Los stubs de la Microsoft Store estan en una carpeta que contiene "\Microsoft\WindowsApps\".
    # Si la ruta NO contiene esa carpeta, entonces es una instalacion real.
    if ($pythonCommand.Source -notlike "*\Microsoft\WindowsApps\*") {
        $isPythonInstalled = $true
    }
}

# Procede a la instalacion solo si la verificacion fallo
if (-not $isPythonInstalled) {
    Write-Host "No se encontro una instalacion real de Python. Se procedera a la descarga." -ForegroundColor Yellow

    # URL del instalador oficial de Python para Windows 64-bit
    $pythonInstallerUrl = "https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe"
    $pythonInstallerPath = "$env:TEMP\python_installer.exe"

    Write-Host "Descargando instalador de Python..."
    Invoke-WebRequest -Uri $pythonInstallerUrl -OutFile $pythonInstallerPath -UseBasicParsing
    
    Write-Host "Instalando Python silenciosamente... (Esto puede tardar unos minutos)"
    
    # Argumentos para una instalacion silenciosa, para todos los usuarios y agregando Python al PATH
    $installerArgs = "/quiet InstallAllUsers=1 PrependPath=1"
    
    # Inicia el proceso de instalacion y espera a que termine
    Start-Process -FilePath $pythonInstallerPath -ArgumentList $installerArgs -Wait -NoNewWindow
    
    Write-Host "Instalacion de Python completada." -ForegroundColor Green

    # Actualiza la variable de entorno PATH para la sesion actual sin necesidad de reiniciar la terminal
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    Write-Host "PATH actualizado para la sesion actual."
} else {
    Write-Host "Se encontro una instalacion real de Python." -ForegroundColor Green
}


# ===================================================================
# 2. LoGICA ORIGINAL DEL SCRIPT
# ===================================================================
# 📥 Descargar extract_mhtml.py desde GitHub
$scriptUrl = "https://raw.githubusercontent.com/lz-migra/MHTML2Files/refs/heads/main/extract_mhtml.py"
$tempDir = "$env:TEMP\MHTML2Files"
$pythonScript = "$tempDir\extract_mhtml.py"

if (-Not (Test-Path $tempDir)) {
    New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
}

Write-Host "Descargando script de extraccion desde GitHub..."
Invoke-WebRequest -Uri $scriptUrl -OutFile $pythonScript -UseBasicParsing
Write-Host "Script guardado en: $pythonScript"

# 👉 Seleccionar el archivo .mhtml
$openFileDialog = New-Object System.Windows.Forms.OpenFileDialog
$openFileDialog.Filter = "MHTML Files (*.mhtml)|*.mhtml"
$openFileDialog.Title = "Selecciona el archivo MHTML a extraer"

if ($openFileDialog.ShowDialog() -eq "OK") {
    $mhtmlFile = $openFileDialog.FileName
} else {
    Write-Host "No seleccionaste ningun archivo MHTML. Saliendo..."
    exit
}

# 👉 Ejecutar Python con el script descargado
Write-Host "🚀 Ejecutando: python $pythonScript $mhtmlFile"
python "$pythonScript" "$mhtmlFile"
