$ErrorActionPreference = 'Stop'

function Get-MachineGuid {
    try {
        return (Get-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Cryptography' -Name MachineGuid).MachineGuid
    } catch {
        return ''
    }
}

function Get-VolumeSerial {
    try {
        $drive = ($env:SystemDrive.TrimEnd(':'))
        $obj = Get-CimInstance -ClassName Win32_LogicalDisk -Filter "DeviceID='$($drive):'"
        if ($obj -and $obj.VolumeSerialNumber) {
            return ($obj.VolumeSerialNumber -replace '[^A-Fa-f0-9]', '').ToUpper()
        }
    } catch {
    }
    return ''
}

$machineGuid = (Get-MachineGuid).ToString().Trim().ToLower()
$volumeSerial = (Get-VolumeSerial).ToString().Trim().ToLower()
$cpu = ($env:PROCESSOR_IDENTIFIER | Out-String).Trim().ToLower()

if ([string]::IsNullOrWhiteSpace($cpu)) {
    $cpu = [Environment]::ProcessorCount.ToString()
}

$joined = "$machineGuid|$volumeSerial|$cpu"
$sha = [System.Security.Cryptography.SHA256]::Create()
$bytes = [System.Text.Encoding]::UTF8.GetBytes($joined)
$hash = $sha.ComputeHash($bytes)
$hex = -join ($hash | ForEach-Object { $_.ToString('x2') })
Write-Output $hex
