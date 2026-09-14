<#
.SYNOPSIS
    ARTEMIS upstream(google/artemis)을 proxy-only 모드로 clone/patch/setup 하는 원샷 스크립트.

.DESCRIPTION
    1. 지정한 위치(기본: 이 저장소의 부모 디렉터리 아래 artemis-upstream)에 google/artemis를 clone
    2. 371aa6d 커밋을 체크아웃하고 proxy-only 브랜치를 만들어 patches/artemis-upstream-proxy-only.patch를 적용
    3. uv 설치 확인 후 `uv sync` 실행
    4. config/artemis-upstream/.env.example -> <target>\.env 복사(이미 있으면 건너뜀)
    5. Claude Code에 artemis / artemis-adb MCP 서버를 user scope로 등록(-SkipMcp로 생략 가능)

    이 저장소(product repo)의 루트에서 실행하는 것을 가정합니다.

.PARAMETER TargetDir
    ARTEMIS upstream을 clone할 경로. 기본값은 "..\artemis-upstream" (product repo 루트 기준).

.PARAMETER SkipMcp
    Claude Code MCP 서버 등록을 건너뜁니다.

.PARAMETER DryRun
    실제로 아무 것도 실행하지 않고, 수행할 작업만 출력합니다.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\setup_artemis_upstream.ps1 -DryRun

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\setup_artemis_upstream.ps1
#>

