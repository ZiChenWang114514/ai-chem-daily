param(
    [switch]$SkipPush,
    [switch]$SkipPull,
    [string]$Date
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$SettingsPath = Join-Path $RepoRoot "config\local.settings.psd1"
$SecretsPath = Join-Path $RepoRoot "config\local.secrets.psd1"
$RunRoot = Join-Path $RepoRoot "work\local-pipeline"
$StatusRoot = Join-Path $RunRoot "status"
$Settings = @{
    Model = "gpt-5.6-terra"
    ReasoningEffort = "high"
    ScheduleTime = "07:00"
}
if (Test-Path -LiteralPath $SettingsPath) {
    $LocalSettings = Import-PowerShellDataFile -LiteralPath $SettingsPath
    foreach ($Key in $LocalSettings.Keys) { $Settings[$Key] = $LocalSettings[$Key] }
}
$Secrets = @{ OpenReviewUsername = ""; OpenReviewPassword = "" }
if (Test-Path -LiteralPath $SecretsPath) {
    $LocalSecrets = Import-PowerShellDataFile -LiteralPath $SecretsPath
    foreach ($Key in $LocalSecrets.Keys) { $Secrets[$Key] = $LocalSecrets[$Key] }
}
$OpenReviewUserInjected = $false
$OpenReviewPassInjected = $false
if (-not $env:OPENREVIEW_USERNAME -and $Secrets.OpenReviewUsername) {
    $env:OPENREVIEW_USERNAME = [string]$Secrets.OpenReviewUsername
    $OpenReviewUserInjected = $true
}
if (-not $env:OPENREVIEW_PASSWORD -and $Secrets.OpenReviewPassword) {
    $env:OPENREVIEW_PASSWORD = [string]$Secrets.OpenReviewPassword
    $OpenReviewPassInjected = $true
}
$GitHubTokenInjected = $false
if (-not $env:GITHUB_TOKEN) {
    $Gh = Get-Command gh -ErrorAction SilentlyContinue
    if ($Gh) {
        $Token = (& gh auth token 2>$null | Select-Object -First 1)
        if ($Token) {
            $env:GITHUB_TOKEN = [string]$Token
            $GitHubTokenInjected = $true
        }
    }
}

$Python = (Get-Command python -ErrorAction Stop).Source
$CodexCommand = (Get-Command codex.cmd -ErrorAction Stop).Source
$CodexRoot = Split-Path $CodexCommand -Parent
$CodexJavaScript = Join-Path $CodexRoot "node_modules\@openai\codex\bin\codex.js"
$Node = (Get-Command node.exe -ErrorAction Stop).Source
$Git = (Get-Command git -ErrorAction Stop).Source
$Channels = @("aixchem", "aixbio", "aixmath", "aivoices", "engineering")
$RunDate = if ($Date) { $Date } else { (Get-Date).ToString("yyyy-MM-dd") }
New-Item -ItemType Directory -Force -Path $RunRoot, $StatusRoot | Out-Null

function Write-ChannelStatus([string]$Channel, [string]$State, [string]$Message) {
    $Value = [ordered]@{
        channel = $Channel; date = $RunDate; state = $State; message = $Message
        updated_at = (Get-Date).ToUniversalTime().ToString("o")
        model = [string]$Settings.Model; reasoning_effort = [string]$Settings.ReasoningEffort
    }
    $Path = Join-Path $StatusRoot "$Channel.json"
    [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth 6) + [Environment]::NewLine, (New-Object System.Text.UTF8Encoding($false)))
}

