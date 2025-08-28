# PowerShell script to create test database for radiator tests
# Run this script to create the radiator_test database

param(
    [switch]$Drop
)

# Database connection parameters
$dbHost = "localhost"
$dbPort = "5432"
$dbUser = "postgres"
$dbPassword = "12345"
$dbName = "postgres"  # Connect to default postgres database first

try {
    # Check if psql is available
    $psqlPath = Get-Command psql -ErrorAction SilentlyContinue
    if (-not $psqlPath) {
        Write-Error "psql command not found. Please ensure PostgreSQL is installed and psql is in your PATH."
        exit 1
    }

    if ($Drop) {
        # Drop test database
        Write-Host "Dropping test database 'radiator_test'..."
        $dropQuery = "DROP DATABASE IF EXISTS radiator_test;"
        $dropQuery | psql -h $dbHost -p $dbPort -U $dbUser -d $dbName
        Write-Host "Test database 'radiator_test' dropped successfully."
    } else {
        # Create test database
        Write-Host "Creating test database 'radiator_test'..."
        $createQuery = "CREATE DATABASE radiator_test;"
        $createQuery | psql -h $dbHost -p $dbPort -U $dbUser -d $dbName
        Write-Host "Test database 'radiator_test' created successfully."
    }
} catch {
    Write-Error "Error: $_"
    exit 1
}
