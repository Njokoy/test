import os
import logging
import tempfile
import asyncio
import random
import json
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
user_languages = {}
download_queue = {}
user_messages = {}

# Translation dictionary
TRANSLATIONS = {
    'fr': {
        'welcome': "🎵 Bienvenue sur MusicBot, ton compagnon musical ! 🎉\n\n"
                 "1️⃣ Envoie le nom d'un artiste ou d'une chanson (ex. : 'Tayc N'y pense plus').\n"
                 "2️⃣ Choisis une vidéo dans les résultats.\n"
                 "3️⃣ Ajoute à la file d'attente pour télécharger en MP3 avec métadonnées !\n\n"
                 "💡 Astuce : Sois précis dans ta recherche pour de meilleurs résultats !\n"
                 "Utilise /end pour terminer la session et nettoyer la conversation.",
        'help': "🎵 Aide MusicBot 🎵\n\n"
                "Je suis là pour t'aider à trouver et télécharger de la musique depuis YouTube ! Voici comment :\n"
                "- /start : Lance le bot et découvre comment l'utiliser.\n"
                "- /lang : Choisis ta langue.\n"
                "- /end : Termine la session et nettoie la conversation.\n"
                "- Envoie un nom d'artiste ou une chanson (ex. : 'Wizkid Essence').\n"
                "- Choisis une vidéo dans les résultats avec les boutons.\n"
                "- Les chansons sont ajoutées à la file d'attente et téléchargées séquentiellement.\n\n"
                "💡 Astuce : Utilise 'artiste - titre' pour des recherches précises.",
        'searching': "🔍 Analyse '{query}' en cours...",
        'no_results': "😕 Aucun résultat trouvé. \n Essaye 'artiste - titre' 🎧 !",
        'search_error': "❌ Problème lors de la recherche. Réessaie !",
        'results': "🎵 Résultats pour : \"{query}\"\nPage {page} - Voici pour toi, {user} !",
        'session_expired': "😴 Session expirée. Relance une recherche !",
        'platform_unsupported': "❌ Plateforme non reconnue.",
        'link_unsupported': "❌ Ce lien n'est pas pris en charge.",
        'downloading': "📥 Téléchargement audio en cours : {title}...",
        'download_failed': "❌ Échec du téléchargement pour {title}. Réessaie.",
        'send_error': "❌ Problème lors de l'envoi de {title}.",
        'added_to_queue': "✅ {title} ajouté à la file d'attente !",
        'queue_empty': "🎉 Tous les téléchargements sont terminés ! Envoie une nouvelle recherche ou un lien.",
        'cancel_search': "Recherche annulée. Relance une nouvelle recherche !",
        'session_ended': "✅ Session terminée. Tous les messages temporaires ont été supprimés.",
        'lang_prompt': "🌐 Choisis ta langue / Choose your language / 选择你的语言 / Выберите язык / Elige tu idioma:",
        'lang_selected': "✅ Langue sélectionnée : {lang}",
        'lang_invalid': "❌ Langue non valide. Choisis parmi : fr (Français), en (English), zh (Mandarin), ru (Русский), es (Español)"
    },
    'en': {
        'welcome': "🎵 Welcome to MusicBot, your musical companion! 🎉\n\n"
                 "1️⃣ Send an artist or song name (e.g., 'Tayc N'y pense plus').\n"
                 "2️⃣ Choose a video from the results.\n"
                 "3️⃣ Add to the queue to download as MP3 with metadata!\n\n"
                 "💡 Tip: Be specific with your search for better results!\n"
                 "Use /end to end the session and clean the chat.",
        'help': "🎵 MusicBot Help 🎵\n\n"
                "I'm here to help you find and download music from YouTube! Here's how:\n"
                "- /start: Start the bot and learn how to use it.\n"
                "- /lang: Choose your language.\n"
                "- /end: End the session and clean the chat.\n"
                "- Send an artist or song name (e.g., 'Wizkid Essence').\n"
                "- Choose a video from the results using the buttons.\n"
                "- Songs are added to the queue and downloaded sequentially.\n\n"
                "💡 Tip: Use 'artist - title' for precise searches.",
        'searching': "🔍 Searching for '{query}'...",
        'no_results': "😕 No results found. \n Try 'artist - title' 🎧!",
        'search_error': "❌ Issue during search. Try again!",
        'results': "🎵 Results for: \"{query}\"\nPage {page} - Here you go, {user}!",
        'session_expired': "😴 Session expired. Start a new search!",
        'platform_unsupported': "❌ Unrecognized platform.",
        'link_unsupported': "❌ This link is not supported.",
        'downloading': "📥 Downloading audio: {title}...",
        'download_failed': "❌ Download failed for {title}. Try again.",
        'send_error': "❌ Issue sending {title}.",
        'added_to_queue': "✅ {title} added to the queue!",
        'queue_empty': "🎉 All downloads completed! Send a new search or link.",
        'cancel_search': "Search canceled. Start a new search!",
        'session_ended': "✅ Session ended. All temporary messages have been deleted.",
        'lang_prompt': "🌐 Choisis ta langue / Choose your language / 选择你的语言 / Выберите язык / Elige tu idioma:",
        'lang_selected': "✅ Language selected: {lang}",
        'lang_invalid': "❌ Invalid language. Choose from: fr (Français), en (English), zh (Mandarin), ru (Русский), es (Español)"
    },
    'zh': {
        'welcome': "🎵 欢迎使用 MusicBot，你的音乐伙伴！🎉\n\n"
                 "1️⃣ 发送歌手或歌曲名称（例如：“Tayc N'y pense plus”）。\n"
                 "2️⃣ 从结果中选择一个视频。\n"
                 "3️⃣ 添加到队列以下载带有元数据的MP3！\n\n"
                 "💡 提示：搜索时尽量具体以获得更好的结果！\n"
                 "使用 /end 结束会话并清理聊天。",
        'help': "🎵 MusicBot 帮助 🎵\n\n"
                "我可以帮助你从 YouTube 查找和下载音乐！操作方法如下：\n"
                "- /start：启动机器人并了解如何使用。\n"
                "- /lang：选择你的语言。\n"
                "- /end：结束会话并清理聊天。\n"
                "- 发送歌手或歌曲名称（例如：“Wizkid Essence”）。\n"
                "- 使用按钮从结果中选择一个视频。\n"
                "- 歌曲将添加到队列并按顺序下载。\n\n"
                "💡 提示：使用“歌手 - 标题”进行精确搜索。",
        'searching': "🔍 正在搜索 '{query}'...",
        'no_results': "😕 未找到结果。\n 尝试“歌手 - 标题” 🎧！",
        'search_error': "❌ 搜索时出现问题。请重试！",
        'results': "🎵 搜索结果：“{query}”\n第 {page} 页 - 给你，{user}！",
        'session_expired': "😴 会话已过期。请重新开始搜索！",
        'platform_unsupported': "❌ 不支持的平台。",
        'link_unsupported': "❌ 不支持此链接。",
        'downloading': "📥 正在下载音频：{title}...",
        'download_failed': "❌ {title} 下载失败。请重试。",
        'send_error': "❌ 发送 {title} 时出现问题。",
        'added_to_queue': "✅ {title} 已添加到队列！",
        'queue_empty': "🎉 所有下载已完成！发送新的搜索或链接。",
        'cancel_search': "搜索已取消。开始新的搜索！",
        'session_ended': "✅ 会话已结束。所有临时消息已被删除。",
        'lang_prompt': "🌐 Choisis ta langue / Choose your language / 选择你的语言 / Выберите язык / Elige tu idioma:",
        'lang_selected': "✅ 已选择语言：{lang}",
        'lang_invalid': "❌ 无效语言。请从以下选项中选择：fr (Français), en (English), zh (Mandarin), ru (Русский), es (Español)"
    },
    'ru': {
        'welcome': "🎵 Добро пожаловать в MusicBot, ваш музыкальный помощник! 🎉\n\n"
                 "1️⃣ Отправьте имя исполнителя или песни (например, 'Tayc N'y pense plus').\n"
                 "2️⃣ Выберите видео из результатов.\n"
                 "3️⃣ Добавьте в очередь для скачивания в формате MP3 с метаданными!\n\n"
                 "💡 Совет: Будьте точны в поиске для лучших результатов!\n"
                 "Используйте /end для завершения сессии и очистки чата.",
        'help': "🎵 Помощь по MusicBot 🎵\n\n"
                "Я здесь, чтобы помочь вам находить и скачивать музыку с YouTube! Вот как это работает:\n"
                "- /start: Запустите бот и узнайте, как им пользоваться.\n"
                "- /lang: Выберите язык.\n"
                "- /end: Завершите сессию и очистите чат.\n"
                "- Отправьте имя исполнителя или песни (например, 'Wizkid Essence').\n"
                "- Выберите видео из результатов с помощью кнопок.\n"
                "- Песни добавляются в очередь и скачиваются последовательно.\n\n"
                "💡 Совет: Используйте формат 'исполнитель - название' для точного поиска.",
        'searching': "🔍 Поиск '{query}'...",
        'no_results': "😕 Результатов не найдено. \n Попробуйте 'исполнитель - название' 🎧!",
        'search_error': "❌ Проблема при поиске. Попробуйте снова!",
        'results': "🎵 Результаты для: \"{query}\"\nСтраница {page} - Вот, {user}!",
        'session_expired': "😴 Сессия истекла. Начните новый поиск!",
        'platform_unsupported': "❌ Нераспознанная платформа.",
        'link_unsupported': "❌ Эта ссылка не поддерживается.",
        'downloading': "📥 Загрузка аудио: {title}...",
        'download_failed': "❌ Не удалось скачать {title}. Попробуйте снова.",
        'send_error': "❌ Проблема при отправке {title}.",
        'added_to_queue': "✅ {title} добавлено в очередь!",
        'queue_empty': "🎉 Все загрузки завершены! Отправьте новый поиск или ссылку.",
        'cancel_search': "Поиск отменен. Начните новый поиск!",
        'session_ended': "✅ Сессия завершена. Все временные сообщения удалены.",
        'lang_prompt': "🌐 Choisis ta langue / Choose your language / 选择你的语言 / Выберите язык / Elige tu idioma:",
        'lang_selected': "✅ Язык выбран: {lang}",
        'lang_invalid': "❌ Недопустимый язык. Выберите из: fr (Français), en (English), zh (Mandarin), ru (Русский), es (Español)"
    },
    'es': {
        'welcome': "🎵 ¡Bienvenido a MusicBot, tu compañero musical! 🎉\n\n"
                 "1️⃣ Envía el nombre de un artista o canción (ej. 'Tayc N'y pense plus').\n"
                 "2️⃣ Elige un video de los resultados.\n"
                 "3️⃣ ¡Añade a la cola para descargar en MP3 con metadatos!\n\n"
                 "💡 Consejo: Sé específico en tu búsqueda para mejores resultados.\n"
                 "Usa /end para finalizar la sesión y limpiar el chat.",
        'help': "🎵 Ayuda de MusicBot 🎵\n\n"
                "¡Estoy aquí para ayudarte a encontrar y descargar música de YouTube! Así funciona:\n"
                "- /start: Inicia el bot y descubre cómo usarlo.\n"
                "- /lang: Elige tu idioma.\n"
                "- /end: Finaliza la sesión y limpia el chat.\n"
                "- Envía el nombre de un artista o canción (ej. 'Wizkid Essence').\n"
                "- Elige un video de los resultados con los botones.\n"
                "- Las canciones se añaden a la cola y se descargan secuencialmente.\n\n"
                "💡 Consejo: Usa 'artista - título' para búsquedas precisas.",
        'searching': "🔍 Buscando '{query}'...",
        'no_results': "😕 No se encontraron resultados. \n ¡Prueba 'artista - título' 🎧!",
        'search_error': "❌ Problema durante la búsqueda. ¡Intenta de nuevo!",
        'results': "🎵 Resultados para: \"{query}\"\nPágina {page} - ¡Aquí tienes, {user}!",
        'session_expired': "😴 Sesión expirada. ¡Inicia una nueva búsqueda!",
        'platform_unsupported': "❌ Plataforma no reconocida.",
        'link_unsupported': "❌ Este enlace no es compatible.",
        'downloading': "📥 Descargando audio: {title}...",
        'download_failed': "❌ Falló la descarga de {title}. Intenta de nuevo.",
        'send_error': "❌ Problema al enviar {title}.",
        'added_to_queue': "✅ ¡{title} añadido a la cola!",
        'queue_empty': "🎉 ¡Todas las descargas completadas! Envía una nueva búsqueda o enlace.",
        'cancel_search': "Búsqueda cancelada. ¡Inicia una nueva búsqueda!",
        'session_ended': "✅ Sesión finalizada. Todos los mensajes temporales han sido eliminados.",
        'lang_prompt': "🌐 Choisis ta langue / Choose your language / 选择你的语言 / Выберите язык / Elige tu idioma:",
        'lang_selected': "✅ Idioma seleccionado: {lang}",
        'lang_invalid': "❌ Idioma no válido. Elige entre: fr (Français), en (English), zh (Mandarin), ru (Русский), es (Español)"
    }
}

