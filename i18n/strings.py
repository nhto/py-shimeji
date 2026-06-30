"""Localized UI label dictionaries."""

from __future__ import annotations

CHAT_DEFAULT_LANGUAGE: str = "zh-Hant"

CHAT_LANGUAGES: list[tuple[str, str]] = [
    ("en", "English"),
    ("zh-Hans", "Simplified Chinese"),
    ("zh-Hant", "Traditional Chinese"),
]

CHAT_LANGUAGE_INSTRUCTIONS: dict[str, str] = {
    "en": "Always reply in English, regardless of the language the user writes in.",
    "zh-Hans": "Always reply in Simplified Chinese (简体中文), regardless of the language the user writes in.",
    "zh-Hant": "Always reply in Traditional Chinese (繁體中文), regardless of the language the user writes in.",
}

CHAT_GREETINGS: dict[str, str] = {
    "en": (
        "Hi! I'm Bubu. Ask me anything — I'm happy to chat while I hang out on your desktop."
    ),
    "zh-Hans": "你好！我是 Bubu。随便问我什么吧——我很乐意一边陪你逛桌面一边聊天。",
    "zh-Hant": "你好！我是 Bubu。隨便問我什麼吧——我很樂意一邊陪你逛桌面一邊聊天。",
}

CHAT_NO_API_KEY_GREETINGS: dict[str, str] = {
    "en": (
        "Hi! I'm Bubu. I'd love to chat, but no OpenRouter API key is set yet. "
        "Use Preference in the tray menu to add one."
    ),
    "zh-Hans": (
        "你好！我是 Bubu。我很想聊天，但还没有配置 OpenRouter API 密钥。"
        "请在托盘菜单中选择「偏好设置」进行设置。"
    ),
    "zh-Hant": (
        "你好！我是 Bubu。我很想聊天，但還沒有設定 OpenRouter API 金鑰。"
        "請在系統匣選單中選擇「偏好設定」進行設定。"
    ),
}

CHAT_NO_API_KEY_SEND_LABELS: dict[str, str] = {
    "en": "Add your OpenRouter API key from Preference in the tray menu to chat.",
    "zh-Hans": "请从托盘菜单的「偏好设置」设置 OpenRouter API 密钥后再聊天。",
    "zh-Hant": "請從系統匣選單的「偏好設定」設定 OpenRouter API 金鑰後再聊天。",
}

CHAT_STATUS_ONLINE_LABELS: dict[str, str] = {
    "en": "Online",
    "zh-Hans": "在线",
    "zh-Hant": "線上",
}

CHAT_STATUS_OFFLINE_LABELS: dict[str, str] = {
    "en": "No API key",
    "zh-Hans": "未配置密钥",
    "zh-Hant": "未設定金鑰",
}

CHAT_STATUS_TYPING_LABELS: dict[str, str] = {
    "en": "Typing...",
    "zh-Hans": "正在回复...",
    "zh-Hant": "正在回覆...",
}

CHAT_TYPING_PHRASE_LABELS: dict[str, str] = {
    "en": "Bubu is thinking",
    "zh-Hans": "Bubu 正在思考",
    "zh-Hant": "Bubu 正在思考",
}

CHAT_TYPING_INTERVAL_MS: int = 380

TRAY_NO_API_KEY_TITLE_LABELS: dict[str, str] = {
    "en": "py-shimeji — chat unavailable",
    "zh-Hans": "py-shimeji — 无法聊天",
    "zh-Hant": "py-shimeji — 無法聊天",
}

TRAY_NO_API_KEY_MESSAGE_LABELS: dict[str, str] = {
    "en": (
        "Open Preference in the tray menu to add an OpenRouter API key and chat with Bubu."
    ),
    "zh-Hans": "在托盘菜单中打开「偏好设置」以添加 OpenRouter API 密钥并与 Bubu 聊天。",
    "zh-Hant": "在系統匣選單中開啟「偏好設定」以新增 OpenRouter API 金鑰並與 Bubu 聊天。",
}

TRAY_API_KEY_SAVED_MESSAGE_LABELS: dict[str, str] = {
    "en": "OpenRouter API key saved. You can chat with Bubu now.",
    "zh-Hans": "OpenRouter API 密钥已保存。现在可以与 Bubu 聊天了。",
    "zh-Hant": "OpenRouter API 金鑰已儲存。現在可以與 Bubu 聊天了。",
}

