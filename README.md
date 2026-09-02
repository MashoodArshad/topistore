Shah G Cap House
A Django e-commerce store for a local Islamic cap business in Pakistan. COD checkout, email order alerts, and a customer dashboard.

Live: https://shah-g-cap-house.onrender.com

Stack
Django 5.2 · PostgreSQL (Supabase) · Tailwind CSS · Resend API · Render

Features
Product catalog with stock tracking
Session-based cart
User auth with unique email validation
Login-required checkout with auto-filled billing
Async email notifications on new orders
Customer profile & order history
Custom 404/500 pages
Admin panel for product & order management
Run Locally
text

git clone https://github.com/MashoodArshad/topistore.git
cd topistore
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
Create .env:

text

SECRET_KEY=your-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1
DATABASE_URL=
RESEND_API_KEY=
text

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
TODO
Cloudinary/S3 for media storage
JazzCash/Easypaisa integration
Product search & filters
Mashood Arshad · mashoodarshad22@gmail.com
