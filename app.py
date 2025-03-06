from flask import Flask, render_template, request, jsonify
import mysql.connector
import telebot

app = Flask(__name__)

# إعداد قاعدة البيانات

db_config = {
    "host": "localhost",
    "user": "alya",
    "password": "mumdad2002",
    "database": "lucky_wheel_bot"
}

# إعداد البوت
BOT_TOKEN = "7640335931:AAE8yJTumsFf93hrewYehNT-lAfyufHEYT4"
bot = telebot.TeleBot(BOT_TOKEN)

def update_user_balance(user_id, result):
    """ تحديث قاعدة البيانات بناءً على النتيجة """
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor2 = conn.cursor()

    cursor2.execute("SELECT spins_remaining FROM users WHERE user_id = %s", (user_id,))
    result2 = cursor2.fetchone()

    if  result2[0] <=  0:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("🎰 Play", "📊 Show Balance")
        markup.row("🎟️ Invite Friends", "💰 Withdraw")
        bot.send_message(user_id, "⚠️ You have no spins left today. Invite friends to earn extra spins!", reply_markup=markup)
        cursor.close()
        cursor2.close()
        conn.close()
        return
    

    # تقليل عدد اللفات المتبقية
    cursor.execute("UPDATE users SET spins_remaining = spins_remaining - 1 WHERE user_id = %s", (user_id,))

    if result == "🎉 $1 WINNER":
        cursor.execute("UPDATE users SET balance = balance + 1 WHERE user_id = %s", (user_id,))
    

    bot.send_message(user_id, f"🎰 Spin Result: {result}")
    
    conn.commit()
    cursor.close()
    conn.close()

@app.route("/spin")
def spin_wheel():
    user_id = request.args.get("user_id")  # استقبال user_id من الرابط
    if not user_id:
        return "User ID is required!", 400
    return render_template("spin.html", user_id=user_id)  # تمرير user_id للصفحة


@app.route("/spin_result", methods=["POST"])
def spin_result():
    data = request.json
    user_id = data.get("user_id")
    result = data.get("result")

    if user_id and result:
        update_user_balance(user_id, result)

    return jsonify({"message": "Result recorded"}), 200

if __name__ == "__main__":
    app.run(debug=True)