TRAY_API_KEY_CLEARED_MESSAGE_LABELS: dict[str, str] = {
    "en": "OpenRouter API key removed. Chat is disabled.",
    "zh-Hans": "OpenRouter API 密钥已移除。聊天功能已禁用。",
    "zh-Hant": "OpenRouter API 金鑰已移除。聊天功能已停用。",
}

TRAY_PREFERENCES_SAVED_MESSAGE_LABELS: dict[str, str] = {
    "en": "Preferences saved.",
    "zh-Hans": "偏好设置已保存。",
    "zh-Hant": "偏好設定已儲存。",
}

TRAY_HIDE_PET_LABELS: dict[str, str] = {
    "en": "Hide Pet {index}",
    "zh-Hans": "隐藏宠物 {index}",
    "zh-Hant": "隱藏寵物 {index}",
}

TRAY_SHOW_PET_LABELS: dict[str, str] = {
    "en": "Show Pet {index}",
    "zh-Hans": "显示宠物 {index}",
    "zh-Hant": "顯示寵物 {index}",
}

TRAY_TOGGLE_ALL_PETS_TOOLTIP_LABELS: dict[str, str] = {
    "en": "The shortcut shows or hides all pets.",
    "zh-Hans": "该快捷键会显示或隐藏全部宠物。",
    "zh-Hant": "該快捷鍵會顯示或隱藏全部寵物。",
}

TRAY_CHANGE_SPRITES_LABELS: dict[str, str] = {
    "en": "Change Pet {index} sprites...",
    "zh-Hans": "更改宠物 {index} 形象...",
    "zh-Hant": "更改寵物 {index} 形象...",
}

TRAY_SELECT_SPRITES_TITLE_LABELS: dict[str, str] = {
    "en": "Select sprite folder for Pet {index}",
    "zh-Hans": "选择宠物 {index} 的形象文件夹",
    "zh-Hant": "選擇寵物 {index} 的形象資料夾",
}

SPRITE_PICKER_TITLE_LABELS: dict[str, str] = {
    "en": "Pet {index} appearance",
    "zh-Hans": "宠物 {index} 形象",
    "zh-Hant": "寵物 {index} 形象",
}

SPRITE_PICKER_INTRO_LABELS: dict[str, str] = {
    "en": "Choose a sprite set, or browse for a custom folder.",
    "zh-Hans": "选择一套形象，或浏览自定义文件夹。",
    "zh-Hant": "選擇一套形象，或瀏覽自訂資料夾。",
}

SPRITE_PICKER_FILES_HEADING_LABELS: dict[str, str] = {
    "en": "PNG files in the folder",
    "zh-Hans": "文件夹中的 PNG 文件",
    "zh-Hant": "資料夾中的 PNG 檔案",
}

SPRITE_STATE_LABELS: dict[str, dict[str, str]] = {
    "idle": {"en": "Idle", "zh-Hans": "待机", "zh-Hant": "待機"},
    "walk": {"en": "Walk", "zh-Hans": "行走", "zh-Hant": "行走"},
    "sit": {"en": "Sit", "zh-Hans": "坐下", "zh-Hant": "坐下"},
    "fall": {"en": "Fall", "zh-Hans": "下落", "zh-Hant": "下落"},
    "drag": {"en": "Drag", "zh-Hans": "拖拽", "zh-Hant": "拖曳"},
}

SPRITE_PICKER_OPTIONAL_LABELS: dict[str, str] = {
    "en": "optional",
    "zh-Hans": "可选",
    "zh-Hant": "選用",
}

SPRITE_PICKER_BROWSE_LABELS: dict[str, str] = {
    "en": "Browse folder…",
    "zh-Hans": "浏览文件夹…",
    "zh-Hant": "瀏覽資料夾…",
}

SPRITE_PICKER_APPLY_LABELS: dict[str, str] = {
    "en": "Apply",
    "zh-Hans": "应用",
    "zh-Hant": "套用",
}

SPRITE_PICKER_CANCEL_LABELS: dict[str, str] = {
    "en": "Cancel",
    "zh-Hans": "取消",
    "zh-Hant": "取消",
}

SPRITE_PICKER_INVALID_FOLDER_LABELS: dict[str, str] = {
    "en": (
        "That folder does not contain py-shimeji PNGs (idle_1.png, …) "
        "or a Shimeji pack (conf/actions.xml plus image files)."
    ),
    "zh-Hans": (
        "该文件夹不包含 py-shimeji 的 PNG（idle_1.png 等），"
        "也不是 Shimeji 形象包（conf/actions.xml 与图片文件）。"
    ),
    "zh-Hant": (
        "該資料夾不包含 py-shimeji 的 PNG（idle_1.png 等），"
        "也不是 Shimeji 形象包（conf/actions.xml 與圖片檔案）。"
    ),
}

