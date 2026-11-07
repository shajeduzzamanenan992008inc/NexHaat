import { Router, Request, Response } from 'express';
import { INITIAL_CATEGORIES, INITIAL_PRODUCTS } from './src/data/mockData.ts';

export function createMarketplaceRouter(): Router {
  const router = Router();

  // Pre-map categories into the exact ApiCategory shape expected by marketplaceApi.ts
  const apiCategories = INITIAL_CATEGORIES.map((c) => ({
    id: c.id,
    name: c.name,
    slug: c.slug,
    description: c.description || '',
    image: c.image || null,
    display_image: c.image || null,
    is_active: true,
  }));

  // Pre-map products into the exact ApiProduct shape required by isApiProduct()
  const apiProducts = INITIAL_PRODUCTS.map((p) => {
    const priceNum = typeof p.price === 'number' && Number.isFinite(p.price) ? p.price : 100;
    const discountNum = typeof p.discount_price === 'number' && Number.isFinite(p.discount_price)
      ? p.discount_price
      : null;
    const displayNum = discountNum !== null && discountNum < priceNum ? discountNum : priceNum;

    return {
      id: p.id,
      name: p.name,
      localized_name: p.name_bn || p.name,
      description: p.description || '',
      localized_description: p.description_bn || p.description || '',
      slug: p.slug,
      brand_name: p.brand_name || null,
      seller_name: p.seller_name || 'NexHaat Verified Merchant',
      price: priceNum.toFixed(2),
      discount_price: discountNum !== null ? discountNum.toFixed(2) : null,
      display_price: displayNum.toFixed(2),
      stock: typeof p.stock_quantity === 'number' && Number.isSafeInteger(p.stock_quantity) ? p.stock_quantity : 30,
      sku: p.sku || `NH-${p.id}`,
      image: p.image || null,
      display_image: p.image || null,
      is_available: p.is_available ?? true,
      is_featured: p.is_featured ?? false,
      moderation_status: p.moderation_status || ('approved' as const),
      category_id: p.category_id,
      seller_id: p.seller_id || 1,
      rating: typeof p.rating === 'number' ? Math.min(5, Math.max(0, p.rating)) : 4.8,
      review_count: typeof p.review_count === 'number' ? p.review_count : 12,
      variants: Array.isArray(p.variants)
        ? p.variants.map((v, idx) => ({
            id: idx + 1,
            option_name: v.name || 'Standard',
            option_value: v.name_bn || v.name || 'সাধারণ',
            price: (displayNum + (v.priceModifier || 0)).toFixed(2),
            stock: typeof v.stock === 'number' ? v.stock : 15,
            sku: `${p.sku || p.id}-v${idx + 1}`,
          }))
        : undefined,
    };
  });

  // CSRF token endpoint
  router.get('/auth/csrf', (_req: Request, res: Response) => {
    res.json({
      success: true,
      data: {
        csrf_token: 'nexhaat-secure-local-csrf-token',
      },
    });
  });

  // User session endpoint: returns 401 when no active session
  router.get('/auth/me', (_req: Request, res: Response) => {
    res.status(401).json({
      success: false,
      error: {
        code: 'UNAUTHENTICATED',
        message: 'No active marketplace session.',
      },
    });
  });

  // 2FA status endpoint
  router.get('/auth/2fa/status', (_req: Request, res: Response) => {
    res.json({
      success: true,
      data: {
        enabled: false,
        confirmed_at: null,
        backup_codes_remaining: 0,
      },
    });
  });

  // Catalog Categories
  router.get('/categories', (_req: Request, res: Response) => {
    res.json({
      success: true,
      data: apiCategories,
    });
  });

  // Catalog Category by slug
  router.get('/categories/:slug', (req: Request, res: Response) => {
    const slug = req.params.slug;
    const category = apiCategories.find((c) => c.slug === slug);
    if (!category) {
      return res.status(404).json({
        success: false,
        error: { code: 'NOT_FOUND', message: 'Category not found' },
      });
    }

    const filtered = apiProducts.filter((p) => p.category_id === category.id);
    const page = Math.max(1, parseInt(String(req.query.page || '1'), 10));
    const limit = Math.max(1, Math.min(100, parseInt(String(req.query.limit || '24'), 10)));
    const start = (page - 1) * limit;
    const paginated = filtered.slice(start, start + limit);

    return res.json({
      success: true,
      data: paginated,
      pagination: {
        page,
        limit,
        total: filtered.length,
      },
    });
  });

  // Catalog Products with filtering, search, and pagination
  router.get('/products', (req: Request, res: Response) => {
    let items = [...apiProducts];

    const q = typeof req.query.q === 'string' ? req.query.q.trim().toLowerCase() : '';
    if (q) {
      items = items.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.description.toLowerCase().includes(q) ||
          (p.brand_name && p.brand_name.toLowerCase().includes(q)) ||
          (p.seller_name && p.seller_name.toLowerCase().includes(q)),
      );
    }

    const categoryId = req.query.category_id ? parseInt(String(req.query.category_id), 10) : undefined;
    if (categoryId && Number.isFinite(categoryId)) {
      items = items.filter((p) => p.category_id === categoryId);
    }

    if (req.query.in_stock === '1' || req.query.in_stock === 'true') {
      items = items.filter((p) => p.stock > 0 && p.is_available);
    }

    if (req.query.discount === '1' || req.query.discount === 'true') {
      items = items.filter((p) => p.discount_price !== null && Number(p.discount_price) < Number(p.price));
    }

    const minPrice = parseFloat(String(req.query.min_price || ''));
    if (!isNaN(minPrice)) {
      items = items.filter((p) => Number(p.display_price) >= minPrice);
    }

    const maxPrice = parseFloat(String(req.query.max_price || ''));
    if (!isNaN(maxPrice)) {
      items = items.filter((p) => Number(p.display_price) <= maxPrice);
    }

    const minRating = parseFloat(String(req.query.min_rating || ''));
    if (!isNaN(minRating)) {
      items = items.filter((p) => (p.rating ?? 0) >= minRating);
    }

    const sort = String(req.query.sort || 'featured');
    if (sort === 'price_asc') {
      items.sort((a, b) => Number(a.display_price) - Number(b.display_price));
    } else if (sort === 'price_desc') {
      items.sort((a, b) => Number(b.display_price) - Number(a.display_price));
    } else if (sort === 'newest') {
      items.sort((a, b) => b.id - a.id);
    }

    const page = Math.max(1, parseInt(String(req.query.page || '1'), 10));
    const limit = Math.max(1, Math.min(100, parseInt(String(req.query.limit || '24'), 10)));
    const start = (page - 1) * limit;
    const paginated = items.slice(start, start + limit);

    return res.json({
      success: true,
      data: paginated,
      pagination: {
        page,
        limit,
        total: items.length,
      },
    });
  });

  // Product detail by ID or Slug
  router.get('/products/:idOrSlug', (req: Request, res: Response) => {
    const idOrSlug = req.params.idOrSlug;
    const id = parseInt(idOrSlug, 10);
    const product = apiProducts.find((p) => (!isNaN(id) && p.id === id) || p.slug === idOrSlug);
    if (!product) {
      return res.status(404).json({
        success: false,
        error: { code: 'NOT_FOUND', message: 'Product not found' },
      });
    }
    return res.json({
      success: true,
      data: product,
    });
  });

  // Cart
  router.get('/cart', (_req: Request, res: Response) => {
    res.json({
      success: true,
      data: { items: [] },
    });
  });

  router.post('/cart/items', (_req: Request, res: Response) => {
    res.json({
      success: true,
      data: { message: 'Item added to cart' },
    });
  });

  router.delete('/cart', (_req: Request, res: Response) => {
    res.json({
      success: true,
      data: { message: 'Cart cleared' },
    });
  });

  // Wishlist
  router.get('/wishlist', (_req: Request, res: Response) => {
    res.json({
      success: true,
      data: { count: 0, products: [] },
    });
  });

  router.post('/wishlist/items', (_req: Request, res: Response) => {
    res.json({
      success: true,
      data: { message: 'Item added to wishlist' },
    });
  });

  // Orders
  router.get('/orders', (_req: Request, res: Response) => {
    res.json({
      success: true,
      data: [],
    });
  });

  // Notifications
  router.get('/notifications', (_req: Request, res: Response) => {
    res.json({
      success: true,
      data: { notifications: [] },
    });
  });

  router.post('/notifications/read-all', (_req: Request, res: Response) => {
    res.json({
      success: true,
      data: { count: 0 },
    });
  });

  // Product reviews
  router.get('/reviews/product/:id', (req: Request, res: Response) => {
    const productId = parseInt(req.params.id, 10);
    res.json({
      success: true,
      data: {
        reviews: [
          {
            id: 1,
            product_id: productId,
            rating: 5,
            comment: 'অসাধারণ কোয়ালিটি! খুব দ্রুত ডেলিভারি পেয়েছি। ধন্যবাদ NexHaat!',
            author_name: 'সাদিয়া ইসলাম',
            created_at: new Date().toISOString(),
            status: 'approved',
            verified_purchase: true,
            helpful_count: 5,
            viewer_helpful: false,
          },
        ],
        total: 1,
      },
    });
  });

  return router;
}
