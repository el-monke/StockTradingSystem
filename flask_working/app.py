from flask import Flask, render_template, request, url_for, flash, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask import jsonify
from flask_bcrypt import Bcrypt
from functools import wraps # For Admin only routes
import datetime
import uuid
import builtins
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DecimalField, SubmitField
from wtforms.validators import DataRequired, NumberRange
from datetime import time as dtime, date as ddate
from sqlalchemy import func
from decimal import Decimal
import random
from apscheduler.schedulers.background import BackgroundScheduler



app = Flask(__name__)
# DATABASE -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://admin:password123@flask-rds-test.cq7ucai8kixi.us-east-1.rds.amazonaws.com:3306/sts_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key'

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)


bcrypt = Bcrypt(app)

# --- Real-Time Stock Price Fluctuation ---
def fluctuate_stock_prices():
    with app.app_context():
        stocks = StockInventory.query.all()
        for stock in stocks:
            # Simulate price change: random walk
            change = random.uniform(-0.5, 0.5)  # Change by up to ±0.5
            new_price = max(0.01, stock.currentMktPrice + change)
            stock.currentMktPrice = round(new_price, 2)
            stock.updatedAt = datetime.datetime.now()
        db.session.commit()

scheduler = BackgroundScheduler()
scheduler.add_job(fluctuate_stock_prices, 'interval', seconds=10)
scheduler.start()
# --- End Real-Time Stock Price Fluctuation ---

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
        return f"user:{self.userId}"

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
        return f"admin:{self.adminId}"

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
    userId = db.Column(db.Integer, ForeignKey("user.userId"))
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

# Return start / end time from workingday default 0730-16
def get_current_hours():
    hrs = WorkingDay.query.order_by(WorkingDay.updatedAt.desc()).first()
    if not hrs or not (hrs.startTime and hrs.endTime):
        return dtime(7, 30), dtime(16, 0)  # default hours
    return hrs.startTime, hrs.endTime

def is_holiday(day: ddate = None) -> bool:
    day = day or ddate.today()
    return db.session.query(Exception.exceptionId).filter(
        func.date(Exception.holidayDate) == day
    ).first() is not None

def is_market_open(now: datetime.datetime = None) -> bool:
    now = now or datetime.datetime.now()
    if is_holiday(now.date()):
        return False
    start, end = get_current_hours()
    time = now.time()
    if start <= end:
        return start <= time <= end
    return not (end < time < start)

# END DATABASE -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# User loader
@login_manager.user_loader
def load_user(user_id):
    type, unprefix = user_id.split(":", 1)
    trueId = int(unprefix)

    if type == "admin":
        return Admin.query.get(trueId)
    if type == "user":
        return User.query.get(trueId)

# Home Route
@app.route('/')
@login_required  # Restricts access to authenticated users only
def home():
    
    market_open = is_market_open()
    start, end = get_current_hours()
    holiday_today = is_holiday()

    if current_user.role == "user":
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
            .filter_by(userId=current_user.userId)
            .order_by(Portfolio.ticker)
            .limit(5)
            .all()
        )
        # Logic for chart.js bar chart
        holdings = {}
        for ticker, mktPrice, quantity in portfolio:
            qty = int(quantity)
            d = holdings.setdefault(ticker, {"qty": 0, "cost": Decimal("0")})
            d["qty"] += quantity
            d["cost"] += Decimal(str(mktPrice)) * quantity

        rows = []
        for ticker, s in holdings.items():
            currentPrice = get_live_price(ticker)
            position = currentPrice * s["qty"]
            pnl = position - s["cost"]

            rows.append({
                "name": ticker,
                "cost": float(s["cost"]),
                "profit_loss": float(pnl)
            })

        return render_template(
            "home.html",
            stock=stock,
            portfolio=portfolio,
            rows=rows,
            market_open=market_open,
            market_start=start,
            market_end=end,
            holiday=holiday_today
        )

    # Admin view
    users = (
        User.query.with_entities(
            User.userId,
            User.fullName,
            User.email,
            User.customerAccountNumber,
            User.availableFunds
        )
        .order_by(User.createdAt.desc())
        .all()
    )
    stock = (
        StockInventory.query.with_entities(
            StockInventory.ticker,
            StockInventory.quantity,
            StockInventory.initStockPrice,
            StockInventory.currentMktPrice
        )
        .order_by(StockInventory.createdAt)
        .all()
    )
    return render_template(
        "home.html",
        user=users,
        stock=stock,
        market_open=market_open,
        market_start=start,
        market_end=end,
        holiday=holiday_today
    )

