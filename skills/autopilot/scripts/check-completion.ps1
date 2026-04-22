Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-ProjectRoot {
  if ($env:CODEX_PROJECT_DIR) {
    return $env:CODEX_PROJECT_DIR
  }

  return (Get-Location).Path
}

function Get-WorkspaceRoot {
  return (Join-Path (Get-ProjectRoot) ".autopilot")
}

function Convert-ToPointerToken {
  param(
    [string]$Value
  )

  if ([string]::IsNullOrWhiteSpace($Value)) {
    return $null
  }

  $token = $Value.ToLowerInvariant()
  $token = [regex]::Replace($token, '[^a-z0-9._-]+', '-')
  $token = [regex]::Replace($token, '^-+|-+$', '')
  $token = [regex]::Replace($token, '-{2,}', '-')

  if ([string]::IsNullOrWhiteSpace($token)) {
    return $null
  }

  return $token
}

function Get-ThreadKey {
  if ($env:AUTOPILOT_THREAD_KEY) {
    return (Convert-ToPointerToken -Value $env:AUTOPILOT_THREAD_KEY)
  }

  if ($env:CODEX_THREAD_ID) {
    return (Convert-ToPointerToken -Value $env:CODEX_THREAD_ID)
  }

  return $null
}

function Resolve-PointerValue {
  param(
    [Parameter(Mandatory = $true)]
    [string]$PointerPath
  )

  if (-not (Test-Path -LiteralPath $PointerPath)) {
    return $null
  }

  $recorded = (Get-Content -LiteralPath $PointerPath -Raw).Trim()
  if (-not $recorded) {
    return $null
  }

  if (Test-Path -LiteralPath $recorded -PathType Leaf) {
    return $recorded
  }

  if (Test-Path -LiteralPath $recorded -PathType Container) {
    $candidate = Join-Path $recorded "plan.md"
    if (Test-Path -LiteralPath $candidate) {
      return $candidate
    }
  }

  return $null
}

function Get-ThreadPointerPath {
  $threadKey = Get-ThreadKey
  if (-not $threadKey) {
    return $null
  }

  $threadsRoot = Join-Path (Get-WorkspaceRoot) "threads"
  return (Join-Path $threadsRoot "$threadKey.current")
}

function Resolve-ThreadPointer {
  $pointerPath = Get-ThreadPointerPath
  if (-not $pointerPath) {
    return $null
  }

  return (Resolve-PointerValue -PointerPath $pointerPath)
}

function Get-CurrentPointerPath {
  return (Join-Path (Get-WorkspaceRoot) "current")
}

function Resolve-CurrentPointer {
  $pointerPath = Get-CurrentPointerPath
  return (Resolve-PointerValue -PointerPath $pointerPath)
}

function Get-LatestAutopilotPlan {
  $autopilotRoot = Get-WorkspaceRoot
  if (-not (Test-Path -LiteralPath $autopilotRoot)) {
    return $null
  }

  $latest = Get-ChildItem -LiteralPath $autopilotRoot -Filter "plan.md" -Recurse -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

  if ($latest) {
    return $latest.FullName
  }

  return $null
}

function Get-PlanPath {
  if ($env:AUTOPILOT_PLAN_PATH -and (Test-Path -LiteralPath $env:AUTOPILOT_PLAN_PATH)) {
    return $env:AUTOPILOT_PLAN_PATH
  }

  $threadPlan = Resolve-ThreadPointer
  if ($threadPlan) {
    return $threadPlan
  }

  $currentPlan = Resolve-CurrentPointer
  if ($currentPlan) {
    return $currentPlan
  }

  $latestAutopilotPlan = Get-LatestAutopilotPlan
  if ($latestAutopilotPlan) {
    return $latestAutopilotPlan
  }

  $candidates = @()
  if ($env:CODEX_PROJECT_DIR) {
    $candidates += (Join-Path $env:CODEX_PROJECT_DIR "plan.md")
  }
  $candidates += (Join-Path (Get-Location) "plan.md")

  foreach ($candidate in $candidates) {
    if ($candidate -and (Test-Path -LiteralPath $candidate)) {
      return $candidate
    }
  }

  $workloopRoot = Join-Path (Get-Location) ".workloop"
  if (Test-Path -LiteralPath $workloopRoot) {
    $latest = Get-ChildItem -LiteralPath $workloopRoot -Filter "plan.md" -Recurse -File -ErrorAction SilentlyContinue |
      Sort-Object LastWriteTime -Descending |
      Select-Object -First 1
    if ($latest) {
      return $latest.FullName
    }
  }

  return $null
}

