from flask import Flask, render_template, request
import telebot
import mysql.connector
import random
import schedule
import time
from datetime import datetime
import threading
from threading import Thread
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton



# 🟢 أدخلي توكن البوت هنا
BOT_TOKEN = "7640335931:AAE8yJTumsFf93hrewYehNT-lAfyufHEYT4"




# 🟢 إعداد الاتصال بقاعدة البيانات

db = {
    "host": "centerbeam.proxy.rlwy.net",
    "user": "root",
    "password": "dxQBNrjTXzObfDNhuVoHgyNbsaeDsmmr",  # استبدليها بكلمة المرور الصحيحة
    "database": "railway",
    "port": 23305  # هنا تكتبين البورت الصحيح
}



bot = telebot.TeleBot(BOT_TOKEN)



# 🟢 دالة لإنشاء اتصال بقاعدة البيانات عند الحاجة
def connect_db():
    return mysql.connector.connect(**db)



# 🟢 دالة `/start`
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    username = message.chat.username

    if not username:
        username = f"{message.chat.first_name or ''} {message.chat.last_name or ''}".strip()
    if not username:
        username = "Unknown"

    args = message.text.split()
    referred_by = None

    if len(args) > 1 and args[1].isdigit():
        referred_by = int(args[1])

    # 🟢 1. إنشاء اتصال بقاعدة البيانات
    conn = connect_db()  # ✅ الاتصال الصحيح
    cursor = conn.cursor()

    # 🟢 2. التحقق من وجود المستخدم
    cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
    user_exists = cursor.fetchone()

    if not user_exists:
        cursor.execute("INSERT INTO users (user_id, username, referred_by) VALUES (%s, %s, %s)", 
                       (user_id, username, referred_by))
        conn.commit()  # ✅ حفظ التغييرات

        if referred_by:
            # 🟢 تحديث عدد الدعوات
            cursor.execute("UPDATE users SET invites_count = invites_count + 1 WHERE user_id = %s", (referred_by,))
            conn.commit()

            # 🟢 جلب عدد الدعوات بعد التحديث
            cursor.execute("SELECT invites_count FROM users WHERE user_id = %s", (referred_by,))
            referrals = cursor.fetchone()[0]

            # ✅ إرسال رسالة للشخص الذي قام بالدعوة
            remaining = max(15 - referrals, 0)  # لضمان عدم ظهور رقم سالب
            bot.send_message(referred_by, f"📢 You've invited {referrals} friends!\n"
                                          f"🎯 You need {remaining} more invites to get an extra spin! 🎰")

            # ✅ التحقق مما إذا وصل إلى 15 دعوة
            if referrals == 15:
                cursor.execute("UPDATE users SET spins_remaining = spins_remaining + 1 WHERE user_id = %s", (referred_by,))
                conn.commit()
                bot.send_message(referred_by, "🎉 You've invited 15 friends! You got an extra spin! 🎰")

    # 🟢 3. إغلاق الاتصال بعد الاستخدام
    cursor.close()
    conn.close()


    # إرسال رسالة الترحيب
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 Play", "📊 Show Balance")
    markup.row("🎟️ Invite Friends", "💰 Withdraw")

    bot.send_message(user_id, "🎡 *Welcome to Lucky Wheel Bot!* 🎡\n"
                              "Spin the wheel and win exciting rewards! 🏆\n"
                              "Please choose an option from the menu below:",
                     parse_mode="Markdown", reply_markup=markup)

