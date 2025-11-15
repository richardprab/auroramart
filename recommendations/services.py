import joblib
import os
import pandas as pd
from django.apps import apps
from products.models import Product, Category


# Load models once at module level
try:
    app_path = apps.get_app_config('recommendations').path
    model_path = os.path.join(app_path, 'mlmodels', 'b2c_customers_100.joblib')
    customer_model = joblib.load(model_path)
    model_path = os.path.join(app_path, 'mlmodels', 'b2c_products_500_transactions_50k.joblib')
    association_rules = joblib.load(model_path)
except Exception as e:
    customer_model = None
    association_rules = None


class CustomerCategoryPredictor:
    """Predicts preferred product category based on customer demographics"""
    
    @staticmethod
    def predict(user):
        """
        Predict preferred category for a user.
        Returns category name as string.
        """
        if customer_model is None:
            raise ValueError("ML model not loaded. Please check model files.")
        features = CustomerCategoryPredictor._prepare_features(user)
        prediction = customer_model.predict(features)
        return prediction[0]
    
    @staticmethod
    def _prepare_features(user):
        """Convert user data to model input format"""
        from accounts.models import Customer
        
        # Ensure user is a Customer instance
        # Since AUTH_USER_MODEL is Customer, user is usually a Customer instance
        if not isinstance(user, Customer):
            # Fallback to defaults if not a customer (edge case: staff/superuser)
            user = None
        
        if user is None:
            # Return default values if user is not a customer
            user_age = 35
            user_gender = 'Male'
            user_employment = 'Full-time'
            user_occupation = 'Service'
            user_education = 'Bachelor'
            user_household_size = 2
            user_has_children = False
            user_monthly_income = 5000.0
        else:
            user_age = user.age if user.age else 35
            user_gender = user.gender or 'Male'
            user_employment = user.employment_status or 'Full-time'
            user_occupation = user.occupation or 'Service'
            user_education = user.education or 'Bachelor'
            user_household_size = user.household_size if user.household_size is not None else 2
            user_has_children = user.has_children is True
            user_monthly_income = float(user.monthly_income_sgd) if user.monthly_income_sgd else 5000.0
        
        data = {
            'age': user_age,
            'household_size': user_household_size,
            'has_children': 1 if user_has_children else 0,
            'monthly_income_sgd': user_monthly_income,
        }
        
        # Add one-hot encoded gender
        data['gender_Female'] = 1 if user_gender == 'Female' else 0
        data['gender_Male'] = 1 if user_gender == 'Male' else 0
        
        # Add one-hot encoded employment status
        data['employment_status_Full-time'] = 1 if user_employment == 'Full-time' else 0
        data['employment_status_Part-time'] = 1 if user_employment == 'Part-time' else 0
        data['employment_status_Retired'] = 1 if user_employment == 'Retired' else 0
        data['employment_status_Self-employed'] = 1 if user_employment == 'Self-employed' else 0
        data['employment_status_Student'] = 1 if user_employment == 'Student' else 0
        
        # Add one-hot encoded occupation
        occupations = ['Admin', 'Education', 'Sales', 'Service', 'Skilled Trades', 'Tech']
        for occ in occupations:
            data[f'occupation_{occ}'] = 1 if user_occupation == occ else 0
        
        # Add one-hot encoded education
        educations = ['Bachelor', 'Diploma', 'Doctorate', 'Master', 'Secondary']
        for edu in educations:
            data[f'education_{edu}'] = 1 if user_education == edu else 0
        
        return pd.DataFrame([data])


