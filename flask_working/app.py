from flask import Flask, render_template, request, url_for, flash, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from functools import wraps # For Admin only routes
import datetime
import uuid
import yfinance as yf
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DecimalField, SubmitField
from wtforms.validators import DataRequired, NumberRange
from decimal import Decimal
#pip install WTForm

app = Flask(__name__)
# DATABASE -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Database configuration
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
        return render_template("home.html", stock=stock, portfolio=portfolio)
    else:
        user = (
            User.query.with_entities(
                User.fullName,
                User.email,
                User.customerAccountNumber,
                User.availableFunds
            )
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
        return render_template("home.html", user=user, stock=stock)

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

#----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# CRUD FUNCTIONS - WORK IN PROGRESS
# CREATE USER -> CREATE CUSTOMER
#@app.route('/createaccount', methods=["GET", "POST"])
#def createaccount():
    #if request.method == "POST":
        #firstname = request.form.get("firstname", "").strip()
        #lastname = request.form.get("lastname", "").strip()
        #email = request.form.get("email", "").strip()
        #password = request.form.get("password", "")
        #confpassword = request.form.get("confpassword", "")

        #if not firstname or not lastname or not email or not password or not confpassword:
            #flash("All fields are required", "error")
            #return redirect(url_for("createaccount"))
        #if password != confpassword:
            #flash("Passwords do not match", "error")
            #return redirect(url_for("createaccount"))

        #fullname = f"{firstname} {lastname}".strip()
        # minimal, simple account number; consider a real generator later
        #account_number = uuid.uuid4().hex[:12].upper()

        #new_customer = Customer(
            #fullname=fullname,
            #email=email,
            #customerAccountNumber=account_number,
            #hashedPassword=password,   # TODO: replace with a real hash
            #availableFunds=0.0
        #)
        #db.session.add(new_customer)
        #db.session.commit()

        #flash("Account created successfully")
        #return redirect(url_for("signin"))
    #return render_template("createaccount.html")

# READ
#@app.route('/read_user/<int:user_id>')
#def read_user(user_id):
    #customer = Customer.query.get_or_404(user_id)
    #return f"Customer Details: ID: {customer.customerId}, Fullname: {customer.fullname}, Email: {customer.email}"

# UPDATE (update fullname & email)
#@app.route('/update_user/<int:user_id>/<path:fullname>/<path:email>')
#def update_user(user_id, fullname, email):
    #customer = Customer.query.get_or_404(user_id)
    #if not fullname or not email:
        #flash('Both fullname and email are required!', 'error')
        #return redirect(url_for('index'))

    #customer.fullname = fullname
    #customer.email = email

    #try:
        #db.session.commit()
        #flash(f'Customer {customer.customerId} updated successfully!', 'success')
    #except Exception as e:
        #db.session.rollback()
        #flash(f'Error updating customer: {str(e)}', 'error')
    #return redirect(url_for('index'))

# DELETE
#@app.route('/delete_user/<int:user_id>')
#def delete_user(user_id):
    #customer = Customer.query.get_or_404(user_id)
    #try:
        #db.session.delete(customer)
        #db.session.commit()
        #flash(f'Customer {customer.customerId} deleted successfully!', 'success')
    #except Exception as e:
        #db.session.rollback()
        #flash(f'Error deleting customer: {str(e)}', 'error')
    #return redirect(url_for('index'))

# ------------------------------------------------------------------------------------------------------

# Buy Stock Route; Need Logic
@app.route('/home/buystock', methods=['GET', 'POST'])
def buyStock():
    if request.method == "POST":
        # Read Sheet
        ticker = request.form.get("ticker")
        stock = StockInventory.query.filter_by(ticker=ticker).first()
        quantity = request.form.get("quantity")
        amt = stock.currentMktPrice * float(quantity)
        # Call Withdraw
        withdraw_action(amt, commit=False)
         # Update Order History
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
            createdAt = datetime.datetime.now(),
            updatedAt = datetime.datetime.now()
        )
        db.session.add(order)
        db.session.flush()
        # Update Portfolio
        portfolio = Portfolio(
            userId=current_user.userId,
            orderId= order.orderId,
            stockName=stock.name,
            ticker=stock.ticker,
            quantity=quantity,
            mktPrice=stock.currentMktPrice,
            createdAt = datetime.datetime.now(),
            updatedAt = datetime.datetime.now()
        )
        db.session.add(portfolio)
        db.session.commit()
        return redirect(url_for("home"))
    
    return render_template('buy_stock.html')

