import os
import logging
import tempfile
import asyncio
import random
from telegram.request import HTTPXRequest
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
)
from googleapiclient.discovery import build
import yt_dlp
from dotenv import load_dotenv
from mutagen.easyid3 import EasyID3
import re
import httpx

# Define the cookie file path
COOKIE_FILE = os.path.join(os.getcwd(), 'cookies.txt')

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

# Logger config
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# YouTube API client
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

PLATFORM_REGEX = re.compile(
    r"(https?:\/\/)?(www\.)?"
    r"("
    r"(youtube\.com|youtu\.be)"
    r"|tiktok\.com"
    r"|instagram\.com"
    r"|facebook\.com"
    r"|fb\.watch"
    r"|likee\.video"
    r")"
    r"(/[^\s]*)?",
    re.IGNORECASE
)

# Language support
LANGUAGES = ['fr', 'en', 'zh', 'ru', 'es']
user_languages = {}  # Store user language preferences
user_searches = {}  # Store search results and pagination
user_queues = {}    # Store download queues
user_messages = {}  # Store message IDs for cleanup

# Translation dictionary
TRANSLATIONS = {
    'fr': {
        'welcome': "🎵 Bienvenue sur MusicBot, ton compagnon musical ! 🎉\n\n"
                 "1️⃣ Envoie le nom d'un artiste ou d'une chanson (ex. : 'Tayc N'y pense plus').\n"
                 "2️⃣ Choisis une vidéo dans les résultats.\n"
                 "3️⃣ Télécharge l'audio en MP3 avec des métadonnées !\n\n"
                 "💡 Astuce : Sois précis dans ta recherche pour de meilleurs résultats !",
        'help': "🎵 Aide MusicBot 🎵\n\n"
                "Je suis là pour t'aider à trouver et télécharger de la musique depuis YouTube ! Voici comment :\n"
                "- /start : Lance le bot et découvre comment l'utiliser.\n"
                "- /lang : Change la langue.\n"
                "- Envoie un nom d'artiste ou une chanson (ex. : 'Wizkid Essence').\n"
                "- Choisis une vidéo dans les résultats avec les boutons.\n"
                "- Les vidéos sélectionnées sont ajoutées à la file d'attente et téléchargées une par une.\n"
                "- Utilise /cancel pour arrêter la session et nettoyer la conversation.\n\n"
                "💡 Astuce : Utilise 'artiste - titre' pour des recherches précises.",
        'searching': "🔍 Analyse '{query}' en cours...",
        'no_results': "😕 Aucun résultat trouvé. \n Essaye 'artiste - titre' 🎧 !",
        'search_error': "❌ Problème lors de la recherche. Réessaie !",
        'results': "🎵 Résultats pour : \"{query}\"\nPage {page} - Voici pour toi, {user} !",
        'session_expired': "😴 Session expirée. Relance une recherche !",
        'platform_unsupported': "❌ Plateforme non reconnue.",
        'link_unsupported': "❌ Ce lien n'est pas pris en charge.",
        'downloading': "📥 Téléchargement audio en cours : {title}...",
        'download_failed': "❌ Échec du téléchargement pour {title}. Vérifie la vidéo ou réessaie.",
        'send_error': "❌ Problème lors de l'envoi du fichier audio pour {title}.",
        'download_success': "✅ Audio téléchargé : {title} !",
        'queue_empty': [
            "🎉 File d'attente terminée ! Envie d'une autre chanson ?",
            "🔥 Tous les téléchargements sont terminés ! Relance une recherche !",
            "🎧 File vide. Quelle chanson veux-tu ensuite ?"
        ],
        'cancel_search': "✅ Session terminée. Tous les messages ont été nettoyés. Relance une nouvelle recherche !",
        'lang_prompt': "🌐 Choisis ta langue / Choose your language / 选择你的语言 / Выберите язык / Elige tu idioma:",
        'lang_selected': "✅ Langue sélectionnée : {lang}",
        'lang_invalid': "❌ Langue non valide. Choisis parmi : fr (Français), en (English), zh (Mandarin), ru (Русский), es (Español)",
        'queue_added': "✅ Vidéo ajoutée à la file d'attente : {title}",
        'queue_status': "📋 File d'attente : {count} vidéo(s) en attente."
    },
    'en': {
        'welcome': "🎵 Welcome to MusicBot, your musical companion! 🎉\n\n"
                 "1️⃣ Send an artist or song name (e.g., 'Tayc N'y pense plus').\n"
                 "2️⃣ Choose a video from the results.\n"
                 "3️⃣ Download the audio as MP3 with metadata!\n\n"
                 "💡 Tip: Be specific with your search for better results!",
        'help': "🎵 MusicBot Help 🎵\n\n"
                "I'm here to help you find and download music from YouTube! Here's how:\n"
                "- /start: Start the bot and learn how to use it.\n"
                "- /lang: Change the language.\n"
                "- Send an artist or song name (e.g., 'Wizkid Essence').\n"
                "- Choose a video from the results using the buttons.\n"
                "- Selected videos are added to the queue and downloaded one by one.\n"
                "- Use /cancel to stop the session and clean up the chat.\n\n"
                "💡 Tip: Use 'artist - title' for precise searches.",
        'searching': "🔍 Searching for '{query}'...",
        'no_results': "😕 No results found. \n Try 'artist - title' 🎧!",
        'search_error': "❌ Issue during search. Try again!",
        'results': "🎵 Results for: \"{query}\"\nPage {page} - Here you go, {user}!",
        'session_expired': "😴 Session expired. Start a new search!",
        'platform_unsupported': "❌ Unrecognized platform.",
        'link_unsupported': "❌ This link is not supported.",
        'downloading': "📥 Downloading audio: {title}...",
        'download_failed': "❌ Download failed for {title}. Check the link or try again.",
        'send_error': "❌ Issue sending the audio file for {title}.",
        'download_success': "✅ Audio downloaded: {title}!",
        'queue_empty': [
            "🎉 Queue completed! Want another song?",
            "🔥 All downloads finished! Start a new search!",
            "🎧 Queue empty. What's the next song?"
        ],
        'cancel_search': "✅ Session ended. All messages have been cleaned. Start a new search!",
        'lang_prompt': "🌐 Choisis ta langue / Choose your language / 选择你的语言 / Выберите язык / Elige tu idioma:",
        'lang_selected': "✅ Language selected: {lang}",
        'lang_invalid': "❌ Invalid language. Choose from: fr (Français), en (English), zh (Mandarin), ru (Русский), es (Español)",
        'queue_added': "✅ Video added to queue: {title}",
        'queue_status': "📋 Queue: {count} video(s) pending."
    },
    'zh': {
        'welcome': "🎵 欢迎使用 MusicBot，你的音乐伙伴！🎉\n\n"
                 "1️⃣ 发送歌手或歌曲名称（例如：“Tayc N'y pense plus”）。\n"
                 "2️⃣ 从结果中选择一个视频。\n"
                 "3️⃣ 下载带有元数据的MP3音频！\n\n"
                 "💡 提示：搜索时尽量具体以获得更好的结果！",
        'help': "🎵 MusicBot 帮助 🎵\n\n"
                "我可以帮助你从 YouTube 查找和下载音乐！操作方法如下：\n"
                "- /start：启动机器人并了解如何使用。\n"
                "- /lang：更改语言。\n"
                "- 发送歌手或歌曲名称（例如：“Wizkid Essence”）。\n"
                "- 使用按钮从结果中选择一个视频。\n"
                "- 所选视频将添加到队列并逐一下载。\n"
                "- 使用 /cancel 停止会话并清理聊天。\n\n"
                "💡 提示：使用“歌手 - 标题”进行精确搜索。",
        'searching': "🔍 正在搜索 '{query}'...",
        'no_results': "😕 未找到结果。\n 尝试“歌手 - 标题” 🎧！",
        'search_error': "❌ 搜索时出现问题。请重试！",
        'results': "🎵 搜索结果：“{query}”\n第 {page} 页 - 给你，{user}！",
        'session_expired': "😴 会话已过期。请重新开始搜索！",
        'platform_unsupported': "❌ 不支持的平台。",
        'link_unsupported': "❌ 不支持此链接。",
        'downloading': "📥 正在下载音频：{title}...",
        'download_failed': "❌ 下载失败：{title}。请检查链接或重试。",
        'send_error': "❌ 发送音频文件时出现问题：{title}。",
        'download_success': "✅ 音频已下载：{title}！",
        'queue_empty': [
            "🎉 队列已完成！想要另一首歌吗？",
            "🔥 所有下载已完成！开始新的搜索！",
            "🎧 队列为空。下一首歌是什么？"
        ],
        'cancel_search': "✅ 会话已结束。所有消息已清理。开始新的搜索！",
        'lang_prompt': "🌐 Choisis ta langue / Choose your language / 选择你的语言 / Выберите язык / Elige tu idioma:",
        'lang_selected': "✅ 已选择语言：{lang}",
        'lang_invalid': "❌ 无效语言。请从以下选项中选择：fr (Français), en (English), zh (Mandarin), ru (Русский), es (Español)",
        'queue_added': "✅ 视频已添加到队列：{title}",
        'queue_status': "📋 队列：{count} 个视频待处理。"
    },
    'ru': {
        'welcome': "🎵 Добро пожаловать в MusicBot, ваш музыкальный помощник! 🎉\n\n"
                 "1️⃣ Отправьте имя исполнителя или песни (например, 'Tayc N'y pense plus').\n"
                 "2️⃣ Выберите видео из результатов.\n"
                 "3️⃣ Скачайте аудио в формате MP3 с метаданными!\n\n"
                 "💡 Совет: Будьте точны в поиске для лучших результатов!",
        'help': "🎵 Помощь по MusicBot 🎵\n\n"
                "Я здесь, чтобы помочь вам находить и скачивать музыку с YouTube! Вот как это работает:\n"
                "- /start: Запустите бот и узнайте, как им пользоваться.\n"
                "- /lang: Изменить язык.\n"
                "- Отправьте имя исполнителя или песни (например, 'Wizkid Essence').\n"
                "- Выберите видео из результатов с помощью кнопок.\n"
                "- Выбранные видео добавляются в очередь и скачиваются по очереди.\n"
                "- Используйте /cancel, чтобы остановить сессию и очистить чат.\n\n"
                "💡 Совет: Используйте формат 'исполнитель - название' для точного поиска.",
        'searching': "🔍 Поиск '{query}'...",
        'no_results': "😕 Результатов не найдено. \n Попробуйте 'исполнитель - название' 🎧!",
        'search_error': "❌ Проблема при поиске. Попробуйте снова!",
        'results': "🎵 Результаты для: \"{query}\"\nСтраница {page} - Вот, {user}!",
        'session_expired': "😴 Сессия истекла. Начните новый поиск!",
        'platform_unsupported': "❌ Нераспознанная платформа.",
        'link_unsupported': "❌ Эта ссылка не поддерживается.",
        'downloading': "📥 Загрузка аудио: {title}...",
        'download_failed': "❌ Не удалось скачать: {title}. Проверьте ссылку или попробуйте снова.",
        'send_error': "❌ Проблема при отправке аудиофайла: {title}.",
        'download_success': "✅ Аудио загружено: {title}!",
        'queue_empty': [
            "🎉 Очередь завершена! Хотите еще одну песню?",
            "🔥 Все загрузки завершены! Начните новый поиск!",
            "🎧 Очередь пуста. Какая следующая песня?"
        ],
        'cancel_search': "✅ Сессия завершена. Все сообщения очищены. Начните новый поиск!",
        'lang_prompt': "🌐 Choisis ta langue / Choose your language / 选择你的语言 / Выберите язык / Elige tu idioma:",
        'lang_selected': "✅ Язык выбран: {lang}",
        'lang_invalid': "❌ Недопустимый язык. Выберите из: fr (Français), en (English), zh (Mandarin), ru (Русский), es (Español)",
        'queue_added': "✅ Видео добавлено в очередь: {title}",
        'queue_status': "📋 Очередь: {count} видео в ожидании."
    },
    'es': {
        'welcome': "🎵 ¡Bienvenido a MusicBot, tu compañero musical! 🎉\n\n"
                 "1️⃣ Envía el nombre de un artista o canción (ej. 'Tayc N'y pense plus').\n"
                 "2️⃣ Elige un video de los resultados.\n"
                 "3️⃣ ¡Descarga el audio en MP3 con metadatos!\n\n"
                 "💡 Consejo: Sé específico en tu búsqueda para mejores resultados.",
        'help': "🎵 Ayuda de MusicBot 🎵\n\n"
                "¡Estoy aquí para ayudarte a encontrar y descargar música de YouTube! Así funciona:\n"
                "- /start: Inicia el bot y descubre cómo usarlo.\n"
                "- /lang: Cambiar el idioma.\n"
                "- Envía el nombre de un artista o canción (ej. 'Wizkid Essence').\n"
                "- Elige un video de los resultados con los botones.\n"
                "- Los videos seleccionados se añaden a la cola y se descargan uno por uno.\n"
                "- Usa /cancel para detener la sesión y limpiar el chat.\n\n"
                "💡 Consejo: Usa 'artista - título' para búsquedas precisas.",
        'searching': "🔍 Buscando '{query}'...",
        'no_results': "😕 No se encontraron resultados. \n ¡Prueba 'artista - título' 🎧!",
        'search_error': "❌ Problema durante la búsqueda. ¡Intenta de nuevo!",
        'results': "🎵 Resultados para: \"{query}\"\nPágina {page} - ¡Aquí tienes, {user}!",
        'session_expired': "😴 Sesión expirada. ¡Inicia una nueva búsqueda!",
        'platform_unsupported': "❌ Plataforma no reconocida.",
        'link_unsupported': "❌ Este enlace no es compatible.",
        'downloading': "📥 Descargando audio: {title}...",
        'download_failed': "❌ Falló la descarga para {title}. Verifica el enlace o intenta de nuevo.",
        'send_error': "❌ Problema al enviar el archivo de audio para {title}.",
        'download_success': "✅ ¡Audio descargado: {title}!",
        'queue_empty': [
            "🎉 ¡Cola completada! ¿Quieres otra canción?",
            "🔥 ¡Todas las descargas terminadas! ¡Inicia una nueva búsqueda!",
            "🎧 Cola vacía. ¿Cuál es la próxima canción?"
        ],
        'cancel_search': "✅ Sesión terminada. Todos los mensajes han sido limpiados. ¡Inicia una nueva búsqueda!",
        'lang_prompt': "🌐 Choisis ta langue / Choose your language / 选择你的语言 / Выберите язык / Elige tu idioma:",
        'lang_selected': "✅ Idioma seleccionado: {lang}",
        'lang_invalid': "❌ Idioma no válido. Elige entre: fr (Français), en (English), zh (Mandarin), ru (Русский), es (Español)",
        'queue_added': "✅ Video añadido a la cola: {title}",
        'queue_status': "📋 Cola: {count} video(s) pendientes."
    }
}

