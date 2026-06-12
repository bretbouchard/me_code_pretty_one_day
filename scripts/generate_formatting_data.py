#!/usr/bin/env python3
"""
Generate formatting training data using real code formatters.

Takes clean code samples, deliberately minifies/messes them up, then uses
real formatters to produce the canonical output. Each before/after pair
becomes a training sample in the open-coder-leaderboard chat format.

Supported languages and formatters:
  Python:  black, ruff
  JS/TS:   prettier
  Rust:    rustfmt

Usage:
  python3 scripts/generate_formatting_data.py --samples 500 --output data/formatting_train.jsonl
  python3 scripts/generate_formatting_data.py --samples 500 --output data/formatting_val.jsonl --seed 42
"""

import glob

import argparse
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SYSTEM_PROMPT = "You are a code formatting assistant. Given messy or minified code, output only the cleanly formatted version with consistent style, proper indentation, and standard spacing."

# --- Clean code corpus per language ---

PYTHON_CORPUS = [
    # Functions
    """\
def calculate_average(numbers):
    total = sum(numbers)
    count = len(numbers)
    if count == 0:
        return 0.0
    return total / count
""",
    """\
def find_max_min(data):
    if not data:
        return None, None
    maximum = minimum = data[0]
    for value in data[1:]:
        if value > maximum:
            maximum = value
        if value < minimum:
            minimum = value
    return maximum, minimum
""",
    """\
def is_palindrome(s):
    cleaned = ''.join(c.lower() for c in s if c.isalnum())
    return cleaned == cleaned[::-1]
""",
    """\
def flatten(nested_list):
    result = []
    for item in nested_list:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result
""",
    """\
def count_words(text):
    words = text.split()
    freq = {}
    for word in words:
        word = word.lower().strip('.,!?;:')
        freq[word] = freq.get(word, 0) + 1
    return freq
""",
    """\
def merge_dicts(dict_a, dict_b):
    merged = dict_a.copy()
    for key, value in dict_b.items():
        if key in merged:
            merged[key] = merged[key] + value
        else:
            merged[key] = value
    return merged
""",
    """\
def chunk_list(lst, size):
    chunks = []
    for i in range(0, len(lst), size):
        chunks.append(lst[i:i + size])
    return chunks
""",
    """\
def binary_search(arr, target):
    low, high = 0, len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
""",
    # Classes
    """\
class Stack:
    def __init__(self):
        self._items = []

    def push(self, item):
        self._items.append(item)

    def pop(self):
        if self.is_empty():
            raise IndexError("pop from empty stack")
        return self._items.pop()

    def peek(self):
        if self.is_empty():
            raise IndexError("peek at empty stack")
        return self._items[-1]

    def is_empty(self):
        return len(self._items) == 0

    def size(self):
        return len(self._items)
""",
    """\
class Circle:
    def __init__(self, radius):
        self.radius = radius

    @property
    def area(self):
        return 3.14159 * self.radius ** 2

    @property
    def circumference(self):
        return 2 * 3.14159 * self.radius

    def __repr__(self):
        return f"Circle(radius={self.radius})"
""",
    """\
class Book:
    def __init__(self, title, author, pages):
        self.title = title
        self.author = author
        self.pages = pages

    def __eq__(self, other):
        if not isinstance(other, Book):
            return False
        return self.title == other.title and self.author == other.author

    def __hash__(self):
        return hash((self.title, self.author))

    def __str__(self):
        return f'"{self.title}" by {self.author} ({self.pages} pages)'
""",
    """\
class Counter:
    def __init__(self, start=0):
        self._value = start

    def increment(self, amount=1):
        self._value += amount

    def decrement(self, amount=1):
        self._value -= amount

    def reset(self):
        self._value = 0

    @property
    def value(self):
        return self._value
""",
    # Async
    """\
import asyncio


async def fetch_all(urls):
    async def fetch_one(url):
        await asyncio.sleep(0.1)
        return f"data from {url}"

    tasks = [fetch_one(url) for url in urls]
    return await asyncio.gather(*tasks)
""",
    """\
import asyncio


class RateLimiter:
    def __init__(self, rate, per_seconds):
        self.rate = rate
        self.per_seconds = per_seconds
        self.timestamps = []

    async def acquire(self):
        now = asyncio.get_event_loop().time()
        self.timestamps = [
            t for t in self.timestamps
            if now - t < self.per_seconds
        ]
        if len(self.timestamps) >= self.rate:
            wait = self.per_seconds - (now - self.timestamps[0])
            await asyncio.sleep(wait)
        self.timestamps.append(asyncio.get_event_loop().time())
""",
    # Data structures
    """\
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Task:
    title: str
    description: str
    priority: int = 0
    tags: Optional[List[str]] = None
    completed: bool = False

    def complete(self):
        self.completed = True
""",
    """\
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Inventory:
    items: Dict[str, int] = field(default_factory=dict)

    def add(self, name, quantity):
        self.items[name] = self.items.get(name, 0) + quantity

    def remove(self, name, quantity):
        if name not in self.items:
            raise ValueError(f"No such item: {name}")
        if self.items[name] < quantity:
            raise ValueError(f"Not enough {name}")
        self.items[name] -= quantity
        if self.items[name] == 0:
            del self.items[name]

    def total_count(self):
        return sum(self.items.values())
""",
    # Decorators / patterns
    """\
import time
from functools import wraps


def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"{func.__name__} took {elapsed:.4f}s")
        return result
    return wrapper
""",
    """\
import time
from functools import wraps


def retry(max_attempts=3, delay=1.0, exceptions=(Exception,)):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay * (attempt + 1))
            raise last_exc
        return wrapper
    return decorator
""",
    # comprehensions / functional
    """\
def process_data(records):
    filtered = [r for r in records if r.get('active', False)]
    mapped = [{'id': r['id'], 'name': r['name'].upper()} for r in filtered]
    return sorted(mapped, key=lambda x: x['name'])
""",
    """\
def group_by(items, key_func):
    groups = {}
    for item in items:
        key = key_func(item)
        groups.setdefault(key, []).append(item)
    return groups
""",
    # file I/O patterns
    """\
import json
from pathlib import Path


def read_config(path):
    p = Path(path)
    if not p.exists():
        return {}
    with p.open('r', encoding='utf-8') as f:
        return json.load(f)
""",
    """\
import csv
from pathlib import Path


def load_csv(path):
    rows = []
    with Path(path).open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows
""",
]

