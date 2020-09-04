#!/bin/bash
pip install -r requirements.txt --target ./deploy
rm -rf deploy/asyncio
cp -r src/* deploy
rm -rf deploy/test
rm -rf deploy/*.dist-info
cd deploy ; zip -r ../lambda_deploy.zip * ; cd ../
