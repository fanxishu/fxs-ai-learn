$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

# Render at 4x resolution, then downsample for smooth native PNG tab icons.
$outputDir = Join-Path $PSScriptRoot '../src/assets/tabbar'
if (-not (Test-Path $outputDir -PathType Container)) {
    throw "Missing tab icon directory: $outputDir"
}

foreach ($name in @('home', 'history', 'mine')) {
    foreach ($active in @($false, $true)) {
        $color = if ($active) { '#ff7a2f' } else { '#7A7E83' }
        $suffix = if ($active) { '-active' } else { '' }
        $canvas = [System.Drawing.Bitmap]::new(288, 288)
        $graphics = [System.Drawing.Graphics]::FromImage($canvas)
        $pen = [System.Drawing.Pen]::new([System.Drawing.ColorTranslator]::FromHtml($color), 1.8)
        $path = [System.Drawing.Drawing2D.GraphicsPath]::new()
        $icon = [System.Drawing.Bitmap]::new(72, 72)
        $target = [System.Drawing.Graphics]::FromImage($icon)
        try {
            $graphics.Clear([System.Drawing.Color]::Transparent)
            $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
            $graphics.ScaleTransform(12, 12)
            $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
            $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
            $pen.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round

            switch ($name) {
                'home' {
                    $path.AddLine(3, 10, 12, 3)
                    $path.AddLine(12, 3, 21, 10)
                    $path.StartFigure()
                    $path.AddLine(5, 9, 5, 21)
                    $path.AddLine(5, 21, 10, 21)
                    $path.AddLine(10, 21, 10, 15)
                    $path.AddLine(10, 15, 14, 15)
                    $path.AddLine(14, 15, 14, 21)
                    $path.AddLine(14, 21, 19, 21)
                    $path.AddLine(19, 21, 19, 9)
                }
                'history' {
                    $path.AddEllipse(3, 3, 18, 18)
                    $path.StartFigure()
                    $path.AddLine(12, 7, 12, 12)
                    $path.AddLine(12, 12, 16, 14)
                }
                'mine' {
                    $path.AddEllipse(8, 3, 8, 8)
                    $path.StartFigure()
                    $path.AddBezier(4, 21, 4, 12, 20, 12, 20, 21)
                }
            }
            $graphics.DrawPath($pen, $path)
            $target.Clear([System.Drawing.Color]::Transparent)
            $target.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $target.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
            $target.DrawImage($canvas, 0, 0, 72, 72)
            $file = Join-Path $outputDir "$name$suffix.png"
            $icon.Save($file, [System.Drawing.Imaging.ImageFormat]::Png)
            Write-Host "Generated $name$suffix.png (72x72, $color)"
        } finally {
            $target.Dispose()
            $icon.Dispose()
            $path.Dispose()
            $pen.Dispose()
            $graphics.Dispose()
            $canvas.Dispose()
        }
    }
}
