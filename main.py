from astrbot.api.star import Star, register, Context
from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.event import MessageChain
from astrbot.api.message_components import Plain, Image  # 确保已导入 Image
import json
import time
import httpx
import asyncio
import os
import random
import math
from .openbox import handle_openbox  # 新增导入
from .steam_list import handle_steam_list  # 新增导入
import re
from .achievement_monitor import AchievementMonitor
from .game_start_render import render_game_start  # 新增导入
from .game_end_render import render_game_end  # 新增导入
from PIL import Image as PILImage
import io
import tempfile
import traceback
import shutil
import builtins
from .superpower_util import load_abilities, get_daily_superpower  # 新增导入

_ACTIVE_INSTANCE_ATTR = "_astrbot_plugin_steam_status_monitor_f_active_instance"

@register(
    "steam_status_monitor_f",
    "Maoer / miz0re7ye",
    "Steam状态监控插件V2版 (Fork)",
    "2.3.0",
    "https://github.com/miz0re7ye/astrbot_plugin_steam_status_monitor"
)
class SteamStatusMonitorF(Star):
    def _get_group_data_path(self, group_id, key):
        """获取分群数据文件路径"""
        return os.path.join(self.data_dir, f"group_{group_id}_{key}.json")

    def _load_persistent_data(self):
        # 分群加载各群的状态数据
        for group_id in self.group_steam_ids:
            try:
                path = self._get_group_data_path(group_id, "states")
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        self.group_last_states[group_id] = json.load(f)
            except Exception as e:
                logger.warning(f"加载 group_last_states 失败: {e} (group_id={group_id})")
            try:
                path = self._get_group_data_path(group_id, "start_play_times")
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        self.group_start_play_times[group_id] = json.load(f)
            except Exception as e:
                logger.warning(f"加载 group_start_play_times 失败: {e} (group_id={group_id})")
            try:
                path = self._get_group_data_path(group_id, "last_quit_times")
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        self.group_last_quit_times[group_id] = json.load(f)
            except Exception as e:
                logger.warning(f"加载 group_last_quit_times 失败: {e} (group_id={group_id})")
            try:
                path = self._get_group_data_path(group_id, "pending_logs")
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        self.group_pending_logs[group_id] = json.load(f)
            except Exception as e:
                logger.warning(f"加载 group_pending_logs 失败: {e} (group_id={group_id})")
            try:
                path = self._get_group_data_path(group_id, "pending_quit")
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        self.group_pending_quit[group_id] = json.load(f)
            except Exception as e:
                logger.warning(f"加载 group_pending_quit 失败: {e} (group_id={group_id})")
            try:
                path = self._get_group_data_path(group_id, "recent_games")
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        self.group_recent_games[group_id] = json.load(f)
            except Exception as e:
                logger.warning(f"加载 group_recent_games 失败: {e} (group_id={group_id})")

    def _save_persistent_data(self):
        # 分群保存各群的状态数据
        for group_id in self.group_steam_ids:
            try:
                path = self._get_group_data_path(group_id, "states")
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.group_last_states.get(group_id, {}), f, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"保存 group_last_states 失败: {e} (group_id={group_id})")
            try:
                path = self._get_group_data_path(group_id, "start_play_times")
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.group_start_play_times.get(group_id, {}), f, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"保存 group_start_play_times 失败: {e} (group_id={group_id})")
            try:
                path = self._get_group_data_path(group_id, "last_quit_times")
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.group_last_quit_times.get(group_id, {}), f, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"保存 group_last_quit_times 失败: {e} (group_id={group_id})")
            try:
                path = self._get_group_data_path(group_id, "pending_logs")
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.group_pending_logs.get(group_id, {}), f, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"保存 group_pending_logs 失败: {e} (group_id={group_id})")
            try:
                path = self._get_group_data_path(group_id, "pending_quit")
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.group_pending_quit.get(group_id, {}), f, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"保存 group_pending_quit 失败: {e} (group_id={group_id})")
            try:
                path = self._get_group_data_path(group_id, "recent_games")
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.group_recent_games.get(group_id, []), f, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"保存 group_recent_games 失败: {e} (group_id={group_id})")

    def _load_notify_session(self):
        path = os.path.join(self.data_dir, "notify_sessions.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.notify_sessions = json.load(f)
                logger.info(f"[SteamStatusMonitorF] 已加载 notify_sessions: {self.notify_sessions}")
            except Exception as e:
                logger.warning(f"加载 notify_sessions 失败: {e}")
                self.notify_sessions = {}
        else:
            self.notify_sessions = {}

    def _save_notify_session(self):
        if hasattr(self, 'notify_sessions'):
            path = os.path.join(self.data_dir, "notify_sessions.json")
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.notify_sessions, f, ensure_ascii=False)
                logger.info(f"[SteamStatusMonitorF] 已保存 notify_sessions: {self.notify_sessions}")
            except Exception as e:
                logger.warning(f"保存 notify_sessions 失败: {e}")

    def _get_game_filters_path(self):
        """获取游戏播报过滤列表文件路径"""
        return os.path.join(self.data_dir, "game_filters.json")

    def _load_game_filters(self):
        """加载分群游戏播报过滤列表"""
        path = self._get_game_filters_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.group_game_filters = json.load(f)
                self.group_game_filters = {
                    str(group_id): self._parse_filter_keywords(filters)
                    for group_id, filters in self.group_game_filters.items()
                }
                logger.info(f"[SteamStatusMonitorF] 已加载 game_filters.json")
            except Exception as e:
                logger.warning(f"加载 game_filters.json 失败: {e}")
                self.group_game_filters = {}
        else:
            self.group_game_filters = {}

    def _save_game_filters(self):
        """保存分群游戏播报过滤列表"""
        path = self._get_game_filters_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.group_game_filters, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存 game_filters.json 失败: {e}")

    def _parse_filter_keywords(self, value):
        """解析游戏过滤关键词，去重并保留原始大小写。"""
        if not value:
            return []
        if isinstance(value, str):
            raw_items = re.split(r"[,，\n]+", value)
        else:
            raw_items = list(value)
        keywords = []
        seen = set()
        for item in raw_items:
            keyword = str(item).strip()
            key = keyword.lower()
            if keyword and key not in seen:
                keywords.append(keyword)
                seen.add(key)
        return keywords

    def _get_global_filter_keywords_path(self):
        """记录上一次从配置同步的全局过滤关键词。"""
        return os.path.join(self.data_dir, "global_filter_keywords.json")

    def _load_previous_global_filters(self):
        path = self._get_global_filter_keywords_path()
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                return self._parse_filter_keywords(json.load(f))
        except Exception as e:
            logger.warning(f"加载 global_filter_keywords.json 失败: {e}")
            return []

    def _save_global_filters_marker(self, keywords):
        path = self._get_global_filter_keywords_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(keywords, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存 global_filter_keywords.json 失败: {e}")

    def _sync_global_filters(self):
        """同步配置中的全局过滤词，并清理旧版本注入到分群列表里的全局词。"""
        current_global = self._parse_filter_keywords(self.config.get("game_filter_list", ""))
        previous_global = self._load_previous_global_filters()
        previous_keys = {kw.lower() for kw in previous_global}

        changed = False
        if previous_keys:
            current_keys = {kw.lower() for kw in current_global}
            for group_id, filters in list(self.group_game_filters.items()):
                group_filters = self._parse_filter_keywords(filters)
                cleaned = [
                    kw for kw in group_filters
                    if kw.lower() not in previous_keys or kw.lower() in current_keys
                ]
                if cleaned != group_filters:
                    self.group_game_filters[group_id] = cleaned
                    changed = True

        self._global_game_filters = current_global
        if changed:
            self._save_game_filters()
        self._save_global_filters_marker(current_global)
        logger.info(f"[SteamStatusMonitorF] 已同步全局游戏过滤关键词: {current_global}")

    def _is_game_filtered(self, group_id, game_name):
        """检查游戏名是否命中全局或本群播报过滤列表（模糊匹配，不区分大小写）"""
        if not game_name:
            return False
        group_id = str(group_id)
        filters = (
            self._parse_filter_keywords(getattr(self, "_global_game_filters", []))
            + self._parse_filter_keywords(self.group_game_filters.get(group_id, []))
        )
        game_name_lower = game_name.lower()
        for keyword in filters:
            if keyword and keyword.lower() in game_name_lower:
                return True
        return False

    def _get_achievement_toggle_path(self):
        """获取成就推送开关文件路径"""
        return os.path.join(self.data_dir, "achievement_toggle.json")

    def _load_achievement_toggle(self):
        """加载分群成就推送开关状态"""
        path = self._get_achievement_toggle_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.group_achievement_enabled = json.load(f)
                logger.info(f"[SteamStatusMonitorF] 已加载 achievement_toggle.json")
            except Exception as e:
                logger.warning(f"加载 achievement_toggle.json 失败: {e}")
                self.group_achievement_enabled = {}
        else:
            self.group_achievement_enabled = {}

    def _save_achievement_toggle(self):
        """保存分群成就推送开关状态"""
        path = self._get_achievement_toggle_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.group_achievement_enabled, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存 achievement_toggle.json 失败: {e}")

    def _ensure_fonts(self):
        """检测插件fonts目录是否有NotoSansHans系列字体，有则复制到缓存目录并缓存路径"""
        plugin_fonts_dir = os.path.join(os.path.dirname(__file__), 'fonts')
        cache_fonts_dir = os.path.join('data', 'steam_status_monitor_f', 'fonts')
        os.makedirs(plugin_fonts_dir, exist_ok=True)
        os.makedirs(cache_fonts_dir, exist_ok=True)
        font_candidates = [
            'NotoSansHans-Regular.otf',
            'NotoSansHans-Medium.otf'
        ]
        self.font_paths = {}
        for font_name in font_candidates:
            plugin_font_path = os.path.join(plugin_fonts_dir, font_name)
            cache_font_path = os.path.join(cache_fonts_dir, font_name)
            if os.path.exists(plugin_font_path):
                shutil.copy(plugin_font_path, cache_font_path)
                self.font_paths[font_name] = cache_font_path
            elif os.path.exists(cache_font_path):
                self.font_paths[font_name] = cache_font_path
            else:
                self.font_paths[font_name] = None
        # 详细日志
        for font_name in font_candidates:
            logger.info(f"[Font] {font_name} 路径: {self.font_paths.get(font_name)}")
        if not all(self.font_paths.values()):
            logger.warning("[Font] 未检测到全部NotoSansHans字体，渲染可能会出现乱码！")

    def get_font_path(self, font_name=None, bold=False):
        """优先返回缓存fonts目录下NotoSansHans字体路径"""
        if not font_name:
            font_name = 'NotoSansHans-Regular.otf'
        if bold:
            font_name = 'NotoSansHans-Medium.otf'
        return self.font_paths.get(font_name) or font_name

    def _get_groups_file_path(self):
        """获取 steam_groups.json 文件路径"""
        return os.path.join(self.data_dir, "steam_groups.json")

    def _normalize_group_steam_ids(self, group_steam_ids):
        normalized = {}
        if not isinstance(group_steam_ids, dict):
            return normalized
        for group_id, steam_ids in group_steam_ids.items():
            if isinstance(steam_ids, str):
                items = [x.strip() for x in re.split(r"[,，\s.]+", steam_ids) if x.strip()]
            else:
                try:
                    items = [str(x).strip() for x in steam_ids if str(x).strip()]
                except TypeError:
                    items = []
            normalized[str(group_id)] = items
        return normalized

    def _load_group_steam_ids(self):
        """从 steam_groups.json 加载所有群的 SteamID 列表"""
        path = self._get_groups_file_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.group_steam_ids = json.load(f)
                self.group_steam_ids = self._normalize_group_steam_ids(self.group_steam_ids)
                logger.info(f"[SteamStatusMonitorF] 已加载 steam_groups.json: {self.group_steam_ids}")
            except Exception as e:
                logger.warning(f"加载 steam_groups.json 失败: {e}")
        else:
            if isinstance(self.group_steam_ids, str):
                try:
                    self.group_steam_ids = json.loads(self.group_steam_ids)
                except Exception:
                    self.group_steam_ids = {}
            if not isinstance(self.group_steam_ids, dict):
                self.group_steam_ids = {}
            self.group_steam_ids = self._normalize_group_steam_ids(self.group_steam_ids)

    def _save_group_steam_ids(self):
        """保存所有群的 SteamID 列表到 steam_groups.json"""
        path = self._get_groups_file_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.group_steam_ids, f, ensure_ascii=False, indent=2)
            logger.info(f"[SteamStatusMonitorF] 已保存 steam_groups.json: {self.group_steam_ids}")
        except Exception as e:
            logger.warning(f"保存 steam_groups.json 失败: {e}")

    def _get_push_groups_path(self):
        """获取 push_groups.json 文件路径"""
        return os.path.join(self.data_dir, "push_groups.json")

    def _load_push_groups(self):
        """加载 SteamID -> 群号列表 的推送映射"""
        self.push_groups = {}
        path = self._get_push_groups_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.push_groups = json.load(f)
            except Exception as e:
                logger.warning(f"加载 push_groups.json 失败: {e}")

    def _save_push_groups(self):
        """保存 SteamID -> 群号列表 的推送映射"""
        path = self._get_push_groups_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.push_groups, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存 push_groups.json 失败: {e}")

    def _normalize_base_url(self, value, default):
        if not value:
            return default
        return str(value).rstrip("/")

    @staticmethod
    def _log_background_task_result(task):
        try:
            result = task.result()
            if isinstance(result, BaseException) and not isinstance(result, asyncio.CancelledError):
                logger.warning(f"[生命周期] 后台任务结束时出现异常: {result}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning(f"[生命周期] 后台任务结束时出现异常: {e}")

    @staticmethod
    def _is_empty_gameid(gameid):
        return gameid in (None, "", "0", 0)

    def _ensure_start_play_time_map(self, start_play_times, sid, gameid=None):
        """兼容旧版 start_play_times 的整数格式，统一为按游戏记录的字典。"""
        current = start_play_times.get(sid)
        if isinstance(current, dict):
            return current

        converted = {}
        if current and not self._is_empty_gameid(gameid):
            try:
                converted[gameid] = int(current)
            except (TypeError, ValueError):
                converted[gameid] = int(time.time())
        if current is not None:
            logger.info(f"[状态迁移] 已转换 SteamID {sid} 的 start_play_times 旧格式")
        start_play_times[sid] = converted
        return converted

    def _clear_start_play_time(self, group_id, sid, gameid):
        """确认游戏结束后清理开始时间，避免下次同一游戏复用旧时长。"""
        start_play_times = self.group_start_play_times.get(group_id, {})
        current = start_play_times.get(sid)
        if isinstance(current, dict):
            keys = [gameid]
            gameid_str = str(gameid)
            if gameid_str not in keys:
                keys.append(gameid_str)
            for key in keys:
                current.pop(key, None)
            if not current:
                start_play_times.pop(sid, None)
        elif sid in start_play_times:
            start_play_times.pop(sid, None)

    def _register_active_instance(self):
        """记录当前插件实例，并在重载时终止旧实例任务。"""
        old_instance = getattr(builtins, _ACTIVE_INSTANCE_ATTR, None)
        if old_instance is self:
            return
        if old_instance and getattr(old_instance, "_ssm_running", False):
            logger.warning("[生命周期] 检测到旧插件实例仍在运行，正在终止旧任务以避免重复播报。")
            try:
                shutdown_task = asyncio.create_task(old_instance.terminate())
                shutdown_task.add_done_callback(self._log_background_task_result)
            except RuntimeError as e:
                logger.warning(f"[生命周期] 无法调度旧插件实例终止任务: {e}")
        setattr(builtins, _ACTIVE_INSTANCE_ATTR, self)

    def __init__(self, context: Context, config=None):
        # 插件运行状态标志，重启后自动丢失
        if hasattr(self, '_ssm_running') and self._ssm_running:
            logger.error("当前插件已在运行中。请重启astrbot而非重载插件")
            return
        self._register_active_instance()
        self._ssm_running = True
        self._ensure_fonts()  # 插件启动时自动检测/下载字体
        self.context = context
        # 分群管理：所有状态数据均以 group_id 为 key
        self.group_steam_ids = {}         # {group_id: [steamid, ...]}
        self.group_last_states = {}       # {group_id: {steamid: status}}
        self.group_start_play_times = {}  # {group_id: {steamid: {gameid: start_time}}}
        self.group_last_quit_times = {}   # {group_id: {steamid: {gameid: quit_time}}}
        self.group_pending_logs = {}      # {group_id: {steamid: {gameid: log_dict}}}
        self.group_recent_games = {}      # {group_id: [gameid, ...]}
        self.group_pending_quit = {}      # {group_id: {steamid: {gameid: {quit_time, name, game_name, duration_min, start_time, notified}}}}
        # 超能力缓存和能力列表
        self._superpower_cache = {}  # {(steamid, date): superpower}
        self._abilities = None
        self._abilities_path = os.path.join(os.path.dirname(__file__), "abilities.txt")
        self._game_name_cache = {}  # 修复: 游戏名缓存，防止 AttributeError
        # 统一使用 AstrBot 配置系统
        self.config = config or {}
        # 旧配置迁移：如存在 steam_ids（未分群），迁移到 group_steam_ids['default']
        if 'steam_ids' in self.config and 'group_steam_ids' not in self.config:
            steam_ids = self.config.get('steam_ids', [])
            if isinstance(steam_ids, str):
                steam_ids = [x.strip() for x in steam_ids.split(',') if x.strip()]
            self.config['group_steam_ids'] = {'default': steam_ids}
            self.config.pop('steam_ids', None)
            logger.info(f"已自动迁移旧 steam_ids 配置到 group_steam_ids['default']")
        # 读取配置项，提供默认值
        self.API_KEY = self.config.get('steam_api_key', '')
        self.STEAM_API_BASE = self._normalize_base_url(
            self.config.get('steam_api_base', ''),
            'https://api.steampowered.com'
        )
        self.STEAM_STORE_BASE = self._normalize_base_url(
            self.config.get('steam_store_base', ''),
            'https://store.steampowered.com'
        )
        self.group_steam_ids = self.config.get('group_steam_ids', {})
        self.RETRY_TIMES = self.config.get('retry_times', 3)
        self.max_group_size = 20
        self.GROUP_ID = None  # 当前操作群号，指令时动态赋值
        self.fixed_poll_interval = self.config.get('fixed_poll_interval', 0)  # 新增：固定轮询间隔，0为智能轮询
        self.next_poll_time = {}  # {group_id: {steamid: next_time}}
        self.detailed_poll_log = self.config.get('detailed_poll_log', True)
        # 新增：智能轮询间隔配置 [游戏中, 12分钟内, 12分钟~3小时, 3小时~24小时, 24~48小时, 超过48小时]
        raw_intervals = self.config.get('smart_poll_intervals', "1,3,5,10,20,30")
        if isinstance(raw_intervals, str):
            self.smart_poll_intervals = [int(x.strip()) for x in raw_intervals.split(",") if x.strip()]
        else:
            self.smart_poll_intervals = list(raw_intervals)
        # 数据持久化目录
        self.data_dir = os.path.join("data", "steam_status_monitor_f")
        os.makedirs(self.data_dir, exist_ok=True)
        self._load_group_steam_ids()  # 新增：优先从 steam_groups.json 加载
        self._load_persistent_data()
        self._load_notify_session()
        self._load_game_filters()
        self._load_achievement_toggle()
        self._sync_global_filters()
        # 读取成就推送全局默认值，用于未设置的群
        self._achievement_default = self.config.get('achievement_enabled', False)
        # 成就监控
        self.achievement_monitor = AchievementMonitor(self.data_dir, steam_api_base=self.STEAM_API_BASE)
        self.max_achievement_notifications = self.config.get('max_achievement_notifications', 5)
        self.achievement_poll_tasks = {}  # {(group_id, sid, gameid): asyncio.Task}
        self.achievement_snapshots = {}   # {(group_id, sid, gameid): [成就列表]}
        self.achievement_blacklist = set()  # 新增：成就查询黑名单
        self.achievement_fail_count = {}    # 新增：成就查询失败计数
        self._pending_quit_tasks = {}       # {group_id: {sid: {gameid: asyncio.Task}}} 延迟退出检查任务
        self._fire_and_forget_tasks = set() # 一次性后台任务集合，terminate 时统一取消
        # --- 新增：重启后自动推送 ---
        self.running_groups = set()  # 正在运行的群号集合
        self.group_monitor_enabled = {}      # {group_id: bool} 监控开关
        self._steam_on_synced_groups = set()  # 本次运行中已由 /steam on 同步过当前状态的群
        # group_achievement_enabled 已由 _load_achievement_toggle() 加载，此处不再覆盖
        # --- 新增：重启后自动恢复所有群的轮询 ---
        if hasattr(self, 'notify_sessions') and self.notify_sessions and self.API_KEY and self.group_steam_ids:
            logger.info(f"[SteamStatusMonitorF] 检测到 notify_sessions={self.notify_sessions}，自动启动监控轮询")
            for group_id in self.notify_sessions:
                if group_id in self.group_steam_ids:
                    self.running_groups.add(group_id)
        # --- 新增：全局日志收集与统一输出 ---
        self._last_round_logs = []  # [(group_id, logstr)]
        # SGDB API Key 可在 https://www.steamgriddb.com/profile/preferences/api 获取
        self.SGDB_API_KEY = self.config.get('sgdb_api_key', '')
        self.SGDB_API_BASE = self._normalize_base_url(
            self.config.get('sgdb_api_base', ''),
            'https://www.steamgriddb.com'
        )
        self._load_push_groups()  # 确保 push_groups 在 create_task 前加载
        self._poll_loop_task = asyncio.create_task(self.global_poll_and_log_loop())
        self._init_poll_task = asyncio.create_task(self.init_poll_time_once())

    async def init_poll_time_once(self):
        '''插件启动后10秒内进行一次全员初始化轮询，设置每个SteamID的next_poll_time，并输出一次初始日志'''
        await asyncio.sleep(10)
        all_logs = []
        for group_id in self.group_steam_ids:
            if group_id not in self.running_groups:
                continue
            steam_ids = self.group_steam_ids[group_id]
            group_lines = []
            for sid in steam_ids:
                msg = await self.check_status_change(group_id, single_sid=sid)
                if msg:
                    group_lines.append(msg)
            if group_lines:
                all_logs.append(f"群{group_id}：\n" + "\n".join(group_lines))
        if all_logs:
            logger.info("====== Steam状态监控初始化日志 ======\n" + "\n".join(all_logs) + "\n=====================================================")

    async def global_poll_and_log_loop(self):
        '''全局定时并发查询所有群Steam状态，按动态间隔判断是否需要查询，40秒统一输出日志'''
        while True:
            try:
                # 计算距离下一个整分钟0秒的秒数
                now = time.time()
                next_minute = (int(now) // 60 + 1) * 60
                await asyncio.sleep(max(0, next_minute - now))
                # 0秒：遍历所有群和SteamID，按动态间隔判断是否需要查询
                group_ids = list(self.group_steam_ids.keys())
                poll_tasks = []
                for group_id in group_ids:
                    if group_id not in self.running_groups:
                        continue
                    if not self.group_monitor_enabled.get(group_id, True):
                        continue
                    steam_ids = self.group_steam_ids.get(group_id, [])
                    next_poll = self.next_poll_time.setdefault(group_id, {})
                    now2 = time.time()
                    # 只查询到点的SteamID
                    sids_to_query = [sid for sid in steam_ids if now2 >= next_poll.get(sid, 0)]
                    if not sids_to_query:
                        continue
                    async def query_one_group(gid, sids):
                        round_msg_lines = []
                        tasks = [self.check_status_change(gid, single_sid=sid) for sid in sids]
                        if tasks:
                            results = await asyncio.gather(*tasks, return_exceptions=True)
                            for msg in results:
                                if isinstance(msg, BaseException):
                                    logger.warning(f"[轮询] 群{gid} 查询异常: {msg}")
                                elif msg:
                                    round_msg_lines.append(msg)
                        if round_msg_lines:
                            self._last_round_logs.append((gid, "\n".join(round_msg_lines)))
                    poll_tasks.append(query_one_group(group_id, sids_to_query))
                if poll_tasks:
                    await asyncio.gather(*poll_tasks, return_exceptions=True)
                # 40秒统一输出日志
                await asyncio.sleep(40)
                if self._last_round_logs:
                    if self.detailed_poll_log:
                        all_logs = []
                        for group_id, logstr in self._last_round_logs:
                            all_logs.append(f"群{group_id}：\n" + logstr)
                        logger.info("====== Steam状态监控轮询日志 ======\n" + "\n".join(all_logs) + "\n=====================================================")
                    else:
                        logger.info("周期轮询成功")
                    self._last_round_logs.clear()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"[轮询] 全局轮询循环异常: {e}\n{traceback.format_exc()}")
                await asyncio.sleep(60)  # 异常后等待1分钟再重试，避免疯狂重试

    async def terminate(self):
        '''插件被卸载/停用时自动保存持久化数据'''
        self._ssm_running = False
        try:
            self._save_persistent_data()
            self._save_game_filters()
            self._save_achievement_toggle()
            self._save_notify_session()
            self._save_push_groups()
            # 停止全局轮询任务和初始化任务
            await self._cancel_tasks(
                [getattr(self, task_attr, None) for task_attr in ('_poll_loop_task', '_init_poll_task')],
                "主轮询任务"
            )
            # 取消所有运行时异步任务（成就轮询、延迟退出、一次性后台任务）
            await self._cancel_all_runtime_tasks()
        finally:
            if getattr(builtins, _ACTIVE_INSTANCE_ATTR, None) is self:
                setattr(builtins, _ACTIVE_INSTANCE_ATTR, None)

    async def crop_image_auto(self, img_path_or_bytes, bg_color=(20,26,33), threshold=25):
        """
        自动裁剪图片内容区域，去除边缘与 bg_color 相近的空白。
        支持本地路径、bytes、URL、PIL.Image。
        """
        # 新增：如果已经是PIL.Image对象，直接用
        if isinstance(img_path_or_bytes, PILImage.Image):
            img = img_path_or_bytes.convert("RGB")
        elif isinstance(img_path_or_bytes, str) and (img_path_or_bytes.startswith("http://") or img_path_or_bytes.startswith("https://")):
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(img_path_or_bytes)
            img = PILImage.open(io.BytesIO(resp.content)).convert("RGB")
        elif isinstance(img_path_or_bytes, bytes):
            img = PILImage.open(io.BytesIO(img_path_or_bytes)).convert("RGB")
        else:
            img = PILImage.open(img_path_or_bytes).convert("RGB")

        width, height = img.size
        pixels = img.load()
        corners = [
            pixels[0, 0],
            pixels[width - 1, 0],
            pixels[0, height - 1],
            pixels[width - 1, height - 1],
        ]
        avg_bg = tuple(sum(pixel[channel] for pixel in corners) / 4 for channel in range(3))

        left, top, right, bottom = width, height, -1, -1
        for y in range(height):
            for x in range(width):
                pixel = pixels[x, y]
                diff = sum(abs(pixel[channel] - avg_bg[channel]) for channel in range(3))
                if diff > threshold:
                    left = min(left, x)
                    top = min(top, y)
                    right = max(right, x)
                    bottom = max(bottom, y)

        if right < left or bottom < top:
            return img

        # 防止裁剪过度，留出2px边距
        left = max(left - 2, 0)
        top = max(top - 2, 0)
        right = min(right + 3, width)
        bottom = min(bottom + 3, height)
        cropped = img.crop((left, top, right, bottom))
        return cropped

    async def fetch_player_status(self, steam_id, retry=None):
        '''拉取单个玩家的 Steam 状态，失败自动重试多次并指数退避'''
        url = (
            f"{self.STEAM_API_BASE}/ISteamUser/GetPlayerSummaries/v2/"
            f"?key={self.API_KEY}&steamids={steam_id}"
        )
        delay = 1
        retry = retry if retry is not None else self.RETRY_TIMES
        for attempt in range(retry):
            async with httpx.AsyncClient(timeout=15) as client:
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        raise Exception(f"HTTP {resp.status_code}")
                    try:
                        data = resp.json()
                    except Exception as je:
                        raise Exception(f"JSON解析失败: {je}")
                    if not data.get('response') or not data['response'].get('players') or not data['response']['players']:
                        raise Exception("响应中无玩家数据")
                    player = data['response'].get('players')[0]
                    # 返回更多字段，包括头像
                    return {
                        'name': player.get('personaname'),
                        'gameid': player.get('gameid'),
                        'lastlogoff': player.get('lastlogoff'),
                        'gameextrainfo': player.get('gameextrainfo'),
                        'personastate': player.get('personastate', 0),
                        'avatarfull': player.get('avatarfull'),
                        'avatar': player.get('avatar')
                    }
                except Exception as e:
                    logger.warning(f"拉取 Steam 状态失败: {e} (SteamID: {steam_id}, 第{attempt+1}次重试)")
                    if attempt < retry - 1:
                        await asyncio.sleep(delay)
                        delay *= 2
        logger.error(f"SteamID {steam_id} 状态获取失败，已重试{retry}次")
        return None

    async def get_chinese_game_name(self, gameid, fallback_name=None):
        '''
        优先通过 Steam 商店API获取游戏中文名（l=schinese），若无则返回英文名（l=en），最后才返回 fallback_name 或“未知游戏”
        '''
        if not gameid:
            return fallback_name or "未知游戏"
        gid = str(gameid)
        if gid in self._game_name_cache:
            return self._game_name_cache[gid]
        # 优先查中文名（l=schinese），再查英文名（l=en）
        url_zh = f"{self.STEAM_STORE_BASE}/api/appdetails?appids={gid}&l=schinese"
        url_en = f"{self.STEAM_STORE_BASE}/api/appdetails?appids={gid}&l=en"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # 查中文名
                resp_zh = await client.get(url_zh)
                data_zh = resp_zh.json()
                info_zh = data_zh.get(gid, {}).get("data", {})
                name_zh = info_zh.get("name")
                if name_zh:
                    self._game_name_cache[gid] = name_zh
                    return name_zh
                # 查英文名
                resp_en = await client.get(url_en)
                data_en = resp_en.json()
                info_en = data_en.get(gid, {}).get("data", {})
                name_en = info_en.get("name")
                if name_en:
                    self._game_name_cache[gid] = name_en
                    return name_en
        except Exception as e:
            logger.warning(f"获取游戏名失败: {e} (gameid={gid})")
        # 不缓存 fallback，让下次还能重试
        return fallback_name or "未知游戏"

    async def get_game_names(self, gameid, fallback_name=None):
        '''
        返回 (中文名, 英文名)，如无则 fallback_name 或 "未知游戏"
        '''
        if not gameid:
            return (fallback_name or "未知游戏", fallback_name or "未知游戏")
        gid = str(gameid)
        if gid in self._game_name_cache:
            cached = self._game_name_cache[gid]
            if isinstance(cached, tuple):
                return cached
            else:
                return (cached, cached)
        url_zh = f"{self.STEAM_STORE_BASE}/api/appdetails?appids={gid}&l=schinese"
        url_en = f"{self.STEAM_STORE_BASE}/api/appdetails?appids={gid}&l=en"
        name_zh = name_en = fallback_name or "未知游戏"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp_zh = await client.get(url_zh)
                data_zh = resp_zh.json()
                info_zh = data_zh.get(gid, {}).get("data", {})
                name_zh = info_zh.get("name") or name_zh
                resp_en = await client.get(url_en)
                data_en = resp_en.json()
                info_en = data_en.get(gid, {}).get("data", {})
                name_en = info_en.get("name") or name_en
        except Exception as e:
            logger.warning(f"获取游戏名失败: {e} (gameid={gid})")
        self._game_name_cache[gid] = (name_zh, name_en)
        return (name_zh, name_en)

    async def get_game_cover_url(self, gameid, force_update=False):
        '''
        获取游戏封面图本地路径（优先小图，失败自动尝试日文/英文区域），自动缓存到本地，定期刷新
        force_update: True 时强制重新下载覆盖本地
        '''
        if not gameid:
            return None
        gid = str(gameid)
        cover_dir = os.path.join(self.data_dir, "covers")
        os.makedirs(cover_dir, exist_ok=True)
        cover_path = os.path.join(cover_dir, f"{gid}.jpg")
        # 定期刷新周期（秒），如30天
        refresh_interval = 30 * 24 * 3600
        need_refresh = force_update
        # 判断本地缓存是否需要刷新
        if os.path.exists(cover_path) and not force_update:
            last_mtime = os.path.getmtime(cover_path)
            if time.time() - last_mtime > refresh_interval:
                need_refresh = True
            else:
                return cover_path
        # 先查缓存
        if not need_refresh and hasattr(self, "_game_cover_cache") and gid in self._game_cover_cache:
            return self._game_cover_cache[gid]
        # 多区域尝试
        lang_list = ["schinese", "japanese", "en"]
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                for lang in lang_list:
                    url = f"{self.STEAM_STORE_BASE}/api/appdetails?appids={gid}&l={lang}"
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        logger.warning(f"获取游戏封面API失败: HTTP {resp.status_code} (gameid={gid}, lang={lang})")
                        continue
                    data = resp.json()
                    info = data.get(gid, {}).get("data", {})
                    header_img = info.get("header_image")
                    if not header_img:
                        logger.info(f"未找到游戏封面字段 header_image (gameid={gid}, lang={lang})，API返回data: {repr(info)[:200]}")
                        continue
                    small_img = header_img.replace("_header.jpg", "_capsule_184x69.jpg")
                    img_resp = await client.get(small_img)
                    if img_resp.status_code == 200:
                        with open(cover_path, "wb") as f:
                            f.write(img_resp.content)
                        return cover_path
                    else:
                        logger.warning(f"封面图片下载失败: HTTP {img_resp.status_code} url={small_img} (gameid={gid}, lang={lang})")
        except Exception as e:
            logger.warning(f"获取/缓存游戏封面异常: {e} (gameid={gid})")
        # 如果下载失败且本地有旧图，兜底返回旧图
        if os.path.exists(cover_path):
            return cover_path
        return None

    async def achievement_periodic_check(self, group_id, sid, gameid, player_name, game_name):
        '''每20分钟对比一次成就列表，直到游戏结束，失败多次自动加入黑名单'''
        key = (group_id, sid, gameid)
        try:
            while True:
                await asyncio.sleep(1200)  # 20分钟
                # 黑名单跳过
                if gameid in self.achievement_blacklist:
                    logger.info(f"[成就定时对比] 游戏 {gameid} 已在黑名单，跳过轮询")
                    break
                achievements_a = self.achievement_snapshots.get(key)
                achievements_b = await self.achievement_monitor.get_player_achievements(
                    self.API_KEY, group_id, sid, gameid
                )
                # 新增：当天失败次数统计
                today = time.strftime('%Y-%m-%d')
                fail_key = (gameid, today)
                if achievements_b is None:
                    cnt = self.achievement_fail_count.get(fail_key, 0) + 1
                    self.achievement_fail_count[fail_key] = cnt
                    if cnt >= 10:
                        self.achievement_blacklist.add(gameid)
                        logger.info(f"[成就黑名单] 游戏 {gameid} 当天累计获取失败10次，已加入黑名单")
                        break
                    continue
                # 修正：补充新成就检测逻辑
                if achievements_a is not None and achievements_b is not None:
                    new_achievements = set(achievements_b) - set(achievements_a)
                    if new_achievements:
                        logger.info(f"[成就定时对比] {player_name} 在 {game_name} 解锁新成就：{', '.join(new_achievements)}")
                        await self.notify_new_achievements(group_id, sid, player_name, gameid, game_name, new_achievements)
                        self.achievement_snapshots[key] = list(achievements_b)
                    else:
                        logger.info(f"[成就定时对比] {player_name} 在 {game_name} 未发现新成就")
        except asyncio.CancelledError:
            logger.info(f"[成就定时对比] 任务已取消 group_id={group_id} sid={sid} gameid={gameid}")
        except Exception as e:
            logger.error(f"[成就定时对比] group_id={group_id} sid={sid} gameid={gameid} 异常: {e}")

    async def achievement_delayed_final_check(self, group_id, sid, gameid, player_name, game_name):
        '''游戏结束后延迟5分钟再做一次成就对比，失败多次自动加入黑名单'''
        key = (group_id, sid, gameid)
        try:
            await asyncio.sleep(300)  # 5分钟
            # 黑名单跳过
            if gameid in self.achievement_blacklist:
                logger.info(f"[成就结束冗余对比] 游戏 {gameid} 已在黑名单，跳过轮询")
                return
            achievements_a = self.achievement_snapshots.get(key)
            achievements_b = await self.achievement_monitor.get_player_achievements(
                self.API_KEY, group_id, sid, gameid
            )
            today = time.strftime('%Y-%m-%d')
            fail_key = (gameid, today)
            if achievements_b is None:
                cnt = self.achievement_fail_count.get(fail_key, 0) + 1
                self.achievement_fail_count[fail_key] = cnt
                if cnt >= 10:
                    self.achievement_blacklist.add(gameid)
                    logger.info(f"[成就黑名单] 游戏 {gameid} 当天累计获取失败10次，已加入黑名单")
                    return
            if achievements_a is not None and achievements_b is not None:
                new_achievements = set(achievements_b) - set(achievements_a)
                if new_achievements:
                    logger.info(f"[成就结束冗余对比] {player_name} 在 {game_name} 解锁新成就：{', '.join(new_achievements)}")
                    await self.notify_new_achievements(group_id, sid, player_name, gameid, game_name, new_achievements)
                else:
                    logger.info(f"[成就结束冗余对比] {player_name} 在 {game_name} 未发现新成就")
        except asyncio.CancelledError:
            logger.info(f"[成就结束对比] 任务已取消 group_id={group_id} sid={sid} gameid={gameid}")
            raise
        except Exception as e:
            logger.error(f"[成就结束对比] group_id={group_id} sid={sid} gameid={gameid} 异常: {e}\n{traceback.format_exc()}")
        finally:
            self.achievement_snapshots.pop(key, None)
            self.achievement_poll_tasks.pop(key, None)
            self.achievement_monitor.clear_game_achievements(group_id, sid, gameid)

    async def notify_new_achievements(self, group_id, steamid, player_name, gameid, game_name, new_achievements):
        if not self.group_achievement_enabled.get(group_id, self._achievement_default):
            return
        # 游戏播报过滤检查
        if self._is_game_filtered(group_id, game_name):
            logger.info(f"[播报过滤] {player_name} 在「{game_name}」的成就推送在过滤列表中，跳过")
            return
        if not new_achievements or not self.notify_sessions:
            return
        achievements_to_notify = list(new_achievements)[:self.max_achievement_notifications]
        extra_count = len(new_achievements) - len(achievements_to_notify)
        # 优先用缓存
        details = self.achievement_monitor.details_cache.get((group_id, gameid))
        if not details:
            try:
                details = await self.achievement_monitor.get_achievement_details(group_id, gameid, lang="schinese", api_key=self.API_KEY, steamid=steamid)
            except Exception as e:
                details = None
                logger.warning(f"获取成就详情失败: {e}")
        # 在渲染前补充 game_name 字段，确保图片顶部能显示游戏名
        if details and game_name:
            for d in details.values():
                d["game_name"] = game_name
        font_path = self.get_font_path('NotoSansHans-Regular.otf')
        # 推送到主群和所有push_group
        notify_sessions = []
        notify_session = getattr(self, 'notify_sessions', {}).get(group_id, None)
        if notify_session:
            notify_sessions.append(notify_session)
        for push_gid in self.push_groups.get(steamid, []):
            push_session = getattr(self, 'notify_sessions', {}).get(push_gid, None)
            if push_session and push_session not in notify_sessions:
                notify_sessions.append(push_session)
        # 图片推送
        if details:
            unlocked_set = await self.achievement_monitor.get_player_achievements(self.API_KEY, group_id, steamid, gameid)
            if not unlocked_set:
                key = (group_id, steamid, gameid)
                unlocked_set = set(self.achievement_snapshots.get(key, []))
            if unlocked_set is None:
                unlocked_set = set()
            tmp_path = None
            try:
                img_bytes = await self.achievement_monitor.render_achievement_image(details, set(achievements_to_notify), player_name=player_name, steamid=steamid, appid=gameid, unlocked_set=unlocked_set, font_path=font_path)
                tmp_path = self._create_temp_image(img_bytes)
                for session in notify_sessions:
                    await self.context.send_message(session, MessageChain([Image.fromFileSystem(tmp_path)]))
                return
            except Exception as e:
                import traceback
                logger.error(f"成就图片渲染失败: {e}\n{traceback.format_exc()}")
            finally:
                self._cleanup_temp_file(tmp_path)
        # 文本推送
        message = f"🎉 {player_name} 在 {game_name} 中解锁了新成就!\n"
        for achievement in achievements_to_notify:
            message += f"• {achievement}\n"
        if extra_count > 0:
            message += f"...以及另外 {extra_count} 个成就"
        for session in notify_sessions:
            try:
                await self.context.send_message(session, MessageChain([Plain(message)]))
            except Exception as e:
                logger.error(f"发送成就通知失败: {e}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("steam on")
    async def steam_on(self, event: AstrMessageEvent):
        '''手动启动Steam状态监控轮询（分群）'''
        group_id = str(event.get_group_id()) if hasattr(event, 'get_group_id') else 'default'
        self.group_monitor_enabled[group_id] = True
        if not self.API_KEY:
            yield event.plain_result("未配置 Steam API Key，请先在插件配置中填写 steam_api_key。")
            return
        steam_ids = self.group_steam_ids.get(group_id, [])
        if not steam_ids or not any(isinstance(x, str) and x.strip() for x in steam_ids):
            yield event.plain_result(
                "未设置监控的 SteamID 列表，请先在插件配置中填写 steam_ids，"
                "或使用 /steam addid [SteamID] 添加要监控的玩家。"
            )
            return
        already_running = group_id in self.running_groups
        if not hasattr(self, 'notify_sessions'):
            self.notify_sessions = {}
        previous_notify_session = self.notify_sessions.get(group_id)
        current_notify_session = event.unified_msg_origin
        session_changed = previous_notify_session != current_notify_session
        self.running_groups.add(group_id)
        self.notify_sessions[group_id] = current_notify_session
        self._save_notify_session()
        # 初始化状态，并在首次开启或修复缺失会话时补发当前正在游戏的开始播报。
        now = int(time.time())
        if group_id not in self.group_last_states:
            self.group_last_states[group_id] = {}
        if group_id not in self.group_start_play_times:
            self.group_start_play_times[group_id] = {}
        initial_push_count = 0
        for sid in steam_ids:
            status = await self.fetch_player_status(sid)
            if not status:
                continue
            prev = self.group_last_states[group_id].get(sid)
            prev_gameid = prev.get('gameid') if prev else None
            current_gameid = status.get('gameid')
            should_push_initial = (
                not self._is_empty_gameid(current_gameid)
                and (
                    group_id not in self._steam_on_synced_groups
                    or self._is_empty_gameid(prev_gameid)
                    or prev_gameid != current_gameid
                    or not previous_notify_session
                    or session_changed
                )
            )
            if should_push_initial:
                if prev_gameid == current_gameid:
                    self.group_last_states[group_id].pop(sid, None)
                await self.check_status_change(group_id, single_sid=sid, status_override=status)
                initial_push_count += 1
                continue

            self.group_last_states[group_id][sid] = status
            if not self._is_empty_gameid(current_gameid):
                start_times = self._ensure_start_play_time_map(
                    self.group_start_play_times[group_id],
                    sid,
                    current_gameid
                )
                if prev_gameid != current_gameid or current_gameid not in start_times:
                    start_times[current_gameid] = now
        self._steam_on_synced_groups.add(group_id)
        self._save_persistent_data()
        result = "本群Steam监控已在运行，已刷新推送会话。" if already_running else "本群Steam状态监控启动完成。"
        if initial_push_count:
            result += f"\n已同步处理 {initial_push_count} 个当前游戏状态。"
        yield event.plain_result(result)

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("steam addid")
    async def steam_addid(self, event: AstrMessageEvent, steamid: str):
        '''添加SteamID到本群监控列表（分群），支持多个ID用逗号分隔'''
        group_id = str(event.get_group_id()) if hasattr(event, 'get_group_id') else 'default'
        # 支持多个ID同时输入
        steamid_list = [x.strip() for x in re.split(r"[,，\s.]+", steamid) if x.strip()]
        invalid_ids = [sid for sid in steamid_list if not sid.isdigit() or len(sid) != 17]
        if invalid_ids:
            yield event.plain_result(f"以下SteamID无效（需为64位数字串，17位）：{', '.join(invalid_ids)}")
            return
        steam_ids = self.group_steam_ids.setdefault(group_id, [])
        added = []
        already = []
        limit = self.max_group_size
        for sid in steamid_list:
            if sid in steam_ids:
                already.append(sid)
            elif len(steam_ids) < limit:
                steam_ids.append(sid)
                added.append(sid)
            else:
                break
        self.group_steam_ids[group_id] = steam_ids
        self._save_group_steam_ids()  # 新增：保存到 steam_groups.json
        msg = ""
        if added:
            msg += f"已为本群添加SteamID: {', '.join(added)}\n"
        if already:
            msg += f"以下SteamID已存在于本群监控组: {', '.join(already)}\n"
        if len(steam_ids) >= limit and len(added) < len(steamid_list):
            msg += f"本群监控组人数已达上限（{limit}人），部分ID未添加。\n"
        yield event.plain_result(msg.strip() if msg else "未添加任何SteamID。")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("steam delid")
    async def steam_delid(self, event: AstrMessageEvent, steamid: str):
        '''从本群监控组删除SteamID（分群）'''
        group_id = str(event.get_group_id()) if hasattr(event, 'get_group_id') else 'default'
        steam_ids = self.group_steam_ids.get(group_id, [])
        if steamid not in steam_ids:
            yield event.plain_result("该SteamID不存在于本群监控组")
            return
        steam_ids.remove(steamid)
        self.group_steam_ids[group_id] = steam_ids
        self._save_group_steam_ids()  # 新增：保存到 steam_groups.json
        yield event.plain_result(f"已为本群删除SteamID: {steamid}")

    @filter.command("steam list")
    async def steam_list(self, event: AstrMessageEvent):
        '''列出本群所有玩家当前状态（分群）'''
        group_id = str(event.get_group_id()) if hasattr(event, 'get_group_id') else 'default'
        steam_ids = self.group_steam_ids.get(group_id, [])
        if not self.API_KEY:
            yield event.plain_result("未配置 Steam API Key，请先在插件配置中填写 steam_api_key。")
            return
        if not steam_ids:
            yield event.plain_result("本群未设置监控的 SteamID 列表，请先添加。"); return
        event.group_steam_ids = steam_ids
        font_path = self.get_font_path('NotoSansHans-Regular.otf')
        logger.info(f"[Font] steam_list 渲染传入字体路径: {font_path}")
        # 修改：显式传递 group_id
        async for result in handle_steam_list(self, event, group_id=group_id, font_path=font_path):
            yield result

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("steam config")
    async def steam_config(self, event: AstrMessageEvent):
        '''显示当前插件配置（敏感信息已隐藏）'''
        lines = []
        hidden_keys = {"steam_api_key", "sgdb_api_key"}
        for k, v in self.config.items():
            if k in hidden_keys:
                lines.append(f"{k}: ****** (已隐藏)")
            else:
                lines.append(f"{k}: {v}")
        # 新增：显示智能轮询间隔说明
        if hasattr(self, "smart_poll_intervals"):
            intervals = self.smart_poll_intervals
            lines.append(f"智能轮询间隔（分钟）: {intervals}（依次为[游戏中, 12分钟内, 12分钟~3小时, 3小时~24小时, 24~48小时, 超过48小时]）")
        yield event.plain_result("当前配置：\n" + "\n".join(lines))

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("steam set")
    async def steam_set(self, event: AstrMessageEvent, key: str, value: str):
        '''设置配置参数，立即生效（如 steam set fixed_poll_interval 600）'''
        if key not in self.config:
            yield event.plain_result(f"无效参数: {key}")
            return
        old = self.config[key]
        if key == "smart_poll_intervals":
            # 支持字符串输入
            try:
                value_list = [int(x.strip()) for x in value.split(",") if x.strip()]
            except Exception:
                yield event.plain_result("类型错误，smart_poll_intervals 应为逗号分隔的整数")
                return
            if len(value_list) != 6 or any(x <= 0 for x in value_list):
                yield event.plain_result("smart_poll_intervals 需要 6 个正整数")
                return
            value = ",".join(str(x) for x in value_list)
            self.smart_poll_intervals = value_list
        elif isinstance(old, bool):
            normalized = value.strip().lower()
            if normalized in ("true", "1", "yes", "on", "开启", "开"):
                value = True
            elif normalized in ("false", "0", "no", "off", "关闭", "关"):
                value = False
            else:
                yield event.plain_result("类型错误，应为布尔值 true/false")
                return
        elif isinstance(old, int):
            try:
                value = int(value)
            except Exception:
                yield event.plain_result("类型错误，应为整数")
                return
        elif isinstance(old, float):
            try:
                value = float(value)
            except Exception:
                yield event.plain_result("类型错误，应为浮点数")
                return
        elif isinstance(old, list):
            # 兼容旧格式
            value = [int(x.strip()) for x in value.split(",") if x.strip()]
        self.config[key] = value
        # 同步到属性
        self.API_KEY = self.config.get('steam_api_key', '')
        self.STEAM_API_BASE = self._normalize_base_url(
            self.config.get('steam_api_base', ''),
            'https://api.steampowered.com'
        )
        self.STEAM_STORE_BASE = self._normalize_base_url(
            self.config.get('steam_store_base', ''),
            'https://store.steampowered.com'
        )
        self.SGDB_API_KEY = self.config.get('sgdb_api_key', '')
        self.SGDB_API_BASE = self._normalize_base_url(
            self.config.get('sgdb_api_base', ''),
            'https://www.steamgriddb.com'
        )
        self.STEAM_IDS = self.config.get('steam_ids', [])
        self.RETRY_TIMES = self.config.get('retry_times', 3)
        self.GROUP_ID = self.config.get('notify_group_id', None)
        self.fixed_poll_interval = self.config.get('fixed_poll_interval', 0)
        self.max_achievement_notifications = self.config.get('max_achievement_notifications', 5)
        self.detailed_poll_log = self.config.get('detailed_poll_log', True)
        # 重新解析智能轮询间隔
        raw_intervals = self.config.get('smart_poll_intervals', "1,3,5,10,20,30")
        if isinstance(raw_intervals, str):
            self.smart_poll_intervals = [int(x.strip()) for x in raw_intervals.split(",") if x.strip()]
        else:
            self.smart_poll_intervals = list(raw_intervals)
        # 同步成就推送全局默认值
        self._achievement_default = self.config.get('achievement_enabled', False)
        self._sync_global_filters()
        if hasattr(self.config, "save_config"):
            self.config.save_config()
        yield event.plain_result(f"已设置 {key} = {value}")

    async def _cancel_tasks(self, tasks, label):
        """取消任务并等待取消完成，避免插件重载后旧任务残留。"""
        active_tasks = [task for task in tasks if task and not task.done()]
        for task in active_tasks:
            task.cancel()
        if active_tasks:
            results = await asyncio.gather(*active_tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
                    logger.warning(f"[任务清理] {label} 取消时出现异常: {result}")

    async def _cancel_group_runtime_tasks(self, group_id):
        """取消指定群的成就轮询、延迟退出和一次性后台任务。"""
        group_id = str(group_id)
        tasks = []
        keys_to_cancel = [key for key in self.achievement_poll_tasks if key[0] == group_id]
        for key in keys_to_cancel:
            task = self.achievement_poll_tasks.pop(key, None)
            if task:
                tasks.append(task)
            self.achievement_snapshots.pop(key, None)

        group_tasks = getattr(self, "_pending_quit_tasks", {}).pop(group_id, {})
        for sid_tasks in group_tasks.values():
            tasks.extend(sid_tasks.values())

        fire_tasks = [
            task for task in getattr(self, "_fire_and_forget_tasks", set())
            if getattr(task, "_steam_monitor_key", (None, None, None))[0] == group_id
        ]
        for task in fire_tasks:
            self._fire_and_forget_tasks.discard(task)
        tasks.extend(fire_tasks)

        await self._cancel_tasks(tasks, f"群 {group_id} 运行时任务")

    async def _cancel_all_runtime_tasks(self):
        """取消所有运行时异步任务（steam rs / terminate 时调用）"""
        tasks = list(self.achievement_poll_tasks.values())
        self.achievement_poll_tasks.clear()

        if hasattr(self, '_pending_quit_tasks'):
            for group_tasks in self._pending_quit_tasks.values():
                for sid_tasks in group_tasks.values():
                    tasks.extend(sid_tasks.values())
            self._pending_quit_tasks.clear()

        fire_tasks = list(getattr(self, "_fire_and_forget_tasks", set()))
        tasks.extend(fire_tasks)
        self._fire_and_forget_tasks.clear()

        await self._cancel_tasks(tasks, "全部运行时任务")
        self.achievement_snapshots.clear()

    def _clear_group_persistent_files(self, group_ids):
        """删除指定群的持久化状态文件，避免清理后重启回灌旧状态。"""
        keys = ("states", "start_play_times", "last_quit_times", "pending_logs", "pending_quit", "recent_games")
        for group_id in group_ids:
            for key in keys:
                path = self._get_group_data_path(group_id, key)
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception as e:
                        logger.warning(f"删除持久化状态文件失败: {e} path={path}")

    def _create_temp_image(self, img_bytes, suffix=".png"):
        """创建临时图片文件，返回路径（调用方需在使用后调用 _cleanup_temp_file 清理）"""
        tmp_dir = os.path.join(self.data_dir, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=tmp_dir) as tmp:
            tmp.write(img_bytes)
            return tmp.name

    def _cleanup_temp_file(self, path):
        """安全删除临时文件"""
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("steam rs")
    async def steam_rs(self, event: AstrMessageEvent):
        '''清除所有状态并初始化（重启插件用）'''
        # 先取消所有运行中的异步任务，再清空数据，避免孤立任务继续访问已清空的状态
        await self._cancel_all_runtime_tasks()
        group_ids = list(self.group_steam_ids.keys())
        self._clear_group_persistent_files(group_ids)
        self.group_last_states.clear()
        self.group_start_play_times.clear()
        self.group_last_quit_times.clear()
        self.group_pending_logs.clear()
        self.group_pending_quit.clear()
        self.group_recent_games.clear()
        self._superpower_cache.clear()
        self._game_name_cache.clear()
        self.running_groups.clear()
        self.group_monitor_enabled.clear()
        self._steam_on_synced_groups.clear()
        self.group_achievement_enabled.clear()
        self.group_game_filters.clear()
        self.achievement_blacklist.clear()
        self.achievement_fail_count.clear()
        self.next_poll_time.clear()
        self.push_groups.clear()
        self.notify_sessions = {}
        self._save_persistent_data()  # 清空后保存
        self._save_achievement_toggle()  # 持久化成就开关清空状态
        self._save_game_filters()  # 持久化过滤列表清空状态
        self._save_notify_session()
        self._save_push_groups()
        yield event.plain_result("Steam状态监控插件已重置，所有状态已清空。")

    @filter.command("steam help")
    async def steam_help(self, event: AstrMessageEvent):
        '''显示所有指令帮助'''
        help_text = (
            "Steam状态监控插件指令：\n"
            "/steam on - 启动监控\n"
            "/steam off - 停止监控\n"
            "/steam list - 列出所有玩家状态\n"
            "/steam alllist - 列出所有群聊绑定及玩家状态\n"
            "/steam config - 查看当前配置\n"
            "/steam set [参数] [值] - 设置配置参数\n"
            "/steam addid [SteamID] - 添加SteamID\n"
            "/steam delid [SteamID] - 删除SteamID\n"
            "/steam push_group [SteamID] - 添加id到联动推送的副群\n"
            "/steam delpush_group [SteamID] - 删除id联动推送的副群\n"
            "/steam achievement_on - 开启本群成就推送\n"
            "/steam achievement_off - 关闭本群成就推送\n"
            "/steam filter_add [关键词] - 添加游戏播报过滤关键词\n"
            "/steam filter_del [关键词] - 移除游戏播报过滤关键词\n"
            "/steam filter_list - 查看本群播报过滤列表\n"
            "/steam openbox [SteamID] - 查看指定SteamID的全部信息\n"
            "/steam clear_allids - 删除所有群聊的全部SteamID\n"
            "/steam clear_groupids [群号] - 删除指定群聊的全部SteamID\n"
            "/steam 清除缓存 - 清除头像/封面图等图片缓存\n"
            "/steam rs - 清除状态并初始化\n"
            "/steam help - 显示本帮助"
        )
        yield event.plain_result(help_text)

    @filter.command("steam openbox")
    async def steam_openbox(self, event: AstrMessageEvent, steamid: str):
        '''查询并格式化展示指定SteamID的全部API返回信息（中文字段名，头像图片附加，位置ID合并，状态字段直观显示）'''
        if not self.API_KEY:
            yield event.plain_result("未配置 Steam API Key，请先在插件配置中填写 steam_api_key。")
            return
        async for result in handle_openbox(self, event, steamid):
            yield result

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("steam off")
    async def steam_off(self, event: AstrMessageEvent):
        '''停止Steam状态监控轮询'''
        group_id = str(event.get_group_id()) if hasattr(event, 'get_group_id') else 'default'
        self.group_monitor_enabled[group_id] = False
        self.running_groups.discard(group_id)
        self._steam_on_synced_groups.discard(group_id)
        await self._cancel_group_runtime_tasks(group_id)
        self.notify_sessions.pop(group_id, None)
        self._save_notify_session()
        yield event.plain_result(f"已为本群关闭Steam监控和推送。")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("steam achievement_on")
    async def steam_achievement_on(self, event: AstrMessageEvent):
        group_id = str(event.get_group_id()) if hasattr(event, 'get_group_id') else 'default'
        self.group_achievement_enabled[group_id] = True
        self._save_achievement_toggle()
        yield event.plain_result(f"已为本群开启Steam成就推送。")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("steam achievement_off")
    async def steam_achievement_off(self, event: AstrMessageEvent):
        group_id = str(event.get_group_id()) if hasattr(event, 'get_group_id') else 'default'
        self.group_achievement_enabled[group_id] = False
        self._save_achievement_toggle()
        yield event.plain_result(f"已为本群关闭Steam成就推送。")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("steam test_achievement_render")
    async def steam_test_achievement_render(self, event: AstrMessageEvent, steamid: str, gameid: int, count: int = 3):
        '''测试成就消息渲染效果（steam test_achievement_render [steamid] [gameid] [数量]）'''
        player_name = steamid
        game_name = await self.get_chinese_game_name(gameid)
        group_id = self.GROUP_ID or 'default'
        achievements = await self.achievement_monitor.get_player_achievements(self.API_KEY, group_id, steamid, gameid)
        if not achievements:
            yield event.plain_result("未获取到任何成就，可能为隐私或无成就。")
            return
        details = await self.achievement_monitor.get_achievement_details(group_id, gameid, lang="schinese", api_key=self.API_KEY, steamid=steamid)
        import random
        count = max(1, min(count, len(achievements)))
        unlocked = set(random.sample(list(achievements), count))
        font_path = self.get_font_path('NotoSansHans-Regular.otf')
        # 直接测试 Pillow 渲染
        try:
            img_bytes = await self.achievement_monitor.render_achievement_image(details, unlocked, player_name=player_name, font_path=font_path)
            tmp_path = self._create_temp_image(img_bytes)
            try:
                yield event.image_result(tmp_path)
            finally:
                self._cleanup_temp_file(tmp_path)
        except Exception as e:
            import traceback
            logger.error(f"成就图片渲染失败: {e}\n{traceback.format_exc()}")
            # 回退文本
            msg = self.achievement_monitor.render_achievement_message(details, unlocked, player_name=player_name)
            yield event.plain_result(msg)

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("steam test_game_start_render")
    async def test_game_start_render(self, event: AstrMessageEvent, steamid: str, gameid: int):
        '''测试开始游戏图片渲染效果（steam test_game_start_render [steamid] [gameid]）'''
        try:
            status = await self.fetch_player_status(steamid)
            player_name = status.get("name") if status else steamid
            avatar_url = status.get("avatarfull") or status.get("avatar") or "" if status else ""
            zh_game_name, en_game_name = await self.get_game_names(gameid)
            logger.info(f"[测试开始游戏渲染] steamid={steamid} gameid={gameid} player_name={player_name} avatar_url={avatar_url} zh_game_name={zh_game_name} en_game_name={en_game_name}")
            superpower = self.get_today_superpower(steamid)
            print(f"[superpower] test_game_start_render superpower={superpower}")
            font_path = self.get_font_path('NotoSansHans-Regular.otf')
            online_count = await self.get_game_online_count(gameid)
            img_bytes = await render_game_start(
                self.data_dir, steamid, player_name, avatar_url, gameid, zh_game_name, api_key=self.API_KEY, superpower=superpower, sgdb_api_key=self.SGDB_API_KEY, font_path=font_path, sgdb_game_name=en_game_name, online_count=online_count, appid=gameid, sgdb_api_base=self.SGDB_API_BASE, steam_api_base=self.STEAM_API_BASE
            )
            logger.info(f"[测试开始游戏渲染] render_game_start 返回类型: {type(img_bytes)} 长度: {len(img_bytes) if img_bytes else 'None'}")
            if img_bytes:
                tmp_path = self._create_temp_image(img_bytes)
                img = PILImage.open(tmp_path).convert("RGB")
                cropped_img = await self.crop_image_auto(img, bg_color=(51,81,66), threshold=15)
                self._cleanup_temp_file(tmp_path)
                import io as _io
                buf = _io.BytesIO()
                cropped_img.save(buf, format="PNG")
                tmp_path = self._create_temp_image(buf.getvalue())
                logger.info(f"[测试开始游戏渲染] 已保存裁剪图到 {tmp_path}")
                try:
                    yield event.image_result(tmp_path)
                finally:
                    self._cleanup_temp_file(tmp_path)
            else:
                yield event.plain_result("渲染失败，未获取到图片数据。")
        except Exception as e:
            logger.error(f"测试开始游戏图片渲染失败: {e}\n{traceback.format_exc()}")
            yield event.plain_result(f"渲染异常: {e}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("steam test_game_end_render")
    async def steam_test_game_end_render(self, event: AstrMessageEvent, steamid: str, gameid: int, duration_min: float = 120, end_time: str = None, tip_text: str = None):
        '''测试游戏结束图片渲染（steam test_game_end_render [steamid] [gameid] [时长分钟] [结束时间 可选] [提示 可选]）'''
        try:
            status = await self.fetch_player_status(steamid)
            player_name = status.get("name") if status else steamid
            avatar_url = status.get("avatarfull") or status.get("avatar") or "" if status else ""
            zh_game_name, en_game_name = await self.get_game_names(gameid)
            logger.info(f"[get_game_names] zh_game_name={zh_game_name}, en_game_name={en_game_name}")  # 新增英文名输出
            from datetime import datetime
            if end_time:
                end_time_str = end_time
            else:
                end_time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            duration_h = float(duration_min) / 60 if duration_min else 0
            if not tip_text:
                if duration_min < 5:
                    tip_text = "风扇都没转热，主人就结束了？"
                elif duration_min < 10:
                    tip_text = "杂鱼杂鱼~主人你就这水平？"
                elif duration_min < 30:
                    tip_text = "热身一下就结束了？"
                elif duration_min < 60:
                    tip_text = "歇会儿再来，别太累了喵！"
                elif duration_min < 120:
                    tip_text = "沉浸在游戏世界，时间过得飞快喵！"
                elif duration_min < 300:
                    tip_text = "肝到手软了喵！主人不如陪陪咱~"
                elif duration_min < 600:
                    tip_text = "你吃饭了吗？还是说你已经忘了吃饭这件事？"
                elif duration_min < 1200:
                    tip_text = "家里电费都要被你玩光了喵！"
                elif duration_min < 1800:
                    tip_text = "咱都要给你颁发‘不眠猫’勋章了！"
                elif duration_min < 2400:
                    tip_text = "主人你还活着喵？你是不是忘了关电脑呀~"
                else:
                    tip_text = "你已经和椅子合为一体，成为传说中的‘椅子精’了喵！"
            font_path = self.get_font_path('NotoSansHans-Regular.otf')
            img_bytes = await render_game_end(
                self.data_dir, steamid, player_name, avatar_url, gameid, zh_game_name,
                end_time_str, tip_text, duration_h, sgdb_api_key=self.SGDB_API_KEY, font_path=font_path, sgdb_game_name=en_game_name, appid=gameid, sgdb_api_base=self.SGDB_API_BASE
            )
            msg = f"👋 {player_name} 不玩 {zh_game_name} 了\n游玩时间 {duration_h:.1f}小时"
            tmp_path = self._create_temp_image(img_bytes)
            try:
                yield event.plain_result(msg)
                yield event.image_result(tmp_path)
            finally:
                self._cleanup_temp_file(tmp_path)
        except Exception as e:
            import traceback
            logger.error(f"测试游戏结束图片渲染失败: {e}\n{traceback.format_exc()}")
            yield event.plain_result(f"渲染异常: {e}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("steam清除缓存")
    async def steam_clear_cache(self, event: AstrMessageEvent):
        '''清除所有头像、封面图等图片缓存（慎用）'''
        try:
            cache_dirs = [
                os.path.join(self.data_dir, "avatars"),
                os.path.join(self.data_dir, "covers"),
                os.path.join(self.data_dir, "covers_v"),
            ]
            cleared = []
            for d in cache_dirs:
                if os.path.exists(d):
                    shutil.rmtree(d)
                    cleared.append(d)
            msg = "已清除以下缓存目录：\n" + "\n".join(cleared) if cleared else "未找到任何缓存目录，无需清理。"
            yield event.plain_result(msg)
        except Exception as e:
            yield event.plain_result(f"清除缓存失败: {e}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("steam clear_allids")
    async def steam_clear_allids(self, event: AstrMessageEvent):
        '''删除所有群聊的所有已监控SteamID，并清空相关状态数据'''
        await self._cancel_all_runtime_tasks()
        group_ids = list(self.group_steam_ids.keys())
        self._clear_group_persistent_files(group_ids)
        self.group_steam_ids.clear()
        self._save_group_steam_ids()  # 新增：保存到 steam_groups.json
        self.group_last_states.clear()
        self.group_start_play_times.clear()
        self.group_last_quit_times.clear()
        self.group_pending_logs.clear()
        self.group_pending_quit.clear()
        self.group_recent_games.clear()
        self.group_game_filters.clear()
        self.group_achievement_enabled.clear()
        self.running_groups.clear()
        self._steam_on_synced_groups.clear()
        self.group_monitor_enabled.clear()
        self.next_poll_time.clear()
        self.notify_sessions = {}
        self.push_groups.clear()
        self._save_game_filters()
        self._save_achievement_toggle()
        self._save_persistent_data()
        self._save_notify_session()
        self._save_push_groups()
        self.config['group_steam_ids'] = self.group_steam_ids
        if hasattr(self.config, "save_config"):
            self.config.save_config()
        yield event.plain_result("已删除所有群聊的所有SteamID，相关状态数据已清空。")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("steam clear_groupids")
    async def steam_clear_groupids(self, event: AstrMessageEvent, group_id: str):
        '''删除指定群聊的所有已监控SteamID，并清空相关状态数据'''
        if group_id not in self.group_steam_ids:
            yield event.plain_result(f"群聊 {group_id} 未绑定任何SteamID，无需清理。")
            return
        await self._cancel_group_runtime_tasks(group_id)
        self._clear_group_persistent_files([group_id])
        self.group_steam_ids.pop(group_id, None)
        self._save_group_steam_ids()  # 保存到 steam_groups.json
        self.group_last_states.pop(group_id, None)
        self.group_start_play_times.pop(group_id, None)
        self.group_last_quit_times.pop(group_id, None)
        self.group_pending_logs.pop(group_id, None)
        self.group_pending_quit.pop(group_id, None)
        self.group_recent_games.pop(group_id, None)
        self.group_game_filters.pop(group_id, None)
        self.group_achievement_enabled.pop(group_id, None)
        self.running_groups.discard(group_id)
        self._steam_on_synced_groups.discard(group_id)
        self.group_monitor_enabled.pop(group_id, None)
        self.next_poll_time.pop(group_id, None)
        for sid, push_group_ids in list(self.push_groups.items()):
            self.push_groups[sid] = [gid for gid in push_group_ids if gid != group_id]
            if not self.push_groups[sid]:
                self.push_groups.pop(sid, None)
        self._save_game_filters()
        self._save_achievement_toggle()
        self._save_persistent_data()
        self.notify_sessions.pop(group_id, None)
        self._save_notify_session()
        self._save_push_groups()
        self.config['group_steam_ids'] = self.group_steam_ids
        if hasattr(self.config, "save_config"):
            self.config.save_config()
        yield event.plain_result(f"已删除群聊 {group_id} 的所有SteamID，相关状态数据已清空。")

    async def _delayed_quit_check(self, group_id, sid, gameid):
        try:
            await asyncio.sleep(180)
            # 游戏播报过滤检查
            info = self.group_pending_quit.get(group_id, {}).get(sid, {}).get(gameid)
            if not info:
                return
            if self._is_game_filtered(group_id, info.get("game_name", "")):
                logger.info(f"[播报过滤] {info.get('name', sid)} 退出的游戏「{info.get('game_name', '')}」在过滤列表中，跳过推送")
                info["notified"] = True
                # 清理成就轮询
                key = (group_id, sid, gameid)
                poll_task = self.achievement_poll_tasks.pop(key, None)
                if poll_task:
                    poll_task.cancel()
                self.achievement_snapshots.pop(key, None)
                self.achievement_monitor.clear_game_achievements(group_id, sid, gameid)
                self._clear_start_play_time(group_id, sid, gameid)
                if sid in self.group_pending_quit.get(group_id, {}):
                    self.group_pending_quit[group_id][sid].pop(gameid, None)
                # 清理延迟任务引用
                if hasattr(self, '_pending_quit_tasks'):
                    self._pending_quit_tasks.get(group_id, {}).get(sid, {}).pop(gameid, None)
                return
            if not info.get("notified"):
                duration_min = info["duration_min"]
                if duration_min == 0:
                    for _ in range(2):
                        last_quit_time = info["quit_time"]
                        start_time = info["start_time"]
                        if start_time and last_quit_time:
                            duration_min = (last_quit_time - start_time) / 60
                            if duration_min > 0:
                                info["duration_min"] = duration_min
                                break
                        await asyncio.sleep(1)
                info["notified"] = True
                duration_min = info["duration_min"]
                if duration_min < 60:
                    time_str = f"{duration_min:.1f}分钟"
                else:
                    time_str = f"{duration_min/60:.1f}小时"
                msg = f"👋 {info['name']} 不玩 {info['game_name']}了\n游玩时间 {time_str}"
                # 推送到主群和所有联动群
                notify_sessions = []
                notify_session = getattr(self, 'notify_sessions', {}).get(group_id, None)
                if notify_session:
                    notify_sessions.append(notify_session)
                for push_gid in self.push_groups.get(sid, []):
                    push_session = getattr(self, 'notify_sessions', {}).get(push_gid, None)
                    if push_session and push_session not in notify_sessions:
                        notify_sessions.append(push_session)
                for session in notify_sessions:
                    tmp_path = None
                    try:
                        from datetime import datetime
                        end_time_str = datetime.fromtimestamp(info["quit_time"]).strftime("%Y-%m-%d %H:%M")
                        duration_h = info["duration_min"] / 60 if info["duration_min"] > 0 else 0
                        avatar_url = None
                        last_state = self.group_last_states.get(group_id, {}).get(sid)
                        if last_state:
                            avatar_url = last_state.get("avatarfull") or last_state.get("avatar")
                        if not avatar_url:
                            status_full = await self.fetch_player_status(sid)
                            if status_full:
                                avatar_url = status_full.get("avatarfull") or status_full.get("avatar")
                        tip_text = info.get("tip_text") or "你已经和椅子合为一体，成为传说中的'椅子精'了喵！"
                        zh_game_name, en_game_name = await self.get_game_names(gameid, info["game_name"])
                        font_path = self.get_font_path('NotoSansHans-Regular.otf')
                        img_bytes = await render_game_end(
                            self.data_dir, sid, info["name"], avatar_url, gameid, zh_game_name,
                            end_time_str, tip_text, duration_h, sgdb_api_key=self.SGDB_API_KEY, font_path=font_path, sgdb_game_name=en_game_name, appid=gameid, sgdb_api_base=self.SGDB_API_BASE
                        )
                        tmp_path = self._create_temp_image(img_bytes)
                        await self.context.send_message(session, MessageChain([Plain(msg), Image.fromFileSystem(tmp_path)]))
                    except Exception as e:
                        logger.error(f"推送游戏结束图片失败: {e}")
                        await self.context.send_message(session, MessageChain([Plain(msg)]))
                    finally:
                        self._cleanup_temp_file(tmp_path)
                # 三分钟后再关闭成就轮询和清理快照
                key = (group_id, sid, gameid)
                poll_task = self.achievement_poll_tasks.pop(key, None)
                if poll_task:
                    poll_task.cancel()
                self.achievement_snapshots.pop(key, None)
                self.achievement_monitor.clear_game_achievements(group_id, sid, gameid)
                self._clear_start_play_time(group_id, sid, gameid)
                self.group_pending_quit.get(group_id, {}).get(sid, {}).pop(gameid, None)
        except asyncio.CancelledError:
            logger.info(f"[延迟退出] 任务已取消 group_id={group_id} sid={sid} gameid={gameid}")
            raise
        except Exception as e:
            logger.error(f"[延迟退出] group_id={group_id} sid={sid} gameid={gameid} 异常: {e}\n{traceback.format_exc()}")
        finally:
            if hasattr(self, '_pending_quit_tasks'):
                self._pending_quit_tasks.get(group_id, {}).get(sid, {}).pop(gameid, None)

    async def check_status_change(self, group_id, single_sid=None, status_override=None, poll_level=None):
        '''轮询检测玩家状态变更并推送通知（分群，支持单个sid）
        返回精简日志字符串，不直接打印日志'''
        now = int(time.time())
        steam_ids = [single_sid] if single_sid else self.group_steam_ids.get(group_id, [])
        last_states = self.group_last_states.setdefault(group_id, {})
        start_play_times = self.group_start_play_times.setdefault(group_id, {})
        last_quit_times = self.group_last_quit_times.setdefault(group_id, {})
        pending_logs = self.group_pending_logs.setdefault(group_id, {})
        pending_quit = self.group_pending_quit.setdefault(group_id, {})
        recent_games = self.group_recent_games.setdefault(group_id, [])
        notify_session = getattr(self, 'notify_sessions', {}).get(group_id, None)
        msg_lines = []
        for sid in steam_ids:
            status = status_override if status_override and sid == single_sid else await self.fetch_player_status(sid)
            if not status:
                continue
            prev = last_states.get(sid)
            name = status.get('name') or sid
            gameid = status.get('gameid')
            game = status.get('gameextrainfo')
            lastlogoff = status.get('lastlogoff')
            personastate = status.get('personastate', 0)
            zh_game_name = await self.get_chinese_game_name(gameid, game) if gameid else (game or "未知游戏")
            prev_gameid = prev.get('gameid') if prev else None
            current_gameid = gameid
            # --- 退出游戏（缓冲3分钟） ---
            if not self._is_empty_gameid(prev_gameid) and self._is_empty_gameid(current_gameid):
                logger.info(f"[退出逻辑] {name} prev_gameid={prev_gameid} current_gameid={current_gameid}")
                zh_prev_game_name = await self.get_chinese_game_name(prev_gameid, prev.get('gameextrainfo') if prev else None) if prev_gameid else (prev.get('gameextrainfo') if prev else "未知游戏")
                duration_min = 0
                sid_start_times = self._ensure_start_play_time_map(start_play_times, sid, prev_gameid)
                start_time = sid_start_times.get(prev_gameid, now)
                if prev_gameid in sid_start_times:
                    duration_min = (now - sid_start_times[prev_gameid]) / 60
                    if duration_min == 0:
                        for _ in range(2):
                            start_time = sid_start_times.get(prev_gameid, now)
                            duration_min = (now - start_time) / 60
                            if duration_min > 0:
                                break
                            await asyncio.sleep(1)
                self.achievement_monitor.clear_game_achievements(group_id, sid, prev_gameid)
                pending_quit.setdefault(sid, {})[prev_gameid] = {
                    "quit_time": now,
                    "name": name,
                    "game_name": zh_prev_game_name,
                    "duration_min": duration_min,
                    "start_time": start_time,
                    "notified": False
                }
                # 成就结算：游戏结束时，延迟15分钟再做一次对比（仅在成就监控曾启动时执行）
                try:
                    player_name = name
                    game_name = zh_prev_game_name
                    key = (group_id, sid, prev_gameid)
                    poll_task = self.achievement_poll_tasks.pop(key, None)
                    if poll_task:
                        poll_task.cancel()
                    if key in self.achievement_snapshots:
                        _final_task = asyncio.create_task(self.achievement_delayed_final_check(group_id, sid, prev_gameid, player_name, game_name))
                        _final_task._steam_monitor_key = key
                        self._fire_and_forget_tasks.add(_final_task)
                        _final_task.add_done_callback(self._fire_and_forget_tasks.discard)
                except Exception as e:
                    logger.error(f"结算成就时异常: {e}")
                # 启动延迟任务
                if not hasattr(self, '_pending_quit_tasks'):
                    self._pending_quit_tasks = {}
                if group_id not in self._pending_quit_tasks:
                    self._pending_quit_tasks[group_id] = {}
                if sid not in self._pending_quit_tasks[group_id]:
                    self._pending_quit_tasks[group_id][sid] = {}
                old_task = self._pending_quit_tasks[group_id][sid].get(prev_gameid)
                if old_task:
                    old_task.cancel()
                task = asyncio.create_task(self._delayed_quit_check(group_id, sid, prev_gameid))
                self._pending_quit_tasks[group_id][sid][prev_gameid] = task
                last_quit_times.setdefault(sid, {})[prev_gameid] = now
                last_states[sid] = status
                continue  # 防止重复推送

            # --- 开始游戏/继续游戏（仅当 gameid 变更时推送） ---
            if not self._is_empty_gameid(current_gameid) and current_gameid != prev_gameid:
                quit_info = pending_quit.setdefault(sid, {}).get(current_gameid)
                # 检查是否为网络波动（3分钟内重启同一游戏）
                if quit_info and now - quit_info["quit_time"] <= 180 and not quit_info.get("notified"):
                    # 取消延迟任务
                    if hasattr(self, '_pending_quit_tasks') and self._pending_quit_tasks.get(group_id, {}).get(sid, {}).get(current_gameid):
                        self._pending_quit_tasks[group_id][sid][current_gameid].cancel()
                        self._pending_quit_tasks[group_id][sid].pop(current_gameid, None)
                    quit_info["notified"] = True
                    # 游戏播报过滤检查
                    if self._is_game_filtered(group_id, zh_game_name):
                        logger.info(f"[播报过滤] {name} 网络波动的游戏「{zh_game_name}」在过滤列表中，跳过推送")
                        last_states[sid] = status
                        continue
                    msg = f"⚠️ {name} 游玩 {zh_game_name} 时网络波动了"
                    # 推送到主群和所有联动群
                    notify_sessions = []
                    notify_session = getattr(self, 'notify_sessions', {}).get(group_id, None)
                    if notify_session:
                        notify_sessions.append(notify_session)
                    for push_gid in self.push_groups.get(sid, []):
                        push_session = getattr(self, 'notify_sessions', {}).get(push_gid, None)
                        if push_session and push_session not in notify_sessions:
                            notify_sessions.append(push_session)
                    for session in notify_sessions:
                        await self.context.send_message(session, MessageChain([Plain(msg)]))
                    last_states[sid] = status
                    continue  # 只推送网络波动提醒，跳过后续逻辑
                # 修复：补充开始游戏推送逻辑
                self._ensure_start_play_time_map(start_play_times, sid, current_gameid)[current_gameid] = now
                # 游戏播报过滤检查
                if self._is_game_filtered(group_id, zh_game_name):
                    logger.info(f"[播报过滤] {name} 开始的游戏「{zh_game_name}」在过滤列表中，跳过推送")
                    last_states[sid] = status
                    continue
                msg = f"🟢【{name}】开始游玩 {zh_game_name}"
                # 推送到主群和所有push_group
                notify_sessions = []
                notify_session = getattr(self, 'notify_sessions', {}).get(group_id, None)
                if notify_session:
                    notify_sessions.append(notify_session)
                for push_gid in self.push_groups.get(sid, []):
                    push_session = getattr(self, 'notify_sessions', {}).get(push_gid, None)
                    if push_session and push_session not in notify_sessions:
                        notify_sessions.append(push_session)
                # 渲染图片只做一次
                img_path = None
                try:
                    avatar_url = status.get("avatarfull") or status.get("avatar")
                    superpower = self.get_today_superpower(sid)
                    font_path = self.get_font_path('NotoSansHans-Regular.otf')
                    online_count = await self.get_game_online_count(current_gameid)
                    zh_game_name, en_game_name = await self.get_game_names(current_gameid, zh_game_name)
                    img_bytes = await render_game_start(
                        self.data_dir, sid, name, avatar_url, current_gameid, zh_game_name,
                        api_key=self.API_KEY, superpower=superpower, sgdb_api_key=self.SGDB_API_KEY,
                        font_path=font_path, sgdb_game_name=en_game_name, online_count=online_count, appid=gameid, sgdb_api_base=self.SGDB_API_BASE, steam_api_base=self.STEAM_API_BASE
                    )
                    img_path = self._create_temp_image(img_bytes)
                except Exception as e:
                    logger.error(f"推送开始游戏图片失败: {e}")
                    img_path = None
                try:
                    for session in notify_sessions:
                        try:
                            msg_chain = [Plain(f"🟢【{name}】开始游玩 {zh_game_name}")]
                            if img_path:
                                msg_chain.append(Image.fromFileSystem(img_path))
                            await self.context.send_message(session, MessageChain(msg_chain))
                        except Exception as e:
                            logger.error(f"推送开始游戏消息失败: {e}")
                finally:
                    self._cleanup_temp_file(img_path)
                # 成就监控任务启动（仅在成就推送开启时启动，节省 API 调用）
                if self.group_achievement_enabled.get(group_id, self._achievement_default):
                    try:
                        player_name = name
                        game_name = zh_game_name
                        key = (group_id, sid, current_gameid)
                        achievements = await self.achievement_monitor.get_player_achievements(self.API_KEY, group_id, sid, current_gameid)
                        self.achievement_snapshots[key] = list(achievements) if achievements else []
                        # 新增日志：已成功获取成就列表
                        unlocked_count = len(achievements) if achievements else 0
                        # 获取总成就数量
                        details = await self.achievement_monitor.get_achievement_details(group_id, current_gameid, lang="schinese", api_key=self.API_KEY, steamid=sid)
                        total_count = len(details) if details else 0
                        logger.info(f"[成就初始化] {name} 已成功获取成就列表 {unlocked_count}/{total_count} 游戏名：{zh_game_name}")
                        poll_task = asyncio.create_task(self.achievement_periodic_check(group_id, sid, current_gameid, player_name, game_name))
                        self.achievement_poll_tasks[key] = poll_task
                    except Exception as e:
                        logger.error(f"启动成就监控任务异常: {e}")
                else:
                    logger.info(f"[成就监控] 本群成就推送已关闭，跳过 {name} 的成就监控任务")
                last_states[sid] = status
                continue

            # 智能轮询间隔设置（支持固定间隔）
            next_poll = self.next_poll_time.setdefault(group_id, {})
            intervals = self.smart_poll_intervals if isinstance(self.smart_poll_intervals, list) and len(self.smart_poll_intervals) == 6 else [1, 3, 5, 10, 20, 30]
            if self.fixed_poll_interval and self.fixed_poll_interval > 0:
                poll_interval = max(1, int(self.fixed_poll_interval))
                if poll_interval >= 60 and poll_interval % 60 == 0:
                    poll_level_str = f"固定{poll_interval // 60}分钟轮询"
                else:
                    poll_level_str = f"固定{poll_interval}秒轮询"
            else:
                # 优先级：游戏中 > 在线 > 离线 > 默认
                if gameid:
                    poll_interval = intervals[0] * 60
                    poll_level_str = f"{intervals[0]}分钟轮询"
                elif personastate and int(personastate) > 0:
                    poll_interval = intervals[1] * 60
                    poll_level_str = f"{intervals[1]}分钟轮询"
                elif lastlogoff:
                    minutes_ago = (now - int(lastlogoff)) / 60
                    if minutes_ago <= 12:
                        poll_interval = intervals[1] * 60
                        poll_level_str = f"{intervals[1]}分钟轮询"
                    elif minutes_ago <= 180:
                        poll_interval = intervals[2] * 60
                        poll_level_str = f"{intervals[2]}分钟轮询"
                    elif minutes_ago <= 1440:
                        poll_interval = intervals[3] * 60
                        poll_level_str = f"{intervals[3]}分钟轮询"
                    elif minutes_ago <= 2880:
                        poll_interval = intervals[4] * 60
                        poll_level_str = f"{intervals[4]}分钟轮询"
                    else:
                        poll_interval = intervals[5] * 60
                        poll_level_str = f"{intervals[5]}分钟轮询"
                else:
                    poll_interval = intervals[5] * 60
                    poll_level_str = f"{intervals[5]}分钟轮询"
            if self.fixed_poll_interval and self.fixed_poll_interval > 0:
                next_time = now + poll_interval
            else:
                interval_min = max(1, poll_interval // 60)
                next_time = ((now // 60) + math.ceil(interval_min)) * 60
                if interval_min in [intervals[1], intervals[2], intervals[3], intervals[4], intervals[5]]:
                    next_time = ((now // 60) // interval_min + 1) * interval_min * 60
            next_poll[sid] = next_time
            # 轮询间隔描述
            if gameid:
                msg_lines.append(f"🟢【{name}】正在玩 {zh_game_name}（{poll_level_str}）")
            elif personastate and int(personastate) > 0:
                msg_lines.append(f"🟡【{name}】在线（{poll_level_str}）")
            elif lastlogoff:
                hours_ago = (now - int(lastlogoff)) / 3600
                msg_lines.append(f"⚪️【{name}】离线 上次在线 {hours_ago:.1f} 小时前（{poll_level_str}）")
            else:
                msg_lines.append(f"⚪️【{name}】离线（{poll_level_str}）")
            last_states[sid] = status

        for sid in pending_quit:
            for gameid in list(pending_quit[sid].keys()):
                info = pending_quit[sid][gameid]
                if now - info["quit_time"] >= 180 and not info.get("notified"):
                    # 游戏播报过滤检查
                    if self._is_game_filtered(group_id, info.get("game_name", "")):
                        logger.info(f"[播报过滤] {info.get('name', sid)} 退出的游戏「{info.get('game_name', '')}」在过滤列表中，跳过推送")
                        info["notified"] = True
                        # 清理成就轮询
                        key = (group_id, sid, gameid)
                        poll_task = self.achievement_poll_tasks.pop(key, None)
                        if poll_task:
                            poll_task.cancel()
                        self.achievement_snapshots.pop(key, None)
                        self.achievement_monitor.clear_game_achievements(group_id, sid, gameid)
                        self._clear_start_play_time(group_id, sid, gameid)
                        if gameid in pending_quit[sid]:
                            del pending_quit[sid][gameid]
                        continue
                    info["notified"] = True
                    duration_min = info.get("duration_min", 0)
                    # 优化时间显示
                    if duration_min < 60:
                        time_str = f"{duration_min:.1f}分钟"
                    else:
                        time_str = f"{duration_min/60:.1f}小时"
                    msg = f"👋 {info['name']} 不玩 {info['game_name']}了\n游玩时间 {time_str}"
                    try:
                        # 推送到主群和所有联动群
                        notify_sessions = []
                        notify_session = getattr(self, 'notify_sessions', {}).get(group_id, None)
                        if notify_session:
                            notify_sessions.append(notify_session)
                        for push_gid in self.push_groups.get(sid, []):
                            push_session = getattr(self, 'notify_sessions', {}).get(push_gid, None)
                            if push_session and push_session not in notify_sessions:
                                notify_sessions.append(push_session)
                        if notify_sessions:
                            tmp_path = None
                            try:
                                from datetime import datetime
                                end_time_str = datetime.fromtimestamp(info["quit_time"]).strftime("%Y-%m-%d %H:%M")
                                avatar_url = None
                                last_state = last_states.get(sid)
                                if last_state:
                                    avatar_url = last_state.get("avatarfull") or last_state.get("avatar")
                                if not avatar_url:
                                    status_full = await self.fetch_player_status(sid)
                                    if status_full:
                                        avatar_url = status_full.get("avatarfull") or status_full.get("avatar")
                                # 获取友好提示词
                                if duration_min < 5:
                                    tip_text = "风扇都没转热，主人就结束了？"
                                elif duration_min < 10:
                                    tip_text = "杂鱼杂鱼~主人你就这水平？"
                                elif duration_min < 30:
                                    tip_text = "热身一下就结束了？"
                                elif duration_min < 60:
                                    tip_text = "歇会儿再来，别太累了喵！"
                                elif duration_min < 120:
                                    tip_text = "沉浸在游戏世界，时间过得飞快喵！"
                                elif duration_min < 300:
                                    tip_text = "肝到手软了喵！主人不如陪陪咱~"
                                elif duration_min < 600:
                                    tip_text = "你吃饭了吗？还是说你已经忘了吃饭这件事？"
                                elif duration_min < 1200:
                                    tip_text = "家里电费都要被你玩光了喵！"
                                elif duration_min < 1800:
                                    tip_text = "咱都要给你颁发‘不眠猫’勋章了！"
                                elif duration_min < 2400:
                                    tip_text = "主人你还活着喵？你是不是忘了关电脑呀~"
                                else:
                                    tip_text = "你已经和椅子合为一体，成为传说中的‘椅子精’了喵！"
                                zh_game_name, en_game_name = await self.get_game_names(gameid, info["game_name"])
                                font_path = self.get_font_path('NotoSansHans-Regular.otf')
                                img_bytes = await render_game_end(
                                    self.data_dir, sid, info["name"], avatar_url, gameid, zh_game_name,
                                    end_time_str, tip_text, duration_min/60 if duration_min > 0 else 0, sgdb_api_key=self.SGDB_API_KEY, font_path=font_path, sgdb_game_name=en_game_name, appid=gameid, sgdb_api_base=self.SGDB_API_BASE
                                )
                                tmp_path = self._create_temp_image(img_bytes)
                                for session in notify_sessions:
                                    await self.context.send_message(session, MessageChain([Plain(msg), Image.fromFileSystem(tmp_path)]))
                            except Exception as e:
                                logger.error(f"推送游戏结束图片失败: {e}")
                                for session in notify_sessions:
                                    await self.context.send_message(session, MessageChain([Plain(msg)]))
                            finally:
                                self._cleanup_temp_file(tmp_path)
                        else:
                            logger.error("未设置推送会话，无法发送消息")
                    except Exception as e:
                        logger.error(f"推送正常退出消息失败: {e}")
                    if gameid in pending_quit[sid]:
                        del pending_quit[sid][gameid]
                    self._clear_start_play_time(group_id, sid, gameid)

        self._save_persistent_data()
        # 只返回日志字符串
        return "\n".join(msg_lines) if msg_lines else None

    async def get_game_online_count(self, gameid):
        '''通过 Steam Web API 获取当前游戏在线人数'''
        if not gameid:
            return None
        url = f"{self.STEAM_API_BASE}/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={gameid}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get('response', {}).get('player_count')
        except Exception as e:
            logger.warning(f"获取在线人数失败: {e} (gameid={gameid})")
        return None

    @filter.command("steam alllist")
    async def steam_alllist(self, event: AstrMessageEvent):
        '''列出所有群聊绑定的steam情况，包含群聊分组，玩家名，在线情况，下次轮询时间'''
        lines = []
        now = int(time.time())
        for group_id, steam_ids in self.group_steam_ids.items():
            lines.append(f"群组: {group_id}")
            last_states = self.group_last_states.get(group_id, {})
            next_poll = self.next_poll_time.get(group_id, {})
            for sid in steam_ids:
                status = last_states.get(sid)
                name = status.get('name') if status else sid
                gameid = status.get('gameid') if status else None
                game = status.get('gameextrainfo') if status else None
                lastlogoff = status.get('lastlogoff') if status else None
                personastate = status.get('personastate', 0) if status else 0
                next_time = next_poll.get(sid, now)
                seconds_left = int(next_time - now)
                if seconds_left < 60:
                    poll_str = f"下次轮询{seconds_left}秒后"
                else:
                    poll_str = f"下次轮询{seconds_left//60}分钟后"
                if gameid:
                    state_str = f"🟢正在玩 {await self.get_chinese_game_name(gameid, game)}"
                elif personastate and int(personastate) > 0:
                    state_str = "🟡在线"
                elif lastlogoff:
                    hours_ago = (now - int(lastlogoff)) / 3600
                    state_str = f"⚪️离线，上次在线 {hours_ago:.1f} 小时前"
                else:
                    state_str = "⚪️离线"
                lines.append(f"  {name}({sid}) - {state_str}（{poll_str}）")
            lines.append("")
        yield event.plain_result("\n".join(lines))

    def get_today_superpower(self, steamid):
        """获取指定SteamID当天的超能力描述（用于图片渲染）"""
        from datetime import date
        today = date.today().isoformat()
        cache_key = (steamid, today)
        if cache_key in self._superpower_cache:
            return self._superpower_cache[cache_key]
        if self._abilities is None:
            self._abilities = load_abilities(self._abilities_path)
        superpower = get_daily_superpower(steamid, self._abilities)
        self._superpower_cache[cache_key] = superpower
        return superpower

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("steam push_group")
    async def steam_push_group(self, event: AstrMessageEvent, steamid: str):
        '''将本群加入指定SteamID的联动推送组（不重复轮询，仅同步推送）'''
        group_id = str(event.get_group_id()) if hasattr(event, 'get_group_id') else 'default'
        if not steamid.isdigit() or len(steamid) != 17:
            yield event.plain_result("SteamID无效（需为64位数字串，17位）")
            return
        # 检查主群是否已轮询该SteamID
        found = False
        for gid, ids in self.group_steam_ids.items():
            if steamid in ids:
                found = True
                break
        if not found:
            yield event.plain_result("未找到已轮询该SteamID的主群，请先在任一群添加并开启监控。")
            return
        # 记录推送群
        self.push_groups.setdefault(steamid, [])
        if group_id not in self.push_groups[steamid]:
            self.push_groups[steamid].append(group_id)
            self._save_push_groups()
            yield event.plain_result(f"本群已加入SteamID {steamid} 的联动推送组。")
        else:
            yield event.plain_result("本群已在该SteamID的推送组中。")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("steam filter_add")
    async def steam_filter_add(self, event: AstrMessageEvent, game_name: str):
        '''添加游戏名关键词到本群播报过滤列表（模糊匹配，不区分大小写）'''
        group_id = str(event.get_group_id()) if hasattr(event, 'get_group_id') else 'default'
        game_name = game_name.strip()
        if not game_name:
            yield event.plain_result("过滤关键词不能为空。")
            return
        filters = self.group_game_filters.setdefault(group_id, [])
        if game_name.lower() in {kw.lower() for kw in filters}:
            yield event.plain_result(f"「{game_name}」已在过滤列表中。")
            return
        filters.append(game_name)
        self._save_game_filters()
        yield event.plain_result(f"已将「{game_name}」添加到本群播报过滤列表。\n当前过滤列表：{', '.join(filters)}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("steam filter_del")
    async def steam_filter_del(self, event: AstrMessageEvent, game_name: str):
        '''从本群播报过滤列表移除游戏名关键词'''
        group_id = str(event.get_group_id()) if hasattr(event, 'get_group_id') else 'default'
        game_name = game_name.strip()
        filters = self.group_game_filters.get(group_id, [])
        next_filters = [kw for kw in filters if kw.lower() != game_name.lower()]
        if len(next_filters) == len(filters):
            yield event.plain_result(f"「{game_name}」不在过滤列表中。")
            return
        self.group_game_filters[group_id] = next_filters
        self._save_game_filters()
        yield event.plain_result(f"已从本群过滤列表移除「{game_name}」。\n当前过滤列表：{', '.join(next_filters) or '空'}")

    @filter.command("steam filter_list")
    async def steam_filter_list(self, event: AstrMessageEvent):
        '''查看本群播报过滤列表'''
        group_id = str(event.get_group_id()) if hasattr(event, 'get_group_id') else 'default'
        filters = self.group_game_filters.get(group_id, [])
        global_filters = getattr(self, "_global_game_filters", [])
        lines = []
        lines.append("全局播报过滤列表：" + (", ".join(global_filters) if global_filters else "空"))
        lines.append("本群播报过滤列表：" + (", ".join(filters) if filters else "空"))
        yield event.plain_result("\n".join(lines))

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("steam delpush_group")
    async def steam_delpush_group(self, event: AstrMessageEvent, steamid: str):
        '''将本群从指定SteamID的联动推送组移除'''
        group_id = str(event.get_group_id()) if hasattr(event, 'get_group_id') else 'default'
        if not steamid.isdigit() or len(steamid) != 17:
            yield event.plain_result("SteamID无效（需为64位数字串，17位）")
            return
        if steamid not in self.push_groups or group_id not in self.push_groups[steamid]:
            yield event.plain_result("本群未在该SteamID的推送组中。")
            return
        self.push_groups[steamid].remove(group_id)
        if not self.push_groups[steamid]:
            self.push_groups.pop(steamid)
        self._save_push_groups()
        yield event.plain_result(f"本群已从SteamID {steamid} 的联动推送组移除。")