class ProductRecommender:
    """Recommends products based on association rules (market basket analysis)"""
    
    @staticmethod
    def _extract_skus(input_data):
        """
        Extract SKU codes from various input types.
        
        Args:
            input_data: Can be:
                - Product object (uses all variant SKUs or product SKU)
                - List/QuerySet of cart items (extracts SKUs from items)
                - List/string of SKU codes
                - List of Product objects (extracts SKUs)
        
        Returns:
            List of SKU codes
        """
        from products.models import ProductVariant
        
        skus = []
        
        # Handle Product object
        if isinstance(input_data, Product):
            variant_skus = list(input_data.variants.filter(is_active=True).values_list('sku', flat=True))
            skus = variant_skus if variant_skus else [input_data.sku]
        
        # Handle cart items (CartItem objects)
        elif hasattr(input_data, '__iter__') and not isinstance(input_data, str):
            # Check if it's cart items (has product_variant or product attribute)
            first_item = next(iter(input_data), None) if hasattr(input_data, '__iter__') else None
            if first_item and (hasattr(first_item, 'product_variant') or hasattr(first_item, 'product')):
                for item in input_data:
                    if hasattr(item, 'product_variant') and item.product_variant:
                        skus.append(item.product_variant.sku)
                    elif hasattr(item, 'product') and item.product:
                        skus.append(item.product.sku)
            # Handle list of Product objects
            elif first_item and isinstance(first_item, Product):
                for product in input_data:
                    variant_skus = list(product.variants.filter(is_active=True).values_list('sku', flat=True))
                    if variant_skus:
                        skus.extend(variant_skus)
                    else:
                        skus.append(product.sku)
            # Handle list of SKU strings
            else:
                for item in input_data:
                    if isinstance(item, str):
                        skus.append(item)
        
        # Handle single SKU string
        elif isinstance(input_data, str):
            skus = [input_data]
        
        return skus
    
    @staticmethod
    def _get_recommended_skus(product_skus, metric='confidence', top_n=5):
        """
        Core method: Get recommended SKU codes based on association rules.
        
        Args:
            product_skus: List of SKU codes
            metric: 'confidence', 'lift', or 'support'
            top_n: Number of recommendations to return
            
        Returns:
            List of recommended SKU codes
        """
        if not product_skus or association_rules is None:
            return []
        
        recommendations = set()
        
        for sku in product_skus:
            matched_rules = association_rules[
                association_rules['antecedents'].apply(lambda x: sku in x)
            ]
            
            if not matched_rules.empty:
                top_rules = matched_rules.sort_values(by=metric, ascending=False).head(top_n)
                
                for _, row in top_rules.iterrows():
                    recommendations.update(row['consequents'])
        
        # Remove items already in the input
        recommendations.difference_update(product_skus)
        
        return list(recommendations)[:top_n]
    
    @staticmethod
    def _skus_to_products(recommended_skus, exclude_product_id=None, top_n=5):
        """
        Convert SKU codes to Product objects.
        Handles both variant SKUs and product SKUs.
        
        Args:
            recommended_skus: List of SKU codes
            exclude_product_id: Product ID to exclude from results
            top_n: Maximum number of products to return
            
        Returns:
            List of Product objects
        """
        if not recommended_skus:
            return []
        
        variant_products = Product.objects.filter(
            variants__sku__in=recommended_skus,
            is_active=True
        ).distinct().select_related('category')
        
        if exclude_product_id:
            variant_products = variant_products.exclude(id=exclude_product_id)
        
        # Also try matching by product SKU (for products without variants)
        product_skus_query = Product.objects.filter(
            sku__in=recommended_skus,
            is_active=True
        )
        
        if exclude_product_id:
            product_skus_query = product_skus_query.exclude(id=exclude_product_id)
        
        # Combine and deduplicate
        all_products = list(variant_products) + [
            p for p in product_skus_query.select_related('category') 
            if p not in variant_products
        ]
        
        return all_products[:top_n]
    
    @staticmethod
    def get_recommendations(input_data, metric='confidence', top_n=5, exclude_product_id=None, return_skus=False):
        """
        Unified method to get product recommendations.
        Accepts various input types and returns Product objects (or SKUs if requested).
        
        Args:
            input_data: Can be:
                - Product object
                - List/QuerySet of cart items
                - List/string of SKU codes
                - List of Product objects
            metric: 'confidence', 'lift', or 'support' (default: 'confidence')
            top_n: Number of recommendations (default: 5)
            exclude_product_id: Product ID to exclude from results (optional)
            return_skus: If True, returns SKU codes instead of Product objects (default: False)
            
        Returns:
            List of Product objects (or SKU codes if return_skus=True)
        
        Examples:
            # From a product
            ProductRecommender.get_recommendations(product, top_n=5)
            
            # From cart items
            ProductRecommender.get_recommendations(cart_items, top_n=5)
            
            # From SKU codes
            ProductRecommender.get_recommendations(['SKU001', 'SKU002'], top_n=5)
            
            # Get SKU codes only
            ProductRecommender.get_recommendations(product, return_skus=True)
        """
        # Extract SKUs from input
        input_skus = ProductRecommender._extract_skus(input_data)
        
        if not input_skus:
            return [] if not return_skus else []
        
        # Get recommended SKUs
        # For product input, get more recommendations to account for filtering
        multiplier = 2 if isinstance(input_data, Product) else 1
        recommended_skus = ProductRecommender._get_recommended_skus(
            input_skus, 
            metric=metric, 
            top_n=top_n * multiplier
        )
        
        if return_skus:
            return recommended_skus[:top_n]
        
        # Convert to Product objects
        # If input is a Product, exclude it from results
        if isinstance(input_data, Product):
            exclude_id = exclude_product_id or input_data.id
        else:
            exclude_id = exclude_product_id
        
        return ProductRecommender._skus_to_products(
            recommended_skus, 
            exclude_product_id=exclude_id,
            top_n=top_n
        )