# Get user's language or default to French
def get_user_language(user_id):
    return user_languages.get(user_id, 'fr')

# Language selection command
async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    keyboard = [
        [
            InlineKeyboardButton("Français", callback_data="lang_fr"),
            InlineKeyboardButton("English", callback_data="lang_en"),
            InlineKeyboardButton("中文", callback_data="lang_zh"),
        ],
        [
            InlineKeyboardButton("Русский", callback_data="lang_ru"),
            InlineKeyboardButton("Español", callback_data="lang_es"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    lang = get_user_language(user_id)
    message = await update.message.reply_text(TRANSLATIONS[lang]['lang_prompt'], reply_markup=reply_markup)
    user_messages.setdefault(user_id, []).append((update.effective_chat.id, message.message_id))

# Cancel command to end session and clean up
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    chat_id = update.effective_chat.id

    # Clear session data
    user_searches.pop(user_id, None)
    user_queues.pop(user_id, None)

    # Delete all stored messages
    if user_id in user_messages:
        for chat_id, message_id in user_messages[user_id]:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                pass
        user_messages.pop(user_id, None)

    message = await update.message.reply_text(TRANSLATIONS[lang]['cancel_search'])
    user_messages.setdefault(user_id, []).append((chat_id, message.message_id))
    await asyncio.sleep(7)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
        user_messages[user_id].remove((chat_id, message.message_id))
        if not user_messages[user_id]:
            user_messages.pop(user_id, None)
    except:
        pass

# Gestion des redirections
def resolve_redirect(url):
    try:
        with httpx.Client(follow_redirects=True, timeout=10.0) as client:
            response = client.get(url)
            return str(response.url)
    except Exception as e:
        logger.error(f"Erreur de résolution du lien : {e}")
        return url

# Détection de l'URL
def detect_platform(url):
    url = url.lower()
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    elif "tiktok.com" in url:
        return "tiktok"
    elif "instagram.com" in url:
        return "instagram"
    elif "facebook.com" in url or "fb.watch" in url:
        return "facebook"
    elif "likee.video" in url:
        return "likee"
    else:
        return "unknown"

# Send temporary message
async def send_temporary_message(context, chat_id, text_key, user_id, delay=5, **kwargs):
    lang = get_user_language(user_id)
    text = TRANSLATIONS[lang][text_key].format(**kwargs) if kwargs else TRANSLATIONS[lang][text_key]
    message = await context.bot.send_message(chat_id=chat_id, text=text)
    user_messages.setdefault(user_id, []).append((chat_id, message.message_id))
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
        user_messages[user_id].remove((chat_id, message.message_id))
        if not user_messages[user_id]:
            user_messages.pop(user_id, None)
    except:
        pass

# Command /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"User {user_id} started the bot.")
    lang = get_user_language(user_id)
    message = await update.message.reply_text(TRANSLATIONS[lang]['welcome'])
    user_messages.setdefault(user_id, []).append((update.effective_chat.id, message.message_id))

# Command /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested help.")
    lang = get_user_language(user_id)
    await send_temporary_message(context, update.effective_chat.id, 'help', user_id, delay=20)

# Search YouTube
async def search_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    user_id = update.effective_user.id
    logger.info(f"Search or link received: \"{query}\" by user {user_id}")
    lang = get_user_language(user_id)
    chat_id = update.effective_chat.id

    # If link detected
    if re.search(PLATFORM_REGEX, query):
        resolved_url = resolve_redirect(query)
        platform = detect_platform(resolved_url)

        if platform in ["youtube", "tiktok", "facebook"]:
            user_queues.setdefault(user_id, []).append((resolved_url, None))
            await process_queue(context, update.message, user_id)
        elif platform in ["instagram", "likee"]:
            user_queues.setdefault(user_id, []).append((resolved_url, None))
            await process_queue(context, update.message, user_id)
        else:
            await send_temporary_message(context, chat_id, 'platform_unsupported', user_id)
        return

    # YouTube search
    message = await update.message.reply_text(TRANSLATIONS[lang]['searching'].format(query=query))
    user_messages.setdefault(user_id, []).append((chat_id, message.message_id))

    try:
        search_response = youtube.search().list(
            q=query, part='snippet', maxResults=50, type='video'
        ).execute()

        videos = search_response.get('items', [])
        if not videos:
            await send_temporary_message(context, chat_id, 'no_results', user_id, delay=10)
            return

        user_searches[user_id] = {
            'query': query,
            'results': videos,
            'page': 0,
            'message_id': None
        }

        await send_results_page(update, context, user_id)

    except Exception as e:
        logger.error(f"Erreur recherche YouTube : {e}")
        await send_temporary_message(context, chat_id, 'search_error', user_id)

# Display paginated results
async def send_results_page(update_or_query, context, user_id):
    search_data = user_searches.get(user_id)
    if not search_data:
        lang = get_user_language(user_id)
        message = await update_or_query.message.reply_text(TRANSLATIONS[lang]['session_expired'])
        user_messages.setdefault(user_id, []).append((update_or_query.message.chat.id, message.message_id))
        return

    page = search_data['page']
    results = search_data['results']
    chat_id = update_or_query.message.chat.id if hasattr(update_or_query, "message") else update_or_query.message.chat.id
    lang = get_user_language(user_id)

    start_idx = page * 5
    end_idx = start_idx + 5
    page_results = results[start_idx:end_idx]

    keyboard = []
    for idx, video in enumerate(page_results, start=start_idx + 1):
        title = video['snippet']['title']
        video_id = video['id']['videoId']
        short_title = (title[:60] + "...") if len(title) > 60 else title
        keyboard.append([
            InlineKeyboardButton(f"{idx}. {short_title}", callback_data=f"video_{video_id}_{title}")
        ])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data="page_prev"))
    nav_buttons.append(InlineKeyboardButton("❌", callback_data="cancel_search"))
    if end_idx < len(results):
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data="page_next"))

    keyboard.append(nav_buttons)
    reply_markup = InlineKeyboardMarkup(keyboard)
    user_name = update_or_query.effective_user.first_name if hasattr(update_or_query, "effective_user") else "Utilisateur"
    text = TRANSLATIONS[lang]['results'].format(query=search_data['query'], page=page + 1, user=user_name)

    if 'message_id' not in search_data or not search_data['message_id']:
        message = await update_or_query.message.reply_text(text, reply_markup=reply_markup)
        user_searches[user_id]['message_id'] = message.message_id
        user_messages.setdefault(user_id, []).append((chat_id, message.message_id))
    else:
        try:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=search_data['message_id'], text=text, reply_markup=reply_markup)
        except:
            message = await update_or_query.message.reply_text(text, reply_markup=reply_markup)
            user_searches[user_id]['message_id'] = message.message_id
            user_messages.setdefault(user_id, []).append((chat_id, message.message_id))

