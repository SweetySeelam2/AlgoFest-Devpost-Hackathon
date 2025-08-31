<# scripts\ablate.ps1
Runs three ablations on the same VRP instance and writes a Markdown table:
  1) Init only (Clarke–Wright)
  2) CW + Local (2-opt + relocate)
  3) CW + Local + SA (time-budgeted)
Also prints the table to console. Requires: src.cli exists and writes run_<stem>.json.
#>

[CmdletBinding()]
param(
  [int]$N = 250,
  [int]$K = 20,
  [int]$Cap = 100,
  [int]$Seed = 42,
  # SA time (seconds) for the third row (CW+Local+SA)
  [int]$SaTime = 10,
  # Where artifacts go
  [string]$OutDir = "results",
  # Add a timestamp suffix to filenames so they never collide
  [switch]$Stamp,
  # Also save PNG plots for each run
  [switch]$Plot
)

$ErrorActionPreference = "Stop"

# --- ensure outdir exists ---
if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Force -Path $OutDir | Out-Null }

# --- optional timestamp suffix ---
$ts = if ($Stamp) { (Get-Date -Format "yyyyMMdd-HHmmss") } else { "" }
function Add-Stamp([string]$s) { if ($ts) { return "${s}_$ts" } else { return $s } }

# --- stems for the three runs ---
$cwStem    = Add-Stamp "ablation_cw_only"
$localStem = Add-Stamp "ablation_local_only"
$saStem    = Add-Stamp ("ablation_local_sa{0}" -f $SaTime)

# --- helper: run one CLI call safely ---
function Run-CLI {
  param(
    [string]$Stem,
    [int]$Sa,
    [switch]$NoLocal
  )
  $args = @(
    "-m","src.cli",
    "--n", $N, "--k", $K, "--cap", $Cap, "--seed", $Seed,
    "--sa_time", $Sa,
    "--outdir", $OutDir,
    "--outstem", $Stem
  )
  if ($NoLocal) { $args += @("--no_local") }
  if ($Plot)    { $args += @("--plot") }

  Write-Host ">> Running: python $($args -join ' ')" -ForegroundColor Cyan
  python $args
}

# --- 1) CW only (no local, no SA) ---
Run-CLI -Stem $cwStem -Sa 0 -NoLocal

# --- 2) CW + Local (no SA) ---
Run-CLI -Stem $localStem -Sa 0

# --- 3) CW + Local + SA (time budget) ---
Run-CLI -Stem $saStem -Sa $SaTime

# --- Collect JSONs ---
$cwJson    = Join-Path $OutDir ("run_{0}.json" -f $cwStem)
$localJson = Join-Path $OutDir ("run_{0}.json" -f $localStem)
$saJson    = Join-Path $OutDir ("run_{0}.json" -f $saStem)

$files = @($cwJson, $localJson, $saJson)
foreach ($f in $files) {
  if (-not (Test-Path $f)) { throw "Expected JSON not found: $f" }
}

# --- Parse & compute deltas ---
$data = foreach ($f in $files) {
  $j = Get-Content $f -Raw | ConvertFrom-Json
  $stage = switch -Wildcard ($f) {
    "*cw_only*"     { 'Init only (Clarke–Wright)'; break }
    "*local_only*"  { 'CW + Local (2-opt + relocate)'; break }
    "*sa*"          { "CW + Local + SA ($SaTime s)"; break }
    default         { 'Unknown' }
  }
  [PSCustomObject]@{
    File        = $f
    Stage       = $stage
    Cost        = [double]$j.cost
    Runtime_sec = [double]$j.runtime_sec
  }
}

# Order nicely
$data = $data | Sort-Object Stage

# Baseline & improvement %
$base = ($data | Where-Object { $_.Stage -like 'Init only*' }).Cost
$data = $data | ForEach-Object {
  $pct = if ($base -gt 0) { [math]::Round((($base - $_.Cost)/$base)*100, 2) } else { 0 }
  $_ | Add-Member -NotePropertyName 'Delta_vs_CW_%' -NotePropertyValue $pct -PassThru
}

# --- Compose Markdown (always n-based filename for convenience) ---
$mdPath = Join-Path $OutDir ("ablation_n{0}.md" -f $N)
$lines = @()
$lines += "### Ablation results (N=$N, K=$K, Cap=$Cap, seed=$Seed)"
$lines += "| Stage                          | Cost   | Runtime (s) | Δ vs CW (%) | JSON |"
$lines += "|-------------------------------:|-------:|------------:|-----------:|------|"
foreach ($row in $data) {
  $pct = $row.'Delta_vs_CW_%'
  $lines += ("| {0,-30} | {1,6:N2} | {2,10:N2} | {3,10:N2} | {4} |" -f `
            $row.Stage, $row.Cost, $row.Runtime_sec, $pct, $row.File)
}

$lines | Out-File -FilePath $mdPath -Encoding utf8 -Force

# --- Print to console too ---
$lines | ForEach-Object { Write-Output $_ }
Write-Host "[OK] Wrote $mdPath" -ForegroundColor Green
