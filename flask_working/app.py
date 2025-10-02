from flask import Flask, render_template, request, url_for, flash, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
import datetime
import uuid

app = Flask(__name__)
# DATABASE -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Sandwich13!!!@localhost/sts_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key'

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

bcrypt = Bcrypt(app)

# Define User model
class User(UserMixin, db.Model):
    userId = db.Column(db.Integer, primary_key=True)
    fullName = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    role = db.Column(db.String(5), default="user", nullable=False) # User role, can be changed later
    customerAccountNumber = db.Column(db.String(32), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    availableFunds = db.Column(db.Float, default=0.0)
    createdAt = db.Column(db.DateTime, nullable=False)
    updatedAt = db.Column(db.DateTime, nullable=False)

    def get_id(self):
        return str(self.userId)

# Define Admin model
class Admin(UserMixin, db.Model):
    adminId = db.Column(db.Integer, primary_key=True)
    fullName = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    role = db.Column(db.String(5), default="admin", nullable=False) # Admin role
    password = db.Column(db.String(255), nullable=False)
    createdAt = db.Column(db.DateTime, nullable=False)
    updatedAt = db.Column(db.DateTime, nullable=False)

    def get_id(self):
        return str(self.adminId)

# Define FinancialTransaction model
class FinancialTransaction(db.Model):
    financialTransId = db.Column(db.Integer, primary_key=True)
    # Foreign Keys
    customerAccountNumber = db.Column(db.String(32), ForeignKey("user.customerAccountNumber"))
    companyId = db.Column(db.Integer, ForeignKey("company.companyId"))
    orderId = db.Column(db.Integer, ForeignKey("order_history.orderId"))
    # Attributes
    amount = db.Column(db.Float)
    type = db.Column(db.String(8)) # BUY/SELL/DEPOSIT/WITHDRAW
    createdAt = db.Column(db.DateTime, nullable=False)

    def get_id(self):
        return str(self.financialTransId)

# Define OrderHistory model
class OrderHistory(db.Model):
    orderId = db.Column(db.Integer, primary_key=True)
    # Foreign Keys
    stockId = db.Column(db.Integer, ForeignKey("stock_inventory.stockId"))
    adminId = db.Column(db.Integer, ForeignKey("admin.adminId"))
    userId = db.Column(db.Integer, ForeignKey("user.userId"))
    # Attributes
    type = db.Column(db.String(8)) # BUY/SELL
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float)
    totalValue = db.Column(db.Float)
    status = db.Column(db.String(6)) # OPEN/CANCEL/CLOSE
    companyName = db.Column(db.String(120))
    ticker = db.Column(db.String(5))
    createdAt = db.Column(db.DateTime, nullable=False)
    updatedAt = db.Column(db.DateTime, nullable=False)

    def get_id(self):
        return str(self.orderId)

# Define Portfolio model
class Portfolio(db.Model):
    portfolioId = db.Column(db.Integer, primary_key=True)
    # Foreign Keys
    customerId = db.Column(db.Integer, ForeignKey("user.userId"))
    orderId = db.Column(db.Integer, ForeignKey("order_history.orderId"))
    # Attributes
    stockName = db.Column(db.String(120))
    ticker = db.Column(db.String(5))
    quantity = db.Column(db.Integer)
    mktPrice = db.Column(db.Float)
    createdAt = db.Column(db.DateTime, nullable=False)
    updatedAt = db.Column(db.DateTime, nullable=False)

    def get_id(self):
        return str(self.portfolioId)

# Define StockInventory model
class StockInventory(db.Model):
    stockId = db.Column(db.Integer, primary_key=True)
    # Foreign Keys
    companyId = db.Column(db.Integer, ForeignKey("company.companyId")) 
    adminId = db.Column(db.Integer, ForeignKey("admin.adminId"))
    # Attributes
    name = db.Column(db.String(120))
    ticker = db.Column(db.String(5))
    quantity = db.Column(db.Integer)
    initStockPrice = db.Column(db.Float)
    currentMktPrice = db.Column(db.Float)
    createdAt = db.Column(db.DateTime, nullable=False)
    updatedAt = db.Column(db.DateTime, nullable=False)

    def get_id(self):
        return str(self.stockId)

# Define Company model
class Company(db.Model):
    companyId = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    description = db.Column(db.String(255))
    stockTotalQty = db.Column(db.Integer)
    ticker = db.Column(db.String(5))
    currentMktPrice = db.Column(db.Float)
    createdAt = db.Column(db.DateTime, nullable=False)
    updatedAt = db.Column(db.DateTime, nullable=False)

    def get_id(self):
        return str(self.companyId)

