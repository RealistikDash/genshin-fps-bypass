# Game specific logic.
from __future__ import annotations

import winapi
import memory

import time
from typing import NamedTuple
from dataclasses import dataclass

GENSHIN_EXE = "GenshinImpact.exe"

# Signatures taken from https://github.com/34736384/genshin-fps-unlock
FPS_SIGNATURE = memory.Signature(
    0xE8,
    None,
    None,
    None,
    None,
    0x85,
    0xC0,
    0x7E,
    0x07,
    0xE8,
    None,
    None,
    None,
    None,
    0xEB,
    0x05,
)
VSYNC_SIGNATURE = memory.Signature(
    0xE8, None, None, None, None, 0x8B, 0xE8, 0x49, 0x8B, 0x1E
)


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
                )
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


def start_game(path: str) -> GenshinInfo:
    game = winapi.create_process(path)
    return GenshinInfo(
        id=game.id,
        path=path,
        handle=game.handle,
    )


def is_game_running() -> bool:
    return bool(winapi.process_id_by_name(GENSHIN_EXE))


def get_running_game() -> GenshinInfo | None:
    process_id = winapi.process_id_by_name(GENSHIN_EXE)

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
    vsync: int
    estimated: bool


# Memory location estimation (based on 7/6/2023 3.7)
ESTIMATE_FPS_OFFSET = 93590149
ESTIMATE_VSYNC_OFFSET = 18528083


# This is once again stolen from https://github.com/34736384/genshin-fps-unlock
# This is just a direct Python port of the C++ code.
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

    # Try the estimated offset first.
    if memory.signature_match(
        user_assembly_buffer[ESTIMATE_FPS_OFFSET : len(FPS_SIGNATURE)], FPS_SIGNATURE
    ):
        buffer_offset = ESTIMATE_FPS_OFFSET
    else:
        # Worst case (~4s).
        buffer_offset = memory.signature_scan(user_assembly_buffer, FPS_SIGNATURE)

    if not buffer_offset:
        return None

    # WTF.
    rip = buffer_offset
    rip += (
        int.from_bytes(user_assembly_buffer[rip + 1 : rip + 5], "little", signed=True)
        + 5
    )
    rip += (
        int.from_bytes(user_assembly_buffer[rip + 3 : rip + 7], "little", signed=True)
        + 7
    )

    del user_assembly_buffer

    genshin_ptr = user_assembly.base + rip

    while not (ptr := winapi.read_memory(genshin.handle, genshin_ptr, 8)):
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
                unity_player_buffer[rip + 1 : rip + 5], "little", signed=True
            )
            + 5
        )

    rip += (
        int.from_bytes(unity_player_buffer[rip + 2 : rip + 6], "little", signed=True)
        + 6
    )

    fps_ptr = rip + unity_player.base

    # VSync.
    rip = memory.signature_scan(unity_player_buffer, VSYNC_SIGNATURE)

    if not rip:
        return None

    rel = int.from_bytes(unity_player_buffer[rip + 1 : rip + 5], "little", signed=True)
    rip += rel + 5
    rax = int.from_bytes(unity_player_buffer[rip + 3 : rip + 7], "little", signed=False)
    ppvsync = rax + rip + 7 + unity_player.base

    while not (ptr := winapi.read_memory(genshin.handle, ppvsync, 8)):
        time.sleep(0.2)

    rip += 7
    vsync_ptr = int.from_bytes(
        unity_player_buffer[rip + 2 : rip + 6], "little", signed=False
    ) + int.from_bytes(ptr, "little", signed=False)

    return MemoryPointers(
        fps=fps_ptr,
        vsync=vsync_ptr,
        estimated=False,
    )


def get_vsync_offset(
    genshin: GenshinInfo, unity_player: winapi.ModuleInfo
) -> int | None:
    # Try the estimated offset first.
    small_buffer = winapi.read_memory(
        genshin.handle,
        unity_player.base + ESTIMATE_VSYNC_OFFSET,
        len(VSYNC_SIGNATURE),
    )

    if memory.signature_match(small_buffer, VSYNC_SIGNATURE):
        return ESTIMATE_VSYNC_OFFSET

    unity_player_buffer = winapi.read_memory(
        genshin.handle,
        unity_player.base,
        unity_player.size,
    )

    return memory.signature_scan(unity_player_buffer, VSYNC_SIGNATURE)


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

    def set_vsync(self, enabled: bool) -> None:
        # VSync is a bool.
        vsync_bytes = b"\x01" if enabled else b"\x00"
        winapi.write_memory(self.genshin.handle, self.pointers.vsync, vsync_bytes)

    def get_vsync(self) -> bool:
        # VSync is a bool.
        vsync_bytes = winapi.read_memory(self.genshin.handle, self.pointers.vsync, 1)
        return vsync_bytes == b"\x01"
