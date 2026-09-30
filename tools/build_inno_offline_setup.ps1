param(
    [string]$ProjectRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Test-IsccReady {
    param([Parameter(Mandatory = $true)][string]$IsccPath)

    if (-not (Test-Path -LiteralPath $IsccPath -PathType Leaf)) {
        return $false
    }

    $isccDir = Split-Path -Parent $IsccPath
    $compilerDll = Join-Path $isccDir 'ISCmplr.dll'
    $languagesDir = Join-Path $isccDir 'Languages'
    if (-not (Test-Path -LiteralPath $compilerDll -PathType Leaf)) {
        return $false
    }
    if (-not (Test-Path -LiteralPath $languagesDir -PathType Container)) {
        return $false
    }

    return $true
}

function Sync-InnoCompilerFiles {
    param(
        [Parameter(Mandatory = $true)][string]$SourceDir,
        [Parameter(Mandatory = $true)][string]$TargetDir
    )

    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null

    $includePatterns = @('*.exe', '*.dll', '*.e32', '*.issig', '*.isl', '*.iss', '*.bmp')
    foreach ($pattern in $includePatterns) {
        Get-ChildItem -Path $SourceDir -Filter $pattern -File -ErrorAction SilentlyContinue |
            ForEach-Object {
                Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $TargetDir $_.Name) -Force
            }
    }

    $sourceLanguages = Join-Path $SourceDir 'Languages'
    $targetLanguages = Join-Path $TargetDir 'Languages'
    if (Test-Path -LiteralPath $sourceLanguages -PathType Container) {
        if (Test-Path -LiteralPath $targetLanguages) {
            Remove-Item -LiteralPath $targetLanguages -Recurse -Force
        }
        Copy-Item -LiteralPath $sourceLanguages -Destination $targetLanguages -Recurse -Force
    }
}

function Test-FileReadable {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $false
    }

    try {
        $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
        $stream.Close()
        return $true
    }
    catch {
        return $false
    }
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

function Get-LatestReadableCompiledZip {
    param([Parameter(Mandatory = $true)][string]$BuildDir)

    $zips = Get-ChildItem (Join-Path $BuildDir 'manifest_offline_compiled_installer_*.zip') -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending

    foreach ($zip in $zips) {
        if (Test-FileReadable -Path $zip.FullName) {
            return $zip
        }
        Write-Warning "Ueberspringe gesperrte ZIP-Datei: $($zip.FullName)"
    }

    return $null
}

function Assert-InstallerStageSafe {
    param([Parameter(Mandatory = $true)][string]$StageRoot)

    $requiredFiles = @(
        'app\__init__.pyc',
        'app\services\neutral_install_seed.pyc',
        'app\security\license_public_key.pem',
        'migrations\env.pyc',
        'manifest_launcher.pyc',
        'run_migrations.pyc',
        'runtime\python\python.exe',
        'runtime\python\pythonw.exe',
        'runtime\gtk\bin\libcairo-2.dll',
        'setup_start_manifest.bat',
        'start_manifest_prod.bat',
        'start_manifest_prod.vbs',
        'tools\license\install_runtime_secrets.py',
        'requirements.txt'
    )

    foreach ($relativePath in $requiredFiles) {
        $path = Join-Path $StageRoot $relativePath
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Required installer stage file is missing: $relativePath"
        }
    }

    $wheelhouse = Join-Path $StageRoot 'packages'
    if (-not (Test-Path -LiteralPath $wheelhouse -PathType Container) -or
        -not (Get-ChildItem -LiteralPath $wheelhouse -Filter '*.whl' -File -ErrorAction SilentlyContinue)) {
        throw 'Installer stage has no offline wheels in packages/.'
    }

    $forbiddenPatterns = @(
        '^data/',
        '(^|/)runtime/(data|logs|session_data|uploads|secrets)/',
        '(^|/)logs/',
        '(^|/)session_data/',
        '(^|/)uploads/',
        '(^|/)noch_zu_loeschen/',
        '(^|/)developer_tools/',
        '(^|/)tools/license/(?!install_runtime_secrets\.py$)[^/]+$',
        '(^|/)generate_license_(key|bundle)\.pyc?$',
        '(^|/)initialize_signing_key\.pyc?$',
        '(^|/)license_signing\.pyc?$',
        '\.(dpapi|p12|pfx)$',
        '(^|/)[^/]*private[^/]*\.(pem|key)$',
        '(^|/)app_settings\.json$',
        '(^|/)auth_config\.json$',
        '\.(db|sqlite|sqlite3)$',
        '\.log$',
        '(^|/)runtime/gtk/var/cache/'
    )

    foreach ($file in Get-ChildItem -Path $StageRoot -Recurse -File -Force) {
        $relativePath = (Get-RelativePath -BasePath $StageRoot -TargetPath $file.FullName).Replace('\', '/')
        foreach ($pattern in $forbiddenPatterns) {
            if ($relativePath -match $pattern) {
                throw "Forbidden local/runtime data in installer stage: $relativePath"
            }
        }

        if ($file.Extension -ieq '.pem') {
            $pemHeader = Get-Content -LiteralPath $file.FullName -TotalCount 1 -ErrorAction Stop
            if ($pemHeader -match 'PRIVATE KEY') {
                throw "Private key material in installer stage: $relativePath"
            }
        }
    }
}

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)