# API route for stock price updates
@app.route('/api/stock_prices')
@login_required
def api_stock_prices():
    stocks = StockInventory.query.with_entities(
        StockInventory.ticker,
        StockInventory.quantity,
        StockInventory.initStockPrice,
        StockInventory.currentMktPrice
    ).order_by(StockInventory.ticker).all()
    result = [
        {"ticker": s.ticker, "quantity": s.quantity, "initStockPrice": s.initStockPrice, "currentMktPrice": s.currentMktPrice}
        for s in stocks
    ]
    return jsonify(result)

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

# Admin Required Route
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            return redirect(url_for("signIn"))
        return f(*args, **kwargs)
    return decorated_function

# LogOut Route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for("signIn"))

# UPDATE (update fullname & email)
@app.route('/update_user/<int:user_id>', methods=["GET","POST"])
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == "POST":
        user.fullName = request.form.get("fullName")
        user.email = request.form.get("email")
        user.availableFunds = request.form.get("availableFunds")
        user.updatedAt = datetime.datetime.now()

        try:
            db.session.commit()
            flash(f'User {user.userId} updated successfully!', 'success')
            return redirect(url_for('home'))
        except builtins.Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'error')
            return redirect(url_for('home'))
    return render_template('update_user.html', user=user)

# DELETE
@app.route('/delete_user/<int:user_id>', methods=["POST"])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    try:
        Portfolio.query.filter_by(userId=user.userId).delete()
        OrderHistory.query.filter_by(userId=user.userId).delete()
        FinancialTransaction.query.filter_by(customerAccountNumber=user.customerAccountNumber).delete()

        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.userId} deleted successfully!', 'success')
    except builtins.Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')
    return redirect(url_for('home'))

#----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


# Buy Stock Route
@app.route('/home/buystock', methods=['GET', 'POST'])
def buyStock():

    market_open = is_market_open()
    start, end = get_current_hours()
    holiday_today = is_holiday()

    if holiday_today:
        market_open = False

    if request.method == "POST":
        if holiday_today:
            flash("Market is closed. Buy orders are disabled right now.", "warning")
            return redirect(url_for("buyStock"))

        ticker = request.form.get("ticker")
        stock = StockInventory.query.filter_by(ticker=ticker).first()
        quantity = request.form.get("quantity")
        amt = stock.currentMktPrice * float(quantity)

        withdraw_action(amt, commit=False)
        order = OrderHistory(
            stockId=stock.stockId,
            userId=current_user.userId,
            type="BUY",
            quantity=quantity,
            price=stock.currentMktPrice,
            totalValue=amt,
            status="OPEN",
            companyName=stock.name,
            ticker=stock.ticker,
            createdAt=datetime.datetime.now(),
            updatedAt=datetime.datetime.now()
        )
        db.session.add(order)
        db.session.flush()
        portfolio = Portfolio(
            userId=current_user.userId,
            orderId=order.orderId,
            stockName=stock.name,
            ticker=stock.ticker,
            quantity=quantity,
            mktPrice=stock.currentMktPrice,
            createdAt=datetime.datetime.now(),
            updatedAt=datetime.datetime.now()
        )
        db.session.add(portfolio)
        db.session.commit()
        return redirect(url_for("home"))

    market_open = is_market_open()
    start, end = get_current_hours()
    return render_template('buy_stock.html',
                           market_open=market_open,
                           market_start=start,
                           market_end=end)

