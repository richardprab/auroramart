import joblib
import os
import pandas as pd
import warnings
from sklearn.exceptions import InconsistentVersionWarning
from django.apps import apps
from products.models import Product, Category


# Suppress scikit-learn version warnings
warnings.filterwarnings('ignore', category=InconsistentVersionWarning)

# Load models once at module level
app_path = apps.get_app_config('recommendations').path
model_path = os.path.join(app_path, 'mlmodels', 'b2c_customers_100.joblib')
customer_model = joblib.load(model_path)
model_path = os.path.join(app_path, 'mlmodels', 'b2c_products_500_transactions_50k.joblib')
association_rules = joblib.load(model_path)

# DEBUG: Print association rules info
print("=" * 80)
print("ASSOCIATION RULES MODEL INFO:")
print(f"Type: {type(association_rules)}")
if isinstance(association_rules, pd.DataFrame):
    print(f"Shape: {association_rules.shape}")
    print(f"Columns: {association_rules.columns.tolist()}")
    print("\nFirst 3 rules:")
    print(association_rules.head(3))
    
    # Extract all unique SKUs from the rules
    all_skus = set()
    for antecedents in association_rules['antecedents']:
        all_skus.update(antecedents)
    for consequents in association_rules['consequents']:
        all_skus.update(consequents)
    
    print(f"\nTotal unique SKUs in model: {len(all_skus)}")
    print(f"Sample SKUs (first 20): {list(all_skus)[:20]}")
    
    if len(association_rules) > 0:
        print(f"\nAntecedents type: {type(association_rules.iloc[0]['antecedents'])}")
print("=" * 80)


