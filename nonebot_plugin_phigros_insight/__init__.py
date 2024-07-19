import nonebot
from nonebot import CommandGroup, get_plugin_config, on_command, require
from nonebot.adapters import Event, Message
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot.rule import to_me
from nonebot.typing import T_State

import nonebot.adapters.onebot.v11
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, GroupMessageEvent

import ctypes
import json
from pathlib import Path

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store  # noqa: E402

# 读取用户 session
sessions_json_file = store.get_data_file(
    "nonebot_plugin_phigros_insight", "sessions.json"
)


class ConfigManager:
    file: Path
    config: dict[str]

    def __init__(self, file: Path):
        self.file = file
        self.config = json.loads(self.file.read_bytes())

    def get(self, key: str):
        return self.config[key]

    def set(self, key: str, value):
        self.config[key] = value
        self.file.write_text(json.dumps(self.config))


sessions = ConfigManager(sessions_json_file)

# 加载 PhigrosLibrary
phigros = ctypes.CDLL("./lib/libphigros.so")
print(phigros)
phigros.get_handle.argtypes = (ctypes.c_char_p,)
phigros.get_handle.restype = ctypes.c_void_p
phigros.free_handle.argtypes = (ctypes.c_void_p,)
phigros.get_nickname.argtypes = (ctypes.c_void_p,)
phigros.get_nickname.restype = ctypes.c_char_p
phigros.get_summary.argtypes = (ctypes.c_void_p,)
phigros.get_summary.restype = ctypes.c_char_p
phigros.get_save.argtypes = (ctypes.c_void_p,)
phigros.get_save.restype = ctypes.c_char_p
phigros.load_difficulty.argtypes = (ctypes.c_void_p,)
phigros.get_b19.argtypes = (ctypes.c_void_p,)
phigros.get_b19.restype = ctypes.c_char_p
phigros.re8.argtypes = (ctypes.c_void_p,)

phigros.load_difficulty(b"./misc/difficulty.tsv")

# 注册命令
command_phigros = CommandGroup("phigros", aliases=["pgr"], rule=to_me())
command_bind = command_phigros.command("bind")
command_unbind = command_phigros.command("unbind")
command_b19 = command_phigros.command("b19")


@command_bind.handle()
async def _(event: MessageEvent, args: Message = CommandArg()):
    global sessions
    sessionToken = args.extract_plain_text()[0].encode(encoding="ascii")
    user_id = event.get_user_id()
    sessions.set(user_id, sessionToken)
    handle = phigros.get_handle(sessionToken)
    await command_bind.send(f"已绑定账号 {phigros.get_nickname(handle)}")
    phigros.free_handle(handle)


@command_unbind.handle()
async def _(event: MessageEvent, args: Message = CommandArg()):
    global sessions
    user_id = event.get_user_id()
    sessions.set(user_id, b"")
    await command_bind.send("已解除绑定")


@command_b19.handle()
async def _(event: MessageEvent):
    global sessions
    user_id = event.get_user_id()
    sessionToken = sessions.get(user_id)
    handle = phigros.get_handle(sessionToken)
    b19_json: dict[str] = json.loads(phigros.get_b19())
    song_id = [entry["songId"] for entry in b19_json]
    song_level = [entry["level"] for entry in b19_json]
    play_score: list[int] = [int(entry["score"]) for entry in b19_json]
    play_acc = [entry["acc"] for entry in b19_json]
    song_rank = [entry["定数"] for entry in b19_json]
    s_rks = [entry["单曲rks"] for entry in b19_json]
    full_combo = [entry["fc"] for entry in b19_json]
    for i in range(20):
        msg: str = f"第 {i} 曲:\n"
        msg += f"{song_id}: {song_level}\n"
        msg += f"  分数: {play_score}\n"
        msg += f"  Acc: {play_acc}\n"
        msg += f"  定数: {song_rank}\n"
        msg += f"  单曲rks: {s_rks}\n"
        msg += f"  fc: {full_combo}\n\n"
        await command_b19.send(msg)
    phigros.free_handle(handle)
