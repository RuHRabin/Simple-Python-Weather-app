# ⛅ Nimbus Weather

A modern, mobile-style desktop weather application built with Python.
Full animated weather backgrounds, live data, and zero API keys required.

---

## Features

- **Animated sky background** — rain, snow, sun rays, thunder, clouds rendered live on a full-window canvas, matching the actual weather condition (just like a mobile weather app)
- **Live weather data** — temperature, feels-like, humidity, wind speed, precipitation, UV index
- **°C / °F toggle** — switch units instantly, all values update
- **5-day forecast** — icon, high, and low for each day
- **Hourly temperature chart** — next 24-hour line chart in a popup window
- **My Location** — auto-detects your city via IP geolocation (4 provider fallback, no GPS needed)
- **Refresh button** — re-fetches latest data without re-searching
- **Favourite cities** — save and load cities with one click, stored locally
- **Weather notifications** — push a system notification with current conditions
- **No API key** — uses Open-Meteo (forecast) and ip-api / ipapi.co (location), both 100% free

---

## Quick Start

### 1. Install Python

Download and install Python 3.10 or newer from https://python.org.

### 2. Install dependencies

```
pip install customtkinter requests
```

For system notifications (optional):

```
pip install plyer
```

### 3. Run

```
python app.py
```

That is all. No account, no API key, no configuration file needed.

---

## How to Use

| Action | How |
|---|---|
| Search a city | Type in the search box and press Enter or click Search |
| Detect your location | Click the 📍 button |
| Switch °C / °F | Click the °F / °C button below the temperature |
| Open hourly chart | Click 📊 Hourly Chart |
| Send a notification | Click 🔔 Notify |
| Save a city | Load it, then click ⭐ |
| View saved cities | Click ☰ |
| Remove a saved city | Open ☰ and click ✕ next to the city |
| Refresh data | Click 🔄 |

---

## APIs Used

| API | Purpose | Cost |
|---|---|---|
| [Open-Meteo Forecast](https://open-meteo.com/) | Temperature, humidity, wind, UV, hourly & daily forecast | Free, no key |
| [Open-Meteo Geocoding](https://open-meteo.com/en/docs/geocoding-api) | City name to coordinates | Free, no key |
| [ipapi.co](https://ipapi.co/) | IP to city (primary) | Free, no key |
| [ipwho.is](https://ipwho.is/) | IP to city (fallback 1) | Free, no key |
| [ip-api.com](https://ip-api.com/) | IP to city (fallback 2) | Free, no key |
| [freeipapi.com](https://freeipapi.com/) | IP to city (fallback 3) | Free, no key |

> **Note:** IP-based location detects your ISP's registered city, not your GPS position.
> If the detected city is wrong (common with VPNs), just search your city by name.

---

## Weather Backgrounds

| Condition | Background |
|---|---|
| Clear Sky | Rotating sun with rays, light clouds |
| Partly Cloudy | Small sun, drifting clouds |
| Overcast | Dense drifting clouds |
| Foggy | Stippled fog layer |
| Rain | Falling rain particles + dark clouds |
| Snow | Drifting snow flakes |
| Thunderstorm | Rain + random lightning bolts |

---

## Project Structure

```
nimbus-weather/
├── app.py            — Full application (API, animation, UI)
├── requirements.txt  — Python dependencies
└── README.md         — This file
```

Favourites are saved to `~/.nimbus_favorites.json` on your machine.

---

## Dependencies

| Package | Purpose |
|---|---|
| `customtkinter` | Modern widget styling |
| `requests` | HTTP calls to weather and location APIs |
| `plyer` *(optional)* | System notifications on Windows, macOS, Linux |
| `tkinter` | Built into Python — canvas, charts, layout |

On Linux, if tkinter is missing:
```
sudo apt install python3-tk
```

---

## License

MIT — free to use, modify, and distribute.

```
Copyright (c) 2026 Rabin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

---

Powered by [Open-Meteo](https://open-meteo.com) · Built with Python
