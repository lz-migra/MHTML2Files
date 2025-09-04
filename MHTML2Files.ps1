Add-Type -AssemblyName System.Windows.Forms

# 📥 Descargar extract_mhtml.py desde GitHub
$scriptUrl = "https://raw.githubusercontent.com/lz-migra/MHTML2Files/refs/heads/main/extract_mhtml.py"
$tempDir = "$env:TEMP\MHTML2Files"
$pythonScript = "$tempDir\extract_mhtml.py"

if (-Not (Test-Path $tempDir)) {
    New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
}

Write-Host "🌐 Descargando script desde GitHub..."
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
