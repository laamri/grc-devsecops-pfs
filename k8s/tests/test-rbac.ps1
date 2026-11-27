# SCRUM-32: read-only authorization regression tests for local Minikube.
# Requires administrator impersonation permissions and the RBAC manifests applied.
$ErrorActionPreference = 'Stop'
$script:passed = 0
$script:failed = 0
$script:errors = 0
$kubectl = (Get-Command kubectl -ErrorAction Stop).Source

function Invoke-Kubectl {
    param([string[]]$Arguments)
    $errorFile = [System.IO.Path]::GetTempFileName()
    $savedPreference = $ErrorActionPreference
    try {
        # Windows PowerShell 5.1 treats native stderr as PowerShell errors.
        # Capture it separately; judge native commands by stdout AND exit status.
        $ErrorActionPreference = 'Continue'
        $output = & $kubectl --context=minikube --request-timeout=10s @Arguments 2> $errorFile
        $code = $LASTEXITCODE
        [pscustomobject]@{
            Output = ($output -join "`n").Trim()
            Error = [System.IO.File]::ReadAllText($errorFile).Trim()
            ExitCode = $code
        }
    }
    finally {
        $ErrorActionPreference = $savedPreference
        Remove-Item -LiteralPath $errorFile -ErrorAction SilentlyContinue
    }
}

function Test-Rbac {
    param(
        [string]$Name,
        [ValidateSet('yes', 'no')][string]$Expected,
        [string[]]$Arguments
    )
    try {
        $result = Invoke-Kubectl (@('auth', 'can-i') + $Arguments)
        $valid = ($result.Output -eq 'yes' -and $result.ExitCode -eq 0) -or
                 ($result.Output -eq 'no' -and $result.ExitCode -eq 1)
        if (!$valid) {
            $script:failed++
            $script:errors++
            Write-Host "[ERROR] $Name : output='$($result.Output)', exit=$($result.ExitCode)" -ForegroundColor Red
            Write-Host $result.Error
        }
        elseif ($result.Output -eq $Expected) {
            $script:passed++
            Write-Host "[PASS] $Name" -ForegroundColor Green
        }
        else {
            $script:failed++
            Write-Host "[FAIL] $Name : expected $Expected, actual $($result.Output)" -ForegroundColor Red
            if ($result.Error) { Write-Host $result.Error }
        }
    }
    catch {
        $script:failed++
        $script:errors++
        Write-Host "[ERROR] $Name : $_" -ForegroundColor Red
    }
}

function Get-ServiceAccountIdentity {
    param([string]$Namespace, [string]$Name)
    @(
        "--as=system:serviceaccount:${Namespace}:$Name"
        '--as-group=system:serviceaccounts'
        "--as-group=system:serviceaccounts:$Namespace"
        '--as-group=system:authenticated'
    )
}

function Test-Cases {
    param([object[]]$Cases, [string[]]$Identity)
    foreach ($case in $Cases) {
        Test-Rbac $case[0] $case[1] ($case[2] + $Identity)
    }
}

