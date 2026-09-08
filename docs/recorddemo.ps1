<#
Voidscape demo recorder  (v2)

Records ONE terminal window while typing real commands into it at human pace, producing raw
footage for Screen Studio.

Why region capture and not `-i title=<window>`:
  gdigrab's window mode uses GDI BitBlt, which returns black for DWM-composited windows -
  Windows Terminal included. Verified: title capture gave a 41s, 1112x626, entirely black file.
  Capturing the desktop *region* the window occupies works. Cost: the window must stay
  foreground and unoccluded for the whole take, so anything that pops over it is filmed.

Safety:
  - focus guard before every keystroke batch; aborts rather than typing into another window
  - graceful ffmpeg stop ('q' on stdin) so the mp4 gets a valid moov atom

Usage: powershell -NoProfile -ExecutionPolicy Bypass -File record-demo.ps1 [-Out <dir>]
#>
param(
    [string]$Out    = "$PSScriptRoot",
    [string]$Title  = "VOIDSCAPE_DEMO",
    [int]$TypeMs    = 55,      # per-character delay; 40-70 reads as natural
    [int]$Width     = 1280,    # window is sized to this for a clean 16:9-ish frame
    [int]$Height    = 720
)

Add-Type @"
using System;using System.Text;using System.Runtime.InteropServices;
public struct RC { public int L,T,Rt,B; }
public class Win {
  [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc f, IntPtr l);
  [DllImport("user32.dll")] static extern int GetWindowText(IntPtr h, StringBuilder s, int c);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RC r);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h,int c);
  [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr h,int x,int y,int w,int ht,bool rp);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  delegate bool EnumProc(IntPtr h, IntPtr l);
  public static IntPtr Find(string t){ IntPtr res=IntPtr.Zero;
    EnumWindows((h,l)=>{ if(IsWindowVisible(h)){ var sb=new StringBuilder(300); GetWindowText(h,sb,300);
      if(sb.ToString()==t){ res=h; return false; } } return true; }, IntPtr.Zero);
    return res; }
  public static string FgTitle(){ var sb=new StringBuilder(300); GetWindowText(GetForegroundWindow(),sb,300); return sb.ToString(); }
}
"@ -ErrorAction SilentlyContinue

$sh = New-Object -ComObject WScript.Shell

function Get-Target {
    $h = [Win]::Find($Title)
    if ($h -eq [IntPtr]::Zero) {
        Start-Process cmd -ArgumentList '/k',"title $Title&&prompt \$G&&cls"
        Start-Sleep -Seconds 3
        $h = [Win]::Find($Title)
    }
    if ($h -eq [IntPtr]::Zero) { throw "could not create or find a window titled $Title" }
    return $h
}

function Assert-Focus {
    $fg = [Win]::FgTitle()
    if ($fg -ne $Title) { throw "focus guard: foreground is '$fg', refusing to send keys" }
}

function Type-Line([string]$Text, [int]$PauseAfter = 1200) {
    Assert-Focus
    foreach ($ch in $Text.ToCharArray()) {
        $c = [string]$ch
        if ('+^%~(){}[]'.Contains($c)) { $c = "{$c}" }   # SendKeys control chars
        $sh.SendKeys($c)
        Start-Sleep -Milliseconds $TypeMs
    }
    Start-Sleep -Milliseconds 350        # beat before Enter, like a human
    $sh.SendKeys('{ENTER}')
    Start-Sleep -Milliseconds $PauseAfter
}

# --- prepare the window ------------------------------------------------------
$h = Get-Target
$null = [Win]::ShowWindow($h, 9)                       # SW_RESTORE
$null = [Win]::MoveWindow($h, 120, 90, $Width, $Height, $true)
$null = [Win]::SetForegroundWindow($h)
Start-Sleep -Milliseconds 900
Assert-Focus

$sh.SendKeys('cls{ENTER}')                             # clean slate on camera
Start-Sleep -Milliseconds 600

$r = New-Object RC; $null = [Win]::GetWindowRect($h, [ref]$r)
$w  = [math]::Floor(($r.Rt - $r.L)/2)*2                # libx264 rejects odd dimensions
$ht = [math]::Floor(($r.B  - $r.T)/2)*2

# --- start recording ---------------------------------------------------------
New-Item -ItemType Directory -Force $Out | Out-Null
$mp4 = Join-Path $Out ("voidscape-demo-{0}.mp4" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName  = 'ffmpeg'
$psi.Arguments = "-hide_banner -loglevel error -f gdigrab -framerate 30 " +
                 "-offset_x $($r.L) -offset_y $($r.T) -video_size ${w}x${ht} -i desktop " +
                 "-c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p -y `"$mp4`""
$psi.RedirectStandardInput = $true
$psi.UseShellExecute = $false
$psi.CreateNoWindow  = $true
$ff = [System.Diagnostics.Process]::Start($psi)
Start-Sleep -Seconds 2                                  # clean frames before typing

# --- the demo script ---------------------------------------------------------
# Each line is one take. Reorder or extend freely; keep pauses >= render time.
$cli  = 'python skill/scripts/voidscape.py'
$clip = 'samples/build-week-demo.mp4'
try {
    Type-Line "$cli doctor"                                              4500
    Type-Line "$cli inspect `"$clip`""                                   5000
    Type-Line "$cli preview `"$clip`" --tier both --backend captions"    5500
    Type-Line "$cli read `"$clip`" --tier both --backend captions --workdir samples/demo-reel-output" 9000
}
finally {
    Start-Sleep -Seconds 2
    $ff.StandardInput.WriteLine('q')                    # graceful: finalises the moov atom
    $ff.WaitForExit(20000) | Out-Null
}

if (Test-Path $mp4) {
    $f = Get-Item $mp4
    "recorded: $($f.FullName)"
    "size:     $([math]::Round($f.Length/1MB,2)) MB   region: ${w}x${ht}"
} else { "recording failed - no file produced" }