JS_CORPUS = [
    """\
function debounce(fn, delay) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}
""",
    """\
function deepClone(obj) {
  if (obj === null || typeof obj !== 'object') return obj;
  if (obj instanceof Date) return new Date(obj.getTime());
  if (Array.isArray(obj)) return obj.map((item) => deepClone(item));
  const cloned = Object.create(Object.getPrototypeOf(obj));
  for (const key of Object.keys(obj)) {
    cloned[key] = deepClone(obj[key]);
  }
  return cloned;
}
""",
    """\
class EventEmitter {
  constructor() {
    this.listeners = new Map();
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  emit(event, ...args) {
    const callbacks = this.listeners.get(event) || [];
    callbacks.forEach((cb) => cb(...args));
  }

  off(event, callback) {
    const callbacks = this.listeners.get(event) || [];
    this.listeners.set(
      event,
      callbacks.filter((c) => c !== callback),
    );
  }
}
""",
    """\
async function paginate(endpoint, pageSize = 20) {
  let page = 1;
  let hasMore = true;

  while (hasMore) {
    const response = await fetch(
      `${endpoint}?page=${page}&size=${pageSize}`,
    );
    const data = await response.json();

    if (data.items.length < pageSize) {
      hasMore = false;
    }

    for (const item of data.items) {
      yield item;
    }

    page++;
  }
}
""",
    """\
function throttle(fn, limit) {
  let lastCall = 0;
  return function (...args) {
    const now = Date.now();
    if (now - lastCall >= limit) {
      lastCall = now;
      fn.apply(this, args);
    }
  };
}
""",
    """\
function chunk(array, size) {
  const chunks = [];
  for (let i = 0; i < array.length; i += size) {
    chunks.push(array.slice(i, i + size));
  }
  return chunks;
}
""",
    """\
function deepEqual(a, b) {
  if (a === b) return true;
  if (typeof a !== typeof b) return false;
  if (a === null || b === null) return false;

  if (Array.isArray(a)) {
    if (a.length !== b.length) return false;
    return a.every((v, i) => deepEqual(v, b[i]));
  }

  if (typeof a === 'object') {
    const keysA = Object.keys(a);
    const keysB = Object.keys(b);
    if (keysA.length !== keysB.length) return false;
    return keysA.every((key) => deepEqual(a[key], b[key]));
  }

  return false;
}
""",
    """\
function groupBy(array, keyFn) {
  const groups = {};
  for (const item of array) {
    const key = keyFn(item);
    if (!groups[key]) groups[key] = [];
    groups[key].push(item);
  }
  return groups;
}
""",
    """\
function uniqueBy(array, keyFn) {
  const seen = new Set();
  return array.filter((item) => {
    const key = keyFn(item);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
""",
    """\
const retry = async (fn, maxAttempts = 3, delay = 1000) => {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (attempt === maxAttempts) throw error;
      await new Promise((r) => setTimeout(r, delay * attempt));
    }
  }
};
""",
]

