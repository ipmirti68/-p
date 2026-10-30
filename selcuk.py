"""SLCK (SelcukSportsHD) spor kaynagi botu - SADECE beIN"""

import re
import sys
import os

import requests
import urllib3
import warnings

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore")

HOME_URL = "https://www.selcuksportshdfe44b96fcb.xyz/"
OUTPUT_FILENAME = "mirti68.m3u"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
    ),
    "Referer": HOME_URL,
}

STREAM_DOMAIN = "https://dga1op10s1u3lea.9e694e1c2ce7ac.click"
STREAM_REFERER = "https://main.uxsyplayer6859599e6c.click/"

PRETTY_NAMES = {
    "selcukbeinsports1": "beIN Sports 1",
    "selcukbeinsports2": "beIN Sports 2",
    "selcukbeinsports3": "beIN Sports 3",
    "selcukbeinsports4": "beIN Sports 4",
    "selcukbeinsports5": "beIN Sports 5",
    "selcukbeinsportsmax1": "beIN Sports Max 1",
    "selcukbeinsportsmax2": "beIN Sports Max 2",
    "selcukbeinsportshaber": "beIN Sports Haber",
    "selcukbeinconnect1": "beIN Connect 1",
}

def pretty(cid: str) -> str:
    return PRETTY_NAMES.get(cid.strip().lower(), cid.replace("selcuk", "").title())

def fetch_home():
    r = requests.get(HOME_URL, headers=HEADERS, timeout=25
