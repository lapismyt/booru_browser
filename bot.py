import telebot
from telebot import types
import requests
from urllib.parse import urlencode
import zipfile
import os
import io
import time

API_TOKEN = os.environ.get("BB_KEY")
bot = telebot.TeleBot(API_TOKEN)б

def download_images(booru, tags, count):
    images = []
    base_url = ""
    if booru == "safebooru":
        base_url = "https://safebooru.org/index.php"
    elif booru == "gelbooru":
        base_url = "https://gelbooru.com/index.php"
    elif booru == "rule34":
        base_url = "https://rule34.xxx/index.php"
    else:
        return None
    
    params = {
        "page": "dapi",
        "s": "post",
        "q": "index",
        "json": "1",
        "limit": count,
        "tags": tags
    }
    
    try:
        for x in range(1, count):
            image = fetch_image_url(booru, tags, index=x, with_tags=True)
            if image is None:
                print("noneimage")
                break
            images.append(image)
        return images
    except Exception as e:
        print(e)
        return None

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
    images = download_images(booru, tags, count)
    
    if images:
        zip_buffer = create_zip(images)
        bot.send_document(message.chat.id, (f"images-{round(time.time())}.zip", zip_buffer), caption="Ваши изображения в ZIP-архиве.")
    else:
        bot.send_message(message.chat.id, "Изображения не найдены или произошла ошибка.")
        print(images)

def fetch_image_url(booru, tags, index=1, with_tags=False):
    base_url = ""
    if booru == "safebooru":
        base_url = "https://safebooru.org/index.php"
    elif booru == "gelbooru":
        base_url = "https://gelbooru.com/index.php"
    elif booru == "rule34":
        base_url = "https://api.rule34.xxx/index.php"
    else:
        return None
    
    params = {
        "page": "dapi",
        "s": "post",
        "q": "index",
        "json": "1",
        "tags": tags,
        "limit": 1,
        "pid": index
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            print("nonedata")
            print(response.content)
            return None
        
        if booru == "safebooru":
            directory = data[0]["directory"]
            file = data[0]["image"]
            if with_tags:
                return f"https://safebooru.org/images/{directory}/{file}", data[0]["tags"]
            return f"https://safebooru.org/images/{directory}/{file}"
        elif booru == "gelbooru":
            if with_tags:
                return data["post"][0]["file_url"], data["post"][0]["tags"]
            return data["post"][0]["file_url"]
        elif booru == "rule34":
            if with_tags:
                return data[0]["file_url"], data[0]["tags"]
            return data[0]["file_url"]
        else:
            print("nonebooru")
            return None
    except Exception as e:
        print(repr(e))
        print(data)
        return None

@bot.message_handler(commands=['tags'])
def send_image_by_tags(message):
    _, booru, *tags = message.text.split()
    tags = "+".join(tags)
    image_url = fetch_image_url(booru, tags)
    
    if image_url:
        markup = types.InlineKeyboardMarkup()
        next_button = types.InlineKeyboardButton("Следующая картинка", callback_data=f"next|{booru}|{tags}|1")
        markup.add(next_button)
        bot.send_photo(message.chat.id, image_url, reply_markup=markup)
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