$buildDir = Join-Path $ProjectRoot 'build'
$buildStamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
$stageDir = Join-Path $buildDir ("inno_stage_{0}_{1}" -f $buildStamp, $PID)
$installerOut = Join-Path $buildDir 'installer'
$issFile = Join-Path $ProjectRoot 'installer\inno\manifest_offline_setup.iss'
$isccCandidates = @(
    'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
    'C:\Program Files\Inno Setup 6\ISCC.exe',
    (Join-Path $ProjectRoot 'tools\inno\ISCC.exe')
)
$isccExe = $isccCandidates | Where-Object {
    Test-IsccReady -IsccPath $_
} | Select-Object -First 1
$iconBuildScript = Join-Path $ProjectRoot 'tools\build_manifest_icon.py'
$runtimePython = Join-Path $ProjectRoot 'runtime\python\python.exe'

New-Item -ItemType Directory -Path $buildDir -Force | Out-Null
$lockPath = Join-Path $buildDir '.inno_build.lock'
try {
    $buildLock = [System.IO.File]::Open(
        $lockPath,
        [System.IO.FileMode]::OpenOrCreate,
        [System.IO.FileAccess]::ReadWrite,
        [System.IO.FileShare]::None
    )
}
catch {
    throw "Ein anderer Installer-Build laeuft bereits. Bitte warten und dann erneut starten."
}

