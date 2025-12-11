<#
Fetch heavy assets into ml-inference\models/
Usage (PowerShell):
  .\scripts\fetch_assets.ps1 -baseUrl "https://github.com/TadiKev/ai-cattle-diagnosis/releases/download/v1.0.0"
If you publish a release named v1.0.0 and attach the named assets, this will download them.

Assets expected (change if you named them differently):
  - best_model_state_dict.pth
  - class_map.json
#>

param(
    [string]$baseUrl = "https://github.com/TadiKev/ai-cattle-diagnosis/releases/download/v1.0.0",
    [switch]$force
)

$root = (Resolve-Path .).Path
$targetDir = Join-Path -Path $root -ChildPath "ml-inference\models"

if (-not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
}

$assets = @("best_model_state_dict.pth", "class_map.json")

foreach ($a in $assets) {
    $outPath = Join-Path $targetDir $a
    if ((Test-Path $outPath) -and (-not $force)) {
        Write-Host "Skipping existing $a (use -force to overwrite)"
        continue
    }
    $url = "$baseUrl/$a"
    Write-Host "Downloading $a from $url ..."
    # Use curl.exe available on modern Windows; -L follows redirects
    $args = @("-L", "-o", $outPath, $url)
    $p = Start-Process -FilePath "curl.exe" -ArgumentList $args -NoNewWindow -Wait -PassThru
    if ($p.ExitCode -ne 0) {
        Write-Error "Failed to download $a (exit $($p.ExitCode)). Open $url in browser to check."
        exit 1
    }
    Write-Host "Saved -> $outPath"
}
Write-Host "All done. Model files are in ml-inference\models\"
