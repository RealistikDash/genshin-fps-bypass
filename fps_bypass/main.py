import os


ERR_SUCCESS = 0
ERR_FAILURE = 1

if os.name != "nt":
    print("This script is only compatible with Windows.")
    exit(ERR_FAILURE)

import winapi
import genshin
import time
import config

if not winapi.has_uac():
    print("UAC is not enabled.")
    exit(ERR_FAILURE)

# Check if genshin is running.
genshin_info = genshin.get_running_game()

if genshin_info:
    genshin_info.handle.close()
    print("Genshin Impact is already running. Please close it and try again.")
    exit(1)

print("Starting Genshin Impact...")

genshin_info = genshin.start_game(GENSHIN_PATH)

print(f"Started Genshin Impact with PID {genshin_info.id}.")

print("Waiting for modules...")
modules = genshin.wait_for_modules(genshin_info)

print("Found modules:")
print(f"UnityPlayer.dll: {modules.unity_player}")
print(f"UserAssembly.dll: {modules.user_assembly}")

print("Searching for pointers...")
pointers = genshin.get_memory_pointers(genshin_info, modules)

if not pointers:
    print("Failed to find offsets. Perhaps the game has updated?")
    exit(ERR_FAILURE)

print("Found offsets:")
print(f"FPS: {pointers.fps}")
print(f"VSync: {pointers.vsync}")
print(f"Estimated: {pointers.estimated}")

state = genshin.FPSState(
    genshin=genshin_info,
    modules=modules,
    pointers=pointers,
)

while state.get_fps() == -1:
    time.sleep(0.2)

print(f"Current FPS: {state.get_fps()}")
print(f"Current VSync: {state.get_vsync()}")


print("Enforcing FPS...")
try:
    while True:
        if state.get_fps() != 144:
            print("Setting FPS to 144")
            state.set_vsync(False)
            state.set_fps(144)
        time.sleep(1)
except KeyboardInterrupt:
    print("Shutting down...")
    # Cleanup handles
    state.genshin.handle.close()
except OSError:
    print("Genshin Impact has closed.")  # likely
    # Cleanup handles
    state.genshin.handle.close()

print("Bye!")
exit(0)
