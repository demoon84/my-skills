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

function Get-ThreadPointerPath {
  $threadKey = Get-ThreadKey
  if (-not $threadKey) {
    return $null
  }

  $threadsRoot = Join-Path (Get-WorkspaceRoot) "threads"
  return (Join-Path $threadsRoot "$threadKey.current")
}

function Convert-ToSlug {
  param(
    [string]$Value = "autopilot"
  )

  $slug = $Value.ToLowerInvariant()
  $slug = [regex]::Replace($slug, '[^a-z0-9]+', '-')
  $slug = [regex]::Replace($slug, '^-+|-+$', '')
  $slug = [regex]::Replace($slug, '-{2,}', '-')

  if ([string]::IsNullOrWhiteSpace($slug)) {
    return "autopilot"
  }

  return $slug
}

function New-RunDirectory {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Root,
    [Parameter(Mandatory = $true)]
    [string]$Slug,
    [Parameter(Mandatory = $true)]
    [string]$Timestamp
  )

  $base = Join-Path $Root "${Slug}_${Timestamp}"
  $candidate = $base
  $suffix = 1

  while (Test-Path -LiteralPath $candidate) {
    $candidate = "${base}_{0:d2}" -f $suffix
    $suffix += 1
  }

  return $candidate
}

$scriptDir = Split-Path -Parent $PSCommandPath
$skillDir = Split-Path -Parent $scriptDir
$templatePath = Join-Path $skillDir "templates\plan.md.template"

if (-not (Test-Path -LiteralPath $templatePath)) {
  throw "plan template not found: $templatePath"
}

$workspaceRoot = Get-WorkspaceRoot
$slug = Convert-ToSlug -Value $args[0]
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$runDir = New-RunDirectory -Root $workspaceRoot -Slug $slug -Timestamp $timestamp
$planPath = Join-Path $runDir "plan.md"
$currentPointer = Join-Path $workspaceRoot "current"
$threadPointer = Get-ThreadPointerPath

New-Item -ItemType Directory -Path $runDir -Force | Out-Null
Copy-Item -LiteralPath $templatePath -Destination $planPath -Force
[System.IO.File]::WriteAllText($currentPointer, "$planPath`n")

if ($threadPointer) {
  New-Item -ItemType Directory -Path (Split-Path -Parent $threadPointer) -Force | Out-Null
  [System.IO.File]::WriteAllText($threadPointer, "$planPath`n")
}

Write-Output $planPath