# 🟢 وظيفة "Play"
@bot.message_handler(func=lambda message: message.text == "🎰 Play")
def play_lucky_wheel(message):
    user_id = message.chat.id

    # 🟢 إنشاء الاتصال بقاعدة البيانات
    conn = connect_db()
    cursor = conn.cursor()

    # التحقق من عدد اللفات المتبقية
    cursor.execute("SELECT spins_remaining FROM users WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()

    print(f'spin: {result}')

    # 🟢 إغلاق الاتصال بعد الاستخدام
    cursor.close()
    conn.close()

    if result and result[0] > 0:
         #يرجع للمنيو 
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("🎰 Play", "📊 Show Balance")
        markup.row("🎟️ Invite Friends", "💰 Withdraw")
        # إرسال رابط صفحة العجلة مع الـ user_id
        wheel_url = f"http://127.0.0.1:5000/spin?user_id={user_id}"
        bot.send_message(user_id, f"🎡 Click the link below to spin the wheel!\n\n[🎰 Spin Now]({wheel_url})",
                         parse_mode="Markdown", reply_markup=markup)
    else:
         #يرجع للمنيو 
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("🎰 Play", "📊 Show Balance")
        markup.row("🎟️ Invite Friends", "💰 Withdraw")

        bot.send_message(user_id, "⚠️ You have no spins left today. Invite friends to earn extra spins!", reply_markup=markup)
       




# 🟢 إعادة تعيين عدد اللفات وعدد مرات السحب يوميًا
def reset_daily_data():
    conn = connect_db()
    cursor = conn.cursor()

    # ✅ إعادة تعيين عدد اللفات إلى 1
    cursor.execute("UPDATE users SET spins_remaining = 1")

    # ✅ إعادة تعيين عدد محاولات السحب إلى 1
    cursor.execute("UPDATE users SET withdraw_attempts_remaining = 1")

    conn.commit()
    cursor.close()
    conn.close()

    print(f"✅ Daily reset completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 🟢 ضبط الجدولة اليومية عند منتصف الليل
schedule.every().day.at("00:00").do(reset_daily_data)

# 🟢 تشغيل الجدولة في Thread منفصلة
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)

scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()


# 🟢 دعوة الأصدقاء
@bot.message_handler(func=lambda message: message.text == "🎟️ Invite Friends")
def invite_friends(message):
    user_id = message.chat.id

    # إنشاء رابط الدعوة بناءً على user_id
    invite_link = f"https://t.me/{bot.get_me().username}?start={user_id}"

    # أزرار الرجوع للمنيو
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 Play", "📊 Show Balance")
    markup.row("🎟️ Invite Friends", "💰 Withdraw")

    bot.send_message(user_id, f"📢 Share this link with your friends!\n\n"
                              f"🔗 {invite_link}\n\n"
                              f"Invite 15 friends and get an extra spin for today! 🎰",
                     reply_markup=markup)




#السحب 
    # 🟢 تعريف الاتصال بقاعدة البيانات - تمت إزالة التكرار
def connect_db():
    return mysql.connector.connect(**db)
# 🟢 التحقق من اشتراك المستخدم في القناة

def is_subscribed(user_id):
    chat_id = "-1002342830576"  # Channel ID
    try:
        chat_member = bot.get_chat_member(chat_id, user_id)
        print(f"✅ User {user_id} status: {chat_member.status}")  # طباعة الحالة للمساعدة في التصحيح
        return chat_member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"❌ Error checking subscription for {user_id}: {e}")
        return False

@bot.message_handler(func=lambda message: message.text == "💰 Withdraw")
def withdraw_request(message):
    user_id = message.from_user.id

    if not is_subscribed(user_id):  
         #يرجع للمنيو 
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("🎰 Play", "📊 Show Balance")
        markup.row("🎟️ Invite Friends", "💰 Withdraw")
        bot.send_message(
            user_id,
            "❌ You must subscribe to the channel first to withdraw!\n"
            "🔗 Join here: [lucky_wheel](https://t.me/lucky_wh2el)",
            parse_mode="Markdown",reply_markup=markup
        )
        return  

    conn = mysql.connector.connect(**db)
    cursor = conn.cursor()

    # 🔹 جلب بيانات المستخدم
    cursor.execute("SELECT balance, withdraw_attempts_remaining FROM users WHERE user_id = %s", (user_id,))
    user_data = cursor.fetchone()

    if not user_data:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("🎰 Play", "📊 Show Balance")
        markup.row("🎟️ Invite Friends", "💰 Withdraw")
        bot.send_message(user_id, "❌ You are not registered in the system.",reply_markup=markup)
        cursor.close()
        conn.close()
        return

    balance, withdraw_attempts_remaining = user_data

    # 🔹 التحقق من عدد محاولات السحب
    if withdraw_attempts_remaining <= 0:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("🎰 Play", "📊 Show Balance")
        markup.row("🎟️ Invite Friends", "💰 Withdraw")
        bot.send_message(user_id, "❌ You have already made a withdrawal today. Try again tomorrow.",reply_markup=markup)
        cursor.close()
        conn.close()
        return

    cursor.close()
    conn.close()

    # 🟢 طلب إدخال المبلغ المطلوب
    bot.send_message(user_id, "💵 Please enter the amount you want to withdraw (in $):")
    bot.register_next_step_handler(message, process_withdraw_amount)