# Download audio
def download_audio_from_url(url, temp_dir):
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'noplaylist': True,
            'nooverwrites': True,
            'retries': 3,
            'sleep_interval': 2,
            'cookiefile': COOKIE_FILE
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'audio')
            filepath = os.path.splitext(ydl.prepare_filename(info))[0] + ".mp3"

        meta = extraire_metadonnees(info)
        try:
            audiofile = EasyID3(filepath)
            audiofile['title'] = meta['titre']
            audiofile['artist'] = meta['artiste']
            audiofile['genre'] = meta['genre']
            audiofile.save()
        except Exception as e:
            logger.warning(f"Pas de métadonnées ajoutées : {e}")

        return filepath, meta

    except Exception as e:
        logger.error(f"Erreur téléchargement yt-dlp : {e}")
        return None, None

def is_supported_media_url(url):
    supported_domains = [
        "youtube.com", "youtu.be", "tiktok.com", "instagram.com", "facebook.com",
        "soundcloud.com", "likee.video", "twitter.com", "x.com"
    ]
    return any(domain in url for domain in supported_domains)

# Process download queue
async def process_queue(context, message_or_query, user_id):
    chat_id = message_or_query.chat.id
    lang = get_user_language(user_id)

    while user_queues.get(user_id):
        url, title = user_queues[user_id][0]
        title_display = title if title else url

        message = await context.bot.send_message(chat_id=chat_id, text=TRANSLATIONS[lang]['downloading'].format(title=title_display))
        user_messages.setdefault(user_id, []).append((chat_id, message.message_id))

        temp_dir = tempfile.gettempdir()
        loop = asyncio.get_running_loop()
        filepath, meta = await loop.run_in_executor(None, lambda: download_audio_from_url(url, temp_dir))

        if filepath and os.path.exists(filepath):
            try:
                with open(filepath, 'rb') as audio:
                    await context.bot.send_audio(chat_id=chat_id, audio=audio, title=f"{meta['titre']}.mp3")
                success_message = await context.bot.send_message(chat_id=chat_id, text=TRANSLATIONS[lang]['download_success'].format(title=meta['titre']))
                user_messages.setdefault(user_id, []).append((chat_id, success_message.message_id))
                await asyncio.sleep(5)
                await context.bot.delete_message(chat_id=chat_id, message_id=success_message.message_id)
                user_messages[user_id].remove((chat_id, success_message.message_id))
            except Exception as e:
                logger.error(f"Erreur envoi audio : {e}")
                await send_temporary_message(context, chat_id, 'send_error', user_id, delay=10, title=meta['titre'])
            finally:
                os.remove(filepath)
        else:
            await send_temporary_message(context, chat_id, 'download_failed', user_id, delay=10, title=title_display)

        user_queues[user_id].pop(0)
        if user_queues.get(user_id):
            count = len(user_queues[user_id])
            status_message = await context.bot.send_message(chat_id=chat_id, text=TRANSLATIONS[lang]['queue_status'].format(count=count))
            user_messages.setdefault(user_id, []).append((chat_id, status_message.message_id))
            await asyncio.sleep(5)
            await context.bot.delete_message(chat_id=chat_id, message_id=status_message.message_id)
            user_messages[user_id].remove((chat_id, status_message.message_id))

        if not user_queues.get(user_id):
            messages = TRANSLATIONS[lang]['queue_empty']
            queue_message = await context.bot.send_message(chat_id=chat_id, text=random.choice(messages))
            user_messages.setdefault(user_id, []).append((chat_id, queue_message.message_id))