SPRITE_PICKER_SHIMEJI_HINT_LABELS: dict[str, str] = {
    "en": "Shimeji pack detected — frames are mapped from actions.xml automatically.",
    "zh-Hans": "已识别 Shimeji 形象包 — 将自动从 actions.xml 映射帧。",
    "zh-Hant": "已識別 Shimeji 形象包 — 將自動從 actions.xml 對應幀。",
}

SPRITE_PICKER_IMPORT_LABELS: dict[str, str] = {
    "en": "Convert to py-shimeji PNGs…",
    "zh-Hans": "转换为 py-shimeji PNG…",
    "zh-Hant": "轉換為 py-shimeji PNG…",
}

SPRITE_PICKER_IMPORT_DONE_LABELS: dict[str, str] = {
    "en": "Converted Shimeji pack to:\n{path}",
    "zh-Hans": "已将 Shimeji 形象包转换到：\n{path}",
    "zh-Hant": "已將 Shimeji 形象包轉換到：\n{path}",
}

SPRITE_PICKER_IMPORT_FAILED_LABELS: dict[str, str] = {
    "en": "Could not convert that Shimeji pack.",
    "zh-Hans": "无法转换该 Shimeji 形象包。",
    "zh-Hant": "無法轉換該 Shimeji 形象包。",
}

TRAY_CHAT_LABELS: dict[str, str] = {
    "en": "Chat with bubu",
    "zh-Hans": "与 bubu 聊天",
    "zh-Hant": "與 bubu 聊天",
}

TRAY_PREFERENCE_LABELS: dict[str, str] = {
    "en": "Preference",
    "zh-Hans": "偏好设置",
    "zh-Hant": "偏好設定",
}

TRAY_BEHAVIOR_LABELS: dict[str, str] = {
    "en": "Pet behavior...",
    "zh-Hans": "宠物行为...",
    "zh-Hant": "寵物行為...",
}

TRAY_BEHAVIOR_SAVED_MESSAGE_LABELS: dict[str, str] = {
    "en": "Pet behavior settings saved.",
    "zh-Hans": "宠物行为设置已保存。",
    "zh-Hant": "寵物行為設定已儲存。",
}

BEHAVIOR_DIALOG_TITLE_LABELS: dict[str, str] = {
    "en": "Pet behavior",
    "zh-Hans": "宠物行为",
    "zh-Hant": "寵物行為",
}

BEHAVIOR_DIALOG_INTRO_LABELS: dict[str, str] = {
    "en": "Adjust how pets move and interact on your desktop.",
    "zh-Hans": "调整宠物在桌面上的移动与互动方式。",
    "zh-Hant": "調整寵物在桌面上的移動與互動方式。",
}

BEHAVIOR_SPEED_LABELS: dict[str, str] = {
    "en": "Movement speed: {value}%",
    "zh-Hans": "移动速度：{value}%",
    "zh-Hant": "移動速度：{value}%",
}

BEHAVIOR_SPEED_HINT_LABELS: dict[str, str] = {
    "en": "Walk, climb, and fall speed.",
    "zh-Hans": "行走、攀爬与下落速度。",
    "zh-Hant": "行走、攀爬與下落速度。",
}

BEHAVIOR_CHASE_LABELS: dict[str, str] = {
    "en": "Cursor chase chance: {value}%",
    "zh-Hans": "追逐鼠标概率：{value}%",
    "zh-Hant": "追逐滑鼠機率：{value}%",
}

BEHAVIOR_CHASE_HINT_LABELS: dict[str, str] = {
    "en": "How often idle pets walk toward your cursor.",
    "zh-Hans": "待机宠物走向鼠标的频率。",
    "zh-Hant": "待機寵物走向滑鼠的頻率。",
}

BEHAVIOR_PET_COUNT_LABELS: dict[str, str] = {
    "en": "Number of pets",
    "zh-Hans": "宠物数量",
    "zh-Hant": "寵物數量",
}

BEHAVIOR_PET_COUNT_HINT_LABELS: dict[str, str] = {
    "en": "Between {min} and {max}. Extra pets appear immediately.",
    "zh-Hans": "范围 {min}–{max}。额外的宠物会立即出现。",
    "zh-Hant": "範圍 {min}–{max}。額外的寵物會立即出現。",
}

