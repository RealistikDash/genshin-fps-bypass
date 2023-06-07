import winapi
import time

GENSHIN_EXE = "GenshinImpact.exe"

if not winapi.has_uac():
    print("UAC is not enabled.")
    exit(1)

print("Waiting for Genshin Impact to start...")
while not (genshin_id := winapi.process_id_by_name(GENSHIN_EXE)):
    time.sleep(0.5)

print(f"Genshin Impact process ID: {genshin_id}")

with winapi.open_process(genshin_id) as genshin_handle:
    path = winapi.get_process_path(genshin_handle)
    print(f"Genshin Impact path: {path}")

    print("Terminating Genshin Impact...")
    winapi.terminate_process(genshin_handle)
