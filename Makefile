.PHONY: help install migrate migrations superuser run test clean resetdb shell collectstatic

# Default target
help:
	@echo "AuroraMart - Available Commands:"
	@echo "================================="
	@echo "make install       - Install dependencies from requirements.txt"
	@echo "make migrations    - Create new migrations"
	@echo "make migrate       - Apply migrations to database"
	@echo "make superuser     - Create a superuser"
	@echo "make run           - Run development server"
	@echo "make test          - Run tests"
	@echo "make shell         - Open Django shell"
	@echo "make clean         - Remove Python cache files"
	@echo "make resetdb       - Delete database and recreate (WARNING: destroys data!)"
	@echo "make collectstatic - Collect static files"
	@echo "make check         - Run system checks"

# Install dependencies
install:
	@echo "Installing dependencies..."
	pip install --upgrade pip
	pip install -r requirements.txt
	@echo "✅ Dependencies installed successfully!"

# Create migrations for all apps (in dependency order)
migrations:
	@echo "Creating migrations..."
	python manage.py makemigrations products
	python manage.py makemigrations accounts
	python manage.py makemigrations chat
	python manage.py makemigrations cart
	python manage.py makemigrations orders
	python manage.py makemigrations notifications
	python manage.py makemigrations adminpanel
	@echo "✅ Migrations created successfully!"

# Apply migrations
migrate:
	@echo "Applying migrations..."
	python manage.py migrate
	@echo "✅ Migrations applied successfully!"

# Create superuser
superuser:
	@echo "Creating superuser..."
	python manage.py createsuperuser

# Run development server
run:
	@echo "Starting development server..."
	@echo "Server will be available at: http://127.0.0.1:8000"
	python manage.py runserver

# Run tests
test:
	@echo "Running tests..."
	python manage.py test

# Open Django shell
shell:
	@echo "Opening Django shell..."
	python manage.py shell

# System check
check:
	@echo "Running system checks..."
	python manage.py check
	@echo "✅ No issues found!"

# Collect static files
collectstatic:
	@echo "Collecting static files..."
	python manage.py collectstatic --noinput
	@echo "✅ Static files collected!"

# Clean Python cache
clean:
	@echo "Cleaning Python cache files..."
	find . -type d -name __pycache__ -not -path "./venv/*" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -not -path "./venv/*" -delete
	find . -type f -name "*.pyo" -not -path "./venv/*" -delete
	find . -type f -name ".DS_Store" -delete
	@echo "✅ Cache cleaned!"

# Reset database (DANGER!)
resetdb:
	@echo "⚠️  WARNING: This will delete your database!"
	@echo "⚠️  Press Ctrl+C to cancel, or Enter to continue..."
	@read -r dummy
	@echo "Deleting database..."
	rm -f db.sqlite3
	@echo "Deleting migration files..."
	find . -path "*/migrations/*.py" -not -name "__init__.py" -not -path "./venv/*" -delete
	find . -path "*/migrations/*.pyc" -not -path "./venv/*" -delete
	@echo "Cleaning cache..."
	$(MAKE) clean
	@echo "Creating fresh migrations..."
	$(MAKE) migrations
	@echo "Applying migrations..."
	$(MAKE) migrate
	@echo "✅ Database reset complete!"
	@echo "Don't forget to run: make superuser"

# Full setup for new developers
setup: install migrations migrate
	@echo "✅ Setup complete!"
	@echo "Run 'make superuser' to create an admin user"
	@echo "Run 'make run' to start the development server"

# Quick reset and run (for development)
dev-reset: resetdb superuser run