import React, { createContext, useContext, useState, useEffect, useRef, ReactNode } from 'react';
import { 
  User, UserRole, Product, Category, CartItem, Order, 
  Review, Notification, Promotion, ProductVariant, OrderStatus, 
  ProductQuestion, AIChatMessage, SponsoredCampaign, PriceAlert 
} from '../types';
import { 
  INITIAL_USERS, INITIAL_CATEGORIES, INITIAL_PRODUCTS, 
  INITIAL_PROMOTIONS, INITIAL_REVIEWS, INITIAL_NOTIFICATIONS, 
  INITIAL_QUESTIONS, INITIAL_SPONSORED_CAMPAIGNS 
} from '../data/mockData';
import { 
  auth, googleProvider, signInWithPopup, fbSignOut, 
  onAuthStateChanged, FirebaseUser, db, handleFirestoreError, OperationType 
} from '../lib/firebase';
import { doc, setDoc } from 'firebase/firestore';
import {
  FlaskAuthError,
  FlaskUser,
  getCurrentFlaskUser,
  LoginResult,
  loginWithFlask as authenticateWithFlask,
  logoutFromFlask,
  RegistrationRequest,
  startFlaskRegistration,
  verifyTwoFactorChallenge as verify2FAChallengeApi,
} from '../lib/flaskAuth';
import {
  addMarketplaceCartItem,
  addMarketplaceWishlistItem,
  fetchMarketplaceCatalog,
  fetchMarketplaceWishlist,
  removeMarketplaceCartItem,
  removeMarketplaceWishlistItem,
  cancelMarketplaceOrder,
  fetchMarketplaceNotifications,
  fetchMarketplaceOrders,
  markAllMarketplaceNotificationsRead,
  markMarketplaceNotificationRead,
  requestMarketplaceReturn,
  submitMarketplaceCheckout,
  updateMarketplaceCartItem,
} from '../lib/marketplaceApi';

export type AppView = 
  | 'home' 
  | 'catalog' 
  | 'deals' 
  | 'product-detail' 
  | 'cart' 
  | 'checkout' 
  | 'order-confirmation' 
  | 'my-orders' 
  | 'wishlist' 
  | 'notifications' 
  | 'seller-portal' 
  | 'rider-portal' 
  | 'admin-portal' 
  | 'support';

interface ToastMessage {
  id: string;
  type: 'success' | 'info' | 'warning' | 'error';
  message: string;
}

interface AppContextType {
  // Navigation & View
  currentView: AppView;
  setCurrentView: (view: AppView) => void;
  selectedProductSlug: string | null;
  setSelectedProductSlug: (slug: string | null) => void;
  activeCategorySlug: string | null;
  setActiveCategorySlug: (slug: string | null) => void;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  navigateToProduct: (slug: string) => void;
  navigateToCategory: (categorySlug: string) => void;

  // Language & Theme
  language: 'en' | 'bn';
  setLanguage: (lang: 'en' | 'bn') => void;
  isDarkMode: boolean;
  toggleDarkMode: () => void;
  t: (en: string, bn: string) => string;
  formatPrice: (amount: number) => string;

  // User & Roles
  currentUser: User;
  setUserRole: (role: UserRole) => void;
  firebaseUser: FirebaseUser | null;
  loginWithGoogle: () => Promise<void>;
  logoutFirebase: () => Promise<void>;
  isFirebaseAuthLoading: boolean;
  flaskUser: FlaskUser | null;
  isFlaskAuthLoading: boolean;
  loginWithFlask: (email: string, password: string) => Promise<LoginResult>;
  verifyTwoFactorChallenge: (code: string) => Promise<FlaskUser>;
  logoutFlask: () => Promise<void>;
  startFlaskRegistration: (request: RegistrationRequest) => Promise<void>;
  submitMarketplaceCheckout: (input: {
    customerName: string;
    phone: string;
    address: string;
    city: string;
    promotionCode?: string;
  }) => Promise<Order>;
  isMarketplaceCatalogLoading: boolean;
  marketplaceCatalogError: string | null;

  // NexHaat Prime
  isPrimeMember: boolean;
  togglePrimeMembership: () => void;
  isPrimeModalOpen: boolean;
  setIsPrimeModalOpen: (open: boolean) => void;

  // Catalog
  products: Product[];
  categories: Category[];
  addProduct: (product: Omit<Product, 'id' | 'rating' | 'review_count' | 'sku'> & { sku?: string }) => void;
  updateProduct: (product: Product) => void;
  deleteProduct: (id: number) => void;
  approveProduct: (id: number, approved: boolean) => void;

  // Cart & Save for Later
  cart: CartItem[];
  savedForLater: CartItem[];
  addToCart: (product: Product, variant?: ProductVariant, quantity?: number) => void;
  updateCartQuantity: (productId: number, variantId: string | undefined, quantity: number) => void;
  removeFromCart: (productId: number, variantId?: string) => void;
  saveForLater: (productId: number, variantId?: string) => void;
  moveToCartFromSaved: (productId: number, variantId?: string) => void;
  removeFromSaved: (productId: number, variantId?: string) => void;
  clearCart: () => void;
  cartCount: number;
  cartSubtotal: number;
  isCartDrawerOpen: boolean;
  setIsCartDrawerOpen: (open: boolean) => void;

  // Product Comparison (Amazon style)
  comparedProductIds: number[];
  toggleCompare: (productId: number) => void;
  clearCompare: () => void;
  isCompareModalOpen: boolean;
  setIsCompareModalOpen: (open: boolean) => void;

  // Recently Viewed (Amazon style)
  recentlyViewed: Product[];
  recordRecentlyViewed: (product: Product) => void;

  // Wishlist
  wishlist: number[];
  toggleWishlist: (productId: number) => void;
  isInWishlist: (productId: number) => boolean;
  wishlistCount: number;

  // Orders & Checkout
  orders: Order[];
  lastConfirmedOrder: Order | null;
  placeOrder: (orderData: Omit<Order, 'id' | 'order_number' | 'created_at' | 'status'>) => Order;
  cancelOrder: (orderNumber: string) => void;
  requestOrderReturn: (orderNumber: string, reason: string) => void;
  updateOrderStatus: (orderNumber: string, status: OrderStatus, riderInfo?: { name: string; phone: string }) => void;

  // Coupons / Promo
  activeCoupon: Promotion | null;
  appliedPromoDiscount: number;
  applyCoupon: (code: string) => boolean;
  removeCoupon: () => void;

