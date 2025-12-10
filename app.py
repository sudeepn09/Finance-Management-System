from datetime import datetime, date, timedelta
import random
import re
from decimal import Decimal, ROUND_HALF_UP

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///guru_finance.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


###########################################################
# Database Models
###########################################################


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_no = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    dob = db.Column(db.Date, nullable=True)
    mobile = db.Column(db.String(15), nullable=True)
    aadhar = db.Column(db.String(20), nullable=True)
    pan = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    opening_date = db.Column(db.Date, default=date.today)
    opening_balance = db.Column(db.Float, default=0.0)
    current_balance = db.Column(db.Float, default=0.0)

    def as_dict_basic(self):
        return {
            "account_no": self.account_no,
            "name": self.name,
            "mobile": self.mobile,
            "current_balance": self.current_balance,
        }


class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.String(20), unique=True, nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=True)
    account_no = db.Column(db.String(20), nullable=False)
    member_name = db.Column(db.String(120), nullable=False)
    date = db.Column(db.Date, default=date.today)
    loan_type = db.Column(db.String(20), nullable=False)  # Weekly / Monthly / Yearly / FD Loan
    principal = db.Column(db.Float, nullable=False)
    interest_rate = db.Column(db.Float, nullable=False)
    installments = db.Column(db.Integer, nullable=False)
    emi_amount = db.Column(db.Float, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    remarks = db.Column(db.Text, nullable=True)


class LoanTransaction(db.Model):
    """Per-loan EMI / interest / fine tracking."""
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey("loan.id"), nullable=False)
    date = db.Column(db.Date, default=date.today)
    txn_type = db.Column(db.String(20), nullable=False)  # EMI / INTEREST / FINE
    amount = db.Column(db.Float, nullable=False)
    remarks = db.Column(db.Text, nullable=True)


class Debit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(20), unique=True, nullable=False)
    date = db.Column(db.Date, default=date.today)
    account_no = db.Column(db.String(20), nullable=True)
    name = db.Column(db.String(120), nullable=True)
    debit_type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    mode = db.Column(db.String(20), nullable=False)  # Cash / Transfer / Other
    remarks = db.Column(db.Text, nullable=True)


class Credit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(20), unique=True, nullable=False)
    date = db.Column(db.Date, default=date.today)
    account_no = db.Column(db.String(20), nullable=True)
    name = db.Column(db.String(120), nullable=True)
    credit_type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    mode = db.Column(db.String(20), nullable=False)
    remarks = db.Column(db.Text, nullable=True)


class MiscExpense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    misc_id = db.Column(db.String(20), unique=True, nullable=False)
    date = db.Column(db.Date, default=date.today)
    head = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    remarks = db.Column(db.Text, nullable=True)