TS_CORPUS = [
    """\
interface User {
  name: string;
  email: string;
  age: number;
  address?: {
    street: string;
    city: string;
    zip: string;
  };
}

function validateUser(user: User): boolean {
  return (
    user.name.length > 0 &&
    user.email.includes('@') &&
    user.age >= 18
  );
}
""",
    """\
type Result<T, E> = Success<T> | Failure<E>;

interface Success<T> {
  ok: true;
  value: T;
}

interface Failure<E> {
  ok: false;
  error: E;
}

function tryParse(json: string): Result<unknown, Error> {
  try {
    return { ok: true, value: JSON.parse(json) };
  } catch (e) {
    return { ok: false, error: e as Error };
  }
}
""",
    """\
function createLookupMap<T extends string>(
  items: readonly T[],
): Map<T, number> {
  const map = new Map<T, number>();
  items.forEach((item, index) => {
    map.set(item, index);
  });
  return map;
}
""",
    """\
interface Config {
  host: string;
  port: number;
  debug: boolean;
  retries?: number;
}

function mergeConfig(
  defaults: Config,
  overrides: Partial<Config>,
): Config {
  return { ...defaults, ...overrides };
}
""",
    """\
type EventHandler<T = void> = T extends void
  ? () => void
  : (data: T) => void;

class TypedEventEmitter<TEvents extends Record<string, unknown>> {
  private handlers = new Map<
    keyof TEvents,
    Set<EventHandler<any>>
  >();

  on<K extends keyof TEvents>(
    event: K,
    handler: EventHandler<TEvents[K]>,
  ): void {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set());
    }
    this.handlers.get(event)!.add(handler);
  }

  off<K extends keyof TEvents>(
    event: K,
    handler: EventHandler<TEvents[K]>,
  ): void {
    this.handlers.get(event)?.delete(handler);
  }

  emit<K extends keyof TEvents>(
    event: K,
    data: TEvents[K],
  ): void {
    this.handlers.get(event)?.forEach((handler) =>
      handler(data),
    );
  }
}
""",
]

RUST_CORPUS = [
    """\
#[derive(Debug, Clone)]
pub struct Config {
    pub host: String,
    pub port: u16,
    pub workers: usize,
}

impl Config {
    pub fn from_env() -> Result<Self, Box<dyn std::error::Error>> {
        let host = std::env::var("HOST")
            .unwrap_or_else(|_| "127.0.0.1".to_string());
        let port = std::env::var("PORT")
            .unwrap_or_else(|_| "8080".to_string())
            .parse::<u16>()?;
        let workers = std::env::var("WORKERS")
            .unwrap_or_else(|_| "4".to_string())
            .parse::<usize>()?;
        Ok(Self {
            host,
            port,
            workers,
        })
    }
}
""",
    """\
use std::collections::HashMap;

fn word_count(text: &str) -> HashMap<&str, usize> {
    let mut counts = HashMap::new();
    for word in text.split_whitespace() {
        let cleaned: &str = word
            .trim_matches(|c: char| !c.is_alphanumeric());
        *counts.entry(cleaned).or_insert(0) += 1;
    }
    counts
}
""",
    """\
pub struct Stack<T> {
    items: Vec<T>,
}

impl<T> Stack<T> {
    pub fn new() -> Self {
        Self { items: Vec::new() }
    }

    pub fn push(&mut self, item: T) {
        self.items.push(item);
    }

    pub fn pop(&mut self) -> Option<T> {
        self.items.pop()
    }

    pub fn peek(&self) -> Option<&T> {
        self.items.last()
    }

    pub fn len(&self) -> usize {
        self.items.len()
    }

    pub fn is_empty(&self) -> bool {
        self.items.is_empty()
    }
}
""",
    """\
fn merge_sort<T: Ord + Clone>(arr: &mut [T]) {
    if arr.len() <= 1 {
        return;
    }
    let mid = arr.len() / 2;
    merge_sort(&mut arr[..mid]);
    merge_sort(&mut arr[mid..]);

    let mut result = Vec::new();
    let mut i = 0;
    let mut j = mid;

    while i < mid && j < arr.len() {
        if arr[i] <= arr[j] {
            result.push(arr[i].clone());
            i += 1;
        } else {
            result.push(arr[j].clone());
            j += 1;
        }
    }
    result.extend_from_slice(&arr[i..mid]);
    result.extend_from_slice(&arr[j..]);
    arr.clone_from_slice(&result);
}
""",
]

# --- Lint-fixing corpus (code with common lint violations) ---

LINT_SYSTEM_PROMPT = "You are a code quality assistant. Fix all lint violations, bugs, and code quality issues in the provided code. Output only the fixed code with no explanation."

