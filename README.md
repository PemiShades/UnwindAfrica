# 🌴 Unwind Africa

**Curated rest experiences across Africa** - A Django-powered platform for wellness tourism, event management, and community engagement.

![Django](https://img.shields.io/badge/Django-4.2-green.svg)
![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 📖 About

Unwind Africa is a comprehensive web platform that promotes rest, wellness, and mindful experiences across Africa. The platform features:

- **📝 Travel Blog** - Stories, guides, and wellness content
- **🎉 Event Management** - Curated rest experiences and wellness events
- **📦 Packages** - Customized travel and wellness packages
- **🗳️ Nominate to Unwind** - Community voting system with reward points
- **🎫 Rest Card System** - Membership rewards and exclusive benefits
- **💰 Payment Integration** - Secure payments via Paystack

---

## ✨ Key Features

### 1. **Content Management**
- Dynamic blog with categorization (Travel, Health, Wellness, etc.)
- Featured posts and content curation
- Rich media support for images and videos

### 2. **Event System**
- Event creation with fliers and thumbnails
- Date-based event management
- Badge system (Featured, Limited, Premium, etc.)

### 3. **Voting & Community Engagement**
- **Nominate to Unwind** monthly campaigns
- Multi-nominee voting with Paystack payment integration
- **Rest Points** reward system (earn ₦100 per vote by default)
- Real-time vote counting and leaderboards
- Referral tracking

### 4. **Rest Card Loyalty Program**
- Membership card system with unique card numbers
- Rest Points accumulation from voting
- Waitlist and activation management
- Status tracking (Waitlist → Active → Expired)

### 5. **Payment Processing**
- Paystack integration for secure payments
- Transaction tracking and verification
- Webhook support for automatic payment confirmation
- Support for both test and live environments

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- pip (Python package manager)
- Git
- Paystack account ([Sign up here](https://paystack.com))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/PemiShades/UnwindAfrica.git
   cd UnwindAfrica
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Activate (Windows)
   venv\Scripts\activate
   
   # Activate (Mac/Linux)
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env with your values
   # See SETUP_NOTES.txt for detailed instructions
   ```

5. **Configure your `.env` file**
   ```properties
   # Generate a secret key
   SECRET_KEY=your-secret-key-here
   
   DEBUG=true
   
   # Add your Paystack keys
   PAYSTACK_PUBLIC_KEY=pk_test_xxxxxxxxxxxxx
   PAYSTACK_SECRET_KEY=sk_test_xxxxxxxxxxxxx
   ```

6. **Run migrations**
   ```bash
   python manage.py migrate
   ```

7. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

8. **Run development server**
   ```bash
   python manage.py runserver
   ```

9. **Access the application**
   - Website: http://127.0.0.1:8000/
   - Admin Panel: http://127.0.0.1:8000/admin/

---

## 📁 Project Structure

```
UnwindAfrica/
├── config/              # Django settings and configuration
│   ├── settings.py      # Main settings file
│   ├── urls.py          # Root URL configuration
│   └── wsgi.py          # WSGI configuration
├── Web/                 # Main application
│   ├── models.py        # Database models (Post, Event, Vote, etc.)
│   ├── views.py         # View functions
│   ├── voting_views.py  # Voting system views
│   ├── admin.py         # Admin panel configuration
│   ├── urls.py          # App URL routing
│   ├── templates/       # HTML templates
│   └── migrations/      # Database migrations
├── dashboard/           # Admin dashboard app
├── static/              # Static files (CSS, JS, images)
├── media/               # User-uploaded files (gitignored)
├── .env.example         # Environment variables template
├── .gitignore           # Git ignore rules
├── requirements.txt     # Python dependencies
├── SETUP_NOTES.txt      # Detailed setup instructions
└── README.md            # This file
```

---

## 🗳️ Voting System

### How It Works

1. **Campaign Creation** (Admin)
   - Create a monthly campaign (e.g., "Nominate to Unwind – November 2025")
   - Set vote price (default: ₦500 per vote)
   - Set rest points per vote (default: ₦100)

2. **Nominee Addition** (Admin)
   - Add nominees with photos and stories
   - Set display order

3. **Voting Process** (Users)
   - Select nominee(s) and quantity of votes
   - Pay via Paystack
   - Earn Rest Points automatically
   - Votes counted after successful payment

4. **Rest Points Rewards**
   ```
   Rest Points = Number of Votes × Rest Points Per Vote
   Example: 5 votes × ₦100 = ₦500 Rest Points
   ```

### Testing Voting System

```bash
# Run the test suite
python test_voting_system.py
```

**Paystack Test Cards:**
- Success: `4084 0840 8408 4081`
- Any CVV and future expiry date

---

## 🔧 Configuration

### Database

**Local Development (Default - SQLite):**
```python
# No configuration needed
# Uses db.sqlite3 automatically
```

**Production (PostgreSQL):**
```bash
# In .env file:
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Or use individual variables:
DB_NAME=unwind_prod
DB_USER=unwind_user
DB_PASS=your-password
DB_HOST=127.0.0.1
DB_PORT=5432
```

### Paystack Setup

1. Sign up at [Paystack](https://paystack.com)
2. Get API keys from [Dashboard](https://dashboard.paystack.com/#/settings/developer)
3. Add to `.env`:
   ```properties
   # Test keys for development
   PAYSTACK_PUBLIC_KEY=pk_test_xxxxxxxxxxxxx
   PAYSTACK_SECRET_KEY=sk_test_xxxxxxxxxxxxx
   ```

---

## 🛠️ Development

### Running Tests
```bash
# Test voting system
python test_voting_system.py

# Run Django tests
python manage.py test
```

### Collecting Static Files
```bash
python manage.py collectstatic
```

### Creating Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

---

## 🔐 Security Notes

⚠️ **IMPORTANT:**
- Never commit `.env` to version control
- Use TEST Paystack keys for development
- Use LIVE Paystack keys only in production
- Keep `SECRET_KEY` secret and unique per environment
- Set `DEBUG=false` in production
- Review `ALLOWED_HOSTS` in `settings.py`

---

## 📄 Documentation

For detailed setup instructions, see [SETUP_NOTES.txt](SETUP_NOTES.txt)

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📧 Contact

- **Website:** [unwindafrica.com](https://unwindafrica.com)
- **Email:** contact@unwindafrica.com
- **GitHub:** [@PemiShades](https://github.com/PemiShades)

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- Django Framework
- Paystack Payment Gateway
- Bootstrap & TailwindCSS
- All contributors and supporters of Unwind Africa

---

**Made with ❤️ in Africa**