class FD(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fd_id = db.Column(db.String(20), unique=True, nullable=False)
    account_no = db.Column(db.String(20), nullable=False)
    member_name = db.Column(db.String(120), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    interest_rate = db.Column(db.Float, nullable=False)
    period_months = db.Column(db.Integer, nullable=False)
    maturity_date = db.Column(db.Date, nullable=False)
    maturity_amount = db.Column(db.Float, nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    is_closed = db.Column(db.Boolean, default=False)


class RD(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rd_id = db.Column(db.String(20), unique=True, nullable=False)
    account_no = db.Column(db.String(20), nullable=False)
    member_name = db.Column(db.String(120), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    installment_amount = db.Column(db.Float, nullable=False)
    period_months = db.Column(db.Integer, nullable=False)
    interest_rate = db.Column(db.Float, nullable=True)
    maturity_date = db.Column(db.Date, nullable=False)
    maturity_amount = db.Column(db.Float, nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    is_closed = db.Column(db.Boolean, default=False)


class RDInstallment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rd_id = db.Column(db.String(20), nullable=False)
    date = db.Column(db.Date, default=date.today)
    installment_no = db.Column(db.Integer, nullable=True)
    amount = db.Column(db.Float, nullable=False)
    remarks = db.Column(db.Text, nullable=True)


class Transaction(db.Model):
    """
    Simple SB transaction table used for /statement
    (your chosen Option 1).
    """
    __tablename__ = "transactions"
    id = db.Column(db.Integer, primary_key=True)
    account_no = db.Column(db.String(20), nullable=False)
    txn_date = db.Column(db.Date, default=date.today)
    type = db.Column(db.String(10), nullable=False)  # 'DEBIT' or 'CREDIT'
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255), nullable=True)


###########################################################
# Helper functions
###########################################################


def login_required(view_func):
    """Simple decorator to require login for protected routes."""
    from functools import wraps

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped


def generate_id(prefix: str) -> str:
    """Generate a short unique ID with prefix."""
    return f"{prefix}{int(datetime.utcnow().timestamp())}{random.randint(100, 999)}"


def generate_account_no() -> str:
    last_member = Member.query.order_by(Member.id.desc()).first()
    base = 10001
    if last_member:
        try:
            base = int(last_member.account_no) + 1
        except ValueError:
            base = last_member.id + 10001
    return str(base)


def create_default_admin():
    """Create a default admin user if not exists."""
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin")
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()


def send_sms(mobile: str, message: str) -> None:
    """SMS sending placeholder."""
    return None


def generate_captcha():
    """Generate a simple math captcha and store answer in session."""
    a = random.randint(1, 9)
    b = random.randint(1, 9)
    question = f"{a} + {b}"
    session["captcha_answer"] = str(a + b)
    return question


# -------- Money helpers (safe 2-decimal rounding) -------- #


def money(value) -> Decimal:
    """Return a Decimal rounded to 2 decimal places for money calculations."""
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def apply_credit_to_member(member: Member, amount: float) -> None:
    """Increase member.current_balance safely."""
    if member:
        current = money(member.current_balance)
        add = money(amount)
        member.current_balance = float(current + add)


def apply_debit_to_member(member: Member, amount: float) -> None:
    """Decrease member.current_balance safely."""
    if member:
        current = money(member.current_balance)
        sub = money(amount)
        member.current_balance = float(current - sub)


def create_sb_transaction(account_no: str, txn_date: date, txn_type: str,
                          amount: float, description: str = "") -> None:
    """
    Mirror ONLY SB activity (Member Received / Member Closed)
    into the `transactions` table so /statement shows correct running balance.
    """
    if not account_no or not amount:
        return
    t = Transaction(
        account_no=account_no,
        txn_date=txn_date,
        type=txn_type.upper(),
        amount=amount,
        description=description or "",
    )
    db.session.add(t)


def get_loan_outstanding(loan: Loan) -> float:
    """Principal outstanding = principal - sum(EMI payments)."""
    principal = float(loan.principal or 0.0)
    paid_principal = (
        db.session.query(db.func.coalesce(db.func.sum(LoanTransaction.amount), 0.0))
        .filter(LoanTransaction.loan_id == loan.id,
                LoanTransaction.txn_type == "EMI")
        .scalar()
    )
    outstanding = principal - float(paid_principal or 0.0)
    return max(outstanding, 0.0)


###########################################################
# Auth & Login
###########################################################


@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    captcha_question = session.get("captcha_question") or generate_captcha()
    session["captcha_question"] = captcha_question

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        captcha_input = request.form.get("captcha", "").strip()

        if captcha_input != session.get("captcha_answer"):
            error = "Invalid captcha. Please try again."
            captcha_question = generate_captcha()
            session["captcha_question"] = captcha_question
        else:
            user = User.query.filter_by(username=username).first()
            if not user or not user.check_password(password):
                error = "Invalid username or password."
                captcha_question = generate_captcha()
                session["captcha_question"] = captcha_question
            else:
                session["user_id"] = user.id
                session["username"] = user.username
                return redirect(url_for("dashboard"))

    return render_template("login.html", error=error, captcha_question=captcha_question)


@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


###########################################################
# Common layout helpers
###########################################################


@app.context_processor
def inject_now():
    """Inject common global variables into templates."""
    return {
        "now": datetime.utcnow(),
        "bank_name": "Shri Guru Finance Corporation Bhainakwadi (Sadalga)",
    }


@app.route("/search_member", methods=["GET"])
@login_required
def search_member():
    """Search member by account or mobile, used by header search bar (AJAX)."""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"success": False, "message": "No query"}), 400

    member = Member.query.filter(
        (Member.account_no == q) | (Member.mobile == q)
    ).first()
    if not member:
        return jsonify({"success": False, "message": "Member not found"}), 404

    return jsonify({"success": True, "member": member.as_dict_basic()})


@app.route("/api/member_name")
@login_required
def api_member_name():
    """Used for auto name in Loan / Debit / Credit when account no is entered."""
    account_no = request.args.get("account_no", "").strip()
    if not account_no:
        return jsonify({"success": False, "message": "Account number required"}), 400

    member = Member.query.filter_by(account_no=account_no).first()
    if not member:
        return jsonify({"success": False, "message": "Member not found"}), 404

    return jsonify({"success": True, "name": member.name})


###########################################################
# Dashboard & Core Modules
###########################################################


@app.route("/dashboard")
@login_required
def dashboard():
    member_count = Member.query.count()
    loan_count = Loan.query.count()
    total_credit = (
        db.session.query(db.func.coalesce(db.func.sum(Credit.amount), 0)).scalar()
    )
    total_debit = (
        db.session.query(db.func.coalesce(db.func.sum(Debit.amount), 0)).scalar()
    )
    return render_template(
        "dashboard.html",
        member_count=member_count,
        loan_count=loan_count,
        total_credit=total_credit,
        total_debit=total_debit,
    )


@app.route("/create_account", methods=["GET", "POST"])
@login_required
def create_account():
    """
    Create NEW member accounts only.
    No search / update / delete from this page.
    """
    if request.method == "POST":
        account_no = request.form.get("account_no") or generate_account_no()
        name = request.form.get("name")
        dob_str = request.form.get("dob")
        mobile = request.form.get("mobile", "").strip()
        aadhar = request.form.get("aadhar", "").strip()
        pan = request.form.get("pan", "").strip().upper()
        address = request.form.get("address")
        opening_date_str = request.form.get("opening_date")
        opening_balance = float(request.form.get("opening_balance") or 0.0)

        errors = []
        if not name:
            errors.append("Name is required.")
        if mobile and not re.fullmatch(r"\d{10}", mobile):
            errors.append("Mobile number must be exactly 10 digits.")
        if aadhar and not re.fullmatch(r"\d{12}", aadhar):
            errors.append("Aadhar number must be exactly 12 digits.")
        if pan and not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", pan):
            errors.append(
                "PAN must be 10 characters: first 5 capital letters, then 4 digits, last 1 capital letter."
            )

        dob = datetime.strptime(dob_str, "%Y-%m-%d").date() if dob_str else None
        opening_date = (
            datetime.strptime(opening_date_str, "%Y-%m-%d").date()
            if opening_date_str
            else date.today()
        )

        if Member.query.filter_by(account_no=account_no).first():
            errors.append("Account number already exists. Please try again.")

        if errors:
            for e in errors:
                flash(e, "danger")
        else:
            member = Member(
                account_no=account_no,
                name=name,
                dob=dob,
                mobile=mobile,
                aadhar=aadhar,
                pan=pan,
                address=address,
                opening_date=opening_date,
                opening_balance=opening_balance,
                current_balance=opening_balance,
            )
            db.session.add(member)

            # Opening balance as SB Received + SB transaction
            if opening_balance > 0:
                opening_credit = Credit(
                    transaction_id=generate_id("C"),
                    date=opening_date,
                    account_no=account_no,
                    name=name,
                    credit_type="SB Received",
                    amount=opening_balance,
                    mode="Cash",
                    remarks=f"Opening balance for account {account_no}",
                )
                db.session.add(opening_credit)
                create_sb_transaction(
                    account_no=account_no,
                    txn_date=opening_date,
                    txn_type="CREDIT",
                    amount=opening_balance,
                    description="SB Received - Opening Balance",
                )

            db.session.commit()
            flash("Member account created successfully.", "success")

            # after save, show next auto account_no
            return redirect(url_for("create_account"))

    # GET or after redirect – show fresh form with next account number
    default_account_no = generate_account_no()
    return render_template("create_account.html", default_account_no=default_account_no)


@app.route("/member", methods=["GET", "POST"])
@login_required
def member():
    found_member = None
    summary = {}
    member_loans = []

    if request.method == "POST":
        action = request.form.get("action")
        if action == "search":
            search_type = request.form.get("search_type")
            query = request.form.get("query", "").strip()

            q = None
            if search_type == "account_no":
                q = Member.query.filter_by(account_no=query).first()
            elif search_type == "name":
                q = Member.query.filter(
                    Member.name.ilike(f"%{query}%")
                ).first()
            elif search_type == "mobile":
                q = Member.query.filter_by(mobile=query).first()

            found_member = q
            if not found_member:
                flash("Member not found.", "warning")

        elif action == "update":
            account_no = request.form.get("account_no")
            found_member = Member.query.filter_by(account_no=account_no).first()
            if not found_member:
                flash("Member not found for update.", "danger")
            else:
                new_mobile = request.form.get("mobile", "").strip()
                if new_mobile and not re.fullmatch(r"\d{10}", new_mobile):
                    flash("Mobile number must be exactly 10 digits.", "danger")
                else:
                    found_member.address = request.form.get("address")
                    found_member.mobile = new_mobile
                    db.session.commit()
                    flash("Member updated successfully.", "success")

    # Also allow GET ?account_no=... to open directly
    if request.method == "GET":
        acc = request.args.get("account_no", "").strip()
        if acc:
            found_member = Member.query.filter_by(account_no=acc).first()
            if not found_member:
                flash("Member not found.", "warning")

    if found_member:
        # All loans for this member
        member_loans = (
            Loan.query.filter_by(account_no=found_member.account_no)
            .order_by(Loan.date.desc())
            .all()
        )
        total_outstanding = sum(get_loan_outstanding(l) for l in member_loans)

        summary = {
            "sb_balance": found_member.current_balance or 0.0,
            "loan_count": len(member_loans),
            "loan_outstanding": total_outstanding,
            "fd_count": FD.query.filter_by(
                account_no=found_member.account_no, is_closed=False
            ).count(),
            "rd_count": RD.query.filter_by(
                account_no=found_member.account_no, is_closed=False
            ).count(),
        }

    return render_template(
        "member.html",
        member=found_member,
        summary=summary,
        member_loans=member_loans,
    )


###########################################################
# Statement (SB)
###########################################################


@app.route("/statement")
@login_required
def statement():
    """
    SB account statement using `transactions` table
    (your chosen Option 1).
    """
    account_no = request.args.get("account_no", "").strip()
    if not account_no:
        flash("Account number is required.", "warning")
        return redirect(url_for("member"))

    member = Member.query.filter_by(account_no=account_no).first()
    if not member:
        flash("Member not found.", "danger")
        return redirect(url_for("member"))

    # Opening balance from member
    opening_balance = float(member.opening_balance or 0.0)
    running_balance = opening_balance

    # Fetch transactions for this account
    txns = (
        Transaction.query.filter_by(account_no=account_no)
        .order_by(Transaction.txn_date.asc(), Transaction.id.asc())
        .all()
    )

    rows = []
    total_debits = 0.0
    total_credits = 0.0

    for t in txns:
        t_type = (t.type or "").lower()
        amt = float(t.amount or 0.0)

        debit = 0.0
        credit = 0.0

        if t_type in ("debit", "d", "out"):
            debit = amt
            running_balance -= amt
            total_debits += amt
        else:
            credit = amt
            running_balance += amt
            total_credits += amt

        rows.append(
            {
                "date": t.txn_date,
                "description": t.description or "",
                "debit": debit,
                "credit": credit,
                "balance": running_balance,
                "mode": "",
                "remarks": "",
            }
        )

    closing_balance = running_balance

    return render_template(
        "statement.html",
        member=member,
        rows=rows,
        total_debits=total_debits,
        total_credits=total_credits,
        opening_balance=opening_balance,
        closing_balance=closing_balance,
    )


###########################################################
# Loan Module
###########################################################


@app.route("/loan", methods=["GET", "POST"])
@login_required
def loan():
    loans = []

    if request.method == "POST":
        action = request.form.get("action")
        if action == "save":
            account_no = request.form.get("account_no")
            member = Member.query.filter_by(account_no=account_no).first()
            if not member:
                flash("Member not found for given account number.", "danger")
            else:
                loan_type = request.form.get("loan_type")

                # ----- BLOCK MULTIPLE ACTIVE LOANS OF SAME TYPE -----
                existing_loans_same_type = Loan.query.filter_by(
                    account_no=account_no,
                    loan_type=loan_type,
                ).all()
                for old_loan in existing_loans_same_type:
                    outstanding = get_loan_outstanding(old_loan)
                    if outstanding > 0:
                        flash(
                            f"This member already has an active {loan_type} Loan "
                            f"(Loan ID: {old_loan.loan_id}). "
                            f"Please clear the old loan before issuing a new {loan_type} loan.",
                            "danger",
                        )
                        return redirect(url_for("loan"))

                # ----- Save new loan -----
                loan_id = generate_id("L")
                principal = float(request.form.get("principal") or 0.0)
                interest_rate = float(request.form.get("interest_rate") or 0.0)
                installments = int(request.form.get("installments") or 0)
                emi_amount = float(request.form.get("emi_amount") or 0.0)
                start_date_str = request.form.get("start_date")
                start_date = (
                    datetime.strptime(start_date_str, "%Y-%m-%d").date()
                    if start_date_str
                    else date.today()
                )
                end_date_str = request.form.get("end_date")
                if end_date_str:
                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                else:
                    if loan_type == "Weekly":
                        end_date = start_date + timedelta(weeks=installments)
                    else:
                        end_date = start_date + timedelta(days=30 * installments)

                remarks = request.form.get("remarks")

                new_loan = Loan(
                    loan_id=loan_id,
                    member_id=member.id,
                    account_no=member.account_no,
                    member_name=member.name,
                    loan_type=loan_type,
                    principal=principal,
                    interest_rate=interest_rate,
                    installments=installments,
                    emi_amount=emi_amount,
                    start_date=start_date,
                    end_date=end_date,
                    remarks=remarks,
                    date=start_date,
                )
                db.session.add(new_loan)

                # Create corresponding debit entry "Loan Given"
                loan_debit = Debit(
                    transaction_id=generate_id("D"),
                    date=start_date,
                    account_no=member.account_no,
                    name=member.name,
                    debit_type="Loan Given",
                    amount=principal,
                    mode="Cash",
                    remarks=f"Loan Given - {loan_id}",
                )
                db.session.add(loan_debit)

                db.session.commit()

                # Optional: SMS about loan creation
                if member.mobile:
                    msg = (
                        f"Shri Guru Finance: Rs {principal:.2f} LOAN SANCTIONED for A/c "
                        f"{member.account_no} on {start_date.isoformat()}. Loan ID: {loan_id}."
                    )
                    send_sms(member.mobile, msg)

                flash("Loan saved successfully.", "success")

    # GET: show latest 10 loans in table
    loans = Loan.query.order_by(Loan.date.desc(), Loan.id.desc()).limit(10).all()

    return render_template("loan.html", loans=loans)


###########################################################
# Debit & Credit Modules
###########################################################


@app.route("/debit", methods=["GET", "POST"])
@login_required
def debit():
    debits = Debit.query.order_by(Debit.date.desc(), Debit.id.desc()).limit(20).all()

    if request.method == "POST":
        transaction_id = generate_id("D")
        date_str = request.form.get("date")
        trx_date = (
            datetime.strptime(date_str, "%Y-%m-%d").date()
            if date_str else date.today()
        )

        account_no = request.form.get("account_no")
        member = (
            Member.query.filter_by(account_no=account_no).first()
            if account_no else None
        )
        if not member:
            flash("Valid member account is required for debit.", "danger")
            return render_template("debit.html", debits=debits)

        name = member.name
        debit_type = request.form.get("debit_type")
        amount = float(request.form.get("amount") or 0.0)
        mode = request.form.get("mode")
        remarks = request.form.get("remarks")

        # Save in Debit table
        new_debit = Debit(
            transaction_id=transaction_id,
            date=trx_date,
            account_no=account_no,
            name=name,
            debit_type=debit_type,
            amount=amount,
            mode=mode,
            remarks=remarks,
        )
        db.session.add(new_debit)

        # Update member SB balance
        apply_debit_to_member(member, amount)

        # 👉 SB statement: ONLY mirror "Member Closed"
        if debit_type == "Member Closed":
            create_sb_transaction(
                account_no=account_no,
                txn_date=trx_date,
                txn_type="DEBIT",
                amount=amount,
                description="Member Closed",
            )

        db.session.commit()

        # Optional SMS
        if member.mobile:
            msg = (
                f"Shri Guru Finance: Rs {amount:.2f} DEBITED from A/c {member.account_no} "
                f"on {trx_date.isoformat()} for {debit_type}."
            )
            send_sms(member.mobile, msg)

        flash("Debit transaction recorded.", "success")
        debits = Debit.query.order_by(Debit.date.desc(), Debit.id.desc()).limit(20).all()

    return render_template("debit.html", debits=debits)


@app.route("/credit", methods=["GET", "POST"])
@login_required
def credit():
    # Load recent 20 credits for the table
    credits = Credit.query.order_by(Credit.date.desc(), Credit.id.desc()).limit(20).all()

    if request.method == "POST":
        transaction_id = generate_id("C")
        date_str = request.form.get("date")
        trx_date = (
            datetime.strptime(date_str, "%Y-%m-%d").date()
            if date_str else date.today()
        )

        account_no = request.form.get("account_no")
        member = (
            Member.query.filter_by(account_no=account_no).first()
            if account_no else None
        )
        if not member:
            flash("Valid member account is required for credit.", "danger")
            return render_template("credit.html", credits=credits)

        name = member.name
        credit_type = request.form.get("credit_type")
        amount = float(request.form.get("amount") or 0.0)
        mode = request.form.get("mode")
        remarks = request.form.get("remarks")

        # Save in Credit table
        new_credit = Credit(
            transaction_id=transaction_id,
            date=trx_date,
            account_no=account_no,
            name=name,
            credit_type=credit_type,
            amount=amount,
            mode=mode,
            remarks=remarks,
        )
        db.session.add(new_credit)

        # ---------- SB BALANCE: ONLY for pure SB credits ----------
        # (Do NOT increase SB for EMI / Interest / Fine)
        if credit_type in ("Member Received", "SB Received"):
            apply_credit_to_member(member, amount)

        # 👉 SB statement: ONLY mirror "Member Received"
        if credit_type == "Member Received":
            create_sb_transaction(
                account_no=account_no,
                txn_date=trx_date,
                txn_type="CREDIT",
                amount=amount,
                description="Member Received",
            )

        # ---------- LOAN SIDE: map EMI / Interest / Fine to LoanTransaction ----------
        principal_types = {
            "Weekly Loan EMI Received": "Weekly",
            "Monthly Loan EMI Received": "Monthly",
            "Yearly Loan EMI Received": "Yearly",
            "FD Loan EMI Received": "FD Loan",
            "Loan EMI Received": None,  # any type
        }
        interest_types = {
            "Weekly Interest Received": "Weekly",
            "Monthly Interest Received": "Monthly",
            "Loan Interest Received": None,
        }
        fine_types = {
            "Fine Received": None,
            "Loan Fine Received": None,
        }

        loan = None
        txn_kind = None
        loan_type_filter = None

        if credit_type in principal_types:
            txn_kind = "EMI"
            loan_type_filter = principal_types[credit_type]
        elif credit_type in interest_types:
            txn_kind = "INTEREST"
            loan_type_filter = interest_types[credit_type]
        elif credit_type in fine_types:
            txn_kind = "FINE"
            loan_type_filter = fine_types[credit_type]

        if txn_kind:
            q = Loan.query.filter_by(account_no=account_no)
            if loan_type_filter:
                q = q.filter_by(loan_type=loan_type_filter)
            # latest loan of that type for this member
            loan = q.order_by(Loan.date.desc(), Loan.id.desc()).first()

            if loan:
                lt = LoanTransaction(
                    loan_id=loan.id,
                    date=trx_date,
                    txn_type=txn_kind,
                    amount=amount,
                    remarks=remarks or credit_type,
                )
                db.session.add(lt)
            # if no loan found, we just keep Credit entry as normal

        db.session.commit()

        # Optional SMS
        if member.mobile:
            msg = (
                f"Shri Guru Finance: Rs {amount:.2f} CREDITED to A/c {member.account_no} "
                f"on {trx_date.isoformat()} for {credit_type}."
            )
            send_sms(member.mobile, msg)

        flash("Credit transaction recorded.", "success")
        credits = Credit.query.order_by(
            Credit.date.desc(), Credit.id.desc()
        ).limit(20).all()

    return render_template("credit.html", credits=credits)



###########################################################
# Miscellaneous
###########################################################


@app.route("/misc", methods=["GET", "POST"])
@login_required
def misc():
    expenses = (
        MiscExpense.query.order_by(MiscExpense.date.desc(), MiscExpense.id.desc())
        .limit(20)
        .all()
    )
    if request.method == "POST":
        misc_id = generate_id("M")
        date_str = request.form.get("date")
        exp_date = (
            datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
        )
        head = request.form.get("head")
        amount = float(request.form.get("amount") or 0.0)
        remarks = request.form.get("remarks")

        expense = MiscExpense(
            misc_id=misc_id,
            date=exp_date,
            head=head,
            amount=amount,
            remarks=remarks,
        )
        db.session.add(expense)
        db.session.commit()
        flash("Miscellaneous expense recorded.", "success")
        expenses = (
            MiscExpense.query.order_by(MiscExpense.date.desc(), MiscExpense.id.desc())
            .limit(20)
            .all()
        )

    return render_template("misc.html", expenses=expenses)


###########################################################
# FD & RD Modules
###########################################################


@app.route("/fd", methods=["GET", "POST"])
@login_required
def fd():
    fds = FD.query.order_by(FD.start_date.desc()).limit(20).all()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "open":
            fd_id = generate_id("FD")
            account_no = request.form.get("account_no")
            member = Member.query.filter_by(account_no=account_no).first()
            if not member:
                flash("Member not found for FD.", "danger")
            else:
                start_date_str = request.form.get("start_date")
                start_date = (
                    datetime.strptime(start_date_str, "%Y-%m-%d").date()
                    if start_date_str
                    else date.today()
                )
                amount = float(request.form.get("amount") or 0.0)
                interest_rate = float(request.form.get("interest_rate") or 0.0)
                period_months = int(request.form.get("period_months") or 0)
                remarks = request.form.get("remarks")

                maturity_date = start_date + timedelta(days=30 * period_months)
                maturity_amount = amount * (
                    1 + interest_rate / 100 * period_months / 12
                )

                fd_obj = FD(
                    fd_id=fd_id,
                    account_no=member.account_no,
                    member_name=member.name,
                    start_date=start_date,
                    amount=amount,
                    interest_rate=interest_rate,
                    period_months=period_months,
                    maturity_date=maturity_date,
                    maturity_amount=maturity_amount,
                    remarks=remarks,
                )
                db.session.add(fd_obj)
                db.session.commit()
                flash("FD opened successfully.", "success")

        elif action == "close":
            fd_id = request.form.get("fd_id")
            amount_paid = float(request.form.get("amount_paid") or 0.0)
            close_date_str = request.form.get("close_date")
            close_date = (
                datetime.strptime(close_date_str, "%Y-%m-%d").date()
                if close_date_str
                else date.today()
            )
            fd_obj = FD.query.filter_by(fd_id=fd_id).first()
            if not fd_obj:
                flash("FD not found.", "danger")
            else:
                fd_obj.is_closed = True

                # principal part
                principal_debit = Debit(
                    transaction_id=generate_id("D"),
                    date=close_date,
                    account_no=fd_obj.account_no,
                    name=fd_obj.member_name,
                    debit_type="FD Close",
                    amount=fd_obj.amount,
                    mode="Cash",
                    remarks=f"FD Close {fd_obj.fd_id}",
                )

                # interest part
                interest_amount = max(amount_paid - fd_obj.amount, 0)
                interest_debit = Debit(
                    transaction_id=generate_id("D"),
                    date=close_date,
                    account_no=fd_obj.account_no,
                    name=fd_obj.member_name,
                    debit_type="FD Interest Closed",
                    amount=interest_amount,
                    mode="Cash",
                    remarks=f"FD Interest Close {fd_obj.fd_id}",
                )

                db.session.add(principal_debit)
                if interest_amount > 0:
                    db.session.add(interest_debit)

                # Update SB balance – BUT DO NOT mirror to SB statement
                member = Member.query.filter_by(account_no=fd_obj.account_no).first()
                if member:
                    apply_debit_to_member(member, fd_obj.amount + interest_amount)

                db.session.commit()
                flash("FD closed and debit entries created.", "success")

        fds = FD.query.order_by(FD.start_date.desc()).limit(20).all()

    return render_template("fd.html", fds=fds)


@app.route("/rd", methods=["GET", "POST"])
@login_required
def rd():
    rds = RD.query.order_by(RD.start_date.desc()).limit(20).all()
    installments = []
    if request.method == "POST":
        action = request.form.get("action")
        if action == "open":
            rd_id = generate_id("RD")
            account_no = request.form.get("account_no")
            member = Member.query.filter_by(account_no=account_no).first()
            if not member:
                flash("Member not found for RD.", "danger")
            else:
                start_date_str = request.form.get("start_date")
                start_date = (
                    datetime.strptime(start_date_str, "%Y-%m-%d").date()
                    if start_date_str
                    else date.today()
                )
                installment_amount = float(
                    request.form.get("installment_amount") or 0.0
                )
                period_months = int(request.form.get("period_months") or 0)
                interest_rate = float(request.form.get("interest_rate") or 0.0)
                remarks = request.form.get("remarks")

                maturity_date = start_date + timedelta(days=30 * period_months)
                total_principal = installment_amount * period_months
                maturity_amount = total_principal * (
                    1 + interest_rate / 100 * period_months / 12
                )

                rd_obj = RD(
                    rd_id=rd_id,
                    account_no=member.account_no,
                    member_name=member.name,
                    start_date=start_date,
                    installment_amount=installment_amount,
                    period_months=period_months,
                    interest_rate=interest_rate,
                    maturity_date=maturity_date,
                    maturity_amount=maturity_amount,
                    remarks=remarks,
                )
                db.session.add(rd_obj)
                db.session.commit()
                flash("RD opened successfully.", "success")

        elif action == "installment":
            rd_id = request.form.get("rd_id")
            rd_obj = RD.query.filter_by(rd_id=rd_id).first()
            if not rd_obj:
                flash("RD not found for installment.", "danger")
            else:
                date_str = request.form.get("date")
                inst_date = (
                    datetime.strptime(date_str, "%Y-%m-%d").date()
                    if date_str
                    else date.today()
                )
                amount = float(
                    request.form.get("amount") or rd_obj.installment_amount
                )
                last_inst = (
                    RDInstallment.query.filter_by(rd_id=rd_id)
                    .order_by(RDInstallment.installment_no.desc())
                    .first()
                )
                next_no = (last_inst.installment_no + 1) if last_inst else 1
                inst = RDInstallment(
                    rd_id=rd_id,
                    date=inst_date,
                    installment_no=next_no,
                    amount=amount,
                    remarks=request.form.get("remarks"),
                )
                db.session.add(inst)
                db.session.commit()
                flash("RD installment recorded.", "success")

        elif action == "close":
            rd_id = request.form.get("rd_id_close")
            amount_paid = float(request.form.get("amount_paid") or 0.0)
            close_date_str = request.form.get("close_date")
            close_date = (
                datetime.strptime(close_date_str, "%Y-%m-%d").date()
                if close_date_str
                else date.today()
            )
            rd_obj = RD.query.filter_by(rd_id=rd_id).first()
            if not rd_obj:
                flash("RD not found to close.", "danger")
            else:
                rd_obj.is_closed = True
                principal_amount = rd_obj.installment_amount * rd_obj.period_months

                principal_debit = Debit(
                    transaction_id=generate_id("D"),
                    date=close_date,
                    account_no=rd_obj.account_no,
                    name=rd_obj.member_name,
                    debit_type="RD Close",
                    amount=principal_amount,
                    mode="Cash",
                    remarks=f"RD Close {rd_obj.rd_id}",
                )

                interest_amount = max(amount_paid - principal_amount, 0)
                interest_debit = Debit(
                    transaction_id=generate_id("D"),
                    date=close_date,
                    account_no=rd_obj.account_no,
                    name=rd_obj.member_name,
                    debit_type="RD Interest Closed",
                    amount=interest_amount,
                    mode="Cash",
                    remarks=f"RD Interest Close {rd_obj.rd_id}",
                )

                db.session.add(principal_debit)
                if interest_amount > 0:
                    db.session.add(interest_debit)

                # Update SB balance – BUT DO NOT mirror to SB statement
                member = Member.query.filter_by(account_no=rd_obj.account_no).first()
                if member:
                    apply_debit_to_member(member, principal_amount + interest_amount)

                db.session.commit()
                flash("RD closed and debit entries created.", "success")

        rds = RD.query.order_by(RD.start_date.desc()).limit(20).all()

    return render_template("rd.html", rds=rds, installments=installments)


###########################################################
# Section Statements (Debit / Credit / Loan / Misc / FD / RD)
###########################################################


def parse_date_or_none(value: str):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


@app.route("/debit_statement")
@login_required
def debit_statement():
    from_date = parse_date_or_none(request.args.get("from_date"))
    to_date = parse_date_or_none(request.args.get("to_date"))

    q = Debit.query
    if from_date:
        q = q.filter(Debit.date >= from_date)
    if to_date:
        q = q.filter(Debit.date <= to_date)

    debits = q.order_by(Debit.date.asc(), Debit.id.asc()).all()
    return render_template(
        "debit_statement.html",
        debits=debits,
        from_date=from_date,
        to_date=to_date,
    )


@app.route("/credit/statement", methods=["GET"])
@login_required
def credit_statement():
    """
    Credit statement with optional FROM / TO date filter.
    Opens from Credit page 'View Statement' button.
    """
    from_date_str = request.args.get("from_date", "").strip()
    to_date_str = request.args.get("to_date", "").strip()

    from_date = None
    to_date = None

    if from_date_str:
        try:
            from_date = datetime.strptime(from_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid From date.", "warning")

    if to_date_str:
        try:
            to_date = datetime.strptime(to_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid To date.", "warning")

    query = Credit.query

    if from_date:
        query = query.filter(Credit.date >= from_date)
    if to_date:
        query = query.filter(Credit.date <= to_date)

    credits = query.order_by(Credit.date.asc(), Credit.id.asc()).all()

    return render_template(
        "credit_statement.html",
        credits=credits,
        from_date=from_date,
        to_date=to_date,
    )


@app.route("/loan_statement")
@login_required
def loan_statement():
    from_date = parse_date_or_none(request.args.get("from_date"))
    to_date = parse_date_or_none(request.args.get("to_date"))
    account_no = request.args.get("account_no", "").strip() or None

    q = Loan.query
    if from_date:
        q = q.filter(Loan.date >= from_date)
    if to_date:
        q = q.filter(Loan.date <= to_date)
    if account_no:
        q = q.filter(Loan.account_no == account_no)

    loans = q.order_by(Loan.date.asc(), Loan.id.asc()).all()

    return render_template(
        "loan_statement.html",
        loans=loans,
        from_date=from_date,
        to_date=to_date,
        account_no=account_no or "",
    )


@app.route("/misc_statement")
@login_required
def misc_statement():
    from_date = parse_date_or_none(request.args.get("from_date"))
    to_date = parse_date_or_none(request.args.get("to_date"))

    q = MiscExpense.query
    if from_date:
        q = q.filter(MiscExpense.date >= from_date)
    if to_date:
        q = q.filter(MiscExpense.date <= to_date)

    expenses = q.order_by(MiscExpense.date.asc(), MiscExpense.id.asc()).all()
    return render_template(
        "misc_statement.html",
        expenses=expenses,
        from_date=from_date,
        to_date=to_date,
    )


@app.route("/fd_statement")
@login_required
def fd_statement():
    from_date = parse_date_or_none(request.args.get("from_date"))
    to_date = parse_date_or_none(request.args.get("to_date"))

    q = FD.query
    if from_date:
        q = q.filter(FD.start_date >= from_date)
    if to_date:
        q = q.filter(FD.start_date <= to_date)

    fds = q.order_by(FD.start_date.asc(), FD.id.asc()).all()
    return render_template(
        "fd_statement.html",
        fds=fds,
        from_date=from_date,
        to_date=to_date,
    )


@app.route("/rd_statement")
@login_required
def rd_statement():
    from_date = parse_date_or_none(request.args.get("from_date"))
    to_date = parse_date_or_none(request.args.get("to_date"))

    q = RD.query
    if from_date:
        q = q.filter(RD.start_date >= from_date)
    if to_date:
        q = q.filter(RD.start_date <= to_date)

    rds = q.order_by(RD.start_date.asc(), RD.id.asc()).all()
    return render_template(
        "rd_statement.html",
        rds=rds,
        from_date=from_date,
        to_date=to_date,
    )


###########################################################
# Member Loan Statement (single loan)
###########################################################


@app.route("/member_loan_statement/<loan_id>")
@login_required
def member_loan_statement(loan_id):
    """
    Single-loan statement:
    - First: Loan Given
    - Then: EMI / Interest / Fine from LoanTransaction
    - EMI reduces outstanding
    - Interest & Fine do NOT reduce outstanding
    - Rows are shown in DESCENDING date order
    """
    loan = Loan.query.filter_by(loan_id=loan_id).first_or_404()
    member = Member.query.filter_by(account_no=loan.account_no).first()

    principal = float(loan.principal or 0.0)

    # All loan transactions, oldest first (for correct running balance)
    txns = (
        LoanTransaction.query.filter_by(loan_id=loan.id)
        .order_by(LoanTransaction.date.asc(), LoanTransaction.id.asc())
        .all()
    )

    events = []

    # Start with Loan Given
    loan_date = loan.date or loan.start_date or loan.start_date
    outstanding = principal
    events.append({
        "date": loan_date,
        "type": "Loan Given",
        "amount": principal,
        "remaining": outstanding,
    })

    total_emi = 0.0
    total_interest = 0.0
    total_fine = 0.0

    # Then each EMI / INTEREST / FINE
    for t in txns:
        amt = float(t.amount or 0.0)
        label = ""
        if t.txn_type == "EMI":
            label = "EMI Received"
            total_emi += amt
            outstanding -= amt
            if outstanding < 0:
                outstanding = 0.0
        elif t.txn_type == "INTEREST":
            label = "Interest Received"
            total_interest += amt
            # outstanding not changed
        elif t.txn_type == "FINE":
            label = "Fine Received"
            total_fine += amt
            # outstanding not changed
        else:
            label = t.txn_type or "Other"

        events.append({
            "date": t.date,
            "type": label,
            "amount": amt,
            "remaining": outstanding,
        })

    # Final outstanding after all EMIs
    final_outstanding = outstanding

    # Show most recent first (DESC by date)
    rows = sorted(
        events,
        key=lambda r: (r["date"] or date.min),
        reverse=True,
    )

    return render_template(
        "member_loan_statement.html",
        loan=loan,
        member=member,
        rows=rows,
        total_emi=total_emi,
        total_interest=total_interest,
        total_fine=total_fine,
        outstanding=final_outstanding,
    )



###########################################################
# Loan Calculator & Monthly Report
###########################################################


@app.route("/loan_calculator")
@login_required
def loan_calculator():
    return render_template("loan_calculator.html")


def week_index_for_day(day: int) -> int:
    """Return week index (1-4) based on day of month."""
    if 1 <= day <= 10:
        return 1
    if 11 <= day <= 17:
        return 2
    if 18 <= day <= 24:
        return 3
    return 4


@app.route("/monthly_report", methods=["GET", "POST"])
@login_required
def monthly_report():
    selected_month = datetime.today().month
    selected_year = datetime.today().year

    if request.method == "POST":
        selected_month = int(request.form.get("month") or selected_month)
        selected_year = int(request.form.get("year") or selected_year)

    start_date = date(selected_year, selected_month, 1)
    if selected_month == 12:
        next_month = date(selected_year + 1, 1, 1)
    else:
        next_month = date(selected_year, selected_month + 1, 1)
    end_date = next_month - timedelta(days=1)

    debit_heads = [
        "Loan Given",
        "FD Close",
        "RD Close",
        "SB Close",
        "Miscellaneous",
        "Member Closed",
        "FD Interest Closed",
        "RD Interest Closed",
    ]

    credit_heads = [
        "SB Received",
        "FD Received",
        "RD Received",
        "Weekly Loan EMI Received",
        "Monthly Loan EMI Received",
        "Yearly Loan EMI Received",
        "FD Loan EMI Received",
        "Bond Charges",
        "Building Fund",
        "Fine Received",
        "Weekly Interest Received",
        "Monthly Interest Received",
        "Loan Interest Received",
        "Miscellaneous Credit",
        "Member Received",
    ]

    debit_data = {head: [0, 0, 0, 0] for head in debit_heads}
    credit_data = {head: [0, 0, 0, 0] for head in credit_heads}

    debits = Debit.query.filter(Debit.date >= start_date, Debit.date <= end_date).all()
    for d in debits:
        idx = week_index_for_day(d.date.day) - 1
        if d.debit_type in debit_data:
            debit_data[d.debit_type][idx] += d.amount

    expenses = MiscExpense.query.filter(
        MiscExpense.date >= start_date, MiscExpense.date <= end_date
    ).all()
    for e in expenses:
        idx = week_index_for_day(e.date.day) - 1
        debit_data["Miscellaneous"][idx] += e.amount

    credits = Credit.query.filter(
        Credit.date >= start_date, Credit.date <= end_date
    ).all()
    for c in credits:
        idx = week_index_for_day(c.date.day) - 1
        if c.credit_type in credit_data:
            credit_data[c.credit_type][idx] += c.amount

    weekly_debit_totals = [sum(week) for week in zip(*debit_data.values())]
    weekly_credit_totals = [sum(week) for week in zip(*credit_data.values())]
    total_debit = sum(weekly_debit_totals)
    total_credit = sum(weekly_credit_totals)
    profit_this_month = total_credit - total_debit

    last_month_profit = 0
    cumulative_profit = profit_this_month

    return render_template(
        "monthly_report.html",
        month=selected_month,
        year=selected_year,
        debit_heads=debit_heads,
        credit_heads=credit_heads,
        debit_data=debit_data,
        credit_data=credit_data,
        weekly_debit_totals=weekly_debit_totals,
        weekly_credit_totals=weekly_credit_totals,
        total_debit=total_debit,
        total_credit=total_credit,
        profit_this_month=profit_this_month,
        last_month_profit=last_month_profit,
        cumulative_profit=cumulative_profit,
        start_date=start_date,
        end_date=end_date,
    )


###########################################################
# Settings
###########################################################


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        section = request.form.get("section")
        if section == "password":
            old_password = request.form.get("old_password")
            new_password = request.form.get("new_password")
            confirm_password = request.form.get("confirm_password")
            user = User.query.get(session["user_id"])
            if not user or not user.check_password(old_password):
                flash("Old password is incorrect.", "danger")
            elif new_password != confirm_password:
                flash("New password and confirmation do not match.", "danger")
            else:
                user.set_password(new_password)
                db.session.commit()
                flash("Password updated successfully.", "success")

    return render_template("settings.html")


###########################################################
# CLI helper to initialize / clear DB
###########################################################


@app.cli.command("init-db")
def init_db_command():
    """Initialize the database and create an admin user."""
    db.create_all()
    create_default_admin()
    print("Initialized the database and ensured default admin user.")


@app.cli.command("clear-db")
def clear_db_command():
    """Clear all data from the database (keeps admin user)."""
    RDInstallment.query.delete()
    RD.query.delete()
    FD.query.delete()
    MiscExpense.query.delete()
    Credit.query.delete()
    Debit.query.delete()
    LoanTransaction.query.delete()
    Loan.query.delete()
    Transaction.query.delete()
    Member.query.delete()
    User.query.filter(User.username != "admin").delete()
    db.session.commit()
    print("All database data cleared successfully. Admin user preserved.")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        create_default_admin()
    app.run(debug=True)