def process_withdraw_amount(message):
    user_id = message.from_user.id
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            bot.send_message(user_id, "❌ Invalid amount! Please enter a positive numeric value.")
            return
    except ValueError:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("🎰 Play", "📊 Show Balance")
        markup.row("🎟️ Invite Friends", "💰 Withdraw")
        bot.send_message(user_id, "❌ Invalid input! Please enter a numeric value.",reply_markup=markup)
        return

    conn = mysql.connector.connect(**db)
    cursor = conn.cursor()
    
    cursor.execute("SELECT balance, withdraw_attempts_remaining FROM users WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()

    if not result:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("🎰 Play", "📊 Show Balance")
        markup.row("🎟️ Invite Friends", "💰 Withdraw")
        bot.send_message(user_id, "❌ You are not registered in the system.",reply_markup=markup)
        cursor.close()
        conn.close()
        return

    balance, withdraw_attempts_remaining = result

    # التحقق من محاولات السحب
    if withdraw_attempts_remaining <= 0:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("🎰 Play", "📊 Show Balance")
        markup.row("🎟️ Invite Friends", "💰 Withdraw")
        bot.send_message(user_id, "❌ You have already made a withdrawal today. Try again tomorrow.",reply_markup=markup)
        cursor.close()
        conn.close()
        return
    # التحقق من الرصيد
    if balance == 0:
        #يرجع للمنيو 
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("🎰 Play", "📊 Show Balance")
        markup.row("🎟️ Invite Friends", "💰 Withdraw")
        
        bot.send_message(
            user_id, 
            "⚠️ Your balance is $0. Play to earn money and try again! 🎰",
            reply_markup=markup
        )
        cursor.close()
        conn.close()
        return
    
    if balance < amount:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("🎰 Play", "📊 Show Balance")
        markup.row("🎟️ Invite Friends", "💰 Withdraw")
        bot.send_message(user_id, "⚠️ Insufficient balance! Please enter a lower amount.",reply_markup=markup)
        cursor.close()
        conn.close()
        return

    cursor.close()
    conn.close()

    # 🟢 طلب رقم فودافون كاش
    bot.send_message(user_id, "📱 Please enter your Vodafone Cash number:")
    bot.register_next_step_handler(message, lambda msg: process_withdraw_number(msg, amount))

ADMIN_ID =  [5808711396,1388747442]  #هعغيره برقم الادمن 
def process_withdraw_number(message, amount):
    user_id = message.from_user.id
    phone_number = message.text.strip()

    if not phone_number.isdigit() or len(phone_number) != 11 or not phone_number.startswith("01"):
        bot.send_message(user_id, "❌ Invalid phone number! Please enter a valid 11-digit Vodafone Cash number.")
        return

    conn = mysql.connector.connect(**db)
    cursor = conn.cursor()

    try:
        # 🔹 تحديث الرصيد وتقليل عدد محاولات السحب
        cursor.execute("UPDATE users SET balance = balance - %s, withdraw_attempts_remaining = withdraw_attempts_remaining - 1 WHERE user_id = %s", 
                       (amount, user_id))

        # 🔹 إدخال طلب السحب في `withdraw_requests`
        cursor.execute(
            "INSERT INTO withdraw_requests (user_id, amount, phone_number, status, request_date) VALUES (%s, %s, %s, 'pending', NOW())",
            (user_id, amount, phone_number)
        )

        conn.commit()

        # إرسال رسالة تأكيد للمستخدم
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("🎰 Play", "📊 Show Balance")
        markup.row("🎟️ Invite Friends", "💰 Withdraw")
        bot.send_message(user_id, f"✅ Your withdrawal request of ${amount} has been submitted successfully!\n📞 Vodafone Cash: {phone_number}\n🕒 Please wait for approval.",reply_markup=markup)
        
        # 🔔 إرسال إشعار للأدمن
        bot.send_message(
            ADMIN_ID, 
            f"📢 New Withdrawal Request!\n👤 User ID: `{user_id}`\n💰 Amount: ${amount}\n📞 Vodafone Cash: `{phone_number}`\n⏳ Status: Pending",
            parse_mode="Markdown"
        )

    except Exception as e:
        conn.rollback()
        bot.send_message(user_id, "❌ An error occurred while processing your request. Please try again later.")

    finally:
        cursor.close()
        conn.close()





#عرض الرصيد 
@bot.message_handler(func=lambda message: message.text == "📊 Show Balance")
def show_balance(message):
    user_id = message.chat.id

    conn = mysql.connector.connect(**db)
    cursor = conn.cursor()

    try:
        # جلب الرصيد من جدول `users`
        cursor.execute("SELECT balance FROM users WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()

        if result:
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.row("🎰 Play", "📊 Show Balance")
            markup.row("🎟️ Invite Friends", "💰 Withdraw")
            balance = result[0]
            bot.send_message(user_id, f"💰 Your current balance: **${balance:.2f}**", parse_mode="Markdown",reply_markup=markup)
        else:
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.row("🎰 Play", "📊 Show Balance")
            markup.row("🎟️ Invite Friends", "💰 Withdraw")
            bot.send_message(user_id, "❌ You are not registered in the system.",reply_markup=markup)

    except Exception as e:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("🎰 Play", "📊 Show Balance")
        markup.row("🎟️ Invite Friends", "💰 Withdraw")
        bot.send_message(user_id, "❌ An error occurred. Please try again later.",reply_markup=markup)
        print(f"⚠️ Error fetching balance: {e}")

    finally:
        cursor.close()
        conn.close()








################################################################################################################
#admin 
ADMINS = [5808711396,1388747442]  # استبدل هذه القيم بـ user_id الخاص بالإدمن

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    user_id = message.chat.id

    # التحقق من هوية الأدمن
    if user_id not in ADMINS:
        bot.send_message(user_id, "❌ You are not authorized to access this panel.")
        return
    
    # إنشاء لوحة التحكم بالأزرار
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("📢 Send message to all users"))
    markup.add(KeyboardButton("💰 Manage Withdraw Requests"))

    bot.send_message(user_id, "🔹 Admin Panel:\nChoose an action:", reply_markup=markup)


#send message 
@bot.message_handler(func=lambda message: message.text == "📢 Send message to all users")
def request_broadcast_message(message):
    user_id = message.chat.id
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("📢 Send message to all users"))
    markup.add(KeyboardButton("💰 Manage Withdraw Requests"))
    # التحقق من الأدمن
    if user_id not in ADMINS:
        
        bot.send_message(user_id, "❌ You are not authorized to perform this action.",reply_markup=markup)
        return

    bot.send_message(user_id, "✍️ Please enter the message you want to send to all users:")
    bot.register_next_step_handler(message, send_broadcast_message)

