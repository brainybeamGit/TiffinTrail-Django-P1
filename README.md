# TiffinTrail

TiffinTrail is a full-featured Django web platform for homemade meal delivery and tiffin subscription services. The platform bridges the gap between home-cooked food lovers and verified local home chefs, providing on-demand lunch and dinner delivery, flexible daily, weekly, and monthly meal subscription packages, integrated Razorpay digital payments and cash on delivery, dynamic promotional coupon discounts, real-time order lifecycle tracking, customer reviews, and dedicated multi-role portals for Customers, Home Chefs, and Platform Administrators.

## Project Features

- **Customer Management**: User registration, authentication, personal profile editing, multiple delivery addresses with default selection, and account security controls.
- **Home Chef Management**: Chef onboarding and registration, kitchen bio and profile presentation, cuisine specialization tags, working hours, service delivery areas, and FSSAI certificate document verification.
- **Admin Management & Moderation**: Superuser control center for verifying or rejecting chef applications, managing platform users, moderating customer reviews, resolving support complaints, and monitoring system audit activity logs.
- **Meal & Category Management**: Categorized homemade dish listings with dietary classification (Veg/Non-Veg), spice level, ingredients, allergen warnings, calorie count, preparation times, and stock availability toggles.
- **Subscription Plans**: Flexible daily, weekly, and monthly tiffin subscription packages with customizable meal slots (Lunch / Dinner), rotating menus, pausing, resuming, and cancellation workflows.
- **Cart & Checkout Experience**: Real-time shopping cart with quantity adjustments, single-kitchen ordering integrity, automated tax and delivery fee computation, and smooth checkout flow.
- **Coupon Management & Dynamic Promotional Descriptions**: Admin-managed promotional discount codes (percentage or fixed amount), order value thresholds, discount caps, expiry dates, and dynamic promotional descriptions rendered seamlessly on customer checkout cards.
- **Order Management & Tracking**: End-to-end order processing lifecycle covering status states: Pending, Confirmed, Preparing, Out for Delivery, Delivered, and Cancelled with customer cancellation rules.
- **Payment Processing**: Integrated Razorpay payment gateway for secure online card/UPI/net-banking transactions alongside Cash on Delivery (COD) options.
- **Customer Dashboard**: Centralized customer hub to view ongoing orders, active tiffin subscriptions, saved delivery addresses, order history, and submitted food reviews.
- **Chef Portal & Kitchen Dashboard**: Home chef workspace featuring real-time incoming order feeds, daily order item prep checklists, subscription subscriber lists, daily menu scheduling, dish catalog management, and earnings breakdowns.
- **Admin Analytics & Business Reports**: Executive overview cards showing total gross revenue, active subscriber counts, completed order tallies, printable invoice summaries, and downloadable CSV financial reports.
- **Reviews & Ratings**: Verified customer star ratings and textual reviews on individual meals and chef profiles with admin content moderation controls.
- **Notifications System**: In-app notifications for order updates, subscription lifecycle changes, kitchen approvals, and payout notices.
- **Customer Complaints & Support**: Ticket-based customer issue submission system with priority categorization, admin assignment, and resolution logging.

## Project Structure

```text
TiffinTrail/
├── manage.py
├── requirements.txt
├── db.sqlite3
├── TiffinTrail/
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── customer/
│   ├── migrations/
│   ├── templates/customer/
│   ├── context_processors.py
│   ├── forms.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   ├── views.py
│   └── management/
│       └── commands/
│           └── seed.py
├── chef/
│   ├── migrations/
│   ├── templates/chef/
│   ├── context_processors.py
│   ├── forms.py
│   ├── models.py
│   ├── urls.py
│   └── views.py
├── adminpanel/
│   ├── migrations/
│   ├── templates/adminpanel/
│   ├── context_processors.py
│   ├── forms.py
│   ├── models.py
│   ├── urls.py
│   └── views.py
├── scripts/
│   ├── seeds.py
├── static/
│   ├── css/
│   ├── js/
│   └── images/
└── media/
    ├── chefs/
    ├── meals/
    └── documents/
```

## Setup Commands

### Clone Repository

```bash
git clone https://github.com/your-username/TiffinTrail.git
cd TiffinTrail/TiffinTrail
```

### Installation on macOS/Linux

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Load database seed data
python docs/seeds.py

