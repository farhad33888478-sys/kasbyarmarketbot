# -*- coding: utf-8 -*-

import requests
import json
import config


def _post(method, payload=None, files=None):

    url = f"{config.TELEGRAM_API_URL}/{method}"

    try:
        response = requests.post(
            url,
            data=payload,
            files=files,
            timeout=40
        )

        print("STATUS:", response.status_code)
        print("BODY:", response.text)

        return response.json()

    except Exception as e:

        print("[telegram_api ERROR]", e)

        return {
            "ok": False,
            "error": str(e)
        }


def get_updates(offset=None, timeout=config.POLL_TIMEOUT):

    data = {
        "timeout": timeout
    }

    if offset is not None:
        data["offset"] = offset

    return _post("getUpdates", data)


def send_message(chat_id, text, reply_markup=None, parse_mode=None):

    data = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_markup:
        data["reply_markup"] = reply_markup_to_json(reply_markup)

    if parse_mode:
        data["parse_mode"] = parse_mode

    return _post("sendMessage", data)


def send_photo(chat_id, photo, caption=None, reply_markup=None):

    data = {
        "chat_id": chat_id,
        "photo": photo
    }

    if caption:
        data["caption"] = caption

    if reply_markup:
        data["reply_markup"] = reply_markup_to_json(reply_markup)

    return _post("sendPhoto", data)


def edit_message_text(chat_id, message_id, text, reply_markup=None):

    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text
    }

    if reply_markup:
        data["reply_markup"] = reply_markup_to_json(reply_markup)

    return _post("editMessageText", data)


def edit_message_reply_markup(chat_id, message_id, reply_markup=None):

    data = {
        "chat_id": chat_id,
        "message_id": message_id
    }

    if reply_markup:
        data["reply_markup"] = reply_markup_to_json(reply_markup)

    return _post("editMessageReplyMarkup", data)


def answer_callback_query(callback_query_id, text=None, show_alert=False):

    data = {
        "callback_query_id": callback_query_id,
        "show_alert": show_alert
    }

    if text:
        data["text"] = text

    return _post("answerCallbackQuery", data)


def delete_message(chat_id, message_id):

    return _post(
        "deleteMessage",
        {
            "chat_id": chat_id,
            "message_id": message_id
        }
    )


def get_file(file_id):

    return _post(
        "getFile",
        {
            "file_id": file_id
        }
    )


def download_file(file_path):

    url = (
        f"https://api.telegram.org/file/bot"
        f"{config.TELEGRAM_BOT_TOKEN}/{file_path}"
    )

    try:

        response = requests.get(
            url,
            timeout=40
        )

        if response.status_code == 200:
            return response.content

    except Exception as e:

        print("[telegram_api DOWNLOAD ERROR]", e)

    return None


def send_photo_bytes(
    chat_id,
    photo_bytes,
    filename="photo.jpg",
    caption=None,
    reply_markup=None
):

    data = {
        "chat_id": chat_id
    }

    if caption:
        data["caption"] = caption

    if reply_markup:
        data["reply_markup"] = reply_markup_to_json(reply_markup)

    files = {
        "photo": (filename, photo_bytes)
    }

    return _post(
        "sendPhoto",
        payload=data,
        files=files
    )


def reply_markup_to_json(markup):

    return json.dumps(
        markup,
        ensure_ascii=False
    )


def is_enabled():

    return bool(config.TELEGRAM_BOT_TOKEN)