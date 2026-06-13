import os

import tempfile

import random  



os.environ['TMPDIR'] = '/tmp'

tempfile.tempdir = '/tmp'



from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_from_directory

from flask_mail import Mail, Message

from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature

import stripe  

import requests 



app = Flask(__name__, template_folder='templates')



app.secret_key = os.environ.get('FLASK_SECRET_KEY')



stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')



app.config['MAIL_SERVER'] = 'smtp-relay.brevo.com'

app.config['MAIL_PORT'] = 587

app.config['MAIL_USE_TLS'] = True

app.config['MAIL_USE_SSL'] = False # جربي تعطيل SSL

app.config['MAIL_USERNAME'] = 'ae9d28001@smtp-brevo.com'

app.config['MAIL_PASSWORD'] = '0vUzKqm79BZ6tH2A'

app.config['MAIL_DEFAULT_SENDER'] = 'support@gharsah.shop'

BREVO_API_KEY = os.environ.get('BREVO_API_KEY')

def send_email_api(to_email, subject, body):
    url = "https://api.brevo.com/v3/smtp/email"
    payload = {
        "sender": {"name": "غرسة", "email": "support@gharsah.shop"},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": body
    }
    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }
    try:
        requests.post(url, json=payload, headers=headers)
    except Exception as e:
        print(f"Email error: {e}")

mail = Mail(app)

s = URLSafeTimedSerializer(app.secret_key)



users = {}

orders_db = {} 



ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') 



@app.route('/styles.css')

def styles():

    return send_from_directory('.', 'styles.css')



@app.route('/')

def home():

    user_email = session.get('user_email', '')

    username = session.get('username', '')

    return render_template('index.html', user_email=user_email, username=username)



@app.route('/auth')

def auth_page():

    if 'user_email' in session:

        return redirect(url_for('home'))

    return render_template('login.html')



@app.route('/profile')

def profile_page():

    if 'user_email' not in session:

        return "<h3>عذراً، يجب تسجيل الدخول أولاً لرؤية الملف الشخصي</h3><a href='/auth'>دخول</a>"

    

    email = session['user_email']

    username = session['username']

    user_orders = orders_db.get(email, [])

    return render_template('profile.html', email=email, username=username, orders=user_orders)



@app.route('/admin/login', methods=['GET', 'POST'])

def admin_login():

    if request.method == 'POST':

        email = request.form.get('email')

        password = request.form.get('password')

        

        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:

            session['admin_logged_in'] = True

            return jsonify({'success': True, 'redirect': url_for('admin_dashboard')})

        else:

            return jsonify({'success': False, 'message': '❌ خطأ: بيانات الدخول الخاصة بالإدارة غير صحيحة!'})

            

    return render_template('admin_login.html')



@app.route('/admin')

def admin_dashboard():

    if not session.get('admin_logged_in'):

        return "<h2 style='color:red; text-align:center; margin-top:50px;'>⛔ خطأ أمني: عذراً، هذه الصفحة مخصصة لإدارة ومتجر غرسة فقط!</h2><br><center><a href='/'>العودة للمتجر</a></center>", 403

        

    all_orders = []

    for customer_email in list(orders_db.keys()):

        user_data = users.get(customer_email, {})

        customer_name = user_data.get('username') if user_data else customer_email.split('@')[0]

        orders_list = orders_db.get(customer_email, [])

        

        for index, single_order in enumerate(orders_list):

            plants_bought = single_order.get('plants_list', 'نباتات غير محددة')

            full_address = f"المدينة: {single_order.get('city', 'غير محدد')} | الحي: {single_order.get('district', 'غير محدد')} | العنوان الوطني: {single_order.get('national_address', 'غير محدد')} | الجوال: {single_order.get('phone', 'غير محدد')}"

            

            all_orders.append({

                'index': index,

                'order_id': single_order.get('order_id', 'N/A'), 

                'name': customer_name,

                'email': customer_email,

                'items': str(plants_bought),

                'plants_list': str(plants_bought),

                'total': single_order.get('total', '0'),

                'status': single_order.get('status', 'قيد التجهيز ⏳'),

                'address': full_address

            })

            

    return render_template('admin.html', orders=all_orders)



@app.route('/admin/update_status', methods=['POST'])

def update_order_status():

    if not session.get('admin_logged_in'):

        return "غير مسموح بالإجراء", 403

        

    email = request.form.get('email')

    order_index = int(request.form.get('index'))

    new_status = request.form.get('status')

    

    if email in orders_db and len(orders_db[email]) > order_index:

        orders_db[email][order_index]['status'] = new_status

        return redirect(url_for('admin_dashboard'))

        

    return jsonify({'success': False, 'message': 'تعذر العثور على الطلب.'})