PYTHON_LINT_CORPUS = [
    # unused imports
    {"bad": "import os\nimport sys\nimport json\n\ndef load_data(path):\n    with open(path) as f:\n        return json.load(f)",
     "good": "import json\n\n\ndef load_data(path):\n    with open(path) as f:\n        return json.load(f)"},
    # mutable default argument
    {"bad": "def add_item(items=[]):\n    items.append('new')\n    return items",
     "good": "def add_item(items=None):\n    if items is None:\n        items = []\n    items.append('new')\n    return items"},
    # bare except
    {"bad": "try:\n    result = do_something()\nexcept:\n    result = None",
     "good": "try:\n    result = do_something()\nexcept Exception:\n    result = None"},
    # unused variable
    {"bad": "def get_name(user):\n    name = user['name']\n    email = user['email']\n    return name",
     "good": "def get_name(user):\n    return user['name']"},
    # == None comparison
    {"bad": "def check(value):\n    if value == None:\n        return 'empty'\n    return 'has value'",
     "good": "def check(value):\n    if value is None:\n        return 'empty'\n    return 'has value'"},
    # missing f-string (string concatenation)
    {"bad": "def greet(name):\n    message = 'Hello, ' + name + '!'\n    print(message)",
     "good": "def greet(name):\n    message = f'Hello, {name}!'\n    print(message)"},
    # key error risk
    {"bad": "def get_age(data):\n    return data['age']",
     "good": "def get_age(data):\n    return data.get('age')"},
    # list index without guard
    {"bad": "def first_item(items):\n    return items[0]",
     "good": "def first_item(items):\n    if not items:\n        return None\n    return items[0]"},
    # isinstance with tuple
    {"bad": "def process(value):\n    if type(value) == int or type(value) == float:\n        return value * 2\n    return value",
     "good": "def process(value):\n    if isinstance(value, (int, float)):\n        return value * 2\n    return value"},
    # shadowing built-in
    {"bad": "def calculate(list):\n    total = sum(list)\n    return total",
     "good": "def calculate(items):\n    return sum(items)"},
    # missing return type + bare return
    {"bad": "def divide(a, b):\n    if b == 0:\n        return\n    return a / b",
     "good": "def divide(a, b):\n    if b == 0:\n        return None\n    return a / b"},
    # global variable usage
    {"bad": "cache = {}\n\ndef get_cached(key):\n    global cache\n    if key not in cache:\n        cache[key] = compute(key)\n    return cache[key]",
     "good": "_cache = {}\n\n\ndef get_cached(key):\n    if key not in _cache:\n        _cache[key] = compute(key)\n    return _cache[key]"},
    # verbose boolean check
    {"bad": "def is_active(user):\n    if user.active == True:\n        return True\n    else:\n        return False",
     "good": "def is_active(user):\n    return user.active"},
    # nested if flattening
    {"bad": "def can_access(user):\n    if user.authenticated:\n        if user.role == 'admin':\n            return True\n    return False",
     "good": "def can_access(user):\n    return user.authenticated and user.role == 'admin'"},
]

JS_LINT_CORPUS = [
    {"bad": "var name = 'world';\nconsole.log('Hello ' + name);",
     "good": "const name = 'world';\nconsole.log(`Hello ${name}`);"},
    {"bad": "function getData() {\n  var result = fetch('/api');\n  return result;\n}",
     "good": "async function getData() {\n  const result = await fetch('/api');\n  return result;\n}"},
    {"bad": "const items = [1, 2, 3];\nfor (var i = 0; i < items.length; i++) {\n  console.log(items[i]);\n}",
     "good": "const items = [1, 2, 3];\nfor (const item of items) {\n  console.log(item);\n}"},
    {"bad": "if (user.age != null) {\n  process(user);\n}",
     "good": "if (user.age !== null) {\n  process(user);\n}"},
    {"bad": "var config = {};\nconfig.host = 'localhost';\nconfig.port = 8080;",
     "good": "const config = {\n  host: 'localhost',\n  port: 8080,\n};"},
    {"bad": "function add(a, b) {\n  result = a + b;\n  return result;\n}",
     "good": "function add(a, b) {\n  const result = a + b;\n  return result;\n}"},
    {"bad": "const data = response.data;\nconst items = data.items;\nconst first = items[0];",
     "good": "const first = response?.data?.items?.[0];"},
    {"bad": "if (error) {\n  console.log('Error: ' + error.message);\n  console.log('Stack: ' + error.stack);\n}",
     "good": "if (error) {\n  console.error('Error:', error.message);\n  console.error('Stack:', error.stack);\n}"},
]

# --- Refactoring corpus (naive code → clean patterns) ---

REFACTOR_SYSTEM_PROMPT = "You are a code refactoring assistant. Improve the code quality, readability, and structure while preserving the same behavior. Output only the refactored code with no explanation."