try {
    $context = & $kubectl config current-context
    if ($LASTEXITCODE -ne 0 -or $context -ne 'minikube') {
        throw 'This test suite must run against Minikube.'
    }
    $required = Invoke-Kubectl @('get', 'namespaces', 'pfs', 'pfs-dev', 'pfs-prod')
    if ($required.ExitCode -ne 0) { throw "Required namespaces unavailable: $($required.Error)" }
    # Snapshot namespaces once for the full default-account test matrix.
    $nsResult = Invoke-Kubectl @('get', 'namespaces', '-o', 'json')
    if ($nsResult.ExitCode -ne 0) { throw "Unable to retrieve namespaces: $($nsResult.Error)" }
    $namespaces = @(($nsResult.Output | ConvertFrom-Json).items.metadata.name | Sort-Object)
    if ($namespaces.Count -eq 0) { throw 'No namespaces returned.' }

    Write-Host "SCRUM-32 RBAC tests | UTC: $([DateTime]::UtcNow.ToString('o'))"
    Write-Host "Context: minikube | Namespaces: $($namespaces -join ', ')"
    Write-Host 'Checks use impersonation; no workloads or permissions are changed.'

    $reader = Get-ServiceAccountIdentity 'pfs' 'pod-reader-sa'
    $ci = Get-ServiceAccountIdentity 'pfs' 'cicd-sa'
    $devCI = Get-ServiceAccountIdentity 'pfs-dev' 'cicd-dev-sa'
    $prodCI = Get-ServiceAccountIdentity 'pfs-prod' 'cicd-prod-sa'
    $developer = @('--as=developer-test', '--as-group=pfs-developers', '--as-group=system:authenticated')
    $observer = @('--as=observer-test', '--as-group=pfs-observers', '--as-group=system:authenticated')
    $devObserver = @('--as=observer-dev-test', '--as-group=pfs-dev-observers', '--as-group=system:authenticated')
    $prodObserver = @('--as=observer-prod-test', '--as-group=pfs-prod-observers', '--as-group=system:authenticated')

    Write-Host "`n--- Pod Reader Tests ---" -ForegroundColor Cyan
    Test-Cases -Identity $reader -Cases @(
        @('Reader can list Pods in pfs', 'yes', @('list', 'pods', '-n', 'pfs')),
        @('Reader cannot delete Pods', 'no', @('delete', 'pods', '-n', 'pfs')),
        @('Reader cannot create Pods', 'no', @('create', 'pods', '-n', 'pfs')),
        @('Reader cannot get individual Pods', 'no', @('get', 'pods', '-n', 'pfs')),
        @('Reader cannot list Secrets', 'no', @('list', 'secrets', '-n', 'pfs')),
        @('Reader cannot list Pods in PROD', 'no', @('list', 'pods', '-n', 'pfs-prod')),
        @('Reader cannot list system Pods', 'no', @('list', 'pods', '-n', 'kube-system')),
        @('Reader cannot list Nodes', 'no', @('list', 'nodes'))
    )

    Write-Host "`n--- Developer Tests ---" -ForegroundColor Cyan
    Test-Cases -Identity $developer -Cases @(
        @('Developer can list Pods', 'yes', @('list', 'pods', '-n', 'pfs')),
        @('Developer can read Pod logs', 'yes', @('get', 'pods', '--subresource=log', '-n', 'pfs')),
        @('Developer cannot read Secrets', 'no', @('list', 'secrets', '-n', 'pfs')),
        @('Developer cannot delete Pods', 'no', @('delete', 'pods', '-n', 'pfs')),
        @('Developer cannot execute commands in Pods', 'no', @('create', 'pods', '--subresource=exec', '-n', 'pfs')),
        @('Developer cannot modify RBAC', 'no', @('create', 'rolebindings', '-n', 'pfs'))
    )

    Write-Host "`n--- Observer Tests ---" -ForegroundColor Cyan
    Test-Cases -Identity $observer -Cases @(
        @('Observer can list Pods', 'yes', @('list', 'pods', '-n', 'pfs')),
        @('Observer can list Deployments', 'yes', @('list', 'deployments.apps', '-n', 'pfs')),
        @('Observer cannot delete Pods', 'no', @('delete', 'pods', '-n', 'pfs')),
        @('Observer cannot read Pod logs', 'no', @('get', 'pods', '--subresource=log', '-n', 'pfs')),
        @('Observer cannot read Secrets', 'no', @('list', 'secrets', '-n', 'pfs'))
    )

    Write-Host "`n--- CI/CD Tests ---" -ForegroundColor Cyan
    foreach ($deployment in @('frontend', 'auth-service', 'task-service')) {
        Test-Rbac "CI/CD can patch $deployment" 'yes' (@('patch', "deployments.apps/$deployment", '-n', 'pfs') + $ci)
    }
    Test-Cases -Identity $ci -Cases @(
        @('CI/CD cannot patch other Deployments', 'no', @('patch', 'deployments.apps/other-app', '-n', 'pfs')),
        @('CI/CD cannot modify MongoDB', 'no', @('patch', 'statefulsets.apps/mongodb', '-n', 'pfs')),
        @('CI/CD cannot read Secrets directly', 'no', @('list', 'secrets', '-n', 'pfs')),
        @('CI/CD cannot create RoleBindings', 'no', @('create', 'rolebindings', '-n', 'pfs')),
        @('CI/CD cannot create ClusterRoleBindings', 'no', @('create', 'clusterrolebindings'))
    )

    Write-Host "`n--- Environment Separation Tests ---" -ForegroundColor Cyan
    Test-Rbac 'Developer can access DEV' 'yes' (@('list', 'pods', '-n', 'pfs-dev') + $developer)
    Test-Rbac 'Developer cannot access PROD' 'no' (@('list', 'pods', '-n', 'pfs-prod') + $developer)
    foreach ($envName in @('dev', 'prod')) {
        $ownNamespace = "pfs-$envName"
        $otherNamespace = if ($envName -eq 'dev') { 'pfs-prod' } else { 'pfs-dev' }
        $observerIdentity = if ($envName -eq 'dev') { $devObserver } else { $prodObserver }
        $ciIdentity = if ($envName -eq 'dev') { $devCI } else { $prodCI }
        Test-Rbac "$envName observer can access own environment" 'yes' (@('list', 'pods', '-n', $ownNamespace) + $observerIdentity)
        Test-Rbac "$envName observer cannot access other environment" 'no' (@('list', 'pods', '-n', $otherNamespace) + $observerIdentity)
        Test-Rbac "$envName CI/CD can patch frontend in own environment" 'yes' (@('patch', 'deployments.apps/frontend', '-n', $ownNamespace) + $ciIdentity)
        Test-Rbac "$envName CI/CD cannot patch frontend in other environment" 'no' (@('patch', 'deployments.apps/frontend', '-n', $otherNamespace) + $ciIdentity)
        Test-Rbac "$envName CI/CD cannot patch unapproved Deployments" 'no' (@('patch', 'deployments.apps/other-app', '-n', $ownNamespace) + $ciIdentity)
        Test-Rbac "$envName CI/CD cannot modify RBAC" 'no' (@('create', 'rolebindings', '-n', $ownNamespace) + $ciIdentity)
    }

    Write-Host "`n--- Application ServiceAccount Tests ---" -ForegroundColor Cyan
    foreach ($account in @('frontend-sa', 'auth-sa', 'task-sa', 'mongodb-sa')) {
        $identity = Get-ServiceAccountIdentity 'pfs' $account
        Test-Cases -Identity $identity -Cases @(
            @("$account cannot list Pods", 'no', @('list', 'pods', '-n', 'pfs')),
            @("$account cannot list Secrets", 'no', @('list', 'secrets', '-n', 'pfs')),
            @("$account cannot delete Pods", 'no', @('delete', 'pods', '-n', 'pfs')),
            @("$account cannot modify RBAC", 'no', @('create', 'rolebindings', '-n', 'pfs')),
            @("$account cannot access PROD Pods", 'no', @('list', 'pods', '-n', 'pfs-prod'))
        )
    }

    Write-Host "`n--- Default ServiceAccount Tests ---" -ForegroundColor Cyan
    foreach ($ns in $namespaces) {
        $identity = Get-ServiceAccountIdentity $ns 'default'
        foreach ($target in $namespaces) {
            Test-Rbac "$ns default cannot list Pods in $target" 'no' (@('list', 'pods', '-n', $target) + $identity)
            Test-Rbac "$ns default cannot list Secrets in $target" 'no' (@('list', 'secrets', '-n', $target) + $identity)
            Test-Rbac "$ns default cannot create RoleBindings in $target" 'no' (@('create', 'rolebindings', '-n', $target) + $identity)
        }
        Test-Rbac "$ns default cannot delete Nodes" 'no' (@('delete', 'nodes') + $identity)
        Test-Rbac "$ns default cannot create ClusterRoleBindings" 'no' (@('create', 'clusterrolebindings') + $identity)
        Test-Rbac "$ns default has no wildcard administrator access" 'no' (@('*', '*', '--all-namespaces') + $identity)
    }

    Write-Host "`n========================================"
    Write-Host '       RBAC SECURITY TEST REPORT'
    Write-Host '========================================'
    Write-Host "Total tests : $($script:passed + $script:failed)"
    Write-Host "Passed      : $script:passed" -ForegroundColor Green
    Write-Host "Failed      : $script:failed" -ForegroundColor Red
    Write-Host "Errors      : $script:errors"
    Write-Host 'Coverage is the operations tested, not proof of every possible privilege.'
    if ($script:failed -gt 0) {
        Write-Host 'RESULT: FAILED' -ForegroundColor Red
        exit 1
    }
    Write-Host 'RESULT: PASSED' -ForegroundColor Green
    exit 0
}
catch {
    Write-Host "[ERROR] RBAC suite aborted: $_" -ForegroundColor Red
    exit 1
}
