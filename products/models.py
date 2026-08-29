from django.db import models


class Category(models.Model):
    """
    Model representing Topi categories (e.g., Sindhi Topi, Peshawari Topi).
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Category name (e.g. Sindhi Topi)"
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="URL-friendly identifier (auto-generated or manual)"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional short description of this collection"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Model representing individual Topi items in Shah G Cap House.
    """
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        help_text="Category this topi belongs to"
    )
    name = models.CharField(
        max_length=200,
        db_index=True,
        help_text="Product title (e.g. Sindhi Ajrak Mirror Work Topi)"
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        db_index=True,
        help_text="URL identifier for product details page"
    )
    description = models.TextField(
        help_text="Detailed description of fabric, design, and style"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Current selling price in PKR (e.g. 2500.00)"
    )
    original_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Original retail price / MRP in PKR (e.g. 3500.00)"
    )
    image = models.ImageField(
        upload_to='products/',
        blank=True,
        null=True,
        help_text="Original photograph of the topi"
    )
    stock = models.PositiveIntegerField(
        default=0,
        help_text="Available inventory units"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Controls visibility on website"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def discount_percentage(self):
        """
        Dynamically calculates the discount percentage safely.
        Converts Decimals to float to avoid Django silent template errors.
        """
        if not self.original_price or not self.price:
            return 0
        
        if self.original_price <= self.price:
            return 0
            
        try:
            orig = float(self.original_price)
            curr = float(self.price)
            discount = orig - curr
            percentage = (discount / orig) * 100
            return int(round(percentage))
        except (ValueError, ZeroDivisionError, TypeError):
            return 0