PYTHON_REFACTOR_CORPUS = [
    {"bad": "def process_order(order):\n    if order['status'] == 'shipped':\n        return True\n    elif order['status'] == 'delivered':\n        return True\n    elif order['status'] == 'processing':\n        return False\n    else:\n        return False",
     "good": "def process_order(order):\n    return order['status'] in ('shipped', 'delivered')"},
    {"bad": "def get_discount(price, customer_type):\n    if customer_type == 'premium':\n        return price * 0.8\n    elif customer_type == 'standard':\n        return price * 0.9\n    elif customer_type == 'basic':\n        return price * 0.95\n    else:\n        return price",
     "good": "DISCOUNT_RATES = {\n    'premium': 0.8,\n    'standard': 0.9,\n    'basic': 0.95,\n}\n\n\ndef get_discount(price, customer_type):\n    rate = DISCOUNT_RATES.get(customer_type, 1.0)\n    return price * rate"},
    {"bad": "def validate_email(email):\n    if email is not None:\n        if '@' in email:\n            if '.' in email.split('@')[1]:\n                return True\n    return False",
     "good": "def validate_email(email):\n    if not email:\n        return False\n    parts = email.split('@')\n    return len(parts) == 2 and '.' in parts[1]"},
    {"bad": "users = []\nfor i in range(len(data)):\n    if data[i]['active']:\n        users.append(data[i]['name'])",
     "good": "users = [item['name'] for item in data if item['active']]"},
    {"bad": "total = 0\nfor item in items:\n    if item.category == 'food':\n        if item.price > 10:\n            total += item.price * 0.9\n        else:\n            total += item.price",
     "good": "def calculate_food_total(items):\n    total = 0\n    for item in items:\n        if item['category'] == 'food':\n            total += item['price'] * (0.9 if item['price'] > 10 else 1.0)\n    return total"},
    {"bad": "config = {}\nconfig['host'] = 'localhost'\nconfig['port'] = 8080\nconfig['debug'] = True\nconfig['workers'] = 4",
     "good": "config = {\n    'host': 'localhost',\n    'port': 8080,\n    'debug': True,\n    'workers': 4,\n}"},
    {"bad": "def send_notification(user, message):\n    if user.preferences.email:\n        send_email(user.email, message)\n    if user.preferences.sms:\n        send_sms(user.phone, message)\n    if user.preferences.push:\n        send_push(user.device, message)",
     "good": "def send_notification(user, message):\n    channels = []\n    if user.preferences.email:\n        channels.append(('email', user.email))\n    if user.preferences.sms:\n        channels.append(('sms', user.phone))\n    if user.preferences.push:\n        channels.append(('push', user.device))\n    for channel, target in channels:\n        _send(channel, target, message)\n\n\ndef _send(channel, target, message):\n    senders = {\n        'email': send_email,\n        'sms': send_sms,\n        'push': send_push,\n    }\n    senders[channel](target, message)"},
    {"bad": "result = []\nfor x in range(1, 11):\n    if x % 2 == 0:\n        result.append(x * x)\nprint(result)",
     "good": "squares = [x * x for x in range(1, 11) if x % 2 == 0]\nprint(squares)"},
]

JS_REFACTOR_CORPUS = [
    {"bad": "function getGreeting(timeOfDay) {\n  if (timeOfDay === 'morning') {\n    return 'Good morning';\n  } else if (timeOfDay === 'afternoon') {\n    return 'Good afternoon';\n  } else if (timeOfDay === 'evening') {\n    return 'Good evening';\n  } else {\n    return 'Hello';\n  }\n}",
     "good": "function getGreeting(timeOfDay) {\n  const greetings = {\n    morning: 'Good morning',\n    afternoon: 'Good afternoon',\n    evening: 'Good evening',\n  };\n  return greetings[timeOfDay] || 'Hello';\n}"},
    {"bad": "let total = 0;\nfor (let i = 0; i < prices.length; i++) {\n  if (prices[i] > 0) {\n    total += prices[i];\n  }\n}",
     "good": "const total = prices.filter((p) => p > 0).reduce((sum, p) => sum + p, 0);"},
    {"bad": "function findUser(users, id) {\n  for (let i = 0; i < users.length; i++) {\n    if (users[i].id === id) {\n      return users[i];\n    }\n  }\n  return null;\n}",
     "good": "function findUser(users, id) {\n  return users.find((user) => user.id === id) ?? null;\n}"},
    {"bad": "function formatDate(date) {\n  const year = date.getFullYear();\n  const month = String(date.getMonth() + 1).padStart(2, '0');\n  const day = String(date.getDate()).padStart(2, '0');\n  return year + '-' + month + '-' + day;\n}",
     "good": "function formatDate(date) {\n  return date.toISOString().split('T')[0];\n}"},
    {"bad": "let config = { debug: false };\nif (process.env.DEBUG === 'true') {\n  config.debug = true;\n}\nif (process.env.LOG_LEVEL) {\n  config.logLevel = process.env.LOG_LEVEL;\n} else {\n  config.logLevel = 'info';\n}",
     "good": "const config = {\n  debug: process.env.DEBUG === 'true',\n  logLevel: process.env.LOG_LEVEL || 'info',\n};"},
]


