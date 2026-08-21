# راهنمای بالا آوردن سایت روی دامنه‌ی واقعی (kasbyarmarket.ir)

این راهنما فرض می‌کند دامنه‌ات را خریده‌ای و یک سرور لینوکسی (Ubuntu 22.04) کرایه کرده‌ای.
تمام دستورها را روی همان سرور (نه کامپیوتر شخصی‌ات) اجرا می‌کنی، معمولاً از طریق SSH.

---

## ۱) اتصال دامنه به سرور (DNS)

در پنل همان‌جایی که دامنه را خریدی، یک رکورد از نوع **A** بساز:

| نوع | Host | مقدار |
|-----|------|-------|
| A   | @    | آی‌پی سرورت |
| A   | www  | آی‌پی سرورت |

این تغییر معمولاً بین چند دقیقه تا چند ساعت طول می‌کشد تا فعال شود.

---

## ۲) آماده‌سازی سرور

با SSH به سرور وصل شو، بعد:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv nginx git
```

---

## ۳) انتقال پروژه به سرور

پوشه `kasbyarmarketbot` را در مسیر `/opt/kasbyarmarketbot` روی سرور قرار بده (با `scp`، `git clone`، یا آپلود مستقیم).

```bash
sudo mkdir -p /opt/kasbyarmarketbot
# فایل‌ها را اینجا کپی کن (مثلاً با scp از کامپیوتر خودت)
cd /opt/kasbyarmarketbot

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

فایل `.env` را ویرایش کن و حتماً این دو مقدار را عوض کن:

```
WEB_SECRET_KEY=یک-رشته-تصادفی-طولانی-بساز
ADMIN_WEB_PASSWORD=یک-رمز-قوی
```

---

## ۴) اجرای دائمی سرویس‌ها (systemd)

فایل‌های آماده در پوشه‌ی `deploy/` این پروژه هستند. کپی‌شان کن:

```bash
sudo cp deploy/kasbyarmarket-web.service /etc/systemd/system/
sudo cp deploy/kasbyarmarket-bot.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable kasbyarmarket-web kasbyarmarket-bot
sudo systemctl start kasbyarmarket-web kasbyarmarket-bot
```

بررسی این‌که درست بالا اومدن:

```bash
sudo systemctl status kasbyarmarket-web
sudo systemctl status kasbyarmarket-bot
```

از این به بعد، حتی اگر سرور ری‌استارت شود، هر دو سرویس خودکار دوباره اجرا می‌شوند.

---

## ۵) وصل کردن Nginx (تا سایت روی پورت ۸۰ در دسترس باشد)

```bash
sudo cp deploy/nginx_kasbyarmarket.conf /etc/nginx/sites-available/kasbyarmarket
sudo ln -s /etc/nginx/sites-available/kasbyarmarket /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

الان با باز کردن `http://kasbyarmarket.ir` باید سایت را ببینی.

---

## ۶) فعال کردن HTTPS (قفل سبز 🔒)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d kasbyarmarket.ir -d www.kasbyarmarket.ir
```

Certbot خودش تنظیمات Nginx را برای HTTPS اصلاح می‌کند و گواهی را هر ۹۰ روز خودکار تمدید می‌کند.

---

## بعد از این مرحله

- سایت: `https://kasbyarmarket.ir`
- پنل مدیریت: `https://kasbyarmarket.ir/admin/login`
- برای هر تغییر در کد، فایل‌های جدید را جایگزین کن و بزن: `sudo systemctl restart kasbyarmarket-web`

## اگر خواستی به‌جای انجام دستی این مراحل کمک بگیری

اگه به سرورت SSH داری و می‌خوای من مرحله‌به‌مرحله کنار دستت باشم برای اجرای همین دستورها (یا اگه توی یکی از مراحل گیر کردی)، بگو تا با هم جلو بریم.