@app.route('/register', methods=['POST'])

def register():

    username = request.form.get('username')

    email = request.form.get('email')

    password = request.form.get('password')

    

    if email in users:

        if users[email]['is_verified']:

            return "<h3>هذا البريد الإلكتروني مسجل ومفعل مسبقاً!</h3><a href='/auth'>العودة للدخول</a>"

        else:

            token = s.dumps(email, salt='email-confirm-salt')

            link = url_for('verify_account', token=token, _external=True)

            

            msg = Message("إعادة إرسال: تأكيد حسابك في متجر غرسة 🌿", recipients=[email])

            msg.body = f"مرحباً {users[email]['username']}،\n\nيرجى الضغط على الرابط التالي لتفعيل حسابك (الرابط صالحة لمدة ساعة):\n\n{link}"

try:
                send_email_api(
                    email, 
                    "إعادة إرسال: تأكيد حسابك في متجر غرسة 🌿", 
                    f"مرحباً {users[email]['username']}،\n\nيرجى الضغط على الرابط التالي لتفعيل حسابك:\n\n{link}"
                )
                return "<h2>تم إعادة إرسال رابط التفعيل بنجاح! 🎉</h2><p>تفقد بريدك الوارد.</p><br><a href='/auth'>العودة لصفحة الدخول</a>"
            except Exception as e:
                return f"خطأ في الإرسال: {str(e)}"

    

    users[email] = {'username': username, 'password': password, 'is_verified': False}

    

    token = s.dumps(email, salt='email-confirm-salt')

    link = url_for('verify_account', token=token, _external=True)

    

    msg = Message("تأكيد حسابك في متجر غرسة 🌿", recipients=[email])

    msg.body = f"مرحباً {username}،\n\nيرجى تفعيل حسابك عبر الرابط الآمن التالي:\n\n{link}"

    try:

        mail.send(msg)

        return "<h2>تم إنشاء الحساب بنجاح! 🎉</h2><p>تفقد بريدك الإلكتروني لتفعيله عبر الرابط المشفر المرسل إليك، ثم يمكنك تسجيل الدخول.</p><br><a href='/auth'>الذهاب لتسجيل الدخول</a>"

    except Exception as e:

        return f"حدث خطأ أثناء إرسال البريد: {str(e)} <br> الحساب تم إنشاؤه محلياً في السيرفر."



@app.route('/verify/<token>')

def verify_account(token):

    try:

        email = s.loads(token, salt='email-confirm-salt', max_age=3600)

    except SignatureExpired:

        return "<h2>❌ خطأ: انتهت صلاحية رابط تفعيل الحساب (الروابط صالحة لمدة ساعة فقط).</h2>"

    except BadTimeSignature:

        return "<h2>❌ خطأ: رابط التفعيل غير صالح أو تم التلاعب به برمجياً.</h2>"



    if email in users:

        users[email]['is_verified'] = True

        return "<h2>تم تفعيل حسابك بنجاح وبشكل آمن! 🌿</h2><br><a href='/auth'>اضغط هنا للانتقال إلى صفحة تسجيل الدخول</a>"

    

    return "<h2>❌ خطأ: المستخدم غير مسجل في النظام.</h2>"



@app.route('/login', methods=['POST'])

def login():

    email = request.form.get('email')

    password = request.form.get('password')

    

    user = users.get(email)

    if user and user['password'] == password:

        if not user['is_verified']:

            return jsonify({'success': False, 'message': '⚠️ يرجى تفعيل حسابك أولاً من خلال الرابط المرسل إلى بريدك الإلكتروني!'})

        

        session['user_email'] = email

        session['username'] = user['username']

        return jsonify({'success': True, 'redirect': url_for('home')})

        

    return jsonify({'success': False, 'message': '❌ البريد الإلكتروني أو كلمة المرور غير صحيحة!'})



@app.route('/forgot-password', methods=['GET', 'POST'])

def forgot_password():

    if request.method == 'POST':

        email = request.form.get('email')

        if email in users:

            token = s.dumps(email, salt='password-reset-salt')

            link = url_for('reset_password', token=token, _external=True)

            

            msg = Message("استعادة كلمة المرور - متجر غرسة 🌿", recipients=[email])

            msg.body = f"مرحباً،\n\nلقد طلبت استعادة كلمة المرور لحسابك في متجر غرسة.\nيرجى الضغط على الرابط التالي لتعيين كلمة مرور جديدة (الرابط صالحة لمدة 10 دقائق):\n\n{link}"

            try:

                mail.send(msg)

                return "تم إرسال رابط استعادة كلمة المرور إلى بريدك الإلكتروني بنجاح! تفقد صندوق الوارد أو البريد المهمل."

            except Exception as e:

                return f"حدث خطأ أثناء إرسال البريد: {str(e)}"

        else:

            return "هذا البريد الإلكتروني غير مسجل لدينا!"

            

    return render_template('forgot_password.html')