# --- Minification strategies ---

def minify_python(code: str) -> str:
    """Apply random minification to Python code."""
    result = code
    strategies = random.randint(2, 5)
    for _ in range(strategies):
        roll = random.random()
        if roll < 0.3:
            # Collapse all extra blank lines
            result = re.sub(r'\n{2,}', '\n', result)
        elif roll < 0.5:
            # Remove spaces around operators (safe subset)
            for op in ['+=', '-=', '*=', '%=', '==', '!=', '>=', '<=']:
                result = result.replace(f' {op} ', op)
        elif roll < 0.7:
            # Join some lines with semicolons (within function bodies)
            lines = result.split('\n')
            new_lines = []
            i = 0
            while i < len(lines):
                line = lines[i].rstrip()
                # Only join simple statements (no control flow, no comments)
                if (i + 1 < len(lines)
                    and '=' in line
                    and not line.strip().startswith(('if ', 'else', 'for ', 'while ', 'def ', 'class ', 'return', 'import', 'from', 'try', 'except', 'finally', 'with', 'async'))
                    and not lines[i + 1].strip().startswith(('if ', 'else', 'for ', 'while ', 'def ', 'class ', 'return', 'import', 'from', 'try', 'except', 'finally', 'with', 'async', '#'))
                    and not lines[i + 1].strip() == ''
                    and lines[i + 1].strip() != ''):
                    next_line = lines[i + 1].strip()
                    if '=' in next_line and '#' not in next_line:
                        new_lines.append(line + ';' + next_line)
                        i += 2
                        continue
                new_lines.append(line)
                i += 1
            result = '\n'.join(new_lines)
        elif roll < 0.85:
            # Remove spaces after commas in function signatures/calls
            result = re.sub(r',\s+', ',', result)
        else:
            # Remove trailing/leading whitespace on lines
            lines = result.split('\n')
            result = '\n'.join(l.rstrip() for l in lines)
    return result


def minify_js(code: str) -> str:
    """Apply random minification to JavaScript/TypeScript."""
    result = code
    strategies = random.randint(2, 4)
    for _ in range(strategies):
        roll = random.random()
        if roll < 0.3:
            # Collapse blank lines
            result = re.sub(r'\n{2,}', '\n', result)
        elif roll < 0.5:
            # Remove spaces around operators
            for op in ['===', '!==', '>=', '<=', '&&', '||', '+=', '-=']:
                result = result.replace(f' {op} ', op)
            result = result.replace('=> ', '=>')
        elif roll < 0.7:
            # Remove spaces after commas
            result = re.sub(r',\s+', ',', result)
        elif roll < 0.85:
            # Remove spaces after colons in type annotations
            result = re.sub(r':\s+(\w)', r':\1', result)
        else:
            # Put short blocks on one line
            lines = result.split('\n')
            new_lines = []
            i = 0
            while i < len(lines):
                line = lines[i]
                stripped = line.strip()
                # If it's a simple return or assignment followed by closing brace
                if (i + 1 < len(lines)
                    and stripped.startswith(('return ', 'const ', 'let '))
                    and lines[i + 1].strip() == '}'):
                    new_lines.append(line.rstrip() + ' ' + lines[i + 1].strip())
                    i += 2
                    continue
                new_lines.append(line)
                i += 1
            result = '\n'.join(new_lines)
    return result


def minify_rust(code: str) -> str:
    """Apply random minification to Rust."""
    result = code
    strategies = random.randint(2, 4)
    for _ in range(strategies):
        roll = random.random()
        if roll < 0.35:
            result = re.sub(r'\n{2,}', '\n', result)
        elif roll < 0.6:
            result = re.sub(r',\s+', ',', result)
        elif roll < 0.8:
            # Remove spaces after colons in type annotations
            result = re.sub(r':\s+(&?\w)', r':\1', result)
        else:
            # Remove spaces around -> in return types
            result = result.replace(' -> ', '->')
    return result


# --- Formatter runners ---

def format_python(code: str) -> str:
    """Format Python code with black."""
    proc = subprocess.run(
        ['black', '-', '--quiet', '--line-length=88'],
        input=code.encode('utf-8'),
        capture_output=True,
    )
    if proc.returncode == 0:
        return proc.stdout.decode('utf-8')
    return code  # fallback to input if black fails


def format_js(code: str, lang: str = 'javascript') -> str:
    """Format JS/TS with prettier."""
    parser = 'typescript' if lang == 'typescript' else 'babel'
    proc = subprocess.run(
        ['prettier', '--parser', parser, '--single-quote', '--print-width=80'],
        input=code.encode('utf-8'),
        capture_output=True,
    )
    if proc.returncode == 0:
        return proc.stdout.decode('utf-8')
    return code


