$ErrorActionPreference = 'Stop'
$piWork = $PSScriptRoot
$piUrl = 'https://downloads.raspberrypi.com/raspios_arm64/images/raspios_arm64-2026-09-15/2026-09-15-raspios-trixie-arm64.img.xz'
$piTotal = 1372609344L
$piPrefix = Join-Path $piWork '2026-09-15-raspios-trixie-arm64.img.xz'
$piPrefixLength = (Get-Item -LiteralPath $piPrefix).Length
if ($piPrefixLength -ne 162177024L) { throw 'Unexpected partial-download size' }
$piChunkSize = 8MB
$piChunkCount = [int][Math]::Ceiling(($piTotal - $piPrefixLength) / [double]$piChunkSize)
$piRanges = for ($piIndex = 0; $piIndex -lt $piChunkCount; $piIndex++) {
    $piStart = $piPrefixLength + $piIndex * $piChunkSize
    $piEnd = [Math]::Min($piTotal - 1, $piStart + $piChunkSize - 1)
    [pscustomobject]@{ Index = $piIndex; Start = $piStart; End = $piEnd; Path = (Join-Path $piWork "image-chunk-$piIndex.bin") }
}
$piRanges | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $piWork 'download-ranges.json')
$piResults = @($piRanges | ForEach-Object -Parallel {
    $piRange = $_
    $piHeader = $piRange.Path + '.headers'
    & curl.exe --fail --location --silent --show-error --retry 3 --max-time 90 --range "$($piRange.Start)-$($piRange.End)" --dump-header $piHeader --output $piRange.Path $using:piUrl
    if ($LASTEXITCODE -ne 0) { throw "Range $($piRange.Index) download failed" }
    $piExpectedLength = $piRange.End - $piRange.Start + 1
    if ((Get-Item -LiteralPath $piRange.Path).Length -ne $piExpectedLength) { throw "Range $($piRange.Index) length mismatch" }
    $piExpectedHeader = "content-range: bytes $($piRange.Start)-$($piRange.End)/$using:piTotal"
    if (-not ((Get-Content -LiteralPath $piHeader) | Where-Object { $_.Trim() -ieq $piExpectedHeader })) { throw "Range $($piRange.Index) response mismatch" }
    if ($piRange.Index % 20 -eq 0) { Write-Host "Download section $($piRange.Index + 1) of $using:piChunkCount complete." }
    $piRange.Index
} -ThrottleLimit 7)
if ($piResults.Count -ne $piChunkCount) { throw 'One or more download sections failed' }
$piFinal = Join-Path $piWork 'raspios-trixie-arm64-verified.img.xz'
$piOutput = [IO.File]::Create($piFinal)
try {
    foreach ($piPart in @($piPrefix) + @($piRanges.Path)) {
        $piInput = [IO.File]::OpenRead($piPart)
        try { $piInput.CopyTo($piOutput) } finally { $piInput.Dispose() }
    }
} finally { $piOutput.Dispose() }
if ((Get-Item -LiteralPath $piFinal).Length -ne $piTotal) { throw 'Combined image length mismatch' }
$piHash = (Get-FileHash -LiteralPath $piFinal -Algorithm SHA256).Hash
if ($piHash -ne '61d95799550aac32788bb3cacc3d471dcc860f8053ce989dec4aecc388b799dd') { throw 'OS image SHA256 verification failed' }
Write-Output "OS image downloaded and SHA256 verified: $piHash"
