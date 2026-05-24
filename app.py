"""
Nimbus Weather — Premium Desktop Weather App
Glassmorphism UI · Animated Sky · No API Key Required
"""

import threading, random, math, json, os
import requests
import tkinter as tk
from tkinter import font as tkfont
from datetime import datetime

# ──────────────────────────────────────────────────────────
#  OPTIONAL: system notifications
# ──────────────────────────────────────────────────────────
try:
    from plyer import notification as _notif
    _HAS_NOTIF = True
except ImportError:
    _HAS_NOTIF = False

# ──────────────────────────────────────────────────────────
#  CONFIG
# ──────────────────────────────────────────────────────────
APP_TITLE    = "Nimbus"
W, H         = 400, 700
GEOCODING    = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST     = "https://api.open-meteo.com/v1/forecast"
FAV_FILE     = os.path.join(os.path.expanduser("~"), ".nimbus_favs.json")
TIMEOUT      = 10

IP_PROVIDERS = [
    {"u":"https://ipapi.co/json/",        "city":"city",     "ctry":"country_name","lat":"latitude","lon":"longitude","ok":lambda d:bool(d.get("city"))},
    {"u":"https://ipwho.is/",             "city":"city",     "ctry":"country",     "lat":"latitude","lon":"longitude","ok":lambda d:d.get("success") is True},
    {"u":"http://ip-api.com/json/",       "city":"city",     "ctry":"country",     "lat":"lat",     "lon":"lon",      "ok":lambda d:d.get("status")=="success"},
    {"u":"https://freeipapi.com/api/json","city":"cityName", "ctry":"countryName", "lat":"latitude","lon":"longitude","ok":lambda d:bool(d.get("cityName"))},
]

WMO = {
    0:("Clear Sky","☀️"),  1:("Mainly Clear","🌤"),  2:("Partly Cloudy","⛅"),
    3:("Overcast","☁️"),   45:("Foggy","🌫"),         48:("Icy Fog","🌫"),
    51:("Drizzle","🌦"),   53:("Drizzle","🌦"),       55:("Heavy Drizzle","🌧"),
    61:("Light Rain","🌧"),63:("Rain","🌧"),           65:("Heavy Rain","🌧"),
    71:("Light Snow","🌨"),73:("Snow","❄️"),           75:("Heavy Snow","❄️"),
    77:("Snow Grains","❄️"),80:("Showers","🌦"),       81:("Rain Showers","🌧"),
    82:("Violent Showers","⛈"),85:("Snow Showers","🌨"),86:("Heavy Snow Showers","❄️"),
    95:("Thunderstorm","⛈"),96:("Thunderstorm","⛈"), 99:("Thunderstorm","⛈"),
}

def _theme(c):
    if c==0:                              return "sunny"
    if c in(1,2):                         return "partly"
    if c==3:                              return "cloudy"
    if c in(45,48):                       return "foggy"
    if c in(51,53,55,61,63,65,80,81,82): return "rain"
    if c in(71,73,75,77,85,86):           return "snow"
    if c in(95,96,99):                    return "thunder"
    return "cloudy"

# (sky_top, sky_bottom, accent, card_tint)
PALETTES = {
    "sunny":   ("#0F3460","#16213E","#FFD700","#1a3a6a"),
    "partly":  ("#1a3a6a","#0d2040","#7EC8E3","#152e55"),
    "cloudy":  ("#2C3E50","#1a252f","#95a5a6","#252f3a"),
    "foggy":   ("#3d4f5e","#2a3a47","#b0bec5","#2e3e4e"),
    "rain":    ("#0a1628","#050d1a","#4a9eff","#0d1f35"),
    "snow":    ("#1a2a4a","#0d1a30","#e0f0ff","#152035"),
    "thunder": ("#070b12","#030508","#f0c040","#0a1020"),
}


# ──────────────────────────────────────────────────────────
#  API
# ──────────────────────────────────────────────────────────
class APIError(Exception): pass

