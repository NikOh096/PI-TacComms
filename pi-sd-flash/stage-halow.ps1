$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$cardRoot = 'G:\'
$disk = Get-Disk -Number 2
if ($disk.IsSystem -or $disk.IsBoot -or $disk.Size -ne 125671833600 -or $disk.BusType -ne 'USB') {
    throw 'The expected removable SD card is not present.'
}
$partition = Get-Partition -DriveLetter G
if ($partition.DiskNumber -ne 2 -or $partition.Offset -ne 8388608 -or $partition.Size -ne 536870912) {
    throw 'The boot partition does not match the verified card.'
}
if ((Get-Volume -DriveLetter G).FileSystemLabel -ne 'bootfs') { throw 'Unexpected volume label' }
$cmdlinePath = Join-Path $cardRoot 'cmdline.txt'
$originalCommand = (Get-Content -LiteralPath $cmdlinePath -Raw).Trim()
if ($originalCommand -notmatch '(^| )root=PARTUUID=ff57595b-02( |$)') { throw 'Unexpected card identity' }
if ($originalCommand -match 'systemd\.run=') { throw 'Another one-time boot action is already armed.' }
$bundle = Join-Path $taskRoot 'halow-setup'
$destination = Join-Path $cardRoot 'halow-setup'
if (Test-Path -LiteralPath $destination) { throw 'Setup directory already exists; inspect before replacing.' }
Copy-Item -LiteralPath $bundle -Destination $destination -Recurse
foreach ($line in Get-Content -LiteralPath (Join-Path $bundle 'BUNDLE-SHA256SUMS')) {
    $parts = $line -split '  ', 2
    $actual = (Get-FileHash -LiteralPath (Join-Path $destination $parts[1]) -Algorithm SHA256).Hash
    if ($actual -ne $parts[0]) { throw ('Read-back verification failed: ' + $parts[1]) }
}
$configPath = Join-Path $cardRoot 'config.txt'
$config = Get-Content -LiteralPath $configPath -Raw
if ($config -notmatch 'dtoverlay=bw-ads7846') { throw 'Touchscreen configuration is missing' }
if ($config -notmatch '(?m)^dtoverlay=dwc2,dr_mode=peripheral\s*$') {
    $config = $config.TrimEnd() + "`n`n# USB-C management for this dedicated Pi`n[all]`ndtoverlay=dwc2,dr_mode=peripheral`n"
    [IO.File]::WriteAllText($configPath, $config, [Text.UTF8Encoding]::new($false))
}
$tokens = $originalCommand -split '\s+' | Where-Object {
    $_ -notin @('quiet','splash','plymouth.ignore-serial-consoles') -and
    $_ -notmatch '^(consoleblank=|video=HDMI-A-[12]:|cloud-init=)'
}
$tokens += @('video=HDMI-A-1:640x480@60','video=HDMI-A-2:640x480@60','consoleblank=60','cloud-init=disabled')
$tokens += @('systemd.run=/boot/firmware/halow-setup/bootstrap.sh','systemd.run_success_action=reboot',
             'systemd.run_failure_action=reboot','systemd.unit=kernel-command-line.target')
$finalCommand = ($tokens -join ' ') + "`n"
# Arm the setup only after all files have passed read-back verification.
[IO.File]::WriteAllText($cmdlinePath, $finalCommand, [Text.UTF8Encoding]::new($false))
if ([IO.File]::ReadAllText($cmdlinePath) -ne $finalCommand) { throw 'Kernel command line read-back failed' }
$result = @{status='staged';disk=2;drive='G:';username='niko';hostname='halow-pi';
    display='640x480; Terminus Bold 16x32';console_timeout_seconds=60;server_autostart=$true;
    hardware_tested=$false;files_verified=(Get-Content -LiteralPath (Join-Path $bundle 'BUNDLE-SHA256SUMS')).Count;
    staged_at=(Get-Date -Format o)}
$result | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskRoot 'staging-result.json')
$result | ConvertTo-Json
