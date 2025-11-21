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
            flash("Please login to access this webpage.", "error")
            return redirect(url_for("signIn"))
        elif not isinstance(current_user, Admin):
            flash("Please login with an Admin account to access this webpage.", "error")
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
            flash("Empty fields. Please try again.", "error")
            return render_template("create_account_admin.html")
        
        if password != confPassword:
            flash("Passwords do not match. Please try again.", "error")
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
            flash("Error. Please try again.", "error")
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

    # Default
    market_open = False
    market_start = None
    market_end = None

    # Market cannot open if no working day OR if it's a holiday
    if wd and not holiday:
        market_start = wd.startTime
        market_end = wd.endTime

        # Check time only if it's today
        if target_date == now.date():
            current = now.time()
            if market_start <= current <= market_end:
                market_open = True

    return market_open, market_start, market_end, holiday

# -------------------------------------------------------------------

# HOME ROUTES---------------------------------------------------------------------------------------

# Home Route for User
@app.route("/home")
@login_required
def home():

    try:
        stock = (
            StockInventory.query.with_entities(
            StockInventory.ticker,
            StockInventory.currentMktPrice,
            StockInventory.initStockPrice
            )
            .order_by(StockInventory.ticker)
            .limit(3)
            .all()
        )

        portfolio = (
            Portfolio.query.with_entities(
                Portfolio.ticker,
                Portfolio.mktPrice,
                Portfolio.quantity
            )
            .filter_by(userId=current_user.userId) # <-- filter by logged-in user
            .order_by(Portfolio.ticker)
            .all()
        )

        portfolioValue = calculateValue()
        contributions = calculateContribution()
        totalReturn = (current_user.availableFunds + portfolioValue) - contributions
    except:
        flash("Error retrieving values from DB.", "error")
        return render_template("home.html")

    return render_template("home.html", stock=stock, portfolio=portfolio, totalReturn=totalReturn)
    
