@echo off
setlocal enabledelayedexpansion

set DIAGRAMS_DIR=d:\Media-Search\Report\diagrams
set TEXFILES=fig41_architecture fig42_erd fig43_dfd0 fig44_dfd1 fig45_usecase fig46_seq_search fig47_seq_upload

echo ============================================================
echo  Compiling all 7 diagram .tex files to PDF
echo ============================================================

for %%F in (%TEXFILES%) do (
    echo.
    echo [%%F] Compiling...
    pdflatex -interaction=nonstopmode -output-directory="%DIAGRAMS_DIR%" "%DIAGRAMS_DIR%\%%F.tex"
    if !errorlevel! equ 0 (
        echo [%%F] SUCCESS
    ) else (
        echo [%%F] FAILED - check log
    )
)

echo.
echo ============================================================
echo  Done! PDF files are in %DIAGRAMS_DIR%
echo ============================================================

REM Optional: convert PDFs to PNG at 200 DPI using Ghostscript (if available)
where gswin64c >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo  Ghostscript found - converting PDFs to PNG at 200 DPI...
    for %%F in (%TEXFILES%) do (
        gswin64c -dNOPAUSE -dBATCH -sDEVICE=pngalpha -r200 -sOutputFile="%DIAGRAMS_DIR%\%%F.png" "%DIAGRAMS_DIR%\%%F.pdf"
        echo [%%F] PNG done
    )
) else (
    echo.
    echo  Ghostscript not found. PDFs only. 
    echo  Install Ghostscript to auto-convert to PNG.
)

pause
