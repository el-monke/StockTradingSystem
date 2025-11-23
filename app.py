from flask import Flask, render_template, request, url_for, flash, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, func
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DecimalField, SubmitField
from wtforms.validators import DataRequired, NumberRange
from functools import wraps
import datetime
from datetime import time as dtime, date as ddate
import uuid
import builtins
from decimal import Decimal
from apscheduler.schedulers.background import BackgroundScheduler
import random
from sqlalchemy.orm import joinedload
import builtins
from flask_login import current_user




app = Flask(__name__)

# DATABASE FUNCTIONS------------------------------------------------------------------------------------

# DB configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost/sts_db'
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
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    availableFunds = db.Column(db.Float, default=0.0)
    createdAt = db.Column(db.DateTime, nullable=False)
    updatedAt = db.Column(db.DateTime, nullable=False)

    def get_id(self):
        return f"user:{self.userId}"

# Define Admin model
class Admin(UserMixin, db.Model):
    adminId = db.Column(db.Integer, primary_key=True)
    fullName = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    createdAt = db.Column(db.DateTime, nullable=False)
    updatedAt = db.Column(db.DateTime, nullable=False)

    def get_id(self):
        return f"admin:{self.adminId}"
    
# Define StockInventory model
class StockInventory(db.Model):
    stockId = db.Column(db.Integer, primary_key=True)
    companyId = db.Column(db.Integer, ForeignKey("company.companyId")) 
    adminId = db.Column(db.Integer, ForeignKey("admin.adminId"))
    name = db.Column(db.String(120))
    ticker = db.Column(db.String(5))
    quantity = db.Column(db.Integer)
    initStockPrice = db.Column(db.Float)
    currentMktPrice = db.Column(db.Float)
    createdAt = db.Column(db.DateTime, nullable=False)
    updatedAt = db.Column(db.DateTime, nullable=False)
    volume = db.Column(db.Integer, default=0)                # today's volume
    dailyOpenPrice = db.Column(db.Float)                     # open for the day
    dailyHighPrice = db.Column(db.Float)                     # intraday high
    dailyLowPrice = db.Column(db.Float)                      # intraday low
    dailyDate = db.Column(db.Date)                           # which day these stats belong to
    company = db.relationship("Company", backref="stock")

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

# Define Portfolio model
class Portfolio(db.Model):
    portfolioId = db.Column(db.Integer, primary_key=True)
    userId = db.Column(db.Integer, ForeignKey("user.userId"))
    orderId = db.Column(db.Integer, ForeignKey("order_history.orderId"))
    stockName = db.Column(db.String(120))
    ticker = db.Column(db.String(5)) # BUY/SELL
    quantity = db.Column(db.Integer)
    mktPrice = db.Column(db.Float)
    createdAt = db.Column(db.DateTime, nullable=False)
    updatedAt = db.Column(db.DateTime, nullable=False)

    def get_id(self):
        return str(self.portfolioId)
    
# Define OrderHistory model
class OrderHistory(db.Model):
    orderId = db.Column(db.Integer, primary_key=True)
    stockId = db.Column(db.Integer, ForeignKey("stock_inventory.stockId"))
    adminId = db.Column(db.Integer, ForeignKey("admin.adminId"))
    userId = db.Column(db.Integer, ForeignKey("user.userId"))
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
    
# Define FinancialTransaction model
class FinancialTransaction(db.Model):
    financialTransId = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), ForeignKey("user.username"))
    companyId = db.Column(db.Integer, ForeignKey("company.companyId"))
    orderId = db.Column(db.Integer, ForeignKey("order_history.orderId"))
    amount = db.Column(db.Float)
    type = db.Column(db.String(8)) # BUY/SELL/DEPOSIT/WITHDRAW
    createdAt = db.Column(db.DateTime, nullable=False)

    def get_id(self):
        return str(self.financialTransId)
    
# Define Exception model
class Exception(db.Model):
    exceptionId = db.Column(db.Integer, primary_key=True)
    # Foreign Key
    adminId = db.Column(db.Integer, ForeignKey("admin.adminId"))
    # Attributes
    reason = db.Column(db.String(255))
    holidayDate = db.Column(db.DateTime)
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
    startTime = db.Column(db.Time())
    endTime = db.Column(db.Time())
    createdAt = db.Column(db.DateTime, nullable=False)
    updatedAt = db.Column(db.DateTime, nullable=False)

    def get_id(self):
        return str(self.workingDayId)

# Initialize database
with app.app_context():
    db.create_all()

# END DATABASE FUNCTIONS------------------------------------------------------------------------------------

