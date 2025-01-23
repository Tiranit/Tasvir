import ccxt
import pandas as pd
import smtplib, ssl
import time
import os
import numpy as np
import mplfinance as mpf
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# تابع ارسال ایمیل با تقسیم تصاویر
def send_email(subject, body, images):
    sender_email = os.getenv("SENDER_EMAIL")  # ایمیل فرستنده از متغیر محیطی
    receiver_email = os.getenv("RECEIVER_EMAIL")  # ایمیل گیرنده از متغیر محیطی
    password = os.getenv("EMAIL_PASSWORD")  # رمز عبور ایمیل از متغیر محیطی

    # تعیین حداکثر حجم مجاز برای هر ایمیل (20 مگابایت)
    max_email_size = 20 * 1024 * 1024  # 20 مگابایت

    # تقسیم تصاویر به گروه‌هایی با حجم کم‌تر از 20 مگابایت
    email_images = []
    current_email_size = 0
    current_images = []

    for image in images:
        image_size = os.path.getsize(image)
        
        # اگر اضافه کردن تصویر به گروه فعلی باعث افزایش حجم بیشتر از حد مجاز می‌شود
        if current_email_size + image_size > max_email_size:
            # ارسال ایمیل قبلی با تصاویر جمع‌آوری‌شده
            send_single_email(subject, body, current_images, sender_email, receiver_email, password)
            # بازنشانی گروه و شروع ارسال ایمیل جدید
            current_images = [image]
            current_email_size = image_size
        else:
            # افزودن تصویر به گروه فعلی
            current_images.append(image)
            current_email_size += image_size

    # ارسال ایمیل نهایی با باقی‌مانده تصاویر
    if current_images:
        send_single_email(subject, body, current_images, sender_email, receiver_email, password)

# تابع ارسال یک ایمیل واحد
def send_single_email(subject, body, images, sender_email, receiver_email, password):
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    for image in images:
        with open(image, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={os.path.basename(image)}",
        )
        message.attach(part)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())

# تابع رسم نمودار
def plot_chart(exchange, symbol, timeframe, length):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)

        df_length = df.tail(length)

        df_length['EMA12'] = df_length['close'].ewm(span=12, adjust=False).mean()
        df_length['EMA26'] = df_length['close'].ewm(span=26, adjust=False).mean()
        df_length['MACD'] = df_length['EMA12'] - df_length['EMA26']
        df_length['Signal Line'] = df_length['MACD'].ewm(span=9, adjust=False).mean()

        high_price = df_length['high'].max()
        low_price = df_length['low'].min()

        log_high_price = np.log(high_price)
        log_low_price = np.log(low_price)

        fib_colors = {
            0.0: 'gray',
            0.236: 'blue',
            0.382: 'purple',
            0.5: 'green',
            0.618: 'orange',
            0.764: 'red',
            1.0: 'gray'
        }

        levels = [0.0, 0.236, 0.382, 0.5, 0.618, 0.764, 1.0]
        fib_levels = {}
        for level in levels:
            log_fib_level = log_high_price - (log_high_price - log_low_price) * level
            fib_levels[level] = np.exp(log_fib_level)

        addplots = [
            mpf.make_addplot(df_length['MACD'], panel=1, color='black'),
            mpf.make_addplot(df_length['Signal Line'], panel=1, color='red')
        ]

        for level, value in fib_levels.items():
            addplots.append(mpf.make_addplot([value] * len(df_length), color=fib_colors[level], linestyle='dashed'))

        os.makedirs('charts', exist_ok=True)
        chart_file = f'charts/{symbol.replace("/", "_")}_{timeframe}_{length}candles.png'
        title = f'{symbol} {timeframe} {length} Candles'
        mpf.plot(df_length, type='candle', addplot=addplots, volume=True, style='yahoo',
                 savefig=dict(fname=chart_file, dpi=100, bbox_inches="tight"),
                 title=title, ylabel='Price (log scale)', yscale='log')
        return chart_file

    except Exception as e:
        print(f"Error plotting data for {symbol} in {timeframe} with {length} candles: {e}")
        return None