# Get user's language or default to French
def get_user_language(user_id):
    return user_languages.get(user_id, 'fr')

# Track message for cleanup
async def track_message(context, chat_id, message):
    if chat_id not in user_messages:
        user_messages[chat_id] = []
    user_messages[chat_id].append(message.message_id)

# Send temporary message
async def send_temporary_message(context, chat_id, text_key, delay=5, **kwargs):
    lang = get_user_language(context._user_id)
    text = TRANSLATIONS[lang][text_key].format(**kwargs) if kwargs else TRANSLATIONS[lang][text_key]
    try:
        message = await context.bot.send_message(chat_id=chat_id, text=text)
        await track_message(context, chat_id, message)
        await asyncio.sleep(delay)
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
            user_messages[chat_id].remove(message.message_id)
        except:
            pass
    except Exception as e:
        logger.error(f"Failed to send temporary message: {e}")

# Commande /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    logger.info(f"User {user_id} started the bot.")
    lang = get_user_language(user_id)
    message = await update.message.reply_text(TRANSLATIONS[lang]['welcome'])
    await track_message(context, chat_id, message)

# Commande /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    logger.info(f"User {user_id} requested help.")
    lang = get_user_language(user_id)
    await send_temporary_message(context, chat_id, 'help', delay=20)

# Commande /lang
async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
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
    await track_message(context, chat_id, message)