# Sell Stock Route
@app.route('/home/sellstock', methods=['GET', 'POST'])
def sellStock():

    market_open = is_market_open()
    start, end = get_current_hours()
    holiday_today = is_holiday()

    if holiday_today:
        market_open = False

    if request.method == "POST":
        if holiday_today:
            flash("Market is closed. Sell orders are disabled right now.", "warning")
            return redirect(url_for("sellStock"))

        ticker = request.form.get("ticker")
        stock = StockInventory.query.filter_by(ticker=ticker).first()
        quantity = request.form.get("quantity")
        amt = stock.currentMktPrice * float(quantity)

        deposit_action(amt)
        order = OrderHistory(
            stockId=stock.stockId,
            userId=current_user.userId,
            type="SELL",
            quantity=quantity,
            price=stock.currentMktPrice,
            totalValue=amt,
            status="OPEN",
            companyName=stock.name,
            ticker=stock.ticker,
            createdAt=datetime.datetime.now(),
            updatedAt=datetime.datetime.now()
        )
        db.session.add(order)
        db.session.flush()
        portfolio = Portfolio(
            userId=current_user.userId,
            orderId=order.orderId,
            stockName=stock.name,
            ticker=stock.ticker,
            quantity=quantity,
            mktPrice=stock.currentMktPrice,
            createdAt=datetime.datetime.now(),
            updatedAt=datetime.datetime.now()
        )
        db.session.add(portfolio)
        db.session.flush()
        return redirect(url_for("home"))

    market_open = is_market_open()
    start, end = get_current_hours()
    return render_template('sell_stock.html',
                           market_open=market_open,
                           market_start=start,
                           market_end=end)

# Deposit Funds Route
@app.route('/home/deposit', methods=["GET", "POST"])
def depositFunds():
    if request.method == "POST":
        amt = request.form.get("amount")
        deposit_action(amt)
        # Call Portfolio
        if FinancialTransaction.query.filter_by(customerAccountNumber=current_user.customerAccountNumber).first() == None:
            createPortfolio(current_user.userId)

        return redirect(url_for("home"))
    return render_template("deposit.html")

def deposit_action(amount):
    deposit = FinancialTransaction(
            customerAccountNumber = current_user.customerAccountNumber,
            amount=amount,
            type="deposit",
            createdAt = datetime.datetime.now()
        )
    # Update Available funds
    current_user.availableFunds = current_user.availableFunds + float(amount)
    current_user.updatedAt = datetime.datetime.now()
    
    db.session.add(deposit)
    db.session.commit()
    
# Create Portfolio
def createPortfolio(userId):
    portfolio = Portfolio(
        userId = current_user.userId,
        createdAt = datetime.datetime.now(),
        updatedAt = datetime.datetime.now()       
    )
    db.session.add(portfolio)
    db.session.commit()

# Withdraw Funds Route
@app.route('/home/withdraw', methods=["GET", "POST"])
def withdrawFunds():
    if request.method == "POST":
        amt = request.form.get("amount")
        withdraw_action(amt)
        
        return redirect(url_for("home"))
    return render_template("withdraw.html")

def withdraw_action(amount, commit=True):
    withdraw = FinancialTransaction(
            customerAccountNumber = current_user.customerAccountNumber,
            amount=amount,
            type="withdraw",
            createdAt=datetime.datetime.now()
        )
    # Withdraw from Available Funds
    current_user.availableFunds = current_user.availableFunds - float(amount)
    current_user.updatedAt = datetime.datetime.now()
    
    db.session.add(withdraw)
    if commit == True:
        db.session.commit()
        
@app.route('/home/history', methods=['GET'])
def orderHistory():

    orders = OrderHistory.query.filter_by(userId=current_user.userId).order_by(OrderHistory.createdAt.desc()).all()
    
    return render_template("order_history.html", orders=orders)

# Stock page Route
@app.route('/home/stock', methods=['GET', 'POST'])
def stocks():
    return render_template("stock.html")