# تنظیمات اولیه
exchange = ccxt.kucoin()
symbols = ['BTC/USDT', 'XRP/USDT', 'ETH/USDT', 'USDC/USDT', 'DOGE/USDT', 'SOL/USDT', 'HBAR/USDT', 'LTC/USDT', 'SUI/USDT', 'PEPE/USDT', 'ADA/USDT', 'SOLV/USDT', 'BNB/USDT', 'XLM/USDT', 'SHIB/USDT', 'ENA/USDT', 'TRX/USDT', 'LINK/USDT', 'AIXBT/USDT', 'PNUT/USDT', 'WIF/USDT', 'WLD/USDT', 'RUNE/USDT', 'ALGO/USDT', 'AVAX/USDT', 'NEIRO/USDT', 'EOS/USDT', 'VET/USDT', 'NEAR/USDT', 'SAND/USDT', 'MOVE/USDT', 'BONK/USDT', 'FET/USDT', 'APT/USDT', 'DOT/USDT', 'FIL/USDT', 'AAVE/USDT', 'UNI/USDT', 'TAO/USDT', 'FLOKI/USDT', 'USUAL/USDT', 'CRV/USDT', 'PHA/USDT', 'TIA/USDT', 'AMP/USDT', 'PENGU/USDT', 'ARB/USDT', 'INJ/USDT', 'CGPT/USDT', 'SEI/USDT', 'IOTA/USDT', 'BCH/USDT', 'RENDER/USDT', 'ZEN/USDT', 'OP/USDT', 'BIO/USDT', 'TON/USDT', 'JASMY/USDT', 'GMT/USDT', 'ICP/USDT', 'ATOM/USDT', 'PENDLE/USDT', 'ETC/USDT', 'RAY/USDT', 'KDA/USDT', 'RSR/USDT', 'BOME/USDT', 'POL/USDT', 'CFX/USDT', 'GRT/USDT', 'VANA/USDT', 'ZRO/USDT', 'IO/USDT', 'ETHFI/USDT', 'STX/USDT', 'ENS/USDT', 'WBTC/USDT', 'COOKIE/USDT', 'TURBO/USDT', 'DYDX/USDT', 'ZK/USDT', 'SUSHI/USDT', 'JUP/USDT', 'BLZ/USDT', 'LDO/USDT', 'ORDI/USDT', 'NOT/USDT', 'EIGEN/USDT', 'OM/USDT', 'THETA/USDT', 'AR/USDT', 'NEO/USDT', 'COW/USDT', 'APE/USDT', 'MANA/USDT', 'MKR/USDT', 'KAIA/USDT', 'CAKE/USDT', 'ARKM/USDT', 'STRK/USDT', 'MEME/USDT', 'EDU/USDT', 'BAL/USDT', 'XAI/USDT', 'CHZ/USDT', 'MANTA/USDT', 'DASH/USDT', 'FTT/USDT', 'BLUR/USDT', 'PROM/USDT', 'SUPER/USDT', 'EGLD/USDT', 'ROSE/USDT', 'ONE/USDT', 'CETUS/USDT', 'LPT/USDT', 'AGLD/USDT', 'FIDA/USDT', 'XTZ/USDT', 'ALT/USDT', 'LUMIA/USDT', 'W/USDT', 'JTO/USDT', 'AXS/USDT', 'LUNC/USDT', 'PYR/USDT', 'COMP/USDT', 'PEOPLE/USDT', 'ME/USDT', 'DOGS/USDT', 'ZRX/USDT', 'PYTH/USDT', 'LUNA/USDT', 'LQTY/USDT', 'QNT/USDT', 'STG/USDT', 'SNX/USDT', 'BB/USDT', 'IOST/USDT', 'ASTR/USDT', 'TRB/USDT', 'SSV/USDT', 'ZIL/USDT', 'PIXEL/USDT', 'MINA/USDT', 'PORTAL/USDT', 'LISTA/USDT', 'IMX/USDT', 'YFI/USDT', 'CELO/USDT', 'ACX/USDT', 'DEXE/USDT', 'WOO/USDT', '1INCH/USDT', 'CKB/USDT', 'FLOW/USDT', 'SCR/USDT', 'ATA/USDT', 'AEVO/USDT', 'VANRY/USDT', 'ONT/USDT', 'ENJ/USDT', 'ANKR/USDT', 'QKC/USDT', 'MAGIC/USDT', 'COTI/USDT', 'AVA/USDT', 'HMSTR/USDT', 'ZEC/USDT', 'DYM/USDT', 'FXS/USDT', 'METIS/USDT', 'SKL/USDT', 'UTK/USDT', 'GAS/USDT', 'OMNI/USDT', 'QTUM/USDT', 'LRC/USDT', 'KSM/USDT', 'YGG/USDT', 'ACH/USDT', 'GMX/USDT', 'DENT/USDT', 'GLMR/USDT', 'CYBER/USDT', 'POLYX/USDT', 'ACE/USDT', 'TRU/USDT', 'CVX/USDT', 'WIN/USDT', 'JST/USDT', 'HIGH/USDT', 'C98/USDT', 'MBL/USDT', 'REZ/USDT', 'RVN/USDT', 'STORJ/USDT', 'BAT/USDT', 'CATI/USDT', 'CLV/USDT', 'DEGO/USDT', 'XEC/USDT', 'TLM/USDT', 'ID/USDT', 'TNSR/USDT', 'SLP/USDT', 'SXP/USDT', 'ILV/USDT', 'ORCA/USDT', 'FLUX/USDT', 'TFUEL/USDT', 'KAVA/USDT', 'POND/USDT', 'MOVR/USDT', 'MASK/USDT', 'PAXG/USDT', 'BICO/USDT', 'USTC/USDT', 'CHR/USDT', 'ELF/USDT', 'IOTX/USDT', 'API3/USDT', 'NTRN/USDT', 'ICX/USDT', 'HIFI/USDT', 'TWT/USDT', 'DGB/USDT', 'STRAX/USDT', 'OSMO/USDT', 'ALPHA/USDT', 'CVC/USDT', 'NMR/USDT', 'NFP/USDT', 'OGN/USDT', 'SCRT/USDT', 'CELR/USDT', 'RDNT/USDT', 'LSK/USDT', 'UMA/USDT', 'AUCTION/USDT', 'AUDIO/USDT', 'BANANA/USDT', 'ARPA/USDT', 'COMBO/USDT', 'SYN/USDT', 'REQ/USDT', 'SLF/USDT', 'RPL/USDT', 'DUSK/USDT', 'HFT/USDT', 'ALICE/USDT', 'RLC/USDT', 'SUN/USDT', 'GLM/USDT', 'KNC/USDT', 'WAXP/USDT', 'AMB/USDT', 'MAV/USDT', 'G/USDT', 'CTSI/USDT', 'LINA/USDT', 'VIDT/USDT', 'OXT/USDT', 'T/USDT', 'DODO/USDT', 'BAND/USDT', 'MTL/USDT', 'LIT/USDT', 'ADX/USDT', 'VOXEL/USDT', 'PUNDIX/USDT', 'TUSD/USDT', 'AERGO/USDT', 'ALPINE/USDT', 'DIA/USDT', 'ERN/USDT', 'BURGER/USDT', 'PERP/USDT', 'NKN/USDT', 'QI/USDT', 'CREAM/USDT', 'SYS/USDT', 'GTC/USDT', 'BSW/USDT', 'XNO/USDT', 'HARD/USDT', 'DCR/USDT', 'LTO/USDT', 'SFP/USDT', 'USDP/USDT', 'FORTH/USDT', 'GNS/USDT', 'DATA/USDT', 'QUICK/USDT', 'KMD/USDT', 'WAN/USDT', 'LOKA/USDT', 'XEM/USDT', 'WAVES/USDT', 'ETHUP/USDT', 'BTCUP/USDT', 'OMG/USDT', 'XMR/USDT', 'HNT/USDT', 'BULL/USDT', 'EPX/USDT', 'POLS/USDT', 'UNFI/USDT', 'BOND/USDT', 'REN/USDT', 'BSV/USDT', 'BTT/USDT', 'REEF/USDT', 'LOOM/USDT', 'KEY/USDT']
timeframes = [('30m', 150), ('1h', 200), ('4h', 300), ('1d', 400)]