# Home Route for Admin
@app.route("/home/admin")
@admin_required
def homeAdmin():

    try:
        user = (
            User.query.with_entities(
                User.fullName,
                User.email,
                User.username,
                User.availableFunds
            )
            .order_by(User.fullName)
            .all()
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
        flash("Error retrieving values from DB", "error")
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
            flash("Please enter a deposit amount.", "error")
            return render_template("deposit.html")
        
        try:
            amount = float(amount)

            if (amount <= 0):
                flash("Deposit amount must be non-negative. Please try again.", "error")
                return render_template("deposit.html")
        except:
            flash("Error converting deposit amount to float. Please try again.", "error")
            return render_template("deposit.html")
        
        try:
            depositAction(amount)
            db.session.commit()
            flash("Deposit processed successfully.", "success")
            return redirect(url_for("home"))
        
        except:
            db.session.rollback()
            flash("Error. Please try again.", "error")
            return render_template("deposit.html")

    return render_template("deposit.html")

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
            flash("Please enter a withdrawal amount.", "error")
            return render_template("withdraw.html")
        
        try:
            amount = float(amount)

            if (amount <= 0):
                flash("Withdrawal amount must be positive. Please try again.", "error")
                return render_template("withdraw.html")
            
            if (amount > current_user.availableFunds):
                flash("Cannot withdraw more than the user's Balance. Please try again.", "error")
                return render_template("withdraw.html")
        except:
            flash("Error converting withdrawal amount to float. Please try again.", "error")
            return render_template("withdraw.html")
        
        try:
            withdrawAction(amount)
            db.session.commit()
            flash("Withdrawal processed successfully.", "success")
            return redirect(url_for("home"))
        except:
            db.session.rollback()
            flash("Error. Please try again.", "error")
            return render_template("withdraw.html")
        
    return render_template("withdraw.html")

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
    # Compute market status once per request (for today)
    market_open, market_start, market_end, holiday = get_market_status()

    if request.method == "POST":

        # HARD BLOCK if market is closed, even if someone tries to POST manually
        if not market_open:
            flash("Market is currently closed. You cannot place buy orders.", "error")
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
            flash("Empty fields. Please enter a ticker and quantity.", "error")
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
                flash("Quantity must be positive. Please try again.", "error")
                return render_template(
                    "buy_stock.html",
                    market_open=market_open,
                    market_start=market_start,
                    market_end=market_end,
                    holiday=holiday
                )
        except:
            flash("Error converting quantity to int. Please try again.", "error")
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
                flash("Stock not found. Please enter a valid stock.", "error")
                return render_template(
                    "buy_stock.html",
                    market_open=market_open,
                    market_start=market_start,
                    market_end=market_end,
                    holiday=holiday
                )

            transactionAmount = stock.currentMktPrice * quantity

            if transactionAmount > current_user.availableFunds:
                flash("Insufficient funds for this transaction. Please deposit funds.", "error")
                return render_template(
                    "buy_stock.html",
                    market_open=market_open,
                    market_start=market_start,
                    market_end=market_end,
                    holiday=holiday
                )

            if quantity > stock.quantity:
                flash("Inputted quantity exceeds Market Cap. Please enter a different quantity.", "error")
                return render_template(
                    "buy_stock.html",
                    market_open=market_open,
                    market_start=market_start,
                    market_end=market_end,
                    holiday=holiday
                )
        except:
            flash("Error. Please try again.", "error")
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
            flash("Error placing buy order. Please try again.", "error")
            return render_template(
                "buy_stock.html",
                market_open=market_open,
                market_start=market_start,
                market_end=market_end,
                holiday=holiday
            )

    # GET request
    return render_template(
        "buy_stock.html",
        market_open=market_open,
        market_start=market_start,
        market_end=market_end,
        holiday=holiday
    )

# Sell Stock Route
@app.route("/home/sellstock", methods=["GET", "POST"])
@login_required
def sellStock():
    if request.method == "POST":

        ticker = request.form.get("ticker")
        quantity = request.form.get("quantity")

        if (ticker == "") or (quantity == "") or (ticker is None) or (quantity is None):
            flash("Empty fields. Please enter a ticker and quantity.", "error")
            return render_template("sell_stock.html")
        
        try:
            ticker = ticker.strip().upper()
            quantity = int(quantity)

            if (quantity <= 0):
                flash("Quantity must be positive. Please try again.", "error")
                return render_template("sell_stock.html")
        except:
            flash("Error converting quantity to int. Please try again.", "error")
            return render_template("sell_stock.html")
        
        try:
            stock = StockInventory.query.filter_by(ticker=ticker).first()

            if not stock:
                flash("Stock not found. Please enter a valid stock.", "error")
                return render_template("sell_stock.html")
            
            transactionAmount = stock.currentMktPrice * quantity

            position = (
                Portfolio.query.filter_by(userId=current_user.userId, ticker=ticker)
                .first()
            )

            if (position is None) or position.quantity == 0:
                flash("User does not own this stock. Please purchase stock to sell.", "error")
                return render_template("sell_stock.html")
            
            if quantity > position.quantity:
                flash("Cannot sell more than owned shares. Please enter a different quantity.", "error")
                return render_template("sell_stock.html")
        except:
            flash("Error. Please try again.", "error")
            return render_template("sell_stock.html")
        
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
            flash("Error placing sell order. Please try again.", "error")
            return render_template("sell_stock.html")

    return render_template("sell_stock.html")

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
    # Get all orders for the logged-in user, most recent first
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
    """
    Simple random-walk price generator.
    Called whenever /api/stock_prices is hit.
    """
    stocks = StockInventory.query.all()

    for stock in stocks:
        # If no current price yet, start from initStockPrice
        if stock.currentMktPrice is None:
            stock.currentMktPrice = stock.initStockPrice or 0.0

        # Random change between -5% and +5%
        change_pct = random.uniform(-0.05, 0.05)

        new_price = stock.currentMktPrice * (1 + change_pct)

        # Never allow 0 or negative prices
        if new_price < 0.01:
            new_price = 0.01

        # Round to 2 decimals (like a real stock price)
        stock.currentMktPrice = round(new_price, 2)
        stock.updatedAt = datetime.datetime.now()

    db.session.commit()


@app.route("/api/stock_prices")
@login_required
def api_stock_prices():
    """
    Returns the latest stock prices as JSON.
    Also updates prices each time it is called.
    home.html and home_admin.html poll this.
    """
    _update_stock_prices()

    stocks = (
        StockInventory.query.with_entities(
            StockInventory.ticker,
            StockInventory.currentMktPrice,
            StockInventory.initStockPrice
        )
        .order_by(StockInventory.ticker)
        .all()
    )

    data = []
    for s in stocks:
        data.append({
            "ticker": s.ticker,
            "currentMktPrice": float(s.currentMktPrice or 0.0),
            "initStockPrice": float(s.initStockPrice or 0.0),
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
            flash("Empty fields. Please enter a name, description, ticker, volume, and price.", "error")
            return render_template("create_stock.html")

        try:
            ticker = ticker.strip().upper()
            volume = int(volume)
            initStockPrice = float(initStockPrice)

            if (volume <= 0) or (initStockPrice <= 0):
                flash("Volume and Price must be positive. Please try again.", "error")
                return render_template("create_stock.html")
        except:
            flash("Error converting values. Please try again.", "error")
            return render_template("create_stock.html")

        try:
            company = Company.query.filter_by(ticker=ticker).first()
            stock = StockInventory.query.filter_by(ticker=ticker).first()

            if (company) or (stock):
                flash("Stock/Company already exists. Please create a new stock.", "error")
                return render_template("create_stock.html")

            company = addCompany(companyName, companyDesc, ticker, volume, initStockPrice)

            addStock(company)

            db.session.commit()

            flash("Stock created successfully.", "success")
            return redirect(url_for("homeAdmin"))
        except:
            db.session.rollback()
            flash("Error creating stock. Please try again.", "error")
            return render_template("create_stock.html")
            


    return render_template("create_stock.html")

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
                flash("Error saving closed date.", "error")
  
        day = request.form.get("dayOfWeek", "").strip()
        startTime = request.form.get("startTime", "").strip()
        endTime = request.form.get("endTime", "").strip()

        if day and startTime and endTime:
            try:
                start_time = datetime.datetime.strptime(startTime, "%H:%M").time()
                end_time = datetime.datetime.strptime(endTime, "%H:%M").time()
            except:
                flash("Time must be in HH:MM format (HH:MM).", "error")
                return render_template("change_mkt_hrs.html")

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
                flash("Market hours saved.", "success")
                return redirect(url_for("changeMktHrs"))
            except:
                db.session.rollback()
                flash("Error saving market hours.", "error")

    workingDays = WorkingDay.query.filter_by(
        adminId=current_user.adminId
    ).order_by(WorkingDay.dayOfWeek).all()

    return render_template("change_mkt_hrs.html", workingDays=workingDays, exceptions=exceptions)

@app.route("/home/admin/openallmarkets", methods=["POST"])
@admin_required
def openAllMarkets():
    try:
        Exception.query.filter_by(adminId=current_user.adminId).delete()
        db.session.commit()
        flash("All market closures cleared. Market is now open.", "success")
    except:
        db.session.rollback()
        flash("Error clearing market closures.", "error")

    return redirect(url_for("changeMktSchedule"))

#Mkt schedule begins
@app.route("/home/admin/changemktschedule", methods=["GET", "POST"])
@admin_required
def changeMktSchedule():
    if request.method == "POST":
        holidayDate = request.form.get("holidayDate", "").strip()
        reason = request.form.get("reason", "").strip()

        if not holidayDate:
            flash("Please enter a date.", "error")
            return render_template("change_mkt_schedule.html")

        try:
            date_obj = datetime.datetime.strptime(holidayDate, "%Y-%m-%d")
        except:
            flash("Date must be in YYYY-MM-DD format.", "error")
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
            flash("Error saving market schedule.", "error")

    exceptions = Exception.query.filter_by(
        adminId=current_user.adminId
    ).order_by(Exception.holidayDate.desc()).all()

    return render_template("change_mkt_schedule.html", exceptions=exceptions)

# END ADMIN ROUTES-------------------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
