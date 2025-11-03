# AuroraMart API Documentation

## Overview
AuroraMart has been converted to use Django REST Framework with JWT authentication. The API provides RESTful endpoints for all e-commerce functionality.

## Authentication

### JWT Token Authentication
The API uses JWT (JSON Web Tokens) for authentication. Tokens are required for protected endpoints.

#### Obtain Token
```bash
POST /api/auth/token/
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}

Response:
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

#### Refresh Token
```bash
POST /api/auth/token/refresh/
Content-Type: application/json

{
  "refresh": "your_refresh_token"
}

Response:
{
  "access": "new_access_token"
}
```

#### Using Tokens
Include the access token in the Authorization header:
```
Authorization: Bearer your_access_token
```

## API Endpoints

### Authentication & User Management

#### Register New User
```
POST /api/auth/register/
```
Body:
```json
{
  "username": "newuser",
  "email": "user@example.com",
  "password": "securepassword",
  "password_confirm": "securepassword",
  "first_name": "John",
  "last_name": "Doe"
}
```

#### Get/Update User Profile
```
GET /api/auth/profile/
PATCH /api/auth/profile/
```

### Products

#### List Products
```
GET /api/products/
```
Query parameters:
- `category`: Filter by category ID
- `is_trending`: true/false
- `is_bestseller`: true/false
- `search`: Search in name, description, SKU
- `ordering`: created_at, -created_at, rating, -rating

#### Get Product Detail
```
GET /api/products/{slug}/
```

#### Get Product Variants
```
GET /api/products/{slug}/variants/
```

#### Get Product Reviews
```
GET /api/products/{slug}/reviews/
```

### Categories

#### List Categories
```
GET /api/categories/
```

#### Get Category with Products
```
GET /api/categories/{slug}/products/
```

### Cart

#### Get Cart
```
GET /api/cart/
```

#### Add Item to Cart
```
POST /api/cart/add_item/
```
Body:
```json
{
  "product_id": 1,
  "product_variant_id": 5,
  "quantity": 1
}
```

#### Update Cart Item
```
PATCH /api/cart/update_item/
```
Body:
```json
{
  "item_id": 10,
  "quantity": 3
}
```

#### Remove Item from Cart
```
DELETE /api/cart/remove_item/
```
Body:
```json
{
  "item_id": 10
}
```

#### Get Cart Count
```
GET /api/cart/count/
```

#### Clear Cart
```
DELETE /api/cart/clear/
```

### Wishlist (Authentication Required)

#### List Wishlist
```
GET /api/wishlist/
```

#### Add to Wishlist
```
POST /api/wishlist/add_product/
```
Body:
```json
{
  "product_id": 1,
  "product_variant_id": 5
}
```

#### Remove from Wishlist
```
DELETE /api/wishlist/remove_product/
```
Body:
```json
{
  "product_id": 1
}
```

### Orders (Authentication Required)

#### List Orders
```
GET /api/orders/
```

#### Get Order Detail
```
GET /api/orders/{id}/
```

#### Create Order from Cart
```
POST /api/orders/
```
Body:
```json
{
  "address_id": 5,
  "payment_method": "credit_card",
  "contact_number": "+1234567890",
  "customer_notes": "Please deliver before 5 PM"
}
```

#### Cancel Order
```
POST /api/orders/{id}/cancel/
```

### Addresses (Authentication Required)

#### List Addresses
```
GET /api/addresses/
```

#### Create Address
```
POST /api/addresses/
```
Body:
```json
{
  "full_name": "John Doe",
  "address_type": "shipping",
  "address_line1": "123 Main St",
  "city": "New York",
  "state": "NY",
  "zip_code": "10001",
  "country": "USA"
}
```

### Notifications (Authentication Required)

#### List Notifications
```
GET /api/notifications/
```

#### Mark Notification as Read
```
POST /api/notifications/{id}/mark_read/
```

#### Mark All as Read
```
POST /api/notifications/mark_all_read/
```

#### Get Unread Count
```
GET /api/notifications/unread_count/
```

### Reviews

#### List Reviews
```
GET /api/reviews/?product_id={id}
```

#### Create Review
```
POST /api/reviews/
```
Body:
```json
{
  "product": 1,
  "rating": 5,
  "title": "Great product!",
  "comment": "Really happy with this purchase."
}
```

## Frontend Integration

### JavaScript JWT Helper
The `static/js/auth.js` file provides JWT token management:

```javascript
// Check if authenticated
if (JWTAuth.isAuthenticated()) {
    // User is logged in
}

