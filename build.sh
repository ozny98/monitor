pyinstaller --onefile main.py --add-data /usr/local/lib/python3.9/site-packages/apprise/plugins:apprise/plugins 

pyinstaller --onefile --clean --name monitor main.py --add-data "/usr/local/lib/python3.9/site-packages/apprise/plugins:apprise/plugins" --additional-hooks-dir=./hooks