class WS:  # WeatherService
    @staticmethod
    def geocode(city):
        try:
            r = requests.get(GEOCODING,
                params={"name":city,"count":1,"language":"en","format":"json"},
                timeout=TIMEOUT)
            r.raise_for_status()
            res = r.json().get("results")
        except requests.exceptions.ConnectionError: raise APIError("No internet connection.")
        except requests.exceptions.Timeout:         raise APIError("Request timed out.")
        except Exception as e:                       raise APIError(str(e))
        if not res: raise APIError(f'"{city}" not found.')
        x=res[0]
        return {"name":x.get("name",city),"country":x.get("country",""),
                "latitude":x["latitude"],"longitude":x["longitude"]}

    @staticmethod
    def fetch(lat,lon):
        p={
            "latitude":lat,"longitude":lon,"timezone":"auto",
            "current":"temperature_2m,apparent_temperature,relative_humidity_2m,"
                      "wind_speed_10m,weather_code,precipitation,uv_index",
            "hourly":"temperature_2m,weather_code",
            "daily":"temperature_2m_max,temperature_2m_min,weather_code,precipitation_sum",
            "wind_speed_unit":"kmh","forecast_days":6,
        }
        try:
            r=requests.get(FORECAST,params=p,timeout=TIMEOUT)
            r.raise_for_status(); data=r.json()
        except requests.exceptions.ConnectionError: raise APIError("No internet connection.")
        except requests.exceptions.Timeout:         raise APIError("Request timed out.")
        except Exception as e:                       raise APIError(str(e))
        cur=data.get("current")
        if not cur: raise APIError("Unexpected response.")

        # hourly next 24
        h=data.get("hourly",{}); ht=h.get("time",[]); hv=h.get("temperature_2m",[])
        hc=h.get("weather_code",[]); ns=cur.get("time","")[:13]
        hours=[]
        for i,t in enumerate(ht):
            if t[:13]>=ns:
                hours.append({"time":t[11:16],
                               "temp":hv[i] if i<len(hv) else "—",
                               "code":hc[i] if i<len(hc) else -1})
            if len(hours)==24: break

        d=data.get("daily",{}); dt=d.get("time",[]); mx=d.get("temperature_2m_max",[])
        mn=d.get("temperature_2m_min",[]); wc=d.get("weather_code",[]); pr=d.get("precipitation_sum",[])
        fc=[]
        for i in range(1,min(6,len(dt))):
            try: dl=datetime.fromisoformat(dt[i]).strftime("%a")
            except: dl=dt[i]
            fc.append({"day":dl,
                "max":mx[i] if i<len(mx) else "—","min":mn[i] if i<len(mn) else "—",
                "code":wc[i] if i<len(wc) else -1,"precip":pr[i] if i<len(pr) else 0})

        return {"temperature":cur.get("temperature_2m","—"),
                "feels_like":cur.get("apparent_temperature","—"),
                "humidity":cur.get("relative_humidity_2m","—"),
                "wind_speed":cur.get("wind_speed_10m","—"),
                "weather_code":cur.get("weather_code",-1),
                "precipitation":cur.get("precipitation",0),
                "uv_index":cur.get("uv_index","—"),
                "updated_at":cur.get("time",""),
                "forecast":fc,"hours":hours}

    @staticmethod
    def ip_loc():
        for p in IP_PROVIDERS:
            try:
                r=requests.get(p["u"],timeout=7,headers={"User-Agent":"Nimbus/2"})
                if r.status_code!=200: continue
                d=r.json()
                if not p["ok"](d): continue
                city=str(d.get(p["city"],"")).strip()
                if not city: continue
                return {"name":city,"country":str(d.get(p["ctry"],"")).strip(),
                        "latitude":float(d[p["lat"]]),"longitude":float(d[p["lon"]])}
            except: continue
        raise APIError("Location detection failed.\nPlease search your city manually.")

    @classmethod
    def city(cls,name):
        loc=cls.geocode(name); wx=cls.fetch(loc["latitude"],loc["longitude"])
        return {**loc,**wx}
    @classmethod
    def ip(cls):
        loc=cls.ip_loc(); wx=cls.fetch(loc["latitude"],loc["longitude"])
        return {**loc,**wx}


# ──────────────────────────────────────────────────────────
#  FAVOURITES
# ──────────────────────────────────────────────────────────
class Favs:
    def __init__(self):
        try:
            with open(FAV_FILE) as f: self._d=json.load(f)
        except: self._d=[]
    def _save(self):
        try:
            with open(FAV_FILE,"w") as f: json.dump(self._d,f)
        except: pass
    def all(self): return list(self._d)
    def add(self,city,country):
        e=f"{city}, {country}"
        if e not in self._d: self._d.append(e); self._save()
    def remove(self,e):
        if e in self._d: self._d.remove(e); self._save()


