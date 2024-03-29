import base64
import sqlite3
import hashlib
from flask_login import current_user, login_user, login_required, logout_user
from flask import redirect, render_template, request, url_for
from func.login import correct_login_information
from func.sign_up import add_user, hash_new_pass
import sqlite3
import bcrypt
from cryptography.fernet import Fernet
import hashlib
from flask import Flask
import flask_login
from flask_login import UserMixin
import random

class User(UserMixin):
    pass

class Password():
    pass

app = Flask(__name__)
app.config['SECRET_KEY'] = str(random.randint(0, 10))

login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = sqlite3.connect("data.db")
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users (email VARCHAR(100) PRIMARY KEY, password CHAR(60) NOT NULL)")
cur.execute("CREATE TABLE IF NOT EXISTS passwords (id INTEGER PRIMARY KEY, owner VARCHAR(100), name TEXT NOT NULL, username TEXT, password TEXT, hash TEXT, url TEXT)")

conn.commit()
conn.close()

@login_manager.user_loader
def load_user(email):
    conn = sqlite3.connect("data.db")
    cur = conn.cursor()

    # Check to see if the email is in the database
    cur.execute("SELECT email FROM users WHERE email = ?", (email,))
    email = cur.fetchone()
    conn.close()

    if email:
        user = User()
        user.id = email[0]
        return user


user_keys = {} # "email": "password"

# Create the default app route
@app.route('/')
def index():
    return render_template('index.html')


# Create the incompatible_width route
@app.route('/incompatible_width')
def incompatible_width():
    return render_template('incompatible_width.html')


# Create the login app route
@app.route('/login', methods = ['POST', 'GET'])
async def login():
    # If the user attempts to login, check the email/username and password against the valid DB entries
    # If the login information is correct, redirect to the dashboard page, otherwise alert the user
    if(request.method == 'POST'):
        if(await correct_login_information(request.form['email'], request.form['password'])):
            user = User()
            user.id = request.form['email']
            login_user(user, remember=True)

            # Hash the password in sha512, turn it into a bytes object, and then encode it in base64
            hashed_pass = hashlib.sha512(request.form['password'].encode()).hexdigest()
            hashed_pass = bytes(hashed_pass[:32], 'utf-8')
            hashed_pass = base64.b64encode(hashed_pass)
            user_keys[user.id] = hashed_pass

            return redirect(url_for('dashboard'))

        return render_template('login.html', error_message='Incorrect email/password. Please try again.')

    elif(request.method == 'GET'):
        if(current_user.is_authenticated):
            if current_user.id not in user_keys:
                logout_user()
                return redirect(url_for('login'))

            return redirect(url_for('dashboard'))

        return render_template('login.html')


# Create the signup route
# If the user attempts to sign up, try to add the new information to the DB, if it fails, then the
# email/username is already taken, so alert the user, otherwise, redirect to the login page

# Make sure that the passwords are hashed and never stored as plaintext in the DB
@app.route('/signup', methods = ['POST', 'GET'])
async def signup():
    if(request.method == 'POST'):
        response = await add_user(request.form['email'], request.form['password'])
        if response == True:
            return render_template('login.html', success_message='Account created successfully. Please login to continue.')
        elif response == "Email too long":
            return render_template('signup.html', error_message='Email too long. Email addresses must be less than 100 characters. Please try again.')
        elif response == "Password too long":
            return render_template('signup.html', error_message='Password too long. Passwords must be less than 100 characters. Please try again.')
        else:
            return render_template('signup.html', error_message='Email already taken, please try again with a different email address.')

    return render_template('signup.html')


user_pfp_path = {'a':'pfp_a.png', 'b':'pfp_b.png', 'c':'pfp_c.png', 'd':'pfp_d.png', 'e':'pfp_e.png',
'f':'pfp_f.png', 'g':'pfp_g.png', 'h':'pfp_h.png', 'i':'pfp_i.png', 'j':'pfp_j.png', 'k':'pfp_k.png',
'l':'pfp_l.png', 'm':'pfp_m.png', 'n':'pfp_n.png', 'o':'pfp_o.png', 'p':'pfp_p.png', 'q':'pfp_q.png',
'r':'pfp_r.png', 's':'pfp_s.png', 't':'pfp_t.png', 'u':'pfp_u.png', 'v':'pfp_v.png', 'w':'pfp_w.png',
'x':'pfp_x.png', 'y':'pfp_y.png', 'z':'pfp_z.png'}

