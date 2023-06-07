import winapi
import memory
import time

# GENSHIN_EXE = "GenshinImpact.exe"
GENSHIN_PATH = r"C:\Program Files\Genshin Impact\Genshin Impact game\GenshinImpact.exe"
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

if not winapi.has_uac():
    print("UAC is not enabled.")
    exit(1)

print("Opening Genshin Impact...")
genshin_process = winapi.create_process(GENSHIN_PATH)

print(f"Process ID: {genshin_process.id}")

time.sleep(2)

results = []

while not len(results) == 2:
    results = list(
        winapi.get_modules(
            genshin_process.handle,
            lambda x: x in ("UnityPlayer.dll", "UserAssembly.dll"),
        )
    )

    time.sleep(0.2)

unity_player, user_assembly = results

if unity_player.name == "UserAssembly.dll":
    unity_player, user_assembly = user_assembly, unity_player

print(f"UnityPlayer.dll: {unity_player!r}")
print(f"UserAssembly.dll: {user_assembly!r}")

print("Reading UserAssembly.dll...")
user_assembly_buffer = winapi.read_memory(
    genshin_process.handle,
    user_assembly.base,
    user_assembly.size,
)

print("Finding FPS signature...")
start_time = time.perf_counter()
fps_offset = memory.signature_scan(user_assembly_buffer, FPS_SIGNATURE)
print(f"Time taken: {time.perf_counter() - start_time:.2f}s")

if fps_offset is None:
    print("Failed to find FPS signature.")
    exit(1)

print(f"Found FPS signature at offset {fps_offset} ({(fps_offset/user_assembly.size) * 100 :.2f}% read).")

genshin_process.handle.close()