# Button handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    data = query.data
    lang = get_user_language(user_id)
    chat_id = query.message.chat.id

    if data in ("page_prev", "page_next"):
        if user_id not in user_searches:
            await query.edit_message_text(TRANSLATIONS[lang]['session_expired'])
            user_messages.setdefault(user_id, []).append((chat_id, query.message.message_id))
            return

        if data == "page_prev":
            user_searches[user_id]['page'] -= 1
        elif data == "page_next":
            user_searches[user_id]['page'] += 1

        await send_results_page(query, context, user_id)
        return

    if data == "cancel_search":
        # Clear session data
        user_searches.pop(user_id, None)
        user_queues.pop(user_id, None)

        # Delete all stored messages
        if user_id in user_messages:
            for chat_id, message_id in user_messages[user_id]:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
                except:
                    pass
            user_messages.pop(user_id, None)

        message = await query.message.reply_text(TRANSLATIONS[lang]['cancel_search'])
        user_messages.setdefault(user_id, []).append((chat_id, message.message_id))
        await asyncio.sleep(7)
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
            user_messages[user_id].remove((chat_id, message.message_id))
            if not user_messages[user_id]:
                user_messages.pop(user_id, None)
        except:
            pass
        return

    if data.startswith("video_"):
        video_id = data.split("_")[1]
        title = "_".join(data.split("_")[2:])
        url = f'https://www.youtube.com/watch?v={video_id}'
        user_queues.setdefault(user_id, []).append((url, title))
        message = await query.message.reply_text(TRANSLATIONS[lang]['queue_added'].format(title=title))
        user_messages.setdefault(user_id, []).append((chat_id, message.message_id))
        await asyncio.sleep(5)
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
            user_messages[user_id].remove((chat_id, message.message_id))
        except:
            pass
        if len(user_queues[user_id]) == 1:  # Start processing if this is the first item
            asyncio.create_task(process_queue(context, query.message, user_id))
        return

    if data.startswith("lang_"):
        lang_code = data[len("lang_"):]
        if lang_code in LANGUAGES:
            user_languages[user_id] = lang_code
            lang_name = {'fr': 'Français', 'en': 'English', 'zh': 'Mandarin', 'ru': 'Русский', 'es': 'Español'}[lang_code]
            await query.edit_message_text(TRANSLATIONS[lang_code]['lang_selected'].format(lang=lang_name))
            user_messages.setdefault(user_id, []).append((chat_id, query.message.message_id))
        else:
            await query.edit_message_text(TRANSLATIONS[lang]['lang_invalid'])
            user_messages.setdefault(user_id, []).append((chat_id, query.message.message_id))
        return

# Extract metadata
def extraire_metadonnees(info):
    title = info.get('title', '')
    uploader = info.get('uploader', '')
    tags = info.get('tags', [])
    description = info.get('description', '')

    artiste = uploader
    chanson = title
    if "-" in title:
        parts = title.split("-", 1)
        artiste = parts[0].strip()
        chanson = parts[1].split("(")[0].strip()

    genre = "Inconnu"
    genres_possibles = ['rap', 'afrobeats', 'pop', 'gospel', 'rock', 'rnb']
    for tag in tags or []:
        if tag.lower() in genres_possibles:
            genre = tag
            break

    featuring = "Non"
    for keyword in ['feat.', 'ft.', 'featuring']:
        if keyword.lower() in title.lower() or keyword.lower() in description.lower():
            featuring = "Oui"
            break

    return {
        'artiste': artiste,
        'titre': chanson,
        'genre': genre,
        'featuring': featuring
    }

# Main
def main():
    request = HTTPXRequest(connect_timeout=60, read_timeout=60, write_timeout=60, pool_timeout=60)
    app = ApplicationBuilder().token(BOT_TOKEN).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("lang", set_language))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_music))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("✅ MusicBot ready.")
    app.run_polling()

if __name__ == '__main__':
    main()