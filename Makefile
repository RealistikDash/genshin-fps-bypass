build: fps_bypass/*.py
	pyinstaller --onefile fps_bypass/main.py --name fps_bypass --clean --noconfirm --uac-admin -i "NONE"
