# File: tools/exe_ui_smoke.ps1
# Purpose: Repeatable Windows-only smoke check for the packaged EXE. Drives the
#          real wizard through UI Automation in demo mode, exports the three
#          Word drafts and verifies that they were written to a temporary
#          Desktop (never the real one).
# Encoding: UTF-8 with BOM (Windows PowerShell 5.1 needs the BOM for Chinese
#           literals such as the window titles and button labels).
<#
.SYNOPSIS
    Runs a packaged-EXE UI smoke check on Windows.

.DESCRIPTION
    Launches dist\民事立案文书助手\民事立案文书助手.exe in demo mode, dismisses the
    advisory network dialog, fills the demo case, walks the five wizard steps,
    clicks "生成 Word 初稿" and checks that the three expected .docx files exist.

    The process USERPROFILE is redirected to a temporary directory so the
    default output folder stays out of the real Desktop; the directory is
    removed afterwards.

    This script needs an interactive desktop session and is therefore not part
    of CI. It complements, but does not replace, the pytest suite and the
    manual restricted acceptance.

.PARAMETER ExePath
    Optional path to the packaged EXE. Defaults to the build.bat output.

.PARAMETER StartupTimeoutSeconds
    How long to wait for the main wizard window. Defaults to 30 seconds.
#>
[CmdletBinding()]
param(
    [string]$ExePath = "",
    [int]$StartupTimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class CfaExeSmokeWin32 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
}
"@

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $ExePath) {
    $ExePath = Join-Path $repoRoot "dist\民事立案文书助手\民事立案文书助手.exe"
}
if (-not (Test-Path $ExePath)) {
    throw "找不到 EXE：$ExePath。请先在仓库根目录运行 build.bat。"
}
$ExePath = (Resolve-Path $ExePath).Path

$testHome = Join-Path $env:TEMP ("cfa-exe-smoke-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path (Join-Path $testHome "Desktop") | Out-Null

function Get-TopWindows([int]$processId) {
    $cond = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ProcessIdProperty, $processId)
    return [System.Windows.Automation.AutomationElement]::RootElement.FindAll(
        [System.Windows.Automation.TreeScope]::Children, $cond)
}

function Wait-MainWindow([int]$processId, [int]$seconds) {
    $deadline = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $deadline) {
        foreach ($window in (Get-TopWindows $processId)) {
            if ($window.Current.ClassName -eq "LawsuitWizard") {
                return $window
            }
        }
        Start-Sleep -Milliseconds 500
    }
    throw "主窗口在 $seconds 秒内未出现。"
}

function Find-Button($root, [string]$name) {
    $cond = New-Object System.Windows.Automation.AndCondition(
        (New-Object System.Windows.Automation.PropertyCondition(
            [System.Windows.Automation.AutomationElement]::NameProperty, $name)),
        (New-Object System.Windows.Automation.PropertyCondition(
            [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
            [System.Windows.Automation.ControlType]::Button)))
    return $root.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $cond)
}

function Invoke-Button($root, [string]$name) {
    $element = Find-Button $root $name
    if ($null -eq $element) {
        throw "找不到按钮：$name"
    }
    if (-not $element.Current.IsEnabled) {
        throw "按钮当前不可用：$name"
    }
    $element.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
    Write-Host "  点击：$name"
}

function Show-VisibleButtons($window) {
    $names = @()
    $all = $window.FindAll([System.Windows.Automation.TreeScope]::Descendants,
        [System.Windows.Automation.Condition]::TrueCondition)
    foreach ($element in $all) {
        if ($element.Current.ControlType.ProgrammaticName -eq 'ControlType.Button' -and
            -not $element.Current.IsOffscreen) {
            $names += $element.Current.Name
        }
    }
    Write-Host "  可见按钮：$($names -join ' | ')"
}

function Clear-Notices($main) {
    # Message boxes are transient children of the wizard, so they are found in
    # its subtree rather than as top-level windows.
    for ($round = 1; $round -le 5; $round++) {
        $cond = New-Object System.Windows.Automation.PropertyCondition(
            [System.Windows.Automation.AutomationElement]::ClassNameProperty, "QMessageBox")
        $boxes = $main.FindAll([System.Windows.Automation.TreeScope]::Descendants, $cond)
        if ($boxes.Count -eq 0) {
            return
        }
        foreach ($box in $boxes) {
            Write-Host "  对话框：$($box.Current.Name)"
            $button = Find-Button $box "确认覆盖"
            if ($null -eq $button) {
                $button = Find-Button $box "确定"
            }
            if ($null -eq $button -or -not $button.Current.IsEnabled) {
                throw "无法关闭对话框：$($box.Current.Name)"
            }
            $button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
            Start-Sleep -Seconds 1
        }
    }
}

