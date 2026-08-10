param(
  [Parameter(Mandatory = $true)][string]$SourceJpeg,
  [Parameter(Mandatory = $true)][string]$OutputIco
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$source = [System.Drawing.Image]::FromFile($SourceJpeg)
try {
  if ($source.Width -ne $source.Height) {
    throw "Canonical app icon must be square for scale-only derivation: $($source.Width)x$($source.Height)"
  }

  $sizes = @(16, 24, 32, 48, 64, 128, 256)
  $frames = @()

  foreach ($size in $sizes) {
    $bitmap = New-Object System.Drawing.Bitmap($size, $size, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    try {
      $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
      try {
        $graphics.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceCopy
        $graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
        $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
        $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
        $graphics.DrawImage($source, 0, 0, $size, $size)
      } finally {
        $graphics.Dispose()
      }

      $stream = New-Object System.IO.MemoryStream
      try {
        $bitmap.Save($stream, [System.Drawing.Imaging.ImageFormat]::Png)
        $frames += ,@($size, $stream.ToArray())
      } finally {
        $stream.Dispose()
      }
    } finally {
      $bitmap.Dispose()
    }
  }

  $outputDirectory = Split-Path -Parent $OutputIco
  New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null

  $file = [System.IO.File]::Open($OutputIco, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write)
  try {
    $writer = New-Object System.IO.BinaryWriter($file)
    try {
      $writer.Write([UInt16]0)
      $writer.Write([UInt16]1)
      $writer.Write([UInt16]$frames.Count)

      $offset = 6 + (16 * $frames.Count)
      foreach ($frame in $frames) {
        $size = [int]$frame[0]
        $bytes = [byte[]]$frame[1]
        $dimension = if ($size -eq 256) { [byte]0 } else { [byte]$size }
        $writer.Write($dimension)
        $writer.Write($dimension)
        $writer.Write([byte]0)
        $writer.Write([byte]0)
        $writer.Write([UInt16]1)
        $writer.Write([UInt16]32)
        $writer.Write([UInt32]$bytes.Length)
        $writer.Write([UInt32]$offset)
        $offset += $bytes.Length
      }

      foreach ($frame in $frames) {
        $writer.Write([byte[]]$frame[1])
      }
    } finally {
      $writer.Dispose()
    }
  } finally {
    $file.Dispose()
  }

  if ((Get-Item $OutputIco).Length -le 0) {
    throw 'Generated Windows icon is empty.'
  }

  Write-Host "ILAIOS_WINDOWS_ICON_DERIVATION=PASS"
} finally {
  $source.Dispose()
}