# Commande /end
async def end_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    lang = get_user_language(user_id)
    logger.info(f"User {user_id} ended the session.")

    # Clear user data
    user_searches.pop(user_id, None)
    download_queue.pop(user_id, None)

    # Delete tracked messages
    if chat_id in user_messages:
        for message_id in user_messages[chat_id][:]:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                pass
        user_messages.pop(chat_id, None)

    message = await update.message.reply_text(TRANSLATIONS[lang]['session_ended'])
    await track_message(context, chat_id, message)

# Gestion des redirections
def resolve_redirect(url):
    try:
        with httpx.Client(follow_redirects=True, timeout=10.0) as client:
            response = client.get(url)
            return str(response.url)
    except Exception as e:
        logger.error(f"Redirect resolution error: {e}")
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

# Stockage recherches utilisateurs
user_searches = {}
RESULTS_PER_PAGE = 5

# Recherche YouTube
async def search_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    logger.info(f"Search or link received: \"{query}\" by user {user_id}")
    lang = get_user_language(user_id)

    # Si lien détecté
    if re.search(PLATFORM_REGEX, query):
        resolved_url = resolve_redirect(query)
        platform = detect_platform(resolved_url)

        if platform in ["youtube", "tiktok", "facebook", "instagram", "likee"]:
            if user_id not in download_queue:
                download_queue[user_id] = []
            download_queue[user_id].append({'url': resolved_url, 'title': query, 'platform': platform})
            message = await update.message.reply_text(TRANSLATIONS[lang]['added_to_queue'].format(title=query))
            await track_message(context, chat_id, message)
            asyncio.create_task(process_download_queue(context, user_id, chat_id))
        else:
            await send_temporary_message(context, chat_id, 'platform_unsupported')
        return

    # Recherche YouTube classique
    message = await update.message.reply_text(TRANSLATIONS[lang]['searching'].format(query=query))
    await track_message(context, chat_id, message)

    try:
        search_response = youtube.search().list(
            q=query, part='snippet', maxResults=50, type='video'
        ).execute()

        videos = search_response.get('items', [])
        if not videos:
            await send_temporary_message(context, chat_id, 'no_results', delay=10)
            return

        user_searches[user_id] = {
            'query': query,
            'results': videos,
            'page': 0
        }

        await send_results_page(update, context, user_id)

    except Exception as e:
        logger.error(f"YouTube search error: {e}")
        await send_temporary_message(context, chat_id, 'search_error')

