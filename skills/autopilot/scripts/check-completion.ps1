Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-PlanPath {
  if ($env:AUTOPILOT_PLAN_PATH -and (Test-Path -LiteralPath $env:AUTOPILOT_PLAN_PATH)) {
    return $env:AUTOPILOT_PLAN_PATH
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

  exit 0
}

$reason = "plan.md에 미완료 항목이 $unchecked개 남았습니다. ## Next Action을 보고 다음 unchecked todo를 처리하세요."
Write-Output (Write-BlockDecision -Reason $reason)
exit 0