try {
    if ((Test-Path -Path $iconBuildScript -PathType Leaf) -and (Test-Path -Path $runtimePython -PathType Leaf)) {
        & $runtimePython $iconBuildScript | Out-Null
    }

    if (-not $isccExe) {
        throw "Inno Setup Compiler nicht lauffaehig. Erwartet wird eine vollstaendige Compiler-Umgebung (inkl. ISCC.exe/ISCmplr.dll/Languages)."
    }
    Write-Host "Verwende Inno-Compiler: $isccExe"

    if (-not (Test-Path -LiteralPath $issFile -PathType Leaf)) {
        throw "Inno Setup Script fehlt: $issFile"
    }

    Write-Host 'Erzeuge frisches compiled ZIP fuer den Installer-Build...'
    & (Join-Path $ProjectRoot 'tools\build_offline_compiled_installer_zip.ps1')
    if ($LASTEXITCODE -ne 0) {
        throw 'Compiled ZIP konnte nicht erzeugt werden.'
    }

    $compiledZip = Get-LatestReadableCompiledZip -BuildDir $buildDir

    if (-not $compiledZip) {
        throw 'Kein lesbares compiled ZIP verfuegbar.'
    }

    New-Item -ItemType Directory -Path $stageDir -Force | Out-Null
    New-Item -ItemType Directory -Path $installerOut -Force | Out-Null

    try {
        Expand-Archive -Path $compiledZip.FullName -DestinationPath $stageDir -Force
    }
    catch {
        Write-Warning "Konnte ZIP nicht entpacken: $($compiledZip.FullName)"
        Write-Warning "Versuche neues compiled ZIP zu erzeugen..."
        & (Join-Path $ProjectRoot 'tools\build_offline_compiled_installer_zip.ps1')
        if ($LASTEXITCODE -ne 0) {
            throw 'Compiled ZIP konnte nicht neu erzeugt werden.'
        }

        $compiledZip = Get-LatestReadableCompiledZip -BuildDir $buildDir
        if (-not $compiledZip) {
            throw 'Kein lesbares compiled ZIP verfuegbar.'
        }

        Expand-Archive -Path $compiledZip.FullName -DestinationPath $stageDir -Force
    }

    # Aktuelle Startskripte aus dem Projekt immer bevorzugen,
    # damit keine veralteten Skripte aus einem älteren ZIP im Installer landen.
    $runtimeScripts = @(
        'setup_start_manifest.bat',
        'start_manifest_prod.bat',
        'start_manifest_prod.vbs'
    )
    foreach ($scriptName in $runtimeScripts) {
        $src = Join-Path $ProjectRoot $scriptName
        $dst = Join-Path $stageDir $scriptName
        if (Test-Path -LiteralPath $src -PathType Leaf) {
            Copy-Item -LiteralPath $src -Destination $dst -Force
        }
    }

    # Nur der Runtime-Provisionierer wird ausgeliefert; Generator/Signer bleiben lokal.
    $licenseToolsTarget = Join-Path $stageDir 'tools\license'
    New-Item -ItemType Directory -Path $licenseToolsTarget -Force | Out-Null
    $installSecretsSource = Join-Path $ProjectRoot 'tools\license\install_runtime_secrets.py'
    if (-not (Test-Path -LiteralPath $installSecretsSource -PathType Leaf)) {
        throw "Runtime-Secrets-Provisionierer fehlt: $installSecretsSource"
    }
    Copy-Item -LiteralPath $installSecretsSource -Destination (Join-Path $licenseToolsTarget 'install_runtime_secrets.py') -Force

    $taskbarPinScriptSrc = Join-Path $ProjectRoot 'tools\pin_taskbar.ps1'
    $taskbarPinScriptDst = Join-Path $stageDir 'tools\pin_taskbar.ps1'
    if (Test-Path -LiteralPath $taskbarPinScriptSrc -PathType Leaf) {
        $taskbarPinDir = Split-Path -Parent $taskbarPinScriptDst
        New-Item -ItemType Directory -Path $taskbarPinDir -Force | Out-Null
        Copy-Item -LiteralPath $taskbarPinScriptSrc -Destination $taskbarPinScriptDst -Force
    }

    Assert-InstallerStageSafe -StageRoot $stageDir

    Write-Host "Kompiliere Inno Setup mit: $isccExe"
    Write-Host "Stage-Verzeichnis: $stageDir"
    $isccArgs = @(
        "/DStageDir=$stageDir",
        $issFile
    )
    $isccProcess = Start-Process -FilePath $isccExe -ArgumentList $isccArgs -NoNewWindow -Wait -PassThru
    if ($isccProcess.ExitCode -ne 0) {
        throw "Inno Setup Build fehlgeschlagen (Exit-Code $($isccProcess.ExitCode))."
    }

    $primaryInstaller = Join-Path $installerOut 'manifest_ou_1_2.exe'
    $legacyInstaller = Join-Path $installerOut 'manifest_ou.exe'
    if (-not (Test-Path -LiteralPath $primaryInstaller -PathType Leaf)) {
        throw "Primaerer Installer fehlt nach dem Build: $primaryInstaller"
    }
    if (Test-Path -LiteralPath $legacyInstaller -PathType Leaf) {
        Remove-Item -LiteralPath $legacyInstaller -Force
    }

    Write-Host ''
    Write-Host 'Offline-Setup erfolgreich erstellt.'
    Write-Host "Installer: $primaryInstaller"
    Write-Host "Output-Ordner: $installerOut"
}
finally {
    if ($buildLock) {
        $buildLock.Close()
        $buildLock.Dispose()
    }

    if (Test-Path -LiteralPath $stageDir) {
        try {
            Remove-Item -LiteralPath $stageDir -Recurse -Force
        }
        catch {
            Write-Warning "Konnte Stage-Verzeichnis nicht komplett entfernen: $stageDir"
        }
    }
}
