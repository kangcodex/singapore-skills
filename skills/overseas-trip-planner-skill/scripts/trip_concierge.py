"""Overseas Trip Planner — Singapore-origin travel concierge helpers.

Stdlib-only. No network. Given a destination + month + 5 preference
dimensions (companion, style, pace, accommodation, rhythm), validates the
mandatory parameters, looks up the seasonal sunset time for that
destination, computes a daylight cutoff, applies a 30% overseas transit
buffer, and returns a combined strategy the agent uses to write the
itinerary. The LLM does the subjective work; this script is the
deterministic safety net.

Usage:
    python3 trip_concierge.py --destination Kyoto --month 2026-11 \
        --companion couple --style cultural --pace moderate \
        --accommodation premium --rhythm early-starts
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFERENCES = HERE.parent / "references"

# ---------------------------------------------------------------- enums ----

COMPANIONS = ("solo", "couple", "family", "friends", "elderly")
STYLES = ("cultural", "classic", "nature", "cityscape", "historical")
PACES = ("ambitious", "moderate", "relaxed")
ACCOMMODATIONS = ("comfort", "premium", "luxury")
RHYTHMS = ("early-starts", "late-nights")

# Backwards-compat aliases (older callers used these names)
_PERSONA_TO_COMPANION = {"solo": "solo", "family": "family", "couple": "couple", "friends": "friends", "elderly": "elderly"}
_BUDGET_TO_ACCOMMODATION = {"backpacker": "comfort", "mid": "premium", "luxury": "luxury"}

# Singapore-origin travel baseline assumptions
SG_ORIGIN = "Singapore (Changi)"

# Cutoff for outdoor / highway driving — sunset minus this many minutes.
SUNSET_BUFFER_MINUTES = 60

# Heavy-transit threshold — any single transit leg above this is flagged.
HEAVY_TRANSIT_MINUTES = 180

# Extra buffer for unfamiliar overseas driving, parking, check-in.
TRANSIT_BUFFER_PCT = 0.30


# ---------------------------------------------------------------- sunset --

# Static sunset lookup for the ~70 most common Singapore-traveler
# destinations. Times are in 24-hour local format, midpoint of the month
# (15th). All values approximate; for exact times the LLM should
# web-search the specific date.
_SUNSET: dict[str, dict[int, str]] = {
    "tokyo":        {1: "16:50", 2: "17:25", 3: "17:55", 4: "18:20", 5: "18:45", 6: "19:00", 7: "18:55", 8: "18:25", 9: "17:40", 10: "16:55", 11: "16:25", 12: "16:30"},
    "osaka":        {1: "17:05", 2: "17:35", 3: "18:00", 4: "18:25", 5: "18:50", 6: "19:10", 7: "19:05", 8: "18:35", 9: "17:50", 10: "17:05", 11: "16:40", 12: "16:45"},
    "kyoto":        {1: "17:05", 2: "17:35", 3: "18:00", 4: "18:25", 5: "18:50", 6: "19:10", 7: "19:05", 8: "18:35", 9: "17:50", 10: "17:05", 11: "16:40", 12: "16:45"},
    "hokkaido":     {1: "16:30", 2: "17:10", 3: "17:50", 4: "18:30", 5: "19:00", 6: "19:20", 7: "19:10", 8: "18:30", 9: "17:40", 10: "16:50", 11: "16:15", 12: "16:05"},
    "sapporo":      {1: "16:30", 2: "17:10", 3: "17:50", 4: "18:30", 5: "19:00", 6: "19:20", 7: "19:10", 8: "18:30", 9: "17:40", 10: "16:50", 11: "16:15", 12: "16:05"},
    "fukuoka":      {1: "17:25", 2: "17:55", 3: "18:20", 4: "18:45", 5: "19:10", 6: "19:25", 7: "19:20", 8: "18:55", 9: "18:10", 10: "17:25", 11: "17:00", 12: "17:05"},
    "okinawa":      {1: "17:55", 2: "18:20", 3: "18:40", 4: "19:00", 5: "19:20", 6: "19:30", 7: "19:25", 8: "19:05", 9: "18:30", 10: "17:55", 11: "17:35", 12: "17:40"},
    "seoul":        {1: "17:35", 2: "18:05", 3: "18:30", 4: "19:00", 5: "19:25", 6: "19:45", 7: "19:40", 8: "19:10", 9: "18:25", 10: "17:40", 11: "17:10", 12: "17:20"},
    "busan":        {1: "17:35", 2: "18:05", 3: "18:30", 4: "19:00", 5: "19:25", 6: "19:45", 7: "19:40", 8: "19:10", 9: "18:25", 10: "17:40", 11: "17:10", 12: "17:20"},
    "jeju":         {1: "17:50", 2: "18:20", 3: "18:50", 4: "19:15", 5: "19:40", 6: "19:55", 7: "19:50", 8: "19:20", 9: "18:35", 10: "17:50", 11: "17:20", 12: "17:30"},
    "hong kong":    {1: "18:00", 2: "18:20", 3: "18:35", 4: "18:50", 5: "19:05", 6: "19:15", 7: "19:10", 8: "18:50", 9: "18:20", 10: "17:50", 11: "17:35", 12: "17:45"},
    "taipei":       {1: "17:30", 2: "17:55", 3: "18:15", 4: "18:35", 5: "18:55", 6: "19:10", 7: "19:05", 8: "18:45", 9: "18:10", 10: "17:35", 11: "17:15", 12: "17:20"},
    "shanghai":     {1: "17:20", 2: "17:50", 3: "18:15", 4: "18:40", 5: "19:00", 6: "19:10", 7: "19:05", 8: "18:40", 9: "18:05", 10: "17:30", 11: "17:05", 12: "17:10"},
    "beijing":      {1: "17:10", 2: "17:45", 3: "18:15", 4: "18:40", 5: "19:05", 6: "19:45", 7: "19:40", 8: "19:10", 9: "18:25", 10: "17:40", 11: "17:05", 12: "16:50"},
    "bangkok":      {1: "18:00", 2: "18:20", 3: "18:30", 4: "18:35", 5: "18:40", 6: "18:50", 7: "18:50", 8: "18:40", 9: "18:20", 10: "18:00", 11: "17:45", 12: "17:45"},
    "chiang mai":   {1: "18:10", 2: "18:30", 3: "18:40", 4: "18:50", 5: "19:00", 6: "19:10", 7: "19:05", 8: "18:50", 9: "18:30", 10: "18:05", 11: "17:50", 12: "17:50"},
    "phuket":       {1: "18:30", 2: "18:40", 3: "18:45", 4: "18:50", 5: "19:00", 6: "19:10", 7: "19:05", 8: "19:00", 9: "18:45", 10: "18:25", 11: "18:15", 12: "18:20"},
    "bali":         {1: "18:35", 2: "18:40", 3: "18:35", 4: "18:20", 5: "18:05", 6: "17:55", 7: "18:00", 8: "18:10", 9: "18:15", 10: "18:25", 11: "18:35", 12: "18:40"},
    "jakarta":      {1: "18:25", 2: "18:30", 3: "18:25", 4: "18:15", 5: "18:05", 6: "17:55", 7: "18:00", 8: "18:05", 9: "18:10", 10: "18:20", 11: "18:30", 12: "18:30"},
    "manila":       {1: "17:55", 2: "18:10", 3: "18:20", 4: "18:30", 5: "18:40", 6: "18:45", 7: "18:40", 8: "18:25", 9: "18:05", 10: "17:45", 11: "17:35", 12: "17:45"},
    "kuala lumpur": {1: "19:25", 2: "19:30", 3: "19:25", 4: "19:15", 5: "19:10", 6: "19:15", 7: "19:20", 8: "19:20", 9: "19:10", 10: "19:00", 11: "19:00", 12: "19:15"},
    "penang":       {1: "19:30", 2: "19:35", 3: "19:30", 4: "19:20", 5: "19:15", 6: "19:20", 7: "19:25", 8: "19:25", 9: "19:15", 10: "19:05", 11: "19:05", 12: "19:20"},
    "vientiane":    {1: "17:55", 2: "18:15", 3: "18:25", 4: "18:35", 5: "18:45", 6: "18:55", 7: "18:50", 8: "18:35", 9: "18:15", 10: "17:50", 11: "17:35", 12: "17:35"},
    "hanoi":        {1: "17:35", 2: "18:00", 3: "18:15", 4: "18:30", 5: "18:45", 6: "18:55", 7: "18:50", 8: "18:30", 9: "18:00", 10: "17:30", 11: "17:15", 12: "17:20"},
    "ho chi minh":  {1: "17:55", 2: "18:10", 3: "18:15", 4: "18:20", 5: "18:30", 6: "18:35", 7: "18:30", 8: "18:20", 9: "18:00", 10: "17:40", 11: "17:30", 12: "17:40"},
    "siem reap":    {1: "18:00", 2: "18:15", 3: "18:20", 4: "18:25", 5: "18:30", 6: "18:35", 7: "18:30", 8: "18:20", 9: "18:05", 10: "17:50", 11: "17:40", 12: "17:45"},
    "yangon":       {1: "17:55", 2: "18:15", 3: "18:25", 4: "18:30", 5: "18:40", 6: "18:45", 7: "18:40", 8: "18:25", 9: "18:05", 10: "17:45", 11: "17:35", 12: "17:40"},
    "mumbai":       {1: "18:20", 2: "18:40", 3: "18:50", 4: "19:00", 5: "19:15", 6: "19:25", 7: "19:20", 8: "19:00", 9: "18:35", 10: "18:10", 11: "17:55", 12: "18:05"},
    "delhi":        {1: "17:45", 2: "18:15", 3: "18:35", 4: "18:55", 5: "19:15", 6: "19:30", 7: "19:25", 8: "19:00", 9: "18:25", 10: "17:50", 11: "17:25", 12: "17:20"},
    "colombo":      {1: "18:10", 2: "18:20", 3: "18:25", 4: "18:25", 5: "18:30", 6: "18:35", 7: "18:30", 8: "18:25", 9: "18:10", 10: "18:00", 11: "17:55", 12: "18:00"},
    "kathmandu":    {1: "17:30", 2: "18:00", 3: "18:20", 4: "18:40", 5: "19:00", 6: "19:15", 7: "19:10", 8: "18:45", 9: "18:15", 10: "17:40", 11: "17:15", 12: "17:15"},
    "dubai":        {1: "17:55", 2: "18:20", 3: "18:35", 4: "18:50", 5: "19:05", 6: "19:20", 7: "19:15", 8: "18:55", 9: "18:25", 10: "17:55", 11: "17:35", 12: "17:40"},
    "doha":         {1: "17:15", 2: "17:40", 3: "17:55", 4: "18:10", 5: "18:30", 6: "18:45", 7: "18:40", 8: "18:15", 9: "17:45", 10: "17:15", 11: "16:55", 12: "17:00"},
    "istanbul":     {1: "17:00", 2: "17:35", 3: "18:05", 4: "18:35", 5: "19:00", 6: "19:25", 7: "19:20", 8: "18:50", 9: "18:05", 10: "17:20", 11: "16:50", 12: "16:45"},
    "london":       {1: "16:30", 2: "17:15", 3: "18:00", 4: "18:50", 5: "19:35", 6: "20:15", 7: "20:10", 8: "19:30", 9: "18:25", 10: "17:20", 11: "16:20", 12: "15:50"},
    "paris":        {1: "17:00", 2: "17:45", 3: "18:30", 4: "19:20", 5: "20:05", 6: "20:45", 7: "20:40", 8: "20:00", 9: "18:55", 10: "17:50", 11: "16:50", 12: "16:20"},
    "amsterdam":    {1: "16:45", 2: "17:30", 3: "18:15", 4: "19:05", 5: "19:50", 6: "20:30", 7: "20:25", 8: "19:45", 9: "18:40", 10: "17:35", 11: "16:35", 12: "16:05"},
    "berlin":       {1: "16:30", 2: "17:15", 3: "18:00", 4: "18:50", 5: "19:35", 6: "20:15", 7: "20:10", 8: "19:30", 9: "18:25", 10: "17:20", 11: "16:20", 12: "15:50"},
    "zurich":       {1: "16:55", 2: "17:40", 3: "18:20", 4: "19:10", 5: "19:50", 6: "20:30", 7: "20:20", 8: "19:45", 9: "18:45", 10: "17:45", 11: "16:50", 12: "16:25"},
    "rome":         {1: "17:00", 2: "17:35", 3: "18:05", 4: "18:40", 5: "19:10", 6: "19:45", 7: "19:40", 8: "19:05", 9: "18:10", 10: "17:15", 11: "16:40", 12: "16:40"},
    "barcelona":    {1: "17:35", 2: "18:10", 3: "18:45", 4: "19:20", 5: "19:50", 6: "20:25", 7: "20:15", 8: "19:40", 9: "18:45", 10: "17:50", 11: "17:15", 12: "17:15"},
    "madrid":       {1: "17:30", 2: "18:10", 3: "18:45", 4: "19:25", 5: "19:55", 6: "20:30", 7: "20:20", 8: "19:45", 9: "18:50", 10: "17:55", 11: "17:15", 12: "17:15"},
    "lisbon":       {1: "17:30", 2: "18:05", 3: "18:35", 4: "19:10", 5: "19:40", 6: "20:15", 7: "20:05", 8: "19:30", 9: "18:40", 10: "17:50", 11: "17:15", 12: "17:10"},
    "athens":       {1: "17:25", 2: "18:00", 3: "18:30", 4: "19:00", 5: "19:30", 6: "20:00", 7: "19:55", 8: "19:20", 9: "18:30", 10: "17:40", 11: "17:10", 12: "17:10"},
    "vienna":       {1: "16:30", 2: "17:15", 3: "18:00", 4: "18:50", 5: "19:30", 6: "20:10", 7: "20:00", 8: "19:25", 9: "18:20", 10: "17:15", 11: "16:20", 12: "15:55"},
    "prague":       {1: "16:30", 2: "17:15", 3: "18:00", 4: "18:50", 5: "19:30", 6: "20:10", 7: "20:00", 8: "19:25", 9: "18:20", 10: "17:15", 11: "16:20", 12: "15:55"},
    "budapest":     {1: "16:20", 2: "17:05", 3: "17:45", 4: "18:30", 5: "19:10", 6: "19:50", 7: "19:40", 8: "19:05", 9: "18:05", 10: "17:00", 11: "16:10", 12: "15:50"},
    "copenhagen":   {1: "16:15", 2: "17:00", 3: "17:45", 4: "18:40", 5: "19:25", 6: "20:10", 7: "20:00", 8: "19:20", 9: "18:10", 10: "17:00", 11: "16:00", 12: "15:35"},
    "stockholm":    {1: "15:20", 2: "16:10", 3: "17:05", 4: "18:10", 5: "19:05", 6: "19:55", 7: "19:45", 8: "18:55", 9: "17:35", 10: "16:15", 11: "15:05", 12: "14:35"},
    "oslo":         {1: "15:30", 2: "16:30", 3: "17:30", 4: "18:40", 5: "19:50", 6: "20:50", 7: "20:35", 8: "19:30", 9: "17:55", 10: "16:20", 11: "15:10", 12: "14:30"},
    "reykjavik":    {1: "16:00", 2: "17:30", 3: "19:00", 4: "20:30", 5: "22:00", 6: "23:30", 7: "23:00", 8: "21:00", 9: "19:00", 10: "17:00", 11: "15:30", 12: "15:30"},
    "new york":     {1: "16:50", 2: "17:25", 3: "18:00", 4: "18:35", 5: "19:05", 6: "19:30", 7: "19:25", 8: "18:55", 9: "18:10", 10: "17:25", 11: "16:45", 12: "16:30"},
    "los angeles":  {1: "17:05", 2: "17:35", 3: "18:00", 4: "18:25", 5: "18:50", 6: "19:10", 7: "19:05", 8: "18:35", 9: "17:50", 10: "17:05", 11: "16:40", 12: "16:45"},
    "san francisco":{1: "17:15", 2: "17:50", 3: "18:20", 4: "18:50", 5: "19:15", 6: "19:35", 7: "19:30", 8: "19:00", 9: "18:10", 10: "17:20", 11: "16:50", 12: "16:55"},
    "seattle":      {1: "16:50", 2: "17:25", 3: "18:00", 4: "18:40", 5: "19:15", 6: "19:45", 7: "19:40", 8: "19:05", 9: "18:10", 10: "17:15", 11: "16:30", 12: "16:20"},
    "vancouver":    {1: "16:40", 2: "17:15", 3: "17:55", 4: "18:35", 5: "19:10", 6: "19:40", 7: "19:35", 8: "19:00", 9: "18:00", 10: "17:05", 11: "16:20", 12: "16:10"},
    "toronto":      {1: "17:00", 2: "17:35", 3: "18:10", 4: "18:45", 5: "19:15", 6: "19:40", 7: "19:35", 8: "19:05", 9: "18:15", 10: "17:30", 11: "16:50", 12: "16:40"},
    "mexico city":  {1: "18:20", 2: "18:40", 3: "18:50", 4: "19:00", 5: "19:10", 6: "19:20", 7: "19:15", 8: "19:00", 9: "18:35", 10: "18:10", 11: "17:55", 12: "18:05"},
    "sydney":       {1: "20:10", 2: "19:50", 3: "19:15", 4: "17:35", 5: "16:55", 6: "16:50", 7: "17:10", 8: "17:35", 9: "17:55", 10: "19:15", 11: "19:45", 12: "20:10"},
    "melbourne":    {1: "20:40", 2: "20:15", 3: "19:35", 4: "17:50", 5: "17:10", 6: "16:55", 7: "17:15", 8: "17:50", 9: "18:10", 10: "19:30", 11: "20:00", 12: "20:40"},
    "auckland":     {1: "20:45", 2: "20:25", 3: "19:50", 4: "18:05", 5: "17:15", 6: "17:05", 7: "17:25", 8: "17:50", 9: "18:10", 10: "19:30", 11: "20:05", 12: "20:45"},
    "fiji":         {1: "19:00", 2: "18:50", 3: "18:30", 4: "18:00", 5: "17:40", 6: "17:35", 7: "17:45", 8: "17:55", 9: "18:05", 10: "18:25", 11: "18:50", 12: "19:00"},
    "cape town":    {1: "20:00", 2: "19:45", 3: "19:15", 4: "18:00", 5: "17:25", 6: "17:15", 7: "17:35", 8: "18:00", 9: "18:20", 10: "19:00", 11: "19:35", 12: "20:00"},
    "johannesburg": {1: "19:10", 2: "18:55", 3: "18:25", 4: "17:10", 5: "16:35", 6: "16:25", 7: "16:45", 8: "17:10", 9: "17:30", 10: "18:10", 11: "18:45", 12: "19:10"},
    "marrakech":    {1: "18:00", 2: "18:25", 3: "18:40", 4: "19:00", 5: "19:20", 6: "19:40", 7: "19:35", 8: "19:10", 9: "18:35", 10: "18:00", 11: "17:35", 12: "17:45"},
    "cairo":        {1: "17:15", 2: "17:45", 3: "18:05", 4: "18:25", 5: "18:50", 6: "19:10", 7: "19:05", 8: "18:40", 9: "18:05", 10: "17:30", 11: "17:05", 12: "17:00"},
    "taipei city":  {1: "17:30", 2: "17:55", 3: "18:15", 4: "18:35", 5: "18:55", 6: "19:10", 7: "19:05", 8: "18:45", 9: "18:10", 10: "17:35", 11: "17:15", 12: "17:20"},
    "singapore":    {1: "19:15", 2: "19:20", 3: "19:20", 4: "19:15", 5: "19:15", 6: "19:20", 7: "19:20", 8: "19:20", 9: "19:10", 10: "19:00", 11: "19:00", 12: "19:10"},
}


# --------------------------------------------------------- destination alias --

_ALIASES = {
    "東京": "tokyo", "tokio": "tokyo", "tyo": "tokyo",
    "大阪": "osaka",
    "京都": "kyoto",
    "北海道": "hokkaido",
    "札幌": "sapporo",
    "福岡": "fukuoka",
    "沖縄": "okinawa",
    "首尔": "seoul", "서울": "seoul",
    "釜山": "busan",
    "濟州": "jeju", "jeju island": "jeju",
    "香港": "hong kong", "hk": "hong kong",
    "臺北": "taipei", "台北": "taipei",
    "上海": "shanghai",
    "北京": "beijing",
    "曼谷": "bangkok",
    "清迈": "chiang mai",
    "普吉": "phuket",
    "巴厘": "bali", "峇里": "bali", "ubud": "bali", "denpasar": "bali",
    "雅加达": "jakarta",
    "吉隆坡": "kuala lumpur", "kl": "kuala lumpur",
    "槟城": "penang",
    "河内": "hanoi",
    "胡志明市": "ho chi minh", "西贡": "ho chi minh", "saigon": "ho chi minh",
    "暹粒": "siem reap", "吴哥": "siem reap",
    "仰光": "yangon",
    "孟买": "mumbai", "bombay": "mumbai",
    "新德里": "delhi",
    "可伦坡": "colombo",
    "加德满都": "kathmandu",
    "杜拜": "dubai",
    "多哈": "doha",
    "伊斯坦布尔": "istanbul",
    "伦敦": "london",
    "巴黎": "paris",
    "阿姆斯特丹": "amsterdam",
    "柏林": "berlin",
    "苏黎世": "zurich",
    "罗马": "rome", "roma": "rome",
    "巴塞罗那": "barcelona",
    "马德里": "madrid",
    "里斯本": "lisbon",
    "雅典": "athens",
    "维也纳": "vienna", "wien": "vienna",
    "布拉格": "prague",
    "布达佩斯": "budapest",
    "哥本哈根": "copenhagen",
    "斯德哥尔摩": "stockholm",
    "奥斯陆": "oslo",
    "雷克雅未克": "reykjavik",
    "纽约": "new york", "nyc": "new york", "manhattan": "new york",
    "洛杉矶": "los angeles", "la": "los angeles",
    "旧金山": "san francisco", "sf": "san francisco",
    "西雅图": "seattle",
    "温哥华": "vancouver",
    "多伦多": "toronto",
    "墨西哥城": "mexico city",
    "悉尼": "sydney",
    "墨尔本": "melbourne",
    "奥克兰": "auckland",
    "开普敦": "cape town",
    "约翰内斯堡": "johannesburg",
    "马拉喀什": "marrakech",
    "开罗": "cairo",
    "新加坡": "singapore",
}


# ------------------------------------------------- 5-dim preference strategies --

_COMPANION_STRATEGY: dict[str, dict] = {
    "solo": {
        "label": "Solo traveler",
        "pacing": "Moderate. 2-3 anchor activities per day, plenty of unstructured time.",
        "lodging": "Boutique hostels, capsule hotels, single-occupancy ryokans. Always central and walkable.",
        "dining": "Counter-seating, standing bars, izakaya nomi-yose. Avoid anywhere that requires a reservation for one.",
        "transit": "Public transit preferred. Flag any >2-hour solo night transit.",
        "evening": "Social hubs: hostel common rooms, language-exchange meetups, standing bars.",
        "daily_activity_cap_hours": 8,
        "single_supplement": True,
    },
    "couple": {
        "label": "Couple (romantic)",
        "pacing": "High-energy afternoon, atmospheric evening. The day's emotional arc matters.",
        "lodging": "Boutique ryokan, design hotel, private onsen, room with a view. One experiential stay per trip.",
        "dining": "Intimate, ambient. Counter-seating omakase, vineyard lunch, private dining. Avoid family-chain restaurants at dinner.",
        "transit": "Comfort matters. First-class rail over local when available. Pre-book scenic train seats.",
        "evening": "Hidden bar, jazz kissaten, sunset viewpoint, private onsen — date-feel, not group activity.",
        "daily_activity_cap_hours": 9,
        "single_supplement": False,
    },
    "family": {
        "label": "Family with children",
        "pacing": "Slow. One Big Event per day. No back-to-back transit changes.",
        "lodging": "Apartment hotel with kitchenette, ground-floor or lift-access, bathtub over shower, near a park.",
        "dining": "Family-friendly seating, kid menus or sharing plates, near a park for post-meal play.",
        "transit": "Spacious SUV / MPV with ISOFIX. Flag bathrooms on legs >90 min. Step-free routes only.",
        "evening": "Early dinner (17:30-18:30), low-key hotel time. No nightlife, no late drives.",
        "daily_activity_cap_hours": 5,
        "single_supplement": False,
    },
    "friends": {
        "label": "Group of friends",
        "pacing": "Ambitious. Maximize shared experiences. 2-3 anchors per day plus night activities.",
        "lodging": "Apartments or 4-bed hotel rooms, central, walkable. Common area for hanging out.",
        "dining": "Group-friendly: izakaya, BBQ, hawker table-style. Long, social meals beat intimate ones.",
        "transit": "Group rail pass or 2-3 taxis. Optimize for group-cohesion, not efficiency.",
        "evening": "Late-night neighborhoods, izakaya nomi-yose, karaoke, night markets.",
        "daily_activity_cap_hours": 10,
        "single_supplement": False,
    },
    "elderly": {
        "label": "Elderly traveler (60+)",
        "pacing": "Relaxed. 1 anchor per day, long mid-day rest, no dawn starts.",
        "lodging": "Ground-floor or lift-access, bathtub, no upper-floor walkups, central. Concierge / porter service preferred.",
        "dining": "Sit-down restaurants only, accessible seating, no standing bars, no counter-only. Frequent snack stops.",
        "transit": "Private car or taxi over rail where possible. Avoid stairs. Step-free routes only. Bathrooms on any leg >60 min.",
        "evening": "Early dinner (17:00-18:00), low-key. No nightlife, no late driving.",
        "daily_activity_cap_hours": 4,
        "single_supplement": False,
    },
}

_STYLE_STRATEGY: dict[str, dict] = {
    "cultural": {
        "label": "Cultural immersion",
        "what_to_prioritize": "Temples, shrines, traditional craft workshops, tea ceremony, calligraphy, local festivals, language classes.",
        "what_to_skip": "Generic 'Top 10' landmark lists. Branded chain experiences. Tour-bus stops under 30 min.",
        "anchor_density": "1-2 cultural anchors/day max (deep, not wide).",
        "dining": "Family-run or neighborhood institution. Order the hyper-local specialty — not the version the menu has in English.",
    },
    "classic": {
        "label": "Classic / must-see",
        "what_to_prioritize": "The famous landmarks of the destination, done at the right time of day (sunrise, golden hour, after dark).",
        "what_to_skip": "Mid-day at the headline attraction — wait for golden hour or do sunrise to skip crowds.",
        "anchor_density": "2 anchors/day is fine. Add a third only if it's a quieter indoor pivot.",
        "dining": "Mix — one signature / tourist-friendly spot, two local finds.",
    },
    "nature": {
        "label": "Nature / outdoors",
        "what_to_prioritize": "Parks, trails, scenic drives, alpine lakes, coastline. Wildlife (ethical, distance-based) where it exists.",
        "what_to_skip": "Urban-only itineraries. Multi-hour indoor museums. Late drives to remote trailheads.",
        "anchor_density": "1-2 nature anchors/day. The third block is rest, picnic, or a short hike.",
        "dining": "Local farm-to-table, picnic supplies from local market, mountain hut food.",
    },
    "cityscape": {
        "label": "City / urban",
        "what_to_prioritize": "Architecture walks, neighborhood food crawls, contemporary art, shopping, transport-as-attraction (tram, ferry, metro art).",
        "what_to_skip": "Single-city day trips that eat the daylight. Beating the same neighborhood three times.",
        "anchor_density": "2-3 anchors/day, all within the city. Use transit time as observation time.",
        "dining": "One signature meal per trip. Hawker / market crawls. Rooftop / view-bar evenings.",
    },
    "historical": {
        "label": "Historical / heritage",
        "what_to_prioritize": "Ruins, museums, ancient sites, war memorials, old quarters. Pre-book guided tours for context.",
        "what_to_skip": "Anything in the 'ancient but newly built' category (verify provenance). Surface-level photo stops.",
        "anchor_density": "1-2 deep-dive anchors/day, with a guide where possible.",
        "dining": "Period-appropriate / regional-historical dishes, not international chains.",
    },
}

_PACE_STRATEGY: dict[str, dict] = {
    "ambitious": {
        "label": "Ambitious / full days",
        "anchors_per_day": "2-3",
        "activity_hours_per_day": "8-10h/day",
        "rest_blocks": "One short rest block (30-60 min) at the hotel mid-afternoon. No full day off.",
        "transit_willingness": "Willing to spend 3-4h/day in transit. Heavy Transit Days OK if the destination is worth it.",
    },
    "moderate": {
        "label": "Moderate / balanced",
        "anchors_per_day": "2",
        "activity_hours_per_day": "6-8h/day",
        "rest_blocks": "Mid-day break (1-2h) plus early-evening down time.",
        "transit_willingness": "Max 2-3h/day in transit. Heavy Transit Days discouraged.",
    },
    "relaxed": {
        "label": "Relaxed / leisurely",
        "anchors_per_day": "1",
        "activity_hours_per_day": "4-6h/day",
        "rest_blocks": "Long mid-day break (2-3h). One full unscheduled day per week.",
        "transit_willingness": "Max 90 min/day. Heavy Transit Days are a no.",
    },
}

_ACCOMMODATION_STRATEGY: dict[str, dict] = {
    "comfort": {
        "label": "Comfort (3-4*)",
        "hotel_class": "Clean, central 3-4* hotel or well-reviewed guesthouse. No frills required.",
        "amenities_priority": ["central location", "clean room", "reliable wifi", "lift"],
        "room_requirements": "Private bathroom. Air-con or heating (depends on climate). Blackout curtains.",
        "skip": "Resort fees, club-lounge access, concierge.",
    },
    "premium": {
        "label": "Premium (4-5* boutique / design)",
        "hotel_class": "4-5* boutique or design hotel. Concierge service, on-site restaurant, character.",
        "amenities_priority": ["characterful property", "central location", "good bed", "on-site breakfast"],
        "room_requirements": "King or twin. Workspace. Bath. Mini-bar or nearby 24h store.",
        "skip": "Generic international chain hotels with no local character.",
    },
    "luxury": {
        "label": "Luxury (5* / suite / villa / signature)",
        "hotel_class": "5* hotel, suite-only, or villa / private stay. One signature property per trip.",
        "amenities_priority": ["private butler / concierge", "spa or signature wellness", "in-room dining", "view"],
        "room_requirements": "Suite or villa. Walk-in wardrobe. Soaking tub. Premium linens.",
        "skip": "Cookie-cutter 5* chain hotels with no signature experience.",
    },
}

_RHYTHM_STRATEGY: dict[str, dict] = {
    "early-starts": {
        "label": "Early starts",
        "morning": "06:30-07:30 wake, breakfast by 07:30, out by 08:30. Crowds avoided, golden hour, cool in summer.",
        "afternoon": "Sights by 09:00-12:00. Mid-day rest 12:00-15:00 (siesta / pool / nap).",
        "evening": "Dinner 18:00-19:30. Back to hotel 21:00-22:00.",
        "best_for": "Sunrise sights, summer heat, crowded tourist cities, photographers.",
    },
    "late-nights": {
        "label": "Late nights",
        "morning": "09:30-10:30 wake, breakfast by 10:30, out by 11:00.",
        "afternoon": "Sights 11:00-17:00. Late-afternoon coffee / snack 16:00-17:00.",
        "evening": "Aperitivo 18:00-20:00. Dinner 20:00-22:00. Night activities 22:00-24:00+.",
        "best_for": "Hot climates, night markets, urban / city trips, Mediterranean dinner culture.",
    },
}

# Watch-out contradictions — these combinations should warn (not block).
# Each entry: (companion, pace, rhythm, warning_message). None = wildcard.
_CONTRADICTION_WATCHES = [
    ("family", "ambitious", None,
     "Family + ambitious pace is hard to sustain — kids cap at 5h/day. Plan to drop one anchor on most days."),
    ("family", None, "late-nights",
     "Family + late-nights rhythm is contradictory. Young children need early dinners. Force 'early-starts' rhythm."),
    ("elderly", "ambitious", None,
     "Elderly + ambitious pace risks fatigue and injury. Force 'relaxed' pace (4h activity cap)."),
    ("elderly", None, "late-nights",
     "Elderly + late-nights is contradictory. Force 'early-starts' rhythm and 17:00 dinners."),
    ("friends", None, "early-starts",
     "Friends + early-starts rarely survives the first morning. Force 'late-nights' rhythm."),
    ("solo", None, "late-nights",
     "Solo + late-nights is the social sweet spot — flag to confirm the traveler is comfortable alone at night (esp. in unfamiliar cities)."),
    ("couple", "ambitious", "late-nights",
     "Couple + ambitious + late-nights is a stamina test. Verify both travelers want the same intensity — couples' trips often split here."),
]


# ---------------------------------------------------------------- helpers --

def normalize_destination(name: str) -> str:
    if not name:
        return ""
    raw = name.strip().lower()
    if raw in _SUNSET:
        return raw
    if raw in _ALIASES:
        return _ALIASES[raw]
    return raw


def parse_month(month: str) -> int | None:
    if not month:
        return None
    s = month.strip()
    m = re.match(r"^(\d{4})[-/](\d{1,2})$", s)
    if m:
        mm = int(m.group(2))
        return mm if 1 <= mm <= 12 else None
    m = re.match(r"^(\d{1,2})$", s)
    if m:
        mm = int(m.group(1))
        return mm if 1 <= mm <= 12 else None
    months = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
        "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    return months.get(s.lower())


def lookup_sunset(destination: str, month: int) -> str:
    key = normalize_destination(destination)
    row = _SUNSET.get(key)
    if not row:
        return "unknown"
    return row.get(month, "unknown")


def cutoff_from_sunset(sunset_hhmm: str, buffer_min: int = SUNSET_BUFFER_MINUTES) -> str:
    if not sunset_hhmm or sunset_hhmm == "unknown":
        return "unknown"
    try:
        hh_str, mm_str = sunset_hhmm.split(":")
        hh, mm = int(hh_str), int(mm_str)
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            return "unknown"
        total = hh * 60 + mm - buffer_min
        if total < 0:
            total += 24 * 60
        return f"{total // 60:02d}:{total % 60:02d}"
    except (ValueError, AttributeError):
        return "unknown"


def apply_transit_buffer(base_minutes: int) -> int:
    if base_minutes < 0:
        return 0
    return round(base_minutes * (1 + TRANSIT_BUFFER_PCT))


def is_heavy_transit(transit_minutes: int) -> bool:
    return transit_minutes > HEAVY_TRANSIT_MINUTES


def _resolve_companion(raw) -> str | None:
    if not raw:
        return None
    s = raw.strip().lower()
    if s in COMPANIONS:
        return s
    if s in _PERSONA_TO_COMPANION:
        return _PERSONA_TO_COMPANION[s]
    return None


def _resolve_accommodation(raw) -> str | None:
    if not raw:
        return None
    s = raw.strip().lower()
    if s in ACCOMMODATIONS:
        return s
    if s in _BUDGET_TO_ACCOMMODATION:
        return _BUDGET_TO_ACCOMMODATION[s]
    return None


def check_params(destination, month, companion, style, pace, accommodation, rhythm, transport):
    """Return (params_complete: bool, missing_params: list[str], errors: list[str])."""
    missing = []
    errors = []

    if not destination or not destination.strip():
        missing.append("destination")
    if month is None:
        missing.append("month")
    if transport not in ("public", "self-drive", "mixed"):
        if not transport:
            missing.append("transport")
        else:
            errors.append(f"invalid transport '{transport}' — must be one of public / self-drive / mixed")

    if not companion:
        missing.append("companion")
    elif companion not in COMPANIONS:
        errors.append(f"invalid companion '{companion}' — must be one of {COMPANIONS}")

    if not style:
        missing.append("style")
    elif style not in STYLES:
        errors.append(f"invalid style '{style}' — must be one of {STYLES}")

    if not pace:
        missing.append("pace")
    elif pace not in PACES:
        errors.append(f"invalid pace '{pace}' — must be one of {PACES}")

    if not accommodation:
        missing.append("accommodation")
    elif accommodation not in ACCOMMODATIONS:
        errors.append(f"invalid accommodation '{accommodation}' — must be one of {ACCOMMODATIONS}")

    if not rhythm:
        missing.append("rhythm")
    elif rhythm not in RHYTHMS:
        errors.append(f"invalid rhythm '{rhythm}' — must be one of {RHYTHMS}")

    return (len(missing) == 0 and len(errors) == 0, missing, errors)


def detect_contradictions(companion, pace, rhythm):
    """Return a list of warning strings for combinations that are unlikely
    to work. The agent uses these to ask the user or apply the safe default."""
    warnings = []
    for c, p, r, msg in _CONTRADICTION_WATCHES:
        if c is not None and companion != c:
            continue
        if p is not None and pace != p:
            continue
        if r is not None and rhythm != r:
            continue
        warnings.append(msg)
    return warnings


def build_warnings(destination, month, transport, sunset_hhmm, cutoff_hhmm, companion=None, pace=None, rhythm=None):
    warnings = []
    if sunset_hhmm == "unknown":
        warnings.append(
            f"Destination '{destination}' is not in the bundled sunset table — "
            "web-search the exact local sunset for the travel dates before "
            "scheduling outdoor / highway legs."
        )
    else:
        warnings.append(
            f"Local sunset {sunset_hhmm} in {destination} for month {month} — "
            f"terminate all outdoor / highway driving by {cutoff_hhmm}."
        )
    if transport == "self-drive":
        warnings.append(
            "Self-drive selected — add 30% buffer to all GPS estimates for "
            "unfamiliar roads, parking, and check-in. Never drive after cutoff."
        )
    if month in (12, 1, 2):
        warnings.append("Winter month — pack layers and watch for icy / wet roads in northern destinations.")
    if month in (6, 7, 8):
        warnings.append("Peak / monsoon season for many Southeast Asia destinations — book transport early.")
    if month in (3, 4, 10, 11):
        warnings.append("Shoulder / peak-period month — popular sights will be busy; arrive early.")
    if companion and pace and rhythm:
        warnings.extend(detect_contradictions(companion, pace, rhythm))
    return warnings


def build_companion_strategy(companion):
    return _COMPANION_STRATEGY.get(companion) if companion else None


def build_style_strategy(style):
    return _STYLE_STRATEGY.get(style) if style else None


def build_pace_strategy(pace):
    return _PACE_STRATEGY.get(pace) if pace else None


def build_accommodation_strategy(accommodation):
    return _ACCOMMODATION_STRATEGY.get(accommodation) if accommodation else None


def build_rhythm_strategy(rhythm):
    return _RHYTHM_STRATEGY.get(rhythm) if rhythm else None


def build_report(args) -> dict:
    """Compose the JSON report the agent consumes."""
    month_int = parse_month(args.month or "")

    # Resolve 5 preference dimensions, with deprecated alias fallback.
    companion = _resolve_companion(getattr(args, "companion", None))
    if not companion and getattr(args, "persona", None):
        companion = _resolve_companion(args.persona)
    accommodation = _resolve_accommodation(getattr(args, "accommodation", None))
    if not accommodation and getattr(args, "budget", None):
        accommodation = _resolve_accommodation(args.budget)
    style = (getattr(args, "style", None) or "").strip().lower() or None
    pace = (getattr(args, "pace", None) or "").strip().lower() or None
    rhythm = (getattr(args, "rhythm", None) or "").strip().lower() or None

    params_complete, missing, errors = check_params(
        args.destination, month_int, companion, style, pace, accommodation, rhythm, args.transport
    )
    sunset = lookup_sunset(args.destination or "", month_int) if (args.destination and month_int) else "unknown"
    cutoff = cutoff_from_sunset(sunset)
    warnings = build_warnings(args.destination or "", month_int, args.transport, sunset, cutoff, companion, pace, rhythm)
    preference_strategy = {
        "companion": build_companion_strategy(companion),
        "style": build_style_strategy(style),
        "pace": build_pace_strategy(pace),
        "accommodation": build_accommodation_strategy(accommodation),
        "rhythm": build_rhythm_strategy(rhythm),
    }
    return {
        "origin": SG_ORIGIN,
        "destination": args.destination or None,
        "month": args.month or None,
        "month_resolved": month_int,
        "transport": args.transport or None,
        "preferences": {
            "companion": companion,
            "style": style,
            "pace": pace,
            "accommodation": accommodation,
            "rhythm": rhythm,
        },
        "preference_strategy": preference_strategy,
        "params_complete": params_complete,
        "missing_params": missing,
        "errors": errors,
        "sunset_local": sunset,
        "cutoff_local": cutoff,
        "warnings": warnings,
        "transit_buffer_pct": int(TRANSIT_BUFFER_PCT * 100),
        "heavy_transit_minutes": HEAVY_TRANSIT_MINUTES,
    }


# ------------------------------------------------------------------- CLI ----

def main(argv=None):
    p = argparse.ArgumentParser(
        description="Overseas Trip Planner — Singapore-origin travel helpers (5-dim preferences).",
    )
    p.add_argument("--destination", help="Primary city or region, e.g. 'Kyoto' or 'Hokkaido'.")
    p.add_argument("--month", help="YYYY-MM, YYYY/MM, MM, or month name, e.g. '2026-11' or 'November 2026'.")
    p.add_argument("--transport", help="Primary transport mode (public / self-drive / mixed).")
    # 5 preference dimensions
    p.add_argument("--companion", help="Travel companion (solo / couple / family / friends / elderly).")
    p.add_argument("--style", help="Travel style (cultural / classic / nature / cityscape / historical).")
    p.add_argument("--pace", help="Travel pace (ambitious / moderate / relaxed).")
    p.add_argument("--accommodation", help="Accommodation tier (comfort / premium / luxury).")
    p.add_argument("--rhythm", help="Day's rhythm (early-starts / late-nights).")
    # Deprecated aliases (kept for back-compat — the LLM is the only caller)
    p.add_argument("--persona", help=argparse.SUPPRESS, default=None)
    p.add_argument("--budget", help=argparse.SUPPRESS, default=None)
    p.add_argument("--json", action="store_true", help="Emit JSON to stdout.")
    args = p.parse_args(argv)

    report = build_report(args)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["params_complete"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
