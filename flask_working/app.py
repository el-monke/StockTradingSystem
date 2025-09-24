from flask import Flask, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
bootstrap = Bootstrap5(app)

# ------------------------------------------------------------------------------------------------------
# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost/sts_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key'

# Initialize database
db = SQLAlchemy(app)

# Define User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(20), unique=False, nullable=False)
    lastname = db.Column(db.String(20), unique=False, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(15), unique=False, nullable=False)
    confpassword = db.Column(db.String(15), unique=False, nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"

# Define Admin model
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(15), unique=False, nullable=False)
    confpassword = db.Column(db.String(15), unique=False, nullable=False)
    createdAt = db.Column(db.String(15))
    updatedAt = db.Column(db.String(15))

    def __repr__(self):
        return f"<User {self.username}>"

# Define FinancialTransaction Model
class FinancialTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float)
    transType = db.Column(db.String(4))
    createdAt = db.Column(db.String(15))

# Define OrderHistory Model
class OrderHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stockID = db.Column(db.Integer)
    adminID = db.Column(db.Integer)
    transType = db.Column(db.String(4))
    qty = db.Column(db.Integer)
    price = db.Column(db.Float)
    totalValue = db.Column(db.Float)
    status = db.Column(db.String(6))
    companyName = db.Column(db.String(15))
    ticker = db.Column(db.String(5))
    createdAt = db.Column(db.String(15))
    updatedAt = db.Column(db.String(15))

# Define Portfolio Model
class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customerID = db.Column(db.Integer)
    orderID = db.Column(db.Integer)
    stockName = db.Column(db.String(15))
    ticker = db.Column(db.String(5))
    qty = db.Column(db.Float)
    currentMktPrice = db.Column(db.Float)
    createdAt = db.Column(db.String(15))
    updatedAt = db.Column(db.String(15))


# Define StockInventory Model
class StockInventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    adminID = db.Column(db.Integer)
    stockName = db.Column(db.String(15))
    ticker = db.Column(db.String(15))
    qty = db.Column(db.Float)
    initStockPrice = db.Column(db.Float)
    currentMktPrice = db.Column(db.Float)
    createdAt = db.Column(db.String(15))
    updatedAt = db.Column(db.String(15))

# Define Company Model
class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    companyName = db.Column(db.String(15))
    description = db.Column(db.String(100))
    stockTotalQuality = db.Column(db.Float)
    ticker = db.Column(db.String(15))
    currentMktPrice = db.Column(db.Float)
    createdAt = db.Column(db.String(15))
    updatedAt = db.Column(db.String(15))

# Define WorkingDay Model
class WorkingDay(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    adminID = db.Column(db.Integer)
    weekDay = db.Column(db.String(3))
    openTime = db.Column(db.String(15))
    closeTime = db.Column(db.String(15))
    holida = db.Column(db.String(15))
    createdAt = db.Column(db.String(15))
    updatedAt = db.Column(db.String(15))


# Create tables
with app.app_context():
    db.create_all()

# ------------------------------------------------------------------------------------------------------
# CRUD FUNCTIONS

# READ
@app.route('/read_user/<int:user_id>')
def read_user(user_id):
    user = User.query.get_or_404(user_id)
    return f"User Details: ID: {user.id}, Username: {user.username}, Email: {user.email}"

# UPDATE
@app.route('/update_user/<int:user_id>/<string:username>/<string:email>')
def update_user(user_id, username, email):
    user = User.query.get_or_404(user_id)
    if not username or not email:
        flash('Both username and email are required!', 'error')
        return redirect(url_for('index'))

    user.username = username
    user.email = email

    try:
        db.session.commit()
        flash(f'User {username} updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating user: {str(e)}', 'error')
    return redirect(url_for('index'))

# DELETE
@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    try:
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.username} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')
    return redirect(url_for('index'))

# ------------------------------------------------------------------------------------------------------
# ROUTES
@app.route("/")
def index():
    users = User.query.all()
    return render_template("index.html")

@app.route("/signin")
def signin():
    return render_template("signin.html")

@app.route("/createaccount")
def createaccount():
    return render_template("createaccount.html")

if __name__ == "__main__":
    app.run(debug=True)