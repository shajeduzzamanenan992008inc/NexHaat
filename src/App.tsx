import React, { Suspense } from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { Navbar } from './components/Navbar';
import { CartDrawer } from './components/CartDrawer';
import { ToastContainer } from './components/Toast';
import { Footer } from './components/Footer';
import { AIAssistantDrawer } from './components/AIAssistantDrawer';
import { CompareModal } from './components/CompareModal';
import { ComparisonBar } from './components/ComparisonBar';
import { PrimeModal } from './components/PrimeModal';
import { OfflineIndicator } from './components/OfflineIndicator';


const HomePage = React.lazy(() => import('./pages/HomePage').then(({ HomePage }) => ({ default: HomePage })));
const CatalogPage = React.lazy(() =>
  import('./pages/CatalogPage').then(({ CatalogPage }) => ({ default: CatalogPage })),
);
const DealsPage = React.lazy(() => import('./pages/DealsPage').then(({ DealsPage }) => ({ default: DealsPage })));
const ProductDetailPage = React.lazy(() =>
  import('./pages/ProductDetailPage').then(({ ProductDetailPage }) => ({ default: ProductDetailPage })),
);
const CheckoutPage = React.lazy(() =>
  import('./pages/CheckoutPage').then(({ CheckoutPage }) => ({ default: CheckoutPage })),
);
const OrderConfirmationPage = React.lazy(() =>
  import('./pages/OrderConfirmationPage').then(({ OrderConfirmationPage }) => ({ default: OrderConfirmationPage })),
);
const MyOrdersPage = React.lazy(() =>
  import('./pages/MyOrdersPage').then(({ MyOrdersPage }) => ({ default: MyOrdersPage })),
);
const WishlistPage = React.lazy(() =>
  import('./pages/WishlistPage').then(({ WishlistPage }) => ({ default: WishlistPage })),
);
const NotificationsPage = React.lazy(() =>
  import('./pages/NotificationsPage').then(({ NotificationsPage }) => ({ default: NotificationsPage })),
);
const SellerPortalPage = React.lazy(() =>
  import('./pages/SellerPortalPage').then(({ SellerPortalPage }) => ({ default: SellerPortalPage })),
);
const RiderPortalPage = React.lazy(() =>
  import('./pages/RiderPortalPage').then(({ RiderPortalPage }) => ({ default: RiderPortalPage })),
);
const AdminPortalPage = React.lazy(() =>
  import('./pages/AdminPortalPage').then(({ AdminPortalPage }) => ({ default: AdminPortalPage })),
);
const SupportPage = React.lazy(() =>
  import('./pages/SupportPage').then(({ SupportPage }) => ({ default: SupportPage })),
);

import { SplashScreen } from './components/SplashScreen';
import { ScrollProgressBar } from './components/ScrollProgressBar';
import { AICopilotFAB } from './components/AICopilotFAB';

const AppContent: React.FC = () => {
  const { currentView, isMarketplaceCatalogLoading, marketplaceCatalogError, t } = useApp();
  const isPreviewPortal = ['seller-portal', 'rider-portal', 'admin-portal'].includes(currentView);
  const [showSplash, setShowSplash] = React.useState(() => {
    try {
      return !sessionStorage.getItem('nexhaat_splash_viewed');
    } catch {
      return false;
    }
  });

  const handleSplashComplete = () => {
    setShowSplash(false);
    try {
      sessionStorage.setItem('nexhaat_splash_viewed', 'true');
    } catch {}
  };

  const renderCurrentView = () => {
    switch (currentView) {
      case 'home':
        return <HomePage />;
      case 'catalog':
        return <CatalogPage />;
      case 'deals':
        return <DealsPage />;
      case 'product-detail':
        return <ProductDetailPage />;
      case 'checkout':
        return <CheckoutPage />;
      case 'order-confirmation':
        return <OrderConfirmationPage />;
      case 'my-orders':
        return <MyOrdersPage />;
      case 'wishlist':
        return <WishlistPage />;
      case 'notifications':
        return <NotificationsPage />;
      case 'seller-portal':
        return <SellerPortalPage />;
      case 'rider-portal':
        return <RiderPortalPage />;
      case 'admin-portal':
        return <AdminPortalPage />;
      case 'support':
        return <SupportPage />;
      default:
        return <HomePage />;
    }
  };

  return (
    <div className="marketplace-app min-h-screen flex flex-col bg-page dark:bg-slate-950 transition-colors relative">
      {showSplash && <SplashScreen onComplete={handleSplashComplete} />}
      <ScrollProgressBar />
      <Navbar />
      {(isMarketplaceCatalogLoading || marketplaceCatalogError) && (
        <div className="marketplace-preview-notice mx-auto mt-3 flex w-[calc(100%-2rem)] max-w-[1536px] items-center justify-between gap-3 rounded-xl px-4 py-2.5 text-xs sm:text-sm" role="status">
          <span>
          {isMarketplaceCatalogLoading && !marketplaceCatalogError
            ? t(
                'Connecting to the live catalog. Listings will appear when the catalog loads.',
                'লাইভ ক্যাটালগে সংযোগ হচ্ছে। ক্যাটালগ লোড হলে পণ্য দেখা যাবে।',
              )
            : t(
                'Live catalog connection is unavailable. Product listings are hidden until the catalog is available.',
                'লাইভ ক্যাটালগ সংযোগ পাওয়া যাচ্ছে না। ক্যাটালগ চালু হলে পণ্যের তালিকা দেখা যাবে।',
              )}
          </span>
          {!isMarketplaceCatalogLoading && marketplaceCatalogError && (
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="shrink-0 rounded-lg bg-primary px-3 py-1.5 text-xs font-bold text-white transition-colors hover:bg-primary-hover"
            >
              {t('Retry', 'আবার চেষ্টা করুন')}
            </button>
          )}
        </div>
      )}
      {isPreviewPortal && (
        <div className="mx-auto mt-3 w-[calc(100%-2rem)] max-w-[1536px] rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-xs text-amber-900 sm:text-sm" role="note">
          {t(
            'This React workspace is a local preview. Marketplace identity, permissions, and operations remain in Flask.',
            'এই React workspace স্থানীয় প্রিভিউ। মার্কেটপ্লেস পরিচয়, অনুমতি ও কার্যক্রম Flask-এ থাকে।'
          )}
        </div>
      )}
      <CartDrawer />
      <AIAssistantDrawer />
      <AICopilotFAB />
      <CompareModal />
      <ComparisonBar />
      <PrimeModal />
      <OfflineIndicator />
      <ToastContainer />

      <main className="flex-1 max-w-[1600px] w-full mx-auto px-4 sm:px-6 xl:px-8 pt-6 sm:pt-8">
        <Suspense
          fallback={
            <div className="neu-flat rounded-2xl p-8 text-center animate-pulse" role="status" aria-live="polite">
              Loading NexHaat...
            </div>
          }
        >
          <div key={currentView} className="animate-view-enter">
            {renderCurrentView()}
          </div>
        </Suspense>
      </main>

      <Footer />
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
};

export default App;
