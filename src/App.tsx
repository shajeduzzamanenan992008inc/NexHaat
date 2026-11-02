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
import { AmazonAppBanner } from './components/AmazonAppBanner';
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

const AppContent: React.FC = () => {
  const { currentView } = useApp();

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
    <div className="min-h-screen flex flex-col bg-page dark:bg-slate-950 transition-colors">
      <AmazonAppBanner />
      <Navbar />
      <CartDrawer />
      <AIAssistantDrawer />
      <CompareModal />
      <ComparisonBar />
      <PrimeModal />
      <OfflineIndicator />
      <ToastContainer />


      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 pt-6 sm:pt-8">
        <Suspense
          fallback={
            <div className="neu-flat rounded-2xl p-8 text-center" role="status" aria-live="polite">
              Loading NexHaat...
            </div>
          }
        >
          {renderCurrentView()}
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