# Define Exception model
class Exception(db.Model):
    exceptionId = db.Column(db.Integer, primary_key=True)
    # Foreign Key
    adminId = db.Column(db.Integer, ForeignKey("admin.adminId"))
    # Attributes
    reason = db.Column(db.String(255))
    holidayDate = db.Column(db.String(25))
    createdAt = db.Column(db.DateTime, nullable=False)
    updatedAt = db.Column(db.DateTime, nullable=False)

    def get_id(self):
        return str(self.exceptionId)

# Define WorkingDay model
class WorkingDay(db.Model):
    workingDayId = db.Column(db.Integer, primary_key=True)
    # Foreign Key
    adminId = db.Column(db.Integer, ForeignKey("admin.adminId"))
    # Attributes
    dayOfWeek = db.Column(db.String(3))
    startTime = db.Column(db.String(25))
    endTime = db.Column(db.String(25))
    createdAt = db.Column(db.String(25))
    updatedAt = db.Column(db.String(25))

    def get_id(self):
        return str(self.workingDayId)

# Initialize database
with app.app_context():
    db.create_all()
# END DATABASE -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# User loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Home Route
@app.route('/')
@login_required  # Restricts access to authenticated users only
def home():
    return render_template("home.html")

# USER AUTHENTICATION----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# Create User Account
@app.route('/createaccount', methods=["GET", "POST"])
def createaccount():
    if request.method == "POST":
        hashedPassword = bcrypt.generate_password_hash(request.form.get("password")).decode('utf-8')
        acctNumber = uuid.uuid4().hex[:12].upper()
        user = User(
            fullName=request.form.get("fullName"),
            email=request.form.get("email"),
            customerAccountNumber=acctNumber,
            password=hashedPassword,  # Hashed password
            role="user",  # Default role is "user"
            createdAt = datetime.datetime.now(),
            updatedAt = datetime.datetime.now()
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("signIn"))
    return render_template("create_account.html")

# Create Admin Account
@app.route('/createaccount/admin', methods=["GET", "POST"])
def createaccount_admin():
    if request.method == "POST":
        # Verify the admin registration key
        admin_key = request.form.get("admin_key")
        if admin_key != "admin":  # Change this to a secure key
            return redirect(url_for("signIn"))
        
        hashedPassword = bcrypt.generate_password_hash(request.form.get("password")).decode('utf-8')
        admin = Admin(
            fullName=request.form.get("fullName"),
            email=request.form.get("email"),
            password=hashedPassword,  # Hashed Password
            role="admin",  # Admin role
            createdAt = datetime.datetime.now(),
            updatedAt = datetime.datetime.now()
        )
        db.session.add(admin)
        db.session.commit()
        return redirect(url_for("signIn"))
    return render_template("create_account_admin.html")

# SignIn Route
@app.route('/signIn', methods=["GET", "POST"])
def signIn():
    if request.method == "POST":
        if User.query.filter_by(email=request.form.get("email")).first() != None:
            user = User.query.filter_by(email=request.form.get("email")).first()
            if user and bcrypt.check_password_hash(user.password, request.form.get("password")):
                login_user(user)
                return redirect(url_for("home"))
        else:
            admin = Admin.query.filter_by(email=request.form.get("email")).first()
            if admin and bcrypt.check_password_hash(admin.password, request.form.get("password")):
                login_user(admin)
                return redirect(url_for("home"))
    return render_template("sign_in.html")

# LogOut Route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for("signIn"))

#----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# Buy Stock Route; Need Logic
@app.route('/home/buystock', methods=['GET'])
def buyStock():
    return render_template('buy_stock.html')

# Sell Stock Route; Need Logic
@app.route('/home/sellstock', methods=['GET'])
def sellStock():
    return render_template('sell_stock.html')

@app.route('/home/deposit', methods=["GET", "POST"])
def depositFunds():
    if request.method == "POST":
        amt = request.form.get("amount")
        deposit = FinancialTransaction(
            customerAccountNumber = current_user.customerAccountNumber,
            amount=amt,
            type="deposit",
            createdAt = datetime.datetime.now()
        )
        # Update Available funds
        current_user.availableFunds = current_user.availableFunds + float(amt)
        current_user.updatedAt = datetime.datetime.now()
        
        db.session.add(deposit)
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("deposit.html")

# Withdraw Funds Route
@app.route('/home/withdraw', methods=["GET", "POST"])
def withdrawFunds():
    if request.method == "POST":
        amt = request.form.get("amount")
        withdraw = FinancialTransaction(
            customerAccountNumber = current_user.customerAccountNumber,
            amount=amt,
            type="withdraw",
            createdAt=datetime.datetime.now()
        )
        # Withdraw from Available Funds
        current_user.availableFunds = current_user.availableFunds - float(amt)
        current_user.updatedAt = datetime.datetime.now()

        db.session.add(withdraw)
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("withdraw.html")

if __name__ == "__main__":
    app.run(debug=True)