# If there is a current user, redirect to the dashboard, otherwise redirect to the login page
@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    try:
        if current_user and user_keys[current_user.id]:
            try:
                path = user_pfp_path[current_user.id[0].lower()]
            except KeyError:
                path = 'pfp_question.png'
            path = url_for('static', filename=path)

            # Get all of the password data
            conn = sqlite3.connect("data.db")
            cur = conn.cursor()
            cur.execute("SELECT id, owner, name, username, password, url FROM passwords WHERE owner = ?", (current_user.id,))
            data = cur.fetchall()
            conn.close()

            data_list = []

            # Create the fernet object for decrypting the passwords, load the key from the user_keys dict as a byte string
            fernet = Fernet(user_keys[current_user.id])
            for i in data:
                i = list(i)

                # Decrypt everything
                name = fernet.decrypt(i[2].encode()).decode('utf-8') if i[2] != '' else ''
                username = fernet.decrypt(i[3].encode()).decode('utf-8') if i[3] != '' else ''
                password = fernet.decrypt(i[4].encode()).decode('utf-8') if i[4] != '' else ''
                url = fernet.decrypt(i[5].encode()).decode('utf-8') if i[5] != '' else ''

                try:
                    img_path = user_pfp_path[name[0].lower()]
                except KeyError:
                    img_path = 'pfp_question.png'
                img_path = url_for('static', filename=img_path)

                data_list.append({'owner':current_user.id, 'img':img_path, 'name':name, 'username':username, 'password':password, 'url':url, 'id':i[0]})

            data = sorted(data_list, key=lambda k: k['name'].lower())

            return render_template('dashboard.html', path=path, data=data)

    except:
        return redirect(url_for('login'))


# Create the blog route
@app.route('/blog', methods=['GET'])
def blog():
    return render_template('blog/blog.html')


# Create the blog post route
@app.route('/blog/<post>', methods=['GET'])
def blog_post(post):
    return render_template('blog/' + post + '.html')


# Create the documentation route
@app.route('/documentation', methods=['GET'])
def documentation():
    return render_template('documentation.html')


@app.route('/tools', methods=['GET'])
@login_required
def tools(breached=False):
    try:
        if current_user and user_keys[current_user.id]:
            try:
                path = user_pfp_path[current_user.id[0].lower()]
            except KeyError:
                path = 'pfp_question.png'
            path = url_for('static', filename=path)

            return render_template('tools.html', path=path, breached=breached)

        else:
            return render_template('login.html')

    except:
        return redirect(url_for('login'))


@app.route('/account-settings', methods=['GET'])
@login_required
def account_settings():
    try:
        if current_user and user_keys[current_user.id]:
            try:
                path = user_pfp_path[current_user.id[0].lower()]
            except KeyError:
                path = 'pfp_question.png'
            path = url_for('static', filename=path)

            return render_template('settings.html', email=current_user.id, path=path)

        else:
            return render_template('login.html')

    except:
        return redirect(url_for('login'))


# Create the route for deleting an account
@app.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    try:
        if current_user and user_keys[current_user.id]:
            conn = sqlite3.connect("data.db")
            cur = conn.cursor()
            cur.execute("SELECT id FROM passwords WHERE owner = ?", (current_user.id,))
            data = cur.fetchall()

            for i in data:
                cur.execute("DELETE FROM passwords WHERE id = ?", (i[0],))

            # Delete the user from the database
            cur.execute("DELETE FROM users WHERE email = ?", (current_user.id,))

            conn.commit()
            conn.close()

            # Delete the user from the user_keys dict
            del user_keys[current_user.id]

            # Delete the user from the session
            logout_user()

            return redirect(url_for('index'))
        else:
            return render_template('login.html')

    except:
        return redirect(url_for('login'))

# Add items to the database (from the 'Add Item' button on the dashboard)
@app.route('/add-item', methods=['POST'])
@login_required
def add_item():
    try:
        if current_user and user_keys[current_user.id]:
            # Get the data from the form
            name_form = request.form['name-save']
            username_form = request.form['username-save']
            password_form = request.form['password-save']
            url_form = request.form['url-save']

            # Encrypt it if there is data, otherwise leave it as an empty string
            fernet = Fernet(user_keys[current_user.id])
            name = fernet.encrypt(name_form.encode()).decode()
            username = fernet.encrypt(username_form.encode()).decode() if username_form != '' else ''

            if password_form != '':
                password = fernet.encrypt(password_form.encode()).decode()
                hash = hashlib.sha512(request.form['password-save'].encode()).hexdigest()
                hash = fernet.encrypt(hash.encode()).decode()
            else:
                password = ''
                hash = ''

            url = fernet.encrypt(url_form.encode()).decode() if url_form != '' else ''

            # Add the data to the database
            try:
                conn = sqlite3.connect("data.db")
                cur = conn.cursor()

                cur.execute("INSERT INTO passwords (owner, name, username, password, hash, url) VALUES (?, ?, ?, ?, ?, ?)", (current_user.id, name, username, password, hash, url))
                conn.commit()
                conn.close()
            except:
                pass

            return redirect(url_for('dashboard'))

    except:
        return redirect(url_for('login'))


