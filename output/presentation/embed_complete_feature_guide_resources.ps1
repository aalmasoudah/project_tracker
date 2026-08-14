[CmdletBinding()]
param(
    [string]$HtmlPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($HtmlPath)) {
    $HtmlPath = Join-Path $PSScriptRoot "insight-tracker-complete-feature-guide-ar.html"
}

$workspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
$resolvedHtml = (Resolve-Path -LiteralPath $HtmlPath).Path
if (-not $resolvedHtml.StartsWith($workspace + "\", [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to update an HTML file outside the workspace."
}

$resources = [ordered]@{
    "../../static/vendor/fonts/NotoSansArabic-VariableFont_wdth,wght.ttf" = @(
        "static\vendor\fonts\NotoSansArabic-VariableFont_wdth,wght.ttf",
        "font/ttf"
    )
    "../../static/img/insight-tracker-mark.png" = @(
        "static\img\insight-tracker-mark.png",
        "image/png"
    )
    "../../static/img/insight-tracker-logo.png" = @(
        "static\img\insight-tracker-logo.png",
        "image/png"
    )
    "assets/dashboard-ar.png" = @(
        "output\presentation\assets\dashboard-ar.png",
        "image/png"
    )
    "assets/projects-ar.png" = @(
        "output\presentation\assets\projects-ar.png",
        "image/png"
    )
    "assets/project-detail-ar.png" = @(
        "output\presentation\assets\project-detail-ar.png",
        "image/png"
    )
    "assets/reports-ar.png" = @(
        "output\presentation\assets\reports-ar.png",
        "image/png"
    )
    "assets/ai-briefing-ar.png" = @(
        "output\presentation\assets\ai-briefing-ar.png",
        "image/png"
    )
    "assets/project-agent-ar.png" = @(
        "output\presentation\assets\project-agent-ar.png",
        "image/png"
    )
    "assets/audit-ar.png" = @(
        "output\presentation\assets\audit-ar.png",
        "image/png"
    )
    "assets/n8n-telegram-ai-workflow.png" = @(
        "output\presentation\assets\n8n-telegram-ai-workflow.png",
        "image/png"
    )
}

function Get-ResourceMimeType {
    param(
        [byte[]]$Bytes,
        [string]$Fallback
    )

    if ($Bytes.Length -ge 4) {
        if ($Bytes[0] -eq 0x89 -and $Bytes[1] -eq 0x50 -and
            $Bytes[2] -eq 0x4E -and $Bytes[3] -eq 0x47) {
            return "image/png"
        }
        if ($Bytes[0] -eq 0xFF -and $Bytes[1] -eq 0xD8 -and
            $Bytes[2] -eq 0xFF) {
            return "image/jpeg"
        }
        if (($Bytes[0] -eq 0x00 -and $Bytes[1] -eq 0x01 -and
             $Bytes[2] -eq 0x00 -and $Bytes[3] -eq 0x00) -or
            ($Bytes[0] -eq 0x4F -and $Bytes[1] -eq 0x54 -and
             $Bytes[2] -eq 0x54 -and $Bytes[3] -eq 0x4F)) {
            return "font/ttf"
        }
    }

    return $Fallback
}

$html = [System.IO.File]::ReadAllText($resolvedHtml, [System.Text.Encoding]::UTF8)
$wrongJpegPrefix = "data:image/png;base64,/9j/"
$repaired = ([regex]::Matches($html, [regex]::Escape($wrongJpegPrefix))).Count
if ($repaired -gt 0) {
    $html = $html.Replace($wrongJpegPrefix, "data:image/jpeg;base64,/9j/")
}
$embedded = 0
foreach ($reference in $resources.Keys) {
    if (-not $html.Contains($reference)) {
        continue
    }
    $resourcePath = Join-Path $workspace $resources[$reference][0]
    if (-not (Test-Path -LiteralPath $resourcePath)) {
        throw "Required resource is missing: $resourcePath"
    }
    $bytes = [System.IO.File]::ReadAllBytes($resourcePath)
    $mimeType = Get-ResourceMimeType -Bytes $bytes -Fallback $resources[$reference][1]
    $base64 = [System.Convert]::ToBase64String($bytes)
    $html = $html.Replace($reference, "data:$mimeType;base64,$base64")
    $embedded += 1
}

if ($embedded -eq 0 -and $repaired -eq 0) {
    Write-Output "No external resources remained to embed."
    exit 0
}

[System.IO.File]::WriteAllText(
    $resolvedHtml,
    $html,
    [System.Text.UTF8Encoding]::new($false)
)
Write-Output "Embedded $embedded local resources and repaired $repaired MIME references in $resolvedHtml"