def send_broadcast_message(message):
    user_id = message.chat.id
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("📢 Send message to all users"))
    markup.add(KeyboardButton("💰 Manage Withdraw Requests"))
    admin_id = message.chat.id
    broadcast_text = message.text.strip()

    # التأكد إن الرسالة مش فاضية
    if not broadcast_text:
        bot.send_message(admin_id, "⚠️ The message cannot be empty.")
        return

    # الاتصال بقاعدة البيانات وجلب جميع `user_id`
    conn = mysql.connector.connect(**db)
    cursor = conn.cursor()
    
    cursor.execute("SELECT user_id FROM users")
    user_ids = [row[0] for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()

    # إرسال الرسالة لكل مستخدم
    success_count = 0
    for user_id in user_ids:
        try:
            bot.send_message(user_id, f"📢 Admin Announcement:\n\n{broadcast_text}")
            success_count += 1
        except Exception as e:
            print(f"❌ Failed to send message to {user_id}: {e}")

    # إبلاغ الأدمن بعد الانتهاء
    bot.send_message(admin_id, f"✅ The message has been sent to {success_count} users.",reply_markup=markup)


# Manage Withdraw Requests

@bot.message_handler(func=lambda message: message.text == "💰 Manage Withdraw Requests")
def show_withdraw_requests(message):
    user_id = message.chat.id
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("📢 Send message to all users"))
    markup.add(KeyboardButton("💰 Manage Withdraw Requests"))

    # التحقق من أن المستخدم هو الأدمن
    if user_id not in ADMINS:
        bot.send_message(user_id, "❌ You are not authorized to access this panel.",reply_markup=markup)
        return

    conn = mysql.connector.connect(**db)
    cursor = conn.cursor()

    # جلب جميع طلبات السحب التي حالتها "pending"
    cursor.execute("SELECT id, user_id, amount, phone_number,request_date FROM withdraw_requests WHERE status = 'pending'")
    requests = cursor.fetchall()
    
    cursor.close()
    conn.close()

    if not requests:
        bot.send_message(user_id, "✅ No pending withdrawal requests.")
        return

   # إرسال كل طلب مع أزرار الموافقة والرفض
    for req in requests:
        req_id, req_user, amount, phone, date = req
        
        response = (f"🆔 **Request ID:** {req_id}\n"
                    f"👤 **User ID:** {req_user}\n"
                    f"📞 **Phone:** {phone}\n"
                    f"💵 **Amount:** ${amount}\n"
                    f"📅 **Date:** {date}\n\n"
                    "🔹 Choose an action:")

        # إنشاء أزرار الموافقة والرفض
        markup = InlineKeyboardMarkup()
        approve_btn = InlineKeyboardButton("✅ Approve", callback_data=f"approve_{req_id}")
        reject_btn = InlineKeyboardButton("❌ Reject", callback_data=f"reject_{req_id}")
        markup.add(approve_btn, reject_btn)

        bot.send_message(user_id, response, reply_markup=markup)


