from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey # Allows you to attach db-level foreign-key to a column
from datetime import datetime # For createdAt/updatedAt date/time
import uuid # Generates unique identifiers (See "Account number" in CRUD)

app = Flask(__name__)
bootstrap = Bootstrap5(app)

# ------------------------------------------------------------------------------------------------------
# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Sandwich13!!!@localhost/sts_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key'

# Initialize database
db = SQLAlchemy(app)

# ================================
# MODELS
# ================================

# ---- Customer (ERD) ----
class Customer(db.Model):
    customerId = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    customerAccountNumber = db.Column(db.String(32), unique=True, nullable=False)
    hashedPassword = db.Column(db.String(255), nullable=False) # Storing plain text, not currently secure, Switch to hashing with Werkzeud before using in a signin route
    availableFunds = db.Column(db.Float, default=0.0, nullable=False)
    createdAt = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updatedAt = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

def __repr__(self):
    return f"<Customer {self.customerId} {self.fullname}>"

# ---- Administrator ----
class Admin(db.Model):
    __tablename__ = "administrator"
    administratorId = db.Column(db.Integer, primary_key=True)  # PK
    fullname = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    hashedPassword = db.Column(db.String(255), nullable=False)
    createdAt = db.Column(db.String(25))
    updatedAt = db.Column(db.String(25))

    def __repr__(self):
        return f"<Admin {self.administratorId} {self.fullname}>"

# ---- FinancialTransaction (ERD) ----
class FinancialTransaction(db.Model):
    financialTransactionId = db.Column(db.Integer, primary_key=True)  # PK
    # FKs (Each financial transaction row must point to a valid customer via account number, company, and order)
    customerAccountNumber = db.Column(db.String(32), ForeignKey("customer.customerAccountNumber"))
    companyId = db.Column(db.Integer, ForeignKey("company.companyId"))
    orderId = db.Column(db.Integer, ForeignKey("order_history.orderId"))
    # Attributes
    amount = db.Column(db.Float)
    type = db.Column(db.String(4))  # BUY/SELL
    createdAt = db.Column(db.String(25))

# ---- OrderHistory (ERD) ----
class OrderHistory(db.Model):
    __tablename__ = "order_history"
    orderId = db.Column(db.Integer, primary_key=True)  # PK
    # FKs (link to Customer per "Has many OrderHistory via customerId")
    stockId = db.Column(db.Integer, ForeignKey("stock_inventory.stockId"))
    administratorId = db.Column(db.Integer, ForeignKey("administrator.administratorId"))
    customerId = db.Column(db.Integer, ForeignKey("customer.customerId"))
    # Attributes
    type = db.Column(db.String(4))  # BUY/SELL
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float)
    totalValue = db.Column(db.Float)
    status = db.Column(db.String(6))  # OPEN, CANCEL, CLOSE
    companyName = db.Column(db.String(120))
    ticker = db.Column(db.String(16))
    createdAt = db.Column(db.String(25))
    updatedAt = db.Column(db.String(25))

# ---- Portfolio ----
class Portfolio(db.Model):
    portfolioId = db.Column(db.Integer, primary_key=True)  # PK
    # FKs (Each portfolio is tied to a customer and potentially an order)
    customerId = db.Column(db.Integer, ForeignKey("customer.customerId"))
    orderId = db.Column(db.Integer, ForeignKey("order_history.orderId"))
    # Attributes
    stockName = db.Column(db.String(120))
    stockTicker = db.Column(db.String(16))
    quantity = db.Column(db.Float)
    currentMarketPrice = db.Column(db.Float)
    createdAt = db.Column(db.String(25))
    updatedAt = db.Column(db.String(25))

# ---- StockInventory ----
class StockInventory(db.Model):
    __tablename__ = "stock_inventory"
    stockId = db.Column(db.Integer, primary_key=True)  # PK
    # FKs (Each stock entry belongs to a company and is managed by an admin)
    companyId = db.Column(db.Integer, ForeignKey("company.companyId"))
    administratorId = db.Column(db.Integer, ForeignKey("administrator.administratorId"))
    # Attributes
    name = db.Column(db.String(120))
    ticker = db.Column(db.String(16))
    quantity = db.Column(db.Float)
    initStockPrice = db.Column(db.Float)
    currentMarketPrice = db.Column(db.Float)
    createdAt = db.Column(db.String(25))
    updatedAt = db.Column(db.String(25))

