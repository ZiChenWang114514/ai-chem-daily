[CmdletBinding()]
param(
    [string]$Repository = "ZiChenWang114514/ai-chem-daily",
    [string]$RemoteHost = "zeus_ts",
    [string]$RemoteRoot = "/data3/zcwang/daily-intelligence-hub/raw",
    [int]$LookbackDays = 14
)

$ErrorActionPreference = "Stop"
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("aix-raw-sync-" + [Guid]::NewGuid().ToString("N"))
$synced = New-Object System.Collections.Generic.List[object]

function Invoke-Native {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Program failed with exit code $LASTEXITCODE"
    }
}

try {
    New-Item -ItemType Directory -Path $tempRoot | Out-Null
    Invoke-Native "gh" @("auth", "status")
    Invoke-Native "ssh" @("-o", "BatchMode=yes", "-o", "ConnectTimeout=10", $RemoteHost, "true")

    $runsJson = & gh run list --repo $Repository --workflow daily.yml --status success --limit 30 --json databaseId,createdAt
    if ($LASTEXITCODE -ne 0) { throw "Unable to list GitHub Actions runs" }
    $cutoff = [DateTimeOffset]::UtcNow.AddDays(-1 * [Math]::Abs($LookbackDays))
    $runs = $runsJson | ConvertFrom-Json | Where-Object { [DateTimeOffset]$_.createdAt -ge $cutoff }

    foreach ($run in $runs) {
        $artifactJson = & gh api ("repos/{0}/actions/runs/{1}/artifacts" -f $Repository, $run.databaseId)
        if ($LASTEXITCODE -ne 0) { throw "Unable to inspect artifacts for run $($run.databaseId)" }
        $artifacts = ($artifactJson | ConvertFrom-Json).artifacts | Where-Object { $_.name -like "raw-aixchem-*" -and -not $_.expired }
        foreach ($artifact in $artifacts) {
            $artifactDir = Join-Path $tempRoot $artifact.name
            if (-not (Test-Path -LiteralPath $artifactDir)) {
                Invoke-Native "gh" @("run", "download", [string]$run.databaseId, "--repo", $Repository, "--name", $artifact.name, "--dir", $artifactDir)
            }
            $manifests = Get-ChildItem -LiteralPath $artifactDir -Recurse -Filter "*.manifest.json"
            foreach ($manifestFile in $manifests) {
                $manifest = Get-Content -LiteralPath $manifestFile.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
                $dataFile = Join-Path $manifestFile.DirectoryName $manifest.data_file

                $year = $manifest.date.Substring(0, 4)
                $month = $manifest.date.Substring(5, 2)
                $remoteDir = "$RemoteRoot/aixchem/$year/$month"
                $remoteData = "$remoteDir/$($manifest.data_file)"
                & ssh $RemoteHost "test -f '$remoteData'"
                if ($LASTEXITCODE -eq 0) { continue }

                Invoke-Native "ssh" @($RemoteHost, "mkdir -p '$remoteDir'")
                Invoke-Native "scp" @($dataFile, "$RemoteHost`:$remoteDir/")
                Invoke-Native "scp" @($manifestFile.FullName, "$RemoteHost`:$remoteDir/")
                $synced.Add([pscustomobject]@{ channel = $manifest.channel; date = $manifest.date; bytes = $manifest.bytes })
            }
        }
    }

    [pscustomobject]@{
        status = "ok"
        remote_root = $RemoteRoot
        synced_count = $synced.Count
        synced = $synced
    } | ConvertTo-Json -Depth 5
}
finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}
