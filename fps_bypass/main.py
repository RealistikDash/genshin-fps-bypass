from __future__ import annotations

import os

VERSION = (0, 1, 0)

ERR_SUCCESS = 0
ERR_FAILURE = 1

if os.name != "nt":
    print("This script is only compatible with Windows.")
    exit(ERR_FAILURE)

import threading

import winapi
import genshin
import time
import utils
import config

if not winapi.has_uac():
    print("Administrator privileges are required to run this script.")
    exit(ERR_FAILURE)


print(f"FPS Bypass v{utils.make_version_string(VERSION)}")

# Load config as we need the path.
fps_config = config.read_config()

if not fps_config:
    print("Starting first time setup.")
    print("Please open Genshin Impact.")

    instance = utils.wait_for(genshin.get_running_game)

    # Create config.
    game_path = winapi.get_process_path(instance.handle)
    fps_value = utils.get_default_fps()

    fps_config = config.Configuration(
        genshin_path=game_path,
        target_fps=fps_value,
    )

    config.write_config(fps_config)


# Check if genshin is running (we need to start the game for the handle).
genshin_info = genshin.get_running_game()

if genshin_info:
    genshin_info.handle.close()
    print("Genshin Impact is already running. Please close it to continue.")

    utils.wait_for(lambda: not genshin.is_game_running())

print("Starting Genshin Impact...")

genshin_info = genshin.start_game(fps_config.genshin_path)

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

utils.wait_for(lambda: state.get_fps() != -1)

enforce_fps = True


def fps_enforcement_thread() -> None:
    assert fps_config is not None, "Started enforcement thread without config."

    while enforce_fps and genshin.is_game_running():
        if state.get_fps() != fps_config.target_fps:
            state.set_vsync(False)
            state.set_fps(fps_config.target_fps)

        time.sleep(0.1)

    print("FPS Bypass is no longer running.")


enforcement_thread = threading.Thread(
    target=fps_enforcement_thread,
    daemon=True,
)

enforcement_thread.start()

print("FPS Bypass is now running.")

try:
    while True:
        if not genshin.is_game_running():
            break

        print(f"Target FPS: {fps_config.target_fps}")
        new_fps = input(">>> ")

        try:
            new_fps = int(new_fps)
        except ValueError:
            print("Please enter a valid number as the target FPS.")
            continue

        if not (1 <= new_fps <= 1000):
            print("Invalid FPS value. Please enter a value between 1 and 1000.")
            continue

        fps_config.target_fps = new_fps
        config.write_config(fps_config)

except KeyboardInterrupt:
    print("Stopping FPS Bypass...")

enforce_fps = False
enforcement_thread.join()
state.genshin.handle.close()


exit(ERR_SUCCESS)