# Add the delete-item route as a DELETE request with the URL parameters passed from the dashboard delete button
@app.route('/delete-item', methods=['DELETE'])
@login_required
def delete_item():
    try:
        if current_user and user_keys[current_user.id]:
            # Get the data from the form
            id = request.args.get('id')
            user = request.args.get('user')

            if current_user.id == user:
                conn = sqlite3.connect("data.db")
                cur = conn.cursor()

                cur.execute("DELETE FROM passwords WHERE id = ?", (id,))
                conn.commit()
                conn.close()

        return render_template('dashboard.html')

    except:
        return redirect(url_for('login'))


# Update an item already in the database
@app.route('/update-item', methods=['POST'])
@login_required
def update_item():
    try:
        if current_user and user_keys[current_user.id]:
            # Get the data from the form
            id = request.form['id']
            name = request.form['name-update']
            username = request.form['username-update']
            password = request.form['password-update']
            url = request.form['url-update']

            # Encrypt the data
            fernet = Fernet(user_keys[current_user.id])

            name = fernet.encrypt(name.encode()).decode()
            username = fernet.encrypt(username.encode()).decode() if username != '' else ''

            if password != '':
                password = fernet.encrypt(password.encode()).decode()
                hash = hashlib.sha512(request.form['password-update'].encode()).hexdigest()
                hash = fernet.encrypt(hash.encode()).decode()
            else:
                password = ''
                hash = ''

            url = fernet.encrypt(url.encode()).decode() if url != '' else ''

            # Update the data in the database
            conn = sqlite3.connect("data.db")
            cur = conn.cursor()

            try:
                cur.execute("UPDATE passwords SET name = ?, username = ?, password = ?, hash = ?, url = ? WHERE id = ? AND owner = ?", (name, username, password, hash, url, id, current_user.id))
                conn.commit()
                conn.close()
            except:
                pass

            return redirect(url_for('dashboard'))

    except:
        return redirect(url_for('login'))


# Update the users email address
@app.route('/update-email', methods=['POST'])
@login_required
def update_email():
    try:
        if current_user and user_keys[current_user.id]:
            # Get the data from the form
            email = request.form['new-email-update']

            # Update the data in the database
            conn = sqlite3.connect("data.db")
            cur = conn.cursor()

            try:
                cur.execute("UPDATE users SET email = ? WHERE email = ?", (email, current_user.id))
                conn.commit()
            except:
                path = user_pfp_path[current_user.id[0].lower()]
                path = url_for('static', filename=path)
                conn.close()
                return render_template('settings.html', path=path, email=current_user.id, email_error='Email already taken, please try again with a different email address.')

            all_passwords = cur.execute("SELECT * FROM passwords WHERE owner = ?", (current_user.id,))
            all_passwords = cur.fetchall()
            for password in all_passwords:
                cur.execute("UPDATE passwords SET owner = ? WHERE id = ?", (email, password[0]))
            conn.commit()
            conn.close()

            return redirect(url_for('account_settings'))

    except:
        return redirect(url_for('login'))


