rmdir /s /q deploy
del /s /f lambda_deploy.zip
pip install -r requirements.txt --target deploy
xcopy /s src\* deploy
for /d /r %%i in (deploy\*.dist-info) do @rmdir /s /q "%%i"
for /d /r %%i in (deploy\__pycache__) do @rmdir /s /q "%%i"
del /s /f /q deploy\*.pyc
rmdir /s /q deploy\asyncio
pushd deploy
zip -r ..\lambda_deploy.zip *
popd