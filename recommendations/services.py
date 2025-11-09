import joblib
import os
import pandas as pd
from django.apps import apps
from products.models import Product, Category


# Load models once at module level
app_path = apps.get_app_config('recommendations').path
model_path = os.path.join(app_path, 'mlmodels', 'b2c_customers_100.joblib')
customer_model = joblib.load(model_path)
model_path = os.path.join(app_path, 'mlmodels', 'b2c_products_500_transactions_50k.joblib')
association_rules = joblib.load(model_path)


class CustomerCategoryPredictor:
    """Predicts preferred product category based on customer demographics"""
    
    @staticmethod
    def predict(user):
        """
        Predict preferred category for a user.
        Returns category name as string.
        """
        features = CustomerCategoryPredictor._prepare_features(user)
        prediction = customer_model.predict(features)
        return prediction[0]
    
    @staticmethod
    def _prepare_features(user):
        """Convert user data to model input format"""
        data = {
            'age': CustomerCategoryPredictor._estimate_age(user.age_range),
            'household_size': user.household_size or 2,
            'has_children': 1 if user.has_children else 0,
            'monthly_income_sgd': CustomerCategoryPredictor._estimate_income(user.income_range),
        }
        
        # Add one-hot encoded gender
        gender_value = user.gender or 'Male'
        data['gender_Female'] = 1 if gender_value == 'Female' else 0
        data['gender_Male'] = 1 if gender_value == 'Male' else 0
        
        # Add one-hot encoded employment status
        employment = user.employment or 'Full-time'
        data['employment_status_Full-time'] = 1 if employment == 'Full-time' else 0
        data['employment_status_Part-time'] = 1 if employment == 'Part-time' else 0
        data['employment_status_Retired'] = 1 if employment == 'Retired' else 0
        data['employment_status_Self-employed'] = 1 if employment == 'Self-employed' else 0
        data['employment_status_Student'] = 1 if employment == 'Student' else 0
        
        # Add one-hot encoded occupation
        occupation = user.occupation or 'Service'
        occupations = ['Admin', 'Education', 'Sales', 'Service', 'Skilled Trades', 'Tech']
        for occ in occupations:
            data[f'occupation_{occ}'] = 1 if occupation == occ else 0
        
        # Add one-hot encoded education
        education = user.education or 'Bachelor'
        educations = ['Bachelor', 'Diploma', 'Doctorate', 'Master', 'Secondary']
        for edu in educations:
            data[f'education_{edu}'] = 1 if education == edu else 0
        
        return pd.DataFrame([data])
    
    @staticmethod
    def _estimate_age(age_range):
        """Convert age range to midpoint"""
        mapping = {
            '18-24': 21,
            '25-34': 29,
            '35-44': 39,
            '45-54': 49,
            '55-64': 59,
            '65+': 67,
        }
        return mapping.get(age_range, 35)
    
    @staticmethod
    def _estimate_income(income_range):
        """Convert income range to estimated value"""
        mapping = {
            'Under $2000': 1500,
            '$2000-$4999': 3500,
            '$5000-$7999': 6500,
            '$8000-$11999': 10000,
            '$12000+': 15000,
        }
        return mapping.get(income_range, 5000)


class ProductRecommender:
    """Recommends products based on association rules (market basket analysis)"""
    
    @staticmethod
    def get_recommendations(product_skus, metric='confidence', top_n=5):
        """
        Get product recommendations based on what customers bought together.
        
        Args:
            product_skus: List of SKU codes or single SKU string
            metric: 'confidence', 'lift', or 'support'
            top_n: Number of recommendations to return
            
        Returns:
            List of recommended SKU codes
        """
        if isinstance(product_skus, str):
            product_skus = [product_skus]
        
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
    def get_cart_recommendations(cart_items, top_n=5):
        """
        Get recommendations based on current cart contents.
        
        Args:
            cart_items: QuerySet or list of cart items with product/variant
            top_n: Number of recommendations
            
        Returns:
            List of Product objects
        """
        cart_skus = []
        for item in cart_items:
            if hasattr(item, 'variant'):
                cart_skus.append(item.variant.sku)
            elif hasattr(item, 'product'):
                cart_skus.append(item.product.sku)
        
        if not cart_skus:
            return []
        
        recommended_skus = ProductRecommender.get_recommendations(cart_skus, top_n=top_n)
        
        # Convert SKUs to actual products
        products = Product.objects.filter(
            sku__in=recommended_skus,
            is_active=True
        ).select_related('category')[:top_n]
        
        return list(products)
    
    @staticmethod
    def get_similar_products(product, top_n=5):
        """
        Get products frequently bought with this product.
        
        Args:
            product: Product object
            top_n: Number of recommendations
            
        Returns:
            List of Product objects
        """
        recommended_skus = ProductRecommender.get_recommendations(product.sku, top_n=top_n)
        
        products = Product.objects.filter(
            sku__in=recommended_skus,
            is_active=True
        ).exclude(id=product.id).select_related('category')[:top_n]
        
        return list(products)


class PersonalizedRecommendations:
    """Combines both models for personalized product recommendations"""
    
    @staticmethod
    def get_for_user(user, limit=10):
        """
        Get personalized product recommendations for a user.
        Uses ML model prediction as primary method, with category filtering as fallback.
        """
        if not user.is_authenticated:
            return Product.objects.filter(
                is_active=True,
                is_featured=True
            ).order_by('-rating')[:limit]
        
        # PRIORITY 1: Use ML model to predict category based on demographics
        if user.age_range and user.gender:
            try:
                predicted_category_name = CustomerCategoryPredictor.predict(user)
                
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
            is_featured=True
        ).order_by('-rating')[:limit])
