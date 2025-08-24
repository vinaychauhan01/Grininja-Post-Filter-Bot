import asyncio
import re
import requests
from fuzzywuzzy import fuzz
from info import *
from utils import *
from time import time 
from client import User
from pyrogram import Client, filters 
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton 

async def search_anilist(query):
    """
    Search AniList API for anime titles and return the closest match.
    """
    url = "https://graphql.anilist.co"
    graphql_query = """
    query ($search: String) {
        Page(page: 1, perPage: 10) {
            media(search: $search, type: ANIME) {
                title {
                    romaji
                    english
                    native
                }
            }
        }
    }
    """
    variables = {"search": query}
    try:
        response = requests.post(url, json={"query": graphql_query, "variables": variables}, timeout=5)
        response.raise_for_status()
        data = response.json()
        titles = []
        for media in data.get("data", {}).get("Page", {}).get("media", []):
            titles.extend([
                media["title"]["romaji"],
                media["title"]["english"],
                media["title"]["native"]
            ])
        titles = [t for t in titles if t]  # Remove None values
        if not titles:
            return query  # Return original query if no results
        # Find the best match using fuzzywuzzy
        best_match = max(titles, key=lambda t: fuzz.ratio(t.lower(), query.lower()), default=query)
        return best_match if fuzz.ratio(best_match.lower(), query.lower()) > 70 else query
    except Exception as e:
        print(f"AniList API error: {e}")
        return query  # Fallback to original query on error

@Client.on_message(filters.text & filters.group & filters.incoming & ~filters.command(["verify", "connect", "id"]))
async def search(bot, message):
    # Check if user is subscribed to required channels
    f_sub = await force_sub(bot, message)
    if f_sub == False:
        return     
    channels = (await get_group(message.chat.id))["channels"]
    if not channels:
        return     

    # Skip if message is a command
    if message.text.startswith("/"):
        return    

    query = message.text.strip()
    
    # Filter for potential titles: short phrases, capitalized words, or specific patterns
    # Skip casual conversation (e.g., questions, long sentences)
    if not is_potential_title(query):
        return

    # Auto-correct the query using AniList API
    corrected_query = await search_anilist(query)
    head = "<u>Here is the results 👇\n\n"
    results = ""
    try:
        # First search with corrected query
        for channel in channels:
            async for msg in User.search_messages(chat_id=channel, query=corrected_query):
                name = (msg.text or msg.caption).split("\n")[0]
                if name in results:
                    continue 
                results += f"<b><I>♻️ {name}\n🔗 {msg.link}</I></b>\n\n"

        # If no results with corrected query, try original query
        if not results:
            for channel in channels:
                async for msg in User.search_messages(chat_id=channel, query=query):
                    name = (msg.text or msg.caption).split("\n")[0]
                    if name in results:
                        continue 
                    results += f"<b><I>♻️ {name}\n🔗 {msg.link}</I></b>\n\n"

        if not results:
            # Directly offer admin request
            msg = await message.reply_text(
                f"<b><I>No results found for '{query}' or its correction '{corrected_query}'.\nRequest this title from the admin?</I></b>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎯 Request To Admin 🎯", callback_data=f"request_{corrected_query}")]])
            )
        else:
            msg = await message.reply_text(text=head + results, disable_web_page_preview=True)
        _time = int(time()) + (15 * 60)
        await save_dlt_message(msg, _time)
    except Exception as e:
        print(f"Error in search: {e}")
        pass

def is_potential_title(query):
    """
    Determine if the query is likely a movie/anime title.
    Returns True for short phrases, capitalized words, or specific patterns.
    Returns False for questions, long sentences, or casual conversation.
    """
    query = query.strip()
    query_lower = query.lower()

    # Skip empty queries
    if not query:
        return False

    # Skip long messages (likely casual conversation)
    if len(query.split()) > 5:
        return False

    # Skip common question patterns or casual phrases
    question_keywords = ["kya", "kaise", "konsi", "kon", "what", "how", "which", "who", "hai", "h", "koi"]
    if any(keyword in query_lower for keyword in question_keywords):
        return False

    # Check for title-like patterns: capitalized words or short phrases
    title_pattern = re.compile(r'^([A-Z][a-z]*\s*)+$')
    if title_pattern.match(query) or len(query.split()) <= 3:
        return True

    return False

@Client.on_callback_query(filters.regex(r"^recheck"))
async def recheck(bot, update):
    clicked = update.from_user.id
    try:      
        typed = update.message.reply_to_message.from_user.id
    except:
        return await update.message.delete(2)       
    if clicked != typed:
        return await update.answer("That's not for you! 👀", show_alert=True)

    m = await update.message.edit("Searching..💥")
    query = update.data.split("_")[-1]  # Use callback data as query
    channels = (await get_group(update.message.chat.id))["channels"]
    head = "<u>Search Results 👇\n\n"
    results = ""
    try:
        # Search with corrected query from AniList
        corrected_query = await search_anilist(query)
        for channel in channels:
            async for msg in User.search_messages(chat_id=channel, query=corrected_query):
                name = (msg.text or msg.caption).split("\n")[0]
                if name in results:
                    continue 
                results += f"<b><I>♻️🍿 {name}</I></b>\n\n🔗 {msg.link}</I></b>\n\n"
        if not results:          
            return await update.message.edit(
                f"<b><I>No results found for '{corrected_query}'.\nRequest this title from the admin?</I></b>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎯 Request To Admin 🎯", callback_data=f"request_{corrected_query}")]])
            )
        await update.message.edit(text=head + results, disable_web_page_preview=True)
    except Exception as e:
        await update.message.edit(f"❌ Error: `{e}`")

@Client.on_callback_query(filters.regex(r"^request"))
async def request(bot, update):
    clicked = update.from_user.id
    try:      
        typed = update.message.reply_to_message.from_user.id
    except:
        return await update.message.delete()       
    if clicked != typed:
        return await update.answer("That's not for you! 👀", show_alert=True)

    admin = (await get_group(update.message.chat.id))["user_id"]
    name = update.data.split("_")[1]
    text = f"#RequestFromYourGroup\n\nName: {name}"
    await bot.send_message(chat_id=admin, text=text, disable_web_page_preview=True)
    await update.answer("✅ Request Sent To Admin", show_alert=True)
    await update.message.delete(60)