def format_rust(code: str) -> str:
    """Format Rust with rustfmt."""
    proc = subprocess.run(
        ['rustfmt'],
        input=code.encode('utf-8'),
        capture_output=True,
    )
    if proc.returncode == 0:
        return proc.stdout.decode('utf-8')
    return code


# --- Sample generation ---

LANGUAGE_CONFIG = [
    ('python', PYTHON_CORPUS, minify_python, format_python, '```python\n{}\n```'),
    ('javascript', JS_CORPUS, minify_js, lambda c: format_js(c, 'javascript'), '```javascript\n{}\n```'),
    ('typescript', TS_CORPUS, minify_js, lambda c: format_js(c, 'typescript'), '```typescript\n{}\n```'),
    ('rust', RUST_CORPUS, minify_rust, format_rust, '```rust\n{}\n```'),
]


def generate_sample(corpus, minify_fn, format_fn, fence_template, rng):
    """Generate a single formatting training sample."""
    clean = rng.choice(corpus)

    # Format with the real formatter (ground truth)
    formatted = format_fn(clean)

    # Minify the formatted version (model input)
    minified = minify_fn(formatted)

    # Skip if minification didn't change anything meaningful
    if minified.strip() == formatted.strip():
        return None

    user_msg = (
        f"Format this code:\n{fence_template.format(minified.strip())}"
    )
    assistant_msg = fence_template.format(formatted.strip())

    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": assistant_msg},
        ]
    }


def generate_dataset(num_samples, seed, max_per_corpus=None):
    """Generate the full dataset."""
    rng = random.Random(seed)
    samples = []
    attempts = 0
    max_attempts = num_samples * 10  # safety valve

    lang_counts = {lang: 0 for lang, *_ in LANGUAGE_CONFIG}

    while len(samples) < num_samples and attempts < max_attempts:
        lang, corpus, minify_fn, format_fn, fence = rng.choice(LANGUAGE_CONFIG)

        # Track per-corpus limits
        if max_per_corpus and lang_counts[lang] >= max_per_corpus:
            attempts += 1
            continue

        sample = generate_sample(corpus, minify_fn, format_fn, fence, rng)
        if sample is not None:
            samples.append(sample)
            lang_counts[lang] += 1
        attempts += 1

    return samples, lang_counts


