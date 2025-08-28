# PowerShell script to run tests with proper test environment configuration
# This script sets up the test environment and runs pytest

param(
    [string]$TestPath = "tests/",
    [string]$Markers = "",
    [switch]$Coverage,
    [switch]$Verbose,
    [switch]$CreateTestDB,
    [switch]$DropTestDB,
    [switch]$ResetTestDB,
    [switch]$CheckEnv
)

# Set only the environment variable - other variables will be loaded from env.test
$env:ENVIRONMENT = "test"

# Function to create test database
function Create-TestDatabase {
    Write-Host "Creating test database 'radiator_test'..." -ForegroundColor Green
    python scripts/database/create_test_db.py
}

# Function to drop test database
function Drop-TestDatabase {
    Write-Host "Dropping test database 'radiator_test'..." -ForegroundColor Yellow
    python scripts/database/create_test_db.py --drop
}

# Function to check test environment
function Check-TestEnvironment {
    Write-Host "Checking test environment configuration..." -ForegroundColor Cyan
    python -c "from radiator.core.config import settings; print(f'ENVIRONMENT: {settings.ENVIRONMENT}'); print(f'Database URL: {settings.DATABASE_URL}'); print(f'Is Test Environment: {settings.is_test_environment}'); print(f'Secret Key: {settings.SECRET_KEY[:20]}...')"
}

# Function to run tests
function Run-Tests {
    $pytestArgs = @()
    
    # Add test path
    $pytestArgs += $TestPath
    
    # Add verbose flag
    if ($Verbose) {
        $pytestArgs += "-v"
    }
    
    # Add markers if specified
    if ($Markers) {
        $pytestArgs += "-m", $Markers
    }
    
    # Add coverage if requested
    if ($Coverage) {
        $pytestArgs += "--cov=radiator", "--cov-report=html", "--cov-report=term-missing"
    }
    
    Write-Host "Running tests with command: pytest $($pytestArgs -join ' ')" -ForegroundColor Green
    python -m pytest $pytestArgs
}

# Main execution
try {
    # Handle database management commands
    if ($CreateTestDB) {
        Create-TestDatabase
        return
    }
    
    if ($DropTestDB) {
        Drop-TestDatabase
        return
    }
    
    if ($ResetTestDB) {
        Drop-TestDatabase
        Create-TestDatabase
        Write-Host "Test database reset complete." -ForegroundColor Green
        return
    }
    
    if ($CheckEnv) {
        Check-TestEnvironment
        return
    }
    
    # Check if test database exists and create if needed
    Write-Host "Checking test database..." -ForegroundColor Cyan
    try {
        $testDBExists = python -c "import psycopg2; conn = psycopg2.connect('postgresql://postgres:12345@localhost:5432/radiator_test'); conn.close(); print('Test database exists')" 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Test database 'radiator_test' does not exist. Creating..." -ForegroundColor Yellow
            Create-TestDatabase
        } else {
            Write-Host "Test database 'radiator_test' exists." -ForegroundColor Green
        }
    } catch {
        Write-Host "Error checking test database: $_" -ForegroundColor Red
        Write-Host "Creating test database..." -ForegroundColor Yellow
        Create-TestDatabase
    }
    
    # Run tests
    Run-Tests
    
} catch {
    Write-Error "Error: $_"
    exit 1
} finally {
    # Clean up environment variables
    Remove-Item Env:ENVIRONMENT -ErrorAction SilentlyContinue
}
