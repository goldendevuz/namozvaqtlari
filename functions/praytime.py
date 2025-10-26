from typing import Dict, Any, Optional, Tuple
import aiohttp
from aiogram.types import CallbackQuery
from aiogram import Bot
from datetime import datetime
import time
import re
import asyncio
import os
from keyboards.inline import (
    cities_keyboard,
    prayer_controls_keyboard,
    BACK_TO_MENU,
    REFRESH_PREFIX,
)
from functions.channel import check_user_subscription, get_subscription_keyboard

REGION_MAP: Dict[str, str] = {
    "andijon": "Andijon",
    "fargona": "Farg'ona",
    "xiva": "Xiva",
    "toshkent": "Toshkent",
    "namangan": "Namangan",
    "buxoro": "Buxoro",
    "guliston": "Guliston",
    "jizzax": "Jizzax",
    "zarafshon": "Zarafshon",
    "qarshi": "Qarshi",
    "navoiy": "Navoiy",
    "nukus": "Nukus",
    "samarqand": "Samarqand",
    "termiz": "Termiz",
    "urganch": "Urganch",
}

ALIASES: Dict[str, str] = {
    "namanga": "namangan",
    "gulistan": "guliston",
    "andijan": "andijon",
    "tashkent": "toshkent",
    "fergana": "fargona",
    "farg'ona": "fargona",
    "samarkand": "samarqand",
    "khiva": "xiva",
    "bukhara": "buxoro",
    "karshi": "qarshi",
    "navoi": "navoiy",
    "urgench": "urganch",
    "djizzakh": "jizzax",
    "zarafshan": "zarafshon",
    "termiz": "termiz",
}

ALL_REGION_KEYS = sorted(set(list(REGION_MAP.keys()) + list(ALIASES.keys())))

API_URL = "https://islomapi.uz/api/present/day"

_TTL_SECONDS = 120
_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_session: Optional[aiohttp.ClientSession] = None


def available_regions() -> Dict[str, str]:
    return dict(REGION_MAP)


def _normalize_region_key(region_key: str) -> str:
    key = (region_key or "").strip().lower()
    if key in REGION_MAP:
        return key
    if key in ALIASES:
        return ALIASES[key]
    return key


async def _get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        timeout = aiohttp.ClientTimeout(total=10)
        _session = aiohttp.ClientSession(timeout=timeout)
    return _session


async def _scrape_namangan_times() -> Dict[str, Any]:
    url = "https://islom.uz/region/15"
    session = await _get_session()
    async with session.get(url) as resp:
        if resp.status != 200:
            raise RuntimeError(f"Failed to scrape Namangan page: HTTP {resp.status}")
        html = await resp.text()
        
        visible_times = re.findall(r'>(\d{2}:\d{2})<', html)
        main_times = [t for t in visible_times if t.startswith(('04:', '05:', '06:', '11:', '12:', '15:', '16:', '17:', '18:', '19:'))]
        
        if len(main_times) < 6:
            raise RuntimeError(f"Not enough prayer times found on page. Found: {len(main_times)}")
        
        weekday_match = re.search(r'\d{4} йил \d+ \w+, (\w+)', html)
        weekday = weekday_match.group(1) if weekday_match else ""
        
        return {
            "times": {
                "tong": main_times[0],
                "quyosh": main_times[1],
                "peshin": main_times[2],
                "asr": main_times[3],
                "shom": main_times[4],
                "hufton": main_times[5],
            },
            "weekday": weekday,
        }


async def fetch_prayer_times(region_key: str) -> Dict[str, Any]:
    key = _normalize_region_key(region_key)
    if key not in REGION_MAP:
        raise ValueError(
            f"Unknown region key '{region_key}'. Valid keys: {', '.join(sorted(REGION_MAP.keys()))}"
        )
    now = time.time()
    cached = _cache.get(key)
    if cached and cached[0] > now:
        return cached[1]
    
    max_retries = 3
    retry_delay = 0.5
    last_error = None
    
    for attempt in range(max_retries):
        try:
            if key == "namangan":
                data = await _scrape_namangan_times()
                _cache[key] = (now + _TTL_SECONDS, data)
                return data
            
            region_name = REGION_MAP[key]
            session = await _get_session()
            async with session.get(API_URL, params={"region": region_name}) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(
                        f"API error: HTTP {resp.status} for region '{region_name}'. Body: {text[:200]}"
                    )
                data: Dict[str, Any] = await resp.json(content_type=None)
                _cache[key] = (now + _TTL_SECONDS, data)
                return data
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                print(f"[RETRY] Attempt {attempt + 1} failed for {key}: {e}")
                await asyncio.sleep(retry_delay)
            else:
                print(f"[ERROR] All retries failed for {key}: {e}")
    
    raise RuntimeError(f"Could not fetch prayer times after {max_retries} attempts: {last_error}")


