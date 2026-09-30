$ErrorActionPreference = 'Stop'

if (-not ('ManifestFingerprintVolume' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;

public static class ManifestFingerprintVolume
{
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool GetVolumeInformation(
        string rootPathName,
        StringBuilder volumeNameBuffer,
        int volumeNameSize,
        out uint volumeSerialNumber,
        out uint maximumComponentLength,
        out uint fileSystemFlags,
        StringBuilder fileSystemNameBuffer,
        int fileSystemNameSize);

    public static string GetSerial(string rootPath)
    {
        uint serial;
        uint maxComponent;
        uint flags;
        bool ok = GetVolumeInformation(rootPath, new StringBuilder(261), 261,
            out serial, out maxComponent, out flags, new StringBuilder(261), 261);
        return ok ? serial.ToString("X8") : "";
    }
}
'@ | Out-Null
}

$machineGuid = ''
try {
    $machineGuid = (Get-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Cryptography' -Name MachineGuid).MachineGuid
} catch {}
$machineGuid = ([string]$machineGuid).Trim().ToLowerInvariant()

$driveRoot = if ($env:SystemDrive) { $env:SystemDrive.TrimEnd(':') + ':\' } else { 'C:\' }
$volumeSerial = [ManifestFingerprintVolume]::GetSerial($driveRoot).Trim().ToLowerInvariant()
$cpu = ([string]$env:PROCESSOR_IDENTIFIER).Trim().ToLowerInvariant()
if ([string]::IsNullOrWhiteSpace($cpu)) {
    try {
        $cpuOutput = & wmic.exe cpu get ProcessorId 2>$null
        $cpu = ([string]($cpuOutput | Where-Object { $_ -and $_ -notmatch 'ProcessorId' } | Select-Object -First 1)).Trim().ToLowerInvariant()
    } catch {}
}

if ([string]::IsNullOrWhiteSpace($machineGuid) -and [string]::IsNullOrWhiteSpace($volumeSerial) -and [string]::IsNullOrWhiteSpace($cpu)) {
    throw 'Windows konnte keine der Fingerprint-Komponenten ermitteln.'
}

$joined = "$machineGuid|$volumeSerial|$cpu"
$sha = [System.Security.Cryptography.SHA256]::Create()
try {
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($joined)
    $fingerprint = -join ($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') })
} finally {
    $sha.Dispose()
}

Write-Host ''
Write-Host 'Maschinen-Fingerprint:' -ForegroundColor Cyan
Write-Host $fingerprint -ForegroundColor White
try {
    Set-Clipboard -Value $fingerprint
    Write-Host 'Fingerprint wurde in die Zwischenablage kopiert.' -ForegroundColor Green
} catch {
    Write-Host 'Automatisches Kopieren nicht möglich; bitte die Zeile markieren und kopieren.' -ForegroundColor Yellow
}