// Get auth headers for API calls
const headers = {
    'Content-Type': 'application/json',
    ...JWTAuth.getAuthHeaders()
};

// Make authenticated request
JWTAuth.authFetch('/api/orders/', {
    method: 'GET'
}).then(response => response.json())
  .then(data => console.log(data));
```

### Cart Integration
The cart automatically uses JWT tokens when available:

```javascript
// Cart operations work for both authenticated and anonymous users
CartModule.addToCart(productId, button);
CartModule.updateCartCount();
```

## Setup Instructions

### 1. Install Dependencies
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Migrations
```bash
python manage.py migrate
```

### 3. Create Superuser (Optional)
```bash
python manage.py createsuperuser
```

### 4. Run Development Server
```bash
python manage.py runserver
```

### 5. Access API
- Browse API: http://127.0.0.1:8000/api/
- Admin: http://127.0.0.1:8000/admin/
- Main Site: http://127.0.0.1:8000/

## Testing API Endpoints

### Using cURL
```bash
# Get products
curl http://127.0.0.1:8000/api/products/

# Login
curl -X POST http://127.0.0.1:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}'

# Use token
curl http://127.0.0.1:8000/api/orders/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Using Browsable API
Django REST Framework provides a browsable API interface. Simply visit any API endpoint in your browser while logged in.

## Configuration

### CORS Settings
For production, update `CORS_ALLOW_ALL_ORIGINS` in `settings.py`:

```python
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "https://yourdomain.com",
    "https://www.yourdomain.com",
]
```

### JWT Settings
Token lifetimes can be configured in `settings.py`:

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}
```

## Key Features

✅ **JWT Authentication** - Secure token-based authentication  
✅ **RESTful API** - Standard HTTP methods and status codes  
✅ **Pagination** - Automatic pagination for list views  
✅ **Filtering & Search** - Query parameters for filtering products  
✅ **Browsable API** - Interactive API explorer for development  
✅ **CORS Support** - Cross-origin resource sharing enabled  
✅ **Anonymous Cart** - Cart works for both logged-in and guest users  
✅ **Backward Compatible** - Traditional Django views still work  

## Migration Notes

### What Changed
- Added DRF ViewSets and serializers for all models
- JWT authentication replaces session-based auth for API
- All API endpoints under `/api/` prefix
- Frontend JavaScript updated to use API endpoints
- Traditional Django views kept for backward compatibility

### Breaking Changes
- Cart endpoints moved from `/cart/` to `/api/cart/`
- Authentication now requires JWT tokens for API calls
- JavaScript must include JWT tokens in headers

### Migration Checklist
- [x] Install DRF and JWT packages
- [x] Create serializers for all models
- [x] Create API ViewSets
- [x] Set up URL routing
- [x] Update frontend JavaScript
- [x] Test key endpoints

## Troubleshooting

### Import Errors
If you see "rest_framework" import errors, ensure packages are installed:
```bash
pip install -r requirements.txt
```

### Token Expired
Access tokens expire after 1 hour. Use the refresh token to get a new access token.

### CORS Errors
Check `CORS_ALLOW_ALL_ORIGINS` setting or add your domain to `CORS_ALLOWED_ORIGINS`.

## Next Steps

1. **Test all API endpoints** - Use Postman or cURL
2. **Update frontend forms** - Convert login/register forms to use API
3. **Add API documentation** - Consider using drf-spectacular for OpenAPI docs
4. **Security hardening** - Review CORS and JWT settings for production
5. **Deploy** - Configure for production environment

## Support

For questions or issues, refer to:
- Django REST Framework docs: https://www.django-rest-framework.org/
- Simple JWT docs: https://django-rest-framework-simplejwt.readthedocs.io/