BEHAVIOR_AMBIENT_LABELS: dict[str, str] = {
    "en": "Ambient speech bubbles",
    "zh-Hans": "随机说话气泡",
    "zh-Hant": "隨機說話氣泡",
}

BEHAVIOR_AMBIENT_HINT_LABELS: dict[str, str] = {
    "en": "Pets occasionally say short phrases while wandering.",
    "zh-Hans": "宠物闲逛时会偶尔说些简短的话。",
    "zh-Hant": "寵物閒逛時會偶爾說些簡短的話。",
}

BEHAVIOR_SAVE_LABELS: dict[str, str] = {
    "en": "Save",
    "zh-Hans": "保存",
    "zh-Hant": "儲存",
}

BEHAVIOR_CANCEL_LABELS: dict[str, str] = {
    "en": "Cancel",
    "zh-Hans": "取消",
    "zh-Hant": "取消",
}

TRAY_CLICK_THROUGH_LABELS: dict[str, str] = {
    "en": "Click-through (pass mouse clicks)",
    "zh-Hans": "穿透点击（鼠标穿透）",
    "zh-Hant": "穿透點擊（滑鼠穿透）",
}

TRAY_CLICK_THROUGH_TOOLTIP_LABELS: dict[str, str] = {
    "en": "When enabled, pets ignore the mouse. Disable to drag them.",
    "zh-Hans": "启用后宠物会忽略鼠标。关闭后可拖动。",
    "zh-Hant": "啟用後寵物會忽略滑鼠。關閉後可拖動。",
}

TRAY_PAUSE_PETS_LABELS: dict[str, str] = {
    "en": "Pause pets (reduce motion)",
    "zh-Hans": "暂停宠物（减少动画）",
    "zh-Hant": "暫停寵物（減少動畫）",
}

TRAY_PAUSE_PETS_TOOLTIP_LABELS: dict[str, str] = {
    "en": (
        "Pets stay still for meetings or accessibility. "
        "Disable click-through to drag them while paused."
    ),
    "zh-Hans": "宠物保持静止，适合开会或无障碍使用。关闭穿透点击后可拖动它们。",
    "zh-Hant": "寵物保持靜止，適合開會或無障礙使用。關閉穿透點擊後可拖動牠們。",
}

TRAY_QUIT_LABELS: dict[str, str] = {
    "en": "Quit",
    "zh-Hans": "退出",
    "zh-Hant": "退出",
}

TRAY_OUTLOOK_MENU_LABELS: dict[str, str] = {
    "en": "Outlook",
    "zh-Hans": "Outlook",
    "zh-Hant": "Outlook",
}

TRAY_OUTLOOK_CONNECT_LABELS: dict[str, str] = {
    "en": "Connect",
    "zh-Hans": "连接",
    "zh-Hant": "連接",
}

TRAY_OUTLOOK_DISCONNECT_LABELS: dict[str, str] = {
    "en": "Disconnect",
    "zh-Hans": "断开",
    "zh-Hant": "斷開",
}

TRAY_OUTLOOK_SETTINGS_LABELS: dict[str, str] = {
    "en": "Outlook settings...",
    "zh-Hans": "Outlook 设置...",
    "zh-Hant": "Outlook 設定...",
}

TRAY_OUTLOOK_CONNECTED_MESSAGE_LABELS: dict[str, str] = {
    "en": "Connected to Outlook as {email}.",
    "zh-Hans": "已连接 Outlook：{email}",
    "zh-Hant": "已連接 Outlook：{email}",
}

TRAY_OUTLOOK_CONNECT_FAILED_TITLE_LABELS: dict[str, str] = {
    "en": "Outlook connection failed",
    "zh-Hans": "Outlook 连接失败",
    "zh-Hant": "Outlook 連線失敗",
}

TRAY_OUTLOOK_CONNECT_FAILED_MESSAGE_LABELS: dict[str, str] = {
    "en": (
        "Could not connect. For New Outlook, set AZURE_CLIENT_ID in .env and sign in when prompted. "
        "For classic Outlook, turn off the New Outlook toggle and try again."
    ),
    "zh-Hans": (
        "连接失败。新版 Outlook 请在 .env 设置 AZURE_CLIENT_ID 并按提示登录。"
        "经典 Outlook 请关闭“新版 Outlook”开关后重试。"
    ),
    "zh-Hant": (
        "連線失敗。新版 Outlook 請在 .env 設定 AZURE_CLIENT_ID 並依提示登入。"
        "傳統 Outlook 請關閉「新版 Outlook」開關後重試。"
    ),
}

