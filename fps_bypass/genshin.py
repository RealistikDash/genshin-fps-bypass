# Game specific logic.
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import NamedTuple

import memory
import winapi

GENSHIN_OS_EXE = "GenshinImpact.exe"
GENSHIN_CN_EXE = "YuanShen.exe"

# Signatures taken from https://github.com/34736384/genshin-fps-unlock
FPS_SIGNATURE = memory.Signature(
    0xB9,
    0x3C,
    0x00,
    0x00,
    0x00,
    0xFF,
    0x15,
)

FPS_SIGNATURE.compile()


class GenshinModules(NamedTuple):
    unity_player: winapi.ModuleInfo
    user_assembly: winapi.ModuleInfo


def wait_for_modules(genshin: GenshinInfo) -> GenshinModules:
    results = []

    while len(results) != 2:
        try:
            results = list(
                winapi.get_modules(
                    genshin.handle,
                    lambda x: x in ("UnityPlayer.dll", "UserAssembly.dll"),
                ),
            )
        except OSError:
            pass

        time.sleep(0.2)

    if results[0].name == "UserAssembly.dll":
        return GenshinModules(
            unity_player=results[1],
            user_assembly=results[0],
        )

    return GenshinModules(
        unity_player=results[0],
        user_assembly=results[1],
    )


class GenshinInfo(NamedTuple):
    id: int
    path: str
    handle: winapi.Handle


def start_game(path: str) -> GenshinInfo | None:
    if not os.path.exists(path):
        return None

    game = winapi.create_process(path)
    return GenshinInfo(
        id=game.id,
        path=path,
        handle=game.handle,
    )


def is_game_running() -> bool:
    return bool(
        winapi.process_id_by_name(GENSHIN_OS_EXE)
        or winapi.process_id_by_name(GENSHIN_CN_EXE),
    )


def get_running_game() -> GenshinInfo | None:
    process_id = winapi.process_id_by_name(GENSHIN_OS_EXE) or winapi.process_id_by_name(
        GENSHIN_CN_EXE,
    )

    if not process_id:
        return None

    genshin = winapi.open_process(process_id)
    path = winapi.get_process_path(genshin)

    return GenshinInfo(
        id=process_id,
        path=path,
        handle=genshin,
    )


class MemoryPointers(NamedTuple):
    fps: int


NULLPTR = bytearray(8)


def get_memory_pointers(
    genshin: GenshinInfo,
    modules: GenshinModules,
) -> MemoryPointers | None:
    # TODO: Optimise memory by not loading the whole thing at once.
    user_assembly = modules.user_assembly
    user_assembly_buffer = winapi.read_memory(  # ~370MB
        genshin.handle,
        user_assembly.base,
        user_assembly.size,
    )
    unity_player = modules.unity_player

    # FPS.
    buffer_offset = 0

    buffer_offset = memory.signature_scan(user_assembly_buffer, FPS_SIGNATURE)

    if not buffer_offset:
        return None

    # This is once again stolen from https://github.com/34736384/genshin-fps-unlock
    # This is just a direct Python port of the C++ code.
    rip = buffer_offset + 5
    rip += (
        int.from_bytes(user_assembly_buffer[rip + 2 : rip + 6], "little", signed=True)
        + 6
    )

    del user_assembly_buffer

    genshin_ptr = user_assembly.base + rip

    while (ptr := winapi.read_memory(genshin.handle, genshin_ptr, 8)) == NULLPTR:
        time.sleep(0.2)

    rip = int.from_bytes(ptr, "little", signed=False) - modules.unity_player.base

    unity_player_buffer = winapi.read_memory(  # ~30MB
        genshin.handle,
        unity_player.base,
        unity_player.size,
    )

    while unity_player_buffer[rip] in (0xE8, 0xE9):
        rip += (
            int.from_bytes(
                unity_player_buffer[rip + 1 : rip + 5],
                "little",
                signed=True,
            )
            + 5
        )

    rip += (
        int.from_bytes(unity_player_buffer[rip + 2 : rip + 6], "little", signed=True)
        + 6
    )

    fps_ptr = rip + unity_player.base

    return MemoryPointers(
        fps=fps_ptr,
    )


@dataclass
class FPSState:
    genshin: GenshinInfo
    modules: GenshinModules
    pointers: MemoryPointers

    # Sometimes the game takes a while to start up.
    def wait_for_fps(self) -> None:
        while self.get_fps() == -1:
            time.sleep(0.2)

    def set_fps(self, fps: int) -> None:
        # FPS is an i32.
        fps_bytes = fps.to_bytes(4, "little", signed=True)
        winapi.write_memory(self.genshin.handle, self.pointers.fps, fps_bytes)

    def get_fps(self) -> int:
        # FPS is an i32.
        fps_bytes = winapi.read_memory(self.genshin.handle, self.pointers.fps, 4)
        return int.from_bytes(fps_bytes, "little", signed=True)