# USER AUTHENTICATION---------------------------------------------------------------------------------------
@login_manager.user_loader
def load_user(user_id):
    type, unprefix = user_id.split(":", 1)
    trueId = int(unprefix)

    if type == "admin":
        return Admin.query.get(trueId)
    if type == "user":
        return User.query.get(trueId)
    
# Admin Required Route
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please login to access this webpage.", "danger")
            return redirect(url_for("signIn"))
        elif not isinstance(current_user, Admin):
            flash("Please login with an Admin account to access this webpage.", "danger")
            return redirect(url_for("home"))
        else:
            return f(*args, **kwargs)
    return decorated_function

# LogOut Route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for("signIn"))
    
# Create User Account
@app.route("/createaccount", methods=["GET", "POST"])
def createaccount():
    if request.method == "POST":

        fullName = request.form.get("fullName")
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confPassword = request.form.get("confPassword")

        if (fullName == "") or (username == "") or (email == "") or (password == "") or (confPassword == ""):
            flash("Empty fields. Please try again.", "danger")
            return render_template("create_account.html")

        if password != confPassword:
            flash("Passwords do not match. Please try again.", "danger")
            return render_template("create_account.html")
        
        try:
            hashedPassword = bcrypt.generate_password_hash(password).decode('utf-8')
            user = User(
                fullName=fullName,
                username=username,
                email=email,
                password=hashedPassword,
                createdAt=datetime.datetime.now(),
                updatedAt=datetime.datetime.now()
            )
            db.session.add(user)
            db.session.commit()
            flash("User account created successfully.", "success")
            return redirect(url_for("signIn"))
        
        except:
            db.session.rollback()
            flash("Error. Please try again.", "danger")
            return render_template("create_account.html")
        
    return render_template("create_account.html")

# Create Admin Account
@app.route("/createaccount/admin", methods=["GET", "POST"])
def createaccount_admin():
    if request.method == "POST":

        fullName = request.form.get("fullName")
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confPassword = request.form.get("confPassword")      

        if (fullName == "") or (username == "") or (email == "") or (password == "") or (confPassword == ""):
            flash("Empty fields. Please try again.", "danger")
            return render_template("create_account_admin.html")
        
        if password != confPassword:
            flash("Passwords do not match. Please try again.", "danger")
            return render_template("create_account_admin.html")
        
        try:
            hashedPassword = bcrypt.generate_password_hash(password).decode('utf-8')
            admin = Admin(
                fullName=fullName,
                username=username,
                email=email,
                password=hashedPassword,
                createdAt = datetime.datetime.now(),
                updatedAt = datetime.datetime.now()
            )
            db.session.add(admin)
            db.session.commit()
            flash("Admin account created successfully.", "success")
            return redirect(url_for("signIn"))
        
        except:
            db.session.rollback()
            flash("Error. Please try again.", "danger")
            return render_template("create_account_admin.html")    
                
    return render_template("create_account_admin.html")

# SignIn Route
@app.route('/', methods=["GET", "POST"])
def signIn():
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if (username == "") or (password == ""):
            flash("Empty fields. Please try again.", "danger")
            return render_template("sign_in.html")

        user = User.query.filter_by(username=username).first()
        admin = Admin.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("home"))

        elif admin and bcrypt.check_password_hash(admin.password, password):
            login_user(admin)
            return redirect(url_for("homeAdmin"))
            
        else:
            flash("Invalid credentials. Please try again.", "danger")
            return render_template("sign_in.html")
        
    return render_template("sign_in.html")

@app.route('/home/admin/updateuser/<int:user_id>', methods=["GET", "POST"])
@admin_required
def updateUser(user_id):
    user = User.query.get_or_404(user_id)

    portfolio = (
        Portfolio.query.with_entities(
            Portfolio.ticker,
            Portfolio.mktPrice,
            Portfolio.quantity
        )
        .filter_by(userId=user.userId)
        .order_by(Portfolio.ticker)
        .all()
    )

    if request.method == "POST":
        fullName = request.form.get("fullName")
        username = request.form.get("username")
        email = request.form.get("email")
        availableFunds = request.form.get("availableFunds")

        try:
            if fullName:
                user.fullName = fullName
            elif username:
                user.username = username
            elif email:
                user.email = email
            elif availableFunds:
                user.availableFunds = availableFunds
            else:
                x = 1 / 0    
            user.updatedAt = datetime.datetime.now()
        except:
            flash(f"No change inputted. Please enter values.", "danger")
            return redirect(url_for('updateUser', user_id=user.userId))

        try:
            db.session.commit()
            flash(f"User {user.username} updated successfully!", "success")
            return redirect(url_for('homeAdmin'))
        except:
            db.session.rollback()
            flash(f"Error updating user. Please try again.", "danger")
            return redirect(url_for('homeAdmin'))


    return render_template("update_user.html", user=user, portfolio=portfolio)