# اجرای اسکریپت
def main():
    all_results = []
    all_images = []

    for symbol in symbols:
        results = [symbol]
        for timeframe, length in timeframes:
            try:
                bars = exchange.fetch_ohlcv(symbol, timeframe)
                df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['SMA5'] = df['close'].rolling(window=5).mean()
                df['SMA10'] = df['close'].rolling(window=10).mean()
                df['SMA15'] = df['close'].rolling(window=15).mean()
                df['SMA20'] = df['close'].rolling(window=20).mean()

                filtered_df = df[(df['close'] < df['SMA5']) & 
                                 (df['close'] < df['SMA10']) & 
                                 (df['close'] < df['SMA15']) & 
                                 (df['close'] < df['SMA20']) & 
                                 (df['close'].iloc[-1] < df['low'].iloc[-3:-1].min())]

                if not filtered_df.empty:
                    results.append(timeframe)
                    chart = plot_chart(exchange, symbol, timeframe, length)
                    if chart:
                        all_images.append(chart)

            except Exception as e:
                print(f"Error fetching data for {symbol} in {timeframe}: {e}")
                continue

        if len(results) > 1:
            all_results.append(' '.join(results))

    if all_results:
        send_email("Alert", '\n'.join(all_results), all_images)

if __name__ == "__main__":
    main()