class StockForm(FlaskForm):
    ticker = StringField("Ticker", validators=[DataRequired()])  # string for stocks
    quantity = IntegerField("Quantity", validators=[DataRequired(), NumberRange(min=1)])
    avg_cost = DecimalField(
        "Average Cost",
        places=2,
        rounding=None,
        validators=[DataRequired(), NumberRange(min=0)]
    )
    submit = SubmitField("Add to Portfolio")

# data
def get_live_price(symbol: str) -> Decimal:
   
    sym = (symbol or "").upper().strip()
    if not sym:
        return Decimal("0")

    # company table
    comp = Company.query.filter_by(ticker=sym).first()
    if comp and comp.currentMktPrice is not None:
        return Decimal(str(comp.currentMktPrice))

    # stock invetory
    sck = (StockInventory.query
          .filter_by(ticker=sym)
          .order_by(StockInventory.updatedAt.desc())
          .first())
    if sck and sck.currentMktPrice is not None:
        return Decimal(str(sck.currentMktPrice))

    # No price found
    return Decimal("0")


@app.route("/stock", methods=["GET", "POST"])
@login_required
def stock():
    market_open = is_market_open()
    start, end = get_current_hours()
    holiday_today = is_holiday()

    form = StockForm()

    if form.validate_on_submit():
        if not market_open:
            flash("Market is closed. Adding to portfolio is disabled right now.", "warning")
            return redirect(url_for("stock"))

        now = datetime.datetime.now()
        p = Portfolio(
            userId=current_user.userId,
            orderId=None,
            stockName=form.ticker.data.upper(),
            ticker=form.ticker.data.upper(),
            quantity=int(form.quantity.data),
            mktPrice=float(form.avg_cost.data),
            createdAt=now,
            updatedAt=now
        )
        db.session.add(p)
        db.session.commit()
        flash(f"Added {p.ticker} x{p.quantity} at ${p.mktPrice:.2f}", "success")
        return redirect(url_for("stock"))

    rows = []
    holdings = Portfolio.query.filter_by(userId=current_user.userId).order_by(Portfolio.ticker.asc()).all()
    for h in holdings:
        current = get_live_price(h.ticker)
        qty = int(h.quantity or 0)
        avg_cost = Decimal(str(h.mktPrice or 0))
        position_value = current * qty
        profit_loss = position_value - (avg_cost * qty)
        rows.append({
            "name": h.ticker,
            "quantity": qty,
            "avg_cost": avg_cost,
            "current_price": current,
            "position_value": position_value,
            "profit_loss": profit_loss
        })

    totals = {
        "value": sum(r["position_value"] for r in rows),
        "cost": sum(r["avg_cost"] * r["quantity"] for r in rows),
    }
    totals["pnl"] = totals["value"] - totals["cost"]

    return render_template(
        "stock.html",
        form=form,
        rows=rows,
        totals=totals,
        market_open=market_open,
        market_start=start,
        market_end=end,
        holiday=holiday_today
    )

# Create Stock Route
@app.route('/createstock', methods=["GET", "POST"])
@login_required
@admin_required
def createStock():
    if request.method == "POST":
        addCompany(
            request.form.get("companyName"),
            request.form.get("companyDesc"),
            request.form.get("totalQuantity"),
            request.form.get("ticker"),
            request.form.get("currentMktPrice"),
            commit=False
        )
        db.session.flush()
        addStockInventory(
            request.form.get("companyName"),
            request.form.get("ticker"),
            request.form.get("totalQuantity"),
            request.form.get("initStockPrice"),
            request.form.get("currentMktPrice"),
            commit=False
        )
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("create_stock.html")

def addCompany(companyName, companyDesc, totalQuantity, ticker, currentMktPrice, commit=True):
    company = Company(
            name=companyName,
            description=companyDesc,
            stockTotalQty=totalQuantity,
            ticker=ticker,
            currentMktPrice=currentMktPrice,
            createdAt=datetime.datetime.now(),
            updatedAt=datetime.datetime.now()
    )

    db.session.add(company)
    if commit == True:
        db.session.commit()

