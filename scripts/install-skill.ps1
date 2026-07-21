param(
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$CodexSkillsRoot = (Join-Path $env:USERPROFILE ".codex\skills"),
    [string]$AgentsSkillsRoot = (Join-Path $env:USERPROFILE ".agents\skills")
)

$VoidscapeSource = Join-Path $RepoRoot "skill"
$LegacySource = Join-Path $RepoRoot "compat\read-video"

function Install-SkillTo {
    param([string]$Harness, [string]$Root, [string]$Name, [string]$Source)

    $Dest = Join-Path $Root $Name
    try {
        if (-not (Test-Path $Source)) { throw "source not found: $Source" }
        New-Item -ItemType Directory -Path $Dest -Force | Out-Null
        Get-ChildItem -LiteralPath $Source -Force | Where-Object {
            $_.Name -notin @("workspace.json", ".env", "load-env.ps1")
        } | Copy-Item -Destination $Dest -Recurse -Force
        [Console]::WriteLine("RESULT $Harness $Name copy OK")
        return $Dest
    } catch {
        [Console]::WriteLine("RESULT $Harness $Name copy FAILED $($_.Exception.Message)")
        return $null
    }
}

function Test-Frontmatter {
    param([string]$Harness, [string]$Name, [string]$Dest)
    try {
        $SkillMdPath = Join-Path $Dest "SKILL.md"
        if (-not (Test-Path $SkillMdPath)) { throw "SKILL.md not found" }
        $content = Get-Content $SkillMdPath -Raw
        if ($content -notmatch '(?s)^---\s*(.*?)\s*---') { throw "no frontmatter block found" }
        $frontmatter = $Matches[1]
        if ($frontmatter -notmatch 'name:\s*\S+') { throw "missing name key" }
        if ($frontmatter -notmatch 'description:') { throw "missing description key" }
        [Console]::WriteLine("RESULT $Harness $Name verify:frontmatter OK")
        return $true
    } catch {
        [Console]::WriteLine("RESULT $Harness $Name verify:frontmatter FAILED $($_.Exception.Message)")
        return $false
    }
}

function Test-CliRuns {
    param([string]$Harness, [string]$Name, [string]$Dest)
    try {
        if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "python not found on PATH" }
        $ScriptPath = Join-Path $Dest "scripts\video.py"
        & python $ScriptPath probe --help *> $null
        if ($LASTEXITCODE -ne 0) { throw "exit code $LASTEXITCODE" }
        [Console]::WriteLine("RESULT $Harness $Name verify:cli OK")
        return $true
    } catch {
        [Console]::WriteLine("RESULT $Harness $Name verify:cli FAILED $($_.Exception.Message)")
        return $false
    }
}

$allVerified = $true
foreach ($target in @(
    @{ Harness = "codex"; Root = $CodexSkillsRoot },
    @{ Harness = "agents"; Root = $AgentsSkillsRoot }
)) {
    foreach ($spec in @(
        @{ Name = "voidscape"; Source = $VoidscapeSource },
        @{ Name = "read-video"; Source = $LegacySource }
    )) {
        $dest = Install-SkillTo -Harness $target.Harness -Root $target.Root `
            -Name $spec.Name -Source $spec.Source
        if (-not $dest) {
            $allVerified = $false
            continue
        }
        if (-not (Test-Frontmatter -Harness $target.Harness -Name $spec.Name -Dest $dest)) {
            $allVerified = $false
        }
        if (-not (Test-CliRuns -Harness $target.Harness -Name $spec.Name -Dest $dest)) {
            $allVerified = $false
        }
    }
}

if (-not $allVerified) {
    [Console]::WriteLine("SUMMARY install FAILED: one or more copies or verification checks failed")
    exit 1
}
[Console]::WriteLine("SUMMARY install complete: Voidscape primary, read-video compatibility retained")
exit 0
