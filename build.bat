pip install -r requirements.txt
src\tkicon.py cmd.ico
pyinstaller .\main.spec
rmdir /q /s .\build