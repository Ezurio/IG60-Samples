rmdir /s /q deploy
pip install -r requirements.txt --target deploy
copy src\* deploy
del /s /f /q deploy\*.dist-info
pushd deploy
zip -r ..\lambda_deploy.zip *
popd