$process = $null
$exitCode = 1
try {
    Write-Host "EXE：$ExePath"
    Write-Host "临时 USERPROFILE：$testHome"

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $ExePath
    $startInfo.Arguments = "--demo"
    $startInfo.WorkingDirectory = Split-Path $ExePath
    $startInfo.UseShellExecute = $false
    $startInfo.EnvironmentVariables["USERPROFILE"] = $testHome
    $process = [System.Diagnostics.Process]::Start($startInfo)
    Write-Host "PID：$($process.Id)"

    Start-Sleep -Seconds 8
    $process.Refresh()
    if ($process.HasExited) {
        throw "EXE 在启动阶段退出，退出码 $($process.ExitCode)。"
    }

    # The advisory network dialog is top-level (it has no wizard parent).
    foreach ($window in (Get-TopWindows $process.Id)) {
        if ($window.Current.ClassName -eq "QMessageBox") {
            Write-Host "启动对话框：$($window.Current.Name)"
            if ($window.Current.NativeWindowHandle -ne 0) {
                [CfaExeSmokeWin32]::SetForegroundWindow(
                    [IntPtr]$window.Current.NativeWindowHandle) | Out-Null
            }
            Start-Sleep -Milliseconds 400
            [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
            Start-Sleep -Seconds 1
        }
    }

    $main = Wait-MainWindow $process.Id $StartupTimeoutSeconds
    Write-Host "主窗口：$($main.Current.Name)"
    Show-VisibleButtons $main

    # Party cards are created only when the party page is first shown, so the
    # demo fill is run twice: once for the claim pages, then again after the
    # party page has been visited.
    Invoke-Button $main "一键填写测试数据"
    Start-Sleep -Seconds 2
    Clear-Notices $main

    Invoke-Button $main "下一步"
    Start-Sleep -Seconds 2
    Clear-Notices $main
    Invoke-Button $main "下一步"
    Start-Sleep -Seconds 2
    Clear-Notices $main

    Invoke-Button $main "上一步"
    Start-Sleep -Seconds 1
    Invoke-Button $main "上一步"
    Start-Sleep -Seconds 1
    Clear-Notices $main

    Invoke-Button $main "一键填写测试数据"
    Start-Sleep -Seconds 2
    Clear-Notices $main
    Show-VisibleButtons $main

    for ($step = 1; $step -le 5; $step++) {
        $main = Wait-MainWindow $process.Id $StartupTimeoutSeconds
        Clear-Notices $main
        Invoke-Button $main "下一步"
        Start-Sleep -Seconds 2
        Clear-Notices $main
    }

    $main = Wait-MainWindow $process.Id $StartupTimeoutSeconds
    Invoke-Button $main "生成 Word 初稿"

    $documents = @()
    $deadline = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $deadline) {
        Clear-Notices $main
        $documents = @(Get-ChildItem (Join-Path $testHome "Desktop") -Recurse -File `
            -Filter *.docx -ErrorAction SilentlyContinue)
        if ($documents.Count -ge 3) {
            break
        }
        Start-Sleep -Seconds 1
    }

    if ($documents.Count -ne 3) {
        throw "期望生成 3 份文书，实际 $($documents.Count) 份。"
    }
    foreach ($keyword in @("起诉状", "证据清单", "送达地址确认书")) {
        if (-not ($documents | Where-Object { $_.Name -like "*$keyword*" })) {
            throw "缺少文书：$keyword"
        }
    }

    foreach ($document in $documents) {
        Write-Host "  生成：$($document.Name)（$($document.Length) 字节）"
    }
    Write-Host "PASS：EXE 启动、五步向导与三份文书生成均正常。"
    $exitCode = 0
} catch {
    Write-Host "FAIL：$($_.Exception.Message)" -ForegroundColor Red
    $exitCode = 1
} finally {
    if ($null -ne $process -and -not $process.HasExited) {
        $process.Kill()
        $process.WaitForExit()
    }
    if (Test-Path $testHome) {
        Remove-Item -Recurse -Force $testHome -ErrorAction SilentlyContinue
    }
}

exit $exitCode