TRAY_OUTLOOK_DISCONNECTED_MESSAGE_LABELS: dict[str, str] = {
    "en": "Outlook disconnected.",
    "zh-Hans": "已断开 Outlook。",
    "zh-Hant": "已斷開 Outlook。",
}

TRAY_OUTLOOK_SETTINGS_SAVED_MESSAGE_LABELS: dict[str, str] = {
    "en": "Outlook settings saved.",
    "zh-Hans": "Outlook 设置已保存。",
    "zh-Hant": "Outlook 設定已儲存。",
}

TRAY_TOOLTIP_OUTLOOK_UNREAD_LABELS: dict[str, str] = {
    "en": "py-shimeji · Outlook: {count} unread",
    "zh-Hans": "py-shimeji · Outlook：{count} 封未读",
    "zh-Hant": "py-shimeji · Outlook：{count} 封未讀",
}

TRAY_TOOLTIP_OUTLOOK_UNAVAILABLE_LABELS: dict[str, str] = {
    "en": "py-shimeji · Outlook: not available",
    "zh-Hans": "py-shimeji · Outlook：不可用",
    "zh-Hant": "py-shimeji · Outlook：不可用",
}

OUTLOOK_DIALOG_TITLE_LABELS: dict[str, str] = {
    "en": "Outlook settings",
    "zh-Hans": "Outlook 设置",
    "zh-Hant": "Outlook 設定",
}

OUTLOOK_DIALOG_INTRO_LABELS: dict[str, str] = {
    "en": (
        "Choose how py-shimeji reads your mailbox. "
        "New Outlook requires Microsoft 365 (Graph API). "
        "Classic Outlook desktop can use COM instead."
    ),
    "zh-Hans": (
        "选择 py-shimeji 读取邮箱的方式。"
        "新版 Outlook 需使用 Microsoft 365（Graph API）。"
        "经典 Outlook 桌面版可使用 COM。"
    ),
    "zh-Hant": (
        "選擇 py-shimeji 讀取信箱的方式。"
        "新版 Outlook 需使用 Microsoft 365（Graph API）。"
        "傳統 Outlook 桌面版可使用 COM。"
    ),
}

OUTLOOK_DIALOG_SOURCE_LABELS: dict[str, str] = {
    "en": "Connection type",
    "zh-Hans": "连接方式",
    "zh-Hant": "連線方式",
}

OUTLOOK_DIALOG_SOURCE_GRAPH_LABELS: dict[str, str] = {
    "en": "Microsoft 365 / New Outlook (Graph API)",
    "zh-Hans": "Microsoft 365 / 新版 Outlook（Graph API）",
    "zh-Hant": "Microsoft 365 / 新版 Outlook（Graph API）",
}

OUTLOOK_DIALOG_SOURCE_COM_LABELS: dict[str, str] = {
    "en": "Classic Outlook desktop (COM)",
    "zh-Hans": "经典 Outlook 桌面版（COM）",
    "zh-Hant": "傳統 Outlook 桌面版（COM）",
}

OUTLOOK_DIALOG_SOURCE_GRAPH_HINT_LABELS: dict[str, str] = {
    "en": "Works with New Outlook. Requires AZURE_CLIENT_ID in .env (one-time browser sign-in).",
    "zh-Hans": "适用于新版 Outlook。需在 .env 中配置 AZURE_CLIENT_ID（浏览器登录一次）。",
    "zh-Hant": "適用於新版 Outlook。需在 .env 中設定 AZURE_CLIENT_ID（瀏覽器登入一次）。",
}

OUTLOOK_DIALOG_SOURCE_COM_HINT_LABELS: dict[str, str] = {
    "en": "Windows only. Requires classic OUTLOOK.EXE — turn off the New Outlook toggle.",
    "zh-Hans": "仅 Windows。需经典 OUTLOOK.EXE — 请关闭“新版 Outlook”开关。",
    "zh-Hant": "僅 Windows。需傳統 OUTLOOK.EXE — 請關閉「新版 Outlook」開關。",
}

OUTLOOK_DIALOG_STATUS_NEEDS_CONFIG_LABELS: dict[str, str] = {
    "en": "Add AZURE_CLIENT_ID to .env to use New Outlook",
    "zh-Hans": "请在 .env 中添加 AZURE_CLIENT_ID 以使用新版 Outlook",
    "zh-Hant": "請在 .env 中新增 AZURE_CLIENT_ID 以使用新版 Outlook",
}