@app.route('/home/admin/deleteuser/<int:user_id>', methods=["POST"])
@admin_required
def deleteUser(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == "POST":

        try:
            Portfolio.query.filter_by(userId=user.userId).delete()
            OrderHistory.query.filter_by(userId=user.userId).delete()
            FinancialTransaction.query.filter_by(username=user.username).delete()

            db.session.delete(user)
            db.session.commit()
            flash(f"User {user.username} deleted successfully!", "success")
        except:
            db.session.rollback()
            flash(f"Error deleting user. Please try again.", "danger")
    return redirect(url_for('homeAdmin'))

# END USER AUTHENTICATION---------------------------------------------------------------------------

# ---------- MARKET STATUS HELPER -------------------------------------------------------------------
def get_market_status(target_date=None):
    now = datetime.datetime.now()

    if target_date is None:
        target_date = now.date()

    weekday_abbr = target_date.strftime("%a")[:3]

    wd = WorkingDay.query.filter_by(dayOfWeek=weekday_abbr).first()

    holiday = Exception.query.filter(
        func.date(Exception.holidayDate) == target_date
    ).first()

    market_open = False
    market_start = None
    market_end = None

    if wd and not holiday:
        market_start = wd.startTime
        market_end = wd.endTime

        if target_date == now.date():
            current = now.time()
            if market_start <= current <= market_end:
                market_open = True

    return market_open, market_start, market_end, holiday

@app.context_processor
def injectMktStatus():
    market_open = get_market_status()[0]
    market_start = get_market_status()[1]
    market_end = get_market_status()[2]
    holiday = get_market_status()[3]

    return dict(market_open=market_open, market_start=market_start, market_end=market_end, holiday=holiday)
# -------------------------------------------------------------------

# HOME ROUTES---------------------------------------------------------------------------------------

# Home Route for User
@app.route("/home")
@login_required
def home():
    try:
        stock = (
            StockInventory.query
                .options(joinedload(StockInventory.company))
                .order_by(StockInventory.ticker)
                .all()
        )

        portfolio = (
            Portfolio.query.with_entities(
                Portfolio.ticker,
                Portfolio.mktPrice,
                Portfolio.quantity
            )
            .filter_by(userId=current_user.userId)
            .order_by(Portfolio.ticker)
            .all()
        )

        portfolioValue = calculateValue()
        contributions = calculateContribution()
        accountValue = current_user.availableFunds + portfolioValue
        totalReturn = (current_user.availableFunds + portfolioValue) - contributions

        labels = ["Liquid", "Invested", "Return"]
        data = [current_user.availableFunds, portfolioValue, totalReturn]

    except builtins.Exception as e: 
        flash(f"Error retrieving values from DB: {e}", "danger")

        stock = []
        portfolio = []
        portfolioValue = 0.0
        contributions = 0.0
        accountValue = float(getattr(current_user, "availableFunds", 0) or 0)
        totalReturn = 0.0
        labels = ["Liquid", "Invested", "Return"]
        data = [accountValue, 0.0, 0.0]

    return render_template(
        "home.html",
        stock=stock,
        portfolio=portfolio,
        contributions=contributions,
        accountValue=accountValue,
        totalReturn=totalReturn,
        pieLabels=labels,
        pieData=data,
    )
    
# Home Route for Admin
@app.route("/home/admin")
@admin_required
def homeAdmin():

    try:
        user = (
            User.query.order_by(User.fullName).all()
        )

        stock = (
            StockInventory.query.with_entities(
                StockInventory.ticker,
                StockInventory.quantity,
                StockInventory.initStockPrice,
                StockInventory.currentMktPrice,
            )
            .order_by(StockInventory.ticker)
            .all()
        )     

    except:
        flash("Error retrieving values from DB", "danger")
        return render_template("home.html")            

    return render_template("home_admin.html", user=user, stock=stock)

# END HOME ROUTES-------------------------------------------------------------------------------------

# USER ROUTES-----------------------------------------------------------------------------------------

# Deposit Funds Route
@app.route("/home/deposit", methods=["GET", "POST"])
@login_required
def depositFunds():
    if request.method == "POST":
        
        amount = request.form.get("amount")

        if amount == "":
            flash("Please enter a deposit amount.", "danger")
            return render_template("deposit.html")
        
        try:
            amount = float(amount)

            if (amount <= 0):
                flash("Deposit amount must be non-negative. Please try again.", "danger")
                return render_template("deposit.html")
        except:
            flash("Error converting deposit amount to float. Please try again.", "danger")
            return render_template("deposit.html")
        
        try:
            depositAction(amount)
            db.session.commit()
            flash("Deposit processed successfully.", "success")
            return redirect(url_for("home"))
        
        except:
            db.session.rollback()
            flash("Error. Please try again.", "danger")
            return render_template("deposit.html")

    transactions = (
        FinancialTransaction.query
        .filter_by(username=current_user.username)
        .order_by(FinancialTransaction.createdAt.desc())
        .limit(10)
        .all()
    )

    return render_template("deposit.html", transactions=transactions)

def depositAction(amount):
        
    deposit = FinancialTransaction(
        username = current_user.username,
        amount = amount,
        type = "DEPOSIT",
        createdAt = datetime.datetime.now()
    )

    current_user.availableFunds += amount
    current_user.updatedAt = datetime.datetime.now()
    db.session.add(deposit)
    db.session.flush()
    
# Withdraw Funds Route
@app.route("/home/withdraw", methods=["GET", "POST"])
@login_required
def withdrawFunds():
    if request.method == "POST":

        amount = request.form.get("amount")

        if amount == "":
            flash("Please enter a withdrawal amount.", "danger")
            return render_template("withdraw.html")
        
        try:
            amount = float(amount)

            if (amount <= 0):
                flash("Withdrawal amount must be positive. Please try again.", "danger")
                return render_template("withdraw.html")
            
            if (amount > current_user.availableFunds):
                flash("Cannot withdraw more than the user's Balance. Please try again.", "danger")
                return render_template("withdraw.html")
        except:
            flash("Error converting withdrawal amount to float. Please try again.", "danger")
            return render_template("withdraw.html")
        
        try:
            withdrawAction(amount)
            db.session.commit()
            flash("Withdrawal processed successfully.", "success")
            return redirect(url_for("home"))
        except:
            db.session.rollback()
            flash("Error. Please try again.", "danger")
            return render_template("withdraw.html")

    transactions = (
        FinancialTransaction.query
        .filter_by(username=current_user.username)
        .order_by(FinancialTransaction.createdAt.desc())
        .limit(10)
        .all()
    )

    return render_template("withdraw.html", transactions=transactions)

def withdrawAction(amount):

    withdraw = FinancialTransaction(
        username = current_user.username,
        amount = amount,
        type = "WITHDRAW",
        createdAt = datetime.datetime.now()
    )

    current_user.availableFunds -= amount
    current_user.updatedAt = datetime.datetime.now()
    db.session.add(withdraw)
    db.session.flush()

# Buy Stock Route
@app.route("/home/buystock", methods=["GET", "POST"])
@login_required
def buyStock():
    market_open, market_start, market_end, holiday = get_market_status()

    if request.method == "POST":

        # HARD BLOCK if market is closed, even if someone tries to POST manually
        if not market_open:
            flash("Market is currently closed. You cannot place buy orders.", "danger")
            return render_template(
                "buy_stock.html",
                market_open=market_open,
                market_start=market_start,
                market_end=market_end,
                holiday=holiday
            )

        ticker = request.form.get("ticker")
        quantity = request.form.get("quantity")

        if (ticker == "") or (quantity == ""):
            flash("Empty fields. Please enter a ticker and quantity.", "danger")
            return render_template(
                "buy_stock.html",
                market_open=market_open,
                market_start=market_start,
                market_end=market_end,
                holiday=holiday
            )

        try:
            ticker = ticker.strip().upper()
            quantity = int(quantity)

            if (quantity <= 0):
                flash("Quantity must be positive. Please try again.", "danger")
                return render_template(
                    "buy_stock.html",
                    market_open=market_open,
                    market_start=market_start,
                    market_end=market_end,
                    holiday=holiday
                )
        except:
            flash("Error converting quantity to int. Please try again.", "danger")
            return render_template(
                "buy_stock.html",
                market_open=market_open,
                market_start=market_start,
                market_end=market_end,
                holiday=holiday
            )

        try:
            stock = StockInventory.query.filter_by(ticker=ticker).first()

            if not stock:
                flash("Stock not found. Please enter a valid stock.", "danger")
                return render_template(
                    "buy_stock.html",
                    market_open=market_open,
                    market_start=market_start,
                    market_end=market_end,
                    holiday=holiday
                )

            transactionAmount = stock.currentMktPrice * quantity

            if transactionAmount > current_user.availableFunds:
                flash("Insufficient funds for this transaction. Please deposit funds.", "danger")
                return render_template(
                    "buy_stock.html",
                    market_open=market_open,
                    market_start=market_start,
                    market_end=market_end,
                    holiday=holiday
                )

            if quantity > stock.quantity:
                flash("Inputted quantity exceeds Market Cap. Please enter a different quantity.", "danger")
                return render_template(
                    "buy_stock.html",
                    market_open=market_open,
                    market_start=market_start,
                    market_end=market_end,
                    holiday=holiday
                )
        except:
            flash("Error. Please try again.", "danger")
            return render_template(
                "buy_stock.html",
                market_open=market_open,
                market_start=market_start,
                market_end=market_end,
                holiday=holiday
            )

        try:
            current_user.availableFunds -= transactionAmount
            current_user.updatedAt = datetime.datetime.now()

            order = orderAction("BUY", transactionAmount, quantity, stock)

            updatePortfolio(order)

            db.session.commit()

            flash("Buy order placed successfully.", "success")
            return redirect(url_for("home"))
        except:
            db.session.rollback()
            flash("Error placing buy order. Please try again.", "danger")
            return render_template(
                "buy_stock.html",
                market_open=market_open,
                market_start=market_start,
                market_end=market_end,
                holiday=holiday
            )

    stock = (
        StockInventory.query.with_entities(
        StockInventory.ticker,
        StockInventory.currentMktPrice,
        StockInventory.initStockPrice
        )
        .order_by(StockInventory.ticker)
        .all()
        )    

    # GET request
    return render_template(
        "buy_stock.html",
        market_open=market_open,
        market_start=market_start,
        market_end=market_end,
        holiday=holiday,
        stock=stock
    )

# Sell Stock Route
@app.route("/home/sellstock", methods=["GET", "POST"])
@login_required
def sellStock():
    # prevent admins from using user-only route
    if not isinstance(current_user, User):
        flash("Sell Stock is only available for user accounts.", "danger")
        return redirect(url_for("homeAdmin"))

    # Get today's market status
    market_open, market_start, market_end, holiday = get_market_status()

    # Portfolio is needed for both GET and POST
    portfolio = (
        Portfolio.query.with_entities(
            Portfolio.ticker,
            Portfolio.mktPrice,
            Portfolio.quantity
        )
        .filter_by(userId=current_user.userId)
        .order_by(Portfolio.ticker)
        .all()
    )

    if request.method == "POST":

        if not market_open:
            flash("Market is currently closed. You cannot place sell orders.", "danger")
            return render_template(
                "sell_stock.html",
                portfolio=portfolio,
                market_open=market_open,
                market_start=market_start,
                market_end=market_end,
                holiday=holiday
            )

        ticker = request.form.get("ticker")
        quantity = request.form.get("quantity")

        if (ticker == "") or (quantity == "") or (ticker is None) or (quantity is None):
            flash("Empty fields. Please enter a ticker and quantity.", "danger")
            return render_template(
                "sell_stock.html",
                portfolio=portfolio,
                market_open=market_open,
                market_start=market_start,
                market_end=market_end,
                holiday=holiday
            )
        
        try:
            ticker = ticker.strip().upper()
            quantity = int(quantity)

            if quantity <= 0:
                flash("Quantity must be positive. Please try again.", "danger")
                return render_template(
                    "sell_stock.html",
                    portfolio=portfolio,
                    market_open=market_open,
                    market_start=market_start,
                    market_end=market_end,
                    holiday=holiday
                )
        except:
            flash("Error converting quantity to int. Please try again.", "danger")
            return render_template(
                "sell_stock.html",
                portfolio=portfolio,
                market_open=market_open,
                market_start=market_start,
                market_end=market_end,
                holiday=holiday
            )
        
        try:
            stock = StockInventory.query.filter_by(ticker=ticker).first()

            if not stock:
                flash("Stock not found. Please enter a valid stock.", "danger")
                return render_template(
                    "sell_stock.html",
                    portfolio=portfolio,
                    market_open=market_open,
                    market_start=market_start,
                    market_end=market_end,
                    holiday=holiday
                )
            
            transactionAmount = stock.currentMktPrice * quantity

            position = (
                Portfolio.query.filter_by(userId=current_user.userId, ticker=ticker)
                .first()
            )

            if (position is None) or position.quantity == 0:
                flash("User does not own this stock. Please purchase stock to sell.", "danger")
                return render_template(
                    "sell_stock.html",
                    portfolio=portfolio,
                    market_open=market_open,
                    market_start=market_start,
                    market_end=market_end,
                    holiday=holiday
                )
            
            if quantity > position.quantity:
                flash("Cannot sell more than owned shares. Please enter a different quantity.", "danger")
                return render_template(
                    "sell_stock.html",
                    portfolio=portfolio,
                    market_open=market_open,
                    market_start=market_start,
                    market_end=market_end,
                    holiday=holiday
                )
        except:
            flash("Error. Please try again.", "danger")
            return render_template(
                "sell_stock.html",
                portfolio=portfolio,
                market_open=market_open,
                market_start=market_start,
                market_end=market_end,
                holiday=holiday
            )
        
        try:
            current_user.availableFunds += transactionAmount
            current_user.updatedAt = datetime.datetime.now()

            order = orderAction("SELL", transactionAmount, quantity, stock)
            updatePortfolio(order)

            db.session.commit()

            flash("Sell order placed successfully.", "success")
            return redirect(url_for("home"))
        except:
            db.session.rollback()
            flash("Error placing sell order. Please try again.", "danger")
            return render_template(
                "sell_stock.html",
                portfolio=portfolio,
                market_open=market_open,
                market_start=market_start,
                market_end=market_end,
                holiday=holiday
            )

    # GET request
    return render_template(
        "sell_stock.html",
        portfolio=portfolio,
        market_open=market_open,
        market_start=market_start,
        market_end=market_end,
        holiday=holiday
    )

def orderAction(process, amount, quantity, stock):

    if (process == "BUY"):
        type = "BUY"
    if (process == "SELL"):
        type = "SELL"

    order = OrderHistory(
        stockId = stock.stockId,
        userId = current_user.userId,
        type = type,
        quantity = quantity,
        price = stock.currentMktPrice,
        totalValue = amount,
        status = "OPEN",
        companyName = stock.name,
        ticker = stock.ticker,
        createdAt = datetime.datetime.now(),
        updatedAt = datetime.datetime.now()
    )

    db.session.add(order)
    db.session.flush()
    return order

def updatePortfolio(order):

    stock = Portfolio.query.filter_by(userId=order.userId, ticker=order.ticker).first()

    if order.type == "BUY":

        if stock is None:
            quantity = order.quantity

            portfolio = Portfolio(
                userId = order.userId,
                orderId = order.orderId,
                stockName = order.companyName,
                ticker = order.ticker,
                quantity = quantity,
                mktPrice = order.price,
                createdAt = datetime.datetime.now(),
                updatedAt = datetime.datetime.now()
            )

            db.session.add(portfolio)
        else:
            stock.quantity = stock.quantity + order.quantity
            stock.orderId = order.orderId
            stock.mktPrice = order.price
            stock.updatedAt = datetime.datetime.now()            
    elif order.type == "SELL":
        quantity = order.quantity

        stock.quantity = stock.quantity - order.quantity

        if stock.quantity > 0:
            stock.orderId = order.orderId
            stock.mktPrice = order.price
            stock.updatedAt = datetime.datetime.now()
        elif stock.quantity == 0:
            db.session.delete(stock)

def calculateValue():

    stock = (
        Portfolio.query.join(StockInventory, Portfolio.ticker == StockInventory.ticker)
        .with_entities(Portfolio.quantity, StockInventory.currentMktPrice)
        .filter(Portfolio.userId == current_user.userId)
        .all()
    )

    value = 0
    for quantity, currentMktPrice in stock:
        row = quantity * currentMktPrice
        value += row

    return value

def calculateContribution():

    transactions = (
        FinancialTransaction.query.with_entities(
            FinancialTransaction.amount,
            FinancialTransaction.type
        )
        .filter_by(username = current_user.username)
        .all()
    )

    contributions = 0
    for amount, type in transactions:
        if type == "DEPOSIT":
            contributions += amount
        elif type == "WITHDRAW":
            contributions -= amount

    return contributions

# View Order History Route
@app.route("/home/order_history")
@login_required
def viewOrderHistory():
    orders = (
        OrderHistory.query
        .filter_by(userId=current_user.userId)
        .order_by(OrderHistory.createdAt.desc())
        .all()
    )

    return render_template("order_history.html", orders=orders)

# END USER ROUTES------------------------------------------------------------------------------------

# BRETT: RANDOM NUMBER GENERATION -------------------------------------------------------------------
def _update_stock_prices():
    now = datetime.datetime.now()
    today = now.date()

    market_open, market_start, market_end, holiday = get_market_status(today)

    stocks = StockInventory.query.all()

    for stock in stocks:
       
        if stock.currentMktPrice is None:
            stock.currentMktPrice = stock.initStockPrice or 0.0

        if stock.dailyDate != today and market_open:
            base_price = float(stock.currentMktPrice or stock.initStockPrice or 0.0)
            stock.dailyDate = today
            stock.dailyOpenPrice = base_price
            stock.dailyHighPrice = base_price
            stock.dailyLowPrice = base_price
            stock.volume = 0

        if not market_open:
            continue

        change_pct = random.uniform(-0.03, 0.03)
        new_price = stock.currentMktPrice * (1 + change_pct)

        if new_price < 0.01:
            new_price = 0.01

        new_price = round(new_price, 2)
        stock.currentMktPrice = new_price
        stock.updatedAt = now

        if stock.dailyHighPrice is None or new_price > stock.dailyHighPrice:
            stock.dailyHighPrice = new_price
        if stock.dailyLowPrice is None or new_price < stock.dailyLowPrice:
            stock.dailyLowPrice = new_price

        if stock.volume is None:
            stock.volume = 0
        stock.volume += random.randint(0, 1000)

    db.session.commit()


@app.route("/api/stock_prices")
@login_required
def api_stock_prices():
    _update_stock_prices()

    stocks = (
        db.session.query(
            StockInventory.ticker,
            StockInventory.currentMktPrice,
            StockInventory.initStockPrice,
            StockInventory.volume,
            StockInventory.dailyOpenPrice,
            StockInventory.dailyHighPrice,
            StockInventory.dailyLowPrice,
            Company.stockTotalQty
        )
        .join(Company, StockInventory.companyId == Company.companyId)
        .order_by(StockInventory.ticker)
        .all()
    )

    data = []
    for s in stocks:
        current = float(s.currentMktPrice or 0.0)
        init_price = float(s.initStockPrice or 0.0)
        volume = int(s.volume or 0)
        open_price = float(s.dailyOpenPrice or 0.0)
        high_price = float(s.dailyHighPrice or 0.0)
        low_price = float(s.dailyLowPrice or 0.0)
        total_qty = int(s.stockTotalQty or 0)

        market_cap = current * total_qty if total_qty > 0 else 0.0

        data.append({
            "ticker": s.ticker,
            "currentMktPrice": current,
            "initStockPrice": init_price,
            "volume": volume,
            "dailyOpenPrice": open_price,
            "dailyHighPrice": high_price,
            "dailyLowPrice": low_price,
            "marketCap": market_cap,
        })

    return jsonify(data)
# END RANDOM NUMBER GENERATION -----------------------------------------------------------------------------------------------------

# ADMIN ROUTES-----------------------------------------------------------------------------------------

# Create Stock Route
@app.route("/home/admin/createstock", methods=["GET", "POST"])
@admin_required
def createStock():
    if request.method == "POST":

        companyName = request.form.get("companyName")
        companyDesc = request.form.get("companyDesc")
        ticker = request.form.get("ticker")
        volume = request.form.get("volume")
        initStockPrice = request.form.get("initStockPrice")

        if (companyName == "") or (companyName is None) or (companyDesc == "") or (companyDesc is None) or (ticker == "") or (ticker is None) or (volume == "") or (volume is None) or (initStockPrice == "") or (initStockPrice is None):
            flash("Empty fields. Please enter a name, description, ticker, volume, and price.", "danger")
            return render_template("create_stock.html")

        try:
            ticker = ticker.strip().upper()
            volume = int(volume)
            initStockPrice = float(initStockPrice)

            if (volume <= 0) or (initStockPrice <= 0):
                flash("Volume and Price must be positive. Please try again.", "danger")
                return render_template("create_stock.html")
        except:
            flash("Error converting values. Please try again.", "danger")
            return render_template("create_stock.html")

        try:
            company = Company.query.filter_by(ticker=ticker).first()
            stock = StockInventory.query.filter_by(ticker=ticker).first()

            if (company) or (stock):
                flash("Stock/Company already exists. Please create a new stock.", "danger")
                return render_template("create_stock.html")

            company = addCompany(companyName, companyDesc, ticker, volume, initStockPrice)

            addStock(company)

            db.session.commit()

            flash("Stock created successfully.", "success")
            return redirect(url_for("homeAdmin"))
        except:
            db.session.rollback()
            flash("Error creating stock. Please try again.", "danger")
            return render_template("create_stock.html")
    
    stock = (
        StockInventory.query.with_entities(
            StockInventory.ticker,
            StockInventory.currentMktPrice,
            StockInventory.initStockPrice
        )
        .order_by(StockInventory.ticker)
        .all()
    )   

    return render_template("create_stock.html", stock=stock)

def addCompany(name, description, ticker, volume, initStockPrice):

    company = Company(
        name = name,
        description = description,
        stockTotalQty = volume,
        ticker = ticker,
        currentMktPrice = initStockPrice,
        createdAt = datetime.datetime.now(),
        updatedAt = datetime.datetime.now()
    )

    db.session.add(company)
    db.session.flush()
    return company


def addStock(company):

    stock = StockInventory(
        companyId = company.companyId,
        adminId = current_user.adminId,
        name = company.name,
        ticker = company.ticker,
        quantity = company.stockTotalQty,
        initStockPrice = company.currentMktPrice,
        currentMktPrice = company.currentMktPrice,
        createdAt = datetime.datetime.now(),
        updatedAt = datetime.datetime.now()
    )

    db.session.add(stock)
    db.session.flush()

# PUT CHANGEMKTHRS/CHANGEMKTSCHEDULE HERE

#Market hrs begins
@app.route("/home/admin/changemkthrs", methods=["GET", "POST"])
@admin_required
def changeMktHrs():
    if request.method == "POST":
        # ---- 0. Quick action: open market (clear all closures) ----
        action = request.form.get("action", "")
        if action == "clear_all":
            try:
                Exception.query.filter_by(adminId=current_user.adminId).delete()
                db.session.commit()
                flash("All market closures cleared. Market is now open on all dates.", "success")
            except:
                db.session.rollback()
                flash("Error clearing market closures.", "danger")
            return redirect(url_for("changeMktHrs"))

        close_market = request.form.get("close_market")
        selected_date = request.form.get("selected_date", "").strip()
        close_reason = request.form.get("close_reason", "").strip()

        if close_market == "on" and selected_date:
            try:
                date_obj = datetime.datetime.strptime(selected_date, "%Y-%m-%d")
                ex = Exception(
                    adminId=current_user.adminId,
                    reason=close_reason or "Closed by admin",
                    holidayDate=date_obj,
                    createdAt=datetime.datetime.now(),
                    updatedAt=datetime.datetime.now()
                )
                db.session.add(ex)
                db.session.commit()
                flash(f"Market closed for {selected_date}.", "success")
                return redirect(url_for("changeMktHrs"))
            except:
                db.session.rollback()
                flash("Error saving closed date.", "danger")
                return redirect(url_for("changeMktHrs"))

    
        day = request.form.get("dayOfWeek", "").strip()
        startTime = request.form.get("startTime", "").strip()
        endTime = request.form.get("endTime", "").strip()

        
        if not day or not startTime or not endTime:
            flash("Please choose a day and enter open/close times.", "danger")
            return redirect(url_for("changeMktHrs"))

        try:
            start_time = datetime.datetime.strptime(startTime, "%H:%M").time()
            end_time = datetime.datetime.strptime(endTime, "%H:%M").time()
        except:
            flash("Time must be in HH:MM format (HH:MM).", "danger")
            return redirect(url_for("changeMktHrs"))

       
        day = day[:3].capitalize()

        try:
            wd = WorkingDay.query.filter_by(
                adminId=current_user.adminId,
                dayOfWeek=day
            ).first()

            if wd is None:
                wd = WorkingDay(
                    adminId=current_user.adminId,
                    dayOfWeek=day,
                    startTime=start_time,
                    endTime=end_time,
                    createdAt=datetime.datetime.now(),
                    updatedAt=datetime.datetime.now()
                )
                db.session.add(wd)
            else:
                wd.startTime = start_time
                wd.endTime = end_time
                wd.updatedAt = datetime.datetime.now()

            db.session.commit()
            flash(f"Market hours saved for {day}.", "success")
            return redirect(url_for("changeMktHrs"))
        except:
            db.session.rollback()
            flash("Error saving market hours.", "danger")
            return redirect(url_for("changeMktHrs"))

   
    workingDays = WorkingDay.query.filter_by(
        adminId=current_user.adminId
    ).order_by(WorkingDay.dayOfWeek).all()

    return render_template("change_mkt_hrs.html", workingDays=workingDays)



#Mkt schedule begins
@app.route("/home/admin/changemktschedule", methods=["GET", "POST"])
@admin_required
def changeMktSchedule():
    if request.method == "POST":
        holidayDate = request.form.get("holidayDate", "").strip()
        reason = request.form.get("reason", "").strip()

        if not holidayDate:
            flash("Please enter a date.", "danger")
            return render_template("change_mkt_schedule.html")

        try:
            date_obj = datetime.datetime.strptime(holidayDate, "%Y-%m-%d")
        except:
            flash("Date must be in YYYY-MM-DD format.", "danger")
            return render_template("change_mkt_schedule.html")

        try:
            ex = Exception(
                adminId=current_user.adminId,
                reason=reason,
                holidayDate=date_obj,
                createdAt=datetime.datetime.now(),
                updatedAt=datetime.datetime.now()
            )
            db.session.add(ex)
            db.session.commit()
            flash("Market closure / holiday added.", "success")
            return redirect(url_for("changeMktSchedule"))
        except:
            db.session.rollback()
            flash("Error saving market schedule.", "danger")

    exceptions = Exception.query.filter_by(
        adminId=current_user.adminId
    ).order_by(Exception.holidayDate.desc()).all()

    return render_template("change_mkt_schedule.html", exceptions=exceptions)

# END ADMIN ROUTES-------------------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
