param(
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$CodexSkillsRoot = (Join-Path $env:USERPROFILE ".agents\skills")
)

$VoidscapeSource = Join-Path $RepoRoot "skill"
$LegacySource = Join-Path $RepoRoot "compat\read-video"

function Install-SkillTo {
    param([string]$Name, [string]$Source)

    $Dest = Join-Path $CodexSkillsRoot $Name
    try {
        if (-not (Test-Path $Source)) { throw "source not found: $Source" }
        New-Item -ItemType Directory -Path $Dest -Force | Out-Null
        Get-ChildItem -LiteralPath $Source -Force | Where-Object {
            $_.Name -notin @("workspace.json", ".env")
        } | Copy-Item -Destination $Dest -Recurse -Force
        [Console]::WriteLine("RESULT codex $Name copy OK")
        return $Dest
    } catch {
        [Console]::WriteLine("RESULT codex $Name copy FAILED $($_.Exception.Message)")
        return $null
    }
}

function Test-Frontmatter {
    param([string]$Name, [string]$Dest)
    try {
        $SkillMdPath = Join-Path $Dest "SKILL.md"
        if (-not (Test-Path $SkillMdPath)) { throw "SKILL.md not found" }
        $content = Get-Content $SkillMdPath -Raw
        if ($content -notmatch '(?s)^---\s*(.*?)\s*---') { throw "no frontmatter block found" }
        $frontmatter = $Matches[1]
        if ($frontmatter -notmatch 'name:\s*\S+') { throw "missing name key" }
        if ($frontmatter -notmatch 'description:') { throw "missing description key" }
        Write-Output "RESULT codex $Name verify:frontmatter OK"
    } catch {
        Write-Output "RESULT codex $Name verify:frontmatter FAILED $($_.Exception.Message)"
    }
}

function Test-CliRuns {
    param([string]$Name, [string]$Dest)
    try {
        if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "python not found on PATH" }
        $ScriptPath = Join-Path $Dest "scripts\video.py"
        & python $ScriptPath probe --help *> $null
        if ($LASTEXITCODE -ne 0) { throw "exit code $LASTEXITCODE" }
        Write-Output "RESULT codex $Name verify:cli OK"
    } catch {
        Write-Output "RESULT codex $Name verify:cli FAILED $($_.Exception.Message)"
    }
}

$anySucceeded = $false
foreach ($spec in @(
    @{ Name = "voidscape"; Source = $VoidscapeSource },
    @{ Name = "read-video"; Source = $LegacySource }
)) {
    $dest = Install-SkillTo -Name $spec.Name -Source $spec.Source
    if ($dest) {
        $anySucceeded = $true
        Test-Frontmatter -Name $spec.Name -Dest $dest
        Test-CliRuns -Name $spec.Name -Dest $dest
    }
}

if (-not $anySucceeded) {
    [Console]::WriteLine("SUMMARY all targets FAILED")
    exit 1
}
[Console]::WriteLine("SUMMARY install complete: Voidscape primary, read-video compatibility retained")
exit 0
