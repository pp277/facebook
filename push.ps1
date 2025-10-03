Param(
    [Parameter(Mandatory = $true)] [string]$RepoUrl,
    [string]$Branch = "main"
)

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "git is not installed or not in PATH."; exit 1
}

if (-not (Test-Path .git)) {
    git init
}

git add -A

if (-not (git rev-parse --verify HEAD 2>$null)) {
    git commit -m "Initial commit: news auto publisher"
} else {
    git commit -m "Update"
}

if (-not (git remote get-url origin 2>$null)) {
    git remote add origin $RepoUrl
} else {
    git remote set-url origin $RepoUrl
}

git branch -M $Branch
git push -u origin $Branch

Write-Host "Pushed to $RepoUrl ($Branch)"