# ──────────────────────────────────────────────────────────
#  SKY CANVAS  — full-window animated weather scene
# ──────────────────────────────────────────────────────────
class Sky(tk.Canvas):
    FPS = 30

    def __init__(self, parent, **kw):
        super().__init__(parent, highlightthickness=0, bd=0, **kw)
        self.W = int(self["width"]); self.H = int(self["height"])
        self._theme = "partly"; self._parts=[]; self._flash=0
        self._sun_a=0.0; self._moon_a=0.0
        self._clouds=[self._mk_cloud() for _ in range(6)]
        self._stars=[(random.randint(0,self.W),random.randint(10,self.H//2),
                      random.uniform(0.6,2.2)) for _ in range(80)]
        self._running=False

    def _mk_cloud(self):
        return {"x":random.randint(-80,self.W+80),
                "y":random.randint(20,self.H//3),
                "r":random.randint(30,75),
                "s":random.uniform(0.12,0.5)}

    def set_theme(self,t):
        self._theme=t; self._parts=[]
        if t=="rain":    [self._parts.append(self._mk_drop()) for _ in range(180)]
        elif t=="snow":  [self._parts.append(self._mk_flake()) for _ in range(110)]
        elif t=="thunder":[self._parts.append(self._mk_drop()) for _ in range(220)]
        if not self._running:
            self._running=True; self._loop()

    def _mk_drop(self):
        return {"x":random.uniform(0,self.W),"y":random.uniform(-self.H,0),
                "vx":random.uniform(-0.8,-.1),"vy":random.uniform(10,20),
                "l":random.randint(10,24)}
    def _mk_flake(self):
        return {"x":random.uniform(0,self.W),"y":random.uniform(-self.H,0),
                "vy":random.uniform(.7,2.2),"dx":random.uniform(-.4,.4),
                "wb":random.uniform(0,6.28),"r":random.uniform(2,5)}

    def stop(self): self._running=False

    def _loop(self):
        if not self._running: return
        self.delete("all")
        t=self._theme; pal=PALETTES.get(t,PALETTES["cloudy"])
        self._grad(pal[0],pal[1])

        night=(t in("thunder","rain","snow"))
        if night: self._draw_stars()

        if t=="sunny":    self._sun(); self._clouds_draw(.3)
        elif t=="partly": self._sun(sm=True); self._clouds_draw(.6)
        elif t=="cloudy": self._clouds_draw(1.0)
        elif t=="foggy":  self._clouds_draw(.8); self._fog()
        elif t=="rain":   self._clouds_draw(1.0); self._rain()
        elif t=="snow":   self._clouds_draw(.9); self._snow()
        elif t=="thunder":self._clouds_draw(1.0); self._rain("#3a7acc"); self._lightning()

        self.after(1000//self.FPS, self._loop)

    # ── drawing ─────────────────────────────────────────
    def _grad(self,top,bot):
        def p(h): return int(h[1:3],16),int(h[3:5],16),int(h[5:7],16)
        r1,g1,b1=p(top); r2,g2,b2=p(bot)
        N=28
        for i in range(N):
            t=i/N
            r=int(r1+(r2-r1)*t); g=int(g1+(g2-g1)*t); b=int(b1+(b2-b1)*t)
            y0=int(self.H*i/N); y1=int(self.H*(i+1)/N)
            self.create_rectangle(0,y0,self.W,y1,fill=f"#{r:02x}{g:02x}{b:02x}",outline="")

    def _draw_stars(self):
        for sx,sy,sr in self._stars:
            twinkle=random.random()
            c="#aaccff" if twinkle>.95 else "#7799cc"
            self.create_oval(sx-sr,sy-sr,sx+sr,sy+sr,fill=c,outline="")

    def _sun(self,sm=False):
        self._sun_a=(self._sun_a+.25)%360
        cx=self.W-65; cy=70; R=sm and 26 or 42
        for i in range(20):
            a=math.radians(self._sun_a+i*18)
            r1=R+5; r2=R+(16 if i%2==0 else 9)
            self.create_line(cx+math.cos(a)*r1,cy+math.sin(a)*r1,
                             cx+math.cos(a)*r2,cy+math.sin(a)*r2,
                             fill="#FFD700",width=2 if not sm else 1)
        self.create_oval(cx-R,cy-R,cx+R,cy+R,fill="#FFB800",outline="#FFD700",width=2)
        self.create_oval(cx-R+7,cy-R+7,cx+R-7,cy+R-7,fill="#FFE660",outline="")
        self.create_oval(cx-R+14,cy-R+14,cx+R-14,cy+R-14,fill="#FFFAAA",outline="")

    def _cloud_col(self):
        t=self._theme
        if t in("thunder","rain"):  return "#1e2c3e"
        if t=="cloudy":             return "#4a5a6a"
        if t=="foggy":              return "#6a7a8a"
        if t=="snow":               return "#3a4a6a"
        return "#c8ddf5"

    def _clouds_draw(self,dens):
        col=self._cloud_col()
        shad="#0d1520" if self._theme in("rain","thunder","cloudy") else "#a0b8d0"
        for c in self._clouds:
            c["x"]=(c["x"]+c["s"])%(self.W+160)
            if random.random()>dens: continue
            cx,cy,r=c["x"],c["y"],c["r"]
            self.create_oval(cx-r+4,cy-r//2+6,cx+r+4,cy+r//2+6,fill=shad,outline="")
            self.create_oval(cx-r,   cy-r//2, cx+r,   cy+r//2,  fill=col,outline="")
            self.create_oval(cx-r+4, cy-r,    cx+r-4, cy+2,     fill=col,outline="")
            self.create_oval(cx-r//2,cy-r//3, cx+r//3,cy+r//2+4,fill=col,outline="")
            self.create_oval(cx+r//4,cy-r//4, cx+r+20,cy+r//2+2,fill=col,outline="")

    def _fog(self):
        for y in range(0,self.H,35):
            self.create_rectangle(0,y,self.W,y+18,
                                  fill="#7a8a90",outline="",stipple="gray25")

    def _rain(self,col="#5a9fdf"):
        for p in self._parts:
            p["x"]+=p["vx"]; p["y"]+=p["vy"]
            if p["y"]>self.H: p["y"]=random.uniform(-40,-5); p["x"]=random.uniform(0,self.W)
            self.create_line(p["x"],p["y"],p["x"]+p["vx"]*2,p["y"]+p["l"],
                             fill=col,width=1)

    def _snow(self):
        for p in self._parts:
            p["wb"]+=.04; p["x"]+=p["dx"]+math.sin(p["wb"])*.5; p["y"]+=p["vy"]
            if p["y"]>self.H: p["y"]=-5; p["x"]=random.uniform(0,self.W)
            r=p["r"]
            self.create_oval(p["x"]-r,p["y"]-r,p["x"]+r,p["y"]+r,
                             fill="#d8ecff",outline="")

    def _lightning(self):
        self._flash=max(0,self._flash-1)
        if random.random()<.02: self._flash=5
        if self._flash>0:
            lx=random.randint(self.W//4,3*self.W//4)
            pts=[(lx,30),(lx-14,85),(lx+10,85),
                 (lx-18,150),(lx+6,150),(lx-22,215)]
            for i in range(len(pts)-1):
                self.create_line(pts[i][0],pts[i][1],pts[i+1][0],pts[i+1][1],
                                 fill="#fff060",width=3)
            for i in range(len(pts)-1):
                self.create_line(pts[i][0],pts[i][1],pts[i+1][0],pts[i+1][1],
                                 fill="#ffe080",width=7)


# ──────────────────────────────────────────────────────────
#  HOURLY CHART
# ──────────────────────────────────────────────────────────
class ChartWin(tk.Toplevel):
    def __init__(self, parent, hours, fmt_fn, accent):
        super().__init__(parent)
        self.title("Hourly Forecast — 24h")
        self.resizable(False,False)
        bg="#060e1a"
        self.configure(bg=bg)
        CW,CH=560,220; PAD=44
        c=tk.Canvas(self,width=CW,height=CH,bg=bg,highlightthickness=0)
        c.pack(padx=12,pady=12)

        temps=[]
        for h in hours[:24]:
            try: temps.append(float(h["temp"]))
            except: temps.append(0.)
        if not temps: return
        mn,mx=min(temps),max(temps); span=mx-mn or 1
        iw=(CW-PAD*2)/max(len(temps)-1,1)

        def xy(i,t):
            return PAD+i*iw, CH-PAD-(t-mn)/span*(CH-PAD*2)

        for k in range(5):
            y=PAD+(CH-PAD*2)*k/4
            c.create_line(PAD,y,CW-PAD,y,fill="#0f2040",width=1,dash=(4,4))
            tv=mx-(mx-mn)*k/4
            c.create_text(PAD-6,y,text=fmt_fn(tv).replace("°",""),
                          fill="#3a6090",font=("Courier",8),anchor="e")

        pts=[PAD,CH-PAD]
        for i,t in enumerate(temps): x,y=xy(i,t); pts+=[x,y]
        pts+=[(PAD+(len(temps)-1)*iw),CH-PAD]
        c.create_polygon(pts,fill="#0a3060",outline="")

        for i in range(len(temps)-1):
            x1,y1=xy(i,temps[i]); x2,y2=xy(i+1,temps[i+1])
            c.create_line(x1,y1,x2,y2,fill=accent,width=2,capstyle="round")

        for i,t in enumerate(temps):
            x,y=xy(i,t)
            c.create_oval(x-4,y-4,x+4,y+4,fill=accent,outline="#060e1a",width=2)
            if i%4==0:
                lbl=hours[i]["time"]
                c.create_text(x,CH-PAD+10,text=lbl,fill="#4a7aaa",
                              font=("Courier",8),anchor="n")
                c.create_text(x,y-14,text=fmt_fn(t),fill="#d0e8ff",
                              font=("Courier",8,"bold"),anchor="s")


# ──────────────────────────────────────────────────────────
#  TRANSPARENT BAR (Canvas-based — simulates alpha overlay)
# ──────────────────────────────────────────────────────────
class TransparentBar(tk.Canvas):
    """
    Title bar that draws a semi-transparent overlay using stipple patterns.
    Since Tkinter doesn't support RGBA colors, we use stipple to fake transparency.
    """
    def __init__(self, parent, **kw):
        super().__init__(parent, highlightthickness=0, bd=0, **kw)
        # Draw a dark overlay using stipple (gray50 ≈ 50% opacity black)
        self.create_rectangle(0, 0, W, 38, fill="#000000", outline="", stipple="gray25")


# ──────────────────────────────────────────────────────────
#  MAIN APP WINDOW
# ──────────────────────────────────────────────────────────
class Nimbus(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(f"{W}x{H}")
        self.minsize(W,H); self.maxsize(W,H)
        self.configure(bg="#060e1a")

        self._data=None; self._use_f=False
        self._favs=Favs(); self._chart=None
        self._theme="partly"
        self._drag_x=self._drag_y=0
        self._anim_temp=0.0
        self._target_temp=0.0

        self._accent="#7EC8E3"
        self._card="#0d1f35"

        self._fonts()
        self._build()

    def _fonts(self):
        self.F_HUGE  = ("Georgia","52","bold")
        self.F_BIG   = ("Georgia","22","bold")
        self.F_MED   = ("Helvetica","13")
        self.F_SMALL = ("Helvetica","10")
        self.F_TINY  = ("Helvetica","9")
        self.F_MONO  = ("Courier","10")

    # ════════════════════════════════════════════════════
    #  BUILD
    # ════════════════════════════════════════════════════
    def _build(self):
        # ── Sky canvas (full background) ─────────────────
        self.sky=Sky(self,width=W,height=H,bg="#060e1a")
        self.sky.place(x=0,y=0)

        # ── Title bar — Canvas with stipple overlay ──────
        # Using Canvas instead of Frame to allow stipple-based transparency simulation
        BAR_BG = "#0a1828"  # fallback solid colour (seen through stipple gaps)
        self._bar = TransparentBar(self, width=W, height=38, bg=BAR_BG)
        self._bar.place(x=0, y=0)

        # Title label — bg must match bar's bg (no alpha support in Label)
        tk.Label(self._bar, text="◈ NIMBUS", bg=BAR_BG, fg="#ffffff",
                 font=("Courier",11,"bold")).place(x=14, y=9)

        self._lbl_clock = tk.Label(self._bar, text="", bg=BAR_BG, fg="#88aacc",
                                   font=("Courier",9))
        self._lbl_clock.place(x=W//2, y=10, anchor="n")

        # window controls
        def _wbtn(txt, cmd, rx, col):
            b = tk.Label(self._bar, text=txt, bg=BAR_BG, fg=col,
                         font=("Helvetica",10,"bold"), cursor="hand2")
            b.place(relx=1, x=rx, y=8, anchor="ne")
            b.bind("<Button-1>", lambda _: cmd())
            b.bind("<Enter>",  lambda e, w=b: w.configure(fg="white"))
            b.bind("<Leave>",  lambda e, w=b, c=col: w.configure(fg=c))
        _wbtn("—", self.iconify,  -36, "#88aacc")
        _wbtn("✕", self.destroy,  -12, "#cc5555")

        # drag-to-move
        self._bar.bind("<ButtonPress-1>", self._drag_start)
        self._bar.bind("<B1-Motion>",     self._drag_move)

        self._tick()

        # ── Search row ───────────────────────────────────
        SR_BG = "#0a1828"
        sr = tk.Frame(self, bg=SR_BG, height=44)
        sr.place(x=0, y=38, width=W)

        self._sv=tk.StringVar()
        self._ent=tk.Entry(sr, textvariable=self._sv, bg="#0f2035", fg="#c8ddf5",
                           insertbackground="#7EC8E3", relief="flat",
                           font=("Helvetica",12), bd=0,
                           highlightthickness=1, highlightcolor="#1a4a7a",
                           highlightbackground="#0f2a45")
        self._ent.place(x=10, y=7, width=220, height=28)
        self._ent.bind("<Return>", lambda _: self._do_search())
        self._ent.insert(0, "Enter city name…")
        self._ent.bind("<FocusIn>",  self._hint_clear)
        self._ent.bind("<FocusOut>", self._hint_set)

        self._btns={}
        specs=[("Search","⌕",236,38,self._do_search),
               ("📍",    "📍",280,26,self._do_locate),
               ("⭐",    "⭐",310,26,self._fav_add),
               ("☰",    "☰", 340,28,self._fav_menu)]
        for key,txt,x,w,cmd in specs:
            b=tk.Label(sr, text=txt, bg="#142030", fg="#7EC8E3",
                       font=("Helvetica",10,"bold"), cursor="hand2",
                       relief="flat", padx=4)
            b.place(x=x, y=7, width=w, height=28)
            b.bind("<Button-1>", lambda _,c=cmd: c())
            b.bind("<Enter>", lambda e,bw=b: bw.configure(bg="#1a3050"))
            b.bind("<Leave>", lambda e,bw=b: bw.configure(bg="#142030"))
            self._btns[key]=b

        # ── Status ───────────────────────────────────────
        self._st=tk.Label(self, text="", bg="#060e1a", fg="#4a9eff",
                          font=("Helvetica",10), wraplength=W-24)
        self._st.place(x=0, y=82, width=W)

        # ══════════════════════════════════════════════
        #  MAIN CARD
        # ══════════════════════════════════════════════
        CARD_Y=96
        CARD_BG="#0d1f35"

        self._card_frame=tk.Frame(self, bg=CARD_BG,
                                  highlightthickness=1, highlightbackground="#1a3a6a")
        self._card_frame.place(x=10, y=CARD_Y, width=W-20, height=H-CARD_Y-10)

        self._lbl_city=tk.Label(self._card_frame, text="—", bg=CARD_BG, fg="#e8f4ff",
                                font=("Georgia",20,"bold"))
        self._lbl_city.place(x=0, y=14, width=W-20)

        self._lbl_ctry=tk.Label(self._card_frame, text="", bg=CARD_BG, fg="#5a8ab0",
                                font=("Helvetica",11))
        self._lbl_ctry.place(x=0, y=42, width=W-20)

        self._lbl_ico=tk.Label(self._card_frame, text="⛅", bg=CARD_BG, fg="#e8f4ff",
                               font=("Helvetica",60))
        self._lbl_ico.place(x=0, y=64, width=W-20)

        self._lbl_temp=tk.Label(self._card_frame, text="—", bg=CARD_BG, fg="#e8f4ff",
                                font=("Georgia",52,"bold"))
        self._lbl_temp.place(x=0, y=132, width=W-20)

        self._lbl_cond=tk.Label(self._card_frame, text="—", bg=CARD_BG, fg="#5a8ab0",
                                font=("Helvetica",14))
        self._lbl_cond.place(x=0, y=196, width=W-20)

        self._lbl_feels=tk.Label(self._card_frame, text="", bg=CARD_BG, fg="#3a6a90",
                                 font=("Helvetica",10))
        self._lbl_feels.place(x=0, y=218, width=W-20)

        btn_y=242
        self._make_pill("°F/°C",  14, btn_y, 56, self._toggle_unit, "_btn_unit")
        self._make_pill("📊 24h", 76, btn_y, 72, self._show_chart)
        self._make_pill("🔔",    154, btn_y, 32, self._notify)
        self._make_pill("🔄",    192, btn_y, 32, self._refresh)

        self._div=tk.Frame(self._card_frame, bg="#1a3a5a", height=1)
        self._div.place(x=14, y=286, width=W-48)

        STAT_Y=296
        self._sv_labels={}
        stats=[("💧","Humidity",0),("💨","Wind",1),("🌂","Precip",2),("🔆","UV",3)]
        cw=(W-20)//4
        for ico,lbl,i in stats:
            bx=i*cw
            tk.Label(self._card_frame, text=ico, bg=CARD_BG, fg="#e8f4ff",
                     font=("Helvetica",18)).place(x=bx, y=STAT_Y, width=cw)
            v=tk.Label(self._card_frame, text="—", bg=CARD_BG, fg="#e8f4ff",
                       font=("Helvetica",11,"bold"))
            v.place(x=bx, y=STAT_Y+24, width=cw)
            tk.Label(self._card_frame, text=lbl, bg=CARD_BG, fg="#3a6080",
                     font=("Helvetica",8)).place(x=bx, y=STAT_Y+44, width=cw)
            self._sv_labels[lbl]=v

        FC_Y=STAT_Y+68
        self._sep2=tk.Frame(self._card_frame, bg="#1a3a5a", height=1)
        self._sep2.place(x=14, y=FC_Y-6, width=W-48)
        tk.Label(self._card_frame, text="FORECAST", bg=CARD_BG, fg="#2a5070",
                 font=("Courier",8,"bold")).place(x=14, y=FC_Y)
        FC_Y+=18
        self._fc=[]
        fcw=(W-20)//5
        FC_CELL_BG="#091520"
        for i in range(5):
            bx=i*fcw
            cell=tk.Frame(self._card_frame, bg=FC_CELL_BG,
                          highlightthickness=1, highlightbackground="#1a3050")
            cell.place(x=bx+2, y=FC_Y, width=fcw-4, height=90)
            ld=tk.Label(cell, text="—", bg=FC_CELL_BG, fg="#3a6080", font=("Courier",9))
            ld.pack(pady=(6,1))
            li=tk.Label(cell, text="—", bg=FC_CELL_BG, fg="#e8f4ff", font=("Helvetica",20))
            li.pack()
            lx=tk.Label(cell, text="—", bg=FC_CELL_BG, fg="#e8f4ff", font=("Helvetica",10,"bold"))
            lx.pack()
            ln=tk.Label(cell, text="—", bg=FC_CELL_BG, fg="#3a6080", font=("Helvetica",9))
            ln.pack()
            self._fc.append((ld,li,lx,ln))

        self._lbl_upd=tk.Label(self._card_frame, text="", bg=CARD_BG, fg="#1e3a55",
                               font=("Courier",8))
        self._lbl_upd.place(x=0, y=H-CARD_Y-28, width=W-20)

        self.sky.set_theme("partly")

    # ── pill button ──────────────────────────────────────
    def _make_pill(self,txt,x,y,w,cmd,attr=None):
        b=tk.Label(self._card_frame, text=txt, bg="#0a1828", fg="#4a8ab8",
                   font=("Helvetica",9,"bold"), cursor="hand2",
                   highlightthickness=1, highlightbackground="#1a3a5a")
        b.place(x=x, y=y, width=w, height=26)
        b.bind("<Button-1>", lambda _: cmd())
        b.bind("<Enter>", lambda e: b.configure(bg="#142035", fg="#7EC8E3"))
        b.bind("<Leave>", lambda e: b.configure(bg="#0a1828", fg="#4a8ab8"))
        if attr: setattr(self, attr, b)
        return b

    # ── draggable window ─────────────────────────────────
    def _drag_start(self,e):
        self._drag_x=e.x_root-self.winfo_x()
        self._drag_y=e.y_root-self.winfo_y()
    def _drag_move(self,e):
        self.geometry(f"+{e.x_root-self._drag_x}+{e.y_root-self._drag_y}")

    # ── clock ────────────────────────────────────────────
    def _tick(self):
        self._lbl_clock.configure(text=datetime.now().strftime("%a %d %b  %H:%M"))
        self.after(20_000, self._tick)

    # ── search hint ──────────────────────────────────────
    def _hint_clear(self,_):
        if self._sv.get()=="Enter city name…":
            self._ent.delete(0,"end"); self._ent.configure(fg="#c8ddf5")
    def _hint_set(self,_):
        if not self._sv.get().strip():
            self._ent.configure(fg="#3a6080"); self._ent.insert(0,"Enter city name…")

    # ── unit ─────────────────────────────────────────────
    def _fmt(self,v):
        try:
            f=float(v)
            return f"{f*9/5+32:.1f}°F" if self._use_f else f"{f:.1f}°C"
        except: return f"{v}°{'F' if self._use_f else 'C'}"

    def _toggle_unit(self):
        self._use_f=not self._use_f
        self._btn_unit.configure(text="°C/°F" if self._use_f else "°F/°C")
        if self._data: self._render(self._data)

    # ── status ───────────────────────────────────────────
    def _status(self,msg,err=False):
        self._st.configure(text=msg, fg="#f85149" if err else "#4a9eff")

    def _busy(self,on):
        for b in self._btns.values():
            b.configure(state="disabled" if on else "normal")

    # ════════════════════════════════════════════════════
    #  ACTIONS
    # ════════════════════════════════════════════════════
    def _do_search(self):
        city=self._sv.get().strip()
        if not city or city=="Enter city name…":
            self._status("Please enter a city name.", err=True); return
        self._busy(True); self._status("Searching…")
        threading.Thread(target=self._run, args=(WS.city,city), daemon=True).start()

    def _do_locate(self):
        self._busy(True); self._status("🔍 Detecting your location…")
        threading.Thread(target=self._run, args=(WS.ip,), daemon=True).start()

    def _refresh(self):
        if not self._data: self._status("Search a city first.", err=True); return
        d=self._data; self._busy(True); self._status("Refreshing…")
        def _w():
            try:
                wx=WS.fetch(d["latitude"],d["longitude"])
                self.after(0, self._render, {**d,**wx})
            except APIError as e:
                self.after(0, self._status, str(e), True)
                self.after(0, self._busy, False)
        threading.Thread(target=_w, daemon=True).start()

    def _run(self,fn,*args):
        try:
            self.after(0, self._render, fn(*args))
        except APIError as e:
            self.after(0, self._status, str(e), True)
            self.after(0, self._busy, False)
        except Exception as e:
            self.after(0, self._status, f"Error: {e}", True)
            self.after(0, self._busy, False)

    # ── animated temperature counter ─────────────────────
    def _anim_counter(self,target,current,steps=20):
        diff=target-current
        if abs(diff)<0.1:
            self._lbl_temp.configure(text=self._fmt(target)); return
        nxt=current+diff/steps
        self._lbl_temp.configure(text=self._fmt(nxt))
        self.after(30, self._anim_counter, target, nxt, steps)

    # ════════════════════════════════════════════════════
    #  RENDER
    # ════════════════════════════════════════════════════
    def _render(self,data):
        self._data=data
        code=data.get("weather_code",-1)
        label,emoji=WMO.get(code,("Unknown","❓"))
        th=_theme(code); pal=PALETTES.get(th,PALETTES["cloudy"])
        acc=pal[2]; card=pal[3]

        self._accent=acc
        for w in (self._card_frame, self._lbl_city, self._lbl_ctry,
                  self._lbl_ico, self._lbl_temp, self._lbl_cond,
                  self._lbl_feels, self._lbl_upd, self._st):
            try: w.configure(bg=card)
            except: pass
        for _,lbl in self._sv_labels.items():
            try: lbl.configure(bg=card)
            except: pass
        for row in self._fc:
            for lbl in row:
                try: lbl.configure(bg="#060e1a")
                except: pass
        self._div.configure(bg=acc)
        self._sep2.configure(bg=acc)

        self.sky.set_theme(th)

        temp=data.get("temperature","—")
        try:
            self._anim_counter(float(temp), self._target_temp)
            self._target_temp=float(temp)
        except:
            self._lbl_temp.configure(text=self._fmt(temp))

        self._lbl_city.configure(text=data.get("name","—"))
        self._lbl_ctry.configure(text=data.get("country",""))
        self._lbl_ico.configure(text=emoji)
        self._lbl_cond.configure(text=label)
        self._lbl_feels.configure(text=f"Feels like {self._fmt(data.get('feels_like','—'))}")

        self._sv_labels["Humidity"].configure(text=f"{data.get('humidity','—')}%")
        self._sv_labels["Wind"].configure(text=f"{data.get('wind_speed','—')} km/h")
        self._sv_labels["Precip"].configure(text=f"{data.get('precipitation',0)} mm")
        self._sv_labels["UV"].configure(text=str(data.get("uv_index","—")))

        raw=data.get("updated_at","")
        try: upd=datetime.fromisoformat(raw).strftime("Updated %d %b %Y, %H:%M")
        except: upd=raw
        self._lbl_upd.configure(text=upd)

        for i,(ld,li,lx,ln) in enumerate(self._fc):
            fc=data.get("forecast",[])
            if i<len(fc):
                f=fc[i]; ico=WMO.get(f["code"],("","❓"))[1]
                ld.configure(text=f["day"])
                li.configure(text=ico)
                lx.configure(text=self._fmt(f["max"]))
                ln.configure(text=self._fmt(f["min"]))

        self._status("")
        self._busy(False)

    # ════════════════════════════════════════════════════
    #  EXTRAS
    # ════════════════════════════════════════════════════
    def _show_chart(self):
        if not self._data: self._status("Load weather first.", err=True); return
        hrs=self._data.get("hours",[])
        if not hrs: self._status("No hourly data.", err=True); return
        if self._chart and self._chart.winfo_exists():
            self._chart.lift(); return
        acc=PALETTES.get(_theme(self._data.get("weather_code",-1)),PALETTES["cloudy"])[2]
        self._chart=ChartWin(self, hrs, self._fmt, acc)

    def _notify(self):
        if not self._data: self._status("Load weather first.", err=True); return
        d=self._data; code=d.get("weather_code",-1)
        label=WMO.get(code,("Unknown",""))[0]
        msg=(f"{label}  ·  {self._fmt(d.get('temperature','—'))}\n"
             f"Humidity {d.get('humidity','—')}%   "
             f"Wind {d.get('wind_speed','—')} km/h")
        if _HAS_NOTIF:
            try:
                _notif.notify(title=f"Nimbus — {d.get('name','—')}",
                              message=msg, app_name="Nimbus", timeout=6)
                return
            except: pass
        import tkinter.messagebox as mb
        mb.showinfo(f"Nimbus — {d.get('name','—')}", msg)

    def _fav_add(self):
        if not self._data: self._status("Load weather first.", err=True); return
        self._favs.add(self._data["name"], self._data["country"])
        self._status(f"⭐  Saved {self._data['name']}")

    def _fav_menu(self):
        favs=self._favs.all()
        if not favs: self._status("No favourites yet."); return
        win=tk.Toplevel(self)
        win.title("Favourites"); win.resizable(False,False)
        win.configure(bg="#060e1a")
        win.geometry(f"240x{min(40*len(favs)+52,340)}")
        tk.Label(win, text="⭐  Saved Cities", bg="#060e1a", fg="#7EC8E3",
                 font=("Georgia",12,"bold")).pack(pady=(10,6))
        for entry in favs:
            row=tk.Frame(win, bg="#060e1a"); row.pack(fill="x", padx=10, pady=2)
            cn=entry.split(",")[0].strip()
            tk.Button(row, text=entry, bg="#0a1828", fg="#c8ddf5", relief="flat",
                      font=("Helvetica",10), anchor="w",
                      activebackground="#142035",
                      command=lambda c=cn,w=win:[
                          w.destroy(),
                          self._ent.delete(0,"end"),
                          self._ent.insert(0,c),
                          self._ent.configure(fg="#c8ddf5"),
                          self._do_search()]
                      ).pack(side="left", fill="x", expand=True, ipady=5)
            tk.Button(row, text="✕", bg="#1a0a0a", fg="#cc4444", relief="flat",
                      font=("Helvetica",9),
                      command=lambda e=entry,w=win:[
                          self._favs.remove(e), w.destroy(), self._fav_menu()]
                      ).pack(side="right", ipadx=6, ipady=5)

    def destroy(self):
        self.sky.stop(); super().destroy()


# ──────────────────────────────────────────────────────────
if __name__=="__main__":
    app=Nimbus(); app.mainloop()