# Start development server
python manage.py runserver
```

### Installation on Windows

```powershell
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Load database seed data
python docs/seeds.py

# Start development server
python manage.py runserver
```

## LocalServer

http://127.0.0.1:8000/

## credentials

### Admin Account

User:- admin<br>
Email:- admin123@gmail.com<br>
Password:- admin123

### Chef Accounts

Chef 1 (Amrita Punjabi Rasoi):<br>
User:- amrita<br>
Email:- chef@example.com<br>
Password:- *(Configured via user registration or reset with `python manage.py changepassword amrita`)*

Chef 2 (Annapurna Ghar Ka Khana):<br>
User:- dklakum<br>
Email:- lakumdharmesh799@gmail.com<br>
Password:- *(Configured via user registration or reset with `python manage.py changepassword dklakum`)*

### Customer Account

User:- dk<br>
Email:- lakumdharmesh798@gmail.com<br>
Password:- *(Configured via user registration or reset with `python manage.py changepassword dk`)*

## Test User Credentials

| Role | Username | Password / Access |
|---|---|---|
| Superuser / Platform Admin | `admin` | `admin123` |
| Home Chef – Amrita Punjabi Rasoi | `amrita` | User Password *(or `manage.py changepassword amrita`)* |
| Home Chef – Annapurna Ghar Ka Khana | `dklakum` | User Password *(or `manage.py changepassword dklakum`)* |
| Customer Account | `dk` | User Password *(or `manage.py changepassword dk`)* |

## Screenshots

### 1. Customer Home Page
![Customer Home Page](docs/screenshots/customer-home.png)

### 2. Customer Login Page
![Customer Login Page](docs/screenshots/customer-login.png)

### 3. Chef Dashboard
![Chef Dashboard](docs/screenshots/chef-dashboard.png)

### 4. Admin Dashboard
![Admin Dashboard](docs/screenshots/admin-dashboard.png)


## Database Seeding

The project includes an idempotent database seeding script that populates all core production data:
- Superuser, Home Chef, and Customer user accounts.
- Customer profile with saved delivery address in Bengaluru.
- Home Chef profiles with kitchen verification details, addresses, and specialties in Ahmedabad.
- Regional Menu Categories: Gujarati Specials, Homestyle Thalis, Punjabi Delights, Rice & Biryani Bowls, and Healthy Meal Boxes.
- Signature homemade meals with pricing, photos, and allergen disclosures.
- Daily, Weekly, and Monthly tiffin subscription plans with meal schedules.
- Active coupon `FESTIVE50` with dynamic promotional description.
- Pre-populated customer orders, subscriptions, and platform notifications.

### Execution Methods

You can seed the database using either of the following commands:

**Method 1: Direct Script Runner**
```bash
python docs/seeds.py
```

**Method 2: Django Management Command**
```bash
python manage.py seed
```

## Static and Media Files

- **Static Files (`static/`)**: Contains global CSS stylesheets (`style.css`, `customer.css`, `chef.css`, `admin.css`), JavaScript modules, and platform brand logos.
- **Media Files (`media/`)**: Stores user-uploaded and seeded assets:
  - `media/chefs/`: Kitchen profile pictures and cover banners.
  - `media/chefs/documents/`: Chef verification documents (FSSAI licenses and kitchen proof).
  - `media/meals/`: High-resolution photographs for meal items and thalis.

In development mode (`DEBUG = True`), static and media files are served directly by Django via `urls.py`.

## Important Development Notes

- **Database Migrations**: Always execute migrations after model schema changes:
  ```bash
  python manage.py makemigrations
  python manage.py migrate
  ```
- **System Checks**: Run Django's built-in validation before committing code:
  ```bash
  python manage.py check
  ```
- **Automated Tests**: Execute the test suite to verify customer workflows, coupon calculations, and checkout features:
  ```bash
  python manage.py test customer.tests
  ```
- **Database Engine**: Uses SQLite (`db.sqlite3`) for development. For enterprise production, configure PostgreSQL by updating `DATABASES` in `TiffinTrail/settings.py`.
- **Payment Gateway Keys**: Razorpay test API keys (`RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`) are configured in `settings.py`. For live deployment, store these in secure environment variables.
- **Production Checklist**: Prior to production deployment, set `DEBUG = False`, configure specific `ALLOWED_HOSTS`, define a production-grade `SECRET_KEY`, and enable HTTPS security headers.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
