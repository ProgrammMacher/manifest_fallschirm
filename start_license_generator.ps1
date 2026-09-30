$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$starter = Join-Path $projectRoot 'developer_tools\lizenzgenerator\Lizenzgenerator starten.bat'
if (-not (Test-Path -LiteralPath $starter -PathType Leaf)) {
    throw "Lizenzgenerator-Starter fehlt: $starter"
}
& $starter
exit $LASTEXITCODE