class CustomerCategoryPredictor:
    """Predicts preferred product category based on customer demographics"""
    
    @staticmethod
    def predict(user):
        """
        Predict user's preferred category based on their demographics.
        
        Args:
            user: User object with age_range and gender attributes
            
        Returns:
            str: Predicted category name
        """
        # Map age ranges to numeric values
        age_map = {
            '18-25': 21.5,
            '26-35': 30.5,
            '36-45': 40.5,
            '46-55': 50.5,
            '56+': 60
        }
        
        # Map gender to numeric (1 for Male, 0 for Female)
        gender_map = {
            'male': 1,
            'female': 0
        }
        
        if not user.age_range or not user.gender:
            raise ValueError("User must have age_range and gender set")
        
        age_numeric = age_map.get(user.age_range)
        gender_numeric = gender_map.get(user.gender.lower())
        
        if age_numeric is None or gender_numeric is None:
            raise ValueError("Invalid age_range or gender value")
        
        # Create feature array for prediction
        features = pd.DataFrame({
            'Age': [age_numeric],
            'Gender': [gender_numeric]
        })
        
        # Make prediction
        predicted_category = customer_model.predict(features)[0]
        
        return predicted_category


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
        
        print(f"\nDEBUG get_recommendations: Input SKUs: {product_skus}")
        print(f"DEBUG get_recommendations: Total rules in model: {len(association_rules)}")
        
        # Check if input SKUs exist in the model at all
        all_model_skus = set()
        for antecedents in association_rules['antecedents']:
            all_model_skus.update(antecedents)
        
        for sku in product_skus:
            if sku in all_model_skus:
                print(f"DEBUG: SKU '{sku}' EXISTS in model")
            else:
                print(f"DEBUG: SKU '{sku}' NOT FOUND in model")
                # Try to find similar SKUs
                similar = [s for s in all_model_skus if sku[:8] in s]  # Match first 8 chars
                if similar:
                    print(f"DEBUG: Similar SKUs found: {similar[:5]}")
        
        recommendations = set()
        
        for sku in product_skus:
            print(f"DEBUG get_recommendations: Searching rules for SKU: {sku}")
            
            # Check if sku exists in any antecedents
            matched_rules = association_rules[
                association_rules['antecedents'].apply(lambda x: sku in x)
            ]
            
            print(f"DEBUG get_recommendations: Found {len(matched_rules)} matching rules for {sku}")
            
            if not matched_rules.empty:
                print(f"DEBUG get_recommendations: Top 2 matching rules:")
                print(matched_rules.head(2)[['antecedents', 'consequents', metric]])
                
                top_rules = matched_rules.sort_values(by=metric, ascending=False).head(top_n)
                
                for _, row in top_rules.iterrows():
                    consequents = row['consequents']
                    print(f"DEBUG get_recommendations: Adding consequents: {consequents}")
                    recommendations.update(consequents)
        
        # Remove items already in the input
        recommendations.difference_update(product_skus)
        
        final_recs = list(recommendations)[:top_n]
        print(f"DEBUG get_recommendations: Final {len(final_recs)} recommendations: {final_recs}\n")
        return final_recs
    
    @staticmethod
    def get_cart_recommendations(cart_items, top_n=5):
        """
        Get recommendations based on current cart contents.
        Gets top 4 recommendations for each cart item, then limits to 10 total products.
        Uses association rules model with SKUs.
        
        Args:
            cart_items: QuerySet or list of CartItem objects
            top_n: Number of recommendations per item (default 4), total limited to 10
            
        Returns:
            List of Product objects (max 10)
        """
        print(f"\n{'='*80}")
        print(f"GET_CART_RECOMMENDATIONS called")
        print(f"{'='*80}")
        
        cart_skus = []
        
        # Extract SKUs from cart items (handle both variant and product)
        # Use only first 12 characters of SKU for AI model input
        for item in cart_items:
            if hasattr(item, 'product_variant') and item.product_variant:
                sku = item.product_variant.sku
                sku_12char = sku[:12] if len(sku) > 12 else sku
                cart_skus.append(sku_12char)
                print(f"DEBUG: Added variant SKU (full: {sku}, truncated: {sku_12char})")
            elif hasattr(item, 'product') and item.product:
                sku = item.product.sku
                sku_12char = sku[:12] if len(sku) > 12 else sku
                cart_skus.append(sku_12char)
                print(f"DEBUG: Added product SKU (full: {sku}, truncated: {sku_12char})")
        
        print(f"DEBUG: Total cart SKUs collected (first 12 chars): {cart_skus}")
        
        if not cart_skus:
            print("DEBUG: No SKUs found in cart - returning empty list")
            print(f"{'='*80}\n")
            return []
        
        # Get top 4 recommendations for EACH cart item
        all_recommended_skus = set()
        per_item_limit = 4  # Top 4 for each item
        
        for sku_12char in cart_skus:
            print(f"DEBUG: Getting recommendations for SKU (first 12 chars): {sku_12char}")
            item_recommendations = ProductRecommender.get_recommendations(
                [sku_12char], 
                metric='confidence', 
                top_n=per_item_limit
            )
            print(f"DEBUG: Got {len(item_recommendations)} recommendations for {sku_12char}: {item_recommendations}")
            all_recommended_skus.update(item_recommendations)
        
        # Remove items already in cart (compare first 12 chars)
        cart_skus_set = set(cart_skus)
        filtered_recommended_skus = set()
        for rec_sku in all_recommended_skus:
            rec_sku_12char = rec_sku[:12] if len(rec_sku) > 12 else rec_sku
            if rec_sku_12char not in cart_skus_set:
                filtered_recommended_skus.add(rec_sku)
        
        print(f"DEBUG: Total unique recommended SKUs (after removing cart items): {len(filtered_recommended_skus)}")
        print(f"DEBUG: Recommended SKUs: {list(filtered_recommended_skus)[:10]}")
        
        if not filtered_recommended_skus:
            print("DEBUG: No recommendations from association rules - returning empty list")
            print(f"{'='*80}\n")
            return []
        
        # Convert SKUs to actual products (match both variant and product SKU using first 12 chars)
        from products.models import ProductVariant
        from django.db.models import Q
        
        # Limit to 10 total products
        limited_skus = list(filtered_recommended_skus)[:10]
        
        # Build Q objects to match first 12 characters of SKUs
        variant_q = Q()
        product_q = Q()
        
        for rec_sku in limited_skus:
            rec_sku_12char = rec_sku[:12] if len(rec_sku) > 12 else rec_sku
            # Match variants where first 12 chars of SKU match
            variant_q |= Q(variants__sku__startswith=rec_sku_12char)
            # Match products where first 12 chars of SKU match
            product_q |= Q(sku__startswith=rec_sku_12char)
        
        variant_products = Product.objects.filter(
            variant_q,
            is_active=True
        ).distinct()
        print(f"DEBUG: Found {variant_products.count()} products by variant SKU (first 12 chars)")
        
        product_sku_products = Product.objects.filter(
            product_q,
            is_active=True
        ).distinct()
        print(f"DEBUG: Found {product_sku_products.count()} products by product SKU (first 12 chars)")
        
        products = list(set(list(variant_products) + list(product_sku_products)))
        print(f"DEBUG: Total unique products: {len(products)}")
        
        if products:
            print("DEBUG: Product names:")
            for p in products:
                print(f"  - {p.name} (SKU: {p.sku})")
        
        # Sort by rating and creation date
        products.sort(key=lambda p: (p.rating or 0, p.created_at), reverse=True)
        
        # Limit to 10 total products
        final_products = products[:10]
        print(f"DEBUG: Returning top {len(final_products)} products (limited to 10)")
        print(f"{'='*80}\n")
        
        return final_products
    
    @staticmethod
    def get_order_recommendations(order_items, start_index=4, end_index=8, fallback_count=4):
        """
        Get recommendations based on order items.
        Returns items at positions 5-9 (index 4-8), or last 4 if fewer than 9 items available.
        Uses first 12 characters of SKU for AI model input.
        
        Args:
            order_items: QuerySet or list of OrderItem objects
            start_index: Start index (default 4 for 5th item)
            end_index: End index (default 8 for 9th item)
            fallback_count: Number of items to return if fewer than 9 available (default 4)
            
        Returns:
            List of Product objects (items 5-9, or last 4 if fewer than 9)
        """
        print(f"\n{'='*80}")
        print(f"GET_ORDER_RECOMMENDATIONS called")
        print(f"{'='*80}")
        
        order_skus = []
        
        # Extract SKUs from order items (handle both variant and product)
        # Use only first 12 characters of SKU for AI model input
        for item in order_items:
            if hasattr(item, 'product_variant') and item.product_variant:
                sku = item.product_variant.sku
                sku_12char = sku[:12] if len(sku) > 12 else sku
                order_skus.append(sku_12char)
                print(f"DEBUG: Added variant SKU (full: {sku}, truncated: {sku_12char})")
            elif hasattr(item, 'product') and item.product:
                sku = item.product.sku
                sku_12char = sku[:12] if len(sku) > 12 else sku
                order_skus.append(sku_12char)
                print(f"DEBUG: Added product SKU (full: {sku}, truncated: {sku_12char})")
        
        print(f"DEBUG: Total order SKUs collected (first 12 chars): {order_skus}")
        
        if not order_skus:
            print("DEBUG: No SKUs found in order - returning empty list")
            print(f"{'='*80}\n")
            return []
        
        # Get top 4 recommendations for EACH order item
        all_recommended_skus = []
        per_item_limit = 4  # Top 4 for each item
        
        for sku_12char in order_skus:
            print(f"DEBUG: Getting recommendations for SKU (first 12 chars): {sku_12char}")
            item_recommendations = ProductRecommender.get_recommendations(
                [sku_12char], 
                metric='confidence', 
                top_n=per_item_limit
            )
            print(f"DEBUG: Got {len(item_recommendations)} recommendations for {sku_12char}: {item_recommendations}")
            all_recommended_skus.extend(item_recommendations)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommended_skus = []
        for rec_sku in all_recommended_skus:
            if rec_sku not in seen:
                seen.add(rec_sku)
                unique_recommended_skus.append(rec_sku)
        
        # Remove items already in order (compare first 12 chars)
        order_skus_set = set(order_skus)
        filtered_recommended_skus = []
        for rec_sku in unique_recommended_skus:
            rec_sku_12char = rec_sku[:12] if len(rec_sku) > 12 else rec_sku
            if rec_sku_12char not in order_skus_set:
                filtered_recommended_skus.append(rec_sku)
        
        print(f"DEBUG: Total unique recommended SKUs (after removing order items): {len(filtered_recommended_skus)}")
        
        if not filtered_recommended_skus:
            print("DEBUG: No recommendations from association rules - returning empty list")
            print(f"{'='*80}\n")
            return []
        
        # Get at least 9 recommendations, then select items 5-9 (index 4-8)
        # If fewer than 9, take the last 4
        if len(filtered_recommended_skus) >= 9:
            # Take items 5-9 (index 4-8)
            selected_skus = filtered_recommended_skus[start_index:end_index+1]
            print(f"DEBUG: Taking items 5-9 (index {start_index}-{end_index}): {len(selected_skus)} items")
        else:
            # Take last 4 items
            selected_skus = filtered_recommended_skus[-fallback_count:] if len(filtered_recommended_skus) >= fallback_count else filtered_recommended_skus
            print(f"DEBUG: Taking last {len(selected_skus)} items (fewer than 9 available)")
        
        print(f"DEBUG: Selected SKUs: {selected_skus}")
        
        # Convert SKUs to actual products (match both variant and product SKU using first 12 chars)
        from products.models import ProductVariant
        from django.db.models import Q
        
        # Build Q objects to match first 12 characters of SKUs
        variant_q = Q()
        product_q = Q()
        
        for rec_sku in selected_skus:
            rec_sku_12char = rec_sku[:12] if len(rec_sku) > 12 else rec_sku
            # Match variants where first 12 chars of SKU match
            variant_q |= Q(variants__sku__startswith=rec_sku_12char)
            # Match products where first 12 chars of SKU match
            product_q |= Q(sku__startswith=rec_sku_12char)
        
        variant_products = Product.objects.filter(
            variant_q,
            is_active=True
        ).distinct()
        print(f"DEBUG: Found {variant_products.count()} products by variant SKU (first 12 chars)")
        
        product_sku_products = Product.objects.filter(
            product_q,
            is_active=True
        ).distinct()
        print(f"DEBUG: Found {product_sku_products.count()} products by product SKU (first 12 chars)")
        
        products = list(set(list(variant_products) + list(product_sku_products)))
        print(f"DEBUG: Total unique products: {len(products)}")
        
        if products:
            print("DEBUG: Product names:")
            for p in products:
                print(f"  - {p.name} (SKU: {p.sku})")
        
        # Sort by rating and creation date
        products.sort(key=lambda p: (p.rating or 0, p.created_at), reverse=True)
        
        # Limit to the number of selected SKUs
        final_products = products[:len(selected_skus)]
        print(f"DEBUG: Returning {len(final_products)} products (items 5-9 or last 4)")
        print(f"{'='*80}\n")
        
        return final_products
    
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
        Uses customer category prediction if user has demographic data.
        """
        if not user or not user.is_authenticated:
            return Product.objects.filter(
                is_active=True,
                is_featured=True
            ).order_by('-rating')[:limit]
        
        # Try to predict preferred category if user has demographic data
        if user.age_range and user.gender:
            try:
                predicted_category = CustomerCategoryPredictor.predict(user)
                category = Category.objects.filter(name=predicted_category).first()
                
                if category:
                    products = Product.objects.filter(
                        category=category,
                        is_active=True
                    ).order_by('-rating', '-created_at')[:limit]
                    
                    if products.exists():
                        return list(products)
            except Exception:
                pass
        
        # Fallback to user's preferred category if set
        if hasattr(user, 'preferred_category') and user.preferred_category:
            products = Product.objects.filter(
                category=user.preferred_category,
                is_active=True
            ).order_by('-rating', '-created_at')[:limit]
            
            if products.exists():
                return list(products)
        
        # Final fallback to featured products
        return list(Product.objects.filter(
            is_active=True,
            is_featured=True
        ).order_by('-rating')[:limit])