def addStockInventory(companyName, ticker, quantity, initStockPrice, currentMktPrice, commit=True):
    company = Company.query.filter_by(ticker=ticker).first()
    
    stock = StockInventory(
        companyId=company.companyId,
        adminId=current_user.adminId,
        name=companyName,
        ticker=ticker,
        quantity=quantity,
        initStockPrice=initStockPrice,
        currentMktPrice=currentMktPrice,
        createdAt=datetime.datetime.now(),
        updatedAt=datetime.datetime.now()
    )

    db.session.add(stock)
    if commit == True:
        db.session.commit()

# Change Mkt Hours Route
@app.route('/admin/changemkthrs', methods=["GET", "POST"])
@login_required
@admin_required
def changeMktHrs():
    if request.method == "POST":
        startHrs = request.form.get("startTime")
        endHrs = request.form.get("endTime")
        start = datetime.datetime.strptime(startHrs.strip(), "%H:%M").time()
        end = datetime.datetime.strptime(endHrs.strip(), "%H:%M").time()
        hrs = WorkingDay(
            adminId=current_user.adminId,
            dayOfWeek=datetime.datetime.now().strftime("%a"),
            startTime=start,
            endTime=end,
            createdAt=datetime.datetime.now(),
            updatedAt=datetime.datetime.now()
        )
        db.session.add(hrs)
        db.session.commit()
        flash("Market hours updated.", "success")
        return redirect(url_for("home"))

    
    return render_template("change_mkt_hrs.html")


# Change Mkt Schedule Route
@app.route('/admin/changemktschedule', methods=["GET","POST"])
@login_required
@admin_required
def changeMktSchedule():
    if request.method == "POST":
        holidayForm = request.form.get("holiday")
        holidayDT = datetime.datetime.strptime(holidayForm.strip(), "%Y-%m-%d")
        holiday = Exception(
            adminId=current_user.adminId,
            reason=request.form.get("reason"),
            holidayDate=holidayDT,
            createdAt=datetime.datetime.now(),
            updatedAt=datetime.datetime.now()
        )
        db.session.add(holiday)
        db.session.commit()
        flash("Holiday added.", "success")
        return redirect(url_for("home"))

    
    return render_template("change_mkt_hrs.html")

def start_workingday(end_time: datetime.time):
    now = datetime.datetime.now()
    wd = WorkingDay(
        adminId=getattr(current_user, "adminId", None),
        dayOfWeek=now.strftime("%a"),
        startTime=now.time().replace(microsecond=0),
        endTime=end_time,
        createdAt=now,
        updatedAt=now
    )
    db.session.add(wd)
    db.session.commit()

def clear_today_holiday():
    with app.app_context():
        today = ddate.today()
        (db.session.query(Exception)
           .filter(func.date(Exception.holidayDate) == today)
           .delete(synchronize_session=False))
        db.session.commit()
        
# Reopen Market
@app.route('/admin/reopen_market', methods=['GET', 'POST'])
@login_required
@admin_required
def reopen_market():
    if request.form.get("clear_holiday") == "on":
        clear_today_holiday()

    end_txt = (request.form.get("endTime") or "").strip()
    if end_txt:
        try:
            end_time = datetime.datetime.strptime(end_txt, "%H:%M").time()
        except ValueError:
            flash("Invalid end time. Use HH:MM (24h).", "danger")
            return redirect(url_for("changeMktHrs"))
    else:
        _, fallback_end = get_current_hours()
        end_time = fallback_end or dtime(16, 0)

    start_workingday(end_time)
    flash("Market reopened for today.", "success")
    return redirect(url_for("home"))

def ensure_market_auto_reopen():
    with app.app_context():
        now = datetime.datetime.now()
        if is_holiday(now.date()):
            return

        if not is_market_open(now):
            _, fallback_end = get_current_hours()
            end_time = fallback_end or dtime(16, 0)
            start_workingday(end_time)

scheduler.add_job(
    ensure_market_auto_reopen,
    'interval',
    minutes=1,
    id='auto_reopen',
    replace_existing=True,
    coalesce=True,
    max_instances=1
)




if __name__ == "__main__":
    app.run(debug=True)
