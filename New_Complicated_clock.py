"""
============================================================
   OVERLAY CLOCK با یادآور استراحت چشم و استراحت اصلی
============================================================
این اسکریپت روی ویندوز تست شده (چون از -transparentcolor استفاده
می‌کنه که یه ویژگی مخصوص ویندوزه در tkinter).

قابلیت‌ها:
 - ساعت شناور، همیشه بالای همه‌ی پنجره‌ها (Always on top)، پس‌زمینه‌ی
   کاملاً شفاف (فقط عدد ساعت دیده میشه، نه یه جعبه‌ی مستطیلی)
 - هر ۲۰ دقیقه: پیغام + تایمر ۲۰ ثانیه‌ای "به یه نقطه‌ی دور نگاه کن"
 - هر ۶۰ دقیقه: پیغام استراحت + تایمر ۱۰ دقیقه‌ای؛ با زدن دکمه‌ی
   "پایان استراحت" پنجره بسته میشه، یک واحد به متغیر ساعت کار
   اضافه میشه و تعداد ساعت کارکرد نمایش داده میشه
 - برای هر پاپ‌آپ (چشم و استراحت) یه بخش مشخص با کامنت گذاشتم که
   بتونی به‌جای متن، یه GIF یا PNG بذاری
============================================================
"""

import tkinter as tk
from tkinter import font as tkfont
import time

# برای نمایش GIF متحرک به pillow نیاز داریم: pip install pillow
# اگه نصب نباشه، برنامه بدون کرش کردن ادامه میده و به‌جای GIF فقط
# ایموجی/متن نشون میده (fallback خودکار پایین‌تر توی کلاس AnimatedGifLabel)
try:
    from PIL import Image, ImageTk, ImageSequence
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ============================================================
# بخش ۱ : تنظیمات ظاهری (فونت‌ها و رنگ‌ها)
# هر چیزی که مربوط به ظاهره رو اینجا عوض کن، لازم نیست بقیه‌ی
# کد رو دست بزنی.
# ============================================================

CLOCK_FONT_FAMILY = "Acumin Pro ExtraCondensed"      # فونت ساعت -> اسم هر فونت نصب‌شده رو بذار
CLOCK_FONT_SIZE = 30                # سایز فونت ساعت
CLOCK_FONT_WEIGHT = "bold"          # "bold" یا "normal"
CLOCK_TEXT_COLOR = "#FFFFFF"        # رنگ متن ساعت (کد HEX)
TRANSPARENT_COLOR = "black"         # این رنگ به‌طور کامل نامرئی میشه
                                     # (پس نباید رنگ متن هم همین باشه)

CLOCK_POSITION_X = 20               # فاصله از چپ صفحه (پیکسل)
CLOCK_POSITION_Y = 10               # فاصله از بالای صفحه (پیکسل)

POPUP_FONT_FAMILY = "Ayandeh"         # فونت متن پیغام‌ها (اگه نصب نیست، از "Tahoma" استفاده کن)
POPUP_FONT_SIZE = 16
POPUP_TEXT_COLOR = "#FFFFFF"
POPUP_BG_COLOR = "black"          # پس‌زمینه‌ی خود پاپ‌آپ (چون پاپ‌آپ‌ها شفاف نیستن)
POPUP_ACCENT_COLOR = "#2B00FF"      # رنگ تایمر / دکمه

EYE_BREAK_INTERVAL_MS = 20 * 60 * 1000     # هر ۲۰ دقیقه
EYE_BREAK_DURATION_SEC = 20                # ۲۰ ثانیه نگاه به دوردست

REST_BREAK_INTERVAL_MS = 60 * 60 * 1000    # هر ۶۰ دقیقه
REST_BREAK_DURATION_SEC = 10 * 60          # ۱۰ دقیقه استراحت

# ------------------------------------------------------------
# مسیر فایل‌های GIF (اختیاری) — اگه فایل رو نداری یا نمی‌خوای
# GIF نشون بدی، مقدارش رو None بذار، برنامه بدون مشکل ادامه میده.
# فایل‌ها رو کنار همین اسکریپت بذار، یا مسیر کامل بده.
# ------------------------------------------------------------
EYE_BREAK_GIF_PATH = None      # مثال: "gifs/eye_break.gif"
REST_BREAK_GIF_PATH = None     # مثال: "gifs/rest_break.gif"
GIF_MAX_SIZE = (160, 160)      # حداکثر عرض/ارتفاع GIF (پیکسل) — برای resize خودکار

# ============================================================
# بخش ۲ : متغیر شمارش ساعت کار
# ============================================================
hours_worked = 0