OUTLOOK_DIALOG_GRAPH_IT_BLOCKED_LABELS: dict[str, str] = {
    "en": (
        "Your organization may block Microsoft Graph for third-party apps. "
        "Use Classic Outlook (COM) instead, or ask IT to approve a Graph app."
    ),
    "zh-Hans": (
        "你的组织可能禁止第三方应用使用 Microsoft Graph。"
        "请改用经典 Outlook（COM），或联系 IT 审批 Graph 应用。"
    ),
    "zh-Hant": (
        "你的組織可能禁止第三方應用程式使用 Microsoft Graph。"
        "請改用傳統 Outlook（COM），或聯絡 IT 審批 Graph 應用。"
    ),
}

OUTLOOK_DIALOG_STATUS_CONNECTED_LABELS: dict[str, str] = {
    "en": "Connected as {email}",
    "zh-Hans": "已连接：{email}",
    "zh-Hant": "已連接：{email}",
}

OUTLOOK_DIALOG_STATUS_DISCONNECTED_LABELS: dict[str, str] = {
    "en": "Not connected",
    "zh-Hans": "未连接",
    "zh-Hant": "未連接",
}

OUTLOOK_DIALOG_STATUS_UNAVAILABLE_LABELS: dict[str, str] = {
    "en": "Outlook not running",
    "zh-Hans": "Outlook 未运行",
    "zh-Hant": "Outlook 未執行",
}

OUTLOOK_DIALOG_STATUS_BLOCKED_LABELS: dict[str, str] = {
    "en": "COM blocked or unavailable",
    "zh-Hans": "COM 被阻止或不可用",
    "zh-Hant": "COM 被阻擋或不可用",
}

OUTLOOK_DIALOG_STATUS_UNSUPPORTED_LABELS: dict[str, str] = {
    "en": "Outlook COM is Windows-only",
    "zh-Hans": "Outlook COM 仅支持 Windows",
    "zh-Hant": "Outlook COM 僅支援 Windows",
}

OUTLOOK_DIALOG_TEST_LABELS: dict[str, str] = {
    "en": "Test connection",
    "zh-Hans": "测试连接",
    "zh-Hant": "測試連線",
}

OUTLOOK_DIALOG_MAIL_LABELS: dict[str, str] = {
    "en": "Mail notifications",
    "zh-Hans": "邮件通知",
    "zh-Hant": "郵件通知",
}

OUTLOOK_DIALOG_CALENDAR_LABELS: dict[str, str] = {
    "en": "Calendar reminders",
    "zh-Hans": "日历提醒",
    "zh-Hant": "行事曆提醒",
}

OUTLOOK_DIALOG_MAIL_HINT_LABELS: dict[str, str] = {
    "en": "When enabled, new unread mail can trigger pet alerts.",
    "zh-Hans": "启用后，未读邮件可触发宠物提醒。",
    "zh-Hant": "啟用後，未讀郵件可觸發寵物提醒。",
}

OUTLOOK_DIALOG_MAIL_EVENTS_LABELS: dict[str, str] = {
    "en": "Real-time mail (classic Outlook COM)",
    "zh-Hans": "实时邮件（经典 Outlook COM）",
    "zh-Hant": "即時郵件（傳統 Outlook COM）",
}

OUTLOOK_DIALOG_MAIL_EVENTS_HINT_LABELS: dict[str, str] = {
    "en": "Instant inbox alerts via COM events. Falls back to polling if unavailable.",
    "zh-Hans": "通过 COM 事件即时提醒；不可用时回退到轮询。",
    "zh-Hant": "透過 COM 事件即時提醒；不可用時回退到輪詢。",
}

OUTLOOK_DIALOG_CALENDAR_HINT_LABELS: dict[str, str] = {
    "en": "When enabled, upcoming meetings trigger pet reminders before they start.",
    "zh-Hans": "启用后，会议开始前会触发宠物提醒。",
    "zh-Hant": "啟用後，會議開始前會觸發寵物提醒。",
}

OUTLOOK_DIALOG_SAVE_LABELS: dict[str, str] = {
    "en": "Save",
    "zh-Hans": "保存",
    "zh-Hant": "儲存",
}

OUTLOOK_DIALOG_CANCEL_LABELS: dict[str, str] = {
    "en": "Cancel",
    "zh-Hans": "取消",
    "zh-Hant": "取消",
}

