# ===================================================================
# 1. VERIFICACIÓN E INSTALACIÓN DE PYTHON
# ===================================================================
Add-Type -AssemblyName System.Windows.Forms
Write-Host "🔍 Verificando instalación real de Python..."

# Variable para rastrear si Python está realmente instalado
$isPythonInstalled = $false

# Busca cualquier comando 'python' disponible en el sistema
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue

if ($pythonCommand) {
    # Si encuentra un comando, verifica su ruta de origen.
    # Los stubs de la Microsoft Store están en una carpeta que contiene "\Microsoft\WindowsApps\".
    # Si la ruta NO contiene esa carpeta, entonces es una instalación real.
    if ($pythonCommand.Source -notlike "*\Microsoft\WindowsApps\*") {
        $isPythonInstalled = $true
    }
}

# Procede a la instalación solo si la verificación falló
if (-not $isPythonInstalled) {
    Write-Host "❌ No se encontró una instalación real de Python. Se procederá a la descarga." -ForegroundColor Yellow

    # URL del instalador oficial de Python para Windows 64-bit
    $pythonInstallerUrl = "https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe"
    $pythonInstallerPath = "$env:TEMP\python_installer.exe"

    Write-Host "🌐 Descargando instalador de Python..."
    Invoke-WebRequest -Uri $pythonInstallerUrl -OutFile $pythonInstallerPath -UseBasicParsing
    
    Write-Host "⚙️ Instalando Python silenciosamente... (Esto puede tardar unos minutos)"
    
    # Argumentos para una instalación silenciosa, para todos los usuarios y agregando Python al PATH
    $installerArgs = "/quiet InstallAllUsers=1 PrependPath=1"
    
    # Inicia el proceso de instalación y espera a que termine
    Start-Process -FilePath $pythonInstallerPath -ArgumentList $installerArgs -Wait -NoNewWindow
    
    Write-Host "✅ Instalación de Python completada." -ForegroundColor Green

    # Actualiza la variable de entorno PATH para la sesión actual sin necesidad de reiniciar la terminal
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    Write-Host "PATH actualizado para la sesión actual."
} else {
    Write-Host "✅ Se encontró una instalación real de Python." -ForegroundColor Green
}


# ===================================================================
# 2. LÓGICA ORIGINAL DEL SCRIPT
# ===================================================================
# 📥 Descargar extract_mhtml.py desde GitHub
$scriptUrl = "https://raw.githubusercontent.com/lz-migra/MHTML2Files/refs/heads/main/extract_mhtml.py"
$tempDir = "$env:TEMP\MHTML2Files"
$pythonScript = "$tempDir\extract_mhtml.py"

if (-Not (Test-Path $tempDir)) {
    New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
}

Write-Host "🌐 Descargando script de extracción desde GitHub..."
Invoke-WebRequest -Uri $scriptUrl -OutFile $pythonScript -UseBasicParsing
Write-Host "✅ Script guardado en: $pythonScript"

# 👉 Seleccionar el archivo .mhtml
$openFileDialog = New-Object System.Windows.Forms.OpenFileDialog
$openFileDialog.Filter = "MHTML Files (*.mhtml)|*.mhtml"
$openFileDialog.Title = "Selecciona el archivo MHTML a extraer"

if ($openFileDialog.ShowDialog() -eq "OK") {
    $mhtmlFile = $openFileDialog.FileName
} else {
    Write-Host "❌ No seleccionaste ningún archivo MHTML. Saliendo..."
    exit
}

# 👉 Ejecutar Python con el script descargado
Write-Host "🚀 Ejecutando: python $pythonScript $mhtmlFile"
python "$pythonScript" "$mhtmlFile"