# ============================================================
# کلاس کمکی: نمایش GIF متحرک داخل یک Label (قابل استفاده مجدد)
# ============================================================
class AnimatedGifLabel(tk.Label):
    """
    یه Label که اگه مسیر یه GIF بهش بدی، خودش فریم‌به‌فریم پخشش می‌کنه.
    اگه pillow نصب نباشه یا مسیر None باشه، یه Label خالی برمی‌گردونه
    (برنامه کرش نمی‌کنه، فقط GIF نشون داده نمیشه).

    استفاده:
        gif = AnimatedGifLabel(parent, "eye_break.gif", bg=POPUP_BG_COLOR)
        gif.pack()
        gif.start()      # شروع پخش
        ...
        gif.stop()       # موقع بستن پنجره صداش بزن تا حلقه‌ی after متوقف بشه
    """

    def __init__(self, master, gif_path, bg="black", max_size=GIF_MAX_SIZE, **kwargs):
        super().__init__(master, bg=bg, **kwargs)
        self.frames = []
        self.frame_delays = []
        self.current_frame = 0
        self._after_id = None
        self._running = False

        if PIL_AVAILABLE and gif_path:
            try:
                img = Image.open(gif_path)
                for frame in ImageSequence.Iterator(img):
                    frame = frame.convert("RGBA")
                    frame.thumbnail(max_size)
                    self.frames.append(ImageTk.PhotoImage(frame))
                    # مدت نمایش هر فریم (میلی‌ثانیه)؛ اگه GIF مشخص نکرده بود، ۱۰۰ms
                    self.frame_delays.append(frame.info.get("duration", 100))
            except Exception as e:
                print(f"[هشدار] بارگذاری GIF ناموفق بود ({gif_path}): {e}")
                self.frames = []

        if self.frames:
            self.config(image=self.frames[0])

    def start(self):
        if self.frames:
            self._running = True
            self._animate()

    def stop(self):
        self._running = False
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None

    def _animate(self):
        if not self._running or not self.frames:
            return
        self.current_frame = (self.current_frame + 1) % len(self.frames)
        self.config(image=self.frames[self.current_frame])
        delay = self.frame_delays[self.current_frame]
        self._after_id = self.after(delay, self._animate)


# ============================================================
# بخش ۳ : پنجره‌ی اصلی ساعت (Overlay شفاف)
# ============================================================
root = tk.Tk()
root.overrideredirect(True)          # بدون نوار عنوان و دکمه‌های پنجره
root.attributes("-topmost", True)    # همیشه روی همه‌چیز
root.attributes("-transparentcolor", TRANSPARENT_COLOR)  # فقط ویندوز
root.configure(bg=TRANSPARENT_COLOR)
root.geometry(f"+{CLOCK_POSITION_X}+{CLOCK_POSITION_Y}")

clock_font = tkfont.Font(family=CLOCK_FONT_FAMILY, size=CLOCK_FONT_SIZE,
                          weight=CLOCK_FONT_WEIGHT)

clock_label = tk.Label(
    root,
    font=clock_font,
    fg=CLOCK_TEXT_COLOR,
    bg=TRANSPARENT_COLOR,
)
clock_label.config(width=8)   # طول "HH:MM:SS" = ۸ کاراکتر
clock_label.pack()  

# ------------------------------------------------------------
# نمایش ساعت کارکرد، درست زیر ساعت اصلی
# ------------------------------------------------------------
hours_font = tkfont.Font(family=CLOCK_FONT_FAMILY, size=20, weight="normal")
hours_label = tk.Label(
    root,
    text="hours : 0",
    font=hours_font,
    fg="#B7B7B7",
    bg=TRANSPARENT_COLOR,
)
hours_label.pack()


def update_clock():
    """هر ثانیه ساعت رو آپدیت می‌کنه"""
    now = time.strftime("%H:%M:%S")
    clock_label.config(text=now)
    root.after(1000, update_clock)


def update_hours_display():
    hours_label.config(text=f"hours : {hours_worked}")


# ============================================================
# بخش ۴ : پاپ‌آپ استراحت چشم (هر ۲۰ دقیقه، ۲۰ ثانیه)
# ============================================================
def show_eye_break_popup():
    popup = tk.Toplevel(root)
    popup.overrideredirect(True)
    popup.attributes("-topmost", True)
    popup.configure(bg=POPUP_BG_COLOR)

    # وسط صفحه قرارش بده
    w, h = 380, 220
    sw = popup.winfo_screenwidth()
    sh = popup.winfo_screenheight()
    popup.geometry(f"{w}x{h}+{(sw - w)//2}+{(sh - h)//2}")

    # ------------------------------------------------------------
    # << اینجا GIF/PNG استراحت چشم نمایش داده میشه >>
    # کافیه بالای فایل، EYE_BREAK_GIF_PATH رو به مسیر فایلت تغییر بدی.
    # اگه None باشه، این بخش خودش رد میشه و فقط متن دیده میشه.
    # ------------------------------------------------------------
    gif_widget = None
    if EYE_BREAK_GIF_PATH:
        gif_widget = AnimatedGifLabel(popup, EYE_BREAK_GIF_PATH, bg=POPUP_BG_COLOR)
        gif_widget.pack(pady=(15, 0))
        gif_widget.start()

    msg = tk.Label(
        popup,
        text="به یه نقطه‌ی دور نگاه کن 👀",
        font=(POPUP_FONT_FAMILY, POPUP_FONT_SIZE),
        fg=POPUP_TEXT_COLOR,
        bg=POPUP_BG_COLOR,
    )
    msg.pack(pady=(20, 10))

    timer_label = tk.Label(
        popup,
        text=str(EYE_BREAK_DURATION_SEC),
        font=(POPUP_FONT_FAMILY, 32, "bold"),
        fg=POPUP_ACCENT_COLOR,
        bg=POPUP_BG_COLOR,
    )
    timer_label.pack(pady=10)

    def countdown(remaining):
        if remaining <= 0:
            if gif_widget is not None:
                gif_widget.stop()   # جلوگیری از باقی‌موندن حلقه‌ی after بعد از بسته‌شدن پنجره
            popup.destroy()
            return
        timer_label.config(text=str(remaining))
        popup.after(1000, countdown, remaining - 1)

    countdown(EYE_BREAK_DURATION_SEC)