OUTLOOK_DIALOG_TEST_OK_LABELS: dict[str, str] = {
    "en": "Connection OK — {email}",
    "zh-Hans": "连接成功 — {email}",
    "zh-Hant": "連線成功 — {email}",
}

OUTLOOK_DIALOG_TEST_FAIL_LABELS: dict[str, str] = {
    "en": "Connection failed — open classic Outlook and try again.",
    "zh-Hans": "连接失败 — 请打开经典 Outlook 后重试。",
    "zh-Hant": "連線失敗 — 請開啟傳統 Outlook 後重試。",
}

OUTLOOK_DIALOG_NOTIFY_PET_LABELS: dict[str, str] = {
    "en": "Notify pet",
    "zh-Hans": "通知宠物",
    "zh-Hant": "通知寵物",
}

OUTLOOK_DIALOG_NOTIFY_PET_FIRST_VISIBLE_LABELS: dict[str, str] = {
    "en": "First visible pet",
    "zh-Hans": "第一个可见宠物",
    "zh-Hant": "第一個可見寵物",
}

OUTLOOK_DIALOG_NOTIFY_PET_NUMBER_LABELS: dict[str, str] = {
    "en": "Pet {number}",
    "zh-Hans": "宠物 {number}",
    "zh-Hant": "寵物 {number}",
}

OUTLOOK_DIALOG_NOTIFY_PET_HINT_LABELS: dict[str, str] = {
    "en": "Which pet shows mail and calendar speech bubbles.",
    "zh-Hans": "由哪只宠物显示邮件和日历气泡。",
    "zh-Hant": "由哪隻寵物顯示郵件和行事曆氣泡。",
}

OUTLOOK_DIALOG_NOTIFY_WHEN_PAUSED_LABELS: dict[str, str] = {
    "en": "Show notifications while pets are paused",
    "zh-Hans": "宠物暂停时仍显示通知",
    "zh-Hant": "寵物暫停時仍顯示通知",
}

OUTLOOK_DIALOG_NOTIFY_WHEN_PAUSED_HINT_LABELS: dict[str, str] = {
    "en": "When off, paused pets use the system tray instead of speech bubbles.",
    "zh-Hans": "关闭后，暂停中的宠物改用系统托盘通知。",
    "zh-Hant": "關閉後，暫停中的寵物改用系統匣通知。",
}

OUTLOOK_DIALOG_SHARED_MAILBOXES_LABELS: dict[str, str] = {
    "en": "Include shared and additional mailboxes",
    "zh-Hans": "包含共享和其他邮箱",
    "zh-Hant": "包含共用和其他信箱",
}

OUTLOOK_DIALOG_SHARED_MAILBOXES_HINT_LABELS: dict[str, str] = {
    "en": "Classic COM only. Polls every inbox in your Outlook profile, not just the default.",
    "zh-Hans": "仅经典 COM。轮询 Outlook 配置中的所有收件箱，不仅是默认邮箱。",
    "zh-Hant": "僅傳統 COM。輪詢 Outlook 設定中的所有收件箱，不僅是預設信箱。",
}

PREFERENCES_TITLE_LABELS: dict[str, str] = {
    "en": "Preferences",
    "zh-Hans": "偏好设置",
    "zh-Hant": "偏好設定",
}

PREFERENCES_OPENROUTER_HEADING_LABELS: dict[str, str] = {
    "en": "OpenRouter configuration",
    "zh-Hans": "OpenRouter 配置",
    "zh-Hant": "OpenRouter 設定",
}

PREFERENCES_OPENROUTER_INTRO_LABELS: dict[str, str] = {
    "en": (
        "Bubu uses OpenRouter for chat. Your key is stored locally in "
        "<b>.env</b> and is only sent to OpenRouter when you message Bubu."
    ),
    "zh-Hans": (
        "Bubu 使用 OpenRouter 进行聊天。你的密钥保存在本地 "
        "<b>.env</b> 文件中，仅在你向 Bubu 发送消息时才会发送给 OpenRouter。"
    ),
    "zh-Hant": (
        "Bubu 使用 OpenRouter 進行聊天。你的金鑰保存在本機 "
        "<b>.env</b> 檔案中，僅在你向 Bubu 傳送訊息時才會傳送給 OpenRouter。"
    ),
}

PREFERENCES_API_KEY_LABELS: dict[str, str] = {
    "en": "API key",
    "zh-Hans": "API 密钥",
    "zh-Hant": "API 金鑰",
}

