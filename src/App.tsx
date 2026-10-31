import React from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { Navbar } from './components/Navbar';
import { CartDrawer } from './components/CartDrawer';
import { ToastContainer } from './components/Toast';
import { Footer } from './components/Footer';
import { AIAssistantDrawer } from './components/AIAssistantDrawer';
import { CompareModal } from './components/CompareModal';
import { ComparisonBar } from './components/ComparisonBar';
import { PrimeModal } from './components/PrimeModal';

// Pages
import { HomePage } from './pages/HomePage';
import { CatalogPage } from './pages/CatalogPage';
import { DealsPage } from './pages/DealsPage';
import { ProductDetailPage } from './pages/ProductDetailPage';
import { CheckoutPage } from './pages/CheckoutPage';
import { OrderConfirmationPage } from './pages/OrderConfirmationPage';
import { MyOrdersPage } from './pages/MyOrdersPage';
import { WishlistPage } from './pages/WishlistPage';
import { NotificationsPage } from './pages/NotificationsPage';
import { SellerPortalPage } from './pages/SellerPortalPage';
import { RiderPortalPage } from './pages/RiderPortalPage';
import { AdminPortalPage } from './pages/AdminPortalPage';
import { SupportPage } from './pages/SupportPage';

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
      <Navbar />
      <CartDrawer />
      <AIAssistantDrawer />
      <CompareModal />
      <ComparisonBar />
      <PrimeModal />
      <ToastContainer />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 pt-6 sm:pt-8">
        {renderCurrentView()}
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