function Invoke-CodexJson([string]$PromptPath, [string]$SchemaPath, [string]$OutputPath, [string]$LogStem) {
    $StdoutPath = Join-Path $RunRoot "$RunDate-$LogStem-output.txt"
    $StderrPath = Join-Path $RunRoot "$RunDate-$LogStem-error.txt"
    $CodexArgs = @(
        "exec", "--ephemeral", "--sandbox", "read-only", "--color", "never",
        "--model", [string]$Settings.Model,
        "-c", "model_reasoning_effort=`"$([string]$Settings.ReasoningEffort)`"",
        "-C", $RepoRoot, "--output-schema", $SchemaPath,
        "--output-last-message", $OutputPath, "-"
    )
    $Process = Start-Process -FilePath $Node -ArgumentList (@($CodexJavaScript) + $CodexArgs) -WorkingDirectory $RepoRoot -RedirectStandardInput $PromptPath -RedirectStandardOutput $StdoutPath -RedirectStandardError $StderrPath -WindowStyle Hidden -Wait -PassThru
    if (Test-Path -LiteralPath $StderrPath) { Get-Content -LiteralPath $StderrPath -Encoding UTF8 | Write-Host }
    if (Test-Path -LiteralPath $StdoutPath) { Get-Content -LiteralPath $StdoutPath -Encoding UTF8 | Write-Host }
    if ($Process.ExitCode -ne 0) { throw "Codex review failed with exit code $($Process.ExitCode)" }
}

function Invoke-Python([string[]]$PythonArgs) {
    $output = & $Python @PythonArgs 2>&1
    $code = $LASTEXITCODE
    foreach ($line in @($output)) { Write-Host $line }
    if ($code -ne 0) { throw "python $($PythonArgs -join ' ') failed with exit code $code" }
}

function Invoke-Collection([string]$Channel) {
    Write-ChannelStatus $Channel "running" "Collection started"
    try {
        Invoke-Python @("backend/aix_pipeline.py", $Channel, "--root", $RepoRoot, "--site-root", "public", "--date", $RunDate)
        Write-ChannelStatus $Channel "collected" "Collection completed; awaiting channel review"
        return $true
    }
    catch {
        Write-ChannelStatus $Channel "failed" $_.Exception.Message
        Write-Warning "$Channel collection failed: $($_.Exception.Message)"
        return $false
    }
}

function Invoke-Curation([string]$Channel) {
    Write-ChannelStatus $Channel "reviewing" "Collection completed; channel review started"
    try {
        $PromptPath = Join-Path $RepoRoot "ops\codex\${Channel}_prompt.md"
        $SchemaPath = Join-Path $RepoRoot "ops\codex\channel_curation.schema.json"
        $CurationPath = Join-Path $RunRoot "$RunDate-$Channel-curation.json"
        Invoke-CodexJson $PromptPath $SchemaPath $CurationPath $Channel
        Invoke-Python @("backend/apply_channel_curation.py", $Channel, $CurationPath, "--site-root", "public")
        Write-ChannelStatus $Channel "success" "Collection and review completed"
        return $true
    }
    catch {
        Write-ChannelStatus $Channel "failed" $_.Exception.Message
        Write-Warning "$Channel review failed: $($_.Exception.Message)"
        return $false
    }
}

function Get-FailedChannels {
    $Failed = @()
    foreach ($Channel in $Channels) {
        $Path = Join-Path $StatusRoot "$Channel.json"
        if (-not (Test-Path -LiteralPath $Path)) { $Failed += $Channel; continue }
        $Value = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($Value.date -ne $RunDate -or $Value.state -ne "success") { $Failed += $Channel }
    }
    return $Failed
}

function Publish-Daily {
    $SummaryPath = Join-Path $RunRoot "$RunDate-daily-summary.json"
    Invoke-CodexJson (Join-Path $RepoRoot "ops\codex\daily_summary_prompt.md") (Join-Path $RepoRoot "ops\codex\daily_summary.schema.json") $SummaryPath "daily-summary"
    Invoke-Python @("backend/publish_daily.py", "--site-root", "public", "--summary", $SummaryPath)
    Invoke-Python @("backend/hub_publish.py", "--site-root", "public")
    Invoke-Python @("-m", "unittest", "discover", "-s", "tests", "-v")
}

Push-Location $RepoRoot
try {
    if (-not $SkipPull) {
        & $Git pull --ff-only origin main
        if ($LASTEXITCODE -ne 0) { throw "git pull failed" }
    }
    $XCache = Join-Path $RepoRoot "work\source-cache\x\$RunDate.json.gz"
    if (-not (Test-Path -LiteralPath $XCache)) {
        Write-Warning "Grok X harvest cache missing: $XCache. AI Voices will skip X posts. See ops/grok/x_harvest_protocol.md"
    }
    $CollectedChannels = @{}
    foreach ($Channel in $Channels) {
        $CollectedChannels[$Channel] = Invoke-Collection $Channel
    }
    foreach ($Channel in $Channels) {
        if ($CollectedChannels[$Channel]) { [void](Invoke-Curation $Channel) }
    }
    $Failed = @(Get-FailedChannels)
    if ($Failed.Count -gt 0) {
        foreach ($Channel in $Failed) {
            if (Invoke-Collection $Channel) { [void](Invoke-Curation $Channel) }
        }
    }
    $StillFailed = @(Get-FailedChannels)
    if ($StillFailed.Count -gt 0) {
        Write-Warning "Retry complete; still failed: $($StillFailed -join ', ')"
        $Succeeded = @($Channels | Where-Object { $StillFailed -notcontains $_ })
        if ($Succeeded.Count -eq 0) {
            throw "All channels failed after retry; skip combined publish"
        }
    }
    Publish-Daily
    if (-not $SkipPush) {
        & $Git add -- public/data public/email public/api public/channels public/index.html public/assets public/library
        & $Git diff --cached --quiet
        $DiffCode = $LASTEXITCODE
        if ($DiffCode -eq 1) {
            & $Git commit -m "data: aix daily $RunDate"
            if ($LASTEXITCODE -ne 0) { throw "git commit failed" }
            & $Git push origin main
            if ($LASTEXITCODE -ne 0) { throw "git push failed" }
        } elseif ($DiffCode -ne 0) {
            throw "git diff failed with exit code $DiffCode"
        }
    }
}
finally {
    if ($OpenReviewUserInjected) {
        Remove-Item Env:OPENREVIEW_USERNAME -ErrorAction SilentlyContinue
    }
    if ($OpenReviewPassInjected) {
        Remove-Item Env:OPENREVIEW_PASSWORD -ErrorAction SilentlyContinue
    }
    if ($GitHubTokenInjected) {
        Remove-Item Env:GITHUB_TOKEN -ErrorAction SilentlyContinue
    }
    Pop-Location
}