# approve 
@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_") or call.data.startswith("reject_"))
def handle_withdraw_action(call):
    admin_id = call.message.chat.id

    # التحقق من أن المستخدم هو الأدمن
    if admin_id not in ADMINS:
        bot.answer_callback_query(call.id, "❌ You are not authorized to perform this action.", show_alert=True)
        return

    action, request_id = call.data.split("_")  # تقسيم الكول باك داتا
    request_id = int(request_id)

    conn = mysql.connector.connect(**db)
    cursor = conn.cursor()

    # جلب بيانات الطلب
    cursor.execute("SELECT user_id, amount FROM withdraw_requests WHERE id = %s", (request_id,))
    request = cursor.fetchone()

    if not request:
        bot.answer_callback_query(call.id, "❌ Request not found!", show_alert=True)
        return

    user_id, amount = request

    if action == "approve":
        new_status = "approved"
        message_to_user = f"✅ Your withdrawal request of ${amount} has been **approved**. You will receive your funds soon."
    else:
        new_status = "rejected"
        message_to_user = f"❌ Your withdrawal request of ${amount} has been **rejected**. Please try again later."

    # تحديث حالة الطلب في قاعدة البيانات
    cursor.execute("UPDATE withdraw_requests SET status = %s WHERE id = %s", (new_status, request_id))
    conn.commit()
    
    cursor.close()
    conn.close()

    # إرسال إشعار للمستخدم
    bot.send_message(user_id, message_to_user)

    # تأكيد الإجراء للأدمن
    bot.answer_callback_query(call.id, f"✔️ Request {request_id} marked as {new_status}.", show_alert=True)








# 🟢 تشغيل البوت
bot.polling()
