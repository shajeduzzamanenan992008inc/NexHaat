# NexHaat — Amazon-Level Mega Multi-Vendor Marketplace

NexHaat is Bangladesh's premier hyper-local mega multi-vendor marketplace platform built for fresh foods, organic produce, river fish, groceries, fashion, electronics, and daily essentials.

Built with **React 18 + TypeScript + Vite + Tailwind CSS**, NexHaat features an Amazon-inspired architecture customized for Bangladesh's commerce ecosystem, featuring full bilingual support (English/Bengali), dark mode, authentic Bangladeshi payment gateways, multi-vendor workspaces, and Gemini AI shopping assistance.

---

## 🌟 Amazon-Level Feature Architecture

### 1. Customer Experience & Discovery
- **NexHaat Prime Membership**:
  - Unlimited FREE 3-Hour Express Delivery inside Dhaka and Chittagong.
  - 5% Wallet Cashback on all purchases.
  - Exclusive member-only deals and early access to Eid flash sales.
  - Monthly (৳199/mo) and Yearly (৳1,999/yr) plans.
- **Gemini HaatAI Shopping Copilot**:
  - Floating interactive AI assistant with recipe ideas, menu planning (e.g. "Dinner for 5 under ৳1,500"), and product discovery.
  - Direct 1-click "Add to Cart" embedded directly in AI chat messages.
  - Automated AI Review Summarizer on product pages.
- **Product Comparison Matrix**:
  - Compare up to 4 products side-by-side on price, rating, halal certification, regional origin, shelf life, and seller reputation.
  - Floating sticky comparison bar for easy access.
- **Save for Later & Recently Viewed**:
  - Dedicated "Save for Later" section in cart drawer.
  - Persistent browsing history shelf on the homepage.
- **Product Q&A (Questions & Answers)**:
  - Ask community and seller questions directly on product pages with verified merchant answers.
- **Voice & Visual Search Simulation**:
  - Voice query and image search integration in the search bar.
- **Theme & Dark Mode**:
  - Seamless Light and Dark mode toggle with persistent preferences.

### 2. Multi-Vendor Marketplace & Seller Central
- **Seller Inventory & Catalog CRUD**:
  - Manage SKUs, stock levels, regular & discount pricing, and variants.
  - Bulk CSV/Excel inventory synchronization simulation.
- **Amazon Ads Sponsored Products**:
  - Launch sponsored product campaigns with daily budget, max CPC bid, and real-time impression & click tracking.
- **Tiered Wholesale / Bulk Discounts (B2B)**:
  - Volume pricing for restaurants and families (e.g., Buy 2+ get 5% off, Buy 5+ get 15% off).
- **Order Fulfillment & Packaging Queue**:
  - Transition orders from Confirmed → Processing/Packaging → Handover to Express Rider.

### 3. Hyper-Local Delivery & Rider Hub
- **Dedicated Rider Operations**:
  - Real-time assigned deliveries queue with customer contact and address mapping.
  - Status management: "Pickup from Store" → "Out for Delivery" → "Delivered & Cash Collected".
  - Daily delivery performance tracking and Cash-on-Delivery settlement.

### 4. Admin Operations & Platform Governance
- **Fulfillment Warehouses**:
  - Monitor Central Karwan Bazar, Mirpur Express Hub, Uttara Depo, and Khatunganj Depo capacities.
- **Category Commission Matrix**:
  - Custom commission rates across categories (Produce 4.5%, Seafood 5.0%, Electronics 8.5%, Fashion 10%).
- **Product Moderation**:
  - Review queue to approve or reject merchant listings ensuring food quality and halal certification.
- **Real-Time Audit Stream**:
  - Live security logs of all transactions, logins, and ad campaigns.

---

## 🛠️ Development & Build

### Prerequisites
- Node.js 20+
- npm

### Development Server
```bash
npm install
npm run dev
```
Starts development server on `http://0.0.0.0:3000`.

### Typecheck & Lint
```bash
npm run lint
```

### Production Build
```bash
npm run build
npm run preview
```
