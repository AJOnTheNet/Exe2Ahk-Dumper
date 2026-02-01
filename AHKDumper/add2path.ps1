$InstallDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Wrapper = Join-Path $InstallDir "dumper.bat"
$Entry = Join-Path $InstallDir "dumper.py"

Write-Host "[ADMIN] Adding AHKDumper to PATH..."

"@echo off`r`npython `"$Entry`" %*" | Out-File -Encoding ASCII $Wrapper

$CurrentPath = [Environment]::GetEnvironmentVariable(
    "Path",
    [EnvironmentVariableTarget]::Machine
)

if ($CurrentPath -notlike "*$InstallDir*") {
    $NewPath = "$CurrentPath;$InstallDir"
    [Environment]::SetEnvironmentVariable(
        "Path",
        $NewPath,
        [EnvironmentVariableTarget]::Machine
    )
    Write-Host "[ADMIN] PATH updated successfully."
} else {
    Write-Host "[ADMIN] AHKDumper already exists in PATH."
}

Write-Host ""
Write-Host "[ADMIN] Done. You may close this window."