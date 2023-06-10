from __future__ import annotations

import os

VERSION = (0, 1, 2)

ERR_SUCCESS = 0
ERR_FAILURE = 1

MIN_FPS = 1
MAX_FPS = 2147483647

if os.name != "nt":
    print("This script is only compatible with Windows.")
    exit(ERR_FAILURE)

import threading
import logging
import sys

import winapi
import genshin
import time
import utils
import config

if not winapi.has_uac():
    print("Administrator privileges are required to run this script.")
    utils.exit_pause()
    exit(ERR_FAILURE)


from rich.console import Console
from rich.progress import Progress
from rich.progress import TextColumn
from rich.progress import BarColumn
from rich.progress import TaskProgressColumn
from rich.logging import RichHandler
from rich.traceback import install
from rich.prompt import IntPrompt

console = Console()
install(console=console)

console.print(
    f"FPS Bypass v{utils.make_version_string(VERSION)}",
    style="bold underline blue",
    highlight=False,
)

is_debug_mode = "debug" in sys.argv

logging.basicConfig(
    level=logging.DEBUG if is_debug_mode else logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(
            rich_tracebacks=True,
            console=console,
        ),
    ],
)

logger = logging.getLogger("rich")


def _make_progress_bar() -> Progress:
    return Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        transient=True,
        console=console,
    )


# Load config as we need the path.
fps_config = config.read_config()

if not fps_config:
    with _make_progress_bar() as progress:
        task = progress.add_task("[blue]First Time Setup", start=False, total=2)
        console.log(":grey_question: Please open Genshin Impact to continue.")

        instance = utils.wait_for(genshin.get_running_game)

        console.log(
            f":white_check_mark: Found Genshin Impact with PID {instance.id}.",
        )
        progress.update(task, advance=1)

        # Create config.
        game_path = winapi.get_process_path(instance.handle)
        fps_value = utils.get_default_fps()

        logger.debug(f"Game path: {game_path!r}")
        logger.debug(f"Default FPS: {fps_value}")

        fps_config = config.Configuration(
            genshin_path=game_path,
            target_fps=fps_value,
        )

        config.write_config(fps_config)

        console.log(
            f":white_check_mark: Configuration complete!",
        )
        progress.update(task, advance=1)


# Check if genshin is running (we need to start the game for the handle).
genshin_info = genshin.get_running_game()

if genshin_info:
    with _make_progress_bar() as progress:
        genshin_info.handle.close()
        task = progress.add_task("[red]Close Game", start=False, total=None)

        console.log(
            ":grey_question: Genshin Impact is already running. Please close it to continue.",
        )

        utils.wait_for(lambda: not genshin.is_game_running())

with _make_progress_bar() as progress:
    task = progress.add_task("[blue]Starting Genshin Impact", start=False, total=4)
    genshin_info = genshin.start_game(fps_config.genshin_path)

    if not genshin_info:
        console.log(":no_entry: Could not find the Genshin Impact installation.")
        console.log(":grey_question: Please restart the bypass to redo the setup.")
        config.delete_config()
        utils.exit_pause()
        exit(ERR_FAILURE)

    console.log(
        f":white_check_mark: Started Genshin Impact with PID {genshin_info.id}.",
    )
    progress.update(task, advance=1)

    logger.debug("Waiting for modules...")
    modules = genshin.wait_for_modules(genshin_info)

    logger.debug("Found modules:")
    logger.debug(f"UnityPlayer.dll: {modules.unity_player!r}")
    logger.debug(f"UserAssembly.dll: {modules.user_assembly!r}")

    console.log(
        f":white_check_mark: Found {len(modules)} required modules.",
    )
    progress.update(task, advance=1)

    logger.debug("Searching for pointers...")
    pointers = genshin.get_memory_pointers(genshin_info, modules)

    if not pointers:
        console.log(":no_entry: Failed to find offsets. Perhaps the game has updated?")
        utils.exit_pause()
        exit(ERR_FAILURE)

    logger.debug(f"Found pointers: {pointers!r}")
    console.log(
        f":white_check_mark: Found the required memory pointers.",
    )
    progress.update(task, advance=1)

    state = genshin.FPSState(
        genshin=genshin_info,
        modules=modules,
        pointers=pointers,
    )

    logger.debug("Waiting for game to load...")

    utils.wait_for(lambda: state.get_fps() != -1)
    console.log(
        f":white_check_mark: Game started!",
    )
    progress.update(task, advance=1)

enforce_fps = True


def fps_enforcement_thread() -> None:
    assert fps_config is not None, "Started enforcement thread without config."

    while enforce_fps and genshin.is_game_running():
        if (old_fps := state.get_fps()) != fps_config.target_fps:
            state.set_vsync(False)
            state.set_fps(fps_config.target_fps)
            logger.debug(f"FPS change {old_fps} -> {fps_config.target_fps}.")

        time.sleep(0.1)

    logging.warning("FPS Bypass is no longer running.")


enforcement_thread = threading.Thread(
    target=fps_enforcement_thread,
    daemon=True,
)

enforcement_thread.start()

console.log(":white_check_mark: FPS Bypass started!")
console.log(":information_source: Press Ctrl+C to stop.")
console.log(f":information_source: Current target FPS: {fps_config.target_fps}.")
console.log(f":grey_question: Enter a new target FPS:")
prompt = IntPrompt(
    console=console,
)

try:
    while True:
        if not genshin.is_game_running():
            break

        new_fps = prompt.ask(
            prompt="[blue]FPS Bypass >>[/blue]",
            default=utils.get_default_fps(),
            show_default=False,
        )

        if not (MIN_FPS <= new_fps <= MAX_FPS):
            console.log(
                f":no_entry: Invalid FPS value. Must be between {MIN_FPS} and {MAX_FPS}.",
            )
            continue

        fps_config.target_fps = new_fps
        config.write_config(fps_config)

        console.log(
            f":white_check_mark: Target FPS set to {new_fps}.",
        )

except KeyboardInterrupt:
    console.log("Stopping FPS Bypass...")

enforce_fps = False
enforcement_thread.join()
state.genshin.handle.close()


exit(ERR_SUCCESS)