@app.route('/reset-password/<token>', methods=['GET', 'POST'])

def reset_password(token):

    try:

        email = s.loads(token, salt='password-reset-salt', max_age=600)

    except SignatureExpired:

        return "<h2>❌ خطأ: انتهت صلاحية رابط استعادة كلمة المرور (10 دقائق).</h2><a href='/forgot-password'>حاول مجدداً</a>"

    except BadTimeSignature:

        return "<h2>❌ خطأ: رابط الاستعادة غير صالح أو تم التلاعب به.</h2>"



    if request.method == 'POST':

        new_password = request.form.get('password')

        if email in users:

            users[email]['password'] = new_password

            return "<h2>تم تحديث كلمة المرور بنجاح! 🎉</h2><br><a href='/auth'>اضغط هنا للانتقال لصفحة تسجيل الدخول</a>"

        return "خطأ: المستخدم لم يعد موجوداً."

        

    return render_template('reset_password.html', token=token)





@app.route('/checkout', methods=['POST'])

def checkout():

    if 'user_email' not in session:

        return jsonify({'success': False, 'message': 'Authentication required!'})



    data = request.get_json() or {}

    cart_items = data.get('items', [])

    address_info = data.get('address_info', {})

    

    if not cart_items:

        return jsonify({'success': False, 'message': 'Cart is empty!'})



    calculated_total_amount = 0

    items_text_list = []



    for item in cart_items:

        plant_name = str(item.get('name', 'Plant'))

        plant_qty = int(item.get('quantity', 1))

        plant_price = float(item.get('price', 0))

        

        calculated_total_amount += int(plant_price * plant_qty * 100)

        items_text_list.append(f"{plant_name} ({plant_qty})")



    final_clean_string = " + ".join(items_text_list)



    random_order_id = f"GHS-{random.randint(10000, 99999)}"



    session['pending_order'] = {

        'order_id': random_order_id,  # ✨ حفظ رقم الطلب هنا

        'plants_list': final_clean_string,  

        'total': str(data.get('total', '0')),

        'city': str(address_info.get('city', 'غير محدد')),

        'district': str(address_info.get('district', 'غير محدد')),

        'national_address': str(address_info.get('national_address', 'غير محدد')),

        'phone': str(address_info.get('phone', 'غير محدد'))

    }



    payload = {

        'payment_method_types[0]': 'card',

        'line_items[0][price_data][currency]': 'sar',

        'line_items[0][price_data][product_data][name]': 'Gharsah Store Plants Purchase Bundle',

        'line_items[0][price_data][unit_amount]': calculated_total_amount,

        'line_items[0][quantity]': 1,

        'mode': 'payment',

        'success_url': url_for('payment_success', _external=True),

        'cancel_url': url_for('home', _external=True),

    }



    headers = {

        'Authorization': f'Bearer {stripe.api_key}',

        'Content-Type': 'application/x-www-form-urlencoded'

    }



    try:

        response = requests.post('https://api.stripe.com/v1/checkout/sessions', data=payload, headers=headers)

        response_data = response.json()



        if response.status_code == 200 and 'url' in response_data:

            return jsonify({'success': True, 'stripe_url': response_data['url']})

        else:

            stripe_err = response_data.get('error', {}).get('message', 'Stripe connection failure')

            return jsonify({'success': False, 'message': f'Stripe Error: {stripe_err}'})



    except Exception as e:

        return jsonify({'success': False, 'message': f'Network Connection Error: {str(e)}'})





@app.route('/payment-success')

def payment_success():

    if 'user_email' not in session or 'pending_order' not in session:

        return redirect(url_for('home'))

        

    customer_email = session['user_email']

    order_entry = session.pop('pending_order') 

    

    order_id = order_entry.get('order_id', 'N/A')

    

    if customer_email not in orders_db:

        orders_db[customer_email] = []

        

    orders_db[customer_email].append(order_entry)

    

    return f"<h2>🎉 تم الدفع بنجاح عبر Stripe وسُجل طلبك برقم ({order_id}) في متجر غرسة!</h2><br><a href='/profile'>اضغطي هنا للذهاب لصفحة فواتيرك</a>"



@app.route('/logout')

def logout_action():

    session.clear()

    return redirect(url_for('home'))



if __name__ == '__main__':

    app.run(port=3000, debug=True)
