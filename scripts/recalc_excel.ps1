param([string]$path)
$ErrorActionPreference = "Stop"
$abs = (Resolve-Path $path).Path
$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
try {
    $wb = $excel.Workbooks.Open($abs)
    $excel.CalculateFullRebuild()
    $wb.Save()
    $errors = @()
    foreach ($ws in $wb.Worksheets) {
        $used = $ws.UsedRange
        if ($used -eq $null) { continue }
        try {
            # XlCellType.xlCellTypeFormulas = -4123
            $cells = $used.SpecialCells(-4123)
            foreach ($cell in $cells) {
                $v = $cell.Value
                if ($v -is [string] -and $v.StartsWith("#")) {
                    $errors += "$($ws.Name)!$($cell.Address()) = $v"
                }
            }
        } catch {
            # no formulas in sheet
        }
    }
    $wb.Close($true)
    if ($errors.Count -eq 0) {
        Write-Output "OK: no formula errors"
    } else {
        Write-Output "ERRORS: $($errors.Count)"
        $errors | ForEach-Object { Write-Output "  $_" }
    }
} finally {
    $excel.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