def _format_prayer_text(region_name: str, payload: Dict[str, Any], show_updated: bool = False) -> str:
    times = payload.get("times", {}) if isinstance(payload, dict) else {}
    tong = times.get("tong_saharlik") or times.get("tong") or "--:--"
    quyosh = times.get("quyosh") or "--:--"
    peshin = times.get("peshin") or "--:--"
    asr = times.get("asr") or "--:--"
    shom = times.get("shom_iftor") or times.get("shom") or "--:--"
    hufton = times.get("hufton") or "--:--"

    now = datetime.now()
    year = now.year
    day = now.day
    time_now = now.strftime("%H:%M")
    weekday = (payload.get("weekday") or "").capitalize() or ""
    date_line = f"{year}-yil|Oyning {day}-kuni|{weekday}|Soat {time_now}"
    
    header = "Namoz Vaqtlari:\n" if not show_updated else "Namoz Vaqtlari: ✅\n"

    text = (
        f"{header}"
        "=========================\n"
        f"📌 《 🏙 {region_name} 》 vaqti bilan\n"
        "--------------------------------------------\n"
        f"🌓  Tong:         -  {tong} \n"
        f"🌞  Quyosh:     -  {quyosh} \n\n"
        f"🕰  Bomdod:   -  {tong}  \n"
        f"🕰  Peshin:      -  {peshin}  \n"
        f"🕰  Asr:           -  {asr} \n"
        f"🕰  Shom:       -  {shom}  \n"
        f"🕰  Xufton:      -  {hufton} \n"
        "--------------------------------------------\n\n"
        f"📅 {date_line}"
    )
    return text


async def on_region_selected(callback: CallbackQuery):
    user_id = callback.from_user.id
    admin_ids = []
    admin1 = os.getenv("ADMIN1")
    admin2 = os.getenv("ADMIN2")
    if admin1:
        admin_ids.append(int(admin1))
    if admin2:
        admin_ids.append(int(admin2))
    
    if user_id not in admin_ids:
        bot = callback.bot
        is_subscribed, not_subscribed = await check_user_subscription(bot, user_id)
        if not is_subscribed:
            await callback.message.answer(
                "⚠️ Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
                reply_markup=get_subscription_keyboard(not_subscribed),
            )
            await callback.answer("Iltimos, kanallarga obuna bo'ling!", show_alert=True)
            return
    
    raw = (callback.data or "")
    key = _normalize_region_key(raw)
    if key not in REGION_MAP:
        await callback.answer("Noma'lum viloyat", show_alert=True)
        return
    region_name = REGION_MAP[key]
    await callback.answer("Yuklanmoqda...")
    try:
        data = await fetch_prayer_times(key)
        text = _format_prayer_text(region_name, data)
        await callback.message.edit_text(
            text=text,
            reply_markup=prayer_controls_keyboard(key),
            disable_web_page_preview=True,
        )
    except Exception as e:
        print(f"[ERROR] on_region_selected key={key}: {e}")
        await callback.message.answer("Namoz vaqtlarini yuklashda xatolik. Iltimos, qayta urinib ko'ring.")



async def on_back(callback: CallbackQuery):
    await callback.message.edit_text(
        "O'zingizga kerakli viloyatni tanlang👇",
        reply_markup=cities_keyboard,
        disable_web_page_preview=True,
    )
    await callback.answer()


async def on_refresh(callback: CallbackQuery):
    user_id = callback.from_user.id
    admin_ids = []
    admin1 = os.getenv("ADMIN1")
    admin2 = os.getenv("ADMIN2")
    if admin1:
        admin_ids.append(int(admin1))
    if admin2:
        admin_ids.append(int(admin2))
    
    if user_id not in admin_ids:
        bot = callback.bot
        is_subscribed, not_subscribed = await check_user_subscription(bot, user_id)
        if not is_subscribed:
            await callback.message.answer(
                "⚠️ Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
                reply_markup=get_subscription_keyboard(not_subscribed),
            )
            await callback.answer("Iltimos, kanallarga obuna bo'ling!", show_alert=True)
            return
    
    raw = (callback.data or "").replace(REFRESH_PREFIX, "")
    key = _normalize_region_key(raw)
    if key not in REGION_MAP:
        await callback.answer("Noma'lum viloyat", show_alert=True)
        return
    region_name = REGION_MAP[key]
    await callback.answer("Yangilanmoqda...")
    
    if key in _cache:
        del _cache[key]
    
    try:
        data = await fetch_prayer_times(key)
        text = _format_prayer_text(region_name, data, show_updated=True)
        await callback.message.edit_text(
            text=text,
            reply_markup=prayer_controls_keyboard(key),
            disable_web_page_preview=True,
        )
    except Exception as e:
        error_msg = str(e)
        if "message is not modified" in error_msg:
            await callback.answer("Ma'lumotlar allaqachon yangi ✅", show_alert=False)
        else:
            print(f"[ERROR] on_refresh key={key}: {e}")
            await callback.answer("Yangilashda xatolik. Qayta urinib ko'ring.", show_alert=True)


async def close_praytime_session():
    global _session
    try:
        if _session and not _session.closed:
            await _session.close()
    finally:
        _session = None


__all__ = [
    "fetch_prayer_times",
    "available_regions",
    "REGION_MAP",
    "ALL_REGION_KEYS",
    "on_region_selected",
    "on_back",
    "on_refresh",
    "close_praytime_session",
]

