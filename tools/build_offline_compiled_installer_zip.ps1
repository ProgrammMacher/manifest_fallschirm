param(
    [string]$ProjectRoot,
    [string]$OutputDir
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Resolve-InsideRoot {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$RelativePath
    )

    $candidate = [System.IO.Path]::GetFullPath((Join-Path $Root $RelativePath))
    $rootFull = [System.IO.Path]::GetFullPath($Root)
    if (-not $candidate.StartsWith($rootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Pfad ausserhalb des Projektordners ist nicht erlaubt: $RelativePath"
    }
    return $candidate
}

function Get-RelativePath {
    param(
        [Parameter(Mandatory = $true)][string]$BasePath,
        [Parameter(Mandatory = $true)][string]$TargetPath
    )

    $base = [System.IO.Path]::GetFullPath($BasePath)
    $target = [System.IO.Path]::GetFullPath($TargetPath)

    if (-not $base.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
        $base = $base + [System.IO.Path]::DirectorySeparatorChar
    }

    $baseUri = New-Object System.Uri($base)
    $targetUri = New-Object System.Uri($target)
    $relativeUri = $baseUri.MakeRelativeUri($targetUri)
    return [System.Uri]::UnescapeDataString($relativeUri.ToString()).Replace('/', '\')
}

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
    throw "Projektordner nicht gefunden: $ProjectRoot"
}

$runtimePython = Resolve-InsideRoot -Root $ProjectRoot -RelativePath 'runtime\python\python.exe'
if (-not (Test-Path -LiteralPath $runtimePython -PathType Leaf)) {
    throw "Lokale Runtime-Python fehlt: $runtimePython"
}

$wheelhouseValidationScript = Resolve-InsideRoot -Root $ProjectRoot -RelativePath 'tools\validate_offline_wheelhouse.py'
& $runtimePython $wheelhouseValidationScript --project-root $ProjectRoot --python $runtimePython
if ($LASTEXITCODE -ne 0) {
    throw 'Offline-Wheelhouse-Pruefung fehlgeschlagen. Build abgebrochen.'
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $ProjectRoot 'build'
}
$OutputDir = [System.IO.Path]::GetFullPath($OutputDir)

if (-not (Test-Path -LiteralPath $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
$packageName = "manifest_offline_compiled_installer_$timestamp"
$stagingRoot = Join-Path $OutputDir $packageName
$zipPath = Join-Path $OutputDir ($packageName + '.zip')

if (Test-Path -LiteralPath $stagingRoot) {
    Remove-Item -LiteralPath $stagingRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $stagingRoot | Out-Null

if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

$includeDirs = @(
    'app',
    'runtime',
    'packages',
    'migrations',
    'data'
)

$includeFiles = @(
    'setup_start_manifest.bat',
    'start_manifest_prod.bat',
    'start_manifest_prod.vbs',
    'diagnose_pdf_runtime.bat',
    'manifest_launcher.py',
    'run_migrations.py',
    'requirements.txt',
    'MANUAL_setup_start_manifest.md',
    'error_response.html'
)

$excludeGlobs = @(
    'app/session_data/**',
    'app/uploads/**',
    'data/archive/**',
    'data/backup/**',
    'data/temp/**',
    'logs/**',
    '__pycache__/**',
    '*.pyc',
    '*.pyo',
    '*.log'
)

foreach ($relativeDir in $includeDirs) {
    $sourceDir = Resolve-InsideRoot -Root $ProjectRoot -RelativePath $relativeDir
    if (-not (Test-Path -LiteralPath $sourceDir -PathType Container)) {
        Write-Warning "Include-Ordner fehlt und wird uebersprungen: $relativeDir"
        continue
    }

    $targetDir = Join-Path $stagingRoot $relativeDir
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null

    $allFiles = Get-ChildItem -Path $sourceDir -Recurse -File -Force
    foreach ($file in $allFiles) {
        $relativeFromRoot = (Get-RelativePath -BasePath $ProjectRoot -TargetPath $file.FullName).Replace('\', '/')
        $isExcluded = $false
        foreach ($pattern in $excludeGlobs) {
            if ($relativeFromRoot -like $pattern) {
                $isExcluded = $true
                break
            }
        }
        if ($isExcluded) {
            continue
        }

        $targetFile = Join-Path $stagingRoot $relativeFromRoot
        $targetFileDir = Split-Path -Parent $targetFile
        if (-not (Test-Path -LiteralPath $targetFileDir)) {
            New-Item -ItemType Directory -Path $targetFileDir -Force | Out-Null
        }
        Copy-Item -LiteralPath $file.FullName -Destination $targetFile -Force
    }
}

foreach ($relativeFile in $includeFiles) {
    $sourceFile = Resolve-InsideRoot -Root $ProjectRoot -RelativePath $relativeFile
    if (-not (Test-Path -LiteralPath $sourceFile -PathType Leaf)) {
        Write-Warning "Include-Datei fehlt und wird uebersprungen: $relativeFile"
        continue
    }

    $targetFile = Join-Path $stagingRoot $relativeFile
    $targetDir = Split-Path -Parent $targetFile
    if (-not (Test-Path -LiteralPath $targetDir)) {
        New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    }
    Copy-Item -LiteralPath $sourceFile -Destination $targetFile -Force
}

$stagingPython = Join-Path $stagingRoot 'runtime\python\python.exe'
if (-not (Test-Path -LiteralPath $stagingPython -PathType Leaf)) {
    throw "Lokale Runtime-Python fehlt im Staging: $stagingPython"
}

$compileTargets = @(
    (Join-Path $stagingRoot 'app'),
    (Join-Path $stagingRoot 'migrations'),
    (Join-Path $stagingRoot 'manifest_launcher.py'),
    (Join-Path $stagingRoot 'run_migrations.py')
)

foreach ($target in $compileTargets) {
    if (Test-Path -LiteralPath $target) {
        & $stagingPython -m compileall -q -b $target
        if ($LASTEXITCODE -ne 0) {
            throw "Kompilierung fehlgeschlagen fuer: $target"
        }
    }
}

$pythonSourcePaths = @(
    (Join-Path $stagingRoot 'app'),
    (Join-Path $stagingRoot 'migrations'),
    (Join-Path $stagingRoot 'manifest_launcher.py'),
    (Join-Path $stagingRoot 'run_migrations.py')
)

$removedPyCount = 0
foreach ($path in $pythonSourcePaths) {
    if (-not (Test-Path -LiteralPath $path)) {
        continue
    }

    $item = Get-Item -LiteralPath $path
    if ($item.PSIsContainer) {
        $pyFiles = Get-ChildItem -Path $path -Recurse -Filter '*.py' -File -Force
        foreach ($pyFile in $pyFiles) {
            Remove-Item -LiteralPath $pyFile.FullName -Force
            $removedPyCount++
        }
    } else {
        if ($item.Extension -ieq '.py') {
            Remove-Item -LiteralPath $item.FullName -Force
            $removedPyCount++
        }
    }
}

$metaFile = Join-Path $stagingRoot 'OFFLINE_COMPILED_INSTALLER_CONTENTS.txt'
@(
    "Paket: $packageName"
    "Erstellt: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    "Projektordner: $ProjectRoot"
    "Entfernte .py-Dateien: $removedPyCount"
    ''
    'Include-Ordner:'
    ($includeDirs | ForEach-Object { "- $_" })
    ''
    'Include-Dateien:'
    ($includeFiles | ForEach-Object { "- $_" })
    ''
    'Exclude-Muster:'
    ($excludeGlobs | ForEach-Object { "- $_" })
    ''
    'Hinweis:'
    '- App- und Migrations-Quellcode wurde zu .pyc kompiliert und als .py entfernt.'
) | Set-Content -Path $metaFile -Encoding UTF8

Compress-Archive -Path (Join-Path $stagingRoot '*') -DestinationPath $zipPath -CompressionLevel Optimal -Force

$zipItem = Get-Item -LiteralPath $zipPath
$sizeMB = [math]::Round(($zipItem.Length / 1MB), 2)

Write-Host ''
Write-Host 'Offline-COMPILED-Installer-ZIP erfolgreich erstellt.'
Write-Host "ZIP: $zipPath"
Write-Host "Groesse: $sizeMB MB"
Write-Host "Staging: $stagingRoot"
Write-Host "Entfernte .py-Dateien: $removedPyCount"
Write-Host ''
Write-Host 'Hinweis: Das Skript verwendet ausschliesslich Pfade innerhalb des Projektordners und keinen Internetzugriff.'