PREFERENCES_KEY_HINT_LABELS: dict[str, str] = {
    "en": "Leave blank and click Save to keep the current key.",
    "zh-Hans": "留空并点击保存以保留当前密钥。",
    "zh-Hant": "留空並點擊儲存以保留目前金鑰。",
}

PREFERENCES_KEY_LINK_LABELS: dict[str, str] = {
    "en": '<a href="https://openrouter.ai/keys">Get a key at openrouter.ai/keys</a>',
    "zh-Hans": '<a href="https://openrouter.ai/keys">在 openrouter.ai/keys 获取密钥</a>',
    "zh-Hant": '<a href="https://openrouter.ai/keys">在 openrouter.ai/keys 取得金鑰</a>',
}

PREFERENCES_LANGUAGE_HEADING_LABELS: dict[str, str] = {
    "en": "Language",
    "zh-Hans": "语言",
    "zh-Hant": "語言",
}

PREFERENCES_LANGUAGE_HINT_LABELS: dict[str, str] = {
    "en": "Choose the language Bubu uses when replying in chat.",
    "zh-Hans": "选择 Bubu 在聊天中回复时使用的语言。",
    "zh-Hant": "選擇 Bubu 在聊天中回覆時使用的語言。",
}

PREFERENCES_CLEAR_KEY_LABELS: dict[str, str] = {
    "en": "Clear key",
    "zh-Hans": "清除密钥",
    "zh-Hant": "清除金鑰",
}

PREFERENCES_SAVE_LABELS: dict[str, str] = {
    "en": "Save",
    "zh-Hans": "保存",
    "zh-Hant": "儲存",
}

PREFERENCES_CANCEL_LABELS: dict[str, str] = {
    "en": "Cancel",
    "zh-Hans": "取消",
    "zh-Hant": "取消",
}

PREFERENCES_STATUS_CONFIGURED_LABELS: dict[str, str] = {
    "en": "Status: configured ({masked})",
    "zh-Hans": "状态：已配置（{masked}）",
    "zh-Hant": "狀態：已設定（{masked}）",
}

PREFERENCES_STATUS_NOT_CONFIGURED_LABELS: dict[str, str] = {
    "en": "Status: not configured",
    "zh-Hans": "状态：未配置",
    "zh-Hant": "狀態：未設定",
}

PREFERENCES_STATUS_ENTER_KEY_LABELS: dict[str, str] = {
    "en": "Status: enter a key before saving.",
    "zh-Hans": "状态：保存前请输入密钥。",
    "zh-Hant": "狀態：儲存前請輸入金鑰。",
}

UI_LANGUAGE_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "en": "English",
        "zh-Hans": "Simplified Chinese",
        "zh-Hant": "Traditional Chinese",
    },
    "zh-Hans": {
        "en": "英语",
        "zh-Hans": "简体中文",
        "zh-Hant": "繁体中文",
    },
    "zh-Hant": {
        "en": "英語",
        "zh-Hans": "簡體中文",
        "zh-Hant": "繁體中文",
    },
}

CHAT_INPUT_PLACEHOLDERS: dict[str, str] = {
    "en": "Say something to Bubu...",
    "zh-Hans": "跟 Bubu 说点什么...",
    "zh-Hant": "跟 Bubu 說點什麼...",
}

CHAT_SEND_LABELS: dict[str, str] = {
    "en": "Send",
    "zh-Hans": "发送",
    "zh-Hant": "傳送",
}

CHAT_ATTACH_IMAGE_LABELS: dict[str, str] = {
    "en": "Attach image",
    "zh-Hans": "附加图片",
    "zh-Hant": "附加圖片",
}

CHAT_IMAGE_ONLY_LABELS: dict[str, str] = {
    "en": "Image",
    "zh-Hans": "图片",
    "zh-Hant": "圖片",
}

CHAT_IMAGE_TOO_LARGE_LABELS: dict[str, str] = {
    "en": "Image must be 4 MB or smaller.",
    "zh-Hans": "图片不能超过 4 MB。",
    "zh-Hant": "圖片不能超過 4 MB。",
}

CHAT_IMAGE_UNSUPPORTED_LABELS: dict[str, str] = {
    "en": "Please choose a PNG, JPEG, GIF, or WebP image.",
    "zh-Hans": "请选择 PNG、JPEG、GIF 或 WebP 图片。",
    "zh-Hant": "請選擇 PNG、JPEG、GIF 或 WebP 圖片。",
}

CHAT_MAX_IMAGE_BYTES: int = 4 * 1024 * 1024