[CmdletBinding()]
param(
    [string]$TargetDir,
    [switch]$SkipMcp,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$PinnedCommit = "371aa6d"
$BranchName = "proxy-only"
$PatchSubject = "Route all LLM calls through OpenAI-compatible proxy (proxy-only mode)"
$RepoUrl = "https://github.com/google/artemis.git"

# ----------------------------------------------------------------------------
# 경로 계산
# ----------------------------------------------------------------------------
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProductRoot = Split-Path -Parent $ScriptDir
$PatchFile = Join-Path $ProductRoot "patches\artemis-upstream-proxy-only.patch"
$EnvTemplate = Join-Path $ProductRoot "config\artemis-upstream\.env.example"

if (-not $TargetDir -or $TargetDir -eq "") {
    $TargetDir = Join-Path $ProductRoot "..\artemis-upstream"
}
$TargetDir = [System.IO.Path]::GetFullPath($TargetDir)

function Invoke-Step {
    param(
        [string]$Description,
        [scriptblock]$Action
    )
    if ($DryRun) {
        Write-Host "[DryRun] $Description"
    } else {
        Write-Host "==> $Description"
        & $Action
    }
}

Write-Host "ARTEMIS upstream setup (proxy-only)"
Write-Host "  TargetDir : $TargetDir"
Write-Host "  PatchFile : $PatchFile"
Write-Host "  EnvTemplate: $EnvTemplate"
Write-Host ""

if (-not (Test-Path $PatchFile)) {
    throw "Patch file not found: $PatchFile"
}

# ----------------------------------------------------------------------------
# 1) Clone + checkout + branch + patch
# ----------------------------------------------------------------------------
$repoExists = Test-Path (Join-Path $TargetDir ".git")

if (-not $repoExists) {
    Invoke-Step "Clone $RepoUrl -> $TargetDir" {
        git clone $RepoUrl $TargetDir
        if ($LASTEXITCODE -ne 0) { throw "git clone failed" }
    }
} else {
    Write-Host "==> $TargetDir already a git repo, skipping clone"
}

$branchExists = $false
$branchAlreadyPatched = $false
if (-not $DryRun -and (Test-Path (Join-Path $TargetDir ".git"))) {
    Push-Location $TargetDir
    try {
        $branchList = git branch --list $BranchName
        if ($branchList) {
            $branchExists = $true
            $prevEap = $ErrorActionPreference
            $ErrorActionPreference = "Continue"
            $subjects = git log $BranchName --format=%s -n 20
            $ErrorActionPreference = $prevEap
            if ($subjects -and ($subjects -match [regex]::Escape($PatchSubject))) {
                $branchAlreadyPatched = $true
            }
        }
    } finally {
        Pop-Location
    }
}

if ($branchAlreadyPatched) {
    Write-Host "==> Branch '$BranchName' already exists and contains the patch commit, skipping checkout/am"
} elseif ($branchExists) {
    # Branch exists but we could not confirm it already has the patch commit
    # (e.g. rebased/reworded, or more than 20 commits ahead). Never delete a
    # branch we can't positively identify as ours — that could destroy the
    # user's own work.
    throw "Branch '$BranchName' already exists in $TargetDir but does not appear to contain the patch commit ('$PatchSubject'). Refusing to delete it automatically. Please delete or rename it manually, or pass -TargetDir to use a fresh clone."
} else {
    Invoke-Step "Checkout $PinnedCommit and create branch $BranchName" {
        Push-Location $TargetDir
        try {
            git checkout $PinnedCommit
            if ($LASTEXITCODE -ne 0) { throw "git checkout $PinnedCommit failed" }
            git checkout -b $BranchName
            if ($LASTEXITCODE -ne 0) { throw "git checkout -b $BranchName failed" }
        } finally {
            Pop-Location
        }
    }
    Invoke-Step "Apply patch with git am" {
        Push-Location $TargetDir
        try {
            git am $PatchFile
            if ($LASTEXITCODE -ne 0) {
                $prevEap = $ErrorActionPreference
                $ErrorActionPreference = "Continue"
                git am --abort
                $ErrorActionPreference = $prevEap
                throw "git am failed to apply $PatchFile"
            }
        } finally {
            Pop-Location
        }
    }
}

# ----------------------------------------------------------------------------
# 2) uv 설치 + sync
# ----------------------------------------------------------------------------
function Resolve-UvExe {
    $cmd = Get-Command uv -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    # pip install --user places uv.exe under the user Scripts dir, which may not
    # be on PATH in the current session even though pip reports success.
    # `site --user-base` omits the versioned subfolder on some Windows/py
    # installs, so ask sysconfig for the actual per-user scripts path instead.
    try {
        $userScripts = (python -c "import sysconfig; print(sysconfig.get_path('scripts', 'nt_user'))" 2>$null | Out-String).Trim()
        if ($userScripts) {
            $candidate = Join-Path $userScripts "uv.exe"
            if (Test-Path $candidate) { return $candidate }
        }
    } catch {}
    return $null
}

$uvExe = Resolve-UvExe
if (-not $uvExe) {
    Invoke-Step "Install uv (pip install --user uv)" {
        python -m pip install --user uv
        if ($LASTEXITCODE -ne 0) {
            Write-Host "pip install --user uv failed, trying winget..."
            winget install --id astral-sh.uv -e --source winget
            if ($LASTEXITCODE -ne 0) { throw "Failed to install uv via pip and winget" }
        }
    }
    if (-not $DryRun) {
        $uvExe = Resolve-UvExe
        if (-not $uvExe) { throw "uv was installed but its executable could not be located (check PATH)" }
    } else {
        $uvExe = "uv"
    }
} else {
    Write-Host "==> uv already installed ($uvExe)"
}

Invoke-Step "uv sync in $TargetDir" {
    Push-Location $TargetDir
    try {
        & $uvExe sync
        if ($LASTEXITCODE -ne 0) { throw "uv sync failed" }
    } finally {
        Pop-Location
    }
}

# ----------------------------------------------------------------------------
# 3) .env 복사 (있으면 건너뜀)
# ----------------------------------------------------------------------------
$targetEnv = Join-Path $TargetDir ".env"
if (Test-Path $targetEnv) {
    Write-Host "==> $targetEnv already exists, not overwriting"
} else {
    Invoke-Step "Copy $EnvTemplate -> $targetEnv" {
        if (-not (Test-Path $EnvTemplate)) { throw "Env template not found: $EnvTemplate" }
        Copy-Item $EnvTemplate $targetEnv
    }
    Write-Host ""
    Write-Host "*** $targetEnv 를 열어 OPENAI_API_KEY 와 (필요하다면) ADB_DEVICE_SERIAL 을 채우세요. ***"
    Write-Host ""
}

# ----------------------------------------------------------------------------
# 4) Claude Code MCP 서버 등록 (user scope)
# ----------------------------------------------------------------------------
if ($SkipMcp) {
    Write-Host "==> -SkipMcp specified, skipping MCP server registration"
} else {
    $claudeCmd = Get-Command claude -ErrorAction SilentlyContinue
    if (-not $claudeCmd) {
        Write-Host "==> 'claude' CLI not found on PATH, skipping MCP server registration"
    } else {
        $pythonExe = Join-Path $TargetDir ".venv\Scripts\python.exe"
        $existingList = ""
        if (-not $DryRun) {
            $prevEap = $ErrorActionPreference
            $ErrorActionPreference = "Continue"
            $existingList = claude mcp list | Out-String
            $ErrorActionPreference = $prevEap
        }

        # `claude mcp list` prints one line per server as "<name>: <command> - <status>".
        # Anchor on "<name>:" at the start of a line so "artemis" does not also
        # match the "artemis-adb: ..." line or the "...\artemis-upstream\..."
        # command path that appears on every registered line.
        if ($existingList -match "(?m)^artemis-adb:") {
            Write-Host "==> MCP server 'artemis-adb' already registered, skipping"
        } else {
            Invoke-Step "Register MCP server 'artemis-adb' (user scope)" {
                claude mcp add --scope user artemis-adb `
                    --env "PYTHONPATH=$TargetDir" `
                    --env "PYTHONUNBUFFERED=1" `
                    -- $pythonExe -m artemis mcp --type adb --transport stdio
            }
        }

        if ($existingList -match "(?m)^artemis:") {
            Write-Host "==> MCP server 'artemis' already registered, skipping"
        } else {
            Invoke-Step "Register MCP server 'artemis' (user scope)" {
                claude mcp add --scope user artemis `
                    --env "PYTHONPATH=$TargetDir" `
                    --env "PYTHONUNBUFFERED=1" `
                    -- $pythonExe -m mcp_server
            }
        }
    }
}

# ----------------------------------------------------------------------------
# 5) 마무리 안내
# ----------------------------------------------------------------------------
Write-Host ""
Write-Host "==> adb devices -l"
if (-not $DryRun) {
    $adbCmd = Get-Command adb -ErrorAction SilentlyContinue
    if ($adbCmd) {
        adb devices -l
    } else {
        Write-Host "(adb not found on PATH)"
    }
}

Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. $targetEnv 에 OPENAI_API_KEY(LiteLLM virtual key) 를 채우세요."
Write-Host "  2. Android 기기를 연결하고 'adb devices -l' 로 인식되는지 확인하세요."
Write-Host "  3. Claude Code를 새 세션으로 열어 MCP 서버(artemis, artemis-adb)를 사용하세요."
Write-Host "  4. 자세한 내용은 docs\artemis-upstream-proxy-only.md 를 참고하세요."
