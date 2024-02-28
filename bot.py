import telebot
from telebot import types
from booru import resolve, Rule34, Danbooru, Gelbooru, Safebooru, Realbooru, Yandere, Lolibooru, Hypnohub
from urllib.parse import urlencode
import zipfile
import os
import io
import time
import asyncio

API_TOKEN = os.environ.get("BB_KEY")
bot = telebot.TeleBot(API_TOKEN)

def get_provider(booru_name):
    booru_name = booru_name.lower()
    if booru_name == "safebooru":
        provider = Safebooru()
    elif booru_name == "gelbooru":
        provider = Gelbooru()
    elif booru_name == "rule34":
        provider = Rule34()
    elif booru_name == "danbooru":
        provider = Danbooru()
    elif booru_name == "realbooru":
        provider = Realbooru()
    elif booru_name == "yandere":
        provider = Yandere()
    elif booru_name == "lolibooru":
        provider = Lolibooru()
    elif booru_name == "hypnohub":
        provider = Hyonohub()
    else:
        return None
    return provider

def download_images(booru_name, tags, count):
    images = []
    for page in range(count):
        resp = fetch_image_url(booru_name, tags, index=page, with_tags=True)
        images.append(resp)
    return images

def create_zip(images):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:
        for i, (image_url, tags) in enumerate(images, start=1):
            image_content = requests.get(image_url).content
            zip_file.writestr(f"{i}.png", image_content)
            zip_file.writestr(f"{i}.txt", tags)
    zip_buffer.seek(0)
    return zip_buffer

@bot.message_handler(commands=['zip'])
def send_zip(message):
    _, booru, tags, count = message.text.split(maxsplit=3)
    count = min(int(count), 100)
    tags = tags.replace("+", " ")
    images = download_images(booru, tags, count)
    
    if images:
        zip_buffer = create_zip(images)
        bot.send_document(message.chat.id, (f"images-{round(time.time())}.zip", zip_buffer), caption="Ваши изображения в ZIP-архиве.")
    else:
        bot.send_message(message.chat.id, "Изображения не найдены или произошла ошибка.")
        print(images)

def fetch_image_url(booru_name, tags, index=1, with_tags=False):
    provider = get_provider(booru_name)
    response = asyncio.run(provider.search(tags, limit=1, page=index))
    data = resolve(response)[0]
    if with_tags:
        return data["file_url"], " ".join(data["tags"])
    return data["file_url"]

@bot.message_handler(commands=["start"])
def start_cmd(message):
    msg = """
    Привет! Это бот для просмотра картинок на разных booru.

    Использование:
    /tags [booru] [теги]
    
    Доступные booru:
    - safebooru
    - gelbooru
    - rule34
    - danbooru
    - realbooru
    - yandere
    - lolibooru
    - hypnohub

    Теги пишутся в подобном стиле:
    1girl charlie_(brawl_stars) open_mouth
    """
    bot.send_message(message.chat.id, msg)

@bot.message_handler(commands=['tags'])
def send_image_by_tags(message):
    _, booru, tags = message.text.split(maxsplit=2)
    image_url = fetch_image_url(booru, tags)
    
    if image_url:
        markup = types.InlineKeyboardMarkup()
        next_button = types.InlineKeyboardButton("Следующая картинка", callback_data=f"next|{booru}|{tags}|1")
        markup.add(next_button)
        if not (image_url.endswith("mp4") or "video" in image_url):
            bot.send_photo(message.chat.id, image_url, reply_markup=markup)
        else:
            bot.send_video(message.chat.id, image_url, reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Картинка не найдена.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('next'))
def send_next_image(call):
    print(call.data.split("|"))
    _, booru, tags, index = call.data.split("|")
    index = int(index) + 1
    image_url = fetch_image_url(booru, tags, index)
    
    if image_url:
        markup = types.InlineKeyboardMarkup()
        next_button = types.InlineKeyboardButton("Следующая картинка", callback_data=f"next|{booru}|{tags}|{index}")
        markup.add(next_button)
        bot.edit_message_media(media=types.InputMediaPhoto(image_url),
                               chat_id=call.message.chat.id,
                               message_id=call.message.message_id,
                               reply_markup=markup)
    else:
        bot.answer_callback_query(call.id, "Больше картинок нет.")

if __name__ == '__main__':
    bot.infinity_polling()