# ---- Company ----
class Company(db.Model):
    companyId = db.Column(db.Integer, primary_key=True)  # PK
    name = db.Column(db.String(120))
    description = db.Column(db.String(255))
    stockTotalQuantity = db.Column(db.Float)
    ticker = db.Column(db.String(16))
    currentMarketPrice = db.Column(db.Float)
    createdAt = db.Column(db.String(25))
    updatedAt = db.Column(db.String(25))

# ---- Exception ----
class Exception(db.Model):
    __tablename__ = "exception"
    exceptionId = db.Column(db.Integer, primary_key=True)  # PK
    # FK (Exception is linked to an administrator)
    administratorId = db.Column(db.Integer, ForeignKey("administrator.administratorId"))
    # Attributes
    reason = db.Column(db.String(255))
    holidayDate = db.Column(db.String(25))
    createdAt = db.Column(db.String(25))
    updatedAt = db.Column(db.String(25))

# ---- WorkingDay ----
class WorkingDay(db.Model):
    workingDayId = db.Column(db.Integer, primary_key=True)  # PK
    # FK (WorkingDay is linked to an administrator)
    administratorId = db.Column(db.Integer, ForeignKey("administrator.administratorId"))
    # Attributes
    dayOfWeek = db.Column(db.String(3))
    startTime = db.Column(db.String(25))
    endTime = db.Column(db.String(25))
    createdAt = db.Column(db.String(25))
    updatedAt = db.Column(db.String(25))

# Create tables
with app.app_context():
    db.create_all()

# ------------------------------------------------------------------------------------------------------
# CRUD FUNCTIONS
# CREATE USER -> CREATE CUSTOMER
@app.route('/createaccount', methods=["GET", "POST"])
def createaccount():
    if request.method == "POST":
        firstname = request.form.get("firstname", "").strip()
        lastname = request.form.get("lastname", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confpassword = request.form.get("confpassword", "")

        if not firstname or not lastname or not email or not password or not confpassword:
            flash("All fields are required", "error")
            return redirect(url_for("createaccount"))
        if password != confpassword:
            flash("Passwords do not match", "error")
            return redirect(url_for("createaccount"))

        fullname = f"{firstname} {lastname}".strip()
        # minimal, simple account number; consider a real generator later
        account_number = uuid.uuid4().hex[:12].upper()

        new_customer = Customer(
            fullname=fullname,
            email=email,
            customerAccountNumber=account_number,
            hashedPassword=password,   # TODO: replace with a real hash
            availableFunds=0.0
        )
        db.session.add(new_customer)
        db.session.commit()

        flash("Account created successfully")
        return redirect(url_for("signin"))
    return render_template("createaccount.html")

# READ
@app.route('/read_user/<int:user_id>')
def read_user(user_id):
    customer = Customer.query.get_or_404(user_id)
    return f"Customer Details: ID: {customer.customerId}, Fullname: {customer.fullname}, Email: {customer.email}"

# UPDATE (update fullname & email)
@app.route('/update_user/<int:user_id>/<path:fullname>/<path:email>')
def update_user(user_id, fullname, email):
    customer = Customer.query.get_or_404(user_id)
    if not fullname or not email:
        flash('Both fullname and email are required!', 'error')
        return redirect(url_for('index'))

    customer.fullname = fullname
    customer.email = email

    try:
        db.session.commit()
        flash(f'Customer {customer.customerId} updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating customer: {str(e)}', 'error')
    return redirect(url_for('index'))

# DELETE
@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    customer = Customer.query.get_or_404(user_id)
    try:
        db.session.delete(customer)
        db.session.commit()
        flash(f'Customer {customer.customerId} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting customer: {str(e)}', 'error')
    return redirect(url_for('index'))

# ------------------------------------------------------------------------------------------------------
# ROUTES
@app.route("/")
def index():
    customers = Customer.query.all()
    return render_template("index.html", users=customers)

@app.route("/signin")
def signin():
    return render_template("signin.html")

@app.route("/stock")
def stock():
    return render_template("stock.html")

if __name__ == "__main__":
    app.run(debug=True)