# Sell Stock Route; Need Logic
@app.route('/home/sellstock', methods=['GET', 'POST'])
def sellStock():
    if request.method == "POST":
        # Read Sheet
        ticker = request.form.get("ticker")
        stock = StockInventory.query.filter_by(ticker=ticker).first()
        quantity = request.form.get("quantity")
        amt = stock.currentMktPrice * float(quantity)
        # Call Deposit
        deposit_action(amt)
        # Update Order History
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
            createdAt = datetime.datetime.now(),
            updatedAt = datetime.datetime.now()
        )
        db.session.add(order)
        db.session.flush()
        # Update Portfolio
        portfolio = Portfolio(
            userId=current_user.userId,
            orderId= order.orderId,
            stockName=stock.name,
            ticker=stock.ticker,
            quantity=quantity,
            mktPrice=stock.currentMktPrice,
            createdAt = datetime.datetime.now(),
            updatedAt = datetime.datetime.now()
        )
        db.session.add(portfolio)
        db.session.flush()
        return redirect(url_for("home"))
    return render_template('sell_stock.html')

# Deposit Funds Route
@app.route('/home/deposit', methods=["GET", "POST"])
def depositFunds():
    if request.method == "POST":
        amt = request.form.get("amount")
        deposit_action(amt)
        # Call Portfolio for first transaction
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

# Stock page Route
@app.route('/home/stock', methods=['GET', 'POST'])
def stocks():
    return render_template("stock.html")

# Stock page Route - WORK IN PROGRESS
#form
class StockForm(FlaskForm):
    ticker = StringField("Ticker", validators=[DataRequired()])  # e.g., AAPL
    quantity = IntegerField("Quantity", validators=[DataRequired(), NumberRange(min=1)])
    avg_cost = DecimalField(
        "Average Cost",
        places=2,
        rounding=None,
        validators=[DataRequired(), NumberRange(min=0)]
    )
    submit = SubmitField("Add to Portfolio")

# live data yfinance
def get_live_price(symbol: str) -> Decimal:
    try:
        t = yf.Ticker(symbol.upper())
        fi = getattr(t, "fast_info", None)
        if fi and getattr(fi, "last_price", None) is not None:
            return Decimal(str(fi.last_price))
        hist = t.history(period="1d")
        if not hist.empty:
            return Decimal(str(float(hist["Close"].iloc[-1])))
    except Exception:
        pass
    return Decimal("0")


@app.route("/stock", methods=["GET", "POST"])
@login_required
def stock():
    form = StockForm()

    # Add info to form
    if form.validate_on_submit():
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

    # Rows for portfolio
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

    return render_template("stock.html", form=form, rows=rows, totals=totals)

# Create Stock Route
@app.route('/createstock', methods=["GET", "POST"])
@login_required
@admin_required
def createStock():
    if request.method == "POST":
        company = Company(
            name=request.form.get("companyName"),
            description=request.form.get("companyDesc"),
            stockTotalQty=request.form.get("totalQuantity"),
            ticker=request.form.get("ticker"),
            currentMktPrice=request.form.get("currentMktPrice"),
            createdAt=datetime.datetime.now(),
            updatedAt=datetime.datetime.now()
        )

        db.session.add(company)
        db.session.flush()

        stock = StockInventory(
            name=request.form.get("companyName"),
            companyId=company.companyId,
            adminId=current_user.adminId,
            ticker=request.form.get("ticker"),
            quantity=request.form.get("quantity"),
            initStockPrice=request.form.get("initStockPrice"),
            currentMktPrice=request.form.get("currentMktPrice"),
            createdAt = datetime.datetime.now(),
            updatedAt = datetime.datetime.now()
        )
        db.session.add(stock)
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("create_stock.html")

if __name__ == "__main__":
    app.run(debug=True)