# Affichage résultats paginés
async def send_results_page(update_or_query, context, user_id):
    search_data = user_searches.get(user_id)
    if not search_data:
        lang = get_user_language(user_id)
        message = await update_or_query.message.reply_text(TRANSLATIONS[lang]['session_expired'])
        await track_message(context, update_or_query.message.chat.id, message)
        return

    page = search_data['page']
    results = search_data['results']
    chat_id = update_or_query.effective_chat.id if hasattr(update_or_query, "effective_chat") else update_or_query.message.chat.id

    if not results:
        lang = get_user_language(user_id)
        message = await update_or_query.message.reply_text(TRANSLATIONS[lang]['no_results'])
        await track_message(context, chat_id, message)
        return

    start_idx = page * RESULTS_PER_PAGE
    end_idx = min(start_idx + RESULTS_PER_PAGE, len(results))
    page_results = results[start_idx:end_idx]

    keyboard = []
    for idx, video in enumerate(page_results, start=start_idx + 1):
        title = video['snippet']['title']
        video_id = video['id']['videoId']
        short_title = (title[:60] + "...") if len(title) > 60 else title
        keyboard.append([
            InlineKeyboardButton(f"{idx}. {short_title}", callback_data=f"video_{video_id}"),
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
    lang = get_user_language(user_id)
    text = TRANSLATIONS[lang]['results'].format(query=search_data['query'], page=page + 1, user=user_name)

    try:
        if 'message_id' not in search_data:
            sent_msg = await update_or_query.message.reply_text(text, reply_markup=reply_markup)
            user_searches[user_id]['message_id'] = sent_msg.message_id
            await track_message(context, chat_id, sent_msg)
        else:
            message_id = search_data['message_id']
            try:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
            except Exception as e:
                logger.warning(f"Failed to edit message {message_id}: {e}")
                sent_msg = await update_or_query.message.reply_text(text, reply_markup=reply_markup)
                user_searches[user_id]['message_id'] = sent_msg.message_id
                await track_message(context, chat_id, sent_msg)
    except Exception as e:
        logger.error(f"Failed to send results page: {e}, Response: {getattr(e, 'response', 'No response')}")
        await send_temporary_message(context, chat_id, 'search_error')

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
            logger.warning(f"No metadata added: {e}")

        return filepath, meta

    except Exception as e:
        logger.error(f"yt-dlp download error: {e}")
        return None, None

def is_supported_media_url(url):
    supported_domains = [
        "youtube.com", "youtu.be", "tiktok.com", "instagram.com", "facebook.com",
        "soundcloud.com", "likee.video", "twitter.com", "x.com"
    ]
    return any(domain in url for domain in supported_domains)

async def process_download_queue(context, user_id, chat_id):
    if user_id not in download_queue or not download_queue[user_id]:
        return

    lang = get_user_language(user_id)
    while download_queue[user_id]:
        item = download_queue[user_id][0]
        url = item['url']
        title = item['title']
        platform = item['platform']

        if not is_supported_media_url(url):
            await send_temporary_message(context, chat_id, 'link_unsupported')
            download_queue[user_id].pop(0)
            continue

        message = await context.bot.send_message(chat_id=chat_id, text=TRANSLATIONS[lang]['downloading'].format(title=title))
        await track_message(context, chat_id, message)

        temp_dir = tempfile.gettempdir()
        loop = asyncio.get_running_loop()
        filepath, meta = await loop.run_in_executor(None, lambda: download_audio_from_url(url, temp_dir))

        if filepath and os.path.exists(filepath):
            try:
                with open(filepath, 'rb') as audio:
                    await context.bot.send_audio(chat_id=chat_id, audio=audio, title=f"{meta['titre']}.mp3")
            except Exception as e:
                logger.error(f"Audio send error: {e}")
                await send_temporary_message(context, chat_id, 'send_error', title=meta['titre'], delay=10)
            finally:
                os.remove(filepath)
        else:
            await send_temporary_message(context, chat_id, 'download_failed', title=title)

        download_queue[user_id].pop(0)

    # Notify when queue is empty
    message = await context.bot.send_message(chat_id=chat_id, text=TRANSLATIONS[lang]['queue_empty'])
    await track_message(context, chat_id, message)

# Bouton gestion
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    await query.answer()
    data = query.data
    lang = get_user_language(user_id)

    if data in ("page_prev", "page_next"):
        if user_id not in user_searches:
            await query.edit_message_text(TRANSLATIONS[lang]['session_expired'])
            return

        if data == "page_prev":
            user_searches[user_id]['page'] -= 1
        elif data == "page_next":
            user_searches[user_id]['page'] += 1

        await send_results_page(query, context, user_id)
        return

    if data == "cancel_search":
        user_searches.pop(user_id, None)
        download_queue.pop(user_id, None)
        message = await query.message.reply_text(TRANSLATIONS[lang]['cancel_search'])
        await track_message(context, chat_id, message)
        return

    if data.startswith("video_"):
        video_id = data[len("video_"):]
        url = f'https://www.youtube.com/watch?v={video_id}'
        title = next((v['snippet']['title'] for v in user_searches[user_id]['results'] if v['id']['videoId'] == video_id), "Unknown")
        if user_id not in download_queue:
            download_queue[user_id] = []
        download_queue[user_id].append({'url': url, 'title': title, 'platform': 'youtube'})
        message = await query.message.reply_text(TRANSLATIONS[lang]['added_to_queue'].format(title=title))
        await track_message(context, chat_id, message)
        asyncio.create_task(process_download_queue(context, user_id, chat_id))
        return

    if data.startswith("lang_"):
        lang_code = data[len("lang_"):]
        if lang_code in LANGUAGES:
            user_languages[user_id] = lang_code
            lang_name = {'fr': 'Français', 'en': 'English', 'zh': 'Mandarin', 'ru': 'Русский', 'es': 'Español'}[lang_code]
            await query.edit_message_text(TRANSLATIONS[lang_code]['lang_selected'].format(lang=lang_name))
        else:
            await query.edit_message_text(TRANSLATIONS[lang]['lang_invalid'])

# Extraction intelligente des métadonnées
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

# Lancement
def main():
    request = HTTPXRequest(connect_timeout=60, read_timeout=60, write_timeout=60, pool_timeout=60)
    app = ApplicationBuilder().token(BOT_TOKEN).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("lang", set_language))
    app.add_handler(CommandHandler("end", end_session))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_music))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("✅ MusicBot ready.")
    app.run_polling()

if __name__ == '__main__':
    main()