from __future__ import annotations

from typing import Any

import requests

from .config import settings
from .models import TelegramFile


class TelegramClient:
    def __init__(self) -> None:
        self.base = f"https://api.telegram.org/bot{settings.telegram_bot_token}"
        self.file_base = f"https://api.telegram.org/file/bot{settings.telegram_bot_token}"

    def _post(self, method: str, *, json_data: dict[str, Any] | None = None, data: dict[str, Any] | None = None, files: dict[str, Any] | None = None) -> dict[str, Any]:
        response = requests.post(f"{self.base}/{method}", json=json_data, data=data, files=files, timeout=60)
        response.raise_for_status()
        return response.json()

    def send_message(self, chat_id: int | str, text: str, reply_markup: dict[str, Any] | None = None) -> None:
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        self._post("sendMessage", json_data=payload)

    def send_document(self, chat_id: int | str, path: str, caption: str = "") -> None:
        with open(path, "rb") as fh:
            files = {"document": (path.split("/")[-1], fh)}
            self._post("sendDocument", data={"chat_id": str(chat_id), "caption": caption[:1000]}, files=files)

    def answer_callback(self, callback_query_id: str, text: str = "") -> None:
        self._post("answerCallbackQuery", json_data={"callback_query_id": callback_query_id, "text": text[:200]})

    def get_file(self, file_id: str) -> TelegramFile:
        data = self._post("getFile", json_data={"file_id": file_id})
        file_path = ((data or {}).get("result") or {}).get("file_path")
        if not file_path:
            raise RuntimeError("Telegram did not return file_path")
        response = requests.get(f"{self.file_base}/{file_path}", timeout=120)
        response.raise_for_status()
        return TelegramFile(file_path=file_path, content=response.content)

    def set_webhook(self, url: str) -> dict[str, Any]:
        payload: dict[str, Any] = {"url": url}
        if settings.telegram_webhook_secret:
            payload["secret_token"] = settings.telegram_webhook_secret
        return self._post("setWebhook", json_data=payload)