def schedule_eye_break():
    show_eye_break_popup()
    root.after(EYE_BREAK_INTERVAL_MS, schedule_eye_break)


# ============================================================
# بخش ۵ : پاپ‌آپ استراحت اصلی (هر ۶۰ دقیقه، ۱۰ دقیقه)
# ============================================================
def show_rest_break_popup():
    global hours_worked

    popup = tk.Toplevel(root)
    popup.overrideredirect(True)
    popup.attributes("-topmost", True)
    popup.configure(bg=POPUP_BG_COLOR)

    w, h = 420, 300
    sw = popup.winfo_screenwidth()
    sh = popup.winfo_screenheight()
    popup.geometry(f"{w}x{h}+{(sw - w)//2}+{(sh - h)//2}")

    # ------------------------------------------------------------
    # << اینجا GIF/PNG استراحتِ اصلی نمایش داده میشه >>
    # کافیه بالای فایل، REST_BREAK_GIF_PATH رو به مسیر فایلت تغییر بدی.
    #
    # نکته: اگه می‌خوای GIF رو به‌جای این پنجره‌ی پیغام، پشتِ سرِ
    # ساعتِ اصلی روی صفحه (اورلی شفاف) نشون بدی، باید یه Toplevel
    # دیگه با -transparentcolor مثل خودِ ساعت بسازی (شبیه بخش ۳)
    # و AnimatedGifLabel رو توی همون Toplevel قرار بدی، نه اینجا.
    # ------------------------------------------------------------
    gif_widget = None
    if REST_BREAK_GIF_PATH:
        gif_widget = AnimatedGifLabel(popup, REST_BREAK_GIF_PATH, bg=POPUP_BG_COLOR)
        gif_widget.pack(pady=(15, 0))
        gif_widget.start()

    msg = tk.Label(
        popup,
        text="وقت استراحته ☕",
        font=(POPUP_FONT_FAMILY, POPUP_FONT_SIZE),
        fg=POPUP_TEXT_COLOR,
        bg=POPUP_BG_COLOR,
    )
    msg.pack(pady=(20, 10))

    timer_label = tk.Label(
        popup,
        text=f"{REST_BREAK_DURATION_SEC // 60:02d}:{REST_BREAK_DURATION_SEC % 60:02d}",
        font=(POPUP_FONT_FAMILY, 32, "bold"),
        fg=POPUP_ACCENT_COLOR,
        bg=POPUP_BG_COLOR,
    )
    timer_label.pack(pady=10)

    # وضعیت داخلی تایمر (برای این‌که بشه با دکمه‌ی پایان قطعش کرد)
    state = {"remaining": REST_BREAK_DURATION_SEC, "job": None}

    def countdown():
        if state["remaining"] <= 0:
            timer_label.config(text="00:00")
            return
        mins, secs = divmod(state["remaining"], 60)
        timer_label.config(text=f"{mins:02d}:{secs:02d}")
        state["remaining"] -= 1
        state["job"] = popup.after(1000, countdown)

    countdown()

    def end_break():
        global hours_worked
        if state["job"] is not None:
            popup.after_cancel(state["job"])
        if gif_widget is not None:
            gif_widget.stop()   # جلوگیری از باقی‌موندن حلقه‌ی after بعد از بسته‌شدن پنجره
        hours_worked += 1
        update_hours_display()
        popup.destroy()

    end_button = tk.Button(
        popup,
        text="پایان استراحت ✔",
        font=(POPUP_FONT_FAMILY, 14),
        fg="black",
        bg=POPUP_ACCENT_COLOR,
        activebackground=POPUP_ACCENT_COLOR,
        relief="flat",
        padx=10,
        pady=6,
        command=end_break,
    )
    end_button.pack(pady=20)


def schedule_rest_break():
    show_rest_break_popup()
    root.after(REST_BREAK_INTERVAL_MS, schedule_rest_break)


# ============================================================
# بخش ۶ : راه‌اندازی
# ============================================================
# می‌تونی برای تست سریع، مقدار EYE_BREAK_INTERVAL_MS و
# REST_BREAK_INTERVAL_MS رو موقتاً به چند ثانیه (مثلاً 5000)
# تغییر بدی تا لازم نباشه ۲۰/۶۰ دقیقه صبر کنی.

update_clock()
update_hours_display()
root.after(EYE_BREAK_INTERVAL_MS, schedule_eye_break)
root.after(REST_BREAK_INTERVAL_MS, schedule_rest_break)

root.mainloop()