  // Reviews & Q&A
  reviews: Review[];
  addReview: (productId: number, rating: number, comment: string) => void;
  getProductReviews: (productId: number) => Review[];
  questions: ProductQuestion[];
  addQuestion: (productId: number, questionText: string) => void;
  getProductQuestions: (productId: number) => ProductQuestion[];

  // Gemini AI Shopping Assistant
  isAIAssistantOpen: boolean;
  setIsAIAssistantOpen: (open: boolean) => void;
  aiMessages: AIChatMessage[];
  sendAIMessage: (text: string) => void;
  clearAIChat: () => void;

  // Seller Ads / Sponsored
  sponsoredCampaigns: SponsoredCampaign[];
  addSponsoredCampaign: (camp: Omit<SponsoredCampaign, 'id' | 'impressions' | 'clicks' | 'spend'>) => void;

  // Notifications & Toast
  notifications: Notification[];
  unreadNotificationCount: number;
  markNotificationAsRead: (id: string) => Promise<void>;
  markAllNotificationsAsRead: () => Promise<void>;
  toasts: ToastMessage[];
  showToast: (message: string, type?: 'success' | 'info' | 'warning' | 'error') => void;

  // Price Alerts
  priceAlerts: PriceAlert[];
  setPriceAlert: (productId: number, targetPrice: number) => PriceAlert;
  removePriceAlert: (productId: number) => void;
  getPriceAlert: (productId: number) => PriceAlert | undefined;
  simulatePriceDrop: (productId: number, newPrice?: number) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  // Navigation
  const [currentView, setCurrentView] = useState<AppView>('home');
  const [selectedProductSlug, setSelectedProductSlug] = useState<string | null>(null);
  const [activeCategorySlug, setActiveCategorySlug] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isCartDrawerOpen, setIsCartDrawerOpen] = useState<boolean>(false);
  const [isCompareModalOpen, setIsCompareModalOpen] = useState<boolean>(false);
  const [isPrimeModalOpen, setIsPrimeModalOpen] = useState<boolean>(false);
  const [isAIAssistantOpen, setIsAIAssistantOpen] = useState<boolean>(false);

  // Localization & Theme
  const [language, setLanguage] = useState<'en' | 'bn'>(() => {
    return (localStorage.getItem('nexhaat_lang') as 'en' | 'bn') || 'en';
  });

  const [isDarkMode, setIsDarkMode] = useState<boolean>(() => {
    return localStorage.getItem('nexhaat_theme') === 'dark';
  });

  // User & Persona
  const [currentRole, setCurrentRole] = useState<UserRole>('customer');
  const [isPrimeMember, setIsPrimeMember] = useState<boolean>(() => {
    return localStorage.getItem('nexhaat_prime') !== 'false';
  });

  const [firebaseUser, setFirebaseUser] = useState<FirebaseUser | null>(null);
  const [isFirebaseAuthLoading, setIsFirebaseAuthLoading] = useState<boolean>(true);
  const [flaskUser, setFlaskUser] = useState<FlaskUser | null>(null);
  const [isFlaskAuthLoading, setIsFlaskAuthLoading] = useState<boolean>(true);

  useEffect(() => {
    let active = true;
    getCurrentFlaskUser()
      .then((user) => {
        if (active) setFlaskUser(user);
      })
      .catch((error: unknown) => {
        if (active && !(error instanceof FlaskAuthError && error.status === 401)) {
          console.warn('Flask session check was unavailable:', error);
        }
      })
      .finally(() => {
        if (active) setIsFlaskAuthLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      setFirebaseUser(user);
      setIsFirebaseAuthLoading(false);
      if (user) {
        showToast(`Google Auth verified: ${user.displayName || user.email}`, 'success');
        try {
          await setDoc(doc(db, 'users', user.uid), {
            userId: user.uid,
            name: user.displayName || 'Google User',
            email: user.email || '',
            role: currentRole,
            isPrime: isPrimeMember,
            createdAt: new Date().toISOString(),
          }, { merge: true });
        } catch (err) {
          handleFirestoreError(err, OperationType.WRITE, `users/${user.uid}`);
        }
      }
    });
    return () => unsubscribe();
  }, [currentRole, isPrimeMember]);

  const isSigningInRef = useRef<boolean>(false);

  const loginWithGoogle = async () => {
    if (isSigningInRef.current) return;
    isSigningInRef.current = true;
    setIsFirebaseAuthLoading(true);

    try {
      const res = await signInWithPopup(auth, googleProvider);
      if (res.user) {
        showToast(`Welcome, ${res.user.displayName || 'Shopper'}!`, 'success');
      }
    } catch (err: any) {
      const errorCode = err?.code;
      if (errorCode === 'auth/cancelled-popup-request' || errorCode === 'auth/popup-closed-by-user') {
        // User closed or dismissed the popup, ignore silently
        return;
      }
      if (errorCode === 'auth/popup-blocked') {
        showToast(
          t(
            'Sign-in pop-up was blocked by browser. Please allow pop-ups to sign in with Google.',
            'ব্রাউজার সাইন-ইন পপ-আপ ব্লক করেছে। গুগল সাইন ইন করতে পপ-আপ অনুমোদন করুন।'
          ),
          'warning'
        );
        return;
      }
      console.warn('Google sign-in notice:', err?.message || err);
      showToast(err?.message || 'Google sign-in was unable to complete', 'error');
    } finally {
      isSigningInRef.current = false;
      setIsFirebaseAuthLoading(false);
    }
  };

  const logoutFirebase = async () => {
    try {
      await fbSignOut(auth);
      showToast('Signed out of Firebase Google Auth', 'info');
    } catch (err: any) {
      showToast(err.message || 'Sign-out failed', 'error');
    }
  };

  const loginWithFlask = async (email: string, password: string): Promise<LoginResult> => {
    setIsFlaskAuthLoading(true);
    try {
      const result = await authenticateWithFlask(email, password);
      if (result.status === 'authenticated') {
        setFlaskUser(result.user);
        showToast(t('Signed in to the NexHaat marketplace.', 'NexHaat মার্কেটপ্লেসে সাইন ইন হয়েছে।'), 'success');
      }
      return result;
    } finally {
      setIsFlaskAuthLoading(false);
    }
  };

  const verifyTwoFactorChallenge = async (code: string): Promise<FlaskUser> => {
    setIsFlaskAuthLoading(true);
    try {
      const user = await verify2FAChallengeApi(code);
      setFlaskUser(user);
      showToast(t('Signed in with two-factor authentication.', 'টু-ফ্যাক্টর অথেনটিকেশন দিয়ে সাইন ইন হয়েছে।'), 'success');
      return user;
    } finally {
      setIsFlaskAuthLoading(false);
    }
  };


  const logoutFlask = async () => {
    setIsFlaskAuthLoading(true);
    try {
      await logoutFromFlask();
      setFlaskUser(null);
      setOrders([]);
      setNotifications(INITIAL_NOTIFICATIONS);
      showToast(t('Marketplace session ended.', 'মার্কেটপ্লেস session শেষ হয়েছে।'), 'info');
    } finally {
      setIsFlaskAuthLoading(false);
    }
  };

  const beginFlaskRegistration = async (request: RegistrationRequest) => {
    setIsFlaskAuthLoading(true);
    try {
      await startFlaskRegistration(request);
    } finally {
      setIsFlaskAuthLoading(false);
    }
  };

  const baseUser = INITIAL_USERS[currentRole] || INITIAL_USERS.customer;
  const currentUser: User = {
    ...baseUser,
    id: firebaseUser ? firebaseUser.uid : baseUser.id,
    name: firebaseUser?.displayName || baseUser.name,
    email: firebaseUser?.email || baseUser.email,
    avatar: firebaseUser?.photoURL || baseUser.avatar,
    isPrimeMember,
  };

  // Data Store with Local Storage persistence
  const [products, setProducts] = useState<Product[]>(() => {
    const saved = localStorage.getItem('nexhaat_products');
    return saved ? JSON.parse(saved) : INITIAL_PRODUCTS;
  });

  const [categories, setCategories] = useState<Category[]>(INITIAL_CATEGORIES);
  const [isMarketplaceCatalogLoading, setIsMarketplaceCatalogLoading] = useState(false);
  const [marketplaceCatalogError, setMarketplaceCatalogError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setIsMarketplaceCatalogLoading(true);
    fetchMarketplaceCatalog()
      .then(({ products: apiProducts, categories: apiCategories }) => {
        if (!active || apiProducts.length === 0) return;
        setProducts(apiProducts);
        if (apiCategories.length > 0) setCategories(apiCategories);
        setMarketplaceCatalogError(null);
      })
      .catch((error: unknown) => {
        if (active) {
          setMarketplaceCatalogError(
            error instanceof Error ? error.message : 'Marketplace catalog is unavailable.',
          );
        }
      })
      .finally(() => {
        if (active) setIsMarketplaceCatalogLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const [cart, setCart] = useState<CartItem[]>(() => {
    const saved = localStorage.getItem('nexhaat_cart');
    return saved ? JSON.parse(saved) : [];
  });

  const [savedForLater, setSavedForLater] = useState<CartItem[]>(() => {
    const saved = localStorage.getItem('nexhaat_saved_later');
    return saved ? JSON.parse(saved) : [];
  });

  const [comparedProductIds, setComparedProductIds] = useState<number[]>([]);

  const [recentlyViewed, setRecentlyViewed] = useState<Product[]>(() => {
    return [INITIAL_PRODUCTS[0], INITIAL_PRODUCTS[1], INITIAL_PRODUCTS[3]];
  });

  const [wishlist, setWishlist] = useState<number[]>(() => {
    const saved = localStorage.getItem('nexhaat_wishlist');
    return saved ? JSON.parse(saved) : [101, 104];
  });

  const [orders, setOrders] = useState<Order[]>(() => {
    const saved = localStorage.getItem('nexhaat_orders');
    if (saved) return JSON.parse(saved);
    return [
      {
        id: 'ord-demo-01',
        order_number: 'NH-2026-8821',
        created_at: new Date(Date.now() - 3600000 * 4).toISOString(),
        customer_name: 'Tanvir Rahman',
        customer_phone: '+8801711223344',
        customer_email: 'tanvir.rahman@example.com',
        delivery_address: {
          division: 'Dhaka',
          district: 'Dhaka',
          thana: 'Dhanmondi',
          street: 'Flat 4B, House 18, Road 7',
          notes: 'Call before arriving',
        },
        delivery_speed: 'standard',
        payment_method: 'cod',
        payment_status: 'pending',
        status: 'shipped',
        items: [
          {
            product_id: 101,
            product_name: 'Premium Rajshahi Fazli Sweet Mangoes (5kg Basket)',
            product_name_bn: 'রাজশাহীর সেরা ফজলি আম (৫ কেজি বাস্কেট)',
            seller_id: 1,
            seller_name: 'Dhaka Fresh & Agro Haat',
            image: 'https://images.unsplash.com/photo-1553279768-865429fa0078?auto=format&fit=crop&w=800&q=80',
            unit_price: 720,
            quantity: 1,
            variant_name: '5kg Crate',
            total_price: 720,
          },
          {
            product_id: 104,
            product_name: 'Authentic Traditional Bogra Shahi Misti Doi',
            product_name_bn: 'ঐতিহ্যবাহী বগুড়ার শাহী মিষ্টি দই',
            seller_id: 3,
            seller_name: 'Gouripur Dairy & Sweets',
            image: 'https://images.unsplash.com/photo-1550583724-b2692b85b150?auto=format&fit=crop&w=800&q=80',
            unit_price: 310,
            quantity: 2,
            total_price: 620,
          }
        ],
        subtotal: 1340,
        delivery_fee: 0,
        discount_amount: 0,
        total_amount: 1340,
        rider_name: 'Kamal Hossain',
        rider_phone: '+8801912998877',
      }
    ];
  });

  const [lastConfirmedOrder, setLastConfirmedOrder] = useState<Order | null>(null);
  const [activeCoupon, setActiveCoupon] = useState<Promotion | null>(null);
  const [reviews, setReviews] = useState<Review[]>(INITIAL_REVIEWS);
  const [questions, setQuestions] = useState<ProductQuestion[]>(INITIAL_QUESTIONS);
  const [sponsoredCampaigns, setSponsoredCampaigns] = useState<SponsoredCampaign[]>(INITIAL_SPONSORED_CAMPAIGNS);
  const [notifications, setNotifications] = useState<Notification[]>(INITIAL_NOTIFICATIONS);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [priceAlerts, setPriceAlerts] = useState<PriceAlert[]>(() => {
    try {
      const saved = localStorage.getItem('nexhaat_price_alerts');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem('nexhaat_price_alerts', JSON.stringify(priceAlerts));
    } catch {}
  }, [priceAlerts]);

  useEffect(() => {
    if (flaskUser?.role !== 'customer') return;
    let active = true;
    setOrders([]);
    Promise.all([fetchMarketplaceOrders(), fetchMarketplaceNotifications()])
      .then(([serverOrders, serverNotifications]) => {
        if (!active) return;
        setOrders(serverOrders);
        setNotifications(serverNotifications);
      })
      .catch((error: unknown) => {
        if (active) {
          setOrders([]);
          setNotifications([]);
          console.warn('Marketplace account data was unavailable:', error);
        }
      });
    return () => {
      active = false;
    };
  }, [flaskUser]);

  // AI Assistant Chat Messages
  const [aiMessages, setAiMessages] = useState<AIChatMessage[]>([
    {
      id: 'ai-init',
      sender: 'assistant',
      text: 'Hello Tanvir! I am HaatAI, your intelligent Gemini shopping assistant on NexHaat. Looking for fresh river ilish, seasonal fruits, organic spices, or recipe pairings?',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      suggestedProductIds: [101, 102, 104],
    }
  ]);

  // Sync state to LocalStorage
  useEffect(() => {
    localStorage.setItem('nexhaat_products', JSON.stringify(products));
  }, [products]);

  useEffect(() => {
    localStorage.setItem('nexhaat_cart', JSON.stringify(cart));
  }, [cart]);

  useEffect(() => {
    localStorage.setItem('nexhaat_saved_later', JSON.stringify(savedForLater));
  }, [savedForLater]);

  useEffect(() => {
    localStorage.setItem('nexhaat_wishlist', JSON.stringify(wishlist));
  }, [wishlist]);

  useEffect(() => {
    if (flaskUser?.role !== 'customer') return;
    let active = true;
    fetchMarketplaceWishlist()
      .then((ids) => {
        if (active) setWishlist(ids);
      })
      .catch(() => {
        // Local wishlist remains available when the server session is unavailable.
      });
    return () => {
      active = false;
    };
  }, [flaskUser]);

  useEffect(() => {
    if (flaskUser?.role === 'customer') return;
    localStorage.setItem('nexhaat_orders', JSON.stringify(orders));
  }, [flaskUser, orders]);

  useEffect(() => {
    localStorage.setItem('nexhaat_lang', language);
  }, [language]);

  useEffect(() => {
    localStorage.setItem('nexhaat_prime', String(isPrimeMember));
  }, [isPrimeMember]);

  useEffect(() => {
    localStorage.setItem('nexhaat_theme', isDarkMode ? 'dark' : 'light');
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

  const toggleDarkMode = () => {
    setIsDarkMode(prev => !prev);
  };

  const togglePrimeMembership = () => {
    setIsPrimeMember(prev => {
      const next = !prev;
      showToast(
        next 
          ? '🎉 Welcome to NexHaat Prime! Unlimited FREE 3-hour delivery activated.'
          : 'Prime membership cancelled.',
        'success'
      );
      return next;
    });
    setIsPrimeModalOpen(false);
  };

  const showToast = (message: string, type: 'success' | 'info' | 'warning' | 'error' = 'success') => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts(prev => [...prev, { id, type, message }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 3800);
  };

  const t = (en: string, bn: string): string => {
    return language === 'bn' ? bn : en;
  };

  const formatPrice = (amount: number): string => {
    if (isNaN(amount)) return '৳0.00';
    const formatted = amount.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
    return language === 'bn' ? `৳ ${formatted}` : `৳${formatted}`;
  };

  const navigateToProduct = (slug: string) => {
    const prod = products.find(p => p.slug === slug);
    if (prod) recordRecentlyViewed(prod);
    setSelectedProductSlug(slug);
    setCurrentView('product-detail');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const navigateToCategory = (categorySlug: string) => {
    setActiveCategorySlug(categorySlug);
    setSearchQuery('');
    setCurrentView('catalog');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const setUserRole = (role: UserRole) => {
    setCurrentRole(role);
    showToast(
      language === 'bn' 
        ? `ভূমিকা পরিবর্তন করা হয়েছে: ${role.toUpperCase()}` 
        : `Switched perspective to ${role.toUpperCase()} Workspace`, 
      'info'
    );
    if (role === 'seller') setCurrentView('seller-portal');
    else if (role === 'rider') setCurrentView('rider-portal');
    else if (role === 'admin') setCurrentView('admin-portal');
    else setCurrentView('home');
  };

  // Cart Management
  const addToCart = async (product: Product, variant?: ProductVariant, quantity = 1) => {
    if (flaskUser?.role === 'customer') {
      try {
        await addMarketplaceCartItem(product, variant, quantity);
      } catch (error) {
        showToast(error instanceof Error ? error.message : t('Unable to update server cart.', 'সার্ভার কার্ট আপডেট করা যায়নি।'), 'error');
        return;
      }
    }
    recordRecentlyViewed(product);
    setCart(prev => {
      const existingIndex = prev.findIndex(
        item => item.product.id === product.id && item.selectedVariant?.id === variant?.id
      );

      if (existingIndex > -1) {
        const updated = [...prev];
        const newQty = updated[existingIndex].quantity + quantity;
        const availableStock = variant ? variant.stock : product.stock_quantity;
        updated[existingIndex].quantity = Math.min(newQty, availableStock);
        return updated;
      } else {
        return [...prev, { product, selectedVariant: variant, quantity }];
      }
    });

    showToast(
      t(
        `Added "${product.name}" to cart`,
        `"${product.name_bn || product.name}" কার্টে যোগ করা হয়েছে`
      )
    );
  };

  const updateCartQuantity = async (productId: number, variantId: string | undefined, quantity: number) => {
    if (quantity <= 0) {
      await removeFromCart(productId, variantId);
      return;
    }
    if (flaskUser?.role === 'customer') {
      try {
        await updateMarketplaceCartItem(productId, variantId, quantity);
      } catch (error) {
        showToast(error instanceof Error ? error.message : t('Unable to update server cart.', 'সার্ভার কার্ট আপডেট করা যায়নি।'), 'error');
        return;
      }
    }
    setCart(prev =>
      prev.map(item => {
        if (item.product.id === productId && item.selectedVariant?.id === variantId) {
          const maxStock = item.selectedVariant ? item.selectedVariant.stock : item.product.stock_quantity;
          return { ...item, quantity: Math.min(quantity, maxStock) };
        }
        return item;
      })
    );
  };

  const removeFromCart = async (productId: number, variantId?: string) => {
    if (flaskUser?.role === 'customer') {
      try {
        await removeMarketplaceCartItem(productId, variantId);
      } catch (error) {
        showToast(error instanceof Error ? error.message : t('Unable to update server cart.', 'সার্ভার কার্ট আপডেট করা যায়নি।'), 'error');
        return;
      }
    }
    setCart(prev =>
      prev.filter(
        item => !(item.product.id === productId && item.selectedVariant?.id === variantId)
      )
    );
    showToast(t('Item removed from cart', 'পণ্যটি কার্ট থেকে সরানো হয়েছে'), 'info');
  };

  // Save for Later (Amazon style)
  const saveForLater = (productId: number, variantId?: string) => {
    const itemToSave = cart.find(
      i => i.product.id === productId && i.selectedVariant?.id === variantId
    );
    if (itemToSave) {
      removeFromCart(productId, variantId);
      setSavedForLater(prev => [...prev, itemToSave]);
      showToast(t('Item saved for later', 'পণ্যটি পরে কেনার জন্য সংরক্ষণ করা হয়েছে'), 'info');
    }
  };

  const moveToCartFromSaved = (productId: number, variantId?: string) => {
    const itemToMove = savedForLater.find(
      i => i.product.id === productId && i.selectedVariant?.id === variantId
    );
    if (itemToMove) {
      setSavedForLater(prev =>
        prev.filter(i => !(i.product.id === productId && i.selectedVariant?.id === variantId))
      );
      addToCart(itemToMove.product, itemToMove.selectedVariant, itemToMove.quantity);
    }
  };

  const removeFromSaved = (productId: number, variantId?: string) => {
    setSavedForLater(prev =>
      prev.filter(i => !(i.product.id === productId && i.selectedVariant?.id === variantId))
    );
  };

  const clearCart = () => {
    setCart([]);
  };

  const cartCount = cart.reduce((total, item) => total + item.quantity, 0);

  // Cart subtotal with bulk discounts applied if applicable
  const cartSubtotal = cart.reduce((total, item) => {
    const basePrice = item.product.discount_price ?? item.product.price;
    const modifier = item.selectedVariant?.priceModifier || 0;
    let itemPrice = basePrice + modifier;

    // Amazon-style Tiered Bulk Discount calculation
    if (item.product.bulk_discounts && item.product.bulk_discounts.length > 0) {
      const applicableTier = item.product.bulk_discounts
        .filter(tier => item.quantity >= tier.minQty)
        .sort((a, b) => b.minQty - a.minQty)[0];
      if (applicableTier) {
        itemPrice = itemPrice * (1 - applicableTier.discountPercent / 100);
      }
    }

    return total + itemPrice * item.quantity;
  }, 0);

  // Product Comparison
  const toggleCompare = (productId: number) => {
    setComparedProductIds(prev => {
      if (prev.includes(productId)) {
        showToast(t('Removed from comparison', 'তুলনা তালিকা থেকে সরানো হয়েছে'), 'info');
        return prev.filter(id => id !== productId);
      }
      if (prev.length >= 4) {
        showToast(t('You can compare up to 4 products at once', 'সর্বোচ্চ ৪টি পণ্য একসঙ্গে তুলনা করতে পারবেন'), 'warning');
        return prev;
      }
      showToast(t('Added to product comparison', 'পণ্যটি তুলনা তালিকায় যোগ করা হয়েছে'));
      return [...prev, productId];
    });
  };

  const clearCompare = () => {
    setComparedProductIds([]);
  };

  // Recently Viewed
  const recordRecentlyViewed = (product: Product) => {
    setRecentlyViewed(prev => {
      const filtered = prev.filter(p => p.id !== product.id);
      return [product, ...filtered].slice(0, 8);
    });
  };

  // Wishlist
  const toggleWishlist = async (productId: number) => {
    const exists = wishlist.includes(productId);
    const product = products.find(p => p.id === productId);
    if (flaskUser?.role === 'customer') {
      try {
        if (exists) await removeMarketplaceWishlistItem(productId);
        else await addMarketplaceWishlistItem(productId);
      } catch (error) {
        showToast(error instanceof Error ? error.message : t('Unable to update wishlist.', 'উইশলিস্ট আপডেট করা যায়নি।'), 'error');
        return;
      }
    }
    if (exists) {
      setWishlist(prev => prev.filter(id => id !== productId));
      showToast(t('Removed from wishlist', 'উইশলিস্ট থেকে সরানো হয়েছে'), 'info');
    } else {
      setWishlist(prev => [...prev, productId]);
      showToast(
        t(
          `Saved ${product?.name || 'product'} to wishlist`,
          `পণ্যটি উইশলিস্টে সংরক্ষণ করা হয়েছে`
        )
      );
    }
  };

  const isInWishlist = (productId: number) => wishlist.includes(productId);
  const wishlistCount = wishlist.length;

  // Coupon / Promo
  const applyCoupon = (code: string): boolean => {
    const cleaned = code.trim().toUpperCase();
    const promo = INITIAL_PROMOTIONS.find(p => p.code === cleaned && p.is_active);

    if (!promo) {
      showToast(t('Invalid or expired coupon code', 'অবৈধ বা মেয়াদোত্তীর্ণ কুপন কোড'), 'error');
      return false;
    }

    if (cartSubtotal < promo.min_spend) {
      showToast(
        t(
          `Minimum spend of ${formatPrice(promo.min_spend)} required for this coupon`,
          `এই কুপনের জন্য নূন্যতম ${formatPrice(promo.min_spend)} ক্রয়ের প্রয়োজন`
        ),
        'warning'
      );
      return false;
    }

    setActiveCoupon(promo);
    showToast(
      t(`Coupon "${promo.code}" applied successfully!`, `কুপন "${promo.code}" সফলভাবে প্রয়োগ করা হয়েছে!`),
      'success'
    );
    return true;
  };

  const removeCoupon = () => {
    setActiveCoupon(null);
    showToast(t('Coupon removed', 'কুপন সরানো হয়েছে'), 'info');
  };

  let appliedPromoDiscount = 0;
  if (activeCoupon) {
    if (activeCoupon.discount_percent) {
      appliedPromoDiscount = (cartSubtotal * activeCoupon.discount_percent) / 100;
    } else if (activeCoupon.discount_amount) {
      appliedPromoDiscount = activeCoupon.discount_amount;
    }
  }

  // Order Placement
  const placeOrder = (
    orderData: Omit<Order, 'id' | 'order_number' | 'created_at' | 'status'>
  ): Order => {
    const randomSuffix = Math.floor(1000 + Math.random() * 9000);
    const orderNumber = `NH-2026-${randomSuffix}`;
    const newOrder: Order = {
      ...orderData,
      id: `ord-${Date.now()}`,
      order_number: orderNumber,
      created_at: new Date().toISOString(),
      status: 'confirmed',
    };

    setOrders(prev => [newOrder, ...prev]);
    setLastConfirmedOrder(newOrder);
    clearCart();
    setActiveCoupon(null);

    const orderNotification: Notification = {
      id: `notif-${Date.now()}`,
      type: 'order',
      title: `Order Placed Successfully #${orderNumber}`,
      title_bn: `অর্ডার সফলভাবে সম্পন্ন হয়েছে #${orderNumber}`,
      message: `Your order for ৳${newOrder.total_amount.toFixed(2)} has been confirmed with ${newOrder.payment_method.toUpperCase()}.`,
      message_bn: `আপনার ৳${newOrder.total_amount.toFixed(2)} টাকার অর্ডারটি নিশ্চিত করা হয়েছে।`,
      link: 'my-orders',
      is_read: false,
      created_at: new Date().toISOString(),
    };
    setNotifications(prev => [orderNotification, ...prev]);

    // Persist to Cloud Firestore
    if (auth.currentUser) {
      setDoc(doc(db, 'orders', newOrder.id), {
        id: newOrder.id,
        orderNumber: newOrder.order_number,
        userId: auth.currentUser.uid,
        totalAmount: newOrder.total_amount,
        status: newOrder.status,
        paymentMethod: newOrder.payment_method,
        createdAt: newOrder.created_at,
      }).catch(err => {
        handleFirestoreError(err, OperationType.CREATE, `orders/${newOrder.id}`);
      });
    }

    return newOrder;
  };

  const createMarketplaceOrder = async (input: {
    customerName: string;
    phone: string;
    address: string;
    city: string;
    promotionCode?: string;
  }): Promise<Order> => {
    const order = await submitMarketplaceCheckout(input);
    setOrders(prev => [order, ...prev.filter(item => item.order_number !== order.order_number)]);
    setLastConfirmedOrder(order);
    setCart([]);
    setActiveCoupon(null);
    return order;
  };

  const cancelOrder = async (orderNumber: string) => {
    if (flaskUser?.role === 'customer') {
      try {
        const order = await cancelMarketplaceOrder(orderNumber);
        setOrders(prev => prev.map(item => item.order_number === orderNumber ? order : item));
        showToast(t(`Order ${orderNumber} has been cancelled`, `অর্ডার ${orderNumber} বাতিল করা হয়েছে`), 'info');
      } catch (error) {
        showToast(error instanceof Error ? error.message : t('Unable to cancel the order.', 'অর্ডার বাতিল করা যায়নি।'), 'error');
      }
      return;
    }
    setOrders(prev =>
      prev.map(ord =>
        ord.order_number === orderNumber ? { ...ord, status: 'cancelled' } : ord
      )
    );
    showToast(
      t(`Order ${orderNumber} has been cancelled`, `অর্ডার ${orderNumber} বাতিল করা হয়েছে`),
      'info'
    );
  };

  const requestOrderReturn = async (orderNumber: string, reason: string) => {
    if (flaskUser?.role === 'customer') {
      try {
        const order = await requestMarketplaceReturn(orderNumber, reason);
        setOrders(prev => prev.map(item => item.order_number === orderNumber ? order : item));
        showToast(t('Return request submitted for review', 'রিটার্ন আবেদন পর্যালোচনার জন্য পাঠানো হয়েছে'), 'success');
      } catch (error) {
        showToast(error instanceof Error ? error.message : t('Unable to submit the return request.', 'রিটার্ন আবেদন পাঠানো যায়নি।'), 'error');
      }
      return;
    }
    const refundRef = `REF-${Math.floor(100000 + Math.random() * 900000)}`;
    setOrders(prev =>
      prev.map(ord =>
        ord.order_number === orderNumber
          ? {
              ...ord,
              return_status: 'requested',
              return_reason: reason,
              return_refund_ref: refundRef,
            }
          : ord
      )
    );
    showToast(
      t('Return request submitted for review', 'রিটার্ন আবেদন পর্যালোচনাধীন রয়েছে'),
      'success'
    );
  };

  const updateOrderStatus = (
    orderNumber: string,
    status: OrderStatus,
    riderInfo?: { name: string; phone: string }
  ) => {
    setOrders(prev =>
      prev.map(ord => {
        if (ord.order_number === orderNumber) {
          return {
            ...ord,
            status,
            rider_name: riderInfo?.name ?? ord.rider_name,
            rider_phone: riderInfo?.phone ?? ord.rider_phone,
            payment_status: status === 'delivered' ? 'paid' : ord.payment_status,
          };
        }
        return ord;
      })
    );
    showToast(t(`Order ${orderNumber} updated to ${status}`, `অর্ডার স্ট্যাটাস আপডেট: ${status}`));
  };

  // Products CRUD
  const addProduct = (productData: Omit<Product, 'id' | 'rating' | 'review_count' | 'sku'> & { sku?: string }) => {
    const newId = Math.max(...products.map(p => p.id), 100) + 1;
    const newProduct: Product = {
      ...productData,
      id: newId,
      sku: productData.sku || `NH-MAN-${newId}`,
      rating: 5.0,
      review_count: 1,
      moderation_status: 'approved',
    };
    setProducts(prev => [newProduct, ...prev]);
    showToast(t('Product added successfully', 'পণ্য সফলভাবে তালিকাভুক্ত হয়েছে'));
  };

  const updateProduct = (updated: Product) => {
    setProducts(prev => prev.map(p => (p.id === updated.id ? updated : p)));
    showToast(t('Product updated successfully', 'পণ্য সফলভাবে আপডেট করা হয়েছে'));
  };

  const deleteProduct = (id: number) => {
    setProducts(prev => prev.filter(p => p.id !== id));
    showToast(t('Product deleted', 'পণ্য মুছে ফেলা হয়েছে'), 'info');
  };

  const approveProduct = (id: number, approved: boolean) => {
    setProducts(prev =>
      prev.map(p =>
        p.id === id
          ? { ...p, moderation_status: approved ? 'approved' : 'rejected' }
          : p
      )
    );
    showToast(
      t(
        `Product #${id} ${approved ? 'approved' : 'rejected'}`,
        `পণ্যটি ${approved ? 'অনুমোদিত' : 'প্রত্যাখ্যাত'} হয়েছে`
      )
    );
  };

  // Reviews & Q&A
  const addReview = (productId: number, rating: number, comment: string) => {
    const newReview: Review = {
      id: `rev-${Date.now()}`,
      product_id: productId,
      user_name: currentUser.name,
      rating,
      comment,
      created_at: new Date().toISOString().split('T')[0],
      verified_purchase: true,
      helpful_count: 0,
    };
    setReviews(prev => [newReview, ...prev]);

    setProducts(prev =>
      prev.map(p => {
        if (p.id === productId) {
          const newCount = p.review_count + 1;
          const newAvg = Number(((p.rating * p.review_count + rating) / newCount).toFixed(1));
          return { ...p, rating: newAvg, review_count: newCount };
        }
        return p;
      })
    );

    showToast(t('Review submitted! Thank you.', 'আপনার মতামত গ্রহণ করা হয়েছে। ধন্যবাদ!'));

    if (auth.currentUser) {
      setDoc(doc(db, 'reviews', newReview.id), {
        id: newReview.id,
        productId: newReview.product_id,
        userId: auth.currentUser.uid,
        userName: newReview.user_name,
        rating: newReview.rating,
        comment: newReview.comment,
        createdAt: newReview.created_at,
      }).catch(err => {
        handleFirestoreError(err, OperationType.CREATE, `reviews/${newReview.id}`);
      });
    }
  };

  const getProductReviews = (productId: number) => {
    return reviews.filter(r => r.product_id === productId);
  };

  const addQuestion = (productId: number, questionText: string) => {
    const newQ: ProductQuestion = {
      id: `q-${Date.now()}`,
      product_id: productId,
      user_name: currentUser.name,
      question: questionText,
      created_at: new Date().toISOString().split('T')[0],
    };
    setQuestions(prev => [newQ, ...prev]);
    showToast(t('Question posted! Seller will respond soon.', 'আপনার প্রশ্ন জমা দেওয়া হয়েছে।'));
  };

  const getProductQuestions = (productId: number) => {
    return questions.filter(q => q.product_id === productId);
  };

  // Gemini AI Assistant Chat Logic
  const sendAIMessage = (text: string) => {
    const userMsg: AIChatMessage = {
      id: `usr-${Date.now()}`,
      sender: 'user',
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setAiMessages(prev => [...prev, userMsg]);

    // Intelligent AI response generation
    setTimeout(() => {
      const lower = text.toLowerCase();
      let reply = '';
      let suggested: number[] = [];

      if (lower.includes('fish') || lower.includes('ilish') || lower.includes('মাছ')) {
        reply = 'For fresh fish, I strongly recommend our Wild-Caught Padma Ilish (1.2kg). Hand-caught at Chandpur/Mawa ghat, formalin-tested, and delivered in insulated ice boxes. Would you like it Whole or Curry Cut?';
        suggested = [102];
      } else if (lower.includes('mango') || lower.includes('fruit') || lower.includes('আম')) {
        reply = 'The Rajshahi Fazli Mango 5kg Crate is currently in season! It is tree-ripened without artificial carbide. Today you also get a 15% flash discount.';
        suggested = [101];
      } else if (lower.includes('dinner') || lower.includes('recipe') || lower.includes('রান্না') || lower.includes('1500') || lower.includes('family')) {
        reply = 'Here is a royal Bangladeshi dinner menu for 4-5 people: 1) Authentic Dinajpur Chinigura Aromatic Rice, 2) Pure Mustard Oil for traditional bhorta, and 3) Bogra Shahi Misti Doi for dessert. Total comes to under ৳1,000!';
        suggested = [103, 105, 104];
      } else if (lower.includes('prime') || lower.includes('delivery') || lower.includes('shipping')) {
        reply = isPrimeMember
          ? 'You are currently an active NexHaat Prime Member! You enjoy guaranteed unlimited FREE 3-hour express delivery inside Dhaka and Chittagong with 5% cashback.'
          : 'With NexHaat Prime (only ৳199/month), you get unlimited FREE express delivery, priority rider dispatch, and member-only pricing!';
      } else {
        reply = `I found several highly rated items matching "${text}" on NexHaat with verified seller ratings above 4.8 stars. Check out these top recommendations:`;
        suggested = [101, 102, 107];
      }

      const botMsg: AIChatMessage = {
        id: `bot-${Date.now()}`,
        sender: 'assistant',
        text: reply,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        suggestedProductIds: suggested,
      };

      setAiMessages(prev => [...prev, botMsg]);
    }, 600);
  };

  const clearAIChat = () => {
    setAiMessages([
      {
        id: 'ai-reset',
        sender: 'assistant',
        text: 'Chat history cleared. How else may I assist your shopping today?',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }
    ]);
  };

  // Sponsored Ads
  const addSponsoredCampaign = (camp: Omit<SponsoredCampaign, 'id' | 'impressions' | 'clicks' | 'spend'>) => {
    const newCamp: SponsoredCampaign = {
      ...camp,
      id: `camp-${Date.now()}`,
      impressions: 0,
      clicks: 0,
      spend: 0,
    };
    setSponsoredCampaigns(prev => [newCamp, ...prev]);
    showToast(t('Sponsored Ad campaign launched successfully!', 'স্পন্সরড ক্যাম্পেইন চালু করা হয়েছে!'));
  };

  // Notifications
  const unreadNotificationCount = notifications.filter(n => !n.is_read).length;

  const markNotificationAsRead = async (id: string) => {
    if (flaskUser?.role === 'customer') {
      try {
        await markMarketplaceNotificationRead(id);
      } catch (error) {
        showToast(error instanceof Error ? error.message : t('Unable to update notification.', 'বিজ্ঞপ্তি আপডেট করা যায়নি।'), 'error');
        return;
      }
    }
    setNotifications(prev =>
      prev.map(n => (n.id === id ? { ...n, is_read: true } : n))
    );
  };

  const markAllNotificationsAsRead = async () => {
    if (flaskUser?.role === 'customer') {
      try {
        await markAllMarketplaceNotificationsRead();
      } catch (error) {
        showToast(error instanceof Error ? error.message : t('Unable to update notifications.', 'বিজ্ঞপ্তিগুলো আপডেট করা যায়নি।'), 'error');
        return;
      }
    }
    setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
    showToast(t('All notifications marked as read', 'সকল নোটিফিকেশন পড়া হয়েছে'));
  };

  // Price Alerts Engine
  const setPriceAlert = (productId: number, targetPrice: number): PriceAlert => {
    const product = products.find(p => p.id === productId);
    if (!product) throw new Error('Product not found');

    const currentPrice = product.discount_price ?? product.price;
    const isAlreadyAtOrBelow = currentPrice <= targetPrice;

    const existing = priceAlerts.find(a => a.product_id === productId);
    const alertId = existing ? existing.id : `pa-${Date.now()}`;

    const newAlert: PriceAlert = {
      id: alertId,
      product_id: product.id,
      product_name: product.name,
      product_name_bn: product.name_bn,
      product_image: product.image,
      product_slug: product.slug,
      initial_price: currentPrice,
      target_price: targetPrice,
      current_price: currentPrice,
      is_active: true,
      is_triggered: isAlreadyAtOrBelow,
      created_at: new Date().toISOString(),
      triggered_at: isAlreadyAtOrBelow ? new Date().toISOString() : undefined,
    };

    setPriceAlerts(prev => [newAlert, ...prev.filter(a => a.product_id !== productId)]);

    if (isAlreadyAtOrBelow) {
      const alertNotif: Notification = {
        id: `notif-pa-${Date.now()}`,
        type: 'price_alert',
        title: `🎯 Price Alert Triggered: ${product.name}`,
        title_bn: `🎯 মূল্য হ্রাস সতর্কতা: ${product.name_bn || product.name}`,
        message: `Great news! The current price of ${product.name} (৳${currentPrice}) is already at or below your target price of ৳${targetPrice}!`,
        message_bn: `দারুণ খবর! ${product.name_bn || product.name}-এর বর্তমান দর (৳${currentPrice}) আপনার লক্ষ্যমূল্য ৳${targetPrice}-এর সমান বা নিচে নেমেছে!`,
        link: 'product-detail',
        product_slug: product.slug,
        is_read: false,
        created_at: new Date().toISOString(),
      };
      setNotifications(prev => [alertNotif, ...prev]);
      showToast(
        t(
          `Price alert active! Current price (৳${currentPrice}) already meets target (৳${targetPrice}). Notification sent!`,
          `সতর্কতা সক্রিয়! বর্তমান দর (৳${currentPrice}) আপনার লক্ষ্য পূরণ করেছে। নোটিফিকেশন পাঠানো হয়েছে!`
        ),
        'success'
      );
    } else {
      showToast(
        t(
          `Price alert set for ${product.name}! We'll notify you when it drops to ৳${targetPrice} or lower.`,
          `${product.name}-এর জন্য সতর্কতা সক্রিয়! দর ৳${targetPrice} বা তার নিচে নামলে নোটিফিকেশন পাবেন।`
        ),
        'success'
      );
    }

    return newAlert;
  };

  const removePriceAlert = (productId: number) => {
    setPriceAlerts(prev => prev.filter(a => a.product_id !== productId));
    showToast(t('Price alert removed', 'মূল্য সতর্কতা মুছে ফেলা হয়েছে'), 'info');
  };

  const getPriceAlert = (productId: number) => {
    return priceAlerts.find(a => a.product_id === productId);
  };

  const simulatePriceDrop = (productId: number, newPrice?: number) => {
    const product = products.find(p => p.id === productId);
    if (!product) return;

    const alert = priceAlerts.find(a => a.product_id === productId);
    const dropTarget = newPrice ?? (alert ? alert.target_price : Math.round((product.discount_price ?? product.price) * 0.85));

    setProducts(prev =>
      prev.map(p => (p.id === productId ? { ...p, discount_price: dropTarget } : p))
    );

    setPriceAlerts(prev =>
      prev.map(a =>
        a.product_id === productId
          ? {
              ...a,
              current_price: dropTarget,
              is_triggered: true,
              triggered_at: new Date().toISOString(),
            }
          : a
      )
    );

    const alertNotif: Notification = {
      id: `notif-pa-${Date.now()}`,
      type: 'price_alert',
      title: `🎯 Price Alert Triggered: ${product.name}`,
      title_bn: `🎯 মূল্য হ্রাস সতর্কতা: ${product.name_bn || product.name}`,
      message: `Great news! The price of ${product.name} dropped to ৳${dropTarget}, reaching your target of ৳${alert?.target_price ?? dropTarget}!`,
      message_bn: `দারুণ খবর! ${product.name_bn || product.name}-এর মূল্য কমে ৳${dropTarget} হয়েছে, যা আপনার লক্ষ্যমূল্য ৳${alert?.target_price ?? dropTarget}-এ পৌঁছেছে!`,
      link: 'product-detail',
      product_slug: product.slug,
      is_read: false,
      created_at: new Date().toISOString(),
    };

    setNotifications(prev => [alertNotif, ...prev]);
    showToast(
      t(
        `⚡ Price drop simulated! ${product.name} is now ৳${dropTarget}. Notification sent!`,
        `⚡ মূল্য হ্রাস টেস্ট সফল! ${product.name}-এর নতুন দর ৳${dropTarget}। নোটিফিকেশন পাঠানো হয়েছে!`
      ),
      'success'
    );
  };

  return (
    <AppContext.Provider
      value={{
        priceAlerts,
        setPriceAlert,
        removePriceAlert,
        getPriceAlert,
        simulatePriceDrop,
        currentView,
        setCurrentView,
        selectedProductSlug,
        setSelectedProductSlug,
        activeCategorySlug,
        setActiveCategorySlug,
        searchQuery,
        setSearchQuery,
        navigateToProduct,
        navigateToCategory,
        language,
        setLanguage,
        isDarkMode,
        toggleDarkMode,
        t,
        formatPrice,
        currentUser,
        setUserRole,
        isPrimeMember,
        togglePrimeMembership,
        isPrimeModalOpen,
        setIsPrimeModalOpen,
        products,
        categories,
        addProduct,
        updateProduct,
        deleteProduct,
        approveProduct,
        cart,
        savedForLater,
        addToCart,
        updateCartQuantity,
        removeFromCart,
        saveForLater,
        moveToCartFromSaved,
        removeFromSaved,
        clearCart,
        cartCount,
        cartSubtotal,
        isCartDrawerOpen,
        setIsCartDrawerOpen,
        comparedProductIds,
        toggleCompare,
        clearCompare,
        isCompareModalOpen,
        setIsCompareModalOpen,
        recentlyViewed,
        recordRecentlyViewed,
        wishlist,
        toggleWishlist,
        isInWishlist,
        wishlistCount,
        orders,
        lastConfirmedOrder,
        placeOrder,
        cancelOrder,
        requestOrderReturn,
        updateOrderStatus,
        activeCoupon,
        appliedPromoDiscount,
        applyCoupon,
        removeCoupon,
        reviews,
        addReview,
        getProductReviews,
        questions,
        addQuestion,
        getProductQuestions,
        isAIAssistantOpen,
        setIsAIAssistantOpen,
        aiMessages,
        sendAIMessage,
        clearAIChat,
        sponsoredCampaigns,
        addSponsoredCampaign,
        notifications,
        unreadNotificationCount,
        markNotificationAsRead,
        markAllNotificationsAsRead,
        toasts,
        showToast,
        firebaseUser,
        loginWithGoogle,
        logoutFirebase,
        isFirebaseAuthLoading,
        flaskUser,
        isFlaskAuthLoading,
        loginWithFlask,
        verifyTwoFactorChallenge,
        logoutFlask,
        startFlaskRegistration: beginFlaskRegistration,
        submitMarketplaceCheckout: createMarketplaceOrder,
        isMarketplaceCatalogLoading,
        marketplaceCatalogError,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
