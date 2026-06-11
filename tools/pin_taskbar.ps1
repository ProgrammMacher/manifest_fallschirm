param(
    [Parameter(Mandatory = $true)]
    [string]$TargetPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-TaskbarPin {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $false
    }

    try {
        $shell = New-Object -ComObject Shell.Application
        $folderPath = Split-Path -Parent $Path
        $fileName = Split-Path -Leaf $Path
        $folder = $shell.Namespace($folderPath)
        if (-not $folder) {
            return $false
        }

        $item = $folder.ParseName($fileName)
        if (-not $item) {
            return $false
        }

        $verbs = @($item.Verbs())
        foreach ($verb in $verbs) {
            $rawName = [string]$verb.Name
            $cleanName = ($rawName -replace '&', '').Trim().ToLowerInvariant()
            if (
                $cleanName -match 'taskbarpin|pintotaskbar|pin to taskbar|an taskleiste|an die taskleiste'
            ) {
                $verb.DoIt()
                return $true
            }
        }

        return $false
    }
    catch {
        return $false
    }
}

# Best-effort only: installation must not fail if pinning is unavailable.
$null = Invoke-TaskbarPin -Path $TargetPath
exit 0