# Update the users password
@app.route('/update-password', methods=['POST'])
@login_required
def update_password():
    try:
        if current_user and user_keys[current_user.id]:
            # Get the data from the form
            cur_pass = request.form['cur-password-update']
            new_pass = request.form['new-password-update']

            if cur_pass == new_pass:
                try:
                    path = user_pfp_path[current_user.id[0].lower()]
                except KeyError:
                    path = 'pfp_question.png'
                path = url_for('static', filename=path)
                return render_template('settings.html', path=path, email=current_user.id, pass_error='New password cannot be the same as your current password, please try again.')

            # Update the data in the database
            conn = sqlite3.connect("data.db")
            cur = conn.cursor()

            # Get the users current password from the DB
            cur.execute("SELECT password FROM users WHERE email = ?", (current_user.id,))
            data = cur.fetchone()
            current_password = data[0]

            # Make sure the cur_pass and current_password match using the bcrpyt.checkpw function
            if bcrypt.checkpw(cur_pass.encode('utf-8'), current_password.encode('utf-8')):
                try:
                    password = hash_new_pass(new_pass)
                    cur.execute("UPDATE users SET password = ? WHERE email = ?", (password, current_user.id))
                    conn.commit()
                except:
                    try:
                        path = user_pfp_path[current_user.id[0].lower()]
                    except KeyError:
                        path = 'pfp_question.png'
                    path = url_for('static', filename=path)
                    return render_template('settings.html', path=path, email=current_user.id, pass_error='An error occured, please try again later.')
            else:
                try:
                    path = user_pfp_path[current_user.id[0].lower()]
                except KeyError:
                    path = 'pfp_question.png'
                path = url_for('static', filename=path)
                return render_template('settings.html', path=path, email=current_user.id, pass_error='The password you entered was not your current password. Please try again.')

            # Take their old password and decrypt all of their passwords, then re-encrypt them with the new password
            fernet = Fernet(user_keys[current_user.id])

            hashed_pass = hashlib.sha512(new_pass.encode()).hexdigest()
            hashed_pass = bytes(hashed_pass[:32], 'utf-8')
            hashed_pass = base64.b64encode(hashed_pass)
            fernet_2 = Fernet(hashed_pass)

            all_passwords = cur.execute("SELECT * FROM passwords WHERE owner = ?", (current_user.id,))
            all_passwords = cur.fetchall()
            for password_entry in all_passwords:
                name = fernet.decrypt(password_entry[2].encode()).decode() if password_entry[2] != '' else ''
                username = fernet.decrypt(password_entry[3].encode()).decode() if password_entry[3] != '' else ''
                password = fernet.decrypt(password_entry[4].encode()).decode() if password_entry[4] != '' else ''
                hash = fernet.decrypt(password_entry[5].encode()).decode() if password_entry[5] != '' else ''
                url = fernet.decrypt(password_entry[6].encode()).decode() if password_entry[6] != '' else ''

                name = fernet_2.encrypt(name.encode()).decode() if name != '' else ''
                username = fernet_2.encrypt(username.encode()).decode() if username != '' else ''
                password = fernet_2.encrypt(password.encode()).decode() if password != '' else ''
                hash = fernet_2.encrypt(hash.encode()).decode() if hash != '' else ''
                url = fernet_2.encrypt(url.encode()).decode() if url != '' else ''

                cur.execute("UPDATE passwords SET name = ?, username = ?, password = ?, hash = ?, url = ? WHERE id = ? AND owner = ?", (name, username, password, hash, url, password_entry[0], current_user.id))

            conn.commit()
            conn.close()

            user_keys[current_user.id] = hashed_pass

            try:
                path = user_pfp_path[current_user.id[0].lower()]
            except KeyError:
                path = 'pfp_question.png'
            path = url_for('static', filename=path)

            return render_template('settings.html', path=path, email=current_user.id, pass_success='Password updated successfully!')

    except:
        return redirect(url_for('login'))


# Create the password breach check route
@app.route('/check-passwords', methods=['POST'])
@login_required
def check_passwords():
    try:
        if current_user and user_keys[current_user.id]:
            # Get all of the users passwords from the database
            conn = sqlite3.connect("data.db")
            cur = conn.cursor()
            cur.execute("SELECT hash FROM passwords WHERE owner = ? AND hash != ''", (current_user.id,))
            data = cur.fetchall()

            breach_conn = sqlite3.connect('breached_passwords.db')
            breach_cur = breach_conn.cursor()

            # Create a list of all of the users passwords
            breached = []
            fernet = Fernet(user_keys[current_user.id])
            for password in data:
                decrypted_password = fernet.decrypt(str(password).encode()).decode()

                # See if the password is in the breached_passwords database
                breach_cur.execute("SELECT * FROM breached_passwords WHERE password = ?", (decrypted_password,))
                data = breach_cur.fetchone()

                # If the password is in the breached_passwords database, add it to the list
                if data:
                    cur.execute("SELECT name FROM passwords WHERE hash = ?", (password[0],))
                    name = cur.fetchone()
                    name = fernet.decrypt(str(name).encode()).decode()
                    breached.append(f'"{name}"')

            conn.close()
            breach_conn.close()

            # Load the tools route and pass the breached passwords list to it
            try:
                path = user_pfp_path[current_user.id[0].lower()]
            except KeyError:
                path = 'pfp_question.png'
            path = url_for('static', filename=path)

            if breached:
                return render_template('tools.html', path=path, breached=breached)
            else:
                return render_template('tools.html', path=path, secure=True)

    except:
        return redirect(url_for('login'))


# Logout the user and redirect to the index page
@app.route('/logout', methods=['GET'])
def logout():
    if current_user:
        logout_user()

    return redirect(url_for('index'))


# If there is a 404 error, then render the 404.html page, for 505 errors, render the index page
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html')

@app.errorhandler(401)
def unauthorized(e):
    return redirect(url_for('login'))

@app.errorhandler(405)
def method_not_allowed(e):
    return redirect(url_for('index'))

@app.errorhandler(500)
def error_500(e):
    return redirect(url_for('index'))


if __name__ == '__main__':
    # Run on localhost at port 5000
    app.run(host='localhost', port=5000)