function Clear-PointerIfPlan {
  param(
    [Parameter(Mandatory = $true)]
    [string]$PointerPath,
    [Parameter(Mandatory = $true)]
    [string]$PlanPath
  )

  if (-not (Test-Path -LiteralPath $pointerPath)) {
    return
  }

  $recorded = (Get-Content -LiteralPath $pointerPath -Raw).Trim()
  if (-not $recorded) {
    return
  }

  $planDirectory = Split-Path -Parent $PlanPath
  if ($recorded -eq $PlanPath -or $recorded -eq $planDirectory) {
    Remove-Item -LiteralPath $pointerPath -Force -ErrorAction SilentlyContinue
  }
}

function Clear-ThreadPointerIfPlan {
  param(
    [Parameter(Mandatory = $true)]
    [string]$PlanPath
  )

  $pointerPath = Get-ThreadPointerPath
  if (-not $pointerPath) {
    return
  }

  Clear-PointerIfPlan -PointerPath $pointerPath -PlanPath $PlanPath
}

function Clear-CurrentPointerIfPlan {
  param(
    [Parameter(Mandatory = $true)]
    [string]$PlanPath
  )

  $pointerPath = Get-CurrentPointerPath
  Clear-PointerIfPlan -PointerPath $pointerPath -PlanPath $PlanPath
}

function Write-BlockDecision {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Reason
  )

  $payload = @{
    hookSpecificOutput = @{
      hookEventName = "Stop"
      decision = "block"
      reason = $Reason
    }
  }

  $payload | ConvertTo-Json -Depth 4 -Compress
}

function Get-UncheckedCount {
  param(
    [Parameter(Mandatory = $true)]
    [AllowEmptyCollection()]
    [AllowEmptyString()]
    [string[]]$Lines
  )

  $inTarget = $false
  $count = 0

  foreach ($line in $Lines) {
    if ($line -match '^## (Done When|Todos)$') {
      $inTarget = $true
      continue
    }

    if ($line -match '^## ') {
      $inTarget = $false
      continue
    }

    if ($inTarget -and $line -match '^[ \t]*- \[ \]') {
      $count += 1
    }
  }

  return $count
}

$planPath = Get-PlanPath
if (-not $planPath) {
  exit 0
}

$planContent = Get-Content -LiteralPath $planPath -Raw
$planLines = if ($planContent) { $planContent -split "\r?\n" } else { @() }

if ($planContent -match '^BLOCKER:\s*true') {
  exit 0
}

$unchecked = Get-UncheckedCount -Lines $planLines

if ($unchecked -eq 0) {
  $donePath = if ($planPath -match '\.md$') {
    $planPath -replace '\.md$', '.done.md'
  } else {
    "$planPath.done.md"
  }

  if (-not (Test-Path -LiteralPath $donePath)) {
    try {
      Move-Item -LiteralPath $planPath -Destination $donePath -ErrorAction Stop
    } catch {
      # Best effort: allow the turn to stop even if archival rename fails.
    }
  }

  Clear-ThreadPointerIfPlan -PlanPath $planPath
  Clear-CurrentPointerIfPlan -PlanPath $planPath
  exit 0
}

$reason = "plan.md에 미완료 항목이 ${unchecked}개 남았습니다. ## Next Action을 보고 다음 unchecked todo를 처리하세요."
Write-Output (Write-BlockDecision -Reason $reason)
exit 0
