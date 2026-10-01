$ErrorActionPreference = 'Stop'
$piImage = Join-Path $PSScriptRoot 'raspios-trixie-arm64-verified.img.xz'
$piExpectedImageHash = '61d95799550aac32788bb3cacc3d471dcc860f8053ce989dec4aecc388b799dd'
if ((Get-FileHash -LiteralPath $piImage -Algorithm SHA256).Hash -ne $piExpectedImageHash) { throw 'OS image integrity check failed' }
$piDisk = Get-Disk -Number 2
if ($piDisk.Size -ne 125671833600L -or $piDisk.SerialNumber.Trim() -ne '000000002961' -or $piDisk.FriendlyName.Trim() -ne 'Generic MassStorageClass' -or $piDisk.BusType -ne 'USB' -or $piDisk.IsBoot -or $piDisk.IsSystem -or $piDisk.IsReadOnly) { throw 'The target disk no longer matches the identified blank microSD card' }
$piPartitions = @(Get-Partition -DiskNumber 2)
if ($piPartitions.Count -ne 1 -or $piPartitions[0].DriveLetter -ne 'G') { throw 'The target partition layout changed' }
$piVolume = Get-Volume -DriveLetter G
if ($piVolume.DriveType -ne 'Removable' -or $piVolume.FileSystem -ne 'exFAT' -or ($piVolume.Size - $piVolume.SizeRemaining) -gt 10MB) { throw 'The target volume no longer looks blank' }
$piFiles = @(Get-ChildItem -LiteralPath 'G:\' -Force | Where-Object { $_.Name -ne 'System Volume Information' })
if ($piFiles.Count -ne 0) { throw 'Unexpected files appeared on the target card' }
$piImager = 'C:\Program Files\Raspberry Pi Ltd\Imager\rpi-imager.exe'
$piSignature = Get-AuthenticodeSignature -LiteralPath $piImager
if ($piSignature.Status -ne 'Valid' -or $piSignature.SignerCertificate.Subject -notmatch 'Raspberry Pi') { throw 'Imager signature check failed' }
Write-Output 'Writing Raspberry Pi OS 64-bit (2026-09-15) to the verified 125.67 GB removable card on PhysicalDrive2.'
Write-Output 'Read-back verification and automatic eject are enabled.'
& $piImager --cli --sha256 'df19cbb09fe8ed30580b34a3da96fb963e7553193e62666d6ed6dd46f4c0f13a' $piImage '\\.\PhysicalDrive2' | Out-Host
$piExit = $LASTEXITCODE
[pscustomobject]@{
    CompletedAt = (Get-Date -Format o)
    ImagerExitCode = $piExit
    Image = $piImage
    ImageSHA256 = $piExpectedImageHash
    OS = 'Raspberry Pi OS 64-bit Desktop, Debian 13 Trixie, 2026-09-15'
    DiskNumber = 2
    DiskSerialNumber = '000000002961'
    DiskSize = 125671833600L
    ReadBackVerificationEnabled = $true
    AutomaticEjectEnabled = $true
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'flash-result.json')
if ($piExit -ne 0) { throw "Raspberry Pi Imager failed with exit code $piExit" }
Write-Output 'Imager completed successfully with verification enabled.'