def generate_lint_sample(pair, lang, rng):
    """Generate a lint-fixing training sample."""
    fence = {'python': '```python\n{}\n```', 'javascript': '```javascript\n{}\n```'}[lang]
    return {
        "messages": [
            {"role": "system", "content": LINT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Fix the issues in this code:\n{fence.format(pair['bad'])}"},
            {"role": "assistant", "content": fence.format(pair['good'])},
        ]
    }


def generate_refactor_sample(pair, lang, rng):
    """Generate a refactoring training sample."""
    fence = {'python': '```python\n{}\n```', 'javascript': '```javascript\n{}\n```'}[lang]
    return {
        "messages": [
            {"role": "system", "content": REFACTOR_SYSTEM_PROMPT},
            {"role": "user", "content": f"Refactor this code to be cleaner and more idiomatic:\n{fence.format(pair['bad'])}"},
            {"role": "assistant", "content": fence.format(pair['good'])},
        ]
    }


def generate_lint_dataset(num_samples, seed):
    """Generate lint-fixing samples."""
    rng = random.Random(seed)
    samples = []
    all_pairs = [(p, 'python') for p in PYTHON_LINT_CORPUS] + [(p, 'javascript') for p in JS_LINT_CORPUS]
    for _ in range(num_samples):
        pair, lang = rng.choice(all_pairs)
        samples.append(generate_lint_sample(pair, lang, rng))
    return samples


def generate_refactor_dataset(num_samples, seed):
    """Generate refactoring samples."""
    rng = random.Random(seed)
    samples = []
    all_pairs = [(p, 'python') for p in PYTHON_REFACTOR_CORPUS] + [(p, 'javascript') for p in JS_REFACTOR_CORPUS]
    for _ in range(num_samples):
        pair, lang = rng.choice(all_pairs)
        samples.append(generate_refactor_sample(pair, lang, rng))
    return samples


# Scraped corpus uses short directory names — map to language keys
CORPUS_DIR_NAMES = {
    "python": ["py", "pyi"],
    "javascript": ["js"],
    "typescript": ["ts", "d.ts"],
    "rust": ["rs"],
}


def load_corpus_files(corpus_dir: str, lang: str, max_files: int) -> list[str]:
    """Load scraped code files from a corpus directory."""
    if not corpus_dir or not os.path.isdir(corpus_dir):
        return []
    snippets = []
    dir_names = CORPUS_DIR_NAMES.get(lang, [lang])
    for subdir in dir_names:
        pattern = os.path.join(corpus_dir, subdir, "*")
        files = sorted(glob.glob(pattern), key=lambda p: os.path.basename(p))
        for fpath in files:
            if len(snippets) >= max_files:
                break
            try:
                code = Path(fpath).read_text(encoding="utf-8")
                lines = code.splitlines()
                # Keep files that fit within token budget: ~80 lines and ~2500 chars
                # (minified + formatted pairs must both fit under 1024 tokens)
                if 5 <= len(lines) <= 80 and len(code) <= 2500:
                    snippets.append(code)
            except Exception:
                continue
    return snippets


def main():
    parser = argparse.ArgumentParser(
        description='Generate code quality training data (formatting, lint-fixing, refactoring)'
    )
    parser.add_argument(
        '--samples', type=int, default=500,
        help='Total samples to generate (default: 500)',
    )
    parser.add_argument(
        '--output', type=str,
        default=os.path.join(PROJECT_ROOT, 'data', 'formatting_train.jsonl'),
        help='Output JSONL file path',
    )
    parser.add_argument(
        '--seed', type=int, default=None,
        help='Random seed for reproducibility',
    )
    parser.add_argument(
        '--max-per-lang', type=int, default=None,
        help='Max formatting samples per language (default: unlimited)',
    )
    parser.add_argument(
        '--lint-samples', type=int, default=100,
        help='Number of lint-fixing samples (default: 100)',
    )
    parser.add_argument(
        '--refactor-samples', type=int, default=100,
        help='Number of refactoring samples (default: 100)',
    )
    parser.add_argument(
        '--corpus-dir', type=str, default=None,
        help='Directory of scraped real code files to supplement formatting corpus',
    )
    parser.add_argument(
        '--formatting-samples', type=int, default=None,
        help='Number of formatting samples (default: samples - lint - refactor)',
    )
    args = parser.parse_args()

    seed = args.seed or random.randint(0, 999999)
    fmt_samples = args.formatting_samples or (args.samples - args.lint_samples - args.refactor_samples)

    print(f"Generating training data (seed={seed})...")

    all_samples = []

    # Formatting samples (from real formatters)
    if fmt_samples > 0:
        # Supplement built-in corpus with scraped files if available
        corpus_map = {
            "python": PYTHON_CORPUS,
            "javascript": JS_CORPUS,
            "typescript": TS_CORPUS,
            "rust": RUST_CORPUS,
        }
        scraped_total = 0
        if args.corpus_dir:
            print(f"\n  Loading scraped corpus from {args.corpus_dir}")
            for lang, corpus_list in corpus_map.items():
                scraped = load_corpus_files(args.corpus_dir, lang, 200)
                if scraped:
                    corpus_list.extend(scraped)
                    scraped_total += len(scraped)
                    print(f"    {lang}: +{len(scraped)} scraped (total: {len(corpus_list)})")
            if scraped_total == 0:
                print("    No scraped files found")

        print(f"\n  Formatting: {fmt_samples} samples")
        print(f"    Corpus: Python={len(PYTHON_CORPUS)}, "
              f"JS={len(JS_CORPUS)}, TS={len(TS_CORPUS)}, Rust={len(RUST_CORPUS)}")
        fmt, fmt_counts = generate_dataset(
            fmt_samples, seed, max_per_corpus=args.max_per_lang,
        )
        all_samples.extend(fmt)
        print(f"    Generated: {fmt_counts}")

    # Lint-fixing samples
    if args.lint_samples > 0:
        lint_seed = seed + 1
        lint = generate_lint_dataset(args.lint_samples, lint_seed)
        all_samples.extend(lint)
        py_lint = sum(1 for p in PYTHON_LINT_CORPUS for _ in range(1))
        print(f"\n  Lint-fixing: {args.lint_samples} samples")
        print(f"    Corpus: Python={len(PYTHON_LINT_CORPUS)}, JS={len(JS_LINT_CORPUS)}")

    # Refactoring samples
    if args.refactor_samples > 0:
        refactor_seed = seed + 2
        refactor = generate_refactor_dataset(args.refactor_samples, refactor_seed)
        all_samples.extend(refactor)
        print(f"\n  Refactoring: {args.refactor_samples} samples")
        print(f"    Corpus: Python={len(PYTHON_REFACTOR_CORPUS)}, JS={len(JS_REFACTOR_CORPUS)}")

    # Shuffle
    rng = random.Random(seed + 3)
    rng.shuffle(all_samples)

    # Write output
    output_path = args.output
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        for sample in all_samples:
            f.write(json.dumps(sample) + '\n')

    print(f"\nWrote {len(all_samples)} samples to {output_path}")
    print(f"  Formatting: {fmt_samples if fmt_samples > 0 else 0}")
    print(f"  Lint-fixing: {len(lint) if args.lint_samples > 0 else 0}")
    print(f"  Refactoring: {len(refactor) if args.refactor_samples > 0 else 0}")


if __name__ == '__main__':
    main()