class PersonalizedRecommendations:
    """Combines both models for personalized product recommendations"""
    
    @staticmethod
    def get_for_user(user, limit=10):
        """
        Get personalized product recommendations for a user.
        Uses ML model prediction as primary method, with category filtering as fallback.
        """
        if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
            return Product.objects.filter(
                is_active=True,
                variants__is_active=True
            ).distinct().order_by('-rating', '-created_at')[:limit]
        
        # PRIORITY 1: Use ML model to predict category based on demographics
        # Check if user is a Customer with demographic data
        # Since AUTH_USER_MODEL is Customer, user is usually a Customer instance
        from accounts.models import Customer
        customer = user if isinstance(user, Customer) else None
        
        if customer and customer.age and customer.gender:
            try:
                predicted_category_name = CustomerCategoryPredictor.predict(customer)
                
                # Map ML model predictions to database category names
                # The ML model might predict different names than what's in the database
                category_name_mapping = {
                    'Electronics': 'Electronics',
                    'Fashion - Men': 'Fashion - Men',
                    'Fashion - Women': 'Fashion - Women',
                    "Men's Fashion": 'Fashion - Men',
                    "Women's Fashion": 'Fashion - Women',
                    'Home & Kitchen': 'Home & Kitchen',
                    'Beauty & Personal Care': 'Beauty & Personal Care',
                    'Sports & Outdoors': 'Sports & Outdoors',
                    'Books': 'Books',
                    'Groceries & Gourmet': 'Groceries & Gourmet',
                    'Pet Supplies': 'Pet Supplies',
                    'Automotive': 'Automotive',
                    'Toys & Games': 'Toys & Games',
                    'Health': 'Health',
                }
                
                # Map the predicted name to database name
                mapped_category_name = category_name_mapping.get(predicted_category_name, predicted_category_name)
                
                # Try to find the category (exact match, then case-insensitive, then partial)
                predicted_category = Category.objects.filter(name=mapped_category_name, is_active=True).first()
                
                if not predicted_category:
                    predicted_category = Category.objects.filter(
                        name__iexact=mapped_category_name, 
                        is_active=True
                    ).first()
                
                if not predicted_category and mapped_category_name:
                    # Try partial match on first word
                    first_word = mapped_category_name.split()[0] if mapped_category_name.split() else mapped_category_name
                    predicted_category = Category.objects.filter(
                        name__icontains=first_word,
                        is_active=True
                    ).first()
                
                if predicted_category:
                    # Get all category IDs to search (parent + all children/subcategories)
                    category_ids = [predicted_category.id]
                    if predicted_category.children.exists():
                        category_ids.extend(
                            predicted_category.children.values_list('id', flat=True)
                        )
                    
                    products = Product.objects.filter(
                        category_id__in=category_ids,
                        is_active=True
                    ).order_by('-rating', '-created_at')[:limit]
                    
                    product_list = list(products)
                    if product_list:
                        return product_list
            except Exception:
                pass
        
        # # PRIORITY 2: Use user's manually selected preferred category as fallback
        # # COMMENTED OUT: Preferred category is redundant - ML model should be primary
        # if user.preferred_category:
        #     # Get all category IDs to search (parent + all children/subcategories)
        #     category_ids = [user.preferred_category.id]
        #     if user.preferred_category.children.exists():
        #         category_ids.extend(
        #             user.preferred_category.children.values_list('id', flat=True)
        #         )
        #     
        #     products = Product.objects.filter(
        #         category_id__in=category_ids,
        #         is_active=True
        #     ).order_by('-rating', '-created_at')[:limit]
        #     
        #     product_list = list(products)
        #     if product_list:
        #         return product_list
        
        # FINAL FALLBACK: Featured products
        return list(Product.objects.filter(
            is_active=True,
            variants__is_active=True
        ).distinct().order_by('-rating', '-created_at')[:limit])
