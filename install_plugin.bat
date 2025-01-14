@echo off
setlocal enabledelayedexpansion

REM --- Définir les variables ---
set PYREVIT_REPO_URL=https://Wiem-Ben-Araar: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@github.com/Wiem-Ben-Araar/UW-Revit-Plugin.git
set PYREVIT_CLONE_DIR=c:\pyRevit\main
set REVIT_VERSION=2022
set REVIT_BUILD=2711
set EXTENSION_NAME=MyExtension
set PYREVIT_INSTALLER_URL=https://github.com/eirannejad/pyRevit/releases/latest/download/pyRevit_Installer.exe
set PYREVIT_INSTALLER_PATH=%temp%\pyRevit_Installer.exe

REM --- Vérifier si PyRevit est déjà installé ---
echo Vérification de l'installation de PyRevit...
where pyrevit >nul 2>nul
if %errorlevel% neq 0 (
    echo PyRevit n'est pas installé. Téléchargement et installation...
    echo Téléchargement de l'installateur PyRevit...
    powershell -Command "Invoke-WebRequest -Uri '%PYREVIT_INSTALLER_URL%' -OutFile '%PYREVIT_INSTALLER_PATH%'"
    if exist "%PYREVIT_INSTALLER_PATH%" (
        echo Installation de PyRevit...
        "%PYREVIT_INSTALLER_PATH%" /silent
        if %errorlevel% neq 0 (
            echo Échec de l'installation de PyRevit.
            pause
            exit /b 1
        ) else (
            echo PyRevit a été installé avec succès.
        )
    ) else (
        echo Impossible de télécharger l'installateur PyRevit.
        pause
        exit /b 1
    )
) else (
    echo PyRevit est installé.
)

REM --- Cloner le dépôt PyRevit principal ---
echo Clonage du dépôt PyRevit principal...
pyrevit clone main core --dest="%PYREVIT_CLONE_DIR%"
if %errorlevel% neq 0 (
    echo Échec du clonage du dépôt PyRevit.
    pause
    exit /b 1
)

REM --- Attacher PyRevit à Revit ---
echo Attachement de PyRevit à Revit version %REVIT_VERSION%...
pyrevit attach main %REVIT_BUILD% %REVIT_VERSION%
if %errorlevel% neq 0 (
    echo Échec de l'attachement de PyRevit à Revit.
    pause
    exit /b 1
)

REM --- Étendre l'interface PyRevit avec l'extension ---
echo Extension de l'interface PyRevit avec l'extension %EXTENSION_NAME%...
pyrevit extend ui %EXTENSION_NAME% "%PYREVIT_REPO_URL%" --branch main
if %errorlevel% neq 0 (
    echo Échec de l'ajout de l'extension à PyRevit.
    pause
    exit /b 1
)

REM --- Finalisation ---
echo Déploiement réussi ! Vous pouvez maintenant utiliser l'extension dans Revit.
pause
exit /b 0
