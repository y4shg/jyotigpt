:: This method is not recommended, and we recommend you use the `start.sh` file with WSL instead.
@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

:: Get the directory of the current script
SET "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%" || exit /b

:: Add conditional Playwright browser installation
IF /I "%WEB_LOADER_ENGINE%" == "playwright" (
    IF "%PLAYWRIGHT_WS_URL%" == "" (
        echo Installing Playwright browsers...
        playwright install chromium
        playwright install-deps chromium
    )

    python -c "import nltk; nltk.download('punkt_tab')"
)

SET "KEY_FILE=.JYOTIGPT_secret_key"
IF "%PORT%"=="" SET PORT=8080
IF "%HOST%"=="" SET HOST=0.0.0.0
SET "JYOTIGPT_SECRET_KEY=%JYOTIGPT_SECRET_KEY%"
SET "JYOTIGPT_JWT_SECRET_KEY=%JYOTIGPT_JWT_SECRET_KEY%"

:: Check if JYOTIGPT_SECRET_KEY and JYOTIGPT_JWT_SECRET_KEY are not set
IF "%JYOTIGPT_SECRET_KEY%%JYOTIGPT_JWT_SECRET_KEY%" == " " (
    echo Loading JYOTIGPT_SECRET_KEY from file, not provided as an environment variable.

    IF NOT EXIST "%KEY_FILE%" (
        echo Generating JYOTIGPT_SECRET_KEY
        :: Generate a random value to use as a JYOTIGPT_SECRET_KEY in case the user didn't provide one
        SET /p JYOTIGPT_SECRET_KEY=<nul
        FOR /L %%i IN (1,1,12) DO SET /p JYOTIGPT_SECRET_KEY=<!random!>>%KEY_FILE%
        echo JYOTIGPT_SECRET_KEY generated
    )

    echo Loading JYOTIGPT_SECRET_KEY from %KEY_FILE%
    SET /p JYOTIGPT_SECRET_KEY=<%KEY_FILE%
)

:: Execute uvicorn
SET "JYOTIGPT_SECRET_KEY=%JYOTIGPT_SECRET_KEY%"
IF "%UVICORN_WORKERS%"=="" SET UVICORN_WORKERS=1
uvicorn JYOTIGPT.main:app --host "%HOST%" --port "%PORT%" --forwarded-allow-ips '*' --workers %UVICORN_WORKERS% --ws auto
:: For ssl user uvicorn JYOTIGPT.main:app --host "%HOST%" --port "%PORT%" --forwarded-allow-ips '*' --ssl-keyfile "key.pem" --ssl-certfile "cert.pem" --ws auto
