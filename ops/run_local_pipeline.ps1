param(
    [switch]$SkipPush,
    [switch]$SkipPull,
    [switch]$SkipCollection
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$SettingsPath = Join-Path $RepoRoot "config\local.settings.psd1"
$RunRoot = Join-Path $RepoRoot "work\local-pipeline"
$RawRoot = Join-Path $RepoRoot "work\raw"
$PromptPath = Join-Path $RepoRoot "ops\codex\aixchem_curation_prompt.md"
$SchemaPath = Join-Path $RepoRoot "ops\codex\aixchem_curation.schema.json"

$Settings = @{
    Days = 3
    Limit = 16
    Model = "gpt-5.6-sol"
}
if (Test-Path -LiteralPath $SettingsPath) {
    $LocalSettings = Import-PowerShellDataFile -LiteralPath $SettingsPath
    foreach ($Key in $LocalSettings.Keys) {
        $Settings[$Key] = $LocalSettings[$Key]
    }
}

$Python = (Get-Command python -ErrorAction Stop).Source
$CodexCommand = (Get-Command codex.cmd -ErrorAction Stop).Source
$CodexRoot = Split-Path $CodexCommand -Parent
$CodexJavaScript = Join-Path $CodexRoot "node_modules\@openai\codex\bin\codex.js"
$Node = (Get-Command node.exe -ErrorAction Stop).Source
$Git = (Get-Command git -ErrorAction Stop).Source

New-Item -ItemType Directory -Force -Path $RunRoot, $RawRoot | Out-Null
$StartedAt = Get-Date

Push-Location $RepoRoot
try {
    if (-not $SkipPull) {
        & $Git pull --ff-only origin main
        if ($LASTEXITCODE -ne 0) { throw "git pull failed" }
    }

    if (-not $SkipCollection) {
        $DigestArgs = @(
            "backend/daily_digest.py",
            "--site-root", "public",
            "--raw-root", $RawRoot,
            "--days", [string]$Settings.Days,
            "--limit", [string]$Settings.Limit
        )
        & $Python @DigestArgs
        if ($LASTEXITCODE -ne 0) { throw "daily metadata collection failed" }
    }

    $Latest = Get-Content -LiteralPath (Join-Path $RepoRoot "public\data\latest.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    $DigestDate = [string]$Latest.date
    $CurationPath = Join-Path $RunRoot "$DigestDate-curation.json"
    $CodexLogPath = Join-Path $RunRoot "$DigestDate-codex-output.txt"
    $CodexErrorPath = Join-Path $RunRoot "$DigestDate-codex-error.txt"

    $CodexArgs = @(
        "exec",
        "--ephemeral",
        "--sandbox", "read-only",
        "--color", "never",
        "--model", [string]$Settings.Model,
        "-C", $RepoRoot,
        "--output-schema", $SchemaPath,
        "--output-last-message", $CurationPath,
        "-"
    )
    $CodexInvocationArgs = @($CodexJavaScript) + $CodexArgs
    $CodexProcess = Start-Process `
        -FilePath $Node `
        -ArgumentList $CodexInvocationArgs `
        -WorkingDirectory $RepoRoot `
        -RedirectStandardInput $PromptPath `
        -RedirectStandardOutput $CodexLogPath `
        -RedirectStandardError $CodexErrorPath `
        -NoNewWindow `
        -Wait `
        -PassThru
    $CodexExitCode = $CodexProcess.ExitCode
    if (Test-Path -LiteralPath $CodexErrorPath) {
        Get-Content -LiteralPath $CodexErrorPath -Encoding UTF8 | Write-Host
    }
    if (Test-Path -LiteralPath $CodexLogPath) {
        Get-Content -LiteralPath $CodexLogPath -Encoding UTF8 | Write-Host
    }
    if ($CodexExitCode -ne 0) { throw "Codex academic review failed with exit code $CodexExitCode" }

    & $Python backend/apply_curation.py $CurationPath --site-root public
    if ($LASTEXITCODE -ne 0) { throw "curation import failed" }

    & $Python backend/hub_publish.py --site-root public
    if ($LASTEXITCODE -ne 0) { throw "hub interface build failed" }

    & $Python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw "project tests failed" }

    if (-not $SkipPush) {
        & $Git add -- public/data public/email public/api
        & $Git diff --cached --quiet
        $HasChanges = $LASTEXITCODE -ne 0
        if ($HasChanges) {
            & $Git commit -m "data: local codex curation $DigestDate"
            if ($LASTEXITCODE -ne 0) { throw "git commit failed" }
            & $Git pull --rebase origin main
            if ($LASTEXITCODE -ne 0) { throw "git rebase failed" }
            & $Git push origin main
            if ($LASTEXITCODE -ne 0) { throw "git push failed" }
        }
    }

    $FinishedAt = Get-Date
    $Report = [ordered]@{
        date = $DigestDate
        started_at = $StartedAt.ToString("o")
        finished_at = $FinishedAt.ToString("o")
        duration_seconds = [math]::Round(($FinishedAt - $StartedAt).TotalSeconds, 1)
        fetched = $Latest.stats.fetched
        candidates = $Latest.stats.candidates
        selected = (Get-Content -LiteralPath $CurationPath -Raw -Encoding UTF8 | ConvertFrom-Json).selected.Count
        model = [string]$Settings.Model
        pushed = -not $SkipPush
        site = "https://zichenwang114514.github.io/ai-chem-daily/"
    }
    $ReportPath = Join-Path $RunRoot "$DigestDate-run.json"
    [System.IO.File]::WriteAllText(
        $ReportPath,
        ($Report | ConvertTo-Json -Depth 5) + [Environment]::NewLine,
        (New-Object System.Text.UTF8Encoding($false))
    )
    $Report | Format-List
}
finally {
    Pop-Location
}
