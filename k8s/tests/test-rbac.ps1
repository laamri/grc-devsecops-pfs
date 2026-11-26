
$ErrorActionPreference = "Stop"

$script:passed = 0
$script:failed = 0

function Test-Rbac {
    param(
        [string]$Name,
        [string]$Expected,
        [string[]]$Arguments
    )

    $errorFile = [System.IO.Path]::GetTempFileName()

    try {
        $output = & kubectl auth can-i @Arguments 2> $errorFile
        $exitCode = $LASTEXITCODE
        $actual = ($output -join "`n").Trim()

        $validResult = (
            ($actual -eq "yes" -and $exitCode -eq 0) -or
            ($actual -eq "no" -and $exitCode -eq 1)
        )

        if ($validResult -and $actual -eq $Expected) {
            Write-Host "[PASS] $Name" -ForegroundColor Green
            $script:passed++
        }
        else {
            Write-Host "[FAIL] $Name" -ForegroundColor Red
            Write-Host "Expected: $Expected"
            Write-Host "Actual: $actual"
            Write-Host "Exit code: $exitCode"
            Get-Content $errorFile
            $script:failed++
        }
    }
    catch {
        Write-Host "[ERROR] $Name : $_" -ForegroundColor Red
        $script:failed++
    }
    finally {
        Remove-Item $errorFile -ErrorAction SilentlyContinue
    }
}
