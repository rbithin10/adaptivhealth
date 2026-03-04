# DEV ONLY — BLE Peripheral Advertiser for Windows 10/11
# Puts this PC into BLE advertising mode as a fake Heart Rate Monitor (0x180D).
# AdaptivHealth will see it in its BLE scan list.
# Run as Administrator in PowerShell.

Add-Type -AssemblyName System.Runtime.WindowsRuntime

# Load WinRT BLE advertisement types (must be single-line each)
$null = [Windows.Devices.Bluetooth.Advertisement.BluetoothLEAdvertisementPublisher,Windows.Devices.Bluetooth,ContentType=WindowsRuntime]
$null = [Windows.Devices.Bluetooth.Advertisement.BluetoothLEAdvertisement,Windows.Devices.Bluetooth,ContentType=WindowsRuntime]

# Create the publisher
$publisher = New-Object Windows.Devices.Bluetooth.Advertisement.BluetoothLEAdvertisementPublisher

# Add Heart Rate Service UUID (0x180D) — this is what AdaptivHealth scans for
$serviceUuid = [System.Guid]"0000180D-0000-1000-8000-00805F9B34FB"
$publisher.Advertisement.ServiceUuids.Add($serviceUuid)

# Set a human-readable local name (shows in AdaptivHealth scan list)
$publisher.Advertisement.LocalName = "TestHRM-PC"

# Start advertising
$publisher.Start()

if ($publisher.Status -eq "Started") {
    Write-Host ""
    Write-Host "✅ BLE advertising STARTED" -ForegroundColor Green
    Write-Host "   Device name : TestHRM-PC"
    Write-Host "   Service UUID: 0x180D (Heart Rate)"
    Write-Host ""
    Write-Host "→ Now open AdaptivHealth on your phone"
    Write-Host "→ Tap 'Scan BLE Devices'"
    Write-Host "→ 'TestHRM-PC' should appear in the list within 5 seconds"
    Write-Host ""
    Write-Host "Press ENTER to stop advertising..." -ForegroundColor Yellow
    Read-Host
} else {
    Write-Host ""
    Write-Host "❌ Failed to start. Status: $($publisher.Status)" -ForegroundColor Red
    Write-Host "   Make sure Bluetooth is ON and you're running as Administrator."
    Write-Host ""
    exit 1
}

$publisher.Stop()
Write-Host "⏹  Advertising stopped." -ForegroundColor Cyan
